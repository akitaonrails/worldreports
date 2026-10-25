#!/usr/bin/env python3
"""Refresh Venezuela's IMF WEO series into review sidecars.

Usage:  python3 -I fetch/fetch_imf.py [--offline]

The IMF is not a courtesy extra here: it is the only publisher that carries
Venezuelan inflation, growth and the general-government accounts through the
years in which the BCV stopped publishing them. Every one of these numbers is
a **staff estimate for a country that does not report**, and the plates say so
— this fetcher's sidecars keep the estimate/projection seam visible so a
projection can never be drawn as an outturn.

The seam used is `last_full_year` from country.yaml: years up to it land in
the plain column, later years only in the `_proj` column, and the two are
asserted disjoint.

One indicator is genuinely absent: GGXWDG_NGDP (general government gross
debt) has no Venezuela series at all in the October 2026 vintage. The fetcher
records that as a miss and never substitutes another debt concept —
SOURCES.yaml meta.pending carries the routes that were tried.

Offline: `--offline` reads the cache only; a cold cache exits 2 and writes
nothing.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
ISO3 = "VEN"
BASE = "https://www.imf.org/external/datamapper/api/v1/{code}"
# www.imf.org's edge answers 403 to any UA beginning "Mozilla/5.0" (verified
# again from this lane 2026-10-25); a plain descriptive UA is served.
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0",
           "Accept": "application/json"}

YEAR_FROM, YEAR_TO = 2006, 2026
LAST_FULL_YEAR = 2025

# (code, column, decimals) — one plain column per series, projections split.
SERIES = [
    ("macro/growth_from_imf.csv", "NGDP_RPCH", "gdp_growth_pct", 2),
    ("macro/inflation_from_imf.csv", "PCPIPCH", "cpi_inflation_pct", 2),
    ("macro/unemployment_from_imf.csv", "LUR", "unemployment_pct", 2),
    ("world/gdp_usd_from_imf.csv", "NGDPD", "gdp_usd", 0),
]

# The fiscal block: one vintage for every column, projections apart.
FISCAL = [
    ("rev", "revenue_pct_gdp", 2),
    ("exp", "expenditure_pct_gdp", 2),
    ("GGXCNL_NGDP", "balance_pct_gdp", 2),
    ("pb", "primary_balance_pct_gdp", 2),
    ("ie", "interest_pct_gdp", 2),
]

COMMENTS = {
    "macro/growth_from_imf.csv": [
        "IMF WEO (October 2026 vintage) NGDP_RPCH, real GDP growth %.",
        "STAFF ESTIMATE for every year: Venezuela has not reported national",
        "accounts to the Fund for years. The World Bank's independent estimate",
        "agrees on the sign throughout and differs on size (2020: -33.2 here,",
        "-29.8 there); both are drawn, neither corrects the other.",
        "SERIES NOTE: the underlying GDP level is a rebased staff estimate, so",
        "growth rates either side of a rebasing year are not strictly",
        "comparable; the plate carries that as a note, not as a seam.",
    ],
    "macro/inflation_from_imf.csv": [
        "IMF WEO (October 2026 vintage) PCPIPCH, average consumer prices, %.",
        "STAFF ESTIMATE. This is the only series that covers the",
        "hyperinflation: 2018 = 65,374%, 2019 = 19,906%, 2020 = 2,355%.",
        "The national CPI (BCV's INPC, as the World Bank republishes it) stops",
        "in 2016 and is a SEPARATE column in macro/economy_from_worldbank.csv",
        "— the two are drawn as two lines and never spliced into one.",
        "This is also the series that leaves the economy slot's shared",
        "-5..225 scale by three orders of magnitude (see country.yaml).",
    ],
    "macro/unemployment_from_imf.csv": [
        "IMF WEO LUR, unemployment % of the labour force. ENDS IN 2018: after",
        "that the Fund publishes no Venezuelan labour-market series. It is the",
        "national-definition line the WEO carried, drawn beside the ILO",
        "modelled estimate in economy_from_worldbank.csv, not instead of it.",
    ],
    "world/gdp_usd_from_imf.csv": [
        "IMF WEO NGDPD, GDP at current prices, US$ bn converted at the WEO's",
        "own rate convention. NOT the canonical world-slot series (that is the",
        "World Bank's NY.GDP.MKTP.CD); it is the second, labelled line that",
        "shows how much of Venezuela's dollar GDP is an artefact of which",
        "exchange rate a compiler chose (2014: 128.8 here against 214.8 at the",
        "World Bank).",
    ],
    "fiscal/fiscal_from_imf.csv": [
        "IMF WEO (October 2026 vintage), general government: rev, exp,",
        "GGXCNL_NGDP, pb, ie — one vintage for all five columns. Observed to",
        "2024 (rev/exp/pb/ie) and 2025 (the overall balance); later years only",
        "in the _proj column. STAFF ESTIMATE: Venezuela publishes no",
        "general-government accounts on any reachable route.",
        "2018: revenue 6.9% of GDP, expenditure 37.9%, overall balance -31.9%.",
        "NO DEBT SERIES: GGXWDG_NGDP has no Venezuela observations in this",
        "vintage, and no other official route produced one (SOURCES.yaml).",
    ],
}


def series(code: str, offline: bool) -> dict[int, float]:
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"imf_{ISO3}_{code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    elif offline:
        print(f"  !! {code}: offline and no cache", file=sys.stderr)
        raise SystemExit(2)
    else:
        last = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(BASE.format(code=code),
                                             headers=HEADERS)
                with urllib.request.urlopen(req, timeout=90) as r:
                    body = r.read()
                ctype = r.headers.get("Content-Type", "")
                if "json" not in ctype:
                    raise ValueError(f"content-type {ctype!r} is not JSON")
                payload = json.loads(body)
                values = payload.get("values", {}).get(code, {}).get(ISO3)
                if not isinstance(values, dict) or not values:
                    raise ValueError("not a DataMapper indicator response")
                cache_file.write_text(json.dumps(payload))
                break
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"  {code} attempt {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        else:
            raise SystemExit(f"{code}: {last}")
    values = payload.get("values", {}).get(code, {}).get(ISO3, {})
    return {int(y): float(v) for y, v in values.items() if v is not None}


def write_series(rel: str, code: str, column: str, dec: int,
                 values: dict[int, float]) -> dict[int, float]:
    if not values:
        print(f"  !! {rel}: nothing fetched", file=sys.stderr)
        raise SystemExit(3)
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in COMMENTS.get(rel, [])]
    # A column of blanks is a promise the data does not keep: the October
    # 2026 vintage carries no Venezuelan projection for some of these
    # series, and then the `_proj` column is not written at all.
    has_proj = any(y > LAST_FULL_YEAR for y in values)
    header = [column, f"{column}_proj"] if has_proj else [column]
    lines.append("year," + ",".join(header))
    rows = 0
    for y in sorted(values):
        if not YEAR_FROM <= y <= YEAR_TO:
            continue
        observed = y <= LAST_FULL_YEAR
        if has_proj:
            row = (f"{values[y]:.{dec}f}", "") if observed \
                else ("", f"{values[y]:.{dec}f}")
            assert (row[0] == "") != (row[1] == ""), \
                f"{code} {y}: observed/projected disjointness broken"
            lines.append(f"{y},{row[0]},{row[1]}")
        else:
            if not observed:
                continue
            lines.append(f"{y},{values[y]:.{dec}f}")
        rows += 1
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {rows} rows "
          f"(<= {LAST_FULL_YEAR} observed"
          + (", later projections apart)" if has_proj else ")"))
    return values


def write_fiscal(series_map: dict[str, dict[int, float]]) -> dict:
    missing = [c for c, _, _ in FISCAL if not series_map.get(c)]
    if missing:
        print(f"  !! fiscal: no series for {missing}, nothing written",
              file=sys.stderr)
        raise SystemExit(3)
    path = ROOT / "data" / "fiscal" / "fiscal_from_imf.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = [("year",)]
    lines = [f"# {c}" for c in COMMENTS["fiscal/fiscal_from_imf.csv"]]
    bal = series_map["GGXCNL_NGDP"]
    has_proj = any(y > LAST_FULL_YEAR for y in bal)
    header = ["year"] + [col for _, col, _ in FISCAL] + \
             (["balance_pct_gdp_proj"] if has_proj else [])
    lines.append(",".join(header))
    years = sorted(set().union(*(s for s in series_map.values())))
    rows = 0
    for y in years:
        if not YEAR_FROM <= y <= YEAR_TO:
            continue
        cells = []
        for code, _, dec in FISCAL:
            s = series_map[code]
            cells.append(f"{s[y]:.{dec}f}"
                         if (y <= LAST_FULL_YEAR and y in s) else "")
        if has_proj:
            cells.append(f"{bal[y]:.2f}"
                         if (y > LAST_FULL_YEAR and y in bal) else "")
        if not any(cells):
            continue
        lines.append(f"{y}," + ",".join(cells))
        rows += 1
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/fiscal/fiscal_from_imf.csv  {rows} rows")
    return series_map


def verify(s: dict[str, dict[int, float]], fiscal: dict) -> None:
    cpi = s["PCPIPCH"]
    assert abs(cpi[2018] - 65374.1) < 0.2, f"CPI 2018: {cpi.get(2018)}"
    assert abs(cpi[2019] - 19906.0) < 0.2, f"CPI 2019: {cpi.get(2019)}"
    assert abs(cpi[2016] - 254.9) < 0.2, f"CPI 2016: {cpi.get(2016)}"
    g = s["NGDP_RPCH"]
    assert abs(g[2020] - -33.2) < 0.05, f"growth 2020: {g.get(2020)}"
    assert abs(g[2018] - -21.4) < 0.05, f"growth 2018: {g.get(2018)}"
    lur = s["LUR"]
    assert max(lur) == 2018 and abs(lur[2018] - 5.5) < 0.05, \
        f"LUR row set changed: {sorted(lur)[-3:]}"
    assert abs(fiscal["GGXCNL_NGDP"][2018] - -31.9) < 0.05, \
        f"balance 2018: {fiscal['GGXCNL_NGDP'].get(2018)}"
    assert abs(fiscal["rev"][2018] - 6.88) < 0.02, \
        f"revenue 2018: {fiscal['rev'].get(2018)}"
    assert abs(fiscal["exp"][2018] - 37.86) < 0.02, \
        f"expenditure 2018: {fiscal['exp'].get(2018)}"
    assert abs(s["NGDPD"][2014] - 128.764) < 0.01, \
        f"WEO GDP 2014: {s['NGDPD'].get(2014)}"


def main() -> None:
    offline = "--offline" in sys.argv[1:]
    print("IMF WEO series for Venezuela" + (" (offline)" if offline else ""))
    store: dict[str, dict[int, float]] = {}
    for rel, code, column, dec in SERIES:
        store[code] = write_series(rel, code, column, dec, series(code, offline))
    fiscal = {code: series(code, offline) for code, _, _ in FISCAL}
    write_fiscal(fiscal)
    verify(store, fiscal)
    print("All discovery anchors verified. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
