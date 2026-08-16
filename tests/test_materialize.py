"""Tests for materialising the archive into file sets (issue #28).

Two things decide whether a consumer gets the right file: how a year or a date
resolves to a release, and whether the index describes what happened on it.
Both are pure and tested here; the mapshaper chain is exercised by the build.
"""

import json

import pytest

from scripts.materialize import index_rows, resolve

CALENDAR = ["2001-10-21", "2005-01-01", "2005-05-04", "2005-05-11",
            "2006-01-01", "2026-01-01"]


def test_a_bare_year_means_its_first_of_january():
    """What someone asking for "the 2005 boundaries" almost always means.

    2005 holds three publication dates. Refusing to answer would be pedantic
    and guessing the wrong one would be silent, so the convention is stated:
    a year is its 1 January, and INDEX.csv serves the exact dates.
    """
    assert resolve("2005", CALENDAR) == "2005-01-01"
    assert resolve(2005, CALENDAR) == "2005-01-01"


def test_an_exact_date_resolves_to_the_release_covering_it():
    assert resolve("2005-06-30", CALENDAR) == "2005-05-11"
    assert resolve("2005-05-04", CALENDAR) == "2005-05-04"
    assert resolve("2005-05-03", CALENDAR) == "2005-01-01"


def test_a_date_before_the_series_is_refused():
    """No geometry exists before the 2001 census edition, and none is
    fabricated from the year the consumer happened to ask for."""
    with pytest.raises(ValueError):
        resolve("1999-01-01", CALENDAR)


def test_a_year_before_the_series_is_refused():
    with pytest.raises(ValueError):
        resolve("1998", CALENDAR)


def _dataset(tmp_path, versions):
    (tmp_path / "reg=01.geojson").write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": props,
                      "geometry": None} for props in versions],
    }))
    return tmp_path


def version(key, frm, to, reason="source_regeneralization"):
    return {"terr_key": key, "valid_from": frm, "valid_to": to,
            "version_reason": reason}


def test_the_index_counts_the_municipalities_valid_at_each_date(tmp_path):
    root = _dataset(tmp_path, [
        version("A001", "2001-10-21", None),
        version("A002", "2001-10-21", "2005-01-01"),
    ])
    rows = {row["valid_from"]: row for row in
            index_rows(["2001-10-21", "2005-01-01"], root=root)}
    assert rows["2001-10-21"]["municipalities"] == 2
    assert rows["2005-01-01"]["municipalities"] == 1


def test_the_index_names_the_release_and_closes_each_interval(tmp_path):
    root = _dataset(tmp_path, [version("A001", "2001-10-21", None)])
    rows = index_rows(["2001-10-21", "2005-01-01"], root=root)
    assert rows[0]["valid_to"] == "2005-01-01"
    assert rows[0]["release_tag"] == "2001-10-21"
    assert rows[-1]["valid_to"] == "", "the current interval stays open"


def test_a_suppression_is_reported_even_when_no_version_begins(tmp_path):
    """Lirio into Montalto Pavese, 31 January 2026: the survivor's attributes
    and geometry are unchanged until the next edition, so counting only the
    versions that begin reports no change on the day a municipality vanished.
    """
    root = _dataset(tmp_path, [
        version("A001", "2001-10-21", None),
        version("A002", "2001-10-21", "2005-01-01"),
    ])
    rows = {row["valid_from"]: row for row in
            index_rows(["2001-10-21", "2005-01-01"], root=root)}
    assert rows["2005-01-01"]["change"] == "1 soppressi"


def test_an_ordinary_version_change_is_not_counted_as_a_suppression(tmp_path):
    root = _dataset(tmp_path, [
        version("A001", "2001-10-21", "2005-01-01"),
        version("A001", "2005-01-01", None, "admin_riassegnazione"),
    ])
    rows = {row["valid_from"]: row for row in
            index_rows(["2001-10-21", "2005-01-01"], root=root)}
    assert rows["2005-01-01"]["change"] == "1 admin_riassegnazione"


def test_a_municipality_that_returns_is_counted_at_both_events(tmp_path):
    """Baranzate: abolished in 2003, re-established in 2004."""
    root = _dataset(tmp_path, [
        version("A618", "2001-10-21", "2005-01-01", "admin_scissione"),
        version("A618", "2006-01-01", None, "admin_scissione"),
    ])
    rows = {row["valid_from"]: row for row in
            index_rows(["2001-10-21", "2005-01-01", "2006-01-01"], root=root)}
    assert rows["2005-01-01"]["change"] == "1 soppressi"
    assert rows["2006-01-01"]["change"] == "1 admin_scissione"


def test_a_regeneralisation_is_not_described_as_a_change(tmp_path):
    """ISTAT redrawing its own lines is not an administrative event, and
    listing it would bury the dates where something actually happened."""
    root = _dataset(tmp_path, [
        version("A001", "2001-10-21", "2005-01-01"),
        version("A001", "2005-01-01", None),
    ])
    rows = {row["valid_from"]: row for row in
            index_rows(["2001-10-21", "2005-01-01"], root=root)}
    assert rows["2005-01-01"]["change"] == "no administrative change"
