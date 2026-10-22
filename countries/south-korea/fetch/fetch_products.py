#!/usr/bin/env python3
"""What Korea actually sells abroad, by product, for a handful of snapshot years.

Korea's own trade statistics classify exports by **MTI**, a national scheme.
It is the right classification for a Korean reader — "반도체" is a category
everyone recognises — but it is not comparable to anything, and the Bank of
Korea's machine-readable trade tables only carry a four-way split (food, raw
materials, light industry, heavy and chemical industry) that says nothing
about semiconductors.

So the product panel is built on **HS headings** from UN Comtrade, as
reported by Korea itself. That buys a consistent definition across twenty
years at the cost of not matching the Korean headlines: MTI 반도체 is wider
than HS 8542 and the ministry's figure is correspondingly larger ($173.4bn
for 2025 against $142.8bn here). Both are right about different things, and
plate 04 says which one it is drawing. See data/SOURCES.yaml.

Snapshot years only — the panel compares composition at five points, so
fetching twenty years of every heading would be data nobody reads.

Output:
  data/trade/exports_products.csv   year,product,usbi
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "trade"
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

API = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS"
       "?reporterCode=410&period={year}&cmdCode={codes}"
       "&flowCode=X&partnerCode=0")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) korea-reports/1.0"}

YEARS = (2006, 2010, 2015, 2020, 2025)

# HS heading -> the column name plate 04 draws. Chapter-level codes (two
# digits) are used where the product is a whole chapter: ships, steel and
# petrochemicals have no single heading that covers them.
PRODUCTS = {
    "8542": "semiconductors",   # electronic integrated circuits
    "8703": "cars",             # motor cars
    "8708": "car_parts",
    "89": "ships",              # ships, boats and floating structures
    "2710": "petroleum",        # refined petroleum products
    "39": "petrochemicals",     # plastics and articles thereof
    "72": "steel",              # iron and steel
    "8517": "telecom",          # telephone sets and network equipment
}


def fetch(year: int) -> dict[str, float]:
    """{HS code: US$ billion} of Korean exports in one year."""
    cache_file = CACHE / f"comtrade_{year}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        url = API.format(year=year, codes=",".join(PRODUCTS))
        payload = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=90) as r:
                    payload = json.loads(r.read().decode("utf-8"))
                break
            except Exception as e:  # noqa: BLE001
                print(f"    {year} retry {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        if payload is None:
            return {}
        cache_file.write_text(json.dumps(payload))
        time.sleep(1)  # the preview endpoint is rate-limited

    out = {}
    for row in payload.get("data", []):
        value = row.get("primaryValue")
        if value:
            out[str(row["cmdCode"])] = value / 1e9
    return out


def main() -> None:
    rows = []
    for year in YEARS:
        values = fetch(year)
        if not values:
            print(f"  ! {year}: no data", file=sys.stderr)
            continue
        for code, name in PRODUCTS.items():
            if code in values:
                rows.append(f"{year},{name},{values[code]:.2f}")
        print(f"  {year}: {len(values)} of {len(PRODUCTS)} headings")
    if rows:
        (DATA / "exports_products.csv").write_text(
            "\n".join(["year,product,usbi", *rows]) + "\n")
        print(f"  -> data/trade/exports_products.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
