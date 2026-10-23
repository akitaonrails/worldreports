#!/usr/bin/env python3
"""Fetch the Corruption Perceptions Index from Transparency International.

Usage:  python3 countries/usa/fetch/fetch_ti.py

TI publishes the CPI once a year as a workbook. The current one carries a
score time series on the 2012 method (0-100), which is the only span TI
says is comparable year on year. Before 2012 the index was on a 0-10 scale
and built differently; the spine draws those years x10 as a separate
segment and never joins them to the 2012 line. Of the old-method packages,
TI still serves only 2011's at a scriptable address (CPI2011_DataPackage),
so 2011 is the one old-method year here; 2006-2010 stay empty.

The 2025 workbook is saved in strict Office Open XML, which openpyxl does
not read, so its sheets are parsed straight from the XML below. The 2011
package is a legacy .xls and is read with xlrd.

Output (a sidecar; fetch/curate.py accepts it into
international/corruption.csv):
  data/international/corruption_from_ti.csv  year,score,score_pre2012
      score          2012 method, 0-100
      score_pre2012  the old method as TI published it, 0-10
"""
from __future__ import annotations

import csv
import io
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "ti"
DATA = ROOT / "data"
YEAR_FROM, YEAR_TO = 2006, 2026

CURRENT = "https://images.transparencycdn.org/images/CPI2025_Results.xlsx"
OLD_2011 = "https://images.transparencycdn.org/images/CPI2011_DataPackage.zip"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) worldreports-fetch"}
NAMES = ("United States of America", "United States")

# Read off TI's published tables.
SPOT = {2012: 73, 2015: 76, 2024: 65, 2025: 64}
SPOT_2011 = 7.1


def download(url: str, name: str) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if not path.exists():
        r = requests.get(url, headers=HEADERS, timeout=180)
        r.raise_for_status()
        if not r.content.startswith(b"PK"):
            raise ValueError(f"{name}: not a zip ({r.content[:60]!r})")
        path.write_bytes(r.content)
    return path.read_bytes()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def strict_sheet(blob: bytes, wanted: str) -> list[list]:
    """One sheet of a strict-OOXML workbook, as rows of values."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")):
            shared.append("".join(t.text or "" for t in si.iter()
                                  if _local(t.tag) == "t"))
    rels = {r.get("Id"): r.get("Target") for r in
            ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    target = None
    for s in ET.fromstring(z.read("xl/workbook.xml")).iter():
        if _local(s.tag) == "sheet" and s.get("name", "").startswith(wanted):
            rid = next(v for k, v in s.attrib.items() if _local(k) == "id")
            target = rels[rid].lstrip("/")
    if target is None:
        raise ValueError(f"no sheet named {wanted!r}")
    if not target.startswith("xl/"):
        target = "xl/" + target
    rows = []
    for row in ET.fromstring(z.read(target)).iter():
        if _local(row.tag) != "row":
            continue
        cells = {}
        for c in row:
            if _local(c.tag) != "c":
                continue
            col = re.match(r"[A-Z]+", c.get("r")).group(0)
            i = 0
            for ch in col:
                i = i * 26 + ord(ch) - 64
            v = next((x.text for x in c if _local(x.tag) == "v"), None)
            if c.get("t") == "s" and v is not None:
                v = shared[int(v)]
            elif c.get("t") not in ("str", "inlineStr") and v is not None:
                try:
                    v = float(v)
                except ValueError:
                    pass
            cells[i - 1] = v
        if cells:
            rows.append([cells.get(i) for i in range(max(cells) + 1)])
    return rows


def current_series() -> dict[int, float]:
    """{year: score} from the 2012-method time series sheet."""
    rows = strict_sheet(download(CURRENT, "CPI2025_Results.xlsx"),
                        "CPI Timeseries")
    head = next(r for r in rows if r and r[0] == "Country / Territory")
    us = next(r for r in rows if r and r[0] in NAMES)
    out = {}
    for i, label in enumerate(head):
        m = re.fullmatch(r"CPI score (\d{4})", str(label or "").strip(),
                         flags=re.I)
        if m and i < len(us) and isinstance(us[i], float):
            out[int(m.group(1))] = us[i]
    return out


def score_2011() -> float:
    import xlrd
    z = zipfile.ZipFile(io.BytesIO(download(OLD_2011,
                                            "CPI2011_DataPackage.zip")))
    name = next(n for n in z.namelist()
                if n.endswith("CPI2011_Results.xls") and "__MACOSX" not in n)
    book = xlrd.open_workbook(file_contents=z.read(name))
    sh = book.sheet_by_name("Global")
    for i in range(sh.nrows):
        r = sh.row_values(i)
        if str(r[1]).strip() in NAMES:
            # TI printed the score to one decimal; the sheet keeps the
            # unrounded value behind it.
            return round(float(r[2]), 1)
    raise ValueError("2011: no United States row")


def main() -> int:
    print("Fetching the Corruption Perceptions Index...")
    cur = current_series()
    old = score_2011()
    for y, want in SPOT.items():
        if cur.get(y) != want:
            print(f"  !! {y}: {cur.get(y)} against {want}; nothing written")
            return 1
    if old != SPOT_2011:
        print(f"  !! 2011: {old} against {SPOT_2011}; nothing written")
        return 1
    print(f"  2012-method years: {min(cur)}-{max(cur)}; 2011 old method {old}")
    dest = DATA / "international" / "corruption_from_ti.csv"
    with dest.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "score", "score_pre2012"])
        for y in range(YEAR_FROM, YEAR_TO + 1):
            s = f"{cur[y]:.0f}" if y in cur else ""
            o = f"{old:.1f}" if y == 2011 else ""
            w.writerow([y, s, o])
    print(f"  -> {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
