"""SQLite: crear tabla, insertar y listar avisos (spec §4). Responsable: Backend."""

DB_PATH = "data/avisos.db"


def init_db(path: str = DB_PATH) -> None:
    """Crea la tabla `avisos` si no existe y carga data/seed_avisos.csv si está vacía."""
    raise NotImplementedError


def insertar_aviso(aviso: dict, path: str = DB_PATH) -> int:
    """Inserta un aviso con los campos de §4 y devuelve su id."""
    raise NotImplementedError


def listar_avisos(path: str = DB_PATH) -> list[dict]:
    """Devuelve todos los avisos como diccionarios con los campos de §4."""
    raise NotImplementedError
