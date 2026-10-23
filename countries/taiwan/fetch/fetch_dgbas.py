#!/usr/bin/env python3
"""Refresh the DGBAS national-accounts spine into sidecar CSVs.

Usage:  python3 -I countries/taiwan/fetch/fetch_dgbas.py

The Directorate General of Budget, Accounting and Statistics (主計總處) is
Taiwan's national statistical office and the single most important
publisher here: with the World Bank, the IMF and the UN absent for Taiwan
(COUNTRIES.md row 8), the DGBAS DPAS engine IS the economy and demography
spine and the only national income/GDP/CPI/population series.

Everything runs on one ASP.NET "DPAS" query protocol (see DISCOVERY.md §1):
  * table definition JSON:  sys=212&x=2100&funid=<CODE>
  * data-out JSON:          sys=220&kind=100&funid=<CODE>&ym=<from>&ymt=<to>
                            &cycle=<col>&outmode=8[&fldlst=<bitmask>]
  * the payload is {funid,name,links,colh,col,row,orgdata,outdata,...};
    orgdata is FIELD-major (one list per column, N values across the
    period rows), and `row` carries the period labels. outmode 2 (CSV) is
    Big5; outmode 8 (JSON) is what we parse.

The DPAS engines date every period by ROC year (民國), so a row label like
`95年` is calendar 2006 (ROC + 1911) and `97年第3季` is 2008 Q3. A fetcher
that silently mis-added the 1911 offset would put the 2008-09 collapse on
the wrong year and every growth bar would still "look fine". So ROC
conversion is asserted twice: against pinned CE-year spot values AND
against a pinned ROC-label offset the fetcher recovers by name.

Two DPAS quirks the code below exists for:

  * the machine's resolver (127.0.0.53) intermittently times out (DISCOVERY
    §), so get() retries the DNS/connect a few times with a short backoff
    before declaring the publisher dead; and
  * some tables emit INVALID JSON — the display markup for the table name
    (`<font size="small">`, an unescaped double quote inside a JSON string)
    leaks into the `title` field, which is enough to break json.loads on an
    otherwise-complete body. That is an "endpoints that lie" case: a truncated
    or unparseable body must never be cached as an empty result. get() strips
    only the display tags, then shape-checks the real {colh,col,row,orgdata}
    BEFORE caching; a body that fails the shape check is retried, not written.

The quarterly national accounts are SEASONALLY-ADJUSTED annual-rate series
(SOURCING §4): the annual GDP is the publisher's own annual row, NOT the
sum or mean of the quarters, so the annual series reads the annual rows and
the quarterly sidecar reads the quarterly rows; nothing is combined.

Output: sidecars only, beside where the curated files will land. A fetcher
never overwrites a curated number; a person diffs these.

  data/economy/gdp_from_dgbas.csv                     (annual levels/growth/per-head/FX)
  data/economy/gdp_growth_quarterly_from_dgbas.csv    (quarterly y/y growth — dates the 2008-09 collapse)
  data/economy/cpi_from_dgbas.csv                     (annual CPI index + y/y inflation)
  data/demography/population_from_dgbas.csv           (mid-year population, administrative register)
  data/mortality/causes_of_death_from_dgbas.csv       (annual deaths by cause, 合計, 2008 on)
"""
from __future__ import annotations

import json
import re
import socket
import sys
import time
import urllib.request
from pathlib import Path

NAME = "Taiwan"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "dgbas"

BASE = "https://nstatdb.dgbas.gov.tw/dgbasAll/webMain.aspx"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "*/*"}

ROC = 1911  # ROC year + ROC = CE year; asserted in every parse below.

# A018101010 column order (colh[0] of the full key table, fldlst=15x1).
NA_COLS = {
    "population": 0,        # 期中人口(人)
    "avg_fx": 1,            # 平均匯率(元/美元)
    "growth": 2,            # 經濟成長率(%)
    "gdp_ntd_mn": 3,        # GDP 名目值, 百萬元
    "gdp_usd_mn": 4,        # GDP 名目值, 百萬美元
    "gdp_pc_usd": 6,        # 平均每人GDP, 美元
}
# A170101020 causes (codName1, 合計), each a block of 4 fields:
#   count, rank, crude rate/100k, standardised rate/100k.
DEATH_CAUSES = [
    ("all_cause", "所有死因"),
    ("cancer", "惡性腫瘤"),
    ("heart", "心臟疾病（高血壓性疾病除外）"),
    ("pneumonia", "肺炎"),
    ("cerebrovascular", "腦血管疾病"),
    ("diabetes", "糖尿病"),
    ("hypertension", "高血壓性疾病"),
    ("accidents", "事故傷害"),
    ("kidney", "腎炎、腎病症候群及腎病變"),
    ("chronic_respiratory", "慢性下呼吸道疾病"),
    ("suicide", "蓄意自我傷害（自殺）"),
]


class FetchError(RuntimeError):
    pass


# ------------------------------------------------------------------- transport
def _repair(raw: str) -> str:
    """Strip DPAS display markup that leaks unescaped quotes into JSON strings.

    A table title like `中央政府債務未償餘額<font size="small">(...)` puts a raw
    `"` inside a JSON string value and breaks json.loads on a complete body.
    These tags only ever appear inside display-name strings, so removing them
    recovers a parseable payload without touching any number.
    """
    return re.sub(r"</?(?:font|b|br|i|u)[^>]*>", "", raw)


def get(url: str, cache_name: str, check):
    """The parsed DPAS payload at `url`, validated by `check` BEFORE caching.

    A cached error page or truncated body is worse than no cache: it survives
    the retry that would have fixed it. So `check` runs on the way in and
    again on a cached copy from an older run, which is thrown away if it fails.
    Retries the DNS/connect (the flaky local resolver) with a short backoff.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        try:
            return check(_repair(path.read_text(encoding="utf-8")))
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache {cache_name}: {e}", file=sys.stderr)
            path.unlink()
    last: Exception | None = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read().decode("utf-8", "replace")
            payload = check(_repair(raw))          # validate BEFORE caching
            path.write_text(raw, encoding="utf-8")  # cache the raw body
            return payload
        except (socket.gaierror, urllib.error.URLError, OSError,
                ValueError, json.JSONDecodeError) as e:
            last = e
            print(f"  {cache_name} attempt {attempt + 1}: {type(e).__name__} {e}",
                  file=sys.stderr)
            time.sleep(2 + 2 * attempt)             # short backoff, then give up
    raise FetchError(f"{url}: {last}")


def dpas(funid: str, *, kind="100", ym, ymt, cycle, fldlst=None,
         codlst0=None, codlst1=None, cache=None):
    """A DPAS data-out call for one table, shape-checked and parsed."""
    url = (f"{BASE}?sys=220&kind={kind}&funid={funid}"
           f"&ym={ym}&ymt={ymt}&cycle={cycle}&outmode=8")
    if fldlst:
        url += f"&fldlst={fldlst}"
    if codlst0:
        url += f"&codlst0={codlst0}"
    if codlst1:
        url += f"&codlst1={codlst1}"

    def check(raw):
        p = json.loads(raw)
        for key in ("colh", "col", "row", "orgdata"):
            if key not in p:
                raise ValueError(f"DPAS payload missing {key!r} "
                                 "(error page or truncated body?)")
        if not p["row"] or not p["orgdata"]:
            raise ValueError("DPAS payload has no rows or no orgdata")
        if p["funid"] != funid:
            raise ValueError(f"payload funid {p['funid']!r} != {funid!r}")
        return p

    return get(url, cache or f"{funid}.json", check)


def period(row_label: str):
    """ROC label -> (CE year, kind, quarter). Raises if the label is not one.

    The ROC offset is not applied blindly: `roc_ce` below pins the mapping to
    a known label the fetcher also asserts against a spot value.
    """
    if m := re.fullmatch(r"(\d{2,3})年第(\d)季", row_label):
        return roc_ce(int(m.group(1))), "q", int(m.group(2))
    if m := re.fullmatch(r"(\d{2,3})年", row_label):
        return roc_ce(int(m.group(1))), "y", None
    if m := re.fullmatch(r"(\d{2,3})年(\d{1,2})月", row_label):
        return roc_ce(int(m.group(1))), "m", int(m.group(2))
    raise ValueError(f"unrecognised period label {row_label!r}")


def roc_ce(roc: int) -> int:
    if not (40 <= roc <= 130):
        raise ValueError(f"ROC year {roc} out of range — offset is wrong")
    return roc + ROC


# ------------------------------------------------------------------- collect
def collect():
    """Every sidecar this fetcher writes: {rel: {year: {col: value}}} (or a
    {rel: (header_cols, rows)} map for the long-format quarterly/deaths files)."""
    tables: dict[str, dict[int, dict[str, float]]] = {}
    decimals: dict[tuple[str, str], int] = {}
    order: dict[str, list[str]] = {}

    def put(rel, column, series, dec):
        if not series:
            raise FetchError(f"{rel}: {column} came back empty")
        t = tables.setdefault(rel, {})
        for year, value in series.items():
            t.setdefault(year, {})[column] = value
        decimals[(rel, column)] = dec
        order.setdefault(rel, []).append(column)

    # --- national income key table: annual + quarterly, 2006..2025 -------
    print("DGBAS A018101010 — national income key table")
    p = dpas("A018101010", ym=9500, ymt=11400, cycle=42, fldlst="1" * 15)
    labels = [r[0] for r in p["row"]]
    org = p["orgdata"]
    assert org[NA_COLS["growth"]][labels.index("98年")] == -1.61, \
        "A018101010 label alignment/offset broken: 98年 is not 2009 growth -1.61"

    def annual(field, want_year):
        out = {}
        for j, lbl in enumerate(labels):
            yr, kind, _ = period(lbl)
            if kind == "y" and yr == want_year:
                return org[field][j]
        return None

    ann_years = [period(lbl)[0] for lbl in labels if period(lbl)[1] == "y"]
    def col_annual(field):
        out = {}
        for j, lbl in enumerate(labels):
            yr, kind, _ = period(lbl)
            if kind == "y":
                out[yr] = org[field][j]
        return out

    pop = col_annual(NA_COLS["population"])
    gdp_n = col_annual(NA_COLS["gdp_ntd_mn"])
    gdp_u = col_annual(NA_COLS["gdp_usd_mn"])
    pc_u = col_annual(NA_COLS["gdp_pc_usd"])
    grw = col_annual(NA_COLS["growth"])
    fx = col_annual(NA_COLS["avg_fx"])

    put("economy/gdp_from_dgbas.csv", "real_growth_pct", grw, 2)
    put("economy/gdp_from_dgbas.csv", "gdp_nominal_ntd_mn", gdp_n, 0)
    put("economy/gdp_from_dgbas.csv", "gdp_nominal_usd_mn", gdp_u, 0)
    put("economy/gdp_from_dgbas.csv", "gdp_per_capita_usd", pc_u, 0)
    put("economy/gdp_from_dgbas.csv", "avg_fx_ntd_per_usd", fx, 2)
    put("demography/population_from_dgbas.csv", "population", pop, 0)
    print(f"  A018101010 annual {len(ann_years)} years "
          f"{min(ann_years)}-{max(ann_years)}")

    # quarterly growth (seasonally adjusted annual rates), same table
    q = {}
    for j, lbl in enumerate(labels):
        yr, kind, qq = period(lbl)
        if kind == "q":
            q[(yr, qq)] = org[NA_COLS["growth"]][j]
    print(f"  A018101010 quarterly {len(q)} observations")
    collect.quarterly_growth = q

    # --- CPI A030101015 (headline 總指數, cycle=41), annual averages ------
    print("DGBAS A030101015 — CPI headline")
    c = dpas("A030101015", ym=9500, ymt=11509, cycle=41)
    clabels = [r[0] for r in c["row"]]
    cidx = c["orgdata"][0]
    cpi_ann = {}
    for j, lbl in enumerate(clabels):
        yr, kind, _ = period(lbl)
        if kind == "y":
            cpi_ann[yr] = cidx[j]
    # y/y inflation off the publisher's own annual average (base 2021=100)
    infl = {}
    for yr in cpi_ann:
        if yr - 1 in cpi_ann and cpi_ann[yr - 1]:
            infl[yr] = (cpi_ann[yr] / cpi_ann[yr - 1] - 1) * 100
    put("economy/cpi_from_dgbas.csv", "cpi_index_2021_100", cpi_ann, 2)
    put("economy/cpi_from_dgbas.csv", "cpi_inflation_pct", infl, 2)
    print(f"  A030101015 CPI annual {len(cpi_ann)} years "
          f"{min(cpi_ann)}-{max(cpi_ann)}")
    collect.cpi = cpi_ann

    # --- deaths by cause A170101020 (合計, 11 causes, 2008 on) ------------
    print("DGBAS A170101020 — deaths by cause")
    d = dpas("A170101020", ym=9700, ymt=11400, cycle=4, fldlst="1111",
             codlst0="1", codlst1="1" * 11)
    dlabels = [r[0] for r in d["row"]]
    dorg = d["orgdata"]                       # 11 causes x 4 fields, year-aligned
    dyears = [period(lbl)[0] for lbl in dlabels]
    for ci, (name, _) in enumerate(DEATH_CAUSES):
        counts = {dyears[j]: dorg[4 * ci][j] for j in range(len(dlabels))}
        put("mortality/causes_of_death_from_dgbas.csv", f"deaths_{name}",
            {y: v for y, v in counts.items() if v}, 0)
    print(f"  A170101020 {len(dyears)} years {min(dyears)}-{max(dyears)}, "
          f"{len(DEATH_CAUSES)} causes")

    collect.decimals = decimals
    collect.order = order
    return tables


# -------------------------------------------------------------------- checks
SPOT = [
    # (sidecar, column, CE year, value) — read off DGBAS live 2026-10-23.
    ("economy/gdp_from_dgbas.csv", "real_growth_pct", 2009, -1.61),
    ("economy/gdp_from_dgbas.csv", "real_growth_pct", 2020, 3.42),
    ("economy/gdp_from_dgbas.csv", "gdp_nominal_ntd_mn", 2025, 28_715_120),
    ("economy/gdp_from_dgbas.csv", "gdp_per_capita_usd", 2025, 39_515),
    ("demography/population_from_dgbas.csv", "population", 2006, 22_823_455),
    ("demography/population_from_dgbas.csv", "population", 2019, 23_596_027),
    ("mortality/causes_of_death_from_dgbas.csv", "deaths_all_cause", 2008, 142_283),
    ("mortality/causes_of_death_from_dgbas.csv", "deaths_all_cause", 2025, 199_576),
]

# The quarterly series that dates the 2008-09 collapse (SOURCING: never
# sum the annual-rate quarters; the collapse is read off the quarterly y/y).
Q_SPOT = [
    ("y", 2009, -1.61),          # annual cross-check
    ("q", (2008, 3), -1.39),
    ("q", (2008, 4), -7.36),
    ("q", (2009, 1), -7.87),
]


def spot_checks(tables):
    bad = []
    for rel, column, year, want in SPOT:
        got = tables.get(rel, {}).get(year, {}).get(column)
        if got is None or abs(got - want) > max(abs(want) * 0.02, 0.1):
            bad.append(f"{rel} {column} {year}: want {want}, got {got}")
    q = collect.quarterly_growth
    for kind, key, want in Q_SPOT:
        if kind == "y":
            got = tables["economy/gdp_from_dgbas.csv"][key]["real_growth_pct"]
        else:
            got = q.get(key)
        if got is None or abs(got - want) > 0.05:
            bad.append(f"quarterly/annual growth {key}: want {want}, got {got}")
    if bad:
        raise FetchError("spot checks failed:\n  " + "\n  ".join(bad))
    print(f"Spot checks: {len(SPOT)} values + ROC-offset pinned "
          f"(98年=2009=-1.61) as expected")


def cross_checks(tables):
    """Internal consistency and, when present, the CBC/CPI cross-reads.

    GDP USD level must equal the publisher's own NTD level over its own
    average exchange rate (the USD column is derived, not a second source).
    The population register must peak at 2019 then fall (the brief's premise).
    CPI must sit on its published 2021=100 base.
    """
    bad = []
    print("Cross-checks")
    gdp = tables["economy/gdp_from_dgbas.csv"]
    for year in sorted(gdp):
        n, u, fx = (gdp[year].get("gdp_nominal_ntd_mn"),
                    gdp[year].get("gdp_nominal_usd_mn"),
                    gdp[year].get("avg_fx_ntd_per_usd"))
        if n and u and fx:
            implied = n / fx
            if abs(implied - u) / u > 0.01:
                bad.append(f"GDP USD {year}: NTD/FX gives {implied:,.0f}, "
                           f"publisher says {u:,.0f}")
    print("  GDP US$ == NTD / avg-FX within 1% — ok")
    pop = tables["demography/population_from_dgbas.csv"]
    peak = max(pop, key=lambda y: pop[y]["population"])
    if peak != 2019:
        bad.append(f"population peaks {peak}, not 2019")
    if not (pop[2025]["population"] < pop[2019]["population"]
            < pop[2006]["population"] + 1_000_000):
        bad.append("population is not 22.8mn -> 23.6mn peak -> 23.3mn falling")
    print(f"  population peak {peak} then declining — ok")
    cpi = tables["economy/cpi_from_dgbas.csv"]
    if abs(cpi.get(2021, {}).get("cpi_index_2021_100", 0) - 100) > 0.5:
        bad.append("CPI 2021 is not on the 100 base")
    print("  CPI base 2021=100 — ok")
    # cross-fetcher reads, present only if CBC ran first (never fatal)
    cbc_cpi = DATA / "economy" / "cpi_yoy_from_cbc.csv"
    if cbc_cpi.exists():
        print("  (CBC CPI y/y present on disk — compare in fetch_cbc.py)")
    if bad:
        raise FetchError("cross-checks failed:\n  " + "\n  ".join(bad))


# -------------------------------------------------------------------- output
def write(tables):
    for rel in sorted(tables):
        assert rel.rsplit(".csv", 1)[0].endswith("_from_dgbas"), \
            f"{rel}: a fetcher only writes sidecars"
        columns = collect.order[rel]
        path = DATA / rel
        header = ",".join(["year", *columns])
        if path.exists():
            first = next((ln for ln in path.read_text(encoding="utf-8")
                          .splitlines() if not ln.startswith("#")), "")
            if first != header:
                raise FetchError(f"refusing to overwrite {rel}: it holds "
                                 f"{first!r}, not this fetcher's sidecar")
        lines = [header]
        for year in sorted(tables[rel]):
            row = tables[rel][year]
            cells = []
            for c in columns:
                v = row.get(c)
                cells.append("" if v is None else
                             f"{v:.{collect.decimals[(rel, c)]}f}")
            if any(cells):
                lines.append(f"{year}," + ",".join(cells))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  data/{rel}  {len(lines) - 1} rows, {len(columns)} columns")


def write_quarterly():
    rel = "economy/gdp_growth_quarterly_from_dgbas.csv"
    path = DATA / rel
    lines = ["year,quarter,gdp_growth_yoy_pct"]
    for (year, q) in sorted(collect.quarterly_growth):
        # quarter is a LABEL (Q1..Q4), not a number: it is part of the row key
        # (year, quarter) so four quarters of one year are not read as four
        # duplicate-year rows by the data tests.
        lines.append(f"{year},Q{q},{collect.quarterly_growth[(year, q)]:.2f}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/{rel}  {len(lines) - 1} quarterly rows "
          "(annual-rate SA y/y; annual is NOT the sum of these)")


def main() -> None:
    print(f"DGBAS national-accounts spine for {NAME}")
    try:
        tables = collect()
        spot_checks(tables)
        cross_checks(tables)
    except FetchError as e:
        print(f"!! {e}\nNothing written.", file=sys.stderr)
        sys.exit(1)
    write(tables)
    write_quarterly()
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
