"""Tests for the publication calendar (issues #24, #28).

The calendar decides what gets published and what does not, so its two edges
are what the tests pin: an unknown variation code must fail the build rather
than be silently classified, and a territory transfer must not mint a release
whose contents would be the previous snapshot under a new date.
"""

import pytest

from scripts.change_dates import (
    UnknownVariation,
    change_dates,
    codes_by_date,
    edition_dates,
    event_date,
    roster_change_dates,
    variation_code,
)


def rec(code, at, described=False):
    key = "DESC_COD_VARIAZIONE" if described else "COD_VARIAZIONE"
    value = f"{code}-Descrizione estesa" if described else code
    return {key: value, "DATA_INIZIO_AMMINISTRATIVA": f"{at}T00:00:00Z"}


def test_variation_code_from_the_bare_field():
    assert variation_code(rec("ES", "2026-02-21")) == "ES"


def test_variation_code_from_the_described_field():
    """Report 129 writes the code and its label in one string."""
    assert variation_code(rec("CD", "2026-05-14", described=True)) == "CD"


def test_event_date_drops_the_time():
    assert event_date(rec("ES", "2026-02-21")) == "2026-02-21"


def test_a_roster_event_makes_a_publication_date():
    dates = roster_change_dates([rec("ES", "2021-06-17")])
    assert dates == ["2021-06-17"]


def test_a_territory_transfer_does_not():
    """CE/AQ move a boundary on a date ISTAT publishes no boundary for.

    Publishing that date would serve the preceding edition's geometry under it,
    which is what D2 forbids.
    """
    assert roster_change_dates([rec("CE", "2021-09-10"), rec("AQ", "2021-09-10")]) == []


def test_a_date_carrying_both_is_published():
    """One roster event on the date is enough; the transfer rides along."""
    records = [rec("CE", "2019-01-30"), rec("ES", "2019-01-30")]
    assert roster_change_dates(records) == ["2019-01-30"]


def test_events_before_the_series_are_ignored():
    assert roster_change_dates([rec("ES", "1998-04-12")]) == []


def test_the_series_starts_where_the_geometry_does():
    """21 October 2001, the 2001 census edition's reference date.

    Fonte Nuova was constituted on 15 October 2001, six days earlier. There is
    no ISTAT geometry for that week, so the date is not published rather than
    served with a boundary set that does not describe it.
    """
    calendar = change_dates([rec("CS", "2001-10-15")])
    assert calendar[0] == "2001-10-21"
    assert "2001-10-15" not in calendar


def test_a_census_year_is_dated_at_the_census_not_at_1_january():
    calendar = change_dates([])
    assert "2011-10-09" in calendar
    assert "2011-01-01" not in calendar


def test_an_unknown_variation_code_raises():
    """Never guessed in either direction: it would add or drop a release date."""
    with pytest.raises(UnknownVariation):
        codes_by_date([rec("ZZ", "2020-01-01")])


def test_every_edition_date_is_a_publication_date():
    """Geometry changes at 1 January even in years with no roster event."""
    assert "2010-01-01" in change_dates([])


def test_the_calendar_is_the_union_and_is_sorted():
    records = [rec("CS", "2021-02-20"), rec("ES", "2003-03-06")]
    calendar = change_dates(records)
    assert calendar == sorted(set(calendar))
    assert {"2003-03-06", "2021-02-20"} <= set(calendar)
    assert set(edition_dates()) <= set(calendar)


def test_a_roster_event_on_1_january_is_not_counted_twice():
    calendar = change_dates([rec("RN", "2026-01-01")])
    assert calendar.count("2026-01-01") == 1
