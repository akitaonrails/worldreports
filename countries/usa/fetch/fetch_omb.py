#!/usr/bin/env python3
"""Fetch the budget's long history from the OMB Historical Tables.

These are the canonical federal budget series — the ones every US analyst
quotes — published by the Office of Management and Budget with the
President's Budget each spring. Treasury's Monthly Treasury Statement API
only reaches back to FY2014, so the earlier years come from here.

Tables used (FY2027 edition, published April 2026):
  hist01z2  Table 1.2  receipts, outlays and the deficit as % of GDP
  hist01z1  Table 1.1  the same in dollars
  hist03z2  Table 3.2  outlays by function and subfunction, in dollars
  hist08z1  Table 8.1  outlays for mandatory and related programs

Everything is on a FISCAL year ending 30 September, and OMB divides by its
own fiscal-year GDP, which is a February vintage and so differs by a few
tenths of a percent from one computed off BEA's latest quarterly accounts.
The published ratio is kept rather than recomputed: it is the number in
circulation, and mixing the two would put a seam in the middle of the series.

A function total for the current year is an ESTIMATE in this edition — OMB
labels the column "2026 estimate" — and is written to a separate column
rather than mixed in with the actuals.

Outputs:
  data/fiscal/budget_from_omb.csv    fiscal_year,receipts_pct_gdp,
                                     outlays_pct_gdp,deficit_pct_gdp,gdp,estimate
  data/fiscal/spending_from_omb.csv  fiscal_year,<function>_usdbn...,estimate
"""
from __future__ import annotations

from pathlib import Path

import openpyxl
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "omb"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

EDITION = "fy2027"
BASE = "https://www.whitehouse.gov/wp-content/uploads/2026/04/hist{t}_{ed}.xlsx"
TABLES = ("01z1", "01z2", "03z2", "08z1")

YEAR_FROM, YEAR_TO = 2006, 2026

# The spending functions the plates draw, by the exact label OMB gives them.
# Medicare and Social Security carry no subfunction total, so their single
# subfunction line is the function; the others have a "Total," row.
FUNCTIONS = (
    ("social_security", "651 Social security"),
    ("medicare", "571 Medicare"),
    ("health", "Total, Health"),
    ("defense", "Total, National Defense"),
    ("income_security", "Total, Income Security"),
    ("net_interest", "Total, Net Interest"),
    ("veterans", "Total, Veterans Benefits and Services"),
    ("education", "Total, Education, Training, Employment, and Social Services"),
    ("transportation", "Total, Transportation"),
)
TOTAL_LABEL = "Total outlays"


def table(t: str):
    """One historical table, cached.

    Loaded WITHOUT openpyxl's read_only mode: these files carry no worksheet
    dimension record, and in read_only mode openpyxl believes that and hands
    back a single cell, so the whole table reads as empty without erroring.
    """
    path = CACHE / f"hist{t}.xlsx"
    if not path.exists():
        url = BASE.format(t=t, ed=EDITION)
        print(f"  downloading {url}")
        r = requests.get(url, timeout=180)
        r.raise_for_status()
        path.write_bytes(r.content)
    wb = openpyxl.load_workbook(path, data_only=True)
    return [list(r) for r in wb["Table"].iter_rows(values_only=True)]


def label_of(row: list) -> str:
    return "" if not row or row[0] is None else str(row[0]).strip()


def year_columns(rows: list[list], header: str) -> dict[int, tuple[int, bool]]:
    """{year: (column index, is_estimate)} read off the table's header row.

    OMB writes a projected column as "2026 estimate", so the flag is kept
    and travels with the value instead of being quietly dropped.
    """
    head = next(i for i, r in enumerate(rows) if label_of(r).startswith(header))
    out = {}
    for j, cell in enumerate(rows[head]):
        text = "" if cell is None else str(cell).strip()
        if len(text) >= 4 and text[:4].isdigit():
            out[int(text[:4])] = (j, "estimate" in text.lower())
    return out


def value(rows: list[list], label: str, col: int) -> float | None:
    row = next((r for r in rows if label_of(r) == label), None)
    if row is None or col >= len(row):
        return None
    v = row[col]
    return float(v) if isinstance(v, (int, float)) else None


def write(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header] + rows) + "\n")
    print(f"  -> {path.relative_to(ROOT)}")


def fmt(v: float | None, dec: int = 1) -> str:
    return "" if v is None else f"{v:.{dec}f}"


def main() -> None:
    print(f"Fetching OMB Historical Tables ({EDITION})...")

    # ---- receipts, outlays, deficit as % of GDP --------------------------
    # Table 1.2 is transposed relative to table 3.2: here the years are ROWS
    # and the measures are columns (year, GDP, then total receipts, outlays
    # and balance, then the same split on- and off-budget). An estimate year
    # is written "2026 estimate" in the year cell itself.
    t12 = table("01z2")
    print(f"  [1.2] {label_of(t12[0])[:64]}")
    by_year: dict[int, tuple[list, bool]] = {}
    for r in t12:
        text = label_of(r)
        if len(text) >= 4 and text[:4].isdigit():
            by_year[int(text[:4])] = (r, "estimate" in text.lower())
    # Table 1.1 is the same years in DOLLARS (millions), laid out the same
    # way: year, then total receipts, outlays and the surplus or deficit.
    # It is read rather than deriving dollars from the ratio, so every
    # number in the file is one OMB published. It agrees with Treasury's
    # Monthly Treasury Statement to 0.03% for FY2025 — $5,236.4bn against
    # $5,234.6bn — which is what makes the two joinable at all.
    t11 = table("01z1")
    print(f"  [1.1] {label_of(t11[0])[:64]}")
    dollars: dict[int, list] = {}
    for r in t11:
        text = label_of(r)
        if len(text) == 4 and text.isdigit():
            dollars[int(text)] = r

    rows = []
    keep = (lambda v, d=1: "" if not isinstance(v, (int, float))
            else f"{float(v):.{d}f}")
    for y in range(YEAR_FROM, YEAR_TO + 1):
        d = dollars.get(y)
        # millions in the file, billions in this atlas
        money = ",".join(keep(None if d is None else
                              (d[i] / 1000 if isinstance(d[i], (int, float))
                               else None))
                         for i in (1, 2, 3))
        if y not in by_year:
            rows.append(f"{y},,,,,,{money}")
            continue
        r, est = by_year[y]
        gdp, rcpt, outly, bal = r[1], r[2], r[3], r[4]
        rows.append(f"{y},{keep(rcpt)},{keep(outly)},{keep(bal)},"
                    f"{keep(gdp)},{int(est)},{money}")
    write(DATA / "fiscal" / "budget_from_omb.csv",
          "fiscal_year,receipts_pct_gdp,outlays_pct_gdp,deficit_pct_gdp,"
          "gdp_usdbn,estimate,receipts_usdbn,outlays_usdbn,deficit_usdbn",
          rows)

    # ---- outlays by function, in dollars --------------------------------
    t32 = table("03z2")
    print(f"  [3.2] {label_of(t32[0])[:64]}")
    cols = year_columns(t32, "Function and Subfunction")
    missing = [lab for _, lab in FUNCTIONS
               if not any(label_of(r) == lab for r in t32)]
    if missing:
        raise SystemExit(f"OMB table 3.2 has no row labelled: {missing}")
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        if y not in cols:
            continue
        j, est = cols[y]
        got = [value(t32, lab, j) for _, lab in FUNCTIONS]
        total = value(t32, TOTAL_LABEL, j)
        named = sum(v for v in got if v is not None)
        other = None if total is None else total - named
        cells = ",".join(fmt(None if v is None else v / 1000) for v in got)
        rows.append(f"{y},{cells},{fmt(None if other is None else other / 1000)},"
                    f"{fmt(None if total is None else total / 1000)},{int(est)}")
    names = ",".join(f"{n}_usdbn" for n, _ in FUNCTIONS)
    write(DATA / "fiscal" / "spending_from_omb.csv",
          f"fiscal_year,{names},other_usdbn,total_usdbn,estimate", rows)
    print("Done.")


if __name__ == "__main__":
    main()
