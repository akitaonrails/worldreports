#!/usr/bin/env python3
"""Fetch goods trade by partner country from the Census Bureau.

Census publishes the whole country-by-month history as one workbook, with an
annual column (IYR for imports, EYR for exports) — no key needed.

This is the CENSUS BASIS and must never be added to or compared against the
BEA figures in `data/trade/trade.csv`. Census counts GOODS at customs value
as they cross the border; BEA's national accounts count goods AND services on
a balance-of-payments basis, which re-times some shipments, nets out goods
that never change ownership, and adds the services surplus. For 2024 the two
differ by about 300 billion dollars, and the services surplus is the single
biggest reason. Shares here are therefore computed against the Census goods
total, not against the BEA total.

The file mixes countries with BLOCS — "European Union", "OPEC", "ASEAN",
"Pacific Rim Countries" are rows of their own. Census gives a bloc a country
code beginning with 0, so summing every row would count Germany once as
Germany, again inside the European Union, and possibly a third time inside
Europe. The total here sums only non-bloc codes, and the script prints that
total against the published US goods total so the reader can check it.

Outputs:
  data/trade/partners.csv  year,country,imports,exports,balance,import_share
  data/trade/goods.csv     year,imports,exports,balance,countries
"""
from __future__ import annotations

import csv
from pathlib import Path

import openpyxl
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "trade"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

URL = "https://www.census.gov/foreign-trade/balance/country.xlsx"

YEAR_FROM, YEAR_TO = 2006, 2026

# The partners the plate draws: the exact Census name, then the name written
# out. The European Union is a bloc and is drawn as one, which is how US
# trade policy treats it; it is excluded from the country total to avoid
# double counting.
#
# "Korea, South" is renamed because its comma is a field separator: written
# straight into a CSV it silently turns a six-column row into seven, and
# every column after it shifts by one. The CSV is written through the csv
# module as well, so a name with a comma would be quoted rather than
# corrupting the file even if one is added later.
PARTNERS = (
    ("China", "China"),
    ("European Union", "European Union"),
    ("Mexico", "Mexico"),
    ("Canada", "Canada"),
    ("Japan", "Japan"),
    ("Vietnam", "Vietnam"),
    ("Korea, South", "South Korea"),
    ("Germany", "Germany"),
    ("India", "India"),
    ("Taiwan", "Taiwan"),
)

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


def workbook() -> Path:
    path = CACHE / "country.xlsx"
    if not path.exists():
        print(f"  downloading {URL}")
        r = requests.get(URL, timeout=300)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path


def write_csv(path: Path, rows: list[list]) -> None:
    """Through the csv module, so a value containing a comma is quoted
    rather than silently shifting every column after it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    print(f"  -> {path.relative_to(ROOT)}")


def is_bloc(code: str) -> bool:
    """Census numbers a country group with a leading zero (0003 = European
    Union, 0001 = OPEC). A real country's code starts 1-9."""
    return code.startswith("0")


def main() -> None:
    print("Fetching Census goods trade by country...")
    wb = openpyxl.load_workbook(workbook(), read_only=True, data_only=True)
    ws = wb["country"]
    rows = ws.iter_rows(values_only=True)
    header = [str(c).strip() if c is not None else "" for c in next(rows)]
    idx = {name: i for i, name in enumerate(header)}

    # {year: {country: (imports, exports, is_bloc)}}, in US$ millions
    data: dict[int, dict[str, tuple[float, float, bool]]] = {}
    # how many months of each year the file actually carries, so a part-year
    # total is never presented as an annual one
    months: dict[int, int] = {}
    for r in rows:
        try:
            year = int(str(r[idx["year"]]))
        except (TypeError, ValueError):
            continue
        if not (YEAR_FROM <= year <= YEAR_TO):
            continue
        name = str(r[idx["CTYNAME"]] or "").strip()
        code = str(r[idx["CTY_CODE"]] or "").strip()
        imp, exp = r[idx["IYR"]], r[idx["EYR"]]
        if not name:
            continue
        # Census ZERO-FILLS the months it has not published yet, so a
        # presence test counts twelve months in August. Only a non-zero
        # month counts, and because the count below is a max across all
        # 259 partners, a month that is genuinely zero for one small
        # country cannot shorten the year.
        filled = sum(1 for m in MONTHS
                     if isinstance(r[idx[f"I{m}"]], (int, float))
                     and r[idx[f"I{m}"]])
        months[year] = max(months.get(year, 0), filled)
        data.setdefault(year, {})[name] = (
            float(imp) if isinstance(imp, (int, float)) else 0.0,
            float(exp) if isinstance(exp, (int, float)) else 0.0,
            is_bloc(code))

    # ---- the all-country total, blocs excluded ---------------------------
    out = [["year", "imports", "exports", "balance", "countries", "months"]]
    totals: dict[int, tuple[float, float]] = {}
    for year in sorted(data):
        countries = [(i, e) for i, e, bloc in data[year].values() if not bloc]
        imp = sum(i for i, _ in countries)
        exp = sum(e for _, e in countries)
        totals[year] = (imp, exp)
        out.append([year, f"{imp / 1000:.1f}", f"{exp / 1000:.1f}",
                    f"{(exp - imp) / 1000:.1f}", len(countries),
                    months.get(year, 0)])
    write_csv(DATA / "trade" / "goods.csv", out)
    for y in (2006, 2018, 2024, 2025, 2026):
        if y in totals:
            imp, exp = totals[y]
            print(f"     {y}: goods imports US$ {imp / 1000:,.0f}bn, "
                  f"exports {exp / 1000:,.0f}bn, "
                  f"balance {(exp - imp) / 1000:+,.0f}bn "
                  f"({months.get(y, 0)} months)")

    # ---- the partners ----------------------------------------------------
    missing = [src for src, _ in PARTNERS
               if not any(src in data[y] for y in data)]
    if missing:
        raise SystemExit(f"no Census rows named: {missing}")
    out = [["year", "country", "imports", "exports", "balance",
            "import_share", "months"]]
    for year in sorted(data):
        imp_total = totals[year][0]
        for source, label in PARTNERS:
            got = data[year].get(source)
            if not got:
                continue
            imp, exp, _ = got
            share = (imp / imp_total * 100) if imp_total else None
            out.append([year, label, f"{imp / 1000:.1f}", f"{exp / 1000:.1f}",
                        f"{(exp - imp) / 1000:.1f}",
                        "" if share is None else f"{share:.2f}",
                        months.get(year, 0)])
    write_csv(DATA / "trade" / "partners.csv", out)
    print(f"     {len(PARTNERS)} partners")
    print("Done.")


if __name__ == "__main__":
    main()
