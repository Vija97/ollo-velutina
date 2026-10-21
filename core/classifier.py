"""Carga YOLO (models/best.pt) y clasifica insectos (spec §6). Responsable: IA."""

UMBRAL_CONFIANZA = 0.70


def clasificar_yolo(imagen_bytes: bytes) -> dict | None:
    """{"especie": "velutina"|"crabro", "confianza": float} de la mejor detección, o None.

    Devuelve None si no hay detección o no existe models/best.pt (plan B: solo LLM).
    """
    raise NotImplementedError
