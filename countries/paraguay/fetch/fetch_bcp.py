#!/usr/bin/env python3
"""Probe the Banco Central del Paraguay, and stage nothing.

Usage:  make C=paraguay fetch   (or: python3 -I fetch/fetch_bcp.py)

This fetcher exists to make one thing checkable rather than remembered:
the BCP is the publisher of Paraguay's national accounts, its consumer
price index, the policy rate, the guaraní's reference rate, reserves and
household credit, and **every path on bcp.gov.py answers a Cloudflare
"Just a moment..." challenge (HTTP 403) from this network**, on both
schemes, with a browser User-Agent, on the www host and on the
subdomains that resolve at all.

So this script probes and reports. It writes no sidecar, because there is
nothing to write: a fetcher that invented a series here would be the one
thing this arrangement exists to prevent. The harmonised layer in
fetch_imf.py and fetch_wb.py carries the same quantities as the IMF and
the World Bank record them, and SOURCES.yaml's `meta.pending` names every
BCP endpoint that was tried, with its status, so the gap is disclosed
rather than hidden.

Exit status is 0 on a confirmed block **deliberately**: `make fetch`
runs every fetcher in the directory and stops on the first non-zero, and
one known-blocked publisher must not stop the six that answer. The
probe's verdict is printed, and a future successful probe prints
"REACHABLE" for whoever re-opens the national layer.
"""
from __future__ import annotations

import sys
import urllib.request

PATHS = [
    "https://www.bcp.gov.py/",
    "https://www.bcp.gov.py/webapps/web/cuadroestadistico",
    "https://www.bcp.gov.py/webapps/sie/",
    "https://estadisticas.bcp.gov.py/",
    "https://www.bcp.gov.py/anexo/1",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/122.0 Safari/537.36"}
MARKERS = (b"Just a moment", b"cf-chl", b"challenge-platform")


def probe(url: str) -> tuple[int, bool]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read(4000)
            return r.status, not any(m in body for m in MARKERS)
    except urllib.error.HTTPError as e:
        body = e.read(4000)
        challenged = any(m in body for m in MARKERS)
        return e.code, not challenged
    except Exception as e:  # noqa: BLE001
        print(f"  {url}: no connection ({e})", file=sys.stderr)
        return 0, False


def main() -> None:
    print("Banco Central del Paraguay — probe only, nothing staged")
    reachable = False
    for url in PATHS:
        status, real = probe(url)
        verdict = "reachable" if real else "BLOCKED (challenge page)"
        print(f"  HTTP {status:>3}  {verdict:<24} {url}")
        reachable = reachable or real
    if reachable:
        print("REACHABLE: the national layer can be rebuilt. Write the "
              "fetcher that replaces the harmonised series with the BCP's "
              "own, and update SOURCES.yaml meta.pending.")
    else:
        print("BLOCKED: no sidecar written. The gap is disclosed in "
              "SOURCES.yaml meta.pending and on the page.")


if __name__ == "__main__":
    main()
