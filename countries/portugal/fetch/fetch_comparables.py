#!/usr/bin/env python3
"""Refresh the cross-country comparables for Portugal into sidecar CSVs.

Usage:  make C=portugal fetch

These are the layer that makes a country legible to a reader who does not
live in it: the same quantity, computed the same way, for everyone. They
are never a substitute for a number Portugal publishes about itself. Where
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

VINTAGE TRAP, flagged at the top of SOURCES.yaml: on 2026-06-22 the INE
revised population estimates 2021–2024 upward (~1.6mn foreign residents
newly counted; end-2024 = 11,387,222). The World Bank series here are the
PRE-revision vintage (2024 = 10,694,681) and the per-capita GDP sits on
that lower denominator. The two vintages are never mixed: the population
series of record is the INE's, and these files carry the warning in their
comment lines.

The HDR file is a single vintage covering every year, which is the point:
the HDI is recomputed for the whole back-series at each methodology
change, so a trend assembled from successive reports is partly an
artefact of the reports. One file, one vintage. The file is Latin-1, not
UTF-8 — it is decoded explicitly below (verified on the PRT row).

Transparency International's CPI is not here. It is published as a PDF
and a spreadsheet per year with no stable machine endpoint, and its
methodology break in 2012 means the pre-2012 scores are not on the same
scale — so it is curated by hand with the break in the CSV.
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

WB = ("https://api.worldbank.org/v2/country/PRT/indicator/{code}"
      "?format=json&per_page=200&date=2006:2026")
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
ISO3 = "PRT"
# hdr.undp.org answers 403 to the default urllib User-Agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

POP_VINTAGE = (
    "PRE-REVISION VINTAGE: the World Bank population series predates the "
    "INE's 2026-06-22 revision (revised end-2024 = 11,387,222, counting "
    "~1.6mn foreign residents; this file has 2024 = 10,694,681). The two "
    "vintages are never mixed — the population series of record is the "
    "INE's, and this file is the cross-country cross-check only."
)

WANTED = [
    ("international/gdp_usd_from_wb.csv", "NY.GDP.MKTP.CD", "gdp_usd", 0, [
        "GDP in current US$ — the comparables layer, never spliced into "
        "the national accounts (the euro's rate moves this as much as "
        "Portugal does).",
    ]),
    ("international/gdp_pc_from_wb.csv", "NY.GDP.PCAP.CD", "gdp_per_person_usd", 0, [
        "Current US$ per person. " + POP_VINTAGE,
        "The per-capita levels sit on the old, lower population — a "
        "magnitude check against the national accounts, not a splice "
        "into them.",
    ]),
    ("international/population_from_wb.csv", "SP.POP.TOTL", "population", 0, [
        POP_VINTAGE,
    ]),
    ("international/reserves_from_wb.csv", "FI.RES.TOTL.CD", "reserves_usd", 0, [
        "Total reserves including gold, current US$. A eurozone member's "
        "reserves are small and semi-dormant — the ECB holds the union's "
        "real buffer.",
    ]),
    ("international/gini_from_wb.csv", "SI.POV.GINI", "gini", 1, [
        "The Bank's harmonised Gini for Portugal is EU-SILC-derived — "
        "the same survey as the INE/Eurostat series through a different "
        "income definition. Three cuts of one survey, not three "
        "measurements.",
    ]),
    ("international/openness_from_wb.csv", "NE.TRD.GNFS.ZS", "trade_pct_gdp", 1, [
        "Exports plus imports of goods and services as a share of GDP — "
        "national-accounts basis, not the customs-value goods of the INE "
        "trade file.",
    ]),
]


def wb_series(code: str) -> dict[int, float]:
    """One World Bank indicator for Portugal as {year: value}.

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
    """Portugal's HDI by year, out of the HDR composite-indices file.

    One row per country and one COLUMN per year, with sibling columns for
    the rank and the sex-disaggregated values — so the key has to match
    `hdi_YYYY` exactly. Matching on the prefix pulls in `hdi_rank_2023`
    and silently writes a rank where a value belongs.

    The file is Latin-1, not UTF-8 (a UTF-8 read corrupts the accented
    country names; verified on the ITA row), so it is decoded explicitly.
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
    text = cache_file.read_bytes().decode("latin-1")
    for row in csv.DictReader(io.StringIO(text)):
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


def write(rel: str, column: str, series: dict[int, float], dec: int,
          comments: list[str]) -> None:
    if not series:
        print(f"  !! {rel}: nothing fetched", file=sys.stderr)
        return
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in comments]
    lines.append(f"year,{column}")
    for y in sorted(series):
        if 2006 <= y <= 2026:
            lines.append(f"{y},{series[y]:.{dec}f}")
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {len(lines) - 1 - len(comments)} rows")


def main() -> None:
    print("World Bank / UNDP comparables for Portugal")
    for rel, code, column, dec, comments in WANTED:
        write(rel, column, wb_series(code), dec, comments)
    write("international/hdi_from_undp.csv", "hdi", hdr_hdi(), 3, [
        "One file, one vintage, every year: the HDR recomputes the whole "
        "back-series at each methodology change, so a trend assembled "
        "from successive reports is partly an artefact of the reports.",
    ])
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
