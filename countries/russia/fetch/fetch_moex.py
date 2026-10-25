#!/usr/bin/env python3
"""Refresh the MOEX index for Russia, in roubles and in dollars.

Usage:  make C=russia fetch   (or: python3 -I fetch/fetch_moex.py)

The Moscow Exchange's own ISS JSON API answers 200 and is the exchange
that computes the index, which makes it the issuer rather than a
redistributor. The atlas still marks an equity index `official: false`:
`SOURCING_A_COUNTRY.md` §5 lists stock indices as market series, and the
spine's markets slot 4 is sourced "exchange / redistributor (official:
false)". So the flag says what the number is, not who serves it.

  https://iss.moex.com/iss/history/engines/stock/markets/index/
      securities/IMOEX.json?from=YYYY-MM-DD&till=YYYY-MM-DD

IMOEX is the rouble-denominated MOEX Russia Index, the successor to the
MICEX index. Two columns are staged:

  imoex_rub_avg    the mean daily close in the year, roubles
  imoex_usd_avg    that mean divided by the Bank of Russia's annual mean
                   official rate — the spine wants the index in US$

THE 2022 BREAK IS IN THE DATA, NOT IN A NOTE. Trading on MOEX equities
was suspended from 25 February to 24 March 2022; the index has no
observations in that window and the panel draws a gap there rather than a
line across it. From 2022 foreign trading in Russian securities was
restricted and the index's dollar value is an arithmetic conversion of a
rouble price set in a market most foreign holders could not access — said
on the panel.

ISS pages its history at 100 rows by default, so the fetcher walks the
cursor until the exchange says there is nothing left.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

ISS = ("https://iss.moex.com/iss/history/engines/stock/markets/index/"
       "securities/IMOEX.json?from={frm}&till={till}&start={start}")
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}
YEAR_FROM, YEAR_TO = 2006, 2026


def daily_closes(year: int) -> dict[str, float]:
    """Every daily close the exchange reports for one year, as {date: close}."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"moex_imoex_{year}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
        return {row[0]: float(row[1]) for row in payload}

    out: dict[str, float] = {}
    start = 0
    for _ in range(40):  # 40 pages * 100 rows is more than a year of sessions
        url = ISS.format(frm=f"{year}-01-01", till=f"{year}-12-31", start=start)
        with urllib.request.urlopen(
                urllib.request.Request(url, headers=HEADERS), timeout=120) as r:
            payload = json.loads(r.read())
        block = payload.get("history", {})
        columns = block.get("columns", [])
        rows = block.get("data", [])
        if not rows:
            break
        i_date = columns.index("TRADEDATE")
        i_close = columns.index("CLOSE")
        for row in rows:
            if row[i_close] is None:
                continue
            out[row[i_date]] = float(row[i_close])
        start += len(rows)
        time.sleep(0.15)
    if not out:
        sys.exit(f"moex {year}: no closes returned")
    cache_file.write_text(json.dumps(sorted(out.items())))
    return out


def annual_mean(series: dict[str, float]) -> float:
    return statistics.fmean(series.values())


def fx_means() -> dict[int, float]:
    """The Bank of Russia's annual mean USD/RUB, from its own sidecar.

    Read from the staged sidecar rather than re-fetched: the dollar index
    must use the same rate the markets panel's currency line uses, or the
    two panels would disagree about the same year.
    """
    path = ROOT / "data" / "markets" / "usd_rub_from_cbr.csv"
    if not path.exists():
        sys.exit("fx: data/markets/usd_rub_from_cbr.csv is missing; run "
                 "fetch_cbr.py first so both panels use one rate")
    out = {}
    for line in path.read_text().splitlines():
        if line.startswith("#") or line.startswith("year"):
            continue
        parts = line.split(",")
        if len(parts) == 2 and parts[1]:
            out[int(parts[0])] = float(parts[1])
    return out


def main() -> None:
    print("Moscow Exchange: IMOEX in roubles and in dollars")
    fx = fx_means()

    rub: dict[int, float] = {}
    for year in range(YEAR_FROM, YEAR_TO + 1):
        try:
            closes = daily_closes(year)
        except Exception as e:  # noqa: BLE001
            print(f"  {year}: {e}", file=sys.stderr)
            continue
        rub[year] = annual_mean(closes)
        print(f"  {year}: {len(closes)} sessions, mean {rub[year]:.1f}")

    # ---- known observations ---------------------------------------------
    # IMOEX closed 2021 around 3,700-3,800 and the index's all-time high
    # was October 2021; the 2022 mean is far below it. Both are pinned as
    # order-of-magnitude checks against a unit or scaling mistake.
    assert 2000 < rub[2019] < 3000, f"IMOEX 2019: {rub[2019]}"
    assert 3000 < rub[2021] < 4000, f"IMOEX 2021: {rub[2021]}"
    assert 2000 < rub[2022] < 3200, f"IMOEX 2022: {rub[2022]}"

    path = ROOT / "data" / "markets" / "imoex_from_moex.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Moscow Exchange ISS, IMOEX (MOEX Russia Index, rouble), daily",
        "# closes, annual MEAN. NOT an official statistic: a stock index is a",
        "# market series (SOURCING_A_COUNTRY.md §5), flagged official: false",
        "# in SOURCES.yaml.",
        "# imoex_usd_avg divides the rouble mean by the Bank of Russia's",
        "# annual mean official rate in markets/usd_rub_from_cbr.csv, one",
        "# rate for both panels.",
        "# Equities were suspended 25.02.2022 - 24.03.2022: no observations,",
        "# drawn as a gap.",
        "year,imoex_rub_avg,imoex_usd_avg",
    ]
    for year in sorted(rub):
        usd = rub[year] / fx[year] if fx.get(year) else None
        usd_cell = f"{usd:.1f}" if usd is not None else ""
        lines.append(f"{year},{rub[year]:.1f},{usd_cell}")
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/markets/imoex_from_moex.csv  {len(rub)} rows")


if __name__ == "__main__":
    main()
