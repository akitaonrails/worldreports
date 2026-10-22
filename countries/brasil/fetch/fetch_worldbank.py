#!/usr/bin/env python3
"""Refresh World Bank (PIP/WDI) and UNDP HDR series into sidecar CSVs.

These never overwrite curated files; diff & adopt manually.
  data/social/gini_from_wb.csv       — SI.POV.GINI (harmonized, 0-100)
  data/social/poverty_from_wb.csv    — SI.POV.UMIC ($8.30/day) & SI.POV.DDAY ($3.00/day)
  data/social/hdi_from_undp.csv      — HDR composite time series (Brazil)
"""
import csv
import io
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "social"
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)

WB = "https://api.worldbank.org/v2/country/BRA/indicator/{code}?format=json&per_page=100&date=2005:2026"
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")


def wb_series(code: str) -> dict[int, float]:
    cf = CACHE / f"wb_{code}.json"
    if cf.exists():
        payload = json.loads(cf.read_text())
    else:
        for attempt in range(4):
            try:
                r = requests.get(WB.format(code=code), timeout=60)
                r.raise_for_status()
                payload = r.json()
                cf.write_text(json.dumps(payload))
                break
            except Exception as e:  # noqa: BLE001
                print(f"  {code} attempt {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        else:
            return {}
    out = {}
    if len(payload) > 1 and isinstance(payload[1], list):
        for row in payload[1]:
            if row["value"] is not None:
                out[int(row["date"])] = float(row["value"])
    return out


def main() -> None:
    gini = wb_series("SI.POV.GINI")
    umic = wb_series("SI.POV.UMIC")
    dday = wb_series("SI.POV.DDAY")

    if gini:
        lines = ["year,wb"]
        for y in sorted(gini):
            lines.append(f"{y},{gini[y]:.1f}")
        (DATA / "gini_from_wb.csv").write_text("\n".join(lines) + "\n")
        print("  -> gini_from_wb.csv")
    if umic or dday:
        lines = ["year,poverty_pct,extreme_pct"]
        for y in sorted(set(umic) | set(dday)):
            lines.append(f"{y},{umic.get(y, '')},{dday.get(y, '')}")
        (DATA / "poverty_from_wb.csv").write_text("\n".join(lines) + "\n")
        print("  -> poverty_from_wb.csv")

    # UNDP HDR composite time series (world CSV, ~30k rows; stream-parse)
    cf = CACHE / "hdr25_series.csv"
    if not cf.exists():
        try:
            r = requests.get(HDR, timeout=120)
            r.raise_for_status()
            cf.write_bytes(r.content)
        except Exception as e:  # noqa: BLE001
            print(f"  HDR fetch failed: {e}", file=sys.stderr)
            return
    text = cf.read_text(errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    hdi = {}
    for row in reader:
        if row.get("iso3") == "BRA" or row.get("ISO3") == "BRA":
            for key, val in row.items():
                # exact 'hdi_YYYY' only — skip hdi_rank_YYYY, hdi_f_YYYY, hdi_m_YYYY
                if key and key.lower().startswith("hdi_"):
                    yr = key.split("_")[-1]
                    if yr.isdigit() and key.lower() == f"hdi_{yr}" and val not in ("", ".."):
                        hdi[int(yr)] = float(val)
            break
    if hdi:
        lines = ["year,undp"]
        for y in sorted(hdi):
            if 2005 <= y <= 2026:
                lines.append(f"{y},{hdi[y]:.3f}")
        (DATA / "hdi_from_undp.csv").write_text("\n".join(lines) + "\n")
        print("  -> hdi_from_undp.csv")


if __name__ == "__main__":
    main()
