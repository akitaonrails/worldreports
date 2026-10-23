#!/usr/bin/env python3
"""Refresh the federal fiscal series from the Fiscal Reference Tables.

Usage:  make C=canada fetch

The FRT is the Department of Finance's annual compendium of federal public
finances, published as one workbook with sixty-five sheets. It is the
publisher of record for everything in the fiscal chapter: the budgetary
balance, revenue and expense by category, and the liabilities.

Six sheets are taken:

  2  fiscal transactions, per cent of GDP
  4  revenues by source, per cent of GDP
  8  expenses by category, per cent of GDP
  15 total liabilities, net debt and the accumulated deficit, $ millions
  53 G7 general-government overall balance, per cent of GDP
  54 G7 general-government net debt, per cent of GDP
  55 G7 general-government gross debt, per cent of GDP

Three things about this source that a chart will get wrong if nobody
writes them down:

**The federal year is not the calendar year.** Rows are labelled
`2024-25` and run 1 April to 31 March, so the `fiscal_year` column here
holds the starting year and must never be plotted against a calendar
series without saying so.

**Tables 1-17 are the federal government; tables 51-55 are general
government.** They are not the same entity and not the same accounting
basis. Canada's federal accumulated deficit was about 42% of GDP in
2024-25 while its general-government gross debt was 111% — the second
number includes the provinces, which do most of the borrowing that
matters, and the much-quoted *net* figure of 12% subtracts the CPP and
QPP assets. All three are correct and they answer different questions.

**The series breaks.** Full accrual accounting arrives in 1983-84, which
is before this window. Inside it: net actuarial losses became a separate
expense line in 2019-20 with 2008-09 onward reclassified, and the
discount-rate methodology changed in 2017-18 with 2008-09 onward
restated. So the columns that split the balance either side of net
actuarial losses simply do not exist before 2008-09, and they are left
empty rather than filled from the undivided figure.

The G7 tables are the IMF's numbers, redistributed by Finance Canada.

Outputs are `_from_frt` sidecars. Nothing here overwrites a curated file.
"""
from __future__ import annotations

import csv
import re
import sys
import urllib.request
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
EDITION = 2025
BOOK = (f"https://www.canada.ca/content/dam/fin/publications/frt-trf/"
        f"{EDITION}/frt-trf-{str(EDITION)[2:]}-eng.xlsx")

FISCAL_YEAR = re.compile(r"^(\d{4})-\d{2}$")
CALENDAR_YEAR = re.compile(r"^(\d{4})$")

# sheet -> (output, key column name, the columns to keep as (index, name)).
# Indexes are positional because the headers are spread over five merged
# rows and three of them repeat the word "Total".
SHEETS = {
    "2 - Fiscal transactions % GDP": (
        "fiscal/transactions_pct_gdp_from_frt.csv", "fiscal_year", [
            (1, "revenues"),
            (2, "program_expenses_excl_actuarial"),
            (3, "public_debt_charges"),
            (4, "balance_excl_actuarial"),
            (5, "net_actuarial_losses"),
            (6, "budgetary_balance"),
            # The federal debt-to-GDP ratio Ottawa argues about: the
            # accumulated deficit, per cent of GDP. Fiscal slot 3 draws it
            # beside the general-government gross debt.
            (9, "accumulated_deficit"),
        ]),
    "4 - Revenues % GDP": (
        "fiscal/revenues_pct_gdp_from_frt.csv", "fiscal_year", [
            (1, "personal_income_tax"),
            (2, "corporate_income_tax"),
            (3, "non_resident_income_tax"),
            (4, "other_taxes_and_duties"),
            (5, "total_tax_revenues"),
            (6, "ei_premiums"),
            (8, "other_revenues"),
            (9, "total_revenues"),
        ]),
    "8 - Expenses % GDP": (
        "fiscal/expenses_pct_gdp_from_frt.csv", "fiscal_year", [
            (1, "transfers_to_persons"),
            (2, "transfers_to_provinces"),
            (4, "direct_program_expenses"),
            (5, "net_actuarial_losses"),
            (6, "total_program_expenses"),
            (7, "public_debt_charges"),
            (8, "total_expenses"),
        ]),
    "15-Total liab,net debt, acc def": (
        "fiscal/liabilities_from_frt.csv", "fiscal_year", [
            (1, "interest_bearing_debt_mn"),
            (5, "total_liabilities_mn"),
            (6, "financial_assets_mn"),
            (7, "net_debt_mn"),
            (8, "non_financial_assets_mn"),
            (9, "accumulated_deficit_mn"),
        ]),
    "53 Gen Gov Overall Balance": (
        "international/g7_balance_from_frt.csv", "year", None),
    "54 - Gen Gov Net Debt ": (
        "international/g7_net_debt_from_frt.csv", "year", None),
    "55 - Gen Gov Gross Debt ": (
        "international/g7_gross_debt_from_frt.csv", "year", None),
}
G7 = [(1, "canada"), (2, "united_states"), (3, "japan"),
      (4, "united_kingdom"), (5, "germany"), (6, "france"), (7, "italy"),
      (8, "g7_average")]


def book() -> openpyxl.Workbook:
    CACHE.mkdir(exist_ok=True)
    local = CACHE / f"frt{EDITION}.xlsx"
    if not local.exists():
        print(f"  downloading {BOOK}")
        with urllib.request.urlopen(BOOK, timeout=300) as r:
            blob = r.read()
        # An error page under HTTP 200 is not a workbook. Every xlsx is a
        # zip, so the magic number is the cheapest possible check.
        if blob[:2] != b"PK":
            raise RuntimeError("the FRT download is not a workbook")
        local.write_bytes(blob)
    return openpyxl.load_workbook(local, data_only=True)


def cell(value) -> str:
    """A spreadsheet cell as it should appear in a CSV.

    The FRT writes a missing figure as a dash, which `float()` accepts
    from nobody and a chart would otherwise draw as zero.
    """
    if value is None or value == "" or value == "-":
        return ""
    if isinstance(value, (int, float)):
        return f"{value:g}"
    text = str(value).strip().replace(",", "")
    return text if text not in ("-", "–", "..", "n/a") else ""


def extract(ws, key: str, cols) -> list[list[str]]:
    pattern = FISCAL_YEAR if key == "fiscal_year" else CALENDAR_YEAR
    cols = cols or G7
    rows = []
    for row in ws.iter_rows(values_only=True):
        head = str(row[0]).strip() if row[0] is not None else ""
        m = pattern.match(head)
        if not m:
            continue
        rows.append([m.group(1)] + [cell(row[i]) if i < len(row) else ""
                                    for i, _ in cols])
    return rows


def main() -> None:
    print(f"Fiscal Reference Tables {EDITION} (Department of Finance Canada)")
    wb = book()
    for sheet, (rel, key, cols) in SHEETS.items():
        if sheet not in wb.sheetnames:
            print(f"  !! {sheet}: not in this edition", file=sys.stderr)
            continue
        rows = extract(wb[sheet], key, cols)
        path = DATA / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([key] + [name for _, name in (cols or G7)])
            w.writerows(rows)
        print(f"  data/{rel}  {len(rows)} rows "
              f"({rows[0][0]}–{rows[-1][0]})" if rows else f"  data/{rel}  EMPTY")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
