"""The facts Spain's plates assert.

Each test states a claim a plate makes about the country's own data, so a
refetch that invalidates the claim fails loudly instead of quietly changing
a published chart. The generic checks — isolation, catalogs, data hygiene,
the spine itself, the built pages — live in tests/ and run against every
country.

Rates: every per-1,000 and per-100,000 panel divides by the INE's 1 July
population of the same year (social/population.csv, population_jul). The
tests below recompute pinned years by hand from the two CSVs, so a plate
that slipped to the 1 January level, or zipped a count and a population by
position, fails here.
"""
from __future__ import annotations

import csv

import pytest
from matplotlib.text import Annotation

from core.country import Country
from tests.probe import plate, plate_names

SLUG = "spain"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(
            ln for ln in fh if not ln.lstrip().startswith("#")))


def by_year(rel: str, key: str = "year") -> dict[int, dict]:
    return {int(r[key]): r for r in rows(rel)}


def col(rel: str, column: str) -> dict[int, float]:
    return {y: float(r[column]) for y, r in by_year(rel).items()
            if (r.get(column) or "").strip()}


def cause(name: str) -> dict[int, float]:
    return {int(r["year"]): float(r["deaths"])
            for r in rows("social/causes_of_death.csv") if r["cause"] == name}


MID = col("social/population.csv", "population_jul")
JAN = col("social/population.csv", "population")


# ------------------------------------------------------------ population
def test_the_mid_year_population_is_the_ine_1_july_figure():
    """The denominator of every rate: ECP at 1 July, not 1 January."""
    assert MID[2024] == 48821936
    assert JAN[2024] == 48619695
    assert JAN[2024] < MID[2024] < JAN[2025]


# ------------------------------------------------------------- economy
def test_gdp_2024_is_the_same_on_both_publishers():
    """Eurostat's transmission and the INE's own release read €1,598.59bn
    for 2024 — same vintage today. The level now rides as a note on the
    world plate; the columns stay apart."""
    t = by_year("macro/gdp.csv")
    assert float(t[2024]["nominal_eurbn"]) == pytest.approx(1598.59, abs=0.05)
    assert float(t[2024]["nominal_eurbn_ine"]) == pytest.approx(1598.59,
                                                               abs=0.05)
    panel = plate(SLUG, "plate_world").panel("GDP at current prices")
    assert any("in euros, €1,690bn in 2025" in s for s in panel.texts())


def test_the_three_contractions_are_what_the_bands_claim():
    t = by_year("macro/gdp.csv")
    assert float(t[2009]["real_growth"]) == pytest.approx(-3.8, abs=0.1)
    assert float(t[2012]["real_growth"]) == pytest.approx(-2.9, abs=0.05)
    assert float(t[2020]["real_growth"]) == pytest.approx(-10.9, abs=0.1)
    panel = plate(SLUG, "plate_economy").panel("Real GDP growth")
    assert any("-10.9" in s for s in panel.texts())
    heights = [p.get_height() for p in panel.ax.patches
               if p.get_data_transform() is panel.ax.transData]
    assert min(heights) == pytest.approx(-10.9, abs=0.01)


def test_the_ipc_rate_reproduces_the_official_media_anual():
    t = by_year("macro/inflation.csv")
    assert float(t[2008]["ipc"]) == pytest.approx(4.08, abs=0.01)
    assert float(t[2024]["ipc"]) == pytest.approx(2.77, abs=0.01)
    assert float(t[2020]["hicp"]) == pytest.approx(-0.3, abs=0.01)
    panel = plate(SLUG, "plate_economy").panel("Consumer prices")
    assert panel.points("Spanish IPC")[2022.0] == pytest.approx(8.39,
                                                                abs=0.01)
    assert any("never spliced" in s for s in panel.texts())


def test_unemployment_peak_and_the_lfs_hole():
    """EPA: 26.09% in 2013. Eurostat's LFS rate has no ES values before
    2009 — the CSV keeps the hole and the panel's LFS line starts in 2009."""
    t = by_year("macro/unemployment.csv")
    assert float(t[2013]["epa"]) == pytest.approx(26.09, abs=0.01)
    for y in (2006, 2007, 2008):
        assert not (t[y]["estat"] or "").strip(), f"{y}: LFS hole filled"
    panel = plate(SLUG, "plate_economy").panel("Unemployment rate")
    assert min(panel.points("Eurostat LFS")) == 2009
    assert panel.ax.get_xlim()[0] < 2009, "the 2006-08 hole is not visible"
    assert any("26.1% in 2013" in s for s in panel.texts())


# ------------------------------------------------------------- fiscal
def test_the_bailout_year_deficit():
    t = by_year("fiscal/deficit.csv")
    assert float(t[2009]["deficit"]) == pytest.approx(-11.2, abs=0.05)
    assert float(t[2012]["deficit"]) == pytest.approx(-11.5, abs=0.05)
    assert float(t[2007]["deficit"]) > 0, "2006-07 were surpluses"
    panel = plate(SLUG, "plate_fiscal").panel("Net lending")
    assert any("bank bailout" in s for s in panel.texts())
    assert any("last surplus was 2007" in s for s in panel.texts())


def test_the_debt_jump_of_2011_to_2013():
    t = by_year("fiscal/debt.csv")
    assert float(t[2011]["gross_pct_gdp"]) == pytest.approx(69.5, abs=0.05)
    assert float(t[2013]["gross_pct_gdp"]) == pytest.approx(100.0, abs=0.05)
    panel = plate(SLUG, "plate_fiscal").panel("Gross public debt")
    assert any("69.5% to 100.0%" in s for s in panel.texts())


def test_the_interest_panel_is_interest_alone():
    """The tax take is not on the interest slot: a 37%-of-GDP line would
    blow the shared 0-8 scale."""
    panel = plate(SLUG, "plate_fiscal").panel("Interest paid")
    assert max(v for ln in panel.data_lines() for v in ln.get_ydata()) < 8


# ------------------------------------------------------------- trade
def test_trade_shares_of_gdp_are_the_national_accounts_divided():
    """Exports % of GDP = P6 ÷ nominal GDP, both Eurostat, same year."""
    x = col("trade/trade.csv", "exports_eurbn")
    g = col("macro/gdp.csv", "nominal_eurbn")
    panel = plate(SLUG, "plate_trade").panel("Exports and imports")
    pts = panel.points("Exports")
    assert pts[2024.0] == pytest.approx(x[2024] / g[2024] * 100, rel=1e-9)
    assert pts[2024.0] == pytest.approx(37.2, abs=0.1)


def test_the_balance_flipped_in_2011_on_services():
    t = by_year("trade/trade.csv")
    bal = {y: float(r["exports_eurbn"]) - float(r["imports_eurbn"])
           for y, r in t.items() if r["exports_eurbn"]}
    assert bal[2010] < 0 < bal[2011]
    assert bal[2024] == pytest.approx(68.96, abs=0.05)
    for y, r in t.items():
        if r["exports_goods_eurbn"]:
            assert float(r["exports_goods_eurbn"]) + float(
                r["exports_services_eurbn"]) == pytest.approx(
                float(r["exports_eurbn"]), abs=0.02), y
            goods = float(r["exports_goods_eurbn"]) - float(
                r["imports_goods_eurbn"])
            assert goods < 0, f"{y}: the goods account is in deficit"
    panel = plate(SLUG, "plate_trade").panel("Trade balance")
    assert any("since 2011" in s for s in panel.texts())


def test_destinations_are_shares_of_the_world_total():
    t = [r for r in rows("trade/destinations.csv") if r["year"] == "2024"]
    fr = next(r for r in t if r["destination"] == "France")
    assert float(fr["share_pct"]) == pytest.approx(14.85, abs=0.01)
    assert float(fr["exports_eurbn"]) == pytest.approx(58.807, abs=0.01)
    assert sum(float(r["share_pct"]) for r in t) < 100
    panel = plate(SLUG, "plate_trade").panel("Where Spain's goods go")
    assert panel.points("France")[2024.0] == pytest.approx(14.85, abs=0.01)


def test_food_outsells_cars_since_2019():
    shares = {}
    for r in rows("trade/export_products.csv"):
        shares.setdefault(r["product"], {})[int(r["year"])] = float(
            r["share_pct"])
    food, cars = shares["agrifood"], shares["vehicles"]
    assert all(food[y] > cars[y] for y in food if y >= 2019)
    assert food[2018] < cars[2018]
    panel = plate(SLUG, "plate_trade").panel("what Spain sells")
    assert any("since 2019" in s for s in panel.texts())


# ------------------------------------------------------------- markets
def test_the_mro_stays_blank_before_october_2008():
    t = by_year("markets/policy_rate.csv")
    for y in (2006, 2007):
        assert not (t[y]["mro"] or "").strip(), f"{y}: MRO back-filled"
    panel = plate(SLUG, "plate_markets").panel("policy rate")
    assert min(panel.points("Main refinancing")) == 2008
    assert any("8 year-ends below zero" in s for s in panel.texts())


def test_the_2012_yield_spike():
    panel = plate(SLUG, "plate_markets").panel("10-year benchmark")
    assert float(by_year("markets/yield_10y.csv")[2012]["yield_10y"]) == 5.85
    assert any("5.85%" in s for s in panel.texts())


def test_the_euro_index_is_rebased_not_inverted():
    """US$ per euro already rises when the euro strengthens: index 2006 =
    100 by plain rebasing. 2022's 1.0530 against 2006's 1.2556 is 83.9."""
    panel = plate(SLUG, "plate_markets").panel("The euro against")
    idx = {x: y for ln in panel.data_lines()
           for x, y in zip(ln.get_xdata(), ln.get_ydata())}
    assert idx[2006] == pytest.approx(100.0)
    assert idx[2022] == pytest.approx(1.0530 / 1.2556 * 100, abs=0.01)


def test_the_ibex_is_drawn_in_dollars_beside_the_sp500():
    ibex = col("markets/ibex.csv", "close")
    eop = col("markets/eurusd.csv", "eop")
    spx = col("markets/sp500.csv", "close")
    assert ibex[2007] == pytest.approx(15182.30, abs=0.1)
    assert spx[2008] == pytest.approx(903.25, abs=0.01)
    panel = plate(SLUG, "plate_markets").panel("IBEX 35 in US$")
    b = panel.points("IBEX 35, in US$")
    s = panel.points("S&P 500")
    want = ibex[2025] * eop[2025] / (ibex[2006] * eop[2006]) * 100
    assert b[2025.0] == pytest.approx(want, rel=1e-9)
    assert s[2025.0] == pytest.approx(spx[2025] / spx[2006] * 100, rel=1e-9)
    texts = " ".join(panel.texts())
    assert "latest close" in texts and "price indices" in texts


# ------------------------------------------------------------- credit
def test_the_npl_peak_is_december_2013():
    t = by_year("credit/npl.csv")
    assert float(t[2013]["npl_ratio"]) == pytest.approx(13.616, abs=0.01)
    panel = plate(SLUG, "plate_credit").panel("Doubtful loans")
    assert any("13.6%" in s for s in panel.texts())
    assert any("computed here" in s for s in panel.texts())


def test_household_debt_two_measures():
    """BIS % of GDP on the canonical slot; the Banco de España's % of
    disposable income (141% in 2008, annual mean) in its note."""
    assert col("credit/household_credit.csv",
               "hh_credit_pct_gdp_q4")[2009] == pytest.approx(85.0)
    assert col("credit/household_debt.csv",
               "debt_pct_income_avg")[2008] == pytest.approx(140.71, abs=0.1)
    panel = plate(SLUG, "plate_credit").panel("Household debt")
    assert any("141% of disposable income in 2008" in s
               for s in panel.texts())


# ----------------------------------------------------------------- people
def test_the_minimum_wage_is_twelve_month_euros_at_the_average_rate():
    """SMI 2024: €1,134 x 14 / 12 = €1,323, times the 2024 average
    US$ per euro (1.0824)."""
    w = col("social/minimum_wage.csv", "eur_month_jul")
    fx = col("markets/eurusd.csv", "avg")
    assert w[2024] == 1323
    panel = plate(SLUG, "plate_people").panel("Minimum wage")
    pts = {x: y for ln in panel.data_lines()
           for x, y in zip(ln.get_xdata(), ln.get_ydata())}
    assert pts[2024] == pytest.approx(1323 * 1.0824, abs=0.01)
    assert pts[2024] == pytest.approx(w[2024] * fx[2024])


def test_the_gini_axis_is_not_inverted():
    panel = plate(SLUG, "plate_people").panel("Gini")
    lo, hi = panel.ylim()
    assert lo < hi


# ----------------------------------------------------------- demography
def test_vital_statistics_stop_at_the_definitive_year():
    t = by_year("social/demography.csv")
    assert float(t[2024]["births"]) == 318005
    assert float(t[2024]["deaths"]) == 436118
    for c in ("births", "deaths"):
        assert not (t[2025][c] or "").strip(), f"2025 {c} filled"
    panel = plate(SLUG, "plate_demography").panel("Births and deaths")
    assert max(panel.points("Deaths")) == 2024


def test_birth_and_death_rates_are_per_1000_mid_year():
    births = col("social/demography.csv", "births")
    panel = plate(SLUG, "plate_demography").panel("Births and deaths")
    got = panel.points("Births")[2024.0]
    assert got == pytest.approx(births[2024] / MID[2024] * 1000, rel=1e-9)
    assert got != pytest.approx(births[2024] / JAN[2024] * 1000, rel=1e-6)


def test_population_and_the_2012_16_decline():
    vals = col("social/population.csv", "population")
    assert vals[2026] == 49596376
    declines = [y for y in sorted(vals) if y - 1 in vals
                and vals[y] < vals[y - 1]]
    assert declines == [2013, 2014, 2015, 2016]
    panel = plate(SLUG, "plate_demography").panel("Resident population")
    pts = {x: y for ln in panel.data_lines()
           for x, y in zip(ln.get_xdata(), ln.get_ydata())}
    assert pts[2026] == pytest.approx(vals[2026] / vals[2006] * 100)


def test_net_migration_is_never_joined_across_the_seam():
    panel = plate(SLUG, "plate_demography").panel("Natural increase")
    old = panel.points("old method, to 2020")
    new = panel.points("new method, from 2021")
    assert max(old) == 2020 and min(new) == 2021


# ------------------------------------------------------------- security
def test_homicide_rate_is_ecm_over_the_mid_year_population():
    """ECM 'Agresiones (homicidio)': 324 in 2024, over 48,821,936 at
    1 July 2024 = 0.664 per 100,000."""
    hom = col("social/homicides.csv", "ecm_deaths")
    assert hom[2024] == 324 and hom[2008] == 378
    panel = plate(SLUG, "plate_security").panel("Homicide rate")
    got = panel.points("INE death certificates")[2024.0]
    assert got == pytest.approx(324 / 48821936 * 1e5, rel=1e-9)
    assert any("324 deaths" in s for s in panel.texts())
    assert panel.points("UNODC")[2023.0] == pytest.approx(0.69)
    assert panel.ax.get_yscale() == "log"


def test_road_and_suicide_rates_and_the_crossing():
    sui, road = (cause("Suicidio y lesiones autoinfligidas"),
                 cause("Accidentes de tráfico"))
    hom = cause("Agresiones (homicidio)")
    for y in set(sui) & set(road) & set(hom):
        assert sui[y] > hom[y] and road[y] > hom[y], y
    assert road[2007] > sui[2007] and sui[2008] > road[2008]
    p = plate(SLUG, "plate_security")
    r = p.panel("Road traffic deaths").points("INE death certificates")
    assert r[2006.0] == pytest.approx(road[2006] / MID[2006] * 1e5,
                                      rel=1e-9)
    s = p.panel("Suicide rate").points("INE death certificates, crude")
    assert s[2024.0] == pytest.approx(sui[2024] / MID[2024] * 1e5, rel=1e-9)
    lens = p.panel("side by side")
    assert any("2008: suicide passes road deaths" in t for t in lens.texts())
    assert any("HTTP 200" in t for t in lens.texts())


# ------------------------------------------------------------- mortality
def test_covid_certified_deaths_split_identified_from_suspected():
    covid = {r["cause"]: float(r["deaths"])
             for r in rows("social/causes_of_death.csv")
             if int(r["year"]) == 2020 and r["cause"].startswith("COVID-19")}
    assert covid["COVID-19. Virus identificado"] == 60358
    assert covid["COVID-19. Virus no identificado (sospechoso)"] == 14481
    panel = plate(SLUG, "plate_mortality").panel("COVID-19 as the certified")
    tops = panel.bars()
    assert max(tops) == pytest.approx((60358 + 14481) / MID[2020] * 1e5,
                                      rel=1e-9)


def test_excess_deaths_against_the_2015_19_mean():
    d = col("social/demography.csv", "deaths")
    base = sum(d[y] for y in range(2015, 2020)) / 5
    panel = plate(SLUG, "plate_mortality").panel("Deaths above")
    heights = [p.get_height() for p in panel.ax.patches
               if p.get_data_transform() is panel.ax.transData]
    assert max(heights) == pytest.approx((d[2020] / base - 1) * 100)
    assert any("+17.3%" in s for s in panel.texts())


def test_the_two_big_killers_crossed_only_in_2024():
    tum = cause("II.Tumores")
    cir = cause("IX.Enfermedades del sistema circulatorio")
    assert tum[2024] > cir[2024] and tum[2023] < cir[2023]
    assert tum[2024] == 115578 and cir[2024] == 113620
    panel = plate(SLUG, "plate_mortality").panel("two big killers")
    assert any("only in 2024" in s for s in panel.texts())


# ------------------------------------------------------------- migration
def test_the_2021_seam_is_published_on_both_methodologies():
    """INE counts 2021 immigration as 528,856 on the EM and 887,960 on the
    EMCR. Eurostat carries EM to 2020 and EMCR from 2021, so the plate
    splits the Eurostat line there rather than drawing across the seam."""
    em = by_year("migration/migration_flows_ine.csv")
    emcr = by_year("migration/migration_flows_emcr_ine.csv")
    assert float(em[2021]["immigration"]) == 528856
    assert float(emcr[2021]["immigration_emcr"]) == 887960
    for y in (2022, 2023, 2024):
        assert not (em[y]["immigration"] or "").strip(), \
            f"{y}: EM spliced past its end"
    eu = by_year("migration/immigration.csv")
    assert float(eu[2020]["by_citizenship_total"]) == 467918
    assert float(eu[2021]["by_citizenship_total"]) == 887960
    panel = plate(SLUG, "plate_migration").panel("two methods")
    for flow in ("Immigration", "Emigration"):
        old = panel.points(f"{flow}, Eurostat — EM method")
        new = panel.points(f"{flow}, Eurostat — EMCR method")
        assert max(old) == 2020 and min(new) == 2021, flow
    ine = panel.points("INE — old method")
    assert sorted(ine) == [2020.0, 2021.0]
    assert ine[2021.0] == pytest.approx(528856 / MID[2021] * 1000, rel=1e-9)
    assert any("528,856" in s and "887,960" in s for s in panel.texts())


def test_flows_are_per_1000_mid_year():
    imm = col("migration/immigration.csv", "by_citizenship_total")
    panel = plate(SLUG, "plate_migration").panel("two methods")
    got = panel.points("Immigration, Eurostat — EMCR")[2024.0]
    assert got == pytest.approx(imm[2024] / MID[2024] * 1000, rel=1e-9)
    assert got == pytest.approx(26.4, abs=0.05)


def test_the_foreign_born_share_and_the_naturalisation_gap():
    t = by_year("migration/stock.csv")
    r = t[2025]
    born = (float(r["by_birth_total"]) - float(r["by_birth_national"])) \
        / float(r["by_birth_total"]) * 100
    assert born == pytest.approx(19.3, abs=0.05)
    gap = float(r["by_citizenship_national"]) - float(r["by_birth_national"])
    assert gap == pytest.approx(2.55e6, abs=1e5)
    panel = plate(SLUG, "plate_migration").panel("Born abroad")
    pairs = panel.paired("born abroad", "foreign citizens")
    assert len(pairs) >= 15
    assert all(b > c for _, b, c in pairs), "born abroad below citizens"
    assert panel.points("born abroad")[2025.0] == pytest.approx(born)


def test_asylums_numbers_stay_separate():
    t = by_year("migration/asylum.csv")
    assert float(t[2024]["applications"]) == 167750
    assert float(t[2024]["positive"]) == 50700
    panel = plate(SLUG, "plate_migration").panel("paperwork")
    pos = panel.points("of which positive")
    dec = panel.points("first-instance asylum decisions")
    shared = [y for y in pos if y in dec]
    assert shared and all(pos[y] <= dec[y] for y in shared)


# ---------------------------------------------------------------- world
def test_the_comparables_layer():
    assert float(by_year("international/hdi.csv")[2023]["hdi"]) == 0.918
    cpi = col("international/cpi.csv", "score")
    assert (cpi[2012], cpi[2024], cpi[2025]) == (65, 56, 55)
    p = plate(SLUG, "plate_world")
    assert any("0.918" in s for s in p.panel("Human Development").texts())
    drawn = {x: y for ln in p.panel("Corruption").data_lines()
             for x, y in zip(ln.get_xdata(), ln.get_ydata())}
    assert min(drawn) == 2012 and drawn[2025] == 55


# ----------------------------------------------------------- clipping
@pytest.mark.parametrize("name", ["plate_economy", "plate_fiscal",
                                  "plate_spending", "plate_trade",
                                  "plate_markets", "plate_people",
                                  "plate_world", "plate_demography",
                                  "plate_security", "plate_mortality",
                                  "plate_credit", "plate_migration"])
def test_nothing_is_clipped(name):
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped(slack=1e-6)
