#!/usr/bin/env python3
"""Refresh South Korea's official migration review sidecars.

Nothing in this script overwrites a curated CSV.  The flow table is the
Statistics Korea International Migration Statistics table exposed by
e-National Indicators.  It counts people entering or leaving for more than
90 days and separates Korean and foreign citizens.  The stock table is the
Statistics Korea register-based census release, measured on 1 November.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from fetch_index_kr import as_series, fetch

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) worldreports/1.0"}
STOCK_URL = ("https://www.kostat.go.kr/boardDownload.es?bid=11739&"
             "list_no=439063&seq=1")


def write_sidecar(rel: str, header: str, years: list[int],
                  columns: list[dict[int, str]]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [header]
    for year in years:
        lines.append(f"{year}," + ",".join(col.get(year, "") for col in columns))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  -> data/{rel}")


def fetch_flows() -> None:
    rows = fetch("migration", "101401", "1014")
    if len(rows) < 13:
        raise RuntimeError(f"migration table changed shape: {len(rows)} rows")
    years = list(range(2006, 2026))
    total = [as_series(rows, label) for label in ("입국자", "출국자", "순이동")]
    korean = [as_series(rows, label, after="내국인")
              for label in ("입국자", "출국자", "순이동")]
    foreign = [as_series(rows, label, after="외국인")
               for label in ("입국자", "출국자", "순이동")]
    if [col.get(2024) for col in total] != ["727357", "601954", "125403"]:
        raise RuntimeError("2024 total-flow landmark changed")
    if [col.get(2024) for col in korean] != ["276490", "248843", "27647"]:
        raise RuntimeError("2024 Korean-citizen landmark changed")
    for year in years:
        for i in range(3):
            if int(total[i][year]) != int(korean[i][year]) + int(foreign[i][year]):
                raise RuntimeError(f"citizenship components do not sum in {year}")
    write_sidecar("social/migration_check.csv", "year,arrivals,departures,net",
                  years, total)
    write_sidecar(
        "migration/flows_by_citizenship_check.csv",
        "year,korean_arrivals,korean_departures,korean_net,"
        "foreign_arrivals,foreign_departures,foreign_net",
        years, [korean[0], korean[1], korean[2],
                foreign[0], foreign[1], foreign[2]])


def fetch_stock() -> None:
    request = urllib.request.Request(STOCK_URL, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
        content_type = response.headers.get("Content-Type", "")
    if not payload.startswith(b"%PDF-") or len(payload) < 100_000:
        raise RuntimeError(f"stock release is not a PDF ({content_type}, {len(payload)} bytes)")
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "stock.pdf"
        txt = Path(tmp) / "stock.txt"
        pdf.write_bytes(payload)
        subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True)
        text = txt.read_text(encoding="utf-8")
    # The release's major-indicators table prints 2022, 2023 and 2024 in
    # columns, in thousands.  Match the labelled rows, never loose numbers.
    def values(label: str) -> list[str]:
        match = re.search(rf"^{label}\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)",
                          text, flags=re.M)
        if not match:
            raise RuntimeError(f"missing stock row: {label}")
        return [value.replace(",", "") for value in match.groups()]

    total = values(r"\s*Total population")
    foreign = values(r"\s*Nationality\s+Foreigner")
    share = values(r"\s*Share of foreigners")
    if (total, foreign, share) != (["51692", "51775", "51806"],
                                  ["1752", "1935", "2043"],
                                  ["3.4", "3.7", "3.9"]):
        raise RuntimeError("register-census stock landmarks changed")
    years = [2022, 2023, 2024]
    write_sidecar(
        "migration/foreign_residents_census_check.csv",
        "year,total_population_thousands,foreign_citizens_thousands,"
        "foreign_citizen_share_pct",
        years,
        [{year: value for year, value in zip(years, col)}
         for col in (total, foreign, share)],
    )


def main() -> None:
    fetch_flows()
    fetch_stock()


if __name__ == "__main__":
    main()
