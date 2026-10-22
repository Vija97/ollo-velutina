"""Llamadas a la API de OpenCode: análisis de imagen y texto del aviso al 012 (spec §7). Responsable: IA."""

import os

# DeepSeek V4.1 Flash vía la API de OpenCode (compatible con OpenAI); spec §7.1.
ENDPOINT = "https://opencode.ai/inference/openai/v1/chat/completions"
MODELO = os.environ.get("OPENCODE_MODEL", "deepseek-v4.1-flash")


def analizar_imagen(imagen_bytes: bytes, tipo: str, yolo_resumen: str = "") -> dict:
    """JSON de §7.1: tipo, especie, confianza, rasgos_observados, explicacion, consejo_foto.

    Si la respuesta no es JSON válido tras un reintento, devuelve especie "no_concluyente".
    """
    raise NotImplementedError


def generar_aviso_012(aviso: dict) -> str:
    """Texto de §7.2 (máx. 80 palabras) listo para copiar."""
    raise NotImplementedError
