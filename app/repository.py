"""Acceso a datos: todo el SQL vive aquí. Depende de db y domain."""
from . import db
from .domain import Point, bounding_box

CellKey = tuple[str, int, int, int, int]  # (radio, mcc, mnc, area, cid)


def ping() -> None:
    """Comprueba que la BD responde (para /health)."""
    with db.connect() as c, c.cursor() as cur:
        cur.execute("SELECT 1")


def find_cell(radio: str, mcc: int, mnc: int, area: int, cid: int) -> dict | None:
    with db.connect(dict_rows=True) as c, c.cursor() as cur:
        cur.execute(
            "SELECT lon, lat, `range`, samples FROM cells "
            "WHERE radio=%s AND mcc=%s AND mnc=%s AND area=%s AND cid=%s",
            (radio.upper(), mcc, mnc, area, cid),
        )
        return cur.fetchone()


def find_wifi(bssid: str) -> dict | None:
    with db.connect(dict_rows=True) as c, c.cursor() as cur:
        cur.execute("SELECT ssid, lon, lat FROM wifi WHERE bssid=%s", (bssid.upper(),))
        return cur.fetchone()


def find_cells(keys: list[CellKey]) -> dict[CellKey, dict]:
    """Busca varias celdas en UNA sola query. Devuelve {clave: fila}."""
    if not keys:
        return {}
    norm = [(r.upper(), mcc, mnc, area, cid) for r, mcc, mnc, area, cid in keys]
    placeholders = ",".join(["(%s,%s,%s,%s,%s)"] * len(norm))
    params = [v for key in norm for v in key]
    # placeholders solo contiene "%s"/comas (depende del nº de claves), nunca datos de
    # usuario; los valores van parametrizados en `params`. No es inyectable.
    with db.connect(dict_rows=True) as c, c.cursor() as cur:
        cur.execute(
            "SELECT radio, mcc, mnc, area, cid, lat, lon, samples FROM cells "
            f"WHERE (radio, mcc, mnc, area, cid) IN ({placeholders})",  # nosec B608
            params,
        )
        return {(r["radio"], r["mcc"], r["mnc"], r["area"], r["cid"]): r for r in cur.fetchall()}


def find_wifis(bssids: list[str]) -> dict[str, dict]:
    """Busca varios APs en UNA sola query. Devuelve {bssid: fila}."""
    if not bssids:
        return {}
    norm = [b.upper() for b in bssids]
    placeholders = ",".join(["%s"] * len(norm))  # solo "%s"/comas, valores parametrizados
    with db.connect(dict_rows=True) as c, c.cursor() as cur:
        cur.execute(f"SELECT bssid, lat, lon FROM wifi WHERE bssid IN ({placeholders})", norm)  # nosec B608
        return {r["bssid"]: r for r in cur.fetchall()}


def nearest(kind: str, center: Point, radius_m: float, limit: int) -> list[dict]:
    """Torres/APs más cercanas a un punto, ordenadas por distancia (m).

    Prefiltra con un bounding box (usa el índice espacial) y refina con
    ST_Distance_Sphere.
    """
    # `table` y `cols` salen de un mapeo fijo según `kind` (validado en la capa API);
    # nunca son datos de usuario. Coords/box/limit van parametrizados. No es inyectable.
    table = "cells" if kind == "cell" else "wifi"
    cols = "radio,mcc,mnc,area,cid" if kind == "cell" else "bssid,ssid"
    min_lat, min_lon, max_lat, max_lon = bounding_box(center, radius_m)
    box = (
        f"POLYGON(({min_lon} {min_lat},{max_lon} {min_lat},"
        f"{max_lon} {max_lat},{min_lon} {max_lat},{min_lon} {min_lat}))"
    )
    with db.connect(dict_rows=True) as c, c.cursor() as cur:
        cur.execute(
            f"SELECT {cols}, lon, lat, "
            "ST_Distance_Sphere(pt, POINT(%s,%s)) AS distance_m "
            f"FROM {table} WHERE MBRContains(ST_GeomFromText(%s), pt) "  # nosec B608
            "ORDER BY distance_m LIMIT %s",
            (center.lon, center.lat, box, limit),
        )
        return list(cur.fetchall())


def bulk_replace(table: str, columns: str, rows, batch_size: int = 5000) -> int:
    """REPLACE INTO masivo por lotes. Devuelve el nº de filas insertadas."""
    placeholders = ",".join(["%s"] * len(columns.split(",")))
    sql = f"REPLACE INTO {table} ({columns}) VALUES ({placeholders})"
    inserted = 0
    with db.connect() as c, c.cursor() as cur:
        batch = []
        for row in rows:
            batch.append(row)
            if len(batch) >= batch_size:
                cur.executemany(sql, batch)
                c.commit()
                inserted += len(batch)
                batch = []
        if batch:
            cur.executemany(sql, batch)
            c.commit()
            inserted += len(batch)
    return inserted
