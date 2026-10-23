#!/usr/bin/env python3
"""Refresh the harmonised cross-country series for Spain into sidecars.

Usage:  python3 -I countries/spain/fetch/fetch_harmonised.py

The plate spine (one indicator, one unit, one axis per canonical slot in
every country) needs the same series from the same harmoniser for all
seven countries. This is that layer: the World Bank, the IMF, the BIS and
the OECD, each fetched once, shape-checked, spot-checked and set beside
the national series it shadows. It is never a substitute for a number the
country publishes about itself; where both exist the plate draws both and
labels the difference.

  World Bank  WDI: GDP and GDP per person (current US$), reserves, GFCF,
              unemployment (ILO modelled), exports and imports (% of GDP),
              population (total and female), fertility, crude birth and
              death rates, net migration (a count), homicide (UNODC),
              suicide and road deaths (WHO), poverty at US$8.30/day (PIP)
  IMF         DataMapper: WEO gross debt and overall balance; Fiscal
              Monitor revenue, expenditure and primary balance
  BIS         WS_TC household credit, % of GDP; WS_DSR debt service ratio
  OECD        National Accounts at a Glance: COFOG and government GFCF,
              % of GDP

Already staged from the same publisher, so not fetched again:
  SI.POV.GINI        international/gini_from_wb.csv
  NY.GDP.MKTP.CD     international/gdp_usd_from_wb.csv (fetch_comparables.py)
  NY.GDP.PCAP.CD     international/gdp_pc_from_wb.csv (fetch_comparables.py)
  FI.RES.TOTL.CD     international/reserves_from_wb.csv (fetch_comparables.py)
  SP.POP.TOTL        international/population_from_wb.csv (fetch_comparables.py)

Not fetched here, and why:
  IMF revenue/expenditure  Spain has Eurostat revenue and expenditure (fiscal/revenue_from_estat.csv)
  OECD COFOG               Spain has Eurostat COFOG (fiscal/spending_by_function_from_estat.csv)
  OECD government GFCF     Spain has Eurostat P51G (fiscal/investment_from_estat.csv)

Spain is covered by Eurostat for the fiscal and spending chapters, so
only the IMF's balance, primary balance and gross debt are fetched, as
the line on the same basis as the non-EU countries. Its world-chapter
World Bank series are already staged by fetch_comparables.py.

Every sidecar is written only after every series has passed its shape
check, its spot value and its cross-check against the national file; a
fetch that cannot confirm what it pulled writes nothing. Holes stay
blank: nothing is interpolated, spliced or projected.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

NAME = 'Spain'
ISO3, ISO2 = 'ESP', 'ES'
# This country's folder for each kind of sidecar.
DIRS = {'intl': 'international', 'macro': 'macro', 'trade': 'trade', 'credit': 'credit'}

# Series this country already stages from the same publisher.
WB_SKIP = {'NY.GDP.MKTP.CD': 'international/gdp_usd_from_wb.csv '
                   '(fetch_comparables.py)',
 'NY.GDP.PCAP.CD': 'international/gdp_pc_from_wb.csv '
                   '(fetch_comparables.py)',
 'FI.RES.TOTL.CD': 'international/reserves_from_wb.csv '
                   '(fetch_comparables.py)',
 'SP.POP.TOTL': 'international/population_from_wb.csv '
                '(fetch_comparables.py)'}
WB_SKIP.setdefault("SI.POV.GINI", 'international/gini_from_wb.csv')

IMF_REVEXP = False
IMF_REVEXP_SKIP = 'Spain has Eurostat revenue and expenditure (fiscal/revenue_from_estat.csv)'
BIS_TC, BIS_TC_SKIP = True, ''
BIS_DSR, BIS_DSR_SKIP = True, ''
OECD_COFOG, OECD_COFOG_SKIP = False, 'Spain has Eurostat COFOG (fiscal/spending_by_function_from_estat.csv)'
OECD_GFCF, OECD_GFCF_SKIP = False, 'Spain has Eurostat P51G (fiscal/investment_from_estat.csv)'

# (sidecar, column, year, value): one known value per series, read off the
# publisher on 2026-10-22.
SPOT = [
    ('macro/economy_from_wb.csv', 'gfcf_pct_gdp', 2019, 20.31),
    ('macro/economy_from_wb.csv', 'unemployment_pct', 2019, 14.1),
    ('trade/trade_from_wb.csv', 'exports_pct_gdp', 2019, 34.68),
    ('trade/trade_from_wb.csv', 'imports_pct_gdp', 2019, 31.69),
    ('social/demography_from_wb.csv', 'population_female', 2019, 23974000.0),
    ('social/demography_from_wb.csv', 'fertility', 2019, 1.23),
    ('social/demography_from_wb.csv', 'birth_rate_per_1000', 2019, 7.6),
    ('social/demography_from_wb.csv', 'death_rate_per_1000', 2019, 8.8),
    ('social/demography_from_wb.csv', 'net_migration', 2019, 464800.0),
    ('social/security_from_wb.csv', 'homicide_per_100k', 2019, 0.6978),
    ('social/security_from_wb.csv', 'suicide_per_100k', 2019, 8.1),
    ('social/security_from_wb.csv', 'road_deaths_per_100k', 2019, 3.9),
    ('social/poverty_from_wb.csv', 'poverty_830_pct', 2019, 2.9),
    ('fiscal/general_government_from_imf.csv', 'balance_pct_gdp', 2019, -3.0),
    ('fiscal/general_government_from_imf.csv', 'primary_balance_pct_gdp', 2019, -1.001),
    ('fiscal/general_government_from_imf.csv', 'gross_debt_pct_gdp', 2019, 97.6),
    ('credit/household_credit_from_bis.csv', 'hh_credit_pct_gdp_q4', 2019, 56.5),
    ('credit/household_credit_from_bis.csv', 'hh_credit_pct_gdp_qavg', 2019, 57.42),
    ('credit/household_credit_from_bis.csv', 'hh_credit_pct_gdp_quarters', 2019, 4.0),
    ('credit/debt_service_from_bis.csv', 'hh_dsr_pct_q4', 2019, 6.0),
    ('credit/debt_service_from_bis.csv', 'hh_dsr_pct_qavg', 2019, 6.05),
    ('credit/debt_service_from_bis.csv', 'hh_dsr_pct_quarters', 2019, 4.0),
]

# (label, sidecar, column, year, national file, column, scale, tolerance):
# the harmonised value x scale against the national one. A tolerance of
# None marks a pair that differs by definition — printed, not asserted.
CROSS = [
    ('Gross debt (IMF vs Eurostat EDP)', 'fiscal/general_government_from_imf.csv', 'gross_debt_pct_gdp', 2019, 'fiscal/debt.csv', 'gross_pct_gdp', 1, ('abs', 1.0)),
    ('Balance (IMF vs Eurostat EDP)', 'fiscal/general_government_from_imf.csv', 'balance_pct_gdp', 2019, 'fiscal/deficit.csv', 'deficit', 1, ('abs', 0.3)),
    ('Unemployment rate (ILO modelled vs Eurostat LFS)', 'macro/economy_from_wb.csv', 'unemployment_pct', 2019, 'macro/unemployment.csv', 'estat', 1, ('abs', 0.3)),
    ('Fertility (WB vs INE)', 'social/demography_from_wb.csv', 'fertility', 2019, 'social/demography.csv', 'tfr', 1, ('abs', 0.03)),
]

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "harmonised"
# www.imf.org answers 403 to urllib's default User-Agent, and also to a
# browser-shaped one that sends no Accept header (checked 2026-10-22).
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "*/*"}

WB = ("https://api.worldbank.org/v2/country/{iso3}/indicator/{code}"
      "?format=json&per_page=200&date=2005:2026")
IMF = "https://www.imf.org/external/datamapper/api/v1/{code}"
BIS = ("https://stats.bis.org/api/v2/data/dataflow/BIS/{flow}/{key}"
       "?format=csv&startPeriod=2005-Q1")
OECD = ("https://sdmx.oecd.org/public/rest/data/"
        "OECD.SDD.NAD,DSD_NAAG_VI@{flow},/A.{iso3}.{measure}..."
        "?startPeriod=2005&dimensionAtObservation=AllDimensions")
OECD_ACCEPT = "application/vnd.sdmx.data+csv;version=1.0.0"

FIRST_YEAR, LAST_YEAR = 2005, 2026
# The IMF tables run to 2031. Everything after the last year the WEO and the
# Fiscal Monitor treat as outturn or estimate is a staff projection, and a
# projection is not a datum: the sidecar stops here.
IMF_LAST_YEAR = 2025

# World Bank indicator -> (sidecar, column, decimals). The sidecar path is a
# template on this country's own folder names.
WB_SERIES = [
    ("NY.GDP.MKTP.CD", "{intl}/world_from_wb.csv", "gdp_usd", 0),
    ("NY.GDP.PCAP.CD", "{intl}/world_from_wb.csv", "gdp_per_person_usd", 0),
    ("FI.RES.TOTL.CD", "{intl}/world_from_wb.csv", "reserves_usd", 0),
    ("NE.GDI.FTOT.ZS", "{macro}/economy_from_wb.csv", "gfcf_pct_gdp", 2),
    ("SL.UEM.TOTL.ZS", "{macro}/economy_from_wb.csv", "unemployment_pct", 2),
    ("NE.EXP.GNFS.ZS", "{trade}/trade_from_wb.csv", "exports_pct_gdp", 2),
    ("NE.IMP.GNFS.ZS", "{trade}/trade_from_wb.csv", "imports_pct_gdp", 2),
    ("SP.POP.TOTL", "social/demography_from_wb.csv", "population", 0),
    ("SP.POP.TOTL.FE.IN", "social/demography_from_wb.csv", "population_female", 0),
    ("SP.DYN.TFRT.IN", "social/demography_from_wb.csv", "fertility", 3),
    ("SP.DYN.CBRT.IN", "social/demography_from_wb.csv", "birth_rate_per_1000", 3),
    ("SP.DYN.CDRT.IN", "social/demography_from_wb.csv", "death_rate_per_1000", 3),
    ("SM.POP.NETM", "social/demography_from_wb.csv", "net_migration", 0),
    ("VC.IHR.PSRC.P5", "social/security_from_wb.csv", "homicide_per_100k", 2),
    ("SH.STA.SUIC.P5", "social/security_from_wb.csv", "suicide_per_100k", 2),
    ("SH.STA.TRAF.P5", "social/security_from_wb.csv", "road_deaths_per_100k", 2),
    ("SI.POV.UMIC", "social/poverty_from_wb.csv", "poverty_830_pct", 1),
]

# IMF DataMapper indicator -> (column, decimals, needs_revexp). The WEO
# carries the balance and the gross debt; revenue, expenditure and the
# primary balance are not WEO indicators on DataMapper (GGR_NGDP,
# GGX_NGDP and GGXONLB_NGDP answer with the country list, which is what
# DataMapper does for an unknown code) and come from the Fiscal Monitor,
# which DataMapper serves from the same general-government database.
IMF_SERIES = [
    ("GGR_G01_GDP_PT", "revenue_pct_gdp", 2, True),
    ("G_X_G01_GDP_PT", "expenditure_pct_gdp", 2, True),
    ("GGXCNL_NGDP", "balance_pct_gdp", 1, False),
    ("GGXONLB_G01_GDP_PT", "primary_balance_pct_gdp", 2, False),
    ("GGXWDG_NGDP", "gross_debt_pct_gdp", 1, False),
]
IMF_FILE = "fiscal/general_government_from_imf.csv"

COFOG = [  # OECD NAAG 6A, EXPENDITURE code -> column, % of GDP
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


class FetchError(RuntimeError):
    pass


# --------------------------------------------------------------- transport
def get(url: str, cache_name: str, check, accept: str | None = None) -> bytes:
    """The body at `url`, validated by `check` BEFORE it is cached.

    A cached error page is worse than no cache: it survives the retry that
    would have fixed it. So the check runs on the way in, and again on a
    cached copy left by an older run, which is thrown away if it fails.
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

    A bad request comes back as a JSON object with a message rather than
    the [metadata, rows] pair, and a paged answer would silently drop the
    later pages, so both are refused.
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
    """One IMF DataMapper indicator for this country, outturn years only.

    DataMapper ignores a country filter and returns the whole world, and
    it answers an indicator it does not know with the country list and a
    200 — so the check is that the payload holds `values[code][ISO3]`.
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


def bis(flow: str, key: str, version: str) -> dict[str, float]:
    """One BIS series as {'YYYY-Qn': value}, from the SDMX-CSV API."""
    def check(raw: bytes) -> None:
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
        if not rows or "TIME_PERIOD" not in rows[0] or "OBS_VALUE" not in rows[0]:
            raise ValueError("not an SDMX-CSV payload")
        if {r["BORROWERS_CTY"] for r in rows} != {ISO2}:
            raise ValueError("payload is for another country")
        if len({r["TITLE_TS"] for r in rows}) != 1:
            raise ValueError("payload holds more than one series")
        if any(not r["TIME_PERIOD"][:4].isdigit() or "-Q" not in r["TIME_PERIOD"]
               for r in rows):
            raise ValueError("not a quarterly series")

    url = BIS.format(flow=f"{flow}/{version}", key=key)
    raw = get(url, f"bis_{flow}_{key}.csv", check)
    rows = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    return {r["TIME_PERIOD"]: float(r["OBS_VALUE"]) for r in rows
            if r["OBS_VALUE"] not in ("", "NaN")}


def annualise(quarters: dict[str, float], prefix: str) -> dict[int, dict]:
    """Year-end (Q4) value, the mean of the quarters published, and how many.

    The spine draws the Q4 stock. The mean is kept beside it with the
    count, so a running year with one quarter is visibly one quarter and
    never a year's result; its Q4 cell stays blank until Q4 exists.
    """
    by_year: dict[int, dict[int, float]] = {}
    for period, value in quarters.items():
        year, q = int(period[:4]), int(period[-1])
        if FIRST_YEAR <= year <= LAST_YEAR:
            by_year.setdefault(year, {})[q] = value
    out = {}
    for year, qs in by_year.items():
        row = {f"{prefix}_qavg": sum(qs.values()) / len(qs),
               f"{prefix}_quarters": len(qs)}
        if 4 in qs:
            row[f"{prefix}_q4"] = qs[4]
        out[year] = row
    return out


def bis_decimals(column: str) -> int:
    """The BIS publishes one decimal; a mean of quarters earns a second."""
    if column.endswith("quarters"):
        return 0
    return 1 if column.endswith("q4") else 2


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
        put(template.format(**DIRS), column, series, dec)

    print("IMF — DataMapper (WEO and Fiscal Monitor)")
    for code, column, dec, revexp in IMF_SERIES:
        if revexp and not IMF_REVEXP:
            print(f"  {code:<18} skipped: {IMF_REVEXP_SKIP}")
            continue
        series = imf(code)
        print(f"  {code:<18} {len(series):>3} years "
              f"{min(series)}-{max(series)}")
        put(IMF_FILE, column, series, dec)
    # The WEO balance and the Fiscal Monitor balance are one number from one
    # database. If they disagree the two endpoints are serving different
    # vintages, and mixing their columns in one file would be a splice.
    weo, fm = imf("GGXCNL_NGDP"), imf("GGXCNL_G01_GDP_PT")
    worst = max(abs(weo[y] - fm[y]) for y in set(weo) & set(fm))
    if worst > 0.11:
        raise FetchError(f"WEO and Fiscal Monitor balances differ by {worst:.2f}")
    print(f"  WEO vs Fiscal Monitor balance: agree within {worst:.2f} pt")

    print("BIS — credit to households and debt service")
    if BIS_TC:
        q = bis("WS_TC", f"Q.{ISO2}.H.A.M.770.A", "2.0")
        print(f"  WS_TC Q.{ISO2}.H.A.M.770.A  {len(q)} quarters "
              f"{min(q)}..{max(q)}")
        rel = f"{DIRS['credit']}/household_credit_from_bis.csv"
        for col in ("hh_credit_pct_gdp_q4", "hh_credit_pct_gdp_qavg",
                    "hh_credit_pct_gdp_quarters"):
            put(rel, col, {y: r[col] for y, r in
                           annualise(q, "hh_credit_pct_gdp").items()
                           if col in r},
                bis_decimals(col))
    else:
        print(f"  WS_TC skipped: {BIS_TC_SKIP}")
    if BIS_DSR:
        q = bis("WS_DSR", f"Q.{ISO2}.H", "1.0")
        print(f"  WS_DSR Q.{ISO2}.H  {len(q)} quarters {min(q)}..{max(q)}")
        rel = f"{DIRS['credit']}/debt_service_from_bis.csv"
        for col in ("hh_dsr_pct_q4", "hh_dsr_pct_qavg", "hh_dsr_pct_quarters"):
            put(rel, col, {y: r[col] for y, r in
                           annualise(q, "hh_dsr_pct").items() if col in r},
                bis_decimals(col))
    else:
        print(f"  WS_DSR skipped: {BIS_DSR_SKIP}")

    print("OECD — National Accounts at a Glance, general government")
    if OECD_COFOG:
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
            put("fiscal/cofog_from_oecd.csv", column, by_fn[fn], 2)
        # The ten divisions must add up to the total the OECD publishes.
        t = tables["fiscal/cofog_from_oecd.csv"]
        for y, row in t.items():
            parts = sum(v for k, v in row.items() if k != "total")
            if "total" in row and abs(parts - row["total"]) > 0.15:
                raise FetchError(f"COFOG {y}: divisions {parts:.2f} "
                                 f"vs total {row['total']:.2f}")
        print(f"  OTES13F  {len(t)} years {min(t)}-{max(t)}; divisions sum "
              "to the total")
    else:
        print(f"  COFOG skipped: {OECD_COFOG_SKIP}")
    if OECD_GFCF:
        rows = oecd("DF_NAAG_VI", "P51GS13")
        series = {int(r["TIME_PERIOD"]): float(r["OBS_VALUE"]) for r in rows
                  if r["OBS_VALUE"]
                  and FIRST_YEAR <= int(r["TIME_PERIOD"]) <= LAST_YEAR}
        if len(series) != len(rows):
            raise FetchError("P51GS13: duplicate or out-of-window years")
        print(f"  P51GS13  {len(series)} years {min(series)}-{max(series)}")
        put("fiscal/public_investment_from_oecd.csv", "gov_gfcf_pct_gdp",
            series, 2)
    else:
        print(f"  government GFCF skipped: {OECD_GFCF_SKIP}")

    collect.decimals = decimals  # type: ignore[attr-defined]
    collect.order = order        # type: ignore[attr-defined]
    return tables


# --------------------------------------------------------------- checks
def spot_checks(tables) -> None:
    """A known value per series. A refetch that moves one fails loudly.

    The tolerance absorbs an ordinary revision (3%, or 0.1 on a rate near
    zero); it does not absorb a unit read as thousands or the wrong row.
    """
    bad = []
    for rel, column, year, want in SPOT:
        got = tables.get(rel, {}).get(year, {}).get(column)
        if got is None or abs(got - want) > max(abs(want) * 0.03, 0.1):
            bad.append(f"{rel} {column} {year}: want {want}, got {got}")
    covered = {(rel, c) for rel, c, _, _ in SPOT}
    missing = [f"{rel} {c}" for rel, cols in collect.order.items()
               for c in cols if (rel, c) not in covered]
    if missing:
        bad.append(f"no spot value asserted for {missing}")
    if bad:
        raise FetchError("spot checks failed:\n  " + "\n  ".join(bad))
    print(f"Spot checks: {len(SPOT)} values as expected")


def national(rel: str, column: str, year: int) -> float | None:
    """One cell of a curated national file of this country."""
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    for row in csv.DictReader(lines):
        key = row.get("year") or row.get("fiscal_year")
        if key == str(year) and (row.get(column) or "").strip():
            return float(row[column])
    return None


def cross_checks(tables) -> None:
    """The harmonised number against the national one, where both exist.

    Where the two measure the same quantity the tolerance is tight and a
    miss is an error. Where they differ by definition (tol None) the pair
    is printed for the record and nothing is asserted.
    """
    bad = []
    print("Cross-checks against the national series")
    for label, rel, column, year, nrel, ncol, scale, tol in CROSS:
        h = tables[rel][year][column] * scale
        n = national(nrel, ncol, year)
        if n is None:
            bad.append(f"{label}: no national value {nrel}:{ncol} {year}")
            continue
        verdict = "printed only (different definitions)"
        if tol is not None:
            kind, limit = tol
            diff = abs(h - n) / abs(n) if kind == "rel" else abs(h - n)
            verdict = f"{'ok' if diff <= limit else 'FAIL'} ({kind} {diff:.3f} <= {limit})"
            if diff > limit:
                bad.append(f"{label} {year}: harmonised {h:.4g} vs national {n:.4g}")
        print(f"  {label} {year}: harmonised {h:,.4g} | {nrel}:{ncol} {n:,.4g} — {verdict}")
    if bad:
        raise FetchError("cross-checks failed:\n  " + "\n  ".join(bad))


# --------------------------------------------------------------- output
def write(tables) -> None:
    for rel in sorted(tables):
        columns = collect.order[rel]
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
