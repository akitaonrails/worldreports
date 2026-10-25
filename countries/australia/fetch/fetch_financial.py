#!/usr/bin/env python3
"""Refresh APRA's non-performing-loan ratios and BITRE's road deaths.

Usage:  python3 -I fetch/fetch_financial.py   (or: make C=australia fetch)

Two regulators, two series, both of which the atlas draws:

  APRA — Quarterly authorised deposit-taking institution performance,
      Table 1g ("ADIs' performance ratios", all ADIs). Two ratios, on two
      definitions, never spliced:
        * "Impaired facilities to loans and advances": September 2004 to
          December 2021, the pre-2022 APRA definition;
        * "Non-performing to loans and advances": 2022 onwards, which is
          a wider definition (it adds facilities 90+ days past due that
          were not previously impaired). The step between the two is
          visible in the CSV because the columns are separate, and the
          plate labels it as a definitional break.
      Year-end = the December quarter, the spine's stock rule.

  BITRE — Australian Road Deaths Database, the individual fatality
      record, mirrored by data.gov.au (the BITRE host itself times out
      from this network; see DISCOVERY.md). The calendar-year count is
      the number of rows; the rate is that count over the ABS estimated
      resident population at 30 June of the same year, which is the
      population the ABS publishes its own rates against. The mirror's
      last complete calendar year is 2022, and a partial 2023 is dropped
      rather than drawn as a year.
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = Path(__file__).resolve().parent / "cache"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _sdmx import FetchError, get  # noqa: E402

APRA = ("https://www.apra.gov.au/system/files/2026-09/"
        "Quarterly%20authorised%20deposit-taking%20institution%20"
        "performance-September%202004%20to%20June%202026%20%281%29.xlsx")
ARDD = ("https://data.gov.au/data/dataset/"
        "5b530fb8-526e-4fbf-b0f6-aa24e84e4277/resource/"
        "fd646fdc-7788-4bea-a736-e4aeb0dd09a8/download/ardd_fatalities.csv")


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    print(f"  wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def npl() -> list[dict]:
    import openpyxl

    body = get(APRA, accept="application/vnd.openxmlformats-officedocument"
                           ".spreadsheetml.sheet")
    if body[:2] != b"PK":
        raise FetchError("APRA: not an xlsx")
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "apra_qadi_performance.xlsx").write_bytes(body)
    wb = openpyxl.load_workbook(io.BytesIO(body), read_only=True,
                                data_only=True)
    ws = wb["Tab 1g"]
    rows = list(ws.iter_rows(min_row=4, max_row=ws.max_row,
                             max_col=ws.max_column, values_only=True))
    hdr = rows[0]
    cols = {i: str(c) for i, c in enumerate(hdr) if c}
    wanted = {"npl_impaired_pct": "impaired facilities to loans",
              "npl_nonperforming_pct": "non-performing to loans"}
    series: dict[str, dict[int, float]] = {k: {} for k in wanted}
    for r in rows:
        label = str(r[0] or "").strip().lower()
        for col, prefix in wanted.items():
            if not label.startswith(prefix):
                continue
            for i, q in cols.items():
                if not i or not q.startswith("Dec "):
                    continue
                v = r[i]
                if v in (None, ""):
                    continue
                year = int(q[-4:])
                series[col][year] = round(float(v) * 100, 2)
    if not series["npl_nonperforming_pct"]:
        raise FetchError("APRA: no non-performing ratio row")
    years = sorted(set(series["npl_impaired_pct"])
                   | set(series["npl_nonperforming_pct"]))
    out = []
    for y in years:
        out.append({"year": y,
                    "npl_impaired_pct": series["npl_impaired_pct"].get(y, ""),
                    "npl_nonperforming_pct": series[
                        "npl_nonperforming_pct"].get(y, "")})
    print(f"  APRA Tab 1g: impaired {min(series['npl_impaired_pct'])}-"
          f"{max(series['npl_impaired_pct'])}, non-performing "
          f"{min(series['npl_nonperforming_pct'])}-"
          f"{max(series['npl_nonperforming_pct'])}")
    return out


def road_deaths() -> list[dict]:
    body = get(ARDD, accept="text/csv")
    text = body.decode("utf-8-sig", "replace")
    if not text.startswith("Crash ID"):
        raise FetchError("ARDD: not the fatality CSV")
    rows = list(csv.DictReader(io.StringIO(text)))
    if len(rows) < 50_000:
        raise FetchError(f"ARDD: only {len(rows)} rows")
    counts: dict[int, int] = {}
    for r in rows:
        y = (r.get("Year") or "").strip()
        if y.isdigit():
            counts[int(y)] = counts.get(int(y), 0) + 1
    pop = {}
    pop_path = DATA / "demography" / "population_from_abs.csv"
    if not pop_path.exists():
        raise FetchError("run fetch_abs.py first (needs the ERP population)")
    for r in csv.DictReader(pop_path.open(encoding="utf-8")):
        pop[int(r["year"])] = int(r["population_jun30"])
    # A year is complete only when the mirror's last month is December.
    last_month = max((int(r["Year"]), int(r["Month"])) for r in rows
                     if (r.get("Month") or "").isdigit()
                     and (r.get("Year") or "").isdigit())
    out = []
    for y in sorted(counts):
        if (y, 12) > last_month:
            continue
        if y not in pop:
            continue
        out.append({"year": y, "road_deaths": counts[y],
                    "road_deaths_per_100k": round(
                        counts[y] / pop[y] * 100_000, 2)})
    if 2022 not in counts or counts[2022] != 1180:
        raise FetchError(f"ARDD: 2022 count {counts.get(2022)}, expected 1180")
    print(f"  ARDD: {out[0]['year']}-{out[-1]['year']} "
          f"(mirror's last month {last_month[0]}-{last_month[1]:02d})")
    return out


def main() -> None:
    try:
        print("APRA — ADI performance ratios")
        write_csv(DATA / "credit" / "npl_from_apra.csv",
                  ["year", "npl_impaired_pct", "npl_nonperforming_pct"], npl())
        print("BITRE — Australian Road Deaths Database (data.gov.au mirror)")
        write_csv(DATA / "security" / "road_deaths_from_bitre.csv",
                  ["year", "road_deaths", "road_deaths_per_100k"],
                  road_deaths())
    except FetchError as e:
        print(f"fetch error: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
