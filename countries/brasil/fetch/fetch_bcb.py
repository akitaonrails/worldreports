#!/usr/bin/env python3
"""Fetch official annual series from Banco Central do Brasil (SGS API).

The public SGS API is authoritative but slow and flaky with long date ranges:
we fetch year-by-year with a small thread pool, generous timeouts, retries,
and per-year caching under cache/ so re-runs only fetch what is missing.

Series used (all official BCB/SGS):
  1     USD/BRL (PTAX, livre - venda, end of period, daily)
  433   IPCA monthly variation (%)          -> compounded per year
  432   Selic accumulated in the year (%)   -> annual
  1178  Selic daily (% a.a.)                -> only latest level (one call)
  13637 International reserves (US$ mn, monthly)
  4513  Gross general government debt % GDP (quarterly)  [candidate id]
  6621  Net public sector debt % GDP (quarterly)         [candidate id]

Outputs (curated-style CSVs):
  data/macro/dollar.csv     year,avg,eop
  data/macro/ipca.csv       year,value
  data/macro/selic.csv      year,value (accumulated; 2026 = current level)
  data/macro/reserves.csv   year,eop_usbi
  data/fiscal/debt_bcb.csv  year,gross_pib,net_pib  (verify magnitudes!)
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
DATA = ROOT / "data"
CACHE.mkdir(exist_ok=True)

BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
HEADERS = {"Accept": "application/json"}

RESERVES = 3546  # reservas internacionais, conceito liquidez (monthly, US$ mn).
# 13637 (the daily "conceito caixa" series) is served as an HTML error page by
# the SGS gateway, so it is unusable; 3546 carries the same year-end level.
SERIES = [1, 433, 432, 4513, 13762, RESERVES]
YEAR_FROM, YEAR_TO = 2005, 2026


def fetch_year(code: int, year: int) -> list[dict] | None:
    cache_file = CACHE / f"sgs_{code}_{year}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    url = (f"{BASE.format(code=code)}?formato=json"
           f"&dataInicial=01/01/{year}&dataFinal=31/12/{year}")
    for attempt in range(5):
        try:
            r = requests.get(url, timeout=90, headers=HEADERS)
            if r.status_code != 200:
                raise ValueError(f"HTTP {r.status_code}")
            payload = r.json()
            if not isinstance(payload, list):
                raise ValueError(payload)
            cache_file.write_text(json.dumps(payload))
            return payload
        except Exception:  # noqa: BLE001
            time.sleep(2 * (attempt + 1))
    return None


def fetch_all() -> dict[int, list[dict]]:
    tasks = [(c, y) for c in SERIES for y in range(YEAR_FROM, YEAR_TO + 1)]
    out: dict[int, list[dict]] = {c: [] for c in SERIES}
    done = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(fetch_year, c, y): (c, y) for c, y in tasks}
        for fut in as_completed(futs):
            c, y = futs[fut]
            payload = fut.result()
            done += 1
            if payload is None:
                print(f"  [sgs {c}] {y}: SKIPPED", file=sys.stderr)
            else:
                out[c].extend(payload)
            if done % 20 == 0:
                print(f"  ... {done}/{len(tasks)} year-requests done")
    for c in SERIES:
        out[c].sort(key=lambda r: r["data"])
        print(f"  [sgs {c}] {len(out[c])} rows")
    return out


def parse_day(s: str) -> date:
    d, m, y = s.split("/")
    return date(int(y), int(m), int(d))


def by_year_daily(rows):
    out = {}
    for r in rows:
        d = parse_day(r["data"])
        out.setdefault(d.year, []).append((d, float(r["valor"])))
    # sort chronologically: upstream rows arrive ordered by the raw dd/mm/yyyy
    # string, which orders by day-of-month first, so vals[-1] is only the
    # year-end value by accident.
    for vals in out.values():
        vals.sort()
    return out


def main() -> None:
    print("Fetching BCB/SGS series (threaded, patient mode)...")
    data = fetch_all()

    # ---- USD/BRL (series 1) --------------------------------------------
    d = by_year_daily(data[1])
    lines = ["year,avg,eop"]
    # from YEAR_FROM, not 2006: the markets plate rebases to the first IBOV
    # year, which is 2005, and a missing base year there silently rescaled
    # the whole S&P-in-reais line by the raw exchange rate
    for y in range(YEAR_FROM, YEAR_TO + 1):
        vals = d.get(y, [])
        if not vals:
            lines.append(f"{y},,")
            continue
        last = vals[-1][1]  # series 1 is end-of-period daily
        avg = sum(v for _, v in vals) / len(vals)
        lines.append(f"{y},{avg:.4f},{last:.4f}")
    (DATA / "macro" / "dollar.csv").write_text("\n".join(lines) + "\n")
    print("  -> data/macro/dollar.csv")

    # ---- IPCA (series 433, monthly %; compound per calendar year) -------
    d = by_year_daily(data[433])
    lines = ["year,value"]
    for y in range(2006, YEAR_TO + 1):
        vals = [v for _, v in d.get(y, [])]
        if not vals:
            lines.append(f"{y},")
            continue
        acc = 1.0
        for v in vals:
            acc *= 1 + v / 100
        lines.append(f"{y},{(acc - 1) * 100:.2f}")
    (DATA / "macro" / "ipca.csv").write_text("\n".join(lines) + "\n")
    print("  -> data/macro/ipca.csv")

    # ---- Selic: 432 accumulated per year + current level from 1178 ------
    d432 = by_year_daily(data[432])
    current = None
    try:
        r = requests.get(BASE.format(code=1178) + "/ultimos/1?formato=json",
                         timeout=90, headers=HEADERS)
        if r.ok:
            current = (r.json()[0]["data"], float(r.json()[0]["valor"]))
    except Exception:  # noqa: BLE001
        pass
    lines = ["year,value"]
    for y in range(2006, YEAR_TO + 1):
        if y == YEAR_TO and current:
            lines.append(f"{y},{current[1]:.2f}")
            continue
        acc = d432.get(y, [])
        lines.append(f"{y},{acc[-1][1]:.2f}" if acc else f"{y},")
    (DATA / "macro" / "selic.csv").write_text("\n".join(lines) + "\n")
    print("  -> data/macro/selic.csv"
          + (f" (current: {current})" if current else ""))

    # ---- International reserves (3546, monthly US$ mn) -------------------
    d = by_year_daily(data[RESERVES])
    lines = ["year,eop_usbi"]
    for y in range(2006, YEAR_TO + 1):
        vals = d.get(y, [])
        lines.append(f"{y},{vals[-1][1] / 1000:.2f}" if vals else f"{y},")
    (DATA / "macro" / "reserves.csv").write_text("\n".join(lines) + "\n")
    print("  -> data/macro/reserves.csv")

    # ---- Debt (13762 gross DBGG / 4513 net DLSP, % GDP) --------------------
    lines = ["year,gross_pib,net_pib"]
    dg = by_year_daily(data[13762])
    dn = by_year_daily(data[4513])
    for y in range(2006, YEAR_TO + 1):
        g = dg.get(y, [])[-1][1] if dg.get(y) else ""
        n = dn.get(y, [])[-1][1] if dn.get(y) else ""
        lines.append(f"{y},{g},{n}")
    (DATA / "fiscal" / "debt_bcb.csv").write_text("\n".join(lines) + "\n")
    print("  -> data/fiscal/debt_bcb.csv (cross-check vs curated debt.csv)")

    print("Done.")


if __name__ == "__main__":
    main()
