#!/usr/bin/env python3
"""Refresh the cross-country comparables for Ukraine into sidecar CSVs.

Usage:  make C=ukraine fetch   (or: python3 -I fetch/fetch_comparables.py)

These are the layer that makes a country legible to a reader who does not
live in it: the same quantity, computed the same way, for everyone. They
are never a substitute for a number Ukraine publishes about itself. Where
both exist — GDP, population, the Gini — the national series is the
curated one and this is the cross-check, and the plate draws both and
labels the difference rather than choosing.

  World Bank    NY.GDP.MKTP.KD.ZG  real GDP growth, %
                FP.CPI.TOTL.ZG     CPI inflation, %
                NE.GDI.FTOT.ZS     gross fixed capital formation, % GDP
                SL.UEM.TOTL.ZS     unemployment, ILO modelled estimate, %
                NY.GDP.MKTP.CD     GDP, current US$
                NY.GDP.MKTP.CN     GDP, current UAH (cross-check only:
                                   2024 = 7,662,376 mn, byte-identical to
                                   Ukrstat's published figure)
                NY.GDP.PCAP.CD     GDP per person, current US$
                FI.RES.TOTL.CD     reserves including gold, current US$
                SI.POV.GINI        Gini, World Bank harmonised (0-100)
                SP.POP.TOTL        population (UN WPP; INCLUDES Crimea and
                                   Sevastopol throughout — see the sidecar
                                   comment; never spliced with Ukrstat's
                                   registered count excl. TOT)
  UNDP          HDI, from the HDR composite-indices file (Latin-1 file)
  IMF           NGDP_RPCH          real GDP growth, % (DataMapper/WEO) —
                                   the independent agreement line for the
                                   WB growth series; projections go in
                                   their own `_proj` column

The HDR file is a single vintage covering every year, which is the point:
the HDI is recomputed for the whole back-series at each methodology
change, so a trend assembled from successive reports is partly an
artefact of the reports. One file, one vintage.

Wartime holes stay holes: the ILO unemployment estimate stops in 2021
(the national labour-force survey is suspended) and the WB Gini stops in
2020. Nothing here interpolates, forward-fills or zero-fills.

Eurostat is deliberately NOT in this fetcher: demo_gind's UA slice stops
in 2022 and every other UA slice probed on 2026-10-24 came back
well-formed EMPTY (the UK lesson: empty, not 404). The comparables layer
for Ukraine is World Bank / UNDP / IMF only; any Eurostat residual
belongs to fetch_harmonised.py and its own manifest entries.

Transparency International's CPI is not here either (no stable machine
endpoint, 2012 methodology break, and the CDN 403s from the discovery
network) — it is a fetch_spine.py concern per SOURCES.yaml.
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

WB = ("https://api.worldbank.org/v2/country/UKR/indicator/{code}"
      "?format=json&per_page=200&date=2006:2026")
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
IMF = "https://www.imf.org/external/datamapper/api/v1/{code}/UKR"
ISO3 = "UKR"
# hdr.undp.org answers 403 to the default urllib User-Agent; a browser UA
# gets 200 from both it and the World Bank.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
# www.imf.org's edge answers 403 to any UA starting with "Mozilla/5.0"
# (verified in the UK lane 2026-10-22); a plain descriptive UA gets 200.
IMF_HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}

# The window every plate shares, from country.yaml. The IMF sidecar
# splits at last_full_year: 2026+ are WEO projections.
YEAR_FROM, YEAR_TO = 2006, 2026
LAST_FULL_YEAR = 2025

POPULATION_COMMENTS = [
    "World Bank SP.POP.TOTL (UN World Population Prospects), mid-year de-facto total.",
    "TERRITORIAL CONVENTION: this series INCLUDES Crimea and Sevastopol",
    "throughout (2021 = 44,298,640; 2022 = 41,048,766). It is NOT the national",
    "registered count: Ukrstat EXCLUDES the temporarily occupied territories from",
    "2014 and stops at 1-Jan-2022 = 41,167,335. The ~3.1mn gap between the two",
    "lines is territory, not error — two labelled lines, never a splice.",
]

GDP_UAH_COMMENTS = [
    "World Bank NY.GDP.MKTP.CN, current-price GDP in hryvnia (units, not",
    "millions). Cross-check only: 2024 = 7,662,376 mn UAH, byte-identical to",
    "Ukrstat's published figure — evidence for the national-accounts line in",
    "macro/gdp_ukrstat.csv, not a series the plates draw directly.",
]

IMF_GROWTH_COMMENTS = [
    "IMF DataMapper NGDP_RPCH (WEO, current vintage): the independent",
    "agreement line for the WB growth series (2022 = -28.8 on both). Years",
    "past last_full_year are WEO staff projections and live only in",
    "gdp_growth_pct_proj — observed and projected never share a row.",
]

# (sidecar, WB indicator, column, decimals); two indicators may share a
# sidecar, in which case they are merged on year.
WANTED = [
    ("macro/growth_prices_from_wb.csv", "NY.GDP.MKTP.KD.ZG", "gdp_growth_pct", 2),
    ("macro/growth_prices_from_wb.csv", "FP.CPI.TOTL.ZG", "cpi_inflation_pct", 2),
    ("macro/economy_from_wb.csv", "NE.GDI.FTOT.ZS", "gfcf_pct_gdp", 2),
    ("macro/economy_from_wb.csv", "SL.UEM.TOTL.ZS", "unemployment_pct", 3),
    ("macro/gdp_uah_from_wb.csv", "NY.GDP.MKTP.CN", "gdp_uah", 0),
    ("world/gdp_usd_from_wb.csv", "NY.GDP.MKTP.CD", "gdp_usd", 0),
    ("world/gdp_pc_from_wb.csv", "NY.GDP.PCAP.CD", "gdp_per_person_usd", 0),
    ("world/reserves_from_wb.csv", "FI.RES.TOTL.CD", "reserves_usd", 0),
    ("people/gini_from_wb.csv", "SI.POV.GINI", "gini", 1),
    ("demography/population_from_wb.csv", "SP.POP.TOTL", "population", 0),
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
    ("migration/net_migration_from_wb.csv", "SM.POP.NETM",
     "net_migration", 0),
    ("migration/migrant_stock_from_wb.csv", "SM.POP.TOTL",
     "migrant_stock", 0),
]

# The IMF fiscal block: one vintage (WEO October 2026) for every column,
# observed years in the plain column and WEO forecasts only in `_proj`.
# Interest paid is a published WEO indicator (`ie`), not a subtraction —
# the difference between the overall and the primary balance would mix
# two rounded series.
IMF_FISCAL = [
    ("rev", "revenue_pct_gdp", 2),
    ("exp", "expenditure_pct_gdp", 2),
    ("GGXCNL_NGDP", "balance_pct_gdp", 2),
    ("pb", "primary_balance_pct_gdp", 2),
    ("ie", "interest_pct_gdp", 2),
    ("GGXWDG_NGDP", "debt_pct_gdp", 2),
]

COMMENTS = {
    "demography/population_from_wb.csv": POPULATION_COMMENTS,
    "macro/gdp_uah_from_wb.csv": GDP_UAH_COMMENTS,
    "macro/growth_from_imf.csv": IMF_GROWTH_COMMENTS,
    "fiscal/fiscal_from_imf.csv": [
        "IMF WEO (October 2026 vintage), general government: rev, exp,",
        "GGXCNL_NGDP, pb, ie, GGXWDG_NGDP. Observed years in the plain",
        "columns; WEO forecasts only in the _proj columns, never mixed.",
        "2023: expenditure 73.4% of GDP and a -19.3% overall balance —",
        "the war budget; 2024 gross debt 89.7%, 2025 107.1%.",
    ],
}


def wb_series(code: str) -> dict[int, float]:
    """One World Bank indicator for Ukraine as {year: value}.

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
    """Ukraine's HDI by year, out of the HDR composite-indices file.

    One row per country and one COLUMN per year, with sibling columns for
    the rank and the sex-disaggregated values — so the key has to match
    `hdi_YYYY` exactly. Matching on the prefix pulls in `hdi_rank_2023`
    and silently writes a rank where a value belongs. The file is
    Latin-1, not UTF-8 — decode it explicitly (a replacement-character
    decode would mangle the country names and still parse, hiding the
    encoding bug).
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
    """One IMF WEO indicator for Ukraine as {year: value}, forecasts included.

    The DataMapper API answers with {"values": {<code>: {"UKR":
    {"1997": ...}}}. A bad indicator or country answers with an empty or
    differently-shaped object, so the nesting is walked explicitly and
    checked before caching, same rule as the World Bank payload.
    """
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
    lines = [f"# {c}" for c in COMMENTS.get(rel, [])]
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
    """The IMF sidecar: observed years in one column, projections apart.

    Every year carries exactly one of `<col>` / `<col>_proj`; the other is
    left empty. Years up to last_full_year are outturn; anything later is
    a WEO forecast and goes only into the `_proj` column, so a projection
    can never be drawn as observed by accident. The disjointness is
    asserted, not just constructed.
    """
    series = imf_series(code)
    if not series:
        print(f"  !! {rel}: nothing fetched", file=sys.stderr)
        return {}
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in COMMENTS.get(rel, [])]
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
    lines = [f"# {c}" for c in COMMENTS["fiscal/fiscal_from_imf.csv"]]
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
           fiscal: dict[str, dict[int, float]] | None = None) -> None:
    """Pin the numbers the discovery pass verified live 2026-10-24, so a
    silent revision, a unit change or a truncated payload fails here
    instead of landing in a sidecar."""
    growth = wb["NY.GDP.MKTP.KD.ZG"]
    assert abs(growth[2022] - -28.76) < 0.01, \
        f"WB growth 2022: {growth.get(2022)}"
    assert abs(growth[2023] - 5.53) < 0.01, \
        f"WB growth 2023: {growth.get(2023)}"
    assert abs(growth[2025] - 1.82) < 0.01, \
        f"WB growth 2025: {growth.get(2025)}"
    # The IMF's NGDP_RPCH agrees on the invasion year (issue anchor −28.8).
    assert abs(imf_growth[2022] - growth[2022]) < 0.15, \
        f"IMF growth 2022 {imf_growth.get(2022)} vs WB {growth.get(2022)}"
    cpi = wb["FP.CPI.TOTL.ZG"]
    assert abs(cpi[2025] - 12.73) < 0.02, f"WB CPI 2025: {cpi.get(2025)}"
    gdp = wb["NY.GDP.MKTP.CD"]
    assert abs(gdp[2024] / 1e9 - 190.8) < 0.2, \
        f"WB GDP 2024: {gdp.get(2024)}"
    assert abs(gdp[2025] / 1e9 - 214.2) < 0.2, \
        f"WB GDP 2025: {gdp.get(2025)}"
    # Byte-identical to Ukrstat's published 7,662,376 million UAH.
    gdp_uah = wb["NY.GDP.MKTP.CN"]
    assert abs(gdp_uah[2024] - 7_662_376_000_000) < 500_000, \
        f"WB GDP (UAH) 2024: {gdp_uah.get(2024)}"
    population = wb["SP.POP.TOTL"]
    assert abs(population[2006] - 47_278_694) < 1_000, \
        f"WB population 2006: {population.get(2006)}"
    assert abs(population[2021] - 44_298_640) < 1_000, \
        f"WB population 2021 (incl. Crimea): {population.get(2021)}"
    assert abs(population[2025] - 38_980_376) < 1_000, \
        f"WB population 2025: {population.get(2025)}"
    # The ILO modelled estimate STOPS in 2021 (the wartime LFS
    # suspension): assert the hole was not filled by a revived or
    # silently extended series.
    unemployment = wb["SL.UEM.TOTL.ZS"]
    assert max(unemployment) == 2021, \
        f"WB unemployment row set changed: {sorted(unemployment)[-3:]}"
    assert abs(unemployment[2021] - 9.834) < 0.005, \
        f"WB unemployment 2021: {unemployment.get(2021)}"
    gfcf = wb["NE.GDI.FTOT.ZS"]
    assert abs(gfcf[2025] - 19.36) < 0.05, f"WB GFCF 2025: {gfcf.get(2025)}"
    reserves = wb["FI.RES.TOTL.CD"]
    assert abs(reserves[2025] / 1e9 - 57.27) < 0.1, \
        f"WB reserves 2025: {reserves.get(2025)}"
    # The WB Gini (0-100) ends in 2020; the wartime hole stays a hole.
    gini = wb["SI.POV.GINI"]
    assert max(gini) == 2020 and abs(gini[2020] - 25.6) < 0.05, \
        f"WB Gini row set changed: {sorted(gini)[-3:]}"
    assert abs(hdi[2006] - 0.762) < 0.001, f"UNDP hdi_2006: {hdi.get(2006)}"
    assert max(hdi) == 2023 and abs(hdi[2023] - 0.779) < 0.001, \
        f"UNDP HDI row set changed: {sorted(hdi)[-3:]}"
    # Trade: the goods-and-services lines the plate draws.
    exports = wb["NE.EXP.GNFS.ZS"]
    imports = wb["NE.IMP.GNFS.ZS"]
    assert abs(exports[2025] - 25.33) < 0.02, f"WB exports 2025: {exports.get(2025)}"
    assert abs(imports[2025] - 51.85) < 0.02, f"WB imports 2025: {imports.get(2025)}"
    # Mortality: crude death rate and life expectancy, latest full year.
    deaths = wb["SP.DYN.CDRT.IN"]
    assert abs(deaths[2024] - 13.6) < 0.02, f"WB death rate 2024: {deaths.get(2024)}"
    assert abs(wb["SP.DYN.LE00.IN"][2024] - 74.69) < 0.02, \
        f"WB life expectancy 2024: {wb['SP.DYN.LE00.IN'].get(2024)}"
    if fiscal:
        # The war budget, pinned: 2023 expenditure 73.4% of GDP and an
        # overall balance of -19.3%; 2025 gross debt 107.1%.
        assert abs(fiscal["rev"][2024] - 54.06) < 0.02, \
            f"IMF revenue 2024: {fiscal['rev'].get(2024)}"
        assert abs(fiscal["exp"][2023] - 73.40) < 0.02, \
            f"IMF expenditure 2023: {fiscal['exp'].get(2023)}"
        assert abs(fiscal["GGXCNL_NGDP"][2023] - -19.3) < 0.02, \
            f"IMF balance 2023: {fiscal['GGXCNL_NGDP'].get(2023)}"
        assert abs(fiscal["GGXWDG_NGDP"][2025] - 107.1) < 0.02, \
            f"IMF debt 2025: {fiscal['GGXWDG_NGDP'].get(2025)}"


def main() -> None:
    print("World Bank / UNDP / IMF comparables for Ukraine")
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
    if all(fetched.values()) and hdi and imf_growth and fiscal:
        verify(fetched, hdi, imf_growth, fiscal)
        print("All discovery anchors verified.")
    else:
        print("!! incomplete fetch — verification skipped, sidecars partial",
              file=sys.stderr)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
