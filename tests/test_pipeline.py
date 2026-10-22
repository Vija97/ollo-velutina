"""Tests de core/pipeline.py (Issue #7). Clasificador y LLM simulados; base temporal."""

import pytest

from core import db, pipeline

LAT = 42.8782
LON = -8.5448
M20 = 20 / 111_194.9


def _llm(especie="velutina", tipo="nido", confianza=0.8, consejo=""):
    return {
        "tipo": tipo,
        "especie": especie,
        "confianza": confianza,
        "rasgos_observados": ["banda naranja", "patas amarillas"],
        "explicacion": f"Parece {especie}.",
        "consejo_foto": consejo,
    }


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "DB_PATH", str(tmp_path / "avisos.db"))
    monkeypatch.setattr(db, "SEED_PATH", tmp_path / "sin-seed.csv")
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "avisos.db"))
    return tmp_path


def test_yolo_con_confianza_se_guarda(entorno, monkeypatch):
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "velutina", "confianza": 0.91})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("velutina", "insecto", 0.9))

    aviso = pipeline.procesar(b"foto", "insecto", LAT, LON)

    assert aviso["especie"] == "velutina"
    assert aviso["confianza"] == pytest.approx(0.91)
    assert aviso["fuente_clasificacion"] == "yolo+llm"
    assert aviso["estado"] == "nuevo"
    assert aviso["duplicado_de"] is None
    assert db.listar_avisos(pipeline.DB_PATH)[0]["id"] == aviso["id"]


def test_segundo_aviso_a_20m_es_duplicado(entorno, monkeypatch):
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "velutina", "confianza": 0.9})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("velutina", "insecto", 0.9))

    primero = pipeline.procesar(b"foto1", "insecto", LAT, LON)
    segundo = pipeline.procesar(b"foto2", "insecto", LAT + M20, LON)

    assert segundo["estado"] == "duplicado"
    assert segundo["duplicado_de"] == primero["id"]
    assert segundo["duplicado_distancia_m"] == pytest.approx(20, abs=1.0)
    assert segundo["duplicado_fecha"] == primero["created_at"]


def test_foto_borrosa_es_no_concluyente(entorno, monkeypatch):
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: None)
    monkeypatch.setattr(
        pipeline, "analizar_imagen",
        lambda *a, **k: _llm("no_concluyente", "nido", 0.0, consejo="Otra foto, por favor."),
    )

    aviso = pipeline.procesar(b"borrosa", "nido", LAT, LON)

    assert aviso["especie"] == "no_concluyente"
    assert aviso["consejo_foto"]
    assert aviso["fuente_clasificacion"] == "llm"


def test_si_discrepan_gana_velutina(entorno, monkeypatch):
    """YOLO velutina + LLM crabro: ante la duda, avisamos de velutina."""
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "velutina", "confianza": 0.95})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("crabro", "insecto", 0.9))

    assert pipeline.procesar(b"foto", "insecto", LAT, LON)["especie"] == "velutina"


def test_yolo_crabro_pero_llm_velutina_gana_velutina(entorno, monkeypatch):
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.93})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("velutina", "insecto", 0.8))

    aviso = pipeline.procesar(b"foto", "insecto", LAT, LON)
    assert aviso["especie"] == "velutina"
    assert aviso["confianza"] == pytest.approx(0.8)


def test_no_se_sesga_al_llm_con_el_crabro_de_yolo(entorno, monkeypatch):
    """Al LLM no se le dice que YOLO cree ver un crabro cuando hay duda."""
    visto = {}

    def llm_sin_sesgo(_img, _tipo, resumen=""):
        visto["resumen"] = resumen
        return _llm("velutina", "insecto", 0.8)

    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.9})
    monkeypatch.setattr(pipeline, "analizar_imagen", llm_sin_sesgo)

    pipeline.procesar(b"foto", "no_se", LAT, LON)
    assert visto["resumen"] == ""


def test_los_dos_crabro_dan_crabro(entorno, monkeypatch):
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.9})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("crabro", "insecto", 0.86))

    aviso = pipeline.procesar(b"foto", "insecto", LAT, LON)
    assert aviso["especie"] == "crabro"
    assert aviso["confianza"] == pytest.approx(0.86)


def test_en_insecto_manda_el_crabro_de_yolo(entorno, monkeypatch):
    """Un crabro de YOLO en un insecto es fiable aunque el LLM no lo confirme."""
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.9})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("otra", "insecto", 0.7))

    aviso = pipeline.procesar(b"foto", "insecto", LAT, LON)
    assert aviso["especie"] == "crabro"
    assert aviso["confianza"] == pytest.approx(0.9)


def test_en_nido_un_crabro_sin_confirmar_es_no_concluyente(entorno, monkeypatch):
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.9})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("otra", "nido", 0.7))

    assert pipeline.procesar(b"nido", "nido", LAT, LON)["especie"] == "no_concluyente"


def test_nido_sin_deteccion_decide_el_llm(entorno, monkeypatch):
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: None)
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("velutina", "nido", 0.85))

    aviso = pipeline.procesar(b"nido", "nido", LAT, LON)

    assert aviso["tipo"] == "nido"
    assert aviso["especie"] == "velutina"
    assert aviso["fuente_clasificacion"] == "llm"


def test_nido_con_yolo_confiable_manda_yolo(entorno, monkeypatch):
    """En nidos el detector de avispas es estable; no se llama al LLM."""
    def llm_prohibido(*_a, **_k):
        raise AssertionError("Con YOLO fiable no se llama al LLM en un nido")

    monkeypatch.setattr(
        pipeline, "clasificar_yolo", lambda _: {"especie": "velutina", "confianza": 0.87}
    )
    monkeypatch.setattr(pipeline, "analizar_imagen", llm_prohibido)

    aviso = pipeline.procesar(b"nido", "nido", LAT, LON)

    assert aviso["tipo"] == "nido"
    assert aviso["especie"] == "velutina"
    assert aviso["confianza"] == pytest.approx(0.87)
    assert aviso["fuente_clasificacion"] == "yolo"
    assert aviso["rasgos_observados"]


def test_nido_crabro_de_yolo_no_manda_solo(entorno, monkeypatch):
    """Un crabro de YOLO en un nido necesita confirmación: es el falso negativo típico."""
    monkeypatch.setattr(
        pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.81}
    )
    monkeypatch.setattr(
        pipeline, "analizar_imagen", lambda *_a, **_k: _llm("otra", "nido", 0.9)
    )

    aviso = pipeline.procesar(b"nido", "nido", LAT, LON)

    assert aviso["especie"] == "no_concluyente"
    assert aviso["tipo"] == "nido"


def test_nido_crabro_de_yolo_pero_llm_velutina(entorno, monkeypatch):
    monkeypatch.setattr(
        pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.83}
    )
    monkeypatch.setattr(
        pipeline, "analizar_imagen", lambda *_a, **_k: _llm("velutina", "nido", 0.8)
    )

    aviso = pipeline.procesar(b"nido", "nido", LAT, LON)

    assert aviso["especie"] == "velutina"
    assert aviso["tipo"] == "nido"


def test_nido_con_los_dos_crabro_se_confirma(entorno, monkeypatch):
    monkeypatch.setattr(
        pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.85}
    )
    monkeypatch.setattr(
        pipeline, "analizar_imagen", lambda *_a, **_k: _llm("crabro", "nido", 0.8)
    )

    aviso = pipeline.procesar(b"nido", "nido", LAT, LON)

    assert aviso["especie"] == "crabro"
    assert aviso["tipo"] == "nido"


def test_confianza_baja_decide_el_llm(entorno, monkeypatch):
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.4})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("velutina", "insecto", 0.82))

    aviso = pipeline.procesar(b"foto", "no_se", LAT, LON)

    assert aviso["especie"] == "velutina"
    assert aviso["fuente_clasificacion"] == "llm"


def test_en_insecto_sin_segunda_opinion_se_mantiene_el_crabro(entorno, monkeypatch):
    """En insectos YOLO es fiable: si el LLM falla, se queda el crabro de YOLO."""
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.93})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("no_concluyente", "insecto", 0.0))

    assert pipeline.procesar(b"foto", "insecto", LAT, LON)["especie"] == "crabro"


def test_en_nido_sin_segunda_opinion_no_se_afirma_crabro(entorno, monkeypatch):
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.93})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("no_concluyente", "nido", 0.0))

    aviso = pipeline.procesar(b"nido", "nido", LAT, LON)
    assert aviso["especie"] == "no_concluyente"
    assert aviso["consejo_foto"]


def test_sin_segunda_opinion_velutina_se_mantiene(entorno, monkeypatch):
    """Si YOLO avisa de velutina y el LLM falla, se mantiene el aviso: es el lado seguro."""
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "velutina", "confianza": 0.91})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("no_concluyente", "insecto", 0.0))

    aviso = pipeline.procesar(b"foto", "insecto", LAT, LON)
    assert aviso["especie"] == "velutina"
    assert aviso["confianza"] == pytest.approx(0.91)


def test_si_el_llm_lanza_excepcion(entorno, monkeypatch):
    def revienta(*_a, **_k):
        raise RuntimeError("sin red")

    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.9})
    monkeypatch.setattr(pipeline, "analizar_imagen", revienta)

    assert pipeline.procesar(b"foto", "insecto", LAT, LON)["especie"] == "crabro"
    assert pipeline.procesar(b"nido", "nido", LAT, LON)["especie"] == "no_concluyente"


def test_velutina_con_confianza_baja_pide_otra_foto(entorno, monkeypatch):
    """Aunque gane velutina, si la confianza es baja se pide otra foto (AGENTS.md)."""
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.93})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("velutina", "insecto", 0.3))

    aviso = pipeline.procesar(b"foto", "insecto", LAT, LON)
    assert aviso["especie"] == "velutina"
    assert aviso["confianza"] == pytest.approx(0.3)
    assert aviso["consejo_foto"]
