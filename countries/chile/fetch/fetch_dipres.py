#!/usr/bin/env python3
"""Dirección de Presupuestos (Dipres) — probe the fiscal routes.

Usage:  python3 -I countries/chile/fetch/fetch_dipres.py

Dipres publishes the national fiscal statistics the country argues about:
central-government revenue, expenditure, the balance and the debt stock,
plus the functional classification of spending and the interest bill. The
fiscal plate draws the IMF's general-government layer canonically (the
perimeter every other country is on) and this national layer beside it
where it exists.

On 2026-10-25 none of Dipres' routes returned a machine-readable file:
the site is a Drupal CMS whose statistics section lists PDF bulletins and
Excel downloads behind article pages, and no index of the files answered.
Nothing is staged and the script exits non-zero.

Consequences recorded in SOURCES.yaml:
  fiscal slots 1-3   IMF general government (WEO + Fiscal Monitor), and
                     the World Bank's tax-revenue series beside it.
  interest paid      PENDING: no general-government interest series was
                     retrievable from either route (meta.pending).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe import probe, report  # noqa: E402

PUBLISHER = "Dirección de Presupuestos (Dipres), Ministerio de Hacienda"

ROUTES = [
    ("https://www.dipres.gob.cl/598/w3-channel.html",
     "the statistics channel answers with HTML; its links are article pages "
     "(w3-article-*) and PDF resources, with no file index"),
    ("https://www.dipres.gob.cl/598/w3-propertyvalue-21469.html",
     "the property page the old statistics index used: HTTP 404, the site "
     "was restructured"),
    ("https://www.dipres.gob.cl/597/w3-multipropertyvalues-15199-37782.html",
     "the current fiscal-statistics listing: HTML shell; the Excel files are "
     "attached to individual articles rather than enumerated"),
]


def main() -> int:
    results = [probe(url, note) for url, note in ROUTES]
    report(PUBLISHER, results)
    return 2


if __name__ == "__main__":
    sys.exit(main())
