#!/usr/bin/env python3
"""Refresh Poland's exchange rates from the National Bank of Poland.

Usage:  make C=poland fetch   (or: python3 -I fetch/fetch_nbp.py)

NBP publishes a documented, keyless Web API for the official mid-rates
(Table A) and the gold price. This fetcher reads Table A for the US dollar
and the euro over the country's window, one calendar year per request —
NBP caps a single query at 367 days — and writes the ANNUAL MEAN of the
daily mid-rates.

Why the mean and not the year-end rate: the atlas converts local-currency
flows (the minimum wage) at an annual average and indexes the currency on
annual averages, so every country's line is the same statistic. NBP's
year-end rate is also staged, from GUS's money table, and the two are
different numbers on purpose.

The API's own rule: a range with no quotations answers 404, which is a
hole in the publisher's coverage, not an error to retry around.

Output: markets/usd_pln_from_nbp.csv (review sidecar only).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DATA, FetchError, assert_close,  # noqa: E402
                    json_get, write_csv)

Y0, Y1 = 2006, 2026
BASE = "https://api.nbp.pl/api/exchangerates/rates/a/{code}/{start}/{end}/"
#: The last working day NBP has published. A range ending in the future is
#: clamped by the API itself; the constant only documents the probe date.
PROBE = "2026-10-24"


def yearly_mean(code: str) -> dict[int, float]:
    """{year: mean of the daily mid-rate} for one currency, per NBP."""
    out = {}
    for year in range(Y0, Y1 + 1):
        # NBP answers 400 to a range that reaches past the last published
        # working day, so the current year is clamped to the probe date.
        start = f"{year}-01-01"
        end = min(f"{year}-12-31", PROBE)
        url = BASE.format(code=code, start=start, end=end)
        try:
            payload = json_get(url, timeout=90)
        except FetchError as e:
            if "HTTP 404" in str(e):
                continue          # NBP has no quotations for that year
            raise
        rates = payload.get("rates") or []
        if not rates:
            continue
        # NBP quotes every currency per `unit` units (100 for JPY, 1 for USD).
        per_unit = [r["mid"] / r.get("unit", 1) for r in rates]
        out[year] = sum(per_unit) / len(per_unit)
        print(f"  {code} {year}: {len(rates)} quotations, mean {out[year]:.4f}")
    if not out:
        raise FetchError(f"nbp {code}: no quotations in {Y0}-{Y1}")
    return out


def main() -> None:
    print("Fetching NBP official mid-rates for Poland...")
    usd = yearly_mean("usd")
    eur = yearly_mean("eur")
    # Known values: the zloty averaged 3.98/US$ in 2024 and 4.30/EUR, and
    # 2.48/US$ in the 2008 pre-crisis year.
    assert_close(usd.get(2024), 3.98, 0.08, "NBP USD/PLN 2024 mean")
    assert_close(usd.get(2008), 2.37, 0.10, "NBP USD/PLN 2008 mean")
    assert_close(eur.get(2024), 4.31, 0.08, "NBP EUR/PLN 2024 mean")

    header = ["year", "usd_pln_mean", "eur_pln_mean"]
    rows = [[y, round(usd[y], 4) if y in usd else None,
             round(eur[y], 4) if y in eur else None]
            for y in range(Y0, Y1 + 1)]
    path = write_csv("markets/usd_pln_from_nbp.csv", header, rows, comment=f"""
NBP Web API, Table A (official mid-rates), annual mean of the daily
quotations. Probed {PROBE}. usd_pln_mean is PLN per 1 US$; a higher number
is a weaker zloty, so the markets plate indexes it 2006 = 100 with up =
stronger (ctx.fx_index) and the line falls as the currency weakens.
NOT the year-end rate: markets_from_gus.csv carries NBP's 31 December
mid-rate from GUS's money table, and the two differ.
""")
    print(f"  -> {path.relative_to(DATA)}")
    print("Done. Diff the *_from_nbp.csv sidecar before adopting.")


if __name__ == "__main__":
    main()
