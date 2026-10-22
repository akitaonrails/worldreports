#!/usr/bin/env python3
"""Fetch household debt, credit availability and borrowing costs.

Two publishers:

  Federal Reserve Bank of New York — the Quarterly Report on Household Debt
  and Credit, built from the FRBNY Consumer Credit Panel (a 5% anonymised
  sample of Equifax credit reports). This is the source for what Americans
  owe and on what: mortgage, home-equity revolving, auto, credit card,
  student loan and other, plus the delinquency rates and the credit card
  limit, which is the closest thing to a published measure of how much credit
  households are actually able to draw on.

  Federal Reserve Board — the G.19 Consumer Credit release's terms of credit,
  for the interest rate actually charged on credit card balances.

Both are quarterly. A year is taken at its FOURTH quarter for a stock (what
is owed at year end) and averaged for a rate, and a year with fewer than four
published quarters is written with the count so nothing can present a partial
year as a complete one.

Note that household debt here is NOT the same universe as the Board's Z.1
financial accounts: the Consumer Credit Panel counts balances on consumer
credit reports, while Z.1 counts liabilities of the household sector
including items that never appear on a credit report. The levels differ by
roughly a trillion dollars and the two must not be mixed.

Outputs:
  data/credit/household_debt.csv   year,mortgage,heloc,auto,credit_card,
                                   student,other,total,quarters
  data/credit/credit_access.csv    year,cc_balance,cc_limit,cc_available,
                                   cc_utilisation,quarters
  data/credit/delinquency.csv      year,mortgage,heloc,auto,credit_card,
                                   student,other,all,quarters
  data/credit/rates.csv            year,cc_apr_all,cc_apr_assessed,
                                   auto_60m,personal_24m,quarters
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import openpyxl
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "credit"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

HHDC = ("https://www.newyorkfed.org/medialibrary/interactives/householdcredit/"
        "data/xls/hhd_c_report_{q}.xlsx")
G19 = "https://www.federalreserve.gov/releases/g19/HIST/cc_hist_tc_levels.html"

YEAR_FROM, YEAR_TO = 2006, 2026

# The report is published about six weeks after the quarter it covers, so the
# newest file is found by walking back from the current quarter rather than
# hardcoded — a hardcoded name silently stops updating.
CANDIDATES = [f"{y}q{q}" for y in range(YEAR_TO, YEAR_FROM - 1, -1)
              for q in (4, 3, 2, 1)]


def latest_report() -> Path:
    """The newest published quarterly workbook, cached."""
    for existing in sorted(CACHE.glob("hhd_c_report_*.xlsx"), reverse=True):
        return existing
    for tag in CANDIDATES:
        url = HHDC.format(q=tag)
        try:
            r = requests.get(url, timeout=180)
        except Exception:  # noqa: BLE001
            continue
        if r.ok and r.content[:2] == b"PK":
            path = CACHE / f"hhd_c_report_{tag}.xlsx"
            path.write_bytes(r.content)
            print(f"  downloaded {tag}")
            return path
    raise SystemExit("no NY Fed household debt report could be downloaded")


def quarter_key(label: str) -> tuple[int, int] | None:
    """The report labels a quarter "03:Q1", meaning 2003Q1. Two-digit years
    are resolved against the report's own span, which starts in 1999."""
    m = re.fullmatch(r"(\d{2}):Q([1-4])", str(label).strip())
    if not m:
        return None
    yy, q = int(m.group(1)), int(m.group(2))
    return (1900 + yy if yy >= 90 else 2000 + yy), q


def read_page(path: Path, sheet: str) -> tuple[list[str], dict[tuple[int, int], list[float | None]]]:
    """(column names, {(year, quarter): row of values}) for one data sheet."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = [list(r) for r in wb[sheet].iter_rows(values_only=True)]
    header_idx = next(i for i, r in enumerate(rows)
                      if any(isinstance(c, str) and c.strip() for c in r[1:4])
                      and quarter_key(r[0]) is None
                      and i > 0 and quarter_key(rows[i + 1][0]) is not None)
    names = [str(c).strip() if c is not None else ""
             for c in rows[header_idx][1:]]
    out: dict[tuple[int, int], list[float | None]] = {}
    for r in rows[header_idx + 1:]:
        key = quarter_key(r[0])
        if key is None:
            continue
        out[key] = [v if isinstance(v, (int, float)) else None
                    for v in r[1:1 + len(names)]]
    return names, out


def by_year(data: dict[tuple[int, int], list[float | None]], col: int,
            how: str = "q4") -> dict[int, tuple[float | None, int]]:
    """{year: (value, quarters available)}.

    how='q4' takes the fourth quarter, which is the year-end stock; a year
    without a Q4 yet returns its latest quarter with the count, so a partial
    year is visible rather than silently shorter.
    how='avg' averages the published quarters, for a rate.
    """
    out: dict[int, tuple[float | None, int]] = {}
    years = {y for y, _ in data}
    for y in sorted(years):
        got = [(q, data[(y, q)][col]) for q in (1, 2, 3, 4)
               if (y, q) in data and col < len(data[(y, q)])
               and data[(y, q)][col] is not None]
        if not got:
            continue
        vals = [v for _, v in got if v is not None]
        if not vals:
            continue
        if how == "avg":
            out[y] = (sum(vals) / len(vals), len(got))
        else:
            out[y] = (vals[-1], len(got))
    return out


def fmt(v: float | None, dec: int = 3) -> str:
    return "" if v is None else f"{v:.{dec}f}"


def write(name: str, header: str, rows: list[str]) -> None:
    path = DATA / "credit" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header] + rows) + "\n")
    print(f"  -> {path.relative_to(ROOT)}")


def match(names: list[str], *words: str) -> int:
    """The index of the first column whose name contains all of `words`."""
    for i, n in enumerate(names):
        low = n.lower()
        if all(w.lower() in low for w in words):
            return i
    raise SystemExit(f"no column matching {words} in {names}")


# ------------------------------------------------------------- the report
def household_debt(path: Path) -> None:
    names, data = read_page(path, "Page 3 Data")
    print(f"  [page 3] {names}")
    cols = [match(names, w) for w in
            ("Mortgage", "HE Revolving", "Auto", "Credit Card",
             "Student", "Other", "Total")]
    series = [by_year(data, c) for c in cols]
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        got = [s.get(y) for s in series]
        nq = max((g[1] for g in got if g), default=0)
        rows.append(f"{y}," + ",".join(
            fmt(g[0]) if g else "" for g in got) + f",{nq}")
    write("household_debt.csv",
          "year,mortgage,heloc,auto,credit_card,student,other,total,quarters",
          rows)


def credit_access(path: Path) -> None:
    names, data = read_page(path, "Page 10 Data")
    print(f"  [page 10] {names}")
    bal = by_year(data, match(names, "Credit Card Balance"))
    avail = by_year(data, match(names, "Credit Card Available"))
    limit = by_year(data, match(names, "Credit Card Limit"))
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        b, a, l = bal.get(y), avail.get(y), limit.get(y)
        # utilisation is balance over limit: the share of the credit line
        # households have actually drawn, which is what "availability"
        # means from the borrower's side rather than the lender's
        util = (b[0] / l[0] * 100) if (b and l and b[0] and l[0]) else None
        nq = max((g[1] for g in (b, a, l) if g), default=0)
        rows.append(f"{y},{fmt(b[0]) if b else ''},{fmt(l[0]) if l else ''},"
                    f"{fmt(a[0]) if a else ''},{fmt(util, 1)},{nq}")
    write("credit_access.csv",
          "year,cc_balance,cc_limit,cc_available,cc_utilisation,quarters", rows)


def delinquency(path: Path) -> None:
    names, data = read_page(path, "Page 12 Data")
    print(f"  [page 12] {names}")
    cols = [match(names, w) for w in
            ("MORTGAGE", "HELOC", "AUTO", "CC", "STUDENT", "OTHER", "ALL")]
    # a delinquency rate is a rate, so the year is its average, not its Q4
    series = [by_year(data, c, "avg") for c in cols]
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        got = [s.get(y) for s in series]
        nq = max((g[1] for g in got if g), default=0)
        rows.append(f"{y}," + ",".join(
            fmt(g[0], 2) if g else "" for g in got) + f",{nq}")
    write("delinquency.csv",
          "year,mortgage,heloc,auto,credit_card,student,other,all,quarters",
          rows)


# ----------------------------------------------------------------- G.19
def borrowing_rates() -> None:
    path = CACHE / "g19_terms.html"
    if not path.exists():
        try:
            path.write_text(requests.get(G19, timeout=120).text)
        except Exception as e:  # noqa: BLE001
            print(f"  !! G.19 failed: {type(e).__name__}: {e}")
            return
    text = re.sub(r"<script.*?</script>", "", path.read_text(), flags=re.S)

    header: list[str] = []
    data: dict[tuple[int, int], list[str]] = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.S):
        cells = [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split())
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr,
                                     flags=re.S)]
        if not cells:
            continue
        m = re.fullmatch(r"(\d{4})\s*Q([1-4])", cells[0])
        if m:
            data[(int(m.group(1)), int(m.group(2)))] = cells[1:]
        elif cells[0] == "Date":
            header = cells[1:]
    if not header or not data:
        print("  !! G.19 table could not be parsed")
        return
    print(f"  [g.19] {header}")

    def col(*words: str) -> int:
        return match(header, *words)

    picks = {"cc_apr_all": col("credit card amounts"),
             "cc_apr_assessed": col("assessed interest"),
             "auto_60m": col("60-month"),
             "personal_24m": col("personal")}
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        quarters = [data[(y, q)] for q in (1, 2, 3, 4) if (y, q) in data]
        out = []
        for _, j in picks.items():
            vals = []
            for qrow in quarters:
                if j < len(qrow):
                    try:
                        vals.append(float(qrow[j]))
                    except ValueError:
                        pass  # "n.a." before a series starts
            out.append(fmt(sum(vals) / len(vals), 2) if vals else "")
        rows.append(f"{y}," + ",".join(out) + f",{len(quarters)}")
    write("rates.csv",
          "year,cc_apr_all,cc_apr_assessed,auto_60m,personal_24m,quarters",
          rows)


def main() -> None:
    print("Fetching household debt and credit...")
    report = latest_report()
    print(f"  report: {report.name}")
    household_debt(report)
    credit_access(report)
    delinquency(report)
    borrowing_rates()
    print("Done.")


if __name__ == "__main__":
    main()
