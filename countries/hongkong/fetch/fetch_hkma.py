"""Hong Kong Monetary Authority — rates, reserves and bank asset quality.

    python3 -m countries.hongkong.fetch.fetch_hkma [--offline]

Writes review sidecars under `data/**/*_from_hkma.csv` only.

Route record (2026-10-25, full detail in DISCOVERY.md):

* `https://api.hkma.gov.hk/public/...` answered **one** request (the daily
  interbank-liquidity figure, HTTP 200, 100 records) and then began
  answering every path with **HTTP 405** and an Aliyun WAF error page
  (`<title>405</title>`), including with a browser User-Agent, `Referer`,
  `Accept-Language`, an XHR header and HTTP/1.0. The API is therefore not a
  reproducible route from this network, and its payload was not kept.
* `https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/...`
  serves the Monthly Statistical Bulletin tables as XLS/XLSX and answers
  200. Those files are the source here.

What is taken from where:

    base rate      BIS WS_CBPOL `D.HK`, whose SOURCE_REF is "Hong Kong
                   Monetary Authority" and whose TITLE is "Official base
                   rate" — the HKMA's own published rate, compiled by the
                   BIS because the HKMA's API is walled. official: false
                   in SOURCES.yaml (a compilation is not the publisher).
    reserves       T0804 foreign currency reserve assets, US$ mn, monthly.
                   This is the national series the World Bank republishes
                   and stops in 2023.
    10y yield      EFBN closing reference, year-end file, note whose
                   remaining maturity is nearest ten years. Exchange Fund
                   Notes are the paper the HKMA issues; there is no
                   conventional government bond curve.
    asset quality  T030601 classified loans (gross) as % of total loans,
                   authorised institutions, quarterly.

`disc_win_base_rate` — the number the HKMA's daily page shows — was captured
by hand in the first (successful) API call: 4.25 on 2026-10-23. That is the
pin for the BIS series, which carries the same rate.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl
import xlrd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "hkma"
DATA = ROOT / "data"

BIS_CBPOL = ("https://stats.bis.org/api/v1/data/WS_CBPOL/D.HK"
             "?format=csv&startPeriod=2005-01-01")
MSB = ("https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/"
       "monthly-statistical-bulletin/{file}")
EFBN = ("https://www.hkma.gov.hk/media/eng/market-data-and-statistics/"
        "monetary-statistics/efbn/attach/{day}_CLOSINGS.xlsx")
UA = {"User-Agent": "curl/8.5.0"}          # BIS 403s a browser string
BROWSER = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
Y0, Y1 = 2005, 2026

# Known values, asserted before a sidecar is written.
CBPOL_PIN = ("2026-10-14", 4.25)            # BIS last observation; the HKMA
#                                             daily page read 4.25 on 2026-10-23
RESERVES_PIN = {2023: 425_554,             # US$ mn at end-2023: exactly the
                2024: 421_503}             # figure World Bank FI.RES.TOTL.CD carries
ASSET_PIN = {(2024, "Dec"): 1.965}          # % classified loans, end-2024


class FetchError(SystemExit):
    pass


def fail(msg: str) -> None:
    print(f"fetch_hkma: {msg}", file=sys.stderr)
    sys.exit(1)


def grab(url: str, name: str, offline: bool, headers: dict,
         soft: bool = False) -> bytes | None:
    """Fetch and cache a file. `soft` turns a 404 into None (a holiday)."""
    cache_file = CACHE / name
    if cache_file.exists():
        return cache_file.read_bytes()
    if offline:
        if soft:
            return None            # a day with no file, offline: nothing to read
        fail(f"offline and no cached file {cache_file}")
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            if body[:1] == b"<":
                raise ValueError("HTML where a data file was expected")
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(body)
            return body
        except urllib.error.HTTPError as e:  # noqa: PERF203
            if soft and e.code == 404:
                return None           # a holiday, or the archive's start
            last = e
            time.sleep(3 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    fail(f"{url}: {last}")


# --------------------------------------------------------------------------
# base rate
# --------------------------------------------------------------------------
def base_rate(offline: bool) -> dict[int, float]:
    body = grab(BIS_CBPOL, "cbpol_hk.csv", offline, UA)
    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8"))))
    daily = {}
    for r in rows:
        v = r.get("OBS_VALUE", "")
        if v in ("", "NaN"):
            continue
        daily[r["TIME_PERIOD"]] = float(v)
    if daily.get(CBPOL_PIN[0]) is None or \
            abs(daily[CBPOL_PIN[0]] - CBPOL_PIN[1]) > 0.001:
        fail(f"BIS CBPOL: {CBPOL_PIN[0]} = {daily.get(CBPOL_PIN[0])!r}, "
             f"expected {CBPOL_PIN[1]}")
    out = DATA / "markets/base_rate_daily_from_hkma.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["date", "base_rate"])
        fmt = lambda v: f"{v:g}"                     # noqa: E731
        for day in sorted(daily):
            w.writerow([day, fmt(daily[day])])
    print(f"  {out.relative_to(ROOT)}  ({len(daily)} days, "
          f"{min(daily)}..{max(daily)})")
    annual: dict[int, list[float]] = {}
    for day, v in daily.items():
        annual.setdefault(int(day[:4]), []).append(v)
    out = DATA / "markets/base_rate_from_hkma.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["year", "base_rate"])
        for year in sorted(annual):
            obs = annual[year]
            w.writerow([year, f"{sum(obs) / len(obs):.3f}"])
    print(f"  {out.relative_to(ROOT)}  ({len(annual)} years, annual mean)")
    return {y: sum(v) / len(v) for y, v in annual.items()}


# --------------------------------------------------------------------------
# reserves
# --------------------------------------------------------------------------
def reserves(offline: bool) -> None:
    body = grab(MSB.format(file="T0804.xlsx"), "T0804.xlsx", offline, BROWSER)
    wb = openpyxl.load_workbook(io.BytesIO(body), data_only=True)
    sh = wb[wb.sheetnames[0]]
    year, last = None, {}
    for row in sh.iter_rows(min_row=1, max_col=8, values_only=True):
        y, month, value = row[0], row[1], row[4]
        if isinstance(y, (int, float)) and 1990 <= y <= 2100:
            year = int(y)
        if year is None or not isinstance(month, str):
            continue
        if not isinstance(value, (int, float)):
            continue
        last[(year, month.strip()[:3])] = float(value)
    if not last:
        fail("T0804: no reserve observations parsed")
    years = {}
    for (y, m), v in sorted(last.items()):
        if m == "Dec" or (y not in years and m in ("Sep", "Jun", "Mar")):
            years[y] = v
    if abs(years.get(2024, 0) - RESERVES_PIN[2024]) > 1:
        fail(f"T0804: 2024 reserve assets {years.get(2024)!r} US$mn, "
             f"expected {RESERVES_PIN[2024]}")
    out = DATA / "world/reserves_national_from_hkma.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["year", "reserves_usd_mn"])
        for y in sorted(years):
            w.writerow([y, f"{years[y]:.0f}"])
    print(f"  {out.relative_to(ROOT)}  ({len(years)} years, "
          f"{min(years)}..{max(years)})")


# --------------------------------------------------------------------------
# bank asset quality
# --------------------------------------------------------------------------
def asset_quality(offline: bool) -> None:
    body = grab(MSB.format(file="T030601.xls"), "T030601.xls", offline, BROWSER)
    book = xlrd.open_workbook(file_contents=body)
    sh = book.sheet_by_index(0)
    year, obs = None, {}
    for r in range(sh.nrows):
        y = sh.cell_value(r, 0)
        month = sh.cell_value(r, 1)
        # column 8 is the "Total" of substandard + doubtful + loss,
        # i.e. gross classified loans; columns 5-7 are the three grades.
        value = sh.cell_value(r, 8)
        if isinstance(y, float) and 1990 <= y <= 2100:
            year = int(y)
        if year is None or not isinstance(month, str):
            continue
        if month.strip() not in ("Mar", "Jun", "Sep", "Dec"):
            continue
        if isinstance(value, float):
            obs[(year, month.strip())] = value
    if obs.get((2024, "Dec")) is None or \
            abs(obs[(2024, "Dec")] - ASSET_PIN[(2024, "Dec")]) > 0.02:
        fail(f"T030601: 2024 Q4 classified loans {obs.get((2024, 'Dec'))!r}, "
             f"expected {ASSET_PIN[(2024, 'Dec')]}")
    out = DATA / "credit/classified_loans_from_hkma.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["year", "quarter", "classified_loans_pct"])
        for (y, m) in sorted(obs):
            w.writerow([y, {"Mar": "Q1", "Jun": "Q2", "Sep": "Q3",
                            "Dec": "Q4"}[m],
                        f"{obs[(y, m)]:.4f}"])
    print(f"  {out.relative_to(ROOT)}  ({len(obs)} quarters, "
          f"{min(obs)[0]}..{max(obs)[0]})")


# --------------------------------------------------------------------------
# Exchange Fund Note yield nearest ten years, year-end
# --------------------------------------------------------------------------
def _note_yield(book, as_of: date):
    """(issue, maturity, yield %, remaining years) of the on-the-run 10-year
    Exchange Fund Note, or None when no 10-year note is outstanding.

    The closing-reference workbook lists every outstanding note with its
    issue number, maturity date (a datetime cell) and closing yield. Notes
    are coded by original tenor, so `10Y...` is a ten-year issue: selecting
    by the code keeps a 15-year note from being passed off as a ten-year
    one, which is what a "nearest maturity" rule would do from 2024, when
    the HKMA stopped issuing ten-year paper.
    """
    best = None
    sh = book["NOTES"]
    for row in sh.iter_rows(min_row=13, max_col=8, values_only=True):
        issue, maturity, yld = row[1], row[3], row[7]
        if not isinstance(issue, str) or not issue.strip().upper().startswith("10Y"):
            continue
        if isinstance(maturity, str):
            try:
                mat = date.fromisoformat(maturity[:10])
            except ValueError:
                continue
        elif isinstance(maturity, datetime):
            mat = maturity.date()
        else:
            continue
        if not isinstance(yld, (int, float)):
            continue
        years = (mat - as_of).days / 365.25
        if years <= 0:
            continue
        if best is None or years < best[3]:
            best = (issue.strip(), mat.isoformat(), float(yld), years)
    return best


def efn_ten_year(offline: bool) -> None:
    """Year-end closing yields: last business day of December, at most five
    days back. Weekends carry no file, so they are not requested at all."""
    dates = []
    for year in range(Y0, Y1 + 1):
        d, tries = date(year, 12, 31), 0
        while tries < 5:
            if d.weekday() < 5:
                dates.append((year, d))
                tries += 1
            d -= timedelta(days=1)
    picked: dict[int, tuple] = {}
    for year, d in dates:
        if year in picked:
            continue
        name = f"EFBN_{d.strftime('%Y%m%d')}.xlsx"
        url = EFBN.format(day=d.strftime("%Y%m%d"))
        body = grab(url, name, offline, BROWSER, soft=True)
        if body is None:
            continue                     # a holiday, or no file that day
        wb = openpyxl.load_workbook(io.BytesIO(body), data_only=True)
        if "NOTES" not in wb.sheetnames:
            continue
        got = _note_yield(wb, d)
        if got:
            picked[year] = (d.isoformat(),) + got
    if not picked:
        fail("EFBN: no year-end closing file parsed")
    # A PROBE, not a yield series: see the docstring and DISCOVERY.md. The
    # only 10Y-coded notes outstanding at these year-ends had under two
    # years left, so their closing yield is not a ten-year benchmark and is
    # never staged as one.
    out = DATA / "markets/efn_tenor_probe_from_hkma.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["year", "as_of", "issue", "maturity",
                    "yield_pct", "remaining_years"])
        for y in sorted(picked):
            as_of, issue, maturity, yld, years = picked[y]
            w.writerow([y, as_of, issue, maturity, f"{yld:.3f}",
                        f"{years:.2f}"])
    print(f"  {out.relative_to(ROOT)}  ({len(picked)} years, "
          f"{min(picked)}..{max(picked)}) — tenor probe, no benchmark")


def main(argv: list[str]) -> None:
    offline = "--offline" in argv
    base_rate(offline)
    reserves(offline)
    asset_quality(offline)
    efn_ten_year(offline)


if __name__ == "__main__":
    main(sys.argv[1:])
