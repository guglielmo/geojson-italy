# The temporal dataset

The administrative boundaries of Italy as ISTAT published them, from **21 October 2001**
onward, as one row per (municipality, validity period).

This is the archive's **source of truth**. The files at the repository root — `comuni.geojson`,
`geojson/`, `topojson/` — are derived from it for the current date, and every historical
snapshot is materialised from it as a release asset. Consumers who want a past date should
take the release for that date rather than read these files; see the README.

## Layout

```
temporal/
├── comuni/reg=NN.geojson   one file per region, features carrying a validity interval
├── INDEX.csv               validity interval -> release tag
└── SCHEMA.md               this file
```

GeoJSON rather than Parquet, deliberately: verifying this archive should require mapshaper,
already this project's only dependency, and not a database engine. Filtering a date out of it
is then a one-liner in a tool consumers already have.

```sh
mapshaper -i temporal/comuni/reg=12.geojson \
  -filter 'valid_from <= "2021-09-10" && (!valid_to || valid_to > "2021-09-10")' \
  -o out.geojson
```

Split by region so that a release touching one region rewrites one file and git stores a
delta. **A municipality reassigned across regions appears in both files**, each version filed
under the region it belonged to at the time: Montecopiolo and Sassofeltrio left the Marche
for Emilia-Romagna on 17 June 2021, so their earlier versions are in `reg=11` and their later
ones in `reg=08`.

## Identity and validity

| Field | Type | Notes |
| --- | --- | --- |
| `terr_key` | string | The entity's **first cadastral (Belfiore) code**, and the key this design turns on. |
| `valid_from` | date | Start of this version's validity. |
| `valid_to` | date or null | End, **exclusive**. Null means still current. |
| `version_reason` | enum | Why this version exists — see below. |
| `source_edition` | string | The ISTAT file the geometry came from. |

**Why not the ISTAT code.** It embeds the province, so it changes whenever a municipality is
reassigned. The Sardinian reform of 1 January 2026 changed all 377 Sardinian
`com_istat_code` values with zero overlap; no dataset keyed on that code can express
continuity across it. The cadastral code is assigned by the Agenzia delle Entrate and
republished by ISTAT, so it is public and checkable — unlike an internal row id, which
renumbers whenever its database is rebuilt.

Measured across the 26 published rosters: 8,231 codes appear, exactly one municipality ever
changed its own (Lonato, `E667` until its renaming to Lonato del Garda in 2007, `M312`
after), and no code has ever been held by two entities. Hence `terr_key` is the **first**
code and never changes, while `com_catasto_code` stays a time-scoped attribute; for every
municipality but Lonato del Garda the two coincide at every date.

**Gaps are meaningful.** Consecutive versions of one entity meet exactly — each `valid_to`
equals the next `valid_from` — except where the entity did not exist. Baranzate was
constituted on 12 December 2001, extinguished on 6 March 2003 when the Constitutional Court
struck down the regional law that created it, and constituted again on 8 June 2004. Its
interval has a hole, and bridging it would publish a municipality that had been abolished.

### `version_reason`

| Value | Meaning |
| --- | --- |
| `initial` | First version of a municipality that already existed when the series begins. |
| `admin_fusione` | Created by a merger, or reshaped by absorbing another municipality. |
| `admin_scissione` | Created by detachment from a municipality that survives. |
| `admin_cambio_codice` | The ISTAT code changed, boundary and name unchanged. |
| `admin_cambio_denominazione` | Renamed, with no other change. |
| `admin_riassegnazione` | Moved to a different province or region. |
| `admin_variazione_territoriale` | Boundary moved by a transfer of territory between municipalities. |
| `source_regeneralization` | ISTAT republished the geometry with different vertices; no administrative change. |

The last value is a **residual**: it is assigned only where no administrative event accounts
for the version. A merger falling in a year ISTAT re-generalised is a merger.

Two of these values are additions to the design's original six. `admin_cambio_denominazione`
exists because 50 records since 1991 rename a municipality without touching its code, and
reporting those as a code change would be false. `admin_variazione_territoriale` exists
because a transfer of territory is an act of parliament or of a regional council, and
attributing it to ISTAT redrawing its own lines would destroy exactly the distinction this
field is for.

`version_reason` is what makes the archive interpretable. ISTAT re-generalises its geometries
in some editions and not others — 2002, 2010, 2011, 2012, 2019, 2022 and 2025 — so a consumer
diffing two adjacent years without this field sees roughly 7,900 changed boundaries and
concludes something historic happened.

### `source_edition`

Names the ISTAT file the geometry was read from, e.g. `Limiti01012012_g`. This is what makes
fidelity to the source a checkable property rather than a claim: download the named file and
compare. Checksums for every edition are in `build/editions/MANIFEST.json`.

Two suffixes mark the cases where ISTAT had not yet drawn the municipality — it publishes
boundaries only at 1 January, so one created during the year has none until the next edition.
39 municipalities across 42 dates are in this position:

| Suffix | Rule |
| --- | --- |
| `(union of predecessors)` | Created by merger: the boundary is its predecessors' geometries in the applicable edition, dissolved. Arithmetic on published data — the same operation used to derive provinces from municipalities. |
| `(anticipated)` | Created by detachment: the boundary is its own, from the next edition that carries it. It cannot be derived from its predecessor, which survives with a reduced area. |

Which rule applies is read from ISTAT's variation records — predecessors extinguished means a
merger, a predecessor ceding territory and surviving means a detachment — and a case matching
neither fails the build rather than being guessed.

## Attributes at that date

Every attribute is as ISTAT published it **for that date**, from the roster (SITUAS report
61), not as it stands today.

| Field | Notes |
| --- | --- |
| `name` | Italian name; bilingual municipalities carry ISTAT's own form. |
| `com_istat_code`, `com_istat_code_num` | Zero-padded string and integer. |
| `com_catasto_code` | Cadastral code **at that date** — see `terr_key` above. |
| `prov_istat_code`, `prov_istat_code_num` | The `COD_PROV` family: Rome is `058`, not `258`. |
| `prov_name`, `prov_acr` | |
| `prov_uts_code` | The `COD_UTS` family, which differs for metropolitan cities: 312 Sassari, 318 Cagliari against `COD_PROV` 112 and 118. Both are carried because ISTAT's own products disagree on which to show. |
| `prov_tipo_uts` | Provincia, Provincia autonoma, Città metropolitana, Libero consorzio di comuni, Unità non amministrativa. |
| `reg_istat_code`, `reg_istat_code_num`, `reg_name` | |
| `com_nuts3` | NUTS 3 code, absent before 2006 and stated in the vintage current at the date. |

### Identifiers that are not ISTAT's

| Field | |
| --- | --- |
| `op_id`, `opdm_id` | openpolis identifiers |
| `minint_elettorale`, `minint_finloc` | interior ministry identifiers |

**No ISTAT source holds these**, so they cannot be reconstructed for past dates. They are
carried across from the current vintage by joining on the cadastral key, which is stable
across reassignment — so a municipality that still exists carries them at every date it
existed, and **a municipality suppressed before the current vintage has them null**. That
distinction is a property of the archive, not an omission.

Two consequences worth stating rather than leaving to be discovered:

- **337 entities are extinct** and carry none of the four. Three exceptions are extinct in
  the archive yet present here: Lirio, Castegnero and Nanto were suppressed *after* the
  1 January 2026 vintage, so the current file still holds them.
- **53 municipalities that still exist have no `op_id` in the current vintage either**, and
  the archive inherits that gap faithfully rather than papering over it. They are the recent
  mergers — Val di Chy, Valchiusa, Alto Sermenza, Cassano Spinola and the rest — which were
  created after the openpolis identifiers were last assigned. `opdm_id` is missing for 7 and
  `minint_elettorale` for 35, so the four fields are not missing together.

## Geometry

MultiPolygon or Polygon, EPSG:4326 (WGS84), at the source's own resolution. No simplification,
no smoothing, no tolerance-based deduplication: if ISTAT published a straightened segment in a
given edition, the archive publishes it straightened.

Versions are collapsed only on **exact equality**. Where ISTAT republishes a geometry
byte-identically across editions, those editions are one validity interval; where it differs
by a single vertex, they are two. This discards repetitions of published geometry and never a
published geometry.

## What is checked

`python -m scripts.validate_temporal`, run against the built dataset:

- **interval integrity** — no overlaps, every interval closing where the next opens;
- **counts against the roster** — at each of the 98 publication dates the archive holds
  exactly as many municipalities as ISTAT's own roster does for that date;
- **continuity across the Sardinian reform** — all 377 municipalities resolve to the same
  `terr_key` before and after 1 January 2026.

## Rebuilding it

Everything comes from ISTAT and needs no credentials:

```sh
python -m scripts.fetch_editions                  # 26 boundary editions
python -m scripts.fetch_situas variations         # the variation reports
python -m scripts.fetch_situas rosters            # the roster at each of the 98 dates
python -m scripts.build_temporal build
python -m scripts.validate_temporal
```
