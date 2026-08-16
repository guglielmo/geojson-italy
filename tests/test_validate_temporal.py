"""Tests for the archive's validation checks (issue #30).

A check that cannot fail is worse than no check, so these test the failures:
an overlap must be reported, a gap must not be, and two versions valid on one
date must raise rather than be counted once.
"""

import pytest

from scripts.validate_temporal import by_key, interval_problems, valid_at


def version(key, frm, to, code="001001"):
    return {"terr_key": key, "valid_from": frm, "valid_to": to,
            "com_istat_code": code}


def test_meeting_intervals_are_clean():
    grouped = by_key([version("A074", "2019-01-01", "2020-01-01"),
                      version("A074", "2020-01-01", None)])
    assert interval_problems(grouped) == []


def test_an_overlap_is_reported():
    grouped = by_key([version("A074", "2019-01-01", "2021-01-01"),
                      version("A074", "2020-01-01", None)])
    assert len(interval_problems(grouped)) == 1


def test_an_interval_left_open_before_another_is_reported():
    grouped = by_key([version("A074", "2019-01-01", None),
                      version("A074", "2020-01-01", None)])
    assert len(interval_problems(grouped)) == 1


def test_a_gap_is_not_a_problem():
    """Baranzate did not exist between 2003 and 2004. Closing that gap would
    publish a municipality that had been abolished."""
    grouped = by_key([version("A618", "2001-12-12", "2003-03-06"),
                      version("A618", "2004-06-08", None)])
    assert interval_problems(grouped) == []


def test_valid_at_selects_one_version_per_entity():
    grouped = by_key([version("A074", "2019-01-01", "2020-01-01"),
                      version("A074", "2020-01-01", None)])
    assert valid_at(grouped, "2019-06-01")["A074"]["valid_to"] == "2020-01-01"
    assert valid_at(grouped, "2020-01-01")["A074"]["valid_to"] is None


def test_valid_at_excludes_an_entity_in_its_gap():
    grouped = by_key([version("A618", "2001-12-12", "2003-03-06"),
                      version("A618", "2004-06-08", None)])
    assert valid_at(grouped, "2004-01-01") == {}


def test_two_versions_valid_at_one_date_raise():
    """The interval filter consumers are told to use would return both."""
    grouped = by_key([version("A074", "2019-01-01", "2021-01-01"),
                      version("A074", "2020-01-01", None)])
    with pytest.raises(AssertionError):
        valid_at(grouped, "2020-06-01")
