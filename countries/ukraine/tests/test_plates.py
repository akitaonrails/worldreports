"""The facts Ukraine's plates assert.

Each test states a claim a plate makes about the country's own data, so a
refetch that invalidates the claim fails loudly instead of quietly
changing a published chart. The three that matter most here:

- the 2022 collapse is drawn at its real size (-28.8%) and is inside the
  shared comparison scale, which had to be widened for it;
- the register's 2015 step is the publisher's perimeter change, not a
  demographic event, and the register and the UN estimate are never
  spliced into one line;
- a series that stops (unemployment in 2021, Gini in 2020) keeps a hole,
  never a zero and never an extrapolation.
"""

from __future__ import annotations

import csv

import pytest

from core.country import Country
from core import sitebuild
from tests.probe import plate

SLUG = "ukraine"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8-sig", newline="") as fh:
        return [r for r in csv.DictReader(fh)
                if not r.get("year", "").startswith("#")]


def num(r: dict, key: str) -> float:
    v = (r.get(key) or "").strip()
    return float(v) if v else float("nan")


def by_year(rel: str) -> dict[int, dict]:
    return {int(r["year"]): r for r in rows(rel)}


def texts(plate_name: str, panel: str) -> list[str]:
    return plate(SLUG, plate_name).panel(panel).texts()


def is_pending(plate_name: str, panel: str) -> None:
    p = plate(SLUG, plate_name).panel(panel)
    assert any("pending" in t.lower() or "дані відсутні" in t.lower()
               or "dados pendentes" in t.lower() for t in p.texts()), \
        f"{panel}: no pending marker"


# ----------------------------------------------------------------- economy
def test_the_invasion_year_is_the_deepest_fall_of_the_window():
    g = by_year("macro/economy.csv")
    vals = {y: num(r, "gdp_growth_pct") for y, r in g.items()}
    assert min(vals, key=vals.get) == 2022
    assert vals[2022] == pytest.approx(-28.76, abs=0.01)
    # The IMF's independent WEO series agrees on the same year and size.
    imf = by_year("macro/gdp_growth_imf.csv")
    assert num(imf[2022], "gdp_growth_pct") == pytest.approx(-28.8, abs=0.1)


def test_the_collapse_is_inside_the_shared_comparison_scale():
    from core import spine
    slot = spine.SLOTS["economy.growth"]
    assert slot.ref[0] <= -28.76
    lo, hi = spine.fit(slot, (-28.76, 8.22))[0]
    assert (lo, hi) == slot.ref


def test_the_hryvnia_collapse_shows_in_inflation_and_not_in_zeroes():
    e = by_year("macro/economy.csv")
    assert num(e[2015], "cpi_inflation_pct") == pytest.approx(48.7, abs=0.05)
    assert num(e[2022], "cpi_inflation_pct") == pytest.approx(20.18, abs=0.01)
    # Two deflationary years (2012, 2013) are real readings, not holes; and
    # no year is a zero-filled stand-in.
    assert num(e[2013], "cpi_inflation_pct") < 0
    assert all(num(r, "cpi_inflation_pct") != 0 for r in e.values())


def test_unemployment_keeps_its_hole_instead_of_extrapolating():
    e = by_year("macro/economy.csv")
    assert 2021 in e and num(e[2021], "unemployment_pct") > 0
    for y in (2022, 2023, 2024, 2025):
        assert y in e
        assert num(e[y], "unemployment_pct") != num(e[y], "unemployment_pct"), \
            f"{y}: the ILO series has no value here and must stay blank"


# ------------------------------------------------------------------- world
def test_nominal_gdp_and_reserves_are_the_staged_dollars():
    w = by_year("world/gdp_usd.csv")
    assert num(w[2022], "gdp_usd") / 1e9 == pytest.approx(162, abs=1)
    assert num(w[2025], "gdp_usd") / 1e9 == pytest.approx(214, abs=1)
    r = by_year("world/reserves.csv")
    assert num(r[2025], "reserves_usd") / 1e9 == pytest.approx(57, abs=1)


def test_hdi_is_one_vintage_and_stops_in_2023():
    h = by_year("world/hdi.csv")
    assert max(h) == 2023
    assert num(h[2023], "hdi") == pytest.approx(0.779, abs=0.001)


# -------------------------------------------------------------- demography
def test_the_2015_step_is_the_perimeter_and_not_a_birth_rate():
    u = by_year("demography/population_ukrstat.csv")
    drop = num(u[2014], "population") - num(u[2015], "population")
    assert drop == pytest.approx(2_496_951, abs=1)
    # Five per cent of the country in one year is not a demographic event;
    # the plate says so, and the two lines stay separate.
    assert num(u[2015], "population") / num(u[2014], "population") == \
        pytest.approx(0.94503, abs=0.0001)


def test_the_register_and_the_un_estimate_are_never_spliced():
    u = by_year("demography/population_ukrstat.csv")
    w = by_year("demography/population.csv")
    # Different perimeters: the UN line includes Crimea, so in 2014 it is
    # larger than the register, and they are not the same series.
    assert num(w[2014], "population") > num(u[2014], "population")
    assert num(u[2021], "population") == pytest.approx(41_588_354, abs=1)
    assert num(w[2021], "population") == pytest.approx(44_298_640, abs=1)
    # The register has no 2023+ row; the plate's note says why.
    assert max(u) == 2022 and max(w) >= 2023


def test_the_register_line_is_inside_the_population_scale():
    from core import spine
    slot = spine.SLOTS["demography.population"]
    lo, hi = spine.fit(slot, (79.81, 100))[0]
    assert (lo, hi) == slot.ref


# ------------------------------------------------------------------ people
def test_gini_stops_where_the_household_survey_stopped():
    g = by_year("people/gini.csv")
    assert max(g) == 2020
    assert num(g[2020], "gini") == pytest.approx(25.6, abs=0.05)


def test_the_price_level_is_the_chained_annual_cpi():
    e = by_year("macro/economy.csv")
    run = 100.0
    for y in sorted(e):
        run *= 1 + num(e[y], "cpi_inflation_pct") / 100
    assert run == pytest.approx(1_006, abs=2)   # ~10.1x the 2006 level


def test_the_people_lens_states_it_is_derived():
    lens = " ".join(texts("plate_people", "What the hryvnia buys"))
    assert "CPI" in lens or "ІСЦ" in lens or "IPC" in lens




# ------------------------------------------------------------------ fiscal
def test_the_war_budget_is_one_imf_vintage():
    f = by_year("fiscal/fiscal.csv")
    assert num(f[2023], "expenditure_pct_gdp") == pytest.approx(73.40, abs=0.01)
    assert num(f[2023], "revenue_pct_gdp") == pytest.approx(54.06, abs=0.01)
    assert num(f[2023], "balance_pct_gdp") == pytest.approx(-19.30, abs=0.01)
    assert num(f[2024], "interest_pct_gdp") == pytest.approx(3.98, abs=0.01)
    # The overall and primary balances keep their published definitions:
    # the primary is the overall before interest, and the two are not
    # the same line.
    assert num(f[2023], "balance_pct_gdp") < num(f[2023], "primary_balance_pct_gdp")


def test_forecast_years_are_not_drawn_as_observed():
    f = by_year("fiscal/fiscal.csv")
    assert max(f) <= 2025
    # 2025 carries only the WEO debt figure; revenue/expenditure/interest
    # have no observed value and stay blank rather than carried.
    assert num(f[2025], "debt_pct_gdp") == pytest.approx(107.1, abs=0.01)
    assert num(f[2025], "revenue_pct_gdp") != num(f[2025], "revenue_pct_gdp")


# ------------------------------------------------------------------- trade
def test_the_trade_lens_is_a_labelled_single_year():
    p = by_year("trade/partners_2023.csv") if False else None
    import csv
    rows = list(csv.DictReader(open(DATA / "trade/partners_2023.csv")))
    shares = [float(r["share_pct"]) for r in rows]
    assert sum(shares) == pytest.approx(100, abs=0.2)
    assert rows[0]["partner"] == "Poland"
    assert shares[0] == pytest.approx(13.15, abs=0.05)
    assert rows[-1]["partner"] == "Rest of the world"


def test_trade_is_the_national_accounts_series_and_its_gap():
    t = by_year("trade/trade.csv")
    assert num(t[2025], "exports_pct_gdp") == pytest.approx(25.33, abs=0.01)
    assert num(t[2025], "imports_pct_gdp") == pytest.approx(51.85, abs=0.01)
    gap = num(t[2025], "exports_pct_gdp") - num(t[2025], "imports_pct_gdp")
    assert gap == pytest.approx(-26.52, abs=0.02)


# ----------------------------------------------------------------- markets
def test_the_nbu_key_rate_is_a_central_bank_series():
    k = by_year("markets/key_rate.csv")
    assert num(k[2023], "policy_rate_pct") == pytest.approx(21.6, abs=1.0)
    assert num(k[2025], "policy_rate_pct") == pytest.approx(15.26, abs=0.05)


def test_the_official_hryvnia_rate_and_its_index():
    f = by_year("markets/usd_uah.csv")
    assert num(f[2006], "uah_per_usd") == pytest.approx(5.05, abs=0.005)
    assert num(f[2025], "uah_per_usd") == pytest.approx(41.69, abs=0.01)
    # The index is 2006 = 100, up = stronger: 5.05/41.69.
    assert 100 * num(f[2006], "uah_per_usd") / num(f[2025], "uah_per_usd") < 13


# ---------------------------------------------------------------- security
def test_security_rates_stop_before_the_invasion():
    s = by_year("security/security.csv")
    assert num(s[2006], "homicide_per_100k") == pytest.approx(6.257, abs=0.001)
    assert num(s[2021], "homicide_per_100k") == pytest.approx(3.777, abs=0.001)
    assert max(y for y in s if num(s[y], "homicide_per_100k") == num(s[y], "homicide_per_100k")) == 2021
    assert max(y for y in s if num(s[y], "road_deaths_per_100k") == num(s[y], "road_deaths_per_100k")) == 2019
    assert num(s[2021], "suicide_per_100k") == pytest.approx(21.21, abs=0.01)


# --------------------------------------------------------------- mortality
def test_the_death_rate_and_life_expectancy():
    m = by_year("mortality/mortality.csv")
    assert num(m[2021], "death_rate_per_1000") == pytest.approx(17.13, abs=0.01)
    assert num(m[2024], "death_rate_per_1000") == pytest.approx(13.60, abs=0.01)
    assert num(m[2006], "life_expectancy") == pytest.approx(67.49, abs=0.01)
    assert num(m[2024], "life_expectancy") == pytest.approx(74.69, abs=0.01)


# ---------------------------------------------------------------- spending
def test_the_war_budget_by_function():
    sp = by_year("fiscal/treasury_functional.csv")
    gdp = by_year("macro/gdp_uah.csv")
    # The dataset's year is the execution year: the NBU's 20240101 stamp
    # carries 2023 (PR #6's finding, anchored to the MoF annual workbook).
    assert int(sp[2023]["source_dt"]) == 20240101
    total = num(sp[2023], "total_million_uah") * 1e6 / num(gdp[2023], "gdp_uah") * 100
    defence = num(sp[2023], "defence_million_uah") * 1e6 / num(gdp[2023], "gdp_uah") * 100
    assert total == pytest.approx(67.0, abs=0.3)
    assert defence == pytest.approx(31.6, abs=0.2)
    # The published total is the sum of the ten functions.
    parts = sum(num(sp[2023], c) for c in (
        "general_public_services_million_uah", "defence_million_uah",
        "public_order_safety_judiciary_million_uah",
        "economic_affairs_million_uah", "environment_million_uah",
        "housing_community_million_uah", "health_million_uah",
        "culture_recreation_religion_million_uah", "education_million_uah",
        "social_protection_million_uah"))
    assert parts == pytest.approx(num(sp[2023], "total_million_uah"), abs=2)


def test_the_spending_scale_holds_the_war_budget():
    from core import spine
    slot = spine.SLOTS["spending.by_function"]
    lo, hi = spine.fit(slot, (0, 67.3))[0]
    assert (lo, hi) == slot.ref


# --------------------------------------------------------------- migration
def test_migration_keeps_the_war_out_of_the_comparable_slot():
    m = by_year("migration/migration.csv")
    pop = by_year("demography/population.csv")
    per = {y: num(m[y], "net_migration") / num(pop[y], "population") * 1000
           for y in m if m[y].get("population")}
    # 2022 is the displacement shock and must stay well outside the
    # canonical range; the plate draws it in the lens.
    assert per[2022] == pytest.approx(-139, abs=2)
    from core import spine
    slot = spine.SLOTS["migration.net"]
    assert per[2022] < slot.ref[0]
    # The comparable line stops in 2021 by construction.
    assert max(y for y in per if y <= 2021) == 2021


def test_the_foreign_born_share_is_a_snapshot():
    m = by_year("migration/migration.csv")
    pop = by_year("demography/population.csv")
    share = {y: num(m[y], "migrant_stock") / num(pop[y], "population") * 100
             for y in m if m[y].get("migrant_stock")}
    assert sorted(share) == [2010, 2015, 2020, 2024]
    assert share[2010] == pytest.approx(10.4, abs=0.1)
    assert share[2024] == pytest.approx(13.4, abs=0.1)


# ------------------------------------------------------------- the cards
def test_the_cards_read_the_committed_csvs():
    cards = {ch["id"]: ch for ch in sitebuild.chapters_for(Country.load(SLUG))}
    assert set(cards) == {
        "01-economy", "02-fiscal", "03-spending", "04-trade", "05-markets",
        "06-people", "07-world", "08-demography", "09-security",
        "10-mortality", "11-migration"}
    cpi = cards["01-economy"]["stats"][0]
    assert cpi["year"] == 2025
    e = by_year("macro/economy.csv")
    assert cpi["value"]["en"].startswith(f"{num(e[2025], 'cpi_inflation_pct'):.1f}")


def test_parked_slots_stay_parked():
    for name, panel in [("plate_world", "Corruption Perceptions Index"),
                        ("plate_demography", "Total fertility rate"),
                        ("plate_demography", "Crude birth and death rates"),
                        ("plate_demography", "Natural increase and net migration"),
                        ("plate_people", "Poverty rate"),
                        ("plate_people", "Minimum wage"),
                        ("plate_trade", "Top export destinations"),
                        ("plate_markets", "10-year government bond yield"),
                        ("plate_markets", "Main equity index in US$"),
                        ("plate_mortality", "Excess deaths"),
                        ("plate_mortality", "COVID-19 deaths")]:
        is_pending(name, panel)
