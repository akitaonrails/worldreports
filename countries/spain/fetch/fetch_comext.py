#!/usr/bin/env python3
"""Refresh Spain's customs goods exports by destination and by product.

Usage:  python3 -I countries/spain/fetch/fetch_comext.py

Eurostat's Comext database (dataset DS-045409, "EU trade since 1988 by
HS2-4-6 and CN8") is where Spain's customs declarations are published on
the harmonised EU basis, the same file every member state reports into.
It is the source for the trade chapter's two customs panels:

  trade/destinations_from_comext.csv   share of goods exports, by partner
  trade/export_products_from_comext.csv share of goods exports, by HS group

Both are SHARES of the year's goods exports to the whole world
(partner WORLD), so they are composition, not level, and the €bn
numbers they are built from are written beside them for anyone who
wants to check the division.

This is the customs, goods-only basis, on Eurostat's *community concept*
(goods physically crossing the border, by the country of destination as
declared). It is a different universe from the national-accounts series
in trade/trade.csv — goods AND services, on a change-of-ownership basis —
and from the DataComex figures the Secretaría de Estado de Comercio
publishes on the *national concept*, which run a few per cent lower
(2024: Comext €396bn, DataComex about €384bn). Shares travel between the
three far better than levels do; none of them is spliced into another.

DataComex itself is the national primary and stays in SOURCES.yaml's
pending block: its portal is an interactive query builder with no
documented machine endpoint. Comext carries the same declarations.

Cross-checked against UN Comtrade (Spain as reporter, US$): France's
share of 2023 goods exports reads 15.0% there and 15.6% here. The gap is
the denominator — Comtrade carries Spain's national-concept total, which
is larger than the community-concept one by goods that clear customs in
Spain without being Spanish exports — so the two must agree within one
point, or nothing is written.

Annual cells only: the running year's months are published monthly and
are not summed here into a part-year.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eurostat import decode  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

BASE = ("https://ec.europa.eu/eurostat/api/comext/dissemination/"
        "statistics/1.0/data/DS-045409")
COMTRADE = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS"
            "?reporterCode=724&period=2023&partnerCode=0,251"
            "&flowCode=X&cmdCode=TOTAL")
Y0, Y1 = 2006, 2026

# The destinations a Spanish reader would name, in 2024 order, plus
# Morocco — the one non-European market in the top ten. Everything else is
# in the denominator, not on the plate.
PARTNERS = {"FR": "France", "DE": "Germany", "IT": "Italy",
            "PT": "Portugal", "GB": "United Kingdom", "US": "United States",
            "MA": "Morocco"}

# Product groups, as HS2 chapters. Agrifood is the food chapters of the
# HS (01-24) summed: the fruit, vegetables, meat, olive oil and wine that
# make Spain Europe's market garden. A group is written only in a year
# where every chapter in it is published.
GROUPS = {
    "vehicles": ("87",),
    "agrifood": tuple(f"{c:02d}" for c in range(1, 25)),
    "machinery": ("84", "85"),
    "fuels": ("27",),
    "pharma": ("30",),
}


def comext(cache_key: str, **filters) -> dict:
    """One Comext cube, cached under cache/ like the dissemination API's."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"comext_{cache_key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    query = urllib.parse.urlencode({"format": "JSON", **filters}, doseq=True)
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f"{BASE}?{query}", timeout=180) as r:
                payload = json.loads(r.read())
            if not payload.get("value"):
                # An unknown code returns a well-formed cube with an empty
                # value map and HTTP 200 — fail rather than write blanks.
                raise ValueError("empty value map")
            cache_file.write_text(json.dumps(payload))
            return payload
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"comext {filters}: {last}")


def by(payload: dict, dim: str) -> dict[str, dict[int, float]]:
    """{code of `dim`: {year: value}} from a cube varying in dim and time."""
    ids = payload["id"]
    free = [d for d, n in zip(ids, payload["size"])
            if n > 1 and d not in (dim, "time")]
    if free:
        raise ValueError(f"{free} left unpinned")
    i, t = ids.index(dim), ids.index("time")
    out: dict[str, dict[int, float]] = {}
    for key, value in decode(payload).items():
        if key[t].isdigit():
            out.setdefault(key[i], {})[int(key[t])] = float(value)
    return out


def comtrade_france_share() -> float:
    cache_file = CACHE / "comtrade_es_2023_fr.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        with urllib.request.urlopen(COMTRADE, timeout=90) as r:
            payload = json.loads(r.read())
        cache_file.write_text(json.dumps(payload))
    vals = {row["partnerCode"]: row["primaryValue"] for row in payload["data"]}
    return vals[251] / vals[0] * 100


def write(rel: str, header: str, lines: list[str]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *lines]) + "\n")
    print(f"  -> data/{rel}")


def main() -> None:
    print("Fetching Comext customs exports for Spain...")
    common = dict(reporter="ES", flow="2", indicators="VALUE_IN_EUROS",
                  freq="A")

    dest = by(comext("es_x_partners", partner=["WORLD", *PARTNERS],
                     product="TOTAL", **common), "partner")
    world = dest["WORLD"]
    # Spot values read off the Comext interface, 2024: €396.1bn to the
    # world, €58.8bn to France.
    assert round(world[2024] / 1e9, 1) == 396.1, world[2024]
    assert round(dest["FR"][2024] / 1e9, 1) == 58.8, dest["FR"][2024]
    fr23 = dest["FR"][2023] / world[2023] * 100
    ct23 = comtrade_france_share()
    if abs(fr23 - ct23) > 1.0:
        raise RuntimeError(f"France 2023: Comext {fr23:.2f}% vs Comtrade "
                           f"{ct23:.2f}%")
    print(f"  France 2023: Comext {fr23:.2f}% · Comtrade {ct23:.2f}%")

    lines = []
    for y in range(Y0, Y1 + 1):
        if y not in world:
            continue
        for code, name in PARTNERS.items():
            v = dest.get(code, {}).get(y)
            if v is None:
                continue
            lines.append(f"{y},{name},{v / world[y] * 100:.2f},"
                         f"{v / 1e9:.3f},{world[y] / 1e9:.3f}")
    write("trade/destinations_from_comext.csv",
          "year,destination,share_pct,exports_eurbn,world_eurbn", lines)

    chapters = sorted({c for cs in GROUPS.values() for c in cs})
    prod = by(comext("es_x_products", partner="WORLD",
                     product=["TOTAL", *chapters], **common), "product")
    total = prod["TOTAL"]
    assert total == world, "the product TOTAL is not the partner WORLD"
    # 2024 spot values: vehicles (HS 87) €58.6bn, fuels (HS 27) €30.1bn.
    assert round(prod["87"][2024] / 1e9, 1) == 58.6, prod["87"][2024]
    assert round(prod["27"][2024] / 1e9, 1) == 30.1, prod["27"][2024]

    lines = []
    for y in range(Y0, Y1 + 1):
        if y not in total:
            continue
        for group, codes in GROUPS.items():
            if not all(y in prod.get(c, {}) for c in codes):
                continue
            v = sum(prod[c][y] for c in codes)
            lines.append(f"{y},{group},{v / total[y] * 100:.2f},"
                         f"{v / 1e9:.3f},{total[y] / 1e9:.3f}")
    write("trade/export_products_from_comext.csv",
          "year,product,share_pct,exports_eurbn,world_eurbn", lines)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
