#!/usr/bin/env python3
"""Refresh Taiwan MOI household-register and NIA ARC review sidecars."""
from __future__ import annotations

import csv
import json
import ssl
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "migration"
CACHE = ROOT / "cache" / "migration"
BASE = "https://www.ris.gov.tw/rs-opendata/api/v1/datastore"
UA = {"User-Agent": "Mozilla/5.0 (compatible; worldreports-source-refresh/1.0)",
      "Accept": "application/json"}


def get_json(dataset: str, roc_month: str, page: int) -> dict:
    path = CACHE / dataset / f"{roc_month}-{page}.json"
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        url = f"{BASE}/{dataset}/{roc_month}?page={page}"
        req = urllib.request.Request(url, headers=UA)
        last = None
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=90,
                                            context=ssl.create_default_context()) as response:
                    body = response.read()
                    ctype = response.headers.get_content_type()
                break
            except OSError as exc:
                last = exc
                time.sleep(1 + attempt * 2)
        else:
            raise RuntimeError(f"{url}: failed after retries: {last}")
        if ctype not in ("application/json", "text/json"):
            raise RuntimeError(f"{url}: expected JSON, got {ctype}")
        payload = json.loads(body)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{dataset}/{roc_month}/{page}: payload is not an object")
    return payload


def records(payload: dict) -> tuple[list[dict], int]:
    """Normalize RIS's documented response wrapper without guessing data."""
    candidates = [payload]
    for value in payload.values():
        if isinstance(value, dict):
            candidates.append(value)
    for obj in candidates:
        rows = next((v for k, v in obj.items()
                     if k.lower() in {"rowdata", "data", "records", "responsedata"}
                     and isinstance(v, list)), None)
        if rows is None:
            continue
        pages = next((int(v) for k, v in obj.items()
                      if k.lower() in {"totalpage", "totalpages", "pagecount"}), 1)
        if rows and not all(isinstance(row, dict) for row in rows):
            raise RuntimeError("RIS rows are not JSON objects")
        return rows, pages
    raise RuntimeError(f"unrecognized RIS response keys: {sorted(payload)}")


def numeric(row: dict, stem: str) -> int:
    # API releases have used both snake_case and condensed field names.
    normalized = {k.lower().replace("_", ""): v for k, v in row.items()}
    key = stem.lower().replace("_", "")
    zh = {
        "inforeignm": "遷入人數自國外男", "inforeignf": "遷入人數自國外女",
        "firstregm": "遷入人數初設戶籍男", "firstregf": "遷入人數初設戶籍女",
        "outforeignm": "遷出人數往國外男", "outforeignf": "遷出人數往國外女",
    }
    if key not in normalized and key in zh:
        key = zh[key]
    if key not in normalized:
        raise RuntimeError(f"RIS field {stem!r} absent; keys={sorted(row)}")
    raw = str(normalized[key]).strip().replace(",", "")
    return int(raw or 0)


def month_rows(dataset: str, roc_month: str) -> list[dict]:
    first = get_json(dataset, roc_month, 1)
    rows, pages = records(first)
    if not (1 <= pages <= 20):
        raise RuntimeError(f"{dataset}/{roc_month}: implausible {pages} pages")
    for page in range(2, pages + 1):
        more, confirmed = records(get_json(dataset, roc_month, page))
        if confirmed != pages:
            raise RuntimeError(f"{dataset}/{roc_month}: pagination changed mid-download")
        rows.extend(more)
    if len(rows) < 7000:
        raise RuntimeError(f"{dataset}/{roc_month}: only {len(rows)} village/sex rows")
    return rows


def write(name: str, header: list[str], rows: list[list[object]]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / name).open("w", encoding="utf-8", newline="") as fh:
        out = csv.writer(fh, lineterminator="\n")
        out.writerow(header)
        out.writerows(rows)


def collect() -> None:
    def one_month(item):
        year, month = item
        roc_month = f"{year - 1911:03d}{month:02d}"
        rows = month_rows("ODRP011", roc_month)
        incoming = sum(numeric(r, "in_foreign_m") + numeric(r, "in_foreign_f")
                       + numeric(r, "first_reg_m") + numeric(r, "first_reg_f")
                       for r in rows)
        outgoing = sum(numeric(r, "out_foreign_m") + numeric(r, "out_foreign_f")
                       for r in rows)
        return year, incoming, outgoing

    totals = {year: [0, 0] for year in range(2018, 2026)}
    work = [(year, month) for year in totals for month in range(1, 13)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for year, incoming, outgoing in pool.map(one_month, work):
            totals[year][0] += incoming
            totals[year][1] += outgoing
    flows = [[year, incoming, outgoing, incoming - outgoing]
             for year, (incoming, outgoing) in totals.items()]

    check = {r[0]: r for r in flows}
    for year, net in {2018: 9309, 2019: 13124, 2020: -33645,
                      2021: -155696, 2022: -42140, 2023: 225980,
                      2024: 47613}.items():
        assert check[year][3] == net, (year, check[year][3], net)
    write("registration_flows_from_ris.csv",
          ["year", "registered_immigration", "registered_emigration", "registered_net"], flows)


if __name__ == "__main__":
    collect()
    print("wrote official RIS review sidecars")
