#!/usr/bin/env python3
"""Singapore's national series, from SingStat's own Table Builder API.

    python3 -I fetch/fetch_singstat.py [--offline]

Writes review sidecars only (SOURCING_A_COUNTRY.md §6); a curated number is
never overwritten. The curated CSVs under data/ were promoted from these
sidecars by hand, with the diffs recorded in DATA_NOTES.md.

Endpoint (probed live 2026-10-25):

    GET https://tablebuilder.singstat.gov.sg/api/table/metadata/<table>
    GET https://tablebuilder.singstat.gov.sg/api/table/tabledata/<table>

Both answer JSON. A retired id answers `{"StatusCode":404,...}` under HTTP
404 — never an HTML page — but the payload shape is still checked before
anything is cached, because a gateway that serves an error under 200 is the
failure this whole arrangement exists to catch.

Two access conditions, recorded rather than worked around:

  * The host rate-limits. A 1,049-table sweep of the metadata endpoint
    started answering 403 after a few hundred requests and recovered
    within minutes. This fetcher therefore takes one table at a time with a
    pause between requests and retries with backoff.
  * A plain `urllib` request is refused with 403 even for a table that
    `curl` and `requests` fetch at the same instant, so the fetcher uses
    `requests` (already a fetch-time dependency) with a browser
    User-Agent and an `Accept: application/json` header.

Table ids come from the publisher's own `sitemap.xml`, not from the
data.gov.sg catalogue: that catalogue's "Adapted from" links point at
retired ids (M450091 no longer resolves) and at saved views (`table/CT/…`),
and several of its dataset names belong to a different table than the id
beside them. Every id below was confirmed through the metadata endpoint
and its `title` is asserted here, so a re-pointed id fails loudly.

Aggregation, all of it stated because the choice changes the number:

  * annual tables are taken as published;
  * monthly price and rate series become the calendar-year mean;
  * monthly flow series become the calendar-year sum;
  * monthly stock series take the December observation, labelled as such;
  * quarterly balance sheets take Q4;
  * financial-year tables keep the publisher's label (FY starts 1 April)
    and are written to a `fiscal_year` column, never to `year`.

`--offline` reads the cache and writes nothing new; a cold cache with
`--offline` exits non-zero having written nothing.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "singstat"

API = "https://tablebuilder.singstat.gov.sg/api/table/{kind}/{tid}"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-SG,en;q=0.9",
}
YEAR_FROM, YEAR_TO = 2006, 2026
PAUSE = 1.2          # seconds between calls; the host rate-limits
RETRIES = 5

# The regions and markets drawn from M451521. The table has 160 rows and the
# endpoint caps a response at 5,000 cells, so every one of these is fetched
# by name rather than read off the first page (see main()).
TRADE_MARKETS = [
    "Total All Markets",
    "America", "Asia", "Europe", "Oceania", "Africa",
    "Mainland China", "Hong Kong", "Taiwan", "United States Of America",
    "Malaysia", "Indonesia", "Thailand", "Viet Nam", "Philippines",
    "Japan", "Republic Of Korea", "India", "Australia",
    "Netherlands", "Germany", "United Kingdom", "France", "Switzerland",
    "United Arab Emirates", "Saudi Arabia",
]

# ---------------------------------------------------------------- tables ---
# tid -> the title the metadata endpoint must return. A changed title means
# the publisher re-pointed the id at a different table, which is exactly the
# silent substitution this atlas must not ship.
TABLES = {
    "M015021": "Expenditure On Gross Domestic Product At Current Prices, Annual",
    "M015951": "Key Data Of Gross Domestic Product In Chained (2015) Dollars, "
               "By Industry (SSIC 2020), Annual",
    "M015121": "Per Capita Gross National Income And Per Capita Gross Domestic "
               "Product At Current Prices, Annual",
    "M213751": "Consumer Price Index (CPI), 2024 As Base Year, Monthly",
    "M182332": "Unemployment Rate Aged 15 Years And Over, End June, Annual, "
               "Seasonally Adjusted",
    "M130661": "Government Overall Fiscal Position (% Of GDP), Annual",
    "M130601": "General Government Finance, Annual",
    "M130611": "Government Finance, Annual",
    "M130191": "Government Debt By Maturity (As At End Of Calendar Year), Annual",
    "M130581": "Government Operating Expenditure By Sector, Annual",
    "M130591": "Government Development Expenditure By Sector, Annual",
    "M451521": "Merchandise Exports By Region And Market, Monthly",
    "M700031": "Official Foreign Reserves (End Of Period), Monthly",
    "M700071": "Current Banks Interest Rates (End Of Period), Monthly",
    "M700851": "Exchange Rates (Average For Period), Annual",
    "M700981": "Household Sector Balance Sheet (End Of Period), Quarterly",
    "M810001": "Indicators On Population, Annual",
    "M810091": "Births And Fertility Rates, Annual",
    "M810131": "Deaths By Broad Groups Of Causes, Annual",
    "M810481": "Death And Death Rates, Annual",
    "M810501": "Life Expectancy By Sex, Annual",
    "M810361": "Key Indicators On Household Employment Income Among Resident "
               "Employed Households, Annual",
    "M810781": "Number And Profile Of Singapore Citizenships And Permanent "
               "Residencies Granted, Annual",
    "M810791": "Share Of Non-Resident Population By Pass Types, At End June, "
               "Annual",
    "M890151": "Land Area (As At December), Annual",
    "M890891": "Cases Recorded For Selected Major Offences, Annual",
    "M891481": "Crime Cases Recorded, Annual",
    "M651421": "Death Rate Due To Road Traffic Injuries, Annual",
}

# Known observations, each read off the live payload on 2026-10-25 and
# quoted in DISCOVERY.md. They are the guard against a unit change, a
# re-pointed table or a truncated payload landing in a sidecar.
ANCHORS = {
    ("M015021", "GDP At Current Market Prices", "2025"): 789529.2,
    ("M015951", "GDP In Chained (2015) Dollars", "2025"): 593869.9,
    ("M015121", "Per Capita Gross Domestic Product", "2025"): 129194.0,
    ("M810001", "Total Population", "2025"): 6111175.0,
    ("M810091", "Total Fertility Rate (TFR)", "2025"): 0.87,
    ("M810481", "Crude Death Rate", "2025"): 6.0,
    ("M810501", "Total Life Expectancy At Birth (Residents)", "2025"): 83.9,
    ("M810131", "Total Deaths By Causes", "2025"): 26499.0,
    ("M182332", "Total Unemployment Rate, (SA)", "2025"): 2.0,
    ("M890151", "Total Land Area", "2025"): 744.3,
    ("M890891", "Murder", "2025"): 7.0,
    ("M651421", "Death Rate Due To Road Traffic Injuries", "2024"): 2.35,
    ("M700851", "US Dollar", "2025"): 1.3066,
    ("M213751", "All Items", "2026 Sep"): 103.551,
    ("M700071", "Government Securities - 10-Year Bond Yield", "2026 Sep"): 2.47,
    ("M700031", "Official Foreign Reserves", "2026 Sep"): 553573.4,
}


def fetch(kind: str, tid: str, offline: bool, params: dict | None = None,
          tag: str = "") -> dict:
    """One table (or one row of one table), cached and shape-checked."""
    suffix = ("_" + "_".join(f"{k}-{v}".replace(" ", "") for k, v in
                             sorted((params or {}).items()))).replace("/", "-")
    cache = CACHE / f"{kind}_{tid}{tag}{suffix}.json"
    if cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
    else:
        if offline:
            sys.exit(f"fetch_singstat: no cache at {cache} and --offline given; "
                     "nothing written")
        payload = None
        for attempt in range(RETRIES):
            try:
                resp = requests.get(API.format(kind=kind, tid=tid),
                                    headers=HEADERS, timeout=90,
                                    params=params or {})
            except Exception as exc:                     # noqa: BLE001
                print(f"  {tid} {kind} attempt {attempt + 1}: {exc}",
                      file=sys.stderr)
                time.sleep(5 * (attempt + 1))
                continue
            if resp.status_code == 200:
                try:
                    candidate = resp.json()
                except ValueError:
                    sys.exit(f"fetch_singstat: {tid} {kind} served "
                             f"{resp.headers.get('content-type')!r} under 200; "
                             "nothing written")
                data = (candidate.get("Data") or {})
                if kind == "metadata" and not (data.get("records") or {}).get("row"):
                    sys.exit(f"fetch_singstat: {tid} metadata has no records; "
                             "nothing written")
                if kind == "tabledata" and not data.get("row"):
                    sys.exit(f"fetch_singstat: {tid} tabledata has no rows; "
                             "nothing written")
                payload = candidate
                break
            if resp.status_code == 403:
                # Rate limit, not a dead table: back off and retry.
                print(f"  {tid} {kind} 403 (rate limit?) attempt {attempt + 1}",
                      file=sys.stderr)
                time.sleep(15 * (attempt + 1))
                continue
            sys.exit(f"fetch_singstat: {tid} {kind} HTTP {resp.status_code}; "
                     "nothing written")
        if payload is None:
            sys.exit(f"fetch_singstat: {tid} {kind} never answered; "
                     "nothing written")
        CACHE.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(payload, indent=0), encoding="utf-8")
    return payload


def series(payload: dict) -> dict:
    """{rowText: [(period, value)]} with blanks dropped, order preserved.

    The publisher uses "-" for "no observation" in some tables (M130191
    government debt has one before the instrument existed). It is a
    placeholder and is dropped here rather than parsed, so it can never
    become a zero — the atlas rule that a missing year stays missing.
    """
    out = {}
    for row in payload["Data"]["row"]:
        label = row["rowText"]
        if label in out:
            # Some tables repeat a label across two blocks (M891481 carries
            # each offence twice, as a count and as a rate). Keying on the
            # label alone would silently keep the last one, so the first is
            # kept and the clash is reported.
            print(f"  !! duplicate series label {label!r} in one table; "
                  "first kept", file=sys.stderr)
            continue
        pts = [(c.get("key"), c.get("value")) for c in (row.get("columns") or [])]
        clean = []
        for key, value in pts:
            if not key or value in (None, "", "-", "na", "N/A"):
                continue
            try:
                clean.append((key, float(value)))
            except (TypeError, ValueError):
                continue
        out[row["rowText"]] = clean
    return out


def year_of(period: str) -> int | None:
    head = period.split(" ")[0].replace(",", "")
    return int(head) if head[:4].isdigit() else None


def annual(points, how: str) -> dict[int, float]:
    """Collapse a period series to calendar years, the stated way.

    A SUM is only taken over a complete year: monthly data that stop in
    September 2026 would otherwise be published as a nine-month "annual
    total", which reads as a thirty-per-cent collapse in exports that never
    happened (SOURCING_A_COUNTRY.md §4, the partial year). Means and
    end-of-period readings keep the running year, because a price index, a
    bond yield or a stock at a date is a point reading rather than a
    nine-month sum — the plate marks the running year as partial.
    """
    per: dict[int, list[float]] = {}
    last: dict[int, tuple[str, float]] = {}
    monthly = quarterly = False
    for period, value in points:
        year = year_of(period)
        if year is None:
            continue
        parts = period.split(" ")
        if len(parts) > 1 and parts[1].rstrip("Q").isdigit():
            quarterly = True
        elif len(parts) > 1:
            monthly = True
        per.setdefault(year, []).append(value)
        last[year] = (period, value)
    if how == "value":
        return {y: v[0] for y, v in per.items()}
    if how == "mean":
        # An annual MEAN is only an annual mean over a complete year: the
        # mean of nine months of 2026 is a year-to-date figure, and putting
        # it in a column of calendar-year means would compare it with twelve
        # months of every other year. Same rule as the sums; the running year
        # therefore ends at last_full_year for prices and rates, while a
        # point reading (end-June unemployment, a Q4 stock) still shows it.
        need = 12 if monthly else (4 if quarterly else 1)
        out = {}
        for y, v in per.items():
            if len(v) < need:
                print(f"    {y}: {len(v)} of {need} periods — partial year "
                      "kept out of an annual mean", file=sys.stderr)
                continue
            out[y] = sum(v) / len(v)
        return out
    if how == "sum":
        need = 12 if monthly else (4 if quarterly else 1)
        out = {}
        for y, v in per.items():
            if len(v) < need:
                print(f"    {y}: {len(v)} of {need} periods — year dropped "
                      "from a sum rather than published as a partial total",
                      file=sys.stderr)
                continue
            out[y] = sum(v)
        return out
    if how in ("dec", "q4"):
        # The December observation; for a quarterly series, Q4.
        want = {"dec": "Dec", "q4": "4Q"}[how]
        out = {}
        for y, (period, value) in last.items():
            if period.endswith(want) or period == str(y):
                out[y] = value
        return out
    raise ValueError(how)


def row(rows: dict, tid: str, match: str) -> list:
    """Exact series-title match; a near-miss is a failure, not a guess.

    `rowText` values are the publisher's own series labels and they are
    the only safe key: positional indexing silently returns the wrong
    series when a table gains a row.
    """
    if match in rows:
        return rows[match]
    near = [k for k in rows if k.lower().startswith(match.lower()[:25])]
    raise SystemExit(f"{tid}: no series titled {match!r}; near matches: "
                     f"{near[:4]}")


def write(rel: str, header: list[str], body: list[list],
          comments: list[str] | None = None) -> None:
    """A sidecar: `#` comments, a header, then rows.

    Cells are quoted by the csv module rather than joined with commas
    because one publisher series carries a comma in its own label
    ("Accidents, Poisonings And Violence"); a naive join turns that into
    two columns and every value after it shifts one place left, which is
    the classic silent mis-parse of this repository.
    """
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        for comment in comments or []:
            fh.write(f"# {comment}\n")
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        for cells in body:
            writer.writerow(["" if c is None else c for c in cells])
    print(f"  data/{rel}  {len(body)} rows")


def f(value, dec: int) -> str:
    return "" if value is None else f"{value:.{dec}f}"


def window(series_by_year: dict[int, dict], years=None) -> list[int]:
    return [y for y in (years or series_by_year) if YEAR_FROM <= y <= YEAR_TO]


def main(argv: list[str]) -> int:
    offline = "--offline" in argv
    meta, data, rows = {}, {}, {}
    for tid, want_title in TABLES.items():
        print(f"  {tid}")
        meta[tid] = fetch("metadata", tid, offline)["Data"]["records"]
        got = (meta[tid].get("title") or "").strip()
        if got != want_title:
            sys.exit(f"fetch_singstat: {tid} is now {got!r}, expected "
                     f"{want_title!r} — the id was re-pointed; nothing written")
        data[tid] = fetch("tabledata", tid, offline)
        rows[tid] = series(data[tid])
        time.sleep(PAUSE)

    # ---- anchors, checked on the raw payload before any aggregation ----
    for (tid, title, period), want in ANCHORS.items():
        got = dict(rows[tid].get(title, [])).get(period)
        if got is None or abs(got - want) > max(1e-6, abs(want) * 1e-4):
            sys.exit(f"fetch_singstat: {tid} {title!r} {period} = {got!r}, "
                     f"expected {want!r}")
    print(f"  {len(ANCHORS)} anchors verified")

    # ---- M451521 needs row-by-row fetching ----------------------------
    # The table carries 160 rows (five regions and every market). The
    # tabledata endpoint returns at most ~5,000 cells per response, which is
    # 17.5 of the table's 285 monthly columns, and `offset` is inert — so
    # without asking for rows by name the payload silently stops after
    # "Honduras". The endpoint does honour a `search` row filter, so the
    # rows this lane draws are fetched individually and merged.
    for market in TRADE_MARKETS:
        extra = series(fetch("tabledata", "M451521", offline,
                             params={"search": market}))
        if market not in extra:
            sys.exit(f"fetch_singstat: M451521 row {market!r} did not come "
                     "back from the search filter; nothing written")
        rows["M451521"][market] = extra[market]
        time.sleep(PAUSE)

    # ---------------------------------------------------------- macro ----
    gdp = {}
    gdp["gdp_current_sgd_mn"] = annual(row(rows["M015021"],
                                           "M015021", "GDP At Current Market Prices"),
                                       "value")
    gdp["gdp_real_2015_sgd_mn"] = annual(row(rows["M015951"], "M015951",
                                             "GDP In Chained (2015) Dollars"), "value")
    gdp["exports_gns_sgd_mn"] = annual(row(rows["M015021"], "M015021",
                                           "Exports Of Goods And Services"), "value")
    gdp["imports_gns_sgd_mn"] = annual(row(rows["M015021"], "M015021",
                                           "Imports Of Goods And Services"), "value")
    gdp["gfcf_sgd_mn"] = annual(row(rows["M015021"], "M015021",
                                    "Gross Fixed Capital Formation"), "value")
    gdp["gov_consumption_sgd_mn"] = annual(
        row(rows["M015021"], "M015021", "Government Consumption Expenditure"), "value")
    gdp["gdp_per_person_sgd"] = annual(row(rows["M015121"], "M015121",
                                           "Per Capita Gross Domestic Product"), "value")
    gdp["gdp_per_person_usd"] = annual(row(rows["M015121"], "M015121",
                                           "Per Capita Gross Domestic Product (US Dollar)"),
                                       "value")
    # Growth is computed inside this one vintage of the chained series so a
    # rebasing can never become a growth step, and the first year of the
    # window needs the year before it, which the publisher supplies.
    real = gdp["gdp_real_2015_sgd_mn"]
    growth = {y: (real[y] / real[y - 1] - 1) * 100
              for y in real if y - 1 in real}
    gdp["real_growth_pct"] = growth
    cols = ["gdp_current_sgd_mn", "gdp_real_2015_sgd_mn", "real_growth_pct",
            "exports_gns_sgd_mn", "imports_gns_sgd_mn", "gfcf_sgd_mn",
            "gov_consumption_sgd_mn", "gdp_per_person_sgd",
            "gdp_per_person_usd"]
    decs = [1, 1, 2, 1, 1, 1, 1, 0, 0]
    yrs = window({y: 1 for y in gdp["gdp_current_sgd_mn"]})
    write("macro/gdp_from_singstat.csv", ["year"] + cols,
          [[str(y)] + [f(gdp[c].get(y), d) for c, d in zip(cols, decs)]
           for y in yrs],
          ["Singapore Department of Statistics, Table Builder: M015021 "
           "(GDP at current prices, expenditure),",
           "M015951 (GDP in chained 2015 dollars), M015121 (per-capita GDP).",
           "real_growth_pct is computed from gdp_real_2015_sgd_mn within this "
           "one vintage.",
           "gdps and exports/imports are million Singapore dollars, current "
           "prices unless stated."])

    cpi_index = annual(row(rows["M213751"], "M213751", "All Items"), "mean")
    cpi = {y: (cpi_index[y] / cpi_index[y - 1] - 1) * 100
           for y in cpi_index if y - 1 in cpi_index}
    write("macro/cpi_from_singstat.csv", ["year", "cpi_index_2024",
                                          "inflation_pct"],
          [[str(y), f(cpi_index.get(y), 3), f(cpi.get(y), 2)]
           for y in window(cpi_index)],
          ["Singapore Department of Statistics, Table Builder M213751, "
           "CPI All Items, 2024 = 100.",
           "cpi_index_2024 is the calendar-year mean of the monthly index; "
           "inflation_pct is its year-on-year change.",
           "One vintage: the 2024-base table back-computes the whole history, "
           "so no rebasing seam is spliced in."])

    labour = {
        "unemployment_total_sa_pct": annual(
            row(rows["M182332"], "M182332", "Total Unemployment Rate, (SA)"), "value"),
        "unemployment_resident_sa_pct": annual(
            row(rows["M182332"], "M182332", "Resident Unemployment Rate, (SA)"), "value"),
    }
    write("macro/labour_from_singstat.csv", ["year"] + list(labour),
          [[str(y)] + [f(labour[c].get(y), 1) for c in labour]
           for y in window(labour["unemployment_total_sa_pct"])],
          ["Singapore Department of Statistics, Table Builder M182332: "
           "unemployment rate, aged 15+, end-June, seasonally adjusted.",
           "The resident rate is a SUBSET population (citizens and permanent "
           "residents), not a second estimate of the same thing.",
           "2026 is the end-June 2026 reading, not a completed calendar year."])

    # --------------------------------------------------------- fiscal ----
    fp = rows["M130661"]
    fiscal = {
        "operating_revenue_pct_gdp": annual(
            row(fp, "M130661", "Operating Revenue"), "value"),
        "tax_revenue_pct_gdp": annual(
            row(fp, "M130661", "Tax Revenue"), "value"),
        "total_expenditure_pct_gdp": annual(
            row(fp, "M130661", "Total Expenditure"), "value"),
        "primary_surplus_pct_gdp": annual(
            row(fp, "M130661", "Primary Surplus/(Deficit)"), "value"),
        "overall_fiscal_position_pct_gdp": annual(
            row(fp, "M130661", "Overall Fiscal Position"), "value"),
        "singa_interest_pct_gdp": annual(
            row(fp, "M130661", "SINGA Interest Costs And Loan Expenses"),
            "value"),
    }
    write("fiscal/fiscal_national_from_singstat.csv", ["fiscal_year"] + list(fiscal),
          [[str(y)] + [f(fiscal[c].get(y), 2) for c in fiscal]
           for y in window(fiscal["operating_revenue_pct_gdp"])],
          ["Singapore Department of Statistics, Table Builder M130661: "
           "Government Overall Fiscal Position, % of GDP.",
           "FINANCIAL YEAR, not calendar: FY starts 1 April, labelled by the "
           "starting year, so fiscal_year 2026 = 1 Apr 2026 - 31 Mar 2027.",
           "Publisher's status: FY2026 is the BUDGET estimate, FY2025 the "
           "revised estimate, FY2024 and earlier are actuals.",
           "Cash-basis national presentation (operating revenue, total "
           "expenditure), NOT the IMF/SNA accrual general-government frame.",
           "SINGA interest costs are the debt-service line the publisher "
           "gives; it is not COFOG D41 interest paid."])

    gov = {
        "cash_surplus_sgd_mn": annual(
            row(rows["M130601"], "M130601", "Cash Surplus/Deficit"), "value"),
        "cash_receipts_sgd_mn": annual(
            row(rows["M130601"], "M130601", "Cash Receipts From Operating Activities"),
            "value"),
        "cash_payments_sgd_mn": annual(
            row(rows["M130601"], "M130601", "Cash Payments For Operating Activities"),
            "value"),
    }
    write("fiscal/cashflow_from_singstat.csv", ["fiscal_year"] + list(gov),
          [[str(y)] + [f(gov[c].get(y), 1) for c in gov] for y in window(gov["cash_surplus_sgd_mn"])],
          ["Singapore Department of Statistics, Table Builder M130601: "
           "General Government Finance, cash basis, million SGD.",
           "Financial years labelled by starting year (1 April start).",
           "Cash receipts/payments from OPERATING activities only; development "
           "expenditure is a separate cash outflow and is not netted here."])

    # ------------------------------------------------------- spending ----
    # The publisher's own functional classification, kept as published:
    # Singapore does not publish COFOG, and mapping ministries onto COFOG
    # groups would be an editorial assertion the source does not make.
    for tid, name, total_title, sidecar in (
            ("M130581", "operating", "Total Operating Expenditure",
             "spending/operating_by_head_from_singstat.csv"),
            ("M130591", "development", "Total Development Expenditure",
             "spending/development_by_head_from_singstat.csv")):
        table = rows[tid]
        heads = [k for k in table if k != total_title]
        cols = {k: annual(row(table, tid, k), "value") for k in [total_title] + heads}
        write(sidecar, ["fiscal_year"] + [total_title] + heads,
              [[str(y)] + [f(cols[c].get(y), 1) for c in [total_title] + heads]
               for y in window(cols[total_title])],
              [f"Singapore Department of Statistics, Table Builder {tid}: "
               f"government {name} expenditure by ministry/sector, million SGD.",
               "Financial years labelled by starting year (FY starts 1 April).",
               "National administrative classification (ministries), NOT "
               "COFOG; the mapping onto COFOG groups would be an editorial "
               "assertion and is not made."])

    # The debt stock, by maturity, as at end of calendar year.
    debt_rows = rows["M130191"]
    print("  M130191 series: " + " | ".join(list(debt_rows)[:6]))
    write("fiscal/debt_stock_from_singstat.csv",
          ["year"] + [k for k in debt_rows],
          [[str(y)] + [f(annual(v, "value").get(y), 1) for v in debt_rows.values()]
           for y in window(annual(list(debt_rows.values())[0], "value"))],
          ["Singapore Department of Statistics, Table Builder M130191: "
           "government debt by maturity, as at end of calendar year, "
           "million SGD.",
           "Gross debt only. Singapore's SGS are issued to build reserves and "
           "to hold the CPF Board's liabilities; the government publishes no "
           "net-debt series here, so no net position is derived."])

    # ---------------------------------------------------------- trade ----
    ex = gdp["exports_gns_sgd_mn"]
    im = gdp["imports_gns_sgd_mn"]
    nom = gdp["gdp_current_sgd_mn"]
    write("trade/trade_from_singstat.csv",
          ["year", "exports_pct_gdp", "imports_pct_gdp", "balance_pct_gdp"],
          [[str(y), f(ex[y] / nom[y] * 100, 2), f(im[y] / nom[y] * 100, 2),
            f((ex[y] - im[y]) / nom[y] * 100, 2)]
           for y in window(nom) if y in ex and y in im],
          ["Computed from Singapore Department of Statistics M015021: exports "
           "and imports of goods AND services at current prices, divided by "
           "GDP at current market prices.",
           "National-accounts basis, not customs goods trade: this includes "
           "services, which for Singapore is a large share.",
           "Both numerator and denominator come from the same table and "
           "vintage, so the ratio has no splice."])

    part = rows["M451521"]
    tot = annual(row(part, "M451521", "Total All Markets"), "sum")
    by_market = {m: annual(row(part, "M451521", m), "sum") for m in TRADE_MARKETS}
    # Year-major: a long-format file whose year column has to ascend, or
    # core.plotting and tests/test_data read a re-ordered series.
    body = []
    for y in window(tot):
        for m in TRADE_MARKETS:
            if m == "Total All Markets":
                continue
            value = by_market[m].get(y)
            if value is None or not tot.get(y):
                continue
            body.append([str(y), m, f(value, 1),
                         f(value / tot[y] * 100, 2)])
    write("trade/partners_from_singstat.csv",
          ["year", "market", "exports_sgd_mn", "share_of_exports_pct"], body,
          ["Singapore Department of Statistics, Table Builder M451521: "
           "merchandise exports by region and market, monthly; annual sums "
           "computed here over complete calendar years only.",
           "CUSTOMS goods basis (not national accounts): total exports = "
           "domestic exports + re-exports, which is what this table sums.",
           "share_of_exports_pct divides by Total All Markets in the same "
           "year. Region rows (America, Asia, Europe, Oceania, Africa) are "
           "aggregates and must not be added to the market rows.",
           "2026 is absent: nine months of data are not an annual total."])

    # -------------------------------------------------------- markets ----
    rates = rows["M700071"]
    m10 = annual(row(rates, "M700071",
                     "Government Securities - 10-Year Bond Yield"), "mean")
    sora = annual(row(rates, "M700071", "Singapore Overnight Rate Average"), "mean")
    sora3 = annual(row(rates, "M700071",
                       "Compounded Singapore Overnight Rate Average (SORA) - 3 Month"),
                   "mean")
    write("markets/rates_from_singstat.csv",
          ["year", "govt_bond_10y_pct", "sora_pct", "sora_3m_compounded_pct"],
          [[str(y), f(m10.get(y), 2), f(sora.get(y), 3), f(sora3.get(y), 3)]
           for y in window(set(m10) | set(sora) | set(sora3))],
          ["Singapore Department of Statistics, Table Builder M700071: bank "
           "interest rates, end of period, monthly; calendar-year means here.",
           "SORA is a money-market benchmark, not a policy rate: Singapore "
           "has no policy interest rate (MAS targets an exchange-rate band).",
           "10-year is the Singapore Government Securities yield."])

    fx = annual(row(rows["M700851"], "M700851", "US Dollar"), "value")
    write("markets/usd_sgd_from_singstat.csv", ["year", "sgd_per_usd"],
          [[str(y), f(fx.get(y), 4)] for y in window(fx)],
          ["Singapore Department of Statistics, Table Builder M700851: "
           "exchange rate, average for period, Singapore dollars per US dollar.",
           "A rise is a weaker Singapore dollar; the plate indexes it so that "
           "up means stronger."])

    # --------------------------------------------------------- credit ----
    bs = rows["M700981"]
    liab = annual(row(bs, "M700981", "Liabilities"), "q4")
    mort = annual(row(bs, "M700981", "Mortgage Loans"), "q4")
    pers = annual(row(bs, "M700981", "Personal Loans"), "q4")
    nw = annual(row(bs, "M700981", "Household Net Worth"), "q4")
    write("credit/household_from_singstat.csv",
          ["year", "household_liabilities_sgd_mn", "mortgage_loans_sgd_mn",
           "personal_loans_sgd_mn", "household_net_worth_sgd_mn",
           "liabilities_pct_gdp"],
          [[str(y), f(liab.get(y), 1), f(mort.get(y), 1), f(pers.get(y), 1),
            f(nw.get(y), 1),
            f(liab[y] / nom[y] * 100, 2) if y in nom else ""]
           for y in window(liab)],
          ["Singapore Department of Statistics, Table Builder M700981: "
           "household sector balance sheet, end of period, million SGD; Q4 "
           "taken for each year.",
           "liabilities_pct_gdp divides the same-vintage Q4 stock by that "
           "year's GDP at current market prices (M015021).",
           "This is the national household-debt measure. The BIS series in "
           "credit/bis_from_bis.csv is the harmonised comparable and is not "
           "spliced with it."])

    # --------------------------------------------------------- people ----
    hi = rows["M810361"]
    ginis = {
        "gini_before_taxes_transfers": "Gini Coefficient Based On Household "
            "Employment Income Per Household Member (Including Employer CPF "
            "Contributions) Before Accounting For Government Transfers And Taxes",
        "gini_after_taxes_transfers": "Gini Coefficient Based On Household "
            "Employment Income Per Household Member (Including Employer CPF "
            "Contributions) After Accounting For Government Transfers And Taxes",
        "median_household_income_sgd": "Median Monthly Household Employment "
            "Income Including Employer CPF Contributions",
        "median_income_per_member_sgd": "Median Monthly Household Employment "
            "Income Per Household Member (Including Employer CPF Contributions)",
    }
    peo = {k: annual(row(hi, "M810361", v), "value") for k, v in ginis.items()}
    write("people/income_from_singstat.csv", ["year"] + list(peo),
          [[str(y)] + [f(peo[c].get(y), 3 if c.startswith("gini") else 0)
                       for c in peo] for y in window(peo["median_household_income_sgd"])],
          ["Singapore Department of Statistics, Table Builder M810361: "
           "household employment income, resident employed households.",
           "TWO Gini definitions, both published, never spliced: before and "
           "after government transfers and taxes, on household income per "
           "household member. The after-transfers figure is the one Singapore "
           "quotes as its headline.",
           "Income includes employer CPF contributions; it is employment "
           "income, so it excludes investment income and transfers."])

    # ------------------------------------------------------- world/dem ---
    ofr = annual(row(rows["M700031"], "M700031", "Official Foreign Reserves"), "dec")
    write("world/reserves_from_singstat.csv", ["year", "official_foreign_reserves_sgd_mn"],
          [[str(y), f(ofr.get(y), 1)] for y in window(ofr)],
          ["Singapore Department of Statistics, Table Builder M700031: "
           "official foreign reserves, end of period, million SGD; December "
           "taken for each year.",
           "The World Bank's FI.RES.TOTL.CD in US$ is the comparable line."])

    pop = rows["M810001"]
    keys = {
        "population_total": "Total Population",
        "population_resident": "Resident Population",
        "population_citizen": "Singapore Citizen Population",
        "population_pr": "Permanent Resident Population",
        "population_nonresident": "Non-Resident Population",
        "population_density_per_km2": "Population Density",
        "natural_increase_residents": "Resident Natural Increase",
        "natural_increase_rate_per_1000": "Rate Of Natural Increase",
        "old_age_support_ratio_citizens": "Old-Age Support Ratio: Citizens Aged "
            "20-64 Years Per Citizen Aged 65 Years & Over",
    }
    # Two series carry their unit inside the rowText; pin them exactly.
    
    popseries = {}
    for col, title in keys.items():
        try:
            popseries[col] = annual(row(pop, "M810001", title), "value")
        except SystemExit:
            print(f"  !! M810001 series {title!r} not found", file=sys.stderr)
    write("demography/population_from_singstat.csv", ["year"] + list(popseries),
          [[str(y)] + [f(popseries[c].get(y), 2 if "ratio" in c or "rate" in c
                         else 0) for c in popseries]
           for y in window(popseries["population_total"])],
          ["Singapore Department of Statistics, Table Builder M810001: "
           "Indicators on Population, mid-year (end June).",
           "TOTAL population includes non-residents (work-permit, employment-"
           "pass, student and dependant's-pass holders); RESIDENT = citizens + "
           "permanent residents. The two are different populations and are "
           "never mixed in one denominator.",
           "2026 is the mid-2026 level, not a completed year.",
           "Pre-1990 figures in the publisher's own note are de facto and "
           "1990 onwards de jure; the window starts in 2006 so that break is "
           "outside it."])

    vital = {
        "crude_death_rate_per_1000": (rows["M810481"], "M810481",
                                      "Crude Death Rate"),
        "deaths_total": (rows["M810481"], "M810481", "Total Deaths"),
        "resident_deaths": (rows["M810481"], "M810481", "Resident Deaths"),
        "infant_mortality_per_1000": (rows["M810481"], "M810481",
                                      "Infant Mortality Rate"),
        "crude_birth_rate_per_1000": (rows["M810091"], "M810091",
                                      "Crude Birth Rate"),
        "tfr": (rows["M810091"], "M810091", "Total Fertility Rate (TFR)"),
        "live_births_total": (rows["M810091"], "M810091", "Total Live-Births"),
        "life_expectancy_total": (rows["M810501"], "M810501",
                                  "Total Life Expectancy At Birth (Residents)"),
        "land_area_km2": (rows["M890151"], "M890151", "Total Land Area"),
    }
    vs = {k: annual(row(*v), "value") for k, v in vital.items()}
    write("demography/vital_from_singstat.csv", ["year"] + list(vs),
          [[str(y)] + [f(vs[c].get(y),
                         2 if ("rate" in c or c in ("tfr", "life_expectancy_total"))
                         else (1 if c == "land_area_km2" else 0))
                       for c in vs]
           for y in window(vs["crude_death_rate_per_1000"])],
          ["Singapore Department of Statistics, Table Builder M810481 "
           "(deaths and death rates), M810091 (births and fertility), M810501 "
           "(life expectancy), M890151 (land area).",
           "SCOPE: the publisher's vital rates are per 1,000 RESIDENTS "
           "(citizens + permanent residents), not per 1,000 people present. "
           "They are therefore not the World Bank's total-population rate; "
           "both are published and neither is spliced into the other.",
           "Land area grows with reclamation (581.5 km2 in 1960 to 744.3 in "
           "2025); it is a measured area, not an estimate."])

    # ------------------------------------------------- security/mortality -
    cr = rows["M890891"]
    crim = {
        "murder_count": "Murder",
        "serious_hurt_count": "Serious Hurt",
        "rape_count": "Rape",
        "robbery_count": "Robbery",
        "housebreaking_count": "Housebreaking",
        "total_selected_offences_count": "Total",
    }
    cs = {k: annual(row(cr, "M890891", v), "value") for k, v in crim.items()}
    road = annual(row(rows["M651421"], "M651421",
                      "Death Rate Due To Road Traffic Injuries"), "value")
    sui = annual(row(rows["M810131"], "M810131", "Suicides"), "value")
    cs["road_death_rate_per_100k"] = road
    cs["suicide_count"] = sui
    write("security/crime_from_singstat.csv", ["year"] + list(cs),
          [[str(y)] + [f(cs[c].get(y), 2 if "rate" in c else 0) for c in cs]
           for y in window(cs["murder_count"])],
          ["Singapore Department of Statistics, Table Builder M890891 "
           "(selected major offences, cases recorded), M651421 (road-traffic "
           "death rate, per 100,000 population) and M810131 (suicides).",
           "Murder is a LEGAL category (Penal Code), not the UNODC intentional-"
           "homicide definition; the UNODC series is drawn beside it, never "
           "substituted for it.",
           "M890891 'Total' sums the selected offence types and is dominated "
           "by cheating-related offences; it is not an all-crime count. "
           "M891481 carries the broader recorded-crime series from 2020.",
           "Rates per 100,000 here use the publisher's population basis where "
           "it states one; counts are otherwise converted with the same-year "
           "resident or total population and the choice is recorded on the "
           "plate."])

    causes = rows["M810131"]
    keep = ["Total Deaths By Causes", "Malignant Neoplasms",
            "Diseases Of The Circulatory System", "Heart And Hypertensive Diseases",
            "Cerebrovascular Disease", "Diseases Of The Respiratory System",
            "Pneumonia", "Diabetes", "Accidents, Poisonings And Violence",
            "Suicides", "Transport Accidents"]
    cols = {k: annual(row(causes, "M810131", k), "value") for k in keep}
    cols = {k.replace(",", ""): v for k, v in cols.items()}
    write("mortality/deaths_by_cause_from_singstat.csv", ["year"] + list(cols),
          [[str(y)] + [f(cols[c].get(y), 0) for c in cols]
           for y in window(cols["Total Deaths By Causes"])],
          ["Singapore Department of Statistics, Table Builder M810131: deaths "
           "by broad groups of causes, count of deaths.",
           "Broad ICD groups as the publisher labels them; 'Malignant "
           "Neoplasms' is contained in 'Neoplasms' and is the one published "
           "separately here.",
           "There is no COVID-19 row in this table: the publisher's broad "
           "groups predate the code and the pandemic deaths appear inside "
           "'Diseases Of The Respiratory System' and 'Infective And Parasitic "
           "Diseases'. The cause-of-death chapter's COVID slot therefore "
           "needs a different publisher (recorded in meta.pending)."])

    # ------------------------------------------------------- migration ---
    mig = {"nonresident_employment_pass_pct": "Employment Pass Holders",
           "nonresident_s_pass_pct": "S Pass Holders",
           "nonresident_work_permit_pct": "Work Permit Holders",
           "nonresident_migrant_domestic_worker_pct": "Migrant Domestic Workers",
           "nonresident_ltvp_dp_pct": "Long-Term Visit Pass Holders And "
                                      "Dependant's Pass Holders",
           "nonresident_student_pass_pct": "Student Pass Holders"}
    ms = {k: annual(row(rows["M810791"], "M810791", v), "value")
          for k, v in mig.items()}
    write("migration/nonresident_from_singstat.csv", ["year"] + list(ms),
          [[str(y)] + [f(ms[c].get(y), 1) for c in ms]
           for y in window(ms["nonresident_work_permit_pct"])],
          ["Singapore Department of Statistics, Table Builder M810791: share of "
           "the non-resident population by pass type, at end June, per cent.",
           "Shares OF THE NON-RESIDENT POPULATION, not of total population. "
           "They sum to 100 across pass types in the publisher's table.",
           "2026 is the mid-2026 reading."])

    grant = rows["M810781"]
    print("  M810781 series: " + " | ".join(list(grant)[:8]))

    print("Done. Diff the sidecars before adopting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
