#!/usr/bin/env python3
"""Fetch comparative indicators from the World Bank and UNDP.

These are the series for which the authoritative publisher is an
international body rather than a US agency — either because the measure is
defined internationally (the Human Development Index) or because the point of
it is the comparison (the US share of world output, health spending against
other rich countries).

Where a US agency publishes the same measure on its own definition, that
agency wins and this is kept only as a cross-check. The clearest case is
poverty: the World Bank's harmonised $-a-day lines say almost nothing about
the United States, where the official measure is the Census Bureau's poverty
threshold and the better one is its Supplemental Poverty Measure. Those come
from `fetch_census.py`; the World Bank's Gini is kept here beside the Census
Bureau's own because the two use different income definitions and must not be
spliced.

Sources:
  World Bank World Development Indicators API (no key)
  UNDP Human Development Report 2025, composite indices time series

Outputs:
  data/international/worldbank.csv  year,<indicator>...
  data/social/hdi.csv               year,hdi,le,eys,mys,gnipc
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "wb"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

WB = "https://api.worldbank.org/v2/country/{c}/indicator/{i}"
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")

YEAR_FROM, YEAR_TO = 2006, 2026

# indicator code -> the column it becomes
INDICATORS = {
    "SI.POV.GINI": "gini_wb",
    "NE.TRD.GNFS.ZS": "trade_openness",
    "SH.XPD.CHEX.GD.ZS": "health_spending_pct_gdp",
    "SP.DYN.LE00.IN": "life_expectancy",
    "SP.DYN.TFRT.IN": "fertility",
    "NY.GDP.MKTP.CD": "gdp_usd",
}
# the same GDP indicator for the world, so the US share can be computed
WORLD = "NY.GDP.MKTP.CD"


def wb(country: str, indicator: str) -> dict[int, float]:
    """{year: value} for one World Bank indicator, cached."""
    cache = CACHE / f"wb_{country}_{indicator}.json"
    if cache.exists():
        payload = json.loads(cache.read_text())
    else:
        try:
            r = requests.get(WB.format(c=country, i=indicator),
                             params={"format": "json", "per_page": 500},
                             timeout=120)
            r.raise_for_status()
            payload = r.json()
        except Exception as e:  # noqa: BLE001
            print(f"  !! {country}/{indicator} failed: {type(e).__name__}: {e}")
            return {}
        cache.write_text(json.dumps(payload))
    if not isinstance(payload, list) or len(payload) < 2:
        return {}
    out = {}
    for row in payload[1] or []:
        if row.get("value") is None:
            continue
        try:
            out[int(row["date"])] = float(row["value"])
        except (TypeError, ValueError):
            continue
    return out


def hdr() -> dict[int, dict[str, float]]:
    """The UNDP composite indices for the United States.

    One vintage for every year, so the whole series is internally consistent:
    UNDP recomputes history under the current methodology with each report,
    and mixing report years produces steps that are not development.
    """
    cache = CACHE / "hdr25.csv"
    if not cache.exists():
        try:
            r = requests.get(HDR, timeout=180)
            r.raise_for_status()
            cache.write_bytes(r.content)
        except Exception as e:  # noqa: BLE001
            print(f"  !! HDR failed: {type(e).__name__}: {e}")
            return {}
    text = cache.read_text(encoding="utf-8-sig", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    us = next((r for r in rows if (r.get("iso3") or "").strip() == "USA"), None)
    if us is None:
        print("  !! no USA row in the HDR series")
        return {}
    out: dict[int, dict[str, float]] = {}
    # the file is wide: one column per measure per year, e.g. hdi_2023
    for key, value in us.items():
        if not key or "_" not in key or not value:
            continue
        measure, _, year = key.rpartition("_")
        if not year.isdigit() or measure not in ("hdi", "le", "eys", "mys",
                                                 "gnipc"):
            continue
        try:
            out.setdefault(int(year), {})[measure] = float(value)
        except ValueError:
            continue
    return out


def fmt(v: float | None, dec: int = 2) -> str:
    return "" if v is None else f"{v:.{dec}f}"


def main() -> None:
    print("Fetching World Bank and UNDP series...")
    series = {name: wb("USA", code) for code, name in INDICATORS.items()}
    world_gdp = wb("WLD", WORLD)
    for name, got in series.items():
        years = sorted(got)
        print(f"  [{name}] {len(years)} years"
              + (f" {years[0]}-{years[-1]}" if years else ""))

    names = list(INDICATORS.values()) + ["us_share_world_gdp"]
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        cells = []
        for name in INDICATORS.values():
            v = series[name].get(y)
            cells.append(fmt(v, 0 if name == "gdp_usd" else 2))
        us, wld = series["gdp_usd"].get(y), world_gdp.get(y)
        cells.append(fmt(us / wld * 100, 2) if (us and wld) else "")
        rows.append(f"{y}," + ",".join(cells))
    (DATA / "international" / "worldbank.csv").write_text(
        f"year,{','.join(names)}\n" + "\n".join(rows) + "\n")
    print("  -> data/international/worldbank.csv")

    # ---- HDI ------------------------------------------------------------
    h = hdr()
    years = sorted(h)
    print(f"  [hdi] {len(years)} years"
          + (f" {years[0]}-{years[-1]}" if years else ""))
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        got = h.get(y, {})
        rows.append(f"{y},{fmt(got.get('hdi'), 3)},{fmt(got.get('le'))},"
                    f"{fmt(got.get('eys'))},{fmt(got.get('mys'))},"
                    f"{fmt(got.get('gnipc'), 0)}")
    (DATA / "social" / "hdi.csv").write_text(
        "year,hdi,life_expectancy,expected_schooling,mean_schooling,gni_pc\n"
        + "\n".join(rows) + "\n")
    print("  -> data/social/hdi.csv")
    print("Done.")


if __name__ == "__main__":
    main()
