#!/usr/bin/env python3
"""Refresh the Eurostat-backed series for Spain into sidecar CSVs.

Usage:  python3 -I countries/spain/fetch/fetch_eurostat.py

Everything here is a series Spain reports to Eurostat under a statistical
obligation — the ESA 2010 national accounts, the EDP (Maastricht) fiscal
notification, COFOG expenditure, the LFS unemployment rate, the HICP — or
the harmonised migration suite that SOURCING_A_COUNTRY.md §4a makes the
system of record for an EU member. Eurostat is the authoritative
publication channel for all of it. Where INE publishes its own national
series of the same thing (the IPC, the EPA rate, the migration flows),
INE is the primary and this is the cross-check; the pairs are kept as
separate files, never spliced.

Output goes to `*_from_estat.csv` sidecars, never over a curated file.

Migration notes, hard-won against the live API (2026-10-22):
  * migr_asyappctza and migr_resfirst use unit=PER. Asking for unit=NR
    returns a well-formed cube with an EMPTY value map and no error — the
    endpoint's own version of the silent-truncation trap. The fetcher
    therefore fails on an empty result rather than writing it.
  * migr_resfirst and migr_asyappctza start in 2008; the blanks before
    that are real absences, carried as blanks.
  * EU27_2020_FOR and NEU27_2020_FOR split intra-EU from third-country
    movement: different legal objects, drawn as separate columns.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eurostat import annual, decode, fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

GEO = "ES"
Y0, Y1 = 2006, 2026

COFOG = {
    "social_protection": "GF10",
    "health": "GF07",
    "general_services": "GF01",   # incl. interest on the debt
    "education": "GF09",
    "economic_affairs": "GF04",
    "defence_order": None,        # GF02 + GF03, summed below
    "other": None,                # GF05 + GF06 + GF08, summed below
}

# The citizenship and country-of-birth cuts share these aggregate codes;
# the pair (same quantity, two definitions) is the point of the chapter.
CUTS = {"total": "TOTAL", "national": "NAT",
        "eu27": "EU27_2020_FOR", "non_eu27": "NEU27_2020_FOR"}


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


def migration(dataset: str, dim: str, name: str,
              agedef: bool = False) -> dict[str, dict[int, float]]:
    """The four CUTS of one migration dataset as {column: {year: value}}.

    An empty result means the filters named nothing — with this API that
    is how a bad unit or a removed code presents, so it fails loudly.
    Flow datasets (and migr_acq) carry an `agedef` dimension the stock
    ones do not; it is pinned to REACH where it exists.
    """
    out = {}
    for col, code in CUTS.items():
        extra = {"agedef": "REACH"} if agedef else {}
        series = annual(dataset, geo=GEO, unit="NR", sex="T", age="TOTAL",
                        freq="A", cache_key=f"{dataset}_{dim}_{code}",
                        **{dim: code}, **extra)
        if not series:
            raise RuntimeError(f"{dataset} {dim}={code}: empty result")
        out[f"{name}_{col}"] = {y: v for y, v in series.items()
                                if isinstance(v, (int, float))}
    return out


def main() -> None:
    years = list(range(Y0, Y1 + 1))
    print("Fetching Eurostat series for Spain...")

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

    # The debt stock in euro: quarterly EDP debt, read at Q4. A stock read
    # at a moment may show the running year as its latest observed quarter;
    # the plate labels it a latest point, not the year's result.
    qd = fetch("gov_10q_ggdebt", "gov_10q_ggdebt_es",
               geo=GEO, na_item="GD", unit="MIO_EUR", sector="S13", freq="Q")
    t = qd["id"].index("time")
    debt_eur_q4 = {}
    for key, value in decode(qd).items():
        year, _, qtr = key[t].partition("-Q")
        if qtr == "4":
            debt_eur_q4[int(year)] = value / 1000  # MIO_EUR -> bn

    write("fiscal/debt_from_estat.csv",
          rows(years, {"gross_pct_gdp": debt,
                       "gross_eurbn_q4": debt_eur_q4}, dec=1))
    write("fiscal/deficit_from_estat.csv",
          rows(years, {"deficit": deficit, "primary": primary,
                       "interest": interest}, dec=2))
    write("fiscal/revenue_from_estat.csv",
          rows(years, {"revenue": revenue, "expenditure": expenditure},
               dec=1))

    # ---- taxes: Eurostat's harmonised total ---------------------------
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
    # A summed line exists only in years where EVERY part is published: a
    # division Eurostat has not released yet is a hole, never a zero, so a
    # missing GF03 must not quietly turn "defence + public order" into
    # defence alone.
    def summed(codes):
        common = set.intersection(*(set(parts[c]) for c in codes))
        return {y: sum(parts[c][y] for c in codes) for y in common}
    cofog["defence_order"] = summed(("GF02", "GF03"))
    cofog["other"] = summed(("GF05", "GF06", "GF08"))
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

    # ---- trade in the national accounts (the customs chapter is pending)
    exports = annual("nama_10_gdp", geo=GEO, na_item="P6",
                     unit="CP_MEUR", freq="A")
    imports = annual("nama_10_gdp", geo=GEO, na_item="P7",
                     unit="CP_MEUR", freq="A")
    # The goods/services split of the same accounts (P61/P62, P71/P72).
    # Spain's surplus is a services surplus — tourism — on top of a goods
    # account that is in deficit most years; the split is what says so.
    split = {}
    for item, col in (("P61", "exports_goods_eurbn"),
                      ("P62", "exports_services_eurbn"),
                      ("P71", "imports_goods_eurbn"),
                      ("P72", "imports_services_eurbn")):
        series = annual("nama_10_gdp", geo=GEO, na_item=item,
                        unit="CP_MEUR", freq="A")
        if not series:
            raise RuntimeError(f"nama_10_gdp {item}: empty result")
        split[col] = {y: v / 1000 for y, v in series.items()}
    # The parts must add up to the totals they split, or one of the codes
    # means something other than what this file says it means.
    for y in exports:
        if y in split["exports_goods_eurbn"] and y in split["exports_services_eurbn"]:
            parts = (split["exports_goods_eurbn"][y]
                     + split["exports_services_eurbn"][y])
            if abs(parts - exports[y] / 1000) > 0.05:
                raise RuntimeError(f"P61+P62 != P6 in {y}")
    write("trade/trade_from_estat.csv",
          rows(years, {"exports_eurbn": {y: v / 1000 for y, v in exports.items()},
                       "imports_eurbn": {y: v / 1000 for y, v in imports.items()},
                       **split},
               dec=2))

    # ---- labour market ------------------------------------------------
    unemp = annual("une_rt_a", geo=GEO, unit="PC_ACT", sex="T",
                   age="Y15-74", freq="A")
    write("macro/unemployment_from_estat.csv",
          rows(years, {"estat": unemp}, dec=1))

    # ---- prices: the HICP, which is NOT the Spanish IPC --------------
    hicp = annual("prc_hicp_aind", geo=GEO, unit="RCH_A_AVG",
                  coicop="CP00", freq="A")
    write("macro/hicp_from_estat.csv", rows(years, {"hicp": hicp}, dec=2))

    # ---- the 10-year benchmark yield ----------------------------------
    y10 = annual("irt_lt_mcby_a", geo=GEO, freq="A")
    write("markets/yield_10y_from_estat.csv", rows(years, {"yield_10y": y10},
                                                   dec=2))

    # ---- the statutory minimum wage (SMI), harmonised ------------------
    # earn_mw_cur is half-yearly: the rate in force on 1 January (S1) and
    # on 1 July (S2), in euro per month on a TWELVE-month basis. Spain pays
    # the SMI in fourteen instalments, so this is the BOE monthly figure
    # times 14/12 (2024: 1,134 x 14/12 = 1,323). The decree is often
    # approved in February and back-dated to 1 January, which is why S1
    # can still show the previous year's rate (2022, 2023): S2 is the
    # year's own decree.
    mw = fetch("earn_mw_cur", geo=GEO, currency="EUR", freq="S")
    t = mw["id"].index("time")
    halves = {"S1": {}, "S2": {}}
    for key, value in decode(mw).items():
        year, _, half = key[t].partition("-")
        if half in halves:
            halves[half][int(year)] = value
    if not halves["S2"]:
        raise RuntimeError("earn_mw_cur: empty result")
    if round(halves["S2"].get(2024, 0)) != 1323:
        raise RuntimeError("earn_mw_cur 2024-S2 is not the 1,323 the BOE "
                           "decree implies (1,134 x 14 / 12)")
    write("social/minimum_wage_from_estat.csv",
          rows(years, {"eur_month_jan": halves["S1"],
                       "eur_month_jul": halves["S2"]}, dec=2))

    # ---- inequality and poverty, EU-SILC ------------------------------
    gini = annual("ilc_di12", geo=GEO, age="TOTAL", statinfo="GINI_HND",
                  freq="A")
    arop = annual("ilc_li02", geo=GEO, unit="PC", sex="T", age="TOTAL",
                  statinfo="MED_EI", rskpovth="B_60", freq="A")
    write("social/gini_from_estat.csv", rows(years, {"silc": gini}, dec=1))
    write("social/poverty_from_estat.csv", rows(years, {"arop60": arop},
                                                dec=1))

    # ---- observed demography (the national series comes from the INE) --
    pop = annual("demo_gind", geo=GEO, indic_de="JAN", freq="A")
    births = annual("demo_gind", geo=GEO, indic_de="LBIRTH", freq="A")
    deaths = annual("demo_gind", geo=GEO, indic_de="DEATH", freq="A")
    tfr = annual("demo_find", geo=GEO, indic_de="TOTFERRT", freq="A")
    write("social/demography_from_estat.csv",
          rows(years, {"pop_mn": {y: v / 1e6 for y, v in pop.items()},
                       "births": births, "deaths": deaths, "tfr": tfr},
               dec=4))

    # ---- migration: the harmonised suite, both definitions ------------
    imm = migration("migr_imm1ctz", "citizen", "by_citizenship", agedef=True)
    imm_birth = migration("migr_imm3ctb", "c_birth", "by_birth", agedef=True)
    write("migration/immigration_from_estat.csv",
          rows(years, {**imm, **imm_birth}, dec=0))

    emi = migration("migr_emi1ctz", "citizen", "by_citizenship", agedef=True)
    write("migration/emigration_from_estat.csv", rows(years, emi, dec=0))

    stock = migration("migr_pop1ctz", "citizen", "by_citizenship")
    stock_birth = migration("migr_pop3ctb", "c_birth", "by_birth")
    write("migration/stock_from_estat.csv",
          rows(years, {**stock, **stock_birth}, dec=0))

    # Asylum: unit=PER — with unit=NR the cube comes back silently empty.
    # Applications are not decisions are not grants: the three columns are
    # three different questions and are drawn as three labelled series.
    asy = annual("migr_asyappctza", geo=GEO, unit="PER", citizen="TOTAL",
                 applicant="TOTAL", sex="T", age="TOTAL", freq="A")
    asy_first = annual("migr_asyappctza", geo=GEO, unit="PER",
                       citizen="TOTAL", applicant="FRST", sex="T",
                       age="TOTAL", freq="A")
    dec_total = annual("migr_asydcfsta", geo=GEO, unit="PER", citizen="TOTAL",
                       decision="TOTAL", sex="T", age="TOTAL", freq="A")
    dec_pos = annual("migr_asydcfsta", geo=GEO, unit="PER", citizen="TOTAL",
                     decision="POS", sex="T", age="TOTAL", freq="A")
    if not asy:
        raise RuntimeError("migr_asyappctza: empty result")
    write("migration/asylum_from_estat.csv",
          rows(years, {"applications": asy, "first_time": asy_first,
                       "decisions": dec_total, "positive": dec_pos},
               dec=0))

    # First residence permits: unit=PER, same empty-cube trap.
    permits = annual("migr_resfirst", geo=GEO, unit="PER", citizen="TOTAL",
                     reason="TOTAL", duration="TOTAL", freq="A")
    if not permits:
        raise RuntimeError("migr_resfirst: empty result")
    write("migration/permits_from_estat.csv",
          rows(years, {"first_permits": permits}, dec=0))

    # Acquisitions of citizenship: the naturalisation flow that moves the
    # citizenship-cut stock without anybody moving.
    acq = annual("migr_acq", geo=GEO, unit="NR", citizen="TOTAL", sex="T",
                 age="TOTAL", agedef="REACH", freq="A")
    if not acq:
        raise RuntimeError("migr_acq: empty result")
    write("migration/naturalisation_from_estat.csv",
          rows(years, {"acquisitions": acq}, dec=0))

    print("Done. Diff the *_from_estat.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
