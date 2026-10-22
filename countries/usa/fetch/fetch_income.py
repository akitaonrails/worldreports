#!/usr/bin/env python3
"""Fetch household income, poverty and the federal minimum wage.

Income and poverty both come from the Census Bureau's Current Population
Survey Annual Social and Economic Supplement, which is the official source
for both. Everything here is taken from ONE release — the current "Poverty in
the United States" P60 report — so the income series, the official poverty
rate and the Supplemental Poverty Measure all share a vintage. Census
re-estimates history with each release, and mixing releases produces steps
that are revisions rather than events.

Two poverty measures are kept side by side on purpose, and must never be
spliced into one line:

  The OFFICIAL poverty measure (OPM) compares pre-tax money income against a
  threshold set in 1963 and moved only by the CPI. It counts no tax credit
  and no in-kind benefit, so by construction it cannot see the effect of the
  Earned Income Tax Credit, the Child Tax Credit, SNAP or housing subsidies.

  The SUPPLEMENTAL poverty measure (SPM) counts those, subtracts tax, medical
  out-of-pocket and work expenses, and varies the threshold by housing cost
  and tenure. Census publishes it from 2009.

The gap between them is the whole point. In 2021 the expanded Child Tax
Credit cut SPM child poverty to 5.1% while OPM child poverty read 15.3% —
the official measure is structurally blind to the policy, so a chart drawn
from the OPM alone would show the largest anti-poverty intervention in
decades as nothing at all.

The federal minimum wage is NOT fetched. The Department of Labor publishes it
as a list of effective dates rather than a series, and there are only four
values across this atlas, so they are written out here against the DOL's
published chart. It is recorded at 1 January and 31 December of each year
because three of the four changes took effect on 24 July, mid-year, and a
single annual figure would have to pick one and hide the other.

The Gini index is Census table H-4, household money income, all races,
from the same CPS ASEC. It carries two method breaks inside this atlas's
window, and each is printed twice in the table, once on each basis:
2013, when the income questions were redesigned, and 2017, when the
processing system was replaced. The series is therefore written as three
columns, one per basis, which overlap in the break year and are drawn as
three segments; joining them would turn two changes of method into two
jumps in inequality. It goes to a sidecar, gini_from_census.csv, and
fetch/curate.py accepts it.

Outputs:
  data/social/income.csv        year,median_household_income,...
  data/social/poverty.csv       year,opm_*,spm_*
  data/social/minimum_wage.csv  year,federal_min_jan1,federal_min_dec31,...
  data/social/gini_from_census.csv  year,gini_to_2013,gini_2013_2017,
                                    gini_from_2017   (Gini x 100)

Usage:  python3 countries/usa/fetch/fetch_income.py [--gini]
        --gini refreshes only the Gini sidecar.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import openpyxl
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "income"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

H08 = ("https://www2.census.gov/programs-surveys/cps/tables/time-series/"
       "historical-income-households/h08.xlsx")
H04 = ("https://www2.census.gov/programs-surveys/cps/tables/time-series/"
       "historical-income-households/h04.xlsx")
P60 = "https://www2.census.gov/programs-surveys/demo/tables/p60/{r}/{f}"

# The P60 report number is not a year and is not derivable from one: p60-290
# carries the 2025 data published in 2026. It is probed downward from a
# ceiling so a new release is picked up on its own, because a hardcoded
# number silently stops updating and would quietly serve last year's
# estimates as this year's.
P60_CEILING = 290 + (2026 - 2026) + 6
P60_FLOOR = 285

YEAR_FROM, YEAR_TO = 2006, 2026

# Department of Labor, Wage and Hour Division, "History of Federal Minimum
# Wage Rates Under the Fair Labor Standards Act". Rate, effective date.
MIN_WAGE = ((5.15, "1997-09-01"), (5.85, "2007-07-24"),
            (6.55, "2008-07-24"), (7.25, "2009-07-24"))


def download(name: str, url: str) -> Path | None:
    path = CACHE / name
    if path.exists():
        return path
    try:
        r = requests.get(url, timeout=180)
        r.raise_for_status()
    except Exception as e:  # noqa: BLE001
        print(f"  !! {name} failed: {type(e).__name__}: {e}")
        return None
    if r.content[:2] != b"PK":
        print(f"  !! {name} is not a workbook")
        return None
    path.write_bytes(r.content)
    return path


def sheet(path: Path) -> list[list]:
    wb = openpyxl.load_workbook(path, data_only=True)
    return [list(r) for r in wb[wb.sheetnames[0]].iter_rows(values_only=True)]


def cell(v) -> str:
    return "" if v is None else str(v).strip()


def year_of(label) -> int | None:
    """Census appends a footnote marker straight onto the year with no
    separator ("20242" is 2024, footnote 2) and also writes it in brackets
    ("2024 (42)"). Both are the first four digits."""
    m = re.match(r"^(\d{4})", cell(label))
    return int(m.group(1)) if m else None


def number(v) -> float | None:
    s = cell(v).replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fmt(v: float | None, dec: int = 1) -> str:
    return "" if v is None else f"{v:.{dec}f}"


def write_csv(path: Path, rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    print(f"  -> {path.relative_to(ROOT)}")


# ------------------------------------------------------------------- release
def p60_release() -> int | None:
    """The newest published P60 report number."""
    for existing in sorted(CACHE.glob("p60_*_table_3.xlsx"), reverse=True):
        return int(existing.name.split("_")[1])
    for r in range(P60_CEILING, P60_FLOOR - 1, -1):
        url = P60.format(r=r, f="table_3_opm_hist.xlsx")
        try:
            got = requests.get(url, timeout=120)
        except Exception:  # noqa: BLE001
            continue
        if got.ok and got.content[:2] == b"PK":
            (CACHE / f"p60_{r}_table_3.xlsx").write_bytes(got.content)
            print(f"  P60 release {r}")
            return r
    print("  !! no P60 release found")
    return None


# -------------------------------------------------------------------- income
def income() -> None:
    """Median household income, in current dollars and in the release's own
    constant dollars.

    Table H-8 is laid out as two stacked blocks of the same table, one per
    dollar basis, each a header row of years and then a row per state. The
    blocks are found by their "State" header rather than by row number, and
    the basis is read from the line above it, so a release that adds a year
    or a block does not silently shift the columns.
    """
    path = download("h08.xlsx", H08)
    if path is None:
        print("  -- income.csv left untouched")
        return
    rows = sheet(path)
    blocks: dict[str, dict[int, float]] = {}
    for i, r in enumerate(rows):
        if cell(r[0]) != "State":
            continue
        basis = next((cell(rows[j][0]) for j in range(i - 1, -1, -1)
                      if cell(rows[j][0])), "")
        us = next((rr for rr in rows[i + 1:]
                   if cell(rr[0]) == "United States"), None)
        if us is None:
            continue
        # First occurrence wins. A redesign year is published twice, once on
        # each processing basis, newest first; taking the first keeps the
        # basis Census itself charts and keeps the whole row consistent.
        got: dict[int, float] = {}
        for col, label in enumerate(r):
            y = year_of(label)
            if y is None or y in got or col >= len(us):
                continue
            v = number(us[col])
            if v is not None:
                got[y] = v
        blocks[basis] = got
        print(f"  [h08] {basis}: {len(got)} years")

    current = next((v for k, v in blocks.items() if "current" in k.lower()), {})
    constant_key = next((k for k in blocks if re.match(r"^\d{4} Dollars", k)), "")
    constant = blocks.get(constant_key, {})
    label = (constant_key.split()[0] + "usd").lower() if constant_key else "real"

    out = [["year", "median_household_income", f"median_household_income_{label}"]]
    for y in range(YEAR_FROM, YEAR_TO + 1):
        out.append([y, fmt(current.get(y), 0), fmt(constant.get(y), 0)])
    write_csv(DATA / "social" / "income.csv", out)
    for y in (2006, 2019, 2021, 2024, 2025):
        if y in current:
            print(f"     {y}: ${current[y]:,.0f} nominal, "
                  f"${constant.get(y, float('nan')):,.0f} in {constant_key}")


# ------------------------------------------------------------------- poverty
def by_age(path: Path, cols: dict[str, int]) -> dict[int, dict[str, float]]:
    """{year: {age group: percent}} from the ALL RACES block.

    Each table repeats the whole year range once per race group, so reading
    past the first block would overwrite the all-races numbers with those of
    whichever group came last. The block ends at the next section heading.
    """
    rows = sheet(path)
    start = next((i for i, r in enumerate(rows)
                  if cell(r[0]).upper() == "ALL RACES"), None)
    if start is None:
        print(f"  !! no ALL RACES block in {path.name}")
        return {}
    out: dict[int, dict[str, float]] = {}
    for r in rows[start + 1:]:
        y = year_of(r[0])
        if y is None:
            if cell(r[0]):
                break  # the next race section
            continue
        if y in out:
            continue  # a redesign year published twice; first wins
        out[y] = {name: v for name, col in cols.items()
                  if col < len(r) and (v := number(r[col])) is not None}
    return out


AGES = ("all", "under18", "18_64", "65plus")


def poverty(release: int) -> None:
    opm_path = CACHE / f"p60_{release}_table_3.xlsx"
    spm_path = download(f"p60_{release}_table_8.xlsx",
                        P60.format(r=release, f="table_8_spm_hist.xlsx"))
    if not opm_path.exists() or spm_path is None:
        print("  -- poverty.csv left untouched")
        return
    # Table 3 groups three columns per age band (total, number, percent);
    # table 8 groups five, because each count and rate carries a margin of
    # error. The percent column of each band is what is drawn.
    opm = by_age(opm_path, {n: 3 + 3 * i for i, n in enumerate(AGES)})
    spm = by_age(spm_path, {n: 4 + 5 * i for i, n in enumerate(AGES)})
    print(f"  [table 3 OPM] {len(opm)} years, "
          f"[table 8 SPM] {len(spm)} years")

    out = [["year"] + [f"opm_{a}" for a in AGES] + [f"spm_{a}" for a in AGES]]
    for y in range(YEAR_FROM, YEAR_TO + 1):
        o, s = opm.get(y, {}), spm.get(y, {})
        out.append([y] + [fmt(o.get(a)) for a in AGES]
                   + [fmt(s.get(a)) for a in AGES])
    write_csv(DATA / "social" / "poverty.csv", out)
    for y in (2006, 2019, 2021, 2025):
        o, s = opm.get(y, {}), spm.get(y, {})
        print(f"     {y}: OPM all {fmt(o.get('all'))}% child "
              f"{fmt(o.get('under18'))}%  |  SPM all {fmt(s.get('all'))}% "
              f"child {fmt(s.get('under18'))}%")


# -------------------------------------------------------------- minimum wage
def minimum_wage() -> None:
    def rate_on(date: str) -> float:
        return max((r for r, eff in MIN_WAGE if eff <= date),
                   key=lambda r: r)

    out = [["year", "federal_min_jan1", "federal_min_dec31", "changed_on"]]
    for y in range(YEAR_FROM, YEAR_TO + 1):
        jan, dec = rate_on(f"{y}-01-01"), rate_on(f"{y}-12-31")
        change = next((eff for _, eff in MIN_WAGE if eff.startswith(str(y))), "")
        out.append([y, f"{jan:.2f}", f"{dec:.2f}", change])
    write_csv(DATA / "social" / "minimum_wage.csv", out)
    print(f"     unchanged at ${MIN_WAGE[-1][0]:.2f} since "
          f"{MIN_WAGE[-1][1]} — {YEAR_TO - 2009} years")


def gini() -> None:
    """Table H-4, all races, as three segments split at the method breaks.

    Rows run newest first. A break year appears twice: the first of the two
    rows (the one with the higher footnote number) is on the newer basis,
    the second on the older one.
    """
    path = download("h04.xlsx", H04)
    if path is None:
        return
    rows = sheet(path)
    head = next(i for i, r in enumerate(rows) if cell(r[0]) == "Year")
    if cell(rows[head][1]) != "All races":
        raise ValueError(f"h04: column 1 is {rows[head][1]!r}, not All races")
    seen: dict[int, list[float]] = {}
    for r in rows[head + 1:]:
        y = year_of(r[0])
        v = number(r[1])
        if y is None or v is None:
            continue
        seen.setdefault(y, []).append(v)
    # 2013 and 2017 are the two breaks; every other year has one row.
    doubled = sorted(y for y, v in seen.items() if len(v) > 1 and y >= YEAR_FROM)
    if doubled != [2013, 2017]:
        raise ValueError(f"h04: expected breaks in 2013 and 2017, found {doubled}")
    # Spot values read off the published table (2026 release).
    for y, i, want in ((2006, 0, 0.470), (2013, 1, 0.476), (2013, 0, 0.482),
                       (2017, 1, 0.482), (2017, 0, 0.489), (2025, 0, 0.490)):
        if abs(seen[y][i] - want) > 0.0005:
            raise ValueError(f"h04: {y} reads {seen[y][i]}, expected {want}")
    out = [["year", "gini_to_2013", "gini_2013_2017", "gini_from_2017"]]
    for y in range(YEAR_FROM, YEAR_TO + 1):
        v = seen.get(y)
        a = b = c = None
        if v:
            if y < 2013:
                a = v[0]
            elif y == 2013:
                a, b = v[1], v[0]
            elif y < 2017:
                b = v[0]
            elif y == 2017:
                b, c = v[1], v[0]
            else:
                c = v[0]
        out.append([y] + [fmt(None if x is None else x * 100, 1)
                          for x in (a, b, c)])
    write_csv(DATA / "social" / "gini_from_census.csv", out)


def main() -> None:
    if "--gini" in sys.argv:
        print("Fetching the Census Gini index (table H-4)...")
        gini()
        return
    print("Fetching income, poverty and the minimum wage...")
    income()
    release = p60_release()
    if release is not None:
        poverty(release)
    minimum_wage()
    gini()
    print("Done.")


if __name__ == "__main__":
    main()
