"""Acceptance checks for the 2026.1 release, one per resolved issue."""

import json

import pytest

# The C1 control range, built with chr() rather than written literally: a test
# that detects mojibake must not carry the very bytes it looks for, or an
# encoding accident in this file would quietly disarm it.
C1_LOW = chr(0x80)
C1_HIGH = chr(0x9F)


@pytest.fixture(scope="module")
def comuni():
    return json.load(open("comuni.geojson"))["features"]


def test_municipality_count(comuni):
    """ISTAT publishes 7,896 municipalities at 1 January 2026."""
    assert len(comuni) == 7896


def test_issue_18_missing_municipalities_present(comuni):
    """The two municipalities whose absence produced holes in the maps."""
    names = {f["properties"]["name"] for f in comuni}
    assert "Bardello con Malgesso e Bregano" in names
    assert "Moransengo-Tonengo" in names


def test_issue_15_montecopiolo_and_sassofeltrio_codes(comuni):
    """Codes reported wrong since 2022."""
    codes = {
        f["properties"]["name"]: f["properties"]["com_istat_code"] for f in comuni
    }
    assert codes["Montecopiolo"] == "099030"
    assert codes["Sassofeltrio"] == "099031"


def test_issue_23_sardinian_provinces(comuni):
    """The 2026 reform: eight Sardinian units on codes 112-119."""
    sardinia = [f for f in comuni if f["properties"]["reg_istat_code_num"] == 20]
    assert len(sardinia) == 377
    codes = {f["properties"]["prov_istat_code_num"] for f in sardinia}
    assert codes == {112, 113, 114, 115, 116, 117, 118, 119}


def test_no_province_code_above_119(comuni):
    """The generation scripts loop up to the maximum; nothing may exceed it."""
    assert max(f["properties"]["prov_istat_code_num"] for f in comuni) == 119


def test_mojibake_fixed(comuni):
    """Two Slovene names carried cp1252-as-latin1 corruption.

    The 2023 release held U+009E where it meant U+017E and U+008A where it
    meant U+0160: cp1252 bytes decoded as latin-1. The escape in the guard
    below is deliberate -- writing those C1 characters literally would make
    this test vulnerable to the very corruption it detects.
    """
    names = {f["properties"]["name"] for f in comuni}
    assert "Duino Aurisina-Devin Nabrežina" in names
    assert "San Floriano del Collio-Števerjan" in names
    for name in names:
        assert not any(C1_LOW <= ch <= C1_HIGH for ch in name), name


def test_cadastral_codes_unique_and_complete(comuni):
    """The cadastral code is the join key for every future release."""
    codes = [f["properties"]["com_catasto_code"] for f in comuni]
    assert all(codes), "some municipality has no cadastral code"
    assert len(set(codes)) == len(codes), "cadastral codes are not unique"


def test_property_schema_unchanged(comuni):
    """Consumers must see exactly the documented property set.

    Checked on every feature, not on a sample: a single municipality carrying an
    extra or missing key is exactly the kind of defect that reaches a consumer
    before it reaches us.
    """
    expected = {
        "name", "com_catasto_code", "com_istat_code", "com_istat_code_num",
        "op_id", "opdm_id", "minint_elettorale", "minint_finloc",
        "prov_name", "prov_istat_code", "prov_istat_code_num", "prov_acr",
        "reg_name", "reg_istat_code", "reg_istat_code_num",
    }
    offenders = [
        f["properties"].get("name")
        for f in comuni
        if set(f["properties"]) != expected
    ]
    assert not offenders, f"{len(offenders)} features with a different schema: {offenders[:5]}"


def test_published_key_order_preserved(comuni):
    """The key order the published file has carried since 2019."""
    assert list(comuni[0]["properties"]) == [
        "name", "op_id", "minint_elettorale", "minint_finloc",
        "prov_name", "prov_istat_code", "prov_istat_code_num", "prov_acr",
        "reg_name", "reg_istat_code", "reg_istat_code_num",
        "opdm_id", "com_catasto_code", "com_istat_code", "com_istat_code_num",
    ]
