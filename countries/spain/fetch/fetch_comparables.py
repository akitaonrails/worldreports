#!/usr/bin/env python3
"""Refresh the cross-country comparables for Spain into sidecar CSVs.

Usage:  python3 -I countries/spain/fetch/fetch_comparables.py

These are the layer that makes a country legible to a reader who does not
live in it: the same quantity, computed the same way, for everyone. They
are never a substitute for a number Spain publishes about itself. Where
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

The HDR file is a single vintage covering every year, which is the point:
the HDI is recomputed for the whole back-series at each methodology
change, so a trend assembled from successive reports is partly an
artefact of the reports. One file, one vintage.

Spain's reserves read small and dormant next to a non-euro country: the
ECB holds the monetary union's real buffer. That is a fact about the
institutional setup, not about Spain's solvency — the plate says so.

  Transparency International  Corruption Perceptions Index, 2012 onward,
                from the CPI 2025 results spreadsheet ("CPI Timeseries
                2012 - 2025" sheet)

TI publishes each edition as a spreadsheet at a URL whose spelling
changes from year to year (CPI2024-Results-and-trends.xlsx, then
CPI2025_Results.xlsx), so the edition is pinned here and bumped by hand.
The file is strict OOXML, which openpyxl cannot read, so it is read as
the zip of XML it is: shared strings resolved by index, cells matched by
their column reference against the header row — a row omits its empty
cells, so position means nothing — and the score header matched without
regard to case, because the 2012 and 2013 columns say "CPI Score" and
every later one "CPI score". Scores before 2012 were on a 0-10 scale
computed another way; TI says only 2012 onward are comparable, and they
are not fetched.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

WB = ("https://api.worldbank.org/v2/country/ESP/indicator/{code}"
      "?format=json&per_page=200&date=2005:2026")
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
ISO3 = "ESP"
# The newest CPI edition and its spreadsheet. Bump both together.
CPI_EDITION = 2025
CPI = "https://images.transparencycdn.org/images/CPI2025_Results.xlsx"
# hdr.undp.org answers 403 to the default urllib User-Agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

WANTED = [
    ("international/gdp_usd_from_wb.csv", "NY.GDP.MKTP.CD", "gdp_usd", 0),
    ("international/gdp_pc_from_wb.csv", "NY.GDP.PCAP.CD", "gdp_per_person_usd", 0),
    ("international/population_from_wb.csv", "SP.POP.TOTL", "population", 0),
    ("international/reserves_from_wb.csv", "FI.RES.TOTL.CD", "reserves_usd", 0),
    ("international/gini_from_wb.csv", "SI.POV.GINI", "gini", 1),
    ("international/openness_from_wb.csv", "NE.TRD.GNFS.ZS", "trade_pct_gdp", 1),
]


def wb_series(code: str) -> dict[int, float]:
    """One World Bank indicator for Spain as {year: value}.

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
    """Spain's HDI by year, out of the HDR composite-indices file.

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


def ti_cpi() -> dict[int, float]:
    """Spain's CPI score by year, 2012 to the pinned edition."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"cpi{CPI_EDITION}.xlsx"
    if not cache_file.exists():
        req = urllib.request.Request(CPI, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
        if not raw.startswith(b"PK"):
            raise RuntimeError("CPI spreadsheet: not a zip (an error page?)")
        cache_file.write_bytes(raw)
    with zipfile.ZipFile(cache_file) as z:
        strings = ["".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S))
                   for si in re.findall(r"<si>(.*?)</si>",
                                        z.read("xl/sharedStrings.xml")
                                        .decode(), re.S)]
        book = z.read("xl/workbook.xml").decode()
        rels = z.read("xl/_rels/workbook.xml.rels").decode()
        rid = re.search(r'<sheet [^>]*name="CPI Timeseries[^"]*"[^>]*'
                        r'r:id="([^"]+)"', book).group(1)
        target = re.search(rf'Id="{rid}"[^>]*Target="([^"]+)"', rels) or \
            re.search(rf'Target="([^"]+)"[^>]*Id="{rid}"', rels)
        sheet = z.read("xl/" + target.group(1).lstrip("/").removeprefix("xl/")
                       ).decode()

    def cells(row: str) -> dict[str, str]:
        out = {}
        for m in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)',
                             row, re.S):
            ref, attrs, body = m.groups()
            v = re.search(r"<v>(.*?)</v>", body or "")
            value = v.group(1) if v else ""
            if 't="s"' in attrs and value:
                value = strings[int(value)]
            out[ref] = value
        return out

    rows = [cells(r) for r in re.findall(r"<row[^>]*>(.*?)</row>", sheet,
                                          re.S)]
    header = next(r for r in rows if "Country / Territory" in r.values())
    spain = next(r for r in rows if r.get("A") == "Spain")
    out = {}
    for ref, label in header.items():
        m = re.fullmatch(r"cpi score (\d{4})", label.strip().lower())
        if m and spain.get(ref):
            out[int(m.group(1))] = float(spain[ref])
    # Spot values from TI's country page: 65 in 2012, 56 in 2024 (the
    # CPI 2024 edition says the same), 55 in 2025.
    if (out.get(2012), out.get(2024), out.get(2025)) != (65, 56, 55):
        raise RuntimeError(f"CPI spot values do not match: {out}")
    if sorted(out) != list(range(2012, CPI_EDITION + 1)):
        raise RuntimeError(f"CPI years {sorted(out)}: a column was missed")
    return out


def write(rel: str, column: str, series: dict[int, float], dec: int) -> None:
    if not series:
        print(f"  !! {rel}: nothing fetched", file=sys.stderr)
        return
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"year,{column}"]
    for y in sorted(series):
        if 2005 <= y <= 2026:
            lines.append(f"{y},{series[y]:.{dec}f}")
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {len(lines) - 1} rows")


def main() -> None:
    print("World Bank / UNDP comparables for Spain")
    for rel, code, column, dec in WANTED:
        write(rel, column, wb_series(code), dec)
    write("international/hdi_from_undp.csv", "hdi", hdr_hdi(), 3)
    write("international/cpi_from_ti.csv", "score", ti_cpi(), 0)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
