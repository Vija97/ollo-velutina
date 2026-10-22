"""Pruebas de la UI de #8; no invocan IA, SQLite ni el pipeline."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
import pytest
from streamlit.testing.v1 import AppTest

from ui.demo import ESCENARIOS, crear_resultado_demo, leer_fotografia


@pytest.fixture
def foto():
    salida = BytesIO()
    Image.new("RGB", (320, 200), "#357A55").save(salida, format="PNG")
    return salida.getvalue()


def test_fotografia_normalizada_sin_metadatos(foto):
    with Image.open(BytesIO(leer_fotografia(foto))) as imagen:
        assert imagen.format == "JPEG"
        assert imagen.size == (320, 200)
        assert not imagen.getexif()


@pytest.mark.parametrize("contenido", [b"no es una foto", b"", b"x" * (10 * 1024 * 1024 + 1)])
def test_rechaza_archivos_invalidos(contenido):
    with pytest.raises(ValueError):
        leer_fotografia(contenido)


def test_no_conserva_imagen_enorme():
    salida = BytesIO()
    Image.new("1", (6000, 5000)).save(salida, format="PNG")
    with pytest.raises(ValueError, match="25 megapíxeles"):
        leer_fotografia(salida.getvalue())


def test_inicio_y_validacion_sin_foto():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run(timeout=30)
    assert not app.exception
    assert app.button[-1].disabled
    assert any("Modo demostración" in aviso.value for aviso in app.info)
    assert any("112" in texto.value for texto in app.markdown)


@pytest.mark.parametrize("escenario", ESCENARIOS)
def test_resultados_y_seguridad(foto, escenario):
    archivo = SimpleNamespace(getvalue=lambda: foto)
    with patch("streamlit.file_uploader", return_value=archivo):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
        app.session_state["ubicacion"] = (42.8782, -8.5448)
        app.run(timeout=30)
        app.selectbox(key="escenario").select(escenario).run()
        app.button[-1].click().run()
        assert not app.exception
        resultado = app.session_state["resultado"]
        assert resultado["especie"] in ("velutina", "crabro", "otra", "no_concluyente")
        assert app.get("progress")[0].value == round(resultado["confianza"] * 100)
        texto = "\n".join(x.value for x in app.markdown)
        assert "Rasgos del ejemplo" in texto
        assert "No te acerques al nido" in texto and "012" in texto and "112" in texto
        avisos = "\n".join(x.value for x in app.warning)
        assert "Resultado simulado" in avisos
        if escenario == "Posible duplicado":
            assert "20 m" in avisos and "2026-10-21" in avisos
        if escenario == "No concluyente":
            assert "otra fotografía más nítida" in avisos
        # Cambiar la entrada no puede dejar el resultado de la foto/caso anterior.
        app.radio(key="tipo").set_value("Nido").run()
        assert "resultado" not in app.session_state
        assert not app.get("progress")


def test_foto_invalida_no_permite_analizar():
    with patch("streamlit.file_uploader", return_value=SimpleNamespace(getvalue=lambda: b"archivo roto")):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run(timeout=30)
        assert not app.exception
        assert app.error and app.button[-1].disabled


def test_captura_camara(foto):
    with patch("streamlit.camera_input", return_value=SimpleNamespace(getvalue=lambda: foto)):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
        app.session_state["ubicacion"] = (42.8782, -8.5448)
        app.run(timeout=30)
        app.radio(key="origen").set_value("Usar cámara").run()
        assert not app.exception
        assert not app.button[-1].disabled


def test_ejemplos_tienen_campos_del_contrato_pr1():
    for escenario in ESCENARIOS:
        resultado = crear_resultado_demo(escenario, "nido", 42.0, -8.0)
        assert resultado["tipo"] == "nido"
        assert {"rasgos_observados", "consejo_foto", "duplicado_distancia_m", "duplicado_fecha"} <= resultado.keys()
