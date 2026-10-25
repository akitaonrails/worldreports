"""Korea's own plate layer: its reading helpers, its conversions, its
political calendar, and the relationships its panels assert.

Everything here is specific to this country. The spine itself — frame,
slot order, reference scales, the "scale extended" marker — is held for
every country by tests/test_spine.py; this file asks whether the numbers
Korea's panels draw are the right numbers: that a rate is the count over
the right population, that two surveys are never spliced, that a label
names the line it sits on.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import pytest  # noqa: E402

from core.context import Context  # noqa: E402
from core.country import Country  # noqa: E402
from core.sideload import sibling  # noqa: E402
from tests.probe import plate  # noqa: E402

SLUG = "south-korea"
COUNTRY = Country.load(SLUG)
plates = sibling(str(COUNTRY.dir / "plates.py"), "plates")
events = sibling(str(COUNTRY.dir / "events.py"), "events")
NAMES = [entry["builder"].__name__ for entry in plates.PLATES]


@pytest.fixture(scope="module")
def ctx():
    return Context(COUNTRY)


@pytest.fixture
def ax():
    figure, axes = plt.subplots()
    yield axes
    plt.close(figure)


def S(ctx, rel, col):
    return plates._series(ctx, rel, col)


# ------------------------------------------------------------- reading
def test_series_reads_a_column(ctx):
    gdp = S(ctx, "macro/gdp.csv", "nominal_krw_tn")
    assert gdp[2006] > 900 and gdp[2025] > 2500


def test_a_blank_year_stays_a_gap(ctx):
    """2026 exists in the file and is empty, and nothing in the stack may
    invent a value for it."""
    births = S(ctx, "social/vital.csv", "births")
    assert 2025 in births
    assert 2026 not in births


def test_a_missing_file_is_empty_rather_than_an_error(ctx):
    assert S(ctx, "macro/does-not-exist.csv", "value") == {}


def test_series_skips_a_non_numeric_column_instead_of_failing(ctx):
    assert S(ctx, "trade/destinations.csv", "destiny") == {}


def test_series_can_be_cut_to_a_window(ctx):
    pop = plates._series(ctx, "social/population.csv", "pop_mn",
                         first=2006, last=2025)
    assert min(pop) == 2006 and max(pop) == 2025


def test_xy_keeps_years_and_values_aligned():
    data = {2010: 1.0, 2008: 2.0, 2009: 3.0}
    assert plates._xy(data) == ([2008, 2009, 2010], [2.0, 3.0, 1.0])


def test_last_is_the_latest_year_not_the_largest_value():
    assert plates._last({2008: 9.0, 2020: 1.0}) == (2020, 1.0)
    assert plates._last({}) == (None, None)


def test_surpluses_and_deficits_get_different_colours(ctx):
    colour = plates._signed(ctx)
    assert colour(1.5) == ctx.p.BLUE and colour(-3.7) == ctx.p.RED


# ---------------------------------------------------------- conversions
def test_the_homicide_denominator_is_the_release_s_own(ctx):
    """Deaths of Korean nationals over the registered Korean-national
    population: total deaths ÷ the all-cause rate recovers it, and it is
    smaller than the projection population, which counts foreigners."""
    pop = plates.kostat_population(ctx)
    deaths = S(ctx, "social/vital.csv", "deaths")[2024]
    rate = S(ctx, "social/mortality.csv", "all_causes")[2024]
    assert pop[2024] == pytest.approx(deaths / rate * 100_000)
    assert 50.9e6 < pop[2024] < 51.1e6
    projection = S(ctx, "macro/gdp.csv", "population_mn")[2024] * 1e6
    assert projection - pop[2024] > 0.5e6


def test_homicide_per_100k_is_the_count_over_that_population(ctx):
    years, rates = plates.homicide_rate(ctx)
    got = dict(zip(years, rates))
    count = S(ctx, "social/homicide.csv", "deaths")
    pop = plates.kostat_population(ctx)
    for y in (2014, 2024, 2025):
        assert got[y] == pytest.approx(count[y] / pop[y] * 100_000)
    # and it reproduces the one-decimal rate the release prints: 0.6
    assert round(got[2024], 1) == 0.6


def test_the_minimum_wage_is_209_hours_at_the_average_rate(ctx):
    usd = plates.minimum_wage_usd(ctx)
    assert plates.MONTHLY_HOURS == 209
    assert usd[2025] == pytest.approx(10030 * 209 / 1421.17)
    assert 1400 < usd[2025] < 1550


def test_net_migration_is_per_1000_of_the_total_population(ctx):
    years, rates = plates.net_migration_rate(ctx)
    got = dict(zip(years, rates))
    net = S(ctx, "social/migration.csv", "net")[2023]
    pop = S(ctx, "social/population.csv", "pop_mn")[2023] * 1e6
    assert got[2023] == pytest.approx(net / pop * 1000)
    assert got[2021] < 0 < got[2023]


def test_excess_deaths_are_measured_against_the_2015_2019_average(ctx):
    deaths = S(ctx, "social/vital.csv", "deaths")
    base = sum(deaths[y] for y in range(2015, 2020)) / 5
    excess = plates.excess_deaths(ctx)
    assert excess[2022] == pytest.approx((deaths[2022] / base - 1) * 100)
    assert abs(sum(excess[y] for y in range(2015, 2020))) < 1e-9


# -------------------------------------------------------------- events
def test_every_presidency_is_contiguous():
    for (_, end, name, _), (start, *_) in zip(events.PRESIDENTS,
                                              events.PRESIDENTS[1:]):
        assert start >= end, f"{name}'s term overlaps the next"
        assert start - end < 0.2, f"there is a gap after {name}"


def test_the_two_impeachments_are_mid_year():
    ends = {name: end for _, end, name, _ in events.PRESIDENTS}
    assert 2017.0 < ends["Park"] < 2017.5
    assert 2025.0 < ends["Yoon"] < 2025.5


def test_term_boundaries_skip_the_term_that_starts_before_the_window():
    marks = events.term_boundaries(2006, 2026)
    assert [name for _, name in marks] == ["Lee M-b", "Park", "Moon", "Yoon",
                                           "Lee J-m"]


def test_every_shock_falls_inside_the_window():
    for name, (x, _) in events.SHOCKS.items():
        assert 2006 <= x <= 2027, f"{name} is outside the atlas window"


def test_every_band_runs_forwards():
    for name, (start, end, _) in events.BANDS.items():
        assert end > start, f"band {name} ends before it begins"


# ------------------------------------------------------------ registry
def test_the_registry_and_the_chapters_agree_on_the_plates():
    """Two lists name the twelve plates, and every card has its figure."""
    from core import sitebuild
    from core.render import load_plates

    drawn = {pl.filename[:-4] for pl in load_plates(COUNTRY)}
    carded = {ch["id"] for ch in sitebuild.chapters_for(COUNTRY)}
    assert drawn == carded and len(carded) == 12
    for plate_id in carded:
        assert (COUNTRY.out_dir / f"{plate_id}.png").exists(), \
            f"card {plate_id} has no rendered plate"


def test_the_mortality_chapter_is_new_and_the_safety_one_kept_its_id():
    from core import sitebuild
    topics = {ch["id"]: ch["topic"] for ch in sitebuild.chapters_for(COUNTRY)}
    assert topics["09_safety"] == "security"
    assert topics["11_mortality"] == "mortality"


# ----------------------------------------------------------- semantics
def test_births_fall_below_deaths_in_2020_and_stay_there(ctx):
    births = S(ctx, "social/vital.csv", "births")
    deaths = S(ctx, "social/vital.csv", "deaths")
    shared = sorted(set(births) & set(deaths))
    before = [y for y in shared if y < 2020 and births[y] <= deaths[y]]
    assert not before, f"deaths already exceeded births in {before}"
    after = [y for y in shared if y >= 2020]
    assert after and all(deaths[y] > births[y] for y in after)


def test_the_demography_panel_names_both_rates_and_the_crossing(ctx):
    panel = plate(SLUG, "plate_demography").panel("crude birth")
    assert "2020" in " ".join(panel.texts())
    births = panel.points("Births per 1,000")
    deaths = panel.points("Deaths per 1,000")
    cbr = S(ctx, "social/vital.csv", "crude_birth_rate")
    assert births[2019] == cbr[2019]
    assert births[2019] > deaths[2019] and births[2020] < deaths[2020]


def test_the_two_gini_surveys_are_never_joined(ctx):
    panel = plate(SLUG, "plate_people").panel("Gini")
    hfws = panel.points("Household Finance")
    hies = panel.points("Household Income")
    assert min(hfws) == 2011 and max(hies) == 2016
    assert hfws[2011] == pytest.approx(
        S(ctx, "social/gini.csv", "hfws")[2011] * 100)
    assert hies[2011] == pytest.approx(
        S(ctx, "social/gini.csv", "hies")[2011] * 100)


def test_the_fiscal_seam_is_drawn_as_a_seam(ctx):
    """The IMF series starts in 2012; the Bank of Korea's covers the years
    before it as its own segment, and the two never share a year."""
    panel = plate(SLUG, "plate_fiscal").panel("Revenue and expenditure")
    imf = panel.points("Revenue, IMF")
    bok = panel.points("Revenue, BOK")
    assert min(imf) == 2012 and max(bok) == 2011
    assert not set(imf) & set(bok)


def test_homicide_is_drawn_from_two_systems_and_labelled(ctx):
    panel = plate(SLUG, "plate_safety").panel("Homicide")
    national = panel.points("Statistics Korea")
    unodc = panel.points("UNODC")
    years, rates = plates.homicide_rate(ctx)
    assert national == pytest.approx(dict(zip(years, rates)))
    assert unodc[2019] == S(ctx, "social/security_intl.csv",
                            "homicide_unodc")[2019]
    assert panel.ax.get_yscale() == "log"


def test_workplace_deaths_are_per_100k_workers_not_people(ctx):
    panel = plate(SLUG, "plate_safety").panel("workplace")
    line = panel.points("Per 100,000 workers")
    assert line[2006] == pytest.approx(
        S(ctx, "social/workplace.csv", "fatal_rate")[2006] * 10)
    assert "insured workers" in panel.ax.get_ylabel()


def test_the_kospi_line_is_in_dollars(ctx):
    panel = plate(SLUG, "plate_markets").panel("equity")
    kospi = S(ctx, "markets/kospi.csv", "close")
    eop = S(ctx, "macro/won.csv", "eop")
    got = panel.points("KOSPI in US$")
    want = kospi[2025] / eop[2025] / (kospi[2006] / eop[2006]) * 100
    assert got[2006] == pytest.approx(100)
    assert got[2025] == pytest.approx(want)


def test_the_won_index_rises_when_the_won_strengthens(ctx):
    panel = plate(SLUG, "plate_markets").panel("Currency")
    idx = panel.points("Won")
    avg = S(ctx, "macro/won.csv", "avg")
    assert idx[2025] == pytest.approx(avg[2006] / avg[2025] * 100)
    assert idx[2025] < 100 < avg[2025] / avg[2006] * 100


def test_deflation_would_not_be_cut_off(ctx):
    """The old CPI axis started at zero. On the spine it starts at -2."""
    panel = plate(SLUG, "plate_economy").panel("inflation")
    assert panel.ylim()[0] <= -2


def test_migration_citizenship_rows_sum_to_the_official_totals(ctx):
    total = {column: S(ctx, "social/migration.csv", column)
             for column in ("arrivals", "departures", "net")}
    split = {column: S(ctx, "migration/flows_by_citizenship.csv", column)
             for column in ("korean_arrivals", "korean_departures",
                            "korean_net", "foreign_arrivals",
                            "foreign_departures", "foreign_net")}
    for year in total["net"]:
        assert total["arrivals"][year] == (
            split["korean_arrivals"][year] + split["foreign_arrivals"][year])
        assert total["departures"][year] == (
            split["korean_departures"][year] + split["foreign_departures"][year])
        assert total["net"][year] == (
            split["korean_net"][year] + split["foreign_net"][year])
    assert total["net"][2024] == 125_403
    assert split["korean_net"][2024] == 27_647
    assert split["foreign_net"][2024] == 97_756


def test_register_census_stock_keeps_its_own_denominator(ctx):
    total = S(ctx, "migration/foreign_residents_census.csv",
              "total_population_thousands")
    foreign = S(ctx, "migration/foreign_residents_census.csv",
                "foreign_citizens_thousands")
    share = S(ctx, "migration/foreign_residents_census.csv",
              "foreign_citizen_share_pct")
    assert (total[2024], foreign[2024], share[2024]) == (51_806, 2_043, 3.9)
    # Counts are published rounded to thousands; the displayed one-decimal
    # share must still agree after rounding on that same census perimeter.
    assert round(foreign[2024] / total[2024] * 100, 1) == share[2024]


def test_migration_plate_uses_rates_and_the_fixed_comparison_scales(ctx):
    flows = plate(SLUG, "plate_migration").panel("Immigration and emigration")
    immigration = flows.points("Immigration")
    population = S(ctx, "social/population.csv", "pop_mn")[2025] * 1e6
    arrivals = S(ctx, "social/migration.csv", "arrivals")[2025]
    assert immigration[2025] == pytest.approx(arrivals / population * 1000)
    assert flows.ylim() == pytest.approx((0, 50))

    net = plate(SLUG, "plate_migration").panel("Net migration")
    assert net.ylim() == pytest.approx((-30, 45))
    stock = plate(SLUG, "plate_migration").panel("Foreign-citizen share")
    assert stock.points("Resident foreigners at 1 November")[2024] == 3.9
    assert stock.ylim() == pytest.approx((0, 50))


def test_citizenship_lens_reconstructs_total_net_rate(ctx):
    panel = plate(SLUG, "plate_migration").panel("net migration by citizenship")
    korean = panel.points("Korean citizens")
    foreign = panel.points("Foreign citizens")
    total = dict(zip(*plates.net_migration_rate(ctx)))
    for year in total:
        assert korean[year] + foreign[year] == pytest.approx(total[year])


@pytest.mark.parametrize("name", NAMES)
def test_nothing_is_clipped(name):
    for panel in plate(SLUG, name).panels():
        if panel.ax.get_visible():
            panel.nothing_is_clipped(slack=1e-6)
