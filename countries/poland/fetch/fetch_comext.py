#!/usr/bin/env python3
"""Refresh Poland's goods-export destinations from Eurostat Comext.

Usage:  make C=poland fetch   (or: python3 -I fetch/fetch_comext.py)

The customs-side answer to "who does Poland sell to". Comext is Eurostat's
dissemination of the member states' INTRASTAT/EXTRASTAT declarations — the
same declarations GUS's own trade statistics are built from — so this is
the publisher's own machine channel for the customs perimeter, and it is
comparable across EU members.

  DS-045409  EU trade since 1988 by HS2-4-6 and CN8
             reporter=PL, flow=1 (exports), product=TOTAL,
             indicators=VALUE_IN_EUROS, annual

The share is computed against the WORLD total of the same cube and the
same year, never against a remembered headline. Two totals in this cube
are NOT trade: `INT_EU`, `EXT_EU`, `INT_EA`, `EXT_EA` and their vintages
are aggregates of the same exports, and summing them double-counts —
they are excluded from the partner list explicitly.

This is GOODS on a customs basis. It is not the national-accounts
exports series (which includes services) and the two are never spliced.

Output: trade/partners_from_comext.csv (review sidecar only).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, FetchError, assert_close, json_get, write_csv  # noqa: E402

URL = ("https://ec.europa.eu/eurostat/api/comext/dissemination/"
       "statistics/1.0/data/DS-045409?format=JSON&reporter=PL&flow=1"
       "&product=TOTAL&indicators=VALUE_IN_EUROS&freq=A")
Y0, Y1 = 2006, 2026

#: The destinations an atlas reader looks for, in the order they matter to
#: Poland: the German supply-chain anchor first, then the Visegrád
#: neighbours, then the large western markets, then the eastern ones whose
#: weight collapsed in 2022.
PARTNERS = {
    "DE": "germany", "CZ": "czechia", "SK": "slovakia", "HU": "hungary",
    "GB": "united_kingdom", "FR": "france", "IT": "italy",
    "NL": "netherlands", "SE": "sweden", "UA": "ukraine", "RU": "russia",
    "CN": "china", "US": "united_states",
}
#: Aggregates of the cube's own dimensions — not partners.
NOT_A_PARTNER = {"WORLD", "INT_EU", "INT_EU27_2020", "INT_EU28",
                 "INT_EA", "INT_EA21", "EXT_EA", "EXT_EA21", "EXT_EU",
                 "EXT_EU27_2020", "INT_EU25", "INT_EU15"}


def cube() -> tuple[dict[int, dict[str, float]], dict[str, str]]:
    """{year: {partner: euros}} for every partner, plus the label map."""
    payload = json_get(URL, timeout=240)
    ids, size = payload["id"], payload["size"]
    cats, labels = [], {}
    for dim in ids:
        category = payload["dimension"][dim]["category"]
        index = category["index"]
        inv = {pos: code for code, pos in index.items()} \
            if isinstance(index, dict) else dict(enumerate(index))
        cats.append(inv)
        if dim == "partner":
            labels = category.get("label", {})
    st = [1] * len(size)
    for i in range(len(size) - 2, -1, -1):
        st[i] = st[i + 1] * size[i + 1]
    pi, ti = ids.index("partner"), ids.index("time")
    out: dict[int, dict[str, float]] = {}
    for flat, value in payload["value"].items():
        n = int(flat)
        key = tuple(cats[i][(n // st[i]) % size[i]] for i in range(len(ids)))
        year = key[ti]
        if not year.isdigit():
            continue
        out.setdefault(int(year), {})[key[pi]] = float(value)
    if not out:
        raise FetchError("comext: empty value map")
    return out, labels


def main() -> None:
    print("Fetching Comext goods exports for Poland...")
    data, labels = cube()
    if 2024 not in data:
        raise FetchError("comext: no 2024 slice")
    world_2024 = data[2024].get("WORLD")
    if not world_2024:
        raise FetchError("comext: no WORLD total for 2024")
    # Known value: Poland exported about EUR 353bn of goods in 2024 and
    # Germany took about a quarter of it.
    assert_close(world_2024 / 1e9, 353.3, 3.0, "comext world exports 2024")
    de_share = data[2024]["DE"] / world_2024 * 100
    assert_close(de_share, 25.2, 2.0, "Germany share of PL goods exports")

    rows = []
    for y in range(Y0, Y1 + 1):
        slice_ = data.get(y, {})
        world = slice_.get("WORLD")
        cells = [y, round(world / 1e9, 3) if world else None]
        for code in PARTNERS:
            v = slice_.get(code)
            cells.append(round(v / world * 100, 2) if v and world else None)
        rows.append(cells)
    header = (["year", "goods_exports_world_eur_bn"]
              + [f"share_{n}_pct" for n in PARTNERS.values()])
    path = write_csv("trade/partners_from_comext.csv", header, rows, comment=f"""
Eurostat Comext DS-045409, reporter PL, flow 1 (exports), product TOTAL,
indicator VALUE_IN_EUROS, annual. Share = partner value / WORLD value of
the same year, in per cent; the WORLD total in EUR bn is carried beside it
because a share without its base hides a shrinking pie.
GOODS on a customs basis (INTRASTAT + EXTRASTAT), not goods and services
and not the balance-of-payments presentation. Partner labels in this
edition: {", ".join(f"{c}={labels.get(c, c)}" for c in ("DE", "CZ", "UA", "RU"))}.
The cube's aggregates (INT_EU, EXT_EU, INT_EA, EXT_EA and their vintages)
are excluded: they restate the same exports and would double-count.
""")
    print(f"  -> {path.relative_to(DATA)}")
    print("Done. Diff the *_from_comext.csv sidecar before adopting.")


if __name__ == "__main__":
    main()
