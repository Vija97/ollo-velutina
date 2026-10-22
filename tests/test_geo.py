"""Tests de core/geo.py (Issue #4)."""

import io
from datetime import datetime, timedelta

import pytest
from PIL import Image

from core import geo

LAT = 42.8782
LON = -8.5448
# 1 grado de latitud ≈ 111.194,9 m → 20 m y 60 m en grados
M20 = 20 / 111_194.9
M60 = 60 / 111_194.9


def _aviso(dlat=0.0, especie="velutina", tipo="insecto", dias=1, duplicado_de=None):
    fecha = (datetime.now() - timedelta(days=dias)).isoformat(timespec="seconds")
    return {
        "lat": LAT + dlat,
        "lon": LON,
        "tipo": tipo,
        "especie": especie,
        "created_at": fecha,
        "duplicado_de": duplicado_de,
    }


def test_haversine_punto_conocido():
    # 0,001° de latitud en Santiago ≈ 111,19 m
    assert geo.haversine_m(LAT, LON, LAT + 0.001, LON) == pytest.approx(111.19, abs=1.0)
    # 1° de longitud en el ecuador ≈ 111.194,9 m
    assert geo.haversine_m(0, 0, 0, 1) == pytest.approx(111_194.9, abs=1.0)
    assert geo.haversine_m(LAT, LON, LAT, LON) == pytest.approx(0, abs=1e-9)


def test_velutina_y_no_concluyente_a_20m_es_duplicado():
    aviso = _aviso(dlat=M20, especie="velutina")
    resultado = geo.buscar_duplicado(LAT, LON, "insecto", "no_concluyente", [aviso])
    assert resultado is not None
    original, distancia = resultado
    assert original is aviso
    assert distancia == pytest.approx(20, abs=1.0)


def test_velutina_y_crabro_a_20m_no_es_duplicado():
    aviso = _aviso(dlat=M20, especie="velutina")
    assert geo.buscar_duplicado(LAT, LON, "insecto", "crabro", [aviso]) is None


def test_mismo_tipo_obligatorio():
    aviso = _aviso(dlat=M20, especie="velutina", tipo="nido")
    assert geo.buscar_duplicado(LAT, LON, "insecto", "velutina", [aviso]) is None


def test_a_60m_no_es_duplicado():
    aviso = _aviso(dlat=M60)
    assert geo.buscar_duplicado(LAT, LON, "insecto", "velutina", [aviso]) is None


def test_de_hace_31_dias_no_es_duplicado():
    aviso = _aviso(dlat=M20, dias=31)
    assert geo.buscar_duplicado(LAT, LON, "insecto", "velutina", [aviso]) is None


def test_ignora_los_que_ya_son_duplicados():
    aviso = _aviso(dlat=M20, duplicado_de=7)
    assert geo.buscar_duplicado(LAT, LON, "insecto", "velutina", [aviso]) is None


def test_devuelve_el_mas_cercano():
    lejos = _aviso(dlat=40 / 111_194.9, especie="crabro")
    cerca = _aviso(dlat=M20, especie="crabro")
    resultado = geo.buscar_duplicado(LAT, LON, "insecto", "crabro", [lejos, cerca])
    assert resultado is not None
    original, distancia = resultado
    assert original is cerca
    assert distancia == pytest.approx(20, abs=1.0)


def test_get_exif_gps_sin_exif():
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "gray").save(buffer, "JPEG")
    assert geo.get_exif_gps(buffer.getvalue()) is None


def test_get_exif_gps_con_exif():
    imagen = Image.new("RGB", (20, 20), "gray")
    exif = imagen.getexif()
    gps = exif.get_ifd(0x8825)
    gps[1], gps[2] = "N", (42.0, 52.0, 41.5)
    gps[3], gps[4] = "W", (8.0, 32.0, 41.3)
    buffer = io.BytesIO()
    imagen.save(buffer, "JPEG", exif=exif)

    lat, lon = geo.get_exif_gps(buffer.getvalue())
    assert lat == pytest.approx(42.878194, abs=1e-5)   # N
    assert lon == pytest.approx(-8.544806, abs=1e-5)   # W → negativo


def test_get_exif_gps_basura_no_rompe():
    assert geo.get_exif_gps(b"esto no es una imagen") is None
