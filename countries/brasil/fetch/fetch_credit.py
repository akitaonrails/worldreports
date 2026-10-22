#!/usr/bin/env python3
"""Credit supply, interest rates and household indebtedness, from BCB/SGS.

Usage:  python3 scripts/fetch_credit.py

Outputs:
  data/macro/credit.csv     year,credit_gdp,stock_brl_mn,rate_total,rate_pj,
                                 rate_pf,npl_total,npl_pf
  data/macro/household_debt.csv  year,debt_income,debt_income_ex_housing,
                                 debt_service

Every series code below was resolved to its official name through BCB's
open-data catalog (`codigo_sgs` on dadosabertos.bcb.gov.br), not guessed
from its value range. That matters: by magnitude alone 20717 looks like
the household rate — it sits highest, at 48.5% — but it is
"recursos livres - Total". The household series is 20716, at 38.2%.
Plotting one under the other's label would be invisible on the chart and
wrong by ten points.

Monthly series are reduced to one value a year by taking DECEMBER, not an
average. These are all stocks or stock ratios measured at a point in
time — debt outstanding against the last twelve months of income — so a
mean of twelve monthly readings would not describe anything. The rate
series are included on the same rule for consistency, which makes them
year-end rates rather than annual averages; SOURCES.yaml says so. The
current year has no December yet, so it takes its latest month and the
plate marks it partial.

Two breaks worth knowing, both documented on the plate:

  - The credit and rate statistics from code 20539 onward begin in March
    2011, when BCB rebuilt them on SCR microdata. Earlier aggregates exist
    but are a different construction.
  - 20539 (credit stock in R$) runs back to 1988 and crosses four currency
    redenominations with no unit column, so its pre-1995 values are not
    money in today's sense. This fetcher starts at 1995.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "sgs_credit"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json"

YEAR_FROM = 1995

# code -> (column, official BCB name, which output file)
SERIES = {
    20622: ("credit_gdp", "Saldo da carteira de crédito em relação ao PIB",
            "credit"),
    20539: ("stock_brl_mn", "Saldo da carteira de crédito - Total", "credit"),
    20714: ("rate_total",
            "Taxa média de juros das operações de crédito - Total", "credit"),
    20715: ("rate_pj",
            "Taxa média de juros das operações de crédito - "
            "Pessoas jurídicas - Total", "credit"),
    20716: ("rate_pf",
            "Taxa média de juros das operações de crédito - "
            "Pessoas físicas - Total", "credit"),
    21082: ("npl_total", "Inadimplência da carteira de crédito - Total",
            "credit"),
    21084: ("npl_pf",
            "Inadimplência da carteira de crédito - Pessoas físicas - Total",
            "credit"),
    29037: ("debt_income",
            "Endividamento das famílias com o SFN em relação à renda "
            "acumulada dos últimos doze meses", "household"),
    29038: ("debt_income_ex_housing",
            "Endividamento das famílias com o SFN exceto crédito "
            "habitacional, em relação à renda acumulada", "household"),
    29034: ("debt_service",
            "Comprometimento de renda das famílias com o serviço da dívida "
            "com o SFN", "household"),
}

FILES = {
    "credit": (DATA / "macro" / "credit.csv",
               ["credit_gdp", "stock_brl_mn", "rate_total", "rate_pj",
                "rate_pf", "npl_total", "npl_pf"]),
    "household": (DATA / "macro" / "household_debt.csv",
                  ["debt_income", "debt_income_ex_housing", "debt_service"]),
}


def fetch(code: int) -> list[dict]:
    cache_file = CACHE / f"sgs_{code}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    req = urllib.request.Request(
        URL.format(code=code),
        headers={"User-Agent": "brasil-reports/1.0",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read().decode("utf-8-sig")
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError:
        # BCB's gateway answers a block with HTTP 200 and an HTML body, so a
        # status check alone would write blank years and exit cleanly
        raise SystemExit(
            f"SGS {code} returned {len(raw)} bytes that are not JSON — the "
            f"gateway is probably blocking: {raw[:120]!r}")
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"SGS {code} returned no observations")
    cache_file.write_text(json.dumps(rows))
    return rows


def december(rows: list[dict]) -> dict[int, float]:
    """One value a year: December, or the latest month of an unfinished year.

    Relies on SGS returning observations in date order, which it does; the
    last row written for a year therefore wins, and for a complete year
    that row is December.
    """
    out: dict[int, float] = {}
    for row in rows:
        value = row.get("valor")
        if value in (None, ""):
            continue
        out[int(row["data"][-4:])] = float(value)
    return out


def main() -> None:
    print("BCB/SGS — credit, interest rates and household debt...")
    cols: dict[str, dict[int, float]] = {}
    for code, (col, name, _) in SERIES.items():
        values = december(fetch(code))
        cols[col] = values
        years = sorted(values)
        print(f"  [sgs {code}] {col}: {len(years)} years "
              f"{years[0]}-{years[-1]}  ({name[:48]})")

    for group, (path, columns) in FILES.items():
        present = [c for c in columns if cols.get(c)]
        years = sorted({y for c in present for y in cols[c]
                        if y >= YEAR_FROM})
        lines = ["year," + ",".join(columns)]
        for y in years:
            cells = []
            for c in columns:
                v = cols.get(c, {}).get(y)
                # the stock is in R$ millions and wants no decimals; every
                # other column is a percentage reported to two
                cells.append("" if v is None else
                             (f"{v:.0f}" if c == "stock_brl_mn"
                              else f"{v:.2f}"))
            lines.append(f"{y}," + ",".join(cells))
        path.write_text("\n".join(lines) + "\n")
        print(f"  -> {path.relative_to(ROOT)} ({years[0]}-{years[-1]})")
    print("Done.")


if __name__ == "__main__":
    main()
