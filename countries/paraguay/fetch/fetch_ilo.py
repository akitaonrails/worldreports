#!/usr/bin/env python3
"""Refresh Paraguay's statutory minimum wage from ILOSTAT.

Usage:  make C=paraguay fetch   (or: python3 -I fetch/fetch_ilo.py)

Paraguay's minimum wage is set by decree (Consejo Nacional de Salarios
Mínimos, published through the Ministerio de Trabajo, Empleo y Seguridad
Social). MTESS publishes no machine-readable series — the homepage and
its salary pages answer 200 but hold no data files, and `datos.gov.py`,
the national open-data portal, has been on a "Sitio en Mantenimiento"
page all through this discovery. ILOSTAT's SDMX API carries the same
statutory rate as the country reports it, in local currency, annually.

This fetcher stages the national-currency series ONLY. The plate's unit
is US$ per month at the annual average exchange rate, and that
conversion belongs to the plate from the staged FX
(markets/fx_from_imf.csv / markets/fx_from_wb.csv), not to this file:
converting here would bury the exchange-rate convention in a fetcher.

The rate is in guaraníes per month and the guaraní has no minor unit in
practice; no redenomination took place (the 2023 proposal was abandoned).
"""
from __future__ import annotations

import csv
import io
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

# DF_EAR_INEE_CUR_NB = "Monthly minimum wage by currency".
URL = ("https://sdmx.ilo.org/rest/data/ILO,DF_EAR_INEE_CUR_NB/PRY..."
       "?startPeriod=2006&format=csv")
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}
YEAR_FROM, YEAR_TO = 2006, 2026

COMMENTS = [
    "ILOSTAT DF_EAR_INEE_CUR_NB, 'Monthly minimum wage by currency',",
    "Paraguay, annual: the statutory national minimum wage in guaranies",
    "per month, as the country reports it. The national publisher (MTESS)",
    "has no machine series and the open-data portal datos.gov.py is down.",
    "NOT converted to US$ here: the plate converts with the staged annual",
    "average exchange rate, and the guaraní has no minor unit in practice.",
]


def fetch() -> bytes:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / "ilo_minwage.csv"
    if path.exists():
        return path.read_bytes()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            if b"OBS_VALUE" not in raw:
                raise ValueError("not an SDMX csv payload")
            path.write_bytes(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  ilo attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise SystemExit(f"cannot fetch {URL}: {last}")


def main() -> None:
    print("ILOSTAT minimum wage for Paraguay")
    rows = list(csv.DictReader(io.StringIO(fetch().decode("utf-8"))))
    series = {}
    for row in rows:
        if row.get("CUR") != "CUR_TYPE_LCU":
            continue
        value = row.get("OBS_VALUE")
        if value in (None, ""):
            continue
        series[int(row["TIME_PERIOD"])] = float(value)
    if not series:
        raise SystemExit("no local-currency minimum wage rows")
    # 2006 = 1,219,795 guaranies/month, the decree in force that year.
    assert abs(series[2006] - 1_219_795) < 1, series.get(2006)
    # The decree is revised by decree, never cut; a fall would mean a
    # different series or a denomination change. ILOSTAT currently ends
    # at 2024 — the 2025 decree is not in this dataset yet, and the
    # plate leaves 2025 blank rather than carrying 2024 forward.
    years = sorted(series)
    for a, b in zip(years, years[1:]):
        assert series[b] >= series[a], f"minimum wage fell {a}->{b}"
    assert abs(series[2024] - 2_798_309) < 1, series.get(2024)
    path = ROOT / "data" / "people" / "minimum_wage_from_ilo.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in COMMENTS]
    lines.append("year,minimum_wage_pyg_month")
    count = 0
    for y in sorted(series):
        if YEAR_FROM <= y <= YEAR_TO:
            lines.append(f"{y},{series[y]:.0f}")
            count += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/people/minimum_wage_from_ilo.csv  {count} rows")
    print("Done. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
