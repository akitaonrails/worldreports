#!/usr/bin/env python3
"""General-government spending by function (COFOG), from the Tesouro.

Usage:  python3 -P countries/brasil/fetch/fetch_cofog.py

Output (a sidecar — diff it into fiscal/cofog.csv by hand):
  data/fiscal/cofog_from_tesouro.csv
      year, social_protection, health, education, general_public,
      economic_affairs, defence_order, other, total     (% of GDP)

Brazil does not report COFOG to the OECD, but the Tesouro, the SOF and
IBGE compile it themselves for the whole general government (central,
state and municipal) on the IMF's GFSM 2014 rules, 2010 onward. Table
1.5.a of the spreadsheet is "Despesa por função de governo - Governo
Geral - Brasil - Anual - % PIB", with the ten COFOG divisions as rows
701-710. They map onto the spine's seven groups with no judgement call:

  social_protection  710           health    707       education 709
  general_public     701 (incl. 7017, public-debt transactions = interest)
  economic_affairs   704           defence_order  702 + 703
  other              705 + 706 + 708

The spreadsheet is the 2023 edition (2010-2023). The 2024 edition was
published as a report whose spreadsheet was not reachable here; its
Table 1 gives 2023 and 2024 by division, and fiscal/cofog.csv carries the
2024 row transcribed from it by hand. This fetcher cross-checks the two
editions on the year they share: the 2023 edition's 2023 column must
match the 2024 report's 2023 column to within 0.02 points of GDP, or
nothing is written.

The host tesourotransparente.gov.br rate-limits hard (HTTP 429 for hours
after a burst); the files themselves are served from cdn.tesouro.gov.br,
which is what this reads.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "cofog"
DATA = ROOT / "data"
URL = ("https://cdn.tesouro.gov.br/sistemas-internos/apex/producao/sistemas/"
       "thot/arquivos/publicacoes/51473_1617293/anexos/24705_1617712/"
       "COFOG%20GG.xlsx")
SHEET = "1.5.a"

GROUPS = {
    "social_protection": (710,), "health": (707,), "education": (709,),
    "general_public": (701,), "economic_affairs": (704,),
    "defence_order": (702, 703), "other": (705, 706, 708),
}

# "Relatório COFOG GG 2024", Tabela 1, the 2023 column, % do PIB.
REPORT_2023 = {701: 11.35, 702: 0.51, 703: 2.85, 704: 2.21, 705: 0.50,
               706: 1.15, 707: 4.72, 708: 0.34, 709: 4.93, 710: 16.75}
REPORT_2023_TOTAL = 45.31


def workbook() -> openpyxl.Workbook:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "COFOG_GG_2023.xlsx"
    if not path.exists():
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=180) as r:
            body = r.read()
        if not body.startswith(b"PK"):
            raise SystemExit(f"not an .xlsx ({body[:60]!r}); nothing written")
        path.write_bytes(body)
    return openpyxl.load_workbook(path, read_only=True, data_only=True)


def divisions() -> tuple[list[int], dict[int, dict[int, float]]]:
    """(years, {division code: {year: % of GDP}}), code 7 being the total."""
    ws = workbook()[SHEET]
    rows = list(ws.iter_rows(values_only=True))
    head = next(r for r in rows if r and r[0] and str(r[0]).startswith("Governo Geral"))
    years = [int(v) for v in head[2:] if isinstance(v, (int, float))]
    out = {}
    for r in rows:
        if isinstance(r[0], int) and (r[0] == 7 or 701 <= r[0] <= 710):
            # the sheet stores fractions of GDP: 0.131 is 13.1%
            out[r[0]] = {y: float(v) * 100 for y, v in zip(years, r[2:])
                         if isinstance(v, (int, float))}
    missing = sorted({7, *range(701, 711)} - set(out))
    if missing:
        raise SystemExit(f"{SHEET}: no rows for {missing}; nothing written")
    return years, out


def main() -> None:
    years, div = divisions()
    for code, want in REPORT_2023.items():
        got = div[code][2023]
        if abs(got - want) > 0.02:
            raise SystemExit(f"2023 edition {code}: {got:.2f}, 2024 report "
                             f"{want:.2f}; nothing written")
    if abs(div[7][2023] - REPORT_2023_TOTAL) > 0.02:
        raise SystemExit(f"2023 total {div[7][2023]:.2f} vs report "
                         f"{REPORT_2023_TOTAL}; nothing written")
    lines = ["year," + ",".join(GROUPS) + ",total"]
    for y in years:
        vals = [sum(div[c][y] for c in codes) for codes in GROUPS.values()]
        # the ten divisions must add up to the published total
        if abs(sum(vals) - div[7][y]) > 0.02:
            raise SystemExit(f"{y}: divisions sum to {sum(vals):.2f}, total "
                             f"is {div[7][y]:.2f}; nothing written")
        lines.append(f"{y}," + ",".join(f"{v:.2f}" for v in vals)
                     + f",{div[7][y]:.2f}")
    out = DATA / "fiscal" / "cofog_from_tesouro.csv"
    out.write_text("\n".join(lines) + "\n")
    print(f"  -> {out.relative_to(ROOT)} ({years[0]}-{years[-1]})",
          file=sys.stderr)


if __name__ == "__main__":
    main()
