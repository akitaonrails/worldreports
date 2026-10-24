"""Semantic and no-splice boundaries behind Japan's twelve plates."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from core.country import Country
from core.render import load_plates
from tests.probe import plate

SLUG = "japan"
DATA = Country.load(SLUG).data_dir / "published"


def rows(name):
    with (DATA / f"{name}.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(line for line in fh if not line.startswith("#")))


def years(name, key="year"):
    return {int(r[key]): r for r in rows(name)}


def num(row, key):
    return float(row[key])


def test_registry_is_the_twelve_topic_spine():
    assert [p.filename for p in load_plates(Country.load(SLUG))] == [
        "01-economy.png", "02-fiscal.png", "03-spending.png",
        "04-trade.png", "05-markets.png", "06-credit.png",
        "07-people.png", "08-world.png", "09-demography.png",
        "10-security.png", "11-mortality.png", "12-migration.png",
    ]


def test_2024_h1_band_remains_two_negative_quarters():
    q = {r["quarter"]: r for r in rows("gdp_quarterly_esri")}
    assert num(q["2024-Q1"], "gdp_real_qoq_pct") < 0
    assert num(q["2024-Q2"], "gdp_real_qoq_pct") < 0


def test_three_debt_definitions_are_not_the_same_series():
    gdp = num(years("gdp_esri")[2024], "gdp_nominal_cy_bn")
    fof = num(years("gg_liabilities_boj")[2024], "gg_liabilities_bn") / gdp * 100
    imf = num(years("gg_fiscal_imf")[2024], "gross_debt_pct_gdp")
    mof = num(years("central_debt_mof")[2024], "total_bn") / gdp * 100
    assert fof > imf > mof
    assert fof == pytest.approx(226.7, abs=0.1)


def test_flow_of_funds_l900_is_assets_not_liabilities():
    row = years("gg_liabilities_boj")[2025]
    assert num(row, "gg_financial_assets_bn") == pytest.approx(948630.8)
    assert num(row, "gg_liabilities_bn") == pytest.approx(1399225.9)
    assert num(row, "gg_liabilities_bn") != num(row, "gg_financial_assets_bn")


def test_vital_rates_use_the_japanese_national_population():
    deaths = num(years("homicide_deaths_mhlw")[2024], "homicide_deaths")
    pop = num(years("population_stat")[2024], "japanese_k") * 1_000
    assert deaths / pop * 100_000 == pytest.approx(0.1845, abs=0.001)


def test_aspiration_pneumonia_starts_only_at_the_2017_code_break():
    data = years("causes_mhlw")
    assert all(not data[y]["aspiration_pneumonia_10601"] for y in range(2006, 2017))
    assert num(data[2017], "aspiration_pneumonia_10601") == 35788


def test_covid_codes_never_cross_the_2023_tabulation_seam():
    data = years("causes_mhlw")
    assert all(not data[y]["covid19_22201"] for y in range(2006, 2023))
    assert num(data[2022], "special_purpose_codes_22200") == 47661
    assert num(data[2023], "covid19_22201") == 38086


def test_the_two_foreigner_registers_never_share_a_row():
    for row in rows("foreign_residents_isa"):
        assert not (row["foreign_residents"] and row["registered_foreigners"])
    data = years("foreign_residents_isa")
    assert num(data[2011], "registered_foreigners") == 2078508
    assert num(data[2012], "foreign_residents") == 2033656


def test_running_year_customs_totals_remain_ytd_only():
    row = years("trade_customs")[2026]
    assert row["exports_jpy_bn"] == row["imports_jpy_bn"] == ""
    assert num(row, "months") == 8
    assert num(row, "exports_ytd_jpy_bn") > 0


def test_fiscal_year_is_keyed_to_its_starting_year():
    row = years("gg_accounts_esri", key="fiscal_year")[2024]
    assert num(row, "gg_net_lending_bn") < 0
    assert num(row, "gg_revenue_bn") > 0
    assert num(row, "gg_expense_bn") > num(row, "gg_revenue_bn")


def test_every_fiscal_account_line_is_drawn_at_october_midpoint():
    fiscal = plate(SLUG, "plate_fiscal")
    series = [
        fiscal.panel("Revenue and expenditure").points("expenditure"),
        fiscal.panel("Overall balance").points("ESRI"),
        fiscal.panel("Interest paid").points("General government"),
    ]
    for points in series:
        assert 2024.75 in points
        assert all(x % 1 == pytest.approx(0.75) for x in points)


def test_cofog_fiscal_years_are_also_drawn_at_october_midpoint():
    panel = plate(SLUG, "plate_spending").panel("Social protection vs")
    points = panel.points("Social protection")
    assert 2024.75 in points
    assert all(x % 1 == pytest.approx(0.75) for x in points)


def test_new_entrants_are_events_and_short_stays_dominate():
    row = years("entrants_isa")[2025]
    assert num(row, "new_entrants") == 39184525
    assert num(row, "new_entrants_non_short_stay") == 726420
    assert num(row, "new_entrants_short_stay") > num(row, "new_entrants_non_short_stay") * 40


def test_nikkei_is_explicitly_non_official_in_the_manifest():
    manifest = yaml.safe_load(
        (Country.load(SLUG).dir / "SOURCES.yaml").read_text(encoding="utf-8"))
    assert manifest["published"]["nikkei_yahoo.csv"]["official"] is False


def test_ti_cpi_is_drawn_from_the_reviewed_historical_series():
    cpi = years("cpi_ti")
    panel = plate(SLUG, "plate_world").panel("Corruption")
    plotted = dict(zip(panel.data_lines()[0].get_xdata(),
                       panel.data_lines()[0].get_ydata()))
    assert plotted[2025] == pytest.approx(num(cpi[2025], "cpi_score"))
    assert plotted[2012] == pytest.approx(74)


def test_net_migration_is_the_un_wpp_model_not_a_national_register():
    migration = years("net_migration_wb")
    population = years("population_stat")
    want = num(migration[2024], "net_migration") / (
        num(population[2024], "population_k") * 1_000
    ) * 1_000
    panel = plate(SLUG, "plate_migration").panel("Net migration")
    bars = {
        round(patch.get_x() + patch.get_width() / 2):
        patch.get_y() + patch.get_height()
        for patch in panel.ax.patches
        if patch.get_data_transform() is panel.ax.transData
    }
    assert bars[2024] == pytest.approx(want)
    migration_plate = next(
        item for item in load_plates(Country.load(SLUG))
        if item.topic == "migration"
    )
    assert "World Bank/UN WPP" in migration_plate.source
    preamble = (DATA / "net_migration_wb.csv").read_text().splitlines()[:2]
    assert any("not Japan's resident-movement register" in line
               for line in preamble)


def test_unavailable_disclosures_exist_in_every_published_language():
    import json

    ui = json.loads((Country.load(SLUG).dir / "ui.json").read_text())
    assert set(ui) == {"ja", "en", "pt"}
    assert all(locale["unavailable"] for locale in ui.values())


def test_road_slot_rejects_the_broader_all_accidents_category():
    panel = plate(SLUG, "plate_security").panel("Road traffic deaths")
    assert not panel.lines()
    text = " ".join(panel.texts()).lower()
    assert "pending" in text
    notes = (Country.load(SLUG).dir / "DATA_NOTES.md").read_text().lower()
    assert "broader\naccident category" in notes


def test_the_cofog_stack_names_all_seven_groups():
    """Issue #3: `_finish` once stripped every in-panel legend, publishing
    the spending stack as seven coloured layers nobody could name. The key
    is part of the chart. The names are plates.py's COFOG7, in draw order.
    """
    want = ["Social protection", "Health", "Education",
            "General public services", "Economic affairs",
            "Defence and public order", "Other"]
    panel = plate(SLUG, "plate_spending").panel("Spending by function")
    assert panel.legend_labels() == want
    for lang in Country.load(SLUG).locale_codes:
        # Slot order is fixed, so the stack is the first panel in any locale.
        first = plate(SLUG, "plate_spending", lang).panels()[0]
        assert len(first.legend_labels()) == 7, \
            f"{lang}: the COFOG key lost entries in translation"


def test_the_cash_benefits_line_is_in_the_key():
    """The dotted cash-benefits line was labelled after the legend was
    built, so the key never named it. The label must land in the legend."""
    panel = plate(SLUG, "plate_spending").panel("Social protection vs")
    assert "of which cash benefits" in panel.legend_labels()
