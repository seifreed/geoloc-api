#!/usr/bin/env python3
"""Carga datos en la BD. Uso:

    python load.py cells   cell_towers.csv.gz   # OpenCelliD
    python load.py wifi    wigle.json|csv        # WiGLE / wardriving propio

Lee la conexión de las mismas env vars que la API (DB_PORT para el puerto dinámico).
"""
import sys

from app import loaders, repository

JOBS = {
    "cells": ("cells", "radio,mcc,mnc,area,cid,lon,lat,`range`,samples", loaders.cell_rows),
    "wifi": ("wifi", "bssid,ssid,lon,lat", loaders.wifi_rows),
}


def main(kind: str, path: str) -> None:
    table, columns, parse = JOBS[kind]
    n = repository.bulk_replace(table, columns, parse(path))
    print(f"{kind} cargad{'a' if kind == 'cells' else 'o'}s: {n}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in JOBS:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
