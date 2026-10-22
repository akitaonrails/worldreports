#!/usr/bin/env python3
"""Refresh the Bank of England series into sidecar CSVs.

Usage:  python3 -I countries/united-kingdom/fetch/fetch_boe.py

Two channels, both publisher-of-record:

**The Interactive Database (IADB) CSV endpoint.** fromshowcolumns.asp
302-redirects to /boeapps/database/_iadb-FromShowColumns.asp (urllib
follows it), then serves application/csv with a `DATE,<CODE>...` header
and `dd Mmm yyyy` dates. A BOGUS series code does not 404: it answers an
HTML error page under HTTP 200, so the header row is shape-checked before
anything is cached — a cached error page survives the retry that would
have fixed it. Codes:

  IUDBEDR    Bank Rate (daily, %)
  XUDLUSS    sterling spot vs US$ (daily, USD per GBP)
  XUDLBK67   sterling effective exchange rate index (daily)
  IUDMNPY    10-year nominal zero-coupon gilt yield (daily, %)
  IUMZICQ    quoted 2-year fixed 60%-LTV mortgage rate (monthly, %, NSA)
  IUMTLMV    quoted revert-to-rate mortgage rate (monthly, %, NSA)
  LPMBZ2A    lending to individuals, amounts outstanding (monthly, £m, SA)
  LPMVTXK    ... of which secured on dwellings (monthly, £m, SA)
  LPMBI2O    ... of which consumer credit (monthly, £m, SA)

The IUM* quoted-rate codes are only used after their product description
is pulled from the html.x=yes view and asserted — IUMTLMV answers with
numbers even if you pick it for the wrong product, so the description is
the check. The LPM* codes are the IADB form of the Bankstats mnemonics
(BZ2A, VTXK, BI2O — prefix LPM; the bare mnemonics are REJECTED by the
IADB with an "Invalid series code" error page, verified 2026-10-22).
LPQAUYN is NOT here: it looks like household debt and is actually
quarterly M4 broad money (£3.1tn) — verified description, do not use.

**The Money and credit release xlsx (Tables A–K).** The release page URL
carries the edition (/statistics/money-and-credit/<year>/<month>-<year>)
and stub pages for unpublished months exist WITHOUT the workbook link,
so the fetcher walks back from the current month and takes the first
page that links a tables-a-and-k xlsx. The workbook's summary tables
carry only the latest few months; their role here is to PIN the series:
the fetcher asserts the codes printed in the tables match the ones it
pulls from the IADB, and asserts the latest overlapping monthly stock
matches to the £m. Table letters are not stable across editions (the
discovery pass called lending to individuals "Table G"; the August 2026
edition letters it Table A), so sheets are found by TITLE, never letter.
The stocks are monthly STOCKS: a year is its December reading (the
running year its latest month, labelled by asof_month), never the sum of
the months — Spain's NPL-fetcher trap.

Outputs are `_from_boe` sidecars. Nothing here overwrites a curated file.
"""
from __future__ import annotations

import csv
import html
import re
import statistics
import time
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
IADB = "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp"
RELEASE_PAGE = ("https://www.bankofengland.co.uk/statistics/"
                "money-and-credit/{year}/{month}-{year}")
UA = {"User-Agent": "Mozilla/5.0 (worldreports data fetcher)"}
Y0, Y1 = 2006, 2026

DAILY = {
    "bank_rate": "IUDBEDR",
    "usd_per_gbp": "XUDLUSS",
    "eri": "XUDLBK67",
    "gilt_10y": "IUDMNPY",
}
MONTHLY = {
    "mortgage_2y_60ltv": "IUMZICQ",
    "mortgage_revert": "IUMTLMV",
    "lending_individuals": "LPMBZ2A",
    "lending_secured": "LPMVTXK",
    "consumer_credit": "LPMBI2O",
}

# What the html.x=yes description must say before a quoted-rate series is
# trusted: the code alone does not say which mortgage product it quotes.
DESCRIPTIONS = {
    "IUMZICQ": ["2 year", "(60% LTV)", "mortgage", "households"],
    "IUMTLMV": ["revert-to-rate", "mortgage", "households"],
}

# Money-and-credit tables pin the lending stocks: sheet title fragment ->
# (series name, the Bankstats mnemonic the table must print).
MC_TABLES = {
    "Lending to individuals": ("lending_individuals", "BZ2A"),
    "Lending secured on dwellings": ("lending_secured", "VTXK"),
    "Consumer credit": ("consumer_credit", "BI2O"),
}

MONTH_NAME = re.compile(r"^[A-Z][a-z]{2} \d{4}$")


def get(url: str, binary=False, retries=4):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                blob = r.read()
            return blob if binary else blob.decode("utf-8")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"boe: {url}: {last}")


def parse_date(text: str) -> str:
    """`02 Jan 2019` (and the documented `02-Jan-2019`) to ISO."""
    for fmt in ("%d %b %Y", "%d-%b-%Y"):
        try:
            return time.strftime("%Y-%m-%d", time.strptime(text, fmt))
        except ValueError:
            continue
    raise ValueError(f"unrecognised IADB date: {text!r}")


def fetch_iadb(series: dict[str, str]) -> dict[str, list[tuple[str, float]]]:
    """{name: [(iso date, value)] ascending} for the requested series."""
    CACHE.mkdir(exist_ok=True)
    codes = ",".join(series.values())
    cache_file = CACHE / f"boe_iadb_{codes.replace(',', '_')}.csv"
    if cache_file.exists():
        text = cache_file.read_text()
    else:
        url = (f"{IADB}?csv.x=yes&Datefrom=01/Jan/{Y0}&Dateto=31/Dec/{Y1}"
               f"&SeriesCodes={codes}&UsingCodes=Y&VPD=Y&VFD=N")
        text = get(url)
        # The shape check: a bogus code answers an HTML page under HTTP
        # 200, so the first line must be exactly DATE,<codes>.
        header = text.splitlines()[0].strip() if text.strip() else ""
        if header != f"DATE,{codes}":
            raise RuntimeError(
                f"iadb: expected header DATE,{codes!s}, got {header[:80]!r}"
                " — the endpoint serves HTML under HTTP 200 for bad codes")
        cache_file.write_text(text)
    out: dict[str, list[tuple[str, float]]] = {n: [] for n in series}
    reader = csv.reader(text.splitlines())
    cols = next(reader)
    for row in reader:
        if not row or not row[0].strip():
            continue
        day = parse_date(row[0].strip())
        for name, code in series.items():
            i = cols.index(code)
            if i < len(row) and row[i].strip():
                out[name].append((day, float(row[i])))
    for name, pairs in out.items():
        if not pairs:
            raise RuntimeError(f"iadb: no observations for {series[name]}")
        pairs.sort()
    return out


def describe(code: str) -> str:
    """The series description from the IADB html view, as plain text.

    The html view wraps the description across one-word table cells just
    before the cell holding the series code; everything after the
    "Series 1 to N" header up to the code is the description.
    """
    cache_file = CACHE / f"boe_desc_{code}.html"
    if cache_file.exists():
        text = cache_file.read_text()
    else:
        text = get(f"{IADB}?html.x=yes&Datefrom=01/Jan/2024"
                   f"&Dateto=31/Dec/2024&SeriesCodes={code}"
                   "&UsingCodes=Y&VPD=Y&VFD=N")
        if code not in text:
            raise RuntimeError(f"iadb html view: no {code} in response")
        cache_file.write_text(text)
    seg = text[:text.find(code)]
    seg = re.sub(r"<script.*?</script>", " ", seg, flags=re.S)
    plain = html.unescape(re.sub(r"<[^>]+>", " ", seg))
    plain = re.sub(r"\s+", " ", plain)
    m = re.search(r"Series 1 to \d+\s*(.+)$", plain)
    if not m or not m.group(1).strip():
        raise RuntimeError(f"iadb html view: no description found for {code}")
    return m.group(1).strip()


def money_credit_workbook() -> openpyxl.Workbook:
    """The latest Tables A–K workbook, resolved from the release pages.

    Release pages for unpublished months exist as stubs without the xlsx
    link, so walking back from the current month and taking the first
    page that links a tables-a-and-k workbook lands the latest edition.
    """
    today = date.today()
    month_names = [""] + [time.strftime("%B", (2000, m, 1, 0, 0, 0, 0, 0, 0))
                          for m in range(1, 13)]
    link = None
    for back in range(0, 9):
        y = today.year if today.month - back > 0 else today.year - 1
        m = (today.month - back - 1) % 12 + 1
        page = get(RELEASE_PAGE.format(year=y, month=month_names[m].lower()))
        found = re.search(
            r'href="(/-/media/boe/files/statistics/money-and-credit/'
            r'[^"]*tables-a-and-k[^"]*\.xlsx)"', page)
        if found:
            link = found.group(1)
            print(f"  money-and-credit edition: "
                  f"{month_names[m].lower()} {y}")
            break
    if not link:
        raise RuntimeError("no tables-a-and-k workbook found in the last "
                           "nine months of money-and-credit releases")
    local = CACHE / f"boe_{Path(link).name}"
    if not local.exists():
        blob = get("https://www.bankofengland.co.uk" + link, binary=True)
        # An error page under HTTP 200 is not a workbook: every xlsx is a
        # zip, so the magic number is the cheapest possible check.
        if blob[:2] != b"PK":
            raise RuntimeError("the money-and-credit download is not a "
                               "workbook")
        local.write_bytes(blob)
    return openpyxl.load_workbook(local, data_only=True, read_only=True)


def pin_lending(wb: openpyxl.Workbook) -> dict[str, tuple[str, float]]:
    """Latest monthly stock per lending series, from the summary tables.

    Returns {series: ("Mon YYYY", value in £ billions)} after asserting
    the sheet (found by TITLE — letters move between editions) prints the
    Bankstats mnemonic the fetcher expects.
    """
    out = {}
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        rows = list(ws.iter_rows(values_only=True))
        title = next((str(c) for row in rows[:3] for c in row if c), "")
        for fragment, (name, mnemonic) in MC_TABLES.items():
            if name in out or fragment not in title:
                continue
            if "by category" in title:
                continue          # Table C: the category split, not the total
            code_row = next((r for r in rows if mnemonic in
                             [str(c).strip() for c in r if c]), None)
            if code_row is None:
                raise RuntimeError(f"{title!r}: expected code {mnemonic}")
            col = [str(c).strip() if c else "" for c in code_row].index(mnemonic)
            months = [(str(r[2]), float(r[col])) for r in rows
                      if len(r) > col and r[2] and MONTH_NAME.match(str(r[2]))
                      and isinstance(r[col], (int, float))]
            if not months:
                raise RuntimeError(f"{title!r}: no monthly rows found")
            label, value = months[-1]
            out[name] = (label, value)
            print(f"  pinned {mnemonic} ({title.split(':')[0]}, "
                  f"latest {label}): {value}")
    missing = [n for _, (n, _) in MC_TABLES.items() if n not in out]
    if missing:
        raise RuntimeError(f"money-and-credit tables not found: {missing}")
    return out


def by_year(obs: list[tuple[str, float]]) -> dict[int, list[float]]:
    years: dict[int, list[float]] = defaultdict(list)
    for day, value in obs:
        years[int(day[:4])].append(value)
    return years


def months_of(obs: list[tuple[str, float]]) -> dict[int, set[int]]:
    out: dict[int, set[int]] = defaultdict(set)
    for day, _ in obs:
        out[int(day[:4])].add(int(day[5:7]))
    return out


def write(rel: str, comments: list[str], header: list[str],
          rows: list[list]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        for comment in comments:
            fh.write(f"# {comment}\n")
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"  data/{rel}  {len(rows)} rows")


def main() -> None:
    print("Bank of England (IADB + Money and credit release)")
    raw = {**fetch_iadb(DAILY), **fetch_iadb(MONTHLY)}
    series = {name: by_year(obs) for name, obs in raw.items()}
    months = {name: months_of(obs) for name, obs in raw.items()}
    running = max(int(d[:4]) for obs in raw.values() for d, _ in obs)

    # The quoted-rate codes are used only once their descriptions say the
    # product they quote; a code that stops matching is a wrong series
    # that still answers with plausible numbers.
    for name in ("mortgage_2y_60ltv", "mortgage_revert"):
        code = MONTHLY[name]
        desc = describe(code)
        missing = [w for w in DESCRIPTIONS[code] if w not in desc]
        if missing:
            raise RuntimeError(
                f"{code} description no longer matches {missing}: {desc!r}")
        print(f"  {code}: {desc}")

    # The must-verify anchors, checked against the daily/monthly rows
    # themselves, not the aggregated output.
    jan20 = [v for d, v in raw["bank_rate"] if d.startswith("2020-01")]
    if not jan20 or min(jan20) != max(jan20) or jan20[0] != 0.75:
        raise RuntimeError(f"Bank Rate Jan-2020 must be 0.75 throughout, "
                           f"got {sorted(set(jan20))}")
    fx = dict(raw["usd_per_gbp"])
    if fx.get("2020-01-02") != 1.3189:
        raise RuntimeError(f"USD per GBP 02-Jan-2020 must be 1.3189, got "
                           f"{fx.get('2020-01-02')}")
    # 0.85 is the first reading of January 2020 (02-Jan = 0.8523); the
    # month's mean is 0.72 because the yield slid all month — the
    # discovery pass recorded the start-of-month figure.
    gilt = dict(raw["gilt_10y"])
    if not gilt.get("2020-01-02") or abs(gilt["2020-01-02"] - 0.85) > 0.01:
        raise RuntimeError(f"10y gilt zero-coupon 02-Jan-2020 must be "
                           f"~0.85, got {gilt.get('2020-01-02')}")

    # The money-and-credit workbook pins the lending codes and the latest
    # stock (the tables carry £ billions; the IADB carries £ millions).
    pinned = pin_lending(money_credit_workbook())
    for name, (label, gbp_bn) in pinned.items():
        y, m = time.strptime(label, "%b %Y")[0:2]
        iadb = {(int(d[:4]), int(d[5:7])): v for d, v in raw[name]}
        if (y, m) not in iadb:
            raise RuntimeError(f"{name}: table month {label} not in the "
                               "IADB series")
        if abs(iadb[(y, m)] / 1000 - gbp_bn) > 0.01:
            raise RuntimeError(f"{name}: IADB {iadb[(y, m)] / 1000} £bn vs "
                               f"table {gbp_bn} £bn for {label}")

    def avg(name, year, nd=2):
        """The annual mean, or blank when the year is not wholly covered.

        The running year is the one exception: it is incomplete by
        definition and the plate hatches it, so it is emitted.
        """
        vals = series[name].get(year)
        if not vals:
            return ""
        if len(months[name][year]) < 12 and year < running:
            return ""
        return round(statistics.fmean(vals), nd)

    def last(name, year, nd=2):
        vals = series[name].get(year)
        return round(vals[-1], nd) if vals else ""

    years = range(Y0, running + 1)

    write("markets/bank_rate_from_boe.csv",
          ["Bank Rate, per cent. avg is the mean of the year's daily "
           "readings, eoy the last; the running year is a partial average "
           "over the months published so far."],
          ["year", "bank_rate_avg", "bank_rate_eoy"],
          [[y, avg("bank_rate", y), last("bank_rate", y)] for y in years])

    write("markets/sterling_from_boe.csv",
          ["usd_per_gbp is USD PER GBP (XUDLUSS): a FALLING line is a "
           "WEAKER pound — the opposite direction from Canada's usdcad "
           "(CAD per USD, where a falling line is a stronger dollar). "
           "eri is the sterling effective exchange rate index (XUDLBK67) "
           "as published."],
          ["year", "usd_per_gbp_avg", "usd_per_gbp_eoy", "eri_avg",
           "eri_eoy"],
          [[y, avg("usd_per_gbp", y, 4), last("usd_per_gbp", y, 4),
            avg("eri", y, 4), last("eri", y, 4)] for y in years])

    write("markets/gilt_yield_from_boe.csv",
          ["10-year nominal zero-coupon spot yield from the Bank's "
           "estimated gilt curve (IUDMNPY), per cent — not a "
           "benchmark-bond quote."],
          ["year", "gilt_10y_avg", "gilt_10y_eoy"],
          [[y, avg("gilt_10y", y, 4), last("gilt_10y", y, 4)]
           for y in years])

    write("credit/mortgage_rate_from_boe.csv",
          ["Quoted new-business mortgage rates to households, per cent, "
           "NSA — monthly series, annual mean; NOT the average rate on "
           "the stock of mortgages. mortgage_2y_60ltv is the 2-year fixed "
           "60% LTV quote (IUMZICQ); mortgage_revert is the sterling "
           "revert-to-rate quote (IUMTLMV). Both product descriptions "
           "are re-verified from the IADB on every refresh."],
          ["year", "mortgage_2y_60ltv_avg", "mortgage_revert_avg"],
          [[y, avg("mortgage_2y_60ltv", y, 3), avg("mortgage_revert", y, 3)]
           for y in years])

    # Monthly STOCKS: a year is its December reading, never the sum of
    # the months; the running year is its latest month, labelled.
    def whole(v: float) -> str:
        """£m stocks arrive as whole numbers; %g would print them in
        scientific notation at six significant figures."""
        return str(int(v)) if v == int(v) else str(v)

    rows = []
    for y in years:
        cells, asof = [], ""
        for name in ("lending_individuals", "lending_secured",
                     "consumer_credit"):
            vals = series[name].get(y)
            if not vals:
                cells.append("")
                continue
            dec = months[name][y]
            if 12 in dec:
                idx = [i for i, (d, _) in enumerate(raw[name])
                       if d.startswith(f"{y}-12")][-1]
                cells.append(whole(raw[name][idx][1]))
                asof = "12"
            elif y == running:
                cells.append(whole(vals[-1]))
                asof = f"{max(dec):02d}"
            else:
                cells.append("")
        rows.append([y, *cells, asof])
    write("credit/lending_from_boe.csv",
          ["Monthly STOCKS of sterling lending to individuals, "
           "£ millions, seasonally adjusted (IADB LPMBZ2A total, "
           "LPMVTXK secured on dwellings, LPMBI2O consumer credit — the "
           "codes pinned against the latest Money and credit Tables A–K "
           "workbook, whose summary tables carry only the latest months "
           "in £ billions). A year is its DECEMBER reading — never the "
           "sum of the months; the running year is its latest month and "
           "asof_month says which."],
          ["year", "lending_individuals_gbp_mn",
           "lending_secured_dwellings_gbp_mn", "consumer_credit_gbp_mn",
           "asof_month"],
          rows)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
