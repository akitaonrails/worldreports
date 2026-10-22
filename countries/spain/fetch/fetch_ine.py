#!/usr/bin/env python3
"""Refresh the INE series for Spain into sidecar CSVs.

Usage:  python3 -I countries/spain/fetch/fetch_ine.py

The Instituto Nacional de Estadística's Tempus3/jaxiT3 JSON API needs no
key and serves the series the INE computes itself — the national accounts,
the IPC, the EPA labour force survey, the continuous population register,
vital statistics, causes of death, and the national twin of the migration
flows:

  CNTR6548    CNTR, quarterly GDP at current prices, €mn (no s.a.)
  IPC290751   IPC general national index, monthly, LINKED series
              (published today in base 2025; the base moved 2006 → 2011
              → 2016 → 2021 → 2025 and the linked series absorbs each
              rebase)
  EPA648630   EPA unemployment rate, national, annual average
  ECP320      Estadística Continua de Población: resident population,
              national total, quarterly grid (1 January = FK_Periodo 19)
  MNP17451    births, national, monthly (MNP, by mother's residence)
  MNP89585    deaths, national, monthly (MNP, by residence)
  ECM table   Defunciones según la Causa de Muerte, lista reducida,
  9936        national totals by cause, annual — including ECM12,
              "Agresiones (homicidio)", the death-certificate count that
              pairs with the police count (SOURCING §4)
  EM825679    immigration from abroad (Estadística de Migraciones)
  EM1392987   emigration abroad (idem)
  EM1393263   migration balance with abroad (idem)

Things this API will do to you:

**Error pages arrive as HTTP 200 HTML in ISO-8859-15.** A bad table id
answers 200 with an HTML 404 page, and DATOS_SERIE without `nult` answers
a real 404. The payload is checked for its JSON shape before caching.

**`nult` caps each series at about 300 rows.** The IPC's monthly series
since 2002 is 297 rows and just fits; anything longer must be paged or
split. None of the series here is longer.

**Period codes are numeric and non-obvious:** 19-22 are Q1-Q4, 1-12 are
the months, 28 is the annual figure (EPA annual average, ECM annual
totals). The fetcher filters on them explicitly.

**Spanish quarterly GDP is published as quarterly LEVELS**, not
annualised rates — the annual figure is the SUM of the four quarters,
and a year with fewer than four published quarters is left blank, never
scaled up.

**MNP births and deaths are provisional for the most recent year or
two** and are revised upward as late registrations arrive; a partial year
is left blank with its month count carried in `*_months`.

Outputs are `_from_ine.csv` sidecars. Nothing here overwrites a curated
file.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

BASE = "https://servicios.ine.es/wstempus/js/ES"
Y0, Y1 = 2006, 2026

Q1 = 19          # FK_Periodo for the first quarter (ECP: 1 January)
ANNUAL = 28      # FK_Periodo for annual figures
MONTHS = set(range(1, 13))
QUARTERS = {19, 20, 21, 22}


def get(path: str) -> object:
    """One JSON document from the Tempus API, shape-checked before caching.

    The error pages this gateway serves under HTTP 200 are ISO-8859-15
    HTML, so a payload that does not start with '{' or '[' after decoding
    is treated as an error rather than cached.
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / ("ine_" + path.replace("/", "_")
                          .replace("?", "_").replace("=", "_")
                          .replace("&", "_") + ".json")
    if cache_file.exists():
        raw = cache_file.read_bytes()
    else:
        last = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(f"{BASE}/{path}",
                                            timeout=120) as r:
                    raw = r.read()
                head = raw.lstrip()[:1]
                if head not in (b"{", b"["):
                    raise ValueError("not JSON (HTML error page?)")
                cache_file.write_bytes(raw)
                break
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"ine {path}: {last}")
    for enc in ("utf-8", "latin-1"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise RuntimeError(f"ine {path}: undecodable payload")


def serie(cod: str, nult: int = 300) -> list[dict]:
    """One series' Data rows as [{Anyo, FK_Periodo, Valor}, ...]."""
    payload = get(f"DATOS_SERIE/{cod}?nult={nult}")
    if not isinstance(payload, dict) or "Data" not in payload:
        raise RuntimeError(f"{cod}: not a series response")
    return payload["Data"]


def annual_only(data: list[dict]) -> dict[int, float]:
    """{year: value} from rows where FK_Periodo is the annual one."""
    return {x["Anyo"]: x["Valor"] for x in data
            if x["FK_Periodo"] == ANNUAL and Y0 <= x["Anyo"] <= Y1}


def sum_periods(data: list[dict], periods: set) -> dict[int, tuple[float, int]]:
    """{year: (total, n_periods)} summing monthly/quarterly levels.

    The caller decides what completeness means; a partial year is written
    blank with its period count carried in a `*_months`-style column.
    """
    by_year: dict[int, list[float]] = {}
    for x in data:
        if x["FK_Periodo"] in periods and Y0 <= x["Anyo"] <= Y1:
            by_year.setdefault(x["Anyo"], []).append(x["Valor"])
    return {y: (sum(vs), len(vs)) for y, vs in by_year.items()}


def write(rel: str, header: str, columns: list[dict], fmts: list[str]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [header]
    for y in range(Y0, Y1 + 1):
        cells = []
        for col, fmt in zip(columns, fmts):
            v = col.get(y)
            cells.append("" if v is None else fmt.format(v))
        lines.append(f"{y}," + ",".join(cells))
    path.write_text("\n".join(lines) + "\n")
    print(f"  -> data/{rel}")


def main() -> None:
    print("Fetching INE series for Spain...")

    # ---- GDP: quarterly current-price levels summed to the year --------
    gdp_q = sum_periods(serie("CNTR6548", nult=250), QUARTERS)
    gdp = {y: t / 1000 for y, (t, n) in gdp_q.items() if n == 4}
    write("macro/gdp_from_ine.csv", "year,nominal_eurbn", [gdp], ["{:.2f}"])
    if abs(gdp.get(2024, 0) - 1593) > 20:
        print("  !! GDP 2024 off the expected ~€1.6tn", file=sys.stderr)

    # ---- IPC: linked index, annual mean, and the rate of that mean -----
    ipc_m = serie("IPC290751", nult=300)
    idx = {y: t / n for y, (t, n) in sum_periods(ipc_m, MONTHS).items()
           if n == 12}
    rate = {y: (idx[y] / idx[y - 1] - 1) * 100
            for y in idx if y - 1 in idx}
    write("macro/ipc_from_ine.csv", "year,ipc_index_avg,ipc_rate",
          [idx, rate], ["{:.3f}", "{:.2f}"])
    if abs(rate.get(2024, 0) - 2.8) > 0.15:
        print("  !! IPC 2024 off the official 2.8%", file=sys.stderr)

    # ---- EPA: national unemployment rate, annual average ---------------
    epa = annual_only(serie("EPA648630", nult=100))
    write("macro/unemployment_from_ine.csv", "year,epa_avg", [epa],
          ["{:.2f}"])
    if abs(epa.get(2024, 0) - 11.4) > 0.3:
        print("  !! EPA 2024 off the official ~11.4%", file=sys.stderr)

    # ---- Population: ECP resident total at 1 January -------------------
    ecp = serie("ECP320", nult=250)
    pop = {x["Anyo"]: x["Valor"] for x in ecp
           if x["FK_Periodo"] == Q1 and Y0 <= x["Anyo"] <= Y1}
    write("social/population_from_ine.csv", "year,population", [pop],
          ["{:.0f}"])
    if abs(pop.get(2025, 0) - 49_128_297) > 300_000:
        print("  !! ECP 1-Jan-2025 off the published 49.13mn",
              file=sys.stderr)

    # ---- Vital statistics: monthly births and deaths summed ------------
    births = sum_periods(serie("MNP17451", nult=300), MONTHS)
    deaths = sum_periods(serie("MNP89585", nult=300), MONTHS)
    b_tot = {y: t for y, (t, n) in births.items() if n == 12}
    b_m = {y: n for y, (t, n) in births.items() if n != 12}
    d_tot = {y: t for y, (t, n) in deaths.items() if n == 12}
    d_m = {y: n for y, (t, n) in deaths.items() if n != 12}
    write("social/vital_from_ine.csv",
          "year,births,births_months,deaths,deaths_months",
          [b_tot, b_m, d_tot, d_m], ["{:.0f}", "{:.0f}", "{:.0f}", "{:.0f}"])

    # ---- Causes of death: the reduced list, national totals ------------
    # SERIES_TABLA pages from the national both-sex totals first; six
    # pages cover the whole reduced list (102 causes × 3 sexes ≈ 306).
    codes: dict[str, str] = {}
    for page in range(1, 7):
        for s in get(f"SERIES_TABLA/9936?page={page}"):
            name = s["Nombre"]
            if ("Total Nacional" in name and ". Total. Todas las edades."
                    in name):
                cause = name.split(".")[0].strip()
                codes.setdefault(cause, s["COD"])
        time.sleep(0.3)
    if "Agresiones (homicidio)" not in codes:
        raise RuntimeError("ECM: assault cause not found in series list")
    causes: dict[str, dict[int, float]] = {}
    for cause, cod in sorted(codes.items()):
        try:
            causes[cause] = annual_only(serie(cod, nult=40))
        except RuntimeError as e:
            print(f"  !! {cause}: {e}", file=sys.stderr)
        time.sleep(0.2)
    # long format is kinder here: one row per year × cause
    lines = ["year,cause,deaths"]
    for cause in sorted(causes):
        for y in range(Y0, Y1 + 1):
            v = causes[cause].get(y)
            if v is not None:
                lines.append(f"{y},{json.dumps(cause, ensure_ascii=False)},{v:.0f}")
    path = DATA / "social" / "causes_of_death_from_ine.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    print(f"  -> data/social/causes_of_death_from_ine.csv "
          f"({len(causes)} causes)")

    # ---- Migration flows: the national twin of the Eurostat files ------
    imm = annual_only(serie("EM825679", nult=40))
    emi = annual_only(serie("EM1392987", nult=40))
    saldo = annual_only(serie("EM1393263", nult=40))
    write("migration/migration_flows_from_ine.csv",
          "year,immigration,emigration,balance",
          [imm, emi, saldo], ["{:.0f}", "{:.0f}", "{:.0f}"])
    if abs(imm.get(2019, 0) - 750_480) > 1:
        print("  !! EM immigration 2019 off the published 750,480",
              file=sys.stderr)

    # The EMCR replaced the EM in 2021 and counts on a wider net: 2021
    # exists on BOTH (EM 528,856; EMCR 887,960), which makes the break
    # measurable rather than asserted. Two files, two segments, never one
    # line stitched across 2021.
    emcr_imm = annual_only(serie("EM1765217", nult=20))
    emcr_emi = annual_only(serie("EM1843418", nult=20))
    write("migration/migration_flows_emcr_from_ine.csv",
          "year,immigration_emcr,emigration_emcr",
          [emcr_imm, emcr_emi], ["{:.0f}", "{:.0f}"])
    if abs(emcr_imm.get(2021, 0) - 887_960) > 1:
        print("  !! EMCR immigration 2021 off the published 887,960",
              file=sys.stderr)

    print("Done. Diff the *_from_ine.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
