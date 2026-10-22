#!/usr/bin/env python3
"""Refresh the UNDP and World Bank series for France into sidecar CSVs.

Usage:  python3 scripts/fetch_worldbank.py

  data/social/hdi_from_undp.csv    HDR 2025 complete time series, France
  data/social/gini_from_wb.csv     SI.POV.GINI (World Bank harmonised)

The HDR file is a single vintage covering every year, which is the point: the
HDI is recomputed for the whole back-series at each methodology change, so
mixing years taken from different reports produces a trend that is partly an
artefact of the reports. One file, one vintage.

France's Gini is kept here only as a harmonised cross-check. The curated
series is INSEE's own, because the World Bank's number for France comes from
EU-SILC through its own income definition and lands in a different place —
they are not two readings of one quantity.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "social"
CACHE = ROOT / "cache"

WB = ("https://api.worldbank.org/v2/country/FRA/indicator/{code}"
      "?format=json&per_page=200&date=2005:2026")
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
ISO3 = "FRA"
# hdr.undp.org answers 403 to the default urllib User-Agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}


def wb_series(code: str) -> dict[int, float]:
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"wb_{code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        for attempt in range(4):
            try:
                req = urllib.request.Request(WB.format(code=code),
                                             headers=HEADERS)
                with urllib.request.urlopen(req, timeout=90) as r:
                    payload = json.loads(r.read())
                cache_file.write_text(json.dumps(payload))
                break
            except Exception as e:  # noqa: BLE001
                print(f"  {code} attempt {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        else:
            return {}
    out = {}
    if len(payload) > 1 and isinstance(payload[1], list):
        for row in payload[1]:
            if row.get("value") is not None:
                out[int(row["date"])] = float(row["value"])
    return out


def hdr_hdi() -> dict[int, float]:
    """France's HDI by year, out of the HDR composite-indices file.

    The file is one row per country and one COLUMN per year, with sibling
    columns for the rank and the sex-disaggregated values — so the key has to
    match `hdi_YYYY` exactly. Matching on the prefix pulls in `hdi_rank_2023`
    and `hdi_f_2023` and silently overwrites the value with a rank.
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "hdr25_series.csv"
    if not cache_file.exists():
        try:
            req = urllib.request.Request(HDR, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as r:
                cache_file.write_bytes(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"  HDR fetch failed: {e}", file=sys.stderr)
            return {}
    text = cache_file.read_text(errors="replace")
    out: dict[int, float] = {}
    for row in csv.DictReader(io.StringIO(text)):
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


def write(name: str, header: str, series: dict[int, float], dec: int) -> None:
    if not series:
        print(f"  !! {name}: nothing fetched", file=sys.stderr)
        return
    lines = [header]
    for y in sorted(series):
        if 2005 <= y <= 2026:
            lines.append(f"{y},{series[y]:.{dec}f}")
    (DATA / name).write_text("\n".join(lines) + "\n")
    print(f"  -> data/social/{name}")


def main() -> None:
    print("Fetching UNDP / World Bank series for France...")
    write("hdi_from_undp.csv", "year,undp", hdr_hdi(), 3)
    write("gini_from_wb.csv", "year,wb", wb_series("SI.POV.GINI"), 1)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
