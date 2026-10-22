#!/usr/bin/env python3
"""Refresh the VN-Index year-end closes and the USD/VND market quote.

Usage:  python3 -I countries/vietnam/fetch/fetch_markets.py [--refresh]

  VNINDEX  VN-Index (HOSE), via CafeF's price-history JSON   -> official: false
  VND=X    USD/VND market quote, via Yahoo Finance, monthly  -> official: false

Nobody official publishes either series in machine form. HOSE's own site
is a React app with no endpoint (meta.pending), Yahoo's ^VNI is delisted,
^VNINDEX.VN returns one point and 0P0000HY8X.VN starts in 2020 and is
wrong (2024-12 1,254.59 against HOSE's 1,266.78). stooq is behind its
JavaScript wall. So the index comes from CafeF, a redistributor of HOSE
closes, and the FX quote from Yahoo.

Things these sources will mislead you about.

**CafeF answers an empty or out-of-range query with HTTP 200** and
Data.TotalCount 0, so every reply is asserted to carry a non-empty
Data.Data. It also caps PageSize at 30 whatever is asked, so a full-year
query silently returns only the newest 30 sessions. The fetcher therefore
asks for a short window at the end of each year (15–31 December, at most
~13 sessions) and asserts the reply was not truncated.

**The VN-Index is a PRICE index**, not total return.

**VND=X is the market quote**, which sits above the SBV's central rate
(25,848 against a central 25,632 on 2026-10-22). It shows the gap; it is
not the official rate. Yahoo stamps monthly bars at the start of the month
in London time, so the exchange gmtoffset is applied before reading the
month, and the running month appears twice (the month bar and a live
tick); the later reading is kept and labelled partial.

Cache: countries/vietnam/cache/cafef_vnindex_<year>.json and
yahoo_vndx.json, reused unless --refresh is given (the running year's
CafeF window is always refetched).
Outputs: data/markets/vnindex_from_cafef.csv, data/markets/usdvnd_from_yahoo.csv
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "markets"
CACHE = ROOT / "cache"

CAFEF = ("https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/PriceHistory.ashx"
         "?Symbol=VNINDEX&StartDate={start}&EndDate={end}&PageIndex=1&PageSize=30")
YAHOO = ("https://query1.finance.yahoo.com/v8/finance/chart/VND%3DX"
         "?range=25y&interval=1mo")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
GAP = 2.0
Y0 = 2005
REFRESH = "--refresh" in sys.argv[1:]
_last = [0.0]

# Year-end closes recorded in DISCOVERY.md (verified 2026-10-22).
VNINDEX_MUST = {2006: 751.77, 2008: 315.62, 2018: 892.54, 2024: 1266.78,
                2025: 1784.49}
# December closes recorded in SOURCES.yaml (verified 2026-10-22).
USDVND_MUST = {2006: 15390, 2008: 17204, 2018: 23194, 2024: 25476, 2025: 26225}
# Second source for the FX magnitude: the SBV central rate on 2026-10-22
# (25,632). The October-2026 market quote must sit above it and within 3%.
SBV_CENTRAL_2026_10_22 = 25632


def _get(url: str) -> bytes:
    last = None
    for attempt in range(4):
        wait = _last[0] + GAP - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read()
            _last[0] = time.monotonic()
            return body
        except urllib.error.HTTPError as e:
            _last[0] = time.monotonic()
            last = e
            if e.code in (403, 429, 500, 502, 503):
                time.sleep(15 * (attempt + 1))
                continue
            raise RuntimeError(f"{url}: HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            _last[0] = time.monotonic()
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def cafef_year_end(year: int, today: date) -> tuple[str, float]:
    """(iso date, close) of the last VN-Index session in the year's window."""
    running = year == today.year
    end = today if running else date(year, 12, 31)
    start = end - timedelta(days=20) if running else date(year, 12, 15)
    path = CACHE / f"cafef_vnindex_{year}.json"
    if path.exists() and not REFRESH and not running:
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        url = CAFEF.format(start=start.strftime("%m/%d/%Y"),
                           end=end.strftime("%m/%d/%Y"))
        payload = json.loads(_get(url).decode("utf-8-sig"))
        data = (payload.get("Data") or {})
        rows = data.get("Data") or []
        if not payload.get("Success", True) or not rows:
            raise SystemExit(f"  !! CafeF {year}: empty Data.Data "
                             f"(TotalCount {data.get('TotalCount')})")
        if data.get("TotalCount", 0) > len(rows):
            raise SystemExit(f"  !! CafeF {year}: truncated reply "
                             f"({len(rows)} of {data['TotalCount']})")
        if {r.get("Symbol") for r in rows} != {"VNINDEX"}:
            raise SystemExit(f"  !! CafeF {year}: rows for another symbol")
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    rows = payload["Data"]["Data"]
    best = max(rows, key=lambda r: datetime.strptime(r["Ngay"], "%d/%m/%Y"))
    d = datetime.strptime(best["Ngay"], "%d/%m/%Y").date()
    if d.year != year:
        raise SystemExit(f"  !! CafeF {year}: latest session is {d}")
    return d.isoformat(), float(best["GiaDongCua"])


def vnindex(today: date) -> dict[int, tuple[str, float]]:
    out = {y: cafef_year_end(y, today) for y in range(Y0, today.year + 1)}
    for y, want in VNINDEX_MUST.items():
        got = out[y][1]
        if abs(got - want) > 0.005:
            raise SystemExit(f"  !! VN-Index {y} = {got}, want {want}")
        print(f"  ok VN-Index {y} close {got:,.2f} ({out[y][0]})")
    return out


def yahoo() -> list[tuple[str, float, bool]]:
    """[(yyyy-mm, close, partial)] monthly, oldest first."""
    path = CACHE / "yahoo_vndx.json"
    if path.exists() and not REFRESH:
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = json.loads(_get(YAHOO))
        res = (payload.get("chart") or {}).get("result") or []
        if not res or res[0]["meta"].get("symbol") != "VND=X" \
                or res[0]["meta"].get("currency") != "VND" \
                or not res[0].get("timestamp"):
            raise SystemExit("  !! Yahoo VND=X: no result / wrong symbol")
        path.write_text(json.dumps(payload), encoding="utf-8")
    res = payload["chart"]["result"][0]
    offset = int(res["meta"].get("gmtoffset") or 0)
    months: dict[str, float] = {}
    for ts, close in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
        if close is None:
            continue
        d = datetime.fromtimestamp(ts + offset, tz=timezone.utc)
        months[f"{d.year:04d}-{d.month:02d}"] = float(close)   # later wins
    fetched = datetime.fromtimestamp(
        res["meta"].get("regularMarketTime") or time.time(), tz=timezone.utc)
    current = f"{fetched.year:04d}-{fetched.month:02d}"
    out = [(m, v, m == current) for m, v in sorted(months.items())]
    for y, want in USDVND_MUST.items():
        got = months.get(f"{y}-12")
        if got is None or abs(got - want) > 1:
            raise SystemExit(f"  !! VND=X Dec {y} = {got}, want {want}")
        print(f"  ok VND=X Dec {y} close {got:,.0f}")
    latest = months.get("2026-10")
    if latest is None or not SBV_CENTRAL_2026_10_22 <= latest <= SBV_CENTRAL_2026_10_22 * 1.03:
        raise SystemExit(f"  !! VND=X 2026-10 {latest} not within 0–3% above "
                         f"the SBV central rate {SBV_CENTRAL_2026_10_22:,}")
    print(f"  ok VND=X 2026-10 {latest:,.0f} vs SBV central "
          f"{SBV_CENTRAL_2026_10_22:,} (+{latest / SBV_CENTRAL_2026_10_22 - 1:.1%})")
    return out


def main() -> None:
    CACHE.mkdir(exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    today = date.today()

    print("Fetching VN-Index year-end closes from CafeF...")
    idx = vnindex(today)
    lines = [
        "# official: false. CafeF (cafef.vn) price history, a redistributor of HOSE closes.",
        "# VN-Index, PRICE index (excludes dividends), points. close is the last",
        "# session of the calendar year (date gives it). The running year's row is",
        f"# the latest session at fetch time ({today.isoformat()}), not a year-end.",
        "year,date,close",
    ] + [f"{y},{d},{c:.2f}" for y, (d, c) in sorted(idx.items())]
    (DATA / "vnindex_from_cafef.csv").write_text("\n".join(lines) + "\n",
                                                  encoding="utf-8")
    print(f"  -> data/markets/vnindex_from_cafef.csv ({len(idx)} rows, "
          f"{min(idx)}–{max(idx)})")

    print("Fetching USD/VND (VND=X) from Yahoo...")
    fx = yahoo()
    lines = [
        "# official: false. Yahoo Finance VND=X, the MARKET quote, VND per USD.",
        "# Monthly close (last trading day of the month). It sits above the SBV",
        "# central rate and is not the official rate. partial=1 marks the running",
        "# month, a live reading at fetch time.",
        "month,close,partial",
    ] + [f"{m},{v:.0f},{int(p)}" for m, v, p in fx]
    (DATA / "usdvnd_from_yahoo.csv").write_text("\n".join(lines) + "\n",
                                                 encoding="utf-8")
    print(f"  -> data/markets/usdvnd_from_yahoo.csv ({len(fx)} rows, "
          f"{fx[0][0]}–{fx[-1][0]})")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
