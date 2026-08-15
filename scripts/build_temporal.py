"""Joining the roster to the geometry (issue #25).

The archive's two halves meet here. The roster (SITUAS report 61) says which
municipalities were valid at a date and what their codes and names were; the
ISTAT boundary edition says what shape they had. The join is on the ISTAT code,
which is the only field both carry — the archive's own key, the first cadastral
code, is assigned afterwards, once an entity's whole series is in hand.

**Which edition applies to a date** is the latest edition whose *reference date*
is at or before it. Not the edition of the same year: for 2011-02-11 the
applicable edition is the 2010 one, because the 2011 edition describes 9 October
2011 and did not exist yet at the date being published.

The interesting output is not the matched majority, it is the two residuals:

- **A municipality in the roster with no geometry.** Expected, and enumerated by
  the design: ISTAT publishes boundaries only at 1 January, so a municipality
  created during the year has none until the next edition. §6 gives the rule —
  union of predecessors for a merger, the next edition's shape for the four
  detachments, and a hard failure for anything else.
- **A geometry with no municipality in the roster.** Not expected at any date,
  and left as an error rather than dropped: it would mean the two ISTAT products
  disagree about who existed, which is a finding, not a nuisance.
"""

import json
import sys
from pathlib import Path

from scripts.change_dates import change_dates, load_variations
from scripts.istat_editions import SERIES_YEARS, edition_filename, edition_reference_date
from scripts.rosters import ROSTERS, available, istat_code, read_roster

ROOT = Path(__file__).resolve().parent.parent
EDITIONS = ROOT / "build" / "editions"

# Field holding the municipality code in the edition, renamed across the series.
_CODE_FIELDS = ("PRO_COM_T", "PRO_COM", "COD_ISTAT", "ISTAT", "PROCOM")


class NoApplicableEdition(ValueError):
    """A date before the first published boundary edition."""


def applicable_edition(at, years=SERIES_YEARS):
    """The year of the edition whose geometry describes `at`.

    The latest edition at or before the date, by reference date — so a date in
    2011 before the census takes the 2010 edition.
    """
    candidates = [y for y in years if edition_reference_date(y) <= at]
    if not candidates:
        raise NoApplicableEdition(
            f"{at} precedes the first edition "
            f"({edition_reference_date(min(years))})"
        )
    return max(candidates)


def read_edition_geometries(year, root=EDITIONS):
    """{istat code: geometry} for one edition."""
    path = Path(root) / str(year) / "comuni.geojson"
    data = json.loads(path.read_text())
    out = {}
    for feature in data["features"]:
        props = feature["properties"]
        for field in _CODE_FIELDS:
            if field in props:
                out[istat_code(props[field])] = feature["geometry"]
                break
        else:
            raise KeyError(f"{path}: no municipality code field in {sorted(props)}")
    return out


def join(at, root=EDITIONS, roster_root=ROSTERS):
    """Join the roster at a date to the applicable edition's geometry.

    Returns (features, missing_geometry, orphan_geometry): the municipalities
    resolved with a shape, the codes the roster has and the edition does not,
    and the reverse.
    """
    year = applicable_edition(at)
    roster = read_roster(at, root=roster_root)
    geometries = read_edition_geometries(year, root=root)
    source = edition_filename(year)

    features, missing = [], []
    for code, attrs in sorted(roster.items()):
        geometry = geometries.get(code)
        if geometry is None:
            missing.append(attrs)
            continue
        features.append({
            "type": "Feature",
            "properties": {**attrs, "source_edition": source},
            "geometry": geometry,
        })
    orphans = sorted(set(geometries) - set(roster))
    return features, missing, orphans


def main(dates=None):
    """Report the join over every date whose roster is cached."""
    calendar = change_dates(load_variations())
    cached = set(available())
    dates = dates or [d for d in calendar if d in cached]

    print(f"{'date':<12}{'edition':>9}{'joined':>8}{'no geom':>9}{'orphan':>8}")
    total_missing, total_orphans = 0, 0
    for at in dates:
        year = applicable_edition(at)
        features, missing, orphans = join(at)
        total_missing += len(missing)
        total_orphans += len(orphans)
        print(f"{at:<12}{year:>9}{len(features):>8}{len(missing):>9}{len(orphans):>8}"
              + ("  " + ", ".join(f"{m['name']} ({m['com_istat_code']})"
                                  for m in missing) if missing else ""))
    print(f"\n{len(dates)} dates joined, {total_missing} without geometry, "
          f"{total_orphans} geometries without a municipality")
    print(f"{len(calendar) - len(cached & set(calendar))} rosters still to fetch")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
