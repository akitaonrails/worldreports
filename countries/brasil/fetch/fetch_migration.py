#!/usr/bin/env python3
"""Validate IBGE census migration values and write review sidecars.

The projection report's 2020 components fail the gross-flow identity check,
so this fetcher deliberately does not emit a gross-flow sidecar.
"""
from __future__ import annotations

import io
from pathlib import Path

import pdfplumber
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "migration"
REPORT = "https://biblioteca.ibge.gov.br/visualizacao/livros/liv102187.pdf"
SIDRA = ("https://apisidra.ibge.gov.br/values/t/10157/n1/all/v/93/p/2022/"
         "c2/6794/c58/95253/c302/all?formato=json")


def main() -> None:
    response = requests.get(REPORT, timeout=90)
    response.raise_for_status()
    raw = response.content
    if not raw.startswith(b"%PDF-") or len(raw) < 500_000:
        raise RuntimeError("IBGE migration endpoint did not return the expected PDF")
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    compact = text.replace(".", "").replace(" ", "")
    for expected in ("1064056", "646015"):
        if expected not in compact:
            raise RuntimeError(f"IBGE known-value check failed: {expected}")
    sidra_response = requests.get(SIDRA, timeout=30)
    sidra_response.raise_for_status()
    rows = sidra_response.json()
    if not rows or "D6N" not in rows[0]:
        raise RuntimeError("SIDRA table 10157 returned an unexpected schema")
    by_nationality = {r["D6N"]: int(r["V"]) for r in rows[1:]}
    expected = {"Total": 203080756, "Naturalizados brasileiros": 216341,
                "Estrangeiros": 793000}
    if any(by_nationality.get(k) != v for k, v in expected.items()):
        raise RuntimeError(f"SIDRA table 10157 known-value check failed: {by_nationality}")
    (DATA / "stock_census_check.csv").write_text(
        "year,total_population,foreign_born,foreign_born_pct,foreign_citizens,"
        "foreign_citizens_pct,naturalized_brazilians,native_brazilians_born_abroad\n"
        "2022,203080756,1064056,0.523963,793000,0.390486,216341,54715\n",
        encoding="utf-8",
    )
    (DATA / "origins_census_check.csv").write_text(
        "year,latin_america_born\n2010,183448\n2022,646015\n", encoding="utf-8")


if __name__ == "__main__":
    main()
