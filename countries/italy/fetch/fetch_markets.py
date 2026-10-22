#!/usr/bin/env python3
"""Refresh the FTSE MIB closes for plate 05 into a sidecar CSV.

Usage:  python3 -I countries/italy/fetch/fetch_markets.py

  FTSEMIB.MI  FTSE MIB  (Borsa Italiana, price index)

Nobody official publishes an index close, so this comes from a
redistributor and is marked official: false in SOURCES.yaml. stooq's
^ftsemib daily CSV was the first choice and is behind a JavaScript
proof-of-work wall (verified 2026-10-22, same wall that blocked ^IBEX in
the Spain session), so Yahoo's monthly bars are used instead.

This is a PRICE index: it excludes dividends. That matters more for the
comparison than it looks, because the FTSE MIB's dividend yield has run
among the highest in Europe for most of the period, so a price-only
chart understates Milan against any total-return series. The plate says
so.

Monthly bars are requested rather than daily: Yahoo's monthly close IS
the last trading day's close of that month, which is exactly the
year-end value, and it keeps the payload small enough to be polite.

Output: data/markets/ftsemib_from_yahoo.csv
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

SYMBOL = "FTSEMIB.MI"
Y0, Y1 = 2005, 2026   # 2005 leaves room for any rebasing the plate wants


def fetch() -> dict[int, tuple[str, float]]:
    """{year: (iso date, close)} for the last observation of each year."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "yahoo_ftsemib.json"
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
            raise RuntimeError(f"yahoo ftsemib: {last}")
    return year_ends(payload)


def year_ends(payload: dict) -> dict[int, tuple[str, float]]:
    """The last non-null monthly close of each calendar year.

    Monthly bars are stamped at the START of their month, in the
    exchange's own time. Read as UTC, midnight in Milan is 23:00 the
    previous day (or 22:00 under DST), so every FTSE MIB bar lands one
    month early and the "2006 close" comes back as January 2007's. The
    exchange offset in `meta` is applied to recover the local date.

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


def main() -> None:
    print("Fetching FTSE MIB closes...")
    series = fetch()
    DATA.mkdir(parents=True, exist_ok=True)
    lines = ["year,close"]
    for y in range(Y0, Y1 + 1):
        hit = series.get(y)
        lines.append(f"{y},{hit[1]:.2f}" if hit else f"{y},")
    (DATA / "ftsemib_from_yahoo.csv").write_text("\n".join(lines) + "\n")
    latest = max(series)
    print(f"  -> data/markets/ftsemib_from_yahoo.csv "
          f"(latest bar {series[latest][0]}: {series[latest][1]:,.2f})")
    print("Done. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
