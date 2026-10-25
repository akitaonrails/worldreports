#!/usr/bin/env python3
"""Refresh Venezuela's World Bank comparables into review sidecars.

Usage:  python3 -I fetch/fetch_worldbank.py [--offline]

Every series here is the World Bank's compilation of somebody else's
statistic: the national accounts the BCV stopped submitting, the CPI it used
to submit, the UN population estimate, UNODC's homicide count. They are the
layer that makes Venezuela legible beside other countries, never a substitute
for a number Venezuela publishes about itself. The one national series that
does exist (the INE's Gini) is fetched by fetch_ine.py and drawn beside these.

Two things this fetcher refuses to do, both of which the raw API invites:

  * **Write a placeholder zero as data.** For NE.GDI.FTOT.ZS, NE.EXP.GNFS.ZS
    and NE.IMP.GNFS.ZS the API answers 0.0 for 2006-2011. Venezuela did not
    have zero exports and zero investment: the national-accounts series the
    ratio is built from does not exist for those years, and the gateway
    returns a zero rather than an empty cell. Those years are dropped, with
    the reason in the sidecar header, so a plate draws a hole and not a
    collapse.
  * **Treat a 200 as proof of data.** The gateway serves an HTML error page or
    a one-element error object under a valid HTTP status; the payload shape is
    checked before anything is cached, because a cached error page survives
    the retry that would have fixed it.

Offline behaviour: `--offline` reads only the cache. A cold cache exits 2 and
writes nothing — it never falls back to the network and never writes a partial
sidecar. Two online runs and two warm offline runs are byte-identical.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
ISO3 = "VEN"
BASE = ("https://api.worldbank.org/v2/country/" + ISO3 + "/indicator/{code}"
        "?format=json&per_page=200&date=2000:2026")
# The World Bank gateway answers a browser UA; a bare urllib UA is served too,
# but the descriptive string keeps the request identifiable in its logs.
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}

YEAR_FROM, YEAR_TO = 2006, 2026

# Indicators the API reports as a flat 0.0 in years where the underlying
# series is absent. Verified live 2026-10-25: every 2000-2011 value of these
# three is exactly 0.0 and the 2012 value is a plausible ratio, which is the
# signature of a placeholder rather than an observation.
ZERO_PLACEHOLDER_BEFORE = {
    "NE.GDI.FTOT.ZS": 2012,
    "NE.EXP.GNFS.ZS": 2012,
    "NE.IMP.GNFS.ZS": 2012,
}

# (sidecar, indicator, column, decimals)
WANTED = [
    ("macro/economy_from_worldbank.csv", "NY.GDP.MKTP.KD.ZG",
     "gdp_growth_pct", 2),
    ("macro/economy_from_worldbank.csv", "FP.CPI.TOTL.ZG",
     "cpi_inflation_pct", 2),
    ("macro/economy_from_worldbank.csv", "SL.UEM.TOTL.ZS",
     "unemployment_pct", 3),
    ("spending/spending_from_worldbank.csv", "NE.GDI.FTOT.ZS",
     "gfcf_pct_gdp", 2),
    ("trade/trade_from_worldbank.csv", "NE.EXP.GNFS.ZS",
     "exports_pct_gdp", 2),
    ("trade/trade_from_worldbank.csv", "NE.IMP.GNFS.ZS",
     "imports_pct_gdp", 2),
    ("world/gdp_usd_from_worldbank.csv", "NY.GDP.MKTP.CD",
     "gdp_usd", 0),
    ("world/gdp_per_person_from_worldbank.csv", "NY.GDP.PCAP.CD",
     "gdp_per_person_usd", 2),
    ("world/reserves_from_worldbank.csv", "FI.RES.TOTL.CD",
     "reserves_usd", 0),
    ("people/gini_from_worldbank.csv", "SI.POV.GINI", "gini", 1),
    ("demography/population_from_worldbank.csv", "SP.POP.TOTL",
     "population", 0),
    ("demography/vital_from_worldbank.csv", "SP.DYN.TFRT.IN",
     "fertility_rate", 3),
    ("demography/vital_from_worldbank.csv", "SP.DYN.CBRT.IN",
     "birth_rate_per_1000", 3),
    ("demography/vital_from_worldbank.csv", "SP.DYN.CDRT.IN",
     "death_rate_per_1000", 3),
    ("demography/vital_from_worldbank.csv", "SP.DYN.LE00.IN",
     "life_expectancy", 3),
    ("migration/migration_from_worldbank.csv", "SM.POP.NETM",
     "net_migration", 0),
    ("migration/migration_from_worldbank.csv", "SM.POP.TOTL",
     "migrant_stock", 0),
    ("security/security_from_worldbank.csv", "VC.IHR.PSRC.P5",
     "homicide_per_100k", 3),
    ("security/security_from_worldbank.csv", "SH.STA.SUIC.P5",
     "suicide_per_100k", 2),
    ("security/security_from_worldbank.csv", "SH.STA.TRAF.P5",
     "road_deaths_per_100k", 2),
    ("markets/fx_official_from_worldbank.csv", "PA.NUS.FCRF",
     "lcu_per_usd", 4),
]

COMMENTS = {
    "macro/economy_from_worldbank.csv": [
        "World Bank WDI for Venezuela (VEN), current vintage, pulled 2026-10-25.",
        "gdp_growth_pct NY.GDP.MKTP.KD.ZG: the World Bank's own estimate of",
        "  real growth — Venezuela has submitted no national accounts to it",
        "  since the 2000s, so these are staff estimates of a rebased series,",
        "  not BCV outturns. IMF WEO NGDP_RPCH agrees on sign every year and",
        "  differs on size (2020: -29.8 here, -33.2 there).",
        "cpi_inflation_pct FP.CPI.TOTL.ZG: the BCV's INPC as the World Bank",
        "  records it, 2009-2016 ONLY. It stops when the BCV stopped",
        "  submitting; the hyperinflation years are IMF staff estimates and",
        "  live in macro/inflation_from_imf.csv. The two are never spliced.",
        "unemployment_pct SL.UEM.TOTL.ZS: ILO modelled estimate, not a",
        "  labour-force survey. The INE's own Encuesta de Hogares tabulado is",
        "  published (fetch_ine.py, meta.pending) but its concept codes carry",
        "  no inline labels.",
    ],
    "spending/spending_from_worldbank.csv": [
        "World Bank NE.GDI.FTOT.ZS: gross fixed capital formation, % of GDP.",
        "2006-2011 are NOT zero: the API returns a placeholder 0.0 for years",
        "where the national-accounts series behind the ratio is absent, and",
        "this fetcher drops them. The line starts in 2012.",
    ],
    "trade/trade_from_worldbank.csv": [
        "World Bank NE.EXP.GNFS.ZS / NE.IMP.GNFS.ZS: exports and imports of",
        "goods and services, % of GDP, national-accounts basis. 2006-2011 are",
        "dropped placeholder zeros, not observations — the line starts 2012.",
        "The trade balance on the plate is derived from these two columns and",
        "never from a second publisher.",
    ],
    "world/gdp_usd_from_worldbank.csv": [
        "World Bank NY.GDP.MKTP.CD, current US$, converted at the official",
        "rate of each year. DEFINITIONAL TRAP: the IMF WEO's NGDPD for the",
        "same years is much lower (2014: US$128.8bn there against US$214.8bn",
        "here) because the two apply different exchange-rate conventions to a",
        "multi-rate economy. The World Bank is the canonical slot per",
        "PLATE_SPINE; the IMF line is a separate column, never a correction.",
    ],
    "world/gdp_per_person_from_worldbank.csv": [
        "World Bank NY.GDP.PCAP.CD, current US$ per person, same population",
        "denominator as SP.POP.TOTL (UN WPP mid-year).",
    ],
    "world/reserves_from_worldbank.csv": [
        "World Bank FI.RES.TOTL.CD, year-end, current US$. STOPS IN 2017: the",
        "BCV stopped reporting and its site is unreachable from this network",
        "(TLS chain), so 2018-2025 are holes, not zeros.",
    ],
    "people/gini_from_worldbank.csv": [
        "World Bank SI.POV.GINI, 0-100: the SEDLAC-harmonised household-survey",
        "Gini. It ends in 2006 — inside this window only 2006 survives, which",
        "is why it is a cross-check on the INE's own series rather than a",
        "line. 2006: 44.7 here, 44.2 from the INE's tabulado.",
    ],
    "demography/population_from_worldbank.csv": [
        "World Bank SP.POP.TOTL = UN World Population Prospects, mid-year",
        "de-facto total. Includes the whole territory; there is no second",
        "national register to compare it with (the INE's 2011 census is a",
        "stock at one date, not a series).",
    ],
    "demography/vital_from_worldbank.csv": [
        "World Bank SP.DYN.* — fertility (children per woman), crude birth and",
        "death rates per 1,000, life expectancy at birth (UN WPP). These are",
        "modelled: the INE's civil-registration counts stop being published as",
        "a machine-readable series and the .xls it does publish are legacy",
        "BIFF files (meta.pending).",
    ],
    "migration/migration_from_worldbank.csv": [
        "World Bank SM.POP.NETM: net migration, COUNT of people (UN WPP",
        "modelled 5-year net). Not a rate: the plate divides by the same",
        "vintage's mid-year population and says so. 2018 = -1,355,602.",
        "SM.POP.TOTL: UN DESA migrant stock, a SNAPSHOT series (2000, 2005,",
        "2010, 2015, 2020, 2024) — never interpolated between those years.",
    ],
    "security/security_from_worldbank.csv": [
        "UNODC (VC.IHR.PSRC.P5 homicide) and WHO (SH.STA.SUIC.P5 suicide,",
        "SH.STA.TRAF.P5 road deaths) as the World Bank republishes them.",
        "Homicide has holes at 2013 and 2018 and a sharp fall after 2019 that",
        "is an estimate, not a police count: the national publisher is the",
        "Cuerpo de Investigaciones Científicas (meta.pending).",
    ],
    "markets/fx_official_from_worldbank.csv": [
        "World Bank PA.NUS.FCRF: official exchange rate, local currency units",
        "per US$, period average. STOPS IN 2017. The values are quoted in the",
        "unit of the day: 2006-2007 in bolívares fuertes (the 2008",
        "redenomination applied retroactively), 2008-2017 in bolívares",
        "fuertes. Converting to the 2021 bolívar (VES) needs the divisors in",
        "DATA_NOTES.md; the collapse after 2017 is not measurable here at all",
        "because no official rate survives any route tried.",
    ],
}


def fetch(indicator: str, offline: bool) -> dict[int, float]:
    """One indicator as {year: value}, cache-first, shape-checked."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"wb_{ISO3}_{indicator}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    elif offline:
        print(f"  !! {indicator}: offline and no cache", file=sys.stderr)
        raise SystemExit(2)
    else:
        last = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(BASE.format(code=indicator),
                                             headers=HEADERS)
                with urllib.request.urlopen(req, timeout=90) as r:
                    body = r.read()
                ctype = r.headers.get("Content-Type", "")
                if "json" not in ctype:
                    raise ValueError(f"content-type {ctype!r} is not JSON")
                payload = json.loads(body)
                # A good indicator answer is [metadata, [rows...]]. An error
                # answer is a one-element list or an object with a message.
                if not (isinstance(payload, list) and len(payload) == 2
                        and isinstance(payload[1], list)):
                    raise ValueError("not an indicator response")
                cache_file.write_text(json.dumps(payload))
                break
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"  {indicator} attempt {attempt + 1}: {e}",
                      file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        else:
            raise SystemExit(f"{indicator}: {last}")

    out: dict[int, float] = {}
    for row in payload[1]:
        if row.get("value") is None:
            continue
        out[int(row["date"])] = float(row["value"])

    cutoff = ZERO_PLACEHOLDER_BEFORE.get(indicator)
    if cutoff:
        dropped = [y for y, v in out.items() if y < cutoff and v == 0.0]
        for y in dropped:
            del out[y]
        # Anything left before the cutoff that is not a placeholder is data
        # and must not be silently dropped by this rule.
        left = sorted(y for y in out if y < cutoff)
        if left:
            print(f"  note: {indicator} has real values before {cutoff}: "
                  f"{left[:6]}", file=sys.stderr)
    return out


def write(rel: str, columns: list[tuple[str, dict[int, float], int]]) -> None:
    if not all(series for _, series, _ in columns):
        print(f"  !! {rel}: a series came back empty, nothing written",
              file=sys.stderr)
        raise SystemExit(3)
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
        if not any(cells):
            continue
        lines.append(f"{y}," + ",".join(cells))
        rows += 1
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {rows} rows")


def verify(s: dict[str, dict[int, float]]) -> None:
    """Pin what the discovery pass verified live 2026-10-25."""
    g = s["NY.GDP.MKTP.KD.ZG"]
    assert abs(g[2020] - -29.82) < 0.02, f"growth 2020: {g.get(2020)}"
    assert abs(g[2019] - -27.62) < 0.02, f"growth 2019: {g.get(2019)}"
    assert abs(g[2025] - 1.57) < 0.02, f"growth 2025: {g.get(2025)}"
    cpi = s["FP.CPI.TOTL.ZG"]
    assert max(cpi) == 2016 and abs(cpi[2016] - 254.95) < 0.02, \
        f"national CPI row set changed: {sorted(cpi)[-3:]}"
    assert min(cpi) == 2009, f"national CPI starts {min(cpi)}, not 2009"
    gdp = s["NY.GDP.MKTP.CD"]
    assert abs(gdp[2013] / 1e9 - 258.51) < 0.02, f"GDP 2013: {gdp.get(2013)}"
    assert abs(gdp[2020] / 1e9 - 42.84) < 0.02, f"GDP 2020: {gdp.get(2020)}"
    assert abs(gdp[2025] / 1e9 - 99.66) < 0.02, f"GDP 2025: {gdp.get(2025)}"
    pop = s["SP.POP.TOTL"]
    assert abs(pop[2006] - 27_224_686) < 1, f"population 2006: {pop.get(2006)}"
    assert abs(pop[2025] - 28_516_896) < 1, f"population 2025: {pop.get(2025)}"
    # The placeholder zeros are gone, not drawn as a collapse.
    for code in ("NE.EXP.GNFS.ZS", "NE.IMP.GNFS.ZS", "NE.GDI.FTOT.ZS"):
        assert all(y >= 2012 for y in s[code]), \
            f"{code}: a placeholder zero survived ({sorted(s[code])[:3]})"
    assert abs(s["NE.EXP.GNFS.ZS"][2019] - 47.20) < 0.02, \
        f"exports 2019: {s['NE.EXP.GNFS.ZS'].get(2019)}"
    # Reserves stop where the BCV stopped reporting.
    assert max(s["FI.RES.TOTL.CD"]) == 2017, \
        f"reserves row set changed: {sorted(s['FI.RES.TOTL.CD'])[-3:]}"
    assert abs(s["FI.RES.TOTL.CD"][2017] / 1e9 - 9.79) < 0.02, \
        f"reserves 2017: {s['FI.RES.TOTL.CD'].get(2017)}"
    gin = s["SI.POV.GINI"]
    assert max(gin) == 2006 and abs(gin[2006] - 44.7) < 0.05, \
        f"WDI Gini row set changed: {sorted(gin)[-3:]}"
    hom = s["VC.IHR.PSRC.P5"]
    assert 2013 not in hom and 2018 not in hom, \
        f"homicide holes filled: {sorted(hom)}"
    assert abs(hom[2012] - 54.382) < 0.01, f"homicide 2012: {hom.get(2012)}"
    # The official rate is the last year the BCV reported one.
    fx = s["PA.NUS.FCRF"]
    assert max(fx) == 2017 and abs(fx[2006] - 2.147) < 0.001, \
        f"official FX row set changed: {sorted(fx)[-3:]}"
    assert abs(fx[2017] - 9.9753) < 0.001, f"FX 2017: {fx.get(2017)}"
    mig = s["SM.POP.NETM"]
    assert abs(mig[2018] - -1_355_602) < 1, f"net migration 2018: {mig.get(2018)}"
    assert abs(s["SM.POP.TOTL"][2024] - 1_263_304) < 1, "migrant stock 2024"


def main() -> None:
    offline = "--offline" in sys.argv[1:]
    print("World Bank comparables for Venezuela"
          + (" (offline)" if offline else ""))
    fetched = {code: fetch(code, offline) for _, code, _, _ in WANTED}
    sidecars: dict[str, list[tuple[str, dict[int, float], int]]] = {}
    for rel, code, column, dec in WANTED:
        sidecars.setdefault(rel, []).append((column, fetched[code], dec))
    for rel, columns in sidecars.items():
        write(rel, columns)
    verify(fetched)
    print("All discovery anchors verified. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
