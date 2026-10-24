#!/usr/bin/env python3
"""Fetch national ACS B05002 rows from official table-based bulk files."""
from __future__ import annotations

import csv
import io
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "migration" / "stock_acs_from_census.csv"
YEARS = (2021, 2022, 2023, 2024)
FIELDS = ("B05002_E001", "B05002_E013", "B05002_E014", "B05002_E021")


def row(year: int) -> list[int]:
    url = ("https://www2.census.gov/programs-surveys/acs/summary_file/"
           f"{year}/table-based-SF/data/1YRData/acsdt1y{year}-b05002.dat")
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    if not response.content.startswith(b"GEO_ID|"):
        raise RuntimeError(f"unexpected ACS file signature for {year}")
    rows = list(csv.DictReader(io.StringIO(response.text), delimiter="|"))
    national = [r for r in rows if r.get("GEO_ID") == "0100000US"]
    if len(national) != 1 or any(name not in national[0] for name in FIELDS):
        raise RuntimeError(f"ACS B05002 national row/header check failed for {year}")
    return [int(national[0][name]) for name in FIELDS]


def main() -> None:
    rows = [(year, *row(year)) for year in YEARS]
    if rows[-1] != (2024, 340110990, 50234858, 25837975, 24396883):
        raise RuntimeError("ACS 2024 known-value check failed")
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(("year", "total_population", "foreign_born",
                         "naturalized", "noncitizen"))
        writer.writerows(rows)


if __name__ == "__main__":
    main()
