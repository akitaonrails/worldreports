#!/usr/bin/env python3
"""Refresh the SMI closes into a sidecar CSV.

Usage:  python3 -I countries/switzerland/fetch/fetch_markets.py

  ^SSMI  Swiss Market Index  (SIX Swiss Exchange, PRICE index, CHF)

Nobody official publishes an index close, so this comes from a
redistributor and is `official: false` in SOURCES.yaml. stooq's ^smi is
behind a JavaScript wall (a 796-byte page under HTTP 200, verified
2026-10-22), so Yahoo's monthly bars are used.

Yahoo needs the SHORT browser User-Agent "Mozilla/5.0 (X11; Linux
x86_64)": both a full Chrome UA and the default urllib/curl UA got 429.

TIMESTAMP TRAP. Monthly bars are stamped at local midnight Europe/Zurich
on the first of the month, expressed in UTC — i.e. 23:00 or 22:00 UTC on
the last day of the PREVIOUS month. A naive UTC conversion labels every
bar one month early, and the "December close" comes back as November's.
Each stamp is converted with the payload's exchangeTimezoneName
(Europe/Zurich, DST-aware via zoneinfo), and the fetcher asserts every
converted bar falls on the 1st at 00:00 local.

This is the SMI PRICE index: it excludes dividends (the SMIC is the
total-return sibling and a different series). Yahoo's monthly close is
the close of the month's last trading day, so the December bar is the
year-end close. The current year's value is a live reading of a month in
progress, not a year-end; its `as_of` date says so.

Output: data/markets/smi_from_yahoo.csv
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "markets"
CACHE = ROOT / "cache"

URL = ("https://query1.finance.yahoo.com/v8/finance/chart/%5ESSMI"
       "?interval=1mo&period1={p1}&period2={p2}")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
Y0, Y1 = 2005, 2026

# December closes verified 2026-10-22 (DISCOVERY.md / SOURCES.yaml).
MUST_MATCH = {2006: 8785.7, 2007: 8484.5, 2008: 5534.5, 2015: 8818.1,
              2022: 10729.4, 2024: 11600.9, 2025: 13267.5}
TOL = 1.0


def fetch() -> dict:
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "mkt_yahoo_ssmi.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    p1 = int(datetime(Y0, 1, 1, tzinfo=timezone.utc).timestamp())
    p2 = int(datetime(Y1, 12, 31, tzinfo=timezone.utc).timestamp())
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL.format(p1=p1, p2=p2),
                                         headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as r:
                payload = json.loads(r.read())
            result = (payload.get("chart") or {}).get("result")
            if not result or not result[0].get("timestamp"):
                raise ValueError("no result/timestamps in payload")
            meta = result[0]["meta"]
            if meta.get("symbol") != "^SSMI" or meta.get("currency") != "CHF":
                raise ValueError(f"unexpected meta {meta.get('symbol')}")
            cache_file.write_text(json.dumps(payload))
            return payload
        except urllib.error.HTTPError as e:
            last = e
            time.sleep(15 * (attempt + 1) if e.code in (403, 429)
                       else 3 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"yahoo ^SSMI: {last}")


def monthly(payload: dict) -> list[tuple[datetime, float]]:
    """[(local bar datetime, close)] with Zurich-local labels."""
    result = payload["chart"]["result"][0]
    tzname = result["meta"].get("exchangeTimezoneName")
    if tzname != "Europe/Zurich":
        raise RuntimeError(f"exchange timezone is {tzname!r}, not Europe/Zurich")
    tz = ZoneInfo(tzname)
    stamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    out = []
    for i, (ts, close) in enumerate(zip(stamps, closes)):
        d = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(tz)
        # Every completed bar must sit on local midnight of the 1st; only
        # the final, in-progress bar carries a live intraday stamp.
        if i < len(stamps) - 1 and (d.day, d.hour, d.minute) != (1, 0, 0):
            raise RuntimeError(f"bar {ts} -> {d.isoformat()} is not a month start")
        if close is not None:
            out.append((d, float(close)))
    return out


def year_ends(bars: list[tuple[datetime, float]]) -> dict[int, tuple[str, float]]:
    """{year: (iso date of the bar, close)} for the last bar of each year."""
    out: dict[int, tuple[str, float]] = {}
    for d, close in bars:
        out[d.year] = (d.date().isoformat(), close)
    return out


def verify(series: dict[int, tuple[str, float]]) -> None:
    for year, want in MUST_MATCH.items():
        got = series.get(year)
        if got is None:
            raise RuntimeError(f"SMI {year}: no bar")
        if not got[0].endswith("-12-01"):
            raise RuntimeError(f"SMI {year}: last bar is {got[0]}, not December")
        if abs(got[1] - want) > TOL:
            raise RuntimeError(f"SMI {year}: got {got[1]:,.2f}, want {want:,.1f}")
    # Magnitude: the SMI has been between ~4,000 and ~15,000 since 2005.
    for y, (_, c) in series.items():
        if not 3000 < c < 20000:
            raise RuntimeError(f"SMI {y}: {c} outside plausible range")


def main() -> None:
    print("Fetching ^SSMI monthly bars from Yahoo...")
    payload = fetch()
    bars = monthly(payload)
    series = year_ends(bars)
    verify(series)
    last_bar = payload["chart"]["result"][0]["timestamp"][-1]
    as_of = datetime.fromtimestamp(last_bar, tz=timezone.utc).astimezone(
        ZoneInfo("Europe/Zurich")).date().isoformat()
    DATA.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Yahoo Finance ^SSMI, SMI PRICE index (excludes dividends; SMIC is the",
        "# total-return series). Units: index points, CHF. official: false.",
        "# close = close of the last monthly bar of the year (December = year-end).",
        "# Bars dated in Europe/Zurich local time (naive UTC would be a month early).",
        f"# The latest year is a live reading of a month in progress (as_of {as_of}).",
        "year,close,bar_month,as_of",
    ]
    for y in range(Y0, Y1 + 1):
        hit = series.get(y)
        if hit is None:
            lines.append(f"{y},,,")
            continue
        partial = as_of if y == max(series) and not hit[0].endswith("-12-01") else ""
        lines.append(f"{y},{hit[1]:.2f},{hit[0][:7]},{partial}")
    (DATA / "smi_from_yahoo.csv").write_text("\n".join(lines) + "\n")
    latest = max(series)
    print(f"  data/markets/smi_from_yahoo.csv  {Y1 - Y0 + 1} rows {Y0}–{Y1} "
          f"({len(bars)} monthly bars; latest {series[latest][1]:,.2f} as of {as_of})")
    print("Done. Spot checks passed. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
