#!/usr/bin/env python3
"""Population, births, deaths and fertility from IBGE's Projeções 2024.

Usage:  python3 scripts/fetch_ibge_population.py

Outputs: data/social/population.csv (Brasil, 2000-2070).

The authoritative series is an FTP spreadsheet, NOT SIDRA: SIDRA's projection
tables (7358/7360/7362/7363/7365) still serve the superseded 2018 revision,
where the year is a classification rather than the period, so they look
current and are not. The 2024 revision moved peak population six years
earlier (2047 -> 2041) and cut it by 12.8 million, so the difference matters.

Population here is model output reconciled across the 2000/2010/2022 censuses
(conciliação demográfica + Pesquisa de Pós-Enumeração). It is deliberately
NOT the Censo 2022 enumerated count of 203,080,756 — IBGE adjusts that
upward by 3.90% for undercount. Never plot the two together.
"""
from __future__ import annotations

from pathlib import Path

import openpyxl
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "ibge_pop"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

URL = ("https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024/"
       "projecoes_2024_tab4_indicadores.xlsx")
SHEET = "4) INDICADORES"
HEADER_ROW = 7
# column indices in the sheet, verified against the header row
ANO, LOCAL, POP_T, TCG_T, NASC_T, OBT_T, TFT = 0, 3, 4, 7, 11, 14, 38


def download() -> Path:
    path = CACHE / "projecoes_2024_tab4_indicadores.xlsx"
    if path.exists():
        print(f"  [cache] {path.name}")
        return path
    print(f"  downloading {URL}")
    # the ibge.gov.br HTML pages 403 a default agent; the FTP host does not,
    # but send a real one anyway
    r = requests.get(URL, timeout=300, headers={"User-Agent": "brasil-reports/1.0"})
    r.raise_for_status()
    path.write_bytes(r.content)
    print(f"  -> {path} ({len(r.content):,} bytes)")
    return path


def main() -> None:
    print("Fetching IBGE Projeções da População (revisão 2024)...")
    path = download()
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[SHEET]

    rows = []
    for row in ws.iter_rows(min_row=HEADER_ROW + 1, values_only=True):
        if row[LOCAL] != "Brasil" or row[ANO] is None:
            continue
        rows.append((int(row[ANO]), row[POP_T], row[TCG_T], row[TFT],
                     row[NASC_T], row[OBT_T]))
    rows.sort()
    if not rows:
        raise SystemExit("no Brasil rows found — sheet layout changed?")

    def fmt(v, spec: str) -> str:
        # the first projected year carries no growth rate: there is no prior
        # year to compare against
        return format(v, spec) if v is not None else ""

    lines = ["year,pop_mn,growth_pct,tfr,births,deaths"]
    for y, pop, tcg, tft, nasc, obt in rows:
        lines.append(f"{y},{fmt(pop and pop / 1e6, '.3f')},{fmt(tcg, '.4f')},"
                     f"{fmt(tft, '.4f')},{fmt(nasc, '.0f')},{fmt(obt, '.0f')}")
    out = DATA / "social" / "population.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"  -> data/social/population.csv ({len(rows)} years: "
          f"{rows[0][0]}-{rows[-1][0]})")

    peak = max(rows, key=lambda r: r[1])
    after = [r for r in rows if r[0] > peak[0]]
    print(f"  peak population: {peak[1]:,} in {peak[0]}"
          + (f"; declines from {after[0][0]}" if after else ""))
    tfr = {r[0]: r[3] for r in rows}
    print(f"  TFR 2000 {tfr[2000]:.4f} -> 2023 {tfr[2023]:.4f} "
          f"({(tfr[2023] / tfr[2000] - 1) * 100:+.1f}%)")
    print("Done.")


if __name__ == "__main__":
    main()
