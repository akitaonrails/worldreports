#!/usr/bin/env python3
"""Fetch interest rates and the dollar from the institutions that set them.

Three publishers, each the authority for its own number:

  Federal Reserve Bank of New York — the effective federal funds rate and the
  FOMC's target, from the reference-rates API. The NY Fed is the publisher of
  EFFR, so this is the source rather than a mirror of it.

  US Treasury — the daily par yield curve, for the 10-year note.

  Federal Reserve Board — the H.10 broad nominal dollar index, which happens
  to be based at January 2006 = 100, so it reads directly as "the dollar
  against its trading partners since the start of this atlas".

The Board's Data Download Program is not used: it serves nothing without an
opaque package hash, and the Board announced it is removing the "Build Your
Package" feature. The H.10 summary page is a stable published table.

Outputs:
  data/macro/fed_funds.csv  year,effr_eop,effr_avg,target_eop,target_hi
  data/macro/treasury.csv   year,ten_year_eop,ten_year_avg
  data/macro/dollar.csv     year,broad_index_dec,broad_index_avg,months
  data/macro/mortgage.csv   year,thirty_year_avg,fifteen_year_avg,...

Mortgage rates come from Freddie Mac's Primary Mortgage Market Survey, which
is the published series for US mortgage rates. Freddie Mac is a
government-sponsored enterprise under FHFA conservatorship rather than a
federal agency, which is noted in SOURCES.md: there is no federal-agency
series for the retail mortgage rate since FHFA retired the Monthly Interest
Rate Survey.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "rates"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

NYFED = "https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json"
TREASURY = ("https://home.treasury.gov/resource-center/data-chart-center/"
            "interest-rates/daily-treasury-rates.csv/{y}/all")
H10 = "https://www.federalreserve.gov/releases/h10/summary/jrxwtfb_nm.htm"
PMMS = "https://www.freddiemac.com/pmms/docs/PMMS_history.csv"

YEAR_FROM, YEAR_TO = 2006, 2026

MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], start=1)}


def cached(name: str, fetch) -> str | None:
    """Text from cache, or fetched and cached. A failure returns None so the
    committed CSVs survive an upstream outage."""
    path = CACHE / name
    if path.exists():
        return path.read_text()
    try:
        text = fetch()
    except Exception as e:  # noqa: BLE001
        print(f"  !! {name} failed: {type(e).__name__}: {e}")
        return None
    path.write_text(text)
    return text


def fmt(v: float | None, dec: int = 2) -> str:
    return "" if v is None else f"{v:.{dec}f}"


def mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


# ------------------------------------------------------------------ fed funds
def fed_funds() -> None:
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        text = cached(f"effr_{y}.json", lambda y=y: requests.get(
            NYFED, params={"startDate": f"{y}-01-01", "endDate": f"{y}-12-31"},
            timeout=120).text)
        if text is None:
            rows.append(f"{y},,,,")
            continue
        refs = json.loads(text).get("refRates", [])
        # the API answers newest-first; sorting by date makes "year end" the
        # last business day rather than whichever row arrived last
        refs.sort(key=lambda r: r["effectiveDate"])
        rates = [r["percentRate"] for r in refs
                 if isinstance(r.get("percentRate"), (int, float))]
        last = refs[-1] if refs else {}
        asof = last.get("effectiveDate", "")
        # The LAST reading of the year, kept but never used as the headline
        # policy rate. EFFR can dislocate on the final business day — it
        # printed 3.06% on 31 December 2007 against a 4.25% target — so the
        # target is the policy series and the average is the market one.
        rows.append(f"{y},{fmt(rates[-1] if rates else None)},"
                    f"{fmt(mean(rates))},{fmt(last.get('targetRateFrom'))},"
                    f"{fmt(last.get('targetRateTo'))},{asof},{len(rates)}")
    (DATA / "macro" / "fed_funds.csv").write_text(
        "year,effr_last,effr_avg,target_eop,target_hi,asof,business_days\n"
        + "\n".join(rows) + "\n")
    print("  -> data/macro/fed_funds.csv")


# ------------------------------------------------------------------- treasury
TENORS = ("3 Mo", "2 Yr", "10 Yr", "30 Yr")


def treasury() -> None:
    """The par yield curve, at several tenors, plus the two spreads that are
    read as recession signals. A negative spread is an inverted curve."""
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        text = cached(f"yields_{y}.csv", lambda y=y: requests.get(
            TREASURY.format(y=y),
            params={"type": "daily_treasury_yield_curve",
                    "field_tdr_date_value": y, "_format": "csv"},
            timeout=120).text)
        blank = "," * 11
        if text is None:
            rows.append(f"{y}{blank}")
            continue
        lines = [ln for ln in text.splitlines() if ln.strip()]
        header = csv_split(lines[0])
        cols = {}
        for tenor in TENORS:
            if tenor in header:
                cols[tenor] = header.index(tenor)
        if "10 Yr" not in cols:
            print(f"  !! {y}: no '10 Yr' column")
            rows.append(f"{y}{blank}")
            continue

        # one pass, keeping each tenor's own series: a day can be missing a
        # tenor (the 30-year was not issued between 2002 and 2006) without
        # that dropping the whole day
        series: dict[str, list[tuple[tuple[int, int, int], float]]] = {
            t: [] for t in cols}
        for ln in lines[1:]:
            cells = csv_split(ln)
            try:
                day = as_date(cells[0])
            except (IndexError, ValueError):
                continue
            for tenor, col in cols.items():
                if col < len(cells):
                    try:
                        series[tenor].append((day, float(cells[col])))
                    except ValueError:
                        continue
        for points in series.values():
            points.sort()

        def last(t: str) -> float | None:
            pts = series.get(t) or []
            return pts[-1][1] if pts else None

        def avg(t: str) -> float | None:
            return mean([v for _, v in series.get(t) or []])

        ten = series["10 Yr"]
        asof = ("%04d-%02d-%02d" % ten[-1][0]) if ten else ""
        spread_2 = (None if last("10 Yr") is None or last("2 Yr") is None
                    else last("10 Yr") - last("2 Yr"))
        spread_3m = (None if last("10 Yr") is None or last("3 Mo") is None
                     else last("10 Yr") - last("3 Mo"))
        # the average spread over the year says whether the curve was
        # inverted for the year, not merely on its last day
        avg_2 = (None if avg("10 Yr") is None or avg("2 Yr") is None
                 else avg("10 Yr") - avg("2 Yr"))
        rows.append(",".join([
            str(y),
            fmt(last("3 Mo")), fmt(last("2 Yr")), fmt(last("10 Yr")),
            fmt(last("30 Yr")),
            fmt(avg("3 Mo")), fmt(avg("2 Yr")), fmt(avg("10 Yr")),
            fmt(spread_2), fmt(spread_3m), fmt(avg_2),
            asof, str(len(ten))]))
    (DATA / "macro" / "treasury.csv").write_text(
        "year,three_month_last,two_year_last,ten_year_last,thirty_year_last,"
        "three_month_avg,two_year_avg,ten_year_avg,"
        "spread_10y_2y,spread_10y_3m,spread_10y_2y_avg,asof,trading_days\n"
        + "\n".join(rows) + "\n")
    print("  -> data/macro/treasury.csv")


def mortgages() -> None:
    """Freddie Mac's Primary Mortgage Market Survey — the 30- and 15-year
    fixed rates, which is the series every US mortgage story quotes.

    Weekly, so a year is the average of its weeks and the count is recorded;
    a year with fewer than about 50 weeks is still running.
    """
    text = cached("pmms_history.csv",
                  lambda: requests.get(PMMS, timeout=120).text)
    if text is None:
        print("  -- mortgage.csv left untouched")
        return
    lines = [ln for ln in text.splitlines() if ln.strip()]
    header = [c.strip() for c in lines[0].split(",")]
    try:
        i30, i15 = header.index("pmms30"), header.index("pmms15")
    except ValueError:
        print("  !! PMMS columns not found")
        return
    by_year: dict[int, list[tuple[float | None, float | None]]] = {}
    for ln in lines[1:]:
        cells = [c.strip() for c in ln.split(",")]
        try:
            m, d, y = cells[0].split("/")
            year = int(y)
        except (IndexError, ValueError):
            continue

        def grab(i: int) -> float | None:
            if i >= len(cells) or not cells[i]:
                return None
            try:
                return float(cells[i])
            except ValueError:
                return None

        by_year.setdefault(year, []).append((grab(i30), grab(i15)))

    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        weeks = by_year.get(y, [])
        v30 = [a for a, _ in weeks if a is not None]
        v15 = [b for _, b in weeks if b is not None]
        rows.append(f"{y},{fmt(mean(v30))},{fmt(mean(v15))},"
                    f"{fmt(v30[-1] if v30 else None)},{len(v30)}")
    (DATA / "macro" / "mortgage.csv").write_text(
        "year,thirty_year_avg,fifteen_year_avg,thirty_year_last,weeks\n"
        + "\n".join(rows) + "\n")
    print(f"  -> data/macro/mortgage.csv ({len(by_year)} years in source)")


def csv_split(line: str) -> list[str]:
    """Treasury quotes its column names ("1 Mo") but not its values."""
    return [c.strip().strip('"') for c in
            re.findall(r'"[^"]*"|[^,]+', line)]


def as_date(text: str) -> tuple[int, int, int]:
    """Treasury writes MM/DD/YYYY. Sorting the raw string orders by month,
    so December and January of the same year come back in the wrong order."""
    m, d, y = text.split("/")
    return int(y), int(m), int(d)


# --------------------------------------------------------------------- dollar
def dollar() -> None:
    text = cached("h10_broad_monthly.htm",
                  lambda: requests.get(H10, timeout=120).text)
    if text is None:
        print("  -- dollar.csv left untouched")
        return
    body = re.sub(r"<script.*?</script>", "", text, flags=re.S)
    by_year: dict[int, dict[int, float]] = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, flags=re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr,
                                     flags=re.S)]
        if len(cells) != 2:
            continue
        m = re.fullmatch(r"([A-Z]{3})\s+(\d{4})", cells[0])
        if not m or m.group(1) not in MONTHS:
            continue
        try:
            value = float(cells[1])
        except ValueError:
            continue
        by_year.setdefault(int(m.group(2)), {})[MONTHS[m.group(1)]] = value

    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        got = by_year.get(y, {})
        vals = [got[m] for m in sorted(got)]
        # December, not the latest month: a partial year has no year-end
        # reading, and passing off September as one would be a silent lie
        rows.append(f"{y},{fmt(got.get(12), 4)},{fmt(mean(vals), 4)},{len(vals)}")
    (DATA / "macro" / "dollar.csv").write_text(
        "year,broad_index_dec,broad_index_avg,months\n" + "\n".join(rows) + "\n")
    print(f"  -> data/macro/dollar.csv ({len(by_year)} years parsed)")


def main() -> None:
    print("Fetching rates and the dollar...")
    fed_funds()
    treasury()
    dollar()
    mortgages()
    print("Done.")


if __name__ == "__main__":
    main()
