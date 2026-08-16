"""Checks on the temporal dataset (issue #30).

The archive's claim is that it reproduces what ISTAT published for each date.
That claim is only worth making if it is mechanically checked, so these run over
the built dataset and fail loudly rather than warn:

1. **Interval integrity** — no overlapping validity periods for one entity, and
   every interval closing exactly where the next opens. A gap is allowed and is
   not an error: it means the entity did not exist, which happened once.
2. **Counts against the roster** — at every publication date, the number of
   municipalities in the archive equals the number ISTAT's own roster carries
   for that date. This is the check that would have caught the join defect that
   lost 310 municipalities to reassignment.
3. **Continuity across the Sardinian reform** — all 377 municipalities whose
   ISTAT code changed on 1 January 2026 resolve to the same `terr_key` before
   and after. This is the regression test for the whole design: it is the event
   that breaks any code-keyed dataset.
4. **One version per entity per date** — an entity resolves to exactly one
   version at any date it exists, or the interval filter consumers are told to
   use returns two rows for one municipality.

Usage:
    python -m scripts.validate_temporal
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

from scripts.change_dates import change_dates, load_variations
from scripts.rosters import read_roster

ROOT = Path(__file__).resolve().parent.parent
TEMPORAL = ROOT / "temporal" / "comuni"


def read_versions(root=TEMPORAL):
    """Every version's properties, geometry dropped.

    Read region by region and stripped immediately: the dataset is 349 MB on
    disk and several times that as Python objects.
    """
    out = []
    for path in sorted(Path(root).glob("reg=*.geojson")):
        data = json.loads(path.read_text())
        out.extend(feature["properties"] for feature in data["features"])
        del data
    return out


def by_key(versions):
    grouped = defaultdict(list)
    for version in versions:
        grouped[version["terr_key"]].append(version)
    for series in grouped.values():
        series.sort(key=lambda v: v["valid_from"])
    return grouped


def interval_problems(grouped):
    """Overlaps and mismatched interval ends."""
    problems = []
    for key, series in grouped.items():
        for earlier, later in zip(series, series[1:]):
            if earlier["valid_to"] is None:
                problems.append(f"{key}: open interval from "
                                f"{earlier['valid_from']} followed by "
                                f"{later['valid_from']}")
            elif earlier["valid_to"] > later["valid_from"]:
                problems.append(f"{key}: {earlier['valid_from']}–"
                                f"{earlier['valid_to']} overlaps "
                                f"{later['valid_from']}")
    return problems


def valid_at(grouped, at):
    """The versions valid on a date, keyed by entity."""
    out = {}
    for key, series in grouped.items():
        for version in series:
            if version["valid_from"] <= at and (version["valid_to"] is None
                                                or version["valid_to"] > at):
                if key in out:
                    raise AssertionError(f"{key}: two versions valid at {at}")
                out[key] = version
    return out


def count_problems(grouped, calendar):
    """Dates where the archive and ISTAT's roster disagree on the count."""
    problems = []
    for at in calendar:
        published = len(valid_at(grouped, at))
        expected = len(read_roster(at))
        if published != expected:
            problems.append(f"{at}: archive has {published}, roster {expected}")
    return problems


def sardinian_continuity(grouped, before="2025-12-31", after="2026-01-01"):
    """Entities whose ISTAT code changed at the reform, and any that broke.

    Returns (continuous, broken): how many kept their key across the change,
    and the keys that did not resolve on both sides.
    """
    earlier, later = valid_at(grouped, before), valid_at(grouped, after)
    continuous, broken = 0, []
    for key, version in earlier.items():
        successor = later.get(key)
        if successor is None:
            continue
        if version["com_istat_code"] != successor["com_istat_code"]:
            continuous += 1
    for key, version in earlier.items():
        if key not in later and version["com_istat_code"].startswith(
                ("090", "091", "092", "095", "104", "105", "106", "107")):
            broken.append(key)
    return continuous, broken


def main():
    variations = load_variations()
    calendar = change_dates(variations)
    versions = read_versions()
    grouped = by_key(versions)

    print(f"{len(grouped)} entities, {len(versions)} versions, "
          f"{len(calendar)} dates")

    failures = 0

    problems = interval_problems(grouped)
    print(f"interval integrity: {'ok' if not problems else problems[:5]}")
    failures += len(problems)

    problems = count_problems(grouped, calendar)
    print(f"counts against the roster: "
          f"{'ok, all ' + str(len(calendar)) + ' dates' if not problems else problems[:5]}")
    failures += len(problems)

    continuous, broken = sardinian_continuity(grouped)
    print(f"Sardinian reform: {continuous} entities kept their key across a "
          f"changed ISTAT code, {len(broken)} lost")
    if continuous != 377 or broken:
        failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
