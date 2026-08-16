"""Tests for the roster-to-geometry join (issue #25).

The rule under test is which edition describes a date. Getting it wrong is not
a crash: it silently publishes one date's boundaries under another's, which is
what D2 exists to prevent.
"""

import json

import pytest

from scripts.build_temporal import (
    NoApplicableEdition,
    UnresolvedGeometry,
    applicable_edition,
    assemble,
    join,
    read_edition_geometries,
    resolve_geometry,
    write_regions,
)

SQUARE = {"type": "Polygon", "coordinates": [[[7.0, 45.0], [7.1, 45.0],
                                              [7.1, 45.1], [7.0, 45.0]]]}
NUDGED = {"type": "Polygon", "coordinates": [[[7.0, 45.0], [7.1, 45.0],
                                              [7.1, 45.100000001], [7.0, 45.0]]]}

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


def test_a_reassigned_municipality_still_finds_its_geometry(tmp_path):
    """Aggius moves from province 090 to 104 on 28 April 2016.

    Its ISTAT code changes with the province, while the applicable edition —
    1 January 2016 — still carries the old one. Joined on the ISTAT code the
    municipality vanishes from every date until the next January; joined on
    identity it does not. Measured before the fix: 310 municipalities lost this
    way, against the 39 the design predicts for genuine intra-year creations.
    """
    before = {**ROSTER_ROW, "PRO_COM_T": "090001", "COD_UTS": "090",
              "COD_CATASTO": "A069", "COMUNE_IT": "Aggius"}
    after = {**before, "PRO_COM_T": "104001", "COD_UTS": "104"}
    rosters = tmp_path / "rosters"
    rosters.mkdir()
    (rosters / "2016-01-01.json").write_text(json.dumps({"resultset": [before]}))
    (rosters / "2016-04-28.json").write_text(json.dumps({"resultset": [after]}))
    editions = tmp_path / "editions"
    (editions / "2016").mkdir(parents=True)
    (editions / "2016" / "comuni.geojson").write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"PRO_COM_T": "090001"},
                      "geometry": SQUARE}],
    }))

    features, missing, orphans = join("2016-04-28", root=editions,
                                      roster_root=rosters)
    assert (missing, orphans) == ([], [])
    assert features[0]["properties"]["com_istat_code"] == "104001"
    assert features[0]["properties"]["terr_key"] == "A069"
    assert features[0]["geometry"] == SQUARE


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


def _fixture(tmp_path, rosters_by_date, geometries_by_year):
    """Write rosters and editions to disk, as the build reads them."""
    rosters = tmp_path / "rosters"
    rosters.mkdir()
    for at, records in rosters_by_date.items():
        (rosters / f"{at}.json").write_text(json.dumps({"resultset": records}))
    editions = tmp_path / "editions"
    for year, geometries in geometries_by_year.items():
        (editions / str(year)).mkdir(parents=True)
        (editions / str(year) / "comuni.geojson").write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {"PRO_COM_T": code},
                          "geometry": geometry}
                         for code, geometry in geometries.items()],
        }))
    return rosters, editions


def test_an_unchanged_municipality_is_one_version_across_editions(tmp_path):
    """Exact-equality collapsing: ISTAT republishing the same shape is not a
    new version, and the interval names the edition where it began."""
    rosters, editions = _fixture(
        tmp_path,
        {"2025-01-01": [ROSTER_ROW], "2026-01-01": [ROSTER_ROW]},
        {2025: {"001001": SQUARE}, 2026: {"001001": SQUARE}},
    )
    assembled = assemble(["2025-01-01", "2026-01-01"], {}, {},
                         root=editions, roster_root=rosters)
    versions = assembled["A074"]
    assert len(versions) == 1
    assert versions[0]["valid_from"] == "2025-01-01"
    assert versions[0]["valid_to"] is None
    assert versions[0]["source_edition"] == "Limiti01012025_g"


def test_a_geometry_changed_by_a_hair_is_a_second_version(tmp_path):
    """No tolerance, at any scale: D2 forbids publishing one edition's shape
    under another edition's date."""
    rosters, editions = _fixture(
        tmp_path,
        {"2025-01-01": [ROSTER_ROW], "2026-01-01": [ROSTER_ROW]},
        {2025: {"001001": SQUARE}, 2026: {"001001": NUDGED}},
    )
    assembled = assemble(["2025-01-01", "2026-01-01"], {}, {},
                         root=editions, roster_root=rosters)
    versions = assembled["A074"]
    assert [(v["valid_from"], v["valid_to"]) for v in versions] == [
        ("2025-01-01", "2026-01-01"), ("2026-01-01", None)
    ]
    assert versions[1]["source_edition"] == "Limiti01012026_g"


def test_a_recoded_municipality_keeps_one_key(tmp_path):
    """The Lonato case, and the Sardinian reform in miniature: the cadastral
    code changes, the entity does not."""
    later = {**ROSTER_ROW, "COD_CATASTO": "M312", "COMUNE_IT": "Lonato del Garda"}
    rosters, editions = _fixture(
        tmp_path,
        {"2025-01-01": [ROSTER_ROW], "2026-01-01": [later]},
        {2025: {"001001": SQUARE}, 2026: {"001001": SQUARE}},
    )
    assembled = assemble(["2025-01-01", "2026-01-01"], {"A074": "M312"}, {},
                         root=editions, roster_root=rosters)
    assert sorted(assembled) == ["A074"]
    versions = assembled["A074"]
    assert len(versions) == 2, "the name and code changed, so the version did"
    assert versions[1]["properties"]["com_catasto_code"] == "M312"


def test_regions_are_written_by_the_region_of_each_version(tmp_path):
    """A municipality moved between regions has versions in both files.

    Montecopiolo and Sassofeltrio left the Marche for Emilia-Romagna in 2021;
    filing every version under the current region would misplace the earlier
    ones.
    """
    moved = {**ROSTER_ROW, "COD_REG": "08", "DEN_REG": "Emilia-Romagna"}
    rosters, editions = _fixture(
        tmp_path,
        {"2025-01-01": [ROSTER_ROW], "2026-01-01": [moved]},
        {2025: {"001001": SQUARE}, 2026: {"001001": SQUARE}},
    )
    assembled = assemble(["2025-01-01", "2026-01-01"], {}, {},
                         root=editions, roster_root=rosters)
    written = write_regions(assembled, out=tmp_path / "temporal", root=editions)
    assert sorted(written) == ["01", "08"]

    early = json.loads((tmp_path / "temporal" / "reg=01.geojson").read_text())
    assert early["features"][0]["properties"]["valid_to"] == "2026-01-01"
    assert early["features"][0]["geometry"] == SQUARE


def test_a_detached_municipality_takes_the_next_edition_that_carries_it(tmp_path):
    """Mappano, Misiliscemi, Baranzate: the predecessor survives with a reduced
    area, so the new boundary cannot be derived from it and is anticipated from
    the next edition instead. The provenance string says so."""
    rosters, editions = _fixture(
        tmp_path,
        {"2025-01-01": [ROSTER_ROW],
         "2026-01-01": [ROSTER_ROW]},
        {2025: {"001001": SQUARE},
         2026: {"001001": SQUARE, "001002": NUDGED}},
    )
    (rosters / "2026-01-01.json").write_text(json.dumps({"resultset": [
        ROSTER_ROW, {**ROSTER_ROW, "PRO_COM_T": "001002",
                     "COMUNE_IT": "Nuovo", "COD_CATASTO": "M999"}]}))
    born = {"M999": [{"date": "2025-06-01", "kind": "detachment",
                      "predecessors": ["A074"]}]}
    geometry, provenance = resolve_geometry(
        "M999", "2025-06-01", 2025, {"A074": SQUARE}, born, {},
        root=editions, roster_root=rosters)
    assert geometry == NUDGED
    assert provenance == "Limiti01012026_g (anticipated)"


def test_a_municipality_with_no_recorded_creation_raises(tmp_path):
    """The design's instruction: never fall back silently. A fabricated
    boundary in a public archive would carry ISTAT's authority."""
    with pytest.raises(UnresolvedGeometry):
        resolve_geometry("M999", "2025-06-01", 2025, {}, {}, {},
                         root=tmp_path, roster_root=tmp_path)


def test_edition_codes_are_padded(tmp_path):
    """The edition serialises some codes as numbers too."""
    (tmp_path / "2026").mkdir()
    (tmp_path / "2026" / "comuni.geojson").write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"PRO_COM": 1001},
                      "geometry": SQUARE}],
    }))
    assert list(read_edition_geometries(2026, root=tmp_path)) == ["001001"]
