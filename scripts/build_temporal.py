"""Joining the roster to the geometry (issue #25).

The archive's two halves meet here. The roster (SITUAS report 61) says which
municipalities were valid at a date and what their codes and names were; the
ISTAT boundary edition says what shape they had.

**The join is on identity, not on the ISTAT code.** That code embeds the
province and changes with every reassignment, so between a reassignment and the
next 1 January the two sides disagree about a municipality's code while agreeing
about the municipality. Both sides are therefore resolved to the cadastral key
first — see `edition_geometries_by_key`, which records what joining on the ISTAT
code costs.

**Which edition applies to a date** is the latest edition whose *reference date*
is at or before it. Not the edition of the same year: for 2011-02-11 the
applicable edition is the 2010 one, because the 2011 edition describes 9 October
2011 and did not exist yet at the date being published.

The interesting output is not the matched majority, it is the two residuals:

- **A municipality in the roster with no geometry.** ISTAT publishes boundaries
  only at 1 January, so one created during the year has none until the next
  edition. Measured over the calendar: **39 municipalities across 42 dates**,
  the number §6 predicts. `resolve_geometry` applies its two rules — the union
  of predecessors for a merger, the next edition's shape for a detachment — and
  fails on anything else.
- **A geometry with no municipality in the roster.** Measured: none, at any
  date. Reported rather than dropped, because it would mean the two ISTAT
  products disagree about who existed, which is a finding, not a nuisance.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts.change_dates import change_dates, load_variations
from scripts.identity import (
    creation_at,
    creations,
    events_by_key,
    identity_links,
    intervals,
    terr_key,
    version_reason,
)
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


def edition_geometries_by_key(year, links, root=EDITIONS, roster_root=ROSTERS):
    """{terr_key: geometry} for one edition.

    **Not keyed on the ISTAT code.** That code embeds the province, so it
    changes whenever a municipality is reassigned — 51 municipalities to Monza
    e della Brianza in 2009, 40 to Fermo, 10 to Barletta-Andria-Trani, 377 in
    Sardinia in 2016 and again in 2026, Montecopiolo and Sassofeltrio in 2021.
    Between the reassignment and the next 1 January the roster carries the new
    code and the applicable edition still carries the old one, so a join on the
    ISTAT code loses exactly the municipalities the archive exists to follow.
    Measured before this was fixed: 310 municipalities "without geometry"
    against the 39 the design predicts, and 1,539 geometries "without a
    municipality" — the same events counted from both sides.

    The edition's codes are resolved through the roster at the edition's own
    reference date, which is in the calendar by construction, and then keyed on
    the archive's identity.
    """
    reference = edition_reference_date(year)
    roster = read_roster(reference, root=roster_root)
    geometries = read_edition_geometries(year, root=root)

    out, orphans = {}, []
    for code, geometry in geometries.items():
        attrs = roster.get(code)
        if attrs is None:
            # The edition holds a municipality its own date's roster does not.
            # Never observed; reported rather than dropped, because it would
            # mean the two ISTAT products disagree about who existed.
            orphans.append(code)
            continue
        out[terr_key(attrs["com_catasto_code"], links)] = geometry
    return out, sorted(orphans)


def join(at, links=None, root=EDITIONS, roster_root=ROSTERS):
    """Join the roster at a date to the applicable edition's geometry.

    Returns (features, missing_geometry, orphan_geometry): the municipalities
    resolved with a shape, those the applicable edition has no geometry for,
    and the geometries the edition's own roster cannot account for.
    """
    links = {} if links is None else links
    year = applicable_edition(at)
    roster = read_roster(at, root=roster_root)
    geometries, orphans = edition_geometries_by_key(
        year, links, root=root, roster_root=roster_root)
    source = edition_filename(year)

    features, missing = [], []
    for _, attrs in sorted(roster.items()):
        key = terr_key(attrs["com_catasto_code"], links)
        geometry = geometries.get(key)
        if geometry is None:
            missing.append(attrs)
            continue
        features.append({
            "type": "Feature",
            "properties": {**attrs, "terr_key": key, "source_edition": source},
            "geometry": geometry,
        })
    return features, missing, orphans


# Identifiers this repository publishes that no ISTAT source holds. They are
# carried across from the current vintage for entities that still exist, and
# stay null for the rest — see #31 and the note in SCHEMA.md.
LEGACY_IDENTIFIERS = ("op_id", "opdm_id", "minint_elettorale", "minint_finloc")


def legacy_identifiers(links, path=ROOT / "comuni.geojson"):
    """{terr_key: {op_id, opdm_id, minint_*}} from the current vintage.

    Joined on the cadastral code and never on the ISTAT code, which is not
    stable across reassignment — the 377 Sardinian municipalities changed theirs
    in 2026 with zero overlap. Keying on `terr_key` rather than on the current
    cadastral code also carries Lonato del Garda's identifiers back to its
    versions as Lonato, which the raw code would not.
    """
    data = json.loads(Path(path).read_text())
    out = {}
    for feature in data["features"]:
        props = feature["properties"]
        code = props.get("com_catasto_code")
        if not code:
            continue
        out[terr_key(code, links)] = {
            field: props.get(field) for field in LEGACY_IDENTIFIERS
        }
    return out


class UnresolvedGeometry(ValueError):
    """A municipality with no geometry and no rule to obtain one.

    The design's instruction, and the reason this is an exception rather than a
    fallback: a silent default here would put a fabricated boundary in a public
    archive under ISTAT's name.
    """


def union(geometries, tmp=None):
    """Merge adjacent published geometries into one.

    Used for a municipality created by merger before ISTAT first drew it: its
    boundary is its predecessors', with the borders between them removed. This
    is arithmetic on published data rather than reconciliation — the same
    dissolve this repository already uses to derive provinces and regions from
    municipalities — so it does not offend D2.
    """
    tmp = Path(tmp or ROOT / "build" / "union")
    tmp.mkdir(parents=True, exist_ok=True)
    source, target = tmp / "in.geojson", tmp / "out.geojson"
    source.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"g": 1},
                      "geometry": geometry} for geometry in geometries],
    }))
    proc = subprocess.run(
        ["mapshaper", "-i", str(source.relative_to(ROOT)), "-clean",
         "-dissolve", "-o", str(target.relative_to(ROOT)),
         "format=geojson", "gj2008"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"mapshaper failed to dissolve: {proc.stderr.strip()}")

    # gj2008 writes a GeometryCollection when the output carries no properties
    # and a FeatureCollection when it does, so both shapes are read.
    result = json.loads(target.read_text())
    shapes = result.get("geometries")
    if shapes is None:
        shapes = [feature["geometry"] for feature in result["features"]]

    # A dissolve normally returns one shape. More than one is legitimate rather
    # than an error: an exclave stays separate from the body it belongs to, as
    # it does in ISTAT's own geometries.
    polygons = []
    for shape in shapes:
        if shape["type"] == "Polygon":
            polygons.append(shape["coordinates"])
        elif shape["type"] == "MultiPolygon":
            polygons.extend(shape["coordinates"])
        else:
            raise RuntimeError(f"unexpected dissolve output: {shape['type']}")
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def resolve_geometry(key, at, year, geometries, creations_by_key, links,
                     root=EDITIONS, roster_root=ROSTERS, cache=None):
    """The geometry of a municipality the applicable edition does not carry.

    ISTAT publishes boundaries once a year, so a municipality created during
    the year has none until the next edition. Two rules, both from §6, and both
    recording how the result was obtained:

    - **created by merger** — the union of its predecessors' geometries in the
      applicable edition, `(union of predecessors)`;
    - **created by detachment** — its own geometry from the next edition that
      carries it, `(anticipated)`. A detached municipality's boundary cannot be
      derived from its predecessor, which survives with a reduced area.

    Anything else raises.
    """
    cache = {} if cache is None else cache
    if (key, year) in cache:
        return cache[(key, year)]

    creation = creation_at(creations_by_key, key, at)
    if creation is None:
        raise UnresolvedGeometry(
            f"{key} has no geometry in the {year} edition and no recorded "
            f"constitution on or before {at}"
        )

    if creation["kind"] == "merger":
        shapes = []
        for predecessor in creation["predecessors"]:
            shape = geometries.get(terr_key(predecessor, links))
            if shape is None:
                raise UnresolvedGeometry(
                    f"{key} was created from {predecessor}, which the {year} "
                    f"edition does not carry either"
                )
            shapes.append(shape)
        resolved = (union(shapes), f"{edition_filename(year)} (union of predecessors)")
    else:
        resolved = None
        for later in (y for y in SERIES_YEARS if y > year):
            candidates, _ = edition_geometries_by_key(
                later, links, root=root, roster_root=roster_root)
            if key in candidates:
                resolved = (candidates[key],
                            f"{edition_filename(later)} (anticipated)")
                break
        if resolved is None:
            raise UnresolvedGeometry(
                f"{key} was detached on {creation['date']} and appears in no "
                f"later edition"
            )

    cache[(key, year)] = resolved
    return resolved


def _digest(value):
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def assemble(calendar, links, creations_by_code, events=None, root=EDITIONS,
             roster_root=ROSTERS):
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
    events = {} if events is None else events
    creations_by_key = {terr_key(code, links): entries
                        for code, entries in creations_by_code.items()}
    resolved = {}
    # The calendar is ordered and so are the editions, so one cached edition is
    # enough: the 72 intra-year dates reuse the edition their year opened with,
    # and each of the 26 files is read once instead of once per date.
    cached_year, geometries = None, {}
    for at in calendar:
        year = applicable_edition(at)
        if year != cached_year:
            geometries, _ = edition_geometries_by_key(
                year, links, root=root, roster_root=roster_root)
            cached_year = year
        source = edition_filename(year)
        for code, attrs in read_roster(at, root=roster_root).items():
            key = terr_key(attrs["com_catasto_code"], links)
            geometry, provenance = geometries.get(key), source
            if geometry is None:
                geometry, provenance = resolve_geometry(
                    key, at, year, geometries, creations_by_key, links,
                    root=root, roster_root=roster_root, cache=resolved)
            versions.setdefault(key, {})[at] = {
                "properties": attrs,
                "geometry_digest": _digest(geometry),
                "source_edition": provenance,
                "edition_year": year,
                "com_istat_code": code,
            }
    del geometries

    out = {}
    for key, series in versions.items():
        collapsed = intervals(calendar, {at: (v["properties"], v["geometry_digest"])
                                         for at, v in series.items()})
        previous = None
        for period in collapsed:
            at = period["valid_from"]
            source = series[at]
            out.setdefault(key, []).append({
                "terr_key": key,
                "valid_from": at,
                "valid_to": period["valid_to"],
                "version_reason": version_reason(
                    key, at, previous, creations_by_key, events),
                "properties": source["properties"],
                "source_edition": source["source_edition"],
                "edition_year": source["edition_year"],
                "com_istat_code": source["com_istat_code"],
            })
            previous = at
    return out


def write_regions(assembled, links=None, creations_by_code=None, legacy=None,
                  out=TEMPORAL, root=EDITIONS, roster_root=ROSTERS):
    """Write one GeoJSON per region, re-reading each edition once.

    Split by region because a release touching one region then rewrites one
    file and git stores a delta, and because a single national file of this size
    opens in nothing. A municipality reassigned to another region — Montecopiolo
    and Sassofeltrio in 2021 — has its versions in both files, each under the
    region it belonged to at the time.
    """
    links = {} if links is None else links
    legacy = {} if legacy is None else legacy
    creations_by_key = {terr_key(code, links): entries
                        for code, entries in (creations_by_code or {}).items()}
    resolved = {}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    by_edition = {}
    for versions in assembled.values():
        for version in versions:
            by_edition.setdefault(version["edition_year"], []).append(version)

    features = {}
    for year in sorted(by_edition):
        geometries, _ = edition_geometries_by_key(
            year, links, root=root, roster_root=roster_root)
        for version in by_edition[year]:
            properties = {
                "terr_key": version["terr_key"],
                "valid_from": version["valid_from"],
                "valid_to": version["valid_to"],
                "version_reason": version["version_reason"],
                "source_edition": version["source_edition"],
                **version["properties"],
                # Null for every municipality suppressed before the current
                # vintage: no ISTAT source holds these, so there is nothing to
                # carry across for an entity that no longer exists.
                **{field: None for field in LEGACY_IDENTIFIERS},
                **legacy.get(version["terr_key"], {}),
            }
            key = version["terr_key"]
            geometry = geometries.get(key)
            if geometry is None:
                geometry, _ = resolve_geometry(
                    key, version["valid_from"], year, geometries,
                    creations_by_key, links, root=root, roster_root=roster_root,
                    cache=resolved)
            features.setdefault(properties["reg_istat_code"], []).append({
                "type": "Feature",
                "properties": properties,
                "geometry": geometry,
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
    born = creations(variations)
    events = events_by_key(variations, links)
    assembled = assemble(calendar, links, born, events, root=root,
                         roster_root=roster_root)
    written = write_regions(assembled, links, born, legacy_identifiers(links),
                            out=out, root=root, roster_root=roster_root)

    versions = sum(len(v) for v in assembled.values())
    total = sum(size for _, size in written.values())
    print(f"{len(assembled)} entities, {versions} versions, "
          f"{len(written)} region files, {total / 1048576:.0f} MB")
    return assembled, written


def main(dates=None):
    """Report the join over every date whose roster is cached."""
    variations = load_variations()
    calendar = change_dates(variations)
    links = identity_links(variations)
    cached = set(available())
    dates = dates or [d for d in calendar if d in cached]

    print(f"{'date':<12}{'edition':>9}{'joined':>8}{'no geom':>9}{'orphan':>8}")
    total_missing, total_orphans = 0, 0
    for at in dates:
        year = applicable_edition(at)
        features, missing, orphans = join(at, links)
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
