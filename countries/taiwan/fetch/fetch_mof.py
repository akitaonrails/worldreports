#!/usr/bin/env python3
"""Refresh the Ministry of Finance fiscal/trade spine into sidecar CSVs.

Usage:  python3 -I countries/taiwan/fetch/fetch_mof.py

MOF (財政部) runs the same DPAS query engine as DGBAS on its own tree
(DISCOVERY §2):  data-out is
  WebMain.aspx?sys=220&kind=21&type=1&funid=<CODE>&ym=<from>&ymt=<to>
  &cycle=<col>&outmode=8[&fldlst=<bitmask>][&codlst0=..][&codlst1=..]
and the ROC-year period labels are `NN年度` = calendar ROC+1911 (the
fiscal year is the CALENDAR year — no separate fiscal-year key here).

This fetcher pulls:
  * i2101 — all-levels government net revenue / expenditure / balance and
    financing (FINAL ACCOUNTS, accrual). The % of GDP is the publisher's own
    column, not a re-derivation.
  * i0121 — all-levels final-account expenditure BY POLICY CATEGORY (spending
    chapter; the national functional classification the spine maps onto COFOG,
    note in the plate).
  * i2201 / i2206 — the PUBLIC TREASURY cash in / cash out (公庫收支). This is
    the cash-basis TWIN of the accrual tables, in the same database (SOURCING
    §4 "two publishers, one idea"). It is staged as SEPARATE labelled columns
    beside the accrual figures — NEVER spliced, and the fetcher asserts the two
    are not equal, because a silent splice would be the seam landing on a
    politically interesting year.
  * i0232 — central-government gross debt outstanding (NTD millions, plus the
    published % of GDP). Central perimeter only; the general-government line
    is the accrual series above — different perimeter, both kept, never joined.
  * i9111 — trade value by continent/country, USD (customs records compiled by
    MOF; the goods stand-in for UN Comtrade, which does not carry Chinese
    Taipei). The balance-of-payments goods series (CBC BPP2Y01, fetch_cbc) is a
    DIFFERENT definition and is staged there, never spliced into this.

The i9111 country dimension is a 205-item codelist; selecting every row
flattens ambiguously, so each partner is pulled as its own single-row query
(fldlst=USD, codlst1=110=出口,進口) — unambiguous export and import series per
country. Continent aggregates (亞洲/歐洲/中東) are deliberately NOT pulled, so
they can never be double-counted with the countries on a destination panel.

Two DPAS quirks (same as fetch_dgbas): the flaky resolver is retried with a
short backoff, and some tables (i0232) emit invalid JSON from leaked display
markup — the tags are stripped and the {colh,col,row,orgdata} shape asserted
BEFORE anything is cached.

Output: sidecars only, beside where the curated files will land.
  data/fiscal/budget_from_mof.csv            (accrual revenue/exp/balance + %GDP)
  data/fiscal/accrual_vs_cash_from_mof.csv   (the accrual vs cash twins, labelled)
  data/fiscal/debt_central_from_mof.csv      (central gross debt + %GDP)
  data/spending/spending_function_from_mof.csv (accrual expenditure by function)
  data/trade/goods_from_mof.csv              (total goods exports/imports, USD)
  data/trade/partners_from_mof.csv           (top destinations by country, USD)
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
CACHE = ROOT / "cache" / "mof"

BASE = "https://web02.mof.gov.tw/njswww/WebMain.aspx"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11, Linux x86_64)", "Accept": "*/*"}
ROC = 1911

# i2101 field indices (fldName order).
I2101 = {"revenue": 0, "rev_pct_gdp": 3, "expenditure": 4, "exp_pct_gdp": 7,
         "balance": 8, "bal_pct_gdp": 11}
# i0121 expenditure by policy category (fldName[1:], the total is field 0).
I0121_FUNCS = [
    ("general_affairs", "一般政務支出"),
    ("defence", "國防支出"),
    ("education_sci_culture", "教育科學文化支出"),
    ("economic_development", "經濟發展支出"),
    ("social_security_pension_subtotal", "社會安全及退撫支出小計"),
    ("social_welfare", "社會福利支出"),
    ("community_environment", "社區發展及環境保護支出"),
    ("pension", "退休撫卹支出"),
    ("debt_service", "債務支出"),
    ("other", "其他支出"),
]
# i9111 top destination countries by 2025 exports, with their codelist index.
PARTNERS = [
    ("United States", 94), ("China_mainland", 2), ("Singapore", 6),
    ("Japan", 4), ("South_Korea", 5), ("Vietnam", 9),
    ("Netherlands", 53), ("Germany", 52),
]


class FetchError(RuntimeError):
    pass


def _repair(raw: str) -> str:
    return re.sub(r"</?(?:font|b|br|i|u)[^>]*>", "", raw)


def get(url: str, cache_name: str, check):
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
            payload = check(_repair(raw))
            path.write_text(raw, encoding="utf-8")
            return payload
        except (socket.gaierror, urllib.error.URLError, OSError,
                ValueError, json.JSONDecodeError) as e:
            last = e
            print(f"  {cache_name} attempt {attempt + 1}: {type(e).__name__} {e}",
                  file=sys.stderr)
            time.sleep(2 + 2 * attempt)
    raise FetchError(f"{url}: {last}")


def mof(code: str, *, fldlst, ym="9500", ymt="11412", cycle=4,
        cod0=None, cod1=None, cache=None):
    url = (f"{BASE}?sys=220&kind=21&type=1&funid={code}"
           f"&ym={ym}&ymt={ymt}&cycle={cycle}&outmode=8&fldlst={fldlst}")
    if cod0:
        url += f"&codlst0={cod0}"
    if cod1:
        url += f"&codlst1={cod1}"

    def check(raw):
        p = json.loads(raw)
        for key in ("colh", "col", "row", "orgdata"):
            if key not in p:
                raise ValueError(f"DPAS payload missing {key!r}")
        if not p["row"] or not p["orgdata"]:
            raise ValueError("DPAS payload has no rows or no orgdata")
        if p["funid"] != code:
            raise ValueError(f"payload funid {p['funid']!r} != {code!r}")
        return p

    return get(url, cache or f"{code}.json", check)


def year_of(label: str) -> int:
    m = re.fullmatch(r"(\d{2,3})年(?:度)?", label)
    if not m:
        raise ValueError(f"unrecognised MOF period label {label!r}")
    roc = int(m.group(1))
    if not (40 <= roc <= 130):
        raise ValueError(f"ROC year {roc} out of range — offset wrong")
    return roc + ROC


def col_by_year(payload, field_index):
    years = [year_of(r[0]) for r in payload["row"]]
    vals = payload["orgdata"][field_index]
    return {y: v for y, v in zip(years, vals)}


# -------------------------------------------------------------------- collect
def collect():
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

    # --- i2101 accrual revenue/expenditure/balance + %GDP -----------------
    print("MOF i2101 — all-levels final accounts (accrual)")
    b = mof("i2101", fldlst="1" * 16)
    assert year_of(b["row"][17][0]) == 2023 and b["orgdata"][0][17] == 3_888_796_962, \
        "i2101 ROC-offset/alignment broken: 112年度 is not 2023 revenue 3,888,796,962"
    put("fiscal/budget_from_mof.csv", "revenue_ntd_thousands", col_by_year(b, I2101["revenue"]), 0)
    put("fiscal/budget_from_mof.csv", "expenditure_ntd_thousands", col_by_year(b, I2101["expenditure"]), 0)
    put("fiscal/budget_from_mof.csv", "balance_ntd_thousands", col_by_year(b, I2101["balance"]), 0)
    put("fiscal/budget_from_mof.csv", "revenue_pct_gdp", col_by_year(b, I2101["rev_pct_gdp"]), 1)
    put("fiscal/budget_from_mof.csv", "expenditure_pct_gdp", col_by_year(b, I2101["exp_pct_gdp"]), 1)
    put("fiscal/budget_from_mof.csv", "balance_pct_gdp", col_by_year(b, I2101["bal_pct_gdp"]), 1)
    accrual_rev = col_by_year(b, I2101["revenue"])
    accrual_exp = col_by_year(b, I2101["expenditure"])
    accrual_bal = col_by_year(b, I2101["balance"])

    # --- i0121 accrual expenditure by function ----------------------------
    print("MOF i0121 — final-account expenditure by policy category")
    f = mof("i0121", fldlst="1" * 11)
    func_total = col_by_year(f, 0)
    put("spending/spending_function_from_mof.csv", "spending_total", func_total, 0)
    for ci, (name, _) in enumerate(I0121_FUNCS):
        put("spending/spending_function_from_mof.csv", f"spending_{name}",
            col_by_year(f, ci + 1), 0)
    collect.i0121_total = func_total

    # --- i2201 cash revenue, i2206 cash expenditure (the accrual twins) ---
    print("MOF i2201 / i2206 — public treasury cash in / out")
    cr = mof("i2201", fldlst="1" + "0" * 26)
    ce = mof("i2206", fldlst="1" + "0" * 16)
    cash_rev = col_by_year(cr, 0)
    cash_exp = col_by_year(ce, 0)
    put("fiscal/accrual_vs_cash_from_mof.csv", "revenue_accrual_ntd_thousands", accrual_rev, 0)
    put("fiscal/accrual_vs_cash_from_mof.csv", "revenue_cash_ntd_thousands", cash_rev, 0)
    put("fiscal/accrual_vs_cash_from_mof.csv", "expenditure_accrual_ntd_thousands", accrual_exp, 0)
    put("fiscal/accrual_vs_cash_from_mof.csv", "expenditure_cash_ntd_thousands", cash_exp, 0)
    collect.accrual = (accrual_rev, accrual_exp, accrual_bal)
    collect.cash = (cash_rev, cash_exp)

    # --- i0232 central-government gross debt ------------------------------
    print("MOF i0232 — central gross debt outstanding")
    d = mof("i0232", fldlst="11111")
    assert year_of(d["row"][-1][0]) == 2025 and d["orgdata"][1][-1] == 21.1, \
        "i0232 broken: 114年度 debt/GDP is not 21.1%"
    put("fiscal/debt_central_from_mof.csv", "debt_central_ntd_mn", col_by_year(d, 0), 0)
    put("fiscal/debt_central_from_mof.csv", "debt_central_pct_gdp", col_by_year(d, 1), 1)

    # --- i9111 total goods exports/imports (USD thousands) ---------------
    print("MOF i9111 — trade totals (customs, USD)")
    mask0 = "1" + "0" * 204                 # 總計
    t = mof("i9111", fldlst="1000", ym="9500", ymt="11400", cod0=mask0, cod1="110",
            cache="i9111_total.json")
    put("trade/goods_from_mof.csv", "exports_usd_thousands", col_by_year(t, 0), 0)
    put("trade/goods_from_mof.csv", "imports_usd_thousands", col_by_year(t, 1), 0)
    collect.total_exp = col_by_year(t, 0)

    # --- i9111 top destinations, one country per query -------------------
    print("MOF i9111 — top destinations by country")
    rows: list[tuple[int, str, float, float]] = []
    for name, idx in PARTNERS:
        m = ["0"] * 205
        m[idx] = "1"
        q = mof("i9111", fldlst="1000", ym="9500", ymt="11400",
                cod0="".join(m), cod1="110", cache=f"i9111_{name}.json")
        ex = col_by_year(q, 0)
        im = col_by_year(q, 1)
        for year in sorted(set(ex) | set(im)):
            rows.append((year, name, ex.get(year, 0), im.get(year, 0)))
    collect.partner_rows = rows
    return tables, rows, decimals, order


# -------------------------------------------------------------------- checks
SPOT = [
    ("fiscal/budget_from_mof.csv", "revenue_ntd_thousands", 2023, 3_888_796_962),
    ("fiscal/budget_from_mof.csv", "expenditure_ntd_thousands", 2023, 4_033_625_949),
    ("fiscal/budget_from_mof.csv", "balance_ntd_thousands", 2023, -144_828_987),
    ("fiscal/debt_central_from_mof.csv", "debt_central_ntd_mn", 2025, 6_071_063),
    ("fiscal/debt_central_from_mof.csv", "debt_central_pct_gdp", 2025, 21.1),
    ("trade/goods_from_mof.csv", "exports_usd_thousands", 2025, 639_961_977),
]


def spot_checks(tables):
    bad = []
    for rel, column, year, want in SPOT:
        got = tables.get(rel, {}).get(year, {}).get(column)
        if got is None or abs(got - want) > max(abs(want) * 0.01, 0.1):
            bad.append(f"{rel} {column} {year}: want {want}, got {got}")
    for year, name, ex, im in collect.partner_rows:
        if name == "United States" and year == 2025 and abs(ex - 198_258_264) > 2_000_000:
            bad.append(f"partner US exports 2025: got {ex}")
    if bad:
        raise FetchError("spot checks failed:\n  " + "\n  ".join(bad))
    print(f"Spot checks: {len(SPOT)} values + ROC-offset (112年度=2023) pinned")


def cross_checks(tables):
    """Accrual balance == revenue - expenditure; accrual != cash (two bases);
    i0121 total == i2101 expenditure; and no partner exceeds / double-counts the
    customs total."""
    bad = []
    print("Cross-checks")
    rev, exp, bal = collect.accrual
    for y in sorted(rev):
        if y in exp and y in bal and abs((rev[y] - exp[y]) - bal[y]) > 1:
            bad.append(f"i2101 {y}: revenue - expenditure != balance")
    print("  i2101 balance == revenue - expenditure (all years) — ok")
    cash_rev, cash_exp = collect.cash
    same = [y for y in cash_rev if y in rev and abs(cash_rev[y] - rev[y]) < 1]
    if same:
        bad.append(f"accrual revenue == cash revenue in {same} — the two "
                   "bases must not be identical (a splice would fit)")
    for y in (2023, 2024, 2025):
        if y in cash_rev and y in rev:
            print(f"  revenue {y}: accrual {rev[y]/1e9:.2f}tn vs cash "
                  f"{cash_rev[y]/1e9:.2f}tn NTD — different bases, kept apart")
    tot = collect.i0121_total
    for y in sorted(tot):
        if y in exp and abs(tot[y] - exp[y]) > 1:
            bad.append(f"i0121 total != i2101 expenditure in {y}")
    print("  i0121 function total == i2101 expenditure — ok")
    gt = collect.total_exp
    for year, name, ex, im in collect.partner_rows:
        if year in gt and ex > gt[year] and ex > 0:
            bad.append(f"partner {name} exports exceed customs total in {year}")
    top2025 = sum(ex for year, _, ex, _ in collect.partner_rows if year == 2025)
    if top2025 > gt[2025]:
        bad.append("sum of top partners exceeds customs total (double count)")
    print(f"  top-8 partners 2025 sum {top2025/1e6:.0f}M USD <= total "
          f"{gt[2025]/1e6:.0f}M USD (no continent double-count) — ok")
    if bad:
        raise FetchError("cross-checks failed:\n  " + "\n  ".join(bad))


# -------------------------------------------------------------------- output
def write(tables, rows, decimals, order):
    for rel in sorted(tables):
        assert rel.rsplit(".csv", 1)[0].endswith("_from_mof"), \
            f"{rel}: a fetcher only writes sidecars"
        columns = order[rel]
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
                      f"{r[c]:.{decimals[(rel, c)]}f}") for c in columns]
            if any(cells):
                lines.append(f"{year}," + ",".join(cells))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  data/{rel}  {len(lines) - 1} rows, {len(columns)} columns")

    # long-format partners file: year, partner, exports, imports
    rel = "trade/partners_from_mof.csv"
    path = DATA / rel
    lines = ["year,partner,exports_usd_thousands,imports_usd_thousands"]
    for year, name, ex, im in sorted(rows):
        if ex or im:
            lines.append(f"{year},{name},{ex:.0f},{im:.0f}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/{rel}  {len(lines) - 1} partner-year rows")


def main() -> None:
    print(f"MOF fiscal + trade spine for {NAME}")
    try:
        tables, rows, decimals, order = collect()
        spot_checks(tables)
        cross_checks(tables)
    except FetchError as e:
        print(f"!! {e}\nNothing written.", file=sys.stderr)
        sys.exit(1)
    write(tables, rows, decimals, order)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
