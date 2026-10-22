#!/usr/bin/env python3
"""Refresh World Bank (PIP/WDI) and UNDP HDR series for Argentina.

Usage:  python3 scripts/fetch_worldbank.py

These are the comparable-across-countries vintages, which is the only reason
they are here: INDEC publishes its own Gini and its own poverty rate on its
own definitions, and those are the official ones. The two must never be
spliced — the World Bank harmonises incomes across countries and measures
poverty against a PPP line, while INDEC measures it against the canasta
básica total. They are kept as separate columns and drawn as separate lines.

Writes sidecars only; diff and adopt by hand.
  data/social/gini_from_wb.csv       SI.POV.GINI (harmonised, 0-100)
  data/social/poverty_from_wb.csv    SI.POV.UMIC ($8.30/day) & SI.POV.DDAY ($3.00/day)
  data/social/hdi_from_undp.csv      HDR composite time series (Argentina)
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "social"
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)

UA = {"User-Agent": "argentina-reports/1.0 (+https://github.com/AkitaOnRails)"}
WB = ("https://api.worldbank.org/v2/country/ARG/indicator/{code}"
      "?format=json&per_page=100&date=2005:2026")
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
ISO3 = "ARG"


def get_bytes(url: str, cache_file: Path) -> bytes | None:
    if cache_file.exists():
        return cache_file.read_bytes()
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            cache_file.write_bytes(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            print(f"  {cache_file.name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return None


def get_json(url: str, cache_file: Path):
    raw = get_bytes(url, cache_file)
    return json.loads(raw) if raw is not None else None


def wb_series(code: str) -> dict[int, float]:
    payload = get_json(WB.format(code=urllib.parse.quote(code)),
                       CACHE / f"wb_{code}.json")
    out: dict[int, float] = {}
    if payload and len(payload) > 1 and isinstance(payload[1], list):
        for row in payload[1]:
            if row.get("value") is not None:
                out[int(row["date"])] = float(row["value"])
    print(f"  {code:<14} {len(out):>3} years")
    return out


def write(name: str, header: str, rows: list[str]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text("\n".join([header] + rows) + "\n")
    print(f"  -> data/social/{name}")


def main() -> None:
    print("World Bank — PIP/WDI (Argentina)")
    gini = wb_series("SI.POV.GINI")
    umic = wb_series("SI.POV.UMIC")
    dday = wb_series("SI.POV.DDAY")

    if gini:
        write("gini_from_wb.csv", "year,wb",
              [f"{y},{gini[y]:.1f}" for y in sorted(gini)])
    if umic or dday:
        write("poverty_from_wb.csv", "year,poverty_pct,extreme_pct",
              [f"{y},{umic.get(y, '')},{dday.get(y, '')}"
               for y in sorted(set(umic) | set(dday))])

    print("UNDP — Human Development Report 2025 composite series")
    raw = get_bytes(HDR, CACHE / "hdr25_series.csv")
    if raw is None:
        print("  HDR fetch failed", file=sys.stderr)
        return
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8", errors="replace")))
    hdi: dict[int, float] = {}
    for row in reader:
        if (row.get("iso3") or row.get("ISO3")) != ISO3:
            continue
        for key, val in row.items():
            # exact 'hdi_YYYY' only — hdi_rank_YYYY, hdi_f_YYYY and hdi_m_YYYY
            # all start with the same prefix and are different indicators
            if not key or not key.lower().startswith("hdi_"):
                continue
            year = key.split("_")[-1]
            if (year.isdigit() and key.lower() == f"hdi_{year}"
                    and val not in ("", "..")):
                hdi[int(year)] = float(val)
        break
    if hdi:
        write("hdi_from_undp.csv", "year,undp",
              [f"{y},{hdi[y]:.3f}" for y in sorted(hdi) if 2005 <= y <= 2026])


if __name__ == "__main__":
    main()
