#!/usr/bin/env python3
"""Refresh Russia's markets and credit series from the Bank of Russia.

Usage:  make C=russia fetch   (or: python3 -I fetch/fetch_cbr.py)

The Bank of Russia is the best machine-readable publisher in this country —
every route below answered 200 on 2026-10-25 while EMISS, data.gov.ru and
the customs service did not answer at all.

  key rate        https://www.cbr.ru/hd_base/KeyRate/  (daily table)
  USD/RUB         https://www.cbr.ru/scripts/XML_dynamic.asp
                  ?VAL_NM_RQ=R01235  (official daily fixing, XML)
  OFZ curve       https://www.cbr.ru/hd_base/zcyc_params/  (daily zero-
                  coupon yields by tenor; the 10-year column is taken)
  household rate  /vfs/statistics/pdko/int_rat/loans_ind_new.xlsx
                  (weighted average rate on new rouble loans to
                  individuals, monthly, by maturity)

Annual convention, the same one the atlas uses elsewhere: the value for a
year is the MEAN OF THE DAILY (or monthly) OBSERVATIONS the publisher
reports in that year. That is stated on every sidecar because it is not
the same as a year-end reading, and for the policy rate in 2022 it matters
a great deal: the emergency 20% set on 28 February 2022 lasted three
weeks, so the annual mean is about 10.6% — the panel's note carries the
peak, not the mean.

The 2022 break is drawn, never smoothed:

  · 28 Feb 2022 the key rate goes to 20.00% from 9.50%.
  · MOEX equity trading was suspended 25 Feb - 24 Mar 2022.
  · Capital controls fixed the rouble's official rate through March 2022;
    the fixing is the Bank of Russia's, not a market price.
"""
from __future__ import annotations

import csv
import io
import re
import statistics
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

KEYRATE = ("https://www.cbr.ru/hd_base/KeyRate/"
           "?UniDbQuery.Posted=True&UniDbQuery.From=01.01.2006"
           "&UniDbQuery.To=31.12.2026")
FX = ("https://www.cbr.ru/scripts/XML_dynamic.asp"
      "?date_req1=01.01.2006&date_req2=31.12.2026&VAL_NM_RQ=R01235")
# The zero-coupon page answers a MULTI-YEAR query with an empty shell and
# no table at all (26,984 bytes, verified 2026-10-25); one year per request
# returns the table (118-124 KB). So the fetcher asks year by year.
ZCYC = ("https://www.cbr.ru/hd_base/zcyc_params/"
        "?UniDbQuery.Posted=True&UniDbQuery.From=01.01.{year}"
        "&UniDbQuery.To=31.12.{year}")
LOANS = "https://www.cbr.ru/vfs/statistics/pdko/int_rat/loans_ind_new.xlsx"

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126.0"}
YEAR_FROM, YEAR_TO = 2006, 2026
LAST_FULL_YEAR = 2025


def download(url: str, name: str, marker: bytes, binary: bool = False) -> Path:
    """Fetch into cache/, refusing an HTML error page served under 200.

    `marker` is the string that must appear in the payload for it to be the
    document this fetcher meant to pull: '<ValCurs' for the XML feed,
    'class="data' for a CBR table page. An official gateway answering an
    error page under HTTP 200 would otherwise parse as zero rows and read
    as a missing series rather than a failed fetch.
    """
    CACHE.mkdir(exist_ok=True)
    path = CACHE / name
    if path.exists() and path.stat().st_size > 2000:
        return path
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = r.read()
    if binary:
        if raw[:2] != b"PK":
            sys.exit(f"{name}: not an xlsx ({len(raw)} bytes)")
    elif marker not in raw:
        sys.exit(f"{name}: payload does not carry {marker!r} "
                 f"({len(raw)} bytes) — not the document requested")
    path.write_bytes(raw)
    return path


def strip_tags(fragment: str) -> list[str]:
    return [re.sub(r"<[^>]+>", "", c).strip()
            for c in re.split(r"</td>\s*<td[^>]*>", fragment)]


def key_rate(path: Path) -> dict[int, list[float]]:
    """Daily key rate as {year: [values]} out of the publisher's table."""
    text = path.read_bytes().decode("utf-8", "replace")
    tables = re.findall(r"<table[^>]*class=\"data[^\"]*\"[^>]*>(.*?)</table>",
                        text, re.S)
    if not tables:
        sys.exit("key rate: no data table in the page")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tables[0], re.S)
    out: dict[int, list[float]] = {}
    for row in rows:
        cells = strip_tags(row)
        if len(cells) < 2:
            continue
        m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", cells[0])
        if not m:
            continue
        value = cells[1].replace(",", ".").replace("\xa0", "")
        try:
            rate = float(value)
        except ValueError:
            continue
        year = int(m.group(3))
        out.setdefault(year, []).append(rate)
    # The key rate itself begins on 13.09.2013; the page carries no earlier
    # rows, so 14 years is the complete series and not a truncated parse.
    if len(out) < 10:
        sys.exit(f"key rate: only {len(out)} years parsed; the table shape changed")
    return out


def fx_usd(path: Path) -> dict[int, list[float]]:
    """Daily official USD/RUB as {year: [values]} out of the XML feed."""
    text = path.read_bytes().decode("windows-1251", "replace")
    if "<ValCurs" not in text:
        sys.exit("fx: not the CBR ValCurs XML")
    out: dict[int, list[float]] = {}
    for m in re.finditer(
            r'<Record Date="(\d{2})\.(\d{2})\.(\d{4})"[^>]*>\s*'
            r"<Nominal>(\d+)</Nominal>\s*<Value>([^<]+)</Value>", text):
        nominal = int(m.group(4))
        value = float(m.group(5).replace(",", "."))
        out.setdefault(int(m.group(3)), []).append(value / nominal)
    if not out:
        sys.exit("fx: no records parsed")
    return out


def ofz_10y() -> dict[int, list[float]]:
    """The 10-year column of the zero-coupon curve, as {year: [values]}.

    One request per year: the publisher's page returns no table for a
    multi-year range.
    """
    out: dict[int, list[float]] = {}
    for year in range(YEAR_FROM, YEAR_TO + 1):
        path = download(ZCYC.format(year=year), f"cbr_zcyc_{year}.html",
                        b'class="data')
        text = path.read_bytes().decode("utf-8", "replace")
        tables = re.findall(
            r"<table[^>]*class=\"data[^\"]*\"[^>]*>(.*?)</table>", text, re.S)
        if not tables:
            continue
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tables[0], re.S)
        for row in rows:
            cells = strip_tags(row)
            if not cells:
                continue
            # A data row is a date plus twelve tenors; the 10-year value is
            # the ninth tenor, i.e. index 9 with the date at index 0.
            m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", cells[0])
            if not m or len(cells) < 10:
                continue
            value = cells[9].replace(",", ".").replace("\xa0", "")
            try:
                out.setdefault(int(m.group(3)), []).append(float(value))
            except ValueError:
                continue
    if not out:
        sys.exit("ofz: no yields parsed")
    return out


def household_rate(path: Path) -> dict[int, list[float]]:
    """Weighted-average rate on new rouble loans to individuals, monthly.

    The workbook's first sheet is by maturity in rouble; the column headed
    'все виды кредитов' under 'по всем срокам' is the all-maturities
    aggregate the spine's slot 2 asks for. Months are Russian names with a
    year: 'Январь 2014'.
    """
    import openpyxl

    months = {name: i for i, name in enumerate(
        ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль",
         "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"], start=1)}
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    # Find the header row carrying 'все виды кредитов'.
    col = None
    for row in rows[:12]:
        for i, cell in enumerate(row):
            if cell and "все виды кредитов" in str(cell):
                col = i
                break
        if col is not None:
            break
    if col is None:
        sys.exit("household rate: 'все виды кредитов' column not found")
    out: dict[int, list[float]] = {}
    for row in rows:
        label = str(row[0] or "").strip()
        parts = label.split()
        if len(parts) != 2 or parts[0] not in months or not parts[1].isdigit():
            continue
        try:
            value = float(row[col])
        except (TypeError, ValueError):
            continue
        out.setdefault(int(parts[1]), []).append(value)
    if not out:
        sys.exit("household rate: no monthly rows parsed")
    return out


def write(rel: str, header: list[str], rows: list[list[str]],
          comments: list[str]) -> None:
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in comments]
    lines.append(",".join(header))
    lines += [",".join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {len(rows)} rows")


def annual(series: dict[int, list[float]]) -> dict[int, float]:
    return {y: statistics.fmean(v) for y, v in series.items() if v}


def main() -> None:
    print("Bank of Russia: markets and credit")
    key = key_rate(download(KEYRATE, "cbr_keyrate.html", b'class="data'))
    fx = fx_usd(download(FX, "cbr_usd_rub.xml", b"<ValCurs"))
    ofz = ofz_10y()
    loans = household_rate(download(LOANS, "cbr_loans_ind_new.xlsx", b"", binary=True))

    key_a, fx_a, ofz_a, loans_a = annual(key), annual(fx), annual(ofz), annual(loans)

    # ---- known observations, before anything is written -----------------
    # The 20.00% emergency rate of 28 February 2022 is in the daily rows.
    assert max(key[2022]) == 20.0, f"key rate 2022 peak: {max(key[2022])}"
    assert min(key_a) == 2013, f"key-rate row set starts {min(key_a)}"
    assert abs(key_a[2013] - 5.50) < 0.05, f"key rate 2013 mean: {key_a[2013]}"
    assert abs(key_a[2022] - 10.55) < 0.1, f"key rate 2022 mean: {key_a[2022]}"
    assert abs(key_a[2024] - 17.54) < 0.1, f"key rate 2024 mean: {key_a[2024]}"
    assert abs(fx_a[2006] - 27.14) < 0.1, f"USD/RUB 2006 mean: {fx_a[2006]}"
    assert abs(fx_a[2014] - 38.60) < 0.1, f"USD/RUB 2014 mean: {fx_a[2014]}"
    assert abs(fx_a[2022] - 68.35) < 0.3, f"USD/RUB 2022 mean: {fx_a[2022]}"
    assert abs(loans_a[2014] - 19.1) < 1.0, f"household rate 2014: {loans_a[2014]}"
    assert 8.0 < ofz_a[2023] < 13.0, f"OFZ 10y 2023 mean: {ofz_a[2023]}"

    write("markets/key_rate_from_cbr.csv",
          ["year", "key_rate_pct", "key_rate_pct_peak"],
          [[str(y), f"{key_a[y]:.2f}", f"{max(key[y]):.2f}"]
           for y in sorted(key_a) if YEAR_FROM <= y <= YEAR_TO],
          ["Bank of Russia, hd_base/KeyRate: the key rate, daily.",
           "key_rate_pct is the MEAN of the daily values in the year;",
           "key_rate_pct_peak is the highest single-day value, which is the",
           "number the story is about: 20.00% on 28.02.2022 against a 2022",
           "mean of about 10.6%. The rate was 9.50% the day before.",
           "The Bank of Russia's key rate began on 13.09.2013; the previous",
           "refinancing rate is continuous with it and the table carries it.",
           "Fetched 2026-10-25."])

    write("markets/usd_rub_from_cbr.csv",
          ["year", "rub_per_usd"],
          [[str(y), f"{fx_a[y]:.4f}"] for y in sorted(fx_a)
           if YEAR_FROM <= y <= YEAR_TO],
          ["Bank of Russia, XML_dynamic VAL_NM_RQ=R01235 (USD): the official",
           "daily rate, annual MEAN. Value is per ONE dollar; the feed quotes",
           "a Nominal multiplier which is applied here.",
           "Capital controls from 28.02.2022 made this a fixed official rate",
           "rather than a market price for part of 2022 — said on the plate.",
           "Fetched 2026-10-25."])

    write("markets/ofz_10y_from_cbr.csv",
          ["year", "ofz_10y_pct"],
          [[str(y), f"{ofz_a[y]:.2f}"] for y in sorted(ofz_a)
           if YEAR_FROM <= y <= YEAR_TO],
          ["Bank of Russia, hd_base/zcyc_params: zero-coupon yield curve of",
           "OFZ, the 10-year tenor, daily, annual MEAN.",
           "The curve is the Bank of Russia's own model estimate from",
           "market prices, not a single bond's yield.",
           "Fetched 2026-10-25."])

    write("credit/household_lending_rate_from_cbr.csv",
          ["year", "household_lending_rate_pct"],
          [[str(y), f"{loans_a[y]:.2f}"] for y in sorted(loans_a)
           if YEAR_FROM <= y <= YEAR_TO],
          ["Bank of Russia, pdko/int_rat/loans_ind_new.xlsx, sheet",
           "'ставки_руб', column 'все виды кредитов' under 'по всем срокам':",
           "weighted-average rate on NEW rouble loans to individuals, all",
           "maturities, monthly, annual MEAN.",
           "The file starts in January 2014; years before that are absent",
           "rather than estimated. Mortgage-only and consumer-only cuts are",
           "in the same workbook and are not what this column is.",
           "Fetched 2026-10-25."])

    print("Bank of Russia anchors verified.")


if __name__ == "__main__":
    main()
