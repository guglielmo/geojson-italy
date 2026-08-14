# ISTAT edition series — measurements

Status: measured 14 August 2026, against the live ISTAT site
Issue: #24
Companion to: [2026-08-14-historical-series-design.md](2026-08-14-historical-series-design.md)

Every figure here comes from downloading the 26 editions and reading them, not from the
identity source. Reproduce with:

```sh
.venv/bin/python -m scripts.fetch_editions      # ~300 MB of zips into build/editions/
.venv/bin/python -m scripts.measure_editions
```

Checksums for every file are recorded in `build/editions/MANIFEST.json`.

## What was confirmed

**Coverage is complete for 2001–2026.** All 26 editions resolve and download. The
"2002–2010 unavailable" gap recorded in the identity source's ingestion code does not exist.

**Two URL shapes, plus a census form.** `Limiti0101<YYYY>_g.zip` is the annual edition,
nested under a year directory from 2022; `Limiti<YYYY>_g.zip` is the census edition,
published for 1991, 2001, 2011 and 2021. For 2001 and 2011 no annual edition exists, so
the census one is the source by necessity.

**Exact-equality collapsing is what makes the archive affordable.** 208,572
edition-instances collapse to **68,428 versions**, a reduction of **3.05×**. No tolerance
is involved: `tests/test_measure_editions.py` proves a geometry differing by 1e-9 degrees
is kept as a separate version.

## What was corrected

### The 2021 edition is not a re-generalisation

The design lists the re-generalising editions as *2002, 2010, 2011, 2012, 2019, 2021, 2022
and 2025*. Measured against the annual editions, they are:

| Transition | Municipalities compared | Geometry changed |
| --- | --- | --- |
| 2001 → 2002 | 8,101 | 100.0% |
| 2009 → 2010 | 7,980 | 100.0% |
| 2010 → 2011 | 8,091 | 100.0% |
| 2011 → 2012 | 8,092 | 100.0% |
| 2018 → 2019 | 7,904 | 100.0% |
| 2021 → 2022 | 7,901 | 100.0% |
| 2024 → 2025 | 7,892 | 100.0% |
| **2020 → 2021** | **7,903** | **4.7%** |

**2021 is not one of them.** It appeared to be only because the identity source had ingested
the census product in its place. Reading the annual edition directly, 2020 → 2021 changes 4.7% of
geometries — an ordinary year with administrative events, nothing more.

This is the clearest vindication of D9 available: sourcing geometry from ISTAT directly
does not merely avoid a known artefact, it changes a documented finding of the design.

### The version count was inflated by that same artefact

The design estimates ~74,600 versions from ~205,000 instances, derived from the identity
source. Measured: **68,428 versions
from 208,572 instances**, over one more edition than the design counted.

The ~6,000 difference is roughly one edition's worth of municipalities, which is what a
spurious whole-country geometry change adds. The archive is about 8% smaller than planned.

### The census/annual divergence is universal but smaller than stated

The design describes the 2021 census-for-annual substitution as fabricating "a 3.5% to 12%
discontinuity across every municipality". Comparing the two 2021 editions directly:

| Measure | Value |
| --- | --- |
| Municipalities in both | 7,901 |
| With **identical** geometry | **0** |
| Median area difference | 0.77% |
| Mean area difference | 1.31% |
| 95th percentile | 4.28% |
| Maximum | 38.88% |
| Share falling in the 3%–12% band | 10% |

So the qualitative claim is understated and the quantitative one overstated: **not one of
the 7,901 municipalities has the same geometry in both editions**, but the typical
discrepancy is under 1% of area rather than 3.5–12%. The distribution has a long tail — one
municipality differs by 39% — which is likely where the original range came from.

Either way the two files are different products and must not be mixed, which is what
`scripts/istat_editions.py` enforces.

## Incidental confirmations

The "municipalities compared" column falls below the edition size whenever ISTAT codes are
reassigned, and each drop matches a known administrative event:

| Transition | Dropped from comparison | Event |
| --- | --- | --- |
| 2005 → 2006 | 123 | The four Sardinian provinces created in 2005 (Olbia-Tempio, Ogliastra, Medio Campidano, Carbonia-Iglesias) recoded their municipalities |
| 2009 → 2010 | 114 | Monza e della Brianza, Fermo and Barletta-Andria-Trani come into use |
| 2016 → 2017 | 165 | Provincial reassignments |
| 2019 → 2020 | 12 | — |
| **2025 → 2026** | **377** | The Sardinian reform: exactly the 377 municipalities whose codes changed |

The 2025 → 2026 figure matching 377 precisely is an independent check on the release
2026.1 finding that all Sardinian municipality codes changed with zero overlap.

## Consequences for the milestone

- `source_edition` can name a real file with a recorded SHA-256, so the round-trip check in
  #30 compares against something a third party can fetch.
- The identity layer (#25) still has to come from the identity source: nothing above
  establishes *which entity is which* across a recoding, only that the codes changed.
- The 39 intra-year cases in #24's scope depend on that identity layer and are not
  addressed here.
