#!/usr/bin/env python3
"""Refresh the Eurostat-backed series for Portugal into sidecar CSVs.

Usage:  python3 -I countries/portugal/fetch/fetch_eurostat.py

Everything here is a series Portugal reports to Eurostat under a statistical
obligation — the ESA 2010 national accounts, the EDP (Maastricht) fiscal
notification, COFOG expenditure, the LFS unemployment rate, the HICP — or
the harmonised migration suite that SOURCING_A_COUNTRY.md §4a makes the
system of record for an EU member. Eurostat is the authoritative
publication channel for all of it. Where INE publishes its own national
series of the same thing (the IPC, the IE/EPA unemployment rate, the
migration flows), INE is the primary and this is the cross-check; the pairs
are kept as separate files, never spliced.

Output goes to `*_from_estat.csv` sidecars, never over a curated file.

Portugal traps, verified live against the API on 2026-10-22:
  * unit=PER empty-cube trap confirmed for PT: migr_asyappctza and
    migr_resfirst asked with unit=NR return a well-formed cube with an
    EMPTY value map and no error. Every query below is asserted non-empty
    and fails loudly rather than writing blanks.
  * citizen=FOR ALSO returns an empty cube for PT: the foreign-citizen
    stock is EU27_2020_FOR + NEU27_2020_FOR, drawn as the two labelled
    components (verified 1-Jan-2024: 179,276 + 866,111).
  * VINTAGE: Eurostat's migr_* tables for PT carry the PRE-REVISION
    transmission — INE's June-2026 population revision (~+1.6mn foreign
    residents, end-2024: 10,749,635 -> 11,387,222) has not been
    transmitted, and immigration stops at 2023. demo_gind DOES carry the
    revision, so two Eurostat datasets sit on two vintages of the same
    population. The CSV comments carry the vintage; never mix these files
    with INE's revised series (0004167/0006055/0006050).
  * une_rt_a for PT starts 2009 — 2006–2008 are absent in the source and
    carried as blanks; the INE series cover them.
  * ilc_di12 for PT carries 2014–2025 only; INE's ICOR Gini covers 2003+.
  * crim_off_cat's offence dimension is `iccs` — a wrong dimension name is
    an HTTP 400, not an empty cube.
  * migr_resfirst 2025 = 310,639 is the AIMA backlog of "manifestação de
    interesse" cases being regularised: administrative events, not
    arrivals. The CSV comment says so; the plate must too.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eurostat import annual, decode, fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

GEO = "PT"
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
# For PT there is no working FOR aggregate (empty cube — see the module
# docstring), so the foreign stock is the eu27 + non_eu27 pair.
CUTS = {"total": "TOTAL", "national": "NAT",
        "eu27": "EU27_2020_FOR", "non_eu27": "NEU27_2020_FOR"}


def need(series: dict, name: str) -> dict:
    """Fail loudly on an empty result — with this API that is how a bad
    unit or a removed code presents (the empty-cube trap), and a silent
    all-blank file is exactly the error this repo exists to avoid."""
    if not series:
        raise RuntimeError(f"{name}: empty result")
    return series


def expect(series: dict, year: int, value: float, name: str,
           tol: float = 0.05) -> None:
    """Spot-check a fetched series against a value verified by hand."""
    got = series.get(year)
    if got is None or abs(got - value) > tol:
        raise RuntimeError(
            f"{name}: expected {year} ≈ {value}, got {got}")
    print(f"  ok {name} {year} = {got}")


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


def write(rel: str, text: str, comment: str | None = None) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if comment:
        banner = "\n".join(f"# {ln}" if ln else "#"
                           for ln in textwrap.dedent(comment).strip().splitlines())
        text = banner + "\n" + text
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
    print("Fetching Eurostat series for Portugal...")

    # ---- national accounts -------------------------------------------
    nominal = need(annual("nama_10_gdp", geo=GEO, na_item="B1GQ",
                          unit="CP_MEUR", freq="A"), "nama_10_gdp B1GQ")
    growth = need(annual("nama_10_gdp", geo=GEO, na_item="B1GQ",
                         unit="CLV_PCH_PRE", freq="A"),
                  "nama_10_gdp growth")
    gfcf = need(annual("nama_10_gdp", geo=GEO, na_item="P51G",
                       unit="CP_MEUR", freq="A"), "nama_10_gdp P51G")
    # Eurostat publishes GDP in millions; the plates read billions of euro.
    nominal_bn = {y: v / 1000 for y, v in nominal.items()}
    expect(nominal_bn, 2024, 291.2, "GDP €bn", tol=0.15)
    expect(nominal_bn, 2025, 308.5, "GDP €bn", tol=0.15)
    expect(growth, 2020, -8.2, "real growth")
    expect(growth, 2022, 7.0, "real growth")
    write("macro/gdp_from_estat.csv",
          rows(years, {"nominal_eurbn": nominal_bn, "real_growth": growth},
               dec=2))

    # ---- EDP / Maastricht: the authoritative fiscal aggregates --------
    deficit = need(annual("gov_10dd_edpt1", geo=GEO, na_item="B9",
                          unit="PC_GDP", sector="S13", freq="A"),
                   "gov_10dd_edpt1 B9")
    debt = need(annual("gov_10dd_edpt1", geo=GEO, na_item="GD",
                       unit="PC_GDP", sector="S13", freq="A"),
                "gov_10dd_edpt1 GD")
    interest = need(annual("gov_10a_main", geo=GEO, na_item="D41PAY",
                           unit="PC_GDP", sector="S13", freq="A"),
                    "gov_10a_main D41PAY")
    revenue = need(annual("gov_10a_main", geo=GEO, na_item="TR",
                          unit="PC_GDP", sector="S13", freq="A"),
                   "gov_10a_main TR")
    expenditure = need(annual("gov_10a_main", geo=GEO, na_item="TE",
                              unit="PC_GDP", sector="S13", freq="A"),
                       "gov_10a_main TE")
    gov_gfcf = need(annual("gov_10a_main", geo=GEO, na_item="P51G",
                           unit="PC_GDP", sector="S13", freq="A"),
                    "gov_10a_main P51G")
    # The primary balance is the headline deficit with interest added back:
    # it is what the budget would be if the debt were free, and it is the
    # number that says whether today's policy is adding to the stock.
    primary = {y: deficit[y] + interest[y] for y in deficit
               if y in interest}

    # The debt stock in euro: quarterly EDP debt, read at Q4. A stock read
    # at a moment may show the running year as its latest observed quarter;
    # the plate labels it a latest point, not the year's result.
    qd = fetch("gov_10q_ggdebt", "gov_10q_ggdebt_pt",
               geo=GEO, na_item="GD", unit="MIO_EUR", sector="S13", freq="Q")
    t = qd["id"].index("time")
    debt_eur_q4 = {}
    for key, value in decode(qd).items():
        year, _, qtr = key[t].partition("-Q")
        if qtr == "4":
            debt_eur_q4[int(year)] = value / 1000  # MIO_EUR -> bn
    if not debt_eur_q4:
        raise RuntimeError("gov_10q_ggdebt: empty result")

    expect(debt_eur_q4, 2025, 275.1, "debt €bn Q4", tol=0.15)
    expect(debt, 2024, 93.0, "debt %GDP")
    expect(debt, 2025, 89.2, "debt %GDP")
    expect(deficit, 2023, 1.1, "deficit %GDP")
    expect(deficit, 2024, 0.7, "deficit %GDP")
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
    # na_item=TR returns an empty cube here; the harmonised taxes-and-
    # contributions aggregate is D2+D5+D91+D61 net of D995 over S13_S212.
    taxes = need(annual("gov_10a_taxag", geo=GEO,
                        na_item="D2_D5_D91_D61_M_D995",
                        unit="PC_GDP", sector="S13_S212", freq="A"),
                 "gov_10a_taxag")
    write("fiscal/tax_burden_from_estat.csv",
          rows(years, {"estat": taxes}, dec=1))

    # ---- COFOG: where the money actually goes ------------------------
    cofog: dict[str, dict[int, float]] = {}
    for name, code in COFOG.items():
        if code:
            cofog[name] = need(
                annual("gov_10a_exp", geo=GEO, na_item="TE", unit="PC_GDP",
                       sector="S13", cofog99=code, freq="A"),
                f"gov_10a_exp {code}")
    parts = {c: need(annual("gov_10a_exp", geo=GEO, na_item="TE",
                            unit="PC_GDP", sector="S13", cofog99=c, freq="A"),
                     f"gov_10a_exp {c}")
             for c in ("GF02", "GF03", "GF05", "GF06", "GF08")}
    # A sum is only written where every part is published: a missing
    # division is a hole, never a zero.
    def summed(codes):
        common = set.intersection(*(set(parts[c]) for c in codes))
        return {y: sum(parts[c][y] for c in codes) for y in common}
    cofog["defence_order"] = summed(("GF02", "GF03"))
    cofog["other"] = summed(("GF05", "GF06", "GF08"))
    cofog["total"] = need(
        annual("gov_10a_exp", geo=GEO, na_item="TE", unit="PC_GDP",
               sector="S13", cofog99="TOTAL", freq="A"), "gov_10a_exp TOTAL")
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

    # ---- trade in the national accounts (the customs chapter is INE) --
    exports = need(annual("nama_10_gdp", geo=GEO, na_item="P6",
                          unit="CP_MEUR", freq="A"), "nama_10_gdp P6")
    imports = need(annual("nama_10_gdp", geo=GEO, na_item="P7",
                          unit="CP_MEUR", freq="A"), "nama_10_gdp P7")
    write("trade/trade_from_estat.csv",
          rows(years, {"exports_eurbn": {y: v / 1000 for y, v in exports.items()},
                       "imports_eurbn": {y: v / 1000 for y, v in imports.items()}},
               dec=2))

    # ---- labour market ------------------------------------------------
    # PT values start 2009; 2006–2008 are absent in the source and carried
    # as blanks — the INE EPA/IE series cover them.
    unemp = need(annual("une_rt_a", geo=GEO, unit="PC_ACT", sex="T",
                        age="Y15-74", freq="A"), "une_rt_a")
    expect(unemp, 2009, 11.2, "unemployment", tol=0.15)
    if any(y in unemp for y in (2006, 2007, 2008)):
        raise RuntimeError("une_rt_a now carries 2006–08 for PT — "
                           "re-check the blank-hole comment")
    write("macro/unemployment_from_estat.csv",
          rows(years, {"estat": unemp}, dec=1),
          comment="""\
          Eurostat LFS unemployment rate (une_rt_a), 15–74. PT values start
          2009 — 2006–2008 are absent in the source and stay blank; the INE
          series (fetch_ine.py) covers them. Drawn beside the INE rate,
          never spliced.""")

    # ---- prices: the HICP, which is NOT the Portuguese IPC ------------
    hicp = need(annual("prc_hicp_aind", geo=GEO, unit="RCH_A_AVG",
                       coicop="CP00", freq="A"), "prc_hicp_aind")
    expect(hicp, 2022, 8.1, "HICP")
    expect(hicp, 2024, 2.7, "HICP")
    write("macro/hicp_from_estat.csv", rows(years, {"hicp": hicp}, dec=2))

    # ---- the 10-year benchmark yield ----------------------------------
    y10 = need(annual("irt_lt_mcby_a", geo=GEO, freq="A"), "irt_lt_mcby_a")
    expect(y10, 2012, 10.55, "10y yield", tol=0.01)
    write("markets/yield_10y_from_estat.csv", rows(years, {"yield_10y": y10},
                                                   dec=2))

    # ---- inequality and poverty, EU-SILC ------------------------------
    # ilc_di12 carries PT 2014–2025 ONLY; earlier years are absent in the
    # source. INE's ICOR Gini covers 2003+ and is the primary for the
    # window's first half.
    gini = need(annual("ilc_di12", geo=GEO, age="TOTAL", statinfo="GINI_HND",
                       freq="A"), "ilc_di12")
    arop = need(annual("ilc_li02", geo=GEO, unit="PC", sex="T", age="TOTAL",
                       statinfo="MED_EI", rskpovth="B_60", freq="A"),
                "ilc_li02")
    if min(gini) != 2014:
        raise RuntimeError(f"ilc_di12 PT now starts {min(gini)}, not 2014 — "
                           "re-check the comment")
    write("social/gini_from_estat.csv", rows(years, {"silc": gini}, dec=1),
          comment="""\
          Eurostat EU-SILC Gini (ilc_di12). PT values run 2014–2025 ONLY;
          the blanks before 2014 are real absences in the source. INE's
          ICOR series (gini_from_ine.csv) covers 2003+ — two files, never
          spliced.""")
    write("social/poverty_from_estat.csv", rows(years, {"arop60": arop},
                                                dec=1))

    # ---- observed demography (the revised vintage; flows are NOT) -----
    pop = need(annual("demo_gind", geo=GEO, indic_de="JAN", freq="A"),
               "demo_gind JAN")
    births = need(annual("demo_gind", geo=GEO, indic_de="LBIRTH", freq="A"),
                  "demo_gind LBIRTH")
    deaths = need(annual("demo_gind", geo=GEO, indic_de="DEATH", freq="A"),
                  "demo_gind DEATH")
    expect(pop, 2025, 11387222, "demo_gind JAN (revised vintage)", tol=0)
    tfr = need(annual("demo_find", geo=GEO, indic_de="TOTFERRT", freq="A"),
               "demo_find TOTFERRT")
    write("social/demography_from_estat.csv",
          rows(years, {"pop_mn": {y: v / 1e6 for y, v in pop.items()},
                       "births": births, "deaths": deaths, "tfr": tfr},
               dec=4),
          comment="""\
          VINTAGE: demo_gind ALREADY carries INE's June-2026 population
          revision (1-Jan-2025 = 11,387,222 = INE's 31-Dec-2024), while the
          migr_* files beside it are the PRE-revision transmission
          (1-Jan-2025 total stock = 10,749,635). Two Eurostat datasets, two
          vintages of the same population — never mix them on one plate.
          tfr is demo_find, which is NOT on the revised denominators: from
          2021 it runs above INE's 0001293 (2024: 1.41 vs 1.27), as more
          women in the denominator would predict. pop_mn 2022 carries
          Eurostat's break flag (the first revised 1 January).""")

    # ---- police-recorded homicide (dimension is `iccs`) ---------------
    homicide = need(annual("crim_off_cat", geo=GEO, iccs="ICCS0101",
                           unit="NR", freq="A"), "crim_off_cat ICCS0101")
    expect(homicide, 2008, 124, "police homicide", tol=0)
    expect(homicide, 2024, 72, "police homicide", tol=0)
    write("social/homicide_from_estat.csv",
          rows(years, {"police_recorded": homicide}, dec=0),
          comment="""\
          Police-recorded intentional homicide (crim_off_cat,
          iccs=ICCS0101). Drawn beside the death-certificate count in
          causes_of_death_from_ine.csv — the two disagree in both
          directions and neither is wrong (SOURCING §4).""")

    # ---- migration: the harmonised suite, both definitions ------------
    # VINTAGE: pre-revision transmission. Immigration stops at 2023; the
    # hole after it is a hole. INE's files carry the revised methodology —
    # drawn beside, never spliced.
    imm = migration("migr_imm1ctz", "citizen", "by_citizenship", agedef=True)
    imm_birth = migration("migr_imm3ctb", "c_birth", "by_birth", agedef=True)
    expect(imm["by_citizenship_total"], 2022, 167098, "immigration", tol=0)
    expect(imm["by_citizenship_total"], 2023, 189367, "immigration", tol=0)
    # The vintage claim in the comment: the transmission stops at 2023.
    # If a later year appears, Eurostat has ingested something new and
    # the comment (and the plate) must be revisited.
    if max(imm["by_citizenship_total"]) != 2023:
        raise RuntimeError("migr_imm1ctz no longer stops at 2023 — "
                           "re-check the vintage comment")
    write("migration/immigration_from_estat.csv",
          rows(years, {**imm, **imm_birth}, dec=0),
          comment="""\
          VINTAGE: PRE-REVISION. Eurostat carries Portugal's old
          transmission — the series STOPS AT 2023 (2022 167,098, 2023
          189,367) and the 2026 population-revision methodology has not
          been ingested. INE's revised file (immigration_from_ine.csv)
          continues it (2024 394,904); the two agree through 2020. Drawn
          beside, never spliced; the 2021 seam in the INE file is
          methodology, not migration.""")

    emi = migration("migr_emi1ctz", "citizen", "by_citizenship", agedef=True)
    expect(emi["by_citizenship_total"], 2024, 33916, "emigration", tol=0)
    write("migration/emigration_from_estat.csv", rows(years, emi, dec=0),
          comment="""\
          VINTAGE: PRE-REVISION (stops at 2024, 33,916). Register-based
          departures are under-measured (leaving needs no paperwork); INE's
          revised emigration_from_ine.csv is the correction. Published
          beside immigration, never as a pre-computed net (SOURCING §4a).""")

    stock = migration("migr_pop1ctz", "citizen", "by_citizenship")
    stock_birth = migration("migr_pop3ctb", "c_birth", "by_birth")
    # citizen=FOR returns an empty cube for PT: the foreign stock is the
    # sum of the two labelled components, verified 1-Jan-2024.
    expect(stock["by_citizenship_eu27"], 2024, 179276, "EU27 stock", tol=0)
    expect(stock["by_citizenship_non_eu27"], 2024, 866111,
           "non-EU27 stock", tol=0)
    expect(stock["by_citizenship_total"], 2025, 10749635,
           "stock total (pre-revision vintage)", tol=0)
    write("migration/stock_from_estat.csv",
          rows(years, {**stock, **stock_birth}, dec=0),
          comment="""\
          Resident population on 1 January, both definitions. VINTAGE:
          PRE-REVISION — total 1-Jan-2025 = 10,749,635 against the revised
          11,387,222 for the same date (INE 31-Dec-2024 = demo_gind
          1-Jan-2025); label the vintage or this plate contradicts the
          demography one. Eurostat flags a break at 1-Jan-2009 (2008 is
          provisional): 2006–2008 are not comparable with 2009+. QUIRK: citizen=FOR is an empty
          cube for PT — the foreign-citizen total is eu27 + non_eu27
          (1-Jan-2024: 179,276 + 866,111 = 1,045,387).""")

    # Asylum: unit=PER — with unit=NR the cube comes back silently empty.
    # Applications are not decisions are not grants: the four columns are
    # four different questions and are drawn as four labelled series.
    asy = need(annual("migr_asyappctza", geo=GEO, unit="PER", citizen="TOTAL",
                      applicant="TOTAL", sex="T", age="TOTAL", freq="A"),
               "migr_asyappctza")
    asy_first = need(annual("migr_asyappctza", geo=GEO, unit="PER",
                            citizen="TOTAL", applicant="FRST", sex="T",
                            age="TOTAL", freq="A"), "migr_asyappctza FRST")
    dec_total = need(annual("migr_asydcfsta", geo=GEO, unit="PER",
                            citizen="TOTAL", decision="TOTAL", sex="T",
                            age="TOTAL", freq="A"), "migr_asydcfsta TOTAL")
    dec_pos = need(annual("migr_asydcfsta", geo=GEO, unit="PER",
                          citizen="TOTAL", decision="POS", sex="T",
                          age="TOTAL", freq="A"), "migr_asydcfsta POS")
    expect(asy, 2023, 2695, "asylum applications", tol=0)
    expect(asy, 2024, 2690, "asylum applications", tol=0)
    write("migration/asylum_from_estat.csv",
          rows(years, {"applications": asy, "first_time": asy_first,
                       "decisions": dec_total, "positive": dec_pos},
               dec=0),
          comment="""\
          Asylum (migr_asyappctza / migr_asydcfsta, unit=PER — unit=NR is
          the empty-cube trap). Applications, first-time applications (a
          subset), first-instance decisions, positive decisions: four
          numbers that are not each other. Portugal's counts are small
          (2024: 2,690 applications). Starts 2008. Eurostat flags a BREAK
          on both decision series in 2024 (positive = 10 of 1,005
          decisions, as published): annotate it, do not read it as a
          policy change until the reason is known.""")

    # First residence permits: unit=PER, same empty-cube trap.
    permits = need(annual("migr_resfirst", geo=GEO, unit="PER",
                          citizen="TOTAL", reason="TOTAL", duration="TOTAL",
                          freq="A"), "migr_resfirst")
    expect(permits, 2024, 121872, "first permits", tol=0)
    expect(permits, 2025, 310639, "first permits", tol=0)
    write("migration/permits_from_estat.csv",
          rows(years, {"first_permits": permits}, dec=0),
          comment="""\
          First residence permits ISSUED in the year (migr_resfirst,
          unit=PER — unit=NR is the empty-cube trap). 2025 = 310,639 is
          the AIMA backlog of "manifestação de interesse" cases being
          regularised: administrative events, not arrivals — the plate
          must say so (SOURCING §4a). Starts 2008. Eurostat flags 2025 as a
          break in series.""")

    # Acquisitions of citizenship: the naturalisation flow that moves the
    # citizenship-cut stock without anybody moving.
    acq = need(annual("migr_acq", geo=GEO, unit="NR", citizen="TOTAL",
                      sex="T", age="TOTAL", agedef="REACH", freq="A"),
               "migr_acq")
    expect(acq, 2020, 32147, "acquisitions", tol=0)
    expect(acq, 2024, 20624, "acquisitions", tol=0)
    write("migration/naturalisation_from_estat.csv",
          rows(years, {"acquisitions": acq}, dec=0),
          comment="""\
          Acquisitions of Portuguese citizenship (migr_acq). The flow that
          moves the citizenship-cut stock without anybody moving; drawn
          beside the stocks, not inside them.""")

    print("Done. Diff the *_from_estat.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
