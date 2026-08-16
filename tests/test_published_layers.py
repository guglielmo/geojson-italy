"""Checks across the published layers, not within one file.

The defects these catch are the ones no single file reveals: a municipality
present in one output and missing from another, a property that never reached
the dissolved layers, a metropolitan-city file that quietly lists provinces.
"""

import json

import pytest


def load(path):
    return json.load(open(path))


@pytest.fixture(scope="module")
def municipalities():
    return load("geojson/limits_IT_municipalities.geojson")["features"]


@pytest.fixture(scope="module")
def provinces():
    return load("geojson/limits_IT_provinces.geojson")["features"]


@pytest.fixture(scope="module")
def all_layers():
    return load("topojson/limits_IT_all.topo.json")["objects"]


def test_issue_34_the_combined_topojson_keeps_every_municipality(
        municipalities, all_layers):
    """limits_IT_all.topo.json carried one municipality fewer than every other
    output — Miagliano, 0.7 km² in Biella, and one municipality in the 2023
    release before it.

    The cause was a second -clean applied *after* simplification: it drops a
    polygon simplification has left degenerate, and reports nothing. The layer
    counts are compared here because that is the only way the loss is visible.
    """
    assert len(all_layers["municipalities"]["geometries"]) == len(municipalities)


def test_the_three_layers_agree_on_the_provinces(provinces, all_layers):
    assert len(all_layers["provinces"]["geometries"]) == len(provinces)


def test_the_dissolved_layers_carry_the_uts_properties(provinces):
    """Only copy-fields survives a dissolve, so a new property has to be added
    to both generation scripts or it silently never arrives."""
    props = provinces[0]["properties"]
    assert "prov_tipo_uts" in props
    assert "prov_uts_code" in props


def test_every_second_level_unit_has_a_type():
    provinces = load("geojson/limits_IT_provinces.geojson")["features"]
    missing = [p["properties"]["prov_name"] for p in provinces
               if not p["properties"].get("prov_tipo_uts")]
    assert not missing, f"{len(missing)} units without a type: {missing[:5]}"


def test_the_metropolitan_city_layer_holds_only_metropolitan_cities():
    cities = load("geojson/limits_IT_metropolitan_cities.geojson")["features"]
    assert len(cities) == 15, "14 instituted from 2015 to 2017, Sassari in 2026"
    assert {c["properties"]["prov_tipo_uts"] for c in cities} == \
        {"Città metropolitana"}


def test_the_metropolitan_cities_are_also_in_the_provinces_file(provinces):
    """The new layer is additive. Metropolitan cities are second-level units
    and have always been in limits_IT_provinces; moving them out would break
    every consumer counting 110 units."""
    cities = load("geojson/limits_IT_metropolitan_cities.geojson")["features"]
    names = {p["properties"]["prov_name"] for p in provinces}
    assert {c["properties"]["prov_name"] for c in cities} <= names
    assert len(provinces) == 110
