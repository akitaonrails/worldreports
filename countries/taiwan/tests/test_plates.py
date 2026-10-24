"""The facts Taiwan's plates assert.

Each test states a claim a plate makes about the country's own data, so a
refetch that invalidates the claim fails loudly instead of quietly changing
a published chart. The conversions pinned here are the ones that actually
broke on the first pass: the trade gap label dividing US$ thousands twice
and printing a five-figure billion; MOF's "social security & pension"
SUBTOTAL being stacked beside the three items it already contains; the
CBC monthly CPI (min -0.25%) spliced onto DGBAS year-averages (min -0.88%);
and developer building-loans read as household debt.

Park decisions get pinned too: remaining pending slots must stay pending with
no invented line, while newly staged official series must draw their values.
"""

from __future__ import annotations

import csv

import pytest

from core.country import Country
from core import sitebuild
from tests.probe import plate

SLUG = "taiwan"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8-sig", newline="") as fh:
        return [r for r in csv.DictReader(fh) if not r.get("year", "").startswith("#")]


def num(r: dict, key: str) -> float:
    v = (r.get(key) or "").strip()
    return float(v) if v else float("nan")


def by_year(rel: str, key: str = "year") -> dict[int, dict]:
    return {int(r[key]): r for r in rows(rel)}


def texts(plate_name: str, panel: str) -> list[str]:
    return plate(SLUG, plate_name).panel(panel).texts()


def is_pending(plate_name: str, panel: str) -> None:
    """A parked slot shows the pending marker and draws no data line."""
    p = plate(SLUG, plate_name).panel(panel)
    joined = " ".join(p.texts()).lower()
    assert "pending" in joined, f"{plate_name}/{panel} no longer says pending"
    assert not p.lines(), f"{plate_name}/{panel} grew an un-sourced line"


# ------------------------------------------------------------------- economy
def test_the_gfc_band_covers_only_negative_quarters():
    """The shaded band on the growth panel claims 2009. If a refetch turns
    any covered quarter positive the band becomes a lie."""
    q = rows("economy/gdp_growth_quarterly.csv")
    ys = {int(r["year"]): r for r in q if r["quarter"] != "Q4"}
    y09 = {r["quarter"]: num(r, "gdp_growth_yoy_pct") for r in q if int(r["year"]) == 2009}
    assert all(y09[k] < 0 for k in ("Q1", "Q2", "Q3"))
    assert y09["Q1"] == pytest.approx(-7.87) and y09["Q4"] > 8
    assert "-1.6%" in " ".join(texts("plate_economy", "Real GDP growth"))


def test_two_inflation_publishers_are_never_spliced():
    """DGBAS annual-average y/y bottoms at -0.9% in 2009; the CBC period
    series bottoms at -0.25% in the same year. A plate that splices them
    publishes a number neither publisher printed."""
    dgbas = by_year("economy/cpi.csv")
    cbc = by_year("economy/cpi_yoy_cbc.csv")
    assert num(dgbas[2009], "cpi_inflation_pct") == pytest.approx(-0.88)
    assert min(num(r, "cpi_yoy_pct") for r in cbc.values()) == pytest.approx(-0.25)
    drawn = plate(SLUG, "plate_economy").panel("Consumer price inflation")
    d = drawn.points("DGBAS")
    assert min(d.values()) == pytest.approx(-0.88, abs=0.01), "annual line must be DGBAS"
    c = drawn.points("CBC")
    assert min(c.values()) == pytest.approx(-0.25, abs=0.01), "period line must be CBC"
    assert 2009 in d and 2009 in c and d[2009] != c[2009]


def test_gdp_per_person_is_the_published_column():
    g = by_year("economy/gdp.csv")
    assert num(g[2025], "gdp_per_capita_usd") == 39515
    assert "39,515" in " ".join(texts("plate_economy", "GDP per person"))


def test_unemployment_uses_dgbas_total_annual_rate():
    data = by_year("economy/unemployment.csv")
    drawn = plate(SLUG, "plate_economy").panel("Unemployment").points("DGBAS total")
    assert num(data[2009], "unemployment_rate_pct") == 5.85
    assert drawn[2009.0] == pytest.approx(5.85)
    assert drawn[2025.0] == pytest.approx(3.35)


# -------------------------------------------------------------------- fiscal
def test_revenue_and_expenditure_endpoints():
    b = by_year("fiscal/budget.csv")
    rev = plate(SLUG, "plate_fiscal").panel("Revenue and expenditure").points("Revenue")
    exp = plate(SLUG, "plate_fiscal").panel("Revenue and expenditure").points("Expenditure")
    assert rev[2006.0] == pytest.approx(num(b[2006], "revenue_pct_gdp"))
    assert exp[2006.0] == pytest.approx(num(b[2006], "expenditure_pct_gdp"))
    assert max(rev.values()) < 18, "the % of GDP lines must not land on a nominal scale"


def test_debt_peak_and_descent():
    d = by_year("fiscal/debt_central.csv")
    drawn = plate(SLUG, "plate_fiscal").panel("Gross debt").points("Central government")
    pk = max(drawn.items(), key=lambda t: t[1])
    assert pk == (2012.0, pytest.approx(34.0))
    assert drawn[2025.0] == pytest.approx(num(d[2025], "debt_central_pct_gdp"))


def test_primary_balance_arithmetic():
    """primary = overall balance + debt-category outlays, each once in % of
    GDP: the NTD thousands/millions factor (_TH/_MN) must not drift."""
    b = by_year("fiscal/budget.csv")
    s = by_year("spending/function.csv")
    g = by_year("economy/gdp.csv")
    drawn = plate(SLUG, "plate_fiscal").panel("Overall and primary").points("Primary balance")
    for y in (2009, 2015, 2025):
        want = (num(b[y], "balance_pct_gdp")
                + num(s[y], "spending_debt_service") * 1_000.0
                / (num(g[y], "gdp_nominal_ntd_mn") * 1_000_000.0) * 100.0)
        assert drawn[float(y)] == pytest.approx(want, abs=0.05), y
    assert min(float(r["balance_pct_gdp"]) for r in b.values()) == -4.3


def test_debt_service_ratio_unit():
    s = by_year("spending/function.csv")
    g = by_year("economy/gdp.csv")
    drawn = plate(SLUG, "plate_fiscal").panel("Interest paid").points("Debt-category")
    assert drawn[2006.0] == pytest.approx(1.1, abs=0.05)
    assert drawn[2025.0] == pytest.approx(
        num(s[2025], "spending_debt_service") * 1_000.0
        / (num(g[2025], "gdp_nominal_ntd_mn") * 1_000_000.0) * 100.0, abs=0.01)


# ------------------------------------------------------------------ spending
def test_the_subtotal_is_never_stacked_with_its_own_parts():
    """function.csv's social-security column is a subtotal over welfare,
    pensions, and community & environment; stacking subtotal + community
    prints 14.8% where the accounts say 14.5."""
    s = by_year("spending/function.csv")
    g = by_year("economy/gdp.csv")
    for y in s.values():
        assert num(y, "spending_social_security_pension_subtotal") == pytest.approx(
            num(y, "spending_social_welfare") + num(y, "spending_pension")
            + num(y, "spending_community_environment"))
        groups = ("spending_general_affairs", "spending_defence",
                  "spending_education_sci_culture", "spending_economic_development",
                  "spending_social_welfare", "spending_pension",
                  "spending_community_environment", "spending_debt_service",
                  "spending_other")
        assert sum(num(y, k) for k in groups) == pytest.approx(num(y, "spending_total"))
    t = " ".join(texts("plate_spending", "Spending by function"))
    assert "14.5% of GDP (2025)" in t and "14.8" not in t


def test_social_protection_pair_adds_to_total():
    drawn = plate(SLUG, "plate_spending").panel("Social protection")
    rest = drawn.points("Everything else")
    soc = drawn.points("Social security")
    s = by_year("spending/function.csv")
    g = by_year("economy/gdp.csv")
    for y in (2006, 2015, 2025):
        want = num(s[y], "spending_total") * 1_000.0 / (num(g[y], "gdp_nominal_ntd_mn") * 1e6) * 100
        assert rest[float(y)] + soc[float(y)] == pytest.approx(want, abs=0.05)


def _spending_card() -> dict[str, dict]:
    """The spending chapter's card figures, by English label."""
    for ch in sitebuild.chapters_for(Country.load(SLUG)):
        stats = {s["label"]["en"]: s for s in ch["stats"]}
        if "Total outlays (final accounts)" in stats:
            return stats
    raise AssertionError("no card carries 'Total outlays (final accounts)'")


def test_spending_card_shares_use_the_plate_unit_factor():
    """The card once inverted thousand-NTD ÷ million-NTD and printed
    14,450,760.0% of GDP; it must agree with the plate's × 1e3 ÷ 1e6."""
    stats = _spending_card()
    spend = by_year("spending/function.csv")
    gdp = by_year("economy/gdp.csv")
    for label, col in (("Total outlays (final accounts)", "spending_total"),
                       ("Social security & pensions",
                        "spending_social_security_pension_subtotal")):
        s = stats[label]
        y = s["year"]
        assert y in spend and y in gdp, f"{label}: {y} missing from a CSV"
        want = num(spend[y], col) * 1e3 / (num(gdp[y], "gdp_nominal_ntd_mn") * 1e6) * 100
        assert 0 < want < 100
        assert s["value"]["en"] == f"{want:,.1f}% GDP"


def test_spending_card_outlays_match_the_publishers_own_share():
    """An independent check on the unit factor: MOF i2101 publishes its own
    expenditure % of GDP (14.5 in 2025). The card divides by DGBAS GDP and
    MOF rounds against its own, so they agree to within a rounding step,
    not to the printed digit."""
    s = _spending_card()["Total outlays (final accounts)"]
    y = s["year"]
    budget = by_year("fiscal/budget.csv")
    assert y in budget, f"card year {y} is not in fiscal/budget.csv yet"
    card = float(s["value"]["en"].removesuffix("% GDP"))
    assert card == pytest.approx(num(budget[y], "expenditure_pct_gdp"), abs=0.15)


# --------------------------------------------------------------------- trade
def test_goods_only_data_do_not_occupy_goods_and_services_slots():
    is_pending("plate_trade", "Exports and imports, goods and services")
    is_pending("plate_trade", "Trade balance, goods and services")


def test_the_twice_counted_lens_keeps_both_counts_apart():
    """Customs (trade/goods) and BoP (world/bop_goods) must stay two lines;
    the first draft printed customs minus customs and called it the gap."""
    gd = by_year("trade/goods.csv")
    bop = by_year("world/bop_goods.csv")
    drawn = plate(SLUG, "plate_trade").panel("counted twice")
    cu = drawn.points("Customs exports")
    bo = drawn.points("BoP exports")
    assert cu[2025.0] == pytest.approx(num(gd[2025], "exports_usd_thousands") / 1e6, rel=1e-3)
    assert bo[2025.0] == pytest.approx(num(bop[2025], "bop_goods_exports_usd_mn") / 1e3, rel=1e-3)
    assert cu[2025.0] != bo[2025.0]


def test_partner_mix_customs_basis():
    pp = rows("trade/partners.csv")
    tot = {}
    for r in pp:
        tot[int(r["year"])] = tot.get(int(r["year"]), 0.0)
    gd = by_year("trade/goods.csv")
    base = {y: num(r, "exports_usd_thousands") for y, r in gd.items()}
    def share(y, partner):
        return sum(num(r, "exports_usd_thousands") for r in pp
                   if int(r["year"]) == y and r["partner"] == partner) / base[y] * 100
    drawn = plate(SLUG, "plate_trade").panel("Top export destinations")
    us = drawn.points("United States")
    ch = drawn.points("Mainland China")
    assert us[2025.0] == pytest.approx(share(2025, "United States"), abs=0.1)
    assert ch[2025.0] == pytest.approx(share(2025, "China_mainland"), abs=0.1)
    assert ch[2025.0] < 0.55 * ch[2020.0], "the halving claim in the note"
    assert us[2025.0] > 30 and ch[2025.0] < 17


# -------------------------------------------------------------------- credit
def test_consumer_credit_peak_is_2006_not_the_gfc():
    """Consumer loans ÷ GDP peaked in 2006, before the reference window
    opens in 2008 elsewhere; the credit window starts at 2006 so the peak is
    visible and no note may blame the GFC for it."""
    hc = by_year("credit/household_credit.csv")
    g = by_year("economy/gdp.csv")
    def pct(y):
        return num(hc[y], "consumer_loans_ntd_mn") / num(g[y], "gdp_nominal_ntd_mn") * 100
    drawn = plate(SLUG, "plate_credit").panel("Household debt").points("Consumer loans")
    pk = max(drawn.items(), key=lambda t: t[1])
    assert pk == (2006.0, pytest.approx(51.9, abs=0.1))
    assert drawn[2025.0] == pytest.approx(47.1, abs=0.1)
    assert pct(2006) == max(pct(y) for y in hc)


def test_building_loans_are_developer_credit():
    hc = by_year("credit/household_credit.csv")
    g = by_year("economy/gdp.csv")
    def pct(y):
        return num(hc[y], "building_loans_ntd_mn") / num(g[y], "gdp_nominal_ntd_mn") * 100
    assert pct(2023) == pytest.approx(14.0, abs=0.1)
    assert pct(2006) == pytest.approx(6.5, abs=0.1)
    assert "14.0% in 2023" in " ".join(texts("plate_credit", "developers"))


def test_npl_and_policy_rate_points():
    npl = by_year("credit/npl.csv")
    pol = by_year("markets/policy_rate.csv")
    assert num(npl[2006], "bank_npl_ratio_pct") == 2.13
    assert num(npl[2025], "bank_npl_ratio_pct") == 0.15
    drawn = plate(SLUG, "plate_markets").panel("Policy rate").points("rediscount")
    assert max(drawn.values()) == pytest.approx(3.375) and drawn[2025.0] == pytest.approx(2.0)


def test_new_housing_rate_is_compared_with_policy_without_splicing():
    housing = by_year("credit/new_housing_rate.csv")
    panel = plate(SLUG, "plate_credit").panel("Household lending rate")
    assert panel.points("Five-bank")[2025.0] == pytest.approx(
        num(housing[2025], "new_housing_loan_rate_pct"))
    assert panel.points("rediscount")[2025.0] == pytest.approx(2.0)
    assert panel.points("Five-bank")[2020.0] == pytest.approx(1.423)


# ------------------------------------------------------------------- markets
def test_taiex_average_and_year_end_are_different_series():
    """stock_index_avg and stock_index_yearend are separate CSVs; a plate
    that mixes them makes the note's '364 vs 385' impossible."""
    sa = by_year("markets/stock_index_avg.csv")
    se = by_year("markets/stock_index_yearend.csv")
    g = by_year("economy/gdp.csv")
    def to_usd_idx(v, y, v06, f06):
        return (v / num(g[y], "avg_fx_ntd_per_usd")) / (v06 / f06) * 100
    avg = plate(SLUG, "plate_markets").panel("Main equity index").points("annual average")
    want = to_usd_idx(num(sa[2025], "taiex_annual_average"), 2025,
                      num(sa[2006], "taiex_annual_average"), num(g[2006], "avg_fx_ntd_per_usd"))
    assert avg[2025.0] == pytest.approx(want, abs=1.0)
    ye = to_usd_idx(num(se[2025], "close"), 2025, num(se[2006], "close"), num(g[2006], "avg_fx_ntd_per_usd"))
    assert ye != pytest.approx(want, abs=1.0), "average and close must not collapse onto each other"
    t = " ".join(texts("plate_markets", "Main equity index"))
    assert "364" in t and "385" in t


def test_fx_index_up_is_stronger():
    fx = by_year("markets/usdtwd.csv")
    base = num(fx[2006], "usd_twd_interbank_annual_mean")
    idx = {y: base / num(r, "usd_twd_interbank_annual_mean") * 100 for y, r in fx.items()}
    pk = max(idx.items(), key=lambda t: t[1])
    assert pk == (2021, pytest.approx(116.3, abs=0.2))
    assert "2021: 116" in " ".join(texts("plate_markets", "Currency against"))


def test_bond_yield_stays_parked():
    is_pending("plate_markets", "bond yield")


# ---------------------------------------------------------------- demography
def test_population_peaks_2019_and_declines():
    pop = by_year("demography/population.csv")
    pk = max((int(r["population"]), y) for y, r in pop.items())
    assert pk == (23596027, 2019)
    assert int(pop[2025]["population"]) < pk[0]
    t = " ".join(texts("plate_demography", "Population (index"))
    assert "23,596,027" in t and "23.3M" in t


def test_births_are_walled_not_invented():
    """The birth-death panel draws only deaths; the MOI register sits behind
    a wall, and inventing a births line is the failure mode pinned here."""
    t = " ".join(texts("plate_demography", "Crude birth and death"))
    assert "deaths only" in t.lower()
    drawn = plate(SLUG, "plate_demography").panel("Crude birth and death")
    assert len(drawn.lines()) == 1 and "Deaths" in next(iter(drawn.lines()))
    is_pending("plate_demography", "Natural increase")
    is_pending("plate_demography", "Total fertility")


# ------------------------------------------------------------------ mortality
def test_crude_death_rate_divides_by_population_once():
    mo = by_year("mortality/causes_of_death.csv")
    pop = by_year("demography/population.csv")
    drawn = plate(SLUG, "plate_mortality").panel("Crude death rate").points("Registrations")
    for y in (2022, 2025):
        want = num(mo[y], "deaths_all_cause") / int(pop[y]["population"]) * 1000
        assert drawn[float(y)] == pytest.approx(want, abs=0.02), y
    assert drawn[2022.0] == pytest.approx(8.94, abs=0.02)


def test_excess_deaths_counted_against_2015_2019():
    mo = by_year("mortality/causes_of_death.csv")
    base = sum(num(mo[y], "deaths_all_cause") for y in range(2015, 2020)) / 5
    peak = max((num(mo[y], "deaths_all_cause") / base - 1) * 100 for y in range(2020, 2026))
    assert peak == pytest.approx(21.7, abs=0.1)
    assert int(base) == 171226
    t = " ".join(texts("plate_mortality", "Excess deaths"))
    assert "+21.7%" in t and "171,226" in t


def test_the_killers_lens_per_100k():
    mo = by_year("mortality/causes_of_death.csv")
    pop = by_year("demography/population.csv")
    drawn = plate(SLUG, "plate_mortality").panel("killers that grew")
    for col, name in (("deaths_cancer", "Cancer"), ("deaths_heart", "Heart"),
                      ("deaths_pneumonia", "Pneumonia")):
        want = num(mo[2025], col) / int(pop[2025]["population"]) * 1e5
        assert drawn.points(name)[2025.0] == pytest.approx(want, abs=1.0)


def test_covid_cause_line_stays_parked():
    is_pending("plate_mortality", "COVID-19 deaths")


# ------------------------------------------------------------------ security
def test_suicide_floor_and_current():
    mo = by_year("mortality/causes_of_death.csv")
    pop = by_year("demography/population.csv")
    drawn = plate(SLUG, "plate_security").panel("Suicide rate").points("Certificates")
    lo = min(drawn.items(), key=lambda t: t[1])
    assert lo[0] == 2011.0 and lo[1] == pytest.approx(15.1, abs=0.05)
    assert drawn[2025.0] == pytest.approx(num(mo[2025], "deaths_suicide") / int(pop[2025]["population"]) * 1e5, abs=0.05)
    assert "15.1 in 2011" in " ".join(texts("plate_security", "Suicide rate"))


def test_accident_lens_per_100k():
    mo = by_year("mortality/causes_of_death.csv")
    pop = by_year("demography/population.csv")
    want = num(mo[2009], "deaths_accidents") / int(pop[2009]["population"]) * 1e5
    assert want == pytest.approx(31.9, abs=0.1)
    assert "31.9 in 2009" in " ".join(texts("plate_security", "accidental deaths"))


def test_homicide_and_road_deaths_stay_parked():
    """The NPA series is walled; road deaths stay out of a per-100k panel
    rather than being divided by an unstated denominator."""
    is_pending("plate_security", "Homicide")
    is_pending("plate_security", "Road traffic deaths")


# --------------------------------------------------------------------- world
def test_gdp_and_reserves_us_dollar_columns():
    g = by_year("economy/gdp.csv")
    rv = by_year("world/reserves.csv")
    assert num(g[2025], "gdp_nominal_usd_mn") / 1000 == pytest.approx(922.45, abs=0.01)
    assert num(rv[2025], "fx_reserves_usd_mn") / 1000 == pytest.approx(602.55, abs=0.1)
    t = " ".join(texts("plate_world", "GDP at current"))
    assert "US$922bn" in t
    assert "2025: US$603bn" in " ".join(texts("plate_world", "Official reserves"))


def test_homepage_goods_balance_converts_usd_thousands_to_billions():
    """Homepage summaries must not label the MOF's raw thousands as bn."""
    country = Country.load(SLUG)
    headline = sitebuild.headline_for(country)
    trade = next(ch for ch in sitebuild.chapters_for(country)
                 if ch["topic"] == "trade")
    headline_balance = next(s for s in headline
                            if s["label"]["en"] == "Trade balance, goods")
    card_balance = next(s for s in trade["stats"]
                        if s["label"]["en"] == "Goods surplus")
    assert headline_balance["value"]["en"] == "US$ 155bn"
    assert card_balance["value"]["en"] == "US$ 155bn"


def test_hdi_absent_but_ti_cpi_is_drawn():
    is_pending("plate_world", "Human Development")
    cpi = by_year("world/corruption.csv")
    drawn = plate(SLUG, "plate_world").panel("Corruption Perceptions").points("Taiwan")
    assert num(cpi[2012], "cpi_score") == 61
    assert drawn[2025.0] == pytest.approx(68)


# -------------------------------------------------------------------- people
def test_people_definitions_and_wage_conversion():
    g = by_year("people/gini.csv")
    p = by_year("people/poverty.csv")
    w = by_year("people/minimum_wage.csv")
    fx = by_year("economy/gdp.csv")
    assert num(g[2025], "gini_points") == 34.1
    assert num(g[2025], "quintile_ratio") == 6.17
    assert num(p[2024], "relative_poverty_pct") == 7.57
    assert num(w[2025], "monthly_usd_at_avg_fx") == pytest.approx(
        num(w[2025], "monthly_ntd_calendar_average")
        / num(fx[2025], "avg_fx_ntd_per_usd"), abs=0.01)
    drawn = plate(SLUG, "plate_people")
    assert drawn.panel("Gini").points("DGBAS")[2025.0] == pytest.approx(34.1)
    assert drawn.panel("minimum wage").points("Calendar-average")[2025.0] == pytest.approx(916.64)


# ----------------------------------------------------------------- migration
def test_registration_flows_are_components_not_border_trips():
    f = by_year("migration/registration_flows.csv")
    for year, expected in {2018: 9309, 2021: -155696,
                           2023: 225980, 2024: 47613}.items():
        assert num(f[year], "registered_net") == expected
        assert (num(f[year], "registered_immigration")
                - num(f[year], "registered_emigration")) == expected


def test_arc_stock_is_not_drawn_as_foreign_born():
    is_pending("plate_migration", "Foreign-born share")
    nia = by_year("migration/foreign_residents.csv")
    assert num(nia[2025], "arc_foreign_residents_dec") == 1028945
    assert num(nia[2025], "foreign_labour_dec") == 751806
    lens = plate(SLUG, "plate_migration").panel("valid ARC")
    assert lens.points("ARC residents")[2025.0] == pytest.approx(1.028945)
    assert lens.points("foreign labour")[2025.0] == pytest.approx(0.751806)


# -------------------------------------------------------------- global rules
@pytest.mark.parametrize("panel_slug", [
    "plate_economy", "plate_fiscal", "plate_trade", "plate_credit",
    "plate_spending", "plate_demography", "plate_security",
    "plate_mortality", "plate_markets", "plate_world", "plate_people",
    "plate_migration"])
def test_nothing_is_clipped(panel_slug):
    for p in plate(SLUG, panel_slug).panels():
        p.nothing_is_clipped()
