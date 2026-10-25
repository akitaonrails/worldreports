#!/usr/bin/env python3
"""Refresh Chile's harmonised cross-country series into review sidecars.

Usage:  python3 -I countries/chile/fetch/fetch_harmonised.py

The plate spine asks every country for the same indicator in the same unit
on the same axis, and for Chile most of those canonical slots have a
harmonised publisher: the World Bank, the IMF, the BIS, the OECD and UNDP.
This script pulls that layer once, shape-checks it, spot-checks it and
writes it beside the curated files as `*_from_<publisher>.csv`. It never
writes a curated file.

  World Bank   WDI: GDP and GDP per person (current US$), reserves, real
               growth, CPI, unemployment (ILO modelled), GFCF, exports and
               imports (% of GDP), population, fertility, crude birth and
               death rates, net migration, migrant stock (UN), homicide
               (UNODC), suicide and road deaths (WHO), poverty at the
               national line and at US$8.30/day (PIP), Gini, the annual
               average exchange rate, tax revenue.
  IMF          DataMapper: WEO gross debt and overall balance; Fiscal
               Monitor revenue, expenditure and primary balance. General
               government, calendar years, % of GDP.
  BIS          WS_CBPOL daily policy rate (annual mean); WS_TC household
               credit, % of GDP (Q4 and quarterly mean).
  OECD         National Accounts at a Glance: COFOG table 11 and general
               government GFCF, % of GDP.
  UNDP         HDR 2025 composite time series: HDI, 1990-2023.
  UN Comtrade  Chile's goods exports by partner, calendar 2024, customs
               basis (HS, aggregate level, TOTAL command).

What is not fetched here, and why (see SOURCES.yaml meta.pending):
  BIS WS_DSR      the BIS publishes no debt-service ratio for Chile.
  IMF interest    DataMapper carries no general-government interest
                  indicator; the national route is Dipres (see
                  fetch_dipres.py).

Every sidecar is written only after every series passes its shape check,
its pinned spot value and, where a national file exists, its cross-check.
Holes stay blank: nothing is interpolated, spliced or projected.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

NAME = "Chile"
ISO3, ISO2 = "CHL", "CL"

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "harmonised"

# www.imf.org answers 403 to urllib's default User-Agent (checked
# 2026-10-25); it wants a browser-shaped agent and an Accept header.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "*/*"}

WB = ("https://api.worldbank.org/v2/country/{iso3}/indicator/{code}"
      "?format=json&per_page=200&date=2005:2026")
IMF = "https://www.imf.org/external/datamapper/api/v1/{code}"
BIS_V1 = ("https://stats.bis.org/api/v1/data/{flow}/{key}/all"
          "?format=csv&startPeriod=2005")
OECD = ("https://sdmx.oecd.org/public/rest/data/"
        "OECD.SDD.NAD,DSD_NAAG_VI@{flow},/A.{iso3}.{measure}..."
        "?startPeriod=2005&dimensionAtObservation=AllDimensions")
OECD_ACCEPT = "application/vnd.sdmx.data+csv;version=1.0.0"
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
COMTRADE = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS"
            "?reporterCode=152&period={year}&partnerCode=&cmdCode=TOTAL"
            "&flowCode=X")
COMTRADE_PARTNERS = "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"

FIRST_YEAR, LAST_YEAR = 2005, 2026
# The IMF tables run past the last outturn; everything after the year the
# WEO still treats as an estimate is a staff projection, not a datum.
IMF_LAST_YEAR = 2025

# (indicator, sidecar, column, decimals). Sidecar paths are relative to
# data/ and are the review file the curated CSV is promoted from.
WB_SERIES = [
    ("NY.GDP.MKTP.CD", "world/world_from_wb.csv", "gdp_usd", 0),
    ("NY.GDP.PCAP.CD", "world/world_from_wb.csv", "gdp_per_person_usd", 2),
    ("FI.RES.TOTL.CD", "world/world_from_wb.csv", "reserves_usd", 0),
    ("NY.GDP.MKTP.KD.ZG", "macro/economy_from_wb.csv", "real_growth_pct", 2),
    ("FP.CPI.TOTL.ZG", "macro/economy_from_wb.csv", "inflation_pct", 2),
    ("SL.UEM.TOTL.ZS", "macro/economy_from_wb.csv", "unemployment_pct", 2),
    ("NE.GDI.FTOT.ZS", "macro/economy_from_wb.csv", "gfcf_pct_gdp", 2),
    ("NE.EXP.GNFS.ZS", "trade/trade_from_wb.csv", "exports_pct_gdp", 2),
    ("NE.IMP.GNFS.ZS", "trade/trade_from_wb.csv", "imports_pct_gdp", 2),
    ("SP.POP.TOTL", "demography/demography_from_wb.csv", "population", 0),
    ("SP.POP.TOTL.FE.IN", "demography/demography_from_wb.csv",
     "population_female", 0),
    ("SP.DYN.TFRT.IN", "demography/demography_from_wb.csv", "fertility", 3),
    ("SP.DYN.CBRT.IN", "demography/demography_from_wb.csv",
     "birth_rate_per_1000", 3),
    ("SP.DYN.CDRT.IN", "demography/demography_from_wb.csv",
     "death_rate_per_1000", 3),
    ("SM.POP.NETM", "demography/demography_from_wb.csv", "net_migration", 0),
    ("SM.POP.TOTL", "migration/migrant_stock_from_wb.csv", "migrant_stock", 0),
    ("VC.IHR.PSRC.P5", "security/security_from_wb.csv",
     "homicide_per_100k", 2),
    ("SH.STA.SUIC.P5", "security/security_from_wb.csv",
     "suicide_per_100k", 2),
    ("SH.STA.TRAF.P5", "security/security_from_wb.csv",
     "road_deaths_per_100k", 2),
    ("SI.POV.NAHC", "people/poverty_from_wb.csv", "poverty_national_pct", 1),
    ("SI.POV.UMIC", "people/poverty_from_wb.csv", "poverty_830_pct", 1),
    ("SI.POV.GINI", "people/gini_from_wb.csv", "gini", 1),
    ("PA.NUS.FCRF", "macro/fx_from_wb.csv", "clp_per_usd", 2),
    ("GC.TAX.TOTL.GD.ZS", "fiscal/tax_from_wb.csv", "tax_revenue_pct_gdp", 2),
]

# IMF DataMapper indicator -> (column, decimals, is_fiscal_monitor).
# Revenue, expenditure and the primary balance are Fiscal Monitor codes:
# DataMapper answers the WEO-looking GGR_NGDP with the country list, which
# is what it does for a code it does not know.
IMF_SERIES = [
    ("GGR_G01_GDP_PT", "revenue_pct_gdp", 2, True),
    ("G_X_G01_GDP_PT", "expenditure_pct_gdp", 2, True),
    ("GGXCNL_NGDP", "balance_pct_gdp", 2, False),
    ("GGXONLB_G01_GDP_PT", "primary_balance_pct_gdp", 2, True),
    ("GGXWDG_NGDP", "gross_debt_pct_gdp", 1, False),
]
IMF_FILE = "fiscal/general_government_from_imf.csv"

# OECD NAAG 6A EXPENDITURE code -> column, % of GDP. Chile reports table
# 11 from 2018 only; the sidecar keeps what exists and nothing pretends
# the 2018 looks were measured in 2006.
COFOG = [
    ("_T", "total"),
    ("GF10", "social_protection"),
    ("GF07", "health"),
    ("GF09", "education"),
    ("GF01", "general_public_services"),
    ("GF04", "economic_affairs"),
    ("GF02", "defence"),
    ("GF03", "public_order"),
    ("GF05", "environment"),
    ("GF06", "housing"),
    ("GF08", "recreation_culture"),
]

# (sidecar, column, year, value): one known value per series, read off the
# publisher on 2026-10-25. The tolerance absorbs an ordinary revision, not
# a unit read as thousands.
SPOT = [
    ("world/world_from_wb.csv", "gdp_usd", 2019, 278_308_000_000.0),
    ("world/world_from_wb.csv", "gdp_per_person_usd", 2019, 14_496.93),
    ("world/world_from_wb.csv", "reserves_usd", 2019, 40_655_524_238.0),
    ("macro/economy_from_wb.csv", "real_growth_pct", 2020, -6.14),
    ("macro/economy_from_wb.csv", "inflation_pct", 2022, 11.64),
    ("macro/economy_from_wb.csv", "unemployment_pct", 2020, 10.93),
    ("macro/economy_from_wb.csv", "gfcf_pct_gdp", 2019, 24.55),
    ("trade/trade_from_wb.csv", "exports_pct_gdp", 2021, 31.97),
    ("trade/trade_from_wb.csv", "imports_pct_gdp", 2021, 32.87),
    ("demography/demography_from_wb.csv", "population", 2019, 19_197_744.0),
    ("demography/demography_from_wb.csv", "fertility", 2019, 1.43),
    ("demography/demography_from_wb.csv", "net_migration", 2022, 59_374.0),
    ("security/security_from_wb.csv", "homicide_per_100k", 2019, 4.81),
    ("people/gini_from_wb.csv", "gini", 2022, 43.2),
    ("fiscal/general_government_from_imf.csv", "gross_debt_pct_gdp", 2021, 36.4),
    ("fiscal/general_government_from_imf.csv", "revenue_pct_gdp", 2022, 28.1),
    ("credit/household_credit_from_bis.csv", "hh_credit_pct_gdp_q4", 2019, 48.1),
    ("macro/policy_rate_from_bis.csv", "policy_rate_pct", 2020, 0.79),
    ("spending/cofog_from_oecd.csv", "health", 2022, 5.29),
    ("world/hdi_from_undp.csv", "hdi", 2023, 0.878),
]


class FetchError(RuntimeError):
    pass


# --------------------------------------------------------------- transport
def get(url: str, cache_name: str, check, accept: str | None = None) -> bytes:
    """The body at `url`, validated by `check` BEFORE it is cached."""
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
    """One World Bank WDI indicator for Chile, {year: value}."""
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
    """One IMF DataMapper indicator for Chile, outturn years only."""
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


def bis(flow: str, key: str, area_column: str) -> list[dict]:
    """Rows of one BIS SDMX-CSV series, checked to be this country's."""
    def check(raw: bytes) -> None:
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
        if not rows or "TIME_PERIOD" not in rows[0] or "OBS_VALUE" not in rows[0]:
            raise ValueError("not an SDMX-CSV payload")
        if area_column not in rows[0]:
            raise ValueError(f"no {area_column} in payload")
        if {r[area_column] for r in rows} != {ISO2}:
            raise ValueError("payload is for another country")

    raw = get(BIS_V1.format(flow=flow, key=key), f"bis_{flow}_{key}.csv", check)
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))


def annual_mean(points: dict[str, float]) -> dict[int, float]:
    """Mean of the daily or monthly observations published in each year."""
    by_year: dict[int, list[float]] = {}
    for period, value in points.items():
        year = int(period[:4])
        if FIRST_YEAR <= year <= LAST_YEAR:
            by_year.setdefault(year, []).append(value)
    return {y: sum(v) / len(v) for y, v in by_year.items()}


def oecd(flow: str, measure: str) -> list[dict]:
    """Rows of one OECD National Accounts at a Glance measure, % of GDP."""
    def check(raw: bytes) -> None:
        text = raw.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
        need = {"REF_AREA", "MEASURE", "UNIT_MEASURE", "TIME_PERIOD", "OBS_VALUE"}
        if not rows or not need <= set(rows[0]):
            raise ValueError(f"not an SDMX-CSV payload: {text[:80]!r}")
        if {r["REF_AREA"] for r in rows} != {ISO3}:
            raise ValueError("payload is for another country")
        if {r["MEASURE"] for r in rows} != {measure}:
            raise ValueError("payload holds another measure")
        if {r["UNIT_MEASURE"] for r in rows} != {"PT_B1GQ"}:
            raise ValueError("unit is not % of GDP")

    url = OECD.format(flow=flow, iso3=ISO3, measure=measure)
    raw = get(url, f"oecd_{flow}_{measure}.csv", check, accept=OECD_ACCEPT)
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))


def undp_hdi() -> dict[int, float]:
    """UNDP HDR composite time series: this country's HDI by year."""
    def check(raw: bytes) -> None:
        head = raw[:400].decode("latin-1", "replace")
        if "iso3" not in head or "hdi_" not in head:
            raise ValueError("not the HDR composite series")

    raw = get(HDR, "hdr25_composite.csv", check)
    # The HDR CSV is published in Latin-1 (an 'ô' in a country name at byte
    # 452,998), not UTF-8. Decode it as what it is rather than dropping the
    # row that carries it.
    for row in csv.DictReader(io.StringIO(raw.decode("latin-1"))):
        if row["iso3"] == ISO3:
            out = {}
            for key, value in row.items():
                if (key.startswith("hdi_") and key[4:].isdigit()
                        and value not in ("", "..")):
                    year = int(key[4:])
                    if FIRST_YEAR <= year <= LAST_YEAR:
                        out[year] = float(value)
            if not out:
                raise FetchError("HDR: no HDI years for Chile")
            return out
    raise FetchError("HDR: Chile is not in the composite series")


def comtrade_partners(year: int = 2024) -> tuple[list[tuple[str, float]], float]:
    """Chile's goods exports by partner, and the world total, US$."""
    def check(raw: bytes) -> None:
        p = json.loads(raw)
        if "data" not in p or not p["data"]:
            raise ValueError(f"no Comtrade rows: {str(p)[:120]}")
        if {r["reporterCode"] for r in p["data"]} != {152}:
            raise ValueError("payload is for another reporter")

    raw = get(COMTRADE.format(year=year), f"comtrade_{year}.json", check)
    data = json.loads(raw)["data"]
    names = {}
    try:
        praw = get(COMTRADE_PARTNERS, "comtrade_partners.json",
                   lambda b: json.loads(b).get("results") or
                   (_ for _ in ()).throw(ValueError("no partner list")))
        names = {r["id"]: r["text"] for r in json.loads(praw)["results"]}
    except FetchError as e:  # the code list is a nicety, not the datum
        print(f"  Comtrade partner names unavailable: {e}", file=sys.stderr)
    total = 0.0
    partners = []
    for row in data:
        value = float(row.get("primaryValue") or 0)
        if row["partnerCode"] == 0:
            total = value
        elif row["partnerCode"] != 152:
            partners.append((names.get(row["partnerCode"],
                                       str(row["partnerCode"])), value))
    if not total:
        raise FetchError("Comtrade: no world total row")
    partners.sort(key=lambda kv: kv[1], reverse=True)
    return partners, total


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
    for code, rel, column, dec in WB_SERIES:
        series = wb(code)
        print(f"  {code:<18} {len(series):>3} years "
              f"{min(series)}-{max(series)}")
        put(rel, column, series, dec)

    print("IMF — DataMapper (WEO and Fiscal Monitor)")
    for code, column, dec, is_fm in IMF_SERIES:
        series = imf(code)
        print(f"  {code:<20} {len(series):>3} years {min(series)}-{max(series)}")
        put(IMF_FILE, column, series, dec)
    # The WEO balance and the Fiscal Monitor balance are one number from
    # one database; if they disagree the endpoints serve different
    # vintages and mixing their columns in one file would be a splice.
    weo, fm = imf("GGXCNL_NGDP"), imf("GGXCNL_G01_GDP_PT")
    worst = max(abs(weo[y] - fm[y]) for y in set(weo) & set(fm))
    if worst > 0.11:
        raise FetchError(f"WEO and Fiscal Monitor balances differ by {worst:.2f}")
    print(f"  WEO vs Fiscal Monitor balance: agree within {worst:.2f} pt")

    print("BIS — policy rate and household credit")
    rows = bis("WS_CBPOL", f"D.{ISO2}", "REF_AREA")
    points = {r["TIME_PERIOD"]: float(r["OBS_VALUE"]) for r in rows
              if r["OBS_VALUE"] not in ("", "NaN")}
    rate = annual_mean(points)
    observed: dict[int, int] = {}
    for period in points:
        year = int(period[:4])
        if FIRST_YEAR <= year <= LAST_YEAR:
            observed[year] = observed.get(year, 0) + 1
    print(f"  WS_CBPOL D.{ISO2}   {len(points)} days -> {len(rate)} years")
    put("macro/policy_rate_from_bis.csv", "policy_rate_pct", rate, 2)
    put("macro/policy_rate_from_bis.csv", "days_observed",
        {y: float(n) for y, n in observed.items()}, 0)

    rows = bis("WS_TC", f"Q.{ISO2}.H.A.M.770.A", "BORROWERS_CTY")
    quarters = {r["TIME_PERIOD"]: float(r["OBS_VALUE"]) for r in rows
                if r["OBS_VALUE"] not in ("", "NaN")}
    by_year: dict[int, dict[int, float]] = {}
    for period, value in quarters.items():
        year, q = int(period[:4]), int(period[-1])
        by_year.setdefault(year, {})[q] = value
    rel = "credit/household_credit_from_bis.csv"
    put(rel, "hh_credit_pct_gdp_qavg",
        {y: sum(v.values()) / len(v) for y, v in by_year.items()}, 2)
    put(rel, "hh_credit_pct_gdp_quarters",
        {y: float(len(v)) for y, v in by_year.items()}, 0)
    q4 = {y: v[4] for y, v in by_year.items() if 4 in v}
    put(rel, "hh_credit_pct_gdp_q4", q4, 1)
    print(f"  WS_TC Q.{ISO2}.H.A.M.770.A  {len(quarters)} quarters, "
          f"{len(by_year)} years, {len(q4)} with Q4")

    print("OECD — National Accounts at a Glance, general government")
    rows = oecd("DF_NAAG_OTEF", "OTES13F")
    by_fn: dict[str, dict[int, float]] = {}
    for r in rows:
        y = int(r["TIME_PERIOD"])
        if r["OBS_VALUE"] and FIRST_YEAR <= y <= LAST_YEAR:
            cell = by_fn.setdefault(r["EXPENDITURE"], {})
            if y in cell:
                raise FetchError(f"COFOG {r['EXPENDITURE']} {y} twice")
            cell[y] = float(r["OBS_VALUE"])
    for fn, column in COFOG:
        if fn not in by_fn:
            print(f"  COFOG {fn:<5} {column}: not reported to the OECD")
            continue
        put("spending/cofog_from_oecd.csv", column, by_fn[fn], 2)
    t = tables["spending/cofog_from_oecd.csv"]
    for y, row in t.items():
        parts = sum(v for k, v in row.items() if k != "total")
        if "total" in row and abs(parts - row["total"]) > 0.15:
            raise FetchError(f"COFOG {y}: divisions {parts:.2f} "
                             f"vs total {row['total']:.2f}")
    print(f"  OTES13F  {len(t)} years {min(t)}-{max(t)}; divisions sum to total")

    rows = oecd("DF_NAAG_VI", "P51GS13")
    series = {int(r["TIME_PERIOD"]): float(r["OBS_VALUE"]) for r in rows
              if r["OBS_VALUE"] and FIRST_YEAR <= int(r["TIME_PERIOD"]) <= LAST_YEAR}
    print(f"  P51GS13  {len(series)} years {min(series)}-{max(series)}")
    put("spending/public_investment_from_oecd.csv", "gov_gfcf_pct_gdp",
        series, 2)

    print("UNDP — Human Development Report 2025 composite series")
    hdi = undp_hdi()
    print(f"  HDI      {len(hdi)} years {min(hdi)}-{max(hdi)}")
    put("world/hdi_from_undp.csv", "hdi", hdi, 3)

    collect.decimals = decimals  # type: ignore[attr-defined]
    collect.order = order        # type: ignore[attr-defined]
    return tables


def spot_checks(tables) -> None:
    """A known value per series. A refetch that moves one fails loudly."""
    for rel, column, year, expected in SPOT:
        got = tables.get(rel, {}).get(year, {}).get(column)
        if got is None:
            raise FetchError(f"{rel}:{column} {year} is missing")
        tol = max(abs(expected) * 0.05, 0.1)
        if abs(got - expected) > tol:
            raise FetchError(f"{rel}:{column} {year} = {got} not {expected}"
                             f" (±{tol:.2f})")
    print(f"  {len(SPOT)} pinned values agree")


def write_sidecars(tables, decimals, order) -> None:
    for rel, rows in sorted(tables.items()):
        path = DATA / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        columns = order[rel]
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["year"] + columns)
            for year in sorted(rows):
                cells = []
                for c in columns:
                    v = rows[year].get(c)
                    cells.append("" if v is None else
                                 f"{v:.{decimals[(rel, c)]}f}")
                w.writerow([year] + cells)
        print(f"  -> {rel}  {len(rows)} years, {len(columns)} columns")


def main() -> int:
    tables = collect()
    spot_checks(tables)
    write_sidecars(tables, collect.decimals, collect.order)
    return 0


if __name__ == "__main__":
    sys.exit(main())
