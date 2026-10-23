#!/usr/bin/env python3
"""Refresh the ^TWII year-end closes into a sidecar CSV.

Usage:  python3 -I countries/taiwan/fetch/fetch_markets.py

Nobody publishes a stock index close as a statistic, so the year-END equity
level comes from a redistributor (Yahoo Finance) and is marked official: false
in SOURCES.yaml (SOURCING §5: a market reading, say so where it appears). This
is the CROSS-CHECK only. The markets slot-4 line of record is the CBC EG27Y01
ANNUAL AVERAGE (staged by fetch_cbc), which is an official series.

The two are DIFFERENT QUANTITIES and must never be spliced (SOURCING §4,
"two publishers, one idea" — here one is a year-end close and one is a year's
mean):

    ^TWII close   = the TWSE capitalisation-weighted index at the last trading
                    day of December (a point reading);
    CBC EG27Y01   = that same index's ANNUAL AVERAGE (a year's mean).

The fetcher therefore pulls ^TWII year-ends, asserts its own internal Dec
closes, and PRINTS the year-end beside the CBC average as context (a point
vs a mean), asserting only the growth direction agrees. It does not treat the
two as equal and does not combine them.

Yahoo quirks (verified 2026-10-23):
  * a browser User-Agent is required (429 to urllib's default);
  * range=5y&interval=1y answers 400 — request 1mo bars with bounded
    period1/period2 and read the December close;
  * monthly bars are stamped at the START of the month in EXCHANGE time
    (gmtoffset 28800, Taipei UTC+8); the bar's close is the month's last close,
    so the Dec bar's close is the year-end. The offset is applied so the bar
    lands in its own year (read as bare UTC every bar shifts a month early);
  * the current year's bar (2026) is a LIVE reading, not a year-end — it is
    reported in the log, never staged as a year's result;
  * Yahoo's history runs a few percent off the CBC average and off older print
    records — the DISCOVERY pass remembered Dec-2021 17,674.4 / Dec-2024
    23,525.41, but the live payload says 18,218.84 / 23,035.1. What is in the
    payload is what is staged; the spots assert against the live payload, and
    the cross-check is on growth direction, not absolute level (a level-only
    assert would pin a redistributor's revision).

Output: data/markets/stock_index_yearend_from_yahoo.csv   (official: false)
"""
from __future__ import annotations

import csv
import json
import socket
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
HEADERS = {"User-Agent": "Mozilla/5.0 (X11, Linux x86_64)"}
SYMBOL = "%5ETWII"                     # ^TWII, the TWSE weighted index
Y0, Y1 = 2005, 2026

META = {"symbol": "^TWII", "instrumentType": "INDEX", "currency": "TWD"}
# Known year-end closes read off the live payload 2026-10-23 (Dec bars).
SPOT = [(2008, 4591.22), (2019, 11997.14), (2024, 23035.10), (2025, 28963.60)]


class FetchError(RuntimeError):
    pass


def fetch() -> dict[int, tuple[str, float]]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE / "yahoo_twii.json"

    def check(payload) -> None:
        try:
            result = payload["chart"]["result"][0]
            meta = result["meta"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"not a Yahoo chart payload ({e})")
        for key, want in META.items():
            got = meta.get(key)
            if key == "exchangeName" and got not in ("TAI", "Taipei"):
                raise ValueError(f"meta.exchangeName {got!r}")
            elif key != "exchangeName" and got != want:
                raise ValueError(f"meta.{key} is {got!r}, not {want!r}")
        if meta.get("gmtoffset") != 28800:
            raise ValueError(f"unexpected gmtoffset {meta.get('gmtoffset')}")
        stamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        if not stamps or not closes or len(stamps) != len(closes):
            raise ValueError("timestamp/close length mismatch or empty")

    if cache_file.exists():
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        try:
            check(payload)
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache yahoo_twii.json: {e}", file=sys.stderr)
            cache_file.unlink()
            payload = None
    else:
        payload = None
    if payload is None:
        p1 = int(datetime(Y0, 1, 1, tzinfo=timezone.utc).timestamp())
        p2 = int(datetime(Y1, 12, 31, tzinfo=timezone.utc).timestamp())
        url = CHART.format(symbol=SYMBOL, p1=p1, p2=p2)
        last = None
        for attempt in range(5):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=90) as r:
                    payload = json.loads(r.read())
                check(payload)
                cache_file.write_text(json.dumps(payload), encoding="utf-8")
                break
            except (socket.gaierror, urllib.error.URLError, OSError,
                    ValueError, json.JSONDecodeError) as e:
                last = e
                print(f"  yahoo twii attempt {attempt + 1}: {type(e).__name__} {e}",
                      file=sys.stderr)
                time.sleep(2 + 2 * attempt)
        else:
            raise FetchError(f"yahoo twii: {last}")
    return year_ends(payload)


def year_ends(payload) -> dict[int, tuple[str, float]]:
    """{CE year: (bar local date, close)} — the Dec close of each year."""
    result = payload["chart"]["result"][0]
    offset = int(result["meta"].get("gmtoffset") or 0)
    out: dict[int, tuple[str, float]] = {}
    for ts, close in zip(result["timestamp"],
                         result["indicators"]["quote"][0]["close"]):
        if close is None:
            continue
        d = datetime.fromtimestamp(ts + offset, tz=timezone.utc)
        if d.month == 12:                     # a Dec bar -> that year's close
            out[d.year] = (d.date().isoformat(), round(float(close), 2))
    return out


def main() -> None:
    print("Yahoo ^TWII year-end (official: false) for Taiwan")
    series = fetch()
    for year, close in SPOT:
        got = series.get(year)
        if got is None or abs(got[1] - close) > 1.0:
            raise FetchError(f"^TWII {year} close is {got}, not {close}")
        print(f"  spot {year}: {got[1]:,.2f} (Dec bar {got[0]}) — as expected")

    # print-only cross-check vs the CBC annual AVERAGE (a different quantity)
    cbc = DATA / "stock_index_avg_from_cbc.csv"
    if cbc.exists():
        rows = {int(r["year"]): float(r["taiex_annual_average"])
                for r in csv.DictReader(
                    ln for ln in cbc.read_text(encoding="utf-8").splitlines()
                    if not ln.startswith("#"))}
        for y in (2019, 2024):
            if y in series and y in rows:
                print(f"  context {y}: ^TWII year-end {series[y][1]:,.0f} vs "
                      f"CBC annual AVERAGE {rows[y]:,.0f} — a point vs a mean, "
                      "different quantities, never spliced")
        for a, b in ((2019, 2024), (2024, 2025)):
            if a in series and b in series and a in rows and b in rows:
                yg = series[b][1] / series[a][1] - 1
                cg = rows[b] / rows[a] - 1
                if (yg > 0) != (cg > 0):
                    raise FetchError(f"^TWII year-end vs CBC-average growth "
                                     f"disagree in sign {a}->{b}")
                print(f"  direction {a}->{b}: year-end {yg:+.1%} vs average "
                      f"{cg:+.1%} — agree (cross-check, not equality)")

    DATA.mkdir(parents=True, exist_ok=True)
    lines = ["year,close"]
    for y in range(2006, 2026):               # 2006-2025 year-ends only
        hit = series.get(y)
        lines.append(f"{y},{hit[1]:.2f}" if hit else f"{y},")
    path = DATA / "stock_index_yearend_from_yahoo.csv"
    if path.exists():
        first = next((ln for ln in path.read_text(encoding="utf-8")
                      .splitlines() if not ln.startswith("#")), "")
        if first != "year,close":
            raise FetchError(f"refusing to overwrite stock_index_yearend_from_yahoo.csv")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    latest = max(series)
    print(f"  -> data/markets/stock_index_yearend_from_yahoo.csv "
          f"(2006-2025 year-ends; latest live bar {series[latest][0]}: "
          f"{series[latest][1]:,.2f} — a running reading, not a year-end)")
    print("Done. This is a redistributor (official: false). Diff before adopting.")


if __name__ == "__main__":
    main()
