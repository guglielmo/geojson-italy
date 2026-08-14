# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A **data distribution repository**, not an application. It publishes geo-referenced
administrative limits for Italy (municipalities, provinces, regions) as GeoJSON and
TopoJSON, regenerated periodically from ISTAT releases. The only "code" is two POSIX
shell scripts wrapping [mapshaper](https://github.com/mbloch/mapshaper); all generated
output is committed to git.

Consequence: the **file paths and the property names are a public API**. Third parties
pin `raw.githubusercontent.com` / CDN URLs against them. Never rename, restructure or
delete published files as a cleanup — including the empty ones (see below).

Canonical home is `guglielmo/geojson-italy`, moved from `openpolis/geojson-italy`, with the
default branch renamed `master` → `main` in August 2026. GitHub redirects both the old owner
and the old branch name, `raw.githubusercontent.com` included — verified, so pre-existing
pinned URLs still resolve. Don't rely on it for new links: use owner `guglielmo` and branch
`main`.

## Commands

```sh
./scripts/fetch_sources.sh 2026        # ISTAT zip + xlsx -> build/istat/2026/, with SHA-256
.venv/bin/python -m scripts.build_comuni 2026   # + comuni.geojson.prev -> comuni.geojson
.venv/bin/pytest tests/                # unit tests + per-issue acceptance checks
./generate_geojson.sh    # comuni.geojson -> geojson/*.geojson   (unsimplified)
./generate_topojson.sh   # comuni.geojson -> topojson/*.topo.json (20% simplified)
```

The shell scripts need the global `mapshaper` CLI (node); verified against `0.6.29`, which
generated release 2026.1, and written against `0.6.65`. Check `mapshaper --version` before
assuming flag behaviour matches. The Python scripts need `.venv` from `requirements.txt`
(`openpyxl`, `pytest`). There is no linter.

`build_comuni.py` reads the previous release from `comuni.geojson.prev`, so a rebuild starts
with `cp comuni.geojson comuni.geojson.prev`. That file is gitignored and deleted once the
release is committed.

`encoding=utf8` must stay immediately after the input filename on `-i`, *before* `-clean`.
Placed after `-clean` it is parsed as an option of that command instead and the encoding is
not applied — that was the fix in PR #20. Accented municipality names are the thing at
stake here.

Each script runs ~131 mapshaper invocations, every one re-reading and re-`clean`ing the
full 38 MB source, so a full regeneration takes minutes. To iterate on a single output,
run the matching mapshaper command by hand rather than the whole loop.

## Pipeline architecture

`comuni.geojson` (35 MB, tracked, EPSG:4326/WGS84) is the **single source of truth** for
everything under `geojson/` and `topojson/`. Since release 2026.1 it is itself rebuilt in
this repository by `scripts/fetch_sources.sh` + `scripts/build_comuni.py`, replacing the
manual procedure in the
[wiki](https://github.com/guglielmo/geojson-italy/wiki/How-to-generate-the-limits-files).

The rebuild joins three sources: the ISTAT boundary edition supplies geometry, names and
territorial codes; `Elenco-comuni-italiani.xlsx` supplies the cadastral code per ISTAT code;
the *previous* `comuni.geojson` supplies `op_id`, `opdm_id`, `minint_elettorale` and
`minint_finloc`, which ISTAT does not publish and which cannot be derived.

Two things about that join are load-bearing:

- **The key is `com_catasto_code`, never the ISTAT code or the name.** The Sardinian reform
  of 1 January 2026 changed all 377 Sardinian `com_istat_code` values with zero overlap.
  Names both collide (Calliano in Asti and Trento, San Teodoro in Messina and Sassari) and
  change, so a name join fails silently.
- **`-proj wgs84` is required when converting the shapefiles.** The `_WGS84` in the ISTAT
  filenames names the datum; the `.prj` is `WGS_1984_UTM_Zone_32N` with `UNIT["Meter"]`.
  Without the reprojection the output carries metres.

`CATASTO_OVERRIDES` in `build_comuni.py` covers municipalities present in a boundary edition
but already suppressed in the spreadsheet — they are absent from the later edition because
they were merged away *after* the reference date. Any municipality that reaches the end of
the build without a cadastral code is reported and must be investigated, not defaulted.

Two deliberately asymmetric derivation paths:

- **GeoJSON** — `limits_IT_municipalities.geojson` is a plain `cp` of `comuni.geojson`
  (never passed through mapshaper, so it keeps the source's `crs` member and full vertex
  count). Provinces and regions come from `-dissolve prov_istat_code` / `reg_istat_code`
  with `copy-fields`, both dissolves targeting layer 1 (the municipalities) so regions are
  dissolved from municipalities, not from provinces. Regional/provincial subsets are
  `-filter` passes on the numeric code fields.
- **TopoJSON** — `-simplify 20% weighted` runs **first**, and provinces/regions are
  dissolved from the *already simplified* municipalities layer. This is the point of the
  ordering: shared borders stay topologically coincident across the three levels.
  `limits_IT_all.topo.json` packs all three layers in one file.

### Invariants not to "fix"

- **`gj2008` on every GeoJSON output.** Emits pre-RFC 7946 GeoJSON (winding order, `crs`)
  for D3 and everything built on it (Plotly). Dropping it silently breaks downstream
  D3 renderings — see mapshaper issue #432.
- **Blind loops over code ranges, with the bound derived from the data.** The scripts
  iterate regions `1..20` and provinces `1..MAX_PROV`, where `MAX_PROV` is computed
  from `comuni.geojson` at run time. Emitting a file for a code with no surviving
  province is *intentional*: consumers get a stable URL and an empty
  `GeometryCollection` instead of a 404, so don't add existence checks that stop
  emitting them. Do not hardcode the bound either — it was `111` until the 1 January
  2026 vintage renumbered the Sardinian provinces up to 119, at which point the
  literal would have silently dropped all of Sardinia. Vacant codes in that vintage:
  90, 91, 92, 95, 104–107, 111.
- **Filenames are not zero-padded** (`limits_P_58_municipalities.geojson`), while the
  `prov_istat_code` / `reg_istat_code` *properties* are (`"058"`). Both forms exist on
  purpose; `*_istat_code_num` is the integer used by `-filter`.
- Municipality-only properties (`op_id`, `opdm_id`, `minint_*`, `com_*`) propagate into all
  municipality-level outputs but are absent from the dissolved province/region files —
  only `copy-fields` survives a dissolve. **Any new
  property must be added to `copy-fields` in both generation scripts** or it silently
  fails to reach `limits_IT_provinces` and `limits_IT_regions`.
- **`prov_iso_3166_2` is null for five units, and that is correct.** ISO 3166-2:IT does not
  define a code for Valle d'Aosta (deleted 2019, the region exercises provincial functions)
  nor for the four Sardinian provinces created in 2026. The Sardinian four carry the plates
  OT, OG, VS and CI — codes ISO *deleted* in April 2019 — so filling the gap from
  `prov_acr` looks obvious and publishes withdrawn identifiers. `scripts/iso_3166_2.py`
  enumerates the valid set rather than deriving it, and its `UNCOVERED` table documents
  each gap. The tables are verified against the `iso-codes` package by
  `tests/test_iso_3166_2.py`, so an edit that invents a code fails the suite.

## Release cycle

Releases are tagged `year[.version]` (`2019`, `2021.1`, `2021.2`, `2022.1`, `2023.1`) and
represent an ISTAT data vintage, not a code change. A release means: replace
`comuni.geojson`, run both scripts, commit the regenerated tree, add a CHANGELOG entry
describing the administrative changes (merges/splits, province or region reassignments),
update the "limits as of <month year>" line in the README, then tag.

Data are ISTAT-derived and redistributed under CC-BY; keep the attribution section intact.
