"""Acceso a la conexión MariaDB. Capa compartida por la API y el loader."""
import pymysql

from .config import settings


def connect(dict_rows: bool = False):
    """Abre una conexión. `dict_rows=True` devuelve filas como dict (API)."""
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_pass,
        database=settings.db_name,
        cursorclass=pymysql.cursors.DictCursor if dict_rows else pymysql.cursors.Cursor,
    )
