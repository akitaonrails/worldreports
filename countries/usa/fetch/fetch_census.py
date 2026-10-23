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

For the plate spine, two sidecars (fetch/curate.py accepts them):

  One continuous July 1 resident population, 2006 on, from the series the
  Bureau itself now publishes as its best history: the 2000-2010
  intercensal estimates (us-est00int-tot.csv, the July rows), the 2010-2020
  intercensal estimates (nc-est2020int-agesex-res.csv, all ages, both
  sexes), then Vintage 2025. The intercensal series are re-anchored on the
  census at each end, so unlike the Vintage 2019 estimates in
  population.csv there is no step at 2020. This is the denominator of every
  rate per 100,000 or per 1,000 on these plates, and it is the same series
  the World Bank carries as SP.POP.TOTL, which is checked year by year.

  The Bureau's own published rates per 1,000 for the components of change
  (RBIRTH, RDEATH, RNATURALINC / RNATURALCHG, RNETMIG), from the Vintage
  2019 and Vintage 2025 files. They are on the July-to-June estimate year
  and are kept apart by vintage.

Outputs:
  data/social/population.csv   year,population,births,deaths,net_migration,
                               natural_increase,growth_pct,vintage
  data/social/projections.csv  year,population,births,deaths,net_migration
  data/social/population_july1_from_census.csv  year,population,series
  data/social/components_from_census.csv        year,vintage,birth_rate,
                               death_rate,natural_rate,net_migration_rate

Usage:  python3 countries/usa/fetch/fetch_census.py [--spine]
        --spine refreshes only the two sidecars.
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

INTERCENSAL_2000S = f"{BASE}/2000-2010/intercensal/national/us-est00int-tot.csv"
INTERCENSAL_2010S = (f"{BASE}/2010-2020/intercensal/national/asrh/"
                     "nc-est2020int-agesex-res.csv")


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


def july1_population() -> dict[int, tuple[float, str]]:
    """{year: (resident population on 1 July, which series)}, 2006 on."""
    out: dict[int, tuple[float, str]] = {}
    text = download("us-est00int-tot.csv", INTERCENSAL_2000S)
    for row in csv.DictReader(io.StringIO(text or "")):
        y = int(row["YEAR"])
        if row["MONTH"] == "7" and YEAR_FROM <= y <= 2009:
            out[y] = (float(row["TOT_POP"]), "intercensal_2000_2010")
    text = download("nc-est2020int-agesex-res.csv", INTERCENSAL_2010S)
    for row in csv.DictReader(io.StringIO(text or "")):
        if row["SEX"] == "0" and row["AGE"] == "999":
            for y in range(2010, 2020):
                out[y] = (float(row[f"POPESTIMATE{y}"]), "intercensal_2010_2020")
    text = download("v2025.csv", VINTAGES[0][1])
    row = us_row(text or "")
    for y in VINTAGES[0][2]:
        v = number(row or {}, f"POPESTIMATE{y}")
        if v is not None:
            out[y] = (v, "v2025")
    return out


def spine() -> None:
    """The two sidecars the plate spine draws from. See the docstring."""
    pop = july1_population()
    # Spot values: the Bureau's published July 1 totals.
    for y, want in ((2006, 298_379_912), (2019, 330_226_227),
                    (2025, 341_784_857)):
        got = pop.get(y, (None,))[0]
        if got != want:
            raise SystemExit(f"  !! July 1 {y}: {got} against {want}; "
                             f"nothing written")
    # Cross-check: the World Bank's SP.POP.TOTL is this same series.
    wb = DATA / "social" / "demography_from_wb.csv"
    if wb.exists():
        for r in csv.DictReader(wb.open()):
            y = int(r["year"])
            if y in pop and r["population"]:
                if abs(float(r["population"]) / pop[y][0] - 1) > 1e-6:
                    print(f"  ?? {y}: World Bank {r['population']} vs "
                          f"Census {pop[y][0]:.0f}")
    lines = ["year,population,series"]
    for y in range(YEAR_FROM, YEAR_TO + 1):
        p, tag = pop.get(y, (None, ""))
        lines.append(f"{y},{fmt(p)},{tag}")
    (DATA / "social" / "population_july1_from_census.csv").write_text(
        "\n".join(lines) + "\n")
    print("  -> data/social/population_july1_from_census.csv")

    rates: dict[int, list[str]] = {}
    for tag, url, years, base in VINTAGES:
        row = us_row(download(f"{tag}.csv", url) or "")
        if row is None:
            raise SystemExit(f"  !! {tag}: no United States row")
        natural = "RNATURALCHG" if tag == "v2025" else "RNATURALINC"
        for y in years:
            if y == base or y in rates:
                continue
            got = [number(row, f"{f}{y}") for f in
                   ("RBIRTH", "RDEATH", natural, "RNETMIG")]
            if all(v is not None for v in got):
                rates[y] = [tag] + [fmt(v, 3) for v in got]
    for y, i, want in ((2019, 3, 1.818), (2024, 3, 8.081), (2011, 2, 4.706)):
        if rates.get(y, [None] * 5)[i + 1] != f"{want:.3f}":
            raise SystemExit(f"  !! components {y}: {rates.get(y)}; "
                             f"nothing written")
    lines = ["year,vintage,birth_rate,death_rate,natural_rate,"
             "net_migration_rate"]
    for y in range(YEAR_FROM, YEAR_TO + 1):
        lines.append(",".join([str(y)] + rates.get(y, [""] * 5)))
    (DATA / "social" / "components_from_census.csv").write_text(
        "\n".join(lines) + "\n")
    print("  -> data/social/components_from_census.csv")


def main() -> None:
    import sys
    if "--spine" in sys.argv:
        print("Fetching Census series for the plate spine...")
        spine()
        return
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
    spine()
    print("Done.")


if __name__ == "__main__":
    main()
