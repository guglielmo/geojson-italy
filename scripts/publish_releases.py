"""Publish the materialised file sets as GitHub Releases (issue #28).

One release per publication date, tagged with the date in ISO form
(`2005-01-01`), carrying the assets `scripts.materialize` produced. Release
assets do not count towards repository size and are served over a CDN with
stable URLs, which is what makes publishing the complete series affordable —
98 dates at roughly 17 MB each.

The existing tags (`2019`, `2021.1`, `2021.2`, `2022.1`, `2023.1`, `2026.1`,
`2026.2`) record what this repository published at those moments, which is a
different fact from what ISTAT published for those reference dates. They are
left alone, and an ISO date cannot collide with them.

**Nothing is published without --yes.** Creating a release is public and
outward-facing, and 98 of them is not something to discover after the fact, so
the default is to print what would happen.

Usage:
    python -m scripts.publish_releases                  # dry run, all dates
    python -m scripts.publish_releases --yes --limit 1  # publish one, to look at it
    python -m scripts.publish_releases --yes            # publish the rest
"""

import csv
import subprocess
import sys
from pathlib import Path

from scripts.materialize import ASSETS, INDEX, RELEASES

ROOT = Path(__file__).resolve().parent.parent


def read_index(path=INDEX):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def notes(row):
    """The release body: what this file set is, and what changed on the date.

    Written for someone who arrived from a search engine with a date in hand
    and no knowledge of this repository, so it states the counts, the one
    caveat that bites (a year is not a date) and the licence.
    """
    valid_to = row["valid_to"] or "the present"
    return f"""Administrative boundaries of Italy **valid from {row['valid_from']} to {valid_to}**,
as published by ISTAT for that date.

| | |
| --- | --- |
| Municipalities | {row['municipalities']} |
| What changed on this date | {row['change']} |

### Files

Each asset is gzipped; every common tool reads that directly.

- `limits_IT_municipalities.geojson.gz` — unsimplified, at the source's own resolution
- `limits_IT_provinces.geojson.gz` — all second-level units, dissolved from the municipalities of this date
- `limits_IT_metropolitan_cities.geojson.gz` — the città metropolitane alone; empty before 2015, when they were instituted
- `limits_IT_regions.geojson.gz`
- `limits_IT_all.topo.json.gz` — the three layers in one file, simplified to 20%

### Choosing the right release

A year is not a date: 72 of the 98 publication dates fall inside the year. If you want a
year, take its 1 January. If you have an exact date, look it up in
[`temporal/INDEX.csv`](https://github.com/guglielmo/geojson-italy/blob/main/temporal/INDEX.csv),
which maps every validity interval to its release.

This release is the one to use for any date from {row['valid_from']} up to (but not
including) {valid_to}.

### Provenance

Derived from ISTAT's published boundary editions and territorial reports; each feature
carries `source_edition`, naming the ISTAT file its geometry came from. Schema in
[`temporal/SCHEMA.md`](https://github.com/guglielmo/geojson-italy/blob/main/temporal/SCHEMA.md).

Data are ISTAT-derived and redistributed under CC-BY.
"""


def existing_tags():
    proc = subprocess.run(
        ["gh", "release", "list", "--limit", "500", "--json", "tagName",
         "--jq", ".[].tagName"],
        capture_output=True, text=True, cwd=ROOT, check=True,
    )
    return set(proc.stdout.split())


def assets_for(tag, root=RELEASES):
    directory = Path(root) / tag
    paths = [directory / f"{name}.gz" for name in ASSETS]
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"{tag}: {len(missing)} assets missing, first {missing[0]}")
    return paths


def publish(row, dry_run=True, root=RELEASES):
    tag = row["release_tag"]
    paths = assets_for(tag, root=root)
    command = [
        "gh", "release", "create", tag,
        "--title", f"Boundaries valid from {row['valid_from']}",
        "--notes", notes(row),
        *[str(p) for p in paths],
    ]
    if dry_run:
        total = sum(p.stat().st_size for p in paths)
        print(f"would publish {tag}  {len(paths)} assets, "
              f"{total / 1048576:5.1f} MB  ({row['change']})")
        return None
    subprocess.run(command, check=True, cwd=ROOT, capture_output=True, text=True)
    print(f"published {tag}")
    return tag


def main(argv):
    dry_run = "--yes" not in argv
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None

    rows = read_index()
    published = existing_tags() if not dry_run else set()
    done = 0
    for row in rows:
        if row["release_tag"] in published:
            continue
        publish(row, dry_run=dry_run)
        done += 1
        if limit and done >= limit:
            break

    if dry_run:
        print(f"\n{done} releases would be created. Nothing was published: "
              f"pass --yes to do it.")


if __name__ == "__main__":
    main(sys.argv[1:])
