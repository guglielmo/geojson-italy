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
./generate_geojson.sh    # comuni.geojson -> geojson/*.geojson   (unsimplified)
./generate_topojson.sh   # comuni.geojson -> topojson/*.topo.json (20% simplified)
```

There is no build system, no test suite, no linter. The only requirement is the global
`mapshaper` CLI (node); the scripts are written against version `0.6.65`, so check
`mapshaper --version` before assuming flag behaviour matches.

`encoding=utf8` must stay immediately after the input filename on `-i`, *before* `-clean`.
Placed after `-clean` it is parsed as an option of that command instead and the encoding is
not applied — that was the fix in PR #20. Accented municipality names are the thing at
stake here.

Each script runs ~131 mapshaper invocations, every one re-reading and re-`clean`ing the
full 38 MB source, so a full regeneration takes minutes. To iterate on a single output,
run the matching mapshaper command by hand rather than the whole loop.

## Pipeline architecture

`comuni.geojson` (38 MB, tracked, EPSG:4326/WGS84) is the **single source of truth** and
is *not* produced by anything in this repo — it is built externally from ISTAT shapefiles
enriched with openpolis/OPDM identifiers, per the
[wiki](https://github.com/guglielmo/geojson-italy/wiki/How-to-generate-the-limits-files).
An update cycle therefore starts by replacing that file, not by editing the scripts.

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
- **Blind loops over code ranges — but the upper bound is currently wrong.** The scripts
  iterate regions `1..20` and provinces `1..111`. Emitting a file for a code with no
  surviving province is *intentional*: consumers get a stable URL and an empty
  `GeometryCollection` instead of a 404, so don't add existence checks that stop emitting
  them. The bound itself is a different matter — the ISTAT vintage of 1 January 2026
  renumbered the Sardinian provinces up to code **119**, so `seq 1 111` would silently drop
  all of Sardinia. Raise it to `119` (or derive it from the data) as part of adopting that
  vintage; see `STATUS.md`. Vacant codes as of that vintage: 90, 91, 92, 95, 104–107, 111.
- **Filenames are not zero-padded** (`limits_P_58_municipalities.geojson`), while the
  `prov_istat_code` / `reg_istat_code` *properties* are (`"058"`). Both forms exist on
  purpose; `*_istat_code_num` is the integer used by `-filter`.
- Municipality features carry `minint_finloc` in addition to the properties documented in
  the README; it propagates into all municipality-level outputs but is absent from the
  dissolved province/region files (only `copy-fields` survives a dissolve).

## Release cycle

Releases are tagged `year[.version]` (`2019`, `2021.1`, `2021.2`, `2022.1`, `2023.1`) and
represent an ISTAT data vintage, not a code change. A release means: replace
`comuni.geojson`, run both scripts, commit the regenerated tree, add a CHANGELOG entry
describing the administrative changes (merges/splits, province or region reassignments),
update the "limits as of <month year>" line in the README, then tag.

Data are ISTAT-derived and redistributed under CC-BY; keep the attribution section intact.
