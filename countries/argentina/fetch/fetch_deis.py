#!/usr/bin/env python3
"""Births and deaths from the Ministerio de Salud's vital statistics (DEIS).

Usage:  python3 scripts/fetch_deis.py

Outputs: data/social/vitals_check.csv  (year, births, deaths, natural_growth)

Argentina's demographic story in this window is not an ageing curve, it is a
collapse in births: 777,012 in 2014 against 413,135 in 2024, down 46.8% in
ten years. Natural growth fell with it, to 36,730 in 2024.

Two sources, each the registry's own:

  births  DEIS open data, one row per (year, jurisdiction, mother's age
          group, ...) cell with a count. Summing the count column by year
          reproduces the published national totals exactly, which is the
          check `verify()` performs. The 2005-2022 file is 68 MB, so it is
          streamed rather than loaded, and the 2023 file is semicolon
          -delimited where the others are comma-delimited.
  deaths  DEIS "serie histórica de defunciones ocurridas", 1914-2024, one
          row per year with a national column.

Both count events **registered** in the year. A death registered late lands
in the year it was registered, so the most recent year is revised upward in
the next edition — the gap is small but it is the reason this file is never
presented as final for its last year.
"""
from __future__ import annotations

import csv
import io
import sys
import time
import urllib.request
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "deis"
DATA = ROOT / "data" / "social"
CACHE.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "argentina-reports/1.0 (+https://github.com/AkitaOnRails)"}
BASE = "https://datos.salud.gob.ar/dataset"

BIRTH_FILES = [
    # (filename, url, delimiter)
    ("nacidos_vivos_2005_2022.csv",
     f"{BASE}/d1350588-d8bb-4892-b21c-48738311e218/resource/"
     "5a68ea36-03fe-4b38-b590-d7cf2a13b821/download/"
     "nacidos-vivos-registrados-en-la-republica-argentina-entre-los-anos-2005-2022.csv",
     ","),
    ("nacimientos2023.csv",
     f"{BASE}/d1350588-d8bb-4892-b21c-48738311e218/resource/"
     "40e722b8-72eb-49a0-89dc-5ee174bf63b4/download/nacimientos2023.csv",
     ";"),
    ("nacimientos2024.csv",
     f"{BASE}/d1350588-d8bb-4892-b21c-48738311e218/resource/"
     "ace82479-4659-4788-9609-5b98bc9081bd/download/nacimientos2024-.csv",
     ","),
]

DEATHS_FILE = (
    "defunciones_1914_2024.xlsx",
    f"{BASE}/76ce7d19-921d-4d17-bb20-73c1fe55f07e/resource/"
    "a73d215a-3bf2-45d9-9fbf-ed1e1a32fd8e/download/"
    "serie-historica-defunciones-ocurridas-argentina-jurisdiccion-1914-2024.xlsx",
)

# Published national totals, for the check below. If a re-fetch disagrees
# with these the upstream file changed shape and the sum is not the series
# it used to be — which is exactly the failure that should stop a build.
KNOWN_BIRTHS = {2014: 777012, 2023: 460902, 2024: 413135}
KNOWN_DEATHS = {2021: 436799, 2024: 376405}


def download(name: str, url: str) -> Path:
    path = CACHE / name
    if path.exists():
        print(f"  [cache] {name}")
        return path
    print(f"  downloading {name} …")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=600) as r:
                path.write_bytes(r.read())
            print(f"  -> {name} ({path.stat().st_size:,} bytes)")
            return path
        except Exception as e:  # noqa: BLE001
            print(f"  {name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"could not download {name}")


def births_from(path: Path, delimiter: str) -> dict[int, int]:
    """Sum the count column by year, streaming — the main file is 68 MB."""
    out: dict[int, int] = {}
    with path.open(encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=delimiter):
            try:
                year = int(row["anio"])
                out[year] = out.get(year, 0) + int(row["nacimientos_cantidad"])
            except (TypeError, ValueError, KeyError):
                continue
    return out


def read_births() -> dict[int, int]:
    total: dict[int, int] = {}
    for name, url, delimiter in BIRTH_FILES:
        part = births_from(download(name, url), delimiter)
        for year, count in part.items():
            # later files restate earlier years rather than add to them
            total[year] = count
        if part:
            print(f"  {name}: {min(part)}-{max(part)}")
    return total


def read_deaths() -> dict[int, int]:
    path = download(*DEATHS_FILE)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
    try:
        national = header.index("república argentina")
    except ValueError:  # the column was renamed: fall back to the first one
        national = 1
        print("  national column not found by name — using column 1",
              file=sys.stderr)
    out: dict[int, int] = {}
    for row in rows[1:]:
        year, value = row[0], row[national]
        if year is None or value is None:
            continue
        year = year.year if hasattr(year, "year") else int(str(year)[:4])
        out[int(year)] = int(value)
    return out


def verify(label: str, got: dict[int, int], known: dict[int, int]) -> None:
    """A silent shape change upstream would quietly rewrite history."""
    for year, expected in known.items():
        actual = got.get(year)
        if actual != expected:
            raise SystemExit(
                f"{label} {year}: got {actual!r}, the published total is "
                f"{expected:,}. The upstream file changed shape — check it "
                f"before adopting this run.")
    print(f"  {label}: matches the published totals for {sorted(known)}")


def main() -> None:
    print("DEIS — nacidos vivos registrados")
    births = read_births()
    verify("births", births, KNOWN_BIRTHS)

    print("DEIS — serie histórica de defunciones")
    deaths = read_deaths()
    verify("deaths", deaths, KNOWN_DEATHS)

    DATA.mkdir(parents=True, exist_ok=True)
    lines = ["year,births,deaths,natural_growth"]
    for year in range(2006, 2027):
        b, d = births.get(year), deaths.get(year)
        growth = b - d if (b is not None and d is not None) else None
        lines.append(f"{year},{b if b is not None else ''},"
                     f"{d if d is not None else ''},"
                     f"{growth if growth is not None else ''}")
    (DATA / "vitals_check.csv").write_text("\n".join(lines) + "\n")
    print("  -> data/social/vitals_check.csv")

    peak = max((y for y in births if y <= 2020), key=lambda y: births[y])
    last = max(births)
    print(f"  births peak {births[peak]:,} in {peak}; {births[last]:,} in "
          f"{last} ({(births[last] / births[peak] - 1) * 100:+.1f}%)")


if __name__ == "__main__":
    main()
