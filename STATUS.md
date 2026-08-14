# Project status

Maintenance status and work plan for this repository. Updated as work progresses.

## Where things stand

The published data are the **1 January 2026** ISTAT vintage. Release `2026.1` resolved
issues #15, #18 and #23 and corrected cp1252 corruption in two municipality names;
`2026.2` added the ISO 3166-2 codes (#22) without touching geometry. Maintenance was
effectively paused between mid-2024 and mid-2026.

That release also replaced the manual rebuild of `comuni.geojson` with
`scripts/fetch_sources.sh` and `scripts/build_comuni.py`, covered by unit tests and by
per-issue acceptance checks in `tests/`. The province loop bound is now derived from the
data rather than hardcoded: left at `111`, it would have dropped all of Sardinia without
producing an error.

The substantial work ahead is the historical series — priority 1 below, tracked under the
`historical-series` milestone.

The repository moved from `openpolis/geojson-italy` to
[`guglielmo/geojson-italy`](https://github.com/guglielmo/geojson-italy), and the default
branch was renamed `master` → `main` in August 2026. GitHub redirects both, on
`raw.githubusercontent.com` as well as the web UI, so pinned URLs keep working — but they
should be updated to the current owner and branch.

## Priorities, in order

### 1. Historical series, 2001 onward (`historical-series` milestone)

The largest piece of work, and the one that returns the repository to its original intent:
serving boundaries at any past date, not only the current one. Design in
[docs/specs/2026-08-14-historical-series-design.md](docs/specs/2026-08-14-historical-series-design.md),
decomposed into issues #24–#32.

**Everything comes from ISTAT, and needs no credentials.** Geometry from the edition
archives — all 26 downloaded and measured, 2001 to 2026. Identity from the SITUAS variation
reports: which entity is which across mergers, splits and recodings, with effective dates
and enacting acts, published anonymously with coverage back to 1861.

That second half was settled in August 2026. The milestone was designed around a derived
reconstruction maintained elsewhere; reading ISTAT directly removed the dependency and, with
it, a defect the derived reading carried — a municipality extinguished in 2003 and
re-established in 2004 appeared as permanently extinct, because only extinction records were
being read.

Three things shape the design.

**Fidelity to the source, without normalisation.** If ISTAT published a straightened boundary
segment in a given edition, the archive publishes it straightened. This repository's value is
provenance; a normalised archive is the maintainer's interpretation carrying ISTAT's
authority, and a third party cannot falsify it.

**A stable, public identity.** The Sardinian reform changed all 377 Sardinian
`com_istat_code` values with zero overlap, because the municipal code embeds the province
code. No dataset keyed on the ISTAT code can express continuity across that event. The
archive keys on the **first cadastral code** and treats the ISTAT code as what it is — an
attribute with a validity period.

The key has to be public as well as stable: an internal row id from someone's database
renumbers on re-import and cannot be checked by anyone else. The cadastral code is assigned
by the Agenzia delle Entrate and republished by ISTAT, and measured across the whole series
8,229 of 8,230 municipalities carry exactly one for their entire life, with no code ever
reused. Rules and tests in `scripts/identity.py`.

**Consumers download files and never run code.** Every one of the 58 change dates from 2001
is pre-materialised and published as release assets, with an index mapping validity intervals
to releases. Publishing only 1 January editions would be wrong rather than merely coarse: 32
of those 58 dates fall inside the year, so an annual series returns plausible, false answers
for them.

### 2. Interoperability with world-geojson (exploratory)

[`georgique/world-geojson`](https://github.com/georgique/world-geojson) provides global
coverage and currently has **no subnational breakdown for Italy** — only a country outline
and three macro-areas — while its contribution guide announces per-state boundaries for a
future release. There is a real gap to fill, but the fit needs negotiating before any code
is written:

- **Granularity.** That project ships as an npm package with roughly one file per area.
  Only simplified provinces and regions are plausible contributions; 7,899 municipalities
  are not.
- **Method.** Its contribution guide asks for hand-drawn polygons at ~20 km scale, with
  accuracy explicitly not required at that scale. This repository publishes unsimplified
  official ISTAT boundaries. The two projects have different ideas of what the data *is*,
  which is the substantive thing to agree on.
- **Licensing.** That project is GPL-3.0; these data are CC-BY 4.0 derived from ISTAT, and
  ISTAT attribution has to survive any transfer.

First step is an exploratory issue on that repository, not a pull request.

## Administrative changes pending for the next release

Read from ISTAT's variation records in August 2026. These all postdate the published
1 January 2026 vintage, so the current data is correct *for its reference date* — but each
will be reported as a defect until the next vintage adopts it.

| Effective | Change |
| --- | --- |
| 2026-01-31 | **Lirio** incorporated into Montalto Pavese (L.R. Lombardia 1/2026) |
| 2026-02-21 | **Castegnero** and **Nanto** merged into **Castegnero Nanto** (`024129`, cadastral `M439`) |
| 2026-05-14 | **Vallecrosia** renamed **Vallecrosia al mare** |

The first two bring the national count to 7,894 and are already noted in the `2026.1`
CHANGELOG. The rename is new — it was found by reading the variation reports directly, and
had not been noticed before.

ISTAT publishes the 1 January 2027 edition around March 2027; all three will be in it.

## Known defects in the current release

| Ref | Defect |
| --- | --- |
| — | `topojson/limits_IT_all.topo.json` carries **7,895** municipalities against 7,896 everywhere else: Miagliano (096034, Biella, 0.7 km²) is dropped. It survives in `limits_IT_municipalities.topo.json`, so only the combined file is affected. Preexisting, not a 2026.1 regression — the 2023 release lost exactly one municipality the same way (7,898 of 7,899). Cause is the `-clean` that follows the 20% simplification in the second mapshaper invocation of `generate_topojson.sh`. Not fixed here because the generation chain is due to be replaced wholesale by the `historical-series` milestone; file an issue so it is not lost. |

## Traps worth keeping

**ISTAT gives metropolitan cities two different codes, and its own products disagree on
which to show.** The boundary shapefiles carry `COD_PROV` **112** for Sassari and **118**
for Cagliari, while `Elenco-comuni-italiani` carries `COD_UTS` **312** and **318** for the
same two units. This repository has always used the `COD_PROV` family — Rome is `058`, not
`258` — so 112 and 118 are the values published here. Cross-checking against the codes list
will appear to contradict this. It doesn't.

**The Sud Sardegna dismemberment splits five ways, not the three usually reported:**
53 municipalities to 118 Cagliari, 28 to 117 Medio Campidano, 24 to 119 Sulcis Iglesiente,
and one each to 116 Ogliastra (Seui) and 114 Nuoro (Seulo). Seui and Seulo are adjacent,
near-homonymous Barbagia municipalities that ended up in different provinces; they are the
case a hand-written crosswalk gets wrong. Cagliari's metropolitan city draws only 17 of its
70 municipalities from the former province 92.

**ISO 3166-2:IT does not cover five of the 110 second-level units**, so `prov_iso_3166_2`
is null for Valle d'Aosta and for the four Sardinian provinces created in 2026 (Gallura
Nord-Est, Ogliastra, Medio Campidano, Sulcis Iglesiente). The Sardinian four bear the
vehicle plates of provinces ISO *deleted* in April 2019 — OT, OG, VS, CI — which makes
filling the gap look trivial and makes it wrong: those codes are withdrawn, not free.
Gorizia, Pordenone, Trieste and Udine are the opposite case, deleted in 2019 and restored
in 2020 as decentralized regional entities, so they do carry codes. Revisit when ISO
registers the Sardinian units; `scripts/iso_3166_2.py` documents each gap and the tables
are checked against the `iso-codes` package on every test run.

**The ISTAT boundary edition and the codes spreadsheet are not in step.** The edition is
frozen at 1 January; the spreadsheet tracks the present. Municipalities suppressed in
between appear in one and not the other — three of them in the 2026.1 build. The build
reports them rather than guessing; see `CATASTO_OVERRIDES`.

## Open questions

Sub-municipal boundaries (#11, #13) were previously declined because the only known ISTAT
source was the 2011 sub-municipal areas dataset, already stale at the time. ISTAT has since
published the 2021 *Basi Territoriali*; whether it carries sub-municipal areas and
inhabited localities in a usable form has not been checked. Worth verifying before
declining these again.

## Out of scope

- **Postal code (CAP) boundaries (#21).** Italian postal codes are proprietary to Poste
  Italiane and are not in the public domain, so they cannot be redistributed here.
- **Non-standard abbreviations (#14).** Only identifiers backed by a national or
  international standard are added to the metadata. `reg_iso_3166_2` and
  `prov_iso_3166_2`, added in `2026.2`, are the standards-based alternative that request
  was reaching for.
