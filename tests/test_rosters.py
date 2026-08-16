"""Tests for reading the ISTAT roster (issue #25).

Every test here is offline and works on literal records, because the failures
worth catching are the ones that produce a plausible result: a code that loses
its leading zeros and stops matching the geometry, a NUTS column whose name
changed vintage, a UTS type nobody has a label for.
"""

import json

import pytest

from scripts.rosters import (
    TIPO_UTS_LABELS,
    UnknownUtsType,
    attributes,
    istat_code,
    read_roster,
)

AGLIE = {
    "COD_REG": "01",
    "COD_UTS": "201",
    "PRO_COM_T": "001001",
    "COMUNE": "Agliè",
    "COMUNE_IT": "Agliè",
    "DEN_UTS": "Torino",
    "DEN_REG": "Piemonte",
    "TIPO_UTS": 3,
    "SIGLA_AUTOMOBILISTICA": "TO",
    "COD_CATASTO": "A074",
    "COM_NUTS3_2024": "ITC11",
}


def test_a_numeric_code_keeps_its_leading_zeros():
    """SITUAS serialises 001001 as the string and 103025 as a number.

    Joined to the geometry without padding, every code that starts with a zero
    fails to match and the result reads as missing municipalities.
    """
    assert istat_code(103025) == "103025"
    assert istat_code(1001) == "001001"
    assert istat_code(" 001001 ") == "001001"


def test_a_bilingual_municipality_keeps_the_form_istat_publishes():
    """Bolzano/Bozen, not Bolzano.

    The boundary editions and this repository both carry the bilingual form,
    on 124 municipalities. Taking the Italian half instead renames them all,
    which for a consumer joining on the name is a break, not a tidy-up.
    """
    props = attributes({**AGLIE, "COMUNE": "Bolzano/Bozen",
                        "COMUNE_IT": "Bolzano", "COMUNE_A": "Bozen"})
    assert props["name"] == "Bolzano/Bozen"
    assert props["name_it"] == "Bolzano"
    assert props["name_other"] == "Bozen"


def test_attributes_use_the_published_property_names():
    props = attributes(AGLIE)
    assert props["name"] == "Agliè"
    assert props["com_istat_code"] == "001001"
    assert props["com_istat_code_num"] == 1001
    assert props["com_catasto_code"] == "A074"
    assert props["reg_istat_code"] == "01"
    assert props["reg_name"] == "Piemonte"


def test_the_province_code_comes_from_the_municipality_code():
    """COD_PROV_STORICO is absent from the older rosters; PRO_COM_T never is.

    It also keeps this repository on the COD_PROV family — Rome is 058, not
    258 — while COD_UTS is carried separately.
    """
    props = attributes(AGLIE)
    assert props["prov_istat_code"] == "001"
    assert props["prov_istat_code_num"] == 1
    assert props["prov_uts_code"] == "201"


def test_the_uts_type_is_resolved_to_its_published_label():
    assert attributes(AGLIE)["prov_tipo_uts"] == "Città metropolitana"
    assert TIPO_UTS_LABELS[1] == "Provincia"


def test_an_unknown_uts_type_raises():
    with pytest.raises(UnknownUtsType):
        attributes({**AGLIE, "TIPO_UTS": 9})


def test_nuts_is_matched_by_prefix_across_vintages():
    """The column is COM_NUTS3_2006, _2010, _2021 or _2024 depending on date."""
    older = {k: v for k, v in AGLIE.items() if not k.startswith("COM_NUTS")}
    assert attributes({**older, "COM_NUTS3_2006": "ITC11"})["com_nuts3"] == "ITC11"
    assert attributes(older)["com_nuts3"] is None


def test_reading_a_roster_keys_on_the_istat_code(tmp_path):
    (tmp_path / "2026-01-01.json").write_text(
        json.dumps({"resultset": [AGLIE, {**AGLIE, "PRO_COM_T": 1002,
                                          "COMUNE": "Airasca",
                                          "COMUNE_IT": "Airasca",
                                          "COD_CATASTO": "A109"}]})
    )
    roster = read_roster("2026-01-01", root=tmp_path)
    assert sorted(roster) == ["001001", "001002"]
    assert roster["001002"]["name"] == "Airasca"


def test_a_duplicated_code_in_one_roster_raises(tmp_path):
    """Two rows for one code at one date would silently drop a municipality."""
    (tmp_path / "2026-01-01.json").write_text(
        json.dumps({"resultset": [AGLIE, AGLIE]})
    )
    with pytest.raises(ValueError):
        read_roster("2026-01-01", root=tmp_path)
