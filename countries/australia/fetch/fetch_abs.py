#!/usr/bin/env python3
"""Refresh Australia's ABS SDMX series into review sidecars.

Usage:  python3 -I fetch/fetch_abs.py      (or: make C=australia fetch)

Everything the ABS publishes through its SDMX gateway lives here:
national accounts, the CPI, the labour force, population, births, deaths,
overseas migration and merchandise exports by destination.

Two rules govern the annualisation, and both are stated in DATA_NOTES.md:

  * flows (GDP, its expenditure components, arrivals, births, deaths,
    exports) are the SUM of the four calendar quarters of the year;
  * stocks and rates (population, the unemployment rate, the CPI index)
    are the second-quarter reading (population, i.e. 30 June) or the MEAN
    of the four quarters (the CPI index and the unemployment rate).

A year with fewer than four quarters is not emitted at all. The atlas
draws no partial year as an annual total (SOURCING_A_COUNTRY.md, "The
partial year"), so the sidecar simply stops at the last complete year and
the residual quarters are kept in the quarterly sidecar for review.

The ABS reports Australia's national accounts on a *fiscal* year
(July-June) in its own annual tables. This fetcher never uses those: it
builds calendar years from the quarterly series, which is what lets the
growth panel sit beside a calendar-year CPI. The fiscal-year national
line is staged separately by fetch_abs_tables.py and labelled as such.

The gateway is https://data.api.abs.gov.au/rest — note the reversed
subdomain. The documented `api.data.abs.gov.au` has no DNS record at all
(see DISCOVERY.md); the working host answers only under /rest.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _sdmx import FetchError, abs_codelist, abs_data  # noqa: E402

START = "2004-Q1"

# --------------------------------------------------------------- quarterly
ANA = {
    # column -> (measure, data item, sector)  ANA_EXP dims:
    # MEASURE.DATA_ITEM.SECTOR.TSEST.REGION.FREQ
    "gdp_current_aud_mn":     ("C", "GPM", "SSS"),
    "gdp_volume_aud_mn":      ("VCH", "GPM", "SSS"),
    "gfcf_current_aud_mn":    ("C", "GFC", "SSS"),
    "ggfcf_current_aud_mn":   ("C", "GFC", "GGS"),
    "exports_current_aud_mn": ("C", "XGS", "SSS"),
    "imports_current_aud_mn": ("C", "MGS", "SSS"),
}


def q_label(period: str) -> tuple[int, int]:
    y, q = period.split("-")
    return int(y), int(q[1:])


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    print(f"  wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def quarter_series() -> dict[tuple[int, int], dict[str, str]]:
    """{ (year, quarter): {column: value} } from ANA_EXP, original terms."""
    got: dict[tuple[int, int], dict[str, str]] = {}
    for col, (measure, item, sector) in ANA.items():
        key = f"{measure}.{item}.{sector}.10.AUS.Q"      # TSEST 10 = original
        rows = abs_data("ANA_EXP", key, START)
        for r in rows:
            if r.get("TSEST") != "10" or r.get("REGION") != "AUS":
                raise FetchError(f"ANA_EXP {key}: unexpected dimensions "
                                 f"{r.get('TSEST')}/{r.get('REGION')}")
            if r.get("UNIT_MEASURE") != "AUD" or r.get("UNIT_MULT") != "6":
                raise FetchError(f"ANA_EXP {key}: unit "
                                 f"{r.get('UNIT_MEASURE')}/{r.get('UNIT_MULT')}")
            yq = q_label(r["TIME_PERIOD"])
            got.setdefault(yq, {})[col] = r["OBS_VALUE"]
        print(f"  ANA_EXP {key}: {len(rows)} quarters")
    # A quarter is usable only when all six series are present in it.
    need = set(ANA)
    return {k: v for k, v in got.items() if need <= set(v)}


def annualise_ana(quarters: dict[tuple[int, int], dict[str, str]]
                  ) -> list[dict]:
    out = []
    years = sorted({y for y, _ in quarters})
    by_year = {}
    for y in years:
        qs = [quarters.get((y, q)) for q in (1, 2, 3, 4)]
        if any(q is None for q in qs):
            continue                                    # incomplete: not a year
        row = {"year": y}
        for col in ANA:
            row[col] = round(sum(float(q[col]) for q in qs), 1)
        row["real_growth_pct"] = ""
        by_year[y] = row
    prev = None
    for y in sorted(by_year):
        row = by_year[y]
        if prev is not None and prev in by_year:
            p = by_year[prev]
            row["real_growth_pct"] = round(
                100 * (row["gdp_volume_aud_mn"] / p["gdp_volume_aud_mn"] - 1), 2)
        for num, den, col in (
                ("gfcf_current_aud_mn", "gdp_current_aud_mn", "gfcf_pct_gdp"),
                ("ggfcf_current_aud_mn", "gdp_current_aud_mn",
                 "gg_gfcf_pct_gdp"),
                ("exports_current_aud_mn", "gdp_current_aud_mn",
                 "exports_pct_gdp"),
                ("imports_current_aud_mn", "gdp_current_aud_mn",
                 "imports_pct_gdp")):
            row[col] = round(100 * row[num] / row[den], 2)
        row["net_exports_pct_gdp"] = round(
            100 * (row["exports_current_aud_mn"]
                   - row["imports_current_aud_mn"]) / row["gdp_current_aud_mn"],
            2)
        out.append(row)
        prev = y
    return out


def prices() -> list[dict]:
    """CPI: all groups, Australia, original. Annual mean index -> YoY %."""
    rows = abs_data("CPI", "1.10001.10.50.Q", "2005-Q1")
    idx: dict[tuple[int, int], float] = {}
    for r in rows:
        if r.get("UNIT_MEASURE") != "IN":
            raise FetchError(f"CPI: unit {r.get('UNIT_MEASURE')}")
        idx[q_label(r["TIME_PERIOD"])] = float(r["OBS_VALUE"])
    by_year: dict[int, list[float]] = {}
    for (y, _q), v in idx.items():
        by_year.setdefault(y, []).append(v)
    out = []
    prev = None
    for y in sorted(by_year):
        vals = by_year[y]
        if len(vals) != 4:
            continue
        mean = sum(vals) / 4
        row = {"year": y, "cpi_index_allgroups": round(mean, 2),
               "cpi_inflation_pct": ""}
        if prev is not None:
            row["cpi_inflation_pct"] = round(100 * (mean / prev - 1), 2)
        out.append(row)
        prev = mean
    print(f"  CPI 1.10001.10.50.Q: {len(rows)} quarters")
    return out


def labour() -> list[dict]:
    """Unemployment rate, persons, Australia, seasonally adjusted, monthly."""
    rows = abs_data("LF", "M13.3.1599.20.AUS.M", "2005-01")
    by_year: dict[int, list[float]] = {}
    for r in rows:
        if r.get("UNIT_MEASURE") != "PCT":
            raise FetchError(f"LF: unit {r.get('UNIT_MEASURE')}")
        by_year.setdefault(int(r["TIME_PERIOD"][:4]), []).append(
            float(r["OBS_VALUE"]))
    out = []
    for y in sorted(by_year):
        vals = by_year[y]
        if len(vals) != 12:
            continue
        out.append({"year": y,
                    "unemployment_pct": round(sum(vals) / 12, 2),
                    "months_observed": len(vals)})
    print(f"  LF M13.3.1599.20.AUS.M: {len(rows)} months")
    return out


def population() -> list[dict]:
    """Estimated resident population, 30 June (Q2), persons."""
    rows = abs_data("ERP_Q", "1.3.TOT.AUS.Q", "2005-Q1")
    out = {}
    for r in rows:
        if r.get("UNIT_MEASURE") != "PSNS":
            raise FetchError(f"ERP_Q: unit {r.get('UNIT_MEASURE')}")
        y, q = q_label(r["TIME_PERIOD"])
        if q == 2:
            out[y] = int(float(r["OBS_VALUE"]))
    print(f"  ERP_Q 1.3.TOT.AUS.Q: {len(rows)} quarters")
    return [{"year": y, "population_jun30": out[y]} for y in sorted(out)]


def migration() -> list[dict]:
    """Net overseas migration: arrivals, departures, net. Calendar years."""
    cols = {"1": "nom_arrivals", "2": "nom_departures", "3": "nom_net"}
    rows_by_year: dict[int, dict[str, int]] = {}
    for code, col in cols.items():
        rows = abs_data("NOM_CY", f"{code}.TOT.3.AUS.A", "2004")
        for r in rows:
            rows_by_year.setdefault(int(r["TIME_PERIOD"]), {})[col] = int(
                float(r["OBS_VALUE"]))
        print(f"  NOM_CY {code}: {len(rows)} years")
    out = [{"year": y, **rows_by_year[y]} for y in sorted(rows_by_year)
           if len(rows_by_year[y]) == 3]
    return out


def foreign_born() -> list[dict]:
    """Overseas-born residents as a share of the resident population.

    ERP_COB: AGE.SEX.COUNTRY_BIRTH.REGION.FREQ. Australia-born is code
    1101, the total is TOT; the difference is the overseas-born
    population on 30 June of each year. The census revision lands in this
    series, so the step at a census year is a revision, not a migration
    event, and is annotated on the plate.
    """
    a = {int(r["TIME_PERIOD"]): int(float(r["OBS_VALUE"]))
         for r in abs_data("ERP_COB", "TOT.3.1101.AUS.A", "2005")}
    t = {int(r["TIME_PERIOD"]): int(float(r["OBS_VALUE"]))
         for r in abs_data("ERP_COB", "TOT.3.TOT.AUS.A", "2005")}
    print(f"  ERP_COB: {len(t)} years")
    out = []
    for y in sorted(set(a) & set(t)):
        out.append({"year": y, "population_ausborn": a[y],
                    "population_total": t[y],
                    "overseas_born_share_pct": round(
                        100 * (t[y] - a[y]) / t[y], 2)})
    return out


def births() -> list[dict]:
    """Registered births and the crude birth rate, year of occurrence."""
    b = {int(r["TIME_PERIOD"]): int(float(r["OBS_VALUE"]))
         for r in abs_data("BIRTHS_SUMMARY", "1.AUS.A", "2005")}
    cbr = {int(r["TIME_PERIOD"]): float(r["OBS_VALUE"])
           for r in abs_data("BIRTHS_SUMMARY", "3.AUS.A", "2005")}
    print(f"  BIRTHS_SUMMARY: {len(b)} years")
    return [{"year": y, "births": b[y], "crude_birth_rate": round(cbr[y], 2)}
            for y in sorted(set(b) & set(cbr))]


def deaths() -> list[dict]:
    """Deaths and the crude death rate, year of registration."""
    d = {int(r["TIME_PERIOD"]): int(float(r["OBS_VALUE"]))
         for r in abs_data("DEATHS_SUMMARY", "4.3.AUS.A", "2005")}
    cdr = {int(r["TIME_PERIOD"]): float(r["OBS_VALUE"])
           for r in abs_data("DEATHS_SUMMARY", "5.3.AUS.A", "2005")}
    print(f"  DEATHS_SUMMARY: {len(d)} years")
    return [{"year": y, "deaths": d[y], "crude_death_rate": round(cdr[y], 2)}
            for y in sorted(set(d) & set(cdr))]


def destinations() -> list[dict]:
    """Goods exports by destination country, calendar year, AUD million.

    MERCH_EXP is monthly only (a request for FREQ=A returns NoRecordsFound),
    so the annual figure is the sum of the twelve months of the calendar
    year. Commodity 'TOT' and state 'TOT' keep this a national total.
    """
    names = abs_codelist("CL_MERCH_COUNTRY")
    out: dict[tuple[int, str], float] = {}
    months: dict[tuple[int, str], int] = {}
    for year in range(2005, 2026):
        rows = abs_data("MERCH_EXP", "TOT..TOT.M", f"{year}-01")
        for r in rows:
            if not r["TIME_PERIOD"].startswith(str(year)):
                continue
            if r.get("UNIT_MEASURE") != "AUD" or r.get("UNIT_MULT") != "3":
                raise FetchError(f"MERCH_EXP: unit {r.get('UNIT_MEASURE')}"
                                 f"/{r.get('UNIT_MULT')}")
            k = (year, r["COUNTRY_DEST"])
            # UNIT_MULT is 3: OBS_VALUE is thousands of AUD.
            out[k] = out.get(k, 0.0) + float(r["OBS_VALUE"]) * 1e3 / 1e9
            months[k] = months.get(k, 0) + 1
        print(f"  MERCH_EXP {year}: {len(rows)} rows")
    rows = []
    for (year, code), v in sorted(out.items()):
        if months[(year, code)] != 12:
            continue                      # a partial year is not a year
        rows.append({"year": year, "country_code": code,
                     "country": names.get(code, code),
                     "exports_aud_bn": round(v, 3)})
    return rows


def main() -> None:
    try:
        print("ABS SDMX — quarterly national accounts")
        quarters = quarter_series()
        write_csv(DATA / "macro" / "ana_quarterly_from_abs.csv",
                  ["year", "period"] + list(ANA),
                  [{"year": y, "period": f"{y}-Q{q}", **v}
                   for (y, q), v in sorted(quarters.items())])
        annual = annualise_ana(quarters)
        write_csv(DATA / "macro" / "activity_from_abs.csv",
                  ["year", "gdp_current_aud_mn", "gdp_volume_aud_mn",
                   "real_growth_pct", "gfcf_pct_gdp", "gg_gfcf_pct_gdp",
                   "exports_pct_gdp", "imports_pct_gdp",
                   "net_exports_pct_gdp"], annual)
        _pin(annual, 2024, "real_growth_pct", 0.5, 2.5, "real GDP growth 2024")
        _pin(annual, 2024, "exports_pct_gdp", 20.0, 26.0, "exports 2024")
        _pin(annual, 2024, "gfcf_pct_gdp", 20.0, 25.0, "GFCF 2024")

        write_csv(DATA / "macro" / "prices_from_abs.csv",
                  ["year", "cpi_index_allgroups", "cpi_inflation_pct"],
                  prices())
        write_csv(DATA / "macro" / "labour_from_abs.csv",
                  ["year", "unemployment_pct", "months_observed"], labour())
        write_csv(DATA / "demography" / "population_from_abs.csv",
                  ["year", "population_jun30"], population())
        write_csv(DATA / "migration" / "nom_from_abs.csv",
                  ["year", "nom_arrivals", "nom_departures", "nom_net"],
                  migration())
        write_csv(DATA / "migration" / "foreign_born_from_abs.csv",
                  ["year", "population_ausborn", "population_total",
                   "overseas_born_share_pct"], foreign_born())
        write_csv(DATA / "demography" / "births_from_abs.csv",
                  ["year", "births", "crude_birth_rate"], births())
        write_csv(DATA / "mortality" / "deaths_from_abs.csv",
                  ["year", "deaths", "crude_death_rate"], deaths())
        write_csv(DATA / "trade" / "destinations_all_from_abs.csv",
                  ["year", "country_code", "country", "exports_aud_bn"],
                  destinations())
    except FetchError as e:
        print(f"fetch error: {e}", file=sys.stderr)
        raise SystemExit(1)


def _pin(rows: list[dict], year: int, col: str, lo: float, hi: float,
         what: str) -> None:
    """A known-value check: refuse to cache a series that is not this one."""
    row = next((r for r in rows if r["year"] == year), None)
    v = (row or {}).get(col)
    if v in ("", None):
        raise FetchError(f"{what}: {year} missing")
    if not lo <= float(v) <= hi:
        raise FetchError(f"{what}: {v} outside the expected {lo}-{hi}")


if __name__ == "__main__":
    main()
