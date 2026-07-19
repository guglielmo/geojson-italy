# Introduction

This repository contains geo-referenced limits for all municipalities in Italy,
and their breakdown by regions and provinces.

The [geographic projection](https://github.com/d3/d3-geo) used is WGS84.

The limits are released both in [topojson](https://github.com/topojson/topojson) with a high simplification rate (20%),
and the non-simplified [geojson](https://geojson.org/) format.

As administrative limits change continuously, the files are upgraded periodically, and refer to the **latest** administrative subdivisions, as published by [ISTAT](https://www.istat.it/) in [this permalink](https://www.istat.it/it/archivio/222527) (hoping it's actually a **permalink**).

Historical versions, year by year, are published as tags, currently only 2019 and 2021 are present.

The master branch currently contains limits as of June 2023.

# Canonical home

This repository lives at
[`guglielmo/geojson-italy`](https://github.com/guglielmo/geojson-italy).
It was previously hosted at `openpolis/geojson-italy`; old links redirect here.
Please update any pinned raw/CDN URLs to point to this repository.


# Attribution
The original administrative limits data are copyrighted by ISTAT, that releases them under the CC-BY license.
The data generated and published here are released under the same CC-BY license.

# Geojson files
These files are **not simplified**, contain a large number of vectors, and can only contain one layer.
They are compatible with almost all visualisers and applications, and can be used to integrate geographic information,
almost as ubiquitously as shp files.

As of June 2023 (tag 2023.1), the geojson files are produced using the `gj2008` flag of mapshaper, in order to make them compatile with the pre-RFC 7946 GeoJSON spec, and with the D3 javascript library, and other libraries using D3 underneath, as Plotly, for example.
You can find the original discussion in [this mapshaper's issue](https://github.com/mbloch/mapshaper/issues/432#issuecomment-675775465).

The following files are available:
- [geojson/limits_IT_municipalities.geojson](https://github.com/openpolis/geojson-italy/blob/master/geojson/limits_IT_municipalities.geojson) - all Italian municipalities, ~40MB
- [geojson/limits_IT_provinces.geojson](https://github.com/openpolis/geojson-italy/blob/master/geojson/limits_IT_provinces.geojson) - all Italian provinces
- [geojson/limits_IT_regions.geojson](https://github.com/openpolis/geojson-italy/blob/master/geojson/limits_IT_regions.geojson) - all Italian regions
- geojson/limits_R_{code}_municipalities.geojson - all municipalities in a region (R is the ISTAT numerical code of the region, ex: [geojson/limits_R_12_municipalities.geojson](https://github.com/openpolis/geojson-italy/blob/master/geojson/limits_R_12_municipalities.geojson) - Lazio region)
- geojson/limits_P_{code}_municipalities.geojson - all munitipalities in a province (P is the ISTAT numerical code of the province, ex: [geojson/limits_P_58_municipalities.geojson](https://github.com/openpolis/geojson-italy/blob/master/geojson/limits_P_58_municipalities.geojson) - Rome province)

Please consider that maps preview for geojson data are only available for files of limited size in github.com; use [mapshaper](https://mapshaper.org) to see and explore larger files.


# Topojson files
These files are **simplified**, **smaller**, but **less precise**, and contains **a lot less vectors** than the corresponding `geojson` files, can contain **many layers**, and can be used in compatible map visualisers ([leaflet](https://webkid.io/blog/maps-with-leaflet-and-topojson/), [d3](https://bl.ocks.org/almccon/410b4eb5cad61402c354afba67a878b8), mapshaper).

The following `topojson` files are available:
- [topojson/limits_IT_all.topo.json](https://github.com/openpolis/geojson-italy/blob/master/topojson/limits_IT_all.topo.json) - all municipalities, provinces and regions (3 layers), ~4MB
- [topojson/limits_IT_municipalities.topo.json](https://github.com/openpolis/geojson-italy/blob/master/topojson/limits_IT_municipalities.topo.json) - all Italian municipalities (1 layer), ~4MB
- [topojson/limits_IT_provinces.topo.json](https://github.com/openpolis/geojson-italy/blob/master/topojson/limits_IT_provinces.topo.json) - all Italian provinces (1 layer)
- [topojson/limits_IT_regions.topo.json](https://github.com/openpolis/geojson-italy/blob/master/topojson/limits_IT_regions.topo.json) - all Italian regions (1 layer)
- topojson/limits_R_{code}_municipalities.topo.json - all municipalities in a region (R is the ISTAT numerical code of the region, for ex: [topojson/limits_R_12_municipalities.topo.json](https://github.com/openpolis/geojson-italy/blob/master/topojson/limits_R_12_municipalities.topo.json) - Lazio region)
- topojson/limits_P_{code}_municipalities.topo.json - all munitipalities in a province (P is the ISTAT numerical code of the province, for ex: [topojson/limits_P_58_municipalities.topo.json](https://github.com/openpolis/geojson-italy/blob/master/topojson/limits_P_58_municipalities.topo.json) - Rome province)

Please consider that maps preview for topojson data are not available on github.com; use [mapshaper](https://mapshaper.org) to see the files.

# Metadata
Each geographic area has the following metadata:
- `name` (M) - the name of the municipality
- `com_catasto_code` (M) - the cadaster code (H501)
- `com_istat_code` (M) - the ISTAT code, as text (zero-padded)
- `com_istat_code_num` (M) - the ISTAT code, as integer
- `op_id` (M) - the openpolis ID (for integration with legacy OP data)
- `opdm_id` (M) - the opdm ID (for integration with OPDM data)
- `minint_elettorale` (M) - interior minister ID
- `prov_name` (M,P) - parent province name
- `prov_istat_code` (M,P) - parent province ISTAT code, as text (zero-padded)
- `prov_istat_code_num` (M,P) - parent province ISTAT code, as integer
- `prov_acr` (M,P,R) - parent province acronym (ex: RM)
- `reg_name` (M,P,R) - parent region full name
- `reg_istat_code` (M,P,R) - parent region ISTAT code, as text (zero padded)
- `reg_istat_code_num` (M,P,R) - parent region ISTAT code, as number

In parenthesis, the contexts where these properties can be found:
- M: Municipalities,
- P: Provinces,
- R: Regions

# Developers
To generate all files, starting from the `comuni.geojson` file:
```
  ./generate_geojson.sh
  ./generate_topojson.sh
```
The [mapshaper client](https://github.com/mbloch/mapshaper), based on [node js](https://nodejs.org/en/), is **required** by the scripts to work. These are currently based on mapshaper version `0.6.65`

How the `comuni.geojson` file is generated, and other scripts' internals are described in [this wiki page](https://github.com/openpolis/geojson-italy/wiki/How-to-generate-the-limits-files).
