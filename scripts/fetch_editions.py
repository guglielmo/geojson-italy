"""Download and convert the ISTAT boundary editions (issue #24).

Usage:
    python -m scripts.fetch_editions [YEAR ...]

With no arguments, fetches the whole series (2001-2026) into build/editions/.
Each edition is downloaded once, its SHA-256 recorded, unpacked, and its
municipality layer converted to GeoJSON in EPSG:4326.

Already-downloaded editions are skipped, so the script is resumable: ISTAT
serves roughly 300 MB across the series and a re-run should not re-fetch it.

The checksum is not hygiene. The archive's claim is that a given geometry came
from a named published file (design D2), and a third party can only falsify
that claim if the file is identified precisely enough to fetch and compare.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from scripts.istat_editions import SERIES_YEARS, edition_filename, edition_url

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "editions"

# The municipality layer is named differently across the series: the annual
# editions use Com<date>_g_WGS84, the census ones use Com<year>_g_WGS84 or a
# plain Com_g. Globbed rather than constructed, then verified to be unique.
_MUNI_GLOBS = ("Com*_g_WGS84.shp", "Com*_g.shp", "Com*.shp")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(year, force=False):
    """Fetch one edition's zip, returning (path, sha256)."""
    dest = OUT / str(year)
    dest.mkdir(parents=True, exist_ok=True)
    zip_path = dest / f"{edition_filename(year)}.zip"

    if zip_path.exists() and not force:
        return zip_path, _sha256(zip_path)

    url = edition_url(year)
    subprocess.run(
        ["curl", "-fsSL", "--retry", "3", "-o", str(zip_path), url],
        check=True,
    )
    return zip_path, _sha256(zip_path)


def unpack(year, zip_path):
    """Unpack the zip and return the directory holding the shapefiles."""
    dest = OUT / str(year) / "unpacked"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    return dest


def find_municipality_shapefile(unpacked):
    """Locate the municipality layer, refusing to guess between candidates."""
    for pattern in _MUNI_GLOBS:
        hits = sorted(unpacked.rglob(pattern))
        # Exclude the province and region layers that share the Com prefix in
        # no edition, but guard anyway against picking up a stray file.
        hits = [h for h in hits if h.stem.lower().startswith("com")]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise RuntimeError(
                f"{unpacked}: {len(hits)} candidate municipality layers for "
                f"pattern {pattern}: {[h.name for h in hits]}"
            )
    raise RuntimeError(f"{unpacked}: no municipality shapefile found")


def convert(year, shapefile):
    """Convert the municipality layer to GeoJSON in EPSG:4326.

    -proj wgs84 is mandatory: the _WGS84 in the ISTAT filenames names the
    datum, while the .prj is WGS_1984_UTM_Zone_32N in metres.
    """
    out = OUT / str(year) / "comuni.geojson"
    # mapshaper is invoked from the repository root with paths relative to it.
    # Absolute paths are not reliably resolved by the mapshaper CLI in
    # containerised environments, where they fail as "File not found" even
    # though the file is readable by every other process.
    cmd = ["mapshaper",
           "-i", str(shapefile.relative_to(ROOT)), "encoding=utf8",
           "-proj", "wgs84",
           "-o", str(out.relative_to(ROOT)), "format=geojson", "gj2008"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if proc.returncode != 0:
        # Surfacing mapshaper's own message matters: swallowing it turns every
        # conversion problem into an opaque non-zero exit.
        raise RuntimeError(
            f"mapshaper failed on {year} ({shapefile.name}), "
            f"exit {proc.returncode}\n"
            f"  command: {' '.join(cmd)}\n"
            f"  stderr: {proc.stderr.strip()}\n"
            f"  stdout: {proc.stdout.strip()}"
        )
    return out


def fetch(year, force=False):
    """Fetch, unpack and convert one edition. Returns a record dict."""
    zip_path, digest = download(year, force=force)
    unpacked = unpack(year, zip_path)
    shapefile = find_municipality_shapefile(unpacked)
    geojson = convert(year, shapefile)
    n = len(json.loads(geojson.read_text())["features"])
    return {
        "year": year,
        "source_edition": edition_filename(year),
        "url": edition_url(year),
        "sha256": digest,
        "zip_bytes": zip_path.stat().st_size,
        "shapefile": shapefile.name,
        "municipalities": n,
    }


def main(years):
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "MANIFEST.json"
    manifest = {}
    if manifest_path.exists():
        manifest = {int(k): v for k, v in
                    json.loads(manifest_path.read_text()).items()}

    for year in years:
        record = fetch(year)
        manifest[year] = record
        print(f"{year}  {record['municipalities']:>5} comuni  "
              f"{record['zip_bytes'] / 1048576:5.1f} MB  "
              f"{record['source_edition']}  {record['sha256'][:16]}")
        manifest_path.write_text(
            json.dumps({str(k): manifest[k] for k in sorted(manifest)},
                       indent=2, ensure_ascii=False)
        )

    return manifest


if __name__ == "__main__":
    requested = [int(a) for a in sys.argv[1:]] or list(SERIES_YEARS)
    main(requested)
