"""Pruebas de la UI de #8 y de la conexión al pipeline de #12."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
import pytest
from streamlit.testing.v1 import AppTest

from core import geo
from ui.demo import (
    ESCENARIOS,
    cargar_registros,
    crear_resultado_demo,
    fotos_demo,
    leer_fotografia,
)

RAIZ = Path(__file__).resolve().parents[1]
UBICACION = (42.8782, -8.5448)


def _app():
    app = AppTest.from_file(RAIZ / "app.py")
    app.session_state["ubicacion"] = UBICACION
    return app


def _resultado(**cambios):
    aviso = {
        "id": 99,
        "created_at": "2026-10-22T16:00:00",
        "lat": UBICACION[0],
        "lon": UBICACION[1],
        "tipo": "nido",
        "especie": "velutina",
        "confianza": 0.9,
        "fuente_clasificacion": "yolo+llm",
        "explicacion": "Nido compatible con velutina.",
        "foto_path": "",
        "duplicado_de": None,
        "estado": "nuevo",
        "rasgos_observados": ["Nido redondeado", "Avispas en la entrada"],
        "consejo_foto": "",
        "duplicado_distancia_m": None,
        "duplicado_fecha": None,
    }
    aviso.update(cambios)
    return aviso


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


def test_fotos_de_demo_disponibles():
    nombres = {foto.name for foto in fotos_demo()}
    assert {"velutina_1.jpg", "velutina_2.jpg", "crabro_1.jpg", "no_concluyente_1.jpg"} <= nombres
    assert len(cargar_registros()) == 4


def test_inicio_y_validacion_sin_ubicacion():
    app = AppTest.from_file(RAIZ / "app.py").run(timeout=30)
    assert not app.exception
    assert app.button[-1].disabled
    assert any("Demostración" in aviso.value for aviso in app.info)
    assert any("112" in texto.value for texto in app.markdown)


def test_analizar_llama_al_pipeline_y_muestra_el_resultado():
    with patch("core.pipeline.procesar", return_value=_resultado()) as procesar:
        app = _app().run(timeout=30)
        app.button[-1].click().run()

    assert not app.exception
    assert procesar.called
    assert app.session_state["resultado"]["id"] == 99
    assert app.get("progress")[0].value == 90
    texto = "\n".join(x.value for x in app.markdown)
    assert "Posible nido de velutina" in texto
    assert "Rasgos observados" in texto
    assert "No te acerques al nido" in texto and "012" in texto and "112" in texto
    assert any("Aviso #99" in c.value for c in app.caption)


def test_la_foto_original_llega_al_pipeline_con_su_gps():
    original = BytesIO()
    imagen = Image.new("RGB", (80, 60), "gray")
    exif = imagen.getexif()
    gps = exif.get_ifd(0x8825)
    gps[1], gps[2] = "N", (42.0, 52.0, 41.5)
    gps[3], gps[4] = "W", (8.0, 32.0, 41.3)
    imagen.save(original, format="JPEG", exif=exif)
    datos = original.getvalue()

    archivo = SimpleNamespace(getvalue=lambda: datos)
    with patch("streamlit.file_uploader", return_value=archivo), patch(
        "core.pipeline.procesar", return_value=_resultado()
    ) as procesar:
        app = AppTest.from_file(RAIZ / "app.py").run(timeout=30)
        app.button[-1].click().run()

    assert not app.exception
    enviado = procesar.call_args.args[0]
    assert enviado == datos
    assert geo.get_exif_gps(enviado) is not None


def test_duplicado_y_consejo_se_muestran():
    aviso = _resultado(
        especie="velutina",
        duplicado_de=7,
        estado="duplicado",
        duplicado_distancia_m=18.0,
        duplicado_fecha="2026-10-21T09:12:00",
    )
    with patch("core.pipeline.procesar", return_value=aviso):
        app = _app().run(timeout=30)
        app.button[-1].click().run()

    avisos = "\n".join(w.value for w in app.warning)
    assert "18 m" in avisos and "2026-10-21" in avisos


def test_no_concluyente_muestra_consejo():
    aviso = _resultado(
        especie="no_concluyente",
        confianza=0.0,
        consejo_foto="Prueba con otra fotografía más nítida.",
    )
    with patch("core.pipeline.procesar", return_value=aviso):
        app = _app().run(timeout=30)
        app.button[-1].click().run()

    avisos = "\n".join(w.value for w in app.warning)
    assert "otra fotografía más nítida" in avisos
    assert app.get("progress")[0].value == 0


def test_error_del_pipeline_se_muestra_sin_resultado():
    with patch("core.pipeline.procesar", side_effect=RuntimeError("sin clave")):
        app = _app().run(timeout=30)
        app.button[-1].click().run()

    assert not app.exception
    assert any("sin clave" in error.value for error in app.error)
    assert "resultado" not in app.session_state


def test_cambiar_el_tipo_retira_el_resultado():
    with patch("core.pipeline.procesar", return_value=_resultado()):
        app = _app().run(timeout=30)
        app.button[-1].click().run()
        assert "resultado" in app.session_state
        app.radio(key="tipo").set_value("Nido").run()
        assert "resultado" not in app.session_state


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


def test_boton_012_solo_para_velutina_no_duplicada():
    casos = [
        (_resultado(), True),
        (_resultado(especie="crabro"), False),
        (
            _resultado(
                duplicado_de=7,
                estado="duplicado",
                duplicado_distancia_m=12.0,
                duplicado_fecha="2026-10-21T09:12:00",
            ),
            False,
        ),
        (_resultado(especie="no_concluyente", consejo_foto="Otra foto"), False),
    ]
    for aviso, esperado in casos:
        with patch("core.pipeline.procesar", return_value=aviso):
            app = _app().run(timeout=30)
            app.button[-1].click().run()
        etiquetas = [boton.label for boton in app.button]
        assert ("Generar aviso para el 012" in etiquetas) is esperado, aviso["especie"]


def test_boton_012_genera_y_muestra_el_texto():
    with patch("core.pipeline.procesar", return_value=_resultado()), patch(
        "core.llm.generar_aviso_012", return_value="Aviso al 012 de prueba"
    ) as generar:
        app = _app().run(timeout=30)
        app.button[-1].click().run()
        [boton for boton in app.button if boton.label == "Generar aviso para el 012"][0].click().run()

    assert generar.called
    assert "Aviso al 012 de prueba" in "\n".join(codigo.value for codigo in app.code)
