#!/usr/bin/env python3
"""Servicio Nacional de Aduanas — probe the customs statistics routes.

Usage:  python3 -I countries/chile/fetch/fetch_aduana.py

Aduanas is the body that records Chile's goods trade as it crosses the
border, and its "Estadísticas de Comercio Exterior" is the national
customs series. The trade plate draws the national-accounts (goods and
services) series canonically and UN Comtrade for the partner snapshot;
Comtrade's Chilean rows are Aduanas' own declarations, harmonised.

On 2026-10-25 the Aduanas statistics pages answered as HTML and the
dynamic query tool answered a request for a data file with a session
page, so no machine-readable file was staged here. The Comtrade route
(fetch_comtrade.py) is the one that worked, and it is recorded as such.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe import probe, report  # noqa: E402

PUBLISHER = "Servicio Nacional de Aduanas"

ROUTES = [
    ("https://www.aduana.cl/aduana/site/edic/base/port/estadisticas.html",
     "the customs statistics landing page: HTML, with the series behind a "
     "query form rather than a file"),
    ("https://www.aduana.cl/aduana/site/edic/base/port/compendio.html",
     "the annual compendium page: HTML; the workbooks are attached to "
     "individual article pages"),
    ("https://datos.gob.cl/api/3/action/package_search?q=aduana&rows=5",
     "the state open-data portal's Aduana collection: catalogue entries "
     "without statistical resources for this series"),
]


def main() -> int:
    results = [probe(url, note) for url, note in ROUTES]
    report(PUBLISHER, results)
    return 2


if __name__ == "__main__":
    sys.exit(main())
