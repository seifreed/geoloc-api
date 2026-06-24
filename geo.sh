#!/usr/bin/env bash
# Helper: levanta el stack y resuelve los puertos dinámicos que asigna Docker.
#   ./geo.sh up                 -> build + arranca, imprime la URL de la API
#   ./geo.sh url                -> imprime la URL de la API
#   ./geo.sh load cells FILE    -> carga OpenCelliD en la BD (resuelve el puerto solo)
#   ./geo.sh load wifi  FILE    -> carga WiGLE
#   ./geo.sh down               -> para todo
set -euo pipefail
cd "$(dirname "$0")"

api_url() { echo "http://localhost:$(docker compose port api 8000 | cut -d: -f2)"; }
db_port() { docker compose port db 3306 | cut -d: -f2; }

case "${1:-}" in
  up)   docker compose up --build -d; sleep 3; echo "API: $(api_url)  (docs en $(api_url)/docs)";;
  url)  api_url;;
  load) DB_PORT="$(db_port)" python load.py "$2" "$3";;
  down) docker compose down;;
  *)    echo "uso: ./geo.sh {up|url|load <cells|wifi> <file>|down}"; exit 1;;
esac
