#!/usr/bin/env python3
"""Chile's goods exports by partner, one calendar year, from UN Comtrade.

Usage:  python3 -I countries/chile/fetch/fetch_comtrade.py [year]

Writes data/trade/partners_<year>_from_comtrade.csv — a review sidecar,
never the curated file. Columns: partner, exports_usd_bn, share_pct.

Definitional notes that matter here:
  * This is the CUSTOMS series (goods only, HS classification, reporter
    Chile, flow exports, aggregate command TOTAL), not the balance of
    payments series the trade plate draws for goods and services. The
    plate's slot 1-2 come from the national accounts; this snapshot only
    answers "to whom", and the two are never spliced.
  * partnerCode 0 is "World" and is the denominator, not a partner.
  * partnerCode 152 is Chile itself (re-exports recorded against the
    reporting economy); it is dropped rather than shown as a partner.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "comtrade"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "*/*"}

API = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS"
       "?reporterCode=152&period={year}&partnerCode=&cmdCode=TOTAL"
       "&flowCode=X")
PARTNERS = "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"


class FetchError(RuntimeError):
    pass


def get(url: str, cache_name: str, check) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        raw = path.read_bytes()
        try:
            check(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache {cache_name}: {e}", file=sys.stderr)
            path.unlink()
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            check(raw)
            path.write_bytes(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {cache_name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def main(year: int) -> int:
    def check_data(raw: bytes) -> None:
        p = json.loads(raw)
        rows = p.get("data") or []
        if not rows:
            raise ValueError(f"empty Comtrade payload: {str(p)[:120]}")
        if {r["reporterCode"] for r in rows} != {152}:
            raise ValueError("payload is for another reporter")
        if {r["flowCode"] for r in rows} != {"X"}:
            raise ValueError("payload is not the export flow")
        if {r["cmdCode"] for r in rows} != {"TOTAL"}:
            raise ValueError("payload is not the TOTAL command")

    def check_names(raw: bytes) -> None:
        if not json.loads(raw).get("results"):
            raise ValueError("no partner code list")

    rows = json.loads(get(API.format(year=year), f"comtrade_{year}.json",
                          check_data))["data"]
    names = {r["id"]: r["text"] for r in
             json.loads(get(PARTNERS, "partner_areas.json",
                            check_names))["results"]}

    total, partners = 0.0, []
    for row in rows:
        value = float(row.get("primaryValue") or 0.0)
        if row["partnerCode"] == 0:
            total = value
        elif row["partnerCode"] != 152:
            partners.append((names.get(row["partnerCode"],
                                       str(row["partnerCode"])), value))
    if not total:
        raise FetchError("Comtrade: no World row, so no denominator")
    partners.sort(key=lambda kv: kv[1], reverse=True)

    # Shape checks on the answer, not just its syntax.
    if len(partners) < 40:
        raise FetchError(f"only {len(partners)} partners: partial payload?")
    top = partners[0][0]
    if top != "China":
        raise FetchError(f"top export destination is {top!r}, not China — "
                         "Chile's customs ranking has moved and needs review")
    covered = sum(v for _, v in partners) / total
    if not (0.95 <= covered <= 1.05):
        raise FetchError(f"partners cover {covered:.1%} of the World total")

    out = DATA / "trade" / f"partners_{year}_from_comtrade.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["partner", "exports_usd_bn", "share_pct"])
        for name, value in partners[:15]:
            w.writerow([name, f"{value / 1e9:.3f}",
                        f"{value / total * 100:.2f}"])
    print(f"  world total US$ {total / 1e9:.1f}bn, {len(partners)} partners, "
          f"{covered:.2%} covered")
    print(f"  -> trade/partners_{year}_from_comtrade.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 2024))
