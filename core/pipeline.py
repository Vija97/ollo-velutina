"""Orquesta el flujo completo foto → resultado → aviso guardado (spec §5). Responsable: Backend."""


def procesar(imagen_bytes: bytes, tipo: str, lat: float, lon: float) -> dict:
    """Clasifica, busca duplicados y guarda el aviso.

    Devuelve el aviso guardado (campos de §4) más `duplicado_distancia_m` si es duplicado.
    `tipo` es "insecto", "nido" o "no_se".
    """
    raise NotImplementedError
