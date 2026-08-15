"""Locating the ISTAT SITUAS reports (issue #24, design D9).

SITUAS is ISTAT's territorial information system. It publishes, anonymously and
over plain HTTP, both halves of what a shapefile cannot say:

    61   the complete roster of municipalities *at a given date*, with the
         cadastral code, the ISTAT code, the UTS and the names
    129  the administrative variations since 1991, with the enacting act
    98   suppressed municipalities, from 1865
    104  name changes, from 1862
    105  statistical code changes, from 1868

Report 61 is the one that changes the shape of this milestone. The design
assumed the roster at a past date had to be *reconstructed*, by replaying the
variation records over a known starting point. It does not: ISTAT answers the
question directly, for any date since 1948, and the answer carries the cadastral
code for every municipality. Reconstruction is replaced by a read, which is what
D4 asks for everywhere else — an archive a third party can check by fetching the
same URL.

Two shapes of endpoint, and they are not interchangeable:

    situas.istat.it/ShibO2Module/api/Report/ReportByUrl   the catalogue (POST)
    situas-servizi.istat.it/publish/reportspooljson        the reports (GET)

The catalogue lists all 77 datasets with their exact download links and their
required parameters. It is read rather than hardcoded, because the parameter set
differs per report; `REPORTS` below is the frozen subset this project uses, and
`check_against_catalogue` proves it still matches what ISTAT publishes.

**Dates are dd/mm/yyyy.** The reports reject the ISO form silently, by returning
the full range instead of the requested one, so the formatting is not cosmetic.

**The payload is double-encoded on some routes.** The catalogue returns a JSON
string containing JSON; the report spool returns an object. `parse_payload`
accepts both rather than guessing from the endpoint, since which route is which
is not a documented property.

**There is no pagination, and adding some would break the fetch.** The spool
returns a report whole — 7,896 rows for a 2026 roster in one response. SITUAS
has no offset parameter; passing a row offset as `pdatada`, which looks
plausible because that parameter exists on the period reports, yields an
unparseable second page. This is not a discovery of this project's: the ISTAT
ingestion in `gst-maps-pipelines` hit it first and documents it in
`flows/istat/comuni/01_ingestion_flow.py`. Recorded here so that a future reader
who sees a 3 MB response does not "fix" the client by paginating it.
"""

import json
from datetime import date

CATALOGUE_URL = "https://situas.istat.it/ShibO2Module/api/Report/ReportByUrl"
CATALOGUE_BODY = {"url": "get_elenco_microservizi"}

SPOOL = "https://situas-servizi.istat.it/publish/reportspooljson"
COUNT = "https://situas-servizi.istat.it/publish/reportspooljsoncount"

# The reports this project reads, with the parameters each one takes and the
# earliest date it covers. Frozen here so the build is deterministic and the
# tests need no network; verified against the live catalogue by
# check_against_catalogue().
REPORTS = {
    61: {
        "name": "elenco_codici_denominazioni",
        "title": "Elenco dei codici e delle denominazioni delle unità territoriali",
        "params": ("pdata",),
        "covers_from": date(1948, 1, 1),
    },
    98: {
        "name": "comuni_soppressi",
        "title": "Comuni soppressi o ceduti a stato estero",
        "params": ("pdatada", "pdataa"),
        "covers_from": date(1861, 3, 17),
    },
    104: {
        "name": "cambio_denominazione",
        "title": "Comuni con cambio denominazione",
        "params": ("pdatada", "pdataa"),
        "covers_from": date(1861, 3, 17),
    },
    105: {
        "name": "variazione_codice",
        "title": "Comuni con variazione del codice statistico",
        "params": ("pdatada", "pdataa"),
        "covers_from": date(1861, 3, 17),
    },
    129: {
        "name": "var_comuni",
        "title": "Variazioni amministrative e territoriali dei comuni dal  1991",
        "params": ("pdata",),
        "covers_from": date(1991, 1, 1),
    },
}

# Filenames already in use for the variation reports. Kept exactly as they are:
# the payloads were fetched before this module existed, and renaming them would
# make every cached copy look missing and re-download 11 MB from an endpoint
# that answers intermittently.
CACHE_NAMES = {
    98: "comuni_soppressi_98",
    104: "cambio_denominazione_104",
    105: "variazione_codice_105",
    129: "var_comuni_129",
}


class UnknownReport(KeyError):
    """A pfun this project does not read."""


class BadParameters(ValueError):
    """Parameters that do not match what the report declares.

    Raised rather than passed through: SITUAS answers an unrecognised parameter
    set with the report's full default range instead of an error, so a typo
    would return plausible data for the wrong period.
    """


def format_date(value):
    """Render a date the way the spool endpoint expects: dd/mm/yyyy."""
    if isinstance(value, str):
        value = date.fromisoformat(value[:10])
    return value.strftime("%d/%m/%Y")


def report(pfun):
    try:
        return REPORTS[pfun]
    except KeyError:
        raise UnknownReport(
            f"pfun {pfun} is not one of the reports this project reads: "
            f"{sorted(REPORTS)}"
        ) from None


def spool_url(pfun, **params):
    """Build the download URL for one report.

    The parameter set must match the report's declaration exactly — see
    BadParameters for why a superset or a subset is not tolerated.
    """
    declared = report(pfun)["params"]
    if set(params) != set(declared):
        raise BadParameters(
            f"report {pfun} takes {declared}, got {tuple(sorted(params))}"
        )
    query = "&".join(f"{p}={format_date(params[p])}" for p in declared)
    return f"{SPOOL}?pfun={pfun}&{query}"


def count_url(pfun, **params):
    """The row-count endpoint for the same report and parameters.

    Cheap enough to check a suspicious download against, but not called by the
    fetcher: a routine count would double the number of requests made to a
    service that must be asked sparingly.
    """
    return spool_url(pfun, **params).replace(SPOOL, COUNT, 1)


def roster_url(at):
    """The complete municipality roster valid on a given date."""
    at = date.fromisoformat(at[:10]) if isinstance(at, str) else at
    if at < REPORTS[61]["covers_from"]:
        raise ValueError(
            f"report 61 covers from {REPORTS[61]['covers_from']}, asked {at}"
        )
    return spool_url(61, pdata=at)


def variations_url(pfun, until, since=None):
    """One variation report, over its full coverage up to `until`.

    `until` is explicit rather than defaulted to today because the catalogue
    ends every period at the current date: an implicit end would make two runs
    of the same script fetch two different things and record it as one.
    """
    meta = report(pfun)
    since = since or meta["covers_from"]
    if meta["params"] == ("pdata",):
        return spool_url(pfun, pdata=since)
    return spool_url(pfun, pdatada=since, pdataa=until)


def parse_payload(text):
    """Return the list of records from a SITUAS response.

    Handles the three shapes observed: a double-encoded JSON string, an object
    with `resultset`, and an object with `items`.
    """
    data = json.loads(text)
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, list):
        return data
    for key in ("resultset", "items"):
        if key in data:
            return data[key]
    raise ValueError(f"unrecognised SITUAS payload, keys: {sorted(data)}")


def catalogue_entries(payload_text):
    """The catalogue's report descriptors, keyed by pfun."""
    entries = {}
    for item in parse_payload(payload_text):
        entries[int(item["Id report"])] = item
    return entries


def check_against_catalogue(payload_text):
    """Differences between the frozen table and the live catalogue.

    Returns a list of complaints, empty when the two agree. A drift here means
    ISTAT changed a report's parameters or withdrew it, which must surface as a
    failure rather than as an empty result set.
    """
    entries = catalogue_entries(payload_text)
    problems = []
    for pfun, meta in sorted(REPORTS.items()):
        entry = entries.get(pfun)
        if entry is None:
            problems.append(f"report {pfun} ({meta['name']}) is gone from the catalogue")
            continue
        declared = tuple(
            p.strip()
            for p in entry["parametri necessari"].split("-")
            if p.strip() and p.strip() != "pfun"
        )
        if declared != meta["params"]:
            problems.append(
                f"report {pfun} now takes {declared}, table says {meta['params']}"
            )
        if entry["Titolo report"] != meta["title"]:
            problems.append(
                f"report {pfun} retitled: {entry['Titolo report']!r} "
                f"against {meta['title']!r}"
            )
    return problems
