"""Tests for the ISO 3166-2:IT reference data (issue #22)."""

import json

import pytest

from scripts.iso_3166_2 import (
    UNCOVERED,
    province_iso_code,
    region_iso_code,
)

ISO_CODES_JSON = "/usr/share/iso-codes/json/iso_3166-2.json"


def test_region_codes_are_not_the_istat_codes():
    """ISO numbers the regions on its own scheme, unrelated to ISTAT's.

    This is the whole reason a lookup table exists: Piedmont is ISTAT 01 and
    ISO IT-21, so deriving one from the other is impossible.
    """
    assert region_iso_code(1) == "IT-21"   # Piemonte
    assert region_iso_code(3) == "IT-25"   # Lombardia
    assert region_iso_code(12) == "IT-62"  # Lazio
    assert region_iso_code(20) == "IT-88"  # Sardegna


def test_every_istat_region_has_a_distinct_code():
    codes = {region_iso_code(n) for n in range(1, 21)}
    assert len(codes) == 20
    assert all(c.startswith("IT-") for c in codes)


def test_unknown_region_raises():
    """A region code outside 1-20 is a data error, not a missing code."""
    with pytest.raises(KeyError):
        region_iso_code(21)


def test_province_code_is_the_vehicle_plate_prefixed():
    assert province_iso_code("TO") == "IT-TO"
    assert province_iso_code("RM") == "IT-RM"
    assert province_iso_code("BZ") == "IT-BZ"


def test_friulian_entities_are_valid_again():
    """Deleted in April 2019, restored in November 2020 as decentralized
    regional entities. ISTAT still carries them as non-administrative units,
    but ISO has a code for them, so we publish it."""
    for sigla in ("GO", "PN", "TS", "UD"):
        assert province_iso_code(sigla) == f"IT-{sigla}"


def test_the_four_sardinian_units_have_no_code():
    """IT-OT, IT-OG, IT-VS and IT-CI were deleted in April 2019 and never
    restored. The 2026 reform created units bearing the same vehicle plates,
    but ISO has not registered them, so there is no standard code to publish.
    Emitting the withdrawn codes would be inventing an identifier."""
    for sigla in ("OT", "OG", "VS", "CI"):
        assert province_iso_code(sigla) is None


def test_valle_d_aosta_has_no_second_level_code():
    """IT-AO was deleted in November 2019: the region exercises provincial
    functions itself, so there is no province to code. ISTAT keeps COD_PROV
    007 for statistical continuity, which is why this looks like a gap."""
    assert province_iso_code("AO") is None


def test_uncovered_documents_exactly_the_gaps():
    assert set(UNCOVERED) == {"AO", "OT", "OG", "VS", "CI"}
    assert all(province_iso_code(s) is None for s in UNCOVERED)


def test_unknown_plate_yields_none_rather_than_a_guess():
    """A plate ISO does not list gets no code. Never fabricate one."""
    assert province_iso_code("ZZ") is None
    assert province_iso_code("") is None
    assert province_iso_code(None) is None


def test_sud_sardegna_is_still_a_valid_iso_code():
    """IT-SU remains in the standard even though the 2026 vintage has no unit
    for it: Sud Sardegna was abolished. Kept so the table stays a faithful
    record of ISO, not of our data."""
    assert province_iso_code("SU") == "IT-SU"


@pytest.mark.skipif(
    not __import__("os").path.exists(ISO_CODES_JSON),
    reason="iso-codes package not installed",
)
def test_table_matches_the_iso_codes_package():
    """The tables here must reproduce the machine-readable standard exactly.

    Hand-maintained reference data drifts. This check fails the build when it
    does, against the same source the tables were extracted from.
    """
    src = json.load(open(ISO_CODES_JSON))
    it = [s for s in src["3166-2"] if s["code"].startswith("IT-")]
    region_types = {"Region", "Autonomous region"}

    iso_regions = {s["code"] for s in it if s["type"] in region_types}
    ours = {region_iso_code(n) for n in range(1, 21)}
    assert ours == iso_regions

    iso_plates = {
        s["code"].split("-")[1] for s in it if s["type"] not in region_types
    }
    assert len(iso_plates) == 106
    for plate in iso_plates:
        assert province_iso_code(plate) == f"IT-{plate}"
    for plate in UNCOVERED:
        assert plate not in iso_plates
