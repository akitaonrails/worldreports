"""HTTP and SDMX plumbing shared by Australia's refreshers.

The atlas rule is that a fetcher validates what it pulled before it caches
anything: an official gateway that answers HTTP 200 with an error page or a
zero-row body must fail here rather than in a curated file twelve months
later (SOURCING_A_COUNTRY.md, "Endpoints that lie").

Every function either returns parsed rows or raises FetchError. Nothing in
this module writes a file; the callers own their sidecars.
"""
from __future__ import annotations

import csv
import io
import sys
import time
import urllib.error
import urllib.request

UA = ("worldreports-atlas/1.0 (Australia data refresh; "
      "+https://github.com/akitaonrails/worldreports)")

ABS = "https://data.api.abs.gov.au/rest"
IMF = "https://api.imf.org/external/sdmx/2.1"
OECD = "https://sdmx.oecd.org/public/rest"
BIS = "https://stats.bis.org/api/v1"
WB = "https://api.worldbank.org/v2"


class FetchError(RuntimeError):
    """A route answered with something that is not the series asked for."""


def get(url: str, *, tries: int = 3, timeout: int = 180,
        accept: str = "*/*") -> bytes:
    """GET with retries, refusing an HTML body that is not JSON, XML or CSV.

    The ABS and OECD gateways both serve an HTML portal page under a data
    URL when a dataflow id is misspelt, and CloudFront serves an HTML block
    page under HTTP 200 to some networks. Either would parse as zero rows.
    """
    last: Exception | None = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept": accept,
            "Accept-Encoding": "identity"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                ctype = (r.headers.get("content-type") or "").lower()
            if not body:
                raise FetchError(f"empty body from {url}")
            head = body[:400].lstrip().lower()
            if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
                if b"application/json" not in ctype.encode():
                    raise FetchError(f"HTML body from {url} "
                                     f"({len(body)} bytes)")
            return body
        except urllib.error.HTTPError as e:
            # 403/404/422 from a gateway is a route result, not a flake:
            # record it and stop rather than hammering the publisher.
            if e.code in (400, 401, 403, 404, 422):
                raise FetchError(f"HTTP {e.code} from {url}") from None
            last = e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
        time.sleep(2 * (attempt + 1))
    raise FetchError(f"{url}: {last}") from last


# ---------------------------------------------------------------- ABS SDMX
def abs_codelist(codelist: str) -> dict[str, str]:
    """code -> English name for an ABS codelist (CL_* id)."""
    import re

    body = get(f"{ABS}/codelist/ABS/{codelist}").decode("utf-8", "replace")
    out: dict[str, str] = {}
    for m in re.finditer(r'<structure:Code id="([^"]+)"', body):
        tail = body[m.end():m.end() + 900]
        nxt = tail.find("<structure:Code id=")
        nm = re.search(r"<common:Name xml:lang=\"en\">([^<]*)</common:Name>",
                       tail)
        if nm and (nxt == -1 or nm.start() < nxt):
            import html as _html
            out[m.group(1)] = _html.unescape(nm.group(1))
        else:
            nxtc = re.search(r'<common:Name xml:lang="en">([^<]*)<', tail)
            out[m.group(1)] = nxtc.group(1) if nxtc else ""
    return out


def abs_codes(flow: str, codelist: str) -> dict[str, str]:
    """Codes of an ABS dataflow's dimension, resolved by codelist id."""
    return abs_codelist(codelist)


def abs_data(flow: str, key: str, start: str) -> list[dict]:
    """Rows of an ABS SDMX dataflow slice, AllDimensions, as dicts.

    The CSV carries the dimension ids as its header, so callers filter on
    names rather than positions. Rows come back in whatever order the
    gateway likes; every caller sorts before caching.
    """
    url = (f"{ABS}/data/ABS,{flow}/{key}?startPeriod={start}"
           f"&dimensionAtObservation=AllDimensions&format=csv")
    body = get(url, accept="text/csv")
    text = body.decode("utf-8-sig", "replace")
    if not text.lstrip().lower().startswith("dataflow"):
        raise FetchError(f"{flow}/{key}: not an SDMX CSV: {text[:120]!r}")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise FetchError(f"{flow}/{key}: zero rows")
    for r in rows:
        if (r.get("OBS_VALUE") or "").strip() == "":
            r["OBS_VALUE"] = ""
    return rows


# ------------------------------------------------------------- plain CSV
def csv_rows(body: bytes) -> list[dict]:
    text = body.decode("utf-8-sig", "replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise FetchError("zero CSV rows")
    return rows


def die(msg: str) -> None:
    print(f"fetch error: {msg}", file=sys.stderr)
    raise SystemExit(1)
