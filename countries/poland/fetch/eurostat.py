"""Minimal Eurostat dissemination-API client for Poland.

Eurostat serves JSON-stat: a flat `value` map keyed by a *linear* index over
the cube's dimensions, plus the dimension sizes. Decoding means rebuilding
the strides — the one piece that is easy to get subtly wrong, so it lives
here once.

Poland is an EU member, so Eurostat is a publisher and not a redistributor:
these are the series Poland is legally obliged to report, harmonised across
members. PLATE_SPINE.md rule 10 makes the harmonised series canonical where
national definitions differ, and `SOURCES.yaml` marks these `official: true`.

The API needs no key. The national line from GUS rides beside it.
"""
from __future__ import annotations

import json
import urllib.parse

from common import CACHE, FetchError, get

BASE = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/"
        "data/{dataset}")


def strides(size: list[int]) -> list[int]:
    """Row-major strides for a cube of these dimension sizes.

    JSON-stat numbers its cells with the LAST dimension varying fastest, so
    the stride of dimension i is the product of every size after it.
    """
    out = [1] * len(size)
    for i in range(len(size) - 2, -1, -1):
        out[i] = out[i + 1] * size[i + 1]
    return out


def decode(payload: dict) -> dict[tuple[str, ...], float]:
    """{(code, ..., time): value} for every populated cell."""
    ids, size = payload["id"], payload["size"]
    cats = []
    for dim in ids:
        index = payload["dimension"][dim]["category"]["index"]
        if isinstance(index, dict):
            cats.append({pos: code for code, pos in index.items()})
        else:  # a single-category dimension may come back as a bare list
            cats.append(dict(enumerate(index)))
    st = strides(size)
    out = {}
    for flat, value in payload["value"].items():
        n = int(flat)
        key = tuple(cats[i][(n // st[i]) % size[i]] for i in range(len(ids)))
        out[key] = value
    return out


def fetch(dataset: str, **filters) -> dict:
    """One Eurostat cube, cached under cache/ so re-runs are free."""
    query = urllib.parse.urlencode({"format": "JSON", "lang": "EN", **filters})
    url = f"{BASE.format(dataset=dataset)}?{query}"
    body = get(url, suffix=".json", timeout=180)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        raise FetchError(f"eurostat {dataset}: not JSON") from e
    if "value" not in payload:
        raise FetchError(
            f"eurostat {dataset} {filters}: no value map "
            f"({str(payload)[:120]})")
    return payload


def annual(dataset: str, **filters) -> dict[int, float]:
    """A single annual series as {year: value}.

    Every dimension except `time` must be pinned by a filter, otherwise the
    cube holds more than one series and silently returning one of them is
    exactly the error this repository exists to avoid.
    """
    payload = fetch(dataset, **filters)
    ids = payload["id"]
    free = [d for d, n in zip(ids, payload["size"]) if n > 1 and d != "time"]
    if free:
        raise FetchError(
            f"{dataset}: {free} left unpinned — the cube holds "
            f"several series")
    t = ids.index("time")
    out = {}
    for key, value in decode(payload).items():
        period = key[t]
        if period.isdigit():
            out[int(period)] = value
    return out


def multi(dataset: str, keep: str, **filters) -> dict[str, dict[int, float]]:
    """{code: {year: value}} for one free dimension named `keep`.

    Use when the cube legitimately holds several series — a breakdown by
    citizenship, or a set of COFOG functions — but exactly one dimension
    varies. Anything else left free is a mistake and raises.
    """
    payload = fetch(dataset, **filters)
    ids = payload["id"]
    free = [d for d, n in zip(ids, payload["size"]) if n > 1 and d != "time"]
    if free != [keep] and free != [keep, "time"] and free != ["time", keep]:
        raise FetchError(
            f"{dataset}: expected only {keep!r} free, got {free}")
    k = ids.index(keep)
    t = ids.index("time")
    out: dict[str, dict[int, float]] = {}
    for key, value in decode(payload).items():
        period = key[t]
        if not period.isdigit():
            continue
        out.setdefault(key[k], {})[int(period)] = value
    return out


def monthly(dataset: str, **filters) -> dict[tuple[int, int], float]:
    """A single monthly series as {(year, month): value}."""
    payload = fetch(dataset, **filters)
    ids = payload["id"]
    free = [d for d, n in zip(ids, payload["size"]) if n > 1 and d != "time"]
    if free:
        raise FetchError(f"{dataset}: {free} left unpinned")
    t = ids.index("time")
    out = {}
    for key, value in decode(payload).items():
        period = key[t]
        if len(period) == 7 and period[4] == "-":
            out[(int(period[:4]), int(period[5:]))] = value
    return out
