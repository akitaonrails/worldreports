#!/usr/bin/env python3
"""Refresh Paraguay's World Bank comparables into sidecar CSVs.

Usage:  make C=paraguay fetch   (or: python3 -I fetch/fetch_wb.py)

The World Bank is the harmonised layer for everything the Banco Central
del Paraguay publishes and this network cannot reach: national accounts,
prices, the labour market, reserves, the exchange rate, the balance of
payments trade lines, and the UN/WHO/UNODC series the security and
mortality chapters draw. It is **never** a substitute for a number
Paraguay publishes about itself — where a national series exists (INE's
population and vital statistics, MEF's fiscal accounts) the national
series is curated and this is the second, labelled line.

Written as `*_from_wb.csv` sidecars under data/. Never a curated file:
a person diffs these and promotes what they accept.

Wartime-style holes are holes: nothing here interpolates, forward-fills
or zero-fills, and the World Bank's own modelled series (ILO
unemployment, UN net migration) are labelled as modelled where they are
drawn.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

WB = ("https://api.worldbank.org/v2/country/PRY/indicator/{code}"
      "?format=json&per_page=200&date=2000:2026")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

YEAR_FROM, YEAR_TO = 2006, 2026

# (sidecar, indicator, column, decimals). Two indicators may share one
# sidecar; they are merged on year and a year one series does not cover
# is an empty cell.
WANTED = [
    ("macro/economy_from_wb.csv", "NY.GDP.MKTP.KD.ZG", "gdp_growth_pct", 2),
    ("macro/economy_from_wb.csv", "FP.CPI.TOTL.ZG", "cpi_inflation_pct", 2),
    ("macro/economy_from_wb.csv", "SL.UEM.TOTL.ZS", "unemployment_pct", 2),
    ("macro/economy_from_wb.csv", "NY.GDP.PCAP.CD", "gdp_per_person_usd", 0),
    ("macro/economy_from_wb.csv", "NE.GDI.FTOT.ZS", "gfcf_pct_gdp", 2),
    ("world/gdp_usd_from_wb.csv", "NY.GDP.MKTP.CD", "gdp_usd", 0),
    ("world/reserves_from_wb.csv", "FI.RES.TOTL.CD", "reserves_usd", 0),
    ("markets/fx_from_wb.csv", "PA.NUS.FCRF", "pyg_per_usd", 2),
    ("trade/trade_from_wb.csv", "NE.EXP.GNFS.ZS", "exports_pct_gdp", 2),
    ("trade/trade_from_wb.csv", "NE.IMP.GNFS.ZS", "imports_pct_gdp", 2),
    ("people/income_from_wb.csv", "SI.POV.GINI", "gini", 1),
    ("demography/population_from_wb.csv", "SP.POP.TOTL", "population", 0),
    ("demography/population_from_wb.csv", "SP.DYN.TFRT.IN", "fertility_rate", 3),
    ("demography/population_from_wb.csv", "SP.DYN.CBRT.IN", "birth_rate_per_1000", 2),
    ("demography/population_from_wb.csv", "SP.DYN.CDRT.IN", "death_rate_per_1000", 2),
    ("demography/migration_from_wb.csv", "SM.POP.NETM", "net_migration", 0),
    ("demography/migration_from_wb.csv", "SM.POP.TOTL", "migrant_stock", 0),
    ("security/security_from_wb.csv", "VC.IHR.PSRC.P5", "homicide_per_100k", 2),
    ("security/security_from_wb.csv", "SH.STA.SUIC.P5", "suicide_per_100k", 2),
    ("security/security_from_wb.csv", "SH.STA.TRAF.P5", "road_deaths_per_100k", 2),
    ("credit/credit_from_wb.csv", "FB.AST.NPER.ZS", "npl_ratio", 2),
    ("credit/credit_from_wb.csv", "FS.AST.PRVT.GD.ZS",
     "private_credit_pct_gdp", 2),
]

COMMENTS = {
    "macro/economy_from_wb.csv": [
        "World Bank WDI for Paraguay: NY.GDP.MKTP.KD.ZG real GDP growth,",
        "FP.CPI.TOTL.ZG consumer prices, SL.UEM.TOTL.ZS unemployment,",
        "NY.GDP.PCAP.CD GDP per person (current US$), NE.GDI.FTOT.ZS gross",
        "fixed capital formation. The CPI is the BCP's index as the World",
        "Bank records it; the BCP computes Paraguay's CPI, not the INE.",
        "Unemployment is the ILO modelled estimate, not the INE's EPHC:",
        "the two are separate columns and separate lines.",
    ],
    "markets/fx_from_wb.csv": [
        "World Bank PA.NUS.FCRF: official exchange rate, guaranies per US$,",
        "period average. The guarni has no minor unit in practice and no",
        "redenomination happened (the 2023 proposal was abandoned).",
    ],
    "demography/population_from_wb.csv": [
        "World Bank SP.POP.TOTL (UN World Population Prospects), mid-year.",
        "The NATIONAL series is INE's revision-2024 estimate/projection",
        "(demography/population.csv); this is the harmonised comparator.",
    ],
    "demography/migration_from_wb.csv": [
        "World Bank SM.POP.NETM (UN WPP modelled net migration, persons per",
        "year) and SM.POP.TOTL (UN DESA migrant stock, five-yearly points).",
        "Modelled: the plate labels it so. INE's own net-migration rate from",
        "the revision-2024 projection is the national line.",
    ],
    "credit/credit_from_wb.csv": [
        "World Bank FB.AST.NPER.ZS bank non-performing loans to total gross",
        "loans (%) and FS.AST.PRVT.GD.ZS domestic credit to the private",
        "sector by banks (% of GDP). Both are the Banco Central del",
        "Paraguay's supervisory data as the World Bank records them:",
        "bcp.gov.py itself answers a Cloudflare challenge. The second is",
        "PRIVATE-sector credit, not household debt — BIS total credit has",
        "no Paraguay series, so the household-debt slot stays pending.",
    ],
    "security/security_from_wb.csv": [
        "UNODC homicide (VC.IHR.PSRC.P5), WHO suicide (SH.STA.SUIC.P5) and",
        "WHO road traffic deaths (SH.STA.TRAF.P5) as the World Bank",
        "republishes them. The national homicide count is the Ministerio",
        "Publico's, which is not published as a machine series.",
    ],
}


def wb_series(code: str) -> dict[int, float]:
    """One World Bank indicator for Paraguay as {year: value}.

    The API answers a bad request with a JSON object carrying a message
    instead of the two-element array of a good one, so the shape is
    checked before anything is cached: a cached error survives the retry
    that would have fixed it.
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"wb_{code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        payload = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(WB.format(code=code),
                                             headers=HEADERS)
                with urllib.request.urlopen(req, timeout=90) as r:
                    payload = json.loads(r.read())
                if not (isinstance(payload, list) and len(payload) > 1
                        and isinstance(payload[1], list)):
                    raise ValueError("not an indicator response")
                cache_file.write_text(json.dumps(payload))
                break
            except Exception as e:  # noqa: BLE001
                print(f"  {code} attempt {attempt + 1}: {e}", file=sys.stderr)
                payload = None
                time.sleep(3 * (attempt + 1))
        if payload is None:
            return {}
    out = {}
    if isinstance(payload[1], list):
        for row in payload[1]:
            if row.get("value") is not None:
                out[int(row["date"])] = float(row["value"])
    return out


def write(rel: str, columns: list[tuple[str, dict[int, float], int]]) -> None:
    """A sidecar: `#` comments, then `year` plus one column per series."""
    empty = [c for c, s, _ in columns if not s]
    if empty:
        print(f"  !! {rel}: {empty} came back empty, nothing written",
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
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/{rel}  {rows} rows")


def verify(fetched: dict[str, dict[int, float]]) -> None:
    """Pin the magnitudes checked live on 2026-10-25.

    A silent revision, a currency change or a truncated payload fails
    here rather than landing in a sidecar nobody re-reads.
    """
    growth = fetched["NY.GDP.MKTP.KD.ZG"]
    # The 2019 drought/Argentina recession and the 2020 pandemic years.
    assert abs(growth[2019] - 0.0) < 1.5, f"WB growth 2019: {growth.get(2019)}"
    assert abs(growth[2020] - -0.8) < 1.5, f"WB growth 2020: {growth.get(2020)}"
    assert abs(growth[2023] - 4.7) < 0.6, f"WB growth 2023: {growth.get(2023)}"
    gdp = fetched["NY.GDP.MKTP.CD"]
    assert abs(gdp[2024] / 1e9 - 44.74) < 0.3, f"WB GDP 2024: {gdp.get(2024)}"
    assert abs(gdp[2025] / 1e9 - 49.28) < 0.3, f"WB GDP 2025: {gdp.get(2025)}"
    cpi = fetched["FP.CPI.TOTL.ZG"]
    assert abs(cpi[2022] - 9.77) < 0.2, f"WB CPI 2022: {cpi.get(2022)}"
    fx = fetched["PA.NUS.FCRF"]
    assert abs(fx[2006] - 5635.09) < 1.0, f"WB FX 2006: {fx.get(2006)}"
    assert abs(fx[2025] - 7545.0) < 5.0, f"WB FX 2025: {fx.get(2025)}"
    pop = fetched["SP.POP.TOTL"]
    assert abs(pop[2006] - 5_505_148) < 1000, f"WB pop 2006: {pop.get(2006)}"
    assert abs(pop[2025] - 7_013_000) < 5000, f"WB pop 2025: {pop.get(2025)}"
    hom = fetched["VC.IHR.PSRC.P5"]
    assert abs(hom[2006] - 13.48) < 0.1, f"WB homicide 2006: {hom.get(2006)}"
    assert abs(hom[2023] - 6.78) < 0.1, f"WB homicide 2023: {hom.get(2023)}"


def main() -> None:
    print("World Bank comparables for Paraguay")
    fetched = {code: wb_series(code) for _, code, _, _ in WANTED}
    sidecars: dict[str, list[tuple[str, dict[int, float], int]]] = {}
    for rel, code, column, dec in WANTED:
        sidecars.setdefault(rel, []).append((column, fetched[code], dec))
    for rel, columns in sidecars.items():
        write(rel, columns)
    if all(fetched[c] for _, c, _, _ in WANTED):
        verify(fetched)
        print("All discovery anchors verified.")
    else:
        missing = [c for _, c, _, _ in WANTED if not fetched[c]]
        print(f"!! incomplete fetch ({missing}) — verification skipped, "
              "sidecars partial", file=sys.stderr)
        sys.exit(1)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
