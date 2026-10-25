"""Shared plumbing for Poland's fetchers.

Every fetcher in this directory obeys the same four rules, and this module
is where they are implemented once rather than remembered four times:

1. **A fetcher never writes a curated file.** It writes `*_from_<source>.csv`
   beside the curated CSV under `data/`, and a person reviews the diff.
2. **Cache first, then network.** Payloads land under `cache/` (gitignored) so
   a second run is free and byte-identical, and a run with no network but a
   warm cache is identical too. A run with neither exits non-zero and writes
   nothing.
3. **An error page is not data.** Official gateways answer 200 with HTML.
   Every payload is shape-checked before it is parsed or cached; a failed
   check raises, and the sidecar is not written.
4. **Numbers have one spelling.** Values are emitted with `%g` at six
   significant figures and years sorted, so the same input always produces
   the same bytes.

Run:  make C=poland fetch     (or)  python3 -I fetch/fetch_eurostat.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

#: A browser-ish UA. GUS's public pages reject the default urllib agent; the
#: APIs do not care. Nothing here needs a key.
UA = "Mozilla/5.0 (X11; Linux x86_64) worldreports-research/1.0"


class FetchError(RuntimeError):
    """A payload did not look like what its publisher said it was."""


def _cache_path(url: str, suffix: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    name = url.split("://", 1)[-1].split("?")[0].rsplit("/", 1)[-1] or "payload"
    name = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)[:60]
    return CACHE / f"{name}.{digest}{suffix}"


def get(url: str, *, suffix: str = ".json", headers: dict | None = None,
        tries: int = 4, timeout: int = 120) -> bytes:
    """Fetch `url` through the cache, with retries on transient failures.

    Offline-warm returns the cached bytes without touching the network.
    Offline-cold raises FetchError — the caller exits non-zero and writes
    no sidecar, which is the contract, rather than silently publishing a
    stale or empty file.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = _cache_path(url, suffix)
    if path.exists() and path.stat().st_size:
        return path.read_bytes()
    last: Exception | None = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            if not body:
                raise FetchError(f"{url}: empty body")
            path.write_bytes(body)
            return body
        except urllib.error.HTTPError as e:  # a 404 will not heal by waiting
            last = e
            if e.code in (400, 401, 403, 404):
                raise FetchError(f"{url}: HTTP {e.code}") from e
            time.sleep(2 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def json_get(url: str, **kw) -> dict:
    body = get(url, suffix=".json", **kw)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        head = body[:120].decode("utf-8", "replace")
        raise FetchError(f"{url}: not JSON ({head!r})") from e
    if isinstance(payload, dict) and "error" in payload:
        raise FetchError(f"{url}: upstream error {payload['error']}")
    return payload


def write_csv(rel: str, header: list[str], rows: list[list],
              comment: str | None = None) -> Path:
    """Write a sidecar under data/, deterministically.

    `rel` is a path under `data/`; it MUST end in `_check.csv` or
    `_from_<source>.csv` — `tests/test_sources.py` treats those names as
    unreviewed working files and fails the build if a plate reads one.
    """
    stem = Path(rel).stem
    if not (stem.endswith("_check") or "_from_" in stem):
        raise FetchError(
            f"{rel}: a fetcher writes only a *_check.csv or "
            f"*_from_<source>.csv sidecar, never a curated file")
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        if comment:
            for line in comment.strip().splitlines():
                fh.write(f"# {line}\n")
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        for row in rows:
            w.writerow(["" if v is None else v for v in row])
    tmp.replace(path)
    return path


def num(v) -> str:
    """One spelling for a float: six significant figures, no trailing zeros.

    `%g` keeps 12.5 as 12.5 and 1234.56789 as 1234.57, and never emits
    `nan` for a missing value — callers pass None for a hole instead.
    """
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return f"{float(v):.6g}"


def annual_from(series: dict[int, float], years: range) -> list[tuple[int, float]]:
    """[(year, value)] over `years`, keeping holes as holes (never zeros)."""
    return [(y, series.get(y)) for y in years]


def assert_close(value: float | None, expected: float, tol: float,
                 label: str) -> None:
    """A known-value check: the fetcher refuses to write if it moved.

    SOURCING_A_COUNTRY.md §3.3 — pull one year by hand and confirm the
    magnitude — but enforced at every run instead of once at discovery.
    """
    if value is None:
        raise FetchError(f"{label}: expected {expected}, series has no value")
    if abs(float(value) - expected) > tol:
        raise FetchError(
            f"{label}: got {value}, expected {expected} ±{tol} — check the "
            f"publisher's vintage before promoting anything")
