#!/usr/bin/env python3
"""The harmonised comparables for Singapore, into review sidecars.

    python3 -I fetch/fetch_comparables.py [--offline]

These are the layer that makes a city-state legible beside the others: the
same quantity, computed the same way, for every country. They are never a
substitute for a number Singapore publishes about itself, and where both
exist the national series is curated and this is the cross-check.

  World Bank   NY.GDP.MKTP.CD   GDP, current US$          (world slot 1)
               NY.GDP.PCAP.CD   GDP per person, current US$ (economy slot 2)
               FI.RES.TOTL.CD   reserves including gold, current US$
               SI.POV.GINI      Gini, World Bank harmonised
               SP.POP.TOTL      population (UN WPP, total, all residents)
               NE.EXP/IMP.GNFS.ZS  goods and services, % of GDP
               SP.DYN.CDRT.IN   crude death rate per 1,000
               SP.DYN.TFRT.IN   total fertility rate
               SP.DYN.LE00.IN   life expectancy
               VC.IHR.PSRC.P5   intentional homicide per 100,000 (UNODC)
               SH.STA.SUIC.P5   suicide per 100,000 (WHO)
               SH.STA.TRAF.P5   road deaths per 100,000 (WHO)
               SL.UEM.TOTL.ZS   unemployment, ILO modelled
               FP.CPI.TOTL.ZG   consumer prices, %
               NE.GDI.FTOT.ZS   gross fixed capital formation, % of GDP
               SM.POP.NETM      net migration (UN WPP)
  IMF          NGDP_RPCH        real GDP growth, % (WEO)
               GGXCNL_NGDP      general government net lending/borrowing, % GDP
               GGXWDG_NGDP      general government gross debt, % GDP
               G_X_G01_GDP_PT   general government expenditure, % GDP
                                  (Fiscal Monitor)
               PCPIPCH, LUR     CPI and unemployment, WEO vintage
  UNDP         HDI              Human Development Report, one vintage
  BIS          WS_TC            credit to households, % of GDP (Q4)

WHAT IS NOT HERE, AND WHY. Two of the spine's canonical fiscal series have
no Singapore row on the DataMapper: `rev` and `exp` come back EMPTY, and so
do `ie` and `pb`, while `GGXCNL_NGDP` and `GGXWDG_NGDP` are populated. The
Fiscal Monitor's revenue indicator `G_GR_G01_GDP_PT` returns no SGP series
either, though its expenditure indicator does. That is a coverage decision
by the publisher, not an access failure, and it is recorded in
SOURCES.yaml meta.pending rather than filled with a derived number.

`--offline` reads the cache and writes nothing new; a cold cache with
`--offline` exits non-zero having written nothing.
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
CACHE = ROOT / "cache" / "comparables"

ISO3 = "SGP"
WB = ("https://api.worldbank.org/v2/country/SGP/indicator/{code}"
      "?format=json&per_page=200&date=2000:2026")
IMF = "https://www.imf.org/external/datamapper/api/v1/{code}"
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
BIS = ("https://stats.bis.org/api/v1/data/WS_TC/Q.SG.H.A.M.770.A.E"
       "?format=csv&startPeriod=2005")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
IMF_HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}

YEAR_FROM, YEAR_TO = 2006, 2026
LAST_FULL_YEAR = 2025

WANTED = [
    ("world/gdp_usd_from_wb.csv", "NY.GDP.MKTP.CD", "gdp_usd", 0),
    ("world/gdp_per_person_from_wb.csv", "NY.GDP.PCAP.CD", "gdp_per_person_usd", 2),
    ("world/reserves_from_wb.csv", "FI.RES.TOTL.CD", "reserves_usd", 0),
    ("people/gini_from_wb.csv", "SI.POV.GINI", "gini", 1),
    ("demography/population_from_wb.csv", "SP.POP.TOTL", "population", 0),
    ("trade/trade_from_wb.csv", "NE.EXP.GNFS.ZS", "exports_pct_gdp", 2),
    ("trade/trade_from_wb.csv", "NE.IMP.GNFS.ZS", "imports_pct_gdp", 2),
    ("mortality/mortality_from_wb.csv", "SP.DYN.CDRT.IN", "death_rate_per_1000", 2),
    ("mortality/mortality_from_wb.csv", "SP.DYN.LE00.IN", "life_expectancy", 2),
    ("security/security_from_wb.csv", "VC.IHR.PSRC.P5", "homicide_per_100k", 3),
    ("security/security_from_wb.csv", "SH.STA.SUIC.P5", "suicide_per_100k", 2),
    ("security/security_from_wb.csv", "SH.STA.TRAF.P5", "road_deaths_per_100k", 2),
    ("macro/labour_from_wb.csv", "SL.UEM.TOTL.ZS", "unemployment_ilo_pct", 3),
    ("macro/cpi_from_wb.csv", "FP.CPI.TOTL.ZG", "cpi_inflation_pct", 2),
    ("macro/gfcf_from_wb.csv", "NE.GDI.FTOT.ZS", "gfcf_pct_gdp", 2),
    ("migration/net_migration_from_wb.csv", "SM.POP.NETM", "net_migration", 0),
    ("demography/fertility_from_wb.csv", "SP.DYN.TFRT.IN", "tfr", 3),
]

IMF_WANTED = [
    ("NGDP_RPCH", "macro/growth_from_imf.csv", "gdp_growth_pct", 2),
    ("PCPIPCH", "macro/cpi_from_imf.csv", "cpi_inflation_pct", 2),
    ("LUR", "macro/labour_from_imf.csv", "unemployment_pct", 2),
    ("GGXCNL_NGDP", "fiscal/balance_from_imf.csv", "balance_pct_gdp", 2),
    ("GGXWDG_NGDP", "fiscal/debt_from_imf.csv", "debt_pct_gdp", 2),
    ("G_X_G01_GDP_PT", "fiscal/expenditure_from_imf.csv",
     "expenditure_pct_gdp", 2),
]

COMMENTS = {
    "demography/population_from_wb.csv": [
        "World Bank SP.POP.TOTL (UN World Population Prospects), mid-year.",
        "SCOPE: this is the TOTAL population, including the non-resident",
        "population SingStat counts separately. SingStat's own series is in",
        "demography/population_from_singstat.csv and agrees to the person in",
        "2024-2025; the resident and citizen lines are different populations.",
    ],
    "world/reserves_from_wb.csv": [
        "World Bank FI.RES.TOTL.CD: reserves including gold, current US$.",
        "Cross-check: at the 2025 year-end exchange rate this is the same",
        "stock SingStat reports in SGD (world/reserves_from_singstat.csv).",
    ],
}


def from_cache(name: str, offline: bool, opener, parse):
    path = CACHE / name
    if path.exists():
        return parse(path.read_bytes())
    if offline:
        sys.exit(f"fetch_comparables: no cache at {path} and --offline given; "
                 "nothing written")
    return None


def wb_series(code: str, offline: bool) -> dict[int, float]:
    """One World Bank indicator for Singapore as {year: value}.

    A bad indicator answers a JSON object carrying a message rather than the
    two-element array of a good response, so the shape is checked before the
    bytes are cached — a cached error survives the retry that would fix it.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = from_cache(f"wb_{code}.json", offline, None, json.loads)
    if cached is not None:
        payload = cached
    else:
        for attempt in range(4):
            try:
                req = urllib.request.Request(WB.format(code=code), headers=HEADERS)
                with urllib.request.urlopen(req, timeout=90) as fh:
                    payload = json.loads(fh.read())
                if not (isinstance(payload, list) and len(payload) > 1
                        and isinstance(payload[1], list)):
                    raise ValueError("not an indicator response")
                (CACHE / f"wb_{code}.json").write_text(
                    json.dumps(payload), encoding="utf-8")
                break
            except Exception as exc:                      # noqa: BLE001
                print(f"  {code} attempt {attempt + 1}: {exc}", file=sys.stderr)
                time.sleep(4 * (attempt + 1))
        else:
            return {}
    return {int(r["date"]): float(r["value"]) for r in payload[1]
            if r.get("value") is not None}


def imf_series(code: str, offline: bool) -> dict[int, float]:
    """One IMF DataMapper indicator for Singapore as {year: value}.

    The payload nests as {"values": {<code>: {"SGP": {<year>: ...}}}}. A
    country the dataset does not cover comes back as an ABSENT or empty
    inner object rather than an error, which is the Singapore fiscal case —
    so the caller distinguishes "empty" from "failed".
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = from_cache(f"imf_{code}.json", offline, None, json.loads)
    if cached is not None:
        payload = cached
    else:
        for attempt in range(4):
            try:
                req = urllib.request.Request(IMF.format(code=code),
                                             headers=IMF_HEADERS)
                with urllib.request.urlopen(req, timeout=90) as fh:
                    payload = json.loads(fh.read())
                if "values" not in payload:
                    raise ValueError("not a DataMapper response")
                (CACHE / f"imf_{code}.json").write_text(
                    json.dumps(payload), encoding="utf-8")
                break
            except Exception as exc:                      # noqa: BLE001
                print(f"  {code} attempt {attempt + 1}: {exc}", file=sys.stderr)
                time.sleep(4 * (attempt + 1))
        else:
            return {}
    values = payload.get("values", {}).get(code, {}) or {}
    series = values.get(ISO3, {}) or {}
    return {int(y): float(v) for y, v in series.items() if v is not None}


def hdi_series(offline: bool) -> dict[int, float]:
    """Singapore's HDI by year from the HDR composite-indices file.

    One row per country and one column per year, plus sibling columns for
    the rank and the sex-disaggregated values — so the key must match
    `hdi_YYYY` exactly or the match pulls a rank into a value. The file is
    Latin-1, not UTF-8.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "hdr25_composite_indices.csv"
    if not path.exists():
        if offline:
            sys.exit(f"fetch_comparables: no cache at {path} and --offline "
                     "given; nothing written")
        req = urllib.request.Request(HDR, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=180) as fh:
            raw = fh.read()
        raw.decode("latin-1")            # validated before the bytes are cached
        path.write_bytes(raw)
    out = {}
    for row in csv.DictReader(io.StringIO(path.read_bytes().decode("latin-1"))):
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


def bis_household_credit(offline: bool) -> dict[int, float]:
    """BIS credit to households as % of GDP, year-end (Q4) observation.

    The key needs all eight WS_TC dimensions: with the collection segment
    omitted the API does not error, it serves a different country's series —
    the first probe of `Q.SG.H.A.M.770.A` returned Australia. The country
    code is asserted from the CSV's own TITLE_TS column before anything is
    parsed as Singapore.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "bis_ws_tc_sg.csv"
    if not path.exists():
        if offline:
            sys.exit(f"fetch_comparables: no cache at {path} and --offline "
                     "given; nothing written")
        req = urllib.request.Request(BIS, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=120) as fh:
            raw = fh.read()
        if b"Singapore" not in raw:
            sys.exit("fetch_comparables: BIS payload does not name Singapore; "
                     "nothing written")
        path.write_bytes(raw)
    out = {}
    meta = {}
    for row in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))):
        if row.get("BORROWERS_CTY") != "SG":
            continue
        title = row.get("TITLE_TS") or ""
        if not title.startswith("Singapore"):
            sys.exit(f"fetch_comparables: BIS row is {title[:60]!r}, not "
                     "Singapore; nothing written")
        if "Percentage of GDP" not in title:
            sys.exit("fetch_comparables: BIS unit is not % of GDP; "
                     "nothing written")
        period = row.get("TIME_PERIOD") or ""
        if not row.get("OBS_VALUE") or "-Q4" not in period:
            continue
        meta[int(period[:4])] = row.get("OBS_STATUS", "")
        out[int(period[:4])] = float(row["OBS_VALUE"])
    return out


def write(rel: str, columns: list[tuple[str, dict[int, float], int]]) -> None:
    """A sidecar: `#` comments, then `year` plus one column per series.

    Columns of one file merge on year; a year a series does not cover is an
    empty cell, never a zero or a carried value.
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
    for year in years:
        if not YEAR_FROM <= year <= YEAR_TO:
            continue
        lines.append(f"{year}," + ",".join(
            f"{series[year]:.{dec}f}" if year in series else ""
            for _, series, dec in columns))
        rows += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/{rel}  {rows} rows")


def write_imf(rel: str, code: str, column: str, dec: int) -> dict[int, float]:
    """Observed years in one column, WEO projections apart in another.

    Every year carries exactly one of the two, and the disjointness is
    asserted rather than assumed, so a forecast can never be drawn as an
    outturn by accident.
    """
    series = imf_series(code, OFFLINE)
    if not series:
        print(f"  !! {rel}: {code} came back empty — no Singapore series; "
              "nothing written", file=sys.stderr)
        return {}
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# IMF DataMapper {code}, one vintage. Years past "
             f"{LAST_FULL_YEAR} are WEO forecasts in the _proj column only."]
    lines.append(f"year,{column},{column}_proj")
    rows = 0
    for year in sorted(series):
        if not YEAR_FROM <= year <= YEAR_TO:
            continue
        observed = year <= LAST_FULL_YEAR
        cells = (f"{series[year]:.{dec}f}", "") if observed \
            else ("", f"{series[year]:.{dec}f}")
        assert (cells[0] == "") != (cells[1] == ""), \
            f"{code} {year}: observed/projected disjointness broken"
        lines.append(f"{year},{cells[0]},{cells[1]}")
        rows += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/{rel}  {rows} rows")
    return series


def verify(wb, hdi, imf_growth, fiscal) -> None:
    """Pin the observations the discovery pass verified live on 2026-10-25."""
    assert abs(wb["NY.GDP.PCAP.CD"][2024] - 94896.56) < 0.05, \
        f"WB GDP per person 2024: {wb['NY.GDP.PCAP.CD'].get(2024)}"
    assert abs(wb["NY.GDP.PCAP.CD"][2025] - 98813.98) < 0.05, \
        f"WB GDP per person 2025: {wb['NY.GDP.PCAP.CD'].get(2025)}"
    # The World Bank's total population is SingStat's to the person.
    assert abs(wb["SP.POP.TOTL"][2024] - 6036860) < 1, \
        f"WB population 2024: {wb['SP.POP.TOTL'].get(2024)}"
    assert abs(wb["SP.POP.TOTL"][2025] - 6111175) < 1, \
        f"WB population 2025: {wb['SP.POP.TOTL'].get(2025)}"
    assert abs(wb["NY.GDP.MKTP.CD"][2024] / 1e9 - 572.88) < 0.02, \
        f"WB GDP 2024: {wb['NY.GDP.MKTP.CD'].get(2024)}"
    assert abs(wb["FI.RES.TOTL.CD"][2025] / 1e9 - 432.11) < 0.05, \
        f"WB reserves 2025: {wb['FI.RES.TOTL.CD'].get(2025)}"
    # The IMF agrees with SingStat on real growth, which is the check that
    # the national chained series and the WEO line describe one economy.
    assert abs(imf_growth[2024] - 5.3) < 0.01, f"IMF growth 2024: {imf_growth.get(2024)}"
    assert abs(imf_growth[2025] - 5.0) < 0.01, f"IMF growth 2025: {imf_growth.get(2025)}"
    # Singapore's gross debt is issued against assets; the ratio is large
    # and it is not a net position. Pinned so a scope change is visible.
    assert abs(fiscal["GGXWDG_NGDP"][2024] - 165.8) < 0.02, \
        f"IMF gross debt 2024: {fiscal['GGXWDG_NGDP'].get(2024)}"
    assert abs(fiscal["GGXCNL_NGDP"][2024] - 3.8) < 0.02, \
        f"IMF balance 2024: {fiscal['GGXCNL_NGDP'].get(2024)}"
    assert abs(hdi[2023] - 0.946) < 0.001, f"UNDP HDI 2023: {hdi.get(2023)}"


def main(argv: list[str]) -> int:
    global OFFLINE
    OFFLINE = "--offline" in argv
    print("World Bank / IMF / UNDP / BIS comparables for Singapore")
    fetched = {code: wb_series(code, OFFLINE) for _, code, _, _ in WANTED}
    sidecars: dict[str, list[tuple[str, dict[int, float], int]]] = {}
    for rel, code, column, dec in WANTED:
        sidecars.setdefault(rel, []).append((column, fetched[code], dec))
    for rel, columns in sidecars.items():
        write(rel, columns)

    hdi = hdi_series(OFFLINE)
    write("world/hdi_from_undp.csv", [("hdi", hdi, 3)])

    imf_growth = write_imf("macro/growth_from_imf.csv", "NGDP_RPCH",
                           "gdp_growth_pct", 2)
    write_imf("macro/cpi_from_imf.csv", "PCPIPCH", "cpi_inflation_pct", 2)
    write_imf("macro/labour_from_imf.csv", "LUR", "unemployment_pct", 2)
    fiscal = {}
    for code, rel, column, dec in IMF_WANTED[3:]:
        got = write_imf(rel, code, column, dec)
        if got:
            fiscal[code] = got

    bis = bis_household_credit(OFFLINE)
    write("credit/household_from_bis.csv",
          [("household_credit_pct_gdp", bis, 1)])

    # SI.POV.GINI has no Singapore row at all (the World Bank's poverty
    # database does not cover it), so the gate is on the series verify()
    # actually reads, not on every indicator requested.
    needed = ("NY.GDP.PCAP.CD", "SP.POP.TOTL", "NY.GDP.MKTP.CD",
              "FI.RES.TOTL.CD")
    if all(fetched[c] for c in needed) and hdi and imf_growth \
            and len(fiscal) == 3:
        verify(fetched, hdi, imf_growth, fiscal)
        print("All discovery anchors verified.")
    else:
        print("!! incomplete fetch — verification skipped", file=sys.stderr)
    print("Done. Diff the sidecars before adopting.")
    return 0


OFFLINE = False

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
