#!/usr/bin/env python3
"""Fetch the CDC's published death RATES that the plate spine draws.

Usage:  python3 countries/usa/fetch/fetch_cdc_rates.py

fetch_cdc.py stages the counts. The spine puts every death series on one
unit, per 100,000 people, and PLATE_SPINE.md rule 5 says that where the
publisher publishes the rate, the published rate is the one drawn. So this
fetches the rates themselves, from the same three CDC systems:

  Suicide, crude rate per 100,000:
    CDC WONDER, Underlying Cause of Death 1999-2020 (D76), ICD-10 X60-X84
    and Y87.0, for the final years; the national "Mapping Injury, Overdose,
    and Violence" series (Socrata t6u2-f84c, intent All_Suicide) for the
    provisional years after it. The two overlap on 2019 and 2020, and the
    overlap is printed so the seam is measured rather than assumed.

  COVID-19 as the UNDERLYING cause (U07.1), which is the spine's definition:
    2020   WONDER D76, the final file, deaths and its published crude rate;
    2021-  "Monthly Provisional Counts of Deaths by Select Causes" (Socrata
    2022   9dzk-mvmi), twelve months summed. NCHS publishes counts here, not
           a rate, so the rate is the plate's: count over the Census July 1
           population (social/population_july1.csv);
    2023-  "VSRR Quarterly provisional estimates for selected indicators of
    2024   mortality" (Socrata 489q-934x): the crude rate for the 12 months
           ending in Q4, which is the calendar year. Published as a rate,
           so drawn as one.
    That dataset's newest 12-month window ending in a Q4 is the last year
    published; a year without one stays empty rather than being read off a
    window that is not a calendar year.

Every value is checked against a spot figure before anything is written.

Output (a sidecar; fetch/curate.py accepts it into social/death_rates.csv):
  data/social/death_rates_from_cdc.csv
      year, suicide_rate, suicide_basis,
      covid_underlying, covid_underlying_rate, covid_basis
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import fetch_cdc as cdc  # the WONDER and Socrata helpers, and their cache

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
YEAR_FROM, YEAR_TO = 2006, 2026

# (series, year, expected) read off the publishers on 2026-10-22.
SPOT = (("suicide_final", 2006, 11.2), ("suicide_final", 2020, 14.0),
        ("suicide_prov", 2021, None), ("covid_final", 2020, 350_831),
        ("covid_monthly", 2021, 417_869), ("covid_vsrr", 2023, 14.9))


def suicide_final() -> dict[int, float]:
    got = cdc.wonder("suicides_rate", ("X60-X84", "Y87.0"))
    return {y: v[1] for y, v in got.items()}


def suicide_provisional() -> dict[int, float]:
    prov = cdc.injury_national()
    return {y: v[1] for y, v in prov.get("All_Suicide", {}).items()}


def covid_final() -> dict[int, tuple[float, float]]:
    return cdc.wonder("covid_underlying", ("U07.1",))


def covid_monthly() -> dict[int, float]:
    rows = cdc.socrata("9dzk-mvmi", "monthly_select_causes",
                       jurisdiction_of_occurrence="United States",
                       **{"$limit": 500})
    months: dict[int, int] = {}
    total: dict[int, float] = {}
    for r in rows:
        try:
            y = int(r["year"])
            v = float(r["covid_19_underlying_cause"])
        except (KeyError, TypeError, ValueError):
            continue
        months[y] = months.get(y, 0) + 1
        total[y] = total.get(y, 0.0) + v
    # Only whole years: the file stops in September 2023.
    return {y: v for y, v in total.items() if months[y] == 12}


def covid_vsrr() -> dict[int, float]:
    rows = cdc.socrata(
        "489q-934x", "vsrr_quarterly_covid",
        cause_of_death="COVID-19", rate_type="Crude",
        time_period="12 months ending with quarter", **{"$limit": 500})
    out = {}
    for r in rows:
        period = r.get("year_and_quarter", "")
        if period.endswith("Q4"):
            out[int(period[:4])] = float(r["rate_overall"])
    return out


def main() -> int:
    print("Fetching CDC published death rates...")
    sf, sp = suicide_final(), suicide_provisional()
    cf, cm, cv = covid_final(), covid_monthly(), covid_vsrr()
    for y in (2019, 2020):
        if y in sf and y in sp:
            print(f"  overlap {y} suicide rate: final {sf[y]} vs "
                  f"provisional {sp[y]}")
    checks = {"suicide_final": sf, "suicide_prov": sp,
              "covid_final": {y: v[0] for y, v in cf.items()},
              "covid_monthly": cm, "covid_vsrr": cv}
    for name, y, want in SPOT:
        got = checks[name].get(y)
        if got is None or (want is not None and abs(got - want) > 1e-6):
            print(f"  !! {name} {y}: {got} against {want}; nothing written")
            return 1

    rows = [["year", "suicide_rate", "suicide_basis", "covid_underlying",
             "covid_underlying_rate", "covid_basis"]]
    for y in range(YEAR_FROM, YEAR_TO + 1):
        if y in sf:
            s_rate, s_basis = f"{sf[y]:.1f}", "final"
        elif y in sp:
            s_rate, s_basis = f"{sp[y]:.1f}", "provisional"
        else:
            s_rate, s_basis = "", ""
        if y in cf:
            c = (f"{cf[y][0]:.0f}", f"{cf[y][1]:.1f}", "final")
        elif y in cm:
            c = (f"{cm[y]:.0f}", "", "provisional_count")
        elif y in cv:
            c = ("", f"{cv[y]:.1f}", "provisional_rate")
        else:
            c = ("", "", "")
        rows.append([y, s_rate, s_basis, *c])
    dest = DATA / "social" / "death_rates_from_cdc.csv"
    with dest.open("w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    print(f"  -> {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
