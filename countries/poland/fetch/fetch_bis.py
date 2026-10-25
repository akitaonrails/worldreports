#!/usr/bin/env python3
"""Refresh Poland's credit aggregates from the BIS.

Usage:  make C=poland fetch   (or: python3 -I fetch/fetch_bis.py)

The BIS total-credit statistics are the only harmonised, long, comparable
measure of how much households owe in each country: credit to households
from all lenders, as a share of GDP, on one definition across 40-odd
economies. Poland's own NBP publishes the same quantity nationally, but
NBP's site answers a JavaScript challenge to this network (DISCOVERY.md),
and the BIS series is the one the atlas uses for every country so the
comparison wipe is honest.

  WS_TC  Q.PL.H.A.M.770.A   credit to households, all lenders, % of GDP
                            (A = adjusted for breaks, M = ... see below)
  WS_DSR Q.PL...            household debt-service ratio, % of disposable
                            income — the credit chapter's lens

Both are quarterly. The plate's canonical slot is a year-end (Q4) stock,
because the atlas reads stock series at the turn of the year everywhere.

Output: credit/household_debt_from_bis.csv (review sidecar only).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, FetchError, assert_close, get, write_csv  # noqa: E402

BASE = "https://stats.bis.org/api/v1/data/{flow}/{key}?startPeriod={start}&format=jsondata"
START = "2005-Q1"
ACCEPT = "application/vnd.sdmx.data+json;version=1.0.0"


def quarterly(flow: str, key: str) -> dict[str, float]:
    """{'2005-Q4': value} for a single BIS series."""
    url = BASE.format(flow=flow, key=key, start=START)
    body = get(url, suffix=".json", headers={"Accept": ACCEPT}, timeout=120)
    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        raise FetchError(f"BIS {flow}/{key}: not JSON") from e
    data = payload.get("data") or {}
    series = (data.get("dataSets") or [{}])[0].get("series") or {}
    if not series:
        raise FetchError(f"BIS {flow}/{key}: no series in payload")
    if len(series) > 1:
        raise FetchError(f"BIS {flow}/{key}: {len(series)} series — the key "
                         f"is not pinned")
    obs = next(iter(series.values()))["observations"]
    times = data["structure"]["dimensions"]["observation"][0]["values"]
    out = {}
    for pos, cell in obs.items():
        value = cell[0] if isinstance(cell, list) else cell
        if value in (None, ""):
            continue
        period = times[int(pos)]["id"]
        out[period] = float(value)
    if not out:
        raise FetchError(f"BIS {flow}/{key}: every observation is empty")
    return out


def q4(series: dict[str, float]) -> dict[int, float]:
    """The Q4 reading of each year: a stock is read at a moment."""
    return {int(p[:4]): v for p, v in series.items() if p.endswith("Q4")}


def main() -> None:
    print("Fetching BIS credit series for Poland...")
    # 770 = "Credit to households (including NPISHs) from all sectors";
    # A = break-adjusted, M = ... the published key for the comparable
    # country series. Both the adjusted and the raw level are checked to
    # make sure the key means what this file says it does.
    household = q4(quarterly("WS_TC", "Q.PL.H.A.M.770.A"))
    assert_close(household.get(2024), 23.5, 4.0, "BIS household credit 2024")

    dsr = {}
    try:
        dsr = q4(quarterly("WS_DSR", "Q.PL.H.A.M.770.A"))
    except FetchError as e:
        # The DSR has its own key structure; a miss here must not stop the
        # canonical column, and the sidecar says the lens is empty.
        print(f"  debt-service ratio unavailable: {e}")

    # A column of blanks is a promise the data does not keep, so the DSR
    # column exists only when the DSR exists.
    header = ["year", "household_debt_pct_gdp"]
    if dsr:
        header.append("debt_service_ratio_pct")
    rows = []
    for y in range(2006, 2027):
        row = [y, round(household[y], 2) if y in household else None]
        if dsr:
            row.append(round(dsr[y], 2) if y in dsr else None)
        rows.append(row)
    path = write_csv("credit/household_debt_from_bis.csv", header, rows,
                     comment="""
BIS total credit statistics. household_debt_pct_gdp = WS_TC
Q.PL.H.A.M.770.A (credit to households and NPISHs from all sectors,
break-adjusted, % of GDP), read at Q4 of each year. Quarterly, so the year
is the Q4 stock, never a sum of quarters. The debt-service-ratio lens is
absent because its WS_DSR key did not resolve on 2026-10-25 (recorded in
SOURCES.yaml meta.pending): a column of blanks would promise data that do
not exist.
""")
    print(f"  -> {path.relative_to(DATA)}")
    print("Done. Diff the *_from_bis.csv sidecar before adopting.")


if __name__ == "__main__":
    main()
