#!/usr/bin/env python3
"""Refresh the FTSE 100 and the S&P 500 closes into sidecar CSVs.

Usage:  python3 -I countries/united-kingdom/fetch/fetch_markets.py

  ^FTSE  FTSE 100  (London Stock Exchange, price index)
  ^GSPC  S&P 500   (price index, the spine's dashed comparison line)

Markets slot 4 draws the country's index in US$ against the S&P 500 in
US$, so the UK needs both: the FTSE converted at the Bank of England's
year-end USD/GBP rate (markets/sterling_from_boe.csv) and the S&P, which
needs no conversion. The S&P sidecar exists only to be the comparison
line, and is marked official: false like the FTSE.

Nobody official publishes an index close, so this comes from a
redistributor and is marked official: false in SOURCES.yaml. stooq's
^ftse daily CSV was the first choice and is behind a JavaScript
proof-of-work wall (verified 2026-10-22, same wall that blocked ^TSX in
the Canada session and ^IBEX in the Spain one), so Yahoo's monthly bars
are used instead.

This is a PRICE index: it excludes dividends. That matters more for the
comparison than it looks, because the FTSE 100's dividend yield has run
among the highest of the major indices for most of the period, so a
price-only chart understates London against any total-return series.
The plate says so, and so does the comment in the CSV.

Monthly bars are requested rather than daily: Yahoo's monthly close IS
the last trading day's close of that month, which is exactly the
year-end value, and it keeps the payload small enough to be polite.

Output: data/markets/ftse_from_yahoo.csv
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "markets"
CACHE = ROOT / "cache"

CHART = ("https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
         "?interval=1mo&period1={p1}&period2={p2}")
# A browser UA is required: the endpoint answers 429 to the default urllib one.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

Y0, Y1 = 2005, 2026   # 2005 leaves room for any rebasing the plate wants

#: (yahoo symbol, cache file, sidecar file, {year: pinned close})
SYMBOLS = [
    ("%5EFTSE", "yahoo_ftse.json", "ftse_from_yahoo.csv",
     # Year-end closes verified against published FTSE 100 annual values
     # on 2026-10-22; small tolerance for Yahoo's adjustment drift.
     {2007: 6456.9, 2024: 8173.0, 2025: 9931.4}),
    ("%5EGSPC", "yahoo_sp500.json", "sp500_from_yahoo.csv",
     # The S&P 500 year-end closes, read from the same monthly-bar channel
     # on 2026-10-23 and pinned so a payload that changes shape or units
     # fails the run instead of redrawing the plate differently.
     {2007: 1468.36, 2024: 5881.63}),
]
TOL = 1.0


def fetch(symbol: str, cache_name: str) -> dict[int, tuple[str, float]]:
    """{year: (iso date, close)} for the last observation of each year."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / cache_name
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        p1 = int(datetime(Y0, 1, 1, tzinfo=timezone.utc).timestamp())
        p2 = int(datetime(Y1, 12, 31, tzinfo=timezone.utc).timestamp())
        url = CHART.format(symbol=SYMBOL, p1=p1, p2=p2)
        last = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=90) as r:
                    payload = json.loads(r.read())
                if not payload.get("chart", {}).get("result"):
                    raise ValueError("no result in payload")
                cache_file.write_text(json.dumps(payload))
                break
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(3 * (attempt + 1))
        else:
            raise RuntimeError(f"yahoo {symbol}: {last}")
    return year_ends(payload)


def year_ends(payload: dict) -> dict[int, tuple[str, float]]:
    """The last non-null monthly close of each calendar year.

    Monthly bars are stamped at the START of their month, in the exchange's
    own time. Read as UTC, midnight in London can sit up to an hour into
    the previous day, so a bar can land one month early and the "December
    close" come back as January's. The exchange offset in `meta` is applied
    to recover the local date.

    A month still in progress reports a close too, so the current year's
    value is a live reading, not an annual total — the plate labels it.
    """
    result = payload["chart"]["result"][0]
    offset = int(result["meta"].get("gmtoffset") or 0)
    stamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    out: dict[int, tuple[str, float]] = {}
    for ts, close in zip(stamps, closes):
        if close is None:
            continue
        d = datetime.fromtimestamp(ts + offset, tz=timezone.utc)
        out[d.year] = (d.date().isoformat(), float(close))
    return out


def verify(series: dict[int, tuple[str, float]],
           must_match: dict[int, float]) -> None:
    for year, want in must_match.items():
        got = series.get(year)
        assert got is not None, f"{year}: no bar returned"
        assert abs(got[1] - want) <= TOL, (
            f"{year}: got {got[1]:,.2f}, want {want:,.2f} (tol {TOL})")


#: The '#' header each sidecar carries: what the number is, and what it is
#: not. Read back by the tests and the provenance page.
HEADERS = {
    "ftse_from_yahoo.csv": [
        "# PRICE index: the FTSE 100 excludes dividends. Its dividend yield is",
        "# among the highest of the major indices, so a price-only chart",
        "# understates London against any total-return series.",
    ],
    "sp500_from_yahoo.csv": [
        "# PRICE index, US dollars, the S&P 500. Drawn only as the spine's",
        "# dashed comparison line on markets slot 4; the FTSE is converted to",
        "# US$ at the Bank of England year-end rate, this one needs no",
        "# conversion. A year's value is the last trading day's close, so the",
        "# 2026 row is a live bar, not an annual figure.",
    ],
}


def main() -> None:
    DATA.mkdir(exist_ok=True)
    for symbol, cache_name, out_name, must_match in SYMBOLS:
        print(f"Fetching {symbol} closes...")
        series = fetch(symbol, cache_name)
        verify(series, must_match)
        lines = HEADERS[out_name] + ["year,close"]
        for y in range(Y0, Y1 + 1):
            hit = series.get(y)
            lines.append(f"{y},{hit[1]:.2f}" if hit else f"{y},")
        (DATA / out_name).write_text("\n".join(lines) + "\n")
        latest = max(series)
        print(f"  -> data/markets/{out_name} "
              f"(latest bar {series[latest][0]}: {series[latest][1]:,.2f})")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
