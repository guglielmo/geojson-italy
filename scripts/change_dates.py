"""The dates at which the published snapshot changes (issues #24, #28).

A release exists for every date on which a consumer downloading the archive
would get something different. Two independent things make that true:

1. **The roster changes.** A municipality is created, suppressed, renamed,
   recoded or moved to another province. ISTAT records each with its effective
   date in the variation reports, and these dates fall wherever the enacting act
   put them — mostly inside the year.
2. **The geometry changes.** ISTAT publishes boundaries only at 1 January, so
   every edition date is a change date: even in a year with no re-generalisation
   the administratively affected municipalities have new shapes.

The union of the two is the publication calendar. It is derived here rather than
listed, because a hand-kept list of dates is exactly the kind of literal that
silently drops a year — the same failure the hardcoded province bound produced
in the 2026.1 build.

**Territory transfers are deliberately not publication dates.** `CE`/`AQ` — a
strip of land ceded from one municipality to another — change boundaries on
their effective date, but ISTAT does not publish a boundary edition on that
date. Minting a release for it would mean serving the *previous* geometry under
the new date, which is D2's prohibition exactly: publishing one edition's shape
under another edition's date. The interval index sends such a date to the
snapshot that precedes it, which is the honest answer, and §9 of the design
records the limitation.
"""

from pathlib import Path

from scripts.istat_editions import SERIES_YEARS, edition_reference_date

ROOT = Path(__file__).resolve().parent.parent
SITUAS = ROOT / "build" / "situas"

# Start of the archive. Not 1 January 2001: the first edition of the series is
# the 2001 census cartography, whose boundaries describe 21 October 2001. For
# the nine months before that ISTAT published no geometry at all, and a snapshot
# without geometry is not this repository's product — so the series begins where
# the geometry does, and says so, rather than dating the census edition back to
# January and shipping a Fonte Nuova that did not exist yet.
SERIES_START = edition_reference_date(min(SERIES_YEARS))

# Variation codes that change the roster or a published attribute, and so start
# a new version of the dataset.
ROSTER_EVENTS = {
    "ES",       # extinction
    "CS",       # constitution
    "AQES",     # acquisition by extinction
    "CECS",     # cession for the constitution of a new unit
    "CD",       # name change
    "RN",       # statistical code renumbering
    "AP",       # change of province
    "RNAPUTS",  # renumbering with change of province, report 105's compound code
    "CDAP",     # name change with change of province, report 105
}

# Variation codes that move a boundary without touching the roster. See the
# module docstring: real events, not publication dates.
BOUNDARY_EVENTS = {
    "CE",  # territory ceded
    "AQ",  # territory acquired
}


class UnknownVariation(ValueError):
    """A variation code outside the two known families.

    Raised rather than ignored. Treating an unrecognised code as a non-event
    would drop a release date without saying so, and treating it as an event
    would mint one that may be empty; either way the archive would be wrong in a
    direction nobody chose.
    """


def variation_code(record):
    """The variation code of one record, across the reports' two layouts.

    Report 129 gives `DESC_COD_VARIAZIONE` as `CD-Cambio denominazione`; reports
    98 and 105 give a bare `COD_VARIAZIONE`.
    """
    if "COD_VARIAZIONE" in record and record["COD_VARIAZIONE"]:
        return str(record["COD_VARIAZIONE"]).strip()
    described = record.get("DESC_COD_VARIAZIONE")
    if not described:
        raise UnknownVariation(f"record carries no variation code: {sorted(record)}")
    return str(described).split("-", 1)[0].strip()


def event_date(record):
    """The effective date of one record, as an ISO date string."""
    return str(record["DATA_INIZIO_AMMINISTRATIVA"])[:10]


def codes_by_date(records, since=SERIES_START):
    """{date: {variation codes}} for every record on or after `since`."""
    out = {}
    for record in records:
        at = event_date(record)
        if at < since:
            continue
        code = variation_code(record)
        if code not in ROSTER_EVENTS and code not in BOUNDARY_EVENTS:
            raise UnknownVariation(
                f"{at}: variation code {code!r} is neither a roster event "
                f"{sorted(ROSTER_EVENTS)} nor a boundary event "
                f"{sorted(BOUNDARY_EVENTS)}"
            )
        out.setdefault(at, set()).add(code)
    return out


def roster_change_dates(records, since=SERIES_START):
    """Dates carrying at least one roster-changing event."""
    return sorted(
        at for at, codes in codes_by_date(records, since=since).items()
        if codes & ROSTER_EVENTS
    )


def edition_dates(years=SERIES_YEARS):
    """The reference date of every ISTAT boundary edition in the series.

    1 January for the annual editions; the census date for 2001 and 2011, which
    have no annual edition. Read from `istat_editions` rather than assembled
    here, so the two cannot drift apart.
    """
    return [edition_reference_date(year) for year in years]


def change_dates(records, years=SERIES_YEARS, since=SERIES_START):
    """The publication calendar: roster changes plus edition dates."""
    return sorted(set(roster_change_dates(records, since=since)) | set(edition_dates(years)))


def load_variations(name="var_comuni_129"):
    """The cached variation report, as a list of records."""
    from scripts.situas import parse_payload

    return parse_payload((SITUAS / f"{name}.json").read_text())


def main():
    records = load_variations()
    by_date = codes_by_date(records)
    dates = change_dates(records)
    roster = set(roster_change_dates(records))
    editions = set(edition_dates())
    boundary_only = sorted(
        at for at, codes in by_date.items() if not codes & ROSTER_EVENTS
    )

    print(f"publication dates          {len(dates)}")
    print(f"  roster changes           {len(roster)}"
          f"  ({sum(1 for d in roster if d[5:] != '01-01')} intra-year)")
    print(f"  edition dates            {len(editions)}")
    print(f"  both                     {len(roster & editions)}")
    print(f"boundary-only, not published  {len(boundary_only)}")
    for at in dates:
        marks = "".join(
            [
                "R" if at in roster else "-",
                "E" if at in editions else "-",
            ]
        )
        print(f"  {at}  {marks}  {','.join(sorted(by_date.get(at, ()))) or '-'}")


if __name__ == "__main__":
    main()
