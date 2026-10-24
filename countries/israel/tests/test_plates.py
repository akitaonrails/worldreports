"""Semantic boundaries published by Israel's twelve spine plates."""
from __future__ import annotations

import csv

import pytest

from core.country import Country
from core.render import load_plates
from tests.probe import plate

SLUG = "israel"
DATA = Country.load(SLUG).data_dir


def rows(rel):
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(
            line for line in fh if not line.lstrip().startswith("#")))


def by_year(rel, key="year"):
    return {int(r[key]): r for r in rows(rel)}


def test_registry_keeps_the_full_standard_spine_order():
    ps = load_plates(Country.load(SLUG))
    assert [p.filename.split("-", 1)[0] for p in ps] == [
        f"{n:02d}" for n in range(1, 13)
    ]
    assert [p.topic for p in ps] == [
        "economy", "fiscal", "spending", "trade", "markets", "credit",
        "people", "world", "demography", "security", "mortality",
        "migration",
    ]


def test_only_the_staged_contraction_is_banded():
    growth = by_year("macro/gdp_growth.csv")
    assert float(growth[2020]["gdp_growth_pct"]) == pytest.approx(-1.9)
    assert float(growth[2008]["gdp_growth_pct"]) > 0
    assert float(growth[2009]["gdp_growth_pct"]) > 0
    assert all(float(growth[y]["gdp_growth_pct"]) > 0
               for y in (2023, 2024, 2025))
    country = Country.load(SLUG)
    assert [(start, end) for start, end, _ in country.recessions] == [
        (2020.0, 2020.9)
    ]


def test_fiscal_war_story_uses_general_government_values():
    fiscal = by_year("fiscal/general_government.csv")
    panel = plate(SLUG, "plate_fiscal").panel("Revenue and expenditure")
    assert panel.points("Revenue")[2024] == pytest.approx(
        float(fiscal[2024]["revenue_pct_gdp"]))
    assert panel.points("Expenditure")[2024] == pytest.approx(
        float(fiscal[2024]["expenditure_pct_gdp"]))
    assert float(fiscal[2024]["balance_pct_gdp"]) == pytest.approx(-8.1)


def test_fiscal_primary_balance_and_interest_share_one_imf_vintage():
    fiscal = by_year("fiscal/general_government.csv")
    balance = plate(SLUG, "plate_fiscal").panel("Overall and primary")
    interest = plate(SLUG, "plate_fiscal").panel("Interest paid")
    assert balance.points("Primary balance")[2024] == pytest.approx(-5.3)
    line = interest.data_lines()[0]
    plotted = dict(zip(line.get_xdata(), line.get_ydata()))
    assert plotted[2024] == pytest.approx(2.8)
    assert float(fiscal[2024]["interest_pct_gdp"]) == pytest.approx(
        float(fiscal[2024]["primary_balance_pct_gdp"])
        - float(fiscal[2024]["balance_pct_gdp"])
    )


def test_comtrade_destinations_use_country_rows_and_the_world_denominator():
    table = rows("trade/trade_partners_comtrade.csv")
    assert table[0]["partner"] == "United States"
    assert float(table[0]["share_of_exports_pct"]) == pytest.approx(29.42)
    assert "837" not in {row["partner_code"] for row in table}
    panel = plate(SLUG, "plate_trade").panel("destinations, 2023")
    assert max(patch.get_height() for patch in panel.ax.patches) == \
        pytest.approx(29.42)


def test_trade_balance_subtracts_import_values_not_the_year_axis():
    trade = by_year("trade/trade.csv")
    want = (float(trade[2024]["exports_pct_gdp"])
            - float(trade[2024]["imports_pct_gdp"]))
    panel = plate(SLUG, "plate_trade").panel("Trade balance")
    bars = {
        round(patch.get_x() + patch.get_width() / 2):
        patch.get_y() + patch.get_height()
        for patch in panel.ax.patches
        if patch.get_data_transform() is panel.ax.transData
    }
    assert bars[2024] == pytest.approx(want)


def test_ti_cpi_and_un_migrant_stock_are_drawn_from_reviewed_files():
    cpi = by_year("international/cpi_ti.csv")
    cpi_panel = plate(SLUG, "plate_world").panel("Corruption")
    cpi_points = dict(zip(cpi_panel.data_lines()[0].get_xdata(),
                          cpi_panel.data_lines()[0].get_ydata()))
    assert cpi_points[2025] == pytest.approx(float(cpi[2025]["cpi_score"]))
    stock = by_year("migration/migrant_stock_wb.csv")
    stock_panel = plate(SLUG, "plate_migration").panel("Foreign-born")
    stock_points = dict(zip(stock_panel.data_lines()[0].get_xdata(),
                            stock_panel.data_lines()[0].get_ydata()))
    assert stock_points[2024] == pytest.approx(
        float(stock[2024]["migrant_stock_pct"]))


def test_population_rates_use_the_same_year_midyear_population():
    pop = by_year("demography/demography.csv")
    police = by_year("security/homicide_police.csv")
    want = float(police[2023]["murder_301"]) / float(pop[2023]["population"]) * 100_000
    panel = plate(SLUG, "plate_security").panel("Homicide rate")
    assert panel.points("Israel Police")[2023] == pytest.approx(want)
    assert want == pytest.approx(12.28, abs=0.01)


def test_homicide_systems_are_labelled_and_never_spliced():
    panel = plate(SLUG, "plate_security").panel("Homicide rate")
    unodc = panel.points("UNODC")
    police = panel.points("Israel Police")
    assert max(unodc) == 2022
    assert min(police) == 2021
    assert set(panel.legend_labels()) == {
        "UNODC count as a published rate, via the World Bank (to 2022)",
        "Israel Police type-301 files ÷ the WB mid-year population (2021 only and later)",
    }


def test_olim_are_a_law_of_return_flow_not_net_migration():
    pop = by_year("demography/demography.csv")
    olim = by_year("migration/olim_flow.csv")
    want = float(olim[2022]["olim"]) / float(pop[2022]["population"]) * 1_000
    panel = plate(SLUG, "plate_migration").panel("new residence and work permits")
    assert panel.points("new olim")[2022] == pytest.approx(want)
    assert float(olim[2022]["olim"]) == 76_601


def test_permit_lens_excludes_visitors_diplomats_and_olim_classes():
    included = {
        "A2", "A2KLLY", "A3", "A4", "A5", "B1", "B1KLLY",
        "B1XVCf", "B3", "B4",
    }
    table = rows("migration/permits.csv")
    totals = {}
    for row in table:
        if row["visa_class"] in included:
            year = int(row["year"])
            totals[year] = totals.get(year, 0) + float(row["new_permits"])
    pop = by_year("demography/demography.csv")
    want = max(totals[year] / float(pop[year]["population"]) * 1_000
               for year in totals if year <= 2025)
    panel = plate(SLUG, "plate_migration").panel("new residence and work permits")
    assert max(panel.bars()) == pytest.approx(want)
    assert any("records, not people" in text for text in panel.texts())


def test_cofog_groups_reconcile_to_total_and_are_all_drawn():
    cofog = by_year("spending/cofog.csv")
    groups = [
        "social_protection_pct_gdp", "health_pct_gdp",
        "education_pct_gdp", "general_public_services_pct_gdp",
        "economic_affairs_pct_gdp", "defence_public_order_pct_gdp",
        "other_pct_gdp",
    ]
    assert len(groups) == 7
    for year, row in cofog.items():
        assert sum(float(row[column]) for column in groups) == pytest.approx(
            float(row["total_pct_gdp"]), abs=1e-8), year

    panel = plate(SLUG, "plate_spending").panel("government spending")
    assert len(panel.legend_labels()) == 7
    plotted_groups = [collection for collection in panel.ax.collections
                      if not collection.get_label().startswith("_")]
    assert {collection.get_label() for collection in plotted_groups} == set(
        panel.legend_labels())


def test_whole_economy_and_government_investment_are_not_conflated():
    economy = by_year("spending/whole_economy_investment.csv")
    government = by_year("spending/public_investment.csv")
    assert float(economy[2019]["gfcf_pct_gdp"]) == pytest.approx(23.132421)
    assert float(government[2019]["gov_gfcf_pct_gdp"]) == pytest.approx(
        4.870103)
    assert float(economy[2019]["gfcf_pct_gdp"]) > 4 * float(
        government[2019]["gov_gfcf_pct_gdp"])

    whole_panel = plate(SLUG, "plate_spending").panel("whole economy")
    public_panel = plate(SLUG, "plate_spending").panel("Public investment")
    whole = whole_panel.points("Whole-economy")
    public = public_panel.points("General government")
    assert whole[2019] == pytest.approx(
        float(economy[2019]["gfcf_pct_gdp"]))
    assert public[2019] == pytest.approx(
        float(government[2019]["gov_gfcf_pct_gdp"]))


def test_income_distribution_methods_are_separate_segments():
    income = by_year("social/income_distribution.csv")
    assert {y for y, row in income.items()
            if row["gini_meth2011_current"]} == set(range(2008, 2012))
    assert {y for y, row in income.items()
            if row["gini_meth2012_previous"]} == set(range(2011, 2023))
    assert {y for y, row in income.items()
            if row["gini_meth2012_current"]} == {2023}
    assert float(income[2023]["gini_meth2012_current"]) == pytest.approx(
        0.34154999256134)
    assert float(income[2023]["poverty50_pct_meth2012_current"]) == \
        pytest.approx(17.1729996800423)

    panel = plate(SLUG, "plate_people").panel("Gini")
    old = panel.points("2011 method")
    previous = panel.points("2012 method, previous")
    assert set(old) == set(range(2008, 2012))
    assert set(previous) == set(range(2011, 2023))
    current = [collection for collection in panel.ax.collections
               if "2012 method, current" in collection.get_label().lower()]
    assert len(current) == 1
    assert list(current[0].get_offsets()[0]) == pytest.approx([
        2023, float(income[2023]["gini_meth2012_current"]) * 100
    ])


def test_minimum_wage_usd_uses_the_calendar_year_average_fx():
    wage = by_year("social/minimum_wage.csv")
    assert float(wage[2017]["monthly_ils_avg"]) == pytest.approx(5025)
    assert 2026 not in wage
    expected = (float(wage[2025]["monthly_ils_avg"])
                / float(wage[2025]["ils_per_usd_avg"]))
    assert float(wage[2025]["monthly_usd_avg"]) == pytest.approx(
        expected, abs=0.01)
    panel = plate(SLUG, "plate_people").panel("Minimum wage")
    assert panel.points("US$")[2025] == pytest.approx(expected, abs=0.01)


def test_policy_rate_keeps_the_2017_aggregation_seam_visible():
    policy = by_year("markets/policy_rate.csv")
    assert {row["annual_aggregation"] for year, row in policy.items()
            if year <= 2016} == {
                "mean_of_12_monthly_liquidity_period_averages"
            }
    assert {row["annual_aggregation"] for year, row in policy.items()
            if year >= 2017} == {
                "calendar_day_weighted_declared_nominal_rate"
            }
    assert float(policy[2006]["policy_rate_pct"]) == pytest.approx(5.125)
    assert float(policy[2017]["policy_rate_pct"]) == pytest.approx(0.1)
    assert float(policy[2025]["policy_rate_pct"]) == pytest.approx(4.476027)

    panel = plate(SLUG, "plate_markets").panel("Policy rate")
    before = panel.points("liquidity-period")
    after = panel.points("declared rate")
    assert max(before) == 2016 and min(after) == 2017
    assert after[2025] == pytest.approx(
        float(policy[2025]["policy_rate_pct"]))


def test_ten_year_yield_is_the_annual_mean_of_complete_months():
    bond = by_year("markets/government_bond_10y.csv")
    assert all(int(row["monthly_observations"]) == 12 for row in bond.values())
    assert float(bond[2006]["government_bond_10y_yield_pct"]) == \
        pytest.approx(6.314167)
    assert float(bond[2020]["government_bond_10y_yield_pct"]) == \
        pytest.approx(0.7775)
    assert float(bond[2025]["government_bond_10y_yield_pct"]) == \
        pytest.approx(4.244167)
    panel = plate(SLUG, "plate_markets").panel("10-year")
    assert panel.data_lines()[0].get_ydata()[-1] == pytest.approx(
        float(bond[2025]["government_bond_10y_yield_pct"]))


def test_household_debt_ratio_is_q4_stock_over_annual_nominal_gdp():
    debt = by_year("credit/household_debt.csv")
    for year in (2006, 2024, 2025):
        expected = (float(debt[year]["household_debt_nis_bn"])
                    / float(debt[year]["nominal_gdp_nis_bn"]) * 100)
        assert float(debt[year]["household_debt_pct_gdp"]) == pytest.approx(
            expected, abs=1e-6)
    panel = plate(SLUG, "plate_credit").panel("Household debt")
    assert panel.data_lines()[0].get_ydata()[-1] == pytest.approx(
        float(debt[2025]["household_debt_pct_gdp"]))


def test_mortgage_rate_starts_with_complete_2014_new_loan_data():
    mortgage = by_year("credit/mortgage_rate.csv")
    assert min(mortgage) == 2014
    assert all(int(row["monthly_observations"]) == 12
               for row in mortgage.values())
    assert float(mortgage[2014]["new_unindexed_mortgage_rate_pct"]) == \
        pytest.approx(2.695)
    panel = plate(SLUG, "plate_credit").panel("Mortgage")
    points = panel.points("new unindexed")
    assert min(points) == 2014
    assert points[2025] == pytest.approx(
        float(mortgage[2025]["new_unindexed_mortgage_rate_pct"]))
    assert any("fixed and variable" in text.lower() for text in panel.texts())


def test_npl_ratio_keeps_the_2022_fsi_method_transition_visible():
    npl = by_year("credit/npl_ratio.csv")
    assert {npl[y]["method_vintage"] for y in range(2012, 2022)} == {
        "IMF_FSI_2006_guide"
    }
    assert {npl[y]["method_vintage"] for y in range(2022, 2026)} == {
        "IMF_FSI_2019_guide_transition_2022"
    }
    panel = plate(SLUG, "plate_credit").panel("Non-performing")
    old = panel.points("2006 Guide")
    new = panel.points("2019 Guide")
    assert max(old) == 2021 and min(new) == 2022
    assert new[2025] == pytest.approx(
        float(npl[2025]["npl_to_total_gross_loans_pct"]))
    assert any("banking system" in text.lower().replace("-", " ")
               for text in panel.texts())


def test_mortality_uses_fixed_baseline_and_underlying_cause_covid():
    mortality = by_year("mortality/mortality.csv")
    baseline = sum(float(mortality[y]["deaths_all"])
                   for y in range(2015, 2020)) / 5
    assert baseline == pytest.approx(44_673.8)
    assert all(not mortality[y]["excess_pct"] for y in range(2005, 2015))
    for year in (2020, 2021, 2023):
        expected = (float(mortality[year]["deaths_all"]) / baseline - 1) * 100
        assert float(mortality[year]["excess_pct"]) == pytest.approx(
            expected, abs=0.01)
    assert float(mortality[2021]["covid_deaths"]) == 4_800

    excess = plate(SLUG, "plate_mortality").panel("Excess deaths")
    assert excess.bars()[6] == pytest.approx(
        float(mortality[2021]["excess_pct"]))
    covid = plate(SLUG, "plate_mortality").panel("COVID-19")
    assert covid.bars()[1] == pytest.approx(
        float(mortality[2021]["covid_per_100k"]))
    assert any("4,800" in text and "underlying-cause" in text.lower()
               for text in covid.texts())


def test_mortality_cause_lens_uses_crude_not_age_standardised_rates():
    mortality = by_year("mortality/mortality.csv")
    panel = plate(SLUG, "plate_mortality").panel("malignant")
    assert panel.points("Malignant neoplasms")[2021] == pytest.approx(
        float(mortality[2021]["malignant_neoplasms_per_100k"]))
    assert panel.points("Circulatory")[2021] == pytest.approx(
        float(mortality[2021]["circulatory_per_100k"]))
    assert any("crude" in text.lower() for text in panel.texts())


def test_filled_series_are_removed_from_page_unavailable_disclosures():
    import json

    ui = json.loads((Country.load(SLUG).dir / "ui.json").read_text())
    assert set(ui) == {"he", "en", "pt"}
    assert all(locale["unavailable"] for locale in ui.values())
    stale_market_terms = {
        "en": "Bank of Israel rates and yields",
        "pt": "Juros e rendimentos do Banco de Israel",
        "he": "ריבית ותשואה של בנק ישראל",
    }
    for locale, stale_term in stale_market_terms.items():
        assert stale_term not in {
            item["term"] for item in ui[locale]["unavailable"]
        }
    english = " ".join(
        item[field]
        for item in ui["en"]["unavailable"]
        for field in ("term", "detail")
    ).lower()
    assert "policy rate" not in english
    assert "ten-year government yield" not in english
    assert "household debt ratio" not in english
    assert "mortgage rate" not in english
    assert "non-performing" not in english
    assert "minimum wage" not in english
    assert "cofog" not in english


def test_public_security_wording_describes_recorded_homicide_cases_neutrally():
    import json

    panel = plate(SLUG, "plate_security").panel("Homicide cases recorded")
    visible = " ".join([panel.title, *panel.legend_labels(),
                        *panel.texts()]).lower()
    assert "murder" not in visible
    assert "assassin" not in visible

    ui = json.loads((Country.load(SLUG).dir / "ui.json").read_text())
    i18n = json.loads((Country.load(SLUG).dir / "i18n.json").read_text())
    public_copy = json.dumps({"ui": ui, "i18n": i18n}, ensure_ascii=False)
    assert "assassinat" not in public_copy.lower()
