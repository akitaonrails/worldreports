#!/usr/bin/env python3
"""Cause-of-death counts from the Ministerio de Salud's vital statistics (DEIS).

Usage:  python3 scripts/fetch_causes.py

Outputs: data/social/causes_check.csv
         (year, deaths_total, covid, influenza, pneumonia, respiratory,
          suicide, transport)

The registry publishes one row per (year, jurisdiction, ICD-10 cause, sex,
age group) cell with a count, so a cause series is a sum over the count
column. Three ICD-10 groups are pulled out:

  U07         COVID-19
  J09-J11     influenza
  J12-J18     pneumonia
  X60-X84     intentional self-harm (suicide)
  V01-V89     land transport accidents

The last two were added for the spine's security slots. With the cause
truncated to three characters, V01-V89 is every land-transport accident,
traffic or not: wider than the WHO road-traffic definition, which needs the
fourth character to separate traffic from non-traffic. It is labelled as
such wherever it is drawn, beside the WHO series, never in place of it.

`respiratory` is influenza + pneumonia, which is the only honest way to read
the flu line: Argentina codes almost nothing as influenza (9 to 358 deaths a
year against 15,000-40,000 pneumonias), because a fatal influenza is
ordinarily certified as the pneumonia it became. The two are therefore
reported together as well as apart, and no panel should quote the influenza
column on its own.

Two caveats that belong on any chart drawn from this file:

  - **The cause column is truncated to three characters**, so U07.1
    (laboratory-confirmed COVID) and U07.2 (clinically diagnosed, no test)
    cannot be separated here. This series is confirmed + probable together.
  - It therefore does **not** reconcile with the epidemiological dashboard
    the ministry ran during the pandemic, which counted only confirmed
    cases and reported roughly 130,000 deaths through 2022 against the
    161,767 this registry records for 2020-2022. The registry is the wider
    and the later of the two; it is not a correction of the dashboard but a
    different count, and the gap is itself worth stating.

The total column is a by-product: it must reproduce the national totals in
`fetch_deis.py`, which is what `verify()` checks. If a cause sum is ever
wrong, the total will almost always be wrong first.
"""
from __future__ import annotations

import csv
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "deis"
DATA = ROOT / "data" / "social"
CACHE.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "argentina-reports/1.0 (+https://github.com/AkitaOnRails)"}
BASE = ("https://datos.salud.gob.ar/dataset/"
        "27c588e8-43d0-411a-a40c-7ecc563c2c9f/resource")

# (filename, url, delimiter) — the yearly files switched to semicolons in 2023
FILES = [
    ("defunciones_2005_2022.csv",
     f"{BASE}/ccf688f4-db38-4b0f-86f3-c99341ac52ad/download/defunciones-"
     "ocurridas-y-registradas-en-la-republica-argentina-entre-los-anos-"
     "2005-2022.csv", ","),
    ("defuncion2023.csv",
     f"{BASE}/e71b36a0-a68b-4bb5-a969-0a25929785bb/download/"
     "defuncion2023.csv", ";"),
    ("defuncion2024.csv",
     f"{BASE}/28e2aef4-c536-43bc-a098-0bdfb9d7933c/download/"
     "defuncion2024.csv", ";"),
]

# Published national totals, the same guard fetch_deis.py uses.
KNOWN_TOTALS = {2021: 436799, 2024: 376405}
# The pandemic's two peak years, from this same registry. A re-fetch that
# disagrees is reading a different file, not a revision.
KNOWN_COVID = {2020: 53222, 2021: 84695}

FIRST_YEAR, LAST_YEAR = 2005, 2026


def download(name: str, url: str) -> Path:
    path = CACHE / name
    if path.exists():
        print(f"  [cache] {name}")
        return path
    print(f"  downloading {name} …")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=900) as r:
                path.write_bytes(r.read())
            print(f"  -> {name} ({path.stat().st_size:,} bytes)")
            return path
        except Exception as e:  # noqa: BLE001
            print(f"  {name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"could not download {name}")


def bucket(code: str) -> str | None:
    """Map a truncated ICD-10 code to one of the groups this file tracks."""
    code = (code or "").strip().upper()
    if code.startswith("U07"):
        return "covid"
    if code[:1] == "J" and code[1:3].isdigit():
        chapter = int(code[1:3])
        if 9 <= chapter <= 11:
            return "influenza"
        if 12 <= chapter <= 18:
            return "pneumonia"
    if code[:1] == "X" and code[1:3].isdigit() and 60 <= int(code[1:3]) <= 84:
        return "suicide"
    if code[:1] == "V" and code[1:3].isdigit() and 1 <= int(code[1:3]) <= 89:
        return "transport"
    return None


def read_file(path: Path, delimiter: str) -> dict[int, dict[str, int]]:
    """Sum counts by year and group, streaming — the main file is 100 MB."""
    out: dict[int, dict[str, int]] = {}
    with path.open(encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=delimiter):
            try:
                year = int(row["anio"])
                count = int(row["cantidad"])
            except (TypeError, ValueError, KeyError):
                continue
            cell = out.setdefault(year, {"total": 0, "covid": 0,
                                         "influenza": 0, "pneumonia": 0,
                                         "suicide": 0, "transport": 0})
            cell["total"] += count
            group = bucket(row.get("cie10_causa_id", ""))
            if group:
                cell[group] += count
    return out


def read_all() -> dict[int, dict[str, int]]:
    total: dict[int, dict[str, int]] = {}
    for name, url, delimiter in FILES:
        part = read_file(download(name, url), delimiter)
        # later files restate earlier years rather than add to them
        total.update(part)
        if part:
            print(f"  {name}: {min(part)}-{max(part)}")
    return total


def verify(label: str, got: dict[int, int], known: dict[int, int]) -> None:
    for year, expected in known.items():
        actual = got.get(year)
        if actual != expected:
            raise SystemExit(
                f"{label} {year}: got {actual!r}, expected {expected:,}. The "
                f"upstream file changed shape — check it before adopting "
                f"this run.")
    print(f"  {label}: matches the known values for {sorted(known)}")


def main() -> None:
    print("DEIS — defunciones por causa (CIE-10)")
    rows = read_all()
    verify("total deaths", {y: c["total"] for y, c in rows.items()},
           KNOWN_TOTALS)
    verify("COVID-19 deaths", {y: c["covid"] for y, c in rows.items()},
           KNOWN_COVID)

    DATA.mkdir(parents=True, exist_ok=True)
    lines = ["year,deaths_total,covid,influenza,pneumonia,respiratory,"
             "suicide,transport"]
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        cell = rows.get(year)
        if cell is None:
            lines.append(f"{year},,,,,,,")
            continue
        respiratory = cell["influenza"] + cell["pneumonia"]
        lines.append(f"{year},{cell['total']},{cell['covid']},"
                     f"{cell['influenza']},{cell['pneumonia']},{respiratory},"
                     f"{cell['suicide']},{cell['transport']}")
    (DATA / "causes_check.csv").write_text("\n".join(lines) + "\n")
    print("  -> data/social/causes_check.csv")

    pandemic = sum(c["covid"] for c in rows.values())
    print(f"  COVID-19, all years: {pandemic:,} deaths "
          f"(confirmed and probable together)")


if __name__ == "__main__":
    main()
