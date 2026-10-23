#!/usr/bin/env python3
"""Refresh the cross-country comparables for Italy into sidecar CSVs.

Usage:  python3 -I countries/italy/fetch/fetch_comparables.py

These are the layer that makes a country legible to a reader who does not
live in it: the same quantity, computed the same way, for everyone. They
are never a substitute for a number Italy publishes about itself. Where
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

The Bank's harmonised Gini and Eurostat's EU-SILC Gini (social/
gini_from_estat.csv) are two readings of ONE survey on different income
definitions — 2023: WB 34.3 vs SILC 31.5. Both are drawn, both labelled;
this layer keeps the WB cut and the CSV comment records the gap.

Transparency International's CPI is read from the pinned CPI 2025 workbook.
Only 2012 onward is retained because that is the comparable methodology.
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

WB = ("https://api.worldbank.org/v2/country/ITA/indicator/{code}"
      "?format=json&per_page=200&date=2005:2026")
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
ISO3 = "ITA"
CPI_EDITION = 2025
CPI = "https://images.transparencycdn.org/images/CPI2025_Results.xlsx"
# hdr.undp.org answers 403 to the default urllib User-Agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

WANTED = [
    ("international/gdp_usd_from_wb.csv", "NY.GDP.MKTP.CD", "gdp_usd", 0),
    ("international/gdp_pc_from_wb.csv", "NY.GDP.PCAP.CD", "gdp_per_person_usd", 0),
    ("international/population_from_wb.csv", "SP.POP.TOTL", "population", 0),
    ("international/reserves_from_wb.csv", "FI.RES.TOTL.CD", "reserves_usd", 0),
    ("social/gini_from_wb.csv", "SI.POV.GINI", "gini", 1),
    ("international/openness_from_wb.csv", "NE.TRD.GNFS.ZS", "trade_pct_gdp", 1),
]

GINI_COMMENT = ("# World Bank harmonised Gini, EU-SILC-derived but on the "
                "Bank's own income definition: 2023 reads 34.3 here against "
                "31.5 in Eurostat's SILC cut (social/gini_from_estat.csv). "
                "Two readings of one survey, not two measurements.")


def wb_series(code: str) -> dict[int, float]:
    """One World Bank indicator for Italy as {year: value}.

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
    """Italy's HDI by year, out of the HDR composite-indices file.

    One row per country and one COLUMN per year, with sibling columns for
    the rank and the sex-disaggregated values — so the key has to match
    `hdi_YYYY` exactly. Matching on the prefix pulls in `hdi_rank_2023`
    and silently writes a rank where a value belongs.

    The file is LATIN-1, not UTF-8 (a 0xf4 byte in a country name trips
    strict decoding) — decode explicitly rather than errors="replace",
    which would corrupt names it never prints.
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


def ti_cpi() -> dict[int, float]:
    """Italy's comparable CPI scores from TI's pinned 2025 workbook."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"cpi{CPI_EDITION}.xlsx"
    if not cache_file.exists():
        req = urllib.request.Request(CPI, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=120) as response:
            raw = response.read()
        if not raw.startswith(b"PK"):
            raise RuntimeError("CPI workbook is not OOXML")
        cache_file.write_bytes(raw)
    with zipfile.ZipFile(cache_file) as archive:
        strings = ["".join(re.findall(r"<t[^>]*>(.*?)</t>", item, re.S))
                   for item in re.findall(r"<si>(.*?)</si>",
                                          archive.read("xl/sharedStrings.xml")
                                          .decode(), re.S)]
        book = archive.read("xl/workbook.xml").decode()
        rels = archive.read("xl/_rels/workbook.xml.rels").decode()
        rid = re.search(r'<sheet [^>]*name="CPI Timeseries[^"]*"[^>]*'
                        r'r:id="([^"]+)"', book).group(1)
        target = re.search(rf'Id="{rid}"[^>]*Target="([^"]+)"', rels) or \
            re.search(rf'Target="([^"]+)"[^>]*Id="{rid}"', rels)
        sheet = archive.read(
            "xl/" + target.group(1).lstrip("/").removeprefix("xl/")).decode()

    def cells(row: str) -> dict[str, str]:
        out = {}
        for match in re.finditer(
                r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', row, re.S):
            ref, attrs, body = match.groups()
            value_match = re.search(r"<v>(.*?)</v>", body or "")
            value = value_match.group(1) if value_match else ""
            if 't="s"' in attrs and value:
                value = strings[int(value)]
            out[ref] = value
        return out

    rows = [cells(row) for row in re.findall(r"<row[^>]*>(.*?)</row>",
                                              sheet, re.S)]
    header = next(row for row in rows if "Country / Territory" in row.values())
    italy = next(row for row in rows if row.get("A") == "Italy")
    out = {}
    for ref, label in header.items():
        match = re.fullmatch(r"cpi score (\d{4})", label.strip().lower())
        if match and italy.get(ref):
            out[int(match.group(1))] = float(italy[ref])
    if (out.get(2012), out.get(2024), out.get(2025)) != (42, 54, 53):
        raise RuntimeError(f"CPI spot values do not match: {out}")
    if sorted(out) != list(range(2012, CPI_EDITION + 1)):
        raise RuntimeError(f"CPI years incomplete: {sorted(out)}")
    return out


def write(rel: str, column: str, series: dict[int, float], dec: int,
          comment: str | None = None) -> None:
    if not series:
        print(f"  !! {rel}: nothing fetched", file=sys.stderr)
        return
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ([comment] if comment else []) + [f"year,{column}"]
    n = 0
    for y in sorted(series):
        if 2005 <= y <= 2026:
            lines.append(f"{y},{series[y]:.{dec}f}")
            n += 1
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {n} rows")


def spot_checks(gdp_usd: dict[int, float], gini: dict[int, float],
                hdi: dict[int, float]) -> None:
    """Bracket assertions on the values verified in discovery — the
    bracket, not the decimal, because the WB revises its back-series."""
    g24 = gdp_usd.get(2024, 0)
    assert 2.2e12 <= g24 <= 2.5e12, \
        f"WB GDP 2024 {g24:,.0f} outside the US$2,383bn bracket"
    print(f"  ok  WB GDP 2024 = US${g24 / 1e9:,.0f}bn "
          f"(~US$2,383bn, consistent with €2,211bn at 2024 FX)")
    g23 = gini.get(2023)
    assert g23 is not None and abs(g23 - 34.3) < 0.15, \
        f"WB Gini 2023 = {g23}, expected 34.3"
    print(f"  ok  WB Gini 2023 = {g23} (SILC cut reads 31.5 — gap in CSV)")
    h23 = hdi.get(2023)
    assert h23 is not None and abs(h23 - 0.915) < 0.002, \
        f"UNDP HDI 2023 = {h23}, expected 0.915"
    print(f"  ok  UNDP HDI 2023 = {h23}")


def main() -> None:
    print("World Bank / UNDP comparables for Italy")
    series: dict[str, dict[int, float]] = {}
    for rel, code, column, dec in WANTED:
        series[code] = wb_series(code)
        comment = GINI_COMMENT if code == "SI.POV.GINI" else None
        write(rel, column, series[code], dec, comment)
    hdi = hdr_hdi()
    write("international/hdi_from_undp.csv", "hdi", hdi, 3)
    write("international/cpi_from_ti.csv", "score", ti_cpi(), 0)
    spot_checks(series["NY.GDP.MKTP.CD"], series["SI.POV.GINI"], hdi)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
