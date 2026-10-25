#!/usr/bin/env python3
"""Chile's Corruption Perceptions Index score, from Transparency International.

Usage:  python3 -I countries/chile/fetch/fetch_transparency.py

Writes data/world/cpi_from_ti.csv (year, score) — a review sidecar.

This is NOT an official statistic and SOURCES.yaml marks it
`official: false`: TI is an association that aggregates expert and
business surveys, not a statistical office. It is here because it is the
only publisher of the index the world chapter compares on.

Two things the reader has to be told, and the plate says both:
  * the index was recomputed onto a 0-100 scale in 2012, so the 2012-2025
    run is one method and anything earlier is a different one;
  * the score is not comparable year to year in the naive sense — TI
    changes its source mix — which is why the series is drawn as it is
    published and not as a trend.

The workbook is served as xlsx and openpyxl refuses it (invalid defined
names), so the sheet is read straight out of the OOXML. That is also why
the check is on the sheet layout rather than on `load_workbook`.
"""
from __future__ import annotations

import csv
import re
import sys
import time
import urllib.request
import zipfile
import io
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "transparency"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "*/*"}

URL = "https://images.transparencycdn.org/images/CPI2025_Results.xlsx"
NS = "{http://purl.oclc.org/ooxml/spreadsheetml/main}"
RELNS = "{http://purl.oclc.org/ooxml/officeDocument/relationships}"
FIRST_YEAR, LAST_YEAR = 2005, 2025


class FetchError(RuntimeError):
    pass


def get(url: str, cache_name: str, check) -> bytes:
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
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
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


def sheet_rows(raw: bytes) -> list[dict[str, str]]:
    """Every row of the 'CPI Historical' sheet, as {column letter: text}."""
    z = zipfile.ZipFile(io.BytesIO(raw))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = {r.get("Id"): r.get("Target") for r in rels}
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        sst = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in sst.iter(NS + "si"):
            shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
    for el in wb.iter(NS + "sheet"):
        if el.get("name", "").strip().lower() != "cpi historical":
            continue
        root = ET.fromstring(z.read("xl/" + target[el.get(RELNS + "id")]
                                    .lstrip("/")))
        out = []
        for row in root.iter(NS + "row"):
            cells = {}
            for c in row.iter(NS + "c"):
                ref = c.get("r") or ""
                col = re.match(r"[A-Z]+", ref)
                if not col:
                    continue
                v = c.find(NS + "v")
                inline = c.find(NS + "is")
                if c.get("t") == "s" and v is not None:
                    cells[col.group()] = shared[int(v.text)]
                elif inline is not None:
                    cells[col.group()] = "".join(
                        t.text or "" for t in inline.iter(NS + "t"))
                elif v is not None:
                    cells[col.group()] = v.text
            out.append(cells)
        return out
    raise FetchError("the workbook has no 'CPI Historical' sheet")


def main() -> int:
    def check(raw: bytes) -> None:
        if not raw.startswith(b"PK"):
            raise ValueError("not an xlsx (no zip signature)")
        rows = sheet_rows(raw)
        head = [r for r in rows if r.get("A") == "Country / Territory"]
        if not head:
            raise ValueError("no header row in the historical sheet")
        if not any(r.get("B") == "CHL" for r in rows):
            raise ValueError("Chile is not in the historical sheet")

    rows = sheet_rows(get(URL, "CPI2025_Results.xlsx", check))
    series: dict[int, float] = {}
    for row in rows:
        if row.get("B") != "CHL":
            continue
        year, score = row.get("C"), row.get("E")
        if not (year and score):
            continue
        y = int(float(year))
        if FIRST_YEAR <= y <= LAST_YEAR:
            if y in series:
                raise FetchError(f"CPI: two rows for {y}")
            series[y] = float(score)

    if len(series) < 10:
        raise FetchError(f"CPI: only {len(series)} years for Chile")
    if series[max(series)] <= 0:
        raise FetchError("CPI: latest score is not positive")
    # TI's 2012 method change: before it the index ran on a 0-10 scale.
    # Both eras are published in this sheet, so the sidecar records which
    # one each row belongs to rather than mixing them silently.
    out = DATA / "world" / "cpi_from_ti.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "score", "method"])
        for year in sorted(series):
            w.writerow([year, f"{series[year]:.0f}",
                        "cpi-2012" if year >= 2012 else "cpi-1995"])
    print(f"  CPI Chile: {len(series)} years {min(series)}-{max(series)}, "
          f"latest {series[max(series)]:.0f}")
    print("  -> world/cpi_from_ti.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
