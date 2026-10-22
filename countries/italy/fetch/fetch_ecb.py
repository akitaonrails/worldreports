#!/usr/bin/env python3
"""Refresh the ECB-backed series into sidecar CSVs.

Usage:  python3 -I countries/italy/fetch/fetch_ecb.py

Italy has no monetary policy of its own: the policy rate in the plate is the
ECB's, and the exchange rate is the ECB reference rate. Both come from the
ECB Data Portal SDMX API, which needs no key and is the publisher of record.

  EXR  D.USD.EUR.SP00.A              daily USD per EUR reference rate
  FM   D.U2.EUR.4F.KR.DFR.LEV        deposit facility rate (level, daily)
  FM   D.U2.EUR.4F.KR.MRR_FR.LEV     main refinancing operations, fixed rate

The deposit facility rate is the one that has actually steered money-market
rates since 2014 — through the whole negative-rate period the MRO sat at zero
while the DFR went to −0.50 — so the plate draws the DFR and keeps the MRO as
a second column rather than splicing a single "the policy rate" line.

Outputs: data/markets/eurusd_from_ecb.csv, data/markets/policy_rate_from_ecb.csv
"""
from __future__ import annotations

import csv
import io
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

BASE = "https://data-api.ecb.europa.eu/service/data/{flow}/{key}"
Y0, Y1 = 2006, 2026

SERIES = {
    "eurusd": ("EXR", "D.USD.EUR.SP00.A"),
    "dfr": ("FM", "D.U2.EUR.4F.KR.DFR.LEV"),
    "mro": ("FM", "D.U2.EUR.4F.KR.MRR_FR.LEV"),
}


def fetch(name: str) -> list[tuple[date, float]]:
    """One daily ECB series as [(date, value)], chronologically.

    The portal serves CSV with TIME_PERIOD as ISO yyyy-mm-dd, which sorts
    correctly as a string — but it is parsed to a real date anyway, because
    the whole point of the year-end value is that it is the LAST observation
    of the year and not merely the last row the gateway happened to send.
    """
    CACHE.mkdir(exist_ok=True)
    flow, key = SERIES[name]
    cache_file = CACHE / f"ecb_{name}.csv"
    if cache_file.exists():
        text = cache_file.read_text()
    else:
        url = (BASE.format(flow=flow, key=key)
               + f"?format=csvdata&startPeriod={Y0}-01-01")
        last = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    text = r.read().decode("utf-8")
                if "TIME_PERIOD" not in text:
                    raise ValueError("unexpected payload")
                cache_file.write_text(text)
                break
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"ecb {flow}/{key}: {last}")
    return parse(text)


def parse(text: str) -> list[tuple[date, float]]:
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        period, raw = row.get("TIME_PERIOD"), row.get("OBS_VALUE")
        if not period or raw in (None, "", "NaN"):
            continue
        try:
            out.append((date.fromisoformat(period), float(raw)))
        except ValueError:
            continue
    out.sort()
    return out


def by_year(obs: list[tuple[date, float]]) -> dict[int, list[tuple[date, float]]]:
    out: dict[int, list[tuple[date, float]]] = {}
    for d, v in obs:
        out.setdefault(d.year, []).append((d, v))
    for vals in out.values():
        vals.sort()
    return out


def months_of(obs: list[tuple[date, float]]) -> dict[int, set[int]]:
    """Which months of each year the series actually covers.

    The reason an annual average needs this: a mean over whatever rows the
    year happens to carry would be a partial average presented as an annual
    figure (the same trap Canada's fetcher guards against with its
    `*_months` columns). A year with incomplete coverage gets a blank
    average and its month count beside it — except the running year, which
    is incomplete by definition and is emitted with its month count so the
    plate can hatch it.
    """
    out: dict[int, set[int]] = {}
    for d, _ in obs:
        out.setdefault(d.year, set()).add(d.month)
    return out


def write(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    print(f"  -> {path.relative_to(ROOT)}  {len(lines) - 1} rows")


def main() -> None:
    print("Fetching ECB series...")
    fx_raw = fetch("eurusd")
    dfr = by_year(fetch("dfr"))
    mro = by_year(fetch("mro"))
    fx = by_year(fx_raw)
    fx_months = months_of(fx_raw)
    running = max(d.year for d, _ in fx_raw)

    # Spot checks against the discovery report (2026-10-22):
    #   EUR/USD 2026-10-21 = 1.1234; DFR currently 2.50 (raised during 2026
    #   from the 2.00 2025 year-end — the 2026 reading is a live level, not
    #   a year-end, and the plate must label it as such).
    fx_check = {d: v for d, v in fx_raw}.get(date(2026, 10, 21))
    assert fx_check == 1.1234, f"EUR/USD 2026-10-21 reads {fx_check}"
    dfr_latest = dfr[max(dfr)][-1][1]
    assert dfr_latest == 2.50, f"latest DFR reads {dfr_latest}"
    print(f"  spot checks ok: EUR/USD 2026-10-21 = {fx_check}, "
          f"DFR latest = {dfr_latest}")

    lines = ["year,avg,avg_months,eop"]
    for y in range(Y0, Y1 + 1):
        vals = fx.get(y, [])
        if not vals:
            lines.append(f"{y},,0,")
            continue
        months = len(fx_months[y])
        if months == 12 or y == running:
            avg = sum(v for _, v in vals) / len(vals)
            avg_s = f"{avg:.4f}"
        else:
            avg_s = ""
        lines.append(f"{y},{avg_s},{months},{vals[-1][1]:.4f}")
    write(DATA / "markets" / "eurusd_from_ecb.csv", lines)

    def eop(series: dict[int, list[tuple[date, float]]], year: int) -> str:
        vals = series.get(year, [])
        return f"{vals[-1][1]:.2f}" if vals else ""

    # Year-end levels. The running year's "eop" is the latest daily reading —
    # a live level, not a year-end (DFR 2.50 at fetch time, after the 2026
    # hikes from the 2.00 of end-2025); the plate labels it as such.
    lines = ["year,dfr,mro"]
    for y in range(Y0, Y1 + 1):
        lines.append(f"{y},{eop(dfr, y)},{eop(mro, y)}")
    write(DATA / "markets" / "policy_rate_from_ecb.csv", lines)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
