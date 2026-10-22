"""SQLite: crear tabla, insertar y listar avisos (spec §4). Responsable: Backend."""

from __future__ import annotations

import csv
import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = "data/avisos.db"
SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_avisos.csv"

COLUMNAS = (
    "id",
    "created_at",
    "lat",
    "lon",
    "tipo",
    "especie",
    "confianza",
    "fuente_clasificacion",
    "explicacion",
    "foto_path",
    "duplicado_de",
    "estado",
)

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS avisos (
    id INTEGER PRIMARY KEY,
    created_at TEXT,
    lat REAL,
    lon REAL,
    tipo TEXT,
    especie TEXT,
    confianza REAL,
    fuente_clasificacion TEXT,
    explicacion TEXT,
    foto_path TEXT,
    duplicado_de INTEGER,
    estado TEXT
)
"""


def _conectar(path: str | Path) -> sqlite3.Connection:
    destino = Path(path)
    if destino.parent != Path(""):
        destino.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(destino)
    con.row_factory = sqlite3.Row
    return con


def _texto(valor) -> str | None:
    if valor is None:
        return None
    valor = str(valor).strip()
    return valor or None


def _numero(valor, tipo):
    if valor is None:
        return None
    valor = str(valor).strip()
    return tipo(valor) if valor else None


def _fila(valores: dict) -> tuple:
    """Normaliza un aviso (CSV o diccionario) al orden y tipos de §4."""
    return (
        _numero(valores.get("id"), int),
        _texto(valores.get("created_at")),
        _numero(valores.get("lat"), float),
        _numero(valores.get("lon"), float),
        _texto(valores.get("tipo")),
        _texto(valores.get("especie")),
        _numero(valores.get("confianza"), float),
        _texto(valores.get("fuente_clasificacion")),
        _texto(valores.get("explicacion")),
        _texto(valores.get("foto_path")),
        _numero(valores.get("duplicado_de"), int),
        _texto(valores.get("estado")),
    )


def init_db(path: str = DB_PATH) -> None:
    """Crea la tabla `avisos` si no existe y carga data/seed_avisos.csv si está vacía."""
    with closing(_conectar(path)) as con, con:
        con.execute(_ESQUEMA)
        total = con.execute("SELECT COUNT(*) FROM avisos").fetchone()[0]
        if total or not Path(SEED_PATH).is_file():
            return
        with open(SEED_PATH, newline="", encoding="utf-8") as fichero:
            filas = [_fila(fila) for fila in csv.DictReader(fichero)]
        marcas = ", ".join("?" * len(COLUMNAS))
        con.executemany(f"INSERT INTO avisos ({', '.join(COLUMNAS)}) VALUES ({marcas})", filas)


def insertar_aviso(aviso: dict, path: str = DB_PATH) -> int:
    """Inserta un aviso con los campos de §4 y devuelve su id."""
    marcas = ", ".join("?" * len(COLUMNAS))
    with closing(_conectar(path)) as con, con:
        con.execute(_ESQUEMA)
        cursor = con.execute(
            f"INSERT INTO avisos ({', '.join(COLUMNAS)}) VALUES ({marcas})",
            _fila(aviso),
        )
        return int(cursor.lastrowid)


def listar_avisos(path: str = DB_PATH) -> list[dict]:
    """Devuelve todos los avisos como diccionarios con los campos de §4."""
    with closing(_conectar(path)) as con:
        con.execute(_ESQUEMA)
        filas = con.execute("SELECT * FROM avisos ORDER BY id").fetchall()
    return [dict(fila) for fila in filas]
