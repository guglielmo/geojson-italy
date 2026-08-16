#!/bin/sh

set -o errexit
set -o nounset

IFS='
	 '

CDPATH= cd -- "$(dirname -- "$0")"

# The highest province code in the data. Hardcoding it silently dropped all of
# Sardinia when the 2026 reform renumbered its provinces up to 119.
MAX_PROV=$(mapshaper -i comuni.geojson encoding=utf8 \
    -filter-fields prov_istat_code_num \
    -o - format=csv | tail -n +2 | sort -un | tail -1)
echo "highest province code in the data: ${MAX_PROV}"

mapshaper \
    -i comuni.geojson encoding=utf8 -clean \
    -simplify 20% weighted \
    -o topojson/limits_IT_municipalities.topo.json bbox format=topojson

# No -clean here. The municipalities were cleaned before simplification, in the
# invocation above, and cleaning them again afterwards is where a municipality
# disappears: simplification can leave a tiny polygon degenerate, and -clean
# drops it without a word. That is issue #34 — Miagliano, 0.7 km² in Biella,
# missing from this file alone since at least the 2023 release, while surviving
# in limits_IT_municipalities.topo.json produced by the step above.
mapshaper \
    -i topojson/limits_IT_municipalities.topo.json encoding=utf8 \
    -rename-layers municipalities \
    -dissolve prov_istat_code + \
      copy-fields=prov_name,prov_istat_code_num,prov_acr,prov_iso_3166_2,prov_uts_code,prov_tipo_uts,reg_name,reg_istat_code,reg_istat_code_num,reg_iso_3166_2 name=provinces \
    -target 1 \
    -dissolve reg_istat_code + \
      copy-fields=reg_name,reg_istat_code_num,reg_iso_3166_2 name=regions \
    -target 1  \
    -o topojson/limits_IT_all.topo.json bbox format=topojson target=regions,provinces,municipalities \
    -o topojson/limits_IT_regions.topo.json bbox format=topojson target=regions \
    -o topojson/limits_IT_provinces.topo.json bbox format=topojson target=provinces

for REG in $(seq 1 20); do
    mapshaper \
        -i topojson/limits_IT_municipalities.topo.json \
        -filter reg_istat_code_num==$REG \
        -o topojson/limits_R_${REG}_municipalities.topo.json bbox format=topojson
done

for PROV in $(seq 1 "$MAX_PROV"); do
    mapshaper \
        -i topojson/limits_IT_municipalities.topo.json \
        -filter prov_istat_code_num==$PROV \
        -rename-layers municipalities target=1 \
        -o topojson/limits_P_${PROV}_municipalities.topo.json bbox format=topojson
done
