# Historical series of Italian administrative boundaries — design

Status: approved, not yet implemented
Date: 2026-08-14
Milestone: `historical-series` (follows `2026.1`)

## 1. Goal

Turn this repository from a single current snapshot with release tags into a genuine
historical series: the administrative boundaries of Italy as they stood at any date from
2001 onward, faithful to what ISTAT published for that date.

The repository was originally intended to serve boundaries at different points in time,
with git tags as the mechanism. That mechanism does not scale — see §3 — and no tag exists
for anything before 2019, so the archive has to be built rather than accumulated.

Two sources, each for what only it can provide: ISTAT publishes the geometry for every
reference date, and the territorial reconstruction built for the MAPS project
(`gst-maps-pipelines`) holds the date-framed identity history — which entity is which across
mergers, splits and recodings — which cannot be derived from shapefiles. MAPS is read
only; see D9.

## 2. Decisions

Each decision is numbered so issues can reference it.

**D1 — The product is snapshots per date.** A consumer asks for the boundaries valid on a
given date and gets the same kind of files this repository already publishes. The identity
graph is a derived secondary output, not the product.

**D2 — Fidelity to the source, without normalisation.** If ISTAT published a straightened
boundary segment in a given edition, the archive publishes that segment straightened. If the
same segment has more vertices two editions later, the archive publishes both. No smoothing,
no tolerance-based deduplication, no reconciliation across editions.

The rationale is that this is a public dataset whose value is provenance. A normalised
archive is the maintainer's interpretation carrying ISTAT's authority, and it cannot be
falsified by a third party. A noisy archive that reproduces the source can.

**D3 — Full resolution in the archive only for the national municipality file.** Historical
dates get `comuni.geojson` at source resolution plus the simplified topojson. The 131
per-region and per-province files are produced only for the current vintage. Provinces,
regions and metropolitan cities must remain derivable from the municipality layer for any
date — which they are, by dissolve, exactly as today.

**D4 — The temporal dataset is tracked in git** (as opposed to living only in release assets
or only in the MAPS database). Anyone must be able to reconstruct any snapshot without
credentials to a private database. An archive that only its maintainer can rebuild is an
archive that has to be taken on trust, which defeats the point of publishing boundaries as
a common good.

**D5 — Depth 2001–2025 initially**, extended to 2026 with the `2026.1` release. This is the
full extent of ISTAT's published coverage of administrative boundaries. Cost measurements
(§3) show depth is not a constraint, so there is no reason to truncate the series.

**D6 — The repository root stays exactly as it is.** `geojson/`, `topojson/` and
`comuni.geojson` keep their paths, names and contents for the current vintage. Third parties
pin these URLs; nothing about this work may break them.

## 3. Measurements behind the decisions

All figures measured, not estimated.

| Quantity | Value |
| --- | --- |
| Municipality geometry versions in MAPS | 74,580 across 25 editions (2001–2025) |
| Same, serialised as GeoJSON geometry | 209 MB |
| One edition | ~22 MB geometry, ~30 MB as complete GeoJSON |
| Same as region-split GeoJSON with properties | ~280 MB working tree, ~80–90 MB in git history |
| Current repository working tree, one vintage | 170 MB |
| Current `.git` | 351 MB (five tagged vintages, ~70 MB each) |
| Distinct change dates, 2001 onward | **58** — 26 on 1 January, **32 intra-year** |
| Published archive as release assets | 58 dates × ~10 MB gzipped ≈ 600 MB, outside repository size |

Why the tag mechanism fails: one vintage costs 170 MB of working tree, so 26 tagged vintages
would be ~4.3 GB of tree and ~1.8 GB of history, against GitHub's 1 GB guidance. The
interval-based dataset holds the same information in 209 MB because it stores one row per
*period*, not per year.

Two kinds of deduplication must be kept apart, because one is essential and the other is
forbidden.

**Exact-equality interval collapsing is used, and is what makes the archive affordable.**
ISTAT re-generalises its geometries only in some editions — 2002, 2010, 2011, 2012, 2019,
2021, 2022 and 2025 — and in the intervening years republishes them byte-identically, so only
administratively affected municipalities differ. Reading all 26 editions and merging
consecutive identical geometries into one validity interval is therefore lossless: it discards
no published geometry, only repetitions of it. This is what reduces roughly 205,000
edition-instances to about 74,600 versions and 209 MB. It does not offend D2, which forbids
altering published geometry, not storing it once.

**Tolerance-based deduplication is excluded by D2.** It would collapse far more — 224 of 250
sampled municipalities differ by less than 0.01% of area between the 2011 and 2012 editions,
a difference invisible on a map — but doing so would mean publishing one edition's geometry
under another edition's date. Residual exact duplication after interval collapsing is only
1.11×, so nothing further is available without crossing that line.

## 4. Architecture

```
geojson-italy/
├── comuni.geojson              generated from temporal/ for the current date
├── geojson/                    unchanged, generated as today
├── topojson/                   unchanged, generated as today
├── temporal/
│   ├── comuni/reg=NN.geojson   source of truth, one file per region
│   ├── INDEX.csv               validity interval -> release tag
│   └── SCHEMA.md
└── scripts/
    ├── build_temporal.py       MAPS -> temporal dataset
    └── materialize.py          temporal dataset + date -> release assets
```

**D7 — The source of truth is GeoJSON, not Parquet.** Parquet is the better format on every
technical axis: 60–90 MB against ~280 MB, and directly queryable with DuckDB. It is rejected
anyway, because the truth of a public boundary archive should be openable with the same tools
as its products. A third party verifying the archive should need mapshaper — already this
project's only dependency — and not a database engine. Filtering a date out of the source is
then a one-liner in a tool consumers already have:

```sh
mapshaper -i temporal/comuni/reg=12.geojson \
  -filter 'valid_from <= "2021-09-10" && (!valid_to || valid_to > "2021-09-10")' \
  -o out.geojson
```

Splitting by region keeps each file in the tens of megabytes and means a release touching one
region rewrites one file. Git compresses the series to roughly 80–90 MB of history, comparable
to what Parquet would occupy on disk.

The central inversion: today `comuni.geojson` **is** the source and the 134 published files
derive from it. After this work the source is `temporal/`, and `comuni.geojson` becomes the
first derived product. The existing `generate_geojson.sh` and `generate_topojson.sh` chain
continues unchanged downstream of it.

Splitting by region is what keeps git viable. A single 280 MB file would be rewritten in full
on every release, adding its whole weight to history each time; split, a release touching only
Sardinia rewrites `reg=20.geojson` alone and git stores a delta of the changed region. It also
keeps each file small enough to open in an editor or a browser, which a single national file of
that size is not.

### How snapshots reach consumers

**D8 — Consumers download files. They never run code.** This repository is used by people
who pin a URL in an R or Python script and have no build step, no interpreter version and no
dependency on this project's tooling. Any design in which obtaining a past date requires
executing something is a different product for a different audience.

The consequence is that every published date is **pre-materialised**, and the source dataset
is never the consumer interface.

1. **The current date** stays at the repository root, at its existing URLs (D6). Most
   consumers need nothing else.
2. **Every change date** — all 58 of them from 2001 onward, not only 1 January — is published
   as assets on a GitHub Release tagged with that date. Release assets do not count towards
   repository size and are served over a CDN with stable URLs, which is what makes publishing
   the complete series affordable.
3. **An index** at `temporal/INDEX.csv` maps each validity interval to its release tag, so
   finding the right file for an arbitrary date is a lookup, not a computation.

`scripts/materialize.py` is a **maintainer** tool: it produces the assets in step 2. It is not
the path a consumer takes.

Publishing at every change date rather than every 1 January is not a refinement, it is a
correctness requirement. Of the 58 change dates, **32 fall inside the year**: a consumer who
needs 2021-09-10 is served by neither the 2021-01-01 nor the 2022-01-01 edition, because
changes took effect on 2021-02-20 and 2021-06-17. An annual series silently returns the wrong
answer for those dates, which is worse than not serving them.

Historical assets are published gzipped (`.geojson.gz`, roughly 10 MB against 43 MB), which
every common tool reads directly. The current vintage at the root stays uncompressed, as
today.

The existing tags (`2019`, `2021.1`, `2021.2`, `2022.1`, `2023.1`) are kept untouched. They
record what this repository actually published at those moments, which is a different fact
from what ISTAT published for those reference dates, and both are worth keeping. New release
tags use the ISO date form (`2021-06-17`) and cannot collide with them.

Resolving a date is an interval filter, not a search for the nearest snapshot:

```sql
WHERE valid_from <= :date AND (valid_to IS NULL OR valid_to > :date)
```

This is exact where annual snapshots are not: it represents intra-year changes, such as the
Moransengo-Tonengo recoding effective 2023-05-15 (issue #18), which a 1 January series
cannot express.

## 5. Schema of the temporal dataset

One row per (territory, validity period). Municipalities only; provinces, regions and
metropolitan cities are derived by dissolve.

### Identity and validity

| Field | Type | Notes |
| --- | --- | --- |
| `terr_id` | int | Stable surrogate identity, from MAPS `territories.id`. Survives every recoding. |
| `valid_from` | date | Start of this version's validity. |
| `valid_to` | date | End, exclusive. Null means current. |
| `version_reason` | enum | Why this version exists — see below. |
| `source_edition` | string | ISTAT file the geometry came from, e.g. `Limiti01012012_g`. |

`terr_id` is the field this whole design turns on. The Sardinian reform of 1 January 2026
changed all 377 Sardinian `com_istat_code` values with zero overlap, because the municipal
code embeds the province code. A dataset keyed on the ISTAT code cannot express continuity
across that event; a dataset keyed on a surrogate can, and the ISTAT code becomes what it
actually is — a time-scoped attribute.

`source_edition` is what makes D2 checkable. A third party can download the named ISTAT file
and verify the geometry byte for byte. Without it, fidelity to the source is a claim rather
than a property.

### `version_reason`

Distinguishes administrative change from source re-generalisation:

| Value | Meaning |
| --- | --- |
| `initial` | First known version of this territory. |
| `admin_fusione` | Created or ended by a merger. |
| `admin_scissione` | Created or ended by a split. |
| `admin_cambio_codice` | ISTAT code changed, boundary unchanged. |
| `admin_riassegnazione` | Moved to a different province or region. |
| `source_regeneralization` | ISTAT republished the geometry with different vertices; no administrative change. |

This field exists because without it the archive is faithful but uninterpretable. ISTAT
re-generalises in some editions and not others — measured: 2002, 2010, 2011, 2012, 2019,
2021, 2022 and 2025 show a full set of changed geometries, while intervening years change
only administratively affected municipalities. A consumer diffing 2011 against 2012 without
this field sees roughly 7,900 changed boundaries and concludes something historic happened.
With it, they can filter to the handful that actually changed.

Populated from MAPS `territory_relationships` (338 succession rows), `territories.end_reason`
and the dated `istat` identifier series. The `admin_*` values are read from those sources
directly. `source_regeneralization` is the residual: a version whose geometry differs from its
predecessor while no administrative event coincides with its `valid_from`. It is therefore
derived by elimination and must never be assigned where an administrative cause exists — a
merger that also happens to fall in a re-generalisation year is `admin_fusione`.

### Attributes at that date

Carried through from the current metadata, all date-framed:
`name`, `com_istat_code`, `com_istat_code_num`, `com_catasto_code`,
`prov_istat_code`, `prov_istat_code_num`, `prov_name`, `prov_acr`,
`reg_istat_code`, `reg_istat_code_num`, `reg_name`.

New fields:

| Field | Source | Why |
| --- | --- | --- |
| `prov_tipo_uts` | MAPS `territories.subtype` | Enables the metropolitan-city layer, which does not exist today. Values present: Provincia (91), Città metropolitana (16), Libero consorzio di comuni (6), Provincia autonoma (2), Unità non amministrativa (4). |
| `prov_uts_code` | MAPS `uts` identifier scheme | The `COD_UTS` code family — 312 Sassari, 318 Cagliari — distinct from `COD_PROV` 112 and 118. ISTAT's own products disagree on which to show; carrying both removes the ambiguity. |
| `reg_iso_3166_2`, `prov_iso_3166_2` | issue #22 | Standard identifiers, resolves #22 and supersedes #14. |

### Geometry

`geometry`, MultiPolygon, EPSG:4326, at source resolution.

## 6. Sourcing

**D9 — Geometry comes from ISTAT directly. MAPS is read-only, and supplies only identity.**

| Layer | Source |
| --- | --- |
| Geometry | The ISTAT edition zip for each reference date, downloaded and read by this project |
| Identity, codes, validity intervals, succession | MAPS `silver.territor*`, read-only |

The split follows what each source is uniquely good at. ISTAT publishes the geometry and is
its only authority. MAPS holds something that cannot be derived from shapefiles at all: the
reconstructed history of which entity is which across mergers, splits and recodings, with
effective dates. Neither substitutes for the other.

Three reasons this is better than sourcing geometry through MAPS:

1. **No coordination with another project.** Nothing in `gst-maps-pipelines` has to change, and
   this milestone does not wait on another roadmap.
2. **D2 gets stronger.** Geometry never passes through an intermediate store, so
   `source_edition` names the file actually read and the round-trip check in §8 becomes close
   to tautological. Fidelity stops being a property of a pipeline and becomes a property of a
   download.
3. **No inherited quirks.** The MAPS geometry table carries artefacts of its own ingestion —
   the 2021 edition loaded from the census product rather than the annual one, which fabricates
   a 3.5% to 12% discontinuity across every municipality; and Misiliscemi given a geometry
   dated 2021-01-01, before it legally existed. Reading ISTAT directly avoids both without
   asking anyone to fix them.

ISTAT coverage is complete and verified: annual editions resolve for every year from 2001 to
2026. The "2002–2010 unavailable" gap recorded in the MAPS ingestion code does not exist —
`Limiti01012003_g.zip`, `…2005…`, `…2007…` and `…2009…` all return 11.7–12.5 MB. For 2001 and
2011 only the census edition exists, so it is the source for those two years by necessity.

One discontinuity is **kept, not fixed**: between the 2022 and 2025 editions ISTAT genuinely
reduced detail (annual file 11.9 MB in 2022 against 10.4 MB in 2025 and 2026). Under D2 this
is the source's own behaviour, flagged `source_regeneralization`.

### Municipalities that exist before their geometry does

ISTAT publishes boundaries only at 1 January, so a municipality created during the year is
absent from the edition covering its first months. There are 39 such municipalities since 2001,
across 23 dates. The rule has three branches, and every result records how it was obtained.

**Created by merger — 35 cases.** Geometry is the union of its predecessors' geometries from
the applicable edition. This is arithmetic on published data, not reconciliation, so it does
not offend D2 — it is the same operation ISTAT itself uses to aggregate provinces from
municipalities. Recorded as `source_edition = "<edition> (union of predecessors)"`.

**Created by detachment — 4 cases**, named exhaustively because they need individual handling:
Fonte Nuova (2001-10-15), Baranzate (2001-12-12), Mappano (2017-04-18) and Misiliscemi
(2021-02-20). A detached municipality's boundary cannot be derived from its predecessor, which
continues to exist with a reduced area. Geometry is taken from the next edition in which the
municipality appears, recorded as `source_edition = "<later edition> (anticipated)"`.

These four also expose a gap in the MAPS succession graph: it holds no `split_into`
relationship for any of them, so they cannot be distinguished from unrelated new entities
programmatically. Hence the explicit list.

**Any further case** must fail the build rather than be guessed. A silent fallback here would
reproduce exactly the failure mode this design exists to avoid.

### Metadata that cannot be reconstructed

MAPS holds no `op_id`, `opdm_id`, `minint_elettorale` or `minint_finloc`. Its identifier
schemes are `istat`, `catasto`, `fiscale`, `uts`, `nuts` and `sigla_automobilistica`.

Mitigation: for any historical municipality that still exists today, backfill these four
fields by joining on `com_catasto_code`, which the current `comuni.geojson` carries and which
is stable across reassignment. Municipalities suppressed before the current vintage keep them
null. Document this in the schema rather than leaving consumers to discover it — the fields
are present for most of the series and absent for extinct entities.

## 7. Backward compatibility

The current vintage at the repository root is byte-comparable to what is published today,
with two intended additions: the new fields in §5. Existing consumers see additional
properties, which is additive and safe.

The generation of the root files moves from manual to derived, which is also the structural
cure for the defects found in the 2026.1 work: a hardcoded province loop bound cannot silently
drop Sardinia if the range comes from the data.

## 8. Validation

The archive is only credible if its fidelity claim is mechanically checked.

1. **Round-trip against the source.** For each edition, materialise the snapshot and compare
   it against the ISTAT file named in `source_edition`. The comparison is vertex-for-vertex
   after reprojection, not byte-for-byte: the source is a shapefile in a projected CRS and the
   output is GeoJSON in EPSG:4326, so coordinate serialisation necessarily differs. What must
   hold is that no vertex is added, removed or moved beyond reprojection tolerance. This is
   the test that gives `source_edition` its meaning.
2. **Municipality counts** per date reconciled against ISTAT's `Elenco-comuni-italiani`.
3. **Interval integrity.** No overlapping validity periods for the same `terr_id`; no gaps
   between consecutive versions; every `valid_to` matching the next `valid_from`.
4. **Derivation equivalence.** Provinces and regions dissolved from the historical
   municipality layer must reproduce the province and region counts ISTAT published for that
   date.
5. **Continuity across the Sardinian reform.** Every one of the 377 municipalities must
   resolve to the same `terr_id` before and after 1 January 2026, with `version_reason` set
   to `admin_cambio_codice` or `admin_riassegnazione`. This is the regression test for the
   whole design.

## 9. Known limitations

- Geometry differs between editions for reasons that are not administrative. This is
  deliberate under D2 and is what `version_reason` exists to explain.
- ISTAT publishes boundaries only at 1 January, so intra-year events are not evenly served.
  A change of code or of provincial assignment — the common case — is represented exactly,
  because it does not move a boundary. A boundary change to an existing municipality carries
  the preceding edition's geometry until the next edition. A municipality created during the
  year is handled by the three-branch rule in §6.
- Depth stops at 2001. ISTAT publishes census boundaries for 1991, and MAPS variation data
  starts 1991-12-10, so the series can be extended backwards later without schema change.
- The four openpolis and interior-ministry identifiers are absent for extinct municipalities
  (§6).

## 10. Out of scope

- Sub-municipal boundaries (issues #11, #13): different dataset, tracked separately.
- Postal code boundaries (issue #21): declined on licensing grounds.
- Republishing the archive as an npm package or contributing it to `world-geojson`: the
  interoperability track is separate and follows the `2026.1` release.
