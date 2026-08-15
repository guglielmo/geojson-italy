"""Tests for locating and reading the SITUAS reports (issue #24).

Two things are load-bearing here and both are silent failures if wrong:

- the date format. SITUAS answers a badly formatted date with the report's full
  default range and HTTP 200, so an ISO date returns plausible data for the
  wrong period rather than an error;
- the parameter set. Same behaviour: an unrecognised parameter is ignored, not
  rejected.

Everything runs offline. No test in this file may reach the network — the
service answers intermittently and must be asked sparingly.
"""

import json

import pytest

from scripts.situas import (
    BadParameters,
    UnknownReport,
    check_against_catalogue,
    format_date,
    parse_payload,
    roster_url,
    spool_url,
    variations_url,
)


def test_dates_are_rendered_in_the_form_the_service_expects():
    assert format_date("2021-06-17") == "17/06/2021"


def test_a_single_digit_day_is_zero_padded():
    """dd/mm/yyyy, not d/m/yyyy: the service parses only the padded form."""
    assert format_date("2003-03-06") == "06/03/2003"


def test_roster_url_names_the_date_and_the_report():
    url = roster_url("2001-10-15")
    assert url.endswith("reportspooljson?pfun=61&pdata=15/10/2001")


def test_a_roster_before_the_report_starts_is_refused():
    with pytest.raises(ValueError):
        roster_url("1930-01-01")


def test_period_reports_take_both_ends():
    url = variations_url(98, until="2026-08-15")
    assert "pfun=98" in url
    assert "pdatada=17/03/1861" in url
    assert "pdataa=15/08/2026" in url


def test_a_dated_report_ignores_the_period_end():
    """Report 129 takes a start date only; passing an end would be rejected."""
    url = variations_url(129, until="2026-08-15")
    assert url.endswith("pfun=129&pdata=01/01/1991")


def test_wrong_parameters_raise_rather_than_being_sent():
    with pytest.raises(BadParameters):
        spool_url(129, pdatada="1991-01-01", pdataa="2026-08-15")


def test_an_extra_parameter_raises():
    with pytest.raises(BadParameters):
        spool_url(61, pdata="2026-01-01", pdataa="2026-08-15")


def test_an_unknown_report_raises():
    with pytest.raises(UnknownReport):
        spool_url(42, pdata="2026-01-01")


def test_payload_as_a_plain_resultset():
    assert parse_payload('{"resultset": [{"a": 1}]}') == [{"a": 1}]


def test_payload_double_encoded():
    """The catalogue route returns a JSON string containing JSON."""
    inner = json.dumps({"items": [{"Id report": 61}]})
    assert parse_payload(json.dumps(inner)) == [{"Id report": 61}]


def test_payload_that_is_neither_raises():
    with pytest.raises(ValueError):
        parse_payload('{"unexpected": []}')


def _catalogue(**overrides):
    entry = {
        "Id report": 61,
        "Titolo report": "Elenco dei codici e delle denominazioni delle unità territoriali",
        "parametri necessari": "pfun - pdata",
    }
    entry.update(overrides)
    return json.dumps(json.dumps({"items": [entry]}))


def test_a_report_whose_parameters_changed_is_reported():
    problems = check_against_catalogue(
        _catalogue(**{"parametri necessari": "pfun - pdatada - pdataa"})
    )
    assert any("now takes" in p for p in problems)


def test_a_report_missing_from_the_catalogue_is_reported():
    problems = check_against_catalogue(json.dumps(json.dumps({"items": []})))
    assert any("is gone from the catalogue" in p for p in problems)
