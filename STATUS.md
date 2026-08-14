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

Beyond the pending data release, the substantial work ahead is the historical series —
priority 3 below, tracked under the `historical-series` milestone.

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

Beware that ISTAT identifies metropolitan cities with two different codes, and its own
products disagree on which to show. The boundary shapefiles carry `COD_PROV` **112** for
Sassari and **118** for Cagliari, while `Elenco-comuni-italiani` carries `COD_UTS` **312** and
**318** for the same two units. This repository has always used the `COD_PROV` family — Rome
is `058`, not `258` — so 112 and 118 are the correct values here, and cross-checking the table
above against the codes list will appear to contradict it. It doesn't.

Two consequences:

- The maximum province code is now **119**, so the hardcoded `seq 1 111` in both scripts
  must become `seq 1 119`. Better still, derive the range from the data.
- Codes 90, 91, 92, 95 and 111 become vacant, which means
  `limits_P_90_municipalities.geojson` and friends will still be generated but will hold an
  empty `GeometryCollection`. Anyone who pinned those files for Sardinia gets a valid-looking
  file with no features rather than an error. Say so explicitly in the CHANGELOG.

#### The break reaches the municipality identifier, not just the province

Verified against the data: **all 377 Sardinian `com_istat_code` values change, with zero
overlap** between the current release and the 1 January 2026 vintage. The municipality code
embeds the province code, so renumbering the provinces renumbered every municipality under
them. `com_istat_code` is the primary key most consumers join on, which makes this the most
disruptive part of the release.

The new code cannot be derived from the old one by substituting the province prefix, because
the progressive part was renumbered too — Aggius goes `090001` → `113001` while Aglientu goes
`090062` → `113002`. Any consumer attempting a string fix-up will produce plausible, wrong
codes.

`com_catasto_code` is the stable key across the reform: it is unique over the 377 Sardinian
municipalities and unaffected by provincial reassignment. It is the right join column for a
time-variant crosswalk, and the only one in the current metadata that survives.

The Sud Sardegna dismemberment splits **five** ways, not the three usually reported:

| To | Municipalities |
| --- | --- |
| 118 Cagliari (metropolitan city) | 53 |
| 117 Medio Campidano | 28 |
| 119 Sulcis Iglesiente | 24 |
| 116 Ogliastra | 1 — Seui |
| 114 Nuoro | 1 — Seulo |

Seui and Seulo are adjacent, near-homonymous Barbagia municipalities that ended up in
different provinces; they are the case a hand-written crosswalk gets wrong. Note also that
Cagliari's metropolitan city draws only 17 of its 70 municipalities from the former province
92, the other 53 coming from Sud Sardegna.

**Note for whoever does this:** `CLAUDE.md` describes the province loop bound of 111 as
intentional. Verified against the 1 January 2026 data, it is now a defect — see the breaking
change above. Codes 104–107 stay vacant, but 111 joins them and 112–119 come into use.

### 2. ISO-3166-2 codes (#22)

Add ISO-3166-2 identifiers for regions and provinces. Low cost, and it is the prerequisite
for anything that consumes these files alongside international datasets — including
priority 3. It also supersedes #14 (region abbreviations), since ISO-3166-2 is the
standardised identifier that request was reaching for.

### 3. Historical series, 2001 onward (`historical-series` milestone)

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

### 4. Interoperability with world-geojson (exploratory)

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
