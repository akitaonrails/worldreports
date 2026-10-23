#!/usr/bin/env python3
"""Refresh the cross-country comparables for Japan into sidecar CSVs.

Usage:  python3 -I countries/japan/fetch/fetch_comparables.py

These are the layer that makes a country legible to a reader who does not
live in it: the same quantity, computed the same way, for everyone. They
are never a substitute for a number Japan publishes about itself. Where
both exist — GDP, population, reserves, the Gini, asylum — the national
series is the curated one and this is the cross-check; the plate draws
both and labels the difference rather than choosing. All official: false.

  World Bank    NY.GDP.MKTP.CD    GDP, current US$
                NY.GDP.PCAP.CD    GDP per person, current US$
                SP.POP.TOTL       population (MID-YEAR; the Statistics
                                  Bureau counts on 1 October)
                FI.RES.TOTL.CD    reserves including gold, current US$
                NE.TRD.GNFS.ZS    trade as a share of GDP
                SI.POV.GINI       Gini, sparse (2008–2020 only)
                VC.IHR.PSRC.P5    intentional homicides per 100,000 (UNODC)
  UNDP          HDI, from the HDR25 composite-indices file (one vintage)
  IMF           GGXWDG_NGDP, GGXCNL_NGDP, NGDPD (DataMapper / WEO)
  OECD          IDD Gini and 50%-line poverty, total population
  UNHCR         asylum applications and decisions, country of asylum JPN

The HDR file is a single vintage covering every year, which is the point:
the HDI is recomputed for the whole back-series at each methodology
change. One file, one vintage.

The IMF payload carries WEO forecasts to 2031 next to the history; years
after last_full_year go only into `*_proj` columns, so a projection can
never be drawn as observed. NOTE: on this vintage Japan's gross debt is
213.6% of GDP in 2024 (peak 228.8% in 2020), not the ">250%" of older
WEO vintages on the 2015-base GDP.

The OECD IDD carries two income definitions for Japan (METH2011 to 2018,
METH2012 from 2018, overlapping in 2018). They are separate columns,
never joined.

UNHCR counts are per year × application type × decision level; new
first-instance applications, appeals, and first-instance decisions are
separate columns and never one line.

Holes stay holes: a null from any API is a blank, never a zero.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
ISO3 = "JPN"

WB = ("https://api.worldbank.org/v2/country/JPN/indicator/{code}"
      "?format=json&per_page=200&date=2006:2026")
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
IMF = "https://www.imf.org/external/datamapper/api/v1/{code}/JPN"
OECD = ("https://sdmx.oecd.org/public/rest/data/OECD.WISE.INE,DSD_WISE_IDD@DF_IDD,"
        "/JPN.A.INC_DISP_GINI+PR_INC_DISP......?startPeriod=2006"
        "&format=csvfilewithlabels")
UNHCR = ("https://api.unhcr.org/population/v1/{kind}/"
         "?coa=JPN&yearFrom=2006&yearTo=2025&cf_type=ISO&limit=1000&page={page}")

# hdr.undp.org answers 403 to the default urllib User-Agent; www.imf.org's
# edge answers 403 to any UA starting "Mozilla/5.0" (UK lane, 2026-10-22).
BROWSER = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
PLAIN = {"User-Agent": "worldreports-data-fetcher/1.0"}

YEAR_FROM, YEAR_TO = 2006, 2026
LAST_FULL_YEAR = 2025

WANTED = [  # (sidecar, code, column, decimals)
    ("international/gdp_usd_from_wb.csv", "NY.GDP.MKTP.CD", "gdp_usd", 0),
    ("international/gdp_pc_from_wb.csv", "NY.GDP.PCAP.CD", "gdp_per_person_usd", 0),
    ("international/population_from_wb.csv", "SP.POP.TOTL", "population", 0),
    ("international/reserves_from_wb.csv", "FI.RES.TOTL.CD", "reserves_usd", 0),
    ("international/openness_from_wb.csv", "NE.TRD.GNFS.ZS", "trade_pct_gdp", 1),
    ("social/gini_from_wb.csv", "SI.POV.GINI", "gini", 1),
    ("security/homicide_rate_from_wb.csv", "VC.IHR.PSRC.P5", "homicides_per_100k", 2),
]
UNITS = {
    "NY.GDP.MKTP.CD": "current US$",
    "NY.GDP.PCAP.CD": "current US$ per person",
    "SP.POP.TOTL": "persons, mid-year (Statistics Bureau counts on 1 October)",
    "FI.RES.TOTL.CD": "current US$, incl. gold (IMF IFS); MOF historical.csv is the national series",
    "NE.TRD.GNFS.ZS": "% of GDP, exports + imports of goods and services",
    "SI.POV.GINI": "index 0–100, World Bank harmonised; sparse — gaps are not data",
    "VC.IHR.PSRC.P5": "per 100,000 people, UNODC definition (neither NPA's nor MHLW's)",
}
IMF_WANTED = [
    ("GGXWDG_NGDP", "gross_debt_pct_gdp", 1),
    ("GGXCNL_NGDP", "net_lending_pct_gdp", 1),
    ("NGDPD", "gdp_usd_bn", 3),
]


class FetchError(RuntimeError):
    pass


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise FetchError(msg)


def cached(name: str, url: str, headers: dict, validate) -> bytes:
    """Fetch once into cache/<name>; the payload is shape-checked BEFORE it
    is cached, because a cached error page survives the retry that would
    have fixed it. Backs off on 429/403/5xx."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / name
    if path.exists():
        return path.read_bytes()
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
            validate(body)
            path.write_bytes(body)
            time.sleep(1.0)
            return body
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (403, 429) and e.code < 500:
                break
        except Exception as e:  # noqa: BLE001
            last = e
        print(f"  {name} attempt {attempt + 1}: {last}", file=sys.stderr)
        time.sleep(5 * (attempt + 1))
    raise FetchError(f"{name}: {last}")


# ---------------------------------------------------------------- World Bank
def wb_series(code: str) -> dict[int, float]:
    def ok(body: bytes) -> None:
        p = json.loads(body)
        check(isinstance(p, list) and len(p) > 1 and isinstance(p[1], list)
              and p[1] and p[1][0]["countryiso3code"] == ISO3,
              f"WB {code}: not an indicator response for {ISO3}")
    p = json.loads(cached(f"wb_{code}.json", WB.format(code=code), PLAIN, ok))
    return {int(r["date"]): float(r["value"]) for r in p[1]
            if r.get("value") is not None}


def write_wb(rel: str, code: str, column: str, series: dict[int, float],
             dec: int) -> None:
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# World Bank WDI {code}, JPN. official: false. Units: {UNITS[code]}.",
             "# Calendar years; blank = null in the API (not published), never zero.",
             f"year,{column}"]
    for y in range(YEAR_FROM, YEAR_TO + 1):
        v = series.get(y)
        lines.append(f"{y}," + ("" if v is None else f"{v:.{dec}f}"))
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {YEAR_TO - YEAR_FROM + 1} rows, "
          f"{len([y for y in series if YEAR_FROM <= y <= YEAR_TO])} non-blank "
          f"({min(series)}–{max(series)})")


# ---------------------------------------------------------------- UNDP
def hdr_hdi() -> dict[int, float]:
    """One row per country and one COLUMN per year; the key must match
    `hdi_YYYY` exactly (a prefix match pulls in hdi_rank_2023)."""
    def ok(body: bytes) -> None:
        head = body[:4000].decode("latin-1")
        check("iso3" in head and "hdi_2023" in head, "HDR: not the series CSV")
    text = cached("hdr25_series.csv", HDR, BROWSER, ok).decode("latin-1")
    out: dict[int, float] = {}
    rank = None
    for row in csv.DictReader(io.StringIO(text)):
        if (row.get("iso3") or row.get("ISO3")) != ISO3:
            continue
        for key, value in row.items():
            if not key or value in (None, "", ".."):
                continue
            name = key.lower()
            year = name.rsplit("_", 1)[-1]
            if year.isdigit() and name == f"hdi_{year}":
                out[int(year)] = float(value)
        rank = row.get("hdi_rank_2023")
        break
    check(bool(out), "HDR: no JPN row")
    check(rank == "23", f"HDR: JPN hdi_rank_2023 = {rank}, expected 23")
    return out


# ---------------------------------------------------------------- IMF
def imf_series(code: str) -> dict[int, float]:
    def ok(body: bytes) -> None:
        values = json.loads(body).get("values", {}).get(code, {}).get(ISO3)
        check(isinstance(values, dict) and bool(values),
              f"IMF {code}: no JPN values")
    p = json.loads(cached(f"imf_{code}.json", IMF.format(code=code), PLAIN, ok))
    return {int(y): float(v) for y, v in p["values"][code][ISO3].items()
            if v is not None}


def write_imf(rel: str) -> dict[str, dict[int, float]]:
    series = {code: imf_series(code) for code, _, _ in IMF_WANTED}
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["year"]
    for _, column, _ in IMF_WANTED:
        header += [column, f"{column}_proj"]
    lines = [
        "# IMF DataMapper (WEO), general government, JPN, CALENDAR years. official: false.",
        "# gross_debt / net_lending: % of GDP. gdp_usd_bn: US$ billion (NGDPD).",
        f"# Years after {LAST_FULL_YEAR} are WEO PROJECTIONS and sit only in *_proj columns.",
        "# Not MOF's central-government debt (face value) nor BoJ flow of funds (market value).",
        ",".join(header),
    ]
    years = sorted(set().union(*series.values()))
    for y in years:
        row = [str(y)]
        for code, _, dec in IMF_WANTED:
            v = series[code].get(y)
            if v is None:
                row += ["", ""]
            elif y <= LAST_FULL_YEAR:
                row += [f"{v:.{dec}f}", ""]
            else:
                row += ["", f"{v:.{dec}f}"]
        lines.append(",".join(row))
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {len(years)} rows ({years[0]}–{years[-1]}, "
          f"projections after {LAST_FULL_YEAR})")
    return series


# ---------------------------------------------------------------- OECD
def oecd_idd(rel: str) -> dict[tuple[str, str], dict[int, float]]:
    def ok(body: bytes) -> None:
        head = body[:2000].decode("utf-8", errors="replace")
        check(head.startswith("STRUCTURE,") and "OBS_VALUE" in head,
              "OECD: not an SDMX csvfilewithlabels payload")
    text = cached("oecd_idd_jpn.csv", OECD, PLAIN, ok).decode("utf-8-sig")
    out: dict[tuple[str, str], dict[int, float]] = {}
    for r in csv.DictReader(io.StringIO(text)):
        if r["REF_AREA"] != ISO3 or r["AGE"] != "_T" or r["DEFINITION"] != "D_CUR":
            continue
        if r["MEASURE"] == "INC_DISP_GINI":
            key = ("gini", r["METHODOLOGY"])
        elif r["MEASURE"] == "PR_INC_DISP" and r["POVERTY_LINE"] == "PL_50":
            key = ("poverty50", r["METHODOLOGY"])
        else:
            continue
        if r["OBS_VALUE"] != "":
            out.setdefault(key, {})[int(r["TIME_PERIOD"])] = float(r["OBS_VALUE"])
    cols = [("gini", "METH2011"), ("gini", "METH2012"),
            ("poverty50", "METH2011"), ("poverty50", "METH2012")]
    check(set(out) == set(cols), f"OECD: unexpected series {sorted(out)}")
    years = sorted(set().union(*out.values()))
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# OECD Income Distribution Database (DF_IDD), JPN, total population, current definition.",
        "# official: false. Built from MHLW's Comprehensive Survey of Living Conditions (triennial;",
        "# the year is the INCOME year). gini: 0–1. poverty50: % of people below 50% of median",
        "# disposable income. BREAK: METH2011 (old income definition) and METH2012 (new) are",
        "# separate columns, overlapping in 2018 — never joined. Blank = no survey that year.",
        "year,gini_meth2011,gini_meth2012,poverty50_pct_meth2011,poverty50_pct_meth2012",
    ]
    for y in years:
        cells = []
        for key in cols:
            v = out[key].get(y)
            cells.append("" if v is None else (f"{v:.3f}" if key[0] == "gini" else f"{v:.1f}"))
        lines.append(f"{y}," + ",".join(cells))
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {len(years)} rows ({years[0]}–{years[-1]}, survey years only)")
    return out


# ---------------------------------------------------------------- UNHCR
def unhcr_items(kind: str) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        def ok(body: bytes) -> None:
            p = json.loads(body)
            check(isinstance(p, dict) and isinstance(p.get("items"), list)
                  and p["items"] and all(i.get("coa") == ISO3 for i in p["items"]),
                  f"UNHCR {kind}: not a JPN items payload")
        p = json.loads(cached(f"unhcr_{kind}_p{page}.json",
                              UNHCR.format(kind=kind, page=page), PLAIN, ok))
        items += p["items"]
        if page >= int(p.get("maxPages") or 1):
            return items
        page += 1


def ival(v) -> int | None:
    if v in (None, "", "-"):
        return None
    return int(v)


def unhcr(rel: str) -> dict[str, dict[int, int]]:
    apps = unhcr_items("asylum-applications")
    decs = unhcr_items("asylum-decisions")
    cols: dict[str, dict[int, int]] = {}

    def add(col: str, year: int, v: int | None) -> None:
        if v is not None:
            cols.setdefault(col, {})
            cols[col][year] = cols[col].get(year, 0) + v

    for i in apps:
        if i["app_type"] == "N" and i["dec_level"] == "FI":
            add("applications_new_first_instance", i["year"], ival(i["applied"]))
        elif i["app_type"] == "A" and i["dec_level"] == "AR":
            add("applications_appeal", i["year"], ival(i["applied"]))
    # From 2021 UNHCR books every POSITIVE decision at level FA (final,
    # all instances combined) and writes "0" recognized/other at FI and AR.
    # Those zeros are a reporting convention, not outcomes: they are blanked
    # for any year that has an FA row, and FA gets its own columns.
    fa_years = {i["year"] for i in decs if i["dec_level"] == "FA"}
    for i in decs:
        level = {"FI": "fi", "AR": "appeal", "FA": "final"}.get(i["dec_level"])
        if level is None:
            continue
        for f in ("recognized", "other", "rejected", "closed", "total"):
            if level == "final" and f not in ("recognized", "other"):
                continue
            if (level != "final" and f in ("recognized", "other")
                    and i["year"] in fa_years):
                check(ival(i.get(f"dec_{f}")) in (0, None),
                      f"UNHCR {i['year']} {i['dec_level']}: positive {f} "
                      "alongside an FA row — the convention changed")
                continue
            add(f"decisions_{level}_{f}", i["year"], ival(i.get(f"dec_{f}")))
    order = ["applications_new_first_instance", "applications_appeal"] + [
        f"decisions_{lv}_{f}" for lv in ("fi", "appeal")
        for f in ("recognized", "other", "rejected", "closed", "total")] + [
        "decisions_final_recognized", "decisions_final_other"]
    order = [c for c in order if c in cols]
    first_fa = min(fa_years) if fa_years else None
    years = range(2006, max(max(s) for s in cols.values()) + 1)
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# UNHCR Refugee Data Finder API, country of asylum JPN. official: false. Persons/cases",
        "# per calendar year. applications_new_first_instance = app_type N at level FI;",
        "# applications_appeal = app_type A at level AR (other combinations — judicial review,",
        "# repeat — are excluded). decisions_* by level: recognized (Convention), other",
        "# (complementary protection), rejected, closed (otherwise closed). Applications,",
        "# decisions and recognitions are separate numbers, never one line. The national ISA",
        "# count is pending. Blank = no row in the API, not zero.",
        f"# BREAK {first_fa}: from {first_fa} UNHCR reports positive decisions only at level FA",
        "# (final, all instances combined) -> decisions_final_*; the FI/appeal recognized/other",
        "# cells are blank from then (the API's 0 there is a convention, not an outcome), and",
        "# FI/appeal *_total from then counts negative and closed decisions only.",
        "year," + ",".join(order),
    ]
    for y in years:
        lines.append(f"{y}," + ",".join(
            "" if cols[c].get(y) is None else str(cols[c][y]) for c in order))
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {len(years)} rows ({years[0]}–{years[-1]})")
    return cols


# ---------------------------------------------------------------- checks
def near(got, want, tol, what) -> None:
    check(got is not None and abs(got - want) <= tol,
          f"{what}: got {got}, want {want} ±{tol}")


def main() -> None:
    print("World Bank / UNDP / IMF / OECD / UNHCR comparables for Japan")
    wb = {}
    for rel, code, column, dec in WANTED:
        wb[code] = wb_series(code)
        write_wb(rel, code, column, wb[code], dec)
    hdi = hdr_hdi()
    path = ROOT / "data" / "international" / "hdi_from_undp.csv"
    lines = ["# UNDP HDR25 composite-indices complete time series, JPN. official: false.",
             "# Index 0–1, ONE vintage for every year (2023 rank 23).",
             "year,hdi"] + [f"{y},{'' if hdi.get(y) is None else f'{hdi[y]:.3f}'}"
                            for y in range(YEAR_FROM, max(hdi) + 1)]
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/international/hdi_from_undp.csv  {max(hdi) - YEAR_FROM + 1} rows "
          f"({YEAR_FROM}–{max(hdi)})")
    imf = write_imf("international/gg_fiscal_from_imf.csv")
    idd = oecd_idd("social/gini_from_oecd.csv")
    asy = unhcr("migration/asylum_from_unhcr.csv")

    # Spot values DISCOVERY.md / SOURCES.yaml verified live on 2026-10-22.
    gdp = wb["NY.GDP.MKTP.CD"]
    near(gdp.get(2024), 4.190e12, 0.005e12, "WB GDP 2024")
    near(gdp.get(2006), 4.648e12, 0.005e12, "WB GDP 2006")
    near(wb["NY.GDP.PCAP.CD"].get(2024), 33_797, 5, "WB GDP pc 2024")
    near(wb["SP.POP.TOTL"].get(2024), 123_975_371, 1_000, "WB population 2024")
    near(wb["FI.RES.TOTL.CD"].get(2024), 1_230.67e9, 1e9, "WB reserves 2024")
    near(wb["NE.TRD.GNFS.ZS"].get(2024), 44.9, 0.05, "WB openness 2024")
    check(2025 not in wb["NE.TRD.GNFS.ZS"], "WB openness 2025 should be blank")
    gini = wb["SI.POV.GINI"]
    near(gini.get(2020), 32.3, 0.05, "WB Gini 2020")
    check(min(gini) >= 2008 and max(gini) <= 2020,
          f"WB Gini span {min(gini)}–{max(gini)}, expected within 2008–2020")
    near(wb["VC.IHR.PSRC.P5"].get(2006), 0.48, 0.005, "WB homicide 2006")
    near(wb["VC.IHR.PSRC.P5"].get(2023), 0.23, 0.005, "WB homicide 2023")
    near(hdi.get(2006), 0.903, 0.0005, "HDI 2006")
    near(hdi.get(2023), 0.925, 0.0005, "HDI 2023")
    debt, nl = imf["GGXWDG_NGDP"], imf["GGXCNL_NGDP"]
    for y, want in {2006: 152.1, 2020: 228.8, 2024: 213.6, 2025: 204.8}.items():
        near(debt.get(y), want, 0.05, f"IMF gross debt {y}")
    for y, want in {2020: -9.0, 2024: -1.7, 2025: -0.7}.items():
        near(nl.get(y), want, 0.05, f"IMF net lending {y}")
    near(idd[("gini", "METH2012")].get(2018), 0.334, 0.0005, "OECD Gini 2018")
    near(idd[("gini", "METH2012")].get(2021), 0.338, 0.0005, "OECD Gini 2021")
    near(idd[("poverty50", "METH2012")].get(2018), 15.7, 0.05, "OECD poverty 2018")
    near(idd[("poverty50", "METH2012")].get(2021), 15.4, 0.05, "OECD poverty 2021")
    near(asy["applications_new_first_instance"].get(2022), 3_772, 0, "UNHCR new 2022")
    near(asy["applications_appeal"].get(2022), 4_461, 0, "UNHCR appeals 2022")
    near(asy["applications_new_first_instance"].get(2023), 13_823, 0, "UNHCR new 2023")

    # Cross-publisher magnitudes: IMF NGDPD vs World Bank GDP (two
    # compilations of the same ESRI number at slightly different rates).
    for y in (2006, 2024):
        gap = imf["NGDPD"][y] * 1e9 / gdp[y] - 1
        print(f"  cross-check GDP {y}: IMF US${imf['NGDPD'][y]:,.0f}bn vs WB "
              f"US${gdp[y] / 1e9:,.0f}bn ({gap:+.2%})")
        check(abs(gap) < 0.02, f"IMF vs WB GDP {y} differ by {gap:+.2%}")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    try:
        main()
    except FetchError as e:
        sys.exit(f"FAILED: {e}")
