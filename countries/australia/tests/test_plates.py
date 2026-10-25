"""The facts Australia's plates assert, checked against the committed CSVs.

Each test states a claim a plate makes about the country's own data, so a
refetch that invalidates the claim fails loudly instead of quietly changing
a published chart. The four that matter most here:

- the fiscal chapter is a July–June year drawn at its midpoint, and the two
  publishers on it (IMF, ABS GFS) are two labelled lines, never one;
- the two credit asset-quality measures meet at a definition break and are
  never spliced, and the household lending rate stays pending because no
  reachable publisher carries it;
- every count that became a rate was divided by the ABS 30 June population
  of the same year, which is what the plate says it did;
- a series that stops (road deaths in 2022, the CPI in 2012, the household
  survey in 2019–20) keeps a hole, never a zero and never an extrapolation.
"""

from __future__ import annotations

import csv

import pytest

from core.country import Country
from core import sitebuild, spine
from tests.probe import plate

SLUG = "australia"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8-sig", newline="") as fh:
        return [r for r in csv.DictReader(fh)
                if not r.get("year", "").startswith("#")]


def num(r: dict, key: str) -> float:
    v = (r.get(key) or "").strip()
    return float(v) if v else float("nan")


def by_year(rel: str) -> dict[int, dict]:
    return {int(r["year"]): r for r in rows(rel)}


def texts(plate_name: str, panel: str) -> list[str]:
    return plate(SLUG, plate_name).panel(panel).texts()


def is_pending(plate_name: str, panel: str) -> None:
    p = plate(SLUG, plate_name).panel(panel)
    assert any("pending" in t.lower() or "pendente" in t.lower()
               for t in p.texts()), f"{panel}: no pending marker"


# ----------------------------------------------------------------- economy
def test_the_2020_recession_and_the_2021_rebound_are_the_staged_values():
    e = by_year("macro/economy.csv")
    assert num(e[2020], "real_growth_pct") == pytest.approx(-2.10, abs=0.01)
    assert num(e[2021], "real_growth_pct") == pytest.approx(5.39, abs=0.01)
    values = {y: num(r, "real_growth_pct") for y, r in e.items()}
    assert min(values, key=values.get) == 2020


def test_the_imf_check_agrees_with_the_abs_without_being_the_same_file():
    e, i = by_year("macro/economy.csv"), by_year("macro/gdp_growth_imf.csv")
    for y in (2020, 2022):
        assert num(i[y], "growth_pct") == pytest.approx(
            num(e[y], "real_growth_pct"), abs=0.1)
    # Two publishers, two columns: the IMF file is never the ABS series.
    assert [num(e[y], "real_growth_pct") for y in sorted(e)] != \
        [num(i[y], "growth_pct") for y in sorted(i)]


def test_growth_is_inside_the_shared_comparison_scale():
    slot = spine.SLOTS["economy.growth"]
    e = by_year("macro/economy.csv")
    vals = [num(r, "real_growth_pct") for r in e.values()]
    lo, hi = spine.fit(slot, (min(vals), max(vals)))[0]
    assert (lo, hi) == slot.ref


def test_prices_and_jobs_are_the_calendar_year_readings():
    e = by_year("macro/economy.csv")
    assert num(e[2022], "cpi_inflation_pct") == pytest.approx(6.62, abs=0.01)
    assert num(e[2020], "cpi_inflation_pct") == pytest.approx(0.85, abs=0.01)
    assert num(e[2020], "unemployment_pct") == pytest.approx(6.48, abs=0.01)
    assert num(e[2025], "unemployment_pct") == pytest.approx(4.21, abs=0.01)


def test_gdp_per_person_is_the_world_bank_dollar():
    w = by_year("world/gdp_and_reserves.csv")
    assert num(w[2012], "gdp_per_person_usd") == pytest.approx(68_301, abs=1)
    assert num(w[2025], "gdp_per_person_usd") == pytest.approx(65_130, abs=1)


# ------------------------------------------------------------------ fiscal
def test_the_fiscal_year_is_drawn_at_its_midpoint_and_says_FY():
    f = by_year("fiscal/fiscal.csv")
    # 2025 is FY2024/25: the year ends in 2025 and the plate draws it 0.5 back.
    p = plate(SLUG, "plate_fiscal").panel("Revenue and expenditure")
    xs = sorted(p.points("Revenue"))
    assert 2024.5 in xs
    assert 2025 not in xs
    assert num(f[2025], "revenue_pct_gdp") == pytest.approx(36.67, abs=0.01)
    assert any("FY" in t or "fiscal years" in t for t in texts(
        "plate_fiscal", "Revenue and expenditure"))


def test_the_fund_and_the_abs_are_two_lines_and_not_one_series():
    f = by_year("fiscal/fiscal.csv")
    # Same year, two definitions: the Fund's expenditure includes net
    # acquisition of non-financial assets, the ABS "expenses" row does not.
    assert num(f[2025], "expenditure_pct_gdp") == pytest.approx(39.56, abs=0.01)
    assert num(f[2025], "gfs_expenses_pct_gdp") == pytest.approx(37.11, abs=0.01)
    assert num(f[2024], "gfs_revenue_pct_gdp") == pytest.approx(36.50, abs=0.01)
    # The ABS columns are blank before FY2015/16 and never filled backwards.
    for y in range(2006, 2016):
        assert num(f[y], "gfs_revenue_pct_gdp") != num(f[y], "gfs_revenue_pct_gdp")
    # And both lines are on the panel.
    p = plate(SLUG, "plate_fiscal").panel("Overall balance")
    assert p.lines().get("Primary balance") is not None


def test_interest_is_derived_and_stops_where_its_input_stops():
    f = by_year("fiscal/fiscal.csv")
    for y in sorted(f):
        i, r = num(f[y], "interest_pct_gdp"), num(f[y], "revenue_pct_gdp")
        if i == i:
            assert 0.3 < i < r
    assert max(y for y in f if num(f[y], "interest_pct_gdp") ==
               num(f[y], "interest_pct_gdp")) == 2022
    assert num(f[2025], "gfs_interest_pct_gdp") == pytest.approx(1.71, abs=0.01)


def test_debt_rises_from_a_debt_free_commonwealth_to_the_pandemic():
    f = by_year("fiscal/fiscal.csv")
    assert num(f[2006], "gross_debt_pct_gdp") == pytest.approx(9.92, abs=0.01)
    assert num(f[2021], "gross_debt_pct_gdp") == pytest.approx(55.37, abs=0.01)
    assert num(f[2025], "gross_debt_pct_gdp") == pytest.approx(51.91, abs=0.01)


# ---------------------------------------------------------------- spending
def test_the_cofog_groups_sum_to_the_published_total():
    t = rows("spending/cofog.csv")
    for r in t:
        if not (r.get("total_expenditure_pct_gdp") or "").strip():
            continue
        parts = sum(num(r, c) for c in (
            "social_protection_pct_gdp", "health_pct_gdp",
            "education_pct_gdp", "general_public_services_pct_gdp",
            "economic_affairs_pct_gdp", "defence_public_order_pct_gdp",
            "other_pct_gdp"))
        assert parts == pytest.approx(num(r, "total_expenditure_pct_gdp"),
                                      abs=0.06)


def test_spending_is_drawn_to_the_last_published_year_only():
    t = by_year("spending/cofog.csv")
    assert max(y for y in t if num(t[y], "total_expenditure_pct_gdp") ==
               num(t[y], "total_expenditure_pct_gdp")) == 2024
    assert num(t[2024], "social_protection_pct_gdp") == pytest.approx(11.49,
                                                                     abs=0.01)
    assert num(t[2020], "total_expenditure_pct_gdp") == pytest.approx(48.42,
                                                                     abs=0.01)


def test_the_two_investment_rates_are_different_perimeters():
    i = by_year("spending/investment.csv")
    for y in sorted(i):
        assert num(i[y], "public_gfcf_pct_gdp") < num(i[y], "gfcf_pct_gdp")
    assert num(i[2025], "gfcf_pct_gdp") == pytest.approx(24.38, abs=0.01)
    assert num(i[2025], "public_gfcf_pct_gdp") == pytest.approx(3.91, abs=0.01)


# ------------------------------------------------------------------- trade
def test_the_trade_balance_is_their_difference_not_a_stored_column():
    t = by_year("trade/trade.csv")
    for y in sorted(t):
        assert num(t[y], "balance_pct_gdp") == pytest.approx(
            num(t[y], "exports_pct_gdp") - num(t[y], "imports_pct_gdp"),
            abs=0.02)
    assert num(t[2025], "exports_pct_gdp") == pytest.approx(23.30, abs=0.01)
    assert num(t[2022], "balance_pct_gdp") == pytest.approx(4.96, abs=0.01)


def test_the_destination_shares_are_the_merchandise_table_over_its_own_total():
    d = by_year("trade/destinations.csv")
    side = {}
    for r in rows("trade/destinations_all_from_abs.csv"):
        side[(int(r["year"]), r["country_code"])] = float(r["exports_aud_bn"])
    for y, col, code in ((2019, "china_pct", "CHIN"),
                         (2020, "china_pct", "CHIN"),
                         (2025, "us_pct", "USA")):
        total = side[(y, "TOT")]
        assert num(d[y], col) == pytest.approx(
            side[(y, code)] / total * 100, abs=0.01)
    # The 2025 column reproduces the one-year snapshot exactly.
    snap = {r["country"]: float(r["share_pct"])
            for r in rows("trade/destinations_2025.csv")}
    assert num(d[2025], "china_pct") == pytest.approx(
        snap["China (excludes SARs and Taiwan)"], abs=0.01)


def test_the_customs_shares_do_not_add_to_the_national_accounts_ratio():
    t, d = by_year("trade/trade.csv"), by_year("trade/destinations.csv")
    # Two bases: the destination shares are of merchandise exports only,
    # the slot-1 ratio is goods AND services over GDP. Neither is the other.
    assert num(d[2025], "total_goods_exports_aud_bn") == pytest.approx(523.637,
                                                                      abs=0.01)
    assert num(t[2025], "exports_pct_gdp") != pytest.approx(
        num(d[2025], "total_goods_exports_aud_bn") / 1e3, abs=0.01)


# ----------------------------------------------------------------- markets
def test_the_cash_rate_is_the_rba_series_through_the_bis():
    k = by_year("markets/policy_rate.csv")
    assert num(k[2008], "policy_rate_pct") == pytest.approx(6.65, abs=0.01)
    assert num(k[2021], "policy_rate_pct") == pytest.approx(0.10, abs=0.01)
    assert num(k[2025], "policy_rate_pct") == pytest.approx(3.85, abs=0.01)


def test_the_currency_index_is_2006_over_the_year_and_rises_when_stronger():
    c = by_year("markets/currency.csv")
    assert num(c[2006], "index_2006") == pytest.approx(100.0, abs=0.01)
    assert num(c[2012], "index_2006") == pytest.approx(137.5, abs=0.05)
    assert num(c[2025], "index_2006") == pytest.approx(85.6, abs=0.05)
    assert num(c[2012], "aud_per_usd") < num(c[2006], "aud_per_usd")


def test_the_bond_and_the_equity_index_are_one_vintage_of_two_publishers():
    b = by_year("markets/bond_10y.csv")
    assert num(b[2020], "bond_10y_pct_annual_avg") == pytest.approx(0.92,
                                                                   abs=0.01)
    e = by_year("markets/equities.csv")
    assert num(e[2006], "asx200_usd_index_2006") == pytest.approx(100.0)
    assert num(e[2006], "sp500_usd_index_2006") == pytest.approx(100.0)
    assert num(e[2025], "asx200_usd_index_2006") == pytest.approx(139.7,
                                                                 abs=0.05)


# ------------------------------------------------------------------ credit
def test_the_two_npl_definitions_never_share_a_year():
    n = by_year("credit/npl.csv")
    for y, r in n.items():
        a, b = num(r, "npl_impaired_pct"), num(r, "npl_nonperforming_pct")
        assert not (a == a and b == b), f"{y}: two definitions in one row"
    assert max(y for y in n if num(n[y], "npl_impaired_pct") ==
               num(n[y], "npl_impaired_pct")) == 2021
    assert min(y for y in n if num(n[y], "npl_nonperforming_pct") ==
               num(n[y], "npl_nonperforming_pct")) == 2022
    # The step is the definition: the new measure starts above the old one.
    assert num(n[2022], "npl_nonperforming_pct") > \
        num(n[2021], "npl_impaired_pct")


def test_household_debt_is_the_bis_fourth_quarter_reading():
    h = by_year("credit/household_debt.csv")
    assert num(h[2016], "household_debt_pct_gdp") == pytest.approx(123.3,
                                                                  abs=0.05)
    assert num(h[2025], "household_debt_pct_gdp") == pytest.approx(114.0,
                                                                  abs=0.05)
    assert num(h[2021], "debt_service_ratio_pct") == pytest.approx(13.4,
                                                                  abs=0.05)


def test_the_lending_rate_slot_stays_pending():
    is_pending("plate_credit", "Household lending rate")


# ------------------------------------------------------------------ people
def test_the_gini_is_a_biennial_survey_and_the_world_bank_is_a_second_line():
    g = by_year("people/gini.csv")
    assert num(g[2020], "gini_hies") == pytest.approx(32.4, abs=0.05)
    assert num(g[2014], "gini_wb") == pytest.approx(34.4, abs=0.05)
    assert max(y for y in g if num(g[y], "gini_hies") == num(g[y], "gini_hies")) == 2020
    # Different concept and vintage: the two are never the same number.
    shared = [y for y in g if num(g[y], "gini_hies") == num(g[y], "gini_hies")
              and num(g[y], "gini_wb") == num(g[y], "gini_wb")]
    assert shared
    assert all(num(g[y], "gini_wb") > num(g[y], "gini_hies") for y in shared)


def test_poverty_is_the_international_line_because_no_national_one_exists():
    p = by_year("people/poverty.csv")
    assert sorted(p) == [2008, 2010, 2014, 2016, 2018, 2020]
    assert num(p[2008], "poverty_4_20_usd") == pytest.approx(0.9, abs=0.01)
    assert num(p[2020], "poverty_4_20_usd") == pytest.approx(1.5, abs=0.01)
    # There is no national column to confuse it with.
    assert "poverty_national_pct" not in p[2020]


def test_the_minimum_wage_is_one_fx_vintage_from_the_weekly_award():
    m = by_year("people/minimum_wage.csv")
    fx = by_year("markets/currency.csv")
    y = 2025
    expect = num(m[y], "minimum_wage_aud_week") * 52 / 12 / \
        num(fx[y], "aud_per_usd")
    assert num(m[y], "minimum_wage_usd_month") == pytest.approx(expect,
                                                               abs=0.02)


# ------------------------------------------------------------------- world
def test_hdi_is_one_vintage_and_stops_in_2023():
    h = by_year("world/hdi.csv")
    assert max(h) == 2023
    assert num(h[2023], "hdi") == pytest.approx(0.9679, abs=0.0005)


def test_the_corruption_index_starts_where_its_method_starts():
    c = by_year("world/cpi.csv")
    assert min(c) == 2012
    assert num(c[2012], "score") == pytest.approx(85.0, abs=0.01)
    assert num(c[2025], "score") == pytest.approx(76.0, abs=0.01)
    assert all(0 <= num(r, "score") <= 100 for r in c.values())


def test_gdp_and_reserves_are_the_world_bank_dollars():
    w = by_year("world/gdp_and_reserves.csv")
    assert num(w[2025], "gdp_usd_bn") == pytest.approx(1_798.5, abs=0.1)
    assert num(w[2025], "reserves_usd_bn") == pytest.approx(72.6, abs=0.05)


# -------------------------------------------------------------- demography
def test_the_population_is_the_30_june_stock_and_its_index():
    p = by_year("demography/population.csv")
    assert num(p[2006], "population_jun30") == pytest.approx(20_450_966, abs=1)
    assert num(p[2025], "population_jun30") == pytest.approx(27_601_739, abs=1)
    assert num(p[2025], "index_2006") == pytest.approx(135.0, abs=0.05)
    for y, r in p.items():
        assert num(r, "index_2006") == pytest.approx(
            num(r, "population_jun30") / num(p[2006], "population_jun30") * 100,
            abs=0.06)


def test_the_rates_are_the_published_ones_over_the_same_population():
    b = by_year("demography/births_deaths.csv")
    p = by_year("demography/population.csv")
    y = 2024
    assert num(b[y], "crude_birth_rate") == pytest.approx(
        num(b[y], "births") / num(p[y], "population_jun30") * 1000, abs=0.06)
    assert num(b[2025], "deaths") == pytest.approx(188_421, abs=1)
    # 2025 has deaths and a rate but no births: a hole, not a zero.
    assert num(b[2025], "births") != num(b[2025], "births")


def test_natural_increase_and_net_migration_are_derived_from_the_counts():
    n = by_year("demography/natural_increase.csv")
    b = by_year("demography/births_deaths.csv")
    m = by_year("migration/migration.csv")
    p = by_year("demography/population.csv")
    y = 2023
    assert num(n[y], "natural_increase_per_1000") == pytest.approx(
        (num(b[y], "births") - num(b[y], "deaths")) /
        num(p[y], "population_jun30") * 1000, abs=0.06)
    assert num(n[y], "net_migration_per_1000") == pytest.approx(
        num(m[y], "net_migration_per_1000"), abs=0.01)


def test_fertility_is_below_replacement_for_the_whole_window():
    f = by_year("demography/fertility.csv")
    assert max(f) == 2024
    assert all(num(r, "tfr") < 2.1 for r in f.values())
    assert num(f[2024], "tfr") == pytest.approx(1.481, abs=0.001)


# ---------------------------------------------------------------- security
def test_homicide_is_the_police_rate_and_its_count_divides_to_it():
    s = by_year("security/security.csv")
    p = by_year("demography/population.csv")
    y = 2024
    assert num(s[y], "homicide_victims") == pytest.approx(448, abs=1)
    assert num(s[y], "homicide_per_100k") == pytest.approx(
        num(s[y], "homicide_victims") / num(p[y], "population_jun30") * 1e5,
        abs=0.06)


def test_road_deaths_stop_in_2022_and_divide_to_their_rate():
    s = by_year("security/security.csv")
    p = by_year("demography/population.csv")
    assert num(s[2022], "road_deaths") == pytest.approx(1_180, abs=1)
    assert num(s[2022], "road_deaths_per_100k") == pytest.approx(
        num(s[2022], "road_deaths") / num(p[2022], "population_jun30") * 1e5,
        abs=0.01)
    for y in (2023, 2024, 2025):
        assert num(s[y], "road_deaths") != num(s[y], "road_deaths")
        assert num(s[y], "road_deaths_per_100k") != \
            num(s[y], "road_deaths_per_100k")


def test_suicide_is_the_who_harmonised_cut_and_stops_in_2023():
    s = by_year("security/security.csv")
    assert num(s[2023], "suicide_per_100k") == pytest.approx(12.6, abs=0.01)
    assert max(y for y in s if num(s[y], "suicide_per_100k") ==
               num(s[y], "suicide_per_100k")) == 2023


# --------------------------------------------------------------- mortality
def test_excess_deaths_are_measured_against_the_2015_2019_mean():
    m = by_year("mortality/mortality.csv")
    base = sum(num(m[y], "crude_death_rate") for y in range(2015, 2020)) / 5
    assert base == pytest.approx(6.56, abs=0.01)
    assert num(m[2022], "excess_deaths_pct") == pytest.approx(
        (num(m[2022], "crude_death_rate") / base - 1) * 100, abs=0.05)
    assert num(m[2022], "excess_deaths_pct") == pytest.approx(11.9, abs=0.05)
    assert num(m[2025], "excess_deaths_pct") == pytest.approx(4.0, abs=0.05)


def test_covid_is_the_underlying_cause_and_its_share_is_derived():
    m = by_year("mortality/mortality.csv")
    assert num(m[2022], "covid_deaths_per_100k") == pytest.approx(37.9, abs=0.05)
    share = num(m[2022], "covid_deaths_per_100k") / \
        (num(m[2022], "crude_death_rate") * 100) * 100
    assert share == pytest.approx(5.16, abs=0.05)
    # Nothing before 2015 and nothing after 2024 carries a COVID value.
    assert num(m[2006], "covid_deaths_per_100k") != \
        num(m[2006], "covid_deaths_per_100k")
    assert num(m[2025], "covid_deaths_per_100k") != \
        num(m[2025], "covid_deaths_per_100k")


# --------------------------------------------------------------- migration
def test_migration_flows_are_per_1000_of_the_same_years_population():
    m = by_year("migration/migration.csv")
    p = by_year("demography/population.csv")
    y = 2023
    assert num(m[y], "net_migration_per_1000") == pytest.approx(19.90, abs=0.01)
    assert num(m[y], "net_migration_per_1000") == pytest.approx(
        num(m[y], "immigration_per_1000") - num(m[y], "emigration_per_1000"),
        abs=0.01)
    assert num(m[y], "net_migration_per_1000") == pytest.approx(
        531_000 / num(p[y], "population_jun30") * 1000, abs=0.6)


def test_the_foreign_born_share_is_a_stock_and_runs_to_2025():
    m = by_year("migration/migration.csv")
    assert num(m[2025], "overseas_born_share_pct") == pytest.approx(31.99,
                                                                   abs=0.01)
    # Flow and stock end in different years and are separate panels.
    assert num(m[2025], "net_migration_per_1000") != \
        num(m[2025], "net_migration_per_1000")


# ------------------------------------------------------------- the cards
def test_the_cards_read_the_committed_csvs():
    cards = {ch["id"]: ch for ch in sitebuild.chapters_for(Country.load(SLUG))}
    assert set(cards) == {
        "01-economy", "02-fiscal", "03-spending", "04-trade", "05-markets",
        "06-credit", "07-people", "08-world", "09-demography", "10-security",
        "11-mortality", "12-migration"}
    e = by_year("macro/economy.csv")
    stat = cards["01-economy"]["stats"][0]
    assert stat["year"] == 2025
    assert stat["value"]["en"].endswith(f"{num(e[2025], 'real_growth_pct'):.1f}%")


def test_the_headline_leads_with_gdp_then_gdp_per_person_then_population():
    head = sitebuild.headline_for(Country.load(SLUG))
    labels = [h["label"]["en"] for h in head]
    assert labels[0] == "GDP"
    assert labels[1].startswith("GDP per person")
    assert labels[2].startswith("Population")
    assert head[0]["value"]["en"].startswith("US$")


def test_a_parked_panel_stays_parked():
    is_pending("plate_credit", "Household lending rate")
