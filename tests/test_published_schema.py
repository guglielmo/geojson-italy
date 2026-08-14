"""The property schema of the published comuni.geojson.

Kept apart from the per-release acceptance checks: this describes the current
published format, which outlives any one release, and it is the file to change
deliberately when the schema changes.
"""

import json

import pytest

PUBLISHED_KEY_ORDER = [
    "name", "op_id", "minint_elettorale", "minint_finloc",
    "prov_name", "prov_istat_code", "prov_istat_code_num", "prov_acr",
    "prov_iso_3166_2",
    "reg_name", "reg_istat_code", "reg_istat_code_num", "reg_iso_3166_2",
    "opdm_id", "com_catasto_code", "com_istat_code", "com_istat_code_num",
]


@pytest.fixture(scope="module")
def comuni():
    return json.load(open("comuni.geojson"))["features"]


def test_property_schema(comuni):
    """Consumers must see exactly the documented property set.

    Checked on every feature, not on a sample: a single municipality carrying
    an extra or missing key is exactly the kind of defect that reaches a
    consumer before it reaches us.
    """
    expected = set(PUBLISHED_KEY_ORDER)
    offenders = [
        f["properties"].get("name")
        for f in comuni
        if set(f["properties"]) != expected
    ]
    assert not offenders, f"{len(offenders)} features with a different schema: {offenders[:5]}"


def test_published_key_order_preserved(comuni):
    """The key order the published file has carried since 2019, with the ISO
    codes inserted next to the ISTAT codes they qualify."""
    assert list(comuni[0]["properties"]) == PUBLISHED_KEY_ORDER


def test_mandatory_fields_are_never_null(comuni):
    """Everything except the identifiers that are legitimately absent.

    `prov_iso_3166_2` is excluded because ISO does not cover five of the 110
    units; the legacy identifiers are excluded because a municipality created
    after the previous release has none.
    """
    mandatory = [
        "name", "prov_name", "prov_istat_code", "prov_istat_code_num",
        "prov_acr", "reg_name", "reg_istat_code", "reg_istat_code_num",
        "reg_iso_3166_2", "com_catasto_code", "com_istat_code",
        "com_istat_code_num",
    ]
    for field in mandatory:
        missing = [f["properties"]["name"] for f in comuni
                   if f["properties"].get(field) in (None, "")]
        assert not missing, f"{field} empty on {len(missing)}: {missing[:5]}"
