#!/bin/sh

set -o errexit
set -o nounset

IFS='
	 '

CDPATH= cd -- "$(dirname -- "$0")"

cp comuni.geojson geojson/limits_IT_municipalities.geojson

# The highest province code in the data. Hardcoding it silently dropped all of
# Sardinia when the 2026 reform renumbered its provinces up to 119.
MAX_PROV=$(mapshaper -i comuni.geojson encoding=utf8 \
    -filter-fields prov_istat_code_num \
    -o - format=csv | tail -n +2 | sort -un | tail -1)
echo "highest province code in the data: ${MAX_PROV}"

mapshaper \
    -i geojson/limits_IT_municipalities.geojson encoding=utf8 -clean \
    -rename-layers municipalities \
    -dissolve prov_istat_code + \
      copy-fields=prov_name,prov_istat_code_num,prov_acr,prov_iso_3166_2,prov_uts_code,prov_tipo_uts,reg_name,reg_istat_code,reg_istat_code_num,reg_iso_3166_2 name=provinces \
    -target 1 \
    -dissolve reg_istat_code + \
      copy-fields=reg_name,reg_istat_code_num,reg_iso_3166_2 name=regions \
    -target 1  \
    -o geojson/limits_IT_provinces.geojson bbox gj2008 format=geojson target=provinces \
    -o geojson/limits_IT_regions.geojson bbox gj2008 format=geojson target=regions

# The metropolitan cities on their own. They stay inside limits_IT_provinces as
# well, where they have always been; this layer is additive. prov_tipo_uts comes
# from the archive, so the file is right for any date rather than for today.
mapshaper \
    -i geojson/limits_IT_provinces.geojson encoding=utf8 \
    -filter 'prov_tipo_uts=="Città metropolitana"' \
    -o geojson/limits_IT_metropolitan_cities.geojson bbox gj2008 format=geojson

for REG in $(seq 1 20)
do
  mapshaper \
    -i geojson/limits_IT_municipalities.geojson encoding=utf8 -clean \
    -filter reg_istat_code_num==$REG \
    -o geojson/limits_R_${REG}_municipalities.geojson bbox format=geojson gj2008
done

for PROV in $(seq 1 "$MAX_PROV")
do
  mapshaper \
    -i geojson/limits_IT_municipalities.geojson encoding=utf8 -clean \
    -filter prov_istat_code_num==$PROV \
    -o geojson/limits_P_${PROV}_municipalities.geojson bbox format=geojson gj2008
done

