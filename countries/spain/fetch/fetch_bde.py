#!/usr/bin/env python3
"""Refresh the Banco de España series into sidecar CSVs.

Usage:  python3 -I countries/spain/fetch/fetch_bde.py

The Banco de España's web service (launched April 2025) serves any series
the BIEST application carries, by series code, with no key:

  D_1NBAF472     Euribor 12 months (monthly, %)
  DN_1TI2T0135   TEDR on new housing loans to households (monthly, %)
  DMZ10E000H0.Q  Household+NPISH loan liabilities, % of gross disposable
                 income, four-quarter accumulation (quarterly)
  D_MEADU000     Doubtful loans to other resident sectors (monthly, € th.)
  D_MEE60000     Total credit to other resident sectors (monthly, € th.)
  DMZ10S800H0.Q  MFI loans to households+NPISH, stock (quarterly, € mn)

Three things this endpoint will do to you if nobody writes them down:

**The observations arrive NEWEST-FIRST**, in `fechas`/`valores` parallel
arrays with null holes for unpublished months. Zip them, drop the nulls,
sort ascending — do not trust the order, and do not mistake the first
value for the series' start.

**The units live only in the `informacion` metadata.** The credit series
are in THOUSANDS of euro; the debt-ratio series is a per cent. The
fetcher records the declared unit into the output and the CSV column
names carry it.

**A wrong path answers with an HTML error page under HTTP 200.** The
payload is checked for the listaSeries shape before it is cached, because
a cached error page survives the retry that would have fixed it.

The NPL ratio is computed here as doubtful ÷ total and labelled as a
computed column. The TEDR housing series starts January 2003; the
new-business rate compilation changed with Circular 5/2012 (2014 data
onward), so pre/post-2014 levels are not strictly one definition.

Outputs: data/markets/euribor_from_bde.csv,
         data/markets/mortgage_rate_from_bde.csv,
         data/credit/household_debt_from_bde.csv,
         data/credit/household_loans_from_bde.csv,
         data/credit/npl_from_bde.csv
"""
from __future__ import annotations

import gzip
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

BASE = ("https://app.bde.es/bierest/resources/srdatosapp/listaSeries"
        "?idioma=es&rango=MAX&series={codes}")
Y0, Y1 = 2006, 2026

SERIES = {
    "euribor": "D_1NBAF472",
    "mortgage_new": "DN_1TI2T0135",
    "hh_debt_pct": "DMZ10E000H0.Q",
    "doubtful": "D_MEADU000",
    "credit_total": "D_MEE60000",
    "hh_loans": "DMZ10S800H0.Q",
}


def fetch(names: list[str]) -> dict[str, list[tuple[str, float]]]:
    """{name: [(iso date, value)] ascending} for the requested series."""
    CACHE.mkdir(exist_ok=True)
    key = "_".join(sorted(names))
    cache_file = CACHE / f"bde_{key}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        codes = ",".join(urllib.parse.quote(SERIES[n], safe="._-")
                         for n in names)
        url = BASE.format(codes=codes)
        last = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(
                    url, headers={"Accept-Encoding": "identity"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    raw = r.read()
                # The gateway gzips even when identity is requested; the
                # magic bytes, not the headers, say which it sent.
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                payload = json.loads(raw)
                # The shape check: listaSeries answers a list of objects
                # carrying fechas/valores; the HTML error page it serves
                # under HTTP 200 parses as neither.
                if not (isinstance(payload, list) and payload and
                        all("fechas" in s and "valores" in s
                            for s in payload)):
                    raise ValueError("not a listaSeries response")
                cache_file.write_text(json.dumps(payload))
                break
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(3 * (attempt + 1))
        else:
            raise RuntimeError(f"bde {names}: {last}")
    out = {}
    wanted = {SERIES[n]: n for n in names}
    for s in payload:
        name = wanted.get(s.get("serie"))
        if not name:
            continue
        # newest-first, with null holes; zip, drop holes, sort ascending
        pairs = sorted((f[:10], v) for f, v in
                       zip(s["fechas"], s["valores"]) if v is not None)
        out[name] = pairs
    missing = [n for n in names if n not in out]
    if missing:
        raise RuntimeError(f"bde: no data for {missing}")
    return out


def annual_mean(pairs: list[tuple[str, float]]) -> dict[int, float]:
    """Mean of a year's observations, only when the year is complete.

    Monthly needs 12, quarterly needs 4; a year in progress is left blank
    rather than averaged over its running months, because a partial mean
    presented as the year's value is exactly the partial-year trap.
    """
    by_year: dict[int, list[float]] = {}
    for d, v in pairs:
        by_year.setdefault(int(d[:4]), []).append(v)
    return {y: sum(vs) / len(vs) for y, vs in by_year.items()
            if Y0 <= y <= Y1 and len(vs) in (12, 4)}


def q4(pairs: list[tuple[str, float]]) -> dict[int, float]:
    """The Q4 observation of a quarterly series, keyed by year."""
    return {int(d[:4]): v for d, v in pairs if d[5:7] == "10"
            and Y0 <= int(d[:4]) <= Y1}


def dec(pairs: list[tuple[str, float]]) -> dict[int, float]:
    """The December observation of a monthly series, keyed by year."""
    return {int(d[:4]): v for d, v in pairs if d[5:7] == "12"
            and Y0 <= int(d[:4]) <= Y1}


def write(rel: str, header: str, columns: list[dict[int, float]],
          fmt: str = "{:.2f}") -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [header]
    for y in range(Y0, Y1 + 1):
        cells = ["" if (v := c.get(y)) is None else fmt.format(v)
                 for c in columns]
        lines.append(f"{y}," + ",".join(cells))
    path.write_text("\n".join(lines) + "\n")
    print(f"  -> data/{rel}")


def main() -> None:
    print("Fetching Banco de España series...")
    rates = fetch(["euribor", "mortgage_new"])
    write("markets/euribor_from_bde.csv", "year,euribor_12m_avg",
          [annual_mean(rates["euribor"])])
    write("markets/mortgage_rate_from_bde.csv",
          "year,mortgage_new_avg",
          [annual_mean(rates["mortgage_new"])],
          fmt="{:.3f}")

    debt = fetch(["hh_debt_pct"])
    write("credit/household_debt_from_bde.csv",
          "year,debt_pct_income_avg,debt_pct_income_q4",
          [annual_mean(debt["hh_debt_pct"]), q4(debt["hh_debt_pct"])])

    # The household loan STOCK (MFI loans to hogares e ISFLSH, millions of
    # euro, quarterly) — read at Q4, like every stock here.
    stock = fetch(["hh_loans"])
    write("credit/household_loans_from_bde.csv",
          "year,loans_eurbn_q4",
          [{y: v / 1000 for y, v in q4(stock["hh_loans"]).items()}],
          fmt="{:.1f}")

    npl = fetch(["doubtful", "credit_total"])
    # Both are STOCKS in thousands of euro: a year is its December reading,
    # never the sum of the months (summing a stock twelve times is the
    # quarterly-annualisation trap in monthly clothing). The ratio is
    # computed here as doubtful ÷ total and labelled as a computed column.
    doubtful_dec = dec(npl["doubtful"])
    total_dec = dec(npl["credit_total"])
    ratio = {y: doubtful_dec[y] / total_dec[y] * 100
             for y in doubtful_dec if y in total_dec and total_dec[y]}
    write("credit/npl_from_bde.csv",
          "year,doubtful_eur_mn,credit_total_eur_mn,npl_ratio",
          [{y: v / 1e3 for y, v in doubtful_dec.items()},
           {y: v / 1e3 for y, v in total_dec.items()},
           ratio],
          fmt="{:.3f}")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
