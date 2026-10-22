#!/usr/bin/env python3
"""Fetch prices and labour from the Bureau of Labor Statistics public API.

The v1 API needs no registration, which is why it is used here, but it caps a
request at 10 years and 25 requests a day — so the window is split into
decades, each cached under cache/bls/.

Series (all official BLS):
  CUUR0000SA0      CPI-U, all items, US city average, NSA index
  CUUR0000SA0L1E   CPI-U, all items less food and energy ("core")
  LNS14000000      unemployment rate, 16+, seasonally adjusted
  LNS13327709      U-6 total underutilisation, seasonally adjusted
  CES0000000001    total nonfarm payroll employment, thousands, SA

BLS publishes an annual average for the CPI index as period M13, but not for
the household-survey rates: those are averaged here from the twelve monthly
readings, which is how BLS computes its own published annual rate.

Outputs:
  data/macro/cpi_from_api.csv           year,value,core,index,core_index
  data/macro/unemployment_from_api.csv  year,value,u6,payrolls_mn,months
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "bls"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

API = "https://api.bls.gov/publicAPI/v1/timeseries/data/"

CPI, CORE = "CUUR0000SA0", "CUUR0000SA0L1E"
U3, U6, PAYROLLS = "LNS14000000", "LNS13327709", "CES0000000001"
SERIES = [CPI, CORE, U3, U6, PAYROLLS]

YEAR_FROM, YEAR_TO = 2005, 2026  # 2005 so the 2006 CPI change has a base
CHUNK = 10  # the v1 API's hard limit per request


def fetch_chunk(start: int, end: int) -> dict:
    """One decade of every series, cached. A failed fetch returns an empty
    result rather than raising: the committed CSVs stay valid without it."""
    path = CACHE / f"bls_{start}_{end}.json"
    if path.exists():
        return json.loads(path.read_text())
    body = {"seriesid": SERIES, "startyear": str(start), "endyear": str(end),
            "annualaverage": True}
    print(f"  requesting {start}-{end}")
    try:
        r = requests.post(API, json=body, timeout=120,
                          headers={"Content-Type": "application/json"})
        r.raise_for_status()
        payload = r.json()
        if payload.get("status") != "REQUEST_SUCCEEDED":
            raise ValueError(payload.get("message") or payload.get("status"))
    except Exception as e:  # noqa: BLE001
        print(f"  !! {start}-{end} failed: {type(e).__name__}: {e}")
        return {"Results": {"series": []}}
    path.write_text(json.dumps(payload))
    return payload


def collect() -> dict[str, dict[int, dict[str, float]]]:
    """{series: {year: {period: value}}} across every decade."""
    out: dict[str, dict[int, dict[str, float]]] = {s: {} for s in SERIES}
    for start in range(YEAR_FROM, YEAR_TO + 1, CHUNK):
        end = min(start + CHUNK - 1, YEAR_TO)
        payload = fetch_chunk(start, end)
        for s in payload.get("Results", {}).get("series", []):
            sid = s["seriesID"]
            for point in s.get("data", []):
                try:
                    value = float(point["value"])
                except (TypeError, ValueError):
                    continue
                out.setdefault(sid, {}).setdefault(
                    int(point["year"]), {})[point["period"]] = value
    for sid in SERIES:
        years = sorted(out.get(sid, {}))
        print(f"  [{sid}] {len(years)} years"
              + (f" {years[0]}-{years[-1]}" if years else ""))
    return out


def months(by_year: dict[str, float]) -> list[float]:
    """The monthly readings only — M13 is the annual average, not a month."""
    return [v for p, v in sorted(by_year.items())
            if p.startswith("M") and p != "M13"]


def annual_index(got: dict[int, dict[str, float]], year: int) -> float | None:
    """The annual average index: BLS's own M13 where it exists, otherwise the
    mean of the months published so far. A year with fewer than twelve months
    is a partial average and is labelled as one wherever it is drawn."""
    by_year = got.get(year)
    if not by_year:
        return None
    if "M13" in by_year:
        return by_year["M13"]
    ms = months(by_year)
    return sum(ms) / len(ms) if ms else None


def fmt(v: float | None, dec: int = 2) -> str:
    return "" if v is None else f"{v:.{dec}f}"


def main() -> None:
    print("Fetching BLS series...")
    data = collect()

    # ---- CPI: annual average index, and the change on the year before ----
    rows = []
    for y in range(YEAR_FROM + 1, YEAR_TO + 1):
        idx, prev = annual_index(data[CPI], y), annual_index(data[CPI], y - 1)
        cidx = annual_index(data[CORE], y)
        cprev = annual_index(data[CORE], y - 1)
        infl = None if not (idx and prev) else (idx / prev - 1) * 100
        core = None if not (cidx and cprev) else (cidx / cprev - 1) * 100
        rows.append(f"{y},{fmt(infl)},{fmt(core)},{fmt(idx, 3)},{fmt(cidx, 3)}")
    (DATA / "macro" / "cpi_from_api.csv").write_text(
        "year,value,core,index,core_index\n" + "\n".join(rows) + "\n")
    print("  -> data/macro/cpi_from_api.csv")

    # ---- unemployment: annual average of the monthly rates ---------------
    rows = []
    for y in range(YEAR_FROM + 1, YEAR_TO + 1):
        u3 = months(data[U3].get(y, {}))
        u6 = months(data[U6].get(y, {}))
        pay = months(data[PAYROLLS].get(y, {}))
        rows.append(
            f"{y},{fmt(sum(u3) / len(u3), 1) if u3 else ''},"
            f"{fmt(sum(u6) / len(u6), 1) if u6 else ''},"
            f"{fmt(pay[-1] / 1000, 2) if pay else ''},{len(u3)}")
    (DATA / "macro" / "unemployment_from_api.csv").write_text(
        "year,value,u6,payrolls_mn,months\n" + "\n".join(rows) + "\n")
    print("  -> data/macro/unemployment_from_api.csv")
    print("Done.")


if __name__ == "__main__":
    main()
