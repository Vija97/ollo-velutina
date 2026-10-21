"""GPS desde EXIF, distancia haversine y detección de duplicados (spec §5.2, §8). Responsable: Backend."""

ETSE = (42.8782, -8.5448)


def get_exif_gps(imagen_bytes: bytes) -> tuple[float, float] | None:
    """(lat, lon) de los metadatos EXIF, o None si la foto no tiene GPS."""
    raise NotImplementedError


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en metros entre dos puntos."""
    raise NotImplementedError


def buscar_duplicado(lat: float, lon: float, especie: str, avisos: list[dict]) -> tuple[dict, float] | None:
    """Aviso original más cercano (misma especie, ≤ 50 m, últimos 30 días, no duplicado) y su distancia."""
    raise NotImplementedError
