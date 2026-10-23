"""Semantic boundaries asserted by Vietnam's twelve plates."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from core.country import Country
from core.render import load_plates
from tests.probe import plate

SLUG = "vietnam"
DATA = Country.load(SLUG).data_dir


def rows(rel):
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(x for x in fh if not x.startswith("#")))


def years(rel, col):
    return {int(r["year"]): float(r[col]) for r in rows(rel)
            if (r.get(col) or "").strip()}


def test_registry_is_twelve_spine_topics():
    p = load_plates(Country.load(SLUG))
    assert [x.filename for x in p] == [
        "01-economy.png","02-fiscal.png","03-spending.png","04-trade.png",
        "05-markets.png","06-credit.png","07-people.png","08-world.png",
        "09-demography.png","10-security.png","11-mortality.png","12-migration.png"]
    assert [x.topic for x in p] == ["economy","fiscal","spending","trade","markets","credit","people","world","demography","security","mortality","migration"]


def test_gdp_scale_seam_is_not_spliced():
    panel = plate(SLUG,"plate_economy").panel("GDP per person")
    assert max(panel.points("old GDP scale")) == 2009
    assert min(panel.points("revalued GDP scale")) == 2010


def test_fiscal_lines_are_general_government():
    panel = plate(SLUG,"plate_fiscal").panel("Revenue and expenditure")
    table = years("fiscal/gg_finance.csv","revenue_pct_gdp")
    assert panel.points("General-government revenue")[2022] == pytest.approx(table[2022])


def test_trade_destinations_use_total_goods_exports():
    rr = [r for r in rows("trade/exports_by_partner.csv") if r["year"]=="2025"]
    total = float(next(r["exports_usd_mn"] for r in rr if r["kind"]=="total"))
    us = float(next(r["exports_usd_mn"] for r in rr if r["partner_iso3"]=="USA"))
    assert us/total*100 == pytest.approx(32.24, abs=0.01)
    assert plate(SLUG,"plate_trade").panel("destinations").points("USA")[2025] == pytest.approx(us/total*100)


def test_currency_index_is_inverted():
    rate = years("markets/usdvnd.csv","usdvnd_avg")
    line = plate(SLUG,"plate_markets").panel("VND against").data_lines()[0]
    points = dict(zip(line.get_xdata(),line.get_ydata()))
    assert points[2024] == pytest.approx(rate[2006]/rate[2024]*100)


def test_credit_substitute_is_labelled_not_household_debt():
    p = plate(SLUG,"plate_credit").panel("Credit to the economy")
    assert "Private-sector credit (World Bank)" in p.legend_labels()
    assert any("no household-debt" in t for t in p.texts())


def test_gini_method_segments_do_not_join():
    p = plate(SLUG,"plate_people").panel("Gini")
    assert max(p.points("old segment")) == 2019
    assert min(p.points("2020-on")) == 2020


def test_road_death_counts_use_same_year_population_and_break():
    pop = years("demography/population.csv","population_total_thousand")
    road = years("security/traffic_fire.csv","traffic_deaths_from2022")
    p = plate(SLUG,"plate_security").panel("Road traffic")
    assert p.points("Police, 2022-on")[2022] == pytest.approx(road[2022]/(pop[2022]*1000)*1e5)
    assert max(p.points("Police, old series")) == 2021


def test_covid_is_who_model_not_registered_deaths():
    p = plate(SLUG,"plate_mortality").panel("COVID-19")
    assert p.data_lines()
    assert any("WHO GHE model" in t for t in p.texts())


def test_migration_omits_the_2006_model_artefact():
    p = plate(SLUG,"plate_migration").panel("Net migration")
    assert 2006 not in set(p.data_lines()[0].get_xdata())
    assert any("artefact omitted" in t for t in p.texts())


def test_no_plate_reads_fetch_sidecars():
    import json
    prov=json.loads((DATA.parent/"provenance.json").read_text())
    assert not [f for fs in prov.values() for f in fs if "_from_" in f or "_check" in f]
