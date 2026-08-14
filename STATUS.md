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

The target vintage is **1 January 2026**, published by ISTAT on 2 March 2026 at the
[reference permalink](https://www.istat.it/it/archivio/222527):

- non-generalised: `confini_amministrativi/non_generalizzati/2026/Limiti01012026.zip` (~94 MB)
- generalised: `confini_amministrativi/generalizzati/2026/Limiti01012026_g.zip` (~10 MB)

It contains **7,896 municipalities** and **110 provinces/UTS**, against 7,899 municipalities
in the current release. It already incorporates the Sardinian reform, so it resolves #23
directly.

Steps:

1. **Raise the province loop bound in both generation scripts before anything else** — see
   the breaking change below. Leaving it at `111` silently drops all of Sardinia.
2. Rebuild `comuni.geojson` from the ISTAT shapefiles (procedure in the
   [wiki](https://github.com/guglielmo/geojson-italy/wiki/How-to-generate-the-limits-files)),
   fixing the defects listed below in the process.
3. Regenerate all outputs (`./generate_geojson.sh`, `./generate_topojson.sh`).
4. Verify the municipality count reconciles to 7,896, that Sardinia has 377
   municipalities spread over province codes 112–119, and visually that no municipality
   holes remain (#18).
5. Update `CHANGELOG.md`, the vintage line in `README.md`, and the province-code
   invariant in `CLAUDE.md`, then tag `2026.1`.

Note that the 1 January 2026 boundaries predate the establishment of Castegnero Nanto
(merger of Castegnero and Nanto, province of Vicenza, effective 21 February 2026), which
brings the national count to 7,894. That municipality will only appear in the 1 January
2027 vintage; expect it to be reported as a defect in the meantime.

#### Breaking change: Sardinian province codes are renumbered

This is not an additive change and it will break downstream consumers, so it belongs in the
release notes rather than being discovered by users. Every Sardinian province code changed:

| Old code | Old province | New codes |
| --- | --- | --- |
| 90 | Sassari | 112 Sassari (metropolitan city), 113 Gallura Nord-Est Sardegna |
| 91 | Nuoro | 114 Nuoro, 116 Ogliastra |
| 92 | Cagliari | 118 Cagliari (metropolitan city), 119 Sulcis Iglesiente |
| 95 | Oristano | 115 Oristano |
| 111 | Sud Sardegna | abolished; 117 Medio Campidano |

Two consequences:

- The maximum province code is now **119**, so the hardcoded `seq 1 111` in both scripts
  must become `seq 1 119`. Better still, derive the range from the data.
- Codes 90, 91, 92, 95 and 111 become vacant, which means
  `limits_P_90_municipalities.geojson` and friends will still be generated but will hold an
  empty `GeometryCollection`. Anyone who pinned those files for Sardinia gets a valid-looking
  file with no features rather than an error. Say so explicitly in the CHANGELOG.

**Note for whoever does this:** `CLAUDE.md` describes the province loop bound of 111 as
intentional. Verified against the 1 January 2026 data, it is now a defect — see the breaking
change above. Codes 104–107 stay vacant, but 111 joins them and 112–119 come into use.

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
| #23 | Sardinian provinces outdated: the reform effective 1 January 2026 renumbered every Sardinian province code and replaced Sud Sardegna. Affects all `limits_P_*` files and provincial aggregation — see the breaking change above. |

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
