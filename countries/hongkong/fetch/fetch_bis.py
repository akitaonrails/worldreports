"""BIS — credit to households as a percentage of GDP.

    python3 -m countries.hongkong.fetch.fetch_bis [--offline]

Writes the review sidecar `data/credit/household_debt_from_bis.csv` only.

This is the series the spine names for credit slot 1 (BIS total credit,
`WS_TC`, key `Q.CC.H.A.M.770.A` — quarterly, all sectors lending, market
value, percentage of GDP, adjusted for breaks). Hong Kong is `HK` here, an
SAR economy reported separately from China: the BIS key is per economy and
must not be confused with `CN`.

The HKMA publishes the same idea in its Half-yearly Monetary and Financial
Stability Report as text and charts, with no machine-readable series; the
national route for a household-debt ratio is therefore a PDF, and the BIS
harmonised series is the only reproducible one. It is `official: false` in
SOURCES.yaml because the BIS is a compilation, and the plate says "BIS".
"""
from __future__ import annotations

import csv
import io
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "bis"
DATA = ROOT / "data"

URL = ("https://stats.bis.org/api/v1/data/WS_TC/Q.HK.H.A.M.770.A"
       "?format=csv&startPeriod=2005")
UA = {"User-Agent": "curl/8.5.0"}

# 57.4% in 2005-Q1, a pandemic peak of 91.6% in 2020-Q4 and 87.8% end-2025.
PINS = {"2005-Q1": 57.4, "2020-Q4": 91.6, "2025-Q4": 87.8}


class FetchError(SystemExit):
    pass


def fail(msg: str) -> None:
    print(f"fetch_bis: {msg}", file=sys.stderr)
    sys.exit(1)


def payload(offline: bool) -> bytes:
    cache_file = CACHE / "ws_tc_households.csv"
    if cache_file.exists():
        return cache_file.read_bytes()
    if offline:
        fail(f"offline and no cached file {cache_file}")
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            if not body.startswith(b"FREQ,"):
                raise ValueError("not the BIS CSV (an SDMX error came back)")
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(body)
            return body
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    fail(f"{URL}: {last}")


def main(argv: list[str]) -> None:
    offline = "--offline" in argv
    rows = list(csv.DictReader(io.StringIO(payload(offline).decode("utf-8"))))
    if not rows:
        fail("BIS returned no rows")
    got = {r["TIME_PERIOD"]: r["OBS_VALUE"] for r in rows}
    for period, want in PINS.items():
        value = got.get(period)
        if value in (None, "") or abs(float(value) - want) > 0.5:
            fail(f"BIS {period} = {value!r}, expected ~{want}")
    out = DATA / "credit/household_debt_from_bis.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["period", "household_debt_pct_gdp"])
        for period in sorted(got):
            if got[period] not in ("", None):
                w.writerow([period, f"{float(got[period]):.1f}"])
    print(f"  {out.relative_to(ROOT)}  ({len(got)} quarters, "
          f"{min(got)}..{max(got)})")


if __name__ == "__main__":
    main(sys.argv[1:])
