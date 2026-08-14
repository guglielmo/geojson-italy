"""Tests for the edition measurements (issue #24).

The load-bearing test here is the one proving interval collapsing is
byte-exact. Design decision D2 forbids tolerance-based merging: collapsing two
geometries that differ slightly would publish one edition's shape under another
edition's date, which is precisely the kind of quiet reinterpretation the
archive exists to avoid.
"""

from scripts.measure_editions import (
    changed_between,
    collapse_to_intervals,
    geometry_digest,
)

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[7.0, 45.0], [7.1, 45.0], [7.1, 45.1], [7.0, 45.1], [7.0, 45.0]]],
}

# The same square with one vertex moved by 1e-9 degrees, roughly a tenth of a
# millimetre — far below any plausible tolerance.
NUDGED = {
    "type": "Polygon",
    "coordinates": [[[7.0, 45.0], [7.1, 45.0], [7.1, 45.100000001],
                     [7.0, 45.1], [7.0, 45.0]]],
}


def test_identical_geometry_hashes_identically():
    assert geometry_digest(SQUARE) == geometry_digest(dict(SQUARE))


def test_a_sub_millimetre_difference_is_a_different_version():
    """No tolerance, at any scale."""
    assert geometry_digest(SQUARE) != geometry_digest(NUDGED)


def test_collapsing_merges_only_byte_identical_runs():
    series = {
        2001: {"001001": geometry_digest(SQUARE)},
        2002: {"001001": geometry_digest(SQUARE)},
        2003: {"001001": geometry_digest(SQUARE)},
    }
    versions, instances = collapse_to_intervals(series)
    assert instances == 3
    assert versions == 1


def test_collapsing_keeps_a_nudged_geometry_as_its_own_version():
    series = {
        2001: {"001001": geometry_digest(SQUARE)},
        2002: {"001001": geometry_digest(NUDGED)},
        2003: {"001001": geometry_digest(NUDGED)},
    }
    versions, instances = collapse_to_intervals(series)
    assert instances == 3
    assert versions == 2, "a sub-millimetre change must not be collapsed away"


def test_a_geometry_that_returns_to_a_previous_shape_is_a_new_version():
    """A->B->A is three versions, not two.

    The archive stores versions by validity period, so a shape that comes back
    after a change occupies a new interval. Deduplicating by value across
    non-consecutive editions would lose the fact that it changed and changed
    back.
    """
    series = {
        2001: {"001001": geometry_digest(SQUARE)},
        2002: {"001001": geometry_digest(NUDGED)},
        2003: {"001001": geometry_digest(SQUARE)},
    }
    versions, _ = collapse_to_intervals(series)
    assert versions == 3


def test_changed_between_ignores_municipalities_absent_from_one_edition():
    """A municipality that did not exist yet has not 'changed'."""
    a = {"001001": "aaa", "001002": "bbb"}
    b = {"001001": "zzz", "001003": "ccc"}
    assert changed_between(a, b) == {"001001"}


def test_collapsing_handles_municipalities_appearing_mid_series():
    series = {
        2001: {"001001": "a"},
        2002: {"001001": "a", "001002": "b"},
        2003: {"001001": "a", "001002": "b"},
    }
    versions, instances = collapse_to_intervals(series)
    assert instances == 5
    assert versions == 2
