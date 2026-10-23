#!/usr/bin/env python3
"""Refresh the UN Comtrade partner cross-check for China into a sidecar CSV.

Usage:  python3 -I countries/china/fetch/fetch_comtrade.py

UN Comtrade, public PREVIEW endpoint (no key): annual C/A/HS, reporter 156
(China), cmdCode TOTAL, period 2023, flows X (exports) and M (imports),
every partner. Comtrade is its own harmonised definition and a cross-check
on partner totals — NOT a substitute for GACC's national figure (GACC's
machine layer is 412-blocked; see SOURCES.yaml pending), and never spliced
with the customs or balance-of-payments series.

Verified live 2026-10-22: 200 without auth, 221 partner rows for X and 220
for M, and the partner rows sum EXACTLY to the partnerCode=0 (World) total
in both flows — the preview is not row-capped for this query, so the top-10
shares below add to real shares, not to a share of a truncated tail. The
endpoint 429s when polled fast, so the two queries are spaced and retried.

Magnitude checks asserted at fetch time (the SOURCING pass promised these):
  exports World 2023 = US$3,379.7bn, imports World 2023 = US$2,556.8bn —
  the same order and the same rounding as the GACC 2023 customs totals
  (~US$3.38tn / ~US$2.56tn as announced in the customs communiqué), which
  is the point of a cross-check: two publishers of adjacent quantities
  agreeing on magnitude while staying on their own definitions.

Partner codes are Comtrade legacy numeric codes; the preview serves null
names, so the map below labels the codes that appear in the staged rows.
Two of them are not ISO-3166: 842 is Comtrade's United States, and 344 is
Hong Kong, China. Partner 156 — the reporter itself (re-imports inside
processing trade; US$104.3bn of the 2023 M total) — is dropped from the
partner panel but stays inside the World denominator. And Comtrade's China
report carries no Taiwan partner code: what GACC books as ~US$200bn of
2023 imports from Taiwan lands in the residual "Other Asia nes" (490) —
that attribution is the atlas's interpretation, not a Comtrade field, and
the curated file's comment says so.

Output: data/trade/trade_comtrade_partner_from_comtrade.csv
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "trade"
CACHE = ROOT / "cache" / "comtrade"

API = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS"
       "?reporterCode=156&period={period}&flowCode={flow}&cmdCode=TOTAL"
       "&format=json")
PERIOD = "2023"                      # snapshot year, pinned; bump by hand
TOP = 10

REPORTER = 156
WORLD = 0

# Known values, read off the preview 2026-10-22 (SOURCING cross-check
# against GACC's published 2023 customs totals: 3.38tn / 2.56tn).
SPOT = {"X": 3379747834884.0, "M": 2556763018595.0}

# Comtrade legacy partner code -> label. Only codes that can appear in the
# staged rows need a label; an unknown code falls back to `partner-<code>`
# rather than being guessed at.
PARTNER = {
    842: "United States",
    344: "China (Hong Kong SAR)",
    392: "Japan",
    410: "Korea, Rep.",
    704: "Viet Nam",
    699: "India",
    643: "Russian Federation",
    276: "Germany",
    528: "Netherlands",
    458: "Malaysia",
    484: "Mexico",
    36: "Australia",
    76: "Brazil",
    490: "Other Asia nes (Comtrade residual)",
}


def fetch(flow: str) -> list[dict]:
    """Rows of one flow's annual HS TOTAL query, validated before caching."""
    def check(raw: bytes) -> None:
        p = json.loads(raw)
        if not isinstance(p, dict) or not isinstance(p.get("data"), list):
            raise ValueError(f"not a Comtrade preview payload: "
                             f"{str(p)[:120]}")
        rows = p["data"]
        if not rows or len(rows) < 100:
            raise ValueError(f"only {len(rows)} partner rows — capped or empty")
        if p.get("count") != len(rows):
            raise ValueError(f"count {p.get('count')} != {len(rows)} rows")
        if any(r.get("reporterCode") != REPORTER or r.get("flowCode") != flow
               for r in rows):
            raise ValueError("payload holds another reporter or flow")
        if any(r.get("cmdCode") != "TOTAL" for r in rows):
            raise ValueError("payload is not the TOTAL product aggregate")
        world = [r for r in rows if r.get("partnerCode") == WORLD]
        if len(world) != 1 or world[0].get("primaryValue") in (None, 0):
            raise ValueError("no single World (partnerCode 0) row")
        want = SPOT[flow]
        got = world[0]["primaryValue"]
        if abs(got - want) / want > 0.02:
            raise ValueError(f"World total {got:,.0f} moved more than 2% "
                             f"from the verified {want:,.0f}")
        parts = sum(r["primaryValue"] for r in rows
                    if r.get("partnerCode") != WORLD)
        if abs(parts - got) / got > 0.01:
            raise ValueError(f"partners sum {parts:,.0f} vs World {got:,.0f} "
                             "— silent row cap")

    CACHE.mkdir(parents=True, exist_ok=True)
    cache_name = f"comtrade_{PERIOD}_{flow}.json"
    path = CACHE / cache_name
    if path.exists():
        raw = path.read_bytes()
        try:
            check(raw)
            return json.loads(raw)["data"]
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache {cache_name}: {e}", file=sys.stderr)
            path.unlink()
    url = API.format(period=PERIOD, flow=flow)
    last: Exception | None = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            check(raw)
            path.write_bytes(raw)
            return json.loads(raw)["data"]
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  comtrade {flow} attempt {attempt + 1}: {e}",
                  file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"comtrade {flow}: {last}")


def main() -> None:
    rows_out: list[str] = []
    for flow, label in (("X", "exports"), ("M", "imports")):
        rows = fetch(flow)
        world = next(r for r in rows if r["partnerCode"] == WORLD)
        total = world["primaryValue"]
        partners = sorted((r for r in rows
                           if WORLD < r["partnerCode"] != REPORTER),
                          key=lambda r: -r["primaryValue"])[:TOP]
        top_sum = sum(r["primaryValue"] for r in partners)
        print(f"  {label}: World {total/1e9:,.1f}bn; top{TOP} partners "
              f"{top_sum/1e9:,.1f}bn = {top_sum/total:.1%}")
        rows_out.append(f"{PERIOD},{flow},World,World,{total:.0f},100.00")
        for r in partners:
            code = r["partnerCode"]
            name = PARTNER.get(code, f"partner-{code}")
            v = r["primaryValue"]
            rows_out.append(f"{PERIOD},{flow},{code},\"{name}\","
                            f"{v:.0f},{100*v/total:.2f}")
        time.sleep(6)   # the preview 429s when polled fast
    DATA.mkdir(parents=True, exist_ok=True)
    body = ("year,flow,partner_code,partner,value_usd,share_of_flow_pct\n"
            + "\n".join(rows_out) + "\n")
    (DATA / "trade_comtrade_partner_from_comtrade.csv").write_text(body)
    print("  -> data/trade/trade_comtrade_partner_from_comtrade.csv "
          f"({len(rows_out)} rows)")
    print("Done. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
