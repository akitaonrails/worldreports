"""Shared probe for Chile's national publishers that block automated access.

Not a fetcher: a fetcher names one publisher and writes that publisher's
sidecar. This is the small transport the probe fetchers share, so that
each of them records the same three facts in the same shape — the exact
URL, the HTTP status and what came back — because those three are the
evidence a pending slot rests on. Run one of the `fetch_<publisher>.py`
scripts to reproduce them.

A probe that a publisher answers with data would be replaced by a real
fetcher; none of the five did on 2026-10-25.
"""
from __future__ import annotations

import urllib.error
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "*/*"}


def probe(url: str, note: str, timeout: int = 45) -> dict:
    """GET `url` and describe what came back, without trusting it."""
    result = {"url": url, "note": note, "status": None, "bytes": 0,
              "kind": "?", "head": ""}
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            result["status"] = r.status
    except urllib.error.HTTPError as e:
        body = e.read() or b""
        result["status"] = e.code
    except Exception as e:  # noqa: BLE001 — a timeout is a route result too
        result["kind"] = f"error: {type(e).__name__}"
        result["head"] = str(e)[:160]
        return result

    result["bytes"] = len(body)
    head = body[:400]
    text = head.decode("utf-8", "replace")
    low = text.lower()
    if body[:2] == b"PK":
        result["kind"] = "xlsx/zip"
    elif body[:4] == b"%PDF":
        result["kind"] = "pdf"
    elif low.lstrip().startswith(("{", "[")):
        result["kind"] = "json"
    elif "<html" in low or "<!doctype" in low:
        result["kind"] = "html"
        if any(k in low for k in ("incapsula", "captcha", "radware",
                                  "access denied", "forbidden")):
            result["kind"] = "html (bot wall)"
        elif "error" in low and "404" in low:
            result["kind"] = "html (404 page)"
    elif "|" in text[:200]:
        result["kind"] = "delimited text"
    result["head"] = " ".join(text.split())[:160]
    return result


def report(publisher: str, probes: list[dict]) -> None:
    """Print the probe table and say plainly that nothing was staged."""
    print(f"{publisher} — route results")
    for p in probes:
        print(f"  [{p['status']}] {p['kind']:<18} {p['bytes']:>8} B  {p['url']}")
        print(f"        {p['note']}")
        if p["head"]:
            print(f"        {p['head']}")
    print(f"  no curated CSV written; see SOURCES.yaml meta.pending")
