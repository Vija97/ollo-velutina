"""Carga YOLO (models/best.pt) y clasifica insectos (spec §6). Responsable: IA."""

from __future__ import annotations

import io
import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)

UMBRAL_CONFIANZA = 0.70
MODELO_PATH = Path("models/best.pt")

# El modelo se carga una sola vez por proceso.
_modelo = None
_modelo_comprobado = False


def _mapear_especie(nombre: str) -> str | None:
    """`Vespa_velutina`/`Vespa_crabro` (y variantes) → `velutina`/`crabro`."""
    clave = str(nombre).strip().lower()
    if "velutina" in clave:
        return "velutina"
    if "crabro" in clave:
        return "crabro"
    return None


def _cargar_modelo():
    """Carga `models/best.pt` una sola vez; None si no existe o no se puede cargar."""
    global _modelo, _modelo_comprobado

    if _modelo is not None or _modelo_comprobado:
        return _modelo

    _modelo_comprobado = True
    if not MODELO_PATH.is_file():
        return None

    try:
        from ultralytics import YOLO

        _modelo = YOLO(str(MODELO_PATH))
        LOGGER.info("YOLO cargado desde %s", MODELO_PATH)
    except Exception:  # modelo corrupto, ultralytics sin instalar... plan B: solo LLM
        LOGGER.warning("No se pudo cargar %s; se usará solo el LLM.", MODELO_PATH, exc_info=True)
        _modelo = None

    return _modelo


def clasificar_yolo(imagen_bytes: bytes) -> dict | None:
    """{"especie": "velutina"|"crabro", "confianza": float} de la mejor detección, o None.

    Devuelve None si no hay detección o no existe models/best.pt (plan B: solo LLM).
    """
    modelo = _cargar_modelo()
    if modelo is None:
        return None

    from PIL import Image

    imagen = Image.open(io.BytesIO(imagen_bytes)).convert("RGB")
    # device="cpu": la demo corre en CPU (spec §2); no depende de GPU.
    resultados = modelo.predict(source=imagen, imgsz=640, device="cpu", verbose=False)
    if not resultados:
        return None

    cajas = resultados[0].boxes
    if cajas is None or len(cajas) == 0:
        return None

    nombres = resultados[0].names
    mejor: dict | None = None
    for caja in cajas:
        especie = _mapear_especie(nombres[int(caja.cls)])
        if especie is None:
            continue
        confianza = float(caja.conf)
        if mejor is None or confianza > mejor["confianza"]:
            mejor = {"especie": especie, "confianza": confianza}

    return mejor
