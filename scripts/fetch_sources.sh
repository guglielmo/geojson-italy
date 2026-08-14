#!/bin/sh
# Download the ISTAT sources for a given reference year into build/.
# Usage: ./scripts/fetch_sources.sh 2026

set -o errexit
set -o nounset

CDPATH= cd -- "$(dirname -- "$0")/.."

YEAR="${1:?usage: fetch_sources.sh YEAR}"
OUT="build/istat/${YEAR}"
mkdir -p "$OUT"

BASE="https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati"

# From 2022 onward ISTAT nests the file under a year directory.
if [ "$YEAR" -ge 2022 ]; then
    ZIP_URL="${BASE}/${YEAR}/Limiti0101${YEAR}_g.zip"
else
    ZIP_URL="${BASE}/Limiti0101${YEAR}_g.zip"
fi

ELENCO_URL="https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx"

echo "Fetching ${ZIP_URL}"
curl -fsSL -o "${OUT}/limiti.zip" "$ZIP_URL"

echo "Fetching ${ELENCO_URL}"
curl -fsSL -o "${OUT}/elenco.xlsx" "$ELENCO_URL"

( cd "$OUT" && sha256sum limiti.zip elenco.xlsx > SHA256SUMS )
cat "${OUT}/SHA256SUMS"

echo "Unpacking"
( cd "$OUT" && unzip -o -q limiti.zip )

# Convert each shapefile to GeoJSON with mapshaper, so the Python step needs no geo stack.
# encoding=utf8 must stay immediately after the input file, before anything else; see CLAUDE.md.
# -proj wgs84 is required: despite the _WGS84 suffix, which names the datum, these files are
# projected in UTM zone 32N (EPSG:32632) and their coordinates are metres. Without it the
# output would carry metres where this repository publishes degrees.
for LAYER in Com ProvCM Reg; do
    SHP=$(find "$OUT" -name "${LAYER}0101${YEAR}_g_WGS84.shp" | head -1)
    if [ -z "$SHP" ]; then
        echo "ERROR: shapefile for layer ${LAYER} not found under ${OUT}" >&2
        exit 1
    fi
    mapshaper -i "$SHP" encoding=utf8 \
        -proj wgs84 \
        -o "${OUT}/${LAYER}.geojson" format=geojson gj2008
done

echo "Done: ${OUT}"
