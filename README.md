# geojson-italy

Administrative boundaries of Italy — regions, provinces and municipalities — as
[GeoJSON](https://geojson.org/) and [TopoJSON](https://github.com/topojson/topojson), in
WGS84 (EPSG:4326).

The repository answers two questions:

1. **What are Italy's administrative boundaries now?** Download a file. No build step, no
   interpreter, no dependency on this project's tooling.
2. **What were they on a given date?** The same boundaries as ISTAT published them for that
   date, back to **21 October 2001** — including the changes that took effect inside the
   year, which an annual series cannot represent.

Everything here is derived from [ISTAT](https://www.istat.it/) and redistributed under
CC-BY. Every figure in this file is measured, not estimated.

> **Breaking change in release 2026.1.** The Sardinian reform effective 1 January 2026
> renumbered every Sardinian province — codes 90, 91, 92, 95 and 111 are vacant, the new
> units occupy 112 to 119 — and with them **all 377 Sardinian `com_istat_code` values**,
> with no overlap against the previous release. Join on `com_catasto_code`, which is stable
> across the reform. See the [CHANGELOG](CHANGELOG.md) before upgrading.

---

## 1. Current boundaries

The files at the root of this repository are the **1 January 2026** ISTAT vintage. Pin them
directly:

```
https://raw.githubusercontent.com/guglielmo/geojson-italy/main/<path>
```

### GeoJSON — unsimplified

Full vertex count, one layer per file, compatible with almost every visualiser and library.

| File | Contents |
| --- | --- |
| [`geojson/limits_IT_municipalities.geojson`](geojson/limits_IT_municipalities.geojson) | all 7,896 municipalities, ~40 MB |
| [`geojson/limits_IT_provinces.geojson`](geojson/limits_IT_provinces.geojson) | all 110 provinces and metropolitan cities |
| [`geojson/limits_IT_regions.geojson`](geojson/limits_IT_regions.geojson) | all 20 regions |
| `geojson/limits_R_{code}_municipalities.geojson` | municipalities of one region — e.g. [`R_12`](geojson/limits_R_12_municipalities.geojson), Lazio |
| `geojson/limits_P_{code}_municipalities.geojson` | municipalities of one province — e.g. [`P_58`](geojson/limits_P_58_municipalities.geojson), Rome |

`{code}` is the ISTAT numeric code **without zero padding**, while the `prov_istat_code` and
`reg_istat_code` *properties* are zero-padded strings. Both forms exist on purpose;
`*_istat_code_num` is the integer.

A file is emitted for every code in range even where no province survives, so a vacant code
returns an empty `GeometryCollection` rather than a 404 — the URL stays stable.

Since release 2023.1 the GeoJSON files are written with mapshaper's `gj2008` flag, which
emits pre-RFC 7946 GeoJSON (winding order and the `crs` member). This is what keeps them
working with D3 and everything built on it, Plotly included — see
[mapshaper#432](https://github.com/mbloch/mapshaper/issues/432#issuecomment-675775465).

### TopoJSON — simplified to 20%

Smaller, less precise, and able to carry several layers in one file. Shared borders stay
topologically coincident across the three levels, because provinces and regions are
dissolved from the *already simplified* municipalities.

| File | Contents |
| --- | --- |
| [`topojson/limits_IT_all.topo.json`](topojson/limits_IT_all.topo.json) | municipalities, provinces and regions in three layers, ~4 MB |
| [`topojson/limits_IT_municipalities.topo.json`](topojson/limits_IT_municipalities.topo.json) | municipalities, one layer |
| [`topojson/limits_IT_provinces.topo.json`](topojson/limits_IT_provinces.topo.json) | provinces |
| [`topojson/limits_IT_regions.topo.json`](topojson/limits_IT_regions.topo.json) | regions |
| `topojson/limits_R_{code}_municipalities.topo.json` | municipalities of one region |
| `topojson/limits_P_{code}_municipalities.topo.json` | municipalities of one province |

GitHub previews GeoJSON only below a size limit and never previews TopoJSON; use
[mapshaper.org](https://mapshaper.org) for the larger files.

### Metropolitan cities

Metropolitan cities are second-level units alongside provinces. They are **inside**
`limits_IT_provinces` as they have always been — Rome is `058`, and the file still holds all
110 units — and they now also have a layer of their own:

| File | Contents |
| --- | --- |
| [`geojson/limits_IT_metropolitan_cities.geojson`](geojson/limits_IT_metropolitan_cities.geojson) | the 15 città metropolitane |

`prov_tipo_uts` distinguishes all five ISTAT unit types — Provincia (83), Città metropolitana
(15), Libero consorzio di comuni (6), Unità non amministrativa (4), Provincia autonoma (2) —
so any other split can be made with a filter.

Note that ISTAT gives metropolitan cities **two** codes and its own products disagree on
which to show: the boundary shapefiles use `COD_PROV` 112 for Sassari and 118 for Cagliari,
the codes list uses `COD_UTS` 312 and 318. This repository has always published the
`COD_PROV` family.

### Properties

| Property | On | Meaning |
| --- | --- | --- |
| `name` | M | municipality name |
| `com_catasto_code` | M | cadastral (Belfiore) code, e.g. `H501` |
| `com_istat_code` / `com_istat_code_num` | M | ISTAT code, zero-padded string / integer |
| `op_id` | M | openpolis id, for integration with legacy OP data |
| `opdm_id` | M | opdm id |
| `minint_elettorale` | M | interior ministry id |
| `minint_finloc` | M | interior ministry id used in Finanza Locale statements |
| `prov_name` | M, P | province name |
| `prov_istat_code` / `prov_istat_code_num` | M, P | province ISTAT code |
| `prov_acr` | M, P, R | province acronym, e.g. `RM` |
| `prov_iso_3166_2` | M, P | province [ISO 3166-2](https://en.wikipedia.org/wiki/ISO_3166-2:IT) code, e.g. `IT-RM`, **or `null`** |
| `prov_uts_code` | M, P | ISTAT's other code family for second-level units: 312 Sassari, 318 Cagliari, against `COD_PROV` 112 and 118 |
| `prov_tipo_uts` | M, P | Provincia, Provincia autonoma, Città metropolitana, Libero consorzio di comuni, Unità non amministrativa |
| `reg_name` | M, P, R | region name |
| `reg_istat_code` / `reg_istat_code_num` | M, P, R | region ISTAT code |
| `reg_iso_3166_2` | M, P, R | region ISO 3166-2 code, e.g. `IT-62` |

M = municipalities, P = provinces, R = regions. Municipality-only properties do not survive
the dissolve into provinces and regions.

ISO numbers the regions on a scheme of its own, unrelated to ISTAT's: Piedmont is ISTAT `01`
and ISO `IT-21`.

**`prov_iso_3166_2` is `null` for five of the 110 second-level units, and that is correct.**
ISO 3166-2:IT defines no code for **Valle d'Aosta** (the region exercises provincial
functions, so `IT-AO` was deleted in 2019) nor for the four Sardinian units created in 2026
— **Gallura Nord-Est Sardegna**, **Ogliastra**, **Medio Campidano**, **Sulcis Iglesiente**.
Those four bear vehicle plates matching codes ISO *withdrew* in April 2019, so filling the
gap from `prov_acr` would publish identifiers the standard no longer defines. 175
municipalities are affected; they still carry `reg_iso_3166_2`.

---

## 2. Boundaries at a past date

Administrative geography moves constantly: since 2001 municipalities have merged, split,
been renumbered and been reassigned to other provinces on **98 distinct dates**, and 72 of
those fall inside the year. A series published only at 1 January cannot answer for them —
it returns a plausible, wrong answer with no error.

### Downloading a past date

Each publication date has a GitHub Release tagged with that date, carrying the same shape of
file set as the root of the repository. Nothing to build, nothing to filter:

```sh
curl -LO https://github.com/guglielmo/geojson-italy/releases/download/2005-01-01/limits_IT_municipalities.geojson.gz
```

| Asset | 2005-01-01 |
| --- | --- |
| `limits_IT_municipalities.geojson.gz` | 8,101 municipalities |
| `limits_IT_provinces.geojson.gz` | 103 provinces |
| `limits_IT_metropolitan_cities.geojson.gz` | 0 — metropolitan cities were instituted in 2015 |
| `limits_IT_regions.geojson.gz` | 20 regions |
| `limits_IT_all.topo.json.gz` | the three layers, simplified to 20% |

Provinces and regions are dissolved from the municipalities **of that date**, so the file
set describes the country as it was, not today's boundaries backdated. Every asset is
gzipped, which every common tool reads directly.

**Which tag do I want?** For a year, take its **1 January** — `2005-01-01` — which is what
"the 2005 boundaries" almost always means. If you have an exact date, look it up in
[`temporal/INDEX.csv`](temporal/INDEX.csv): one row per validity interval, saying which
release serves it and what changed on that date.

```csv
valid_from,valid_to,release_tag,municipalities,change
2005-01-01,2005-05-04,2005-01-01,8101,16 admin_variazione_territoriale
2005-05-04,2005-05-11,2005-05-04,8101,1 admin_cambio_denominazione
2005-05-11,2006-01-01,2005-05-11,8101,1 admin_cambio_denominazione
```

This matters more than it looks. 72 of the 98 dates fall inside the year, so for a date like
10 September 2021 both the 2021 and the 2022 January editions are wrong — Misiliscemi was
established on 20 February 2021, and Montecopiolo and Sassofeltrio were recoded on 17 June.
The index resolves it to `2021-06-17`.

Per-region and per-province subsets (`limits_R_*`, `limits_P_*`) are produced for the current
vintage only.

### The archive behind them

The historical archive lives in [`temporal/`](temporal/), holds **8,231 municipalities in
78,325 versions**, and is the repository's source of truth: the current files above and every
release asset are derived from it. Read it directly only if you want the whole history at
once — for a single date, take the release.

```
temporal/
├── comuni/reg=NN.geojson   one file per region, each feature carrying a validity interval
├── SCHEMA.md               every field, and what is checked
└── INDEX.csv               validity interval -> release tag   (not published yet)
```

Each feature is one municipality over one validity period, so a date is an interval filter:

```sh
mapshaper -i temporal/comuni/reg=12.geojson \
  -filter 'valid_from <= "2021-09-10" && (!valid_to || valid_to > "2021-09-10")' \
  -o boundaries_2021-09-10.geojson
```

**Why GeoJSON rather than a database format.** Parquet would be smaller and directly
queryable. It is rejected anyway: verifying this archive should require mapshaper, already
this project's only dependency, not a database engine. Split by region so a change touching
one region rewrites one file.

Read [`temporal/SCHEMA.md`](temporal/SCHEMA.md) before using it. Three things are not
self-evident:

- **The key is `terr_key`, the municipality's first cadastral code — never the ISTAT code.**
  The ISTAT code embeds the province, so it changes on reassignment; the 2026 Sardinian
  reform changed 377 of them with zero overlap. Measured across the series, exactly one
  municipality ever changed its own cadastral code and no code was ever reused.
- **`version_reason` separates administrative change from ISTAT redrawing its own lines.**
  ISTAT re-generalises its geometry in some editions and not others — 2002, 2010, 2011,
  2012, 2019, 2022, 2025 — so a naive diff of two adjacent years shows ~7,900 changed
  boundaries and suggests something historic happened. Filter on this field instead.
- **Gaps are meaningful.** Baranzate was constituted in 2001, abolished in 2003 when the
  Constitutional Court struck down the regional law behind it, and constituted again in
  2004. Its intervals have a hole, on purpose.

The archive is faithful to what ISTAT published for each date, and is not smoothed,
normalised or reconciled. `source_edition` names the file each geometry was read from, so
the claim can be checked by downloading it.

The older release tags (`2019`, `2021.1`, `2021.2`, `2022.1`, `2023.1`, `2026.1`, `2026.2`)
record what this repository published at those moments, which is a different fact from what
ISTAT published for those reference dates. They stay untouched, and the ISO-date tags cannot
collide with them.

---

## Sources

Everything comes from ISTAT, over anonymous HTTP, with **no credentials**.

| Layer | Source |
| --- | --- |
| Geometry | The [generalised boundary editions](https://www.istat.it/it/archivio/222527), one per reference date. 26 editions, 2001–2026, checksummed in `build/editions/MANIFEST.json`. |
| Codes, names, provincial and regional assignment | The SITUAS roster of territorial units, which answers with the complete list of municipalities valid on **any** date since 1948. |
| Why each version exists, and under which act | The SITUAS variation reports, covering municipal variations from 1991 and suppressions, renamings and code changes from the 1860s. |

Two facts about the sources are load-bearing and easy to get wrong:

- **The census editions do not describe 1 January.** `Limiti2001_g` contains Fonte Nuova,
  constituted 15 October 2001, and `Limiti2011_g` contains Gravedona ed Uniti, constituted
  11 February 2011, in place of the three municipalities it replaced. They describe their
  census date. This is why the series starts on 21 October 2001 rather than in January: for
  the preceding nine months ISTAT published no boundaries at all, and those dates are not
  served rather than served with a boundary set that does not describe them.
- **`-proj wgs84` is required when converting the shapefiles.** The `_WGS84` in the ISTAT
  filenames names the *datum*; the `.prj` is `WGS_1984_UTM_Zone_32N` in metres.

The two products agree: the municipality count in the boundary edition matches ISTAT's own
roster for **24 of 26** years, and the two exceptions are the census editions above.

## Reproducing it

Requires [mapshaper](https://github.com/mbloch/mapshaper) (node) — verified against `0.6.29`,
which generated release 2026.1, and `0.6.65` — and Python 3 for the fetch and build scripts.

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# the historical archive, from ISTAT to temporal/
.venv/bin/python -m scripts.fetch_editions            # 26 boundary editions, ~300 MB
.venv/bin/python -m scripts.fetch_situas variations   # the variation reports
.venv/bin/python -m scripts.fetch_situas rosters      # the roster at each of the 98 dates
.venv/bin/python -m scripts.build_temporal build
.venv/bin/python -m scripts.validate_temporal

# the current vintage, and the files derived from it
./scripts/fetch_sources.sh 2026
cp comuni.geojson comuni.geojson.prev
.venv/bin/python -m scripts.build_comuni 2026
./generate_geojson.sh
./generate_topojson.sh
.venv/bin/pytest tests/
```

**Please ask SITUAS sparingly.** It answers one request at a time and returns 503 to some
client addresses for stretches at a time. The fetcher pauses between requests, retries
slowly, caches everything and takes `--limit N` to spread the first fill across sessions.

The build checks itself. `validate_temporal` verifies that no entity has overlapping
validity periods, that the municipality count matches ISTAT's roster at every one of the 98
dates, and that all 377 Sardinian municipalities resolve to the same key across the 2026
reform — the event that breaks any dataset keyed on the ISTAT code.

Older releases were built by hand following
[this wiki page](https://github.com/guglielmo/geojson-italy/wiki/How-to-generate-the-limits-files),
which the scripts above supersede.

## Canonical home

[`guglielmo/geojson-italy`](https://github.com/guglielmo/geojson-italy), previously
`openpolis/geojson-italy`. The default branch was renamed `master` → `main` in August 2026.
GitHub redirects both the old owner and the old branch name, `raw.githubusercontent.com`
included, so existing pinned URLs keep working — but a redirect is a convenience, not a
guarantee. Update pinned URLs to owner `guglielmo` and branch `main`.

## License and attribution

The administrative limits are copyrighted by **ISTAT** and released under
[CC-BY](https://creativecommons.org/licenses/by/4.0/). The data generated and published here
are released under the same licence. Keep the ISTAT attribution when redistributing.
