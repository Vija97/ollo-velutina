"""Llamadas al LLM: análisis de imagen y texto del aviso al 012 (spec §7). Responsable: IA."""

import base64
import io
import json
import os
import re
import urllib.request

from PIL import Image, ImageOps

# DeepSeek V4.1 Flash vía OpenRouter (formato OpenAI), spec §7.1.
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODELO = os.environ.get("OPENCODE_MODEL", "deepseek/deepseek-v4.1-flash-1017")
# Cloudflare bloquea el User-Agent por defecto de urllib (error 1010).
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)

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
CLAVE = "OPENCODE_API_KEY"

LADO_MAX = 1280  # px de lado máximo antes de enviar la imagen
MAX_TOKENS = 2000  # el modelo razona antes de responder; 600 se queda corto
RAZONAMIENTO = {"effort": "low"}

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
    """Modelo a usar: `OPENCODE_MODEL` si está definido; si no, DeepSeek V4.1 Flash."""
    return _secreto("OPENCODE_MODEL") or MODELO


def _clave() -> str:
    """Clave de la API de OpenCode. Falla pronto si no está configurada."""
    clave = _secreto(CLAVE) or _secreto("OPENROUTER_API_KEY")
    if not clave:
        raise ValueError(f"Falta {CLAVE} (o OPENROUTER_API_KEY) en .streamlit/secrets.toml o el entorno.")
    return clave


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
    """POST a la API de OpenCode (formato OpenAI) y devuelve el texto de respuesta."""
    cuerpo = {
        "model": modelo(),
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "system", "content": SYSTEM_ANALISIS}, *mensajes],
        "reasoning": RAZONAMIENTO,
    }
    peticion = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_clave()}",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(peticion, timeout=60) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8"))
    return str(datos["choices"][0]["message"].get("content") or "")


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
                    "type": "text",
                    "text": (
                        f"Tipo indicado por el usuario: {tipo}. "
                        f"Resultado del modelo YOLO (puede ser vacío): {yolo_resumen}"
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
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
