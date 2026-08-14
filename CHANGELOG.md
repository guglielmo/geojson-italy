# Changelog

All notable changes to this project will be documented in this file.

Releases will be tagged with year[.version].

## [2026.2] August 2026
ISO 3166-2 codes for regions and second-level units (#22). Same boundaries as `2026.1`:
this release adds metadata and changes no geometry.

Two new properties, additive and safe for existing consumers:

- `reg_iso_3166_2` — present on all 20 regions. Note that ISO numbers the regions on its
  own scheme, unrelated to the ISTAT one: Piedmont is ISTAT `01` and ISO `IT-21`.
- `prov_iso_3166_2` — present on 105 of the 110 second-level units, `null` on the other
  five. Where present it is the vehicle plate prefixed, e.g. `IT-TO`, `IT-RM`.

They appear on municipality features and, through the dissolve, on
`limits_IT_provinces` and `limits_IT_regions` as well.

**Why five units carry `null`.** Publishing a code the standard does not define would make
the field useless for the interoperability it exists to serve, so the gaps are left honest:

| Unit | Plate | Why |
| --- | --- | --- |
| Valle d'Aosta | AO | `IT-AO` deleted 22 November 2019 — the region exercises provincial functions itself, so there is no province to code. ISTAT keeps `COD_PROV 007` for statistical continuity. |
| Gallura Nord-Est Sardegna | OT | Created 1 January 2026. `IT-OT` was deleted 9 April 2019 with the old Olbia-Tempio and never restored. |
| Ogliastra | OG | Re-created 1 January 2026. `IT-OG` deleted 9 April 2019. |
| Medio Campidano | VS | Re-created 1 January 2026. `IT-VS` deleted 9 April 2019. |
| Sulcis Iglesiente | CI | Created 1 January 2026. `IT-CI` was deleted 9 April 2019 with the old Carbonia-Iglesias. |

The four Sardinian units bear the plates of provinces ISO deleted in 2019. Reusing those
codes would assert an identifier the standard has withdrawn, so they wait until ISO
registers the new units. 175 municipalities are affected; all of them still carry
`reg_iso_3166_2` = `IT-88`, since the region's code is unaffected.

By contrast Gorizia, Pordenone, Trieste and Udine **do** carry codes: deleted in April 2019
along with the others, they were restored on 22 November 2020 as decentralized regional
entities.

The reference tables live in `scripts/iso_3166_2.py` and are checked against the
`iso-codes` package on every test run, so drift fails the build rather than shipping.

## [2026.1] August 2026
Boundaries updated to the ISTAT vintage of 1 January 2026 (7,896 municipalities).

**Breaking change — Sardinian codes renumbered.** The reform effective 1 January 2026
replaced Sud Sardegna with two metropolitan cities and six provinces, and renumbered
every Sardinian province: codes 90, 91, 92, 95 and 111 are now vacant, and the new
units occupy 112 to 119. `limits_P_90_municipalities.geojson` and its siblings for
those codes still exist but hold an empty `GeometryCollection`, so a consumer pinning
them receives an empty result rather than an error. Update pinned province files.

| Code | Unit | Municipalities |
| --- | --- | --- |
| 112 | Sassari (metropolitan city) | 66 |
| 113 | Gallura Nord-Est Sardegna | 26 |
| 114 | Nuoro | 53 |
| 115 | Oristano | 87 |
| 116 | Ogliastra | 23 |
| 117 | Medio Campidano | 28 |
| 118 | Cagliari (metropolitan city) | 70 |
| 119 | Sulcis Iglesiente | 24 |

Because the municipal code embeds the province code, **all 377 Sardinian
`com_istat_code` values changed**, with no overlap against the previous release, and
the new code cannot be derived from the old by substituting the prefix — Aggius goes
`090001` → `113001` while Aglientu goes `090062` → `113002`. Join on
`com_catasto_code`, which is unaffected.

Also fixed: two municipalities missing since 2023 (#18), the `com_istat_code` of
Montecopiolo and Sassofeltrio (#15), and cp1252 corruption in the names of
Duino Aurisina-Devin Nabrežina and San Floriano del Collio-Števerjan.

Seven municipalities appear that the 2023 release did not carry, and they have no
`op_id`, `opdm_id`, `minint_elettorale` or `minint_finloc`, since those identifiers
exist only in this repository's history: Bardello con Malgesso e Bregano,
Misiliscemi, Moransengo-Tonengo, Santa Caterina d'Este, Setteville, Sovizzo (recoded
`024128` after absorbing Gambugliano) and Uggiate con Ronago.

Note that these boundaries are ISTAT's edition of 1 January 2026 and so predate three
later changes, which bring the national count to 7,894: Lirio was incorporated into
Montalto Pavese on 31 January 2026, and Castegnero and Nanto merged into Castegnero
Nanto on 21 February 2026. All three are still present here, as ISTAT published them
for the reference date; they will disappear in the 1 January 2027 vintage.

## [2023.1] June 2023
Municipalities merges and splits.
Geojson files are now compatible with pre-RFC 7946 GeoJSON spec.

## [2022.1] Sept 2022
Municipalities merges and splits.

## [2021.2] Jul 2021 
Two municipalities in the province of Pesaro switched to the province of Rimini, changing region from Marche to Emilia-Romagna.
This changes provincial and regional subdivisions.

## [2021.1] Feb 2021
Municipalities merges and splits. It appears as no change of province or region happened from the 2019 release.

## [2019] Jan 2019

Initial release

