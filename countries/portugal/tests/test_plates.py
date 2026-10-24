"""Semantic boundaries behind Portugal's twelve plates."""
from __future__ import annotations

import csv
from pathlib import Path
import pytest

from core.country import Country
from core.render import load_plates
from tests.probe import plate

SLUG = "portugal"
DATA = Country.load(SLUG).data_dir / "published"


def rows(name):
    with (DATA / f"{name}.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(x for x in fh if not x.startswith("#")))


def years(name):
    return {int(r["year"]): r for r in rows(name)}


def num(row, key):
    return float(row[key])


def test_registry_is_the_twelve_topic_spine():
    got = load_plates(Country.load(SLUG))
    assert [p.filename for p in got] == [
        "01-economy.png", "02-fiscal.png", "03-spending.png",
        "04-trade.png", "05-markets.png", "06-credit.png",
        "07-people.png", "08-world.png", "09-demography.png",
        "10-security.png", "11-mortality.png", "12-migration.png"]


def test_economy_uses_current_growth_and_keeps_price_definitions():
    g = years("gdp_estat")
    panel = plate(SLUG, "plate_economy").panel("Real GDP growth")
    assert panel.bars()[14] == pytest.approx(num(g[2020], "real_growth"))
    prices = plate(SLUG, "plate_economy").panel("Consumer prices")
    assert set(prices.legend_labels()) >= {"INE CPI", "Eurostat HICP"}


def test_fiscal_panels_share_the_general_government_perimeter():
    f = years("deficit_estat")
    panel = plate(SLUG, "plate_fiscal").panel("Overall and primary")
    assert panel.points("Primary balance")[2024] == pytest.approx(num(f[2024], "primary"))
    assert num(f[2010], "deficit") == pytest.approx(-11.4)


def test_trade_destinations_use_all_goods_exports():
    t = years("goods_trade_ine")[2025]
    want = num(t, "exports_es_eur") / num(t, "exports_mundo_eur") * 100
    panel = plate(SLUG, "plate_trade").panel("Goods export destinations")
    assert panel.points("Spain")[2025] == pytest.approx(want)


def test_equity_slot_does_not_publish_a_2013_base_as_2006_base():
    panel = plate(SLUG, "plate_markets").panel("Main equity index")
    assert not panel.data_lines()
    assert any("data pending" in text.lower() for text in panel.texts())


def test_credit_keeps_the_stock_and_ratio_concepts():
    h = years("household_debt_bpstat")
    panel = plate(SLUG, "plate_credit").panel("Household debt")
    line = panel.data_lines()[0]
    points = dict(zip(map(int, line.get_xdata()), line.get_ydata()))
    assert points[2025] == pytest.approx(
        num(h[2025], "housing_pct_gdp") + num(h[2025], "consumption_other_pct_gdp"))
    assert num(years("npl_bpstat")[2015], "npl_ratio") == pytest.approx(17.5)


def test_silc_year_convention_is_not_spliced_to_ine():
    ine, estat = years("gini_ine"), years("gini_estat")
    assert num(ine[2024], "gini") == pytest.approx(num(estat[2025], "silc"))


def test_minimum_wage_uses_eurostats_twelve_month_equivalent():
    wages, fx = years("minimum_wage_estat"), years("eurusd_ecb")
    assert num(wages[2024], "eur_month_jul") == pytest.approx(957)
    panel = plate(SLUG, "plate_people").panel("Minimum wage")
    line = panel.data_lines()[0]
    points = dict(zip(map(int, line.get_xdata()), map(float, line.get_ydata())))
    assert points[2024] == pytest.approx(
        num(wages[2024], "eur_month_jul") * num(fx[2024], "avg"))


def test_cpi_is_the_complete_comparable_2012_2025_run():
    cpi = years("cpi_ti")
    assert sorted(cpi) == list(range(2012, 2026))
    assert num(cpi[2012], "score") == 63
    assert num(cpi[2025], "score") == 56
    panel = plate(SLUG, "plate_world").panel("Corruption Perceptions Index")
    line = panel.data_lines()[0]
    points = dict(zip(map(int, line.get_xdata()), map(float, line.get_ydata())))
    assert points[2012] == 63 and points[2025] == 56


def test_demography_rates_use_the_revised_population():
    d = years("demography_ine")
    panel = plate(SLUG, "plate_demography").panel("Births and deaths")
    want = num(d[2023], "births_nuts2024") / num(d[2023], "population") * 1000
    assert panel.points("Births")[2023] == pytest.approx(want)


def test_homicide_systems_remain_two_lines():
    panel = plate(SLUG, "plate_security").panel("Homicide rate")
    assert set(panel.legend_labels()) == {"Police-recorded offences", "Death certificates"}
    assert panel.points("Police-recorded")[2022] != panel.points("Death certificates")[2022]


def test_excess_deaths_use_a_fixed_2015_2019_baseline():
    d = years("demography_estat")
    base = sum(num(d[y], "deaths") for y in range(2015, 2020)) / 5
    panel = plate(SLUG, "plate_mortality").panel("Excess deaths")
    want = [(num(d[y], "deaths") / base - 1) * 100 for y in d
            if y >= 2015 and d[y]["deaths"]]
    assert max(panel.bars()) == pytest.approx(max(want))


def test_migration_uses_published_net_not_flow_subtraction():
    net = years("net_migration_ine")[2021]
    imm, emi = years("immigration_ine")[2021], years("emigration_ine")[2021]
    assert num(net, "net_nuts2024") != num(imm, "immigrants") - num(emi, "emigrants")
    assert num(net, "net_nuts2024") == pytest.approx(250079)


def test_first_permits_are_labelled_as_administrative_events():
    assert num(years("permits_estat")[2025], "first_permits") == pytest.approx(310639)
    panel = plate(SLUG, "plate_migration").panel("First residence permits")
    assert any("Administrative events" in text for text in panel.texts())
