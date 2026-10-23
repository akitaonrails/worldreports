#!/usr/bin/env python3
"""Refresh the ECB-backed series into sidecar CSVs.

Usage:  python3 -I countries/portugal/fetch/fetch_ecb.py

Portugal has no monetary policy of its own: the policy rate in the markets
plate is the ECB's, and the exchange rate is the ECB reference rate. Both
come from the ECB Data Portal SDMX API, which needs no key and is the
publisher of record — the same construct as France and Spain.

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

    The reason an annual average needs this: a mean over the rows the
    gateway returns for a partially-covered year is a partial average
    presented as an annual figure. The daily EXR series has no such gap in
    the 2006–2026 window, but the running year is incomplete by definition
    and any future hole would land inside the plausible range for the euro,
    which is why nothing would have caught it. The coverage column beside
    the average is what makes the blank explainable.
    """
    out: dict[int, set[int]] = {}
    for d, _ in obs:
        out.setdefault(d.year, set()).add(d.month)
    return out


def main() -> None:
    print("Fetching ECB series...")
    fx_obs = fetch("eurusd")
    fx = by_year(fx_obs)
    fx_months = months_of(fx_obs)
    dfr = by_year(fetch("dfr"))
    mro = by_year(fetch("mro"))
    running = max(d.year for d, _ in fx_obs)

    def avg(year: int) -> str:
        """The annual mean, or blank when the year is not wholly covered.

        The running year is the one exception: it is incomplete by
        definition and the plate hatches it, so it is emitted with its
        month count beside it rather than withheld.
        """
        vals = fx.get(year, [])
        if not vals:
            return ""
        if len(fx_months[year]) < 12 and year < running:
            return ""
        return f"{sum(v for _, v in vals) / len(vals):.4f}"

    lines = ["year,avg,eop,avg_months"]
    for y in range(Y0, Y1 + 1):
        vals = fx.get(y, [])
        eop = f"{vals[-1][1]:.4f}" if vals else ""
        lines.append(f"{y},{avg(y)},{eop},{len(fx_months.get(y, ()))}")
    (DATA / "markets" / "eurusd_from_ecb.csv").parent.mkdir(
        parents=True, exist_ok=True)
    (DATA / "markets" / "eurusd_from_ecb.csv").write_text(
        "\n".join(lines) + "\n")
    print("  -> data/markets/eurusd_from_ecb.csv")

    def eop(series: dict[int, list[tuple[date, float]]], year: int) -> str:
        """The year-end level, or blank.

        A level series needs no annual average: the DFR is a administered
        rate that steps on decision dates, so the end-of-year reading IS the
        annual figure. The running-year cell is therefore the LIVE level —
        as of 2026-10-22 the DFR stands at 2.50, raised during 2026 from
        2.00 at end-2025 — not a year-end, and the plate labels it so.
        """
        vals = series.get(year, [])
        return f"{vals[-1][1]:.2f}" if vals else ""

    lines = ["year,dfr,mro"]
    for y in range(Y0, Y1 + 1):
        lines.append(f"{y},{eop(dfr, y)},{eop(mro, y)}")
    (DATA / "markets" / "policy_rate_from_ecb.csv").write_text(
        "\n".join(lines) + "\n")
    print("  -> data/markets/policy_rate_from_ecb.csv")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
