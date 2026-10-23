#!/usr/bin/env python3
"""Refresh the TA-125 and S&P 500 closes for plate 05 into sidecar CSVs.

Usage:  python3 -I countries/israel/fetch/fetch_markets.py

  ^TA125.TA  TASE TA-125 (price index, ILS)
  ^GSPC      S&P 500 (price index, US$) — the yardstick the spine draws
             dashed beside every country's index

Nobody official publishes an index close, so this comes from a
redistributor and is marked official: false in SOURCES.yaml. stooq's
challenge page under HTTP 200 is dead from this machine (checked
2026-10-22), so Yahoo's monthly bars are used; interval=1y is rejected,
1mo is the coarse valid stride. Max range back to 1992, 409 monthly
closes.

TA-125 lives in ILS; the spine's markets slot 4 draws equities in US$
at index 2006 = 100. The plate converts with the staged FX
(markets/usdils_from_wb.csv, fetch_harmonised.py); this sidecar keeps
the index's own points, which is what the exchange quotes.

Yahoo caveat, measured 2026-10-22 and it matters: Yahoo's TA-125
history is internally consistent (each monthly close equals its own
last daily close) but differs from the TASE's own year-end closes by
a few percent in both directions — 2020: 1568.1 here vs 1624.1 TASE,
2024: 2426.8 vs 2500.6, while 2010 runs the other way (1224.0 vs
1203.8). SOURCES.yaml's discovery note recorded the TASE figures
as if read from this endpoint; they are not in this payload. The
sidecar stages what the redistributor actually says, the spot values
below are read off it, and the cross-check asserts the 2020→2024
growth rate agrees with TASE's two published closes (±5%) — a level
shift of a few percent moves the line, not the story. A plate that
needs the official closes needs them hand-curated from TASE; this
file is never that.

Monthly bars are requested rather than daily: Yahoo's monthly close IS
the last trading day's close of that month, which is exactly the
year-end value, and it keeps the payload small enough to be polite.
Bars are stamped at the START of their month in the exchange's own
time; the exchange offset in `meta` is applied, as for the other
countries' market fetchers. The current year's bar is a live reading,
not an annual result — the plate labels it.

Output: data/markets/ta125_from_yahoo.csv, data/markets/sp500_from_yahoo.csv
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
# range=max is NOT safe for every symbol: for ^GSPC it answers with 169
# coarse bars from 1984 whose closes sit in the wrong months (checked
# 2026-10-22), while ^TA125.TA gives true monthly bars. Bounded periods
# are exact for both, as in the Spain fetcher.
# A browser UA is required: the endpoint answers 429 to the default urllib one.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11, Linux x86_64)"}

SYMBOLS = {"ta125": "%5ETA125.TA", "sp500": "%5EGSPC"}
Y0, Y1 = 2005, 2026   # 2005 leaves room; TA-125 bars in fact start 1992

# One known year-end close per index, read off this payload 2026-10-22
# (see the module docstring for the TASE divergence).
SPOT = {"ta125": [(2006, 925.6), (2010, 1224.0), (2015, 1315.2),
                  (2020, 1568.1), (2024, 2426.8)],
        "sp500": [(2008, 903.25), (2024, 5881.63)]}

# TASE's own TA-125 year-end closes (exchange record, hand-entered) for
# the growth-rate cross-check described in the docstring.
TASE_OFFICIAL = {2020: 1624.1, 2024: 2500.6}


class FetchError(RuntimeError):
    pass


def check(payload: dict) -> None:
    """Shape-check the payload before anything is cached or trusted."""
    result = (payload.get("chart") or {}).get("result")
    if not result:
        raise ValueError("no chart result in payload")
    r = result[0]
    stamps, closes = r.get("timestamp"), r["indicators"]["quote"][0]["close"]
    if not stamps or len(stamps) != len(closes):
        raise ValueError("timestamp/close length mismatch")
    filled = [c for c in closes if c is not None]
    if len(filled) < 100:
        raise ValueError(f"only {len(filled)} closes in payload")
    if not all(0 < c < 100_000 for c in filled):
        raise ValueError("close outside any plausible index scale")


def fetch(name: str) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE / f"yahoo_{name}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_bytes())
        try:
            check(payload)
            return payload["chart"]["result"][0]
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache {name}: {e}", file=sys.stderr)
            cache_file.unlink()
    last: Exception | None = None
    p1 = int(datetime(Y0 - 1, 1, 1, tzinfo=timezone.utc).timestamp())
    p2 = int(datetime(Y1, 12, 31, tzinfo=timezone.utc).timestamp())
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                CHART.format(symbol=SYMBOLS[name], p1=p1, p2=p2),
                headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()
            payload = json.loads(raw)
            check(payload)
            cache_file.write_bytes(raw)
            return payload["chart"]["result"][0]
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  yahoo {name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise FetchError(f"yahoo {name}: {last}")


def year_ends(result: dict) -> dict[int, tuple[str, float]]:
    """The last non-null monthly close of each calendar year.

    Monthly bars are stamped at the START of their month in the
    exchange's own time; the `gmtoffset` from meta recovers the local
    date, exactly as in the other countries' market fetchers.
    """
    offset = int(result["meta"].get("gmtoffset") or 0)
    out: dict[int, tuple[str, float]] = {}
    for ts, close in zip(result["timestamp"],
                         result["indicators"]["quote"][0]["close"]):
        if close is None:
            continue
        d = datetime.fromtimestamp(ts + offset, tz=timezone.utc)
        out[d.year] = (d.date().isoformat(), float(close))
    return out


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    series = {}
    for name in SYMBOLS:
        print(f"Fetching {name} closes...")
        result = fetch(name)
        series[name] = year_ends(result)
        for year, want in SPOT[name]:
            got = series[name].get(year, (None, None))[1]
            if got is None or abs(got - want) > 0.6:
                raise FetchError(f"{name} {year} close is {got}, want {want}")
        print(f"  spots ok: {', '.join(f'{y} {v}' for y, v in SPOT[name])}")

    # TA-125 vs TASE's own closes: levels differ by a few percent (the
    # redistributor's history vs the exchange's record), so what is
    # asserted is that the four-year growth rate agrees. If a refetch
    # moves a level by more than that, the payload changed series.
    t = series["ta125"]
    here = t[2024][1] / t[2020][1] - 1
    there = TASE_OFFICIAL[2024] / TASE_OFFICIAL[2020] - 1
    if abs(here - there) > 0.05:
        raise FetchError(f"TA-125 2020->2024 growth {here:.1%} here vs "
                         f"{there:.1%} on TASE's own closes")
    print(f"cross-check TA-125 2020->2024: {here:.1%} here | {there:.1%} "
          "TASE official — ok (the levels themselves differ by a few "
          "percent, recorded in SOURCES.yaml)")

    for name in SYMBOLS:
        lines = ["year,close"]
        for y in range(Y0, Y1 + 1):
            hit = series[name].get(y)
            lines.append(f"{y},{hit[1]:.2f}" if hit else f"{y},")
        path = DATA / f"{name}_from_yahoo.csv"
        if path.exists():
            first = next((ln for ln in path.read_text().splitlines()
                          if not ln.startswith("#")), "")
            if first != "year,close":
                raise FetchError(f"refusing to overwrite {name}_from_yahoo.csv: "
                                 f"it holds {first!r}")
        path.write_text("\n".join(lines) + "\n")
        latest = max(series[name])
        print(f"  -> data/markets/{name}_from_yahoo.csv "
              f"(latest bar {series[name][latest][0]}: "
              f"{series[name][latest][1]:,.2f})")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
