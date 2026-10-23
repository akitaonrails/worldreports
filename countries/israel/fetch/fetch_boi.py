#!/usr/bin/env python3
"""Refresh the Bank of Israel representative exchange rates into a sidecar.

Usage:  python3 -I countries/israel/fetch/fetch_boi.py

The one BoI endpoint that survives the portal redesign is the PublicApi
FX call: https://www.boi.org.il/currency.xml 301-redirects to
https://boi.org.il/PublicApi/GetExchangeRates and answers live JSON
{"exchangeRates": [{"key": "USD", "currentExchangeRate": 3.107,
"currentChange": ..., "unit": 1, "lastUpdate": ...}, ...]} (verified
2026-10-22). The direction is ILS per one unit of the foreign
currency; JPY-style rows carry unit:100 — the quoted rate is per 100
units — so the fetcher divides by unit and stages the per-one rate.

This is an INTRADAY SNAPSHOT of the representative rate, not a history.
The daily-history ZIP advertised on data.gov.il is dead (404), and the
other PublicApi paths — GetInterestRates, GetCPI, GetMaccam — are 404
while several wrong paths answer HTTP 200 with a Radware bot-challenge
loader page. A 200 here proves nothing, so the payload is shape- and
value-checked BEFORE caching: JSON object, exchangeRates list, USD
present, rate inside a plausible band, every unit positive. An error
page cannot pass as an empty result.

The annual FX plate (markets slot 3) runs meanwhile on the World Bank
PA.NUS.FCRF annual average (markets/usdils_from_wb.csv, staged by
fetch_harmonised.py); this snapshot keeps the live reading honestly
labelled as one, and its USD cell is cross-checked against that
annual-average file when it exists — printed only, since a point
reading and a year's mean are different quantities.

Parked with the BoI block (SOURCES.yaml meta.pending): rate history,
policy rate, reserves, mac"m yields, mortgage rates.

Output: data/markets/usdils_from_boi.csv
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

NAME = "Israel"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "markets"
CACHE = ROOT / "cache" / "boi"

URL = "https://www.boi.org.il/currency.xml"   # 301 -> PublicApi/GetExchangeRates
HEADERS = {"User-Agent": "Mozilla/5.0 (X11, Linux x86_64)", "Accept": "application/json"}

# A snapshot, not a history: one row per currency at the API's own
# timestamp. ILS per ONE unit of the foreign currency.
HEADER = "currency,unit,rate_per_unit,ils_per_unit,last_update_utc"

# The shekel has traded roughly 3.1-5.0 per US$ across the atlas window;
# anything outside a wide band is an error page or a unit mistake.
USD_BAND = (2.0, 6.0)


class FetchError(RuntimeError):
    pass


def check(raw: bytes) -> dict:
    """Parse and validate the payload BEFORE anything is cached."""
    try:
        p = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"not JSON (Radware loader or error page?): {raw[:60]!r}") from e
    rates = p.get("exchangeRates")
    if not isinstance(rates, list) or not rates:
        raise ValueError("no exchangeRates list in payload")
    by_key = {}
    for row in rates:
        k, v, u = row.get("key"), row.get("currentExchangeRate"), row.get("unit")
        if not (isinstance(k, str) and isinstance(v, (int, float))
                and isinstance(u, (int, float)) and u > 0 and v > 0):
            raise ValueError(f"malformed rate row: {row!r}")
        by_key[k] = row
    if "USD" not in by_key:
        raise ValueError("payload has no USD row")
    if not USD_BAND[0] < by_key["USD"]["currentExchangeRate"] < USD_BAND[1]:
        raise ValueError(f"USD rate {by_key['USD']['currentExchangeRate']} "
                         f"outside band {USD_BAND} — wrong unit or a lie")
    if not all(k in by_key for k in ("EUR", "GBP", "JPY")):
        raise ValueError("expected currency rows missing")
    return by_key


def fetch() -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "exchange_rates.json"
    if path.exists():
        raw = path.read_bytes()
        try:
            return check(raw)
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache: {e}", file=sys.stderr)
            path.unlink()
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()
            check(raw)                 # validate BEFORE caching
            path.write_bytes(raw)
            return check(raw)
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  boi attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise FetchError(f"{URL}: {last}")


def main() -> None:
    print(f"Bank of Israel representative rates for {NAME}")
    by_key = fetch()
    usd = by_key["USD"]
    # Spot: the USD representative rate on 2026-10-22 was 3.107 ILS/USD.
    want, got = 3.107, usd["currentExchangeRate"]
    if abs(got - want) / want > 0.05:
        raise FetchError(f"USD spot moved from {want} to {got} — cache a "
                         "stale day or upstream changed the payload")
    print(f"  USD {got} ILS/USD at {usd['lastUpdate']} (spot 3.107 ok)")

    lines = [HEADER]
    for k in sorted(by_key):
        row = by_key[k]
        unit = float(row["unit"])
        rate = float(row["currentExchangeRate"])
        per_one = rate / unit
        if not 1e-6 <= per_one <= 100:
            raise FetchError(f"{k}: per-one rate {per_one} implausible")
        lines.append(f"{k},{int(unit)},{rate},%.6f,{row['lastUpdate']}"
                     % per_one)
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / "usdils_from_boi.csv"
    if path.exists():
        first = next((ln for ln in path.read_text().splitlines()
                      if not ln.startswith("#")), "")
        if first != HEADER:
            raise FetchError(f"refusing to overwrite usdils_from_boi.csv: "
                             f"it holds {first!r}")
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/markets/usdils_from_boi.csv  {len(lines) - 1} rows "
          f"(snapshot at {usd['lastUpdate']})")

    wb = DATA / "usdils_from_wb.csv"
    if wb.exists():
        rows = list(csv.DictReader(
            ln for ln in wb.read_text().splitlines()
            if not ln.startswith("#")))
        year = int(usd["lastUpdate"][:4])
        hit = next((r for r in rows if int(r["year"]) == year
                    and r["ils_per_usd"]), None)
        if hit:
            print(f"  context: annual-average WB {year} mean "
                  f"{hit['ils_per_usd']} vs today's point {got} — "
                  "printed only (different quantities)")
    print("Done. This is one live reading, not a year's result. "
          "Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
