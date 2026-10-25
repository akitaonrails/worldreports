#!/usr/bin/env python3
"""Refresh Paraguay's Ministry of Economy and Finance fiscal series.

Usage:  make C=paraguay fetch   (or: python3 -I fetch/fetch_mef.py)

The MEF (Ministerio de Economía y Finanzas, until 2025 the Ministerio de
Hacienda) publishes the national fiscal accounts as XLSX workbooks on
`mef.gov.py`. The one used here is

  MEFP 2001 ADMINISTRACIÓN CENTRAL 2003-2025 serie anual.xlsx

whose `% PIB` sheet is the Gobierno Central's GFS-2001 presentation in
percent of GDP for 2003-2025, and whose `Serie` sheet carries the same
table in *miles de millones de guaraníes* (thousands of millions — NOT
millions: the older `Situacion Financiera 1980-2022` workbook is in
millions, and reading one as the other is a factor of 1,000). Both are
read and cross-checked against each other before anything is written.

Scope, which the plates must keep labelled:
  * Administración Central — central government, not general government.
    The IMF WEO general-government series in fiscal/fiscal_from_imf.csv
    runs about four points of GDP above this one, permanently.
  * Cash basis (GFS 2001 "Estado de operaciones"), not accrual.
  * Calendar year.
  * The guaraní has no minor unit in practice and was never
    redenominated; every value is current guaraníes of its own year.

Two revenue lines are staged separately because they are the country's
own story: the Itaipú/Yacyretá royalties and the energy-cession
compensation. They are FISCAL REVENUE under the binational treaties, not
a share of GDP produced by hydroelectricity, and the plate says so.
"""
from __future__ import annotations

import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

BASE = "https://www.mef.gov.py"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
ANNUAL = ("/sites/default/files/2026-05/MEFP 2001 ADMINISTRACIÓN CENTRAL "
          "2003-2025 serie anual.xlsx")

YEAR_FROM, YEAR_TO = 2003, 2025

COMMENTS = [
    "MEF (Paraguay), 'MEFP 2001 Administración Central 2003-2025 serie",
    "anual': Gobierno Central on a cash basis, GFS-2001 presentation, in",
    "percent of GDP. NOT general government (the IMF series in",
    "fiscal_from_imf.csv is that perimeter and sits ~4 points higher).",
    "Itaipu/Yacyretá royalties and the energy-cession compensation are",
    "staged as their own revenue lines: they are fiscal revenue under the",
    "binational treaties, not a share of GDP produced by hydro.",
    "public_investment_pct_gdp is 'Activos fijos' (net acquisition of",
    "non-financial fixed assets), the central government's own capital",
    "spending, not whole-economy GFCF.",
]

# normalized label -> column. Labels are matched exactly (after accent
# folding) because several appear twice in the sheet as group headers
# and as line items, and a prefix match would take the wrong one.
FIELDS = {
    "ingreso total": "revenue_pct_gdp",
    "gasto total obligado": "expenditure_pct_gdp",
    "intereses": "interest_pct_gdp",
    "balance operativo neto (ingreso menos gasto)": "operating_balance_pct_gdp",
    "resultado primario": "primary_balance_pct_gdp",
    "prestamo neto / endeudamiento neto": "net_lending_pct_gdp",
    "regalias y compensacion itaipu y yacyreta":
        "itaipu_royalties_pct_gdp",
    "compensacion cesion de energia itaipu y yacyreta":
        "itaipu_cession_pct_gdp",
    "activos fijos": "public_investment_pct_gdp",
    "producto interno bruto (pib)": "gdp_pyg_bn",
}


def norm(text) -> str:
    if text is None:
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def fetch() -> Path:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / "mef_annual.xlsx"
    if path.exists():
        return path
    url = BASE + urllib.parse.quote(ANNUAL, safe="/")
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
            if not raw.startswith(b"PK"):
                raise ValueError("not a workbook (HTML under 200?)")
            path.write_bytes(raw)
            return path
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  mef attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise SystemExit(f"cannot fetch {url}: {last}")


def sheet_year_table(ws, header_row: int) -> dict[str, dict[int, float]]:
    """{normalized label: {year: value}} for one MEF sheet."""
    years = list(next(ws.iter_rows(min_row=header_row, max_row=header_row,
                                   values_only=True)))
    table: dict[str, dict[int, float]] = {}
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        label = norm(row[0])
        if not label:
            continue
        values = {}
        for y, v in zip(years[2:], row[2:]):
            if isinstance(y, (int, float)) and 1990 < y < 2100 \
                    and isinstance(v, (int, float)):
                values[int(y)] = float(v)
        if values:
            table.setdefault(label, values)
    return table


def main() -> None:
    import openpyxl

    print("MEF Paraguay — central administration fiscal series")
    wb = openpyxl.load_workbook(fetch(), data_only=True)
    pct = sheet_year_table(wb["% PIB"], header_row=12)
    series = sheet_year_table(wb["Serie"], header_row=12)

    columns: dict[str, dict[int, float]] = {}
    for label, column in FIELDS.items():
        if label not in pct:
            raise SystemExit(f"label not found in % PIB: {label!r}")
        columns[column] = pct[label]

    # The same table in miles de millones de guaraníes, to prove the
    # percent sheet and the level sheet are one workbook and not two
    # vintages, and to catch a unit read as millions: the implied GDP
    # from each line must be the same number and must sit where
    # Paraguay's GDP sits (hundreds of thousands of millions of PYG).
    # The workbook's own GDP row (miles de millones de guaraníes) runs
    # 2003-2022 only, and the level sheet stops at 2023, so those years
    # are checked by identity and the later ones by the percent sheet's
    # own pins below.
    for y in (2019, 2022, 2023):
        implied = []
        for label in ("ingreso total", "gasto total obligado"):
            implied.append(100.0 * series[label][y] / pct[label][y])
        assert abs(implied[0] / implied[1] - 1) < 0.005, \
            f"{y}: revenue and expenditure imply different GDPs {implied}"
        assert 200_000 < implied[0] < 400_000, \
            f"{y}: implied GDP {implied[0]:,.0f} is not in thousands of " \
            "millions of guaraníes"
        published_gdp = pct["producto interno bruto (pib)"].get(y)
        if published_gdp:
            assert abs(implied[0] - published_gdp) < 1.0, \
                f"{y}: implied GDP {implied[0]:,.1f} vs published " \
                f"{published_gdp:,.1f}"

    # Known values from the publisher's own tables.
    assert abs(columns["revenue_pct_gdp"][2006] - 12.63) < 0.01
    assert abs(columns["net_lending_pct_gdp"][2025] - -2.00) < 0.01
    assert abs(columns["gdp_pyg_bn"][2022] - 292166.75) < 0.01

    path = ROOT / "data" / "fiscal" / "fiscal_national_from_mef.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(columns)
    lines = [f"# {c}" for c in COMMENTS]
    lines.append("year," + ",".join(names))
    for y in range(YEAR_FROM, YEAR_TO + 1):
        cells = []
        for name in names:
            v = columns[name].get(y)
            cells.append("" if v is None else
                         f"{v:.0f}" if name == "gdp_pyg_bn" else f"{v:.2f}")
        lines.append(f"{y}," + ",".join(cells))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/fiscal/fiscal_national_from_mef.csv  "
          f"{YEAR_TO - YEAR_FROM + 1} rows")
    print("Done. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
