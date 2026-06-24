"""Parsing de los ficheros de las fuentes a filas para la BD. Sin acceso a BD."""
import csv
import gzip
import json
from collections.abc import Iterator

RADIOS = {"GSM", "UMTS", "LTE", "NR", "CDMA"}


def _open(path: str):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def cell_rows(path: str) -> Iterator[tuple]:
    """Filas de OpenCelliD: (radio,mcc,mnc,area,cid,lon,lat,range,samples).

    El .gz completo trae cabecera; los ficheros por-MCC no. Si la 1a columna no
    es un tipo de radio, es cabecera y se descarta.
    """
    with _open(path) as f:
        reader = csv.reader(f)
        first = next(reader, None)
        if first and first[0].strip().upper() in RADIOS:
            row = _cell_row(first)
            if row:
                yield row
        for raw in reader:
            row = _cell_row(raw)
            if row:
                yield row


def _cell_row(row: list[str]) -> tuple | None:
    # OpenCelliD: radio,mcc,net,area,cell,unit,lon,lat,range,samples,...
    # Salta filas malformadas (blancas o truncadas) en vez de romper la carga.
    if len(row) < 10:
        return None
    return (row[0].upper(), row[1], row[2], row[3], row[4], row[6], row[7], row[8], row[9])


def wifi_rows(path: str) -> Iterator[tuple]:
    """Filas de WiGLE: (bssid,ssid,lon,lat). Acepta JSON (API) o CSV (web export)."""
    return _wifi_rows_json(path) if path.endswith(".json") else _wifi_rows_csv(path)


def _wifi_rows_json(path: str) -> Iterator[tuple]:
    with open(path) as f:
        for r in json.load(f).get("results", []):
            # salta resultados sin coordenadas o sin BSSID
            if r.get("trilat") is None or r.get("trilong") is None or not r.get("netid"):
                continue
            yield (r["netid"].upper(), r.get("ssid"), r["trilong"], r["trilat"])


def _wifi_rows_csv(path: str) -> Iterator[tuple]:
    with _open(path) as f:
        reader = csv.reader(f)
        idx = {name: i for i, name in enumerate(next(reader, []))}
        missing = [c for c in ("netid", "trilat", "trilong") if c not in idx]
        if missing:
            raise ValueError(f"WiGLE CSV sin columnas requeridas: {missing}")
        need = max(idx["netid"], idx["trilat"], idx["trilong"])
        for row in reader:
            if len(row) <= need:
                continue  # fila truncada/malformada
            ssid = row[idx["ssid"]] if "ssid" in idx else None
            yield (row[idx["netid"]].upper(), ssid, row[idx["trilong"]], row[idx["trilat"]])
