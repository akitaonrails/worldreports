#!/usr/bin/env python3
"""Refresh Venezuela's HDI from the UNDP Human Development Report.

Usage:  python3 -I fetch/fetch_undp.py [--offline]

The HDI is recomputed for its whole back-series at every methodology change,
so a trend assembled from successive reports is partly an artefact of the
reports. One file, one vintage (HDR 2025) — never mixed with HDR 2023/24,
whose 1990-2022 values differ from this vintage's in the third decimal.

The report is the reference, not a live API: the file is a single CSV of
about 2 MB held at a stable path. The column names matter — `hdi_YYYY` is the
value, `hdi_rank_YYYY` is a rank, and a prefix match writes a rank where a
value belongs. The file is Latin-1, not UTF-8.

Offline: `--offline` reads the cache only; a cold cache exits 2 and writes
nothing.
"""
from __future__ import annotations

import csv
import io
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
ISO3 = "VEN"
URL = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

YEAR_FROM, YEAR_TO = 2006, 2026

COMMENTS = [
    "UNDP Human Development Report 2025, composite-indices complete time",
    "series (HDR25), Venezuela (VEN). ONE VINTAGE for every year: the HDR",
    "recomputes the whole back-series at each methodology change, so mixing",
    "report years would put a methodology step into a development trend.",
    "Covers 2006-2023; 2024 and 2025 are not yet published, and the holes",
    "stay holes. 2006 = 0.736, peak 2013 = 0.773, 2023 = 0.709.",
]


def fetch(offline: bool) -> bytes:
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "hdr25_composite_indices.csv"
    if cache_file.exists():
        return cache_file.read_bytes()
    if offline:
        print("  !! HDR: offline and no cache", file=sys.stderr)
        raise SystemExit(2)
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = r.read()
        ctype = r.headers.get("Content-Type", "")
    if "csv" not in ctype.lower():
        raise SystemExit(f"HDR: content-type {ctype!r} is not CSV")
    text = raw.decode("latin-1")  # validated before the bytes are cached
    if "iso3" not in text.split("\n", 1)[0]:
        raise SystemExit("HDR: payload does not start with the expected header")
    cache_file.write_bytes(raw)
    return raw


def series(raw: bytes) -> dict[int, float]:
    out: dict[int, float] = {}
    for row in csv.DictReader(io.StringIO(raw.decode("latin-1"))):
        if (row.get("iso3") or row.get("ISO3")) != ISO3:
            continue
        for key, value in row.items():
            if not key or value in (None, "", ".."):
                continue
            name = key.lower()
            year = name.rsplit("_", 1)[-1]
            if year.isdigit() and name == f"hdi_{year}":
                out[int(year)] = float(value)
        break
    return out


def write(values: dict[int, float]) -> None:
    if not values:
        raise SystemExit("HDR: no Venezuela row found")
    path = ROOT / "data" / "world" / "hdi_from_undp.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in COMMENTS]
    lines.append("year,hdi")
    rows = 0
    for y in sorted(values):
        if YEAR_FROM <= y <= YEAR_TO:
            lines.append(f"{y},{values[y]:.3f}")
            rows += 1
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/world/hdi_from_undp.csv  {rows} rows")


def verify(values: dict[int, float]) -> None:
    assert abs(values[2006] - 0.736) < 0.001, f"HDI 2006: {values.get(2006)}"
    assert abs(values[2013] - 0.773) < 0.001, f"HDI 2013: {values.get(2013)}"
    assert abs(values[2023] - 0.709) < 0.001, f"HDI 2023: {values.get(2023)}"
    assert max(values) == 2023, \
        f"HDI row set changed: {sorted(values)[-3:]}"


def main() -> None:
    offline = "--offline" in sys.argv[1:]
    print("UNDP HDI for Venezuela" + (" (offline)" if offline else ""))
    values = series(fetch(offline))
    write(values)
    verify(values)
    print("All discovery anchors verified. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
