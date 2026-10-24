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


# ------------------------------------------------------------- the cards
def test_the_cards_read_the_committed_csvs():
    cards = {ch["id"]: ch for ch in sitebuild.chapters_for(Country.load(SLUG))}
    assert set(cards) == {"01-economy", "02-world", "03-demography",
                          "04-people"}
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
                        ("plate_people", "Minimum wage")]:
        is_pending(name, panel)
