#!/usr/bin/env python3
"""Banco Central de Chile — probe the machine-readable routes (2026-10-25).

Usage:  python3 -I countries/chile/fetch/fetch_bcentral.py

The Bank is the publisher of the policy rate, the 10-year sovereign yield,
the exchange rate and the monetary aggregates, and it runs the best-known
statistical API in the country (SieteRestWS). Every route below was tried
on 2026-10-25 from this network. None of them answered with data, so this
script stages nothing and exits non-zero: a fetcher that cannot confirm
what it pulled must not write.

What the plate uses instead is recorded in SOURCES.yaml:
  policy rate      BIS WS_CBPOL D.CL (the Bank's own series, harmonised)
  exchange rate    World Bank PA.NUS.FCRF (annual average, from the Bank)
  10-year yield    PENDING — no route answered (see meta.pending)
  equity / IPSA    PENDING — Bolsa de Santiaago serves a bot wall
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe import probe, report  # noqa: E402

PUBLISHER = "Banco Central de Chile"

ROUTES = [
    ("https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
     "?user=&pass=&function=GetSeries&timeseries=G073"
     "&firstdate=2020-01-01&lastdate=2020-12-31",
     "the documented REST API, anonymous: HTTP 200 with an HTML error page "
     "and a redirect to ErrorPage.htm — not data"),
    ("https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
     "?user=test&pass=test&function=GetSeries&timeseries=G073"
     "&firstdate=2020-01-01&lastdate=2020-12-31",
     "the same call with credentials: HTTP 200 and JSON "
     '{"Codigo": -5, "Descripcion": "Invalid username or password"} — the '
     "API is credentialled and the Bank issues tokens by registration"),
    ("https://www.bcentral.cl/web/guest/estadisticas",
     "the Bank's public statistics site: an Incapsula bot wall under 200"),
    ("https://si3.bcentral.cl/estadisticas/Principal1/Excel/CCNN/PIB/"
     "PIB_trimestral.xls",
     "the old static Excel tree the API replaced: bot wall under 200, "
     "served as HTML, so a naive fetcher would parse a page as a workbook"),
    ("https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_MONET_POL_MON/"
     "PM_PDT/PM_TPM",
     "the Siete table viewer: an HTML shell whose grid is filled by "
     "JavaScript; no CSV or JSON endpoint behind it without a session"),
]


def main() -> int:
    results = [probe(url, note) for url, note in ROUTES]
    report(PUBLISHER, results)
    return 2


if __name__ == "__main__":
    sys.exit(main())
