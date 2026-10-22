#!/usr/bin/env python3
"""Refresh the SSE Composite year-end closes into a sidecar CSV.

Usage:  python3 -I countries/china/fetch/fetch_markets.py

  000001.SS  SSE Composite (上证综合指数), Shanghai Stock Exchange, price
             index in CNY — the index the country argues about, the one
             that carried the 2007 bubble (peak 6124.04 on 2007-10-16)
             and the June 2015 crash.

Nobody publishes a stock index as a statistic, so this comes from a
redistributor (Yahoo Finance) and is marked official: false in
SOURCES.yaml; the plate says so too. stooq's daily CSV — the first
choice in other countries — is JS-walled from this machine, and Yahoo
answers 429 to urllib's default User-Agent; the browser UA below gets
through (verified 2026-10-22, meta: symbol 000001.SS, exchange SHH,
instrumentType INDEX, currency CNY, firstTradeDate 1997-07).

This is a PRICE index: it excludes dividends. The spine draws it
converted to US$ and rebased to 2006 = 100 (markets slot 4) — the CNY
level here is the raw reading the conversion is computed from.

Monthly bars are requested rather than daily: Yahoo's monthly close IS
the last trading day's close of that month, which is exactly the
year-end value, and it keeps the payload small enough to be polite. The
bars are stamped at the START of their month in the EXCHANGE's time
(gmtoffset 28800, Shanghai UTC+8); read as bare UTC every bar lands one
month early and the "2015 close" comes back as January 2016's. The
offset below is applied to recover the local date — the spot asserts on
known year-end closes exist precisely so a shift like that cannot pass.

Year-ends asserted against the exchange's own record as redistributed
(2026-10-22, and cross-checked against Yahoo's daily bars for the last
trading day of each asserted December): 2007-12-28 5261.56, 2015-12-31
3539.18, 2024-12-31 3351.76. The print record for 2007 quotes 5261.24;
Yahoo's history runs 0.32 points (0.006%) higher for that one bar and
the sidecar records what the redistributor says, unrounded.

A month still in progress reports a close too, so the current year's
row is a live reading, not an annual total — the plate labels it.

Output: data/markets/sse_index_from_yahoo.csv
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "markets"
CACHE = ROOT / "cache" / "markets"

CHART = ("https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
         "?interval=1mo&period1={p1}&period2={p2}")
# A browser UA is required: the endpoint answers 429 to the default urllib one.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

SYMBOL = "000001.SS"
Y0, Y1 = 2005, 2026   # 2005 leaves room for any rebasing the plate wants

# (year, close): known year-end closes, read off the redistributor's own
# record 2026-10-22 and checked against Yahoo's daily bars (same dates,
# same values) — see the docstring for the 2007 print-record note.
SPOT = [(2007, 5261.56), (2015, 3539.18), (2024, 3351.76)]

META = {
    "symbol": "000001.SS",
    "exchangeName": "SHH",
    "instrumentType": "INDEX",
    "currency": "CNY",
}


def fetch() -> dict[int, tuple[str, float]]:
    """{year: (bar local date, close)} for the last observation of each year."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE / "yahoo_sse.json"

    def check(payload: dict) -> None:
        result = payload["chart"]["result"][0]
        meta = result["meta"]
        for key, want in META.items():
            if meta.get(key) != want:
                raise ValueError(f"meta.{key} is {meta.get(key)!r}, "
                                 f"not {want!r}")
        if meta.get("gmtoffset") != 28800:
            raise ValueError(f"unexpected gmtoffset {meta.get('gmtoffset')}")
        stamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        if not stamps or not closes or len(stamps) != len(closes):
            raise ValueError("timestamp/close length mismatch or empty")
        if any(c is None for c in closes):
            raise ValueError("null monthly close in the window")

    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
        try:
            check(payload)
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache yahoo_sse.json: {e}", file=sys.stderr)
            cache_file.unlink()
            payload = None
    else:
        payload = None
    if payload is None:
        p1 = int(datetime(Y0, 1, 1, tzinfo=timezone.utc).timestamp())
        p2 = int(datetime(Y1, 12, 31, tzinfo=timezone.utc).timestamp())
        url = CHART.format(symbol=SYMBOL, p1=p1, p2=p2)
        last = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=90) as r:
                    payload = json.loads(r.read())
                check(payload)
                cache_file.write_text(json.dumps(payload))
                break
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"  yahoo sse attempt {attempt + 1}: {e}",
                      file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        else:
            raise RuntimeError(f"yahoo sse: {last}")
    return year_ends(payload)


def year_ends(payload: dict) -> dict[int, tuple[str, float]]:
    """The last non-null monthly close of each calendar year.

    Bar stamps carry the exchange offset (see docstring): the map's year
    is the LOCAL year of the bar, so the December bar lands in its own
    year and its close is the year-end value.
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
    series = fetch()
    for year, close in SPOT:
        got = series.get(year)
        if got is None or abs(got[1] - close) > 0.05:
            raise RuntimeError(f"sse {year} close is {got}, not {close}")
        print(f"  spot {year}: {got[1]:,.2f} (bar {got[0]}) — as expected")
    DATA.mkdir(parents=True, exist_ok=True)
    lines = ["year,close"]
    for y in range(Y0, Y1 + 1):
        hit = series.get(y)
        lines.append(f"{y},{hit[1]:.2f}" if hit else f"{y},")
    (DATA / "sse_index_from_yahoo.csv").write_text("\n".join(lines) + "\n")
    latest = max(series)
    print(f"  -> data/markets/sse_index_from_yahoo.csv "
          f"(latest bar {series[latest][0]}: {series[latest][1]:,.2f}; "
          "running year, not an annual total)")
    print("Done. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
