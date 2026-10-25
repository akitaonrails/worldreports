#!/usr/bin/env python3
"""Servicio de Impuestos Internos — probe the tax-statistics routes.

Usage:  python3 -I countries/chile/fetch/fetch_sii.py

SII publishes the tax take, the number and size distribution of firms
and the exporters' register. The fiscal plate uses the IMF's
general-government revenue (canonical) and the World Bank's tax-revenue
series (GC.TAX.TOTL.GD.ZS) beside it; the SII series would be the
national layer, on a central-government-and-taxes-only perimeter.

On 2026-10-25 the SII statistics pages answered as HTML with no
machine-readable table, so nothing is staged and this script exits
non-zero. That is why no SII series appears in SOURCES.yaml.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe import probe, report  # noqa: E402

PUBLISHER = "Servicio de Impuestos Internos (SII)"

ROUTES = [
    ("https://www.sii.cl/sobre_el_sii/estadisticas_de_empresas.html",
     "the firm-statistics page answers as HTML; its tables are per-year "
     "pages with downloads attached, not one series"),
    ("https://www.sii.cl/estadisticas/inicio.htm",
     "the statistics landing page the site still links: HTTP 404"),
    ("https://datos.gob.cl/api/3/action/package_search?q=impuestos&rows=5",
     "the state open-data portal returns municipal and unrelated tax "
     "datasets, no SII revenue series"),
]


def main() -> int:
    results = [probe(url, note) for url, note in ROUTES]
    report(PUBLISHER, results)
    return 2


if __name__ == "__main__":
    sys.exit(main())
