"""Pruebas de la UI de #8: fotos reales clasificadas y seguridad."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
import pytest
from streamlit.testing.v1 import AppTest

from ui.demo import (
    ESCENARIOS,
    cargar_registros,
    crear_resultado_demo,
    leer_fotografia,
)

RAIZ = Path(__file__).resolve().parents[1]
UBICACION = (42.8782, -8.5448)


def _app():
    app = AppTest.from_file(RAIZ / "app.py")
    app.session_state["ubicacion"] = UBICACION
    return app


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


@pytest.mark.parametrize("contenido", [b"no es una foto", b""])
def test_rechaza_archivos_invalidos(contenido):
    with pytest.raises(ValueError):
        leer_fotografia(contenido)


def test_rechaza_archivo_demasiado_grande():
    with pytest.raises(ValueError, match="10 MB"):
        leer_fotografia(b"x" * (10 * 1024 * 1024 + 1))


def test_no_conserva_imagen_enorme():
    salida = BytesIO()
    Image.new("1", (6000, 5000)).save(salida, format="PNG")
    with pytest.raises(ValueError, match="25 megapíxeles"):
        leer_fotografia(salida.getvalue())


def test_inicio_y_validacion_sin_foto():
    app = AppTest.from_file(RAIZ / "app.py").run(timeout=30)
    assert not app.exception
    assert app.button[-1].disabled
    assert any("Modo demostración" in aviso.value for aviso in app.info)
    assert any("112" in texto.value for texto in app.markdown)


def test_manifiesto_tiene_las_fotos_de_la_demo():
    registros = cargar_registros()
    assert len(registros) == 4
    assert {registro["especie"] for registro in registros} == {
        "velutina",
        "crabro",
        "no_concluyente",
    }
    assert all(registro["foto_path"].is_file() for registro in registros)


@pytest.mark.parametrize("indice", range(len(cargar_registros())))
def test_resultado_sale_de_la_clasificacion_guardada(indice):
    registros = cargar_registros()
    esperado = registros[indice]
    app = _app()
    app.run(timeout=30)
    app.selectbox(key="foto_ejemplo").select_index(indice).run()
    app.button[-1].click().run()

    assert not app.exception
    resultado = app.session_state["resultado"]
    assert resultado["especie"] == esperado["especie"]
    assert resultado["confianza"] == pytest.approx(esperado["confianza"])
    assert resultado["fuente_clasificacion"] == esperado["fuente_clasificacion"]
    assert app.get("progress")[0].value == round(resultado["confianza"] * 100)

    texto = "\n".join(x.value for x in app.markdown)
    assert "Rasgos observados" in texto
    assert "No te acerques al nido" in texto and "012" in texto and "112" in texto

    avisos = "\n".join(x.value for x in app.warning)
    assert "clasificación guardada" in avisos
    if esperado["duplicado_de"] is not None:
        assert "18 m" in avisos and "2026-10-21" in avisos
    if esperado["especie"] == "no_concluyente":
        assert "otra fotografía más nítida" in avisos

    # Cambiar la entrada no puede dejar el resultado anterior en pantalla.
    app.radio(key="tipo").set_value("Nido").run()
    assert "resultado" not in app.session_state
    assert not app.get("progress")


def test_subir_una_foto_conocida_usa_su_clasificacion():
    registro = next(r for r in cargar_registros() if r["especie"] == "crabro")
    archivo = SimpleNamespace(getvalue=lambda: registro["foto_path"].read_bytes())
    with patch("streamlit.file_uploader", return_value=archivo):
        app = _app().run(timeout=30)
        assert not any(box.key == "foto_ejemplo" for box in app.selectbox)
        app.button[-1].click().run()
        assert not app.exception
        assert app.session_state["resultado"]["especie"] == "crabro"


def test_foto_no_clasificada_avisa_y_ofrece_ejemplos(foto):
    with patch(
        "streamlit.file_uploader",
        return_value=SimpleNamespace(getvalue=lambda: foto),
    ):
        app = _app().run(timeout=30)
        assert not app.exception
        assert any("no está entre las clasificadas" in aviso.value for aviso in app.info)
        assert any(box.key == "foto_ejemplo" for box in app.selectbox)


def test_foto_invalida_no_permite_analizar():
    with patch("streamlit.file_uploader", return_value=SimpleNamespace(getvalue=lambda: b"archivo roto")):
        app = AppTest.from_file(RAIZ / "app.py").run(timeout=30)
        assert not app.exception
        assert app.error and app.button[-1].disabled


def test_captura_camara(foto):
    with patch("streamlit.camera_input", return_value=SimpleNamespace(getvalue=lambda: foto)):
        app = _app().run(timeout=30)
        assert not app.exception
        assert not app.button[-1].disabled


def test_ejemplos_de_reserva_tienen_campos_del_contrato_pr1():
    for escenario in ESCENARIOS:
        resultado = crear_resultado_demo(escenario, "nido", 42.0, -8.0)
        assert resultado["tipo"] == "nido"
        assert {"rasgos_observados", "consejo_foto", "duplicado_distancia_m", "duplicado_fecha"} <= resultado.keys()
