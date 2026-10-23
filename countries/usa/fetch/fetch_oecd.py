#!/usr/bin/env python3
"""Fetch general-government interest payable from the OECD.

Usage:  python3 countries/usa/fetch/fetch_oecd.py

The spine's fiscal slot 4 is interest PAID by general government, % of GDP:
Eurostat's D41PAY, or its equivalent elsewhere. For the United States the
equivalent is SNA transaction D41, interest, payable by sector S13, from the
OECD's annual national accounts Table 12 (government deficit/surplus,
revenue, expenditure and main aggregates), dataflow
OECD.SDD.NAD,DSD_NASEC10@DF_TABLE12_EXP. It is in US$ millions at current
prices; the plate divides it by BEA's nominal GDP.

The IMF's DataMapper carries no gross interest series, and its primary and
overall balances give net interest only, which is a different measure.

Cross-check: BEA NIPA table 3.1, line 27, A180RC, government interest
payments, read from the cached Section 3 workbook that fetch_bea.py uses.
BEA's own footnote says that line includes interest accrued on the
actuarial liabilities of government employees' defined-benefit pension
plans; the OECD figure is within a few per cent of it, so it carries the
same convention, which DATA_NOTES.md records.

Output (a sidecar; fetch/curate.py accepts it into fiscal/interest.csv):
  data/fiscal/interest_from_oecd.csv  year,interest_paid_usdmn
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "oecd"
DATA = ROOT / "data"
YEAR_FROM, YEAR_TO = 2006, 2026

URL = ("https://sdmx.oecd.org/public/rest/data/"
       "OECD.SDD.NAD,DSD_NASEC10@DF_TABLE12_EXP,/A.USA.S13..D.D41.........."
       "?startPeriod=2005&format=csvfilewithlabels")
# US$ millions, read off the OECD Data Explorer on 2026-10-22.
SPOT = {2024: 1_384_602.216}


def fetch() -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "table12_d41.csv"
    if not path.exists():
        r = requests.get(URL, timeout=180)
        r.raise_for_status()
        if not r.text.startswith("STRUCTURE"):
            raise ValueError(f"not an SDMX csv: {r.text[:80]!r}")
        path.write_text(r.text)
    return path.read_text()


def bea_interest() -> dict[int, float]:
    """A180RC from the cached NIPA Section 3 workbook, if it is there."""
    path = ROOT / "cache" / "bea" / "Section3All.xlsx"
    if not path.exists():
        return {}
    sys.path.insert(0, str(Path(__file__).parent))
    import fetch_bea
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    series, _ = fetch_bea.sheet_series(wb, "T30100-A")
    return fetch_bea.annual(series, "A180RC")


def main() -> int:
    print("Fetching OECD general-government interest payable...")
    out: dict[int, float] = {}
    for r in csv.DictReader(io.StringIO(fetch())):
        if (r["REF_AREA"], r["SECTOR"], r["TRANSACTION"], r["UNIT_MEASURE"],
                r["PRICE_BASE"]) != ("USA", "S13", "D41", "XDC", "V"):
            continue
        out[int(r["TIME_PERIOD"])] = float(r["OBS_VALUE"])
    for y, want in SPOT.items():
        if abs(out.get(y, 0) - want) > 0.5:
            print(f"  !! {y}: {out.get(y)} against {want}; nothing written")
            return 1
    bea = bea_interest()
    for y in sorted(set(out) & set(bea)):
        gap = out[y] / bea[y] - 1
        flag = "" if abs(gap) < 0.05 else "  <-- more than 5% apart"
        print(f"  {y}: OECD {out[y]:,.0f} vs BEA A180RC {bea[y]:,.0f} "
              f"({gap * 100:+.1f}%){flag}")
    dest = DATA / "fiscal" / "interest_from_oecd.csv"
    with dest.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "interest_paid_usdmn"])
        for y in range(YEAR_FROM, YEAR_TO + 1):
            w.writerow([y, f"{out[y]:.1f}" if y in out else ""])
    print(f"  -> {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
