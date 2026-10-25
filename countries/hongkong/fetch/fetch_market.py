"""Market series nobody publishes as a statistic, plus Transparency
International's index.

    python3 -m countries.hongkong.fetch.fetch_market [--offline]

Writes review sidecars under `data/**/*_from_<source>.csv` only. Every series
here is `official: false` in SOURCES.yaml (SOURCING_A_COUNTRY.md §5):

* the Hang Seng Index is compiled by Hang Seng Indexes Company Limited, a
  private subsidiary of Hang Seng Bank. It is the Hong Kong market's own
  reading and it is not a statistic of the SAR government;
* the S&P 500 is the dashed comparison line in markets slot 4;
* Transparency International's Corruption Perceptions Index is a
  think-tank compilation, not an official series.

Yahoo's chart endpoint is the house pattern (see taiwan/fetch/fetch_markets.py
for the full quirk list): a browser User-Agent is required, monthly bars are
stamped in exchange time, and the December bar's close is the year-end. The
running year is a live reading, not a year's result, and is never staged as
one.

TI's CPI workbook is read from its XML directly because it carries defined
names that make openpyxl report no sheets, and TI's CDN answers 403 with an
HTML page that must never reach the cache.
"""
from __future__ import annotations

import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "market"
DATA = ROOT / "data"

CHART = ("https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
         "?interval=1mo&period1={p1}&period2={p2}")
TI = "https://images.transparencycdn.org/images/CPI2025_Results.xlsx"
TI_SHEET = "CPI Historical"
ISO3 = "HKG"
UA = {"User-Agent": "Mozilla/5.0 (X11, Linux x86_64)"}
Y0, Y1 = 2005, 2026

SYMBOLS = [
    # symbol, sidecar stem, column, gmtoffset, pins {year: close}
    ("%5EHSI", "markets/hsi_yearend", "hsi_close", 28800,
     {2006: 19964.72, 2019: 28189.75}),
    ("%5EGSPC", "markets/sp500_yearend", "sp500_close", -18000,
     {2006: 1418.30, 2019: 3230.78}),
]


class FetchError(SystemExit):
    pass


def fail(msg: str) -> None:
    print(f"fetch_market: {msg}", file=sys.stderr)
    sys.exit(1)


def grab(url: str, name: str, offline: bool) -> bytes:
    cache_file = CACHE / name
    if cache_file.exists():
        return cache_file.read_bytes()
    if offline:
        fail(f"offline and no cached file {cache_file}")
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            if not body:
                raise ValueError("empty body")
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(body)
            return body
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 + 2 * attempt)
    fail(f"{url}: {last}")


def year_ends(payload: dict, offset: int) -> dict[int, tuple[str, float]]:
    result = payload["chart"]["result"][0]
    stamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    out = {}
    for ts, close in zip(stamps, closes):
        if close is None:
            continue
        d = datetime.fromtimestamp(ts + offset, tz=timezone.utc)
        if d.month == 12:
            out[d.year] = (d.date().isoformat(), round(float(close), 2))
    return out


def equity(offline: bool) -> None:
    for symbol, stem, column, offset, pins in SYMBOLS:
        p1 = int(datetime(Y0, 1, 1, tzinfo=timezone.utc).timestamp())
        p2 = int(datetime(Y1, 12, 31, tzinfo=timezone.utc).timestamp())
        body = grab(CHART.format(symbol=symbol, p1=p1, p2=p2),
                    f"yahoo_{column}.json", offline)
        payload = json.loads(body)
        try:
            meta = payload["chart"]["result"][0]["meta"]
            if meta.get("instrumentType") != "INDEX":
                raise ValueError(f"instrumentType {meta.get('instrumentType')!r}")
        except (KeyError, IndexError, TypeError) as e:
            fail(f"{symbol}: not a Yahoo chart payload ({e})")
        series = year_ends(payload, offset)
        for year, want in pins.items():
            got = series.get(year)
            if got is None or abs(got[1] - want) > max(1.5, want * 0.005):
                fail(f"{symbol}: {year} close {got}, expected ~{want}")
        # 2006..2025 only: 2026 is a live reading, not a year's result.
        out = DATA / f"{stem}_from_yahoo.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["year,date," + column]
        for year in range(2006, Y1):
            hit = series.get(year)
            if hit:
                lines.append(f"{year},{hit[0]},{hit[1]:.2f}")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        live = series.get(Y1)
        print(f"  {out.relative_to(ROOT)}  ({len(lines) - 1} year-ends; "
              f"{Y1} live reading {live[1] if live else '—'}, not staged)")


def _ti_sheet(raw: bytes, sheet_name: str) -> list[dict[str, str]]:
    """One sheet of the TI xlsx as rows of {column letter: text}."""
    z = zipfile.ZipFile(io.BytesIO(raw))
    book = z.read("xl/workbook.xml").decode()
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    sheets = dict(re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"',
                             book))
    target = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels)
                  + [(b, a) for a, b in re.findall(
                      r'Target="([^"]+)"[^>]*Id="([^"]+)"', rels)])
    path = "xl/" + target[sheets[sheet_name]].lstrip("/").replace("xl/", "")
    ss = z.read("xl/sharedStrings.xml").decode()
    strings = ["".join(re.findall(r"<t[^>]*>(.*?)</t>", c, re.S))
               for c in re.findall(r"<si>(.*?)</si>", ss, re.S)]
    out = []
    for row in re.findall(r"<row[^>]*>(.*?)</row>",
                          z.read(path).decode(), re.S):
        cells = {}
        for m in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)',
                             row, re.S):
            ref, attrs, body = m.groups()
            v = re.search(r"<v>(.*?)</v>", body or "")
            val = v.group(1) if v else ""
            if 't="s"' in attrs and val:
                val = strings[int(val)]
            cells[ref] = val
        out.append(cells)
    return out


def ti(offline: bool) -> dict[int, float]:
    raw = grab(TI, "ti_CPI2025.xlsx", offline)
    if raw[:2] != b"PK":
        fail("TI: not a workbook (the CDN answers 403 with an HTML page)")
    sheet = _ti_sheet(raw, TI_SHEET)
    head = next((r for r in sheet if (r.get("A") or "").startswith("Country")),
                None)
    if head is None:
        fail("TI: workbook has no CPI header row")
    col = {v: k for k, v in head.items() if v}
    for want in ("ISO3", "Year", "CPI score"):
        if want not in col:
            fail(f"TI: no {want!r} column in the CPI sheet")
    out = {}
    for r in sheet:
        if (r.get(col["ISO3"]) or "").strip() == ISO3 and r.get(col["CPI score"]):
            out[int(float(r[col["Year"]]))] = float(r[col["CPI score"]])
    if not out:
        fail("TI: no HKG rows in the CPI sheet")
    if out.get(2024) is None or not 60 <= out[2024] <= 90:
        fail(f"TI: 2024 HKG score {out.get(2024)!r} is implausible")
    path = DATA / "world/cpi_ti_from_ti.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["year,cpi_score"] + [f"{y},{out[y]:.0f}" for y in sorted(out)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}  ({len(out)} years, "
          f"{min(out)}-{max(out)})")


def main(argv: list[str]) -> None:
    offline = "--offline" in argv
    equity(offline)
    ti(offline)


if __name__ == "__main__":
    main(sys.argv[1:])
