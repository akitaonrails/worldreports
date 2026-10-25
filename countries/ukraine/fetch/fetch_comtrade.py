"""Ukraine's 2023 goods exports by partner, from UN Comtrade.

    python3 -m countries.ukraine.fetch.fetch_comtrade [--offline]

Writes the review sidecar `trade/partners_2023_from_comtrade.csv`; the
curated file is a separate reviewed step.

One year, on purpose: the canonical destination slot is a time series and
the customs service that would publish one answers 403, so the snapshot
lives in the trade lens and is labelled with its year. The preview API
returns every partner for one reporter-year in a single call; partner
names are M49 codes, mapped here for the partners the plate shows.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "comtrade_2023.json"
SIDECAR = ROOT / "data" / "trade" / "partners_2023_from_comtrade.csv"
URL = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS"
       "?reporterCode=804&period=2023&cmdCode=TOTAL&flowCode=X")
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}

# M49 → name, for the partners that reach the plate.
M49 = {616: "Poland", 642: "Romania", 156: "China", 792: "Türkiye",
       276: "Germany", 724: "Spain", 380: "Italy", 528: "Netherlands",
       804: "Ukraine", 0: "World"}

# 2023 world exports, verified live 2026-10-25.
WORLD_TOTAL = 36_185_539_498.82


def fail(msg: str) -> None:
    print(f"fetch_comtrade: {msg}", file=sys.stderr)
    sys.exit(1)


def payload(offline: bool) -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    if offline:
        fail(f"no cache at {CACHE} and --offline given; nothing written")
    body = b""
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(URL, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as fh:
                body = fh.read()
            break
        except Exception as exc:                       # noqa: BLE001
            last = exc
            time.sleep(3 * (attempt + 1))
    else:
        fail(f"{URL} failed: {type(last).__name__}: {last}; nothing written")
    data = json.loads(body)
    if not isinstance(data, dict) or data.get("count", 0) < 100:
        fail(f"payload shape is not a partner list: {str(data)[:120]}")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(body)
    return data


def main(argv: list[str]) -> int:
    data = payload("--offline" in argv)
    rows = data.get("data") or []
    world = next((r for r in rows if r.get("partnerCode") == 0), None)
    if world is None or abs(float(world["primaryValue"]) - WORLD_TOTAL) > 1e6:
        fail("world total moved; re-verify the anchor before writing")
    partners = [r for r in rows
                if r.get("partnerCode") not in (0, 804)
                and r.get("primaryValue")]
    partners.sort(key=lambda r: -float(r["primaryValue"]))
    picked = partners[:6]
    named = [p for p in picked if p["partnerCode"] in M49]
    if len(named) != len(picked):
        fail(f"unmapped partner codes: "
             f"{[p['partnerCode'] for p in picked if p['partnerCode'] not in M49]}")
    total = float(world["primaryValue"])
    rest = total - sum(float(p["primaryValue"]) for p in picked)

    SIDECAR.parent.mkdir(parents=True, exist_ok=True)
    with SIDECAR.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["partner", "exports_usd_mn", "share_pct"])
        for p in picked:
            value = float(p["primaryValue"])
            w.writerow([M49[p["partnerCode"]], f"{value / 1e6:.1f}",
                        f"{value / total * 100:.2f}"])
        w.writerow(["Rest of the world", f"{rest / 1e6:.1f}",
                    f"{rest / total * 100:.2f}"])
    print(f"  data/trade/partners_2023_from_comtrade.csv  "
          f"{len(picked)} partners + rest, world US${total / 1e9:.1f}bn")
    print("Done. Diff the sidecar before adopting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
