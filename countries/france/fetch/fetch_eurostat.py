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


def spot(series: dict[int, float], year: int, expected: float, tol: float,
         what: str) -> None:
    """Fail rather than write when a known value does not come back.

    An API that changes units between editions, or serves an empty cube
    under HTTP 200, still produces a CSV; a pinned value is what tells the
    two apart from a real revision.
    """
    got = series.get(year)
    if got is None or abs(got - expected) > tol:
        raise SystemExit(f"{what}: {year} is {got}, expected {expected} "
                         f"± {tol}; nothing written")


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
    # A sum is only written where every part is published: a division the
    # source has not released yet is a hole, never a zero. `.get(y, 0)`
    # here once would have turned a late GF03 into a defence-and-order
    # figure that was defence alone.
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


    # ---- the plate spine's gap series --------------------------------
    # Each of these fills a canonical slot France had no committed series
    # for. They are sidecars like everything else here; the curated copy
    # the plate draws is written by hand after the diff is read.

    # Ten-year benchmark yields, the EMU convergence-criterion series
    # (annual average of monthly secondary-market yields). Germany is the
    # reference the OAT is quoted against, so it rides beside it.
    oat = annual("irt_lt_mcby_a", geo="FR", freq="A")
    bund = annual("irt_lt_mcby_a", geo="DE", freq="A")
    spot(oat, 2023, 2.99, 0.02, "irt_lt_mcby_a FR")
    spot(bund, 2023, 2.43, 0.02, "irt_lt_mcby_a DE")
    write("markets/bond_yields_from_estat.csv",
          rows(years, {"fr_10y": oat, "de_10y": bund}, dec=2))

    # Exports and imports of goods AND services, national accounts (P6,
    # P7), the spine's trade basis. The customs series in trade.csv is
    # goods only, on a FAB/FAB basis, and stays the national line.
    x_gs = annual("nama_10_gdp", geo=GEO, na_item="P6", unit="PC_GDP",
                  freq="A")
    m_gs = annual("nama_10_gdp", geo=GEO, na_item="P7", unit="PC_GDP",
                  freq="A")
    spot(x_gs, 2022, 36.6, 0.15, "nama_10_gdp P6")
    write("trade/trade_na_from_estat.csv",
          rows(years, {"exports_pct_gdp": x_gs, "imports_pct_gdp": m_gs,
                       "balance_pct_gdp": {y: x_gs[y] - m_gs[y]
                                           for y in x_gs if y in m_gs}},
               dec=1))

    # Crude rates as Eurostat publishes them (per 1,000 of the average
    # population), and that average population itself, which is the
    # denominator every rate France computes on the spine is put over.
    vit = {k: annual("demo_gind", geo=GEO, indic_de=k, freq="A")
           for k in ("AVG", "JAN", "GBIRTHRT", "GDEATHRT", "NATGROWRT",
                     "CNMIGRATRT")}
    spot(vit["GDEATHRT"], 2020, 9.9, 0.05, "demo_gind GDEATHRT")
    spot(vit["AVG"], 2019, 67_382_061, 5_000, "demo_gind AVG")
    write("social/vital_rates_from_estat.csv",
          rows(years, {"pop_avg": vit["AVG"], "pop_jan": vit["JAN"],
                       "birth_rate": vit["GBIRTHRT"],
                       "death_rate": vit["GDEATHRT"],
                       "natural_rate": vit["NATGROWRT"],
                       "net_migration_rate": vit["CNMIGRATRT"]}, dec=1))

    # Migration: the flows and stocks France reports under Regulation
    # 862/2007, all from INSEE's population estimates, plus the asylum,
    # permit and citizenship series of the interior ministry.
    common = dict(geo=GEO, age="TOTAL", sex="T", unit="NR", freq="A")
    imm = annual("migr_imm1ctz", citizen="TOTAL", agedef="COMPLET", **common)
    emi = annual("migr_emi1ctz", citizen="TOTAL", agedef="COMPLET", **common)
    born_abroad = annual("migr_pop3ctb", c_birth="FOR", **common)
    by_birth = annual("migr_pop3ctb", c_birth="TOTAL", **common)
    nationals = annual("migr_pop1ctz", citizen="NAT", **common)
    by_citizenship = annual("migr_pop1ctz", citizen="TOTAL", **common)
    asylum = annual("migr_asyappctza", geo=GEO, citizen="TOTAL", age="TOTAL",
                    sex="T", applicant="FRST", unit="PER", freq="A")
    permits = annual("migr_resfirst", geo=GEO, reason="TOTAL",
                     duration="TOTAL", citizen="TOTAL", unit="PER", freq="A")
    acq = annual("migr_acq", citizen="TOTAL", agedef="COMPLET", **common)
    spot(imm, 2022, 490_655, 1_000, "migr_imm1ctz")
    spot(born_abroad, 2025, 9_633_730, 10_000, "migr_pop3ctb FOR")
    write("migration/migration_from_estat.csv",
          rows(years, {"immigration": imm, "emigration": emi,
                       "foreign_born": born_abroad,
                       "pop_by_birth": by_birth,
                       "nationals": nationals,
                       "pop_by_citizenship": by_citizenship,
                       "asylum_first_time": asylum,
                       "first_permits": permits,
                       "citizenship_acquired": acq}, dec=0))

    # Causes of death (Inserm-CépiDc, as reported to Eurostat): crude
    # rates per 100,000 and the counts behind them, residents in France.
    # And road deaths from the CARE database (ONISR, 30-day definition),
    # with Eurostat's own rate per million inhabitants.
    cod = {}
    for name, icd in (("suicide", "X60-X84_Y870"),
                      ("homicide", "X85-Y09_Y871"),
                      ("transport", "V_Y85")):
        cod[f"{name}_rate"] = annual("hlth_cd_acdr2", geo=GEO, icd10=icd,
                                     sex="T", age="TOTAL", unit="RT",
                                     freq="A")
        cod[f"{name}_count"] = annual("hlth_cd_aro", geo=GEO, icd10=icd,
                                      sex="T", age="TOTAL", unit="NR",
                                      resid="TOT_IN", freq="A")
    road = dict(geo=GEO, sex="T", age="TOTAL", pers_cat="TOTAL", freq="A")
    cod["road_killed"] = annual("tran_sf_roadus", unit="NR", **road)
    cod["road_per_million"] = annual("tran_sf_roadus", unit="P_MHAB", **road)
    spot(cod["suicide_count"], 2019, 8_861, 20, "hlth_cd_aro suicide")
    spot(cod["road_killed"], 2019, 3_238, 10, "tran_sf_roadus")
    write("social/causes_from_estat.csv", rows(years, cod, dec=2))

    print("Done. Diff the *_from_estat.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
