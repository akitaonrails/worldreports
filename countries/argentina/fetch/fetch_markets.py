#!/usr/bin/env python3
"""Market series: the Merval, the S&P 500, the parallel dollar, country risk.

Usage:  python3 scripts/fetch_markets.py

Outputs
  data/markets/merval_check.csv       year,close          (year-end, ARS)
  data/markets/sp500_check.csv        year,close          (year-end, USD)
  data/markets/parallel_fx_check.csv  year,blue,ccl       (year-end, ARS/US$)
  data/markets/country_risk_check.csv year,eop_bp,avg_bp  (EMBI+ Argentina)

**These are the only series in this atlas that are not official.** There is
no official source for any of them, and saying so is more honest than
leaving the panels empty:

  - The **Merval** is BYMA's index but BYMA publishes no open historical
    endpoint; the closes come from Yahoo Finance (^MERV).
  - The **S&P 500** is here only as the comparison line, likewise from Yahoo.
  - The **blue and CCL dollar** are, by construction, rates the state does
    not publish: the blue is the street rate and the CCL is implied by
    arbitraging a cross-listed bond. Both come from Ámbito Financiero's
    daily series, republished by api.argentinadatos.com. During the two
    cepo periods the official rate on its own describes a price at which
    most people could not buy, so the gap is the story and the panel draws
    both.
  - **Country risk** is J.P. Morgan's EMBI+ Argentina spread, also via
    Ámbito. It is a vendor index with no public primary feed.

Each is marked as a market reference in SOURCES.yaml rather than attributed
to an institution that never published it.
"""
from __future__ import annotations

import datetime as dt
import json
import ssl
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "markets"
DATA = ROOT / "data" / "markets"
CACHE.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (argentina-reports; data provenance build)"}
YEAR_FROM, YEAR_TO = 2005, 2026

YAHOO = ("https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
         "?period1=1104537600&period2=2000000000&interval=1mo")
AR_DATA = "https://api.argentinadatos.com/v1/{path}"


def get(url: str, cache_name: str):
    cache_file = CACHE / cache_name
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    # api.argentinadatos.com serves a chain some stores do not carry; the
    # payload is public price data, so a verified fetch is attempted first
    # and an unverified one only as the fallback.
    for attempt in range(4):
        for context in (None, ssl._create_unverified_context()):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=120,
                                            context=context) as r:
                    payload = json.load(r)
                cache_file.write_text(json.dumps(payload))
                return payload
            except Exception as e:  # noqa: BLE001
                last = e
        print(f"  {cache_name} attempt {attempt + 1}: {last}", file=sys.stderr)
        time.sleep(3 * (attempt + 1))
    return None


def write(name: str, header: str, rows: list[str]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text("\n".join([header] + rows) + "\n")
    print(f"  -> data/markets/{name}")


def year_end(points: dict[str, float]) -> dict[int, float]:
    """The last reading of each year, by date — never by file order."""
    out: dict[int, tuple[str, float]] = {}
    for date, value in points.items():
        year = int(date[:4])
        if year not in out or date > out[year][0]:
            out[year] = (date, value)
    return {y: v for y, (_, v) in out.items()}


def year_avg(points: dict[str, float]) -> dict[int, float]:
    buckets: dict[int, list[float]] = {}
    for date, value in points.items():
        buckets.setdefault(int(date[:4]), []).append(value)
    return {y: sum(v) / len(v) for y, v in buckets.items()}


# ------------------------------------------------------------------ Yahoo
def yahoo_closes(symbol: str, cache_name: str) -> dict[str, float]:
    payload = get(YAHOO.format(symbol=symbol), cache_name)
    if not payload:
        return {}
    result = payload["chart"]["result"][0]
    stamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    out: dict[str, float] = {}
    for ts, close in zip(stamps, closes):
        if close is None:
            continue
        stamp = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
        out[stamp.strftime("%Y-%m-%d")] = float(close)
    print(f"  {symbol}: {len(out)} monthly closes "
          f"{min(out)[:7]}..{max(out)[:7]}")
    return out


# --------------------------------------------------------- Ámbito mirrors
def ar_series(path: str, cache_name: str, field: str) -> dict[str, float]:
    payload = get(AR_DATA.format(path=path), cache_name)
    if not payload:
        return {}
    out: dict[str, float] = {}
    for row in payload:
        value = row.get(field)
        if value is not None and row.get("fecha"):
            out[row["fecha"]] = float(value)
    print(f"  {path}: {len(out)} days {min(out)}..{max(out)}")
    return out


def rows_for(series: list[dict[int, float]], spec: str) -> list[str]:
    out = []
    for year in range(YEAR_FROM, YEAR_TO + 1):
        cells = [format(s[year], spec) if year in s else "" for s in series]
        out.append(",".join([str(year)] + cells))
    return out


def main() -> None:
    print("Yahoo Finance — index closes")
    merval = year_end(yahoo_closes("%5EMERV", "merv.json"))
    sp500 = year_end(yahoo_closes("%5EGSPC", "gspc.json"))
    write("merval_check.csv", "year,close", rows_for([merval], ".2f"))
    write("sp500_check.csv", "year,close", rows_for([sp500], ".2f"))

    print("Ámbito Financiero (via api.argentinadatos.com) — parallel dollar")
    blue = year_end(ar_series("cotizaciones/dolares/blue", "blue.json", "venta"))
    ccl = year_end(ar_series("cotizaciones/dolares/contadoconliqui",
                             "ccl.json", "venta"))
    write("parallel_fx_check.csv", "year,blue,ccl", rows_for([blue, ccl], ".2f"))

    print("J.P. Morgan EMBI+ Argentina (via api.argentinadatos.com)")
    risk = ar_series("finanzas/indices/riesgo-pais", "riesgo.json", "valor")
    write("country_risk_check.csv", "year,eop_bp,avg_bp",
          rows_for([year_end(risk), year_avg(risk)], ".0f"))


if __name__ == "__main__":
    main()
