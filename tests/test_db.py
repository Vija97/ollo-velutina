"""Tests de core/db.py (Issue #3). Base temporal, sin tocar data/avisos.db."""

import csv

import pytest

from core import db


def test_init_db_carga_el_seed(tmp_path):
    ruta = tmp_path / "avisos.db"
    db.init_db(str(ruta))

    with open(db.SEED_PATH, newline="", encoding="utf-8") as fichero:
        filas_seed = list(csv.DictReader(fichero))

    avisos = db.listar_avisos(str(ruta))
    assert len(avisos) == len(filas_seed)
    assert len(avisos) >= 25

    primero = avisos[0]
    assert set(primero) == set(db.COLUMNAS)
    assert primero["tipo"] in {"insecto", "nido"}
    assert primero["especie"] in {"velutina", "crabro", "otra", "no_concluyente"}
    assert primero["fuente_clasificacion"] in {"yolo", "llm", "yolo+llm"}
    assert primero["estado"] in {"nuevo", "duplicado", "enviado"}
    assert isinstance(primero["lat"], float) and isinstance(primero["lon"], float)


def test_init_db_es_idempotente(tmp_path):
    ruta = tmp_path / "avisos.db"
    db.init_db(str(ruta))
    total = len(db.listar_avisos(str(ruta)))
    db.init_db(str(ruta))
    assert len(db.listar_avisos(str(ruta))) == total


def test_insertar_y_listar(tmp_path, monkeypatch):
    # sin seed, para saber exactamente qué hay en la base
    monkeypatch.setattr(db, "SEED_PATH", tmp_path / "no-existe.csv")
    ruta = tmp_path / "avisos.db"
    db.init_db(str(ruta))
    assert db.listar_avisos(str(ruta)) == []

    aviso = {
        "created_at": "2026-10-22T16:00:00",
        "lat": 42.8782,
        "lon": -8.5448,
        "tipo": "insecto",
        "especie": "velutina",
        "confianza": 0.91,
        "fuente_clasificacion": "yolo",
        "explicacion": "Banda naranja en el abdomen.",
        "foto_path": "data/fotos/99_velutina.jpg",
        "estado": "nuevo",
    }
    nuevo_id = db.insertar_aviso(aviso, str(ruta))
    assert nuevo_id == 1

    avisos = db.listar_avisos(str(ruta))
    assert len(avisos) == 1
    guardado = avisos[0]
    assert guardado["id"] == nuevo_id
    assert guardado["especie"] == "velutina"
    assert guardado["confianza"] == pytest.approx(0.91)
    assert guardado["duplicado_de"] is None
    assert guardado["lat"] == pytest.approx(42.8782)


def test_insertar_respeta_duplicado_de(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "SEED_PATH", tmp_path / "no-existe.csv")
    ruta = tmp_path / "avisos.db"
    db.init_db(str(ruta))

    original = db.insertar_aviso(
        {"lat": 42.88, "lon": -8.54, "tipo": "insecto", "especie": "velutina", "estado": "nuevo"},
        str(ruta),
    )
    copia = db.insertar_aviso(
        {
            "lat": 42.8802,
            "lon": -8.5401,
            "tipo": "insecto",
            "especie": "velutina",
            "estado": "duplicado",
            "duplicado_de": original,
        },
        str(ruta),
    )

    avisos = {aviso["id"]: aviso for aviso in db.listar_avisos(str(ruta))}
    assert avisos[copia]["duplicado_de"] == original
    assert avisos[copia]["estado"] == "duplicado"
