#!/usr/bin/env python3
"""Refresh Venezuela's displacement figures from UNHCR's population API.

Usage:  python3 -I fetch/fetch_unhcr.py [--offline]

What this measures, and what it does not:

  * It is the number of Venezuelans **registered as refugees or asylum
    seekers by the countries they are in**, attributed to Venezuela as the
    country of origin (`coo=VEN`). That is an operational count of people
    with a UNHCR-visible status, not a census and not a count of emigrants.
  * It is **not** the R4V platform's "Venezuelans abroad" figure (about 7.7
    million), which is a host-government and agency operational estimate of
    all Venezuelans outside the country including irregular migrants. That
    figure is a different definition by a different publisher and is not
    staged here; the lens says which one it draws.
  * It is an origin-country total, so it is not a per-1,000 rate of
    Venezuela's population and cannot enter the canonical migration slots.
    It is the lens: the flow of people out, which no Venezuelan publisher
    measures.

Offline: `--offline` reads the cache only; a cold cache exits 2 and writes
nothing.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
URL = ("https://api.unhcr.org/population/v1/population/"
       "?limit=200&yearFrom=2006&yearTo=2026&coo=VEN")
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0",
           "Accept": "application/json"}

YEAR_FROM, YEAR_TO = 2006, 2025

COMMENTS = [
    "UNHCR Refugee Data Finder, population API, country of origin VEN",
    "(coo=VEN), years 2006-2025, pulled 2026-10-25.",
    "refugees + asylum_seekers = people with a UNHCR-visible protection",
    "status in the countries they are in, attributed to Venezuela as origin.",
    "OPERATIONAL ESTIMATE, NOT A CENSUS: registration coverage differs by",
    "host country and the asylum backlog lags the movement of people.",
    "NOT the R4V 'Venezuelans abroad' figure (~7.7mn), which counts all",
    "Venezuelans outside the country including irregular migrants on host-",
    "government estimates: different publisher, different definition.",
    "Origin totals, so this is a lens, never a canonical per-1,000 slot.",
]


def fetch(offline: bool) -> dict:
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "unhcr_ven_origin.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    if offline:
        print("  !! UNHCR: offline and no cache", file=sys.stderr)
        raise SystemExit(2)
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read()
                ctype = r.headers.get("Content-Type", "")
            if "json" not in ctype:
                raise ValueError(f"content-type {ctype!r} is not JSON")
            payload = json.loads(body)
            items = payload.get("items")
            if not isinstance(items, list) or not items:
                raise ValueError("no items in the population payload")
            cache_file.write_text(json.dumps(payload))
            return payload
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise SystemExit(f"UNHCR: {last}")


def rows(payload: dict) -> dict[int, tuple[int, int]]:
    out: dict[int, tuple[int, int]] = {}
    for it in payload["items"]:
        if it.get("coo") != "VEN":
            continue
        year = int(it["year"])
        refugees = int(it.get("refugees") or 0)
        seekers = int(it.get("asylum_seekers") or 0)
        if year in out:
            raise SystemExit(f"UNHCR: duplicate year {year}")
        out[year] = (refugees, seekers)
    return out


def write(data: dict[int, tuple[int, int]]) -> None:
    if not data:
        raise SystemExit("UNHCR: no Venezuela rows")
    path = ROOT / "data" / "migration" / "displacement_from_unhcr.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in COMMENTS]
    lines.append("year,refugees,asylum_seekers,refugees_and_asylum_seekers")
    n = 0
    for year in sorted(data):
        if not YEAR_FROM <= year <= YEAR_TO:
            continue
        refugees, seekers = data[year]
        lines.append(f"{year},{refugees},{seekers},{refugees + seekers}")
        n += 1
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/migration/displacement_from_unhcr.csv  {n} rows")


def verify(data: dict[int, tuple[int, int]]) -> None:
    assert data[2015] == (7455, 15087), f"2015: {data.get(2015)}"
    assert data[2018][1] == 464223, f"asylum seekers 2018: {data.get(2018)}"
    assert data[2023][1] == 1200130, f"asylum seekers 2023: {data.get(2023)}"
    assert sum(data[2025]) == 417010 + 1181156, f"2025: {data.get(2025)}"


def main() -> None:
    offline = "--offline" in sys.argv[1:]
    print("UNHCR displacement for Venezuela" + (" (offline)" if offline else ""))
    payload = fetch(offline)
    data = rows(payload)
    write(data)
    verify(data)
    print("All discovery anchors verified. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
