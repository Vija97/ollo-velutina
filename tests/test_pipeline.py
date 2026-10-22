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


def test_si_yolo_y_llm_discrepan_no_concluyente(entorno, monkeypatch):
    monkeypatch.setattr(pipeline, "clasificar_yolo", lambda _: {"especie": "velutina", "confianza": 0.95})
    monkeypatch.setattr(pipeline, "analizar_imagen", lambda *a, **k: _llm("crabro", "insecto", 0.9))

    aviso = pipeline.procesar(b"foto", "insecto", LAT, LON)

    assert aviso["especie"] == "no_concluyente"
    assert aviso["confianza"] == 0.0
    assert aviso["consejo_foto"]


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


def test_nido_crabro_con_yolo_confiable(entorno, monkeypatch):
    monkeypatch.setattr(
        pipeline, "clasificar_yolo", lambda _: {"especie": "crabro", "confianza": 0.81}
    )
    monkeypatch.setattr(
        pipeline, "analizar_imagen", lambda *_a, **_k: _llm("otra", "nido", 0.9)
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
