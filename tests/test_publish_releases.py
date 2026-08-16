"""Tests for publishing the file sets as releases (issue #28).

The release body is the only documentation most consumers will read: they
arrive from a search engine with a date in hand. So what it must say is tested,
and so is the refusal to publish anything by default.
"""

from scripts.publish_releases import main, notes

ROW = {
    "valid_from": "2005-01-01",
    "valid_to": "2005-05-04",
    "release_tag": "2005-01-01",
    "municipalities": "8101",
    "change": "16 admin_variazione_territoriale",
}


def test_the_body_states_the_interval_it_serves():
    body = notes(ROW)
    assert "valid from 2005-01-01 to 2005-05-04" in body
    assert "8101" in body
    assert "16 admin_variazione_territoriale" in body


def test_the_open_interval_reads_as_the_present():
    """The current release has no end date, and an empty cell would read as a
    missing value rather than as "still valid"."""
    body = notes({**ROW, "valid_to": ""})
    assert "to the present" in body
    assert "up to (but not\nincluding) the present" in body


def test_the_body_warns_that_a_year_is_not_a_date():
    """The one thing a consumer can get wrong without noticing."""
    body = notes(ROW)
    assert "A year is not a date" in body
    assert "INDEX.csv" in body


def test_the_body_carries_the_caveats_where_they_are_met():
    """The release notes are the only documentation most consumers read.

    Three things silently produce wrong conclusions if unstated: boundaries
    are drawn once a year while codes change on the day; a diff between two
    dates is mostly ISTAT re-generalising; and a municipality ISTAT had not
    yet drawn carries a derived boundary that says so.
    """
    body = notes(ROW)
    assert "once a year" in body
    assert "version_reason" in body
    assert "source_regeneralization" in body
    assert "(union of predecessors)" in body
    assert "(anticipated)" in body


def test_the_body_states_what_the_files_are_faithful_to():
    body = notes(ROW)
    assert "not smoothed, not normalised, not reconciled" in body
    assert "source_edition" in body


def test_the_body_keeps_the_attribution():
    assert "CC-BY" in notes(ROW)
    assert "ISTAT" in notes(ROW)


def test_nothing_is_published_without_yes(monkeypatch, capsys):
    """A dry run may look at what is already published; it must not write.

    98 public releases is not something to discover after the fact, so the
    guard is on the command that creates them, not on reading the list.
    """
    def fail(*args, **kwargs):
        raise AssertionError("publishing attempted during a dry run")

    monkeypatch.setattr("scripts.publish_releases.subprocess.run", fail)
    monkeypatch.setattr("scripts.publish_releases.existing_tags", set)
    monkeypatch.setattr("scripts.publish_releases.read_index", lambda: [ROW])
    monkeypatch.setattr("scripts.publish_releases.assets_for",
                        lambda tag, root=None: [])

    main([])
    out = capsys.readouterr().out
    assert "would publish 2005-01-01" in out
    assert "Nothing was published" in out
