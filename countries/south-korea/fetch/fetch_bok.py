#!/usr/bin/env python3
"""Fetch official annual series from the Bank of Korea (ECOS open API).

ECOS is authoritative — it is the Bank of Korea's own statistics system, and
it republishes Korea Customs Service trade and Statistics Korea population
figures alongside its national accounts — but unlike Brazil's SGS it is
key-gated. Two ways in:

  BOK_API_KEY=<your key>   a free key from https://ecos.bok.or.kr/api/
                           (no row limit)
  (unset)                  the public "sample" key, which works for every
                           endpoint but serves at most 10 rows per request

The sample key is enough for everything here: the longest series is a
250-month exchange-rate history, which is 25 paged requests. Every response
is cached under cache/, so a re-run only fetches what is missing and an
upstream outage leaves the committed CSVs untouched.

Series used (all official BOK/ECOS):
  200Y113  national accounts, nominal, annual   — GDP, gross fixed capital
  200Y110  national accounts, real, annual      — real GDP (chained) -> growth
  200Y152  general government expenditure by COFOG function
  200Y153  general government total revenue, expenditure, net lending
  722Y001  BOK base rate (0101000)
  731Y006  KRW/USD monthly close (0000003)
  732Y001  foreign exchange reserves, total (99)
  311Y001  international investment position — assets (1000000), liabilities (2000000)
  901Y009  consumer price index, all items (0)
  901Y027  economically active population — unemployment rate (I61BC)
  901Y028  projected population / elderly share / total fertility rate
  901Y081  total tax revenue (G2A)
  901Y092  exports and imports by commodity nature — totals incl. partial year
  901Y121  exports and imports by country

Outputs (curated CSVs; these series involve no hand-picked methodology, so
the fetcher owns them outright):
  data/macro/gdp.csv            year,nominal_krw_tn,real_growth,gdp_per_capita_usd,population_mn
  data/macro/cpi.csv            year,value
  data/macro/base_rate.csv      year,value
  data/macro/won.csv            year,avg,eop
  data/macro/reserves.csv       year,eop_usbi
  data/macro/external.csv       year,assets_usbi,liabilities_usbi,net_usbi
  data/macro/unemployment.csv   year,value
  data/fiscal/government.csv    year,revenue,expenditure,balance   (% of GDP)
  data/fiscal/tax_burden.csv    year,value                         (% of GDP)
  data/fiscal/investment.csv    year,gfcf_krw_tn,gfcf_pct_gdp
  data/fiscal/spending_by_function.csv      % of GDP, by COFOG function
  data/fiscal/spending_by_function_krw.csv  the same in trillion won
  data/trade/trade.csv          year,exports,imports,balance       (US$ bn)
  data/trade/destinations.csv   year,destiny,share_pct
  data/social/population.csv    year,pop_mn,elderly_pct,tfr        (to 2072)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
DATA = ROOT / "data"
CACHE.mkdir(exist_ok=True)

BASE = "https://ecos.bok.or.kr/api"
KEY = os.environ.get("BOK_API_KEY", "sample")
# The sample key refuses a window wider than 10 rows; a real key does not.
PAGE = 10 if KEY == "sample" else 1000

YEAR_FROM, YEAR_TO = 2005, 2026
LAST_FULL_YEAR = 2025

# Trade partners drawn on plate 04, in the order the panel lists them.
PARTNERS = {"CN": "China", "US": "United States", "VN": "Vietnam",
            "JP": "Japan"}

# COFOG functions, ECOS code -> our column name. Everything not named here
# falls into `other`, which is computed as the published total minus these.
FUNCTIONS = {
    "110": "social_protection",
    "107": "health",
    "109": "education",
    "104": "economic_affairs",
    "101": "general_public",
    "102": "defence",
    "103": "public_order",
}
TOTAL_FUNCTION = "201"


def _get(url: str) -> dict | None:
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"    retry {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    return None


def search(stat: str, cycle: str, t0: str, t1: str, *items: str) -> dict[str, float]:
    """One ECOS series as {period: value}, paged and cached.

    Rows are keyed by period rather than appended to a list: a paged read can
    overlap at the seams when the gateway's own total count disagrees with
    what it serves, and a duplicated year would otherwise be counted twice by
    anything that sums.
    """
    tag = "_".join([stat, cycle, t0, t1, *items])
    cache_file = CACHE / f"ecos_{tag}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    out: dict[str, float] = {}
    start = 1
    while start < 2000:
        url = "/".join([BASE, "StatisticSearch", KEY, "json", "kr",
                        str(start), str(start + PAGE - 1), stat, cycle,
                        t0, t1, *items])
        payload = _get(url)
        if not payload:
            break
        block = payload.get("StatisticSearch")
        if not block:
            if start == 1:
                msg = payload.get("RESULT", {}).get("MESSAGE", "?")
                print(f"  ! {tag}: {msg[:90]}", file=sys.stderr)
            break
        for row in block["row"]:
            value = row.get("DATA_VALUE")
            if value not in (None, "", "-"):
                out[row["TIME"]] = float(value)
        if len(block["row"]) < PAGE or len(out) >= int(block["list_total_count"]):
            break
        start += PAGE
    cache_file.write_text(json.dumps(out))
    return out


def annual(series: dict[str, float]) -> dict[int, float]:
    return {int(k): v for k, v in series.items() if len(k) == 4}


def by_year_monthly(series: dict[str, float]) -> dict[int, list[tuple[int, float]]]:
    """{year: [(month, value), ...]} in month order."""
    out: dict[int, list[tuple[int, float]]] = {}
    for period, value in series.items():
        if len(period) != 6:
            continue
        out.setdefault(int(period[:4]), []).append((int(period[4:]), value))
    for values in out.values():
        values.sort()
    return out


def write(rel: str, header: str, rows: list[str]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *rows]) + "\n")
    print(f"  -> data/{rel}")


def fmt(value: float | None, dec: int = 2) -> str:
    return "" if value is None else f"{value:.{dec}f}"


def main() -> None:  # noqa: C901 — one block per output file, read top to bottom
    print(f"Fetching Bank of Korea ECOS series (key: "
          f"{'BOK_API_KEY' if KEY != 'sample' else 'public sample'})...")

    years = list(range(2006, YEAR_TO + 1))

    # ---- national accounts ------------------------------------------------
    # ECOS serves the nominal accounts in 십억원 (billion won); the plates and
    # the site read trillions, which is the unit Korean coverage uses.
    gdp_bn = annual(search("200Y113", "A", "2005", "2026", "10106"))
    gfcf_bn = annual(search("200Y113", "A", "2005", "2026", "10109"))
    real_gdp = annual(search("200Y110", "A", "2005", "2026", "10601"))
    population = annual(search("901Y028", "A", "2000", "2072", "I35A"))
    elderly = annual(search("901Y028", "A", "2000", "2072", "I35D"))
    tfr = annual(search("901Y028", "A", "2000", "2026", "I35E"))

    # ---- exchange rate ----------------------------------------------------
    # 731Y006/0000003 is the 15:30 close. The annual average is the mean of
    # the monthly closes, and `eop` is December's — not the last row served,
    # which is only December by luck of ordering.
    won_m = by_year_monthly(search("731Y006", "M", "200601", "202610", "0000003"))
    won_avg, won_eop = {}, {}
    for year, values in won_m.items():
        won_avg[year] = sum(v for _, v in values) / len(values)
        won_eop[year] = values[-1][1]

    rows = []
    for y in years:
        gdp_tn = gdp_bn.get(y, 0) / 1000 or None
        pop_mn = population.get(y, 0) / 1e6 or None
        percap = None
        if gdp_tn and pop_mn and won_avg.get(y):
            # trillion won -> won, / people, / won-per-dollar
            percap = gdp_tn * 1e12 / (pop_mn * 1e6) / won_avg[y]
        growth = None
        if y in real_gdp and (y - 1) in real_gdp:
            growth = (real_gdp[y] / real_gdp[y - 1] - 1) * 100
        rows.append(f"{y},{fmt(gdp_tn, 1)},{fmt(growth, 1)},"
                    f"{'' if percap is None else f'{percap:.0f}'},{fmt(pop_mn, 2)}")
    write("macro/gdp.csv",
          "year,nominal_krw_tn,real_growth,gdp_per_capita_usd,population_mn", rows)

    write("macro/won.csv", "year,avg,eop",
          [f"{y},{fmt(won_avg.get(y))},{fmt(won_eop.get(y))}" for y in years])

    # ---- consumer prices --------------------------------------------------
    # The index is published on a 2020=100 base; the plates show the annual
    # change, computed from the index rather than taken from a second series
    # so the two can never disagree.
    cpi_index = annual(search("901Y009", "A", "2005", "2026", "0"))
    cpi = {}
    for y in years:
        if y in cpi_index and (y - 1) in cpi_index:
            cpi[y] = (cpi_index[y] / cpi_index[y - 1] - 1) * 100
    write("macro/cpi.csv", "year,value",
          [f"{y},{fmt(cpi.get(y))}" for y in years])

    # ---- policy rate ------------------------------------------------------
    # Year-end level, which is what a reader comparing it to inflation wants;
    # the annual series ECOS also publishes is an average over the year.
    rate_m = by_year_monthly(search("722Y001", "M", "200601", "202610", "0101000"))
    write("macro/base_rate.csv", "year,value",
          [f"{y},{fmt(rate_m[y][-1][1]) if rate_m.get(y) else ''}"
           for y in years])

    # ---- reserves ---------------------------------------------------------
    # Published in thousands of US dollars; the panel reads billions.
    res_m = by_year_monthly(search("732Y001", "M", "200601", "202609", "99"))
    write("macro/reserves.csv", "year,eop_usbi",
          [f"{y},{fmt(res_m[y][-1][1] / 1e6) if res_m.get(y) else ''}"
           for y in years])

    # ---- international investment position --------------------------------
    # Reserves are only the state's share of what Korea owns abroad. The IIP
    # is the whole country's balance sheet, and it crossed zero in 2014:
    # Korea stopped being a net debtor to the rest of the world and is now a
    # net creditor on the order of a trillion dollars. Net is computed here
    # rather than read, because ECOS publishes only the two sides.
    iip_a = annual(search("311Y001", "A", "2005", "2026", "1000000"))
    iip_l = annual(search("311Y001", "A", "2005", "2026", "2000000"))
    rows = []
    for y in years:
        a, l = iip_a.get(y), iip_l.get(y)
        net = "" if a is None or l is None else fmt((a - l) / 1000, 1)
        rows.append(f"{y},{fmt(a / 1000, 1) if a is not None else ''},"
                    f"{fmt(l / 1000, 1) if l is not None else ''},{net}")
    write("macro/external.csv",
          "year,assets_usbi,liabilities_usbi,net_usbi", rows)

    # ---- unemployment -----------------------------------------------------
    # The annual series stops at the last complete year; 2026 is the mean of
    # the months published so far, and the plate marks it partial.
    unemp = annual(search("901Y027", "A", "2005", "2026", "I61BC"))
    unemp_m = by_year_monthly(search("901Y027", "M", "200601", "202609", "I61BC"))
    for year, values in unemp_m.items():
        if year not in unemp:
            unemp[year] = sum(v for _, v in values) / len(values)
    write("macro/unemployment.csv", "year,value",
          [f"{y},{fmt(unemp.get(y), 1)}" for y in years])

    # ---- general government ----------------------------------------------
    # 저축투자차액 (net lending/borrowing) is the SNA balance. It is a wider
    # measure than Korea's own headline 관리재정수지, and the two must not be
    # read as the same number — see data/SOURCES.yaml.
    revenue = annual(search("200Y153", "A", "2005", "2026", "1", "1401"))
    expense = annual(search("200Y153", "A", "2005", "2026", "1", "1400"))
    balance = annual(search("200Y153", "A", "2005", "2026", "1", "1309"))

    def pct_gdp(table: dict[int, float], year: int) -> float | None:
        base = gdp_bn.get(year)
        return None if not base or year not in table else table[year] / base * 100

    write("fiscal/government.csv", "year,revenue,expenditure,balance",
          [f"{y},{fmt(pct_gdp(revenue, y))},{fmt(pct_gdp(expense, y))},"
           f"{fmt(pct_gdp(balance, y))}" for y in years])

    # ---- tax burden -------------------------------------------------------
    # 조세총액 is published in 억원 (hundred-million won); nominal GDP is in
    # 십억원, so the ratio needs the factor of 10 between them.
    tax = annual(search("901Y081", "A", "2005", "2026", "G2A"))
    write("fiscal/tax_burden.csv", "year,value",
          [f"{y},{fmt(tax[y] / 10 / gdp_bn[y] * 100) if y in tax and y in gdp_bn else ''}"
           for y in years])

    # ---- investment -------------------------------------------------------
    write("fiscal/investment.csv", "year,gfcf_krw_tn,gfcf_pct_gdp",
          [f"{y},{fmt(gfcf_bn[y] / 1000, 1) if y in gfcf_bn else ''},"
           f"{fmt(pct_gdp(gfcf_bn, y))}" for y in years])

    # ---- spending by COFOG function --------------------------------------
    funcs = {code: annual(search("200Y152", "A", "2005", "2026", "1112", code))
             for code in [*FUNCTIONS, TOTAL_FUNCTION]}
    cols = list(FUNCTIONS.values())
    head = "year," + ",".join([*cols, "other", "total"])
    pct_rows, krw_rows = [], []
    for y in years:
        total = funcs[TOTAL_FUNCTION].get(y)
        named = [funcs[c].get(y) for c in FUNCTIONS]
        if total is None or any(v is None for v in named):
            blank = f"{y}" + "," * (len(cols) + 2)
            pct_rows.append(blank)
            krw_rows.append(blank)
            continue
        other = total - sum(named)
        values = [*named, other, total]
        base = gdp_bn.get(y)
        pct_rows.append(f"{y}," + ",".join(
            fmt(v / base * 100) if base else "" for v in values))
        krw_rows.append(f"{y}," + ",".join(f"{v / 1000:.1f}" for v in values))
    write("fiscal/spending_by_function.csv", head, pct_rows)
    write("fiscal/spending_by_function_krw.csv", head, krw_rows)

    # ---- trade ------------------------------------------------------------
    # 901Y092's annual row for a year still running is the cumulative total of
    # the months published so far, not a projection: for 2026 it is Jan-Sep.
    exports = annual(search("901Y092", "A", "2005", "2026", "E100"))
    imports = annual(search("901Y092", "A", "2005", "2026", "I100"))
    rows = []
    for y in years:
        e = exports.get(y, 0) / 1e6 or None
        i = imports.get(y, 0) / 1e6 or None
        bal = None if e is None or i is None else e - i
        rows.append(f"{y},{fmt(e, 1)},{fmt(i, 1)},{fmt(bal, 1)}")
    write("trade/trade.csv", "year,exports,imports,balance", rows)

    # ---- export destinations ---------------------------------------------
    dest = {code: annual(search("901Y121", "A", "2005", "2026", "T002", code))
            for code in PARTNERS}
    rows = []
    for y in years:
        total = exports.get(y)
        if not total:
            continue
        for code, name in PARTNERS.items():
            value = dest[code].get(y)
            if value is not None:
                rows.append(f"{y},{name},{value / total * 100:.1f}")
    write("trade/destinations.csv", "year,destiny,share_pct", rows)

    # ---- household credit -------------------------------------------------
    # 가계신용 is the headline measure: household loans plus 판매신용, the
    # credit extended by card issuers and retailers. It is a stock at
    # year-end, so the ratio to GDP divides a stock by a flow — the standard
    # presentation, and the reason the level reads above 100% at its peak.
    credit = annual(search("151Y001", "A", "2005", "2026", "1000000"))
    loans = annual(search("151Y001", "A", "2005", "2026", "1100000"))
    card = annual(search("151Y001", "A", "2005", "2026", "1200000"))
    rows = []
    for y in years:
        base = gdp_bn.get(y)
        rows.append(
            f"{y},{fmt(credit[y] / 1000, 1) if y in credit else ''},"
            f"{fmt(loans[y] / 1000, 1) if y in loans else ''},"
            f"{fmt(card[y] / 1000, 1) if y in card else ''},"
            f"{fmt(credit[y] / base * 100) if y in credit and base else ''}")
    write("macro/household_credit.csv",
          "year,credit_krw_tn,loans_krw_tn,card_krw_tn,credit_pct_gdp", rows)

    # ---- the price of that credit, and who stops paying -------------------
    # Rates are new-business averages at deposit banks; the delinquency rate
    # is the share of bank loan balances overdue by at least one month.
    rate_house = annual(search("121Y006", "A", "2005", "2026", "BECBLA03"))
    rate_mortgage = annual(search("121Y006", "A", "2005", "2026", "BECBLA0302"))
    rate_credit = annual(search("121Y006", "A", "2005", "2026", "BECBLA03051"))
    late_house = annual(search("901Y054", "A", "2005", "2026", "MO3AB"))
    late_firms = annual(search("901Y054", "A", "2005", "2026", "MO3AA"))
    write("macro/credit_terms.csv",
          "year,household_rate,mortgage_rate,unsecured_rate,"
          "household_late,corporate_late",
          [f"{y},{fmt(rate_house.get(y))},{fmt(rate_mortgage.get(y))},"
           f"{fmt(rate_credit.get(y))},{fmt(late_house.get(y))},"
           f"{fmt(late_firms.get(y))}" for y in years])

    # ---- population, to the end of the projection ------------------------
    # This file deliberately runs past the 2006-2026 window: the point of the
    # demographic plate is what happens after it.
    proj_years = sorted(set(population) | set(elderly) | set(tfr))
    write("social/population.csv", "year,pop_mn,elderly_pct,tfr",
          [f"{y},{fmt(population[y] / 1e6, 3) if y in population else ''},"
           f"{fmt(elderly.get(y))},"
           f"{fmt(tfr.get(y), 3)}" for y in proj_years if 2000 <= y <= 2072])

    print("Done.")


if __name__ == "__main__":
    main()
