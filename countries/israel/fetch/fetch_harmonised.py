#!/usr/bin/env python3
"""Refresh the harmonised cross-country series for Israel into sidecars.

Usage:  python3 -I countries/israel/fetch/fetch_harmonised.py

Israel's national statistical office (CBS) is unreachable from scripted
clients (SOURCES.yaml meta.pending), so every spine slot the national
office would fill draws its harmonised line here: the World Bank, the
IMF, UNDP and the OECD, each fetched once, shape-checked, spot-checked
and staged beside the parked national series. It is never a substitute
for a CBS number and nothing here is spliced with one; when CBS returns
the plate draws both and labels the difference (SOURCING §4).

  World Bank  WDI: GDP and GDP per person (current US$), reserves, GFCF,
              unemployment (ILO modelled), CPI inflation, exports and
              imports (% of GDP), population (total and female),
              fertility, crude birth and death rates, net migration (a
              count), homicide (UNODC), suicide and road deaths (WHO),
              the annual-average FX rate (PA.NUS.FCRF, the FX-history
              stopgap while the BoI daily file is dead)
  IMF         DataMapper (WEO + Fiscal Monitor): real GDP growth, CPI
              inflation, general-government revenue, expenditure,
              balance and gross debt
  UNDP        HDR25 composite indices: the whole HDI back-series from
              one vintage (HDR recomputes history at each methodology
              change, so one vintage only)
  OECD        SDMX REST DSD_LFS@DF_IALFS_INDIC: Israel's own LFS on the
              OECD harmonised key (quarterly to 2026-Q2 in the payload;
              the annual observations are what this sidecar stages)

Not fetched here, and why:
  BIS WS_TC / WS_DSR    Israel is not in the BIS credit coverage (the
                        API answers "No results for query", checked
                        2026-10-22); the credit chapter's national side
                        is Bank of Israel and is parked.
  OECD IDD (Gini)       flow version not resolved (meta.pending).

Quirks verified live 2026-10-22 and handled below:
  * IMF DataMapper ignores the country path segment and returns every
    country — filter client-side, and check the payload holds
    values[code][ISR] before believing it.
  * The current WEO vintage (source label: World Economic Outlook,
    October 2026) says Israel 2008 +3.2, 2009 +1.2. SOURCES.yaml's
    discovery note recorded +3.8/-2.8 from the same endpoint; that
    pair is Sudan's (SDN) row — the client-side-filter trap firing
    on its author. The 2008-09 recession band's annual-data argument
    does not hold on the current vintage; the bands owner must revisit
    it (recorded in SOURCES.yaml, not fudged here).
  * OECD SDMX: nine key segments (ISR + eight dots), response_format
    is not a parameter (Accept header only), dimensionAtObservation
    accepts only the DSD's own dimensions.
  * A DataMapper code it does not know answers 200 with the country
    list — the shape check is that values[code][ISR] exists.

Every sidecar is written only after every series has passed its shape
check, its spot value and its cross-check against an independent
publisher; a fetch that cannot confirm what it pulled writes nothing.
Holes stay blank: nothing is interpolated, spliced or projected — the
WEO's projection years (to 2031) are cut, not kept in an adjacent
column.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

NAME = "Israel"
ISO3 = "ISR"

# Series this country stages from another fetcher, so not fetched twice.
WB_SKIP: dict[str, str] = {}

# (sidecar, column, year, value): one known value per series, read off
# the publisher on 2026-10-22, the current vintage.
SPOT = [
    ("international/world_from_wb.csv", "gdp_usd", 2024, 542284494490.778),
    ("international/world_from_wb.csv", "gdp_per_person_usd", 2024, 54216.5218),
    ("international/world_from_wb.csv", "reserves_usd", 2024, 214543676669.814),
    ("macro/economy_from_wb.csv", "gfcf_pct_gdp", 2019, 23.1324217345266),
    ("macro/economy_from_wb.csv", "unemployment_pct", 2024, 3.595),
    ("macro/economy_from_wb.csv", "cpi_inflation_pct", 2022, 4.41162725488371),
    ("trade/trade_from_wb.csv", "exports_pct_gdp", 2024, 28.399007008222),
    ("trade/trade_from_wb.csv", "imports_pct_gdp", 2024, 25.9832493695112),
    ("demography/demography_from_wb.csv", "population", 2024, 10002200.0),
    ("demography/demography_from_wb.csv", "population", 2025, 10122800.0),
    ("demography/demography_from_wb.csv", "population_female", 2024, 5021989.0),
    ("demography/demography_from_wb.csv", "fertility", 2023, 2.85),
    ("demography/demography_from_wb.csv", "birth_rate_per_1000", 2023, 18.6),
    ("demography/demography_from_wb.csv", "death_rate_per_1000", 2023, 5.2),
    ("demography/demography_from_wb.csv", "net_migration", 2024, 10612.0),
    ("security/security_from_wb.csv", "homicide_per_100k", 2021, 1.9344902218508),
    ("security/security_from_wb.csv", "suicide_per_100k", 2019, 5.03),
    ("security/security_from_wb.csv", "road_deaths_per_100k", 2019, 3.9),
    ("markets/usdils_from_wb.csv", "ils_per_usd", 2024, 3.69971964970892),
    ("markets/usdils_from_wb.csv", "ils_per_usd", 2025, 3.45189166666666),
    ("macro/gdp_growth_from_imf.csv", "gdp_growth_pct", 2008, 3.2),
    ("macro/gdp_growth_from_imf.csv", "gdp_growth_pct", 2009, 1.2),
    ("macro/gdp_growth_from_imf.csv", "gdp_growth_pct", 2020, -1.9),
    ("macro/gdp_growth_from_imf.csv", "gdp_growth_pct", 2024, 1.7),
    ("macro/gdp_growth_from_imf.csv", "gdp_growth_pct", 2025, 3.5),
    ("macro/cpi_inflation_from_imf.csv", "cpi_inflation_pct", 2022, 4.4),
    ("macro/cpi_inflation_from_imf.csv", "cpi_inflation_pct", 2024, 3.1),
    ("fiscal/general_government_from_imf.csv", "revenue_pct_gdp", 2024, 35.648523533676),
    ("fiscal/general_government_from_imf.csv", "expenditure_pct_gdp", 2024, 43.721115833044),
    ("fiscal/general_government_from_imf.csv", "balance_pct_gdp", 2024, -8.0725922993677),
    ("fiscal/general_government_from_imf.csv", "gross_debt_pct_gdp", 2020, 71.4),
    ("fiscal/general_government_from_imf.csv", "gross_debt_pct_gdp", 2024, 67.7),
    ("international/hdi_from_undp.csv", "hdi", 2006, 0.867),
    ("international/hdi_from_undp.csv", "hdi", 2023, 0.919),
    ("international/hdi_from_undp.csv", "hdi_rank_2023", 2023, 27.0),
    ("social/labour_from_oecd.csv", "unemployment_pct", 2006, 8.4),
    ("social/labour_from_oecd.csv", "unemployment_pct", 2020, 4.333333),
    ("social/labour_from_oecd.csv", "youth_unemployment_pct", 2024, 4.64),
    ("social/labour_from_oecd.csv", "labour_force_thousands", 2006, 2810.0),
]

# (label, sidecar A, column A, year, sidecar B, column B, scale, tolerance):
# two staged series from different publishers measuring the same thing.
# A tolerance of None marks a pair that differs by definition — printed,
# not asserted.
CROSS = [
    ("GDP per person (WB GDP / WB population vs WB PCAP series)",
     "international/world_from_wb.csv", "gdp_usd", 2024,
     "international/world_from_wb.csv", "gdp_per_person_usd", None,
     ("rel", 0.01)),
    ("Real GDP growth (IMF WEO vs WB national accounts)",
     "macro/gdp_growth_from_imf.csv", "gdp_growth_pct", 2020,
     "macro/gdp_growth_from_wb_xcheck.csv", "gdp_growth_pct", 1, ("abs", 1.0)),
    ("CPI inflation (IMF WEO vs WB republished CPI)",
     "macro/cpi_inflation_from_imf.csv", "cpi_inflation_pct", 2022,
     "macro/economy_from_wb.csv", "cpi_inflation_pct", 1, ("abs", 0.6)),
    ("Gross debt (WEO GGXWDG vs DataMapper GG_DEBT_GDP)",
     "fiscal/general_government_from_imf.csv", "gross_debt_pct_gdp", 2024,
     "fiscal/gross_debt_from_imf_xcheck.csv", "gross_debt_pct_gdp", 1, ("abs", 1.0)),
    ("Unemployment (OECD IALFS vs WB ILO-modelled)",
     "social/labour_from_oecd.csv", "unemployment_pct", 2024,
     "macro/economy_from_wb.csv", "unemployment_pct", 1, ("abs", 0.7)),
    ("Reserves (WB vs BoI Dec-2024 release, hand-recorded)",
     "international/world_from_wb.csv", "reserves_usd", 2024,
     "hand:boi_reserves_2024_12", None, 1, ("rel", 0.02)),
    ("Population 2024 (WB; Israel crossed 10mn — the band's stale edge)",
     "demography/demography_from_wb.csv", "population", 2024,
     "hand:wb_population_2024", None, 1, ("rel", 0.005)),
]

# Hand-recorded constants for cross-checks whose second publisher has no
# scripted route (each names its source in the printed line).
HAND = {
    # Bank of Israel press release, international reserves end-2024.
    "hand:boi_reserves_2024_12": (212100000000.0,
                                  "BoI end-2024 reserves $212.1bn"),
    # The WB figure the discovery pass recorded on 2026-10-22.
    "hand:wb_population_2024": (10002200.0, "manifest 2024 population"),
}

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "harmonised"
# www.imf.org answers 403 to urllib's default User-Agent, and also to a
# browser-shaped one that sends no Accept header (checked 2026-10-22).
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "*/*"}

WB = ("https://api.worldbank.org/v2/country/{iso3}/indicator/{code}"
      "?format=json&per_page=200&date=2005:2026")
IMF = "https://www.imf.org/external/datamapper/api/v1/{code}"
OECD = ("https://sdmx.oecd.org/public/rest/data/"
        "OECD.SDD.TPS,DSD_LFS@DF_IALFS_INDIC,1.0/{key}"
        "?startPeriod=2005")
OECD_ACCEPT = "application/vnd.sdmx.data+csv;version=1.0.0"
UNDP = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
        "HDR25_Composite_indices_complete_time_series.csv")

FIRST_YEAR, LAST_YEAR = 2005, 2026
# The IMF tables run to 2031. Everything after the last year the WEO and
# the Fiscal Monitor treat as outturn or estimate is a staff projection,
# and a projection is not a datum: the sidecar stops here.
IMF_LAST_YEAR = 2025

# World Bank indicator -> (sidecar, column, decimals).
WB_SERIES = [
    ("NY.GDP.MKTP.CD", "international/world_from_wb.csv", "gdp_usd", 0),
    ("NY.GDP.PCAP.CD", "international/world_from_wb.csv", "gdp_per_person_usd", 0),
    ("FI.RES.TOTL.CD", "international/world_from_wb.csv", "reserves_usd", 0),
    ("NE.GDI.FTOT.ZS", "macro/economy_from_wb.csv", "gfcf_pct_gdp", 2),
    ("SL.UEM.TOTL.ZS", "macro/economy_from_wb.csv", "unemployment_pct", 2),
    ("FP.CPI.TOTL.ZG", "macro/economy_from_wb.csv", "cpi_inflation_pct", 2),
    ("NE.EXP.GNFS.ZS", "trade/trade_from_wb.csv", "exports_pct_gdp", 2),
    ("NE.IMP.GNFS.ZS", "trade/trade_from_wb.csv", "imports_pct_gdp", 2),
    ("SP.POP.TOTL", "demography/demography_from_wb.csv", "population", 0),
    ("SP.POP.TOTL.FE.IN", "demography/demography_from_wb.csv", "population_female", 0),
    ("SP.DYN.TFRT.IN", "demography/demography_from_wb.csv", "fertility", 3),
    ("SP.DYN.CBRT.IN", "demography/demography_from_wb.csv", "birth_rate_per_1000", 3),
    ("SP.DYN.CDRT.IN", "demography/demography_from_wb.csv", "death_rate_per_1000", 3),
    ("SM.POP.NETM", "demography/demography_from_wb.csv", "net_migration", 0),
    ("VC.IHR.PSRC.P5", "security/security_from_wb.csv", "homicide_per_100k", 2),
    ("SH.STA.SUIC.P5", "security/security_from_wb.csv", "suicide_per_100k", 2),
    ("SH.STA.TRAF.P5", "security/security_from_wb.csv", "road_deaths_per_100k", 1),
    ("PA.NUS.FCRF", "markets/usdils_from_wb.csv", "ils_per_usd", 4),
]

# Cross-check-only WB series: not staged, pulled to stand beside the
# IMF number. It is the growth the national accounts publish, which the
# parked CBS series will replace as the line of record when CBS returns.
WB_XCHECK = [("NY.GDP.MKTP.KD.ZG", "macro/gdp_growth_from_wb_xcheck.csv",
              "gdp_growth_pct", 2)]

# IMF DataMapper indicator -> (column, decimals). Gross debt uses
# GGXWDG_NGDP, the WEO indicator the spine names for fiscal slot 3 and
# shared with every other country; GG_DEBT_GDP is the older DataMapper
# series ending at 2024, kept as a cross-check, never a splice.
IMF_SERIES = [
    ("NGDP_RPCH", "gdp_growth_pct", 1, "macro/gdp_growth_from_imf.csv"),
    ("PCPIPCH", "cpi_inflation_pct", 1, "macro/cpi_inflation_from_imf.csv"),
    ("GGR_G01_GDP_PT", "revenue_pct_gdp", 2, "fiscal/general_government_from_imf.csv"),
    ("G_X_G01_GDP_PT", "expenditure_pct_gdp", 2, "fiscal/general_government_from_imf.csv"),
    ("GGXCNL_G01_GDP_PT", "balance_pct_gdp", 1, "fiscal/general_government_from_imf.csv"),
    ("GGXWDG_NGDP", "gross_debt_pct_gdp", 1, "fiscal/general_government_from_imf.csv"),
]
IMF_XCHECK = [("GG_DEBT_GDP", "fiscal/gross_debt_from_imf_xcheck.csv",
               "gross_debt_pct_gdp", 1)]


class FetchError(RuntimeError):
    pass


# --------------------------------------------------------------- transport
def get(url: str, cache_name: str, check, accept: str | None = None) -> bytes:
    """The body at `url`, validated by `check` BEFORE it is cached.

    A cached error page is worse than no cache: it survives the retry
    that would have fixed it. So the check runs on the way in, and again
    on a cached copy left by an older run, which is thrown away if it
    fails.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        raw = path.read_bytes()
        try:
            check(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache {cache_name}: {e}", file=sys.stderr)
            path.unlink()
    headers = dict(HEADERS)
    if accept:
        headers["Accept"] = accept
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
            check(raw)
            path.write_bytes(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {cache_name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


# --------------------------------------------------------------- publishers
def wb(code: str) -> dict[int, float]:
    """One World Bank WDI indicator for this country, {year: value}.

    A bad request comes back as a JSON object with a message rather
    than the [metadata, rows] pair, and a paged answer would silently
    drop the later pages, so both are refused.
    """
    def check(raw: bytes) -> None:
        p = json.loads(raw)
        if not (isinstance(p, list) and len(p) == 2
                and isinstance(p[1], list) and p[1]):
            raise ValueError("not a World Bank indicator response")
        if p[0].get("pages") != 1:
            raise ValueError(f"paged response ({p[0].get('pages')} pages)")
        ids = {r["indicator"]["id"] for r in p[1]}
        isos = {r["countryiso3code"] for r in p[1]}
        if ids != {code} or isos != {ISO3}:
            raise ValueError(f"wrong series in payload: {ids} {isos}")

    raw = get(WB.format(iso3=ISO3, code=code), f"wb_{code}.json", check)
    out = {}
    for row in json.loads(raw)[1]:
        year = int(row["date"])
        if row["value"] is not None and FIRST_YEAR <= year <= LAST_YEAR:
            out[year] = float(row["value"])
    return out


def imf(code: str) -> dict[int, float]:
    """One IMF DataMapper indicator for Israel, outturn years only.

    DataMapper ignores the country path segment and returns the whole
    world, and it answers an indicator it does not know with the
    country list and a 200 — so the check is that the payload holds
    values[code][ISR]. Client-side filtering is the whole trap that
    moved the discovery pass's 2008/2009 spots onto Sudan's row; the
    filter here keys on the payload, never on the URL.
    """
    def check(raw: bytes) -> None:
        p = json.loads(raw)
        series = (p.get("values") or {}).get(code)
        if not isinstance(series, dict):
            raise ValueError(f"{code} is not a DataMapper indicator")
        if ISO3 not in series:
            raise ValueError(f"{code} has no values for {ISO3}")

    raw = get(IMF.format(code=code), f"imf_{code}.json", check)
    out = {}
    for year, value in json.loads(raw)["values"][code][ISO3].items():
        y = int(year)
        if value is not None and FIRST_YEAR <= y <= IMF_LAST_YEAR:
            out[y] = float(value)
    return out


def oecd_ialfs() -> list[dict]:
    """Israel's LFS from the OECD harmonised key, as SDMX-CSV rows.

    The key is nine segments: ISR plus eight dots. Annual observations
    (FREQ=A) are what the sidecar stages; the payload also carries
    quarterly to 2026-Q2 and monthly, and the latest quarter is
    asserted so a payload that quietly truncated cannot pass.
    """
    def check(raw: bytes) -> None:
        text = raw.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
        need = {"REF_AREA", "MEASURE", "UNIT_MEASURE", "FREQ", "AGE",
                "SEX", "ADJUSTMENT", "TIME_PERIOD", "OBS_VALUE"}
        if not rows or not need <= set(rows[0]):
            raise ValueError(f"not an SDMX-CSV payload: {text[:80]!r}")
        if {r["REF_AREA"] for r in rows} != {ISO3}:
            raise ValueError("payload is for another country")
        if not any(r["FREQ"] == "Q" for r in rows):
            raise ValueError("no quarterly observations in payload")

    raw = get(OECD.format(key="ISR........"), "oecd_ialfs.csv", check,
              accept=OECD_ACCEPT)
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    latest_q = max(r["TIME_PERIOD"] for r in rows
                   if r["FREQ"] == "Q" and r["MEASURE"] == "UNE_LF")
    if latest_q < "2026-Q2":
        raise FetchError(f"IALFS quarterly series stops at {latest_q}, "
                         "not 2026-Q2")
    return rows


def oecd_series(rows: list[dict], measure: str, unit: str,
                age: str) -> dict[int, float]:
    """Annual, both sexes, unadjusted: {year: value} for one dimension cut."""
    out = {}
    for r in rows:
        if (r["FREQ"] == "A" and r["MEASURE"] == measure
                and r["UNIT_MEASURE"] == unit and r["AGE"] == age
                and r["SEX"] == "_T" and r["ADJUSTMENT"] == "N"
                and r["OBS_VALUE"]):
            y = int(r["TIME_PERIOD"])
            if y in out:
                raise FetchError(f"{measure} {age} {y}: duplicate annual obs")
            if FIRST_YEAR <= y <= LAST_YEAR:
                out[y] = float(r["OBS_VALUE"])
    if not out:
        raise FetchError(f"{measure} {age}: no annual series")
    return out


def undp_hdi() -> tuple[dict[int, float], dict[int, float]]:
    """The ISR row of the HDR25 composite table: ({year: hdi}, {year: rank}).

    One vintage throughout (the HDR recomputes the whole back-series at
    each methodology change). The file is not valid UTF-8 (a cp1252
    byte at 452998, checked 2026-10-22), so decode cp1252.
    """
    def check(raw: bytes) -> None:
        text = raw.decode("cp1252")
        rows = list(csv.DictReader(io.StringIO(text)))
        if len(rows) < 150 or "iso3" not in (rows[0] if rows else {}):
            raise ValueError("not the HDR composite table")
        if not any(r["iso3"] == ISO3 for r in rows):
            raise ValueError(f"no {ISO3} row")

    raw = get(UNDP, "undp_hdr25.csv", check)
    rows = list(csv.DictReader(io.StringIO(raw.decode("cp1252"))))
    row = next(r for r in rows if r["iso3"] == ISO3)
    hdi, rank = {}, {}
    for key, value in row.items():
        if key and key.startswith("hdi_") and key[4:].isdigit() and value:
            y = int(key[4:])
            v = float(value)
            if not 0.4 <= v <= 1.0:
                raise FetchError(f"HDI {y} = {v}: outside any index scale")
            hdi[y] = v
    rank_value = int(row["hdi_rank_2023"])
    if not 1 <= rank_value <= 200:
        raise FetchError(f"HDI rank {rank_value} implausible")
    for y in hdi:
        rank[y] = float(rank_value)
    return hdi, rank


# --------------------------------------------------------------- assembly
def collect() -> dict[str, dict[int, dict[str, float]]]:
    """Every sidecar this country gets, as {rel: {year: {column: value}}}."""
    tables: dict[str, dict[int, dict[str, float]]] = {}
    decimals: dict[tuple[str, str], int] = {}
    order: dict[str, list[str]] = {}

    def put(rel: str, column: str, series: dict[int, float], dec: int) -> None:
        if not series:
            raise FetchError(f"{rel}: {column} came back empty")
        t = tables.setdefault(rel, {})
        for year, value in series.items():
            t.setdefault(year, {})[column] = value
        decimals[(rel, column)] = dec
        order.setdefault(rel, []).append(column)

    print("World Bank — World Development Indicators")
    for code, template, column, dec in WB_SERIES:
        if code in WB_SKIP:
            print(f"  {code:<18} skipped: already staged in {WB_SKIP[code]}")
            continue
        series = wb(code)
        print(f"  {code:<18} {len(series):>3} years "
              f"{min(series)}-{max(series)}")
        put(template, column, series, dec)
    for code, rel, column, dec in WB_XCHECK:
        series = wb(code)
        put(rel, column, series, dec)
        print(f"  {code:<18} {len(series):>3} years {min(series)}-{max(series)} "
              "(cross-check only)")

    print("IMF — DataMapper (WEO and Fiscal Monitor, current vintage)")
    for code, column, dec, rel in IMF_SERIES:
        series = imf(code)
        print(f"  {code:<18} {len(series):>3} years "
              f"{min(series)}-{max(series)}")
        put(rel, column, series, dec)
    for code, rel, column, dec in IMF_XCHECK:
        series = imf(code)
        put(rel, column, series, dec)
    # Two WEO gross-debt codes run side by side in DataMapper; if they
    # drift the endpoint is serving mixed vintages and the spine's
    # debt line would be a splice. 2024: 67.7 vs 67.8.
    weo, old = tables["fiscal/general_government_from_imf.csv"], tables["fiscal/gross_debt_from_imf_xcheck.csv"]
    both = set(weo) & set(old)
    worst = max(abs(weo[y]["gross_debt_pct_gdp"]
                    - old[y]["gross_debt_pct_gdp"]) for y in both)
    if worst > 2.0:
        raise FetchError(f"the two WEO gross-debt series differ by "
                         f"{worst:.1f} pt — mixed vintages, write nothing")
    print(f"  GGXWDG vs GG_DEBT_GDP: agree within {worst:.2f} pt "
          f"over {len(both)} years")

    print("UNDP — HDR25 composite indices (one vintage)")
    hdi, rank = undp_hdi()
    put("international/hdi_from_undp.csv", "hdi", hdi, 3)
    put("international/hdi_from_undp.csv", "hdi_rank_2023", rank, 0)
    print(f"  hdi              {len(hdi):>3} years {min(hdi)}-{max(hdi)}")

    print("OECD — SDMX REST DSD_LFS@DF_IALFS_INDIC (Israel's LFS, "
          "harmonised key)")
    rows = oecd_ialfs()
    put("social/labour_from_oecd.csv", "unemployment_pct",
        oecd_series(rows, "UNE_LF", "PT_LF_SUB", "Y_GE15"), 2)
    put("social/labour_from_oecd.csv", "youth_unemployment_pct",
        oecd_series(rows, "UNE_LF", "PT_LF_SUB", "Y15T24"), 2)
    put("social/labour_from_oecd.csv", "labour_force_thousands",
        oecd_series(rows, "LF", "PS", "Y_GE15"), 0)
    print("  UNE_LF Y_GE15 + Y15T24 + LF Y_GE15 staged; payload carries "
          "quarterly to 2026-Q2")

    collect.decimals = decimals  # type: ignore[attr-defined]
    collect.order = order        # type: ignore[attr-defined]
    return tables


# --------------------------------------------------------------- checks
def spot_checks(tables) -> None:
    """A known value per series. A refetch that moves one fails loudly.

    The tolerance absorbs an ordinary revision (3%, or 0.1 on a rate
    near zero); it does not absorb a unit read as thousands or the
    wrong row — which is how the discovery pass read Sudan's growth
    row as Israel's.
    """
    bad = []
    for rel, column, year, want in SPOT:
        got = tables.get(rel, {}).get(year, {}).get(column)
        if got is None or abs(got - want) > max(abs(want) * 0.03, 0.1):
            bad.append(f"{rel} {column} {year}: want {want}, got {got}")
    staged = {(rel, c) for rel in tables for c in order_of(rel)
              if not rel.endswith("_xcheck.csv")}
    covered = {(rel, c) for rel, c, _, _ in SPOT}
    missing = [f"{rel} {c}" for rel, c in staged if (rel, c) not in covered]
    if missing:
        bad.append(f"no spot value asserted for {missing}")
    if bad:
        raise FetchError("spot checks failed:\n  " + "\n  ".join(bad))
    print(f"Spot checks: {len(SPOT)} values as expected")


def order_of(rel: str) -> list[str]:
    return collect.order[rel]  # type: ignore[attr-defined]


def cross_checks(tables) -> None:
    """A staged number against an independent one, where both exist.

    Where the two measure the same quantity the tolerance is tight and
    a miss is an error. Where they differ by definition (tol None) the
    pair is printed for the record and nothing is asserted.
    """
    bad = []
    print("Cross-checks against independent publishers")
    for label, rel, column, year, rel_b, column_b, scale, tol in CROSS:
        h = tables[rel][year][column]
        if rel_b == "macro/gdp_growth_from_wb_xcheck.csv" or \
           rel_b == "fiscal/gross_debt_from_imf_xcheck.csv":
            b = tables[rel_b][year][column_b]
            note = rel_b
        elif rel_b.startswith("hand:"):
            b, note = HAND[rel_b]
        else:
            b = tables[rel_b][year][column_b]
            note = f"{rel_b}:{column_b}"
        h = h * (scale or 1)
        if scale is None:  # derived pair: GDP divided by population
            pop = tables["demography/demography_from_wb.csv"][year]["population"]
            h = tables[rel][year][column] / pop
        verdict = "printed only (different definitions)"
        if tol is not None:
            kind, limit = tol
            if kind == "self":
                diff = abs(h - b) / abs(b)
                kind = "rel"
            elif kind == "rel":
                diff = abs(h - b) / abs(b)
            else:
                diff = abs(h - b)
            verdict = f"{'ok' if diff <= limit else 'FAIL'} ({kind} {diff:.4f} <= {limit})"
            if diff > limit:
                bad.append(f"{label} {year}: {h:.6g} vs {note} {b:.6g}")
        print(f"  {label} {year}: {h:,.4g} | {note} {b:,.4g} — {verdict}")
    if bad:
        raise FetchError("cross-checks failed:\n  " + "\n  ".join(bad))


# --------------------------------------------------------------- output
def write(tables) -> None:
    for rel in sorted(tables):
        if rel.endswith("_xcheck.csv"):
            continue  # pulled to cross-check, not staged as a sidecar
        columns = order_of(rel)
        path = DATA / rel
        header = ",".join(["year", *columns])
        if path.exists():
            first = next((ln for ln in path.read_text().splitlines()
                          if not ln.startswith("#")), "")
            if first != header:
                raise FetchError(f"refusing to overwrite {rel}: it holds "
                                 f"{first!r}, not this fetcher's sidecar")
        lines = [header]
        for year in sorted(tables[rel]):
            row = tables[rel][year]
            cells = []
            for c in columns:
                v = row.get(c)
                cells.append("" if v is None else
                             f"{v:.{collect.decimals[(rel, c)]}f}")
            if any(cells):
                lines.append(f"{year}," + ",".join(cells))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")
        print(f"  data/{rel}  {len(lines) - 1} rows, {len(columns)} columns")


def main() -> None:
    print(f"Harmonised series for {NAME}")
    try:
        tables = collect()
        spot_checks(tables)
        cross_checks(tables)
    except FetchError as e:
        print(f"!! {e}\nNothing written.", file=sys.stderr)
        sys.exit(1)
    write(tables)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
