# Project status

Maintenance status and work plan for this repository. Updated as work progresses.

## Where things stand

The published data are the **June 2023** ISTAT vintage (tag `2023.1`). Several
administrative changes have happened since, and there are known defects in the current
release — see *Known defects* below. Maintenance was effectively paused between mid-2024
and mid-2026.

The open issues have been triaged: three were closed (two resolved or superseded, one out
of scope), three confirmed defects are tracked under the `2026.1` milestone, and three
remain open as planned work or open questions.

The repository moved from `openpolis/geojson-italy` to
[`guglielmo/geojson-italy`](https://github.com/guglielmo/geojson-italy), and the default
branch was renamed `master` → `main` in August 2026. GitHub redirects both, on
`raw.githubusercontent.com` as well as the web UI, so pinned URLs keep working — but they
should be updated to the current owner and branch.

## Priorities, in order

### 1. Data update (`2026.1`)

The single highest-value item: it is what current users are actually blocked on, and it
resolves four open issues at once. Steps:

1. Determine the current ISTAT vintage at the
   [reference permalink](https://www.istat.it/it/archivio/222527).
2. Rebuild `comuni.geojson` from the ISTAT shapefiles (procedure in the
   [wiki](https://github.com/guglielmo/geojson-italy/wiki/How-to-generate-the-limits-files)),
   fixing the defects listed below in the process.
3. Regenerate all outputs (`./generate_geojson.sh`, `./generate_topojson.sh`).
4. Verify visually that no municipality holes remain (see #18) and that municipality
   counts reconcile against the ISTAT `Elenco-comuni-italiani` list.
5. Update `CHANGELOG.md`, the vintage line in `README.md`, and the province-code
   invariant in `CLAUDE.md` (see note below), then tag `2026.1`.

**Note for whoever does this:** `CLAUDE.md` documents province codes 104–107 as permanently
vacant placeholders. The 2025 Sardinian reform (#23) puts those codes back in play, so that
invariant has to be re-checked and rewritten as part of this release, not assumed.

### 2. ISO-3166-2 codes (#22)

Add ISO-3166-2 identifiers for regions and provinces. Low cost, and it is the prerequisite
for anything that consumes these files alongside international datasets — including
priority 3. It also supersedes #14 (region abbreviations), since ISO-3166-2 is the
standardised identifier that request was reaching for.

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
| #18 | Two municipalities missing relative to the 2023 ISTAT dataset (Bardello con Malgesso e Bregano, established 2023-01-01; Moransengo-Tonengo, recoded 2023-05-15). Produces visible holes in municipality maps. |
| #15 | Wrong `com_istat_code` for Montecopiolo (should be 099030) and Sassofeltrio (099031). Residue of the `2021.2` release, which updated the Marche → Emilia-Romagna transfer geometry but not the municipal codes. |
| #23 | Sardinian provinces outdated: the 2025 reform replaced Sud Sardegna with 2 metropolitan cities and 6 provinces. Affects all `limits_P_*` files and provincial aggregation. |

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
