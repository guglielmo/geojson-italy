# Project status

Maintenance status and work plan for this repository. Updated as work progresses.

## Where things stand

The published data are the **1 January 2026** ISTAT vintage (tag `2026.1`), which resolved
issues #15, #18 and #23 and corrected cp1252 corruption in two municipality names.
Maintenance was effectively paused between mid-2024 and mid-2026.

That release also replaced the manual rebuild of `comuni.geojson` with
`scripts/fetch_sources.sh` and `scripts/build_comuni.py`, covered by unit tests and by
per-issue acceptance checks in `tests/`. The province loop bound is now derived from the
data rather than hardcoded: left at `111`, it would have dropped all of Sardinia without
producing an error.

The substantial work ahead is the historical series — priority 2 below, tracked under the
`historical-series` milestone.

The repository moved from `openpolis/geojson-italy` to
[`guglielmo/geojson-italy`](https://github.com/guglielmo/geojson-italy), and the default
branch was renamed `master` → `main` in August 2026. GitHub redirects both, on
`raw.githubusercontent.com` as well as the web UI, so pinned URLs keep working — but they
should be updated to the current owner and branch.

## Priorities, in order

### 1. ISO-3166-2 codes (#22)

Add ISO-3166-2 identifiers for regions and provinces. Low cost, and it is the prerequisite
for anything that consumes these files alongside international datasets — including
priority 2. It also supersedes #14 (region abbreviations), since ISO-3166-2 is the
standardised identifier that request was reaching for.

### 2. Historical series, 2001 onward (`historical-series` milestone)

The largest piece of work, and the one that returns the repository to its original intent:
serving boundaries at any past date, not only the current one. Design in
[docs/specs/2026-08-14-historical-series-design.md](docs/specs/2026-08-14-historical-series-design.md),
decomposed into issues #24–#32.

Two sources, each for what only it can provide. Geometry comes from the ISTAT edition
archives, downloaded and read here, complete for every year from 2001 to 2026. The identity
history — which entity is which across mergers, splits and recodings, with effective dates —
comes from the territorial reconstruction built for the MAPS project, read-only, because it
cannot be derived from shapefiles at all.

Three things shape the design.

**Fidelity to the source, without normalisation.** If ISTAT published a straightened boundary
segment in a given edition, the archive publishes it straightened. This repository's value is
provenance; a normalised archive is the maintainer's interpretation carrying ISTAT's
authority, and a third party cannot falsify it.

**A surrogate stable identity.** The Sardinian reform changed all 377 Sardinian
`com_istat_code` values with zero overlap, because the municipal code embeds the province
code. No dataset keyed on the ISTAT code can express continuity across that event. The
archive keys on a surrogate identifier and treats the ISTAT code as what it is — an attribute
with a validity period.

**Consumers download files and never run code.** Every one of the 58 change dates from 2001
is pre-materialised and published as release assets, with an index mapping validity intervals
to releases. Publishing only 1 January editions would be wrong rather than merely coarse: 32
of those 58 dates fall inside the year, so an annual series returns plausible, false answers
for them.

### 3. Interoperability with world-geojson (exploratory)

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
  international standard are added to the metadata; see priority 2 for the standards-based
  alternative.
