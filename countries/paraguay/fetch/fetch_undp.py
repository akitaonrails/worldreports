#!/usr/bin/env python3
"""Refresh Paraguay's HDI from the UNDP Human Development Report.

Usage:  make C=paraguay fetch   (or: python3 -I fetch/fetch_undp.py)

One file, one vintage: the HDR 2025 composite-indices workbook carries
the HDI for every year in a single table, so the whole back-series is
recomputed under one methodology. Assembling a trend from successive
reports is the classic development-index defect — each report restates
history, so a mixed vintage produces steps that are methodology rather
than development. This fetcher refuses to mix.

hdr.undp.org answers 403 to the default urllib User-Agent; a browser UA
gets 200. The file is Latin-1, not UTF-8.
"""
from __future__ import annotations

import csv
import io
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
ISO3 = "PRY"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
YEAR_FROM, YEAR_TO = 2006, 2026

COMMENTS = [
    "UNDP Human Development Report 2025, composite indices, one vintage:",
    "the HDR recomputes the whole back-series at each methodology change,",
    "so a trend stitched from successive reports would partly measure the",
    "reports. Covers 1990-2023; later years are not yet published.",
]


def fetch() -> bytes:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / "hdr25_series.csv"
    if path.exists():
        return path.read_bytes()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(HDR, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=240) as r:
                raw = r.read()
            raw.decode("latin-1")  # validated before the bytes are cached
            if b"iso3" not in raw[:2000].lower():
                raise ValueError("not the composite-indices file")
            path.write_bytes(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  hdr attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise SystemExit(f"cannot fetch {HDR}: {last}")


def hdi() -> dict[int, float]:
    """Paraguay's HDI by year, out of the HDR composite-indices file.

    One row per country and one COLUMN per year, with sibling columns
    for the rank and the sex-disaggregated values — so the key has to
    match `hdi_YYYY` exactly. A prefix match pulls in `hdi_rank_2023`
    and writes a rank where a value belongs.
    """
    out: dict[int, float] = {}
    for row in csv.DictReader(io.StringIO(fetch().decode("latin-1"))):
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


def main() -> None:
    print("UNDP HDI for Paraguay")
    series = hdi()
    if not series:
        raise SystemExit("no PRY row in the HDR file")
    assert abs(series[2006] - 0.684) < 0.002, f"HDI 2006: {series.get(2006)}"
    assert abs(series[2023] - 0.756) < 0.002, f"HDI 2023: {series.get(2023)}"
    path = ROOT / "data" / "world" / "hdi_from_undp.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in COMMENTS] + ["year,hdi"]
    for y in sorted(series):
        if YEAR_FROM <= y <= YEAR_TO:
            lines.append(f"{y},{series[y]:.3f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/world/hdi_from_undp.csv  "
          f"{sum(1 for y in series if YEAR_FROM <= y <= YEAR_TO)} rows")
    print("Done. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
