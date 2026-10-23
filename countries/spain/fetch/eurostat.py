"""Minimal Eurostat dissemination-API client.

Eurostat serves JSON-stat: one flat `value` map keyed by a *linear* index over
the cube's dimensions, plus the dimension sizes. Decoding it means
reconstructing the strides — which is the one piece of this that is easy to
get subtly wrong, so it lives here once and is unit-tested rather than
reimplemented per series.

The API needs no key and is the authoritative publication channel for the
ESA 2010 national accounts and the EDP (Maastricht) fiscal series that France
reports to Eurostat, so it is the primary source for anything that is a
European statistical obligation. Where INSEE publishes its own national
series of the same thing (the IPC, the ILO unemployment rate), INSEE is the
primary and this is the cross-check.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/"
        "data/{dataset}")
ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"


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
    """{(code, code, ..., time): value} for every populated cell.

    The key is the dimension codes in the cube's own dimension order, so the
    caller reads it with `payload["id"].index("time")` rather than guessing.
    """
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


def fetch(dataset: str, cache_key: str | None = None, **filters) -> dict:
    """One Eurostat cube, cached under cache/ so re-runs are free."""
    CACHE.mkdir(exist_ok=True)
    key = cache_key or dataset + "_" + "_".join(
        f"{k}-{v}" for k, v in sorted(filters.items()))
    cache_file = CACHE / f"estat_{key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    query = urllib.parse.urlencode({"format": "JSON", **filters}, doseq=True)
    url = f"{BASE.format(dataset=dataset)}?{query}"
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                payload = json.loads(r.read())
            if "value" not in payload:
                raise ValueError("no value map in response")
            cache_file.write_text(json.dumps(payload))
            return payload
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"eurostat {dataset} {filters}: {last}")


def annual(dataset: str, cache_key: str | None = None,
           **filters) -> dict[int, float]:
    """A single annual series as {year: value}.

    Every dimension except `time` must be pinned by a filter, otherwise the
    cube carries more than one series and silently returning one of them is
    exactly the kind of error this repo exists to avoid.
    """
    payload = fetch(dataset, cache_key, **filters)
    ids = payload["id"]
    free = [d for d, n in zip(ids, payload["size"]) if n > 1 and d != "time"]
    if free:
        raise ValueError(
            f"{dataset}: {free} left unpinned — the cube holds several series")
    t = ids.index("time")
    out = {}
    for key, value in decode(payload).items():
        period = key[t]
        if period.isdigit():
            out[int(period)] = value
    return out
