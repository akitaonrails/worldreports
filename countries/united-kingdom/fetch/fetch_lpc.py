#!/usr/bin/env python3
"""Refresh the statutory adult minimum-wage history from the LPC.

The Low Pay Commission's current report workbook includes a ``Historic
rates`` sheet with every effective date and age-specific statutory rate since
1999.  This fetcher uses the highest adult rate in force on each day, computes
its calendar-year average, and converts a full-time monthly equivalent to
current US dollars with the already staged Bank of England annual-average
USD/GBP series.

The monthly convention is explicit rather than publisher-supplied: 40 hours a
week x 52 weeks / 12 months = 173.333 hours.  It is only a common-hours
equivalent for the plate spine; UK law sets an hourly floor and does not define
a statutory monthly wage.

Output is ``data/social/minimum_wage_from_lpc.csv``.  Curated publication
copies remain a separate review step.
"""
from __future__ import annotations

import csv
import re
import urllib.request
from datetime import date
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
DATA = ROOT / "data"
REPORT = "https://www.gov.uk/government/publications/low-pay-commission-report-2025"
ASSET = re.compile(r'https://assets\.publishing\.service\.gov\.uk/[^" ]+/2025_Main_Report_Data\.xlsx')
HOURS_MONTH = 40 * 52 / 12
YEAR_FROM, YEAR_TO = 2006, 2026


def workbook() -> openpyxl.Workbook:
    CACHE.mkdir(exist_ok=True)
    local = CACHE / "lpc_2025_report_data.xlsx"
    if not local.exists():
        with urllib.request.urlopen(REPORT, timeout=90) as r:
            page = r.read().decode("utf-8", errors="replace")
        hit = ASSET.search(page)
        if not hit:
            raise RuntimeError("LPC report data workbook link not found")
        with urllib.request.urlopen(hit.group(0), timeout=180) as r:
            local.write_bytes(r.read())
    return openpyxl.load_workbook(local, read_only=True, data_only=True)


def rates(wb: openpyxl.Workbook) -> list[tuple[date, float]]:
    ws = wb["Historic rates"]
    rows = ws.iter_rows(values_only=True)
    next(rows)  # title
    header = [str(v or "").strip() for v in next(rows)]
    adult = [i for i, name in enumerate(header)
             if re.fullmatch(r"(?:21|22|23|25)\+ rate", name)]
    out = []
    for row in rows:
        effective = row[0]
        if not hasattr(effective, "date"):
            continue
        candidates = [float(row[i]) for i in adult if row[i] is not None]
        if not candidates:
            continue
        out.append((effective.date(), max(candidates)))
    if not out or out[-1] != (date(2026, 4, 1), 12.71):
        raise RuntimeError(f"unexpected latest LPC rate: {out[-1] if out else None}")
    return out


def annual_average(history: list[tuple[date, float]], year: int) -> float:
    start, stop = date(year, 1, 1), date(year + 1, 1, 1)
    total = 0.0
    for i, (effective, rate) in enumerate(history):
        next_effective = history[i + 1][0] if i + 1 < len(history) else stop
        left, right = max(start, effective), min(stop, next_effective)
        if right > left:
            total += (right - left).days * rate
    days = (stop - start).days
    if total == 0:
        raise RuntimeError(f"no LPC rate covers {year}")
    return total / days


def exchange_rates() -> dict[int, float]:
    path = DATA / "markets" / "sterling.csv"
    with path.open(newline="") as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        return {int(r["year"]): float(r["usd_per_gbp_avg"]) for r in rows}


def main() -> None:
    history = rates(workbook())
    fx = exchange_rates()
    lines = [
        "# Low Pay Commission statutory adult rate; calendar-year average,",
        "# weighted by days at each rate. Monthly equivalent assumes 40 hours",
        "# per week x 52 / 12 = 173.333 hours. USD uses the Bank of England",
        "# staged annual-average USD per GBP; 2026 exchange rate is year-to-date.",
        "year,adult_rate_gbp_hour_avg,hours_month,usd_per_gbp_avg,adult_rate_usd_month",
    ]
    for year in range(YEAR_FROM, YEAR_TO + 1):
        hourly = annual_average(history, year)
        monthly = hourly * HOURS_MONTH * fx[year]
        lines.append(f"{year},{hourly:.4f},{HOURS_MONTH:.3f},{fx[year]:.4f},{monthly:.2f}")
    out = DATA / "social" / "minimum_wage_from_lpc.csv"
    out.write_text("\n".join(lines) + "\n")
    print(f"  -> {out.relative_to(ROOT)} ({YEAR_FROM}-{YEAR_TO})")


if __name__ == "__main__":
    main()
