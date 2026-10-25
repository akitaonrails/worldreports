#!/usr/bin/env python3
"""Refresh the World Bank comparables for Poland into review sidecars.

Usage:  make C=poland fetch   (or: python3 -I fetch/fetch_worldbank.py)

This is the layer that makes Poland legible beside every other country in
the atlas: GDP and GDP per person in US$, reserves, the population series
the World Bank carries, the Gini the Bank harmonises, the lending rate and
the stock of non-performing loans. None of it is a substitute for a number
GUS or NBP publishes about Poland; where both exist the national series is
the curated one and this rides beside it, labelled.

`official: false` in SOURCES.yaml: the World Bank is a redistributor here,
not the institution that computed the Polish number.

Lending rate and NPL both have a stale tail — FR.INR.LEND ends years
before the present and GFDD.SI.02 ends in 2020 — so they are staged but
the credit chapter's NPL line comes from the EBA (fetch_eba.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DATA, FetchError, assert_close, json_get,  # noqa: E402
                    write_csv)

ISO = "POL"
Y0, Y1 = 2006, 2026
BASE = "https://api.worldbank.org/v2/country/{iso}/indicator/{code}"


def series(code: str) -> dict[int, float]:
    """{year: value} for one WDI indicator, from the Bank's own API."""
    url = (BASE.format(iso=ISO, code=code)
           + f"?format=json&per_page=500&date={Y0}:{Y1}")
    payload = json_get(url, timeout=120)
    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        raise FetchError(f"worldbank {code}: no observations "
                         f"({str(payload)[:120]})")
    out = {}
    for row in payload[1]:
        v = row.get("value")
        if v is not None:
            out[int(row["date"])] = float(v)
    if not out:
        raise FetchError(f"worldbank {code}: empty series")
    return out


def wide(rel: str, columns: dict[str, dict[int, float]], dec: int = 4,
         comment: str | None = None) -> None:
    header = ["year"] + list(columns)
    rows = []
    for y in range(Y0, Y1 + 1):
        cells = [y]
        for s in columns.values():
            v = s.get(y)
            cells.append(None if v is None else round(v, dec))
        rows.append(cells)
    path = write_csv(rel, header, rows, comment=comment)
    print(f"  -> {path.relative_to(DATA)}")


def main() -> None:
    print("Fetching World Bank series for Poland...")
    gdp = series("NY.GDP.MKTP.CD")
    gdp_pc = series("NY.GDP.PCAP.CD")
    reserves = series("FI.RES.TOTL.CD")
    pop = series("SP.POP.TOTL")
    gini = series("SI.POV.GINI")
    # Known values (current vintage): GDP 2024 = US$914.7bn, GDP per person
    # 2024 = US$24,981, reserves 2024 = US$223.1bn, population 2024.
    assert_close(gdp.get(2024) / 1e9, 914.7, 15, "WB GDP 2024, US$bn")
    assert_close(gdp_pc.get(2024), 24_981, 500, "WB GDP per capita 2024")
    assert_close(reserves.get(2024) / 1e9, 223.1, 5, "WB reserves 2024, US$bn")

    wide("macro/gdp_per_person_from_wb.csv", {
        "gdp_per_capita_usd": gdp_pc,
        "gdp_usd_bn": {y: v / 1e9 for y, v in gdp.items()},
    }, dec=2, comment="""
World Bank WDI NY.GDP.PCAP.CD and NY.GDP.MKTP.CD, current US$, the same
denominator every country in the atlas uses for the shared GDP-per-person
slot. This is GDP per RESIDENT: Poland's population denominator after the
2021 census revision is ~1.0 million below the pre-revision balance, so
this line is not comparable with a per-person figure divided by the old
register.
""")

    wide("world/world_from_wb.csv", {
        "gdp_usd_bn": {y: v / 1e9 for y, v in gdp.items()},
        "reserves_usd_bn": {y: v / 1e9 for y, v in reserves.items()},
        "population_wb_million": {y: v / 1e6 for y, v in pop.items()},
    }, dec=3, comment="""
World Bank WDI: NY.GDP.MKTP.CD (GDP, current US$), FI.RES.TOTL.CD (total
reserves including gold, current US$, year-end) and SP.POP.TOTL (UN World
Population Prospects). The reserves figure is the World Bank's record of
NBP's official reserve assets; NBP's own monthly series is the national
publisher and is not machine-readable from this network (DISCOVERY.md).
""")

    wide("people/people_from_wb.csv", {"gini_wb": gini}, dec=2, comment="""
World Bank SI.POV.GINI: the Gini the Bank harmonises from national
household surveys, 0-100. It is a different compilation from Eurostat's
EU-SILC Gini (ilc_di12) and the two do not agree year for year; the
national survey line and the EU-SILC line are drawn separately.
""")

    # ---- credit: the Bank's NPL cross-check ---------------------------
    # FR.INR.LEND is not merely stale for Poland: the Bank carries the
    # indicator and returns no observation at all for POL, so there is
    # nothing to stage. That is recorded in DISCOVERY.md with the route.
    npl = series("GFDD.SI.02")
    wide("credit/credit_from_wb.csv", {
        "npl_pct_wb": npl,
    }, dec=2, comment="""
World Bank GFDD.SI.02 (bank non-performing loans to total gross loans,
%), the Bank's compilation of the IMF financial-soundness series. STAGED
FOR CROSS-CHECK, NOT FOR THE PLATE: the Polish series stops in 2020. The
credit chapter's NPL line is the EBA Risk Dashboard
(credit/npl_from_eba.csv), which runs to the current quarter, and the
national sector-wide ratio NBP publishes is not reachable from this
network (DISCOVERY.md).
""")

    # ---- security: the harmonised rates ------------------------------
    homicide = series("VC.IHR.PSRC.P5")
    suicide = series("SH.STA.SUIC.P5")
    road = series("SH.STA.TRAF.P5")
    wide("security/security_from_wb.csv", {
        "homicide_per_100k_unodc": homicide,
        "suicide_per_100k_who": suicide,
        "road_deaths_per_100k_who": road,
    }, dec=3, comment="""
World Bank republication of UNODC (VC.IHR.PSRC.P5), WHO (SH.STA.SUIC.P5)
and WHO road-traffic estimates (SH.STA.TRAF.P5), per 100,000. These are
the comparable rates the spine puts beside the national count; they are
modelled/estimated series, not the police's recorded offences, and they
end earlier than the national series (see the sidecar's own coverage).
""")

    print("Done. Diff the *_from_wb.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
