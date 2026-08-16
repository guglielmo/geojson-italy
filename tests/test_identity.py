"""Tests for the identity rules of the historical series (issue #25).

The rules under test are the ones that decide what an entity *is* and when a
version of it was valid: which key identifies it across a recoding, and what
must fail loudly rather than be guessed.
"""

import pytest

from scripts.identity import (
    VERSION_REASONS,
    AmbiguousIdentity,
    creation_at,
    creations,
    first_code,
    identity_links,
    intervals,
    version_reason,
)


def var(code, old, new):
    return {
        "DESC_COD_VARIAZIONE": f"{code}-Descrizione",
        "COD_CATASTO": old,
        "COD_CATASTO_REL": new,
    }


def test_a_renaming_that_changes_the_code_is_an_identity_link():
    """Lonato -> Lonato del Garda, 2 November 2007: E667 becomes M312.

    The only such record in the series, and the reason terr_key is the *first*
    code rather than the current one.
    """
    assert identity_links([var("CD", "E667", "M312")]) == {"E667": "M312"}


def test_a_transfer_of_territory_is_not_an_identity_link():
    """CE/AQ name the two municipalities either side of a boundary change.

    Reading them as identity would merge unrelated entities wholesale: there
    are 293 such records with differing codes since 2001, against one real
    link.
    """
    assert identity_links([var("CE", "A794", "G108"),
                           var("AQ", "G108", "A794")]) == {}


def test_an_extinction_is_not_an_identity_link():
    """ES and CS relate two different entities, which is the opposite claim."""
    assert identity_links([var("ES", "C056", "M439")]) == {}


def test_a_record_that_does_not_change_the_code_links_nothing():
    assert identity_links([var("CD", "L599", "L599")]) == {}


def test_contradictory_links_raise():
    with pytest.raises(AmbiguousIdentity):
        identity_links([var("CD", "E667", "M312"), var("CD", "E667", "M999")])


def test_the_key_is_the_first_code_in_the_chain():
    links = {"E667": "M312"}
    assert first_code("M312", links) == "E667"
    assert first_code("E667", links) == "E667"


def test_a_code_never_renamed_is_its_own_key():
    assert first_code("A074", {}) == "A074"


def test_a_longer_chain_walks_all_the_way_back():
    """Walking backwards keeps published keys stable when a link is added."""
    assert first_code("C", {"A": "B", "B": "C"}) == "A"


def test_a_cycle_raises_rather_than_looping():
    with pytest.raises(AmbiguousIdentity):
        first_code("A", {"A": "B", "B": "A"})


def test_two_predecessors_for_one_code_raise():
    with pytest.raises(AmbiguousIdentity):
        first_code("C", {"A": "C", "B": "C"})


def event(code, this, related, at):
    return {
        "DESC_COD_VARIAZIONE": f"{code}-Descrizione",
        "COD_CATASTO": this,
        "COD_CATASTO_REL": related,
        "DATA_INIZIO_AMMINISTRATIVA": f"{at}T00:00:00Z",
    }


def test_a_merger_is_read_from_its_predecessors_extinction():
    """Castegnero and Nanto are extinguished into Castegnero Nanto, so the new
    boundary is their union."""
    records = [
        event("CS", "M439", "C056", "2026-02-21"),
        event("CS", "M439", "F838", "2026-02-21"),
        event("ES", "C056", "M439", "2026-02-21"),
        event("ES", "F838", "M439", "2026-02-21"),
    ]
    assert creations(records)["M439"] == [
        {"date": "2026-02-21", "kind": "merger", "predecessors": ["C056", "F838"]}
    ]


def test_a_detachment_is_read_from_its_predecessor_surviving():
    """Trapani cedes territory and continues to exist, so Misiliscemi's
    boundary cannot be derived from it."""
    records = [
        event("CS", "M432", "L331", "2021-02-20"),
        event("CECS", "L331", "M432", "2021-02-20"),
    ]
    assert creations(records)["M432"][0]["kind"] == "detachment"


def test_a_constitution_with_no_matching_predecessor_event_raises():
    with pytest.raises(AmbiguousIdentity):
        creations([event("CS", "M999", "A001", "2020-01-01")])


def test_a_municipality_constituted_twice_keeps_both_creations():
    """Baranzate: created 2001, extinguished 2003 by the Constitutional Court,
    created again 2004. One entry would date its second life from its first."""
    records = [
        event("CS", "A618", "A940", "2001-12-12"),
        event("CECS", "A940", "A618", "2001-12-12"),
        event("CS", "A618", "A940", "2004-06-08"),
        event("CECS", "A940", "A618", "2004-06-08"),
    ]
    born = creations(records)
    assert [c["date"] for c in born["A618"]] == ["2001-12-12", "2004-06-08"]
    assert creation_at(born, "A618", "2003-01-01")["date"] == "2001-12-12"
    assert creation_at(born, "A618", "2005-01-01")["date"] == "2004-06-08"
    assert creation_at(born, "A618", "2001-01-01") is None


def test_the_first_version_of_a_pre_existing_municipality_is_initial():
    assert version_reason("A074", "2001-10-21", None, {}, {}) == "initial"


def test_a_municipality_born_of_a_merger_says_so():
    born = {"M439": [{"date": "2026-02-21", "kind": "merger",
                      "predecessors": ["C056", "F838"]}]}
    assert version_reason("M439", "2026-02-21", None, born, {}) == "admin_fusione"


def test_a_municipality_born_of_a_detachment_says_so():
    born = {"M432": [{"date": "2021-02-20", "kind": "detachment",
                      "predecessors": ["L331"]}]}
    assert version_reason("M432", "2021-02-20", None, born, {}) == "admin_scissione"


def test_a_reassignment_outranks_the_recoding_it_causes():
    """1 January 2026 in Sardinia is one event, not two: the province changed
    and the municipal code followed, because the code embeds the province."""
    events = {"A069": {"2026-01-01": {"own": {"AP", "RN"}, "related": set()}}}
    assert version_reason("A069", "2026-01-01", "2025-01-01", {}, events) == \
        "admin_riassegnazione"


def test_a_bare_renumbering_is_a_code_change():
    events = {"F478": {"2021-06-17": {"own": {"RN"}, "related": set()}}}
    assert version_reason("F478", "2021-06-17", "2021-01-01", {}, events) == \
        "admin_cambio_codice"


def test_a_rename_is_not_reported_as_a_code_change():
    """Vallecrosia became Vallecrosia al mare with the same code. The design's
    six values have nothing for this, so a seventh was added rather than
    reporting a change that did not happen."""
    events = {"L599": {"2026-05-14": {"own": {"CD"}, "related": set()}}}
    assert version_reason("L599", "2026-05-14", "2026-01-01", {}, events) == \
        "admin_cambio_denominazione"


def test_absorbing_another_municipality_is_a_merger_for_the_survivor():
    """The absorber appears only as the related party of the other's
    extinction, and that is why its own boundary changes."""
    events = {"F408": {"2026-01-31": {"own": set(), "related": {"ES"}}}}
    assert version_reason("F408", "2026-01-31", "2026-01-01", {}, events) == \
        "admin_fusione"


def test_a_transfer_between_editions_explains_the_next_version():
    """CE/AQ move a boundary on a date ISTAT draws nothing for, so the change
    surfaces at the following edition. Attributing it to re-generalisation
    would blame ISTAT for an act of parliament."""
    events = {"A794": {"2024-04-18": {"own": {"CE"}, "related": set()}}}
    assert version_reason("A794", "2025-01-01", "2024-01-01", {}, events) == \
        "admin_variazione_territoriale"


def test_a_version_with_no_administrative_cause_is_a_regeneralisation():
    """The residual, and only the residual."""
    assert version_reason("A074", "2025-01-01", "2024-01-01", {}, {}) == \
        "source_regeneralization"


def test_an_unchanged_geometry_is_not_reported_as_redrawn():
    """ISTAT's roster began carrying NUTS codes in 2006, so every published
    record changed while about 310 boundaries moved. Calling all 7,966 of them
    a re-generalisation would show a nationwide redrawing that never happened.
    """
    assert version_reason("A074", "2006-01-01", "2005-01-01", {}, {},
                          geometry_changed=False) == "source_attribute_change"


def test_an_administrative_event_outranks_both_residuals():
    events = {"A069": {"2026-01-01": {"own": {"AP"}, "related": set()}}}
    assert version_reason("A069", "2026-01-01", "2025-01-01", {}, events,
                          geometry_changed=False) == "admin_riassegnazione"


def test_an_event_outside_the_window_does_not_explain_the_version():
    events = {"A794": {"2010-02-13": {"own": {"CE"}, "related": set()}}}
    assert version_reason("A794", "2025-01-01", "2024-01-01", {}, events) == \
        "source_regeneralization"


def test_every_reason_produced_is_in_the_published_vocabulary():
    cases = [
        version_reason("A074", "2001-10-21", None, {}, {}),
        version_reason("A074", "2025-01-01", "2024-01-01", {}, {}),
        version_reason("A069", "2026-01-01", "2025-01-01", {},
                       {"A069": {"2026-01-01": {"own": {"AP"}, "related": set()}}}),
    ]
    assert set(cases) <= set(VERSION_REASONS)


CALENDAR = ["2001-10-21", "2002-01-01", "2003-01-01", "2004-01-01", "2005-01-01"]


def test_an_unchanging_entity_is_one_open_interval():
    versions = {at: "same" for at in CALENDAR}
    assert intervals(CALENDAR, versions) == [
        {"valid_from": "2001-10-21", "valid_to": None, "version": "same"}
    ]


def test_a_change_closes_one_interval_and_opens_the_next():
    versions = {at: ("a" if at < "2003-01-01" else "b") for at in CALENDAR}
    got = intervals(CALENDAR, versions)
    assert [(i["valid_from"], i["valid_to"]) for i in got] == [
        ("2001-10-21", "2003-01-01"), ("2003-01-01", None)
    ]


def test_intervals_meet_exactly_with_no_gap():
    versions = {at: at for at in CALENDAR}
    got = intervals(CALENDAR, versions)
    for earlier, later in zip(got, got[1:]):
        assert earlier["valid_to"] == later["valid_from"]


def test_an_extinct_entity_gets_a_closed_interval():
    versions = {at: "x" for at in CALENDAR[:2]}
    assert intervals(CALENDAR, versions) == [
        {"valid_from": "2001-10-21", "valid_to": "2003-01-01", "version": "x"}
    ]


def test_an_entity_that_returns_gets_a_second_interval():
    """Baranzate: constituted 2001, extinguished 2003, re-established 2004.

    The gap is a fact about the entity. Bridging it would publish a
    municipality that did not exist for a year, which is what a reader of
    extinction records alone produces.
    """
    versions = {"2001-10-21": "b", "2002-01-01": "b", "2005-01-01": "b"}
    got = intervals(CALENDAR, versions)
    assert [(i["valid_from"], i["valid_to"]) for i in got] == [
        ("2001-10-21", "2003-01-01"), ("2005-01-01", None)
    ]


def test_a_version_that_returns_to_an_earlier_value_is_a_new_interval():
    """A->B->A is three intervals: the archive stores versions by period."""
    versions = dict(zip(CALENDAR, ["a", "a", "b", "a", "a"]))
    assert len(intervals(CALENDAR, versions)) == 3
