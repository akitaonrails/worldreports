#!/usr/bin/env python3
"""Refresh the PSI 20 closes for the markets plate into a sidecar CSV.

Usage:  python3 -I countries/portugal/fetch/fetch_markets.py

  PSI20.LS  PSI 20  (Euronext Lisbon, price index)

Nobody official publishes an index close, so this comes from a
redistributor and is marked official: false in SOURCES.yaml. The old
^PSI20 symbol is DELISTED on Yahoo ("No data found, symbol may be
delisted"); the index now trades as PSI20.LS. stooq's ^psi daily CSV
was the first choice and is behind the same JavaScript proof-of-work
wall that blocked ^ibex/^tsx (verified 2026-10-22), and Euronext's own
download 404'd, so Yahoo's monthly bars are used instead.

This is a PRICE index: it excludes dividends, so a price-only chart
understates Lisbon against any total-return series. The plate says so.

COVERAGE TRAP: Yahoo's PSI20.LS history starts 2013-04-30. The
2006–2012 year-ends are NOT in it and stay BLANK — holes, not zeros.
Hand-curating them from another redistributor is a build-phase
decision, recorded in the manifest's meta.pending list; the sidecar's
comment header says the same.

Monthly bars are requested rather than daily: Yahoo's monthly close IS
the last trading day's close of that month, which is exactly the
year-end value, and it keeps the payload small enough to be polite.

Output: data/markets/psi20_from_yahoo.csv
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "markets"
CACHE = ROOT / "cache"

CHART = ("https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
         "?interval=1mo&period1={p1}&period2={p2}")
# A browser UA is required: the endpoint answers 429 to the default urllib one.
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

SYMBOL = "PSI20.LS"
Y0, Y1 = 2006, 2026   # country window; Yahoo only serves 2013-04-30 onward

# December closes verified live on 2026-10-22 (discovery phase).
KNOWN_CLOSES = {2013: 6558.85, 2024: 6377.26, 2025: 8263.65}

COMMENT = [
    "# PSI 20 year-end closes via Yahoo (a redistributor — nobody official",
    "# publishes an index close; official: false). PRICE index: dividends",
    "# excluded. Yahoo's PSI20.LS history STARTS 2013-04-30 — the 2006-2012",
    "# year-ends are missing upstream (stooq is JS-walled, Euronext 404s) and",
    "# stay blank here: holes, not zeros. Hand-curation is a build-phase",
    "# decision (see meta.pending in SOURCES.yaml).",
]


def fetch() -> dict[int, tuple[str, float]]:
    """{year: (iso date, close)} for the last observation of each year."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "yahoo_psi20.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        p1 = int(datetime(Y0, 1, 1, tzinfo=timezone.utc).timestamp())
        p2 = int(datetime(Y1, 12, 31, tzinfo=timezone.utc).timestamp())
        url = CHART.format(symbol=SYMBOL, p1=p1, p2=p2)
        last = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=90) as r:
                    payload = json.loads(r.read())
                if not payload.get("chart", {}).get("result"):
                    raise ValueError("no result in payload")
                cache_file.write_text(json.dumps(payload))
                break
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(3 * (attempt + 1))
        else:
            raise RuntimeError(f"yahoo psi20: {last}")
    return year_ends(payload)


def year_ends(payload: dict) -> dict[int, tuple[str, float]]:
    """The last non-null monthly close of each calendar year.

    Monthly bars are stamped at the START of their month, in the exchange's
    own time; the exchange offset in `meta` is applied to recover the local
    date. A month still in progress reports a close too, so the current
    year's value is a live reading, not an annual total — the plate labels
    it.
    """
    result = payload["chart"]["result"][0]
    offset = int(result["meta"].get("gmtoffset") or 0)
    stamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    out: dict[int, tuple[str, float]] = {}
    for ts, close in zip(stamps, closes):
        if close is None:
            continue
        d = datetime.fromtimestamp(ts + offset, tz=timezone.utc)
        out[d.year] = (d.date().isoformat(), float(close))
    return out


def check(series: dict[int, tuple[str, float]]) -> None:
    """Guard against a silent symbol or payload change upstream."""
    first = min(series)
    assert first == 2013, f"expected history to start 2013, got {first}"
    for year, close in KNOWN_CLOSES.items():
        got = series[year][1]
        assert abs(got - close) < 0.01, f"{year}: expected {close}, got {got}"


def main() -> None:
    print("Fetching PSI 20 closes...")
    series = fetch()
    check(series)
    DATA.mkdir(parents=True, exist_ok=True)
    lines = COMMENT + ["year,close"]
    for y in range(Y0, Y1 + 1):
        hit = series.get(y)
        lines.append(f"{y},{hit[1]:.2f}" if hit else f"{y},")
    (DATA / "psi20_from_yahoo.csv").write_text("\n".join(lines) + "\n")
    latest = max(series)
    print(f"  -> data/markets/psi20_from_yahoo.csv "
          f"(latest bar {series[latest][0]}: {series[latest][1]:,.2f})")
    print("Done. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
