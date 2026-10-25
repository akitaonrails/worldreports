#!/usr/bin/env python3
"""Refresh the OECD-based series into review sidecars.

Usage:  python3 -I fetch/fetch_oecd.py      (or: make C=australia fetch)

Three OECD dataflows, three different jobs:

  DSD_NASEC10@DF_TABLE11  Annual government expenditure by function
                          (COFOG). Australia files general government
                          (S13) expenditure in national currency; the
                          share of GDP is computed here against ABS
                          calendar-year GDP at current prices because the
                          OECD slice carries no percent-of-GDP unit for
                          Australia. The national GFS COFOG table (fiscal
                          years, 2015-16 onwards) is the cross-check.
  DSD_STES@DF_FINMARK     Long-term (10-year) government bond yield,
                          monthly; annualised as the MEAN of the twelve
                          months, which is what the spine's "annual
                          average" means.
  DSD_EARNINGS@MW_CURP    The statutory national minimum wage in AUD per
                          week; converted to US$ per month at the annual
                          average exchange rate (World Bank PA.NUS.FCRF,
                          the same series the currency panel uses).

The RBA publishes the cash rate and lending rates itself, but every path
on www.rba.gov.au answers HTTP 403 to this network (see DISCOVERY.md).
The policy rate therefore comes from the BIS central-bank policy rates
dataset in fetch_markets.py, and the lending-rate panel is recorded as
pending in SOURCES.yaml rather than filled with a different statistic.
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _sdmx import OECD, FetchError, get  # noqa: E402

COFOG_GROUPS = {
    # spine group -> OECD COFOG codes (top-level divisions)
    "social_protection": ("GF10",),
    "health": ("GF07",),
    "education": ("GF09",),
    "general_public_services": ("GF01",),
    "economic_affairs": ("GF04",),
    "defence_public_order": ("GF02", "GF03"),
    "other": ("GF05", "GF06", "GF08"),
}


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    print(f"  wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def oecd_rows(flow: str, key: str, start: str) -> list[dict]:
    url = (f"{OECD}/data/{flow}/{key}?startPeriod={start}"
           f"&format=csvfilewithlabels")
    body = get(url, accept="text/csv")
    text = body.decode("utf-8-sig", "replace")
    if not text.startswith("STRUCTURE,"):
        raise FetchError(f"OECD {flow}: not a labelled CSV")
    return list(csv.DictReader(io.StringIO(text)))


def gdp_calendar() -> dict[int, float]:
    """ABS calendar-year nominal GDP, AUD million (same concept, official)."""
    path = DATA / "macro" / "ana_quarterly_from_abs.csv"
    if not path.exists():
        raise FetchError(f"{path.name} missing: run fetch_abs.py first")
    q: dict[tuple[int, int], float] = {}
    for r in csv.DictReader(path.open(encoding="utf-8")):
        q[(int(r["year"]), int(r["period"][-1]))] = float(
            r["gdp_current_aud_mn"])
    out = {}
    for y in range(2006, 2027):
        parts = [(y, 1), (y, 2), (y, 3), (y, 4)]
        if all(p in q for p in parts):
            out[y] = sum(q[p] for p in parts)
    return out


def cofog() -> list[dict]:
    key = "A.AUS.S13" + "." * 10
    rows = oecd_rows("OECD.SDD.NAD,DSD_NASEC10@DF_TABLE11", key, "2006")
    gdp = gdp_calendar()
    # TRANSACTION 'OTE' is total expenditure per function; EXPENDITURE is
    # the COFOG division. Both are needed or the rows double-count.
    keep = [r for r in rows
            if r.get("TRANSACTION") == "OTE"
            and r.get("ACCOUNTING_ENTRY") == "D"
            and r.get("UNIT_MEASURE") == "XDC"]
    if not keep:
        raise FetchError("OECD COFOG: no OTE/accrual/National-currency rows")
    by_year: dict[int, dict[str, float]] = {}
    for r in keep:
        code = r.get("EXPENDITURE")
        try:
            v = float(r["OBS_VALUE"])
        except (KeyError, ValueError):
            continue
        by_year.setdefault(int(r["TIME_PERIOD"]), {})[code] = v
    out = []
    for y in sorted(by_year):
        if y not in gdp:
            continue
        groups = {}
        for name, codes in COFOG_GROUPS.items():
            groups[name] = sum(by_year[y].get(c, 0.0) for c in codes)
        # OECD reports millions of AUD; GDP is in AUD million too.
        row = {"year": y, "gdp_aud_mn": round(gdp[y], 1)}
        for name, v in groups.items():
            row[f"{name}_aud_mn"] = round(v, 1)
            row[f"{name}_pct_gdp"] = round(100 * v / gdp[y], 2)
        row["total_expenditure_pct_gdp"] = round(
            100 * sum(groups.values()) / gdp[y], 2)
        out.append(row)
    if not out or out[-1]["year"] < 2023:
        raise FetchError(f"OECD COFOG: coverage ends "
                         f"{out[-1]['year'] if out else None}")
    last = out[-1]
    if not 6 <= last["social_protection_pct_gdp"] <= 18:
        raise FetchError(f"OECD COFOG: social protection "
                         f"{last['social_protection_pct_gdp']}% of GDP")
    print(f"  OECD COFOG: {out[0]['year']}-{out[-1]['year']}")
    return out


def bond_10y() -> list[dict]:
    rows = oecd_rows("OECD.SDD.STES,DSD_STES@DF_FINMARK", "AUS" + "." * 8,
                     "2005-01")
    monthly: dict[int, list[float]] = {}
    for r in rows:
        if (r.get("MEASURE") != "IRLT" or r.get("FREQ") != "M"
                or not r.get("OBS_VALUE")):
            continue
        y = int(r["TIME_PERIOD"][:4])
        monthly.setdefault(y, []).append(float(r["OBS_VALUE"]))
    out = []
    for y in sorted(monthly):
        vals = monthly[y]
        if len(vals) < 12:
            continue                     # a partial year is not a year
        out.append({"year": y, "bond_10y_pct_annual_avg":
                    round(sum(vals) / 12, 2),
                    "months_observed": len(vals)})
    if not out:
        raise FetchError("OECD FINMARK: no IRLT rows")
    print(f"  OECD long-term rate: {out[0]['year']}-{out[-1]['year']}")
    return out


def minimum_wage() -> list[dict]:
    rows = oecd_rows("OECD.ELS.SAE,DSD_EARNINGS@MW_CURP", "AUS" + "." * 6,
                     "2005")
    per_year: dict[int, float] = {}
    for r in rows:
        if not r.get("OBS_VALUE"):
            continue
        if r.get("MEASURE") != "SM_WG" or r.get("PAY_PERIOD") != "W":
            continue
        per_year[int(r["TIME_PERIOD"])] = float(r["OBS_VALUE"])
    fx = {}
    fx_path = DATA / "world" / "wb_from_worldbank.csv"
    if not fx_path.exists():
        raise FetchError("run fetch_comparables.py first (needs aud_per_usd)")
    for r in csv.DictReader(fx_path.open(encoding="utf-8")):
        if r.get("aud_per_usd"):
            fx[int(r["year"])] = float(r["aud_per_usd"])
    out = []
    for y in sorted(per_year):
        weekly = per_year[y]
        monthly_aud = weekly * 52 / 12
        row = {"year": y, "minimum_wage_aud_week": round(weekly, 2),
               "minimum_wage_aud_month": round(monthly_aud, 2)}
        if y in fx:
            row["aud_per_usd"] = round(fx[y], 4)
            row["minimum_wage_usd_month"] = round(monthly_aud / fx[y], 2)
        out.append(row)
    if not out:
        raise FetchError("OECD MW_CURP: no statutory minimum wage rows")
    print(f"  OECD minimum wage: {out[0]['year']}-{out[-1]['year']}")
    return out


def main() -> None:
    try:
        print("OECD — COFOG, long-term rate, statutory minimum wage")
        write_csv(DATA / "spending" / "cofog_from_oecd.csv",
                  ["year", "gdp_aud_mn"] +
                  [f"{k}_aud_mn" for k in COFOG_GROUPS] +
                  [f"{k}_pct_gdp" for k in COFOG_GROUPS] +
                  ["total_expenditure_pct_gdp"], cofog())
        write_csv(DATA / "markets" / "bond_10y_from_oecd.csv",
                  ["year", "bond_10y_pct_annual_avg", "months_observed"],
                  bond_10y())
        write_csv(DATA / "people" / "minimum_wage_from_oecd.csv",
                  ["year", "minimum_wage_aud_week", "minimum_wage_aud_month",
                   "aud_per_usd", "minimum_wage_usd_month"], minimum_wage())
    except FetchError as e:
        print(f"fetch error: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
