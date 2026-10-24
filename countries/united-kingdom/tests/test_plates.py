"""The published meaning of the United Kingdom's twelve spine plates.

The generic suite checks rendering, catalogs and geometry.  These tests cover
the semantic boundaries that a visually correct chart cannot reveal: public-
sector perimeters, incompatible methods, denominators and reference periods.
"""
from __future__ import annotations

import csv
from collections import Counter

import pytest

from core.country import Country
from core.render import load_plates
from tests.probe import plate, plate_names

SLUG = "united-kingdom"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(
            line for line in fh if not line.lstrip().startswith("#")))


def by_year(rel: str, key: str = "year") -> dict[int, dict]:
    return {int(r[key]): r for r in rows(rel)}


def col(rel: str, column: str) -> dict[int, float]:
    return {y: float(r[column]) for y, r in by_year(rel).items()
            if (r.get(column) or "").strip()}


def test_registry_is_the_twelve_plate_spine_in_order():
    loaded = load_plates(Country.load(SLUG))
    assert [p.filename for p in loaded] == [
        "01-economy.png", "02-fiscal.png", "03-spending.png",
        "04-trade.png", "05-markets.png", "06-credit.png",
        "07-people.png", "08-world.png", "09-demography.png",
        "10-security.png", "11-mortality.png", "12-migration.png",
    ]
    assert [p.topic for p in loaded] == [
        "economy", "fiscal", "spending", "trade", "markets", "credit",
        "people", "world", "demography", "security", "mortality",
        "migration",
    ]
    assert plate_names(SLUG) == sorted(f"plate_{p.topic}" for p in loaded)


def test_fiscal_spine_uses_general_government_flows_and_exact_interest():
    """The canonical slots are IMF general government, not ONS/PESA data
    silently relabelled to fit; the PESA interest line remains secondary."""
    imf = by_year("international/fiscal_imf.csv")
    assert float(imf[2024]["revenue_pct_gdp"]) == pytest.approx(37.44)
    assert float(imf[2024]["expenditure_pct_gdp"]) == pytest.approx(43.44)
    assert float(imf[2024]["overall_balance_pct_gdp"]) == pytest.approx(-6.00)
    assert float(imf[2024]["primary_balance_pct_gdp"]) == pytest.approx(-3.98)

    panel = plate(SLUG, "plate_fiscal").panel("Revenue and expenditure")
    assert panel.points("general-government revenue")[2024] == \
        pytest.approx(37.44)
    assert panel.points("general-government expenditure")[2024] == \
        pytest.approx(43.44)

    interest = col("fiscal/gfs_operations.csv", "interest_payable_pct_gdp")
    panel = plate(SLUG, "plate_fiscal").panel("Interest paid")
    assert panel.points("IMF general government")[2024] == \
        pytest.approx(interest[2024])
    assert set(panel.legend_labels()) == {
        "IMF general government, interest payable",
        "PESA public-sector debt interest",
    }


def test_trade_destinations_use_all_goods_exports_as_denominator():
    partners = [r for r in rows("trade/goods_by_partner.csv")
                if r["year"] == "2025"]
    us = next(r for r in partners if r["country"] == "United States")
    assert float(us["export_share"]) == pytest.approx(15.78)
    selected_share = sum(float(r["export_share"]) for r in partners)
    assert selected_share == pytest.approx(60.55, abs=0.01)
    assert selected_share < 100, "the selected partners became the denominator"
    implied_world_total = float(us["exports"]) / float(us["export_share"]) * 100
    assert implied_world_total == pytest.approx(426.259, abs=0.5)
    panel = plate(SLUG, "plate_trade").panel("Top export destinations")
    assert panel.points("United States")[2025] == pytest.approx(15.78)
    assert any("all UK goods" in text for text in panel.texts())


def test_ftse_dollar_index_uses_year_end_sterling():
    ftse = col("markets/ftse.csv", "close")
    eoy = col("markets/sterling.csv", "usd_per_gbp_eoy")
    avg = col("markets/sterling.csv", "usd_per_gbp_avg")
    panel = plate(SLUG, "plate_markets").panel("FTSE 100 in US$")
    points = panel.points("FTSE 100")
    want = ftse[2025] * eoy[2025] / (ftse[2006] * eoy[2006]) * 100
    wrong = ftse[2025] * avg[2025] / (ftse[2006] * avg[2006]) * 100
    assert points[2025] == pytest.approx(want, rel=1e-9)
    assert points[2025] == pytest.approx(109.73, abs=0.02)
    assert points[2025] != pytest.approx(wrong, abs=0.1)


def test_credit_slots_use_bis_q4_and_the_imf_fsi():
    debt = col("credit/household_credit.csv", "household_credit_pct_gdp_q4")
    assert debt[2009] == pytest.approx(97.4)
    assert debt[2025] == pytest.approx(73.5)
    assert 2026 not in debt, "a Q1 observation was presented as a Q4 stock"
    panel = plate(SLUG, "plate_credit").panel("Household debt (% of GDP)")
    assert panel.data_lines()[0].get_xdata()[-1] == 2025
    assert panel.data_lines()[0].get_ydata()[-1] == pytest.approx(73.5)

    npl = col("credit/npl.csv", "npl_pct")
    panel = plate(SLUG, "plate_credit").panel("Non-performing loans")
    assert npl[2011] == pytest.approx(3.96)
    assert panel.data_lines()[0].get_ydata()[-1] == pytest.approx(npl[2025])
    assert any("IMF Financial Soundness" in text for text in panel.texts())


def test_people_plate_keeps_wage_conversion_and_poverty_concepts_explicit():
    wage = by_year("social/minimum_wage.csv")[2024]
    expected = (float(wage["adult_rate_gbp_hour_avg"])
                * float(wage["hours_month"])
                * float(wage["usd_per_gbp_avg"]))
    assert float(wage["adult_rate_usd_month"]) == pytest.approx(expected,
                                                                 abs=0.02)
    panel = plate(SLUG, "plate_people").panel("Minimum wage")
    assert panel.points("Statutory adult rate")[2024] == \
        pytest.approx(expected, abs=0.02)
    assert any("40 hours/week" in text and "annual-average" in text
               for text in panel.texts())

    poverty = col("international/poverty.csv",
                  "poverty_at_8_30_2021_ppp_pct")
    panel = plate(SLUG, "plate_people").panel("Relative low income")
    assert panel.points("US$8.30/day")[2021] == pytest.approx(poverty[2021])
    assert {"Before housing costs", "After housing costs"}.issubset(
        panel.legend_labels())
    assert any("absolute international threshold" in text
               for text in panel.texts())


def test_corruption_index_methods_are_two_unjoined_segments():
    table = by_year("international/cpi.csv")
    assert float(table[2011]["cpi_pre2012_0_10"]) == pytest.approx(7.8)
    assert not table[2011]["cpi_2012_method_0_100"]
    assert not table[2012]["cpi_pre2012_0_10"]
    assert float(table[2012]["cpi_2012_method_0_100"]) == pytest.approx(74)
    panel = plate(SLUG, "plate_world").panel("Corruption Perceptions")
    assert set(panel.points("old method")) == set(range(2006, 2012))
    assert set(panel.points("2012 method")) == set(range(2012, 2026))
    assert any("only scores from 2012 onward are comparable" in text
               for text in panel.texts())


def test_demography_uses_wb_fertility_and_keeps_migration_seams_visible():
    fertility = col("demography/fertility.csv", "tfr")
    panel = plate(SLUG, "plate_demography").panel("Total fertility rate")
    assert panel.data_lines()[0].get_ydata()[-1] == \
        pytest.approx(fertility[2024])
    assert fertility[2024] == pytest.approx(1.551)

    panel = plate(SLUG, "plate_demography").panel("Natural increase")
    estat = panel.points("Eurostat IPS-era")
    pre = panel.points("ONS new approach")
    post = panel.points("ONS fully administrative")
    assert max(estat) == 2019
    assert max(pre) == 2020 and min(post) == 2021
    assert any("never spliced" in text for text in panel.texts())


def test_homicide_rates_keep_scope_and_reference_periods_separate():
    pop = by_year("demography/population.csv")
    ew_2022 = (float(pop[2022]["population_england"])
               + float(pop[2022]["population_wales"]))
    police = by_year("security/homicide_police.csv", "fiscal_year")
    cert = by_year("security/homicide_deaths.csv")
    panel = plate(SLUG, "plate_security").panel("Homicide rate")
    police_points = panel.points("Home Office Homicide Index")
    cert_points = panel.points("Death certificate")
    assert police_points[2022.25] == pytest.approx(
        float(police[2022]["offences_currently_recorded"]) / ew_2022 * 1e5)
    assert cert_points[2022] == pytest.approx(
        float(cert[2022]["homicide_ons_definition"]) / ew_2022 * 1e5)
    assert min(cert_points) == 2007
    assert any("separately rated and never joined" in text
               for text in panel.texts())


def test_mortality_uses_published_rate_fixed_baseline_and_five_regimes():
    vital = by_year("demography/vital.csv")
    panel = plate(SLUG, "plate_mortality").panel("Crude death rate")
    assert panel.data_lines()[0].get_ydata()[-1] == pytest.approx(
        float(vital[2025]["crude_death_rate_per_1000"]))

    baseline = sum(float(vital[y]["deaths"]) for y in range(2015, 2020)) / 5
    assert baseline == pytest.approx(532_077.2)
    panel = plate(SLUG, "plate_mortality").panel("Excess deaths")
    assert any("fixed baseline: 532,077" in text for text in panel.texts())

    panel = plate(SLUG, "plate_mortality").panel("neoplasms")
    ranges = Counter((int(min(line.get_xdata())), int(max(line.get_xdata())))
                     for line in panel.data_lines())
    assert ranges == Counter({(2006, 2010): 2, (2011, 2013): 2,
                              (2014, 2019): 2, (2020, 2021): 2,
                              (2022, 2025): 2})
    text = " ".join(panel.texts())
    assert "IRIS replaces MMDS/NCHS" in text
    assert "MUSE replaces IRIS" in text

    covid = plate(SLUG, "plate_mortality").panel("COVID-19 deaths")
    assert not covid.data_lines()
    assert any("never substituted with chapter 22" in text
               for text in covid.texts())


def test_migration_systems_published_net_and_stock_denominators():
    panel = plate(SLUG, "plate_migration").panel("Immigration and emigration")
    assert max(panel.points("Eurostat immigration")) == 2019
    assert max(panel.points("ONS Immigration, pre")) == 2020
    assert min(panel.points("ONS Immigration, from")) == 2021
    assert any("never joined" in text for text in panel.texts())

    flow_rows = rows("migration/flows.csv")
    dec_2024 = {(r["flow"]): float(r["all_nationalities"])
                for r in flow_rows if r["period_end"] == "2024-12"}
    assert dec_2024["net"] != dec_2024["immigration"] - dec_2024["emigration"]
    population = float(by_year("demography/population.csv")[2024]["population_uk"])
    net = plate(SLUG, "plate_migration").panel("Net migration")
    assert net.points("ONS published net, from")[2024] == pytest.approx(
        dec_2024["net"] / population * 1_000)

    stocks = by_year("migration/stocks.csv")
    expected_born = ((float(stocks[2019]["stock_by_birth_total"])
                      - float(stocks[2019]["stock_by_birth_national"]))
                     / float(stocks[2019]["stock_by_birth_total"]) * 100)
    stock_panel = plate(SLUG, "plate_migration").panel("Foreign-born")
    assert stock_panel.points("Foreign-born")[2019] == \
        pytest.approx(expected_born)
    assert any("its own Eurostat classification total" in text
               for text in stock_panel.texts())


def test_asylum_flows_are_not_confused_with_the_year_end_backlog():
    asylum = by_year("migration/asylum.csv")
    panel = plate(SLUG, "plate_migration").panel("asylum applications")
    assert panel.points("Asylum applications")[2025] == pytest.approx(
        float(asylum[2025]["applications_persons"]) / 1_000)
    assert panel.points("Initial decisions")[2025] == pytest.approx(
        float(asylum[2025]["initial_decisions_persons"]) / 1_000)
    assert panel.points("Initial grants")[2025] == pytest.approx(
        float(asylum[2025]["initial_grants_persons"]) / 1_000)
    assert panel.points("31 Dec (stock)")[2025] == pytest.approx(
        float(asylum[2025]["awaiting_initial_decision_31dec_persons"]) / 1_000)
    assert any("annual flows" in text and "31 December stock" in text
               for text in panel.texts())
