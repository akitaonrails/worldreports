"""Does each line on a Brazilian plate mean what its label says?

This repository has the scar that makes the question worth asking: the
S&P 500 converted *into* reais was once labelled "(USD)" and the native
dollar index "(in BRL)". The panel measured perfectly and said the
opposite of the truth, and it was caught by eye months later.

Each test below states a relationship between a label and the numbers
drawn under it, or between a drawn rate and the count and population it
was computed from, so a swapped label or a wrong denominator fails the
build. The generic checks — isolation, catalogs, data hygiene, the spine,
the built pages — live in tests/ and run against every country.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tests.probe import plate, plate_names

SLUG = "brasil"
DATA = Path(__file__).resolve().parent.parent / "data"


def column(rel: str, name: str) -> dict[int, float]:
    with open(DATA / rel, encoding="utf-8") as f:
        return {int(r["year"]): float(r[name]) for r in csv.DictReader(f)
                if r.get(name) not in (None, "")}


def close(a: float, b: float, rel: float = 1e-6) -> bool:
    return abs(a - b) <= rel * max(1.0, abs(b))


def bars(panel) -> dict[float, float]:
    """{x: height} for the bars drawn in data space."""
    ax = panel.ax
    return {round(p.get_x() + p.get_width() / 2, 6): p.get_height()
            for p in ax.patches
            if p.get_data_transform() is ax.transData
            and hasattr(p, "get_height")}


# ------------------------------------------------------------ markets
def test_the_ibovespa_in_dollars_is_the_close_over_the_exchange_rate():
    """Index 2006 = 100 of close ÷ year-end PTAX. Dividing by the rate
    instead of multiplying is the swap this file exists to catch: the
    line would then rise when the real fell."""
    ib = column("markets/ibov.csv", "close")
    fx = column("macro/dollar.csv", "eop")
    pts = plate(SLUG, "fig_markets").panel("equity index").points("Ibovespa")
    want = ib[2025] / fx[2025] / (ib[2006] / fx[2006]) * 100
    assert close(pts[2025], want), (pts[2025], want)
    assert close(pts[2006], 100)


def test_the_sp500_and_the_ibovespa_start_together():
    panel = plate(SLUG, "fig_markets").panel("equity index")
    assert close(panel.points("S&P")[2006], 100)
    assert close(panel.points("Ibovespa")[2006], 100)


def test_the_currency_index_rises_when_the_real_strengthens():
    """fx_index inverts R$ per US$: 2011, the real's strongest year,
    must sit above 2006, and 2020's slump far below it."""
    pts = plate(SLUG, "fig_markets").panel("real against").points("BRL")
    avg = column("macro/dollar.csv", "avg")
    assert close(pts[2020], avg[2006] / avg[2020] * 100)
    assert pts[2011] > 100 > pts[2020]


# ------------------------------------------------------------- fiscal
def test_canonical_debt_panel_contains_only_gross_definitions():
    """The IMF and BCB gross perimeters can share the canonical slot;
    DLSP net debt cannot inherit a gross-debt axis."""
    panel = plate(SLUG, "fig_fiscal").panel("gross debt")
    for _, imf, dbgg in panel.paired("(IMF)", "DBGG"):
        assert imf > dbgg
    assert not any("DLSP" in label for label in panel.legend_labels())


def test_the_tax_burden_is_not_drawn_across_its_2010_break():
    """STN's 2010 method drops FGTS and Sistema S and has no
    recalculation before it. The labelled line starts at the break and
    the old years are a separate, unlabelled segment."""
    panel = plate(SLUG, "fig_fiscal").panel("revenue and expenditure")
    new = panel.points("Tax burden")
    assert min(new) == 2010
    old = [ln for ln in panel.data_lines()
           if ln.get_label().startswith("_")
           and max(ln.get_xdata()) <= 2009 and len(ln.get_xdata()) >= 3]
    assert old, "the pre-2010 tax burden is not drawn as its own segment"


def test_imf_net_interest_is_primary_minus_overall():
    gg_p = column("fiscal/general_government.csv", "primary_balance_pct_gdp")
    gg_b = column("fiscal/general_government.csv", "balance_pct_gdp")
    pts = plate(SLUG, "fig_fiscal").panel("interest paid").points("IMF")
    assert close(pts[2025], gg_p[2025] - gg_b[2025])


# ----------------------------------------------------------- security
def test_estimated_homicides_are_never_below_registered():
    """The estimated series adds the deaths hidden in the
    undetermined-intent pool, so it is an upper bound on the registered
    rate, never a lower one.

    An earlier version of this test looked on the wrong panel, found no
    series it recognised, and skipped — so it checked nothing at all for
    as long as that was true. It now asserts the overlap exists.
    """
    panel = plate(SLUG, "fig_security").panel("homicide rate")
    pairs = panel.paired("estimated", "registered")
    assert len(pairs) >= 10, "the two series barely overlap"
    below = [(int(y), e, r) for y, e, r in pairs if e < r]
    assert not below, f"estimated below registered in {below[:4]}"


def test_the_two_homicide_systems_stay_two_lines():
    """FBSP counts violent intentional deaths where they happened; IPEA
    reads death certificates where the victim lived. They disagree by
    design and must never be merged into one line."""
    labels = plate(SLUG, "fig_security").panel("homicide rate").lines()
    blob = " ".join(labels).lower()
    assert "fbsp" in blob and "ipea" in blob
    assert len(labels) >= 3


def test_the_fbsp_line_is_the_published_rate():
    """FBSP publishes MVI per 100,000; the plate draws theirs rather than
    recomputing it (PLATE_SPINE.md rule 5)."""
    pts = plate(SLUG, "fig_security").panel("homicide rate").points("FBSP")
    assert close(pts[2025], column("social/violence_fbsp.csv", "mvi_rate")[2025])


def test_police_killings_are_per_100k_residents_of_the_same_year():
    pk = column("social/violence_fbsp.csv", "police_killings")
    pop = column("social/population.csv", "pop_mn")
    pts = plate(SLUG, "fig_security").panel("police").points("Deaths following police intervention")
    assert close(pts[2025], pk[2025] / (pop[2025] * 1e6) * 1e5)


def test_femicides_are_per_100k_women_and_a_subset_of_womens_homicides():
    """Every femicide is a homicide of a woman; both are divided by the
    female population of the same year, not by everyone."""
    fem = column("social/violence_fbsp.csv", "femicides")
    women = column("social/demography.csv", "population_female")
    panel = plate(SLUG, "fig_security").panel("police")
    pts = panel.points("femicide")
    assert close(pts[2025], fem[2025] / women[2025] * 1e5)
    pairs = panel.paired("femicide", "All homicides of women")
    assert pairs, "the two series never overlap"
    assert all(f <= t for _, f, t in pairs)


def test_suicide_and_road_rates_divide_sim_counts_by_ibge_population():
    deaths = DATA / "social/deaths.csv"
    assert deaths.exists()
    sui = column("social/deaths.csv", "suicide")
    road = column("social/deaths.csv", "road")
    pop = column("social/population.csv", "pop_mn")
    fig = plate(SLUG, "fig_security")
    assert close(fig.panel("suicide").points("SIM")[2024],
                 sui[2024] / (pop[2024] * 1e6) * 1e5)
    assert close(fig.panel("road").points("SIM")[2024],
                 road[2024] / (pop[2024] * 1e6) * 1e5)


# ---------------------------------------------------------- mortality
def test_the_crude_death_rate_is_registered_deaths_per_1000():
    reg = column("social/deaths.csv", "registered")
    pop = column("social/population.csv", "pop_mn")
    pts = plate(SLUG, "fig_epidemics").panel("crude death").points("Registered")
    assert close(pts[2021], reg[2021] / (pop[2021] * 1e6) * 1e3)


def test_excess_deaths_are_measured_against_2015_to_2019():
    reg = column("social/deaths.csv", "registered")
    base = sum(reg[y] for y in range(2015, 2020)) / 5
    drawn = bars(plate(SLUG, "fig_epidemics").panel("excess"))
    assert close(drawn[2021], (reg[2021] / base - 1) * 100)
    assert min(drawn) == 2015, "pre-baseline years read as a death deficit"


def test_covid_is_per_100k_and_never_drawn_before_2020():
    """B34 before 2020 is unspecified viral deaths, not COVID-19."""
    cv = column("social/epidemic_deaths.csv", "covid")
    pop = column("social/population.csv", "pop_mn")
    drawn = bars(plate(SLUG, "fig_epidemics").panel("covid"))
    assert min(drawn) == 2020
    assert close(drawn[2021], cv[2021] / (pop[2021] * 1e6) * 1e5)


# ------------------------------------------------------------- people
def test_the_minimum_wage_is_converted_at_the_years_average_rate():
    mw = column("macro/minimum_wage.csv", "value")
    fx = column("macro/dollar.csv", "avg")
    pts = plate(SLUG, "fig_people").panel("minimum wage").points("PTAX")
    assert close(pts[2025], mw[2025] / fx[2025])


def test_the_gini_is_drawn_on_the_0_to_100_scale_not_inverted():
    panel = plate(SLUG, "fig_people").panel("gini")
    lo, hi = panel.ylim()
    assert lo < hi
    ib = column("social/gini.csv", "ibge")
    assert close(panel.points("IBGE")[2024], ib[2024] * 100)


def test_pnad_and_pme_unemployment_are_never_spliced():
    panel = plate(SLUG, "fig_economy").panel("unemployment")
    pnad, pme = panel.points("PNAD"), panel.points("PME")
    assert min(pnad) == 2012 and max(pme) <= 2012


# -------------------------------------------------------------- world
def test_the_pre_2012_corruption_scores_are_a_separate_segment():
    """TI rebased the index in 2012 and says only 2012+ is comparable."""
    panel = plate(SLUG, "fig_world").panel("corruption")
    assert min(panel.points("2012+")) == 2012
    assert max(panel.points("old 0–10")) == 2011


# ----------------------------------------------------------- clipping
@pytest.mark.parametrize("name", plate_names(SLUG))
def test_nothing_is_clipped(name):
    """A hardcoded set_ylim silently hides data once the series grows past
    it; a GDP-per-capita panel once clipped its own 2011 peak, and the
    reader simply never learned the peak was there."""
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped(slack=1e-6)


def test_every_plate_renders():
    """The renderer catches a failing plate so one does not stop the rest,
    which means a broken figure reaches the site unless something fails
    loudly here."""
    assert len(plate_names(SLUG)) == 12


def test_migration_census_stock_and_definition_gate():
    stock = column("migration/stock_census.csv", "foreign_born")
    citizen = column("migration/stock_census.csv", "foreign_citizens")
    assert stock[2022] == 1_064_056
    assert citizen[2022] == 793_000
    # The failed 2020 identity is why no gross-flow CSV is published.
    assert not (DATA / "migration/flows_ibge.csv").exists()
