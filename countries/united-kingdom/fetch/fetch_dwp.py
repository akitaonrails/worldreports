#!/usr/bin/env python3
"""Refresh the relative-poverty series from DWP's HBAI release.

Usage:  make C=united-kingdom fetch

Households Below Average Income is the Department for Work and Pensions'
annual read on the UK income distribution, built from the Family
Resources Survey. DWP runs the survey, so DWP is the publisher of record
for low income; the Gini and the income deciles are the ONS's inequality
bulletin (fetch_ons.py), a different survey family.

One table is taken, from the data-tables zip of the latest release:

  3.10ts  percentage of individuals living in households in relative
          low income, all individuals, before and after housing costs

Four things about this source that a chart will get wrong if nobody
writes them down:

**The year is not the calendar year.** Columns are labelled `24/25` and
run April to March, so the `fiscal_year` column here holds the starting
year: FYE 2025 (April 2024 to March 2025) is keyed 2024. It must never
be plotted against a calendar series without saying so.

**UK is not GB.** HBAI figures are United Kingdom from 2002/03 onwards;
earlier years are Great Britain only (the release's own Note 10). The
series below starts at 2002/03 so the whole file is one scope, and the
pre-2002/03 GB cells are left in the workbook, not spliced on.

**The series breaks at 2021/22.** From that year survey data is
integrated with DWP and HMRC administrative records and the release
states income data before and after the break are not comparable
(Note 1). It is one line with a marked seam, not two series.

**BHC and AHC are two columns, never one.** Relative low income is below
60 per cent of that year's median equivalised disposable household
income; the before/after housing costs gap is itself the finding
(housing costs). A relative threshold does not fall in a recession where
everyone's income falls together.

The release ships the tables as ODS inside a zip, not xlsx — so openpyxl
(the fetch dependency, checked below) is of no use here and the workbook
is parsed with the standard library: an ODS file is a zip carrying
content.xml. The gov.uk asset URL carries a content hash, so a new
edition means re-resolving the zip link from the collection page —
there is no /current/ equivalent.

Outputs are `_from_dwp` sidecars. Nothing here overwrites a curated file.
"""
from __future__ import annotations

import csv
import io
import re
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import openpyxl  # noqa: F401
    HAVE_XLSX = True
except ImportError:
    HAVE_XLSX = False

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
# The FYE 2025 release (published 2026-03), verified live from the
# collection page. Asset URLs are content-hashed: a new edition means a
# new URL, resolved from
# https://www.gov.uk/government/collections/households-below-average-income-hbai--2
RELEASE = "https://assets.publishing.service.gov.uk/media/69c2902a7e02b81c0d1c7762/hbai-data_tables-2025.zip"
MEMBER = "population-hbai-timeseries-1994-95-2024-25-tables.ods"
SHEET = "3_10ts"

T = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
X = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
O = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"

YEAR_LABEL = re.compile(r"^(\d{2})/(\d{2})$")
FIRST_UK_YEAR = 2002  # 2002/03 onwards is UK scope; earlier is GB (Note 10)


def workbook() -> bytes:
    CACHE.mkdir(exist_ok=True)
    local = CACHE / "hbai_data_tables_2025.zip"
    if not local.exists():
        print(f"  downloading {RELEASE}")
        with urllib.request.urlopen(RELEASE, timeout=300) as r:
            blob = r.read()
        # An error page under HTTP 200 is not a zip. Every zip carries
        # the PK magic number — the cheapest possible check.
        if blob[:2] != b"PK":
            raise RuntimeError("the HBAI download is not a zip")
        local.write_bytes(blob)
    with zipfile.ZipFile(local) as z:
        names = z.namelist()
        if MEMBER not in names:
            raise RuntimeError(f"{MEMBER}: not in this edition "
                               f"({len(names)} members)")
        payload = z.read(MEMBER)
    # The member is itself a zip (every ODS is). Shape-check before
    # parsing so a substituted file fails loudly rather than silently.
    if payload[:2] != b"PK":
        raise RuntimeError(f"{MEMBER}: not an ODS workbook")
    return payload


def rows_of(payload: bytes, sheet: str) -> list[list[str]]:
    """One sheet of an ODS workbook as a grid of strings.

    Repeated rows and columns are expanded; values come from the office
    value attribute with the paragraph text as fallback.
    """
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(payload))
                         .read("content.xml"))
    for table in root.iter(T + "table"):
        if table.get(T + "name") != sheet:
            continue
        grid = []
        for row in table.findall(T + "table-row"):
            values = []
            for cell in row.findall(T + "table-cell"):
                value = cell.get(O + "value") or "".join(
                    t for p in cell.iter(X + "p") for t in p.itertext())
                values += [value] * int(
                    cell.get(T + "number-columns-repeated") or 1)
            grid += [values] * int(
                row.get(T + "number-rows-repeated") or 1)
        return grid
    raise RuntimeError(f"sheet {sheet}: not in {MEMBER}")


def extract(grid: list[list[str]]) -> list[list]:
    """The two 'All individuals' rows of 3.10ts, keyed by fiscal_year.

    The sheet lays years across the columns (94/95 … 24/25) and stacks
    the breakdowns down the rows: a Before housing costs block, then an
    After housing costs block, each closing with 'All individuals
    (per cent)'. Only UK-scope years (2002/03 onward) are emitted.
    """
    title = grid[0][0] if grid and grid[0] else ""
    if "United Kingdom" not in title:
        raise RuntimeError(f"3.10ts title lost its scope: {title!r}")

    years, bhc, ahc = None, None, None
    section = None
    for row in grid:
        head = row[0].strip() if row else ""
        if head == "Before housing costs":
            section = "bhc"
        elif head == "After housing costs":
            section = "ahc"
        if years is None and any(YEAR_LABEL.match(c.strip())
                                 for c in row[1:]):
            years = [YEAR_LABEL.match(c.strip()) if c else None
                     for c in row]
        elif head == "All individuals (per cent)" and section:
            if section == "bhc":
                bhc = row
            else:
                ahc = row
    if not (years and bhc is not None and ahc is not None):
        raise RuntimeError("3.10ts: year header or an All individuals row "
                           "not found — the edition's layout changed")

    out = []
    for i, label in enumerate(years):
        if label is None:
            continue
        # 24/25 ends in March 2025 (FYE 2025); the fiscal_year key is
        # the starting year, 2024. The labels run 94/95 onward, so the
        # two-digit ending year pivots at the century.
        yy = int(label.group(2))
        ending = 1900 + yy if yy >= 60 else 2000 + yy
        starting = ending - 1
        if starting < FIRST_UK_YEAR:
            continue  # GB-only years stay in the workbook
        for column in (bhc, ahc):
            if i >= len(column) or column[i] in ("", ".."):
                raise RuntimeError(f"3.10ts: empty cell at {label.group(0)}")
        pair = (float(bhc[i]), float(ahc[i]))
        if not all(0.0 < v < 100.0 for v in pair):
            raise RuntimeError(f"3.10ts: implausible percentage at "
                               f"{label.group(0)}: {pair}")
        out.append([starting] + [f"{v:.1f}" for v in pair])
    return out


def main() -> None:
    print("DWP Households Below Average Income (release to FYE 2025)")
    if not HAVE_XLSX:
        print("  !! openpyxl not importable — harmless here: this release "
              "ships ODS, parsed with the standard library. If a future "
              "edition moves to xlsx, pip install -r requirements-fetch.txt")
    rows = extract(rows_of(workbook(), SHEET))

    rel = "social/poverty_from_dwp.csv"
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        fh.write("# DWP HBAI: individuals in relative low income (below 60%\n"
                 "# of that year's median equivalised disposable household\n"
                 "# income), before and after housing costs. United Kingdom\n"
                 "# scope from 2002/03 onwards; earlier years are Great\n"
                 "# Britain only (release Note 10) and are not included.\n"
                 "# fiscal_year is the STARTING year: 2024 = FYE 2025 =\n"
                 "# April 2024 to March 2025. Break in series at 2021/22:\n"
                 "# survey data integrated with DWP/HMRC admin records\n"
                 "# (release Note 1); not comparable across the seam.\n")
        w = csv.writer(fh)
        w.writerow(["fiscal_year",
                    "relative_low_income_bhc_pct",
                    "relative_low_income_ahc_pct"])
        w.writerows(rows)
    print(f"  data/{rel}  {len(rows)} rows "
          f"({rows[0][0]}–{rows[-1][0]})" if rows else
          f"  data/{rel}  EMPTY")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
