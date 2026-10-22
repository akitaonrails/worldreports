#!/usr/bin/env python3
"""Build the committed CSVs from the fetched sidecars.

The committed CSVs under `data/` are this atlas's source of truth: the charts
and the site are built from them and from nothing else. The fetchers never
write them. Each fetcher writes a SIDECAR instead — `*_from_api.csv`,
`*_from_omb.csv` — so that re-running `make update` against a live API can
never silently change a published chart.

This script is the deliberate step between the two, and it is the only place
a source is chosen. Run it when a sidecar has been inspected and the change
in it is wanted; `make diff` shows what would change before it does.

Most of the work is a copy, because for most series exactly one publisher is
the authority and the sidecar already holds its numbers. The federal budget
is the exception and the reason this file reasons rather than copies:

  OMB's Historical Tables and Treasury's Monthly Treasury Statement both
  publish the federal budget, and they do not agree. For FY2019 and FY2021
  they are within $2bn of each other, but for FY2020 OMB's outlays are
  $6,516.8bn against Treasury's $6,551.9bn — $35bn, half a percent, apart.
  OMB revises history as loan-programme costs are re-estimated under credit
  reform; the Monthly Treasury Statement is the cash position as reported at
  the time. Neither is wrong.

  So the series is taken from ONE publisher per column rather than whichever
  number is larger or later: OMB for FY2006-2025, which is the long
  consistent history and divides by its own fiscal-year GDP, and Treasury
  for FY2026, which OMB's current edition does not carry at all — its
  Tables 1.1 and 1.2 stop at the last actual year. The `source` column
  records which publisher each row came from, so the one seam is in the
  data rather than in a footnote.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# sidecar -> committed file, where exactly one publisher is the authority and
# curation is simply the decision to accept what was fetched.
COPIES = (
    ("macro/gdp_from_api.csv", "macro/gdp.csv"),
    ("macro/cpi_from_api.csv", "macro/cpi.csv"),
    ("macro/unemployment_from_api.csv", "macro/unemployment.csv"),
    ("trade/trade_from_api.csv", "trade/trade.csv"),
    ("fiscal/debt_from_api.csv", "fiscal/debt.csv"),
    ("fiscal/spending_from_omb.csv", "fiscal/spending.csv"),
)

# The year OMB's current edition stops publishing actuals. Beyond it the
# Monthly Treasury Statement is the only source, and it is read from the
# sidecar rather than assumed: a new OMB edition moves this on its own.
BUDGET_COLUMNS = ("receipts_usdbn", "outlays_usdbn", "deficit_usdbn",
                  "receipts_pct_gdp", "outlays_pct_gdp", "deficit_pct_gdp",
                  "gdp_usdbn", "gdp_quarters")


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def write(path: Path, header: list[str], rows: list[list], dry: bool) -> bool:
    """Returns True when the file would change. Nothing is written on a dry
    run, so `make diff` can be read before `make curate` is trusted."""
    lines = [header] + rows
    new = "".join(",".join("" if c is None else str(c) for c in r) + "\n"
                  for r in lines)
    old = path.read_text() if path.exists() else ""
    if new == old:
        print(f"  = {path.relative_to(ROOT)}")
        return False
    verb = "would write" if dry else "wrote"
    n = sum(1 for a, b in zip(old.splitlines(), new.splitlines()) if a != b)
    extra = abs(len(new.splitlines()) - len(old.splitlines()))
    print(f"  {'~' if old else '+'} {path.relative_to(ROOT)} — {verb}, "
          f"{n + extra} line(s) differ")
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new)
    return True


def one(text: str) -> str:
    """A ratio to one decimal place, or empty."""
    try:
        return f"{float(text):.1f}"
    except (TypeError, ValueError):
        return ""


def budget(dry: bool) -> bool:
    """One row per fiscal year, from one publisher per row."""
    omb = {r["fiscal_year"]: r for r in read(DATA / "fiscal" / "budget_from_omb.csv")}
    mts = {r["fiscal_year"]: r for r in read(DATA / "fiscal" / "budget_from_api.csv")}

    # OMB rows that carry no receipts are the years its edition does not
    # reach; they are not years without a budget.
    omb_actual = {y for y, r in omb.items()
                  if r.get("receipts_usdbn") and r.get("estimate") == "0"}
    rows = []
    for year in sorted(set(omb) | set(mts)):
        if year in omb_actual:
            r, source = omb[year], "omb"
            cells = [r["receipts_usdbn"], r["outlays_usdbn"], r["deficit_usdbn"],
                     r["receipts_pct_gdp"], r["outlays_pct_gdp"],
                     r["deficit_pct_gdp"], r["gdp_usdbn"], 4]
        elif year in mts and mts[year].get("receipts"):
            r, source = mts[year], "treasury"
            # OMB prints a ratio to one decimal and Treasury's is computed,
            # so it is rounded to match: a column that switches from 17.3 to
            # 16.90 mid-series reads as a change in precision of measurement
            # when it is only a change of arithmetic.
            cells = [r["receipts"], r["outlays"], r["deficit"],
                     one(r["receipts_pct_gdp"]), one(r["outlays_pct_gdp"]),
                     one(r["deficit_pct_gdp"]), r["fy_gdp"],
                     r.get("gdp_quarters", "")]
        else:
            # A year both publishers are silent on stays empty. The Monthly
            # Treasury Statement only reaches back to FY2014, so without OMB
            # there is nothing here, and a blank row says so.
            cells = [""] * len(BUDGET_COLUMNS)
            source = ""
        rows.append([year] + cells + [source])
    return write(DATA / "fiscal" / "budget.csv",
                 ["fiscal_year", *BUDGET_COLUMNS, "source"], rows, dry)


def main() -> None:
    dry = "--check" in sys.argv or "--diff" in sys.argv
    print("Curating committed CSVs from sidecars"
          + (" (dry run)" if dry else "") + "...")
    changed = False
    for src, dst in COPIES:
        rows = [r for r in csv.reader((DATA / src).open(newline=""))]
        if not rows:
            print(f"  !! {src} is empty — {dst} left alone")
            continue
        changed |= write(DATA / dst, rows[0], rows[1:], dry)
    changed |= budget(dry)
    if dry and changed:
        print("\nSidecars differ from the committed CSVs. Review the numbers, "
              "then run `make curate` to accept them.")
        sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()
