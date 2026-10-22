#!/usr/bin/env python3
"""Adopt reviewed sidecars into the curated CSVs the plates draw.

Usage:  python3 -I countries/argentina/fetch/curate.py            # dry run
        python3 -I countries/argentina/fetch/curate.py --write    # adopt

A fetcher writes `<name>_check.csv` or `<name>_from_<source>.csv` and never
touches a curated number. This is the step after a person has read the
diff: it copies the window's rows (2006-2026) of each sidecar into the
curated file, renaming columns where the curated name is clearer and, for
the World Bank's US$ levels, dividing by 1e9 so the file is in US$ bn like
every other money file here. Nothing is interpolated, spliced or rounded
beyond the stated precision.

Without --write it only prints what would change, row by row, so the run
that adopts a revision is always preceded by one that shows it.

Hand-entered rows (values the publisher's machine-readable file does not
carry yet) are listed in EXTRA with their source, and are the only numbers
here not read from a sidecar.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
YEAR_FROM, YEAR_TO = 2006, 2026

# curated file -> (sidecar, [(curated column, sidecar column, scale, fmt)])
PLAN = {
    "macro/world.csv": ("macro/world_from_wb.csv", [
        ("gdp_usd_bn", "gdp_usd", 1e-9, ".2f"),
        ("gdp_per_person_usd", "gdp_per_person_usd", 1, ".0f"),
        ("reserves_usd_bn", "reserves_usd", 1e-9, ".2f")]),
    "macro/economy_intl.csv": ("macro/economy_from_wb.csv", [
        ("gfcf_pct_gdp", "gfcf_pct_gdp", 1, ".2f"),
        ("unemployment_ilo_pct", "unemployment_pct", 1, ".2f")]),
    "macro/household_credit.csv": ("macro/household_credit_from_bis.csv", [
        ("bis_q4_pct_gdp", "hh_credit_pct_gdp_q4", 1, ".1f"),
        ("bis_quarters", "hh_credit_pct_gdp_quarters", 1, ".0f")]),
    "macro/policy_rate.csv": ("macro/policy_rate_check.csv", [
        ("policy_avg", "policy_avg", 1, ".2f"),
        ("policy_eoy", "policy_eoy", 1, ".2f"),
        ("badlar_avg", "badlar_avg", 1, ".2f"),
        ("badlar_days", "badlar_days", 1, ".0f")]),
    "markets/us_treasury_10y.csv": ("markets/us_treasury_10y_check.csv", [
        ("avg", "avg", 1, ".3f"),
        ("days", "days", 1, ".0f")]),
    "trade/trade_gns.csv": ("trade/trade_from_wb.csv", [
        ("exports_pct_gdp", "exports_pct_gdp", 1, ".2f"),
        ("imports_pct_gdp", "imports_pct_gdp", 1, ".2f")]),
    "trade/destinations.csv": ("trade/destinations_check.csv", [
        (c, c, 1, ".2f") for c in
        ("brazil", "china", "usa", "chile", "india", "world_usd_bn")]),
    "fiscal/general_government.csv": (
        "fiscal/general_government_from_imf.csv", [
            (c, c, 1, ".2f") for c in
            ("revenue_pct_gdp", "expenditure_pct_gdp", "balance_pct_gdp",
             "primary_balance_pct_gdp", "gross_debt_pct_gdp")]),
    "fiscal/public_investment.csv": ("fiscal/public_investment_check.csv", [
        (c, c, 1, ".2f") for c in ("m1993", "m2007", "m2017")]),
    "social/demography_intl.csv": ("social/demography_from_wb.csv", [
        ("population", "population", 1, ".0f"),
        ("population_female", "population_female", 1, ".0f"),
        ("fertility", "fertility", 1, ".3f"),
        ("birth_rate_per_1000", "birth_rate_per_1000", 1, ".3f"),
        ("death_rate_per_1000", "death_rate_per_1000", 1, ".3f"),
        ("net_migration", "net_migration", 1, ".0f")]),
    "social/security_intl.csv": ("social/security_from_wb.csv", [
        (c, c, 1, ".2f") for c in
        ("homicide_per_100k", "suicide_per_100k", "road_deaths_per_100k")]),
    "social/gini_intl.csv": ("social/gini_from_wb.csv", [
        ("wb", "wb", 1, ".1f")]),
    "social/poverty_intl.csv": ("social/poverty_from_wb.csv", [
        ("poverty_830_pct", "poverty_pct", 1, ".1f"),
        ("extreme_300_pct", "extreme_pct", 1, ".1f")]),
    "social/corruption.csv": ("social/corruption_check.csv", [
        ("score", "score", 1, ".0f"),
        ("rank", "rank", 1, ".0f")]),
    "social/causes.csv": ("social/causes_check.csv", [
        (c, c, 1, ".0f") for c in
        ("deaths_total", "covid", "influenza", "pneumonia", "respiratory",
         "suicide", "transport")]),
}

# Rows no machine-readable file carries yet: (curated file, year, values).
EXTRA = {
    # CPI 2025, published 10 February 2026: 36/100, rank 104 of 182.
    # TI's results workbook for 2025 is not downloadable without a browser
    # session (403); read off TI's release as reported by the Buenos Aires
    # Herald and DLA Piper's regional summary, which agree.
    ("social/corruption.csv", 2025): {"score": 36, "rank": 104},
}


def read(rel: str) -> dict[int, dict[str, str]]:
    path = DATA / rel
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {int(r["year"]): r for r in csv.DictReader(fh)}


def build(rel: str) -> list[list[str]]:
    sidecar, cols = PLAN[rel]
    src = read(sidecar)
    if not src:
        raise SystemExit(f"{sidecar} is missing; run its fetcher first")
    years = sorted(y for y in src if YEAR_FROM <= y <= YEAR_TO)
    extra = {y: v for (f, y), v in EXTRA.items() if f == rel}
    years = sorted(set(years) | set(extra))
    rows = []
    for y in years:
        row = [str(y)]
        for out, col, k, spec in cols:
            if y in extra and out in extra[y]:
                row.append(format(extra[y][out], spec))
                continue
            raw = (src.get(y, {}).get(col) or "").strip()
            row.append(format(float(raw) * k, spec) if raw else "")
        rows.append(row)
    return [["year"] + [c[0] for c in cols]] + rows


def main(write: bool) -> None:
    for rel in PLAN:
        new = build(rel)
        old = read(rel)
        header = new[0]
        changed = []
        for row in new[1:]:
            y = int(row[0])
            before = [old.get(y, {}).get(c, "") for c in header[1:]]
            if before != row[1:]:
                changed.append((y, before, row[1:]))
        print(f"{rel}: {len(changed)} row(s) differ")
        for y, a, b in changed[:4]:
            print(f"    {y}: {a} -> {b}")
        if write and changed:
            with (DATA / rel).open("w", encoding="utf-8", newline="") as fh:
                csv.writer(fh, lineterminator="\n").writerows(new)
            print(f"    adopted -> data/{rel}")


if __name__ == "__main__":
    main("--write" in sys.argv[1:])
