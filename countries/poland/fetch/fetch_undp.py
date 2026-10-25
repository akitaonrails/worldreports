#!/usr/bin/env python3
"""Refresh Poland's Human Development Index from UNDP.

Usage:  make C=poland fetch   (or: python3 -I fetch/fetch_undp.py)

UNDP publishes the HDI as one complete time series per report — the whole
back-history is recomputed with each edition, so mixing two report years
produces steps that are methodology rather than development. This fetcher
therefore takes ONE vintage (the current composite-indices file) and
stages it whole; `DATA_NOTES.md` records which report it came from.

The file is the HDR's "composite indices" CSV: one row per country, one
column per year (hdi_1990 ... hdi_2023). Poland's row is selected by ISO3.

Output: world/hdi_from_undp.csv (review sidecar only).
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, FetchError, assert_close, get, write_csv  # noqa: E402

URL = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
ISO3 = "POL"
Y0, Y1 = 2006, 2026


def main() -> None:
    print("Fetching UNDP HDI for Poland...")
    body = get(URL, suffix=".csv", timeout=240)
    text = body.decode("utf-8-sig", "replace")
    if "," not in text.splitlines()[0]:
        raise FetchError("UNDP HDI: not a CSV (HTML error page?)")
    reader = csv.DictReader(io.StringIO(text))
    if "iso3" not in (reader.fieldnames or []):
        raise FetchError(f"UNDP HDI: unexpected columns "
                         f"{(reader.fieldnames or [])[:6]}")
    row = next((r for r in reader if r.get("iso3") == ISO3), None)
    if row is None:
        raise FetchError(f"UNDP HDI: no {ISO3} row")
    series = {}
    for key, value in row.items():
        if not key or not key.startswith("hdi_") or not value:
            continue
        year = key.split("_", 1)[1]
        if not year.isdigit():
            continue
        try:
            series[int(year)] = float(value)
        except ValueError:
            continue
    if not series:
        raise FetchError("UNDP HDI: no hdi_ columns populated")
    # Known value: the HDR 2025 edition has Poland at 0.906 for 2023.
    assert_close(series.get(max(series)), 0.906, 0.02, "HDI latest year")

    header = ["year", "hdi"]
    rows = [[y, round(series[y], 4) if y in series else None]
            for y in range(Y0, Y1 + 1)]
    path = write_csv("world/hdi_from_undp.csv", header, rows, comment=f"""
UNDP Human Development Report, composite-indices complete time series,
edition 2025 (one vintage throughout; the HDR recomputes the whole
back-series each year, so two editions must never be spliced). Latest
observation in this file: {max(series)} = {series[max(series)]:.3f}. The
HDR runs two years behind the plate window, so the last years are blank.
""")
    print(f"  -> {path.relative_to(DATA)}  (to {max(series)})")
    print("Done. Diff the *_from_undp.csv sidecar before adopting.")


if __name__ == "__main__":
    main()
