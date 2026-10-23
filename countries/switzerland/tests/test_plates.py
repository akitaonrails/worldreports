"""Semantic contracts for Switzerland's twelve comparison-spine plates."""
from __future__ import annotations

import csv

import pytest

from core.country import Country
from core.render import load_plates
from tests.probe import plate, plate_names

SLUG = "switzerland"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(
            line for line in fh if not line.lstrip().startswith("#")))


def by_year(rel: str, key: str = "year") -> dict[int, dict]:
    return {int(row[key]): row for row in rows(rel)}


def col(rel: str, field: str) -> dict[int, float]:
    return {year: float(row[field]) for year, row in by_year(rel).items()
            if (row.get(field) or "").strip()}


def test_registry_is_the_twelve_plate_spine_in_order():
    loaded = load_plates(Country.load(SLUG))
    assert [item.filename for item in loaded] == [
        "01-economy.png", "02-fiscal.png", "03-spending.png",
        "04-trade.png", "05-markets.png", "06-credit.png",
        "07-people.png", "08-world.png", "09-demography.png",
        "10-security.png", "11-mortality.png", "12-migration.png",
    ]
    assert plate_names(SLUG) == sorted(
        f"plate_{item.topic}" for item in loaded)


def test_gdp_vintages_agree_through_2022_then_remain_separate():
    bfs = col("macro/gdp_bfs.csv", "gdp_nominal_chf_mn")
    estat = col("macro/gdp_estat.csv", "gdp_chf_mn")
    assert all(bfs[year] == pytest.approx(estat[year])
               for year in range(2006, 2023))
    assert bfs[2023] == pytest.approx(837_159.4)
    assert estat[2023] == pytest.approx(834_189.8)
    panel = plate(SLUG, "plate_economy").panel("Real GDP growth")
    assert panel.points("Eurostat")[2024] == pytest.approx(1.4)
    assert panel.bars()[-1] == pytest.approx(1.61)
    assert any("diverges from 2023" in text for text in panel.texts())


def test_fiscal_plate_selects_general_government_not_five_sectors():
    efv = [row for row in rows("fiscal/general_government_efv.csv")
           if row["sector"] == "general_government"]
    assert len(efv) == len({row["year"] for row in efv})
    point = next(row for row in efv if row["year"] == "2025")
    panel = plate(SLUG, "plate_fiscal").panel("Revenue and expenditure")
    assert panel.points("Revenue, EFV")[2025] == pytest.approx(
        float(point["revenue_pct_gdp"]))
    assert panel.points("Expenditure, EFV")[2025] == pytest.approx(
        float(point["expenditure_pct_gdp"]))
    debt = plate(SLUG, "plate_fiscal").panel("Gross debt")
    assert debt.points("Maastricht")[2025] == pytest.approx(
        float(point["maastricht_debt_pct_gdp"]))


def test_primary_balance_uses_one_eurostat_vintage():
    fiscal = by_year("fiscal/general_government_estat.csv")
    panel = plate(SLUG, "plate_fiscal").panel("Overall and primary")
    want = (float(fiscal[2025]["balance_pct_gdp"])
            + float(fiscal[2025]["interest_pct_gdp"]))
    assert panel.points("Primary balance")[2025] == pytest.approx(want)


def test_trade_partner_shares_use_total_one_and_gold_is_not_spliced():
    table = rows("trade/goods_by_partner_bazg.csv")
    total = next(row for row in table
                 if row["year"] == "2025" and row["partner_code"] == "TOTAL1")
    usa = next(row for row in table
               if row["year"] == "2025" and row["partner"] == "USA")
    expected = float(usa["exports_chf_mn"]) / float(total["exports_chf_mn"]) * 100
    panel = plate(SLUG, "plate_trade").panel("Top export destinations")
    assert panel.points("United States")[2025] == pytest.approx(expected)
    assert any("Total 1 denominator" in text for text in panel.texts())

    gold = plate(SLUG, "plate_trade").panel("gold changes")
    assert min(gold.points("Total 2, incl.")) == 2012
    assert gold.points("Total 2, incl.")[2025] == pytest.approx(461.0141)
    assert gold.points("Non-monetary gold")[2025] == pytest.approx(163.7624)


def test_market_currency_is_reciprocal_and_equity_uses_year_end_fx():
    panel = plate(SLUG, "plate_markets").panel("Franc against")
    fx = panel.data_lines()[0]
    assert float(fx.get_ydata()[0]) == pytest.approx(100)
    assert float(fx.get_ydata()[-1]) > 150, "a stronger franc was inverted"

    smi = col("markets/smi_yahoo.csv", "close")
    monthly = rows("markets/fx_snb.csv")
    eoy = {int(row["month"][:4]): float(row["usd_chf_eom"])
           for row in monthly if row["month"].endswith("-12")}
    expected = smi[2025] / eoy[2025] / (smi[2006] / eoy[2006]) * 100
    equity = plate(SLUG, "plate_markets").panel("SMI in US$")
    assert equity.points("SMI")[2025] == pytest.approx(expected)


def test_credit_slots_use_bis_q4_and_imf_fsi():
    debt = col("credit/household_credit_bis.csv",
               "household_credit_pct_gdp_q4")
    assert debt[2025] == pytest.approx(122.9)
    assert 2026 not in debt
    panel = plate(SLUG, "plate_credit").panel("Household debt")
    assert panel.points("BIS, Q4")[2025] == pytest.approx(122.9)
    npl = col("credit/npl_wb.csv", "npl_pct")
    panel = plate(SLUG, "plate_credit").panel("Non-performing")
    assert panel.data_lines()[0].get_ydata()[-1] == pytest.approx(npl[2025])
    assert any("IMF FSI" in text for text in panel.texts())


def test_people_plate_keeps_three_poverty_concepts_and_no_fake_wage():
    panel = plate(SLUG, "plate_people").panel("Poverty rate")
    assert set(panel.legend_labels()) == {
        "BFS national poverty line", "At risk, below 60% median",
        "US$8.30/day, 2021 PPP",
    }
    gini = plate(SLUG, "plate_people").panel("Income inequality")
    assert gini.points("BFS HABE")[2023] == pytest.approx(30.5)
    wage = plate(SLUG, "plate_people").panel("Minimum wage")
    assert not wage.data_lines()
    assert any("No statutory national minimum wage" in text
               for text in wage.texts())
    real = plate(SLUG, "plate_people").panel("real wages")
    assert len(real.bars()) == len(rows("macro/wages_bfs.csv"))


def test_demography_rates_use_mean_population_and_type_changes():
    balance = by_year("demography/balance_bfs.csv")
    row = balance[2025]
    population = (float(row["pop_1jan"]) + float(row["pop_31dec"])) / 2
    expected = float(row["net_migration_incl_type_change"]) / population * 1_000
    panel = plate(SLUG, "plate_demography").panel("Natural increase")
    assert panel.points("Net migration")[2025] == pytest.approx(expected)


def test_security_keeps_assisted_suicide_separate_across_2009_seam():
    causes = [row for row in rows("mortality/causes_of_death_bfs.csv")
              if row["cause"] == "Suizid"]
    suicide = {int(row["year"]): float(row["deaths_total"])
               for row in causes}
    assisted = col("mortality/assisted_suicide_bfs.csv", "assisted_suicides")
    assert suicide[2008] == pytest.approx(1313)
    assert suicide[2009] == pytest.approx(1105)
    assert assisted[2008] == pytest.approx(253)
    panel = plate(SLUG, "plate_security").panel("firearms and assisted")
    assert panel.points("Assisted suicide")[2024] == pytest.approx(1774)
    assert panel.points("All firearm deaths")[2024] == pytest.approx(204)


def test_mortality_has_fixed_pre_pandemic_baseline():
    deaths = {int(row["year"]): float(row["deaths_total"])
              for row in rows("mortality/causes_of_death_bfs.csv")
              if row["cause"] == "Alle Todesursachen"}
    baseline = sum(deaths[year] for year in range(2015, 2020)) / 5
    panel = plate(SLUG, "plate_mortality").panel("Excess deaths")
    assert any(f"{baseline:,.1f}" in text for text in panel.texts())
    assert panel.bars()[5] == pytest.approx((deaths[2020] / baseline - 1) * 100)


def test_migration_keeps_flows_stocks_and_definition_seams_distinct():
    bfs = by_year("migration/flows_bfs.csv")
    assert float(bfs[2023]["immigration_total"]) == pytest.approx(263_081)
    assert float(bfs[2023]["type_change_foreign"]) == pytest.approx(87_623)
    estat = by_year("migration/flows_estat.csv")
    assert float(estat[2015]["imm_total"]) == pytest.approx(
        float(bfs[2015]["immigration_total"])
        - float(bfs[2015]["type_change_foreign"]))
    assert float(estat[2023]["imm_total"]) == pytest.approx(
        float(bfs[2023]["immigration_total"]))

    panel = plate(SLUG, "plate_migration").panel("asylum, S status")
    assert panel.points("Asylum applicants")[2025] == pytest.approx(25.75)
    assert panel.points("S permit holders")[2025] == pytest.approx(65.26)
    assert "flow" in " ".join(panel.legend_labels()).lower()
    assert "stock" in " ".join(panel.legend_labels()).lower()


@pytest.mark.parametrize("name", plate_names(SLUG))
def test_every_drawn_series_stays_inside_its_panel(name):
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped()
