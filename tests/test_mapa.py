"""Pruebas del mapa de avisos (#9): seed, colores, duplicados y arranque de la página."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from ui.mapa import COLORES, construir_mapa, leer_seed, normalizar

RAIZ = Path(__file__).resolve().parents[1]


def test_seed_cargado():
    avisos = leer_seed()
    assert len(avisos) == 30
    assert {aviso["especie"] for aviso in avisos} == {"velutina", "crabro"}


def test_duplicado_apunta_a_un_aviso_del_seed():
    avisos = leer_seed()
    ids = {aviso["id"] for aviso in avisos}
    duplicados = [aviso for aviso in avisos if aviso["duplicado_de"]]
    assert duplicados
    assert all(aviso["duplicado_de"] in ids for aviso in duplicados)


def test_mapa_pinta_un_marcador_por_aviso():
    avisos = leer_seed()
    mapa = construir_mapa(avisos).get_root().render()
    assert mapa.count("L.circleMarker") == len(avisos)


def test_colores_de_la_spec():
    assert COLORES == {
        "velutina": "#C94B4B",
        "crabro": "#357A55",
        "otra": "#6B7280",
        "no_concluyente": "#E6A23C",
    }


def test_normalizar_tolera_campos_vacios():
    aviso = normalizar(
        {"id": "", "lat": "", "lon": "x", "confianza": "", "duplicado_de": ""}
    )
    assert aviso["id"] is None
    assert aviso["lat"] is None
    assert aviso["lon"] is None
    assert aviso["confianza"] == 0.0
    assert aviso["duplicado_de"] is None


def test_pagina_del_mapa_arranca_y_marca_datos_de_ejemplo():
    app = AppTest.from_file(RAIZ / "pages" / "1_Mapa.py").run(timeout=60)
    assert not app.exception
    assert any("Datos de ejemplo" in aviso.value for aviso in app.warning)
