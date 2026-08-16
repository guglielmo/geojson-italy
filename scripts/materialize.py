"""Materialise the archive into downloadable file sets (issue #28).

**This is a maintainer tool. It is not the path a consumer takes.** The whole
point of D8 is that someone who wants the boundaries of 2005 downloads a file:
they have no build step, no interpreter version and no dependency on this
project's tooling. So every publication date is pre-materialised here and
published as release assets, and the temporal dataset is never the consumer
interface.

Per date, the same shape of file set the repository root carries today:

    limits_IT_municipalities.geojson.gz     unsimplified, source resolution
    limits_IT_provinces.geojson.gz          all second-level units
    limits_IT_metropolitan_cities.geojson.gz  the città metropolitane alone
    limits_IT_regions.geojson.gz
    limits_IT_all.topo.json.gz              three layers, simplified to 20%

Provinces and regions are dissolved from the municipalities of *that date*, not
carried over from today: in 2005 there were 103 provinces and no metropolitan
cities at all, and the file set has to say so.

The per-region and per-province subsets (131 files) stay current-vintage only,
per D3. At 98 dates they would be 12,838 assets, and the national file is the
one nearly every consumer of a past date wants.

**A year is not a date.** The archive has 98 publication dates and 72 of them
fall inside the year, so "2005" is ambiguous — it holds three. The convention,
stated in the README and encoded in `resolve`: a bare year means its 1 January,
which is what someone asking for "the 2005 boundaries" almost always means, and
`INDEX.csv` resolves any exact date for the cases where it isn't.

Usage:
    python -m scripts.materialize index                 # write temporal/INDEX.csv
    python -m scripts.materialize date 2005-01-01 ...   # one or more dates
    python -m scripts.materialize all [--limit N]       # every date, resumable
"""

import csv
import gzip
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

from scripts.change_dates import change_dates, load_variations

ROOT = Path(__file__).resolve().parent.parent
TEMPORAL = ROOT / "temporal" / "comuni"
INDEX = ROOT / "temporal" / "INDEX.csv"
RELEASES = ROOT / "build" / "releases"

# Fields that survive a dissolve. Anything not listed here is lost on the
# province and region layers, which is why a new property has to be added in
# both this list and the two generation scripts.
PROVINCE_FIELDS = (
    "prov_name,prov_istat_code_num,prov_acr,prov_iso_3166_2,prov_uts_code,"
    "prov_tipo_uts,reg_name,reg_istat_code,reg_istat_code_num,reg_iso_3166_2"
)
REGION_FIELDS = "reg_name,reg_istat_code_num,reg_iso_3166_2"

METROPOLITAN = "Città metropolitana"

ASSETS = (
    "limits_IT_municipalities.geojson",
    "limits_IT_provinces.geojson",
    "limits_IT_metropolitan_cities.geojson",
    "limits_IT_regions.geojson",
    "limits_IT_all.topo.json",
)


class MaterializationFailed(RuntimeError):
    """A date whose file set could not be produced, or came out wrong."""


def resolve(wanted, calendar):
    """The publication date serving `wanted`, which may be a year or a date.

    A bare year resolves to its 1 January. An exact date resolves to the latest
    publication date at or before it — the interval filter consumers are told to
    use, done for them.
    """
    wanted = str(wanted).strip()
    if len(wanted) == 4 and wanted.isdigit():
        wanted = f"{wanted}-01-01"
    covering = [at for at in calendar if at <= wanted]
    if not covering:
        raise ValueError(
            f"{wanted} precedes the series, which begins {min(calendar)}"
        )
    return max(covering)


def snapshot(at, root=TEMPORAL):
    """The municipalities valid on a date, as a FeatureCollection.

    Reads the region files one at a time and keeps only what the date selects,
    because the whole dataset is 359 MB and a snapshot is a fortieth of it.
    """
    features = []
    for path in sorted(Path(root).glob("reg=*.geojson")):
        data = json.loads(path.read_text())
        for feature in data["features"]:
            props = feature["properties"]
            if props["valid_from"] <= at and (props["valid_to"] is None
                                              or props["valid_to"] > at):
                features.append(feature)
        del data
    features.sort(key=lambda f: f["properties"]["com_istat_code"])
    return {"type": "FeatureCollection", "features": features}


def _mapshaper(args, description):
    proc = subprocess.run(["mapshaper", *args], capture_output=True, text=True,
                          cwd=ROOT)
    if proc.returncode != 0:
        raise MaterializationFailed(
            f"{description} failed\n  mapshaper {' '.join(args)}\n"
            f"  {proc.stderr.strip()}"
        )
    return proc


def _rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


def _count(path):
    data = json.loads(Path(path).read_text())
    if data.get("type") == "Topology":
        return {name: len(layer["geometries"])
                for name, layer in data["objects"].items()}
    # An empty layer is written as a bare GeometryCollection, and an empty
    # layer is a real answer here: metropolitan cities were instituted in 2015,
    # so every date before that has none. The file is still published, because
    # a consumer pinning the URL should get an empty collection rather than a
    # 404 — the same reason vacant province codes still get a file.
    if "features" not in data:
        return len(data.get("geometries", []))
    return len(data["features"])


def _overlapping(collection):
    """Whether the snapshot contains a geometry anticipated from a later edition.

    It does at the four dates between a detachment and the next 1 January.
    Baranzate was constituted on 12 December 2001 and its boundary comes from
    the 2002 edition, while Bollate, which it was detached from, still carries
    its undivided 2001 shape: the two overlap, and no ISTAT edition describes
    that moment consistently.

    This matters because `-clean` resolves overlaps by discarding one of the
    polygons — silently. It is the same mechanism that drops Miagliano from the
    current `limits_IT_all.topo.json` (#34). Where the overlap is expected the
    clean is skipped, so the municipality survives; subtracting the new
    boundary from its predecessor's would produce a shape ISTAT never published,
    which D2 forbids.
    """
    return any(
        (feature["properties"].get("source_edition") or "").endswith("(anticipated)")
        for feature in collection["features"]
    )


def materialize(at, out=RELEASES, root=TEMPORAL, force=False):
    """Write one date's file set, gzipped. Returns the counts per layer."""
    target = Path(out) / at
    if target.exists() and not force and all(
            (target / f"{name}.gz").exists() for name in ASSETS):
        return {"skipped": True}
    target.mkdir(parents=True, exist_ok=True)

    municipalities = target / ASSETS[0]
    collection = snapshot(at, root=root)
    if not collection["features"]:
        raise MaterializationFailed(f"{at}: no municipalities in the archive")
    municipalities.write_text(json.dumps(collection, ensure_ascii=False,
                                         separators=(",", ":")))
    expected = len(collection["features"])
    clean = [] if _overlapping(collection) else ["-clean"]
    del collection

    # Provinces and regions, both dissolved from layer 1 — the municipalities —
    # so that regions come from municipalities and not from provinces.
    _mapshaper([
        "-i", _rel(municipalities), "encoding=utf8", *clean,
        "-rename-layers", "municipalities",
        "-dissolve", "prov_istat_code", "+",
        f"copy-fields={PROVINCE_FIELDS}", "name=provinces",
        "-target", "1",
        "-dissolve", "reg_istat_code", "+",
        f"copy-fields={REGION_FIELDS}", "name=regions",
        "-o", _rel(target / ASSETS[1]), "bbox", "gj2008", "format=geojson",
        "target=provinces",
        "-o", _rel(target / ASSETS[3]), "bbox", "gj2008", "format=geojson",
        "target=regions",
    ], f"{at}: provinces and regions")

    # The metropolitan cities alone. They are second-level units and stay in the
    # provinces file as well; this is the layer that does not exist today.
    _mapshaper([
        "-i", _rel(target / ASSETS[1]), "encoding=utf8",
        "-filter", f'prov_tipo_uts=="{METROPOLITAN}"',
        "-o", _rel(target / ASSETS[2]), "bbox", "gj2008", "format=geojson",
    ], f"{at}: metropolitan cities")

    # Simplify first, then dissolve from the simplified municipalities, so the
    # three layers share their borders exactly. One invocation, with no second
    # -clean: re-cleaning after simplification is what drops a municipality
    # from the current limits_IT_all.topo.json (issue #34).
    _mapshaper([
        "-i", _rel(municipalities), "encoding=utf8", *clean,
        "-simplify", "20%", "weighted",
        "-rename-layers", "municipalities",
        "-dissolve", "prov_istat_code", "+",
        f"copy-fields={PROVINCE_FIELDS}", "name=provinces",
        "-target", "1",
        "-dissolve", "reg_istat_code", "+",
        f"copy-fields={REGION_FIELDS}", "name=regions",
        "-o", _rel(target / ASSETS[4]), "bbox", "format=topojson",
        "target=regions,provinces,municipalities",
    ], f"{at}: topojson")

    counts = {name: _count(target / name) for name in ASSETS}

    # The check issue #34 exists for: a municipality lost to -clean produces a
    # smaller layer and no error. Here it is an error.
    topology = counts[ASSETS[4]]
    if topology["municipalities"] != expected:
        raise MaterializationFailed(
            f"{at}: the topojson carries {topology['municipalities']} "
            f"municipalities against {expected} in the geojson"
        )

    for name in ASSETS:
        path = target / name
        with open(path, "rb") as raw, gzip.open(f"{path}.gz", "wb") as packed:
            shutil.copyfileobj(raw, packed)
        path.unlink()

    return counts


def index_rows(calendar, root=TEMPORAL):
    """One row per validity interval: which release serves which dates.

    This is what turns "I need the boundaries of 10 September 2021" into a
    lookup. The `change` column says what happened on the date, read from the
    version_reason of the versions that start there.
    """
    starts = {at: Counter() for at in calendar}
    counts = {at: 0 for at in calendar}
    ends = {at: 0 for at in calendar}
    spans = {}
    for path in sorted(Path(root).glob("reg=*.geojson")):
        data = json.loads(path.read_text())
        for feature in data["features"]:
            props = feature["properties"]
            if props["valid_from"] in starts:
                starts[props["valid_from"]][props["version_reason"]] += 1
            spans.setdefault(props["terr_key"], []).append(
                (props["valid_from"], props["valid_to"]))
            for at in calendar:
                if props["valid_from"] <= at and (props["valid_to"] is None
                                                  or props["valid_to"] > at):
                    counts[at] += 1
        del data

    # A municipality ceasing to exist is a change too, and often the only
    # visible one: when Lirio was incorporated into Montalto Pavese on 31
    # January 2026, no new version began — Montalto's attributes and geometry
    # were unchanged until the next edition — so counting starts alone reported
    # "no administrative change" on the day a municipality disappeared.
    #
    # An interval ending is not enough by itself: most endings are one version
    # giving way to the next. What counts is an ending with no version of the
    # same entity beginning on that date, which is also how Baranzate's
    # abolition in 2003 is caught while its 2004 return is not double-counted.
    for periods in spans.values():
        beginnings = {frm for frm, _ in periods}
        for _, to in periods:
            if to and to not in beginnings and to in ends:
                ends[to] += 1

    rows = []
    for at, following in zip(calendar, list(calendar[1:]) + [None]):
        described = [f"{n} {reason}" for reason, n in
                     sorted(starts[at].items(), key=lambda kv: -kv[1])
                     if reason != "source_regeneralization"]
        if ends[at]:
            described.append(f"{ends[at]} soppressi")
        change = ", ".join(described) or "no administrative change"
        rows.append({
            "valid_from": at,
            "valid_to": following or "",
            "release_tag": at,
            "municipalities": counts[at],
            "change": change,
        })
    return rows


def write_index(rows, path=INDEX):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # LF, not the CRLF csv defaults to: this file is read by people and by git
    # as much as by csv readers.
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]),
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def main(argv):
    command = argv[0] if argv else "index"
    rest = argv[1:]
    calendar = change_dates(load_variations())

    if command == "index":
        path = write_index(index_rows(calendar))
        print(f"{path}: {len(calendar)} intervals")
        return

    if command == "date":
        for wanted in rest:
            at = resolve(wanted, calendar)
            counts = materialize(at)
            print(f"{at}  {counts}")
        return

    if command == "all":
        limit = None
        if "--limit" in rest:
            limit = int(rest[rest.index("--limit") + 1])
        done = 0
        for at in calendar:
            counts = materialize(at)
            if counts.get("skipped"):
                continue
            done += 1
            print(f"{at}  {counts[ASSETS[0]]} comuni, "
                  f"{counts[ASSETS[1]]} province, {counts[ASSETS[3]]} regioni, "
                  f"{counts[ASSETS[2]]} città metropolitane")
            if limit and done >= limit:
                print(f"stopping at {limit} dates materialised")
                break
        return

    raise SystemExit(f"unknown command {command!r}: index | date | all")


if __name__ == "__main__":
    main(sys.argv[1:])
