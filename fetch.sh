#!/usr/bin/env bash
# Descarga datos de las fuentes publicas. Lee credenciales de .env (ver .env.example).
#   ./fetch.sh cells <MCC>          OpenCelliD: celdas de un pais (Espana=214)
#   ./fetch.sh wifi  <lat1> <lon1> <lat2> <lon2>   WiGLE: APs en un bounding box
#   ./fetch.sh agnss <YYYY> <DDD>   CDDIS: efemerides broadcast (dia del anio, 001-366)
# Los ficheros se guardan en data/.
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || { echo "Falta .env (copia .env.example y rellena)"; exit 1; }
set -a; . ./.env; set +a
mkdir -p data

case "${1:-}" in
  cells)
    mcc="$2"; out="data/ocid_${mcc}.csv.gz"
    echo "Descargando OpenCelliD MCC=$mcc -> $out"
    # token vía --config en stdin para no exponerlo en la lista de procesos (ps)
    curl -fSL -m 300 -o "$out" --config - <<EOF
url = "https://opencellid.org/ocid/downloads?token=${OCID_TOKEN}&type=mcc&file=${mcc}.csv.gz"
EOF
    echo "OK: $(gzip -dc "$out" | wc -l) celdas";;

  wifi)
    la1="$2"; lo1="$3"; la2="$4"; lo2="$5"; out="data/wigle.json"
    echo "Descargando WiGLE bbox [$la1,$lo1]-[$la2,$lo2] -> $out"
    nr=$(mktemp)  # netrc temporal (600): credenciales fuera de la lista de procesos
    printf 'machine api.wigle.net login %s password %s\n' "$WIGLE_USER" "$WIGLE_PASS" > "$nr"
    curl -fSL -m 60 -H 'Accept:application/json' --netrc-file "$nr" --basic \
      "https://api.wigle.net/api/v2/network/search?latrange1=${la1}&latrange2=${la2}&longrange1=${lo1}&longrange2=${lo2}&resultsPerPage=100" \
      -o "$out"
    rm -f "$nr"
    echo "OK: $(grep -o '"netid"' "$out" | wc -l) APs (sube resultsPerPage para mas)";;

  agnss)
    yyyy="$2"; ddd="$3"; yy="${yyyy:2:2}"; out="data/brdc${ddd}0.${yy}n.gz"
    echo "Descargando CDDIS efemerides $yyyy dia $ddd -> $out"
    nr=$(mktemp); ck=$(mktemp)
    printf 'machine urs.earthdata.nasa.gov login %s password %s\n' "$EARTHDATA_USER" "$EARTHDATA_PASS" > "$nr"
    curl -fSL -m 120 --netrc-file "$nr" -c "$ck" -b "$ck" -o "$out" \
      "https://cddis.nasa.gov/archive/gnss/data/daily/${yyyy}/${ddd}/${yy}n/brdc${ddd}0.${yy}n.gz"
    rm -f "$nr" "$ck"
    echo "OK: $(gzip -dc "$out" | head -1)";;

  *) echo "uso: ./fetch.sh {cells <MCC>|wifi <lat1> <lon1> <lat2> <lon2>|agnss <YYYY> <DDD>}"; exit 1;;
esac
