#!/usr/bin/env python3
"""Refresh the treasury's debt-stock sidecar from the IGCP workbooks.

Usage:  make C=portugal fetch   (or: python3 -I fetch/fetch_igcp.py)

The IGCP — Agência de Gestão da Tesouraria e da Dívida Pública — publishes
two Excel workbooks from the igcp.pt homepage: the monthly stock of the
Dívida Direta do Estado and the historical debt indicators. Both are taken
here and merged into one annual file.

Four things about this source that a chart will get wrong if nobody writes
them down:

**This is the TREASURY definition of the debt stock.** The Dívida Direta
do Estado is the debt of the central government (the State) managed by the
IGCP, at nominal value, after swaps. It is NOT the Maastricht/EDP
general-government debt that Eurostat publishes (gov_10dd_edpt1, staged in
debt_from_estat.csv) and NOT the cash-basis budget outturn that the Banco
de Portugal republishes from the DGO. Portugal's fiscal layer keeps all
three definitions in three files — the DDE runs HIGHER than the Maastricht
stock (Dec-2025: €315.2bn here vs €275.1bn EDP) because it is
non-consolidated within the State sector and counts more than the EDP
instrument list. Beside, never spliced.

**The download URL churns.** Both workbooks live under a dated folder
(`/sites/default/files/2026-09/…`) that rolls every month. The hrefs are
resolved from the igcp.pt homepage at fetch time; the dated path is never
hardcoded. The cache file carries the folder date so a new month forces a
fresh download.

**The monthly workbook's header row is two formats.** Columns are real
Excel dates until Oct-2020, then switch to text labels ("Nov/20",
"Dez/20", "Jan/21", …) — a mostly-English month abbreviation with the odd
Portuguese "Dez". Both are parsed.

**The series breaks.** From Dec-2015 the headline total began including
the cash-collateral margin accounts on interest- and exchange-rate
derivatives (the component is kept in margin_accounts_mn; it exists from
Mar-2011 and is what the "total incl. margin accounts" row adds back
before the break). The modified-duration series breaks again at
31-Dec-2018 on a present/market-value methodology change.

The stock is a STOCK: the annual reading is the last month of the year
(December, or the latest month for the current year), never a sum and
never an average of the months.

Output is a `_from_igcp` sidecar. Nothing here overwrites a curated file.
"""
from __future__ import annotations

import csv
import re
import sys
import urllib.request
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl is required to read the IGCP xlsx workbooks — "
             "pip install -r requirements-fetch.txt")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
PAGE = "https://www.igcp.pt/pt"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

# Basenames are stable; the dated folder between them and the host is not.
BOOKS = {
    "stock": "Stock_divida_valores_mensais_Debt_stock_monthly_figures.xlsx",
    "indicators": "Indicadores_divida_slonga_Debt_indicators_historical_series.xlsx",
}

MONTHS = {"jan": 1, "feb": 2, "fev": 2, "mar": 3, "apr": 4, "abr": 4,
          "may": 5, "mai": 5, "jun": 6, "jul": 7, "aug": 8, "ago": 8,
          "sep": 9, "set": 9, "oct": 10, "out": 10, "nov": 11,
          "dec": 12, "dez": 12}
TEXT_MONTH = re.compile(r"^([A-Za-z]{3})/(\d{2})$")
FOLDER = re.compile(r"/files/(\d{4}-\d{2})/")


def resolve() -> dict[str, str]:
    """The current URL of each workbook, read off the homepage.

    The month folder in the path rolls with every edition, so hardcoding
    it guarantees a stale-or-404 download within weeks.
    """
    with urllib.request.urlopen(urllib.request.Request(PAGE, headers=UA),
                                timeout=120) as r:
        html = r.read().decode("utf-8", "replace")
    hrefs = re.findall(r'href="([^"]+\.xlsx)"', html)
    urls = {}
    for key, base in BOOKS.items():
        match = [h for h in hrefs if h.rsplit("/", 1)[-1] == base]
        if not match:
            raise RuntimeError(f"{base}: no href on {PAGE} — the page or "
                               "the filename changed; re-check by hand")
        urls[key] = urllib.request.urljoin(PAGE, match[0])
    return urls


def workbook(key: str, url: str) -> openpyxl.Workbook:
    CACHE.mkdir(exist_ok=True)
    folder = FOLDER.search(url)
    local = CACHE / f"{key}_{folder.group(1) if folder else 'undated'}.xlsx"
    if not local.exists():
        print(f"  downloading {url}")
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=300) as r:
            blob = r.read()
        # An error page under HTTP 200 is not a workbook. Every xlsx is a
        # zip, so the magic number is the cheapest possible check.
        if blob[:2] != b"PK":
            raise RuntimeError(f"the {key} download is not a workbook")
        local.write_bytes(blob)
    return openpyxl.load_workbook(local, data_only=True)


def month_of(value) -> tuple[int, int] | None:
    """A header cell as (year, month), from an Excel date or 'Nov/20'."""
    if hasattr(value, "year") and hasattr(value, "month"):
        return (value.year, value.month)
    if isinstance(value, str):
        m = TEXT_MONTH.match(value.strip())
        if m and m.group(1).lower() in MONTHS:
            return (2000 + int(m.group(2)), MONTHS[m.group(1).lower()])
    return None


def label_of(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().lower() if value else ""


def find_row(ws, prefix: str) -> int:
    for row in ws.iter_rows(min_col=1, max_col=1):
        if label_of(row[0].value).startswith(prefix):
            return row[0].row
    raise RuntimeError(f"{ws.title}: no row labelled '{prefix}…'")


def header_row(ws, probes: int = 10) -> dict[int, tuple[int, int]]:
    """column -> (year, month) for the first row that parses as months."""
    for r in range(1, probes + 1):
        months = {c.column: m for c in ws[r] if (m := month_of(c.value))}
        if len(months) > 12:
            return months
    raise RuntimeError(f"{ws.title}: no monthly header row found")


def monthly(ws, row: int, months: dict) -> dict[tuple[int, int], float]:
    out = {}
    for col, ym in months.items():
        v = ws.cell(row=row, column=col).value
        if isinstance(v, (int, float)):
            out[ym] = float(v)
    return out


def fmt(value: float | None, decimals: int) -> str:
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


def main() -> None:
    print("IGCP — Agência de Gestão da Tesouraria e da Dívida Pública")
    urls = resolve()
    stock = workbook("stock", urls["stock"])
    ind = workbook("indicators", urls["indicators"])

    ws = stock["DDE"]
    months = header_row(ws)
    # The headline row ("Dívida total / Total debt") is what the IGCP
    # announces monthly; it gains the margin accounts at the Dec-2015
    # break. The workbook's "total incl. margin accounts" row, which adds
    # them back before the break, is left in the workbook — the shipped
    # series follows the headline definition and margin_accounts_mn keeps
    # the component visible.
    total = monthly(ws, find_row(ws, "dívida total /"), months)
    margin = monthly(ws, find_row(ws, "contas margem"), months)
    if not total:
        raise RuntimeError("DDE: the total-debt row is empty")

    wi = ind["Indicadores hist"]
    imonths = header_row(wi)
    pct_euro = monthly(wi, find_row(wi, "percentagem da dívida euro"), imonths)
    pct_fixed = monthly(wi, find_row(wi, "percentagem de taxa fixa"), imonths)
    maturity = monthly(wi, find_row(wi, "prazo médio residual"), imonths)
    duration = monthly(wi, find_row(wi, "duração modificada"), imonths)

    # A stock is read at the LAST month of each year, never summed.
    latest = {}
    for ym in sorted(total):
        latest[ym[0]] = ym
    rows = []
    for year in sorted(latest):
        ym = latest[year]
        rows.append([
            str(year),
            fmt(total.get(ym), 1),
            fmt(margin.get(ym), 1),
            fmt(pct_euro.get(ym), 2),
            fmt(pct_fixed.get(ym), 2),
            fmt(maturity.get(ym), 2),
            fmt(duration.get(ym), 2),
        ])
    last_year, last_ym = rows[-1][0], latest[int(rows[-1][0])]

    rel = "fiscal/state_debt_from_igcp.csv"
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(
            "# Dívida Direta do Estado (State direct debt) — the TREASURY\n"
            "# definition of the debt stock, managed by the IGCP at nominal\n"
            "# value, after swaps. NOT the Maastricht/EDP general-government\n"
            "# debt (debt_from_estat.csv) and NOT the cash-basis budget\n"
            "# outturn (BPstat/DGO). Three definitions, three files; never\n"
            "# splice. The gap changes SIGN: DDE ran €3–28bn BELOW the EDP\n"
            "# stock through 2018 and €10–40bn ABOVE it from 2021 (Dec-2025\n"
            "# €315.2bn vs €275.1bn) — EDP adds the rest of general\n"
            "# government and consolidates away State debt held inside it.\n"
            "# Monthly stocks read at the LAST month of each year — never\n"
            f"# summed; the running year is its latest month\n"
            f"# ({last_ym[0]}-{last_ym[1]:02d}), a level, not a year-end.\n"
            "# Break Dec-2015: the total began including derivative\n"
            "# cash-collateral margin accounts (margin_accounts_mn, first\n"
            "# nonzero Mar-2011). Modified duration breaks again 31-Dec-2018\n"
            "# (valuation methodology). EUR millions; percentages and years\n"
            "# from the IGCP historical-indicators workbook. Source hrefs\n"
            "# resolved from igcp.pt at fetch time (dated folder churns).\n"
        )
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["year", "direct_debt_mn", "margin_accounts_mn",
                    "pct_euro", "pct_fixed_rate", "avg_maturity_years",
                    "modified_duration_years"])
        w.writerows(rows)
    print(f"  data/{rel}  {len(rows)} rows "
          f"({rows[0][0]}–{last_year}, latest month "
          f"{last_ym[0]}-{last_ym[1]:02d} = {total[last_ym]:,.0f} M€)")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
