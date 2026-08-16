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
from scripts.istat_editions import SERIES_YEARS, edition_filename, edition_reference_date
from scripts.materialize import snapshot
from scripts.build_temporal import edition_geometries_by_key
from scripts.identity import identity_links
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


def round_trip_problems(links=None, years=SERIES_YEARS, root=TEMPORAL):
    """Check 1: every version's geometry is the one the file it names holds.

    `source_edition` claims a boundary was read from a named ISTAT file. This
    is what gives the claim meaning — compared coordinate for coordinate, not
    by area or bounding box, because an area comparison passes on a shape that
    has been quietly resampled.

    It checks the claim each version actually makes, not the edition applicable
    at some date. Those differ, and the difference is the point of interval
    collapsing: where ISTAT republishes a geometry unchanged, the version keeps
    the edition it began in. Bolzano/Bozen is valid on 17 June 2021 carrying
    `Limiti01012020_g`, because its boundary has not moved since — and the 2021
    file holds the same bytes, so the claim is true either way. An earlier
    version of this check demanded the applicable edition and would have failed
    on almost every municipality in the archive.

    Municipalities ISTAT had not yet drawn are exempt and must say so: their
    `source_edition` carries `(union of predecessors)` or `(anticipated)`. An
    exemption that does not declare itself is a failure — that is exactly how a
    derived boundary would pass for a published one.

    Slow on purpose: 26 editions against the whole archive, once per edition.
    The cheap version of this check is the one that proves nothing.
    """
    links = {} if links is None else links
    problems = []
    checked, derived = 0, 0
    for year in years:
        # Keyed on identity, never on the ISTAT code. That code changes with
        # the province, so at 30 June 2009 the 51 municipalities of the new
        # Monza e della Brianza carry 108xxx while the applicable edition still
        # has them under Milan — the same trap that cost the join 310
        # municipalities, met a second time here.
        published, _ = edition_geometries_by_key(year, links)
        edition = edition_filename(year)
        matched = 0
        for path in sorted(Path(root).glob("reg=*.geojson")):
            data = json.loads(path.read_text())
            for feature in data["features"]:
                props = feature["properties"]
                source = props.get("source_edition") or ""
                if not source.startswith(edition):
                    continue
                if "(" in source:
                    derived += 1
                    continue
                matched += 1
                theirs = published.get(props["terr_key"])
                if theirs is None:
                    problems.append(f"{props['com_istat_code']} "
                                    f"({props['valid_from']}) claims {edition}, "
                                    f"which does not contain it")
                elif theirs != feature["geometry"]:
                    problems.append(f"{props['com_istat_code']} "
                                    f"({props['valid_from']}) differs from "
                                    f"the geometry in {edition}")
            del data
        checked += matched
        print(f"  {edition}  {matched} versions verified vertex for vertex")
    print(f"  {checked} versions checked, {derived} declared as derived")
    return problems


def derivation_problems(grouped, calendar):
    """Check 4: dissolving the archive reproduces ISTAT's own unit counts.

    Province and region layers are not stored, they are dissolved from the
    municipalities, so what has to hold is that the number of distinct units
    the archive yields at a date equals the number ISTAT's roster lists for the
    same date. The roster counts them under `COD_UTS` and the archive under
    `COD_PROV`, which are two code families for the same units — comparing the
    counts is what proves they are.
    """
    problems = []
    for at in calendar:
        versions = valid_at(grouped, at).values()
        provinces = {v["prov_istat_code"] for v in versions}
        regions = {v["reg_istat_code"] for v in versions}
        roster = read_roster(at).values()
        published_provinces = {str(r["prov_uts_code"]) for r in roster}
        published_regions = {str(r["reg_istat_code"]) for r in roster}
        if len(provinces) != len(published_provinces):
            problems.append(f"{at}: {len(provinces)} provinces dissolved, "
                            f"roster lists {len(published_provinces)}")
        if len(regions) != len(published_regions):
            problems.append(f"{at}: {len(regions)} regions dissolved, "
                            f"roster lists {len(published_regions)}")
    return problems


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

    problems = derivation_problems(grouped, calendar)
    print(f"provinces and regions dissolved: "
          f"{'ok, all ' + str(len(calendar)) + ' dates' if not problems else problems[:5]}")
    failures += len(problems)

    if "--quick" not in sys.argv:
        print("round trip against the ISTAT editions:")
        problems = round_trip_problems(identity_links(variations))
        print(f"  {'ok, all 26 editions' if not problems else problems[:5]}")
        failures += len(problems)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
