"""Llamadas al LLM: análisis de imagen y texto del aviso al 012 (spec §7). Responsable: IA."""

import base64
import io
import json
import os
import re
import urllib.request
from datetime import datetime

from PIL import Image, ImageOps

# DeepSeek V4.1 Flash vía la API de OpenCode (formato compatible con OpenAI), spec §7.1.
ENDPOINT = "https://opencode.ai/inference/openai/v1/chat/completions"
MODELO = os.environ.get("OPENCODE_MODEL", "deepseek-v4.1-flash")

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

# §7.2, literal. Los datos van en el hueco {json_del_aviso}.
PROMPT_AVISO = """Redacta un aviso breve y claro (máx. 80 palabras) para el servicio 012 de la Xunta de Galicia sobre un posible nido o avistamiento de avispa velutina. Incluye: tipo (insecto/nido), especie probable y confianza, coordenadas (lat, lon) con enlace a OpenStreetMap, referencia de lugar si se conoce, fecha y hora, y que la identificación es automática y orientativa. Tono neutro, en castellano.
Datos: {json_del_aviso}"""

# Valores cerrados de AGENTS.md.
TIPOS = ("insecto", "nido")
ESPECIES = ("velutina", "crabro", "otra", "no_concluyente")

MAX_PALABRAS_AVISO = 80
FECHA_FALLO = "sin fecha"


class _TextoLLM(str):
    """Texto del LLM con el `finish_reason` de la respuesta (p. ej. ``length``)."""

    finish_reason: str | None = None

# Configuración del proveedor. Se lee de st.secrets si estamos dentro de
# Streamlit y, si no hay valor, de variables de entorno. Así el módulo funciona
# también desde pytest o un script suelto.
CLAVE = "OPENCODE_API_KEY"

LADO_MAX = 1280  # px de lado máximo antes de enviar la imagen
MAX_TOKENS = 600

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
    clave = _secreto(CLAVE)
    if not clave:
        raise ValueError(f"Falta {CLAVE} en .streamlit/secrets.toml o el entorno.")
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


def _llamar(mensajes: list, sistema: str = SYSTEM_ANALISIS) -> str:
    """POST a la API de OpenCode (formato OpenAI) y devuelve el texto de respuesta."""
    cuerpo = {
        "model": modelo(),
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "system", "content": sistema}, *mensajes],
    }
    peticion = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_clave()}",
        },
        method="POST",
    )
    with urllib.request.urlopen(peticion, timeout=60) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8"))
    eleccion = datos["choices"][0]
    texto = _TextoLLM(eleccion["message"].get("content") or "")
    texto.finish_reason = eleccion.get("finish_reason")
    return texto


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


def _formatear_fecha(valor) -> str:
    """Fecha del aviso como dd/mm/aaaa HH:MM; si no se entiende, ``FECHA_FALLO``."""
    if isinstance(valor, datetime):
        fecha = valor
    elif valor:
        try:
            fecha = datetime.fromisoformat(str(valor).strip().replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return FECHA_FALLO
    else:
        fecha = datetime.now()
    if fecha.tzinfo is not None:
        fecha = fecha.astimezone()
    return fecha.strftime("%d/%m/%Y %H:%M")


def _confianza_pct(valor) -> int:
    """Confianza en porcentaje entero, aceptando 0-1 (contrato) o 0-100."""
    try:
        confianza = float(valor)
    except (TypeError, ValueError):
        confianza = 0.0
    if 0.0 <= confianza <= 1.0:
        confianza *= 100.0
    return int(round(max(0.0, min(100.0, confianza))))


def _datos_aviso(aviso: dict) -> tuple[dict, str]:
    """Solo los datos de §7.2; el enlace y las coordenadas los fija el código."""
    lat = f"{float(aviso['lat']):.5f}"
    lon = f"{float(aviso['lon']):.5f}"
    enlace = (
        f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}"
        f"#map=18/{lat}/{lon}"
    )
    datos = {
        "tipo": _tipo_seguro(aviso.get("tipo")),
        "especie": str(aviso.get("especie") or "no_concluyente").strip().lower(),
        "confianza": _confianza_pct(aviso.get("confianza")),
        "lat": lat,
        "lon": lon,
        "enlace": enlace,
        "fecha": _formatear_fecha(aviso.get("created_at") or aviso.get("fecha")),
    }
    for clave in ("lugar", "referencia_lugar", "referencia", "direccion"):
        valor = aviso.get(clave)
        if valor and str(valor).strip():
            datos["lugar"] = str(valor).strip()
            break
    return datos, enlace


def _contar_palabras(texto: str, enlace: str) -> int:
    """Palabras del aviso sin contar el enlace de OpenStreetMap."""
    return len((texto or "").replace(enlace, " ").split())


def _limpiar_aviso(texto: str) -> str:
    """Quita vallas, comillas y encabezados tipo «Aquí tienes el aviso:»."""
    limpio = (texto or "").strip()
    limpio = re.sub(r"^```[A-Za-z0-9_-]*\s*", "", limpio)
    limpio = re.sub(r"\s*```$", "", limpio).strip()

    lineas = limpio.splitlines()
    while lineas:
        primera = lineas[0].strip()
        if not primera:
            lineas.pop(0)
        elif re.match(
            r"^(aqu[ií] tienes|este es|el texto|el aviso|texto|aviso)\b[^.]*:\s*$",
            primera,
            re.I,
        ):
            lineas.pop(0)
        else:
            break
    limpio = "\n".join(lineas).strip()
    limpio = re.sub(
        r"^(aqu[ií] tienes el aviso|este es el aviso|el aviso|aviso)\s*:\s*",
        "",
        limpio,
        flags=re.I,
    ).strip()

    while len(limpio) >= 2 and limpio[0] in "\"'“”‘’" and limpio[-1] in "\"'“”‘’":
        limpio = limpio[1:-1].strip()
    return limpio


def _texto_fallback(datos: dict) -> str:
    """Plantilla sin LLM: mismos datos y aviso de identificación orientativa."""
    que = "nido" if datos["tipo"] == "nido" else "avistamiento"
    partes = [
        f"Aviso al 012 (tipo: {datos['tipo']}): posible {que} de avispa.",
        (
            f"Especie probable: {datos['especie']}, "
            f"confianza del {datos['confianza']} %."
        ),
        (
            f"Ubicación: {datos['lat']}, {datos['lon']} – "
            f"{datos['enlace']}."
        ),
    ]
    if datos.get("lugar"):
        partes.append(f"Lugar: {datos['lugar']}.")
    partes.extend(
        [
            f"Fecha: {datos['fecha']}.",
            "Identificación automática y orientativa.",
        ]
    )
    return " ".join(partes)


def _respuesta_aviso(mensajes: list, prompt: str) -> tuple[str, bool]:
    """Devuelve el texto limpio y si la respuesta se cortó por `max_tokens`."""
    respuesta = _llamar(mensajes, sistema=prompt)
    truncada = getattr(respuesta, "finish_reason", None) == "length"
    return _limpiar_aviso(str(respuesta)), truncada


def generar_aviso_012(aviso: dict) -> str:
    """Texto de §7.2 (máx. 80 palabras) listo para copiar."""
    datos, enlace = _datos_aviso(aviso)
    prompt = PROMPT_AVISO.replace(
        "{json_del_aviso}", json.dumps(datos, ensure_ascii=False)
    )
    mensajes = [
        {"role": "user", "content": "Redacta el aviso siguiendo las instrucciones."}
    ]

    try:
        texto, truncada = _respuesta_aviso(mensajes, prompt)
    except Exception:
        return _texto_fallback(datos)
    if truncada or not texto:
        return _texto_fallback(datos)

    palabras = _contar_palabras(texto, enlace)
    if palabras > MAX_PALABRAS_AVISO:
        mensajes = mensajes + [
            {"role": "assistant", "content": texto},
            {
                "role": "user",
                "content": (
                    f"El texto tiene {palabras} palabras sin contar el enlace. "
                    f"Acórtalo a un máximo de {MAX_PALABRAS_AVISO} palabras, "
                    "conservando el enlace y las coordenadas."
                ),
            },
        ]
        try:
            texto, truncada = _respuesta_aviso(mensajes, prompt)
        except Exception:
            return _texto_fallback(datos)
        if (
            truncada
            or not texto
            or _contar_palabras(texto, enlace) > MAX_PALABRAS_AVISO
        ):
            return _texto_fallback(datos)

    if enlace not in texto or datos["lat"] not in texto or datos["lon"] not in texto:
        texto = (
            f"{texto.rstrip()}\n"
            f"Ubicación: {datos['lat']}, {datos['lon']} – {enlace}"
        )
        if _contar_palabras(texto, enlace) > MAX_PALABRAS_AVISO:
            return _texto_fallback(datos)
    return texto
