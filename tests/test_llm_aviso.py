"""Pruebas sin red de generar_aviso_012 (#10)."""

import json

import core.llm as llm

AVISO = {
    "id": 7,
    "created_at": "2026-10-21T17:05:00",
    "lat": 42.8782,
    "lon": -8.5448,
    "tipo": "nido",
    "especie": "velutina",
    "confianza": 0.72,
    "fuente_clasificacion": "yolo",
    "explicacion": "Nido en un árbol.",
    "foto_path": "data/fotos/07.jpg",
    "duplicado_de": None,
    "estado": "nuevo",
    "lugar": "ETSE, Santiago de Compostela",
}

LAT = "42.87820"
LON = "-8.54480"
ENLACE = (
    f"https://www.openstreetmap.org/?mlat={LAT}&mlon={LON}#map=18/{LAT}/{LON}"
)


def _texto_corto() -> str:
    return (
        f"Aviso al 012: posible nido de avispa velutina, confianza 72 %. "
        f"Coordenadas {LAT}, {LON}. {ENLACE} "
        "ETSE, Santiago de Compostela. 21/10/2026 17:05. "
        "Identificación automática y orientativa."
    )


def test_prompt_es_el_de_la_spec():
    assert llm.PROMPT_AVISO.startswith("Redacta un aviso breve y claro (máx. 80 palabras)")
    assert llm.PROMPT_AVISO.endswith("Datos: {json_del_aviso}")


def test_datos_json_y_enlace_osm(monkeypatch):
    capturado = {}

    def falso(mensajes, sistema=llm.SYSTEM_ANALISIS):
        capturado["sistema"] = sistema
        return _texto_corto()

    monkeypatch.setattr(llm, "_llamar", falso)
    texto = llm.generar_aviso_012(AVISO)

    assert ENLACE in texto
    assert LAT in texto and LON in texto

    datos = json.loads(capturado["sistema"].split("Datos: ", 1)[1])
    assert set(datos) == {
        "tipo",
        "especie",
        "confianza",
        "lat",
        "lon",
        "enlace",
        "fecha",
        "lugar",
    }
    assert datos["tipo"] == "nido"
    assert datos["especie"] == "velutina"
    assert datos["confianza"] == 72
    assert datos["lat"] == LAT
    assert datos["lon"] == LON
    assert datos["enlace"] == ENLACE
    assert datos["fecha"] == "21/10/2026 17:05"
    assert datos["lugar"] == "ETSE, Santiago de Compostela"
    assert "foto_path" not in datos and "id" not in datos


def test_plantilla_si_falla_la_api(monkeypatch):
    def falla(mensajes, sistema=llm.SYSTEM_ANALISIS):
        raise OSError("sin red")

    monkeypatch.setattr(llm, "_llamar", falla)
    texto = llm.generar_aviso_012(AVISO)

    assert "Aviso al 012" in texto
    assert "tipo: nido" in texto
    assert "velutina" in texto and "72 %" in texto
    assert LAT in texto and LON in texto and ENLACE in texto
    assert "ETSE, Santiago de Compostela" in texto
    assert "21/10/2026 17:05" in texto
    assert "Identificación automática y orientativa" in texto


def test_anade_ubicacion_si_el_llm_la_omite(monkeypatch):
    monkeypatch.setattr(
        llm,
        "_llamar",
        lambda mensajes, sistema=llm.SYSTEM_ANALISIS: (
            "Aviso al 012: posible nido de avispa velutina. "
            "Identificación automática y orientativa."
        ),
    )
    texto = llm.generar_aviso_012(AVISO)

    assert texto.endswith(f"Ubicación: {LAT}, {LON} – {ENLACE}")


def test_reintenta_una_vez_si_pasa_de_80_palabras(monkeypatch):
    larga = f"{' '.join(['palabra'] * 81)} {LAT}, {LON} {ENLACE}."
    respuestas = iter([larga, _texto_corto()])
    llamadas = []

    def falso(mensajes, sistema=llm.SYSTEM_ANALISIS):
        llamadas.append(mensajes)
        return next(respuestas)

    monkeypatch.setattr(llm, "_llamar", falso)
    texto = llm.generar_aviso_012(AVISO)

    assert len(llamadas) == 2
    assert "Acórtalo a un máximo de 80 palabras" in llamadas[1][-1]["content"]
    assert texto == _texto_corto()
    assert llm._contar_palabras(texto, ENLACE) <= 80


def test_plantilla_si_la_respuesta_esta_cortada(monkeypatch):
    cortada = llm._TextoLLM("Aviso al 012: posible nido de avispa, coordenadas 42.87820")
    cortada.finish_reason = "length"
    monkeypatch.setattr(
        llm,
        "_llamar",
        lambda mensajes, sistema=llm.SYSTEM_ANALISIS: cortada,
    )
    texto = llm.generar_aviso_012(AVISO)

    assert "Identificación automática y orientativa" in texto
    assert ENLACE in texto and LAT in texto and LON in texto


def test_plantilla_si_sigue_pasando_de_80_palabras(monkeypatch):
    larga = f"{' '.join(['palabra'] * 81)} {LAT}, {LON} {ENLACE}."
    monkeypatch.setattr(
        llm,
        "_llamar",
        lambda mensajes, sistema=llm.SYSTEM_ANALISIS: larga,
    )
    texto = llm.generar_aviso_012(AVISO)

    assert "Identificación automática y orientativa" in texto
    assert len(texto.split()) < 81


def test_limpia_vallas_comillas_y_encabezado(monkeypatch):
    sucio = f'```\nAquí tienes el aviso: "{_texto_corto()}"\n```'
    monkeypatch.setattr(
        llm,
        "_llamar",
        lambda mensajes, sistema=llm.SYSTEM_ANALISIS: sucio,
    )
    texto = llm.generar_aviso_012(AVISO)

    assert "```" not in texto
    assert "Aquí tienes el aviso" not in texto
    assert not texto.startswith('"') and not texto.endswith('"')
    assert texto.startswith("Aviso al 012")


def test_el_enlace_no_cuenta_como_palabras():
    assert llm._contar_palabras(f"dos palabras {ENLACE}", ENLACE) == 2
