"""Tests for the identity rules of the historical series (issue #25).

The rules under test are the ones that decide what an entity *is* and when a
version of it was valid: which key identifies it across a recoding, and what
must fail loudly rather than be guessed.
"""

import pytest

from scripts.identity import (
    AmbiguousIdentity,
    first_code,
    identity_links,
    intervals,
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
