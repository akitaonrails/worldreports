#!/usr/bin/env python3
"""Fetch the S&P 500 index.

This is the ONE series in this atlas that does not come from the body that
produces it. The S&P 500 is owned and calculated by S&P Dow Jones Indices,
which licenses its history commercially and publishes no free archive; there
is no federal agency equivalent, because the index is private intellectual
property rather than an official statistic. The Federal Reserve's own
releases carry no equity index, and FRED's mirror of one has been
unreachable for the whole of this build.

So the quotes are read from Yahoo Finance, a redistributor, and that is
stated plainly here and in SOURCES.md rather than dressed up. What makes it
usable is that it is checkable: a market close is a published fact that many
parties record independently, so the year-end closes are asserted against
known values and the script fails if any of them has moved. Seven years are
checked and all seven agree to the cent.

Two other sources were tried and rejected. Robert Shiller's `ie_data.xls`,
the standard academic series, now ends in September 2023. Stooq serves a
JavaScript proof-of-work challenge, which is an anti-bot measure and is left
alone rather than worked around.

A year is reported four ways because "the market in 2008" has four different
honest answers: the close (where it ended), the average (where it sat), and
the high and low with the largest peak-to-trough fall inside the year (what
it did). The 2008 close alone hides a 48% drawdown.

Outputs:
  data/markets/sp500.csv  year,close,average,high,low,drawdown_pct,
                          change_pct,trading_days,asof
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "markets"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"

YEAR_FROM, YEAR_TO = 2006, 2026

# Published year-end closes, used as an assertion rather than as data. If
# the feed ever disagrees with these the series is wrong and the script
# stops, because a market close does not get revised.
KNOWN_CLOSE = {
    2007: 1468.36, 2008: 903.25, 2012: 1426.19, 2019: 3230.78,
    2021: 4766.18, 2022: 3839.50, 2024: 5881.63,
}
TOLERANCE = 0.01


def quotes() -> list[tuple[dt.date, float]]:
    """Daily closes, cached. One year before YEAR_FROM is requested so the
    first year has a prior close to measure its change against."""
    path = CACHE / "gspc_daily.json"
    if not path.exists():
        start = dt.datetime(YEAR_FROM - 1, 1, 1, tzinfo=dt.UTC)
        end = dt.datetime(YEAR_TO + 1, 1, 1, tzinfo=dt.UTC)
        r = requests.get(CHART, timeout=180,
                         params={"period1": int(start.timestamp()),
                                 "period2": int(end.timestamp()),
                                 "interval": "1d"},
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        path.write_text(r.text)
    payload = json.loads(path.read_text())
    result = payload["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    out = []
    for stamp, close in zip(result["timestamp"], closes):
        if close is None:
            continue  # a holiday the feed still lists
        out.append((dt.datetime.fromtimestamp(stamp, dt.UTC).date(),
                    float(close)))
    out.sort()
    return out


def main() -> None:
    print("Fetching the S&P 500...")
    pts = quotes()
    if not pts:
        raise SystemExit("no quotes returned")
    print(f"  {len(pts)} trading days, {pts[0][0]} to {pts[-1][0]}")

    by_year: dict[int, list[tuple[dt.date, float]]] = {}
    for day, close in pts:
        by_year.setdefault(day.year, []).append((day, close))

    # ---- the assertion ---------------------------------------------------
    for year, expected in sorted(KNOWN_CLOSE.items()):
        got = by_year.get(year)
        if not got:
            raise SystemExit(f"no {year} quotes to check against {expected}")
        if abs(got[-1][1] - expected) > TOLERANCE:
            raise SystemExit(
                f"{year} close is {got[-1][1]:.2f}, not the published "
                f"{expected:.2f} — the feed cannot be trusted")
    print(f"  {len(KNOWN_CLOSE)} published year-end closes all agree")

    rows = []
    for year in range(YEAR_FROM, YEAR_TO + 1):
        got = by_year.get(year)
        if not got:
            rows.append(f"{year},,,,,,,,")
            continue
        values = [c for _, c in got]
        close, high, low = values[-1], max(values), min(values)

        # the largest fall from a running peak, which is the drawdown a
        # holder actually lived through; the year's high minus its low
        # would overstate it whenever the low came first
        peak, drawdown = values[0], 0.0
        for v in values:
            peak = max(peak, v)
            drawdown = min(drawdown, v / peak - 1)

        prior = by_year.get(year - 1)
        change = (close / prior[-1][1] - 1) * 100 if prior else None
        rows.append(
            f"{year},{close:.2f},{sum(values) / len(values):.2f},"
            f"{high:.2f},{low:.2f},{drawdown * 100:.1f},"
            f"{'' if change is None else f'{change:.1f}'},"
            f"{len(values)},{got[-1][0]}")

    path = DATA / "markets" / "sp500.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("year,close,average,high,low,drawdown_pct,change_pct,"
                    "trading_days,asof\n" + "\n".join(rows) + "\n")
    print(f"  -> {path.relative_to(ROOT)}")
    for y in (2008, 2020, 2025, 2026):
        if y in by_year:
            v = [c for _, c in by_year[y]]
            print(f"     {y}: close {v[-1]:,.0f}, {len(v)} trading days")
    print("Done.")


if __name__ == "__main__":
    main()
