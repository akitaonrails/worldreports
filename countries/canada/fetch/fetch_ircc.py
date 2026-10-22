#!/usr/bin/env python3
"""Refresh the immigration series from IRCC's open data.

Usage:  make C=canada fetch

Immigration, Refugees and Citizenship Canada publishes monthly counts of
permanent-resident admissions and of study and work permit holders
through open.canada.ca. It is the department that admits them, so it is
the publisher of record for the flow.

Three things this source will mislead you about.

**The numbers are rounded.** Every cell is a multiple of five — all
19,503 of them in the permanent-resident file, with no exceptions — and
IRCC labels the files "not for calculations" for that reason. At the
national level it does not matter: the 2024 admissions sum here to
482,960 against IRCC's published 483,390, a difference of 0.02 per cent.
It matters enormously for a small country of citizenship, where a cell
holding two people is published as zero or as five. Composition panels
drawn from this must stay well above that floor, and the national total
belongs to Statistics Canada's demographic estimates, which are not
rounded.

**The files are tab-separated and named .csv.**

**They begin in 2015.** There is no 2006–2014 here, so the back half of
this atlas's window has to come from IRCC's annual reports to Parliament
or from Statistics Canada. A chart that starts in 2015 without saying so
draws the rise and hides what it rose from.

A fourth thing, which is not a trap but is the whole point of the
chapter: the permanent-resident flow is the smaller half of the story.
Canada's population grew by about three per cent in 2023 — a rate
unmatched in the G7 and unmatched in Canada since 1957 — and most of
that was non-permanent residents, students and temporary workers who do
not appear in the permanent-resident file at all.

Outputs are `_from_ircc` sidecars. Nothing here overwrites a curated file.
"""
from __future__ import annotations

import csv
import io
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "migration"
CACHE = ROOT / "cache"
BASE = "https://www.ircc.canada.ca/opendata-donneesouvertes/data/{name}"

FILES = {
    "pr_by_citizenship": "ODP-PR-Citz.csv",
    "pr_by_province": "ODP-PR-PT_IMMCAT.csv",
    "study_by_citizenship": "ODP-TR-Study-IS_CITZ.csv",
}
# Rows that are a total, a suppression marker or a residual, and must be
# dropped before anything is summed or ranked.
NOT_A_COUNTRY = {
    "total", "total unknown", "unknown", "not stated", "other",
    "united nations", "stateless",
}


def grab(key: str) -> list[dict]:
    CACHE.mkdir(exist_ok=True)
    local = CACHE / f"ircc_{key}.tsv"
    if not local.exists():
        with urllib.request.urlopen(BASE.format(name=FILES[key]),
                                    timeout=300) as r:
            blob = r.read()
        if b"\t" not in blob[:400]:
            raise RuntimeError(f"{FILES[key]}: not the tab-separated file")
        local.write_bytes(blob)
    text = local.read_text(encoding="utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def number(raw: str | None) -> int | None:
    """One cell as a count, or None.

    IRCC writes a suppressed cell as `--` and a zero as `0`; they are not
    the same and must not both become zero.
    """
    if raw is None:
        return None
    text = raw.replace(",", "").strip()
    return int(text) if text.isdigit() else None


def write(name: str, header: list[str], rows: list[list]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"  data/migration/{name}  {len(rows)} rows")


def main() -> None:
    print("IRCC open data")

    pr = grab("pr_by_citizenship")
    years: Counter[str] = Counter()
    by_country: dict[str, Counter[str]] = defaultdict(Counter)
    for row in pr:
        n = number(row.get("TOTAL"))
        country = (row.get("EN_COUNTRY_OF_CITIZENSHIP") or "").strip()
        year = (row.get("EN_YEAR") or "").strip()
        if n is None or not year.isdigit():
            continue
        if country.lower() in NOT_A_COUNTRY:
            continue
        years[year] += n
        by_country[country][year] += n

    write("pr_admissions_from_ircc.csv", ["year", "admissions"],
          [[y, years[y]] for y in sorted(years)])

    # The ten largest sources over the whole file, each as its own column,
    # so the plate ranks once rather than re-ranking every year and
    # drawing a composition that reshuffles under the reader.
    top = [c for c, _ in Counter(
        {c: sum(v.values()) for c, v in by_country.items()}).most_common(10)]
    rows = [[y] + [by_country[c].get(y, "") for c in top]
            for y in sorted(years)]
    write("pr_by_origin_from_ircc.csv",
          ["year"] + [c.lower().replace(" ", "_") for c in top], rows)

    study = grab("study_by_citizenship")
    totals: Counter[str] = Counter()
    for row in study:
        n = number(row.get("TOTAL"))
        year = (row.get("EN_YEAR") or "").strip()
        country = (row.get("EN_COUNTRY_OF_CITIZENSHIP") or "").strip()
        if n is None or not year.isdigit():
            continue
        if country.lower() in NOT_A_COUNTRY:
            continue
        totals[year] += n
    write("study_permits_from_ircc.csv", ["year", "permit_holders"],
          [[y, totals[y]] for y in sorted(totals)])

    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
