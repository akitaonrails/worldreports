#!/usr/bin/env python3
"""Credit, household debt and interest rates from the BCRA's own API.

Usage:  python3 scripts/fetch_bcra.py

Outputs
  data/macro/credit_check.csv  year, private credit and its household
                               components, each as % of GDP, plus the peso
                               stocks the ratios were built from
  data/macro/rates_check.csv   year, the three rates a household or a firm
                               actually meets, nominal and real

Why not `apis.datos.gob.ar` like everything else in this atlas: the series
gateway's BCRA mirror is broken in exactly the places this panel needs.

  - `174.1_PTAMOS_TAL_0_0_33` (loans to the private sector) has a
    **42-year hole, July 1975 to March 2017**. The complete sibling,
    "préstamos totales", includes lending to the public sector and to other
    financial institutions — in December 2017 the private share was 42% of
    it — so it is not a substitute.
  - The loans-to-the-public-sector series that would let you subtract is
    null for the entire window.
  - `174.1_T_INTERS_0_0_56` (5-10 year mortgage rate) and
    `174.1_T_INTERO_II_0_0_57` (overdraft rate) stop being measured in June
    2017 and December 2016 and then **keep publishing 0.0 every month
    through 2026**.

The BCRA's own `api.bcra.gob.ar/estadisticas/v4.0` serves all of it, daily,
with real coverage: private credit from 1996, the deposit rate from 1990,
credit-card balances from 2002, the overdraft rate from 2009 and the
personal-loan rate from 2010. It is the same institution publishing the
same numbers through a better door.

The stocks are daily balances in millions of pesos. A year is represented
by its **December average** rather than by 31 December: the last business
day of an Argentine December is a liquidity spike, and in a year where
prices tripled the difference between the two is not a rounding question.

Nominal rates are reported alongside real ones because across this window
the nominal rate alone carries almost no information — a 95% annual
deposit rate in 2023 was a 37% real loss. Real rates are only computed for
the years the national IPC covers; the intervened decade has no
denominator this atlas is willing to divide by.
"""
from __future__ import annotations

import csv
import json
import ssl
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "bcra"
DATA = ROOT / "data" / "macro"
CACHE.mkdir(parents=True, exist_ok=True)

API = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"
UA = {"User-Agent": "argentina-reports/1.0 (+https://github.com/AkitaOnRails)"}
PAGE = 3000
YEAR_FROM, YEAR_TO = 2006, 2026

# Stocks, daily balances in millions of pesos.
STOCKS = {
    "private_total": 26,   # préstamos al sector privado, todas las líneas
    "cards": 115,          # tarjetas de crédito
    "personal": 114,       # préstamos personales
    "mortgage": 112,       # hipotecarios
    "pledge": 113,         # prendarios
}
# What a household owes the banking system: the four retail lines. Business
# lending (adelantos, documentos) is deliberately not in here.
HOUSEHOLD = ("cards", "personal", "mortgage", "pledge")

# Rates, daily, nominal annual percentages.
RATES = {
    "deposit_30d": 12,     # plazo fijo a 30 días — what saving pays
    "overdraft": 13,       # adelantos en cuenta corriente
    "personal_loan": 14,   # préstamos personales — what borrowing costs
}


def get(variable: int) -> dict[str, float]:
    """Every published daily point of one variable, {ISO date -> value}."""
    cache_file = CACHE / f"{variable}.json"
    if cache_file.exists():
        points = json.loads(cache_file.read_text())
        print(f"  [cache] v{variable}: {len(points)} days")
        return points

    points: dict[str, float] = {}
    for offset in range(0, 60000, PAGE):
        url = (f"{API}/{variable}?desde=1990-01-01&hasta={YEAR_TO}-12-31"
               f"&limit={PAGE}&offset={offset}")
        page = request(url, f"v{variable}+{offset}")
        results = page.get("results") or []
        detail = results[0].get("detalle", []) if results else []
        if not detail:
            break
        for row in detail:
            if row.get("valor") is not None:
                points[row["fecha"]] = float(row["valor"])
    if not points:
        print(f"  v{variable}: EMPTY", file=sys.stderr)
        return {}
    cache_file.write_text(json.dumps(points))
    print(f"  v{variable}: {len(points)} days "
          f"{min(points)} .. {max(points)}")
    return points


def request(url: str, label: str) -> dict:
    # The BCRA serves a chain some stores do not carry. The payload is
    # public monetary statistics, so a verified fetch is tried first and an
    # unverified one only as the fallback.
    last: Exception | None = None
    for attempt in range(3):
        for context in (None, ssl._create_unverified_context()):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=120,
                                            context=context) as r:
                    return json.load(r)
            except Exception as e:  # noqa: BLE001
                last = e
        print(f"  {label} attempt {attempt + 1}: {last}", file=sys.stderr)
        time.sleep(3 * (attempt + 1))
    return {}


def december_average(points: dict[str, float]) -> dict[int, float]:
    """One value per year: the mean of that year's December balances.

    31 December is a liquidity spike in Argentine banking and a single
    reading of it is not the year. Averaging the month smooths that without
    reaching back into a different price level, which an annual average
    would do in a year where prices tripled.
    """
    buckets: dict[int, list[float]] = {}
    for date, value in points.items():
        if date[5:7] == "12":
            buckets.setdefault(int(date[:4]), []).append(value)
    return {y: sum(v) / len(v) for y, v in buckets.items()}


def annual_average(points: dict[str, float]) -> dict[int, float]:
    """The mean of every daily reading in the year — for a rate, where the
    whole year is the thing being described."""
    buckets: dict[int, list[float]] = {}
    for date, value in points.items():
        buckets.setdefault(int(date[:4]), []).append(value)
    return {y: sum(v) / len(v) for y, v in buckets.items()}


def read_column(path: Path, column: str) -> dict[int, float]:
    out: dict[int, float] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                out[int(row["year"])] = float(row[column])
            except (TypeError, ValueError, KeyError):
                continue
    return out


def gdp_millions() -> dict[int, float]:
    """Nominal GDP in millions of pesos, from the curated CSV if there is
    one and the fetch sidecar otherwise."""
    for name in ("gdp.csv", "gdp_check.csv"):
        got = read_column(DATA / name, "ars_bn")
        if got:
            print(f"  GDP denominator from data/macro/{name}")
            return {y: v * 1000 for y, v in got.items()}
    raise SystemExit("no GDP series — run fetch_datos_gob.py first")


def inflation() -> dict[int, float]:
    """December-to-December CPI inflation, %, official national IPC only."""
    ipc = read_column(DATA / "ipc.csv", "official") or \
        read_column(DATA / "ipc_check.csv", "official")
    return ipc


def write(name: str, header: str, rows: list[str]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text("\n".join([header] + rows) + "\n")
    print(f"  -> data/macro/{name}")


def fmt(value, spec: str) -> str:
    return format(value, spec) if value is not None else ""


def table(name: str, columns: list[tuple[str, dict[int, float], str]]) -> None:
    rows = [",".join([str(y)] + [fmt(d.get(y), s) for _, d, s in columns])
            for y in range(YEAR_FROM, YEAR_TO + 1)]
    write(name, "year," + ",".join(n for n, _, _ in columns), rows)


def main() -> None:
    print("BCRA — saldos de préstamos al sector privado")
    stocks = {name: december_average(get(v)) for name, v in STOCKS.items()}
    gdp = gdp_millions()

    def share(values: dict[int, float]) -> dict[int, float]:
        return {y: v / gdp[y] * 100 for y, v in values.items() if y in gdp}

    households = {}
    for year in sorted(set().union(*(stocks[k] for k in HOUSEHOLD))):
        parts = [stocks[k][year] for k in HOUSEHOLD if year in stocks[k]]
        if len(parts) == len(HOUSEHOLD):
            households[year] = sum(parts)

    table("credit_check.csv", [
        ("private_pct_gdp", share(stocks["private_total"]), ".2f"),
        ("households_pct_gdp", share(households), ".2f"),
        ("cards_pct_gdp", share(stocks["cards"]), ".2f"),
        ("personal_pct_gdp", share(stocks["personal"]), ".2f"),
        ("mortgage_pct_gdp", share(stocks["mortgage"]), ".2f"),
        ("pledge_pct_gdp", share(stocks["pledge"]), ".2f"),
        ("private_ars_mn", stocks["private_total"], ".0f"),
    ])

    print("BCRA — tasas de interés")
    rates = {name: annual_average(get(v)) for name, v in RATES.items()}
    cpi = inflation()
    columns = []
    for name in RATES:
        columns.append((name, rates[name], ".1f"))
        real = {y: ((1 + r / 100) / (1 + cpi[y] / 100) - 1) * 100
                for y, r in rates[name].items() if y in cpi}
        columns.append((f"{name}_real", real, ".1f"))
    table("rates_check.csv", columns)

    last = max(stocks["private_total"])
    print(f"  private credit {share(stocks['private_total'])[last]:.1f}% of "
          f"GDP in {last}; households "
          f"{share(households).get(last, float('nan')):.1f}%")


if __name__ == "__main__":
    main()
