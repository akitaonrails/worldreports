#!/usr/bin/env python3
"""Refresh the ECB-backed series into sidecar CSVs.

Usage:  python3 scripts/fetch_ecb.py

France has no monetary policy of its own: the policy rate in plate 05 is the
ECB's, and the exchange rate is the ECB reference rate. Both come from the ECB
Data Portal SDMX API, which needs no key and is the publisher of record.

  EXR  D.USD.EUR.SP00.A              daily USD per EUR reference rate
  FM   D.U2.EUR.4F.KR.DFR.LEV        deposit facility rate (level, daily)
  FM   D.U2.EUR.4F.KR.MRR_FR.LEV     main refinancing operations, fixed rate

The deposit facility rate is the one that has actually steered money-market
rates since 2014 — through the whole negative-rate period the MRO sat at zero
while the DFR went to −0.50 — so the plate draws the DFR and keeps the MRO as
a second column rather than splicing a single "the policy rate" line.

  SUP  Q.FR.W0._Z.I7000._T.SII._Z._Z._Z.PCT.C
                                     non-performing loans ratio of the
                                     significant institutions the ECB
                                     supervises in France, quarterly

Outputs: data/macro/eurusd_from_ecb.csv, data/macro/policy_rate_from_ecb.csv,
data/credit/npl_from_ecb.csv
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


NPL = ("SUP", "Q.FR.W0._Z.I7000._T.SII._Z._Z._Z.PCT.C")


def npl_q4() -> dict[int, float]:
    """The supervisory NPL ratio at each year end (the Q4 reading).

    A ratio of a stock, so the year's value is its December reading, not
    an average of the quarters. The series starts in 2015, with the SSM's
    harmonised reporting.
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "ecb_npl.csv"
    if cache_file.exists():
        text = cache_file.read_text()
    else:
        flow, key = NPL
        url = BASE.format(flow=flow, key=key) + "?format=csvdata"
        with urllib.request.urlopen(url, timeout=120) as r:
            text = r.read().decode("utf-8")
        if "TIME_PERIOD" not in text:
            raise RuntimeError(f"ecb {flow}/{key}: unexpected payload")
        cache_file.write_text(text)
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        period, raw = row.get("TIME_PERIOD") or "", row.get("OBS_VALUE")
        if period.endswith("-Q4") and raw not in (None, "", "NaN"):
            out[int(period[:4])] = float(raw)
    # A known year end, so a changed definition or an empty answer fails
    # here instead of landing in the sidecar.
    if abs(out.get(2019, 0) - 2.49) > 0.05:
        raise SystemExit(f"SUP NPL ratio 2019-Q4 is {out.get(2019)}, "
                         "expected 2.49; nothing written")
    return out


def main() -> None:
    print("Fetching ECB series...")
    fx = by_year(fetch("eurusd"))
    dfr = by_year(fetch("dfr"))
    mro = by_year(fetch("mro"))

    lines = ["year,avg,eop"]
    for y in range(Y0, Y1 + 1):
        vals = fx.get(y, [])
        if not vals:
            lines.append(f"{y},,")
            continue
        avg = sum(v for _, v in vals) / len(vals)
        lines.append(f"{y},{avg:.4f},{vals[-1][1]:.4f}")
    (DATA / "macro" / "eurusd_from_ecb.csv").write_text("\n".join(lines) + "\n")
    print("  -> data/macro/eurusd_from_ecb.csv")

    def eop(series: dict[int, list[tuple[date, float]]], year: int) -> str:
        vals = series.get(year, [])
        return f"{vals[-1][1]:.2f}" if vals else ""

    lines = ["year,dfr,mro"]
    for y in range(Y0, Y1 + 1):
        lines.append(f"{y},{eop(dfr, y)},{eop(mro, y)}")
    (DATA / "macro" / "policy_rate_from_ecb.csv").write_text(
        "\n".join(lines) + "\n")
    print("  -> data/macro/policy_rate_from_ecb.csv")

    npl = npl_q4()
    lines = ["year,npl_ssm_pct"]
    for y in range(Y0, Y1 + 1):
        lines.append(f"{y},{npl[y]:.2f}" if y in npl else f"{y},")
    (DATA / "credit" / "npl_from_ecb.csv").write_text("\n".join(lines) + "\n")
    print("  -> data/credit/npl_from_ecb.csv")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
