#!/usr/bin/env python3
"""Refresh the Central Bank (CBC) statistics database into sidecar CSVs.

Usage:  python3 -I countries/taiwan/fetch/fetch_cbc.py

The Central Bank of the Republic of China (Taiwan) carries the whole
markets / credit / reserves spine (DISCOVERY §3). The legacy
www.cbc.gov.tw/opendata JSON API is dead (302s to the homepage); the live
carrier is the statistics database at cpx.cbc.gov.tw, every table of which
has a keyless JSON endpoint:

    https://cpx.cbc.gov.tw/api/dataapi/Get?FileName=<CODE>      (CODE w/o .px)

The payload is PCAxis-flavoured:
    {meta:{title,sender,units,last_updated,...},
     data:{structure:{Table1:[{data:"col name"},...]}, dataSets:[[row...]]}}
Two parser facts the code enforces:

  * MISSING VALUES ARE THE STRING "-". They map to blank (None), NEVER to 0 —
    a "-" read as zero would draw a policy-rate or reserve collapse that never
    happened (SOURCING "a missing year is missing").
  * a table's dataSets rows are WIDER than Table1's column list whenever the
    table interleaves a growth-rate (%) column after each level. EG2AM01 /
    EG51M01 / EF07M01 / BPP2Y01 have len(row)-1 == ncols (no growth columns);
    EG27Y01 / EF99Y01 have len(row)-1 == 2*ncols (a "%" after every level).
    The value column is therefore at cell 1+col for the first kind and 1+2*col
    for the second. get() asserts the width is one of those two, so a shape
    change fails rather than silently reading a growth column as a level.

Period codes are CE-native (annual `2024`, monthly `2024M12`) — no ROC offset
here (the DPAS engines carry that; see fetch_dgbas/fetch_mof). The spots below
pin the CE mapping anyway: EG27Y01 2024 = 21,382.78, EG51M01 2026M08 = 31.666.

Annualisation follows the spine, not a blanket rule:
  * a stock or rate read once a year (policy rate, reserves, NPL, CPI y/y)
    takes its DECEMBER observation (period-end) — a point reading, not a mean;
  * the exchange rate for the currency panel takes the ANNUAL MEAN of the
    monthly interbank closing (the spine's slot 3 is an annual average), and
    that mean is cross-checked against DGBAS's own average exchange rate;
  * EG27Y01's index column is the ANNUAL AVERAGE (labelled as such — it is
    NOT the year-end close; the Yahoo year-end in fetch_markets is a DIFFERENT
    quantity and the two are never spliced).

Output: sidecars only.
  data/markets/policy_rate_from_cbc.csv      (EG2AM01 rediscount rate, Dec)
  data/markets/usdtwd_from_cbc.csv           (EG51M01 interbank close, annual mean)
  data/markets/stock_index_avg_from_cbc.csv  (EG27Y01 index, ANNUAL AVERAGE)
  data/world/reserves_from_cbc.csv           (EF07M01 FX reserves mn USD, Dec)
  data/credit/npl_from_cbc.csv               (EF07M01 bank NPL ratio, Dec)
  data/economy/cpi_yoy_from_cbc.csv          (EF07M01 CPI y/y, Dec — cross-check)
  data/credit/household_credit_from_cbc.csv  (EF99Y01 consumer + building loans)
  data/world/bop_goods_from_cbc.csv          (BPP2Y01 current acct + goods BoP)
"""
from __future__ import annotations

import json
import re
import socket
import statistics
import sys
import time
import urllib.request
from pathlib import Path

NAME = "Taiwan"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "cbc"

API = "https://cpx.cbc.gov.tw/api/dataapi/Get?FileName={code}"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11, Linux x86_64)", "Accept": "*/*"}
FIRST, LAST = 2006, 2025      # the plate window; annual sidecars stop at last_full_year


class FetchError(RuntimeError):
    pass


def _num(v):
    """A CBC cell -> float, with the missing sentinel '-' mapped to blank."""
    if v is None:
        return None
    v = v.strip()
    if v in ("", "-"):
        return None
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return None


def get(code: str):
    """A PCAxis payload, shape-checked BEFORE caching, DNS-retried."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{code}.json"

    def check(raw):
        p = json.loads(raw)
        try:
            cols = [c["data"] for c in p["data"]["structure"]["Table1"]]
            rows = p["data"]["dataSets"]
        except (KeyError, TypeError) as e:
            raise ValueError(f"not a PCAxis payload: missing {e}")
        if not cols or not rows:
            raise ValueError("empty Table1/dataSets")
        width = len(rows[0]) - 1
        if width not in (len(cols), 2 * len(cols)):
            raise ValueError(f"dataSets width {width} not ncols({len(cols)}) "
                             f"or 2x — table shape changed")
        if p["meta"].get("filename") not in (None, f"{code}.px"):
            raise ValueError(f"meta.filename {p['meta'].get('filename')} "
                             f"!= {code}.px")
        return p

    if path.exists():
        try:
            return check(path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache {code}: {e}", file=sys.stderr)
            path.unlink()
    last: Exception | None = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(API.format(code=code), headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read().decode("utf-8", "replace")
            payload = check(raw)
            path.write_text(raw, encoding="utf-8")
            return payload
        except (socket.gaierror, urllib.error.URLError, OSError,
                ValueError, json.JSONDecodeError) as e:
            last = e
            print(f"  {code} attempt {attempt + 1}: {type(e).__name__} {e}",
                  file=sys.stderr)
            time.sleep(2 + 2 * attempt)
    raise FetchError(f"{code}: {last}")


def col_index(cols, name):
    hit = [i for i, c in enumerate(cols) if c == name]
    if not hit:
        raise FetchError(f"column {name!r} not in {cols}")
    return hit[0]


def table(code):
    """-> (cols, cell_for(colidx), {period: [value-per-column]})."""
    p = get(code)
    cols = [c["data"] for c in p["data"]["structure"]["Table1"]]
    interleaved = (len(p["data"]["dataSets"][0]) - 1) == 2 * len(cols)
    cell = (lambda i: 1 + 2 * i) if interleaved else (lambda i: 1 + i)
    out = {}
    for r in p["data"]["dataSets"]:
        out[r[0]] = [_num(r[cell(i)]) for i in range(len(cols))]
    return cols, out


def annual(code, col_name):
    """{CE year: value} for an ANNUAL-period table."""
    cols, t = table(code)
    ci = col_index(cols, col_name)
    out = {}
    for per, vals in t.items():
        if re.fullmatch(r"\d{4}", per) and FIRST <= int(per) <= LAST:
            out[int(per)] = vals[ci]
    return out


def dec(code, col_name):
    """{CE year: December observation} for a MONTHLY table (period-end)."""
    cols, t = table(code)
    ci = col_index(cols, col_name)
    out = {}
    for per, vals in t.items():
        m = re.fullmatch(r"(\d{4})M12", per)
        if m and FIRST <= int(m.group(1)) <= LAST:
            out[int(m.group(1))] = vals[ci]
    return out


def fx_annual_mean():
    """{CE year: annual mean of the monthly interbank closing USD/TWD}."""
    cols, t = table("EG51M01")
    ci = col_index(cols, "美元即期匯率-銀行間收盤匯率")
    out = {}
    for y in range(FIRST, LAST + 1):
        vals = [t[f"{y}M{m:02d}"][ci] for m in range(1, 13)
                if f"{y}M{m:02d}" in t]
        vals = [v for v in vals if v is not None]
        if len(vals) >= 6:
            out[y] = statistics.mean(vals)
    return out


# -------------------------------------------------------------------- collect
def collect():
    tables = {}
    decimals = {}
    order = {}

    def put(rel, column, series, dec):
        if not series:
            raise FetchError(f"{rel}: {column} came back empty")
        t = tables.setdefault(rel, {})
        for year, v in series.items():
            t.setdefault(year, {})[column] = v
        decimals[(rel, column)] = dec
        order.setdefault(rel, []).append(column)

    print("CBC EG2AM01 — policy rate (rediscount)")
    put("markets/policy_rate_from_cbc.csv", "rediscount_rate_pct",
        dec("EG2AM01", "重貼現率"), 3)
    print("CBC EG51M01 — USD/TWD interbank close (annual mean)")
    put("markets/usdtwd_from_cbc.csv", "usd_twd_interbank_annual_mean",
        fx_annual_mean(), 4)
    print("CBC EG27Y01 — stock index, ANNUAL AVERAGE (not year-end)")
    put("markets/stock_index_avg_from_cbc.csv", "taiex_annual_average",
        annual("EG27Y01", "加權平均股價指數"), 2)
    print("CBC EF07M01 — reserves / NPL / CPI y/y (Dec)")
    put("world/reserves_from_cbc.csv", "fx_reserves_usd_mn",
        dec("EF07M01", "外匯存底(百萬美元)"), 0)
    put("credit/npl_from_cbc.csv", "bank_npl_ratio_pct",
        dec("EF07M01", "本國銀行逾放比率"), 2)
    put("economy/cpi_yoy_from_cbc.csv", "cpi_yoy_pct",
        dec("EF07M01", "消費者物價指數年增率"), 2)
    print("CBC EF99Y01 — consumer + building loans")
    put("credit/household_credit_from_cbc.csv", "consumer_loans_ntd_mn",
        annual("EF99Y01", "消費者貸款-小計"), 0)
    put("credit/household_credit_from_cbc.csv", "building_loans_ntd_mn",
        annual("EF99Y01", "建築貸款"), 0)
    print("CBC BPP2Y01 — balance of payments (goods, current account)")
    put("world/bop_goods_from_cbc.csv", "current_account_usd_mn",
        annual("BPP2Y01", "經常帳-淨額"), 0)
    put("world/bop_goods_from_cbc.csv", "bop_goods_exports_usd_mn",
        annual("BPP2Y01", "商品-收入"), 0)
    put("world/bop_goods_from_cbc.csv", "bop_goods_imports_usd_mn",
        annual("BPP2Y01", "商品-支出"), 0)
    collect.decimals = decimals
    collect.order = order
    return tables


# -------------------------------------------------------------------- checks
SPOT = [
    ("markets/policy_rate_from_cbc.csv", "rediscount_rate_pct", 2020, 1.125),
    ("markets/policy_rate_from_cbc.csv", "rediscount_rate_pct", 2025, 2.0),
    ("markets/stock_index_avg_from_cbc.csv", "taiex_annual_average", 2024, 21382.78),
    ("markets/usdtwd_from_cbc.csv", "usd_twd_interbank_annual_mean", 2025, 31.2598),
    ("world/reserves_from_cbc.csv", "fx_reserves_usd_mn", 2025, 602553),
    ("credit/household_credit_from_cbc.csv", "consumer_loans_ntd_mn", 2025, 13_531_340),
    ("world/bop_goods_from_cbc.csv", "bop_goods_exports_usd_mn", 2025, 583736),
]


def spot_checks(tables):
    bad = []
    for rel, column, year, want in SPOT:
        got = tables.get(rel, {}).get(year, {}).get(column)
        if got is None or abs(got - want) > max(abs(want) * 0.005, 0.01):
            bad.append(f"{rel} {column} {year}: want {want}, got {got}")
    if bad:
        raise FetchError("spot checks failed:\n  " + "\n  ".join(bad))
    # '-' -> blank, never 0: confirm a gap stayed blank, not zero.
    npl = tables["credit/npl_from_cbc.csv"]
    if any((v.get("bank_npl_ratio_pct") == 0.0) for v in npl.values()):
        raise FetchError("an NPL cell read as 0.0 — the '-' sentinel leaked a zero")
    print(f"Spot checks: {len(SPOT)} values pinned; '-'->blank held "
          "(no spurious zeros)")


def cross_checks(tables):
    """Named cross-checks the discovery pass promised. Cross-fetcher reads are
    present only if the partner ran first, and are PRINTED (they are different
    definitions, so they are never a tight equality)."""
    print("Cross-checks")
    fx = tables["markets/usdtwd_from_cbc.csv"]
    dgbas = DATA / "economy" / "gdp_from_dgbas.csv"
    if dgbas.exists():
        import csv as _csv
        rows = {int(r["year"]): r for r in _csv.DictReader(
            ln for ln in dgbas.read_text(encoding="utf-8").splitlines()
            if not ln.startswith("#"))}
        for y in (2024, 2025):
            if y in fx and rows.get(y, {}).get("avg_fx_ntd_per_usd"):
                d = float(rows[y]["avg_fx_ntd_per_usd"])
                c = fx[y]["usd_twd_interbank_annual_mean"]
                print(f"  FX {y}: CBC interbank mean {c:.3f} vs DGBAS avg "
                      f"{d:.3f} — {abs(c-d)/d*100:.2f}% apart")
    # MOF customs goods vs CBC BoP goods: two DEFINITIONS, printed not asserted.
    mof = DATA / "trade" / "goods_from_mof.csv"
    bop = tables["world/bop_goods_from_cbc.csv"]
    if mof.exists():
        import csv as _csv
        r = {int(x["year"]): x for x in _csv.DictReader(
            ln for ln in mof.read_text(encoding="utf-8").splitlines()
            if not ln.startswith("#"))}
        for y in (2024, 2025):
            if y in bop and r.get(y):
                cust = int(r[y]["exports_usd_thousands"]) / 1000.0
                b = bop[y]["bop_goods_exports_usd_mn"]
                print(f"  goods exports {y}: MOF customs {cust:,.0f} vs CBC "
                      f"BoP {b:,.0f} US$mn — customs vs BoP definitions, "
                      "kept apart (never spliced)")
    # reserves band sanity (the brief's 'among the world's largest')
    res = tables["world/reserves_from_cbc.csv"]
    vals = [v["fx_reserves_usd_mn"] for v in res.values() if v.get("fx_reserves_usd_mn")]
    lo, hi = min(vals) / 1e3, max(vals) / 1e3
    if not (250 <= lo and hi <= 800):
        raise FetchError(f"reserves out of band: {lo:.0f}-{hi:.0f} bn USD")
    print(f"  FX reserves {lo:.0f}-{hi:.0f} bn USD (2006 low -> 2025 high) "
          "— among the world's largest")
    # CPI y/y (CBC) vs DGBAS annual inflation, printed (different cuts).
    cpi_cbc = tables["economy/cpi_yoy_from_cbc.csv"]
    dgb_cpi = DATA / "economy" / "cpi_from_dgbas.csv"
    if dgb_cpi.exists():
        import csv as _csv
        rr = {int(x["year"]): x for x in _csv.DictReader(
            ln for ln in dgb_cpi.read_text(encoding="utf-8").splitlines()
            if not ln.startswith("#"))}
        for y in (2024,):
            if y in cpi_cbc and rr.get(y, {}).get("cpi_inflation_pct"):
                print(f"  CPI y/y {y}: CBC Dec {cpi_cbc[y]['cpi_yoy_pct']:.2f} "
                      f"vs DGBAS annual {float(rr[y]['cpi_inflation_pct']):.2f} "
                      "— monthly point vs annual mean, both kept")


def write(tables):
    for rel in sorted(tables):
        assert rel.rsplit(".csv", 1)[0].endswith("_from_cbc"), \
            f"{rel}: a fetcher only writes sidecars"
        columns = collect.order[rel]
        path = DATA / rel
        header = ",".join(["year", *columns])
        if path.exists():
            first = next((ln for ln in path.read_text(encoding="utf-8")
                          .splitlines() if not ln.startswith("#")), "")
            if first != header:
                raise FetchError(f"refusing to overwrite {rel}: it holds {first!r}")
        lines = [header]
        for year in sorted(tables[rel]):
            r = tables[rel][year]
            cells = [("" if r.get(c) is None else
                      f"{r[c]:.{collect.decimals[(rel, c)]}f}") for c in columns]
            if any(cells):
                lines.append(f"{year}," + ",".join(cells))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  data/{rel}  {len(lines) - 1} rows, {len(columns)} columns")


def main() -> None:
    print(f"Central Bank (CBC) spine for {NAME}")
    try:
        tables = collect()
        spot_checks(tables)
        cross_checks(tables)
    except FetchError as e:
        print(f"!! {e}\nNothing written.", file=sys.stderr)
        sys.exit(1)
    write(tables)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
