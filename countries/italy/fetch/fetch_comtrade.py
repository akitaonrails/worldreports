#!/usr/bin/env python3
"""Refresh Italy's 2023 export destinations from UN Comtrade.

Usage: python3 -I countries/italy/fetch/fetch_comtrade.py

The public preview endpoint returns Italy as reporter, annual HS TOTAL,
customs-value goods. It is a definition-safe substitute for the unreachable
Coeweb partner table, but never for the goods-and-services national-accounts
lines elsewhere on the trade plate. Output is a review sidecar.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "trade"
CACHE = ROOT / "cache" / "comtrade"
PERIOD = "2023"
REPORTER = 380
WORLD = 0
API = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS"
       f"?reporterCode={REPORTER}&period={PERIOD}&flowCode=X"
       "&cmdCode=TOTAL&format=json")
SPOT = 676_819_818_431.702
PARTNER = {
    276: "Germany", 842: "United States", 251: "France", 724: "Spain",
    757: "Switzerland", 826: "United Kingdom", 616: "Poland",
    56: "Belgium", 156: "China", 528: "Netherlands",
}


def checked(raw: bytes) -> list[dict]:
    payload = json.loads(raw)
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) < 100:
        raise ValueError("Comtrade response is empty or truncated")
    if payload.get("count") != len(rows):
        raise ValueError("Comtrade count does not match returned rows")
    if any(row.get("reporterCode") != REPORTER or row.get("flowCode") != "X"
           or row.get("cmdCode") != "TOTAL" for row in rows):
        raise ValueError("Comtrade response has another reporter/flow/product")
    world = [row for row in rows if row.get("partnerCode") == WORLD]
    if len(world) != 1:
        raise ValueError("Comtrade response lacks one World row")
    total = float(world[0]["primaryValue"])
    if abs(total - SPOT) / SPOT > 0.02:
        raise ValueError(f"World export total moved unexpectedly: {total}")
    parts = sum(float(row["primaryValue"]) for row in rows
                if row.get("partnerCode") != WORLD)
    if abs(parts - total) / total > 0.01:
        raise ValueError("Partner rows do not sum to the World total")
    return rows


def fetch() -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"italy_{PERIOD}_exports.json"
    if cached.exists():
        try:
            return checked(cached.read_bytes())
        except Exception:
            cached.unlink()
    last = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(API, timeout=120) as response:
                raw = response.read()
            rows = checked(raw)
            cached.write_bytes(raw)
            return rows
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"UN Comtrade: {last}")


def main() -> None:
    rows = fetch()
    world = next(row for row in rows if row["partnerCode"] == WORLD)
    total = float(world["primaryValue"])
    partners = sorted((row for row in rows if row["partnerCode"] in PARTNER),
                      key=lambda row: -float(row["primaryValue"]))
    lines = ["year,flow,partner_code,partner,value_usd,share_of_flow_pct",
             f'{PERIOD},X,World,"World",{total:.0f},100.00']
    for row in partners:
        code = row["partnerCode"]
        value = float(row["primaryValue"])
        lines.append(f'{PERIOD},X,{code},"{PARTNER[code]}",'
                     f'{value:.0f},{100 * value / total:.2f}')
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "trade_comtrade_partner_from_comtrade.csv").write_text(
        "\n".join(lines) + "\n")
    print("  -> data/trade/trade_comtrade_partner_from_comtrade.csv")


if __name__ == "__main__":
    main()
