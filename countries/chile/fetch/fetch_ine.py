#!/usr/bin/env python3
"""Instituto Nacional de Estadísticas — probe the machine-readable routes.

Usage:  python3 -I countries/chile/fetch/fetch_ine.py

INE computes the CPI, the labour force survey, the population projections
and the vital statistics. Its site answers this network, but every route
to a *series* was tried on 2026-10-25 and none of them returned one: the
statistics pages carry methodology PDFs and news bulletins, the bulk files
are behind an interactive viewer, and the API portal is a login page with
no anonymous endpoint. Nothing is staged here and the script exits
non-zero.

Consequence for the plates, kept in SOURCES.yaml:
  CPI              economy slot 3 uses the World Bank's republication of
                   the national index (FP.CPI.TOTL.ZG) — the national line
                   joins it when INE's series API answers.
  unemployment     ILO-modelled WDI (SL.UEM.TOTL.ZS), labelled modelled.
  population       demography slot 1 uses INE's projected population as
                   embedded in the DEIS weekly-deaths file (fetch_deis.py),
                   which is an INE projection, and the World Bank series
                   beside it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe import probe, report  # noqa: E402

PUBLISHER = "Instituto Nacional de Estadísticas (INE)"

ROUTES = [
    ("https://stat.ine.cl/",
     "the INE.STAT data portal: an HTML login shell ('INE.STAT'), no "
     "statistics served anonymously"),
    ("https://stat.ine.cl/api/v1/auth/login",
     "the API's own auth path: HTTP 404, so the documented /api/v1 tree is "
     "not exposed on this host any more"),
    ("https://www.ine.gob.cl/estadisticas/economia/indices-de-precio-e-"
     "inflacion/indice-de-precios-al-consumidor",
     "the IPC page answers, but the only downloads it links are the monthly "
     "bulletins as PDF; no xlsx or csv of the index"),
    ("https://www.ine.gob.cl/estadisticas/sociales/demografia-y-vitales/"
     "proyecciones-de-poblacion",
     "the population-projections page: same shape, narrative and PDFs, no "
     "machine-readable table"),
    ("https://datos.gob.cl/api/3/action/package_search"
     "?fq=organization:instituto_nacional_de_estadisticas&rows=100",
     "the state open-data portal does list 63 INE datasets — IPC and ENE "
     "included — but every statistical one has zero resources attached "
     "(package_show? id=ipc -> num_resources 0): stale catalogue entries "
     "pointing back at ine.gob.cl"),
]


def main() -> int:
    results = [probe(url, note) for url, note in ROUTES]
    report(PUBLISHER, results)
    return 2


if __name__ == "__main__":
    sys.exit(main())
