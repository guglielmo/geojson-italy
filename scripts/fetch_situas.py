"""Download the ISTAT SITUAS reports (issue #24, design D9).

Usage:
    python -m scripts.fetch_situas variations [--until YYYY-MM-DD]
    python -m scripts.fetch_situas seed --seed-from DIR
    python -m scripts.fetch_situas rosters [--limit N] [--seed-from DIR] [DATE ...]
    python -m scripts.fetch_situas catalogue

`variations` fetches the four variation reports over their full coverage.
`rosters` fetches report 61 — the complete municipality roster with cadastral
codes — for each change date; with no arguments it uses the dates derived by
`scripts.change_dates`, which is the set the archive publishes.

Everything lands in build/situas/, is skipped when already present, and is
recorded in build/situas/MANIFEST.json with its URL, checksum and record count.
As with the editions, the checksum is not hygiene: the archive's claim is that
an attribute came from a named published report, and a claim is only falsifiable
if the file can be fetched and compared.

**The endpoint answers intermittently, and must be asked sparingly.**
`situas-servizi.istat.it` returns 503 to some client addresses for stretches of
minutes at a time, then serves the same request normally — observed from a VPN
address in August 2026, where a plain request failed and the same request with
backoff succeeded. Whatever the cause, the response to it is not to push harder:
an IP blocked outright would cost this project its only source for the identity
layer. So the fetcher is deliberately slow and polite —

- **one request at a time**, never in parallel;
- **a pause between requests** (`SITUAS_PAUSE` seconds, default 5);
- **few retries, long waits** rather than many rapid ones;
- **cache first**: a re-run must not re-ask for the ~300 MB of rosters it
  already holds;
- **`--limit`** to spread the first full fetch across several sessions.

The whole calendar is 99 rosters. At this pace that is roughly ten minutes of
wall clock, once, and never again.
"""

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from scripts.situas import (
    CACHE_NAMES,
    CATALOGUE_BODY,
    CATALOGUE_URL,
    parse_payload,
    roster_url,
    variations_url,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "situas"
ROSTERS = OUT / "rosters"
MANIFEST = OUT / "MANIFEST.json"

# Retry budget for the intermittent 503s: few attempts, long waits. A tight
# retry loop is indistinguishable from hammering the service, which is the one
# outcome to avoid.
RETRIES = "4"
RETRY_DELAY = "20"

# Seconds between two successful requests. Overridable for a one-off, but the
# default is the polite one.
PAUSE = float(os.environ.get("SITUAS_PAUSE", "5"))


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {}


def _save_manifest(manifest):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps({k: manifest[k] for k in sorted(manifest)},
                   indent=2, ensure_ascii=False)
    )


def download(url, dest, force=False):
    """Fetch one report to `dest`, returning the number of records.

    The payload is parsed before the file is accepted. SITUAS answers an
    overloaded backend with an HTML error page and HTTP 200 often enough that
    trusting the status code alone leaves truncated JSON in the cache.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        return len(parse_payload(dest.read_text()))

    tmp = dest.with_suffix(dest.suffix + ".part")
    proc = subprocess.run(
        ["curl", "-sS", "-L",
         "--retry", RETRIES,
         "--retry-delay", RETRY_DELAY,
         "--retry-all-errors",
         "-H", "Accept: application/json",
         "-w", "%{http_code}",
         "-o", str(tmp), url],
        capture_output=True, text=True,
    )
    status = proc.stdout.strip()
    if proc.returncode != 0 or status != "200":
        tmp.unlink(missing_ok=True)
        # 503 here is not an outage: the service refuses some client addresses
        # for stretches at a time. Saying so is the difference between waiting
        # and debugging a script that is working correctly.
        raise RuntimeError(
            f"SITUAS answered {status or 'nothing'} for {url}\n"
            f"  {RETRIES} attempts, {RETRY_DELAY}s apart. A 503 that persists "
            f"means this address is being refused; try from another network "
            f"rather than retrying harder.\n"
            f"  {proc.stderr.strip()}"
        )
    records = parse_payload(tmp.read_text())
    tmp.replace(dest)
    # Only after a real request: a cache hit costs the service nothing and
    # should not be slowed down.
    time.sleep(PAUSE)
    return len(records)


def fetch_catalogue(force=False):
    """Fetch the report catalogue, which lists every dataset and its parameters."""
    dest = OUT / "catalogue.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or force:
        subprocess.run(
            ["curl", "-fsSL",
             "--retry", RETRIES,
             "--retry-delay", RETRY_DELAY,
             "--retry-all-errors",
             "-X", "POST", CATALOGUE_URL,
             "-H", "Content-Type: application/json",
             "-H", "Accept: application/json",
             "-d", json.dumps(CATALOGUE_BODY),
             "-o", str(dest)],
            check=True,
        )
    return dest


def fetch_variations(until, force=False):
    """The four variation reports, over their full coverage."""
    manifest = _load_manifest()
    for pfun, name in sorted(CACHE_NAMES.items()):
        dest = OUT / f"{name}.json"
        url = variations_url(pfun, until=until)
        records = download(url, dest, force=force)
        manifest[dest.name] = {
            "pfun": pfun,
            "url": url,
            "sha256": _sha256(dest),
            "records": records,
            "bytes": dest.stat().st_size,
        }
        print(f"{pfun:>4}  {records:>5} records  {dest.name}")
        _save_manifest(manifest)
    return manifest


def seed_rosters(source, dates=None):
    """Adopt rosters already downloaded elsewhere, to spare the service.

    The ISTAT ingestion in `gst-maps-pipelines` fetches report 61 at 1 January
    of every year from 2000 and keeps the payload as
    `data/bronze/istat/<year>/istat_comuni_<year>.json`. Those are the same
    report at the same dates, so 26 of the calendar's 99 rosters can be adopted
    instead of asked for again.

    Provenance stays explicit rather than being quietly equated: the manifest
    entry keeps the ISTAT URL, so anyone can re-fetch and compare, and records
    `seeded_from` so nobody reads the checksum as one of an ISTAT response. The
    payload is normalised to `{"resultset": [...]}` because that copy holds the
    bare record list.
    """
    source = Path(source).expanduser()
    manifest = _load_manifest()
    adopted = []
    for path in sorted(source.rglob("istat_comuni_*.json")):
        year = path.stem.rsplit("_", 1)[-1]
        iso = f"{year}-01-01"
        if dates is not None and iso not in dates:
            continue
        dest = ROSTERS / f"{iso}.json"
        if dest.exists():
            continue
        records = parse_payload(path.read_text())
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps({"resultset": records}, ensure_ascii=False))
        manifest[f"rosters/{dest.name}"] = {
            "pfun": 61,
            "date": iso,
            "url": roster_url(iso),
            "sha256": _sha256(dest),
            "records": len(records),
            "bytes": dest.stat().st_size,
            "seeded_from": str(path),
        }
        adopted.append(iso)
        print(f"{iso}  {len(records):>5} comuni  seeded from {path.name}")
    _save_manifest(manifest)
    return adopted


def fetch_rosters(dates, force=False, limit=None):
    """Report 61 at each date: the roster the archive's attributes come from.

    `limit` caps how many *missing* rosters this run fetches, so the calendar
    can be filled over several sessions without asking the service for
    everything at once. Cached dates never count against it.
    """
    manifest = _load_manifest()
    fetched = 0
    for at in dates:
        iso = at if isinstance(at, str) else at.isoformat()
        dest = ROSTERS / f"{iso}.json"
        if not dest.exists() or force:
            if limit is not None and fetched >= limit:
                print(f"stopping at {limit} fetched; {iso} and later still missing")
                break
            fetched += 1
        url = roster_url(iso)
        records = download(url, dest, force=force)
        manifest[f"rosters/{dest.name}"] = {
            "pfun": 61,
            "date": iso,
            "url": url,
            "sha256": _sha256(dest),
            "records": records,
            "bytes": dest.stat().st_size,
        }
        print(f"{iso}  {records:>5} comuni  {dest.stat().st_size / 1048576:5.1f} MB")
        _save_manifest(manifest)
    return manifest


def main(argv):
    command = argv[0] if argv else "variations"
    rest = argv[1:]

    if command == "catalogue":
        print(fetch_catalogue(force=True))
        return

    if command == "variations":
        until = date.today()
        if "--until" in rest:
            until = date.fromisoformat(rest[rest.index("--until") + 1])
        fetch_variations(until=until)
        return

    if command in ("rosters", "seed"):
        limit = None
        seed = None
        if "--limit" in rest:
            at = rest.index("--limit")
            limit = int(rest[at + 1])
            rest = rest[:at] + rest[at + 2:]
        if "--seed-from" in rest:
            at = rest.index("--seed-from")
            seed = rest[at + 1]
            rest = rest[:at] + rest[at + 2:]
        dates = rest
        if not dates:
            from scripts.change_dates import change_dates, load_variations

            dates = change_dates(load_variations())
        if seed:
            seed_rosters(seed, dates=set(dates))
        if command == "rosters":
            fetch_rosters(dates, limit=limit)
        return

    raise SystemExit(f"unknown command {command!r}: variations | rosters | catalogue")


if __name__ == "__main__":
    main(sys.argv[1:])
