#!/usr/bin/env python3
"""Refresh the cross-country comparables for the United Kingdom.

Usage:  make C=united-kingdom fetch

These are the layer that makes a country legible to a reader who does not
live in it: the same quantity, computed the same way, for everyone. They
are never a substitute for a number the UK publishes about itself. Where
both exist — GDP, population, the Gini — the national series is the
curated one and this is the cross-check, and the plate draws both and
labels the difference rather than choosing.

  World Bank    NY.GDP.MKTP.CD    GDP, current US$
                NY.GDP.PCAP.CD    GDP per person, current US$
                SP.POP.TOTL       population
                FI.RES.TOTL.CD    reserves including gold, current US$
                SI.POV.GINI       Gini, World Bank harmonised
                NE.TRD.GNFS.ZS    trade as a share of GDP
  UNDP          HDI, from the HDR composite-indices file
  IMF           GGXWDG_NGDP       general government gross debt, % GDP
                GGXCNL_NGDP       net lending/borrowing, % GDP

The HDR file is a single vintage covering every year, which is the point:
the HDI is recomputed for the whole back-series at each methodology
change, so a trend assembled from successive reports is partly an
artefact of the reports. One file, one vintage.

The IMF pair is the harmonised fiscal layer the UK no longer gets from
Eurostat (gov_10dd_edpt1 carries no UK rows at all since Brexit): general
government on the national-accounts basis, CALENDAR years, comparable
across the G7 and never spliced with the ONS public-sector-finances
fiscal-year series. The DataMapper API returns forecasts out to 2031 in
the same payload as the history, so the projections go in their own
`*_proj` columns — a forecast year is never written into the observed
column, and the two never share a row.

The World Bank Gini for the UK lags: 2023 and 2024 are null in the
current vintage. The holes stay holes — no interpolation, no carry.

Transparency International's CPI is not here, as for the other countries:
no stable machine endpoint, and the 2012 methodology break means the
pre-2012 scores are not on the same scale. It is curated by hand with
the break in the CSV.
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

WB = ("https://api.worldbank.org/v2/country/GBR/indicator/{code}"
      "?format=json&per_page=200&date=2006:2026")
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
IMF = "https://www.imf.org/external/datamapper/api/v1/{code}/GBR"
ISO3 = "GBR"
# hdr.undp.org answers 403 to the default urllib User-Agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
# www.imf.org's edge answers 403 to any UA starting with "Mozilla/5.0"
# (verified 2026-10-22); a plain descriptive UA gets 200.
IMF_HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}

# The window every plate shares, from country.yaml. The IMF sidecar keeps
# its full 1980+ history (the manifest describes it that way) and splits
# at last_full_year: 2026+ are WEO projections.
YEAR_FROM, YEAR_TO = 2006, 2026
LAST_FULL_YEAR = 2025

WANTED = [
    ("international/gdp_usd_from_wb.csv", "NY.GDP.MKTP.CD", "gdp_usd", 0),
    ("international/gdp_pc_from_wb.csv", "NY.GDP.PCAP.CD", "gdp_per_person_usd", 0),
    ("international/population_from_wb.csv", "SP.POP.TOTL", "population", 0),
    ("international/reserves_from_wb.csv", "FI.RES.TOTL.CD", "reserves_usd", 0),
    ("international/gini_from_wb.csv", "SI.POV.GINI", "gini", 1),
    ("international/openness_from_wb.csv", "NE.TRD.GNFS.ZS", "trade_pct_gdp", 1),
]

IMF_WANTED = [
    ("GGXWDG_NGDP", "gross_debt_pct_gdp"),
    ("GGXCNL_NGDP", "net_lending_pct_gdp"),
]


def wb_series(code: str) -> dict[int, float]:
    """One World Bank indicator for the UK as {year: value}.

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
    """The UK's HDI by year, out of the HDR composite-indices file.

    One row per country and one COLUMN per year, with sibling columns for
    the rank and the sex-disaggregated values — so the key has to match
    `hdi_YYYY` exactly. Matching on the prefix pulls in `hdi_rank_2023`
    and silently writes a rank where a value belongs.
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "hdr25_series.csv"
    if not cache_file.exists():
        try:
            req = urllib.request.Request(HDR, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as r:
                cache_file.write_bytes(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"  HDR fetch failed: {e}", file=sys.stderr)
            return {}
    out: dict[int, float] = {}
    for row in csv.DictReader(io.StringIO(
            cache_file.read_text(errors="replace"))):
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
    """One IMF WEO indicator for the UK as {year: value}, forecasts included.

    The DataMapper API answers with {"values": {<code>: {"GBR":
    {"1980": ...}}}. A bad indicator or country answers with an empty or
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


def write(rel: str, column: str, series: dict[int, float], dec: int) -> None:
    if not series:
        print(f"  !! {rel}: nothing fetched", file=sys.stderr)
        return
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"year,{column}"]
    for y in sorted(series):
        if YEAR_FROM <= y <= YEAR_TO:
            lines.append(f"{y},{series[y]:.{dec}f}")
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {len(lines) - 1} rows")


def write_imf(rel: str, wanted: list[tuple[str, str]]) -> None:
    """The fiscal sidecar: observed years in one column, projections apart.

    Every year carries exactly one of `<col>` / `<col>_proj`; the other is
    left empty. Years up to last_full_year are outturn; anything later is
    a WEO forecast and goes only into the `_proj` column, so a projection
    can never be drawn as observed by accident.
    """
    series = {code: imf_series(code) for code, _ in wanted}
    if not all(series.values()):
        print(f"  !! {rel}: an IMF indicator came back empty",
              file=sys.stderr)
        return
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["year"]
    for _, column in wanted:
        header += [column, f"{column}_proj"]
    lines = [",".join(header)]
    years = sorted(set().union(*series.values()))
    for y in years:
        row = [str(y)]
        for code, _ in wanted:
            value = series[code].get(y)
            if value is None:
                row += ["", ""]
            elif y <= LAST_FULL_YEAR:
                row += [f"{value:.1f}", ""]
            else:
                row += ["", f"{value:.1f}"]
        lines.append(",".join(row))
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {len(lines) - 1} rows")


def verify(gdp: dict[int, float], population: dict[int, float],
           hdi: dict[int, float], gini: dict[int, float]) -> None:
    """Pin the numbers the discovery pass verified live, so a silent
    revision, a unit change or a truncated payload fails here instead of
    landing in a sidecar."""
    assert abs(gdp[2024] - 3_695.5e9) < 2e9, f"WB GDP 2024: {gdp.get(2024)}"
    assert abs(population[2024] - 69_281_000) < 50_000, \
        f"WB population 2024: {population.get(2024)}"
    assert abs(hdi[2023] - 0.946) < 0.001, f"UNDP hdi_2023: {hdi.get(2023)}"
    # The Bank's UK Gini lags: these years are null in the current
    # vintage. The holes stay holes — assert they were not filled in.
    assert 2023 not in gini and 2024 not in gini, \
        f"WB Gini 2023/2024 should be null: {sorted(gini)[-3:]}"


def main() -> None:
    print("World Bank / UNDP / IMF comparables for the United Kingdom")
    fetched = {}
    for rel, code, column, dec in WANTED:
        series = wb_series(code)
        write(rel, column, series, dec)
        fetched[code] = series
    hdi = hdr_hdi()
    write("international/hdi_from_undp.csv", "hdi", hdi, 3)
    write_imf("international/fiscal_from_imf.csv", IMF_WANTED)
    verify(fetched["NY.GDP.MKTP.CD"], fetched["SP.POP.TOTL"], hdi,
           fetched["SI.POV.GINI"])
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
