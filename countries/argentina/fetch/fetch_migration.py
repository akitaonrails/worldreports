#!/usr/bin/env python3
"""Validate the INDEC 2022 migration report and write review sidecars."""
from __future__ import annotations

import io
from pathlib import Path

import pdfplumber
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "migration"
URL = "https://www.indec.gob.ar/ftp/cuadros/poblacion/censo2022_migraciones.pdf"


def main() -> None:
    error = None
    for _ in range(3):
        try:
            response = requests.get(URL, timeout=120)
            response.raise_for_status()
            raw = response.content
            break
        except requests.RequestException as exc:
            error = exc
    else:
        raise RuntimeError(f"INDEC PDF transfer failed after three attempts: {error}")
    if not raw.startswith(b"%PDF-") or len(raw) < 500_000:
        raise RuntimeError("INDEC migration endpoint did not return the expected PDF")
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    compact = text.replace(".", "").replace(" ", "")
    for expected in ("1933463", "522598", "338299", "161495"):
        if expected not in compact:
            raise RuntimeError(f"INDEC known-value check failed: {expected}")
    (DATA / "foreign_born_census_check.csv").write_text(
        "year,foreign_born,foreign_born_pct\n2010,,4.5\n2022,1933463,4.2\n",
        encoding="utf-8",
    )
    (DATA / "origins_census_2022_check.csv").write_text(
        "origin,count,year\nParaguay,522598,2022\nBolivia,338299,2022\n"
        "Venezuela,161495,2022\n", encoding="utf-8",
    )


if __name__ == "__main__":
    main()
