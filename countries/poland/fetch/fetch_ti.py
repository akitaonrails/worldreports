#!/usr/bin/env python3
"""Refresh Poland's Corruption Perceptions Index from Transparency International.

Usage:  make C=poland fetch   (or: python3 -I fetch/fetch_ti.py)

Transparency International is not a statistical office: the CPI is an
aggregate of expert and business surveys, and `SOURCES.yaml` marks it
`official: false`, which is what the page reads. It is in the atlas
because the world chapter asks how a country is perceived, and because
the spine names it.

The CPI changed method in 2012 and is NOT comparable across that seam:
before 2012 the score ran 0-10, after it runs 0-100. This fetcher stages
only the 2012+ scores from the current edition's historical sheet; the
pre-2012 series is a different index and is not spliced into it.

The current workbook is strict OOXML (the purl.oclc.org namespace), which
openpyxl refuses to open, so the sheets are read straight from the zip.

  https://images.transparencycdn.org/images/CPI2024-Results-and-trends.xlsx
  sheet "CPI Historical": Country, ISO3, Year, Region, CPI score, Rank

The 2025 edition's workbook answers S3 AccessDenied and the CPI pages
answer a Cloudflare challenge to this network; the 2024 edition's file is
the newest that returns an XLSX here (DISCOVERY.md).

Output: world/cpi_from_ti.csv (review sidecar only).
"""
from __future__ import annotations

import io
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, FetchError, assert_close, get, write_csv  # noqa: E402

URLS = [
    "https://images.transparencycdn.org/images/CPI2024-Results-and-trends.xlsx",
]
ISO3 = "POL"
M = "{http://purl.oclc.org/ooxml/spreadsheetml/main}"
Y0, Y1 = 2006, 2026


def read_strict_xlsx(body: bytes, sheet: str) -> list[list[str]]:
    """Rows of one sheet from a strict-OOXML workbook, as text."""
    z = zipfile.ZipFile(io.BytesIO(body))
    shared = ET.fromstring(z.read("xl/sharedStrings.xml"))
    strings = ["".join((t.text or "") for t in si.iter(M + "t"))
               for si in shared.findall(M + "si")]
    book = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid = None
    for s in book.iter(M + "sheet"):
        if s.get("name") == sheet:
            rid = s.get("{http://purl.oclc.org/ooxml/officeDocument/"
                        "relationships}id")
    if rid is None:
        raise FetchError(f"TI workbook: no sheet {sheet!r}")
    target = None
    for r in rels:
        if r.get("Id") == rid:
            target = r.get("Target").lstrip("/")
    if target is None:
        raise FetchError("TI workbook: sheet relationship unresolved")
    path = target if target.startswith("xl/") else "xl/" + target
    root = ET.fromstring(z.read(path))
    out = []
    for row in root.iter(M + "row"):
        cells = []
        for c in row:
            v = c.find(M + "v")
            value = v.text if v is not None else None
            if c.get("t") == "s" and value is not None:
                value = strings[int(value)]
            cells.append(value or "")
        out.append(cells)
    return out


def main() -> None:
    print("Fetching the Transparency International CPI for Poland...")
    body = None
    for url in URLS:
        try:
            body = get(url, suffix=".xlsx", timeout=180)
            break
        except FetchError as e:
            print(f"  {url}: {e}")
    if body is None:
        raise FetchError("TI CPI: no workbook answered")
    if not zipfile.is_zipfile(io.BytesIO(body)):
        raise FetchError("TI CPI: not an XLSX")
    rows = read_strict_xlsx(body, "CPI Historical")
    # Row 1 is the sheet's title, row 2 blank, row 3 the header.
    head = next(r for r in rows[:6] if "ISO3" in r)
    try:
        i_iso = head.index("ISO3")
        i_year = head.index("Year")
        i_score = head.index("CPI score")
        i_rank = head.index("Rank")
    except ValueError as e:
        raise FetchError(f"TI CPI: unexpected columns {head}") from e
    scores: dict[int, float] = {}
    ranks: dict[int, float] = {}
    for row in rows[1:]:
        if len(row) <= max(i_iso, i_year, i_score) or row[i_iso] != ISO3:
            continue
        try:
            year = int(row[i_year])
            scores[year] = float(row[i_score])
            ranks[year] = float(row[i_rank])
        except ValueError:
            continue
    if not scores:
        raise FetchError("TI CPI: no Polish observations")
    # Known values: Poland scored 53 in the 2024 edition and 56 in 2016.
    assert_close(scores.get(max(scores)), 53, 1, "CPI latest score")
    assert_close(scores.get(2016), 62, 1, "CPI 2016 score")

    header = ["year", "cpi_score", "cpi_rank"]
    out = []
    for y in range(Y0, Y1 + 1):
        out.append([y, scores.get(y), ranks.get(y)])
    path = write_csv("world/cpi_from_ti.csv", header, out, comment=f"""
Transparency International Corruption Perceptions Index, current edition
(2024 results; sheet "CPI Historical"), score 0-100 (higher = cleaner)
and rank among the countries scored. NON-OFFICIAL: an expert/survey
aggregate published by a NGO, not a statistic of the Polish state.
The CPI changed method in 2012: pre-2012 scores were 0-10 and are NOT
staged here, so this column starts in {min(scores)}. The atlas draws the
seam rather than splicing the two indices.
""")
    print(f"  -> {path.relative_to(DATA)}  ({min(scores)}-{max(scores)})")
    print("Done. Diff the *_from_ti.csv sidecar before adopting.")


if __name__ == "__main__":
    main()
