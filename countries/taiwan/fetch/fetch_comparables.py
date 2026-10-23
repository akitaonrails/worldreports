#!/usr/bin/env python3
"""Refresh Taiwan's available international comparable sidecars.

Transparency International publishes Taiwan in the CPI Historical sheet of
its annual workbook.  This fetcher reads that official workbook directly and
writes only the review sidecar; it never overwrites the curated CSV.
"""
from __future__ import annotations

import io
import re
import socket
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "comparables"
TI = "https://images.transparencycdn.org/images/CPI2025_Results.xlsx"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "*/*"}


class FetchError(RuntimeError):
    pass


def sheet(raw: bytes, sheet_name: str) -> list[dict[str, str]]:
    """Read one xlsx sheet as ``{column letter: value}`` rows."""
    z = zipfile.ZipFile(io.BytesIO(raw))
    book = z.read("xl/workbook.xml").decode()
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    sheets = dict(re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', book))
    targets = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels)
                   + [(b, a) for a, b in re.findall(
                       r'Target="([^"]+)"[^>]*Id="([^"]+)"', rels)])
    path = "xl/" + targets[sheets[sheet_name]].lstrip("/").replace("xl/", "")
    strings_xml = z.read("xl/sharedStrings.xml").decode()
    strings = ["".join(re.findall(r"<t[^>]*>(.*?)</t>", cell, re.S))
               for cell in re.findall(r"<si>(.*?)</si>", strings_xml, re.S)]
    out = []
    for row in re.findall(r"<row[^>]*>(.*?)</row>", z.read(path).decode(), re.S):
        cells = {}
        for match in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', row, re.S):
            ref, attrs, body = match.groups()
            value_match = re.search(r"<v>(.*?)</v>", body or "")
            value = value_match.group(1) if value_match else ""
            if 't="s"' in attrs and value:
                value = strings[int(value)]
            cells[ref] = value
        out.append(cells)
    return out


def fetch() -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "ti_CPI2025.xlsx"

    def valid(raw: bytes) -> bool:
        return raw[:2] == b"PK" and bool(sheet(raw, "CPI Historical"))

    if path.exists() and valid(path.read_bytes()):
        return path.read_bytes()
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(TI, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as response:
                raw = response.read()
            if not valid(raw):
                raise ValueError("not the CPI workbook")
            path.write_bytes(raw)
            return raw
        except (socket.gaierror, urllib.error.URLError, OSError, ValueError,
                zipfile.BadZipFile) as error:
            last = error
            print(f"  attempt {attempt + 1}: {type(error).__name__} {error}",
                  file=sys.stderr)
            time.sleep(2 + 2 * attempt)
    raise FetchError(f"TI workbook unavailable: {last}")


def main() -> None:
    rows = sheet(fetch(), "CPI Historical")
    head = next((r for r in rows if (r.get("A") or "").startswith("Country")), None)
    if head is None:
        raise FetchError("CPI Historical has no header row")
    columns = {value: key for key, value in head.items() if value}
    scores = {}
    for row in rows:
        if row.get(columns["ISO3"]) == "TWN" and row.get(columns["CPI score"]):
            year = int(float(row[columns["Year"]]))
            if 2012 <= year <= 2025:
                scores[year] = float(row[columns["CPI score"]])
    if scores.get(2025) != 68 or len(scores) < 14:
        raise FetchError(f"unexpected Taiwan CPI series: {scores}")
    path = DATA / "world" / "corruption_from_ti.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["year,cpi_score", *[f"{year},{scores[year]:.0f}" for year in sorted(scores)]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"data/world/corruption_from_ti.csv  {len(scores)} rows; 2025={scores[2025]:.0f}")


if __name__ == "__main__":
    main()
