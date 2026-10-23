"""Semantic boundaries for China's harmonised-first publication."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from core.country import Country
from core.render import load_plates
from tests.probe import plate, plate_names

SLUG = "china"
COUNTRY = Country.load(SLUG)
DATA = COUNTRY.data_dir


def rows(rel):
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(x for x in fh if not x.startswith("#")))


def by_year(rel):
    return {int(r["year"]): r for r in rows(rel)}


def col(rel, field):
    return {year: float(row[field]) for year, row in by_year(rel).items()
            if (row.get(field) or "").strip()}


def test_registry_is_the_complete_twelve_plate_spine():
    loaded = load_plates(COUNTRY)
    assert [p.filename for p in loaded] == [
        "01-economy.png", "02-fiscal.png", "03-spending.png",
        "04-trade.png", "05-markets.png", "06-credit.png",
        "07-people.png", "08-world.png", "09-demography.png",
        "10-security.png", "11-mortality.png", "12-migration.png",
    ]
    assert plate_names(SLUG) == sorted(f"plate_{p.topic}" for p in loaded)


def test_no_recession_band_is_manufactured_from_a_slowdown():
    config = yaml.safe_load((COUNTRY.dir / "country.yaml").read_text())
    assert config["bands"] == []
    growth = by_year("economy/gdp_growth_intl.csv")
    assert all(float(r["wb_real_growth_pct"]) > 0 for r in growth.values())
    assert all(float(r["imf_real_growth_pct"]) > 0 for r in growth.values())
    assert float(growth[2020]["wb_real_growth_pct"]) == pytest.approx(2.34)


def test_growth_keeps_world_bank_bars_and_imf_line_distinct():
    growth = by_year("economy/gdp_growth_intl.csv")
    panel = plate(SLUG, "plate_economy").panel("Real GDP growth")
    assert panel.points("IMF WEO")[2025] == pytest.approx(
        float(growth[2025]["imf_real_growth_pct"]))
    assert panel.bars()[-1] == pytest.approx(
        float(growth[2025]["wb_real_growth_pct"]))
    assert any("NBS national accounts unavailable" in t for t in panel.texts())


def test_unemployment_is_not_mislabelled_as_nbs_urban_rate():
    panel = plate(SLUG, "plate_economy").panel("Unemployment")
    assert panel.data_lines()[0].get_ydata()[-1] == pytest.approx(4.62)
    assert any("not the NBS surveyed urban rate" in t for t in panel.texts())


def test_fiscal_debt_declares_the_broad_imf_perimeter():
    panel = plate(SLUG, "plate_fiscal").panel("Gross debt")
    assert panel.points("IMF broad")[2025] == pytest.approx(98.6)
    text = " ".join(panel.texts())
    assert "MOF on-budget debt excludes LGFVs" in text
    assert "remain separate" in text


def test_pending_fiscal_flows_are_not_invented_from_narrow_budget_data():
    panel = plate(SLUG, "plate_fiscal").panel("Revenue and expenditure")
    assert not panel.data_lines()
    assert any("MOF's budget is a narrower perimeter" in t
               for t in panel.texts())


def test_trade_balance_is_one_world_bank_vintage():
    trade = by_year("trade/trade_intl_openness.csv")
    expected = (float(trade[2025]["exports_pct_gdp"])
                - float(trade[2025]["imports_pct_gdp"]))
    panel = plate(SLUG, "plate_trade").panel("Trade balance")
    assert panel.bars()[-1] == pytest.approx(expected)
    assert expected == pytest.approx(4.18)


def test_comtrade_snapshot_uses_world_denominator_and_keeps_caveat():
    table = rows("trade/trade_comtrade_partner.csv")
    world = next(r for r in table if r["flow"] == "X" and r["partner"] == "World")
    us = next(r for r in table if r["flow"] == "X" and r["partner"] == "United States")
    expected = float(us["value_usd"]) / float(world["value_usd"]) * 100
    assert float(us["share_of_flow_pct"]) == pytest.approx(expected, abs=0.01)
    assert not any("Taiwan" in r["partner"] for r in table)
    panel = plate(SLUG, "plate_trade").panel("Top export destinations")
    assert any("Taiwan absent" in t for t in panel.texts())


def test_currency_direction_is_stronger_up_and_equity_is_converted_to_usd():
    fx = col("markets/fx_cny_per_usd.csv", "cny_per_usd_avg")
    panel = plate(SLUG, "plate_markets").panel("Renminbi against")
    points = panel.data_lines()[0].get_ydata()
    assert points[0] == pytest.approx(100)
    assert points[8] == pytest.approx(fx[2006] / fx[2014] * 100)

    sse = col("markets/sse_index.csv", "close")
    expected = sse[2025] / fx[2025] / (sse[2006] / fx[2006]) * 100
    equity = plate(SLUG, "plate_markets").panel("SSE Composite in US$")
    assert equity.points("SSE Composite")[2025] == pytest.approx(expected)


def test_npl_is_bank_wide_and_not_household_arrears():
    npl = col("credit/npl_intl.csv", "npl_pct")
    panel = plate(SLUG, "plate_credit").panel("Non-performing loans")
    assert panel.data_lines()[0].get_ydata()[-1] == pytest.approx(npl[2024])
    assert any("bank-wide, not households" in t for t in panel.texts())


def test_poverty_thresholds_are_international_not_national():
    panel = plate(SLUG, "plate_people").panel("Poverty rate")
    assert panel.points("US$8.30")[2022] == pytest.approx(21.3)
    assert any("not China's national poverty line" in t for t in panel.texts())
    wage = plate(SLUG, "plate_people").panel("Minimum wage")
    assert not wage.data_lines()
    assert any("provinces and municipalities" in t for t in wage.texts())


def test_demography_uses_published_rates_and_population_for_net_migration():
    vital = by_year("demography/vital_intl.csv")
    assert float(vital[2022]["birth_rate_per_1000"]) < \
        float(vital[2022]["death_rate_per_1000"])
    pop = col("demography/population_intl.csv", "population")
    expected = float(vital[2024]["net_migration"]) / pop[2024] * 1000
    panel = plate(SLUG, "plate_demography").panel("Natural increase")
    assert panel.points("Net migration")[2024] == pytest.approx(expected)


def test_security_series_end_where_harmonised_publishers_end():
    panel = plate(SLUG, "plate_security").panel("Homicide rate")
    assert max(panel.points("UNODC")) == 2020
    assert any("No accessible comparable national police series" in t
               for t in panel.texts())
    road = plate(SLUG, "plate_security").panel("Road traffic")
    assert max(road.points("WHO")) == 2019


def test_mortality_does_not_invent_counts_from_a_crude_rate():
    rate = plate(SLUG, "plate_mortality").panel("Crude death rate")
    assert rate.points("World Bank")[2023] == pytest.approx(7.87)
    excess = plate(SLUG, "plate_mortality").panel("Excess deaths")
    assert not excess.data_lines()
    assert any("death counts" in t for t in excess.texts())


def test_migrant_stock_remains_four_snapshots_without_interpolation():
    stock = col("migration/migrant_stock_intl.csv", "migrant_stock_pct")
    assert set(stock) == {2010, 2015, 2020, 2024}
    panel = plate(SLUG, "plate_migration").panel("Foreign-born share")
    assert set(panel.points("International migrant stock")) == set(stock)
    assert any("never interpolated" in t for t in panel.texts())


@pytest.mark.parametrize("name", plate_names(SLUG))
def test_every_drawn_series_stays_inside_its_panel(name):
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped()
