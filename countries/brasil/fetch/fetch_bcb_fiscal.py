#!/usr/bin/env python3
"""The consolidated public sector's borrowing requirement, from BCB/SGS.

Usage:  python3 -I countries/brasil/fetch/fetch_bcb_fiscal.py

Output (a sidecar — diff it into fiscal/nfsp.csv by hand):
  data/fiscal/nfsp_from_bcb.csv   year,nfsp_nominal,nfsp_primary,interest

NFSP ("necessidades de financiamento do setor público") is the BCB's
"below the line" fiscal result: it is read off the change in the public
sector's net debt, not off the budget. It is the measure the Brazilian
argument about interest is conducted in — "juros nominais" at 6-8% of GDP.
The perimeter is the consolidated public sector: the central government,
the states and municipalities, and the state-owned firms outside
Petrobras and Eletrobras. That is neither the IMF's general government nor
the Tesouro's central government, so it is drawn as its own labelled line.

Series (12-month flow, % of GDP, "sem desvalorização cambial"), each
resolved by code in the BCB open-data catalogue (codigo_sgs), not guessed:
  5727  Resultado nominal - Total - Setor público consolidado
  5793  Resultado primário - Total - Setor público consolidado
  5760  Juros nominais - Total - Setor público consolidado
The December value of a 12-month flow is the calendar year. A positive NFSP
is a DEFICIT (a need for financing); the columns keep the BCB's sign and
the plate flips it. The running year's latest value is a twelve-month
window ending mid-year, not a calendar year, so it is not written.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
URL = ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
       "?formato=json&dataInicial=01/12/2005&dataFinal=31/12/2025")
SERIES = {"nfsp_nominal": 5727, "nfsp_primary": 5793, "interest": 5760}
YEARS = range(2006, 2026)

# Pinned on 2026-10-22: the widely reported headline figures for those
# years (2015: interest 8.37%, nominal deficit 10.22%; 2023: primary
# deficit about 2.3%), which the API reproduced that day. A miss means the
# BCB revised the history or the code moved; look before accepting it.
SPOT = [("interest", 2015, 8.37), ("nfsp_nominal", 2015, 10.22),
        ("nfsp_primary", 2023, 2.29)]


def fetch(code: int) -> dict[int, float]:
    req = urllib.request.Request(URL.format(code=code),
                                 headers={"Accept": "application/json",
                                          "User-Agent": "worldreports/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        rows = json.load(r)
    if not isinstance(rows, list):
        raise SystemExit(f"SGS {code}: not a list: {rows!r:.200}")
    out = {}
    for row in rows:
        d, m, y = (int(x) for x in row["data"].split("/"))
        if m == 12:
            out[y] = float(row["valor"])
    return out


def main() -> None:
    cols = {name: fetch(code) for name, code in SERIES.items()}
    for name, year, want in SPOT:
        got = cols[name].get(year)
        if got is None or abs(got - want) > 0.06:
            raise SystemExit(f"{name} {year}: got {got}, expected {want}; "
                             "nothing written")
    # nominal = primary + interest, by construction of the NFSP
    for y in YEARS:
        gap = cols["nfsp_nominal"][y] - cols["nfsp_primary"][y] \
            - cols["interest"][y]
        if abs(gap) > 0.02:
            raise SystemExit(f"{y}: nominal is not primary + interest "
                             f"({gap:+.3f}); nothing written")
    lines = ["year," + ",".join(SERIES)]
    for y in YEARS:
        lines.append(f"{y}," + ",".join(f"{cols[c][y]:.2f}" for c in SERIES))
    out = DATA / "fiscal" / "nfsp_from_bcb.csv"
    out.write_text("\n".join(lines) + "\n")
    print(f"  -> {out.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
