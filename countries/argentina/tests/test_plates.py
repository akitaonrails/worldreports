"""Argentina's plates: the registry, the alt text, and what the panels say.

The generic checks — isolation, catalogs, data hygiene, layout, the spine
itself — run against every country from tests/. What is here is what only
this atlas can be asked: that the intervened decade is never drawn
through, that three fiscal methodologies stay three, that a running year
is never drawn as a finished one, and that every rate on a plate is the
count it came from over the population of the same year.
"""
from __future__ import annotations

import csv
import re

import pytest
from matplotlib.patches import Rectangle

from core.country import Country
from core.render import load_plates
from core.sideload import sibling
from tests.probe import plate

SLUG = "argentina"
COUNTRY = Country.load(SLUG)
plates = sibling(str(COUNTRY.dir / "plates.py"), "plates")
datasets = sibling(str(COUNTRY.dir / "datasets.py"), "datasets")
events = sibling(str(COUNTRY.dir / "events.py"), "events")
IDS = [p["id"] for p in plates.PLATES]
LAST = COUNTRY.last_full_year


def column(rel: str, col: str) -> dict[int, float]:
    with (COUNTRY.data_dir / rel).open(encoding="utf-8") as fh:
        return {int(r["year"]): float(r[col]) for r in csv.DictReader(fh)
                if (r.get(col) or "").strip()}


def population() -> dict[int, float]:
    return {y: v * 1e6 for y, v in column("macro/gdp.csv",
                                          "population_mn").items()}


def segments(panel, needle: str) -> list[list[float]]:
    """The x values of every drawn line whose label contains `needle`,
    plus the unlabelled continuation segments drawn in the same colour."""
    named = [ln for ln in panel.data_lines()
             if needle.lower() in ln.get_label().lower()]
    assert named, f"no line like {needle!r} on {panel.title!r}"
    colour = named[0].get_color()
    return [[float(x) for x in ln.get_xdata()] for ln in panel.data_lines()
            if ln.get_color() == colour and len(ln.get_xdata())]


# ---------------------------------------------------------------- registry
def test_thirteen_plates_with_unique_ids_slugs_and_topics():
    assert len(plates.PLATES) == 13
    assert len(set(IDS)) == 13
    assert len({p["slug"] for p in plates.PLATES}) == 13
    assert len({p["topic"] for p in plates.PLATES}) == 13
    assert IDS == sorted(IDS), "the plates are numbered out of order"


def test_the_chapters_keep_their_ids_and_answer_their_topics():
    """The nine original ids survive, so links do; the names and the
    topics differ on purpose and this pins which is which."""
    topics = {f"{p['id']}-{p['slug']}": p["topic"] for p in plates.PLATES}
    assert topics == {
        "01-output": "economy", "02-prices": "prices", "03-living": "people",
        "04-state": "fiscal", "05-trade": "trade", "06-credit": "credit",
        "07-markets": "markets", "08-people": "demography",
        "09-violence": "security", "10-spending": "spending",
        "11-world": "world", "12-mortality": "mortality",
        "13-migration": "migration"}


def test_plates_is_defined_once():
    """A second PLATES further down silently replaced the first for months."""
    src = (COUNTRY.dir / "plates.py").read_text(encoding="utf-8")
    assert len(re.findall(r"^PLATES\s*=", src, re.M)) == 1


@pytest.mark.parametrize("spec", plates.PLATES, ids=IDS)
def test_every_plate_describes_itself(spec):
    """`alt` is what a screen-reader user gets instead of the plate."""
    for key in ("title", "subtitle", "source", "alt"):
        assert spec[key].strip(), f"{spec['id']}: {key} is empty"
    assert len(spec["alt"]) > 300, "alt text too short to replace the plate"
    assert spec["alt"] != spec["title"]
    assert any(c.isdigit() for c in spec["alt"]), "alt text quotes no figures"


def test_every_panel_of_every_plate_is_filled():
    for spec in plates.PLATES:
        figure = plate(SLUG, spec["builder"].__name__)
        shown = [p for p in figure.panels() if p.ax.get_visible()]
        drawn = [p for p in shown if p.ax.has_data() or p.texts()]
        assert len(shown) == 4 and len(drawn) == 4, \
            f"{spec['id']}: {4 - len(drawn)} empty panel(s)"


def test_the_renderer_and_the_registry_agree():
    assert {p.name for p in load_plates(COUNTRY)} == \
        {p["builder"].__name__ for p in plates.PLATES}


def test_the_reader_refuses_another_countrys_data():
    from core.country import DataIsolationError

    for escape in ("../../france/data/macro/gdp.csv", "/etc/passwd", ".."):
        with pytest.raises(DataIsolationError):
            datasets.path(escape)


@pytest.mark.parametrize("name", [p["builder"].__name__ for p in plates.PLATES],
                         ids=IDS)
def test_nothing_is_clipped(name):
    for panel in plate(SLUG, name).panels():
        if panel.ax.get_visible():
            panel.nothing_is_clipped(slack=1e-6)


# ------------------------------------------------------------- the bands
def test_the_recession_bands_are_the_years_gdp_fell():
    """country.yaml's bands are a claim about gdp.csv; hold them to it."""
    fell = sorted(y for y, v in column("macro/gdp.csv", "real_growth").items()
                  if v < 0)
    banded = sorted(y for a, b, _ in COUNTRY.recessions
                    for y in range(round(a + 0.5), round(b + 0.5)))
    assert banded == fell


def _hatched_bands(panel):
    return [p for p in panel.ax.patches
            if isinstance(p, Rectangle) and p.get_hatch() == "////"]


@pytest.mark.parametrize("name,needle", [
    ("plate_output", "Real GDP growth"),
    ("plate_output", "Consumer price inflation"),
    ("plate_output", "Unemployment"),
    ("plate_prices", "Consumer price inflation"),
    ("plate_living", "Gini"),
    ("plate_living", "Poverty rate"),
    ("plate_living", "poverty each half year"),
    ("plate_markets", "Policy rate vs inflation"),
])
def test_the_intervened_decade_is_banded_wherever_indec_is_drawn(name, needle):
    panel = plate(SLUG, name).panel(needle)
    bands = _hatched_bands(panel)
    assert bands, f"{needle}: no INDEC band"
    a, b = events.INDEC_GAP
    x0 = bands[0].get_x()
    assert abs(x0 - a) < 1e-9 and abs(bands[0].get_width() - (b - a)) < 1e-9


def test_the_band_covers_the_ten_intervened_years_and_no_others():
    a, b = events.INDEC_GAP
    assert [y for y in range(2006, 2027) if a < y < b] == list(range(2007,
                                                                     2017))


# ------------------------------------------------------------- no splices
def test_cpi_is_two_series_never_one_line():
    """San Luis (2007-16) and INDEC (2017-) are two indices; no single
    line may hold a year of each."""
    panel = plate(SLUG, "plate_output").panel("Consumer price inflation")
    for xs in segments(panel, "INDEC, national"):
        assert min(xs) >= 2017
    for xs in segments(panel, "San Luis"):
        assert max(xs) <= 2016


def test_poverty_is_never_drawn_across_the_withdrawn_years():
    panel = plate(SLUG, "plate_living").panel("Poverty rate")
    for xs in segments(panel, "national basket"):
        assert not (min(xs) < 2007 and max(xs) > 2015), xs


def test_the_three_fiscal_methodologies_stay_three():
    panel = plate(SLUG, "plate_state").panel("Overall and primary balance")
    segs = segments(panel, "national public sector")
    assert len(segs) >= 3
    for xs in segs:
        spans = {("m1993" if x <= 2006 else "m2007" if x <= 2014
                  else "m2017") for x in xs}
        assert len(spans) == 1, f"a national segment spans {spans}"


def test_public_investment_methodologies_stay_apart():
    panel = plate(SLUG, "plate_spending").panel("Public investment")
    xs_all = [xs for xs in (
        [float(x) for x in ln.get_xdata()] for ln in panel.data_lines())
        if xs]
    for xs in xs_all:
        assert not (min(xs) <= 2014 < 2015 <= max(xs))
        assert not (min(xs) <= 2006 < 2007 <= max(xs))


# ----------------------------------------------------- the running year
def test_the_running_year_is_never_drawn_as_a_full_one():
    """2026 is year to date: dashed on a line, hatched on a bar, or not
    drawn at all — never on the solid line beside the finished years."""
    yy = LAST + 1
    for spec in plates.PLATES:
        for panel in plate(SLUG, spec["builder"].__name__).panels():
            for ln in panel.data_lines():
                xs = [float(x) for x in ln.get_xdata()]
                if xs and max(xs) > LAST + 0.75 and ln.get_linestyle() == "-":
                    assert min(xs) >= LAST - 0.5, \
                        f"{panel.title}: {ln.get_label()} solid into {yy}"
            for p in panel.ax.patches:
                if (p.get_data_transform() is panel.ax.transData
                        and hasattr(p, "get_x")
                        and p.get_x() + p.get_width() / 2 >= yy - 0.01
                        and p.get_x() < yy + 1):
                    assert p.get_hatch(), f"{panel.title}: {yy} bar unhatched"


def test_no_trade_balance_is_drawn_for_a_year_without_gdp():
    panel = plate(SLUG, "plate_trade").panel("Trade balance")
    xs = [float(patch.get_x() + patch.get_width() / 2)
          for patch in panel.ax.patches
          if patch.get_data_transform() is panel.ax.transData]
    assert max(xs) <= LAST
    assert max(p.get_x() + p.get_width() / 2 for p in panel.ax.patches
               if p.get_data_transform() is panel.ax.transData) <= LAST + 0.01


# ------------------------------------------------------------ the rates
def test_crude_birth_rate_is_births_over_indec_population():
    panel = plate(SLUG, "plate_people").panel("Crude birth and death rates")
    births = column("social/vitals.csv", "births")
    pop = population()
    got = panel.points("births")
    for y in (2014, 2024):
        assert got[y] == pytest.approx(births[y] / pop[y] * 1000, rel=1e-9)
    assert got[2014] == pytest.approx(18.21, abs=0.01)


def test_covid_rate_is_deaths_over_indec_population():
    panel = plate(SLUG, "plate_mortality").panel("COVID-19 deaths")
    covid = column("social/causes.csv", "covid")
    pop = population()
    tops = {round(p.get_x() + p.get_width() / 2): p.get_height()
            for p in panel.ax.patches
            if p.get_data_transform() is panel.ax.transData}
    assert tops[2021] == pytest.approx(covid[2021] / pop[2021] * 1e5)
    assert tops[2021] == pytest.approx(184.9, abs=0.1)


def test_suicide_rate_is_registered_deaths_over_population():
    panel = plate(SLUG, "plate_violence").panel("Suicide rate")
    s = column("social/causes.csv", "suicide")
    pop = population()
    assert panel.points("DEIS")[2019] == pytest.approx(s[2019] / pop[2019]
                                                       * 1e5)


def test_the_homicide_rate_is_the_published_one():
    """SNIC publishes its rate; the plate draws it, not a recomputation."""
    panel = plate(SLUG, "plate_violence").panel("Homicide rate")
    assert panel.points("SNIC") == {float(y): v for y, v in column(
        "social/homicides.csv", "rate").items()}


def test_net_migration_is_a_count_over_the_same_sources_population():
    panel = plate(SLUG, "plate_people").panel("Natural increase")
    mig = column("social/demography_intl.csv", "net_migration")
    pop = column("social/demography_intl.csv", "population")
    assert panel.points("net migration")[2019] == pytest.approx(
        mig[2019] / pop[2019] * 1000)


def test_excess_deaths_are_against_the_2015_19_mean():
    panel = plate(SLUG, "plate_mortality").panel("Excess deaths")
    d = column("social/causes.csv", "deaths_total")
    base = sum(d[y] for y in range(2015, 2020)) / 5
    tops = {round(p.get_x() + p.get_width() / 2): p.get_y() + p.get_height()
            for p in panel.ax.patches
            if p.get_data_transform() is panel.ax.transData}
    assert tops[2021] == pytest.approx((d[2021] / base - 1) * 100)


def test_the_spending_stack_adds_up_to_the_published_total():
    panel = plate(SLUG, "plate_spending").panel("Spending by function")
    total = column("fiscal/spending_by_function.csv", "total")
    tops: dict[int, float] = {}
    for p in panel.ax.patches:
        if p.get_data_transform() is panel.ax.transData:
            y = round(p.get_x() + p.get_width() / 2)
            tops[y] = max(tops.get(y, 0), p.get_y() + p.get_height())
    for y, v in total.items():
        assert tops[y] == pytest.approx(v, abs=1e-9)


def test_the_currency_index_rises_when_the_peso_strengthens():
    panel = plate(SLUG, "plate_markets").panel("Peso against the US$")
    fx = column("macro/dollar.csv", "official_avg")
    got = panel.points("official rate")
    assert got[2006] == pytest.approx(100)
    assert got[2025] == pytest.approx(fx[2006] / fx[2025] * 100)


# ----------------------------------------------- what the panels must say
def test_no_policy_rate_is_drawn_before_2016_and_badlar_says_it_is_a_proxy():
    panel = plate(SLUG, "plate_markets").panel("Policy rate vs inflation")
    assert min(panel.points("BCRA policy rate")) >= 2016
    assert max(panel.points("BCRA policy rate")) <= 2024
    assert "proxy" in next(k for k in panel.lines() if "BADLAR" in k)
    assert any("No single policy rate" in t for t in panel.texts())


@pytest.mark.parametrize("name,needle", [
    ("plate_output", "Unemployment"),
    ("plate_living", "Poverty rate"),
    ("plate_living", "Gini"),
])
def test_the_urban_scope_of_the_eph_is_stated(name, needle):
    panel = plate(SLUG, name).panel(needle)
    said = " ".join(panel.texts() + list(panel.lines())).lower()
    assert "urban" in said or "cities" in said


def test_the_femicide_method_change_is_marked_at_2017():
    panel = plate(SLUG, "plate_violence").panel("femicide")
    marks = [ln for ln in panel.ax.get_lines()
             if ln.get_transform() is not panel.ax.transData
             and list(ln.get_xdata()) == [2017, 2017]]
    assert marks
    assert any("2017" in t for t in panel.texts())


def test_the_cepos_are_dated_from_events():
    panel = plate(SLUG, "plate_prices").panel("The gap")
    starts = sorted(round(p.get_x(), 2) for p in panel.ax.patches
                    if isinstance(p, Rectangle) and p.get_hatch() == "..")
    assert starts == [events.MARKS["cepo1"][0], events.MARKS["cepo2"][0]]


def test_the_us_dollar_yield_is_labelled_as_a_sum_not_a_bond():
    panel = plate(SLUG, "plate_markets").panel("Government bond yield")
    label = next(k for k in panel.lines() if "EMBI" in k)
    assert "+" in label
    ust = column("markets/us_treasury_10y.csv", "avg")
    embi = column("markets/country_risk.csv", "avg_bp")
    assert panel.points("EMBI")[2023] == pytest.approx(ust[2023]
                                                       + embi[2023] / 100)


def test_migration_uses_birthplace_and_preserves_pending_gross_flows():
    stock = column("migration/foreign_born_census.csv", "foreign_born_pct")
    assert stock == {2010: 4.5, 2022: 4.2}
    spec = next(p for p in plates.PLATES if p["topic"] == "migration")
    assert "trips" in spec["alt"] and "decisions" in spec["alt"]
    origins = (COUNTRY.data_dir / "migration/origins_census_2022.csv").read_text()
    assert "Paraguay,522598" in origins and "Venezuela,161495" in origins
