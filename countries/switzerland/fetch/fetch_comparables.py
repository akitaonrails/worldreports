#!/usr/bin/env python3
"""Refresh the cross-country comparables for Switzerland into sidecar CSVs.

Usage:  python3 -I countries/switzerland/fetch/fetch_comparables.py

These are the layer that makes a country legible to a reader who does not
live in it: the same quantity, computed the same way, for everyone. They
are never a substitute for a number Switzerland publishes about itself.
Where both exist (GDP, population, the Gini, government debt) the national
series is the curated one and this is the cross-check. All of it is
`official: false` in SOURCES.yaml.

  World Bank    NY.GDP.MKTP.CD    GDP, current US$
                NY.GDP.PCAP.CD    GDP per person, current US$
                SP.POP.TOTL       population, mid-year
                FI.RES.TOTL.CD    reserves including gold, current US$
                SI.POV.GINI       Gini, World Bank harmonised
                NE.TRD.GNFS.ZS    trade as a share of GDP
  UNDP          HDI, from the HDR25 composite-indices file
  IMF           GGXWDG_NGDP       general government gross debt, % GDP

GDP VINTAGE (Swiss trap 1). The BFS revised the national accounts on
2026-08-25; the World Bank still carries the PREVIOUS BFS vintage for 2023
onward (2024 US$969.9bn; the current BFS vintage gives about US$978bn).
Every World Bank ratio here (openness, GDP per person) is on that old
denominator. The CSV comments say so; never divide these by BFS numbers.

The HDR file is a single vintage covering every year: the HDI is
recomputed for the whole back-series at each methodology change, so one
file, one vintage. It is Latin-1 and the host answers 403 to urllib's UA.

The IMF DataMapper series is general government gross debt in the GFS
sense, which for Switzerland equals the EFV's GFS total-liabilities ratio
(40.4% in 2024), NOT the Maastricht 23.7% (Swiss trap 5). Calendar years.
The payload carries WEO projections to 2031 beside the history; years
after last_full_year go only into the `_proj` column, never the observed
one, and the two never share a row.

The World Bank Gini lags: 2024 and 2025 are null. Holes stay holes.
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
ISO3 = "CHE"

WB = ("https://api.worldbank.org/v2/country/CHE/indicator/{code}"
      "?format=json&per_page=200&date=2006:2026")
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
IMF = "https://www.imf.org/external/datamapper/api/v1/{code}/CHE"
# hdr.undp.org answers 403 to the default urllib User-Agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
# www.imf.org's edge answers 403 to any UA starting with "Mozilla/5.0"
# (UK lane, verified 2026-10-22); a plain descriptive UA gets 200.
IMF_HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}

YEAR_FROM, YEAR_TO = 2006, 2026      # country.yaml window
LAST_FULL_YEAR = 2025

OLD_VINTAGE = ("# GDP vintage: World Bank WDI carries the PREVIOUS BFS national-"
               "accounts vintage for 2023+ (BFS revised 2026-08-25); do not mix "
               "with BFS-vintage numbers.")

# (sidecar, indicator, column, decimals, comment lines)
WANTED = [
    ("international/gdp_usd_from_wb.csv", "NY.GDP.MKTP.CD", "gdp_usd", 0,
     ["# World Bank NY.GDP.MKTP.CD, Switzerland (CHE). Units: current US$ (not mn).",
      OLD_VINTAGE]),
    ("international/gdp_pc_from_wb.csv", "NY.GDP.PCAP.CD", "gdp_per_person_usd", 0,
     ["# World Bank NY.GDP.PCAP.CD, Switzerland. Units: current US$ per person.",
      OLD_VINTAGE]),
    ("international/population_from_wb.csv", "SP.POP.TOTL", "population", 0,
     ["# World Bank SP.POP.TOTL, Switzerland. Units: persons, MID-YEAR estimate",
      "# (sits between BFS STATPOP 1 Jan and 31 Dec). Cross-check only."]),
    ("international/reserves_from_wb.csv", "FI.RES.TOTL.CD", "reserves_usd", 0,
     ["# World Bank FI.RES.TOTL.CD (IMF IFS), Switzerland. Units: current US$,",
      "# total reserves including gold, end of year."]),
    ("international/gini_from_wb.csv", "SI.POV.GINI", "gini", 1,
     ["# World Bank SI.POV.GINI, Switzerland. Units: Gini index 0-100.",
      "# Years the Bank leaves null are absent (holes stay holes)."]),
    ("international/openness_from_wb.csv", "NE.TRD.GNFS.ZS", "trade_pct_gdp", 1,
     ["# World Bank NE.TRD.GNFS.ZS, Switzerland. Units: % of GDP, exports +",
      "# imports of goods and services (BoP basis, gold flows included).",
      OLD_VINTAGE]),
]


def get(url: str, headers: dict, timeout: int = 90) -> bytes:
    """GET with polite spacing and back-off on 429/403/5xx."""
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            time.sleep(1)
            return body
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (403, 429) and e.code < 500:
                break
            time.sleep(10 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def wb_series(code: str) -> dict[int, float]:
    """One World Bank indicator for CHE as {year: value}.

    The API answers a bad request with a JSON object carrying a message
    instead of the two-element array of a good one; the shape is checked
    before caching, so an error page never survives into the cache.
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"cmp_wb_{code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        try:
            payload = json.loads(get(WB.format(code=code), HEADERS))
        except Exception as e:  # noqa: BLE001
            print(f"  !! WB {code}: {e}", file=sys.stderr)
            return {}
        if not (isinstance(payload, list) and len(payload) > 1
                and isinstance(payload[1], list) and payload[1]):
            raise RuntimeError(f"WB {code}: not an indicator response")
        if payload[1][0].get("countryiso3code") != ISO3:
            raise RuntimeError(f"WB {code}: wrong country in payload")
        cache_file.write_text(json.dumps(payload))
    return {int(row["date"]): float(row["value"])
            for row in payload[1] if row.get("value") is not None}


def hdr_hdi() -> dict[int, float]:
    """Switzerland's HDI by year from the HDR composite-indices file.

    One row per country, one COLUMN per year, with sibling rank and
    sex-disaggregated columns, so the key must be exactly `hdi_YYYY`
    (a prefix match would pull in `hdi_rank_2023`).
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "cmp_hdr25_series.csv"
    if not cache_file.exists():
        try:
            body = get(HDR, HEADERS, timeout=180)
        except Exception as e:  # noqa: BLE001
            print(f"  !! HDR: {e}", file=sys.stderr)
            return {}
        head = body[:2000].decode("latin-1").lower()
        if "iso3" not in head or "hdi_2023" not in head:
            raise RuntimeError("HDR: not the composite-indices CSV")
        cache_file.write_bytes(body)
    text = cache_file.read_bytes().decode("latin-1")
    for row in csv.DictReader(io.StringIO(text)):
        if (row.get("iso3") or row.get("ISO3")) != ISO3:
            continue
        out: dict[int, float] = {}
        for key, value in row.items():
            if not key or value in (None, "", ".."):
                continue
            name = key.lower()
            year = name.rsplit("_", 1)[-1]
            if year.isdigit() and name == f"hdi_{year}":
                out[int(year)] = float(value)
        return out
    raise RuntimeError("HDR: no CHE row")


def imf_series(code: str) -> dict[int, float]:
    """One IMF WEO indicator for CHE as {year: value}, projections included."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"cmp_imf_{code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        try:
            payload = json.loads(get(IMF.format(code=code), IMF_HEADERS))
        except Exception as e:  # noqa: BLE001
            print(f"  !! IMF {code}: {e}", file=sys.stderr)
            return {}
        values = payload.get("values", {}).get(code, {}).get(ISO3)
        if not isinstance(values, dict) or not values:
            raise RuntimeError(f"IMF {code}: not a DataMapper response")
        cache_file.write_text(json.dumps(payload))
    values = payload["values"][code][ISO3]
    return {int(y): float(v) for y, v in values.items() if v is not None}


def write(rel: str, column: str, series: dict[int, float], dec: int,
          comments: list[str]) -> None:
    if not series:
        print(f"  !! {rel}: nothing fetched", file=sys.stderr)
        return
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [*comments, f"year,{column}"]
    rows = 0
    for y in sorted(series):
        if YEAR_FROM <= y <= YEAR_TO:
            lines.append(f"{y},{series[y]:.{dec}f}")
            rows += 1
    path.write_text("\n".join(lines) + "\n")
    span = [y for y in series if YEAR_FROM <= y <= YEAR_TO]
    print(f"  data/{rel}  {rows} rows  {min(span)}–{max(span)}")


def write_imf(rel: str, series: dict[int, float]) -> None:
    """Observed years in `gross_debt_pct_gdp`, WEO projections apart."""
    if not series:
        print(f"  !! {rel}: nothing fetched", file=sys.stderr)
        return
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# IMF WEO via DataMapper, GGXWDG_NGDP, Switzerland. Units: % of GDP,",
        "# general government gross debt (GFS) = EFV GFS total liabilities, NOT",
        "# Maastricht debt. Calendar years. Years after "
        f"{LAST_FULL_YEAR} are WEO projections",
        "# and sit only in gross_debt_pct_gdp_proj. GDP denominator is the IMF's",
        "# own WEO vintage.",
        "year,gross_debt_pct_gdp,gross_debt_pct_gdp_proj",
    ]
    for y in sorted(series):
        v = f"{series[y]:.1f}"
        lines.append(f"{y},{v}," if y <= LAST_FULL_YEAR else f"{y},,{v}")
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {len(series)} rows  {min(series)}–{max(series)}")


def check(ok: bool, msg: str) -> None:
    if not ok:
        raise RuntimeError(f"spot check failed: {msg}")


def verify(wb: dict[str, dict[int, float]], hdi: dict[int, float],
           debt: dict[int, float]) -> None:
    """Pin the values DISCOVERY.md / SOURCES.yaml recorded on 2026-10-22,
    plus magnitudes cross-checked against a second publisher."""
    gdp, pop = wb["NY.GDP.MKTP.CD"], wb["SP.POP.TOTL"]
    check(abs(gdp.get(2024, 0) - 969.9e9) < 1e9, f"WB GDP 2024 {gdp.get(2024)}")
    check(abs(gdp.get(2025, 0) - 1043.5e9) < 1e9, f"WB GDP 2025 {gdp.get(2025)}")
    check(abs(gdp.get(2006, 0) - 448.4e9) < 1e9, f"WB GDP 2006 {gdp.get(2006)}")
    check(pop.get(2025) == 9_092_436, f"WB population 2025 {pop.get(2025)}")
    # Second source: BFS demographic balance 2025, 1 Jan 9,051,029 and
    # 31 Dec 9,127,125 — the Bank's mid-year figure must sit between.
    check(9_051_029 < pop[2025] < 9_127_125, "WB pop outside BFS 2025 bounds")
    pc = wb["NY.GDP.PCAP.CD"]
    check(abs(pc.get(2024, 0) - 107_702) < 50, f"WB GDP pc 2024 {pc.get(2024)}")
    res = wb["FI.RES.TOTL.CD"]
    # Second source: SNB snbimfra official reserve assets Dec-2025 US$1,075.1bn.
    check(abs(res.get(2025, 0) - 1075.1e9) / 1075.1e9 < 0.01,
          f"WB reserves 2025 {res.get(2025)} vs SNB 1,075.1bn")
    opn = wb["NE.TRD.GNFS.ZS"]
    check(abs(opn.get(2024, 0) - 130.4) < 0.15, f"WB openness 2024 {opn.get(2024)}")
    gini = wb["SI.POV.GINI"]
    check(abs(gini.get(2023, 0) - 33.5) < 0.05, f"WB Gini 2023 {gini.get(2023)}")
    check(2024 not in gini and 2025 not in gini, "WB Gini 2024/25 should be null")
    check(abs(hdi.get(2023, 0) - 0.970) < 0.0005, f"HDI 2023 {hdi.get(2023)}")
    check(abs(hdi.get(2006, 0) - 0.918) < 0.0005, f"HDI 2006 {hdi.get(2006)}")
    check(abs(debt.get(2024, 0) - 40.4) < 0.05, f"IMF debt 2024 {debt.get(2024)}")
    check(abs(debt.get(2006, 0) - 47.9) < 0.05, f"IMF debt 2006 {debt.get(2006)}")
    # Second source: EFV GFS total liabilities 2024 = 40.4% of GDP; the
    # Maastricht 23.7% must NOT match (wrong concept would slip in silently).
    check(abs(debt[2024] - 23.7) > 10, "IMF debt looks like Maastricht")
    check(max(debt) >= 2030, "IMF payload lost its projections")


def main() -> None:
    print("World Bank / UNDP / IMF comparables for Switzerland")
    wb = {}
    for rel, code, column, dec, comments in WANTED:
        wb[code] = wb_series(code)
        write(rel, column, wb[code], dec, comments)
    hdi = hdr_hdi()
    write("international/hdi_from_undp.csv", "hdi", hdi, 3,
          ["# UNDP HDR25 composite indices, complete time series, CHE. Index 0-1.",
           "# One report vintage for every year (no splicing across reports)."])
    debt = imf_series("GGXWDG_NGDP")
    write_imf("international/gg_debt_from_imf.csv", debt)
    verify(wb, hdi, debt)
    print("Done. Spot checks passed. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
