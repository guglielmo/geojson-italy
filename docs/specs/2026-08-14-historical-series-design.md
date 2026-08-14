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

Everything comes from ISTAT, by two routes. The **edition archives** publish the geometry
for each reference date. The **SITUAS variation reports** publish the history of which
entity is which across mergers, splits and recodings — which cannot be derived from
shapefiles at all, and which ISTAT records with effective dates and enacting acts. Both are
public and need no credentials; see D9.

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

**D4 — The temporal dataset is tracked in git**, rather than living only in release assets
or being regenerated on demand. Anyone must be able to reconstruct any snapshot without
credentials. An archive that only its maintainer can rebuild is an archive that has to be
taken on trust, which defeats the point of publishing boundaries as a common good.

Since D9 was revised, this holds twice over: the tracked dataset is rebuildable from public
sources end to end, so the guarantee is a property of the pipeline and not only of the
committed files.

**D5 — Depth 2001–2026.** Cost measurements (§3) show depth is not a constraint, so the
series is not truncated for size.

> **Revised 14 August 2026.** This decision read "2001–2025, the full extent of ISTAT's
> published coverage". That was the extent of the *derived* source's coverage, not ISTAT's.
> Measured since:
>
> - **Geometry** resolves for every year 2002–2026, plus census editions for 1991, 2001 and
>   2011 — so 1991 is reachable, and the annual series has no gaps (§3).
> - **Identity** goes back further still: the variation reports start in 1861, 1862, 1865
>   and 1868 depending on the report.
>
> The binding constraint is therefore geometry at 1991, not identity at 2001. Depth stays at
> 2001 for this milestone because that is what the measurements in §3 cost out; extending to
> 1991 is a decision about scope, no longer about availability.

**D6 — The repository root stays exactly as it is.** `geojson/`, `topojson/` and
`comuni.geojson` keep their paths, names and contents for the current vintage. Third parties
pin these URLs; nothing about this work may break them.

## 3. Measurements behind the decisions

All figures measured, not estimated.

| Quantity | Value |
| --- | --- |
| Municipality geometry versions in the identity source | 74,580 across 25 editions (2001–2025) |
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
2022 and 2025 — and in the intervening years republishes them byte-identically, so only
administratively affected municipalities differ. Reading all 26 editions and merging
consecutive identical geometries into one validity interval is therefore lossless: it discards
no published geometry, only repetitions of it. It does not offend D2, which forbids
altering published geometry, not storing it once.

> **Measured, August 2026** — see
> [2026-08-14-edition-measurements.md](2026-08-14-edition-measurements.md). Reading the
> editions directly gives **208,572 instances collapsing to 68,428 versions (3.05×)**,
> against the ~205,000 → ~74,600 estimated here from the identity source. **2021 is not a
> re-generalising edition**: it appeared to be one only because that source had ingested the
> census product in place of the annual edition, and that single artefact accounts for most of the ~6,000
> version difference. 2020 → 2021 changes 4.7% of geometries, an ordinary year.

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
    ├── fetch_editions.py       ISTAT edition archives -> build/editions/
    ├── fetch_variations.py     SITUAS variation reports -> build/situas/
    ├── identity.py             identity rules (key, validity, no silent repair)
    ├── build_temporal.py       editions + variations -> temporal dataset
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
| `terr_key` | string | Stable public identity: the entity's **first cadastral (Belfiore) code**. |
| `valid_from` | date | Start of this version's validity. |
| `valid_to` | date | End, exclusive. Null means current. |
| `version_reason` | enum | Why this version exists — see below. |
| `source_edition` | string | ISTAT file the geometry came from, e.g. `Limiti01012012_g`. |

`terr_key` is the field this whole design turns on. The Sardinian reform of 1 January 2026
changed all 377 Sardinian `com_istat_code` values with zero overlap, because the municipal
code embeds the province code. A dataset keyed on the ISTAT code cannot express continuity
across that event; a dataset keyed on a stable identity can, and the ISTAT code becomes what
it actually is — a time-scoped attribute.

> **Revised 14 August 2026.** This field was first specified as an integer surrogate taken
> from the identity source. That was wrong: the column is a database sequence assigned at
> import time, so it renumbers whenever the source is rebuilt and no third party can verify
> it. Keying a public archive on it would contradict D4.
>
> The cadastral code is public — assigned by the Agenzia delle Entrate and republished in
> ISTAT's `Elenco-comuni-italiani` — and it behaves as a key: measured across the identity
> source, **8,229 of 8,230 municipalities carry exactly one for their whole life, and no code
> has ever been used by two entities**. The single exception is **Lonato del Garda**, `E667`
> until 2008 and `M312` after.
>
> Hence: `terr_key` is the entity's **first** cadastral code and never changes, while
> `com_catasto_code` stays a time-scoped attribute. For every municipality but Lonato del
> Garda the two coincide at every date. No internal surrogate is published.

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
re-generalises in some editions and not others — measured against the annual editions:
2002, 2010, 2011, 2012, 2019, 2022 and 2025 show a full set of changed geometries, while
intervening years change only administratively affected municipalities. A consumer diffing 2011 against 2012 without
this field sees roughly 7,900 changed boundaries and concludes something historic happened.
With it, they can filter to the handful that actually changed.

Populated from the SITUAS variation records: `ES`/`AQES` give mergers, `CS`/`CECS` give
constitutions and detachments, `CD` gives renames, `RN` code renumbering and `AP` provincial
reassignment — each with its effective date and enacting act. The `admin_*` values are read from those sources
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
| `prov_tipo_uts` | ISTAT edition, `TIPO_UTS` | Enables the metropolitan-city layer, which does not exist today. In the 2026 edition: Provincia (83), Città metropolitana (15), Libero consorzio di comuni (6), Unità non amministrativa (4), Provincia autonoma (2). |
| `prov_uts_code` | ISTAT edition, `COD_UTS` | The `COD_UTS` family — 312 Sassari, 318 Cagliari — distinct from `COD_PROV` 112 and 118. ISTAT's own products disagree on which to show, and SITUAS reports the 2026 reform against `COD_UTS`; carrying both removes the ambiguity. |
| `reg_iso_3166_2`, `prov_iso_3166_2` | issue #22 | Standard identifiers, resolves #22 and supersedes #14. |

### Geometry

`geometry`, MultiPolygon, EPSG:4326, at source resolution.

## 6. Sourcing

**D9 — Geometry comes from ISTAT directly. The identity source is read-only, and supplies
only identity.**

> **Revised 14 August 2026.** D9 originally assumed the identity history could only come
> from a reconstruction maintained elsewhere. That assumption was wrong: ISTAT publishes the
> underlying variation records itself, anonymously, with coverage from 1861 against 1991 for
> the reconstruction. The reports and their layout are documented below; the reconstruction
> is no longer a dependency of this milestone.

Both layers come from ISTAT, by different routes:

| Layer | Source | Verified |
| --- | --- | --- |
| Geometry | The ISTAT edition zip for each reference date | 26 editions, 2001–2026, §3 |
| Identity, codes, validity, succession | The SITUAS variation reports | 4 reports, from 1861 |

### The SITUAS reports

Anonymous HTTP, `Accept: application/json`. The catalogue at
`situas.istat.it/ShibO2Module/api/Report/ReportByUrl` (POST `{"url":
"get_elenco_microservizi"}`) lists all 77 datasets with their exact download links —
read those rather than constructing URLs, because the parameter set differs per report.

| pfun | Report | Params | Records | From | Key |
| --- | --- | --- | --- | --- | --- |
| 129 | Municipal variations | `pdata` | 2,356 | 1991 | `COD_CATASTO` both sides |
| 98 | Suppressed municipalities | `pdatada`/`pdataa` | 3,618 | 1865 | `COD_CATASTO` both sides |
| 104 | Name changes | `pdatada`/`pdataa` | 2,765 | 1862 | **no cadastral code** |
| 105 | Statistical code changes | `pdatada`/`pdataa` | 4,761 | 1868 | **no cadastral code** |

Every record carries the effective date, the enacting act and the related unit.

The variation taxonomy in report 129 is closed, and **every record has a related code**:

| Code | Meaning | Records |
| --- | --- | --- |
| `AP` | Change of province | 964 |
| `ES` | Extinction | 348 |
| `CS` | Constitution | 342 |
| `RN` | Statistical code renumbering | 222 |
| `CE` / `AQ` | Territory ceded / acquired | 197 each |
| `CD` | Name change | 50 |
| `AQES` | Acquisition by extinction | 21 |
| `CECS` | Cession for constitution of a new unit | 15 |

Report 105 uses a narrower one: `AP` (4,220), `RN` (474), `RNAPUTS` (66), `CDAP` (1).

Reading `ES` and `CS` **together** is not optional. A municipality can be extinguished and
later re-established, and a reader that keeps only `ES` records loses the second event:
Baranzate was constituted 2001-12-12, genuinely extinguished 2003-03-06 when the
Constitutional Court struck down the regional law that created it (sentenza 47/2003), and
re-established 2004-06-08 by a new one. It is the only such sequence in the 2,356 records
since 1991, and it is present in every ISTAT boundary edition from 2004 onward — so an
archive that misses it contradicts its own geometry source.

**Reports 104 and 105 have no cadastral code**, so binding them to an entity means walking
the ISTAT code chain, which 105 itself provides as `PRO_COM_T → PRO_COM_T_REL`. Verified on
the hardest known case, Aggius: `090001 → 104001` (2006), `104001 → 090001` (2016),
`090001 → 113001` (2026) — the same chain the derived reconstruction held, from the public
source.

**Codes for metropolitan cities differ between the two layers.** SITUAS reports the 2026
Sardinian reform against `COD_UTS` **312** (Sassari) and **318** (Cagliari); the boundary
shapefiles use `COD_PROV` **112** and **118**. The municipality counts agree exactly — 66
and 70 — so the two are the same units under two code families. This repository publishes
the `COD_PROV` family; see the note in `STATUS.md`.

### Why not source identity through a derived reconstruction

A reconstruction of this history is maintained elsewhere, and the milestone was originally
designed around it. Reading ISTAT directly is better on three counts, and the third is the
decisive one:

1. **No coordination with another project**, and no waiting on another roadmap.
2. **D2 gets stronger.** Geometry never passes through an intermediate store, so
   `source_edition` names the file actually read and the round-trip check in §8 becomes close
   to tautological. Fidelity stops being a property of a pipeline and becomes a property of a
   download.
3. **Interpretation stays where it can be checked.** A reconstruction does not hold data
   ISTAT lacks — it holds a *reading* of these same variation records, and a reading can be
   wrong in ways its consumers cannot see. Reading the records here means an ambiguous
   classification can fail the build instead of being silently resolved, which is what this
   design asks for everywhere else.
4. **No inherited quirks.** A derived store carries artefacts of its own ingestion —
   the 2021 edition loaded from the census product rather than the annual one; and Misiliscemi
   given a geometry dated 2021-01-01, before it legally existed. Reading ISTAT directly avoids
   both without asking anyone to fix them.

   Measured since: of the 7,901 municipalities present in both 2021 editions, **not one has
   the same geometry** — but the typical discrepancy is 0.77% of area (median; 4.28% at the
   95th percentile, 38.88% at most), not the 3.5%–12% stated earlier. The substitution is
   universal and the two files are plainly different products; the magnitude was overstated.

ISTAT coverage is complete and verified: all 26 editions from 2001 to 2026 were downloaded
in August 2026, with checksums recorded in `build/editions/MANIFEST.json`. The
"2002–2010 unavailable" gap recorded in the identity source does not exist. For 2001 and
2011 only the census edition exists, so it is the source for those two years by necessity.

URL resolution lives in `scripts/istat_editions.py`, which knows the three shapes ISTAT
uses — `Limiti0101<YYYY>_g.zip`, the same nested under a year directory from 2022, and the
census form `Limiti<YYYY>_g.zip` — and always prefers the annual edition where both exist.

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

These four also expose a gap in the succession graph: it holds no `split_into`
relationship for any of them, so they cannot be distinguished from unrelated new entities
programmatically. Hence the explicit list.

**Any further case** must fail the build rather than be guessed. A silent fallback here would
reproduce exactly the failure mode this design exists to avoid.

### Metadata that cannot be reconstructed

The identity source holds no `op_id`, `opdm_id`, `minint_elettorale` or `minint_finloc`.
Its identifier schemes are `istat`, `catasto`, `fiscale`, `uts`, `nuts` and
`sigla_automobilistica`.

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
3. **Interval integrity.** No overlapping validity periods for the same `terr_key`; no gaps
   between consecutive versions; every `valid_to` matching the next `valid_from`.
4. **Derivation equivalence.** Provinces and regions dissolved from the historical
   municipality layer must reproduce the province and region counts ISTAT published for that
   date.
5. **Continuity across the Sardinian reform.** Every one of the 377 municipalities must
   resolve to the same `terr_key` before and after 1 January 2026, with `version_reason` set
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
- Depth stops at 2001. ISTAT publishes census boundaries for 1991, and the identity source's
  variation data starts 1991-12-10, so the series can be extended backwards later without
  schema change.
- The four openpolis and interior-ministry identifiers are absent for extinct municipalities
  (§6).

## 10. Out of scope

- Sub-municipal boundaries (issues #11, #13): different dataset, tracked separately.
- Postal code boundaries (issue #21): declined on licensing grounds.
- Republishing the archive as an npm package or contributing it to `world-geojson`: the
  interoperability track is separate and follows the `2026.1` release.
