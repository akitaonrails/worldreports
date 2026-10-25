#!/usr/bin/env python3
"""Refresh Poland's non-performing-loan ratio from the EBA Risk Dashboard.

Usage:  make C=poland fetch   (or: python3 -I fetch/fetch_eba.py)

The European Banking Authority publishes, every quarter, the Risk
Dashboard: one workbook with bank-level aggregates by country for the EU
banking sample it supervises. It is the only official series in this
lens that runs to the current quarter for Poland — the NBP's own
sector-wide NPL ratio sits behind a JavaScript challenge on nbp.pl, the
Polish Financial Supervision Authority's site does not answer this
network at all, and the World Bank's copy stops in 2020.

  AQT_3.2  "Share of non-performing loans and advances (NPL ratio)"
           loans and advances, gross amount, % — country aggregate.

SCOPE, and it matters: the Risk Dashboard covers the EBA's reporting
sample (large banks), NOT the whole Polish banking sector. Poland's
cooperative banks are not in it, so this ratio sits below the sector-wide
one NBP publishes. It is comparable ACROSS COUNTRIES, which is what the
credit slot needs, and it is not the national sector number.

The workbook is 6-7 MB and changes URL every quarter; the link is read
from the Risk Dashboard page rather than hard-coded, and the newest
workbook on the page is the one used.

Output: credit/npl_from_eba.csv (review sidecar only).
"""
from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, FetchError, assert_close, get, write_csv  # noqa: E402

PAGE = ("https://www.eba.europa.eu/risk-and-data-analysis/risk-analysis/"
        "risk-monitoring/risk-dashboard")
SHEET = "KRIs by country and EU"
CODE = "AQT_3.2"          # NPL ratio, loans and advances, gross
COUNTRY = "PL"


def workbook_url() -> str:
    """The newest 'Data Annex InteractiveRiskDashboard' link on the page."""
    html = get(PAGE, suffix=".html", timeout=120).decode("utf-8", "replace")
    links = re.findall(
        r'href="([^"]*Data%20Annex%20InteractiveRiskDashboard[^"]*\.xlsx)"',
        html)
    if not links:
        raise FetchError("EBA: no Risk Dashboard data annex on the page")
    links = [l if l.startswith("http") else "https://www.eba.europa.eu" + l
             for l in links]
    # The page lists the current quarter first; a stable sort keeps that
    # order, so the first link is the newest edition.
    return links[0]


def quarterly(url: str) -> dict[str, float]:
    body = get(url, suffix=".xlsx", timeout=300)
    if not zipfile.is_zipfile(io.BytesIO(body)):
        raise FetchError("EBA workbook: not an XLSX (HTML error page?)")
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(body), read_only=True,
                                data_only=True)
    if SHEET not in wb.sheetnames:
        raise FetchError(f"EBA workbook: no {SHEET!r} sheet")
    out: dict[str, float] = {}
    for row in wb[SHEET].iter_rows(values_only=True):
        # [Period, Country, Code, Name, Ratio]
        if not row or len(row) < 5 or row[1] != COUNTRY or row[2] != CODE:
            continue
        period = str(row[0]).strip()
        if len(period) == 6 and period.isdigit():
            out[f"{period[:4]}-Q{(int(period[4:]) - 1) // 3 + 1}"] = \
                float(row[4]) * 100      # the workbook carries a fraction
    if not out:
        raise FetchError(f"EBA: no {CODE} rows for {COUNTRY}")
    return out


def main() -> None:
    print("Fetching the EBA Risk Dashboard...")
    url = workbook_url()
    print(f"  workbook: {url.rsplit('/', 1)[-1]}")
    series = quarterly(url)
    q4 = {int(p[:4]): v for p, v in series.items() if p.endswith("Q4")}
    latest_period = sorted(series)[-1]
    # Known value: the Polish NPL ratio in the EBA sample was 2-3% through
    # 2024, well under the sector-wide figure NBP publishes.
    if 2024 in q4:
        assert_close(q4[2024], 3.8, 1.0, "EBA NPL ratio PL 2024")

    header = ["year", "npl_ratio_pct_q4", "npl_ratio_pct_latest",
              "latest_quarter"]
    rows = []
    for y in range(2014, 2027):
        latest = [p for p in sorted(series) if p.startswith(str(y))]
        rows.append([
            y,
            round(q4[y], 2) if y in q4 else None,
            round(series[latest[-1]], 2) if latest else None,
            latest[-1] if latest else None,
        ])
    path = write_csv("credit/npl_from_eba.csv", header, rows, comment=f"""
EBA Risk Dashboard, {SHEET}, code {CODE}: share of non-performing loans
and advances in gross loans, % of the country aggregate of the EBA's
reporting banks. Q4 = the year-end stock; npl_ratio_pct_latest is the last
quarter available for that year ({latest_period} in this edition), kept
separately so a partial year is never read as a year-end figure.
SCOPE: EBA reporting sample (large banks), NOT the whole Polish banking
sector — cooperative banks are outside it, so this sits below the national
sector-wide ratio.
""")
    print(f"  -> {path.relative_to(DATA)}  ({len(series)} quarters)")
    print("Done. Diff the *_from_eba.csv sidecar before adopting.")


if __name__ == "__main__":
    main()
