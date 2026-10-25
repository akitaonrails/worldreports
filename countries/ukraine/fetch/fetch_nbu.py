"""Ukraine's central-bank series, from the NBU's own statistics API.

    python3 -m countries.ukraine.fetch.fetch_nbu [--offline]

Writes review sidecars only (SOURCING_A_COUNTRY.md §4):

    markets/usd_uah_from_nbu.csv     official USD/UAH, annual mean of the
                                     daily rate (NBU `exchange`)
    markets/key_rate_from_nbu.csv    NBU key policy rate, annual mean of
                                     the daily rate (`key`, KEY_PolicyRate)

The endpoints are documented on the bank's own open-data page
(https://bank.gov.ua/en/open-data/api-dev) and were probed live on
2026-10-24. Both return JSON arrays of daily observations; the annual
mean is taken over the observations the publisher supplies for that year,
and a year with no observations is left out rather than carried.

`--offline` reads the cache and writes nothing new; a cold cache without
`--offline` fetches and caches. Re-running either mode produces a
byte-identical sidecar.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "nbu"

KEY_URL = ("https://bank.gov.ua/NBUStatService/v1/statdirectory/key"
           "?start={start}&end={end}&json")
FX_URL = ("https://bank.gov.ua/NBU_Exchange/exchange_site"
          "?start={start}&end={end}&valcode=usd&sort=exchangedate"
          "&order=asc&json")
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}
FIRST, LAST = 2006, 2026

# Anchors verified live 2026-10-24: the key rate was 25.0% on 2023-07-23
# (the war-time peak) and 13.0% at the end of 2024.
KNOWN = {"2023-07-23": 25.0}


def fetch(url: str, cache: Path, offline: bool, tries: int = 3,
          required: bool = True) -> list:
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    if offline:
        sys.exit(f"fetch_nbu: no cache at {cache} and --offline given; "
                 "nothing written")
    body = b""
    last: Exception | None = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as fh:
                body = fh.read()
            break
        except Exception as exc:                  # noqa: BLE001
            last = exc
            time.sleep(3 * (attempt + 1))
    else:
        sys.exit(f"fetch_nbu: {url} failed: {type(last).__name__}: {last}")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        sys.exit(f"fetch_nbu: {url} did not return JSON ({exc}); nothing written")
    if not isinstance(payload, list) or not payload:
        if required:
            sys.exit(f"fetch_nbu: {url} returned no observations; nothing written")
        return []
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    return payload


def annual_mean(rows, day_key: str, value_key: str) -> dict[int, float]:
    per_year: dict[int, list[float]] = {}
    for row in rows:
        day = str(row.get(day_key, ""))
        value = row.get(value_key)
        if value in (None, ""):
            continue
        # `key` dates are YYYYMMDD; the FX feed uses DD.MM.YYYY.
        if "." in day:
            parts = day.split(".")
            if len(parts) != 3:
                continue
            year = int(parts[2])
        elif len(day) >= 8 and day[:4].isdigit():
            year = int(day[:4])
        else:
            continue
        if FIRST <= year <= LAST:
            per_year.setdefault(year, []).append(float(value))
    return {y: statistics.fmean(v) for y, v in sorted(per_year.items())}


def write(rel: str, series: dict[int, float], column: str, dec: int) -> None:
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["year", column])
        for y, v in series.items():
            w.writerow([y, f"{v:.{dec}f}"])
    print(f"  data/{rel}  {len(series)} rows")


def main(argv: list[str]) -> int:
    offline = "--offline" in argv
    key_rows: list = []
    fx_rows: list = []
    for year in range(FIRST, LAST + 1):
        span = (f"{year}0101", f"{year}1231")
        key_rows += fetch(KEY_URL.format(start=span[0], end=span[1]),
                          CACHE / f"key_{year}.json", offline)
        fx_rows += fetch(FX_URL.format(start=span[0], end=span[1]),
                         CACHE / f"usd_{year}.json", offline)

    # Only the key-policy-rate rows; the endpoint also carries the other
    # NBU rates.
    key_rows = [r for r in key_rows if r.get("id_api") == "KEY_PolicyRate"]
    key = annual_mean(key_rows, "dt", "value")
    # `rate` is quoted per `units` (100 before the 2015 redenomination,
    # 1 after); `rate_per_unit` is always the rate for one US dollar.
    fx = annual_mean(fx_rows, "exchangedate", "rate_per_unit")

    if not key or not fx:
        sys.exit("fetch_nbu: a series came back empty; nothing written")
    # Known-value check on the raw daily row, before aggregation.
    daily = {r["dt"][:4] + "-" + r["dt"][4:6] + "-" + r["dt"][6:8]: r["value"]
             for r in key_rows}
    for day, want in KNOWN.items():
        got = daily.get(day)
        if got is None or abs(float(got) - want) > 1e-9:
            sys.exit(f"fetch_nbu: key rate on {day} is {got!r}, expected {want}")

    write("markets/key_rate_from_nbu.csv", key, "policy_rate_pct", 2)
    write("markets/usd_uah_from_nbu.csv", fx, "uah_per_usd", 4)

    print("Done. Diff the sidecars before adopting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
