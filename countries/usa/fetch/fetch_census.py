#!/usr/bin/env python3
"""Fetch population, its components and the projections from the Census Bureau.

The Census Bureau's JSON API needs a registered key, so this reads the
published flat files instead, which do not. They are also the better source
for a reproducible repo: each is a dated vintage, and the vintage is what
decides whether a projection puts the population peak in one decade or the
next.

Files used:
  popest 2020-2025, state totals, NST-EST2025-ALLDATA.csv
    population, births, deaths and net international migration, 2020-2025.
    The "state" file carries a United States row, which the national
    directory does not publish for this vintage.
  popest 2010-2019, national totals, nst-est2019-alldata.csv
    the same measures for 2010-2019.
  popproj 2023, np2023_d1_mid.csv
    the 2023 National Population Projections, middle series, to 2100.

A Census estimate year runs 1 July to 30 June, so BIRTHS2024 is the twelve
months to 1 July 2024 rather than calendar 2024. That is the Bureau's own
convention and is kept, not re-based, because re-basing it would silently
disagree with every published figure.

Births and net migration before 2010 are left EMPTY. The 2000s vintage files
publish intercensal population but not its components, and an estimate built
here to fill the gap would be this repo's number rather than the Bureau's.

Outputs:
  data/social/population.csv   year,population,births,deaths,net_migration,
                               natural_increase,growth_pct,vintage
  data/social/projections.csv  year,population,births,deaths,net_migration
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "census"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

BASE = "https://www2.census.gov/programs-surveys/popest/datasets"
PROJ = ("https://www2.census.gov/programs-surveys/popproj/datasets/2023/"
        "2023-popproj/np2023_d1_mid.csv")

# (tag, url, estimate years, the vintage's base year)
#
# The base year's components are NOT a year: a vintage starts at the census
# reference date of 1 April and its first "year" is the three months to
# 1 July, so BIRTHS2020 is 894,123 where a real year is about 3.6 million.
# Those are dropped rather than drawn as a collapse in births. The base
# year's POPULATION is fine and is kept.
VINTAGES = (
    ("v2025", f"{BASE}/2020-2025/state/totals/NST-EST2025-ALLDATA.csv",
     range(2020, 2026), 2020),
    ("v2019", f"{BASE}/2010-2019/national/totals/nst-est2019-alldata.csv",
     range(2010, 2020), 2010),
)

YEAR_FROM, YEAR_TO = 2006, 2026
PROJ_TO = 2100


def download(name: str, url: str) -> str | None:
    path = CACHE / name
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    try:
        r = requests.get(url, timeout=180)
        r.raise_for_status()
    except Exception as e:  # noqa: BLE001
        print(f"  !! {name} failed: {type(e).__name__}: {e}")
        return None
    path.write_bytes(r.content)
    return r.text


def us_row(text: str) -> dict[str, str] | None:
    """The United States row. The state files carry one; it is identified by
    name rather than by summary level, which differs between vintages."""
    for row in csv.DictReader(io.StringIO(text)):
        if (row.get("NAME") or "").strip() == "United States":
            return row
    return None


def number(row: dict[str, str], field: str) -> float | None:
    raw = (row.get(field) or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def fmt(v: float | None, dec: int = 0) -> str:
    return "" if v is None else f"{v:.{dec}f}"


def projections() -> dict[int, float]:
    """{year: projected population} from the middle series.

    np2023_d1 is wide: one row per sex/origin/race group per year, with a
    TOTAL_POP and then a column per single year of age. The all-groups row is
    SEX=0, ORIGIN=0, RACE=0 — the file already contains those totals, so
    summing the group rows would double-count every person.
    """
    text = download("np2023_d1_mid.csv", PROJ)
    if text is None:
        return {}
    out: dict[int, float] = {}
    for row in csv.DictReader(io.StringIO(text)):
        try:
            if not (int(row["SEX"]) == int(row["ORIGIN"])
                    == int(row["RACE"]) == 0):
                continue
            year = int(row["YEAR"])
        except (KeyError, TypeError, ValueError):
            continue
        v = number(row, "TOTAL_POP")
        if v is not None:
            out[year] = v
    return out


def main() -> None:
    print("Fetching Census population...")

    # ---- estimates, newest vintage first so it wins any overlap ----------
    pop: dict[int, tuple[float, str]] = {}
    comp: dict[int, dict[str, float]] = {}
    for tag, url, years, base in VINTAGES:
        text = download(f"{tag}.csv", url)
        if text is None:
            continue
        row = us_row(text)
        if row is None:
            print(f"  !! {tag}: no United States row")
            continue
        got = 0
        for y in years:
            p = number(row, f"POPESTIMATE{y}")
            if p is None or y in pop:
                continue
            pop[y] = (p, tag)
            comp[y] = {}
            if y == base:
                got += 1
                continue  # three months, not a year — see VINTAGES
            for key, field in (("births", f"BIRTHS{y}"),
                               ("deaths", f"DEATHS{y}"),
                               ("net_migration", f"INTERNATIONALMIG{y}")):
                v = number(row, field)
                if v is not None:
                    comp[y][key] = v
            got += 1
        print(f"  [{tag}] {got} years (components from {base + 1})")

    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        entry = pop.get(y)
        c = comp.get(y, {})
        births, deaths = c.get("births"), c.get("deaths")
        natural = (births - deaths) if (births and deaths) else None
        prev = pop.get(y - 1)
        # Growth is only computed WITHIN a vintage. Across the 2019/2020
        # boundary the jump is the 2020 Census re-basing the estimate upward,
        # not people: it reads as +1.0% against a real +0.5%, which would be
        # the fastest growth on the chart and is an artefact.
        growth = ((entry[0] / prev[0] - 1) * 100
                  if (entry and prev and prev[0] and entry[1] == prev[1])
                  else None)
        rows.append(
            f"{y},{fmt(entry[0]) if entry else ''},{fmt(births)},{fmt(deaths)},"
            f"{fmt(c.get('net_migration'))},{fmt(natural)},{fmt(growth, 3)},"
            f"{entry[1] if entry else ''}")
    (DATA / "social" / "population.csv").write_text(
        "year,population,births,deaths,net_migration,natural_increase,"
        "growth_pct,vintage\n" + "\n".join(rows) + "\n")
    print("  -> data/social/population.csv")

    # ---- projections -----------------------------------------------------
    pr = projections()
    years = sorted(pr)
    if years:
        peak = max(years, key=lambda y: pr[y])
        print(f"  [np2023 mid] {years[0]}-{years[-1]}, peak "
              f"{pr[peak] / 1e6:.1f}M in {peak}")
    rows = [f"{y},{fmt(pr[y])}" for y in years if y <= PROJ_TO]
    (DATA / "social" / "projections.csv").write_text(
        "year,population\n" + "\n".join(rows) + "\n")
    print("  -> data/social/projections.csv")
    print("Done.")


if __name__ == "__main__":
    main()
