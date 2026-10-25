#!/usr/bin/env python3
"""Refresh Poland's Eurostat-backed series into review sidecars.

Usage:  make C=poland fetch   (or: python3 -I fetch/fetch_eurostat.py)

Poland is an EU member, so almost every spine topic has a series Poland
reports to Eurostat under a statistical obligation: the ESA 2010 national
accounts, the EDP (Maastricht) notification, COFOG expenditure, the LFS
unemployment rate, the HICP, the EU-SILC income and poverty tables, the
cause-of-death table, and the harmonised migration suite that
SOURCING_A_COUNTRY.md §4a makes the system of record for an EU member.
Eurostat is a publisher here, not a redistributor.

Where GUS publishes the national series of the same thing (GDP, CPI,
population, births and deaths, registered unemployment), GUS is primary
and these are the harmonised comparison line; the two live in separate
files and are never spliced.

Output goes to `*_from_estat.csv` sidecars under data/, never over a
curated file. Every series is checked for an empty result before it is
written: this API answers a bad filter with a well-formed cube and an
empty value map, which is the silent-truncation trap in its purest form.

Filters verified live 2026-10-25; see DISCOVERY.md for the route record.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DATA, FetchError, assert_close, num,  # noqa: E402
                    write_csv)
from eurostat import annual, decode, fetch, multi  # noqa: E402

GEO = "PL"
Y0, Y1 = 2006, 2026
YEARS = list(range(Y0, Y1 + 1))

COFOG = {
    "social_protection": "GF10",
    "health": "GF07",
    "general_services": "GF01",   # includes interest on the debt
    "education": "GF09",
    "economic_affairs": "GF04",
    "defence_order": None,        # GF02 + GF03, summed below
    "other": None,                # GF05 + GF06 + GF08, summed below
}

# The citizenship and country-of-birth cuts share these aggregate codes.
# TOTAL / NAT / FOR_STLS are the three the Polish register does publish;
# PL reports the foreign population only as groups, never by single
# country, so "Ukrainian" is NOT available on the citizenship cut — see
# DISCOVERY.md and the temporary-protection column, which is where the
# 2022 inflow actually shows.
CUTS = {"total": "TOTAL", "national": "NAT", "foreign": "FOR_STLS",
        "eu27": "EU27_2020_FOR", "non_eu27": "NEU27_2020_FOR"}
# The country-of-birth dimension names "all foreign-born" FOR; the
# citizenship dimension names it FOR_STLS (foreigners plus stateless).
CUTS_BIRTH = {**CUTS, "foreign": "FOR"}


def wide(rel: str, columns: dict[str, dict[int, float]], dec: int = 2,
         comment: str | None = None) -> None:
    """One row per year, one column per series, holes left as holes."""
    header = ["year"] + list(columns)
    rows = []
    for y in YEARS:
        cells = [y]
        for series in columns.values():
            v = series.get(y)
            cells.append(None if v is None else f"{v:.{dec}f}")
        rows.append(cells)
    path = write_csv(rel, header, rows, comment=comment)
    print(f"  -> {path.relative_to(DATA)}")


def pinned(dataset: str, **filters) -> dict[int, float]:
    """annual() that refuses an empty result instead of writing a blank."""
    series = annual(dataset, geo=GEO, freq="A", **filters)
    if not series:
        raise FetchError(f"{dataset} {filters}: empty result")
    return series


def migration_cuts(dataset: str, dim: str, name: str,
                   agedef: bool = False,
                   cuts: dict[str, str] | None = None
                   ) -> dict[str, dict[int, float]]:
    """The CUTS of one migration dataset as {column: {year: value}}."""
    out = {}
    for col, code in (cuts or CUTS).items():
        extra = {"agedef": "COMPLET"} if agedef else {}
        series = annual(dataset, geo=GEO, unit="NR", sex="T", age="TOTAL",
                        freq="A", **{dim: code}, **extra)
        if not series:
            raise FetchError(f"{dataset} {dim}={code}: empty result")
        out[f"{name}_{col}"] = series
    return out


def main() -> None:
    print("Fetching Eurostat series for Poland...")

    # ---- national accounts -------------------------------------------
    nominal = pinned("nama_10_gdp", na_item="B1GQ", unit="CP_MEUR")
    growth = pinned("nama_10_gdp", na_item="B1GQ", unit="CLV_PCH_PRE")
    gfcf = pinned("nama_10_gdp", na_item="P51G", unit="CP_MEUR")
    exports = pinned("nama_10_gdp", na_item="P6", unit="CP_MEUR")
    imports = pinned("nama_10_gdp", na_item="P7", unit="CP_MEUR")
    parts = {}
    for item, col in (("P61", "exports_goods_meur"),
                      ("P62", "exports_services_meur"),
                      ("P71", "imports_goods_meur"),
                      ("P72", "imports_services_meur")):
        parts[col] = pinned("nama_10_gdp", na_item=item, unit="CP_MEUR")
    # The parts must add up to the totals they split, or one code means
    # something other than what this file says it means.
    for y in exports:
        if y in parts["exports_goods_meur"] and y in parts["exports_services_meur"]:
            got = parts["exports_goods_meur"][y] + parts["exports_services_meur"][y]
            # Eurostat publishes one decimal, so two parts can miss their
            # total by 0.1 without anything being wrong.
            if abs(got - exports[y]) > 0.3:
                raise FetchError(f"P61+P62 != P6 in {y}: {got} vs {exports[y]}")

    # ---- prices and the labour market --------------------------------
    hicp = pinned("prc_hicp_aind", unit="RCH_A_AVG", coicop="CP00")
    # Eurostat's LFS unemployment begins in 2009 for the 15-74 group that
    # the atlas draws; the earlier years are on GUS's old BAEL methodology
    # and stay blank here rather than being back-filled.
    unemp = pinned("une_rt_a", unit="PC_ACT", sex="T", age="Y15-74")

    wide("macro/economy_from_estat.csv", {
        "gdp_meur": nominal,
        "gdp_growth_pct": growth,
        "gfcf_meur": gfcf,
        "hicp_pct": hicp,
        "unemployment_pct": unemp,
        "exports_meur": exports,
        "imports_meur": imports,
        **parts,
    }, dec=2, comment="""
Eurostat nama_10_gdp (B1GQ, P51G, P6, P7, P61/P62, P71/P72), prc_hicp_aind
(CP00, annual rate of change) and une_rt_a (15-74, LFS). PL/EUR, annual.
A euro GDP-per-person column is deliberately ABSENT: the canonical slot is
US$ per person from the World Bank, which is the same denominator every
country uses, and a euro column here would invite a second, unlike series.
HICP is NOT the Polish CPI (GUS publishes that separately): since 2022 the
two differ by the weight of housing costs the HICP carries.
""")

    # ---- fiscal: EDP aggregates and the COFOG split -------------------
    deficit = pinned("gov_10dd_edpt1", na_item="B9", unit="PC_GDP",
                     sector="S13")
    debt = pinned("gov_10dd_edpt1", na_item="GD", unit="PC_GDP", sector="S13")
    interest = pinned("gov_10a_main", na_item="D41PAY", unit="PC_GDP",
                      sector="S13")
    revenue = pinned("gov_10a_main", na_item="TR", unit="PC_GDP", sector="S13")
    expenditure = pinned("gov_10a_main", na_item="TE", unit="PC_GDP",
                         sector="S13")
    gov_gfcf = pinned("gov_10a_main", na_item="P51G", unit="PC_GDP",
                      sector="S13")
    primary = {y: deficit[y] + interest[y] for y in deficit if y in interest}
    wide("fiscal/fiscal_from_estat.csv", {
        "revenue_pct_gdp": revenue,
        "expenditure_pct_gdp": expenditure,
        "deficit_pct_gdp": deficit,
        "primary_pct_gdp": primary,
        "interest_pct_gdp": interest,
        "debt_pct_gdp": debt,
    }, dec=2, comment="""
Eurostat EDP notification (gov_10dd_edpt1: B9, GD) and gov_10a_main
(TR, TE, D41PAY, P51G) for general government (S13), calendar years, % of
GDP. One definition throughout: ESA 2010 accrual, the perimeter Poland
notifies to the Commission. The national cash-basis deficit and the
Ministry of Finance's debt definition (dług publiczny, excluding some
agency debt) are DIFFERENT series and are not spliced into these columns.
Primary balance = B9 + D41PAY, computed from the published components.
""")

    cofog: dict[str, dict[int, float]] = {}
    for name, code in COFOG.items():
        if code:
            cofog[name] = pinned("gov_10a_exp", na_item="TE", unit="PC_GDP",
                                 sector="S13", cofog99=code)
    pieces = {c: pinned("gov_10a_exp", na_item="TE", unit="PC_GDP",
                        sector="S13", cofog99=c)
              for c in ("GF02", "GF03", "GF05", "GF06", "GF08")}

    def summed(codes: tuple[str, ...]) -> dict[int, float]:
        # A summed line exists only in years where EVERY part is published.
        common = set.intersection(*(set(pieces[c]) for c in codes))
        return {y: sum(pieces[c][y] for c in codes) for y in common}

    cofog["defence_order"] = summed(("GF02", "GF03"))
    cofog["other"] = summed(("GF05", "GF06", "GF08"))
    cofog["total"] = pinned("gov_10a_exp", na_item="TE", unit="PC_GDP",
                            sector="S13", cofog99="TOTAL")
    order = ["social_protection", "health", "general_services", "education",
             "economic_affairs", "defence_order", "other", "total"]
    gfcf_pct = {y: gfcf[y] / nominal[y] * 100 for y in gfcf if y in nominal}
    wide("spending/spending_from_estat.csv", {
        **{k: cofog[k] for k in order},
        "gfcf_pct_gdp": gfcf_pct,
        "public_investment_pct_gdp": gov_gfcf,
    }, dec=2, comment="""
Eurostat gov_10a_exp (COFOG, na_item TE, S13) grouped into the spine's
seven functions: social protection GF10, health GF07, general public
services GF01, education GF09, economic affairs GF04, defence + public
order GF02+GF03, other GF05+GF06+GF08. Total is the published TOTAL.
gfcf_pct_gdp = nama_10_gdp P51G / B1GQ, whole economy, % of GDP.
public_investment_pct_gdp = gov_10a_main P51G, general government, % GDP.
""")

    # ---- trade --------------------------------------------------------
    wide("trade/trade_from_estat.csv", {
        "exports_pct_gdp": {y: exports[y] / nominal[y] * 100
                            for y in exports if y in nominal},
        "imports_pct_gdp": {y: imports[y] / nominal[y] * 100
                            for y in imports if y in nominal},
        "exports_meur": exports,
        "imports_meur": imports,
        **parts,
    }, dec=2, comment="""
Eurostat nama_10_gdp P6/P7: goods AND services, national-accounts basis,
% of GDP and EUR million. This is NOT the customs (KAS/GUS) goods series,
which is a different perimeter without services; both exist in this
country's data and are kept apart.
""")

    # ---- markets: the 10-year benchmark -------------------------------
    y10 = pinned("irt_lt_mcby_a")
    assert_close(y10.get(2024), 5.6, 0.6, "irt_lt_mcby_a 2024")
    wide("markets/yield_from_estat.csv", {"yield_10y": y10}, dec=3,
         comment="""
Eurostat irt_lt_mcby_a: EMU convergence-criterion 10-year government bond
yield, annual average, %. Poland is not in the euro area but reports it.
""")

    # ---- people: inequality, poverty, minimum wage --------------------
    gini = pinned("ilc_di12", age="TOTAL", statinfo="GINI_HND")
    arop = pinned("ilc_li02", unit="PC", sex="T", age="TOTAL",
                  statinfo="MED_EI", rskpovth="B_60")
    # earn_mw_cur is half-yearly and NAC is the national currency (PLN).
    # Poland sets the rate by regulation, effective 1 January; since 2023 a
    # second increase on 1 July means S1 and S2 differ, so both are kept.
    mw = fetch("earn_mw_cur", geo=GEO, currency="NAC", freq="S")
    t = mw["id"].index("time")
    halves: dict[str, dict[int, float]] = {"S1": {}, "S2": {}}
    for key, value in decode(mw).items():
        year, _, half = key[t].partition("-")
        if half in halves:
            halves[half][int(year)] = value
    if not halves["S2"]:
        raise FetchError("earn_mw_cur: empty result")
    assert_close(halves["S2"].get(2024), 4300, 0.01, "minimum wage 2024-S2")
    assert_close(halves["S1"].get(2024), 4242, 0.01, "minimum wage 2024-S1")
    wide("people/people_from_estat.csv", {
        "gini": gini,
        "arop60_pct": arop,
        "minimum_wage_pln_jan": halves["S1"],
        "minimum_wage_pln_jul": halves["S2"],
    }, dec=2, comment="""
Eurostat ilc_di12 (GINI_HND, EU-SILC), ilc_li02 (at-risk-of-poverty after
social transfers, 60% of median equivalised income) and earn_mw_cur in
national currency (PLN per month, statutory gross). S1 = rate in force on
1 January, S2 = rate from 1 July where Poland legislated a mid-year rise.
Both are the statutory rate, not the average wage.
""")

    # ---- demography ---------------------------------------------------
    pop = pinned("demo_gind", indic_de="JAN")
    births = pinned("demo_gind", indic_de="LBIRTH")
    deaths = pinned("demo_gind", indic_de="DEATH")
    tfr = pinned("demo_find", indic_de="TOTFERRT")
    rates = {k: pinned("demo_gind", indic_de=k) for k in
             ("GBIRTHRT", "GDEATHRT", "NATGROWRT", "CNMIGRATRT", "MIGTRT")}
    # demo_gind's MIGTRT is the demographic-balance residual (population
    # change minus natural change), while CNMIGRATRT is the REGISTERED
    # migration rate. They are two different measurements of "net
    # migration" and in 2022 they diverge by an order of magnitude —
    # 12.6 vs 0.2 per 1,000. Both are staged; neither fills the other.
    wide("demography/demography_from_estat.csv", {
        "population_jan": pop,
        "births": births,
        "deaths": deaths,
        "tfr": tfr,
        "birth_rate_per_1000": rates["GBIRTHRT"],
        "death_rate_per_1000": rates["GDEATHRT"],
        "natural_change_rate_per_1000": rates["NATGROWRT"],
        "net_migration_registered_per_1000": rates["CNMIGRATRT"],
        "net_migration_residual_per_1000": rates["MIGTRT"],
    }, dec=3, comment="""
Eurostat demo_gind (JAN, LBIRTH, DEATH, GBIRTHRT, GDEATHRT, NATGROWRT,
CNMIGRATRT, MIGTRT) and demo_find (TOTFERRT). Population is 1 January.
The TWO net-migration columns are not the same statistic: CNMIGRATRT is
the registered (meldunek) migration rate and MIGTRT is the residual
implied by the population balance. 2022: 0.2 vs 12.6 per 1,000. Never
draw one line from both.
""")

    # ---- mortality: deaths and causes ---------------------------------
    cause = multi("hlth_cd_aro", "icd10", geo=GEO, sex="T", age="TOTAL",
                  resid="TOT_IN", unit="NR")
    total = cause.get("TOTAL", {})
    covid = {y: (cause.get("U071", {}).get(y) or 0)
             + (cause.get("U072", {}).get(y) or 0)
             for y in YEARS
             if y in cause.get("U071", {}) or y in cause.get("U072", {})}
    wide("mortality/mortality_from_estat.csv", {
        "deaths_all": total,
        "covid_deaths_u071": cause.get("U071", {}),
        "covid_deaths_u072": cause.get("U072", {}),
        "covid_deaths_both": covid,
        "deaths_circulatory": cause.get("I", {}),
        "deaths_cancer": cause.get("C", {}),
    }, dec=0, comment="""
Eurostat hlth_cd_aro, residents, total population, underlining cause of
death (ICD-10), counts. U071 = COVID-19 virus identified, U072 = COVID-19
virus not identified; the combined column is the sum of the two published
codes and exists only in years where at least one is published. The table
starts in 2011; earlier years are GUS's own cause-of-death series.
""")

    # ---- security: the deaths the justice and police series disagree on
    assault = cause.get("X85-Y09_Y871", {})
    self_harm = cause.get("X60-X84_Y870", {})
    wide("security/security_from_estat.csv", {
        "assault_deaths_count": assault,
        "self_harm_deaths_count": self_harm,
        "accidents_deaths_count": cause.get("ACC", {}),
        "transport_deaths_count": cause.get("V_Y85", {}),
    }, dec=0, comment="""
Eurostat hlth_cd_aro (vital statistics, residents, underlying cause):
X85-Y09 assault, X60-X84 intentional self-harm, ACC accidents, V_Y85
transport accidents. These are DEATH-CERTIFICATE counts of homicide and
suicide; the police's recorded-offence count of the same homicides is a
different series (homicide_from_police.csv) and neither is wrong.
""")

    # ---- migration ----------------------------------------------------
    imm = migration_cuts("migr_imm1ctz", "citizen", "imm", agedef=True)
    emi = migration_cuts("migr_emi1ctz", "citizen", "emi", agedef=True)
    stock = migration_cuts("migr_pop1ctz", "citizen", "stock")
    stock_birth = migration_cuts("migr_pop3ctb", "c_birth", "stock_birth",
                                 cuts=CUTS_BIRTH)
    wide("migration/flows_from_estat.csv", {**imm, **emi}, dec=0,
         comment="""
Eurostat migr_imm1ctz / migr_emi1ctz, unit NR, agedef COMPLET: the
REGISTERED (meldunek) immigration and emigration flows. They do not count
the 2022 refugee inflow, which did not register a permanent residence —
see temporary_protection_from_estat.csv and the residual net-migration
column in demography_from_estat.csv for the two measures that do.
""")
    wide("migration/stock_from_estat.csv", {**stock, **stock_birth}, dec=0,
         comment="""
Eurostat migr_pop1ctz (citizenship) and migr_pop3ctb (country of birth),
population on 1 January, unit NR. Poland reports the foreign population
as GROUPS (FOR_STLS, EU27_2020_FOR, NEU27_2020_FOR), not by single
country, so no "Ukrainian" column exists in this table. The citizenship
cut and the birthplace cut are different legal objects and are drawn as
separate lines.
""")

    # Asylum: unit=PER. With unit=NR this cube comes back silently empty.
    asy = pinned("migr_asyappctza", unit="PER", citizen="TOTAL",
                 applicant="TOTAL", sex="T", age="TOTAL")
    asy_first = pinned("migr_asyappctza", unit="PER", citizen="TOTAL",
                       applicant="FRST", sex="T", age="TOTAL")
    dec_total = pinned("migr_asydcfsta", unit="PER", citizen="TOTAL",
                       decision="TOTAL", sex="T", age="TOTAL")
    dec_pos = pinned("migr_asydcfsta", unit="PER", citizen="TOTAL",
                     decision="POS", sex="T", age="TOTAL")
    permits = pinned("migr_resfirst", unit="PER", citizen="TOTAL",
                     reason="TOTAL", duration="TOTAL")
    acq = pinned("migr_acq", unit="NR", citizen="TOTAL", sex="T",
                 age="TOTAL", agedef="COMPLET")
    wide("migration/asylum_from_estat.csv", {
        "applications": asy, "first_time_applications": asy_first,
        "decisions_total": dec_total, "decisions_positive": dec_pos,
        "first_permits": permits, "acquisitions_of_citizenship": acq,
    }, dec=0, comment="""
Eurostat migr_asyappctza (applicants), migr_asydcfsta (first-instance
decisions, TOTAL and POS), migr_resfirst (FIRST permits issued in the
year — not permits in force), migr_acq (acquisitions of citizenship).
Four different questions; never one line called "asylum".
""")

    # Beneficiaries of temporary protection: the one harmonised series that
    # measures the 2022 Ukrainian inflow, monthly, from March 2022.
    tp = fetch("migr_asytpsm", geo=GEO, citizen="TOTAL", age="TOTAL",
               sex="T", unit="PER", freq="M", sinceTimePeriod="2022-03")
    t = tp["id"].index("time")
    latest: dict[int, tuple[int, float]] = {}
    for key, value in decode(tp).items():
        period = key[t]
        if len(period) != 7:
            continue
        y, m = int(period[:4]), int(period[5:])
        if y not in latest or m > latest[y][0]:
            latest[y] = (m, value)
    if not latest:
        raise FetchError("migr_asytpsm: empty result")
    # Keep the December stock where the year is complete, else the latest
    # month of that year, and say which in the comment.
    wide("migration/temporary_protection_from_estat.csv",
         {"beneficiaries_end_of_year": {y: v for y, (m, v) in latest.items()}},
         dec=0, comment=f"""
Eurostat migr_asytpsm: beneficiaries of temporary protection at the end
of the month, all citizenships, persons. The value kept for each year is
its LAST observed month (December where published; {sorted(latest)[-1]}
runs to month {latest[sorted(latest)[-1]][0]}). This is the only
harmonised series that measures the 2022+ Ukrainian inflow; it is a stock
of people under a specific legal status, NOT an immigration flow and NOT
a residence-permit count.
""")

    print("Done. Diff the *_from_estat.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
