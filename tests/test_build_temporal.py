"""Tests for the roster-to-geometry join (issue #25).

The rule under test is which edition describes a date. Getting it wrong is not
a crash: it silently publishes one date's boundaries under another's, which is
what D2 exists to prevent.
"""

import json

import pytest

from scripts.build_temporal import (
    NoApplicableEdition,
    applicable_edition,
    join,
    read_edition_geometries,
)

SQUARE = {"type": "Polygon", "coordinates": [[[7.0, 45.0], [7.1, 45.0],
                                              [7.1, 45.1], [7.0, 45.0]]]}

ROSTER_ROW = {
    "COD_REG": "01",
    "COD_UTS": "001",
    "PRO_COM_T": "001001",
    "COMUNE_IT": "Agliè",
    "DEN_UTS": "Torino",
    "DEN_REG": "Piemonte",
    "TIPO_UTS": 1,
    "SIGLA_AUTOMOBILISTICA": "TO",
    "COD_CATASTO": "A074",
}


def test_an_annual_date_takes_its_own_edition():
    assert applicable_edition("2019-01-01") == 2019
    assert applicable_edition("2019-05-31") == 2019


def test_a_date_before_the_census_takes_the_previous_edition():
    """11 February 2011 is served by the 2010 edition, not the 2011 one.

    The 2011 edition is census cartography describing 9 October 2011: it did
    not exist yet at the date being published, and it already carries Gravedona
    ed Uniti in place of the three municipalities valid in February.
    """
    assert applicable_edition("2011-02-11") == 2010
    assert applicable_edition("2011-10-09") == 2011
    assert applicable_edition("2011-12-31") == 2011


def test_a_date_before_the_first_edition_is_refused():
    """No geometry exists for the first nine months of 2001, and none is
    invented from the 1991 census."""
    with pytest.raises(NoApplicableEdition):
        applicable_edition("2001-10-20")


def test_the_join_carries_the_source_edition(tmp_path):
    rosters = tmp_path / "rosters"
    rosters.mkdir()
    (rosters / "2026-01-01.json").write_text(json.dumps({"resultset": [ROSTER_ROW]}))
    editions = tmp_path / "editions"
    (editions / "2026").mkdir(parents=True)
    (editions / "2026" / "comuni.geojson").write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"PRO_COM_T": "001001"},
                      "geometry": SQUARE}],
    }))

    features, missing, orphans = join("2026-01-01", root=editions,
                                      roster_root=rosters)
    assert (missing, orphans) == ([], [])
    assert features[0]["properties"]["source_edition"] == "Limiti01012026_g"
    assert features[0]["geometry"] == SQUARE


def test_a_municipality_without_geometry_is_reported_not_dropped(tmp_path):
    """The intra-year case: created after the edition was published.

    It must surface as a residual to be resolved by the rules in §6, never as a
    feature quietly missing from the output.
    """
    rosters = tmp_path / "rosters"
    rosters.mkdir()
    (rosters / "2026-01-01.json").write_text(json.dumps({"resultset": [
        ROSTER_ROW, {**ROSTER_ROW, "PRO_COM_T": "001002",
                     "COMUNE_IT": "Nuovo", "COD_CATASTO": "M999"}]}))
    editions = tmp_path / "editions"
    (editions / "2026").mkdir(parents=True)
    (editions / "2026" / "comuni.geojson").write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"PRO_COM_T": "001001"},
                      "geometry": SQUARE}],
    }))

    features, missing, orphans = join("2026-01-01", root=editions,
                                      roster_root=rosters)
    assert len(features) == 1
    assert [m["com_istat_code"] for m in missing] == ["001002"]
    assert orphans == []


def test_a_geometry_without_a_municipality_is_reported(tmp_path):
    rosters = tmp_path / "rosters"
    rosters.mkdir()
    (rosters / "2026-01-01.json").write_text(json.dumps({"resultset": [ROSTER_ROW]}))
    editions = tmp_path / "editions"
    (editions / "2026").mkdir(parents=True)
    (editions / "2026" / "comuni.geojson").write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"PRO_COM_T": "001001"},
             "geometry": SQUARE},
            {"type": "Feature", "properties": {"PRO_COM_T": 1002},
             "geometry": SQUARE},
        ],
    }))

    _, _, orphans = join("2026-01-01", root=editions, roster_root=rosters)
    assert orphans == ["001002"]


def test_edition_codes_are_padded(tmp_path):
    """The edition serialises some codes as numbers too."""
    (tmp_path / "2026").mkdir()
    (tmp_path / "2026" / "comuni.geojson").write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"PRO_COM": 1001},
                      "geometry": SQUARE}],
    }))
    assert list(read_edition_geometries(2026, root=tmp_path)) == ["001001"]
