"""Llamadas al LLM: análisis de imagen y texto del aviso al 012 (spec §7). Responsable: IA."""

import base64
import io
import json
import os
import re

import anthropic
from PIL import Image, ImageOps

MODELO = "claude-sonnet-5-5"

# §7.1, literal.
SYSTEM_ANALISIS = """Eres un experto entomólogo en especies invasoras de Galicia. Analizas una foto enviada por un ciudadano para decidir si muestra una avispa velutina (Vespa velutina) o su nido.

Distingue entre:
- velutina: cuerpo oscuro, banda naranja en el 4.º segmento abdominal, extremos de las patas amarillos, cara naranja. Nido secundario grande en copa de árbol con entrada lateral pequeña.
- crabro (avispón europeo, autóctono): tórax rojizo, abdomen mayoritariamente amarillo, patas marrones. Nidos en huecos, abiertos por abajo.
- otra: avispas comunes (Vespula, Polistes), abejas u otros insectos.
- no_concluyente: foto borrosa, lejana o sin rasgos visibles.

Sé prudente: si no ves rasgos claros, usa no_concluyente. Nunca recomiendes acercarse ni retirar el nido.

Responde SOLO con un JSON válido con esta forma:
{
  "tipo": "insecto" | "nido",
  "especie": "velutina" | "crabro" | "otra" | "no_concluyente",
  "confianza": número entre 0 y 1,
  "rasgos_observados": ["...", "..."],
  "explicacion": "1-2 frases en castellano para el ciudadano",
  "consejo_foto": "si no es concluyente, cómo hacer una foto mejor; si no, cadena vacía"
}"""

# Valores cerrados de AGENTS.md.
TIPOS = ("insecto", "nido")
ESPECIES = ("velutina", "crabro", "otra", "no_concluyente")

# Configuración del proveedor. Se lee de st.secrets si estamos dentro de
# Streamlit y, si no hay valor, de variables de entorno. Así el módulo funciona
# también desde pytest o un script suelto.
CLAVES = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "ANTHROPIC_API_KEY")

LADO_MAX = 1280  # px de lado máximo antes de enviar la imagen
MAX_TOKENS = 600
SIN_RAZONAMIENTO = {"type": "disabled"}

CONSEJO_FOTO = (
    "Haz otra foto más cerca y con buena luz, enfocando al insecto o al nido "
    "sin acercarte a él."
)
EXPLICACION_FALLO = "No he podido analizar la foto con seguridad."


def _secreto(nombre: str) -> str:
    """Valor de `nombre` en st.secrets o en el entorno; cadena vacía si no está."""
    try:  # fuera de Streamlit (o sin secrets.toml) st.secrets lanza
        import streamlit as st

        valor = st.secrets.get(nombre)
        if valor:
            return str(valor).strip()
    except Exception:
        pass
    return (os.environ.get(nombre) or "").strip()


def modelo() -> str:
    """Modelo a usar: LLM_MODEL si está definido; si no, MODELO (Anthropic)."""
    return _secreto("LLM_MODEL") or MODELO


_cliente: anthropic.Anthropic | None = None


def cliente() -> anthropic.Anthropic:
    """Cliente de Anthropic, creado una sola vez por proceso.

    Con LLM_BASE_URL apunta a una capa compatible (OpenRouter) usando
    LLM_API_KEY como auth_token; sin ella, habla con Anthropic con
    ANTHROPIC_API_KEY.
    """
    global _cliente
    if _cliente is None:
        base_url = _secreto("LLM_BASE_URL")
        if base_url:
            api_key = _secreto("LLM_API_KEY")
            if not api_key:
                raise ValueError("Falta LLM_API_KEY en .streamlit/secrets.toml o el entorno.")
            _cliente = anthropic.Anthropic(
                auth_token=api_key,
                api_key=None,
                base_url=base_url,
            )
        else:
            api_key = _secreto("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("Falta ANTHROPIC_API_KEY en .streamlit/secrets.toml o el entorno.")
            _cliente = anthropic.Anthropic(api_key=api_key)
    return _cliente


def _imagen_para_llm(imagen_bytes: bytes) -> bytes:
    """JPEG sin EXIF y con el lado mayor a 1280 px como máximo."""
    with Image.open(io.BytesIO(imagen_bytes)) as original:
        imagen = ImageOps.exif_transpose(original)  # orienta antes de perder el EXIF
        if imagen.mode != "RGB":
            imagen = imagen.convert("RGB")
        imagen.thumbnail((LADO_MAX, LADO_MAX), Image.LANCZOS)
        salida = io.BytesIO()
        imagen.save(salida, format="JPEG", quality=85)  # sin `exif=`: no se copia
    return salida.getvalue()


def _tipo_seguro(tipo: str) -> str:
    t = str(tipo or "").strip().lower()
    return t if t in TIPOS else "insecto"


def _no_concluyente(tipo: str) -> dict:
    """Resultado de §7.1 cuando no hay JSON usable o la API falla."""
    return {
        "tipo": _tipo_seguro(tipo),
        "especie": "no_concluyente",
        "confianza": 0.0,
        "rasgos_observados": [],
        "explicacion": EXPLICACION_FALLO,
        "consejo_foto": CONSEJO_FOTO,
    }


def _extraer_json(texto: str) -> dict | None:
    """Quita las vallas ```json (o el texto de alrededor) y parsea con json.loads."""
    limpio = (texto or "").strip()
    valla = re.search(r"```(?:json)?\s*(.*?)```", limpio, re.S | re.I)
    if valla:
        limpio = valla.group(1).strip()
    else:
        inicio, fin = limpio.find("{"), limpio.rfind("}")
        if inicio != -1 and fin > inicio:
            limpio = limpio[inicio : fin + 1]
    try:
        datos = json.loads(limpio)
    except (json.JSONDecodeError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def _validar(datos: dict, tipo_usuario: str) -> dict:
    """Comprueba los valores cerrados de AGENTS.md; si algo no cuadra, no concluyente."""
    tipo = str(datos.get("tipo") or "").strip().lower()
    especie = str(datos.get("especie") or "").strip().lower()
    confianza = datos.get("confianza")
    valido = (
        tipo in TIPOS
        and especie in ESPECIES
        and isinstance(confianza, (int, float))
        and not isinstance(confianza, bool)
        and 0.0 <= float(confianza) <= 1.0
    )
    if not valido:
        return _no_concluyente(tipo_usuario)

    rasgos = datos.get("rasgos_observados")
    if isinstance(rasgos, str):
        rasgos = [rasgos]
    elif not isinstance(rasgos, list):
        rasgos = []
    rasgos = [str(r).strip() for r in rasgos if str(r).strip()][:10]

    explicacion = str(datos.get("explicacion") or "").strip() or EXPLICACION_FALLO
    consejo = str(datos.get("consejo_foto") or "").strip()

    if especie == "no_concluyente":
        confianza = 0.0
        consejo = consejo or CONSEJO_FOTO

    return {
        "tipo": tipo,
        "especie": especie,
        "confianza": float(confianza),
        "rasgos_observados": rasgos,
        "explicacion": explicacion,
        "consejo_foto": consejo,
    }


def _llamar(mensajes: list) -> str:
    respuesta = cliente().messages.create(
        model=modelo(),
        max_tokens=MAX_TOKENS,
        system=SYSTEM_ANALISIS,
        thinking=SIN_RAZONAMIENTO,
        messages=mensajes,
    )
    return "".join(b.text for b in respuesta.content if b.type == "text")


def analizar_imagen(imagen_bytes: bytes, tipo: str, yolo_resumen: str = "") -> dict:
    """JSON de §7.1: tipo, especie, confianza, rasgos_observados, explicacion, consejo_foto.

    Si la respuesta no es JSON válido tras un reintento, devuelve especie "no_concluyente".
    """
    try:
        b64 = base64.standard_b64encode(_imagen_para_llm(imagen_bytes)).decode("ascii")
    except Exception:
        return _no_concluyente(tipo)

    mensajes = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                },
                {
                    "type": "text",
                    "text": (
                        f"Tipo indicado por el usuario: {tipo}. "
                        f"Resultado del modelo YOLO (puede ser vacío): {yolo_resumen}"
                    ),
                },
            ],
        }
    ]

    try:
        respuesta = _llamar(mensajes)
        datos = _extraer_json(respuesta)
        if datos is None:
            mensajes = mensajes + [
                {"role": "assistant", "content": respuesta},
                {
                    "role": "user",
                    "content": "Responde SOLO con el JSON válido, sin texto adicional.",
                },
            ]
            respuesta = _llamar(mensajes)
            datos = _extraer_json(respuesta)
    except Exception:
        return _no_concluyente(tipo)

    if datos is None:
        return _no_concluyente(tipo)
    return _validar(datos, tipo)


def generar_aviso_012(aviso: dict) -> str:
    """Texto de §7.2 (máx. 80 palabras) listo para copiar."""
    raise NotImplementedError
