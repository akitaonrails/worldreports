#!/usr/bin/env python3
"""Fetch the UK's harmonised household-credit and bad-loan series.

BIS total credit is quarterly.  The publication sidecar keeps Q4 as the
annual stock reading, plus the annual mean and the number of observations;
the current year therefore has a blank Q4 rather than pretending Q1 is a
year-end stock.  The World Bank indicator is the IMF Financial Soundness
Indicator for bank non-performing loans.
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIS = ("https://stats.bis.org/api/v2/data/dataflow/BIS/WS_TC/2.0/"
       "Q.GB.H.A.M.770.A?format=csv")
WB = ("https://api.worldbank.org/v2/country/GBR/indicator/FB.AST.NPER.ZS"
      "?format=json&per_page=100&date=2006:2026")
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def household_credit() -> list[tuple[int, str, str, int]]:
    rows = csv.DictReader(io.StringIO(get(BIS).decode("utf-8-sig")))
    by_year: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for row in rows:
        period = row["TIME_PERIOD"]
        if not period.startswith(tuple(str(y) for y in range(2006, 2027))):
            continue
        year, quarter = period.split("-Q")
        by_year[int(year)].append((int(quarter), float(row["OBS_VALUE"])))
    out = []
    for year, values in sorted(by_year.items()):
        values.sort()
        q4 = next((v for q, v in values if q == 4), None)
        out.append((year, "" if q4 is None else f"{q4:.1f}",
                    f"{sum(v for _, v in values) / len(values):.1f}",
                    len(values)))
    assert dict((y, q4) for y, q4, _, _ in out)[2024] == "74.9"
    assert dict((y, q4) for y, q4, _, _ in out)[2025] == "73.5"
    assert dict((y, avg) for y, _, avg, _ in out)[2026] == "72.6"
    return out


def npl() -> list[tuple[int, float]]:
    payload = json.loads(get(WB))
    if not (isinstance(payload, list) and len(payload) == 2):
        raise ValueError("World Bank NPL response changed shape")
    out = sorted((int(row["date"]), float(row["value"]))
                 for row in payload[1] if row.get("value") is not None)
    values = dict(out)
    assert abs(values[2008] - 1.56) < 0.01
    assert abs(values[2025] - 0.95) < 0.01
    return out


def write() -> None:
    credit = ROOT / "data" / "credit"
    credit.mkdir(parents=True, exist_ok=True)
    with (credit / "household_credit_from_bis.csv").open(
            "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["year", "household_credit_pct_gdp_q4",
                         "household_credit_pct_gdp_qavg", "quarters"])
        writer.writerows(household_credit())
    with (credit / "npl_from_wb.csv").open(
            "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["year", "npl_pct"])
        writer.writerows((year, f"{value:.2f}") for year, value in npl())
    print("data/credit/household_credit_from_bis.csv")
    print("data/credit/npl_from_wb.csv")


if __name__ == "__main__":
    write()
