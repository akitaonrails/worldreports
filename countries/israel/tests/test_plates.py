"""Semantic boundaries published by Israel's eight spine plates."""
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


def test_registry_keeps_the_eight_supported_spine_topics():
    ps = load_plates(Country.load(SLUG))
    assert [p.filename.split("-", 1)[0] for p in ps] == [
        f"{n:02d}" for n in range(1, 9)
    ]
    assert [p.topic for p in ps] == [
        "economy", "fiscal", "trade", "markets", "world",
        "demography", "security", "migration",
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
    panel = plate(SLUG, "plate_migration").panel("New olim")
    assert panel.bars()[list(panel.bars()).index(max(panel.bars()))] == \
        pytest.approx(want)
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


def test_unsupported_slots_are_explicitly_pending():
    checks = [
        ("plate_fiscal", "Interest paid"),
        ("plate_trade", "destinations"),
        ("plate_markets", "Policy rate"),
        ("plate_markets", "10-year"),
        ("plate_world", "Corruption"),
        ("plate_migration", "Foreign-born"),
    ]
    for builder, title in checks:
        panel = plate(SLUG, builder).panel(title)
        assert not panel.data_lines()
        assert any("pending" in text.lower() for text in panel.texts())
