"""Measure the ISTAT edition series (issue #24).

Answers, from the downloaded editions rather than from assertion:

1. How many municipalities each edition carries.
2. Which editions re-generalise geometry — that is, republish a changed shape
   for municipalities that had no administrative event.
3. How far exact-equality interval collapsing gets us, which is the number the
   whole archive's feasibility rests on (design §3).

Geometry is compared by hashing its canonical JSON form. That is deliberately
byte-exact: tolerance-based merging is forbidden by D2, because collapsing two
editions' geometries means publishing one edition's shape under another
edition's date.

Usage:
    python -m scripts.measure_editions
"""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EDITIONS = ROOT / "build" / "editions"

# Field holding the municipality's ISTAT code. ISTAT renamed it across the
# series, so the reader tries them in order of preference.
_CODE_FIELDS = ("PRO_COM_T", "PRO_COM", "COD_ISTAT", "ISTAT", "PROCOM")


def _code_field(props):
    for field in _CODE_FIELDS:
        if field in props:
            return field
    raise KeyError(f"no municipality code field in {sorted(props)}")


def geometry_digest(geometry):
    """Stable hash of a geometry's exact coordinates."""
    blob = json.dumps(geometry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def read_edition(year):
    """Return {istat_code: geometry digest} for one edition."""
    path = EDITIONS / str(year) / "comuni.geojson"
    data = json.loads(path.read_text())
    out = {}
    for feature in data["features"]:
        props = feature["properties"]
        field = _code_field(props)
        code = str(props[field]).strip().zfill(6)
        out[code] = geometry_digest(feature["geometry"])
    return out


def load_series(years):
    return {y: read_edition(y) for y in years}


def changed_between(a, b):
    """Codes present in both editions whose geometry differs."""
    return {code for code in a.keys() & b.keys() if a[code] != b[code]}


def collapse_to_intervals(series):
    """Merge consecutive byte-identical geometries into validity intervals.

    Returns (versions, instances): the number of distinct versions kept and the
    number of edition-instances read. Their ratio is the saving that makes the
    archive affordable.
    """
    years = sorted(series)
    by_code = defaultdict(list)
    for year in years:
        for code, digest in series[year].items():
            by_code[code].append((year, digest))

    versions = 0
    instances = 0
    for entries in by_code.values():
        instances += len(entries)
        previous = None
        for _, digest in entries:
            if digest != previous:
                versions += 1
                previous = digest
    return versions, instances
