"""Orquesta el flujo completo foto → resultado → aviso guardado (spec §5). Responsable: Backend."""


def procesar(imagen_bytes: bytes, tipo: str, lat: float, lon: float) -> dict:
    """Clasifica, busca duplicados y guarda el aviso.

    Devuelve el aviso guardado (campos de §4) más estos campos, que no se guardan en la tabla:
    - `rasgos_observados`: list[str] (puede ir vacía)
    - `consejo_foto`: str, vacío salvo si es `no_concluyente`
    - `duplicado_distancia_m`: float | None
    - `duplicado_fecha`: str ISO | None, `created_at` del aviso original
    `tipo` es "insecto", "nido" o "no_se".
    """
    raise NotImplementedError
