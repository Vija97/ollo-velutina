"""Pruebas de la página «Sobre el modelo» (#14)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]


def test_pagina_muestra_metricas_y_licencia():
    app = AppTest.from_file(RAIZ / "pages" / "2_Sobre_el_modelo.py").run(timeout=30)

    assert not app.exception
    etiquetas = [metrica.label for metrica in app.metric]
    assert "Precisión" in etiquetas
    assert "mAP50" in etiquetas
    assert "mAP50-95" in etiquetas

    texto = "\n".join(bloque.value for bloque in app.markdown)
    assert "CC BY 4.0" in texto
    assert "Roboflow" in texto

    assert app.get("image")
