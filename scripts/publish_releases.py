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
    python -m scripts.publish_releases --yes --replace  # re-upload corrected assets
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

### Three things to know before using these files

**ISTAT draws boundaries once a year, on 1 January.** Codes, names, provincial and regional
assignment are exact for {row['valid_from']} — those change on the day the act says. Boundaries
are the ones ISTAT last published, so at a date inside the year they come from that year's
1 January edition. A change of code or of province, which is the common case, moves no
boundary and is represented exactly; a boundary moved by a transfer of territory appears at
the following edition.

**Do not read a diff between two dates as administrative change.** ISTAT re-generalises its
geometries in some editions and not others — 2002, 2010, 2011, 2012, 2019, 2022 and 2025 —
so comparing two adjacent years shows roughly 7,900 changed boundaries and means nothing
happened. Every feature carries `version_reason`: `source_regeneralization` is ISTAT
redrawing its own lines, and the `admin_*` values are the real events. Filter on it.

**Municipalities that ISTAT had not yet drawn** carry it in `source_edition`:
`(union of predecessors)` where a merger's boundary is its predecessors' dissolved together,
`(anticipated)` where a detached municipality's boundary is taken from the next edition that
carries it. Both are stated rather than smoothed over.

### Provenance

Faithful to what ISTAT published for this date: not smoothed, not normalised, not reconciled
across editions. Each feature carries `source_edition`, naming the ISTAT file its geometry
was read from, so the claim can be checked by downloading that file. Every field is
documented in
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


def publish(row, dry_run=True, root=RELEASES, replace=False):
    """Create the release, or replace the assets of one that already exists.

    Replacing matters because an asset can be wrong after it is published: the
    first upload of this series carried Italian-only names for the 124
    bilingual municipalities and no ISO codes at all. A release whose assets
    cannot be corrected is a release nobody can trust.
    """
    tag = row["release_tag"]
    paths = assets_for(tag, root=root)
    if replace:
        # The notes go up again too. They are the only documentation most
        # consumers read — they arrive from a search engine with a date in
        # hand — so leaving a corrected file set under stale caveats would
        # keep the worst half of the mistake.
        command = ["gh", "release", "edit", tag, "--notes", notes(row)]
        verb = "would replace the assets and notes of"
    else:
        command = [
            "gh", "release", "create", tag,
            "--title", f"Boundaries valid from {row['valid_from']}",
            "--notes", notes(row),
            *[str(p) for p in paths],
        ]
        verb = "would publish"
    if dry_run:
        total = sum(p.stat().st_size for p in paths)
        print(f"{verb} {tag}  {len(paths)} assets, "
              f"{total / 1048576:5.1f} MB  ({row['change']})")
        return None
    subprocess.run(command, check=True, cwd=ROOT, capture_output=True, text=True)
    if replace:
        subprocess.run(
            ["gh", "release", "upload", tag,
             *[str(p) for p in paths], "--clobber"],
            check=True, cwd=ROOT, capture_output=True, text=True,
        )
    print(f"{'replaced' if replace else 'published'} {tag}")
    return tag


def main(argv):
    dry_run = "--yes" not in argv
    replace = "--replace" in argv
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    wanted = {a for a in argv if a[:1].isdigit()}

    rows = read_index()
    published = existing_tags()
    done = 0
    for row in rows:
        already = row["release_tag"] in published
        if already and not replace:
            continue
        if replace and not already:
            continue
        if wanted and row["release_tag"] not in wanted:
            continue
        publish(row, dry_run=dry_run, replace=replace)
        done += 1
        if limit and done >= limit:
            break

    if dry_run:
        print(f"\n{done} releases would be created. Nothing was published: "
              f"pass --yes to do it.")


if __name__ == "__main__":
    main(sys.argv[1:])
