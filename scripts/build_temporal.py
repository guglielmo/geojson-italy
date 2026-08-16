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

import hashlib
import json
import sys
from pathlib import Path

from scripts.change_dates import change_dates, load_variations
from scripts.identity import identity_links, intervals, terr_key
from scripts.istat_editions import SERIES_YEARS, edition_filename, edition_reference_date
from scripts.rosters import ROSTERS, available, istat_code, read_roster

ROOT = Path(__file__).resolve().parent.parent
EDITIONS = ROOT / "build" / "editions"
TEMPORAL = ROOT / "temporal" / "comuni"

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


def _digest(value):
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def assemble(calendar, links, root=EDITIONS, roster_root=ROSTERS):
    """Build the validity intervals of every entity over the calendar.

    Two passes, because holding 98 dates of geometry in memory is ~3 GB. This
    first pass reads each date once, in order, keeping only a digest of each
    municipality's geometry: enough to know when a version ends, not enough to
    write it out. The geometry itself is re-read per edition in `write_regions`.

    A version is (attributes, geometry). Two consecutive dates carrying an
    identical pair are one interval — the exact-equality collapsing of §3, which
    is lossless because it discards repetitions of published geometry and never
    a published geometry. `source_edition` names the edition applicable when the
    version began, which is the file a third party fetches to check it.
    """
    versions = {}
    for at in calendar:
        year = applicable_edition(at)
        geometries = read_edition_geometries(year, root=root)
        source = edition_filename(year)
        for code, attrs in read_roster(at, root=roster_root).items():
            geometry = geometries.get(code)
            if geometry is None:
                continue  # the intra-year cases, resolved by #24's rules
            key = terr_key(attrs["com_catasto_code"], links)
            versions.setdefault(key, {})[at] = {
                "properties": attrs,
                "geometry_digest": _digest(geometry),
                "source_edition": source,
                "edition_year": year,
                "com_istat_code": code,
            }
        del geometries

    out = {}
    for key, series in versions.items():
        collapsed = intervals(calendar, {at: (v["properties"], v["geometry_digest"])
                                         for at, v in series.items()})
        for period in collapsed:
            at = period["valid_from"]
            source = series[at]
            out.setdefault(key, []).append({
                "terr_key": key,
                "valid_from": at,
                "valid_to": period["valid_to"],
                "properties": source["properties"],
                "source_edition": source["source_edition"],
                "edition_year": source["edition_year"],
                "com_istat_code": source["com_istat_code"],
            })
    return out


def write_regions(assembled, out=TEMPORAL, root=EDITIONS):
    """Write one GeoJSON per region, re-reading each edition once.

    Split by region because a release touching one region then rewrites one
    file and git stores a delta, and because a single national file of this size
    opens in nothing. A municipality reassigned to another region — Montecopiolo
    and Sassofeltrio in 2021 — has its versions in both files, each under the
    region it belonged to at the time.
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    by_edition = {}
    for versions in assembled.values():
        for version in versions:
            by_edition.setdefault(version["edition_year"], []).append(version)

    features = {}
    for year in sorted(by_edition):
        geometries = read_edition_geometries(year, root=root)
        for version in by_edition[year]:
            properties = {
                "terr_key": version["terr_key"],
                "valid_from": version["valid_from"],
                "valid_to": version["valid_to"],
                "source_edition": version["source_edition"],
                **version["properties"],
            }
            features.setdefault(properties["reg_istat_code"], []).append({
                "type": "Feature",
                "properties": properties,
                "geometry": geometries[version["com_istat_code"]],
            })
        del geometries

    written = {}
    for region, collected in sorted(features.items()):
        path = out / f"reg={region}.geojson"
        collected.sort(key=lambda f: (f["properties"]["terr_key"],
                                      f["properties"]["valid_from"]))
        path.write_text(json.dumps(
            {"type": "FeatureCollection", "features": collected},
            ensure_ascii=False, separators=(",", ":"),
        ))
        written[region] = (len(collected), path.stat().st_size)
    return written


def build(root=EDITIONS, roster_root=ROSTERS, out=TEMPORAL):
    """The whole assembly: calendar, identity links, intervals, region files."""
    variations = load_variations()
    calendar = change_dates(variations)
    missing = [d for d in calendar if not (Path(roster_root) / f"{d}.json").exists()]
    if missing:
        raise FileNotFoundError(
            f"{len(missing)} rosters missing, first {missing[0]}: "
            f"run `python -m scripts.fetch_situas rosters`"
        )
    links = identity_links(variations)
    assembled = assemble(calendar, links, root=root, roster_root=roster_root)
    written = write_regions(assembled, out=out, root=root)

    versions = sum(len(v) for v in assembled.values())
    total = sum(size for _, size in written.values())
    print(f"{len(assembled)} entities, {versions} versions, "
          f"{len(written)} region files, {total / 1048576:.0f} MB")
    return assembled, written


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
    argv = sys.argv[1:]
    if argv and argv[0] == "build":
        build()
    else:
        main(argv or None)
