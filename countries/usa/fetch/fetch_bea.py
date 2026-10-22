#!/usr/bin/env python3
"""Fetch the national accounts from the Bureau of Economic Analysis.

BEA publishes the NIPA tables as plain workbooks at a stable URL, with no API
key, which is why this reads them rather than the keyed JSON API: the file
states its own vintage on every sheet ("Data published September 30, 2026"),
so a committed CSV can name the release it came from.

Sheets used (all official BEA NIPA tables):
  T10105  Table 1.1.5  GDP, current dollars (annual + quarterly)
  T10101  Table 1.1.1  real GDP, % change from preceding period
  T10106  Table 1.1.6  real GDP, chained 2017 dollars
  T70100  Table 7.1    GDP per capita (current $) and population
  T40100  Table 4.1    exports and imports of goods and services
  T30200  Table 3.2    federal government current receipts and expenditures

Annual tables stop at the last complete year; 2026 is built from the
published quarters instead, and is marked partial everywhere it is used.

Outputs:
  data/macro/gdp_from_api.csv       year,nominal_usdbn,real_growth,
                                    gdp_per_capita_usd,population_mn
  data/trade/trade_from_api.csv     year,exports,imports,balance,
                                    goods_balance,services_balance
  data/fiscal/federal_from_api.csv  year,receipts_pct_gdp,outlays_pct_gdp
                                    (NIPA basis cross-check only)
"""
from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "bea"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

BASE = "https://apps.bea.gov/national/Release/XLS/Survey/Section{n}All_xls.xlsx"
SECTIONS = (1, 3, 4, 7)

YEAR_FROM, YEAR_TO = 2006, 2026


# ------------------------------------------------------------------ download
def workbook(section: int):
    """The section workbook, cached. BEA revises these monthly, so a cached
    copy is also what makes a re-run reproduce the same numbers."""
    path = CACHE / f"Section{section}All.xlsx"
    if not path.exists():
        url = BASE.format(n=section)
        print(f"  downloading {url}")
        r = requests.get(url, timeout=180)
        r.raise_for_status()
        path.write_bytes(r.content)
    return openpyxl.load_workbook(path, read_only=True, data_only=True)


# --------------------------------------------------------------------- parse
def sheet_series(wb, sheet: str) -> tuple[dict[str, dict[str, float]], str]:
    """{BEA series code: {period: value}} for one NIPA sheet, plus the
    vintage line the sheet carries.

    A NIPA sheet is a header block, then a row of periods, then one row per
    line: line number, label, series code, then the values. The period row is
    found by looking for the one whose first cell is 'Line', rather than by a
    fixed offset — BEA's header block is not the same height on every sheet.
    """
    ws = wb[sheet]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    vintage = next((str(r[0]) for r in rows
                    if r and str(r[0] or "").startswith("Data published")), "")
    head = next(i for i, r in enumerate(rows)
                if r and str(r[0] or "").strip() == "Line")
    periods = [str(p).strip() if p is not None else "" for p in rows[head]]

    out: dict[str, dict[str, float]] = {}
    for row in rows[head + 1:]:
        if len(row) < 4:
            continue
        code = str(row[2]).strip() if row[2] is not None else ""
        if not code:
            continue
        vals = {}
        for i in range(3, min(len(row), len(periods))):
            period, value = periods[i], row[i]
            if not period or not isinstance(value, (int, float)):
                continue
            vals[period] = float(value)
        if vals:
            out[code] = vals
    return out, vintage


def annual(series: dict[str, dict[str, float]], code: str) -> dict[int, float]:
    """Values keyed by calendar year, from an annual sheet."""
    got = series.get(code, {})
    out = {}
    for period, value in got.items():
        if period.isdigit():
            out[int(period)] = value
    return out


def from_quarters(series: dict[str, dict[str, float]], code: str,
                  year: int) -> tuple[float | None, int]:
    """One year's value from the quarterly sheet, and how many quarters it is
    built from. Current-dollar NIPA quarterlies are seasonally adjusted
    ANNUAL RATES, so the annual figure is their mean, not their sum — summing
    them overstates the year fourfold. An incomplete year averages the
    quarters that exist, which is the right partial reading and is labelled
    as one wherever it is drawn.
    """
    got = series.get(code, {})
    qs = [v for p, v in got.items() if p.startswith(f"{year}Q")]
    if not qs:
        return None, 0
    return sum(qs) / len(qs), len(qs)


def rows_to_csv(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header] + rows) + "\n")
    print(f"  -> {path.relative_to(ROOT)}")


def fmt(v: float | None, dec: int = 2) -> str:
    return "" if v is None else f"{v:.{dec}f}"


# ---------------------------------------------------------------------- main
def main() -> None:
    print("Fetching BEA NIPA tables...")
    wb1, wb3, wb4, wb7 = (workbook(n) for n in SECTIONS)

    gdp_a, vintage = sheet_series(wb1, "T10105-A")
    gdp_q, _ = sheet_series(wb1, "T10105-Q")
    growth_a, _ = sheet_series(wb1, "T10101-A")
    real_a, _ = sheet_series(wb1, "T10106-A")
    real_q, _ = sheet_series(wb1, "T10106-Q")
    cap_a, _ = sheet_series(wb7, "T70100-A")
    fx_a, _ = sheet_series(wb4, "T40100-A")
    fx_q, _ = sheet_series(wb4, "T40100-Q")
    gov_a, _ = sheet_series(wb3, "T30200-A")
    print(f"  vintage: {vintage}")

    # ---- GDP -------------------------------------------------------------
    # A191RC nominal GDP, A191RL real GDP % change, A939RC GDP per capita,
    # B230RC population (midperiod, thousands)
    nominal = annual(gdp_a, "A191RC")
    growth = annual(growth_a, "A191RL")
    percap = annual(cap_a, "A939RC")
    pop = annual(cap_a, "B230RC")
    real = annual(real_a, "A191RX")

    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        nom = nominal.get(y)
        g = growth.get(y)
        pc = percap.get(y)
        pp = pop.get(y)
        if nom is None:
            nom, nq = from_quarters(gdp_q, "A191RC", y)
            if nq:
                print(f"  {y}: nominal GDP from {nq} quarter(s) (partial)")
        if g is None:
            # a partial year has no annual volume change; the best honest
            # reading is the published quarters against the same quarters a
            # year earlier, which is what BEA's own "year to date" compares
            cur, nq = from_quarters(real_q, "A191RX", y)
            prev_same = [v for p, v in real_q.get("A191RX", {}).items()
                         if p.startswith(f"{y - 1}Q")
                         and int(p[-1]) <= nq]
            if cur is not None and len(prev_same) == nq and nq:
                g = (cur / (sum(prev_same) / nq) - 1) * 100
                print(f"  {y}: real growth from {nq} quarter(s) vs. same "
                      f"quarters {y - 1} (partial)")
        rows.append(
            f"{y},{fmt(None if nom is None else nom / 1000, 1)},{fmt(g, 1)},"
            f"{fmt(pc, 0)},{fmt(None if pp is None else pp / 1000, 3)}")
    rows_to_csv(DATA / "macro" / "gdp_from_api.csv",
                "year,nominal_usdbn,real_growth,gdp_per_capita_usd,population_mn",
                rows)

    # ---- trade -----------------------------------------------------------
    # B020RC exports, B021RC imports, A253RC/A255RC goods,
    # A646RC/B656RC services — all NIPA basis, US$ millions
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        def get(code: str) -> float | None:
            v = annual(fx_a, code).get(y)
            if v is None:
                v, _ = from_quarters(fx_q, code, y)
            return v

        exp, imp = get("B020RC"), get("B021RC")
        gx, gm = get("A253RC"), get("A255RC")
        sx, sm = get("A646RC"), get("B656RC")
        bal = None if exp is None or imp is None else exp - imp
        gbal = None if gx is None or gm is None else gx - gm
        sbal = None if sx is None or sm is None else sx - sm
        rows.append(
            f"{y},{fmt(None if exp is None else exp / 1000, 1)},"
            f"{fmt(None if imp is None else imp / 1000, 1)},"
            f"{fmt(None if bal is None else bal / 1000, 1)},"
            f"{fmt(None if gbal is None else gbal / 1000, 1)},"
            f"{fmt(None if sbal is None else sbal / 1000, 1)}")
    rows_to_csv(DATA / "trade" / "trade_from_api.csv",
                "year,exports,imports,balance,goods_balance,services_balance",
                rows)

    # ---- federal receipts and expenditures, NIPA basis -------------------
    # W005RC current receipts, W013RC current expenditures. These are the
    # national-accounts measure, which is NOT the budget measure Treasury
    # publishes: it is calendar-year and accrual, where the budget is fiscal
    # year and cash. Kept as a cross-check, not as the headline, and no
    # plate draws it.
    #
    # W005RC, not W006RC. W006RC is "Current tax receipts", a SUBSET that
    # leaves out contributions for government social insurance — about a
    # third of federal revenue. Used as the total it put FY2006 receipts at
    # 11.1% of GDP against OMB's 17.6%, which is what caught it. W005RC is
    # the line BEA itself labels "Current receipts" and lands at 17.4%,
    # the remaining gap being the NIPA basis rather than an error.
    receipts = annual(gov_a, "W005RC")
    outlays = annual(gov_a, "W013RC")
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        nom = nominal.get(y)
        r = receipts.get(y)
        o = outlays.get(y)
        rows.append(
            f"{y},{fmt(None if (r is None or not nom) else r / nom * 100)},"
            f"{fmt(None if (o is None or not nom) else o / nom * 100)}")
    rows_to_csv(DATA / "fiscal" / "federal_from_api.csv",
                "year,receipts_pct_gdp,outlays_pct_gdp", rows)

    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
