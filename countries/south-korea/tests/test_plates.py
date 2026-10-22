"""Korea's own plate layer: its drawing helpers, its political calendar,
and the relationships its panels assert.

Everything here is specific to this country. The helpers below are
private to countries/south-korea/plates.py on purpose — they were not
promoted into core because no other country draws this way — so they are
tested beside the plates that use them. The generic checks run against
every country from tests/.
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


@pytest.fixture(scope="module")
def ctx():
    return Context(COUNTRY)


@pytest.fixture
def ax():
    figure, axes = plt.subplots()
    yield axes
    plt.close(figure)


# ------------------------------------------------------------- reading
def test_series_reads_a_column(ctx):
    gdp = plates._series(ctx, "macro/gdp.csv", "nominal_krw_tn")
    assert gdp[2006] > 900 and gdp[2025] > 2500


def test_a_blank_year_stays_a_gap(ctx):
    """The whole point of the convention: 2026 exists in the file and is
    empty, and nothing in the stack may invent a value for it."""
    births = plates._series(ctx, "social/vital.csv", "births")
    assert 2025 in births
    assert 2026 not in births


def test_a_missing_file_is_empty_rather_than_an_error(ctx):
    """A panel whose fetcher has never run draws its 'data pending' note
    instead of stopping the build."""
    assert plates._series(ctx, "macro/does-not-exist.csv", "value") == {}


def test_series_skips_a_non_numeric_cell_instead_of_failing(ctx):
    assert plates._series(ctx, "trade/destinations.csv", "destiny") == {}


def test_xy_keeps_years_and_values_aligned():
    data = {2010: 1.0, 2008: 2.0, 2009: 3.0}
    assert plates._xy(data) == ([2008, 2009, 2010], [2.0, 3.0, 1.0])


def test_xy_can_be_restricted_to_years_that_exist():
    data = {2008: 1.0, 2010: 2.0}
    assert plates._xy(data, [2008, 2009, 2010]) == ([2008, 2010], [1.0, 2.0])


def test_last_is_the_latest_year_not_the_largest_value():
    assert plates._last({2008: 9.0, 2020: 1.0}) == (2020, 1.0)
    assert plates._last({}) == (None, None)


# ------------------------------------------------------------- drawing
def test_room_only_ever_widens_to_the_right(ax):
    """An end label sits past the last point, so the axis has to grow for
    it — and the left edge must not move, or the panels stop lining up."""
    ax.set_xlim(2006, 2026)
    plates._room(ax, pad=3)
    assert ax.get_xlim() == (2006, 2029)


def test_an_end_label_lands_on_the_last_point(ctx, ax):
    plates._end_label(ctx, ax, {2006: 1.0, 2025: 42.0})
    (text,) = list(ax.texts)
    assert text.get_text() == "42.0"
    assert text.xy == (2025, 42.0)


def test_an_end_label_on_an_empty_series_draws_nothing(ctx, ax):
    plates._end_label(ctx, ax, {})
    assert not ax.texts


def test_deficits_are_red_and_surpluses_blue(ctx, ax):
    bars = plates._signed_bars(ctx, ax, {2007: 1.5, 2020: -3.7})
    first, second = (b.get_facecolor() for b in bars)
    assert first != second
    assert first[0] < first[2], "a surplus should be more blue than red"
    assert second[0] > second[2], "a deficit should be more red than blue"


def test_pct_axis_formats_with_a_sign_of_its_unit(ax):
    plates._pct_axis(ax, decimals=1)
    assert ax.yaxis.get_major_formatter()(0.5) == "0.5%"


# -------------------------------------------------------------- events
def test_every_presidency_is_contiguous():
    """A gap or an overlap would draw two political strips over one year."""
    for (_, end, name, _), (start, *_) in zip(events.PRESIDENTS,
                                              events.PRESIDENTS[1:]):
        assert start >= end, f"{name}'s term overlaps the next"
        assert start - end < 0.2, f"there is a gap after {name}"


def test_the_two_impeachments_are_mid_year():
    """Park left office in March 2017 and Yoon in April 2025. Stored as
    whole years both strips would be a year wrong, which is the kind of
    error a reader notices and nothing else would catch."""
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
    """Two lists name the ten plates. They have to be the same ten, or a
    card on the page points at another plate's figure.

    The two lists do not use the same names — a plate is declared by its
    drawing function, a card by the file that function writes — so they
    are compared through the filenames both end up at.
    """
    from core import sitebuild
    from core.render import load_plates

    drawn = {pl.name for pl in load_plates(COUNTRY)}
    assert {name for name, _ in plates.PLATES} == drawn
    carded = {ch["id"] for ch in sitebuild.chapters_for(COUNTRY)}
    assert len(carded) == len(drawn) == 10, \
        f"{len(drawn)} plates drawn, {len(carded)} cards built"
    for plate_id in carded:
        assert (COUNTRY.out_dir / f"{plate_id}.png").exists(), \
            f"card {plate_id} has no rendered plate"


# ----------------------------------------------------------- semantics
def test_births_fall_below_deaths_in_2020_and_stay_there(ctx):
    """Korea crossed into natural decrease in 2020 and has not come back.

    Asked of the data rather than of the drawn lines: this panel names its
    two series in place, beside their last points, rather than in a
    legend, so there is no label on the line to match. The claim is about
    the numbers anyway — the panel's job is to show them, which the test
    below checks separately.
    """
    births = plates._series(ctx, "social/vital.csv", "births")
    deaths = plates._series(ctx, "social/vital.csv", "deaths")
    shared = sorted(set(births) & set(deaths))
    assert shared, "births and deaths never overlap"
    before = [y for y in shared if y < 2020 and births[y] <= deaths[y]]
    assert not before, f"deaths already exceeded births in {before}"
    after = [y for y in shared if y >= 2020]
    assert after, "the series stop before the crossing"
    assert all(deaths[y] > births[y] for y in after), \
        "deaths no longer exceed births from 2020 on"


def test_the_demography_panel_names_both_series_and_the_crossing():
    """Two unlabelled lines are two shapes. The panel labels each where it
    ends and says in words what the crossing is, which is the only reason
    a reader can tell which line is which."""
    panel = plate(SLUG, "plate_demography").panel("births")
    captions = " ".join(panel.texts()).lower()
    assert "births" in captions
    assert "deaths" in captions
    assert "2020" in captions, "the crossing year is not named on the panel"
    assert len(panel.data_lines()) >= 2


@pytest.mark.parametrize("name", [n for n, _ in plates.PLATES])
def test_nothing_is_clipped(name):
    """A hardcoded set_ylim silently hides data once the series grows past
    it: the line leaves the top of the panel and the reader never learns a
    peak is missing."""
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped(slack=1e-6)
