"""Tests for ISTAT edition URL resolution (issue #24)."""

import pytest

from scripts.istat_editions import (
    ANNUAL_YEARS,
    CENSUS_ONLY_YEARS,
    SERIES_YEARS,
    edition_filename,
    edition_reference_date,
    edition_url,
)

BASE = "https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati"


def test_years_from_2022_live_under_a_year_directory():
    assert edition_url(2026) == f"{BASE}/2026/Limiti01012026_g.zip"
    assert edition_url(2022) == f"{BASE}/2022/Limiti01012022_g.zip"


def test_years_up_to_2021_are_flat():
    assert edition_url(2021) == f"{BASE}/Limiti01012021_g.zip"
    assert edition_url(2020) == f"{BASE}/Limiti01012020_g.zip"
    assert edition_url(2002) == f"{BASE}/Limiti01012002_g.zip"


def test_2021_resolves_to_the_annual_edition_not_the_census_one():
    """Both exist for 2021, and picking the wrong one is a documented trap.

    Limiti2021_g.zip is the census product; loading it in place of the annual
    edition fabricates a 3.5%-12% area discontinuity on every municipality,
    which is the artefact this issue exists to avoid inheriting.
    """
    assert edition_url(2021).endswith("Limiti01012021_g.zip")
    assert "Limiti2021_g.zip" not in edition_url(2021)


def test_census_only_years_use_the_bare_year_form():
    """2001 and 2011 have no annual edition at all: ISTAT published only the
    census cartography for them, so it is the source by necessity."""
    assert edition_url(2001) == f"{BASE}/Limiti2001_g.zip"
    assert edition_url(2011) == f"{BASE}/Limiti2011_g.zip"


def test_the_series_covers_2001_to_2026():
    assert SERIES_YEARS == tuple(range(2001, 2027))
    assert len(SERIES_YEARS) == 26


def test_census_only_years_are_exactly_2001_and_2011():
    assert CENSUS_ONLY_YEARS == (2001, 2011)
    assert set(ANNUAL_YEARS) == set(SERIES_YEARS) - set(CENSUS_ONLY_YEARS)


def test_every_series_year_resolves():
    urls = {edition_url(y) for y in SERIES_YEARS}
    assert len(urls) == 26
    assert all(u.startswith(BASE) and u.endswith(".zip") for u in urls)


def test_years_outside_the_published_range_are_refused():
    """ISTAT publishes nothing before 1991 and nothing beyond the current
    vintage. Silently building a URL that 404s would push the failure into the
    download, where it reads as a network problem."""
    with pytest.raises(ValueError):
        edition_url(1990)
    with pytest.raises(ValueError):
        edition_url(2027)


def test_1991_is_addressable_though_outside_the_series():
    """The design stops at 2001 but notes 1991 can be added without schema
    change. The resolver should already know it."""
    assert edition_url(1991) == f"{BASE}/Limiti1991_g.zip"
    assert 1991 not in SERIES_YEARS


def test_an_annual_edition_describes_1_january():
    assert edition_reference_date(2026) == "2026-01-01"
    assert edition_reference_date(2012) == "2012-01-01"


def test_a_census_edition_describes_the_census_date():
    """Measured, not assumed: Limiti2001_g contains Fonte Nuova, constituted
    15 October 2001, and Limiti2011_g contains Gravedona ed Uniti, constituted
    11 February 2011 out of three municipalities that are absent from it.

    Dating either edition at 1 January would publish a municipality that did
    not exist at the date claimed — the same defect this project refused to
    inherit from a derived source.
    """
    assert edition_reference_date(2001) == "2001-10-21"
    assert edition_reference_date(2011) == "2011-10-09"


def test_the_2021_reference_date_is_1_january_because_the_source_is_annual():
    """2021 has both editions and the resolver takes the annual one, so its
    reference date must follow the file actually read, not the census year."""
    assert edition_reference_date(2021) == "2021-01-01"


def test_edition_filename_identifies_the_source_file():
    """This string lands in source_edition, which is what makes the fidelity
    claim checkable by a third party."""
    assert edition_filename(2026) == "Limiti01012026_g"
    assert edition_filename(2011) == "Limiti2011_g"
    assert edition_filename(2021) == "Limiti01012021_g"
