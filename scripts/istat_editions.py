"""Locating the ISTAT boundary editions (issue #24).

ISTAT publishes generalised administrative boundaries under three different URL
shapes, and the difference is not cosmetic — one of them is a different product.

    Limiti0101<YYYY>_g.zip    annual edition, boundaries as of 1 January
    <YYYY>/Limiti0101<YYYY>_g.zip   same, nested from 2022 onward
    Limiti<YYYY>_g.zip        census edition, published for census years only

For 2021 both an annual and a census edition exist. They are not
interchangeable: not one of the 7,901 municipalities present in both has the
same geometry in the two files. Loading the census product in place of the
annual one is a documented way to fabricate a discontinuity across the whole
country, so the resolver always prefers the annual edition where one exists.

For 2001 and 2011 there is no annual edition at all — ISTAT published only the
census cartography — so it is the source for those two years by necessity, and
`source_edition` records which file was actually read.

Verified against the live site in August 2026: every year from 2002 to 2026
resolves in its annual form, so the "2002-2010 unavailable" gap this project
had previously recorded does not exist.
"""

BASE = "https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati"

# Depth of the historical series (design D5). 1991 is addressable but out of
# scope: the design notes it can be added later without a schema change.
SERIES_YEARS = tuple(range(2001, 2027))

# Years with no annual edition, where the census cartography is the only source.
CENSUS_ONLY_YEARS = (2001, 2011)

# Every other year in the series has an annual edition.
ANNUAL_YEARS = tuple(y for y in SERIES_YEARS if y not in CENSUS_ONLY_YEARS)

# ISTAT nested the file under a year directory starting with this vintage.
_NESTED_FROM = 2022

# Census cartography exists for these years; 1991 predates the series.
_CENSUS_YEARS = (1991, 2001, 2011, 2021)

_EARLIEST = 1991
_LATEST = 2026

# The reference date of each census edition. A census edition is *not* the state
# at 1 January of its year, and treating it as one publishes municipalities that
# did not yet exist at the date claimed:
#
#   Limiti2001_g contains Fonte Nuova, constituted 15 October 2001
#   Limiti2011_g contains Gravedona ed Uniti, constituted 11 February 2011,
#                in place of its three predecessors
#
# Both are exactly the defect this design objects to in derived sources. The
# dates below are the official census reference dates, and the editions'
# contents bracket them: the 2001 file holds a municipality created on 15
# October and not one created on 12 December, so its date lies between the two.
CENSUS_REFERENCE_DATES = {
    1991: "1991-10-20",
    2001: "2001-10-21",
    2011: "2011-10-09",
    2021: "2021-10-03",
}


def _check(year):
    year = int(year)
    if not _EARLIEST <= year <= _LATEST:
        raise ValueError(
            f"no ISTAT edition for {year}: published range is "
            f"{_EARLIEST}-{_LATEST}"
        )
    return year


def edition_filename(year):
    """Return the edition's base name, without extension.

    This is the string that belongs in `source_edition`: it names the file a
    third party can download to check the geometry, which is what turns the
    fidelity claim into a property of a download rather than of a pipeline.
    """
    year = _check(year)
    if year in CENSUS_ONLY_YEARS or year == _EARLIEST:
        return f"Limiti{year}_g"
    return f"Limiti0101{year}_g"


def edition_reference_date(year):
    """The date an edition's boundaries actually describe, as an ISO string.

    1 January for the annual editions, and the census date for the two years
    where only the census cartography exists. This is the date the archive dates
    the geometry at; see CENSUS_REFERENCE_DATES for why the distinction is not
    pedantry.
    """
    year = _check(year)
    if year in CENSUS_ONLY_YEARS or year == _EARLIEST:
        return CENSUS_REFERENCE_DATES[year]
    return f"{year}-01-01"


def edition_url(year):
    """Return the download URL for a year's generalised boundary edition."""
    year = _check(year)
    name = edition_filename(year)
    if year >= _NESTED_FROM:
        return f"{BASE}/{year}/{name}.zip"
    return f"{BASE}/{name}.zip"


def census_edition_url(year):
    """Return the census edition URL for a census year.

    Provided so the 2021 census/annual divergence can be measured rather than
    argued about. It is never the series source for a year that has an annual
    edition.
    """
    year = _check(year)
    if year not in _CENSUS_YEARS:
        raise ValueError(f"{year} is not a census year: {_CENSUS_YEARS}")
    return f"{BASE}/Limiti{year}_g.zip"
