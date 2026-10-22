#!/usr/bin/env python3
"""Fetch road-traffic deaths from NHTSA's Fatality Analysis Reporting System.

Usage:  python3 countries/usa/fetch/fetch_fars.py

FARS is the census of fatal motor-vehicle crashes on US public roads: every
crash in which someone died within 30 days. It is the series NHTSA, the
states and the press all quote, and the one the WHO's road-safety reporting
starts from. The death-certificate series (CDC WONDER "motor vehicle
accidents") counts something else — it includes some non-traffic deaths and
has no 30-day rule — so the two are never joined.

NHTSA's query API (crashviewer.nhtsa.dot.gov/CrashAPI) refuses scripted
requests, so this reads the published national data files instead: one zip
per year under static.nhtsa.gov/nhtsa/downloads/FARS/<year>/National/,
each holding an accident table with one row per fatal crash and its FATALS
count. The year's deaths are the sum of FATALS. The newest file is the
latest one NHTSA has released; the year after it has no file yet and stays
empty.

The zips are 15-35 MB each and are cached under cache/fars, so a refresh
downloads only what is new.

Output (a sidecar; fetch/curate.py accepts it into social/road_deaths.csv):
  data/social/road_deaths_from_fars.csv   year,road_deaths
"""
from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "fars"
DATA = ROOT / "data"

URL = ("https://static.nhtsa.gov/nhtsa/downloads/FARS/{y}/National/"
       "FARS{y}NationalCSV.zip")
YEAR_FROM, YEAR_TO = 2006, 2026
# NHTSA's CDN answers a bare client with "Access Denied"; it serves the
# same file to an ordinary browser user agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) worldreports-fetch"}

# Fatalities as NHTSA publishes them in Traffic Safety Facts for years whose
# final file is long settled. A sum that misses these by more than 0.5%
# means the file layout changed under us, and nothing is written. Recent
# years are not spot-checked against a remembered figure on purpose: NHTSA
# first publishes an Annual Report File and replaces it with a final file
# about a year later (2021 went from 42,939 to 43,230), so the newest
# years legitimately move between refreshes.
SPOT = {2006: 42_708, 2010: 32_999, 2019: 36_355}


def download(year: int) -> Path | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"FARS{year}NationalCSV.zip"
    if path.exists() and path.stat().st_size > 1_000_000:
        return path
    r = requests.get(URL.format(y=year), headers=HEADERS, timeout=600)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    if not r.content.startswith(b"PK"):
        raise ValueError(f"{year}: not a zip ({r.content[:60]!r})")
    path.write_bytes(r.content)
    return path


def fatalities(path: Path) -> int:
    """The sum of FATALS over the accident table, whatever it is called."""
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist()
                 if Path(n).name.lower() == "accident.csv"]
        if len(names) != 1:
            raise ValueError(f"{path.name}: accident table not found in "
                             f"{z.namelist()[:12]}")
        raw = z.read(names[0])
    text = raw.decode("latin-1")
    rows = csv.DictReader(io.StringIO(text))
    field = next((f for f in rows.fieldnames or [] if f.strip().upper()
                  == "FATALS"), None)
    if field is None:
        raise ValueError(f"{path.name}: no FATALS column")
    total = 0
    crashes = 0
    for r in rows:
        total += int(r[field])
        crashes += 1
    if crashes < 25_000:
        raise ValueError(f"{path.name}: only {crashes} crashes")
    return total


def main() -> int:
    print("Fetching NHTSA FARS fatalities...")
    out: dict[int, int] = {}
    for y in range(YEAR_FROM, YEAR_TO + 1):
        p = download(y)
        if p is None:
            print(f"  {y}: no file published yet")
            continue
        out[y] = fatalities(p)
        print(f"  {y}: {out[y]:,}")
    for y, want in SPOT.items():
        got = out.get(y)
        if got is None or abs(got / want - 1) > 0.005:
            print(f"  !! {y}: summed {got} against NHTSA's published "
                  f"{want:,}; nothing written")
            return 1
        print(f"  spot {y}: {got:,} vs published {want:,} ok")
    dest = DATA / "social" / "road_deaths_from_fars.csv"
    with dest.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "road_deaths"])
        for y in range(YEAR_FROM, YEAR_TO + 1):
            w.writerow([y, out.get(y, "")])
    print(f"  -> {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
