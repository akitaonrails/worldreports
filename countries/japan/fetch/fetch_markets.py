#!/usr/bin/env python3
"""Refresh the Nikkei 225 monthly closes into a sidecar CSV.

Usage:  python3 -I countries/japan/fetch/fetch_markets.py

  ^N225  Nikkei Stock Average (Nikkei Inc., price index), via Yahoo Finance

Nobody official publishes an index close, so this comes from a
redistributor and is official: false in SOURCES.yaml. stooq's ^nkx is
behind a JavaScript wall (796 bytes under HTTP 200, verified 2026-10-22),
so Yahoo's monthly bars are used. Yahoo wants a short plain User-Agent
here; a long browser UA got an empty body during discovery.

THE TIME-ZONE TRAP. Each monthly bar is stamped at 00:00 JST on the first
day of its month (meta.gmtoffset = 32400), which is 15:00 UTC on the LAST
day of the PREVIOUS month. Labelled in UTC every bar slips back one month
and the December close comes out as "November". The exchange offset from
`meta` is added to each timestamp before the month is read off it, and the
2025 year-end close of 50,339.5 is asserted on the DECEMBER label to prove
it was.

Yahoo appends one extra bar for the latest trade, stamped at the trade
time inside the running month; the running month therefore appears twice
and the later stamp (the live reading) is kept. That month is
flagged `partial=1`: it is a live reading, not a month-end close.

This is a PRICE index; dividends are excluded.

Output: data/markets/nikkei_from_yahoo.csv  (month, close, partial)
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "markets"
CACHE = ROOT / "cache"

URL = ("https://query1.finance.yahoo.com/v8/finance/chart/%5EN225"
       "?interval=1mo&range=30y")
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}
JST_OFFSET = 32400

# Year-end (December) closes verified 2026-10-22 against Nikkei's published
# year-end values; ±0.1 for rounding to one decimal.
MUST_MATCH = {(2007, 12): 15307.8, (2008, 12): 8859.6, (2012, 12): 10395.2,
              (2019, 12): 23656.6, (2023, 12): 33464.2, (2024, 12): 39894.5,
              (2025, 12): 50339.5}
TOL = 0.1


class FetchError(RuntimeError):
    pass


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise FetchError(msg)


def payload() -> dict:
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "yahoo_n225_1mo.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as r:
                body = json.loads(r.read())
            result = (body.get("chart") or {}).get("result")
            check(bool(result), "no chart.result in payload")
            meta = result[0]["meta"]
            check(meta.get("symbol") == "^N225" and meta.get("currency") == "JPY",
                  f"not the ^N225 JPY series: {meta.get('symbol')}")
            check(len(result[0].get("timestamp") or []) > 300,
                  "fewer than 300 monthly bars")
            cache_file.write_text(json.dumps(body))
            return body
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (403, 429) and e.code < 500:
                break
        except FetchError:
            raise
        except Exception as e:  # noqa: BLE001
            last = e
        print(f"  attempt {attempt + 1}: {last}", file=sys.stderr)
        time.sleep(5 * (attempt + 1))
    raise FetchError(f"yahoo ^N225: {last}")


def monthly(body: dict) -> tuple[dict[tuple[int, int], float], tuple[int, int], str]:
    """{(year, month): close} in exchange-local months; the running month;
    the ISO time of the live reading."""
    result = body["chart"]["result"][0]
    offset = int(result["meta"].get("gmtoffset") or 0)
    check(offset == JST_OFFSET, f"gmtoffset {offset}, expected JST {JST_OFFSET}")
    stamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    out: dict[tuple[int, int], float] = {}
    for ts, close in zip(stamps, closes):   # ascending: a later stamp wins
        if close is None:
            continue                         # a hole stays a hole
        local = datetime.fromtimestamp(ts + offset, tz=timezone.utc)
        out[(local.year, local.month)] = float(close)
    last_local = datetime.fromtimestamp(stamps[-1] + offset, tz=timezone.utc)
    # Every month-start bar must sit at local midnight on day 1; anything
    # else (bar the live reading) means the offset logic is wrong.
    for ts in stamps[:-1]:
        d = datetime.fromtimestamp(ts + offset, tz=timezone.utc)
        check(d.day == 1 and d.hour == 0,
              f"bar {ts} is {d.isoformat()} local, not a month start")
    return out, (last_local.year, last_local.month), last_local.strftime("%Y-%m-%d %H:%M")


def main() -> None:
    print("Nikkei 225 monthly closes (Yahoo ^N225)")
    series, running, live_at = monthly(payload())
    for ym, want in MUST_MATCH.items():
        got = series.get(ym)
        check(got is not None and abs(got - want) <= TOL,
              f"{ym[0]}-{ym[1]:02d}: got {got}, want {want}")
    months = sorted(series)
    DATA.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Nikkei Stock Average (^N225), Nikkei Inc., redistributed by Yahoo Finance. official: false.",
        "# Monthly closes in JPY (index points). PRICE index — dividends excluded.",
        "# Months are EXCHANGE-LOCAL (JST): Yahoo stamps bars at 00:00 JST = 15:00 UTC the",
        "# previous day; gmtoffset was applied so December is December.",
        f"# partial=1: the running month, a live reading at {live_at} JST, not a month-end close.",
        "month,close,partial",
    ]
    y, m = months[0]
    while (y, m) <= months[-1]:
        v = series.get((y, m))
        flag = "1" if (y, m) == running else ""
        lines.append(f"{y}-{m:02d},{'' if v is None else f'{v:.2f}'},{flag}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    (DATA / "nikkei_from_yahoo.csv").write_text("\n".join(lines) + "\n")
    print(f"  data/markets/nikkei_from_yahoo.csv  {len(lines) - 6} rows "
          f"({months[0][0]}-{months[0][1]:02d} → {months[-1][0]}-{months[-1][1]:02d}); "
          f"2025-12 close {series[(2025, 12)]:,.2f}; latest {series[months[-1]]:,.2f}"
          f" (partial, {live_at})")
    print("Done. Diff the sidecar before adopting.")


if __name__ == "__main__":
    try:
        main()
    except FetchError as e:
        sys.exit(f"FAILED: {e}")
