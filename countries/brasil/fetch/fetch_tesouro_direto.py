#!/usr/bin/env python3
"""A 10-year government bond yield for Brazil, from Tesouro Direto.

Usage:  python3 -P countries/brasil/fetch/fetch_tesouro_direto.py

Output (a sidecar — diff it into markets/bond_10y.csv by hand):
  data/markets/bond_10y_from_tesouro.csv
      year,yield_10y,days,maturity_years_mean,maturity_years_min,maturity_years_max

Brazil publishes no constant-maturity 10-year yield in any official
time-series API: the BCB's SGS has none, and the OECD's "long-term
interest rate" for Brazil is the TJLP, a BNDES lending rate, not a bond
yield. What the Tesouro does publish, for every business day since 2002,
is the rate at which it sold each fixed-rate bond to the public through
Tesouro Direto. The fixed-coupon NTN-F ("Tesouro Prefixado com Juros
Semestrais") is the closest thing Brazil has to a benchmark nominal
government bond, and Tesouro Direto has always offered one maturing
roughly ten years out.

So, for each business day: take every NTN-F on offer, keep the one whose
maturity is closest to ten years from that day, and read its buy rate
("Taxa Compra Manhã", the yield an investor locks in). The year's value
is the mean over its business days that had such a bond. The day count
and the maturities actually used are written
beside it, so a year served by a 7-year or a 12-year bond is visible in
the file rather than hidden in an average. This is a retail offer rate,
set by the Tesouro from the market each morning; it is not ANBIMA's
secondary-market curve, and the panel says which it is.

The files are one workbook per year on the Tesouro's CDN, one sheet per
bond; reading them needs xlrd (requirements-fetch.txt).
"""
from __future__ import annotations

import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

import xlrd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "tesouro_direto"
DATA = ROOT / "data"
URL = ("https://cdn.tesouro.gov.br/sistemas-internos/apex/producao/sistemas/"
       "sistd/{y}/NTN-F_{y}.xls")
YEARS = range(2006, 2027)
TARGET = 10.0
# A day whose nearest bond matures further than this from ten years out
# is not a 10-year quote and is skipped; a year with fewer than MIN_DAYS
# such days is left blank rather than drawn. In 2006 the longest NTN-F on
# offer was seven years and in 2009 eight, so those years are blank.
TOLERANCE = 1.5
MIN_DAYS = 60


def workbook(year: int) -> xlrd.book.Book:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"NTN-F_{year}.xls"
    if not path.exists():
        req = urllib.request.Request(URL.format(y=year),
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
        if not body.startswith(b"\xd0\xcf\x11\xe0"):
            raise SystemExit(f"{year}: not an .xls workbook "
                             f"({body[:60]!r}); nothing written")
        path.write_bytes(body)
    return xlrd.open_workbook(path)


def day(v, book) -> date:
    if isinstance(v, float):
        return xlrd.xldate_as_datetime(v, book.datemode).date()
    return datetime.strptime(str(v).strip(), "%d/%m/%Y").date()


def quotes(year: int) -> dict[date, list[tuple[float, float]]]:
    """{business day: [(years to maturity, buy rate %), ...]}."""
    book = workbook(year)
    out: dict[date, list[tuple[float, float]]] = {}
    for sh in book.sheets():
        head = sh.row_values(0)
        if str(head[0]).strip() != "Vencimento":
            raise SystemExit(f"{year}/{sh.name}: unexpected header {head!r}")
        maturity = day(head[1], book)
        cols = sh.row_values(1)
        rate_col = cols.index("Taxa Compra Manhã")
        for r in range(2, sh.nrows):
            row = sh.row_values(r)
            if row[0] in ("", None) or row[rate_col] in ("", None):
                continue
            d = day(row[0], book)
            rate = float(row[rate_col])
            # the workbooks store 0.1299, not 12.99
            rate = rate * 100 if rate < 1 else rate
            out.setdefault(d, []).append(((maturity - d).days / 365.25, rate))
    return out


# Read by hand off NTN-F_2015.xls, sheet "NTN-F 010125", 02/01/2015:
# Taxa Compra Manhã 0.1234. A fetch that does not reproduce it writes
# nothing.
SPOT = (2015, date(2015, 1, 2), date(2025, 1, 1), 12.34)


def check_spot() -> None:
    year, d, maturity, want = SPOT
    years = (maturity - d).days / 365.25
    got = [r for m, r in quotes(year).get(d, []) if abs(m - years) < 1e-6]
    if not got or abs(got[0] - want) > 1e-6:
        raise SystemExit(f"spot {d} NTN-F {maturity}: {got}, expected "
                         f"{want}; nothing written")


def main() -> None:
    check_spot()
    lines = ["year,yield_10y,days,maturity_years_mean,maturity_years_min,"
             "maturity_years_max"]
    for y in YEARS:
        picks = []
        for d, offers in sorted(quotes(y).items()):
            if d.year != y:
                continue
            m, rate = min(offers, key=lambda o: abs(o[0] - TARGET))
            if abs(m - TARGET) <= TOLERANCE:
                picks.append((m, rate))
        ms = [m for m, _ in picks]
        if len(picks) < MIN_DAYS:
            lines.append(f"{y},,{len(picks)},,,")
            print(f"  {y}: no NTN-F near ten years — blank", file=sys.stderr)
            continue
        avg = sum(r for _, r in picks) / len(picks)
        lines.append(f"{y},{avg:.2f},{len(picks)},{sum(ms) / len(ms):.1f},"
                     f"{min(ms):.1f},{max(ms):.1f}")
        print(f"  {y}: {avg:.2f}% over {len(picks)} days", file=sys.stderr)
    out = DATA / "markets" / "bond_10y_from_tesouro.csv"
    out.write_text("\n".join(lines) + "\n")
    print(f"  -> {out.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
