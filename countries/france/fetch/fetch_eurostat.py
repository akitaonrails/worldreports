#!/usr/bin/env python3
"""Refresh the Eurostat-backed series for France into sidecar CSVs.

Usage:  python3 scripts/fetch_eurostat.py

Everything here is a series France reports to Eurostat under a statistical
obligation — the ESA 2010 national accounts, the EDP (Maastricht) fiscal
notification, COFOG expenditure, the LFS unemployment rate, the HICP — so
Eurostat is the authoritative publication channel rather than a convenience.

Output goes to `*_from_estat.csv` sidecars beside the curated CSVs, never over
them: a bad upstream day, or a vintage revision landing mid-week, must not
silently rewrite a committed number. Diff the sidecar and copy across what you
accept.

The one exception is `data/fiscal/debt.csv` and `deficit.csv`, which ARE the
Eurostat series with nothing added — there is no national series that is more
authoritative for the Maastricht aggregates — so those are written directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eurostat import annual  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

GEO = "FR"      # France including the overseas departments (FRM = metropolitan)
Y0, Y1 = 2006, 2026

# COFOG divisions, in the order plate 03 stacks them. GF01 carries debt
# interest, which is why it is not simply "administration".
COFOG = {
    "social_protection": "GF10",
    "health": "GF07",
    "general_services": "GF01",   # incl. interest on the debt
    "education": "GF09",
    "economic_affairs": "GF04",
    "defence_order": None,        # GF02 + GF03, summed below
    "other": None,                # GF05 + GF06 + GF08, summed below
}


def rows(years, columns: dict[str, dict[int, float]], dec: int = 2) -> str:
    """A wide CSV: one row per year, blanks where the source has no value."""
    head = "year," + ",".join(columns)
    lines = [head]
    for y in years:
        cells = []
        for series in columns.values():
            v = series.get(y)
            cells.append("" if v is None else f"{v:.{dec}f}")
        lines.append(f"{y}," + ",".join(cells))
    return "\n".join(lines) + "\n"


def write(rel: str, text: str) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    print(f"  -> data/{rel}")


def main() -> None:
    years = list(range(Y0, Y1 + 1))
    print("Fetching Eurostat series for France...")

    # ---- national accounts -------------------------------------------
    nominal = annual("nama_10_gdp", geo=GEO, na_item="B1GQ",
                     unit="CP_MEUR", freq="A")
    growth = annual("nama_10_gdp", geo=GEO, na_item="B1GQ",
                    unit="CLV_PCH_PRE", freq="A")
    gfcf = annual("nama_10_gdp", geo=GEO, na_item="P51G",
                  unit="CP_MEUR", freq="A")
    # Eurostat publishes GDP in millions; the plates read billions of euro.
    nominal_bn = {y: v / 1000 for y, v in nominal.items()}
    write("macro/gdp_from_estat.csv",
          rows(years, {"nominal_eurbn": nominal_bn, "real_growth": growth},
               dec=2))

    # ---- EDP / Maastricht: the authoritative fiscal aggregates --------
    deficit = annual("gov_10dd_edpt1", geo=GEO, na_item="B9",
                     unit="PC_GDP", sector="S13", freq="A")
    debt = annual("gov_10dd_edpt1", geo=GEO, na_item="GD",
                  unit="PC_GDP", sector="S13", freq="A")
    interest = annual("gov_10a_main", geo=GEO, na_item="D41PAY",
                      unit="PC_GDP", sector="S13", freq="A")
    revenue = annual("gov_10a_main", geo=GEO, na_item="TR",
                     unit="PC_GDP", sector="S13", freq="A")
    expenditure = annual("gov_10a_main", geo=GEO, na_item="TE",
                         unit="PC_GDP", sector="S13", freq="A")
    gov_gfcf = annual("gov_10a_main", geo=GEO, na_item="P51G",
                      unit="PC_GDP", sector="S13", freq="A")
    # The primary balance is the headline deficit with interest added back:
    # it is what the budget would be if the debt were free, and it is the
    # number that says whether today's policy is adding to the stock.
    primary = {y: deficit[y] + interest[y] for y in deficit
               if y in interest}

    write("fiscal/debt_from_estat.csv", rows(years, {"gross": debt}, dec=1))
    write("fiscal/deficit_from_estat.csv",
          rows(years, {"deficit": deficit, "primary": primary,
                       "interest": interest}, dec=2))
    write("fiscal/revenue_from_estat.csv",
          rows(years, {"revenue": revenue, "expenditure": expenditure},
               dec=1))

    # ---- taxes: Eurostat's harmonised total, not the French ratio -----
    # D2+D5+D91+D61 net of D995 is Eurostat's "taxes and social
    # contributions"; France's own "taux de prélèvements obligatoires" is a
    # national definition that lands a point or so lower. They are kept as
    # separate columns, never spliced.
    taxes = annual("gov_10a_taxag", geo=GEO,
                   na_item="D2_D5_D91_D61_M_D995",
                   unit="PC_GDP", sector="S13_S212", freq="A")
    write("fiscal/tax_burden_from_estat.csv",
          rows(years, {"estat": taxes}, dec=1))

    # ---- COFOG: where the money actually goes ------------------------
    cofog: dict[str, dict[int, float]] = {}
    for name, code in COFOG.items():
        if code:
            cofog[name] = annual("gov_10a_exp", geo=GEO, na_item="TE",
                                 unit="PC_GDP", sector="S13",
                                 cofog99=code, freq="A")
    parts = {c: annual("gov_10a_exp", geo=GEO, na_item="TE", unit="PC_GDP",
                       sector="S13", cofog99=c, freq="A")
             for c in ("GF02", "GF03", "GF05", "GF06", "GF08")}
    cofog["defence_order"] = {
        y: parts["GF02"].get(y, 0) + parts["GF03"].get(y, 0)
        for y in parts["GF02"]}
    cofog["other"] = {
        y: sum(parts[c].get(y, 0) for c in ("GF05", "GF06", "GF08"))
        for y in parts["GF05"]}
    cofog["total"] = annual("gov_10a_exp", geo=GEO, na_item="TE",
                            unit="PC_GDP", sector="S13", cofog99="TOTAL",
                            freq="A")
    order = ["social_protection", "health", "general_services", "education",
             "economic_affairs", "defence_order", "other", "total"]
    write("fiscal/spending_by_function_from_estat.csv",
          rows(years, {k: cofog[k] for k in order}, dec=2))

    # ---- investment: three concepts, kept apart ----------------------
    gfcf_pct = {y: gfcf[y] / nominal[y] * 100 for y in gfcf if y in nominal}
    write("fiscal/investment_from_estat.csv",
          rows(years, {"gfcf_eurbn": {y: v / 1000 for y, v in gfcf.items()},
                       "gfcf_pct_gdp": gfcf_pct,
                       "gov_gfcf_pct_gdp": gov_gfcf}, dec=2))

    # ---- labour market ------------------------------------------------
    unemp = annual("une_rt_a", geo=GEO, unit="PC_ACT", sex="T",
                   age="Y15-74", freq="A")
    write("macro/unemployment_from_estat.csv",
          rows(years, {"estat": unemp}, dec=1))

    # ---- prices: the HICP, which is NOT the French IPC ----------------
    hicp = annual("prc_hicp_aind", geo=GEO, unit="RCH_A_AVG",
                  coicop="CP00", freq="A")
    write("macro/hicp_from_estat.csv", rows(years, {"hicp": hicp}, dec=2))

    # ---- inequality and poverty, EU-SILC ------------------------------
    gini = annual("ilc_di12", geo=GEO, age="TOTAL", statinfo="GINI_HND",
                  freq="A")
    arop = annual("ilc_li02", geo=GEO, unit="PC", sex="T", age="TOTAL",
                  statinfo="MED_EI", rskpovth="B_60", freq="A")
    write("social/gini_from_estat.csv", rows(years, {"silc": gini}, dec=1))
    write("social/poverty_from_estat.csv", rows(years, {"arop60": arop},
                                                dec=1))

    # ---- observed demography (the projection comes from INSEE) --------
    pop = annual("demo_gind", geo=GEO, indic_de="JAN", freq="A")
    births = annual("demo_gind", geo=GEO, indic_de="LBIRTH", freq="A")
    deaths = annual("demo_gind", geo=GEO, indic_de="DEATH", freq="A")
    tfr = annual("demo_find", geo=GEO, indic_de="TOTFERRT", freq="A")
    write("social/demography_from_estat.csv",
          rows(years, {"pop_mn": {y: v / 1e6 for y, v in pop.items()},
                       "births": births, "deaths": deaths, "tfr": tfr},
               dec=4))

    print("Done. Diff the *_from_estat.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
