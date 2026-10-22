#!/usr/bin/env python3
"""Refresh the Bank of Canada series into sidecar CSVs.

Usage:  make C=canada fetch   (or: python3 countries/canada/fetch/fetch_bankofcanada.py)

The Bank publishes everything here through Valet, a plain JSON API with no
key and no rate limit worth worrying about, and it is the publisher of
record for all of it. Four things come from here:

  STATIC_ATABLE_V39079   target for the overnight rate, end of month
  V122514                the realised overnight rate, monthly average
  BD.CDN.2YR.DQ.YLD      Government of Canada benchmark yield, 2-year
  BD.CDN.10YR.DQ.YLD     Government of Canada benchmark yield, 10-year
  IEXE0101               USD noon rate, daily, to 2017-04-28
  FXUSDCAD               USD daily indicative rate, 2017-01-03 on

The target rate is taken from the monthly static table rather than from
V39079, the business-daily series, which Valet only carries from 2009:
V39079 begins in the middle of the easing that followed 2008 and a plate
drawn from it opens at 0.25% with no fall in front of it.

The two exchange-rate series are NOT one series. The Bank retired the noon
rate on 2017-03-01 and replaced it with a single indicative rate published
at 16:30, computed differently; they are written to two columns and the
plate shows the break rather than hiding it. January to April 2017 is
published on both, which is what makes the break measurable instead of
asserted.

Nothing here overwrites a curated file. Every output is a `_from_boc`
sidecar for a person to diff.
"""
from __future__ import annotations

import csv
import json
import statistics
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
BASE = "https://www.bankofcanada.ca/valet/observations/{series}/json"
Y0, Y1 = 2006, 2026

SERIES = {
    "target_rate": "STATIC_ATABLE_V39079",
    "overnight": "V122514",
    "yield_2y": "BD.CDN.2YR.DQ.YLD",
    "yield_10y": "BD.CDN.10YR.DQ.YLD",
    "usdcad_noon": "IEXE0101",
    "usdcad_daily": "FXUSDCAD",
}


def fetch(name: str) -> list[tuple[str, float]]:
    """One Valet series as [(iso date, value)], chronologically.

    Valet answers an outage with an HTML page under HTTP 200 — Statistics
    Canada was serving one the day this was written — so the payload is
    checked for the shape it must have before anything is cached.
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"boc_{name}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        url = BASE.format(series=SERIES[name]) + f"?start_date={Y0}-01-01"
        last = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    text = r.read().decode("utf-8")
                payload = json.loads(text)
                if "observations" not in payload:
                    raise ValueError("no observations in payload")
                cache_file.write_text(text)
                break
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"valet {SERIES[name]}: {last}")
    out = []
    for obs in payload["observations"]:
        cell = obs.get(SERIES[name]) or {}
        raw = cell.get("v")
        if raw in (None, ""):
            continue          # a holiday, or a month the series had not begun
        out.append((obs["d"], float(raw)))
    out.sort()
    return out


def by_year(obs: list[tuple[str, float]]) -> dict[int, list[float]]:
    years: dict[int, list[float]] = defaultdict(list)
    for day, value in obs:
        years[int(day[:4])].append(value)
    return years


def months_of(obs: list[tuple[str, float]]) -> dict[int, set[str]]:
    """Which months of each year the series actually covers.

    The reason an annual average needs this: IEXE0101 begins in May 2007
    and ends in April 2017, so a mean over the rows Valet returns for
    either of those years is an eight-month average and a four-month
    average presented as annual figures. Both land inside the plausible
    range for the Canadian dollar, which is why nothing would have caught
    them downstream.
    """
    out: dict[int, set[str]] = defaultdict(set)
    for day, _ in obs:
        out[int(day[:4])].add(day[5:7])
    return out


def write(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {path.relative_to(ROOT)}  {len(rows)} rows")


def main() -> None:
    print("Bank of Canada (Valet)")
    raw = {name: fetch(name) for name in SERIES}
    series = {name: by_year(obs) for name, obs in raw.items()}
    months = {name: months_of(obs) for name, obs in raw.items()}
    running = max(int(d[:4]) for obs in raw.values() for d, _ in obs)

    def avg(name, year, nd=2):
        """The annual mean, or blank when the year is not wholly covered.

        The running year is the one exception: it is incomplete by
        definition and the plate hatches it, so it is emitted with its
        month count beside it rather than withheld.
        """
        vals = series[name].get(year)
        if not vals:
            return ""
        if len(months[name][year]) < 12 and year < running:
            return ""
        return round(statistics.fmean(vals), nd)

    def covered(name, year):
        return len(months[name].get(year, ()))

    def last(name, year, nd=2):
        vals = series[name].get(year)
        return round(vals[-1], nd) if vals else ""

    rows = []
    for year in range(Y0, Y1 + 1):
        rows.append([year,
                     last("target_rate", year), avg("target_rate", year),
                     avg("overnight", year),
                     avg("yield_2y", year), avg("yield_10y", year),
                     last("yield_10y", year)])
    write(DATA / "markets" / "rates_from_boc.csv",
          ["year", "target_rate_eoy", "target_rate_avg", "overnight_avg",
           "yield_2y_avg", "yield_10y_avg", "yield_10y_eoy"], rows)

    # Two columns, never one: see the module docstring.
    rows = []
    for year in range(Y0, Y1 + 1):
        rows.append([year,
                     avg("usdcad_noon", year, 4), covered("usdcad_noon", year),
                     avg("usdcad_daily", year, 4), covered("usdcad_daily", year)])
    write(DATA / "markets" / "usdcad_from_boc.csv",
          ["year", "usd_cad_noon_avg", "noon_months",
           "usd_cad_daily_avg", "daily_months"], rows)


if __name__ == "__main__":
    main()
