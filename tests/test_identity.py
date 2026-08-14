"""Tests for the identity rules of the historical series (issue #25).

The rules under test are the ones that decide what reaches a public archive:
which key identifies an entity, what gets dropped, and what must fail loudly
rather than be guessed.
"""

import pytest

from scripts.identity import (
    ReversedInterval,
    first_cadastral_code,
    is_publishable,
    reversed_intervals,
    sort_by_validity,
)


def iv(code, frm=None, to=None):
    return {"identifier": code, "valid_from": frm, "valid_to": to}


def test_first_cadastral_code_of_a_stable_municipality():
    assert first_cadastral_code([iv("A069")]) == "A069"


def test_a_null_valid_from_sorts_before_a_dated_one():
    """The source leaves valid_from null for 'since before records began'.

    Sorting it as the earliest is the only reading that matches the data: the
    dated rows are all later amendments.
    """
    rows = [iv("M312", "2008-01-01"), iv("E667", None)]
    assert first_cadastral_code(rows) == "E667"


def test_lonato_del_garda_keys_on_its_original_code():
    """The one municipality holding two cadastral codes.

    It was E667 until 2008 and M312 after, alongside its rename. The key is the
    first code and never changes; com_catasto_code stays a time-scoped
    attribute, so the two diverge for this entity alone.
    """
    rows = [iv("E667", None, "2008-01-01"), iv("M312", "2008-01-01")]
    assert first_cadastral_code(rows) == "E667"


def test_no_cadastral_code_yields_none():
    assert first_cadastral_code([]) is None


def test_sort_by_validity_is_deterministic():
    """Output ordering must be stable, or every extraction churns the diff."""
    rows = [iv("C", "2010-01-01"), iv("A", None), iv("B", "2005-01-01")]
    assert [r["identifier"] for r in sort_by_validity(rows)] == ["A", "B", "C"]


def test_ties_break_on_the_identifier():
    rows = [iv("B", "2010-01-01"), iv("A", "2010-01-01")]
    assert [r["identifier"] for r in sort_by_validity(rows)] == ["A", "B"]


def test_reversed_interval_is_detected():
    rows = [iv("M312", "2008-01-01", "2000-01-01"), iv("E667", None, "2008-01-01")]
    bad = reversed_intervals(rows)
    assert len(bad) == 1
    assert bad[0]["identifier"] == "M312"


def test_an_open_interval_is_not_reversed():
    assert reversed_intervals([iv("A069", "2006-01-01", None)]) == []


def test_building_an_interval_from_a_reversed_pair_raises():
    """Never sort the two dates into order.

    A reversed pair means the source is wrong about something; picking which
    end to trust would fabricate a validity period that was never published.
    """
    with pytest.raises(ReversedInterval):
        sort_by_validity([iv("X", "2008-01-01", "2000-01-01")], strict=True)


def test_a_record_with_no_identifiers_is_not_publishable():
    """MilanoT and RomaT are test rows left in production: typed comune, with
    no name, no identifier and no dates."""
    assert not is_publishable({"identifiers": [], "names": []})


def test_a_record_with_identifiers_is_publishable():
    assert is_publishable({"identifiers": [iv("A069")], "names": ["Aggius"]})
