"""Acceptance checks for the 2026.2 release: ISO 3166-2 codes (issue #22)."""

import json

import pytest

from scripts.iso_3166_2 import UNCOVERED


@pytest.fixture(scope="module")
def comuni():
    return json.load(open("comuni.geojson"))["features"]


@pytest.fixture(scope="module")
def units(comuni):
    """One entry per second-level unit, keyed by its ISTAT code."""
    return {
        f["properties"]["prov_istat_code_num"]: f["properties"]
        for f in comuni
    }


@pytest.fixture(scope="module")
def regions(comuni):
    return {
        f["properties"]["reg_istat_code_num"]: f["properties"]
        for f in comuni
    }


def test_every_region_has_an_iso_code(regions):
    assert len(regions) == 20
    codes = {p["reg_iso_3166_2"] for p in regions.values()}
    assert len(codes) == 20
    assert None not in codes


def test_known_region_codes(regions):
    """Spot-checked against the standard: ISO's numbering is not ISTAT's."""
    assert regions[1]["reg_iso_3166_2"] == "IT-21"    # Piemonte
    assert regions[3]["reg_iso_3166_2"] == "IT-25"    # Lombardia
    assert regions[12]["reg_iso_3166_2"] == "IT-62"   # Lazio
    assert regions[20]["reg_iso_3166_2"] == "IT-88"   # Sardegna


def test_second_level_coverage(units):
    """105 of the 110 units carry a code; the five gaps are documented."""
    assert len(units) == 110
    covered = [p for p in units.values() if p["prov_iso_3166_2"]]
    assert len(covered) == 105

    uncovered_plates = {p["prov_acr"] for p in units.values()
                        if not p["prov_iso_3166_2"]}
    assert uncovered_plates == set(UNCOVERED)


def test_the_code_is_the_plate_prefixed(units):
    for p in units.values():
        if p["prov_iso_3166_2"]:
            assert p["prov_iso_3166_2"] == f"IT-{p['prov_acr']}"


def test_no_withdrawn_code_is_published(comuni):
    """IT-OT, IT-OG, IT-VS, IT-CI and IT-AO were deleted by ISO in 2019.

    The 2026 Sardinian reform created units bearing four of those plates, so
    the tempting fix is to emit the old codes. This test exists to make that
    regression fail loudly: a deleted code is not a standard identifier.
    """
    withdrawn = {f"IT-{plate}" for plate in UNCOVERED}
    published = {f["properties"]["prov_iso_3166_2"] for f in comuni}
    assert not (published & withdrawn)


def test_iso_codes_do_not_collide(units, regions):
    prov = [p["prov_iso_3166_2"] for p in units.values() if p["prov_iso_3166_2"]]
    assert len(set(prov)) == len(prov)
    reg = [p["reg_iso_3166_2"] for p in regions.values()]
    assert len(set(reg)) == len(reg)


def test_sardinian_municipalities_keep_their_region_code(comuni):
    """The provincial gap must not propagate to the region: IT-88 is valid and
    every Sardinian municipality carries it, including those in the four
    uncoded provinces."""
    sardinia = [f for f in comuni if f["properties"]["reg_istat_code_num"] == 20]
    assert len(sardinia) == 377
    assert {f["properties"]["reg_iso_3166_2"] for f in sardinia} == {"IT-88"}


def test_municipalities_without_a_provincial_code(comuni):
    """175 municipalities sit in the five uncoded units. Asserted so that a
    change in that number is noticed rather than discovered by a consumer."""
    n = sum(1 for f in comuni if not f["properties"]["prov_iso_3166_2"])
    assert n == 175
