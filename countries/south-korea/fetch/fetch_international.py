#!/usr/bin/env python3
"""Refresh the international comparison series — World Bank, UNDP and TI.

These two publishers are the reason the atlas can say anything about how
Korea compares: a national statistics office harmonises nothing, so a Gini
coefficient computed by Statistics Korea and one computed by the World Bank
are different numbers measuring the same idea. Both are kept, in separate
columns, and never spliced.

Curated files are never overwritten here. Everything lands in a sidecar for
diffing, except the two series that have no national counterpart at all —
the HDI and R&D intensity — which this script owns.

  data/social/hdi.csv                — UNDP HDR composite index, Korea
  data/social/gini_from_wb.csv       — SI.POV.GINI (harmonised, 0-100)
  data/social/poverty_from_wb.csv    — SI.POV.UMIC / SI.POV.DDAY, for scale
  data/fiscal/rnd.csv                — GB.XPD.RSDV.GD.ZS, R&D as % of GDP
  data/intl/openness.csv             — NE.TRD.GNFS.ZS, trade as % of GDP
  data/intl/cpi_from_ti.csv          — Transparency International CPI, sidecar

Trade openness is taken from the national accounts (goods *and* services,
NE.TRD.GNFS.ZS) rather than computed from data/trade/trade.csv, which is a
customs series covering goods only. The two differ by several points of GDP
and are not interchangeable.

The Corruption Perceptions Index lands in a sidecar because the published
spreadsheet always stops at the edition it belongs to: the curated
data/intl/cpi.csv carries the current year, taken from the country table TI
publishes alongside the release. CPI scores before 2012 were on a 0-10 scale
computed a different way and are deliberately absent.

Korea's own poverty measure is relative (below half the median), not an
absolute dollar line, so the World Bank's absolute series is fetched only to
show how far off the bottom of the scale Korea sits — it is not what plate 06
draws. See data/SOURCES.yaml.
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
SOCIAL = ROOT / "data" / "social"
FISCAL = ROOT / "data" / "fiscal"
INTL = ROOT / "data" / "intl"
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)

WB = ("https://api.worldbank.org/v2/country/KOR/indicator/{code}"
      "?format=json&per_page=200&date=2000:2026")
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
# The newest edition whose spreadsheet is published. Bump both together.
CPI_EDITION = 2024
CPI = ("https://images.transparencycdn.org/images/"
       f"CPI{CPI_EDITION}-Results-and-trends.xlsx")

YEAR_FROM, YEAR_TO = 2006, 2026


# hdr.undp.org serves 403 to a request with no browser-shaped user agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) korea-reports/1.0"}


def _get(url: str, binary: bool = False):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            return raw if binary else json.loads(raw.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"    retry {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return None


def wb_series(code: str) -> dict[int, float]:
    cache_file = CACHE / f"wb_{code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        payload = _get(WB.format(code=code))
        if not payload:
            return {}
        cache_file.write_text(json.dumps(payload))
    out = {}
    if len(payload) > 1 and isinstance(payload[1], list):
        for row in payload[1]:
            if row["value"] is not None:
                out[int(row["date"])] = float(row["value"])
    return out


def hdr_korea() -> dict[int, float]:
    """Korea's HDI, from the one complete-time-series file.

    The whole world's composite indices are in a single ~30k-row CSV. Only
    the exact `hdi_YYYY` columns are read: the file also carries
    `hdi_rank_YYYY`, `hdi_f_YYYY` and `hdi_m_YYYY`, and a prefix match would
    silently mix a rank into the index.
    """
    cache_file = CACHE / "hdr25_series.csv"
    if not cache_file.exists():
        raw = _get(HDR, binary=True)
        if not raw:
            print("  ! HDR fetch failed", file=sys.stderr)
            return {}
        cache_file.write_bytes(raw)
    reader = csv.DictReader(io.StringIO(cache_file.read_text(errors="replace")))
    for row in reader:
        if (row.get("iso3") or row.get("ISO3")) != "KOR":
            continue
        out = {}
        for key, value in row.items():
            if not key or not key.lower().startswith("hdi_"):
                continue
            year = key.split("_")[-1]
            if (year.isdigit() and key.lower() == f"hdi_{year}"
                    and value not in ("", "..")):
                out[int(year)] = float(value)
        return out
    return {}


def cpi_korea() -> dict[int, tuple[str, str]]:
    """{year: (score, rank)} for Korea, from TI's own results spreadsheet.

    Read with the standard library rather than a spreadsheet package: the
    sheet is a flat table, and an xlsx is a zip of XML. Three details make it
    work. Cells with `t="s"` hold an index into sharedStrings rather than a
    value; a row omits empty cells entirely, so columns are matched by their
    `r` reference against the header row and never by position; and the
    header is inconsistent in its own capitalisation — the 2012 and 2013
    columns read "CPI Score", every later one "CPI score" — so the prefix is
    matched case-insensitively. Matching it exactly drops the two oldest
    years without any error at all.
    """
    cache_file = CACHE / f"cpi{CPI_EDITION}.xlsx"
    if not cache_file.exists():
        raw = _get(CPI, binary=True)
        if not raw:
            print("  ! CPI fetch failed", file=sys.stderr)
            return {}
        cache_file.write_bytes(raw)

    with zipfile.ZipFile(cache_file) as z:
        strings = [
            "".join(re.findall(r"<t[^>]*>(.*?)</t>", chunk, re.S))
            for chunk in re.findall(
                r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)
        ]
        # sheet2 is the "CPI Timeseries" tab; sheet1 is the current year only.
        sheet = z.read("xl/worksheets/sheet2.xml").decode()

    def cells(row: str) -> dict[str, str]:
        out = {}
        for m in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*)>(.*?)</c>', row, re.S):
            ref, attrs, body = m.groups()
            v = re.search(r"<v>(.*?)</v>", body)
            value = v.group(1) if v else ""
            if 't="s"' in attrs and value:
                value = strings[int(value)]
            out[ref] = value
        return out

    rows = [cells(r) for r in re.findall(r"<row[^>]*>(.*?)</row>", sheet, re.S)]
    header = next((r for r in rows if "Country / Territory" in r.values()), None)
    korea = next((r for r in rows if r.get("A") == "Korea, South"), None)
    if header is None or korea is None:
        print("  ! CPI sheet layout changed", file=sys.stderr)
        return {}

    out: dict[int, tuple[str, str]] = {}
    for ref, label in header.items():
        for prefix, slot in (("cpi score ", 0), ("rank ", 1)):
            if not label.lower().startswith(prefix):
                continue
            year = label[len(prefix):].strip()
            if not year.isdigit():
                continue
            score, rank = out.get(int(year), ("", ""))
            value = korea.get(ref, "")
            out[int(year)] = (value, rank) if slot == 0 else (score, value)
    return {y: v for y, v in out.items() if any(v)}


def write(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *rows]) + "\n")
    print(f"  -> {path.relative_to(ROOT)}")


def main() -> None:
    hdi = hdr_korea()
    if hdi:
        write(SOCIAL / "hdi.csv", "year,value",
              [f"{y},{hdi[y]:.3f}" for y in sorted(hdi)
               if YEAR_FROM <= y <= YEAR_TO])

    gini = wb_series("SI.POV.GINI")
    if gini:
        write(SOCIAL / "gini_from_wb.csv", "year,wb",
              [f"{y},{gini[y]:.1f}" for y in sorted(gini)])

    umic = wb_series("SI.POV.UMIC")
    dday = wb_series("SI.POV.DDAY")
    if umic or dday:
        years = sorted(set(umic) | set(dday))
        write(SOCIAL / "poverty_from_wb.csv", "year,poverty_pct,extreme_pct",
              [f"{y},{umic.get(y, '')},{dday.get(y, '')}" for y in years])

    rnd = wb_series("GB.XPD.RSDV.GD.ZS")
    if rnd:
        write(FISCAL / "rnd.csv", "year,value",
              [f"{y},{rnd[y]:.2f}" for y in sorted(rnd)
               if YEAR_FROM <= y <= YEAR_TO])

    openness = wb_series("NE.TRD.GNFS.ZS")
    if openness:
        write(INTL / "openness.csv", "year,value",
              [f"{y},{openness[y]:.1f}" for y in sorted(openness)
               if YEAR_FROM <= y <= YEAR_TO])

    cpi = cpi_korea()
    if cpi:
        write(INTL / "cpi_from_ti.csv", "year,score,rank",
              [f"{y},{cpi[y][0]},{cpi[y][1]}" for y in sorted(cpi)])


if __name__ == "__main__":
    main()
