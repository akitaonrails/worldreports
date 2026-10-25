#!/usr/bin/env python3
"""Refresh the INE tabulados Venezuela actually publishes, into sidecars.

Usage:  python3 -I fetch/fetch_ine.py [--offline]

The Instituto Nacional de Estadística's site is a WordPress portal, not a
statistical API: there is no SDMX, no JSON endpoint and no CPI. What it does
publish, as .xlsx under `wp-content/uploads/`, is the household-survey Gini
and the labour-force tabulado. This fetcher handles only the Gini, because
the labour sheet's rows are identified by numeric concept codes whose legend
is not in the workbook (see SOURCES.yaml meta.pending) and guessing which code
is the unemployment rate is how a wrong series gets published.

Two hard checks stand between the gateway and the sidecar:

  * the payload must start with the ZIP magic `PK`: the portal serves an HTML
    page under HTTP 200 when a path moves, and openpyxl would raise something
    less clear than this;
  * the sheet must be the one expected and must carry the pinned years and
    values. The workbook's own title is stale ("1997 - 2020") while the values
    run 1999-2025, so the title is checked for being *the expected string*
    rather than read as a claim about coverage.

NETWORK NOTE (2026-10-25): ine.gob.ve does not answer the build network at
all — curl exits 000 after a 25-second timeout on both schemes and both
`ine.gob.ve` and `www.ine.gob.ve`, and no proxy is configured. The same host
answers an agent's egress proxy, so this is an access condition on this
network, not a dead publisher. The 2026-10-25 payload is preserved as
fetch/reference_ine_gini_2026-10-25.csv, transcribed cell by cell, and the
curated CSV was promoted from it. Run this fetcher from a network that can
reach the INE to regenerate data/people/gini_from_ine.csv and diff it against
the reference.

Offline: `--offline` reads the cache only; a cold cache exits 2 and writes
nothing.
"""
from __future__ import annotations

import io
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
URL = "https://ine.gob.ve/wp-content/uploads/2026/09/COEFICIENTE-GINI.xlsx"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
           "Accept": "application/vnd.openxmlformats-officedocument."
                     "spreadsheetml.sheet,*/*"}
YEAR_FROM, YEAR_TO = 2006, 2025
EXPECTED_SHEET = "Coeficiente Gini, 1997 - 2020"

COMMENTS = [
    "Instituto Nacional de Estadística (Venezuela), 'Tabulados — Coeficiente",
    "GINI', workbook published 2026-09, retrieved 2026-10-25.",
    "URL: https://ine.gob.ve/wp-content/uploads/2026/09/COEFICIENTE-GINI.xlsx",
    "UNIT: converted from the workbook's 0-1 index to the atlas's 0-100",
    "scale by multiplying by 100 (an exact unit change, not a re-estimate).",
    "The workbook's sheet title says '1997 - 2020' while its values run",
    "1999-2025: the title is stale, the cells are what is published.",
    "DEFINITION: the INE's household-survey Gini (Encuesta de Hogares por",
    "Muestreo). It is the national series; the World Bank's SEDLAC-harmonised",
    "Gini stops in 2006 and is a separate cross-check column, never spliced.",
    "The published series shows no collapse after 2014 (0.38-0.39 throughout),",
    "which is itself the finding to disclose: the survey's coverage and its",
    "non-response in the emigration years are not documented by the publisher.",
]


def fetch(offline: bool) -> bytes:
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "ine_gini.xlsx"
    if cache_file.exists():
        return cache_file.read_bytes()
    if offline:
        print("  !! INE: offline and no cache", file=sys.stderr)
        raise SystemExit(2)
    last = None
    for attempt in range(1):
        try:
            req = urllib.request.Request(URL, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as r:
                raw = r.read()
            if not raw[:2] == b"PK":
                raise ValueError("payload is not a ZIP/xlsx (HTML under 200?)")
            cache_file.write_bytes(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3)
    raise SystemExit(
        f"INE unreachable or unparseable: {last}. The publisher does not "
        f"answer this network (see the module docstring and SOURCES.yaml "
        f"meta.pending); fetch/reference_ine_gini_2026-10-25.csv holds the "
        f"2026-10-25 payload's values.")


def parse(raw: bytes) -> dict[int, float]:
    from openpyxl import load_workbook

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        if "xl/workbook.xml" not in zf.namelist():
            raise SystemExit("INE: not an xlsx workbook")
    wb = load_workbook(io.BytesIO(raw), data_only=True)
    if EXPECTED_SHEET not in wb.sheetnames:
        raise SystemExit(f"INE: sheet {EXPECTED_SHEET!r} missing; "
                         f"found {wb.sheetnames}")
    ws = wb[EXPECTED_SHEET]
    if ws.max_row < 25:
        raise SystemExit(f"INE: sheet has {ws.max_row} rows, expected ~30")
    sheet_title = ws.cell(row=1, column=2).value
    if sheet_title != EXPECTED_SHEET:
        raise SystemExit(f"INE: title cell reads {sheet_title!r}")

    out: dict[int, float] = {}
    for row in range(4, 40):
        year = ws.cell(row=row, column=2).value
        value = ws.cell(row=row, column=3).value
        if year is None or value is None:
            continue
        year = int(year)
        value = float(value)
        if not 0 < value < 1:
            raise SystemExit(f"INE: {year} Gini {value} is not on a 0-1 scale")
        out[year] = value
    if len(out) < 25:
        raise SystemExit(f"INE: only {len(out)} observations parsed")
    return out


def write(values: dict[int, float]) -> None:
    path = ROOT / "data" / "people" / "gini_from_ine.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in COMMENTS]
    lines.append("year,gini")
    rows = 0
    for y in sorted(values):
        if YEAR_FROM <= y <= YEAR_TO:
            lines.append(f"{y},{values[y] * 100:.3f}")
            rows += 1
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/people/gini_from_ine.csv  {rows} rows")


def verify(values: dict[int, float]) -> None:
    assert abs(values[2006] - 0.442) < 0.0005, f"Gini 2006: {values.get(2006)}"
    assert abs(values[2014] - 0.380) < 0.0005, f"Gini 2014: {values.get(2014)}"
    assert abs(values[2023] - 0.38555) < 0.00005, \
        f"Gini 2023: {values.get(2023)}"
    assert abs(values[2025] - 0.394) < 0.0005, f"Gini 2025: {values.get(2025)}"
    assert min(values) == 1999 and max(values) == 2025, \
        f"row set changed: {sorted(values)[:2]}..{sorted(values)[-2:]}"


def main() -> None:
    offline = "--offline" in sys.argv[1:]
    print("INE tabulados for Venezuela" + (" (offline)" if offline else ""))
    values = parse(fetch(offline))
    write(values)
    verify(values)
    print("All discovery anchors verified. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
