#!/usr/bin/env python3
"""Refresh Russia's cross-country comparables into sidecar CSVs.

Usage:  make C=russia fetch   (or: python3 -I fetch/fetch_comparables.py)

These are the layer that makes a country legible to a reader who does not
live in it: the same quantity, computed the same way, for everyone. They
are never a substitute for a number Rosstat publishes about itself. Where
both exist — GDP, population, prices, unemployment — the national series
is the curated one and this is the cross-check, and the plate draws both
and labels the difference rather than choosing.

  World Bank    NY.GDP.MKTP.KD.ZG  real GDP growth, %
                FP.CPI.TOTL.ZG     CPI inflation, %
                NE.GDI.FTOT.ZS     gross fixed capital formation, % GDP
                SL.UEM.TOTL.ZS     unemployment, ILO modelled estimate, %
                NY.GDP.MKTP.CD     GDP, current US$
                NY.GDP.PCAP.CD     GDP per person, current US$
                NY.GDP.DEFL.KD.ZG  GDP deflator, % per year
                FI.RES.TOTL.CD     reserves including gold, current US$
                SI.POV.GINI        Gini, World Bank harmonised (0-100)
                SI.POV.NAHC        poverty headcount, national definition, %
                SI.POV.UMIC        poverty at the upper-middle-income line
                SP.POP.TOTL        population (UN WPP)
                SP.DYN.TFRT.IN     total fertility rate
                SP.DYN.CBRT.IN     crude birth rate, per 1,000
                SP.DYN.CDRT.IN     crude death rate, per 1,000
                SP.DYN.LE00.IN     life expectancy at birth
                SM.POP.NETM        net migration (UN WPP, modelled)
                SM.POP.TOTL        international migrant stock
                VC.IHR.PSRC.P5     intentional homicide, per 100,000
                SH.STA.SUIC.P5     suicide, per 100,000
                SH.STA.TRAF.P5     road traffic deaths, per 100,000
                FB.AST.NPER.ZS     bank non-performing loans, % of gross loans
                NE.EXP.GNFS.ZS     exports of goods and services, % GDP
                NE.IMP.GNFS.ZS     imports of goods and services, % GDP
  UNDP          HDI, from the HDR composite-indices file (Latin-1 file)
  IMF           NGDP_RPCH          real GDP growth, % (DataMapper/WEO) —
                                   the independent agreement line for the
                                   WB growth series; projections go in
                                   their own `_proj` column
                rev, exp, GGXCNL_NGDP, pb, ie, GGXWDG_NGDP
                                   general government, one WEO vintage
  BIS           WS_TC Q.RU.H.A.M.770.A  credit to households and NPIFS
                                   from all sectors, % of GDP, adjusted
                                   for breaks, year-end (Q4) reading

The HDR file is a single vintage covering every year, which is the point:
the HDI is recomputed for the whole back-series at each methodology
change, so a trend assembled from successive reports is partly an artefact
of the reports. One file, one vintage.

Transparency International's CPI is NOT here: both
images.transparencycdn.org/images/CPI2025-Results-and-trends.xlsx and
www.transparency.org/en/cpi/2025 answered HTTP 403 from this network on
2026-10-25, the same block the Ukraine lane recorded on 2026-10-24. It is
recorded in SOURCES.yaml meta.pending; the world plate's corruption slot
stays visibly pending rather than being filled from a republication.

Sanctions-era holes stay holes. Four series tell the story and none of
them is filled:

  · VC.IHR.PSRC.P5 stops in 2021 — Rosstat's own homicide count is not in
    the machine-readable layer (fedstat 403) and UNODC has no 2022+ row.
  · SH.STA.TRAF.P5 stops in 2019.
  · SI.POV.GINI stops in 2023.
  · The IMF's revenue and expenditure lines stop at 2024.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

WB = ("https://api.worldbank.org/v2/country/RUS/indicator/{code}"
      "?format=json&per_page=200&date=1990:2026")
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
IMF = "https://www.imf.org/external/datamapper/api/v1/{code}/RUS"
BIS = ("https://stats.bis.org/api/v1/data/WS_TC/Q.RU.H.A.M.770.A"
       "?format=csv&startPeriod=2005-Q4")
ISO3 = "RUS"
# hdr.undp.org answers 403 to the default urllib User-Agent; a browser UA
# gets 200 from both it and the World Bank.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
# www.imf.org's edge answers 403 to a UA starting with "Mozilla/5.0"
# (verified in the UK lane 2026-10-22); a plain descriptive UA gets 200.
IMF_HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}

# The window every plate shares, from country.yaml.
YEAR_FROM, YEAR_TO = 2006, 2026
LAST_FULL_YEAR = 2025

POPULATION_COMMENTS = [
    "World Bank SP.POP.TOTL (UN World Population Prospects), mid-year de-facto",
    "total. THE SEAM: Rosstat's own series (popul_1897+.xlsx) rises by 2.7m",
    "between its 2014 and 2015 rows (144.0m -> 146.7m) because Russia annexed",
    "Crimea and Sevastopol in March 2014 and began counting them; Crimea plus",
    "Sevastopol is about 2.3m people. This UN series rises by only 0.4m across",
    "the same step, so from 2015 the two lines differ by ~2.3-2.7m and the gap",
    "is territory plus the 2020-census rebase, not births. The lines are drawn",
    "separately and never spliced.",
]

WB_COMMENTS = {
    "macro/economy_from_wb.csv": [
        "World Bank WDI, harmonised comparable layer for Russia. Growth, CPI",
        "and unemployment are the World Bank's republication of Rosstat's own",
        "indices (NY.GDP.MKTP.KD.ZG 2025 = 1.00, identical to Rosstat's own",
        "101.0 index); they ride beside the national line, never instead of it.",
        "SL.UEM.TOTL.ZS is the ILO modelled estimate, not the LFS headline.",
    ],
    "demography/population_from_wb.csv": POPULATION_COMMENTS,
    "trade/trade_from_wb.csv": [
        "World Bank WDI NE.EXP.GNFS.ZS / NE.IMP.GNFS.ZS: goods AND services,",
        "national-accounts basis, % of GDP. This is not the customs series.",
        "Russia stopped publishing detailed customs statistics in 2022, so the",
        "goods-only cut is not on the canonical slot; the BoP/national-accounts",
        "basis is, and it is the one the spine names.",
    ],
    "security/security_from_wb.csv": [
        "World Bank WDI as the UNODC/WHO carrier. Homicide (VC.IHR.PSRC.P5)",
        "stops in 2021 and road deaths (SH.STA.TRAF.P5) in 2019: neither the",
        "UNODC nor the WHO rows extend past those years for Russia, and the",
        "national publishers are not machine-reachable (fedstat 403). The",
        "holes are holes.",
    ],
    "credit/household_debt_from_bis.csv": [
        "BIS total credit statistics, WS_TC, series Q.RU.H.A.M.770.A: credit to",
        "households and NPISHs from all sectors, market value, percentage of",
        "GDP, adjusted for breaks. Quarterly; the plate takes the Q4 reading of",
        "each year, which is the year-end stock the spine's slot 1 asks for.",
        "The BIS flags the series as break-adjusted; the underlying national",
        "aggregate is the Bank of Russia's, which publishes it monthly.",
    ],
    "people/gini_from_wb.csv": [
        "World Bank WDI SI.POV.GINI, 0-100, household survey based. The series",
        "stops in 2023: Rosstat's own Gini is published in the 'Уровень жизни'",
        "release, not in a machine-readable file reachable from here.",
    ],
    "fiscal/fiscal_from_imf.csv": [
        "IMF WEO (October 2026 vintage), general government: rev, exp,",
        "GGXCNL_NGDP, pb, ie, GGXWDG_NGDP. Observed years in the plain",
        "columns; WEO forecasts only in the _proj columns, never mixed.",
        "Definitions: accrual, consolidated general government — NOT the",
        "Russian federal budget, which is cash execution of one level of",
        "government and is staged separately in fiscal/federal_budget.csv.",
        "Revenue and expenditure stop at 2024; the 2025 rows are absent rather",
        "than forecast, and stay absent.",
    ],
}

# (sidecar, WB indicator, column, decimals); two indicators may share a
# sidecar, in which case they are merged on year.
WANTED = [
    ("macro/economy_from_wb.csv", "NY.GDP.MKTP.KD.ZG", "gdp_growth_pct", 2),
    ("macro/economy_from_wb.csv", "FP.CPI.TOTL.ZG", "cpi_inflation_pct", 2),
    ("macro/economy_from_wb.csv", "SL.UEM.TOTL.ZS", "unemployment_pct", 3),
    ("macro/economy_from_wb.csv", "NE.GDI.FTOT.ZS", "gfcf_pct_gdp", 2),
    ("macro/economy_from_wb.csv", "NY.GDP.DEFL.KD.ZG", "deflator_pct", 2),
    ("world/gdp_usd_from_wb.csv", "NY.GDP.MKTP.CD", "gdp_usd", 0),
    ("world/gdp_pc_from_wb.csv", "NY.GDP.PCAP.CD", "gdp_per_person_usd", 0),
    ("world/reserves_from_wb.csv", "FI.RES.TOTL.CD", "reserves_usd", 0),
    ("people/gini_from_wb.csv", "SI.POV.GINI", "gini", 1),
    ("people/poverty_from_wb.csv", "SI.POV.NAHC", "poverty_national_pct", 2),
    ("people/poverty_from_wb.csv", "SI.POV.UMIC", "poverty_umic_pct", 2),
    ("demography/population_from_wb.csv", "SP.POP.TOTL", "population", 0),
    ("demography/fertility_from_wb.csv", "SP.DYN.TFRT.IN", "tfr", 3),
    ("demography/vitals_from_wb.csv", "SP.DYN.CBRT.IN", "birth_rate_per_1000", 2),
    ("demography/vitals_from_wb.csv", "SP.DYN.CDRT.IN", "death_rate_per_1000", 2),
    ("trade/trade_from_wb.csv", "NE.EXP.GNFS.ZS", "exports_pct_gdp", 2),
    ("trade/trade_from_wb.csv", "NE.IMP.GNFS.ZS", "imports_pct_gdp", 2),
    ("mortality/mortality_from_wb.csv", "SP.DYN.CDRT.IN",
     "death_rate_per_1000", 2),
    ("mortality/mortality_from_wb.csv", "SP.DYN.LE00.IN",
     "life_expectancy", 2),
    ("security/security_from_wb.csv", "VC.IHR.PSRC.P5",
     "homicide_per_100k", 3),
    ("security/security_from_wb.csv", "SH.STA.SUIC.P5",
     "suicide_per_100k", 2),
    ("security/security_from_wb.csv", "SH.STA.TRAF.P5",
     "road_deaths_per_100k", 2),
    ("credit/npl_from_wb.csv", "FB.AST.NPER.ZS", "npl_pct_loans", 2),
    ("migration/net_migration_from_wb.csv", "SM.POP.NETM",
     "net_migration", 0),
    ("migration/migrant_stock_from_wb.csv", "SM.POP.TOTL",
     "migrant_stock", 0),
]

# The IMF fiscal block: one vintage (WEO October 2026) for every column,
# observed years in the plain column and WEO forecasts only in `_proj`.
IMF_FISCAL = [
    ("rev", "revenue_pct_gdp", 2),
    ("exp", "expenditure_pct_gdp", 2),
    ("GGXCNL_NGDP", "balance_pct_gdp", 2),
    ("pb", "primary_balance_pct_gdp", 2),
    ("ie", "interest_pct_gdp", 2),
    ("GGXWDG_NGDP", "debt_pct_gdp", 2),
]


def wb_series(code: str) -> dict[int, float]:
    """One World Bank indicator for Russia as {year: value}.

    The API answers a bad request with a JSON *object* carrying a message
    rather than the two-element array of a good one, so the shape is
    checked before anything is cached — a cached error page is worse than
    no cache, because it survives the retry that would have fixed it.
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"wb_{code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        for attempt in range(4):
            try:
                req = urllib.request.Request(WB.format(code=code),
                                             headers=HEADERS)
                with urllib.request.urlopen(req, timeout=90) as r:
                    payload = json.loads(r.read())
                if not (isinstance(payload, list) and len(payload) > 1):
                    raise ValueError("not an indicator response")
                cache_file.write_text(json.dumps(payload))
                break
            except Exception as e:  # noqa: BLE001
                print(f"  {code} attempt {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        else:
            return {}
    out = {}
    if isinstance(payload[1], list):
        for row in payload[1]:
            if row.get("value") is not None:
                out[int(row["date"])] = float(row["value"])
    return out


def hdr_hdi() -> dict[int, float]:
    """Russia's HDI by year, out of the HDR composite-indices file.

    One row per country and one COLUMN per year, with sibling columns for
    the rank and the sex-disaggregated values — so the key has to match
    `hdi_YYYY` exactly. Matching on the prefix pulls in `hdi_rank_2023`
    and silently writes a rank where a value belongs. The file is
    Latin-1, not UTF-8: decode it explicitly.
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "hdr25_series.csv"
    if not cache_file.exists():
        try:
            req = urllib.request.Request(HDR, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
            raw.decode("latin-1")  # validated before the bytes are cached
            cache_file.write_bytes(raw)
        except Exception as e:  # noqa: BLE001
            print(f"  HDR fetch failed: {e}", file=sys.stderr)
            return {}
    out: dict[int, float] = {}
    for row in csv.DictReader(io.StringIO(
            cache_file.read_bytes().decode("latin-1"))):
        if (row.get("iso3") or row.get("ISO3")) != ISO3:
            continue
        for key, value in row.items():
            if not key or value in (None, "", ".."):
                continue
            name = key.lower()
            year = name.rsplit("_", 1)[-1]
            if year.isdigit() and name == f"hdi_{year}":
                out[int(year)] = float(value)
        break
    return out


def imf_series(code: str) -> dict[int, float]:
    """One IMF WEO indicator for Russia as {year: value}, forecasts included."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"imf_{code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        for attempt in range(4):
            try:
                req = urllib.request.Request(IMF.format(code=code),
                                             headers=IMF_HEADERS)
                with urllib.request.urlopen(req, timeout=90) as r:
                    payload = json.loads(r.read())
                values = payload.get("values", {}).get(code, {}).get(ISO3)
                if not isinstance(values, dict) or not values:
                    raise ValueError("not a DataMapper indicator response")
                cache_file.write_text(json.dumps(payload))
                break
            except Exception as e:  # noqa: BLE001
                print(f"  {code} attempt {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        else:
            return {}
    values = payload.get("values", {}).get(code, {}).get(ISO3, {})
    return {int(y): float(v) for y, v in values.items() if v is not None}


def bis_q4() -> dict[int, float]:
    """Household credit as % of GDP, the Q4 reading of each year.

    The BIS publishes this quarterly and the spine's credit slot 1 asks for
    a year-end stock, so the Q4 observation is the year's value. A year
    whose Q4 is missing stays missing rather than borrowing Q3: the
    difference between them is a quarter of a credit cycle.
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "bis_ws_tc_ru.csv"
    if not cache_file.exists():
        try:
            req = urllib.request.Request(BIS, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            text = raw.decode("utf-8")
            if "TIME_PERIOD" not in text:
                raise ValueError("not a BIS CSV")
            cache_file.write_text(text)
        except Exception as e:  # noqa: BLE001
            print(f"  BIS fetch failed: {e}", file=sys.stderr)
            return {}
    out: dict[int, float] = {}
    for row in csv.DictReader(io.StringIO(cache_file.read_text())):
        period = (row.get("TIME_PERIOD") or "").strip()
        value = (row.get("OBS_VALUE") or "").strip()
        if not period.endswith("-Q4") or not value:
            continue
        year = int(period.split("-")[0])
        out[year] = float(value)
    return out


def write(rel: str, columns: list[tuple[str, dict[int, float], int]]) -> None:
    """A sidecar: `#` comments, then `year` plus one column per series.

    Columns of one file are merged on year; a year one series does not
    cover is an empty cell, never a zero or a carried value.
    """
    if not all(series for _, series, _ in columns):
        print(f"  !! {rel}: a series came back empty, nothing written",
              file=sys.stderr)
        return
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in WB_COMMENTS.get(rel, [])]
    lines.append("year," + ",".join(c for c, _, _ in columns))
    years = sorted(set().union(*(s for _, s, _ in columns)))
    rows = 0
    for y in years:
        if not YEAR_FROM <= y <= YEAR_TO:
            continue
        cells = [f"{series[y]:.{dec}f}" if y in series else ""
                 for _, series, dec in columns]
        lines.append(f"{y}," + ",".join(cells))
        rows += 1
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {rows} rows")


def write_imf(rel: str, code: str, column: str, dec: int) -> dict[int, float]:
    """The IMF sidecar: observed years in one column, projections apart."""
    series = imf_series(code)
    if not series:
        print(f"  !! {rel}: nothing fetched", file=sys.stderr)
        return {}
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in WB_COMMENTS.get(rel, [])]
    lines.append(f"year,{column},{column}_proj")
    rows = 0
    for y in sorted(series):
        if not YEAR_FROM <= y <= YEAR_TO:
            continue
        observed = y <= LAST_FULL_YEAR
        row = (f"{series[y]:.{dec}f}", "") if observed \
            else ("", f"{series[y]:.{dec}f}")
        assert (row[0] == "") != (row[1] == ""), \
            f"{code} {y}: observed/projected disjointness broken"
        lines.append(f"{y},{row[0]},{row[1]}")
        rows += 1
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {rows} rows "
          f"(observed <= {LAST_FULL_YEAR}, projections apart)")
    return series


def write_fiscal() -> dict[str, dict[int, float]]:
    """The IMF fiscal sidecar: six series, one vintage, projections apart."""
    series = {code: imf_series(code) for code, _, _ in IMF_FISCAL}
    if not all(series.values()):
        print("  !! fiscal: a series came back empty, nothing written",
              file=sys.stderr)
        return {}
    path = ROOT / "data" / "fiscal" / "fiscal_from_imf.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    obs = [(col, series[code], dec) for code, col, dec in IMF_FISCAL]
    proj = [("balance_pct_gdp_proj", series["GGXCNL_NGDP"], 2),
            ("debt_pct_gdp_proj", series["GGXWDG_NGDP"], 2)]
    lines = [f"# {c}" for c in WB_COMMENTS["fiscal/fiscal_from_imf.csv"]]
    lines.append("year," + ",".join(c for c, _, _ in obs + proj))
    years = sorted(set().union(*(s for _, s, _ in obs + proj)))
    rows = 0
    for y in years:
        if not YEAR_FROM <= y <= YEAR_TO:
            continue
        cells = [f"{s[y]:.{dec}f}" if (y <= LAST_FULL_YEAR and y in s) else ""
                 for _, s, dec in obs]
        cells += [f"{s[y]:.{dec}f}" if (y > LAST_FULL_YEAR and y in s) else ""
                  for _, s, dec in proj]
        lines.append(f"{y}," + ",".join(cells))
        rows += 1
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/fiscal/fiscal_from_imf.csv  {rows} rows "
          f"(observed <= {LAST_FULL_YEAR}, projections apart)")
    return {code: series[code] for code, _, _ in IMF_FISCAL}


def verify(wb: dict[str, dict[int, float]], hdi: dict[int, float],
           imf_growth: dict[int, float],
           fiscal: dict[str, dict[int, float]] | None = None,
           bis: dict[int, float] | None = None) -> None:
    """Pin the numbers the discovery pass verified live 2026-10-25, so a
    silent revision, a unit change or a truncated payload fails here
    instead of landing in a sidecar."""
    growth = wb["NY.GDP.MKTP.KD.ZG"]
    # Rosstat's own physical-volume index for the same years, read from
    # VVP_god_s1995-2025.xlsx: 2022 = 98.56, 2025 = 101.00.
    assert abs(growth[2022] - -1.44) < 0.02, f"WB growth 2022: {growth.get(2022)}"
    assert abs(growth[2025] - 1.00) < 0.02, f"WB growth 2025: {growth.get(2025)}"
    assert abs(imf_growth[2022] - growth[2022]) < 0.6, \
        f"IMF growth 2022 {imf_growth.get(2022)} vs WB {growth.get(2022)}"
    # DEFINITION TRAP, pinned so a silent alignment fails here: the World
    # Bank's CPI is the ANNUAL AVERAGE change; Rosstat's headline is the
    # December-to-December one. 2008: WB 14.11 vs Rosstat 113.28 -> 13.28.
    # 2015: WB 15.53 vs Rosstat 112.91 -> 12.91. Both are correct.
    cpi = wb["FP.CPI.TOTL.ZG"]
    assert abs(cpi[2008] - 14.11) < 0.05, f"WB CPI 2008: {cpi.get(2008)}"
    assert abs(cpi[2015] - 15.53) < 0.05, f"WB CPI 2015: {cpi.get(2015)}"
    assert cpi[2008] - 13.28 > 0.5 and cpi[2015] - 12.91 > 0.5, \
        "the average-vs-December CPI gap vanished; re-check the definition"
    gdp = wb["NY.GDP.MKTP.CD"]
    assert abs(gdp[2013] / 1e9 - 2292.5) < 1.0, f"WB GDP 2013: {gdp.get(2013)}"
    assert abs(gdp[2015] / 1e9 - 1363.5) < 1.0, f"WB GDP 2015: {gdp.get(2015)}"
    population = wb["SP.POP.TOTL"]
    assert abs(population[2021] - 144_746_762) < 1_000, \
        f"WB population 2021: {population.get(2021)}"
    assert population[2015] < 145_000_000, "WB population looks spliced onto Rosstat"
    unemployment = wb["SL.UEM.TOTL.ZS"]
    assert abs(unemployment[2009] - 8.30) < 0.05, \
        f"WB unemployment 2009: {unemployment.get(2009)}"
    assert abs(hdi[2006] - 0.791) < 0.002, f"UNDP hdi_2006: {hdi.get(2006)}"
    assert max(hdi) == 2023 and abs(hdi[2023] - 0.832) < 0.002, \
        f"UNDP HDI row set changed: {sorted(hdi)[-3:]}"
    reserves = wb["FI.RES.TOTL.CD"]
    assert reserves[2024] / 1e9 > 600, f"WB reserves 2024: {reserves.get(2024)}"
    # Trade: the goods-and-services lines the plate draws.
    exports = wb["NE.EXP.GNFS.ZS"]
    assert abs(exports[2022] - 27.5) < 1.5, f"WB exports 2022: {exports.get(2022)}"
    # The sanctions-era stops, asserted rather than assumed: a revived row
    # set would mean the source changed, not that the gap closed.
    assert max(wb["VC.IHR.PSRC.P5"]) == 2021, \
        f"homicide row set changed: {sorted(wb['VC.IHR.PSRC.P5'])[-3:]}"
    assert max(wb["SH.STA.TRAF.P5"]) == 2019, \
        f"road-death row set changed: {sorted(wb['SH.STA.TRAF.P5'])[-3:]}"
    if fiscal:
        assert abs(fiscal["rev"][2024] - 35.27) < 0.02, \
            f"IMF revenue 2024: {fiscal['rev'].get(2024)}"
        assert abs(fiscal["GGXCNL_NGDP"][2023] - -2.20) < 0.02, \
            f"IMF balance 2023: {fiscal['GGXCNL_NGDP'].get(2023)}"
        assert abs(fiscal["GGXWDG_NGDP"][2020] - 19.20) < 0.02, \
            f"IMF debt 2020: {fiscal['GGXWDG_NGDP'].get(2020)}"
    if bis:
        assert abs(bis[2024] - 21.5) < 0.2, f"BIS household credit 2024: {bis.get(2024)}"
        assert abs(bis[2006] - 8.2) < 0.2, f"BIS household credit 2006: {bis.get(2006)}"


def main() -> None:
    print("World Bank / UNDP / IMF / BIS comparables for Russia")
    fetched = {code: wb_series(code) for _, code, _, _ in WANTED}
    sidecars: dict[str, list[tuple[str, dict[int, float], int]]] = {}
    for rel, code, column, dec in WANTED:
        sidecars.setdefault(rel, []).append((column, fetched[code], dec))
    for rel, columns in sidecars.items():
        write(rel, columns)
    hdi = hdr_hdi()
    write("world/hdi_from_undp.csv", [("hdi", hdi, 3)])
    imf_growth = write_imf("macro/growth_from_imf.csv", "NGDP_RPCH",
                           "gdp_growth_pct", 2)
    fiscal = write_fiscal()
    bis = bis_q4()
    write("credit/household_debt_from_bis.csv",
          [("household_debt_pct_gdp", bis, 1)])
    if all(fetched.values()) and hdi and imf_growth and fiscal and bis:
        verify(fetched, hdi, imf_growth, fiscal, bis)
        print("All discovery anchors verified.")
    else:
        print("!! incomplete fetch — verification skipped, sidecars partial",
              file=sys.stderr)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
