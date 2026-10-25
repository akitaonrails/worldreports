#!/usr/bin/env python3
"""Comisión para el Mercado Financiero — probe the banking routes.

Usage:  python3 -I countries/chile/fetch/fetch_cmf.py

The CMF (which absorbed the SBIF in 2019) publishes the banking system's
loan book, its delinquency and the lending rates: the credit chapter's
national layer. Its predecessor's open-data files on datos.gob.cl carry
board lending rates ("Tasas de Pizarra de Bancos") but not the arrears
ratio the plate needs.

On 2026-10-25 the CMF's statistics pages answered as HTML and the file
paths under /institucional/estadisticas/ answered 403, so nothing is
staged and this script exits non-zero.

Consequences recorded in SOURCES.yaml:
  household debt   BIS WS_TC (canonical, % of GDP, Q4).
  NPL / arrears    PENDING — no route answered (meta.pending).
  lending rates    datos.gob.cl SBIF/CMF "Tasas de Pizarra" CSVs exist but
                   are board rates for 30-360 day paper, not the mortgage
                   rate the spine asks for, so they are not used as a proxy.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe import probe, report  # noqa: E402

PUBLISHER = "Comisión para el Mercado Financiero (CMF)"

ROUTES = [
    ("https://www.cmfchile.cl/portal/estadisticas/626/w4-propertyname-619.html",
     "the banking statistics page answers as HTML with no file links; the "
     "grids are drawn client-side"),
    ("https://www.cmfchile.cl/institucional/estadisticas/archivos/"
     "estadisticas_mensuales/SP_A.rar",
     "the historical monthly-statistics archive path: HTTP 403"),
    ("https://www.cmfchile.cl/portal/principal/613/w3-channel.html",
     "the CMF home section that used to list the statistical bulletins: "
     "HTML, bulletins as PDF"),
]


def main() -> int:
    results = [probe(url, note) for url, note in ROUTES]
    report(PUBLISHER, results)
    return 2


if __name__ == "__main__":
    sys.exit(main())
