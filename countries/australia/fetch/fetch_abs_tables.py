#!/usr/bin/env python3
"""Refresh Australia's ABS spreadsheet releases into review sidecars.

Usage:  python3 -I fetch/fetch_abs_tables.py      (or: make C=australia fetch)

Three ABS publications are not on the SDMX gateway and are published only
as Excel data cubes on www.abs.gov.au:

  Government Finance Statistics, Australia (cat. 5512.0), annual
      Table 1  revenue, expenses, interest, net operating balance and
               gross fixed capital formation, all levels of government
      Table 4  expenses by purpose (COFOG), all levels of government
      The whole publication is on a FISCAL year (July-June) and its
      current vintage reaches back only to 2015-16. The fiscal chapter's
      canonical series is the IMF general-government layer (calendar-year
      labels, its own fiscal-year basis); this is the national line,
      staged as fiscal years and never drawn on a calendar-year axis
      without saying so.

  Recorded Crime - Victims, Australia (cat. 4510.0), annual calendar year
      Table 1  homicide victims and the victimisation rate per 100,000
               the ABS itself publishes.

  Causes of Death, Australia (cat. 3303.0), annual registration year
      Table 1.2  underlying cause, persons, 2015-2024, one vintage:
                 total deaths, intentional self-harm, COVID-19.

The GFS ratios use nominal GDP for the matching fiscal year (the four
quarters ending in June), read from the national-accounts sidecar that
fetch_abs.py writes. Run fetch_abs.py first; this script refuses to guess
a denominator.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = Path(__file__).resolve().parent / "cache"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _sdmx import FetchError, get  # noqa: E402

GFS_202425 = ("https://www.abs.gov.au/statistics/economy/government/"
              "government-finance-statistics-annual/2024-25/")
GFS_TABLE1 = GFS_202425 + "55120DO021_202425.xlsx"
CRIME = ("https://www.abs.gov.au/statistics/people/crime-and-justice/"
         "recorded-crime-victims/2025/"
         "1.%20Victims%20of%20crime%2C%20Australia%20%28Tables%201%20to%208%29"
         ".xlsx")
HIES = ("https://www.abs.gov.au/statistics/economy/finance/"
        "household-income-and-wealth-australia/2019-20/"
        "1.%20Household%20income%20and%20income%20distribution%2C%20"
        "Australia.xlsx")
CAUSES = ("https://www.abs.gov.au/statistics/health/causes-death/"
          "causes-death-australia/2024/"
          "2024_01%20Underlying%20causes%20of%20death%20%28Australia%29.xlsx")


def workbook(url: str, name: str):
    import io

    import openpyxl

    body = get(url, accept="application/vnd.openxmlformats-officedocument"
                          ".spreadsheetml.sheet")
    if body[:2] != b"PK":
        raise FetchError(f"{name}: not an xlsx (magic {body[:2]!r})")
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / name).write_bytes(body)          # reviewable, not committed
    return openpyxl.load_workbook(io.BytesIO(body), read_only=True,
                                  data_only=True)


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    print(f"  wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def fiscal_gdp() -> dict[int, float]:
    """{fiscal year end: nominal GDP for July-June}, AUD million.

    FY2015-16 is 2015Q3 + 2015Q4 + 2016Q1 + 2016Q2. The quarters come from
    the national-accounts sidecar, which is the same publisher's series on
    the same concept (current prices, original terms).
    """
    path = DATA / "macro" / "ana_quarterly_from_abs.csv"
    if not path.exists():
        raise FetchError(f"{path.name} missing: run fetch_abs.py first")
    q: dict[tuple[int, int], float] = {}
    for r in csv.DictReader(path.open(encoding="utf-8")):
        q[(int(r["year"]), int(r["period"][-1]))] = float(
            r["gdp_current_aud_mn"])
    out = {}
    for end_year in range(2006, 2027):
        parts = [(end_year - 1, 3), (end_year - 1, 4), (end_year, 1),
                 (end_year, 2)]
        if all(p in q for p in parts):
            out[end_year] = round(sum(q[p] for p in parts), 1)
    return out


def _years(row) -> list[str]:
    return [str(c) for c in row if c not in (None, "")]


def gfs() -> tuple[list[dict], list[dict]]:
    wb = workbook(GFS_TABLE1, "gfs_5512_table1_202425.xlsx")
    ws = wb["Table_1"]
    rows = list(ws.iter_rows(min_row=5, max_row=ws.max_row, max_col=12,
                             values_only=True))
    header = rows[0]
    years = _years(header)
    if len(years) != 10 or years[0] != "2015-16" or years[-1] != "2024-25":
        raise FetchError(f"GFS Table 1: unexpected years {years}")
    want = {
        "Total GFS revenue": "revenue_aud_mn",
        "Total GFS expenses": "expenses_aud_mn",
        "GFS Net operating balance": "net_operating_balance_aud_mn",
        "Interest expenses n.e.c.": "interest_aud_mn",
        "Gross fixed capital formation": "gfcf_aud_mn",
    }
    got: dict[str, list[str]] = {}
    for r in rows[1:]:
        label = str(r[0] or "").strip()
        if label in want and want[label] not in got:
            vals = [v for v in r[1:11]]
            if len([v for v in vals if v not in (None, "")]) != 10:
                raise FetchError(f"GFS Table 1: {label} has blank cells")
            got[want[label]] = vals
    missing = set(want.values()) - set(got)
    if missing:
        raise FetchError(f"GFS Table 1: rows not found {sorted(missing)}")

    gdp = fiscal_gdp()
    out = []
    for i, fy in enumerate(years):
        end = 2000 + int(fy[-2:])
        if end not in gdp:
            continue
        row = {"fiscal_year": fy, "fiscal_year_end": end,
               "gdp_fy_aud_mn": gdp[end]}
        for col, vals in got.items():
            row[col] = round(float(vals[i]), 1)
        row["revenue_pct_gdp"] = round(100 * row["revenue_aud_mn"] / gdp[end], 2)
        row["expenses_pct_gdp"] = round(
            100 * row["expenses_aud_mn"] / gdp[end], 2)
        row["net_operating_balance_pct_gdp"] = round(
            100 * row["net_operating_balance_aud_mn"] / gdp[end], 2)
        row["interest_pct_gdp"] = round(100 * row["interest_aud_mn"] / gdp[end], 2)
        out.append(row)

    # COFOG: the same publication, Table 4, all levels of government.
    ws = wb["Table_4"]
    rows = list(ws.iter_rows(min_row=5, max_row=ws.max_row, max_col=12,
                             values_only=True))
    functions: dict[str, list[float]] = {}
    published_total: list[float] | None = None
    for r in rows[1:]:
        label = " ".join(str(r[0] or "").split())
        if not label:
            continue
        vals = r[1:11]
        if len([v for v in vals if v not in (None, "")]) != 10:
            continue
        if label.lower().startswith("total expenses"):
            published_total = [float(v) for v in vals]
            continue
        functions[label.lower()] = [float(v) for v in vals]

    # The ABS prints the ten COFOG divisions plus Transport as its own row
    # (COFOG 04.5, normally inside Economic affairs). The eleven rows add
    # up to the published Total Expenses, which is the check below; the
    # spine's "economic affairs" group therefore carries both.
    groups_of = {
        "general public services": ["general public services"],
        "defence": ["defence"],
        "public order and safety": ["public order and safety"],
        "economic affairs": ["economic affairs", "transport"],
        "environmental protection": ["environmental protection"],
        "housing and community amenities": ["housing and community amenities"],
        "health": ["health"],
        "recreation": ["recreation, culture and religion"],
        "education": ["education"],
        "social protection": ["social protection"],
    }
    missing = [k for k in groups_of for v in [k]
               if not any(f in functions for f in groups_of[v])]
    if missing or published_total is None:
        raise FetchError(f"GFS Table 4: COFOG rows missing {missing} "
                         f"(total row {published_total is not None})")
    for i in range(10):
        summed = round(sum(v[i] for v in functions.values()), 0)
        if abs(summed - published_total[i]) > 2:
            raise FetchError(f"GFS Table 4: divisions sum to {summed}, "
                             f"published total {published_total[i]} "
                             f"for {years[i]}")

    def row_for(name: str) -> list[float]:
        return [sum(functions[f][i] for f in groups_of[name])
                for i in range(10)]

    cofog = []
    for i, fy in enumerate(years):
        end = 2000 + int(fy[-2:])
        if end not in gdp:
            continue
        groups = {
            "social_protection": row_for("social protection")[i],
            "health": row_for("health")[i],
            "education": row_for("education")[i],
            "general_public_services": row_for(
                "general public services")[i],
            "economic_affairs": row_for("economic affairs")[i],
            "defence_public_order": (row_for("defence")[i]
                                     + row_for("public order and safety")[i]),
            "other": (row_for("environmental protection")[i]
                      + row_for("housing and community amenities")[i]
                      + row_for("recreation")[i]),
        }
        row = {"fiscal_year": fy, "fiscal_year_end": end,
               "gdp_fy_aud_mn": gdp[end]}
        for k, v in groups.items():
            row[f"{k}_aud_mn"] = round(v, 1)
            row[f"{k}_pct_gdp"] = round(100 * v / gdp[end], 2)
        row["total_expenses_aud_mn"] = round(sum(groups.values()), 1)
        cofog.append(row)

    total = cofog[-1]
    if not 8 <= total["social_protection_pct_gdp"] <= 16:
        raise FetchError(f"GFS COFOG: social protection "
                         f"{total['social_protection_pct_gdp']}% of GDP")
    return out, cofog


def crime() -> list[dict]:
    wb = workbook(CRIME, "recorded_crime_victims_table1_2025.xlsx")
    ws = wb["Table 1"]
    rows = list(ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=34,
                             values_only=True))
    import re as _re

    years: list[int] = []
    for c in rows[4][1:]:
        if c in (None, ""):
            continue
        years.append(int(_re.match(r"(\d{4})", str(c)).group(1)))
    if years[0] != 1993 or years[-1] != 2025 or len(years) != 33:
        raise FetchError(f"crime: unexpected year header {years[:3]}..."
                         f"{years[-1]} ({len(years)})")
    section = "count"
    counts: dict[int, int] = {}
    rates: dict[int, float] = {}
    for r in rows:
        cells = [str(c or "").strip() for c in r[:3]]
        if any(c.lower().startswith("victimisation rate") for c in cells):
            section = "rate"
            continue
        if str(r[0] or "").strip().startswith("Homicide"):
            for y, v in zip(years, r[1:1 + len(years)]):
                if v in (None, "", "np", "—"):
                    continue
                if section == "rate":
                    rates[y] = float(v)
                else:
                    counts[y] = int(float(v))
    if counts.get(2024) != 448 or rates.get(2006) != 2.7:
        raise FetchError(f"crime: pinned values moved "
                         f"({counts.get(2024)}, {rates.get(2006)})")
    return [{"year": y, "homicide_count": counts[y],
             "homicide_per_100k": round(rates[y], 2)}
            for y in sorted(set(counts) & set(rates))]


def causes() -> list[dict]:
    wb = workbook(CAUSES, "causes_of_death_2024_table1_2.xlsx")
    ws = wb["Table 1.2"]
    rows = list(ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=40,
                             values_only=True))
    hdr = rows[4]
    years: list[int] = []
    col_of: dict[int, int] = {}
    for i, c in enumerate(hdr):
        if c not in (None, "") and str(c).isdigit():
            years.append(int(c))
            col_of[int(c)] = i + 2          # Persons is the third sub-column
    total: dict[int, float] = {}
    suicide: dict[int, float] = {}
    covid: dict[int, float] = {}
    for r in rows[5:]:
        label = " ".join(str(r[0] or "").split())
        target = None
        if label.startswith("Total deaths"):
            target = total
        elif label.startswith("Intentional self-harm (X60-X84"):
            target = suicide
        elif label.startswith("COVID-19 (U07.1"):
            target = covid
        if target is None:
            continue
        for y in years:
            if y in target:
                continue
            v = r[col_of[y]]
            if v in (None, "", "—", "np"):
                continue
            target[y] = float(v)
    if total.get(2024) != 187268:
        raise FetchError(f"causes: 2024 total deaths {total.get(2024)}")
    out = []
    for y in sorted(set(total) | set(suicide) | set(covid)):
        out.append({"year": y, "deaths_underlying": total.get(y, ""),
                    "suicide_deaths": suicide.get(y, ""),
                    "covid_deaths": covid.get(y, "")})
    return out


def gini() -> list[dict]:
    """Gini of equivalised disposable household income, HIES 2019-20.

    The survey runs every two years and ABS labels each observation by
    the financial year it covers (2007-08 ... 2019-20). The CSV carries
    the financial-year label AND the calendar year the financial year
    ENDS in, because the plate's axis is calendar years and a reader must
    not have to guess which convention the dot is on.
    """
    wb = workbook(HIES, "hies_2019_20_table1_1.xlsx")
    ws = wb["Table 1.1"]
    rows = list(ws.iter_rows(min_row=1, max_row=60, max_col=10,
                             values_only=True))
    years = [str(c) for c in rows[4] if c not in (None, "")]
    fy = [y for y in years if "\u2013" in y or "-" in y]
    for r in rows:
        if str(r[0] or "").strip().lower().startswith("gini coefficient"):
            vals = r[2:2 + len(fy)]
            out = []
            for label, v in zip(fy, vals):
                if v in (None, ""):
                    continue
                end = 2000 + int(str(label).split("\u2013")[-1][-2:])
                out.append({"financial_year": label, "year": end,
                            "gini_hies": round(float(v) * 100, 1)})
            print(f"  HIES Gini: {len(out)} survey years")
            return out
    raise FetchError("HIES: Gini row not found")


def main() -> None:
    try:
        print("ABS tables — Government Finance Statistics (fiscal years)")
        fiscal, cofog = gfs()
        write_csv(DATA / "fiscal" / "gfs_national_from_abs.csv",
                  ["fiscal_year", "fiscal_year_end", "gdp_fy_aud_mn",
                   "revenue_aud_mn", "expenses_aud_mn",
                   "net_operating_balance_aud_mn", "interest_aud_mn",
                   "gfcf_aud_mn", "revenue_pct_gdp", "expenses_pct_gdp",
                   "net_operating_balance_pct_gdp", "interest_pct_gdp"],
                  fiscal)
        write_csv(DATA / "spending" / "cofog_national_from_abs.csv",
                  ["fiscal_year", "fiscal_year_end", "gdp_fy_aud_mn",
                   "social_protection_pct_gdp", "health_pct_gdp",
                   "education_pct_gdp", "general_public_services_pct_gdp",
                   "economic_affairs_pct_gdp", "defence_public_order_pct_gdp",
                   "other_pct_gdp", "total_expenses_aud_mn"],
                  cofog)
        print("ABS tables — Recorded Crime, Victims")
        write_csv(DATA / "security" / "homicide_from_abs.csv",
                  ["year", "homicide_count", "homicide_per_100k"], crime())
        print("ABS tables — Household Income and Wealth (Gini)")
        write_csv(DATA / "people" / "gini_from_abs.csv",
                  ["financial_year", "year", "gini_hies"], gini())
        print("ABS tables — Causes of Death (2024 vintage)")
        write_csv(DATA / "mortality" / "causes_from_abs.csv",
                  ["year", "deaths_underlying", "suicide_deaths",
                   "covid_deaths"], causes())
    except FetchError as e:
        print(f"fetch error: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
