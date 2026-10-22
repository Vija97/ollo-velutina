"""GPS desde EXIF, distancia haversine y detección de duplicados (spec §5.2, §8). Responsable: Backend."""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt

from PIL import Image

ETSE = (42.8782, -8.5448)

RADIO_TIERRA_M = 6_371_000
RADIO_DUPLICADO_M = 50.0
DIAS_DUPLICADO = 30
_GPS_IFD = 0x8825  # ExifTags.IFD.GPSInfo


def _racional(valor) -> float:
    """IFDRational o tupla (grados, minutos, segundos) → grados decimales."""
    if isinstance(valor, (tuple, list)):
        grados, minutos, segundos = (float(parte) for parte in valor)
        return grados + minutos / 60 + segundos / 3600
    return float(valor)


def get_exif_gps(imagen_bytes: bytes) -> tuple[float, float] | None:
    """(lat, lon) de los metadatos EXIF, o None si la foto no tiene GPS."""
    try:
        with Image.open(io.BytesIO(imagen_bytes)) as imagen:
            gps = imagen.getexif().get_ifd(_GPS_IFD) or {}
    except Exception:
        return None

    if 2 not in gps or 4 not in gps:
        return None

    try:
        lat = _racional(gps[2])
        lon = _racional(gps[4])
    except (TypeError, ValueError, ZeroDivisionError):
        return None

    if str(gps.get(1, "N")).upper() == "S":
        lat = -lat
    if str(gps.get(3, "E")).upper() == "W":
        lon = -lon

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return (lat, lon)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en metros entre dos puntos."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * RADIO_TIERRA_M * asin(sqrt(a))


def _compatible(especie: str, otra: str) -> bool:
    """Misma especie, o una de las dos es no_concluyente (spec §8)."""
    return especie == otra or "no_concluyente" in (especie, otra)


def _fecha(valor) -> datetime | None:
    if not valor:
        return None
    try:
        fecha = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None
    # Los avisos se guardan sin zona; comparamos en hora local sin tzinfo.
    return fecha.astimezone().replace(tzinfo=None) if fecha.tzinfo else fecha


def buscar_duplicado(lat: float, lon: float, tipo: str, especie: str, avisos: list[dict]) -> tuple[dict, float] | None:
    """Aviso original más cercano (mismo tipo, especie compatible, ≤ 50 m, últimos 30 días, no duplicado) y su distancia.

    Especie compatible: igual, o una de las dos es "no_concluyente" (spec §8).
    """
    limite = datetime.now() - timedelta(days=DIAS_DUPLICADO)
    mejor: tuple[dict, float] | None = None

    for aviso in avisos:
        if aviso.get("duplicado_de") not in (None, ""):
            continue
        if str(aviso.get("tipo") or "").strip() != str(tipo).strip():
            continue
        if not _compatible(str(especie).strip(), str(aviso.get("especie") or "").strip()):
            continue
        fecha = _fecha(aviso.get("created_at"))
        if fecha is None or fecha < limite:
            continue
        try:
            distancia = haversine_m(lat, lon, float(aviso["lat"]), float(aviso["lon"]))
        except (KeyError, TypeError, ValueError):
            continue
        if distancia > RADIO_DUPLICADO_M:
            continue
        if mejor is None or distancia < mejor[1]:
            mejor = (aviso, distancia)

    return mejor
