#!/usr/bin/env python3
"""Refresh SECO's quarterly GDP from its real-time database.

Usage:  python3 -I countries/switzerland/fetch/fetch_seco.py

SECO (Staatssekretariat für Wirtschaft) produces Switzerland's quarterly
national accounts. Its real-time database, realtime-database.xlsx, keeps
every published vintage: one sheet per variable, each a matrix with one
column per release (a release-date row above a vintage-label row that
starts with "time"; label 2026q2 = the vintage released in 2026Q2, carrying
data to 2026Q1), column A = quarter start date, values CHF millions at
previous-year prices, chained, seasonally adjusted).

The file's URL is a DAM id that changes when SECO replaces the asset, so it
is resolved on every run from the page that links it, read through the
site's own JSON content API (the HTML is a Nuxt shell with no links):
/api/collector/de/weiterfuehrende-informationen-bip.json.

Things this source will mislead you about.

**Two GDPs.** `gdp_cssa` is adjusted for calendar effects AND for major
international sporting events: FIFA, IOC and UEFA book their licence
revenue in Switzerland, which lifts measured GDP in championship and
Olympic quarters and drops it after. `gdp` keeps those events in. SECO's
headline is `gdp_cssa`; Eurostat namq_10_gdp (SCA) is NOT event-adjusted.
They are separate columns, never one line.

**The latest vintage lags.** The database is refreshed after SECO's
releases, typically a quarter behind its newest press release. The vintage
used is named in the CSV comment.

**Growth is revised.** `*_qoq_first` is the q/q growth as first published
(the first vintage that carried the quarter), kept beside the current
vintage's growth so revisions are visible, never substituted.

openpyxl needs read_only=True plus ws.reset_dimensions(): the sheets
declare a 1x1 dimension, and the workbook references a missing drawing
that breaks a normal load.

Spot q/q values recorded in SOURCES.yaml are asserted; the event-unadjusted
`gdp` growth is checked against Eurostat namq_10_gdp (a second publisher).
Output is a `_from_seco.csv` sidecar; nothing here overwrites a curated file.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import re
import statistics
import time
import urllib.error
import urllib.request
import warnings
import zipfile
from pathlib import Path

try:
    import openpyxl
except ImportError:
    raise SystemExit("openpyxl is required to read the SECO workbook "
                     "(pip install openpyxl); refusing to skip it silently.")

warnings.filterwarnings("ignore", module="openpyxl")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
INDEX = ("https://www.seco.admin.ch/api/collector/de/"
         "weiterfuehrende-informationen-bip.json")
ESTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
         "namq_10_gdp?geo=CH&na_item=B1GQ&unit=CLV_PCH_PRE&s_adj=SCA&freq=Q")
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}
Y0 = 2006
SHEETS = ("gdp_cssa", "gdp")
MAX_STALE_DAYS = 270

# SOURCES.yaml, gdp_cssa q/q %, rounded to one decimal.
SPOT_QOQ = {"2008Q4": -2.1, "2009Q1": -1.5, "2020Q2": -6.4, "2025Q3": -0.4}


def get(url: str, timeout: int = 600) -> bytes:
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            wait = 30 * (attempt + 1) if e.code in (403, 429) else 3 * (attempt + 1)
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 3 * (attempt + 1)
        time.sleep(wait)
    raise RuntimeError(f"{url}: {last}")


def resolve() -> str:
    """The workbook's current URL, from the page that links it."""
    text = get(INDEX, 120).decode("utf-8")
    json.loads(text)  # an HTML error page fails here
    urls = sorted(set(re.findall(
        r"https://www\.seco\.admin\.ch/dam/[^\"\s]*?/realtime-database\.xlsx", text)))
    if len(urls) != 1:
        raise SystemExit(f"  !! expected one realtime-database.xlsx link, found {urls}")
    return urls[0]


def workbook() -> tuple[Path, str]:
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "seco_realtime-database.xlsx"
    url_file = CACHE / "seco_realtime-database.url"
    if cache_file.exists() and not zipfile.is_zipfile(cache_file):
        cache_file.unlink()          # a truncated download never survives
    if not cache_file.exists():
        url = resolve()
        blob = get(url)
        if not blob.startswith(b"PK"):
            raise RuntimeError(f"{url}: not an xlsx (error page?)")
        names = zipfile.ZipFile(io.BytesIO(blob)).namelist()
        if not any(n.startswith("xl/worksheets/") for n in names):
            raise RuntimeError(f"{url}: zip without worksheets")
        cache_file.write_bytes(blob)
        url_file.write_text(url)
    url = url_file.read_text().strip() if url_file.exists() else "(cached)"
    return cache_file, url


def quarter(d) -> str | None:
    if isinstance(d, dt.datetime):
        d = d.date()
    if isinstance(d, dt.date):
        return f"{d.year}Q{(d.month - 1) // 3 + 1}"
    return None


def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str):
        try:
            return dt.date.fromisoformat(v.strip()[:10])
        except ValueError:
            return None
    return None


def vintages(wb, name: str) -> list[dict]:
    """[{label, release, data:{quarter: value}}] in column order."""
    if name not in wb.sheetnames:
        raise SystemExit(f"  !! sheet {name} missing (have {wb.sheetnames[:12]}…)")
    ws = wb[name]
    ws.reset_dimensions()
    rows = list(ws.iter_rows(values_only=True))
    # The label row starts with "time"; the release dates sit just above it.
    li = next((i for i, r in enumerate(rows) if r and r[0] == "time"), None)
    if li is None or li == 0:
        raise SystemExit(f"  !! {name}: no 'time' header row")
    release_row, label_row = rows[li - 1], rows[li]
    width = max(len(r) for r in rows)
    cols = []
    for j in range(1, width):
        label = label_row[j] if j < len(label_row) else None
        if not (isinstance(label, str) and re.fullmatch(r"\d{4}q[1-4]", label.strip())):
            continue
        cols.append({"j": j, "label": label.strip(),
                     "release": as_date(release_row[j] if j < len(release_row) else None),
                     "data": {}})
    if not cols:
        raise SystemExit(f"  !! {name}: no vintage labels in row 10")
    for r in rows[li + 1:]:
        q = quarter(r[0]) if r else None
        if not q:
            continue
        for c in cols:
            v = r[c["j"]] if c["j"] < len(r) else None
            if isinstance(v, (int, float)):
                c["data"][q] = float(v)
    cols = [c for c in cols if c["data"]]
    return cols


def prev_q(q: str) -> str:
    y, n = int(q[:4]), int(q[5])
    return f"{y - 1}Q4" if n == 1 else f"{y}Q{n - 1}"


def qoq(data: dict[str, float], q: str):
    p = prev_q(q)
    if q in data and p in data:
        return (data[q] / data[p] - 1) * 100
    return None


def first_release_qoq(cols: list[dict]) -> dict[str, float]:
    """Only a quarter that is the NEWEST in some vintage has a first release
    here; quarters older than the first vintage on the sheet stay blank
    (the sheet's first vintage is not their first publication)."""
    out: dict[str, float] = {}
    for c in cols:                       # column order = release order
        q = max(c["data"])
        if q not in out:
            g = qoq(c["data"], q)
            if g is not None:
                out[q] = g
    return out


def estat_qoq() -> dict[str, float]:
    cache_file = CACHE / "seco_xcheck_estat_namq_10_gdp.json"
    if cache_file.exists():
        p = json.loads(cache_file.read_text())
    else:
        p = json.loads(get(ESTAT, 120))
        if "value" not in p or "dimension" not in p:
            raise RuntimeError("eurostat namq_10_gdp: unexpected payload")
        cache_file.write_text(json.dumps(p))
    idx = p["dimension"]["time"]["category"]["index"]
    return {t.replace("-", ""): p["value"][str(i)] for t, i in idx.items()
            if str(i) in p["value"]}


def fmt(v, nd):
    return "" if v is None else round(v, nd)


def main() -> None:
    print("SECO (real-time GDP database)")
    path, url = workbook()
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    cols = {name: vintages(wb, name) for name in SHEETS}
    latest = {name: cols[name][-1] for name in SHEETS}
    lab, rel = latest["gdp_cssa"]["label"], latest["gdp_cssa"]["release"]
    if latest["gdp"]["label"] != lab:
        raise SystemExit(f"  !! gdp and gdp_cssa latest vintages differ: "
                         f"{latest['gdp']['label']} vs {lab}")
    print(f"  .. gdp_cssa {len(cols['gdp_cssa'])} vintages from "
          f"{cols['gdp_cssa'][0]['label']}, gdp {len(cols['gdp'])} from "
          f"{cols['gdp'][0]['label']}; latest {lab} released {rel}, "
          f"data to {max(latest['gdp_cssa']['data'])}")
    if rel is None or (dt.date.today() - rel).days > MAX_STALE_DAYS:
        raise SystemExit(f"  !! latest vintage released {rel}: stale file?")
    cssa, raw = latest["gdp_cssa"]["data"], latest["gdp"]["data"]
    for q, want in SPOT_QOQ.items():
        got = qoq(cssa, q)
        if got is None or round(got, 1) != want:
            raise SystemExit(f"  !! gdp_cssa q/q {q} = {got}, expected {want}")
        print(f"  ok gdp_cssa q/q {q}: {got:.2f} (expected {want})")
    # Sport events: the two GDPs must differ, most in event years.
    diffs = {q: raw[q] - cssa[q] for q in cssa if q in raw}
    if max(abs(v) for v in diffs.values()) < 100:
        raise SystemExit("  !! gdp and gdp_cssa are identical: sheet mix-up?")
    # Second publisher: Eurostat namq_10_gdp (SCA, NOT event-adjusted).
    es = estat_qoq()
    common = [q for q in raw if q >= f"{Y0}Q1" and q in es and qoq(raw, q) is not None]
    gaps = [abs(qoq(raw, q) - es[q]) for q in common]
    mean_gap = statistics.fmean(gaps)
    if mean_gap > 0.3 or max(gaps) > 1.5:
        raise SystemExit(f"  !! SECO gdp vs Eurostat q/q: mean gap {mean_gap:.2f}, "
                         f"max {max(gaps):.2f}")
    print(f"  ok SECO gdp q/q vs Eurostat namq_10_gdp: mean gap {mean_gap:.2f} pt, "
          f"max {max(gaps):.2f} over {len(common)} quarters (vintages differ)")

    first = {name: first_release_qoq(cols[name]) for name in SHEETS}
    quarters = sorted(q for q in cssa if q >= f"{Y0}Q1")
    out = [[q, fmt(cssa.get(q), 1), fmt(qoq(cssa, q), 2),
            fmt(first["gdp_cssa"].get(q), 2), fmt(raw.get(q), 1),
            fmt(qoq(raw, q), 2), fmt(first["gdp"].get(q), 2)] for q in quarters]
    rel_path = "macro/gdp_quarterly_from_seco.csv"
    p = DATA / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    comment = f"""
SECO quarterly GDP, real-time database ({url}).
Vintage {lab}, released {rel}: real GDP, CHF MILLIONS, chained at
previous-year prices, seasonally and calendar adjusted; quarters labelled
YYYYQn. This file lags SECO's newest release by about a quarter.
TWO GDPs, NEVER ONE LINE: gdp_cssa_* = ALSO adjusted for major international
sporting events (FIFA/IOC/UEFA licence revenue booked in Switzerland), SECO's
headline; gdp_* = not event-adjusted (comparable with Eurostat namq_10_gdp
SCA). *_qoq = % change on the previous quarter in this vintage;
*_qoq_first = the same as FIRST published (first vintage carrying the
quarter), kept to show revisions; the event-adjusted sheet starts with
vintage {cols['gdp_cssa'][0]['label']}, so gdp_cssa_qoq_first is blank before that vintage's
newest quarter. Blank = not published.
"""
    with p.open("w", newline="", encoding="utf-8") as fh:
        for line in comment.strip().splitlines():
            fh.write(f"# {line}".rstrip() + "\n")
        w = csv.writer(fh)
        w.writerow(["quarter", "gdp_cssa", "gdp_cssa_qoq", "gdp_cssa_qoq_first",
                    "gdp", "gdp_qoq", "gdp_qoq_first"])
        w.writerows(out)
    print(f"  data/{rel_path}  {len(out)} rows ({out[0][0]}–{out[-1][0]})")


if __name__ == "__main__":
    main()
