# The identity layer — measurements

Status: measured 15 August 2026, against ISTAT's SITUAS reports
Issues: #24, #25, #28
Companion to: [2026-08-14-historical-series-design.md](2026-08-14-historical-series-design.md)

The design's §6 was revised on 14 August to source identity from ISTAT's SITUAS variation
reports instead of a derived reconstruction. Reading them turned up something the design did
not anticipate, and it removes most of the work the identity layer was expected to need.

Reproduce with:

```sh
.venv/bin/python -m scripts.fetch_situas variations --until 2026-08-15
.venv/bin/python -m scripts.fetch_situas rosters --limit 10   # polite; repeat
.venv/bin/python -m scripts.change_dates
```

## The roster at any date is published, not reconstructed

SITUAS report **61**, *Elenco dei codici e delle denominazioni delle unità territoriali*,
answers with the complete list of municipalities valid on a given date, for any date since
1948. Each record carries what the archive's attribute layer needs:

`PRO_COM_T`, `COD_CATASTO`, `COD_UTS`, `TIPO_UTS`, `COD_REG`, `COMUNE`, `COMUNE_IT`,
`DEN_UTS`, `DEN_REG`, `SIGLA_AUTOMOBILISTICA`, `COD_COM_FISCALE`, and from 2006 the NUTS
codes.

The design assumed the state at a past date had to be *reconstructed*, by replaying the
variation records over a known starting point. It does not. That matters beyond convenience:
a replay is an interpretation, and an interpretation that goes wrong is invisible to
consumers. A roster is a download, and D4's guarantee — anyone can rebuild this archive from
public sources — becomes a property of the URL rather than of our code.

The variation reports (129, 98, 104, 105) keep a narrower job: they supply the *reason* a
version exists and the act that enacted it, which is `version_reason` (#26), and they supply
the publication calendar.

## The roster reconciles with the boundary editions

Municipality counts, ISTAT edition against ISTAT roster at the edition's date — the check
issue #30 asks for, run early because both halves were already on disk:

| Years | Editions compared | Counts agree |
| --- | --- | --- |
| 2002–2010, 2012–2026 | 24 | **24** |
| 2001, 2011 | 2 | 0, and for a reason worth keeping |

Twenty-four exact matches across twenty-four years is a strong result for two independently
published products. The two exceptions are not errors in either source: they are the census
editions, and they are not dated 1 January.

## The census editions do not describe 1 January

| Edition | Municipalities | Roster at 1 January | Difference |
| --- | --- | --- | --- |
| `Limiti2001_g` | 8,101 | 8,100 | **Fonte Nuova**, constituted 15 October 2001 |
| `Limiti2011_g` | 8,092 | 8,094 | **Gravedona ed Uniti**, constituted 11 February 2011, in place of Consiglio di Rumo, Germasino and Gravedona |

Both editions describe their census reference date — 21 October 2001 and 9 October 2011 —
not 1 January of that year. The contents bracket the dates: the 2001 file holds a
municipality created on 15 October and not one created on 12 December.

Dating them at 1 January would publish, for 2001-01-01, a municipality that did not exist
for another nine months. That is precisely the defect §6 objects to in the derived source,
where Misiliscemi carries a geometry dated 2021-01-01, before it legally existed. Recorded
as `CENSUS_REFERENCE_DATES` in `scripts/istat_editions.py`, with
`edition_reference_date()` as the only place either date is stated.

**Consequence for D5.** The series begins **21 October 2001**, not 1 January 2001. For the
first nine months of 2001 ISTAT published no boundaries at all — the previous edition is the
1991 census — so those dates are not served rather than served with a boundary set that does
not describe them. Extending the series to the 1991 census would close the gap, and the
design already notes 1991 is reachable without schema change.

## The publication calendar is 98 dates, not 58

Derived in `scripts/change_dates.py` from the variation records plus the edition reference
dates, rather than listed:

| | Dates |
| --- | --- |
| Roster changes (a municipality created, suppressed, renamed, recoded, reassigned) | 86, of which **72 intra-year** |
| ISTAT edition reference dates | 26 |
| Both on the same date | 14 |
| **Published** | **98** |
| Boundary transfers only (`CE`/`AQ`), deliberately not published | 70 |

The design estimated 58 from the derived source, of which 32 intra-year. The real figure is
higher on both counts, and the reason is the same one that motivated D8: intra-year change
is the normal case, not the exception. Only 14 of the 26 January editions coincide with an
administrative event at all.

**The 70 boundary-only dates are excluded on principle, not for cost.** A `CE`/`AQ` pair
moves a strip of land from one municipality to another on a date ISTAT publishes no boundary
edition for. Minting a release there would serve the *preceding* edition's geometry under the
new date, which is exactly what D2 forbids. The interval index sends such a date to the
snapshot that precedes it, which is the honest answer, and §9 records the limitation.

## The cadastral code behaves as a key, measured on public data

The design's justification for `terr_key` — 8,229 of 8,230 municipalities carrying exactly
one cadastral code for their whole life, no code ever reused — was measured against the
derived source. Re-measured against the 26 published rosters, 2001 to 2026:

| Measure | Result |
| --- | --- |
| Distinct cadastral codes | 8,231 |
| Present in all 26 rosters | 7,766 |
| Municipalities whose cadastral code changed under a constant ISTAT code | **1** — Lonato → Lonato del Garda, `E667` → `M312`, 2008 |
| Codes whose presence in the series is interrupted and resumes | **1** — `A618` Baranzate, absent from the 2004 roster alone |
| Codes carrying more than one name over time | 38, every one a rename of the same entity |

Both exceptions are the ones the design names, and both now rest on a public source. The
Baranzate interruption is the extinction of 6 March 2003 and the re-establishment of 8 June
2004 — visible in the roster series as a single missing year, which is what §6 predicts and
what a reader of extinction records alone would miss.

## Asking SITUAS sparingly

`situas-servizi.istat.it` returns 503 to some client addresses for stretches of minutes,
then serves the same request normally. The response to that is not more requests:

- one at a time, never in parallel, with a pause between them (`SITUAS_PAUSE`, default 5 s);
- few retries with long waits rather than many rapid ones;
- cache first, and `--limit N` to spread the first fill across sessions;
- report 61 returns whole, with no pagination. Passing a row offset as `pdatada` looks
  plausible and yields an unparseable second page — documented first by the ISTAT ingestion
  in `gst-maps-pipelines`, repeated here so nobody "fixes" the client by paginating it.

**24 of the calendar's 98 rosters cost nothing**: that ingestion already holds report 61 at
1 January of every year, and `fetch_situas seed --seed-from` adopts those files, keeping the
ISTAT URL in the manifest so anyone can re-fetch and compare. 74 remain to be fetched, about
ten minutes at the polite pace.

## What this changes for the milestone

- **#24** keeps geometry as specified; its intra-year rule gains a fourth case — a
  municipality created *before* the census edition of its own year, which the census dating
  now handles correctly.
- **#25** loses most of its assembly work: the attribute layer is a roster read, joined to
  geometry on `PRO_COM_T` at the applicable edition and keyed on the first `COD_CATASTO`.
- **#26** is unaffected in intent, and its inputs are now the variation reports rather than a
  reconstruction's `end_reason` column.
- **#28** publishes 98 releases rather than 58, and the calendar is derived rather than kept
  by hand.
- **#30** gains its first passing check: 24 of 26 edition counts reconcile against ISTAT's
  own roster, and the two that do not are explained by a dating rule now encoded in the code.
