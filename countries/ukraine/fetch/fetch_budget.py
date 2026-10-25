"""Ukraine's consolidated budget by function, from the NBU's budget API.

    python3 -m countries.ukraine.fetch.fetch_budget [--offline]

Writes the review sidecar `spending/budget_function_from_nbu.csv`; the
curated file is a separate reviewed step.

The endpoint (https://bank.gov.ua/NBUStatService/v1/statdirectory/budget)
carries the Treasury's monthly execution. Its December row is the
year-to-date total, which is the annual figure this sidecar stores. The
functional classification is the Ukrainian budget one (gf_budgtef_0100 …
_1000); `0180` is the inter-budget transfer *inside* `0100`, so it is
excluded from the stack or every total would double-count it. `Total_1`
is expenditure less inter-budget transfers and equals the sum of the
functions — asserted, not assumed.

Cash basis, consolidated budget (state plus local). That is NOT the IMF
general-government accrual layer the fiscal chapter draws, and the plate
says so.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "nbu" / "budget"
URL = ("https://bank.gov.ua/NBUStatService/v1/statdirectory/budget"
       "?start={start}&end={end}&json")
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}
FIRST, LAST = 2006, 2026

FUNCTIONS = {
    "gf_budgtef_0100": "state_administration",
    "gf_budgtef_0200": "defence",
    "gf_budgtef_0300": "public_order",
    "gf_budgtef_0400": "economic_activity",
    "gf_budgtef_0500": "environment",
    "gf_budgtef_0600": "housing",
    "gf_budgtef_0700": "health",
    "gf_budgtef_0800": "recreation",
    "gf_budgtef_0900": "education",
    "gf_budgtef_1000": "social_protection",
}
TOTAL = "gf_budgtef_Total_1"          # less inter-budget transfers
CAPITAL = "gf_budgtee_3000"           # capital expenditure

# 2023 as published: total 3,776,857 mn UAH, defence 1,784,473 mn.
KNOWN = {2023: {"total": 3_776_857.0, "defence": 1_784_473.0}}


def fail(msg: str) -> None:
    print(f"fetch_budget: {msg}", file=sys.stderr)
    sys.exit(1)


def payload(year: int, offline: bool) -> list:
    cache = CACHE / f"budget_{year}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    if offline:
        fail(f"no cache at {cache} and --offline given; nothing written")
    url = URL.format(start=f"{year}1201", end=f"{year}1231")
    body = b""
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as fh:
                body = fh.read()
            break
        except Exception as exc:                    # noqa: BLE001
            last = exc
            time.sleep(3 * (attempt + 1))
    else:
        fail(f"{url} failed: {type(last).__name__}: {last}; nothing written")
    rows = json.loads(body)
    if not isinstance(rows, list) or not rows:
        # Early years predate the series; an empty year is skipped, and the
        # minimum-year check below still guards against a dead endpoint.
        return []
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    return rows


def year_totals(rows: list) -> dict[str, float]:
    """The year-to-date value of each series in the December payload."""
    out: dict[str, float] = {}
    for row in rows:
        api = row.get("id_api")
        # mcr200p distinguishes the consolidated budget (CBU) from the
        # state budget alone (SBU); this sidecar is the consolidated one.
        if row.get("mcr200p") not in (None, "CBU"):
            continue
        if api in FUNCTIONS or api in (TOTAL, CAPITAL):
            if row.get("value") not in (None, ""):
                out[api] = float(row["value"])
    return out


def main(argv: list[str]) -> int:
    offline = "--offline" in argv
    records: dict[int, dict[str, float]] = {}
    for year in range(FIRST, LAST + 1):
        rows = payload(year, offline)
        vals = year_totals(rows)
        if TOTAL in vals:
            records[year] = vals
    if len(records) < 15:
        fail(f"only {len(records)} years came back; expected most of "
             f"{FIRST}-{LAST}")

    for year, want in KNOWN.items():
        got = records.get(year, {})
        if abs(got.get(TOTAL, 0) - want["total"]) > 1:
            fail(f"{year} total: {got.get(TOTAL)!r}, expected {want['total']}")
        if abs(got.get("gf_budgtef_0200", 0) - want["defence"]) > 1:
            fail(f"{year} defence: {got.get('gf_budgtef_0200')!r}")
        # The published total must equal the sum of the functions; a
        # payload that breaks this is double-counting 0180 or missing one.
        parts = sum(got.get(k, 0.0) for k in FUNCTIONS)
        if abs(parts - got[TOTAL]) > 2:
            fail(f"{year}: functions sum to {parts:,.0f} but Total_1 is "
                 f"{got[TOTAL]:,.0f}")

    path = ROOT / "data" / "spending" / "budget_function_from_nbu.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(FUNCTIONS.values()) + ["capital", "total"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["year"] + cols)
        for year in sorted(records):
            vals = records[year]
            w.writerow([year] + [f"{vals.get(k, 0.0):.1f}"
                                 for k in FUNCTIONS]
                       + [f"{vals.get(CAPITAL, 0.0):.1f}",
                          f"{vals[TOTAL]:.1f}"])
    print(f"  data/spending/budget_function_from_nbu.csv  "
          f"{len(records)} rows")
    print("Done. Diff the sidecar before adopting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
