#!/usr/bin/env python3
"""Refresh the market series: the policy rate and the equity index.

Usage:  python3 -I fetch/fetch_markets.py     (or: make C=australia fetch)

Two publishers, both reached because the obvious one is blocked:

  BIS central bank policy rates (WS_CBPOL, monthly, end of period)
      Australia's cash rate target as the BIS records it, sourced from
      the RBA. www.rba.gov.au answers HTTP 403 to this network on every
      path including robots.txt (DISCOVERY.md records the probes), and
      the RBA's data.gov.au mirror stopped in 2013, so the BIS
      harmonised republication of the RBA's own series is the route.
      Annualised as the MEAN of the monthly end-of-period values, the
      rule for every rate in this country.

  Yahoo Finance (chart JSON) — ASX 200 (^AXJO), S&P 500 (^GSPC) and the
      AUD/USD rate (AUDUSD=X), monthly closes. A redistributor, so
      `official: false` in SOURCES.yaml. The index is rebased to
      2006 = 100 in US$: the annual mean of the monthly closes divided
      by the annual mean of AUD/USD, then indexed. The S&P 500 is the
      dashed comparison line the spine asks for, on the same basis.

Neither is spliced with anything: the equity panel is one redistributed
series, labelled as such on the plate, and the policy rate is one official
series with a single publisher.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = Path(__file__).resolve().parent / "cache"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _sdmx import BIS, FetchError, get  # noqa: E402

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/"
# 2006-01-01 .. well past the plate window; fixed so the file is
# reproducible rather than "whatever is close today".
P1, P2 = 1133395200, 1790000000   # 1 Dec 2005, so 2006 has twelve bars


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    print(f"  wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def policy_rate() -> list[dict]:
    body = get(f"{BIS}/data/WS_CBPOL/M.AU?format=csv", accept="text/csv")
    import io

    rows = list(csv.DictReader(io.StringIO(
        body.decode("utf-8-sig", "replace"))))
    if not rows:
        raise FetchError("BIS WS_CBPOL: no rows")
    monthly: dict[int, list[tuple[str, float]]] = {}
    for r in rows:
        v = (r.get("OBS_VALUE") or "").strip()
        if not v:
            continue
        monthly.setdefault(int(r["TIME_PERIOD"][:4]), []).append(
            (r["TIME_PERIOD"], float(v)))
    out = []
    for y in sorted(monthly):
        vals = monthly[y]
        if len(vals) < 12:
            continue
        out.append({"year": y,
                    "policy_rate_pct": round(sum(v for _p, v in vals) / 12, 2),
                    "policy_rate_dec_pct": round(vals[-1][1], 2),
                    "months_observed": len(vals)})
    if len(out) < 15:
        raise FetchError(f"BIS WS_CBPOL: only {len(out)} complete years")
    print(f"  BIS CBPOL: {out[0]['year']}-{out[-1]['year']}")
    return out


def yahoo_monthly(symbol: str) -> dict[int, list[float]]:
    url = (f"{YAHOO}{symbol}?period1={P1}&period2={P2}&interval=1mo")
    payload = json.loads(get(url, accept="application/json"))
    try:
        result = payload["chart"]["result"][0]
        stamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError):
        raise FetchError(f"Yahoo {symbol}: unexpected payload") from None
    monthly: dict[int, dict[tuple[int, int], float]] = {}
    for ts, c in zip(stamps, closes):
        if c is None:
            continue
        t = time.gmtime(ts)
        monthly.setdefault(t.tm_year, {})[(t.tm_year, t.tm_mon)] = float(c)
    if not monthly:
        raise FetchError(f"Yahoo {symbol}: no closes")
    return {y: list(v.values()) for y, v in monthly.items()}


def equities() -> list[dict]:
    """ASX 200 and the S&P 500, annual mean of monthly closes, 2006 = 100.

    The ASX 200 is quoted in AUD, so it is divided by the World Bank's
    annual-average AUD/USD rate (PA.NUS.FCRF, staged by
    fetch_comparables.py) rather than by a monthly FX series: Yahoo's
    monthly FX history is incomplete before 2008, and an annual average
    belongs with an annual average anyway. Both indices are rebased on
    the same 2006 annual mean, which is what the spine's "2006 = 100"
    means.
    """
    asx = yahoo_monthly("%5EAXJO")
    spx = yahoo_monthly("%5EGSPC")
    fx = {}
    fx_path = DATA / "world" / "wb_from_worldbank.csv"
    if not fx_path.exists():
        raise FetchError("run fetch_comparables.py first (needs aud_per_usd)")
    for r in csv.DictReader(fx_path.open(encoding="utf-8")):
        if r.get("aud_per_usd"):
            fx[int(r["year"])] = float(r["aud_per_usd"])
    rows = []
    base_asx = base_spx = None
    for y in sorted(set(asx) & set(spx) & set(fx)):
        if y < 2006 or len(asx[y]) < 11 or len(spx[y]) < 11:
            continue
        mean_asx = sum(asx[y]) / len(asx[y])
        mean_spx = sum(spx[y]) / len(spx[y])
        asx_usd = mean_asx / fx[y]
        if base_asx is None:
            base_asx, base_spx = asx_usd, mean_spx
            rows.append({"year": y, "asx200_usd_index_2006": 100.0,
                         "sp500_usd_index_2006": 100.0,
                         "aud_per_usd_avg": round(fx[y], 4)})
            continue
        rows.append({"year": y,
                     "asx200_usd_index_2006": round(100 * asx_usd / base_asx, 1),
                     "sp500_usd_index_2006": round(100 * mean_spx / base_spx, 1),
                     "aud_per_usd_avg": round(fx[y], 4)})
    if len(rows) < 15 or rows[0]["year"] != 2006:
        raise FetchError(f"equities: base year is "
                         f"{rows[0]['year'] if rows else None}, "
                         f"{len(rows)} years")
    print(f"  Yahoo: ASX 200 in US$ {rows[0]['year']}-{rows[-1]['year']}")
    return rows


def main() -> None:
    try:
        print("Market series")
        write_csv(DATA / "markets" / "policy_rate_from_bis.csv",
                  ["year", "policy_rate_pct", "policy_rate_dec_pct",
                   "months_observed"], policy_rate())
        write_csv(DATA / "markets" / "equity_from_yahoo.csv",
                  ["year", "asx200_usd_index_2006", "sp500_usd_index_2006",
                   "aud_per_usd_avg"], equities())
    except FetchError as e:
        print(f"fetch error: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
