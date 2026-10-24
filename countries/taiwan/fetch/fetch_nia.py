#!/usr/bin/env python3
"""Refresh the NIA month-end ARC-resident review sidecar from its ODS."""
from __future__ import annotations

import csv
import io
import ssl
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "migration"
CACHE = ROOT / "cache" / "migration"
URL = ("https://www.immigration.gov.tw/media/117189/"
       "%E5%A4%96%E5%83%91%E5%B1%85%E7%95%99%E4%BA%BA%E6%95%B8%E7%B5%B1%E8%A8%88"
       "%E8%A1%A811412.ods")
NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
}


def download() -> bytes:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90,
                               context=ssl.create_default_context()) as response:
        body = response.read()
    if not body.startswith(b"PK") or not zipfile.is_zipfile(io.BytesIO(body)):
        raise RuntimeError("NIA response is not an ODS/ZIP file")
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "nia-foreign-residents-11412.ods").write_bytes(body)
    return body


def rows(body: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        root = ET.fromstring(zf.read("content.xml"))
    sheets = root.findall(".//table:table", NS)
    if not sheets:
        raise RuntimeError("NIA ODS has no worksheets")
    out = []
    for row in sheets[0].findall("table:table-row", NS):
        values = []
        for cell in row.findall("table:table-cell", NS):
            repeat = int(cell.get(f"{{{NS['table']}}}number-columns-repeated", "1"))
            value = "".join(cell.itertext()).strip()
            values.extend([value] * min(repeat, 50))
        if any(values):
            out.append(values)
    return out


def main() -> None:
    table = rows(download())
    # Preserve a reviewable flattened extract first.  Parsing the publisher's
    # merged bilingual presentation table is intentionally pinned to the two
    # latest December totals and foreign-labour counts.
    CACHE.joinpath("nia-first-sheet.tsv").write_text(
        "\n".join("\t".join(row) for row in table), encoding="utf-8")
    text = "\n".join("\t".join(row) for row in table)
    for expected in ("948,066", "1,028,945", "712,158", "751,806"):
        if expected not in text and expected.replace(",", "") not in text:
            raise RuntimeError(f"NIA ODS no longer contains pinned value {expected}")
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / "foreign_residents_from_nia.csv").open(
            "w", encoding="utf-8", newline="") as fh:
        out = csv.writer(fh, lineterminator="\n")
        out.writerow(["year", "arc_foreign_residents_dec", "foreign_labour_dec"])
        out.writerow([2024, 948066, 712158])
        out.writerow([2025, 1028945, 751806])
    print("wrote official NIA ARC review sidecar")


if __name__ == "__main__":
    main()
