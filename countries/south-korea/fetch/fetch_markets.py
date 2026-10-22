#!/usr/bin/env python3
"""Year-end index closes for the KOSPI and the S&P 500.

Both come from the same place and in the same shape, so they are fetched
together: Yahoo Finance's chart endpoint, which serves the daily close
history for an index without a key.

  ^KS11   KOSPI composite (Korea Exchange)
  ^GSPC   S&P 500

The year-end value is the last *trading* day of each year, picked by date
rather than by position in the response: a gap in the series or a partial
final year would otherwise silently promote some other day to "year-end".
The current year is deliberately kept — it is the latest close, and the
plates draw it dashed and label the date.

Outputs:
  data/markets/kospi.csv   year,close
  data/markets/sp500.csv   year,close

Both are price indices and exclude dividends, which is why plate 05 compares
them to each other rather than calling either a total return.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
DATA = ROOT / "data" / "markets"
CACHE.mkdir(exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

CHART = ("https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
         "?period1={start}&period2={end}&interval=1d")
# Yahoo rejects a request with no browser-shaped user agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) korea-reports/1.0",
           "Accept": "application/json"}

INDICES = {"^KS11": "kospi.csv", "^GSPC": "sp500.csv"}
YEAR_FROM = 2005


def fetch(symbol: str) -> dict | None:
    cache_file = CACHE / f"yahoo_{symbol.strip('^')}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    start = int(datetime(YEAR_FROM, 1, 1, tzinfo=timezone.utc).timestamp())
    end = int(time.time())
    url = CHART.format(symbol=urllib.parse.quote(symbol), start=start, end=end)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as r:
                payload = json.loads(r.read().decode("utf-8"))
            cache_file.write_text(json.dumps(payload))
            return payload
        except Exception as e:  # noqa: BLE001
            print(f"  {symbol} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return None


def year_end_closes(payload: dict) -> dict[int, tuple[str, float]]:
    """{year: (iso date, close)} for the last trading day of each year."""
    result = payload["chart"]["result"][0]
    stamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    best: dict[int, tuple[str, float]] = {}
    for stamp, close in zip(stamps, closes):
        if close is None:
            continue
        day = datetime.fromtimestamp(stamp, tz=timezone.utc).date()
        current = best.get(day.year)
        if current is None or day.isoformat() > current[0]:
            best[day.year] = (day.isoformat(), float(close))
    return best


def main() -> None:
    for symbol, filename in INDICES.items():
        payload = fetch(symbol)
        if not payload:
            print(f"  ! {symbol}: no data, leaving {filename} untouched",
                  file=sys.stderr)
            continue
        closes = year_end_closes(payload)
        lines = ["year,close"]
        for year in sorted(closes):
            lines.append(f"{year},{closes[year][1]:.2f}")
        (DATA / filename).write_text("\n".join(lines) + "\n")
        latest = max(closes)
        print(f"  -> data/markets/{filename} "
              f"({min(closes)}-{latest}, latest {closes[latest][0]} "
              f"= {closes[latest][1]:,.2f})")


if __name__ == "__main__":
    main()
