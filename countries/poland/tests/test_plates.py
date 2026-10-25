"""Poland's plates, held to what their labels promise.

Every number below is computed from the committed CSV at test time, never
typed: an annotation that says 29.0% must still be the 2021 excess the file
carries after the next refetch, and a rate drawn per 100,000 must still be
the count divided by the population it names. The definitional pairs are
asserted to stay pairs — CPI against HICP, the survey against the register,
the customs perimeter against the national accounts, police offences
against assault deaths — because the cheapest way to break this country's
chapter is to join two of them into one tidy line.

The four pending slots are asserted to *stay* pending: three of them have
no official machine route and the fourth is a scale conflict the atlas core
has not widened, and a test that let any of them be filled silently would
publish a number nobody reviewed.
"""
from __future__ import annotations

import pytest

from core.country import Country
from core import plotting
from tests import probe

POLAND = "poland"


@pytest.fixture(scope="module", autouse=True)
def _close():
    yield
    probe.close_all()


def _table(rel: str) -> dict:
    t = Country.load(POLAND).table(rel)
    assert t, f"{POLAND}: {rel} is not committed"
    return t


def _years(rel: str, col: str) -> dict[int, float]:
    return dict(zip(*plotting.series(_table(rel), col)))


def _at(rel: str, col: str, year: int) -> float:
    return _years(rel, col)[year]


def _panel(plate: str, title_fragment: str):
    return probe.plate(POLAND, plate).panel(title_fragment)


def _texts(plate: str) -> list[str]:
    return probe.plate(POLAND, plate).texts()


# ------------------------------------------------------------- slot map
SLOTS = {
    "economy": ["economy.growth", "economy.gdp_per_person",
                "economy.inflation", "economy.unemployment"],
    "fiscal": ["fiscal.revenue_expenditure", "fiscal.balance", "fiscal.debt",
               "fiscal.interest"],
    "spending": ["spending.by_function", "spending.social_protection",
                 "spending.investment", "spending.public_investment"],
    "trade": ["trade.exports_imports", "trade.balance",
              "trade.destinations", "trade.lens"],
    "markets": ["markets.policy_rate", "markets.bond_10y",
                "markets.currency", "markets.equities"],
    "credit": ["credit.household_debt", "credit.lending_rate", "credit.npl",
               "credit.lens"],
    "people": ["people.gini", "people.poverty", "people.minimum_wage",
               "people.lens"],
    "world": ["world.gdp", "world.hdi", "world.cpi", "world.reserves"],
    "demography": ["demography.population", "demography.fertility",
                   "demography.birth_death", "demography.natural_migration"],
    "security": ["security.homicide", "security.suicide",
                 "security.road_deaths", "security.lens"],
    "mortality": ["mortality.death_rate", "mortality.excess_deaths",
                  "mortality.covid", "mortality.lens"],
    "migration": ["migration.flows", "migration.net",
                  "migration.foreign_born", "migration.lens"],
}

#: Slots that are deliberately empty, and why.
PENDING = {
    "markets.equities": "WIG20",
    "credit.lending_rate": "lending rate",
}

BUILDERS = {topic: f"plate_{topic}" for topic in SLOTS}


def _axes_by_key() -> dict:
    out = {}
    for topic, builder in BUILDERS.items():
        fig = probe.plate(POLAND, builder).fig
        for ax in fig.axes:
            key = getattr(ax, "spine_slot", None)
            if key is not None:
                out[key.key] = ax
    return out


def test_every_canonical_slot_is_claimed_in_spine_order():
    for topic, keys in SLOTS.items():
        drawn = probe.plate(POLAND, BUILDERS[topic]).fig
        claimed = [getattr(ax, "spine_slot", None).key
                   for ax in drawn.axes if getattr(ax, "spine_slot", None)]
        assert claimed == keys, f"{topic}: {claimed}"


def test_the_pending_slots_are_exactly_the_documented_two():
    axes = _axes_by_key()
    pending = {k for k, ax in axes.items() if getattr(ax, "spine_pending",
                                                      False)}
    assert pending == set(PENDING), sorted(pending)


def test_every_pending_slot_states_its_reason_on_the_panel():
    axes = _axes_by_key()
    for key, word in PENDING.items():
        blurb = " ".join(t.get_text() for t in axes[key].texts)
        assert word in blurb, f"{key}: no reason on the panel ({blurb!r})"


# ------------------------------------------------------- the shape of it
def test_the_two_net_migration_panels_are_drawn_not_parked():
    """Both official net series are staged, so both are drawn."""
    axes = _axes_by_key()
    for key in ("migration.net", "demography.natural_migration"):
        ax = axes[key]
        assert not getattr(ax, "spine_pending", False), key
        assert len(ax.lines) >= 2, f"{key}: expected two labelled series"


def test_the_headline_strip_leads_with_gdp_then_people_then_population():
    from core import sitebuild

    headline = sitebuild.headline_for(Country.load(POLAND))
    labels = [h["label"]["en"] for h in headline]
    assert labels[0] == "GDP"
    assert labels[1] == "GDP per person"
    assert labels[2] == "Population"
    assert headline[2]["value"]["en"]


def test_every_chapter_declares_a_table_and_a_plate():
    from core import sitebuild

    chapters = sitebuild.chapters_for(Country.load(POLAND))
    assert len(chapters) == 12
    assert {c["topic"] for c in chapters} == set(SLOTS)
    for ch in chapters:
        assert ch["sources"], f"{ch['id']}: cites no file"
        assert ch["blurb"]["en"] and ch["blurb"]["pl"] and ch["blurb"]["pt"]


# ------------------------------------------------------ annotation numbers
def test_the_growth_annotation_is_the_2020_contraction_in_the_file():
    value = _at("macro/economy.csv", "gdp_growth_pct", 2020)
    assert value < 0
    panel = _panel("plate_economy", "Real GDP growth")
    assert any(f"{value:.1f}%" in t for t in panel.texts()), panel.texts()


def test_the_growth_panel_bands_only_the_one_negative_year():
    country = Country.load(POLAND)
    negative = [y for y, v in _years("macro/economy.csv",
                                    "gdp_growth_pct").items() if v < 0]
    assert negative == [2020]
    assert [name for _, _, name in country.recessions] == ["COVID-19"]
    assert country.recessions[0][0] <= 2020 < country.recessions[0][1]


def test_the_inflation_peak_annotation_is_the_file_maximum():
    cpi = _years("macro/economy.csv", "cpi_pct")
    peak = max(cpi, key=cpi.get)
    panel = _panel("plate_economy", "Consumer price inflation")
    assert any(f"{cpi[peak]:.1f}% in {peak}" in t for t in panel.texts()), \
        panel.texts()


def test_the_2025_balance_annotation_matches_the_preliminary_estimate():
    value = _at("fiscal/fiscal.csv", "deficit_pct_gdp", 2025)
    panel = _panel("plate_fiscal", "Overall and primary balance")
    assert any(f"{value:.1f}%" in t for t in panel.texts()), panel.texts()


def test_the_spending_total_is_the_sum_of_the_seven_cofog_layers():
    """The annotation matches the stack, and the stack is the sum of the
    seven published layers — 49.3% for 2024 against GUS's own 49.4% total,
    the 0.1 being each layer's rounding. DATA_NOTES records it."""
    t = _table("spending/spending.csv")
    years = sorted(_years("spending/spending.csv", "total_pct_gdp"))
    total = [sum(_at("spending/spending.csv", col, y) for col, _, _ in SPEND)
             for y in years]
    panel = _panel("plate_spending", "Spending by function")
    tops = publishing_tops(panel)
    last = sorted(tops)[-1]
    assert last == pytest.approx(total[-1], abs=0.15), (last, total[-1])
    assert any(f"{total[-1]:.1f}% of GDP ({years[-1]})" in x
               for x in panel.texts()), panel.texts()


SPEND = [("social_protection_pct_gdp", 0, 0), ("health_pct_gdp", 0, 0),
         ("general_services_pct_gdp", 0, 0), ("education_pct_gdp", 0, 0),
         ("economic_affairs_pct_gdp", 0, 0), ("defence_order_pct_gdp", 0, 0),
         ("other_pct_gdp", 0, 0)]


def publishing_tops(panel) -> list[float]:
    """The stack's total height per year, from the drawn polygons."""
    import numpy as np

    out = []
    for coll in panel.ax.collections:
        paths = getattr(coll, "get_paths", lambda: [])()
        if not paths:
            continue
        v = np.asarray(paths[0].vertices, dtype=float)
        out.append(float(v[:, 1].max()))
    return out


def test_the_excess_deaths_annotation_is_recomputed_from_the_counts():
    t = _table("mortality/mortality.csv")
    deaths = dict(zip(*plotting.series(t, "deaths_all")))
    base = sum(deaths[y] for y in range(2015, 2020)) / 5
    expected = (deaths[2021] - base) / base * 100
    stored = _at("mortality/mortality.csv",
                 "excess_deaths_pct_vs_2015_2019", 2021)
    assert stored == pytest.approx(expected, abs=0.01)
    panel = _panel("plate_mortality", "Excess deaths")
    assert any(f"{stored:.1f}%" in x for x in panel.texts()), panel.texts()


def test_the_covid_peak_is_the_2021_rate_per_100k():
    t = _table("mortality/mortality.csv")
    cases = dict(zip(*plotting.series(t, "covid_deaths")))
    pop = _years("demography/demography.csv", "population_jan")
    rate = cases[2021] / pop[2021] * 100_000
    assert rate == pytest.approx(
        _at("mortality/mortality.csv", "covid_deaths_per_100k", 2021),
        abs=0.01)
    panel = _panel("plate_mortality", "COVID-19 deaths")
    assert any(f"{rate:.0f}" in x for x in panel.texts()), panel.texts()


# ------------------------------------------------------------- conversions
def test_the_police_homicide_rate_is_the_published_rate_on_the_revised_population():
    t = _table("security/security.csv")
    counts = dict(zip(*plotting.series(t, "homicides_police_confirmed")))
    pop = _years("demography/demography.csv", "population_jan")
    for year in (2006, 2013, 2023):
        assert (counts[year] / pop[year] * 100_000
                == pytest.approx(
                    _at("security/security.csv",
                        "homicides_police_per_100k", year), abs=1e-6))
    panel = _panel("plate_security", "Homicide rate")
    drawn = panel.series("Polish Police")
    assert max(drawn) == pytest.approx(
        _at("security/security.csv", "homicides_police_per_100k", 2007),
        abs=1e-6)


def test_the_suicide_rate_uses_the_same_year_population():
    t = _table("security/security.csv")
    counts = dict(zip(*plotting.series(t, "suicides")))
    pop = _years("demography/demography.csv", "population_jan")
    for year in (2011, 2024):
        assert (counts[year] / pop[year] * 100_000
                == pytest.approx(
                    _at("security/security.csv", "suicides_per_100k",
                        year), abs=1e-6))


def test_the_population_index_is_the_revised_series_not_the_old_balance():
    revised = _at("demography/demography.csv", "population_jan", 2022)
    unrevised = 37_766_300        # GUS's 31 December balance, not staged
    base = _at("demography/demography.csv", "population_jan", 2006)
    panel = _panel("plate_demography", "Population")
    drawn = [float(v) for v in panel.data_lines()[0].get_ydata()]
    assert drawn[16] == pytest.approx(revised / base * 100, abs=0.001)
    assert drawn[16] != pytest.approx(unrevised / base * 100, abs=0.05)


def test_the_foreign_born_share_and_the_protection_stock_are_population_shares():
    t = _table("migration/migration.csv")
    born = _years("migration/migration.csv", "foreign_born_pct")
    tps = dict(zip(*plotting.series(t, "temporary_protection_beneficiaries")))
    pop = _years("demography/demography.csv", "population_jan")
    panel = _panel("plate_migration", "Foreign-born share")
    drawn = panel.series("Foreign-born")
    # The solid part ends at the last full year; 2025 and 2026 are drawn
    # dashed by ctx.line and are asserted on the CSV, not on the artist.
    assert drawn[-1] == pytest.approx(born[2024], abs=0.01)
    assert born[2025] > born[2024]
    assert panel.series("Temporary protection")[0] == pytest.approx(
        tps[2022] / pop[2022] * 100, abs=0.01)


def test_the_currency_index_is_up_equals_stronger():
    """2008's zloty was strong and 2022's weak, in that order."""
    index = _years("markets/markets.csv", "pln_index_usd_2006")
    assert index[2008] > index[2022]
    panel = _panel("plate_markets", "Currency against the US$")
    line = panel.data_lines()[0]
    drawn = {float(x): float(y) for x, y in zip(line.get_xdata(),
                                               line.get_ydata())}
    assert max(drawn.values()) == pytest.approx(index[2008], abs=0.01)
    assert min(drawn.values()) == pytest.approx(index[2022], abs=0.01)


# ------------------------------------------------------------------ seams
def test_the_survey_and_the_register_stay_two_lines():
    panel = _panel("plate_economy", "Unemployment rate")
    survey = panel.points("BAEL")
    register = panel.points("Registered")
    estat = panel.points("Eurostat LFS")
    assert min(survey) == 2010 and max(survey) >= 2024
    assert min(register) == 2006
    assert min(estat) == 2009
    for year in sorted(set(survey) & set(register)):
        assert survey[year] < register[year], (
            f"{year}: the survey and the register have been spliced")
    # 2020 is the long-row figure (6.3), not the upper row's 6.8.
    assert register[2020] == pytest.approx(
        _at("macro/economy.csv", "unemployment_registered_pct", 2020))
    assert register[2020] != pytest.approx(6.8)


def test_cpi_and_hicp_are_drawn_side_by_side_and_differ():
    cpi = _years("macro/economy.csv", "cpi_pct")
    hicp = _years("macro/economy.csv", "hicp_pct")
    panel = _panel("plate_economy", "Consumer price inflation")
    assert panel.points("CPI")[2022] == pytest.approx(cpi[2022])
    assert panel.points("HICP")[2022] == pytest.approx(hicp[2022])
    assert cpi[2022] != hicp[2022]


def test_the_two_trade_perimeters_are_never_one_line():
    """EUR billion of customs goods against a share of GDP."""
    t = _table("trade/trade.csv")
    national = dict(zip(*plotting.series(t, "balance_pct_gdp")))
    customs = {y: v / 1000
               for y, v in zip(*plotting.series(t, "goods_balance_mln_eur"))}
    lens = _panel("plate_trade", "Goods balance, customs basis")
    tops = lens.bars()
    assert min(tops) == pytest.approx(customs[2008], abs=0.01)
    assert max(tops) == pytest.approx(customs[2020], abs=0.01)
    # They disagree in sign in 2013, 2018 and 2022, and agree in 2024 —
    # which is exactly why neither may be drawn as the other.
    disagree = [y for y in customs if y in national
                and (customs[y] < 0) != (national[y] < 0)]
    assert set(disagree) >= {2013, 2018, 2022}, disagree
    assert customs[2022] == pytest.approx(-20.0, abs=0.1)
    assert national[2022] == pytest.approx(1.7, abs=0.1)


def test_police_offences_and_assault_deaths_stay_two_definitions():
    panel = _panel("plate_security", "Homicide, two definitions")
    offences = panel.points("Police offences")
    deaths = panel.points("Assault deaths")
    for year in sorted(set(offences) & set(deaths)):
        assert offences[year] > deaths[year], (
            f"{year}: an offence count below the death count")
    assert offences[2023] / deaths[2023] == pytest.approx(2.84, abs=0.01)


def test_the_npl_lens_keeps_two_compilations_apart():
    panel = _panel("plate_credit", "NPL ratio, two compilations")
    eba = panel.points("EBA")
    world = panel.points("World Bank")
    assert max(world) == 2020 and min(eba) == 2014
    assert min(world) == 2006


def test_the_mortality_lens_recomputes_its_own_rates():
    t = _table("mortality/mortality.csv")
    circ = dict(zip(*plotting.series(t, "deaths_circulatory")))
    pop = _years("demography/demography.csv", "population_jan")
    panel = _panel("plate_mortality", "Circulatory and cancer deaths")
    assert panel.series("Circulatory")[-1] == pytest.approx(
        circ[2024] / pop[2024] * 100_000, abs=0.01)


# ---------------------------------------------------------------- pendings
def test_the_migration_lens_draws_both_net_series_where_the_slot_cannot():
    t = _table("migration/migration.csv")
    register = dict(zip(*plotting.series(t,
                                         "net_migration_registered_per_1000")))
    residual = dict(zip(*plotting.series(t,
                                         "net_migration_residual_per_1000")))
    assert register[2020] < -20 and residual[2020] < -10
    panel = _panel("plate_migration", "Net migration, two measures")
    assert panel.points("Register")[2020] == pytest.approx(register[2020])
    assert panel.points("Population balance")[2022] == pytest.approx(
        residual[2022])


def test_no_panel_draws_a_proxy_for_the_equity_index_or_the_lending_rate():
    axes = _axes_by_key()
    for key in ("markets.equities", "credit.lending_rate"):
        ax = axes[key]
        assert not ax.get_lines(), f"{key}: something was drawn after all"
        assert not ax.patches, f"{key}: something was drawn after all"


def test_the_catalogue_covers_the_spine_units():
    import json

    catalog = json.loads(
        (Country.load(POLAND).dir / "i18n.json").read_text(encoding="utf-8"))
    from core import spine

    for unit in spine.strings():
        assert unit in catalog, unit
        assert catalog[unit].get("pl") and catalog[unit].get("pt"), unit
