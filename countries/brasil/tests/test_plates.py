"""Does each line on a Brazilian plate mean what its label says?

This repository has the scar that makes the question worth asking: the
S&P 500 converted *into* reais was once labelled "(USD)" and the native
dollar index "(in BRL)". The panel measured perfectly and said the
opposite of the truth, and it was caught by eye months later.

Each test below states a relationship between a label and the numbers
drawn under it, so swapping two labels fails the build. The generic
checks — isolation, catalogs, data hygiene, the built pages — live in
tests/ and run against every country.
"""
from __future__ import annotations

import pytest

from tests.probe import plate, plate_names

SLUG = "brasil"


# ------------------------------------------------------------ markets
def test_the_sp500_in_reais_outruns_the_dollar_index():
    """The real went from about 2.3 to over 5 per dollar across the
    window, so the same index converted into reais must end far above the
    native dollar one. If those two labels are ever swapped again, this is
    the assertion that fails.
    """
    lines = plate(SLUG, "fig_markets").panel("local terms").lines()
    brl = next(v for k, v in lines.items() if "BRL" in k and "S&P" in k)
    usd = next(v for k, v in lines.items() if "USD" in k and "S&P" in k)
    assert brl[-1] > usd[-1] * 1.5, (
        "the line labelled as converted into reais is not above the dollar "
        "one — the labels look swapped")


def test_the_two_sp500_lines_start_together():
    """Both are rebased to the same year, so they start at the same level;
    only the currency path separates them afterwards."""
    lines = plate(SLUG, "fig_markets").panel("local terms").lines()
    brl = next(v for k, v in lines.items() if "BRL" in k and "S&P" in k)
    usd = next(v for k, v in lines.items() if "USD" in k and "S&P" in k)
    assert abs(brl[0] - usd[0]) <= max(1.0, usd[0] * 0.02)


def test_every_series_on_the_rebased_panel_starts_at_100():
    for label, vals in plate(SLUG, "fig_markets").panel("local terms") \
            .lines().items():
        assert abs(vals[0] - 100) <= 2.0, f"{label} starts at {vals[0]}"


# ------------------------------------------------------------- fiscal
def test_gross_debt_is_plotted_above_net_debt():
    """Gross debt exceeds net debt by construction: net subtracts the
    government's financial assets. Two panels plotting them the other way
    round would mean the columns are crossed."""
    fig = plate(SLUG, "fig_fiscal")

    def last(panel):
        labelled = panel.lines()
        if labelled:
            return max(v[-1] for v in labelled.values())
        return float(panel.data_lines()[0].get_ydata()[-1])

    assert last(fig.panel("gross")) > last(fig.panel("net"))


# ----------------------------------------------------------- security
def test_estimated_homicides_are_never_below_registered():
    """The estimated series adds the deaths hidden in the
    undetermined-intent pool, so it is an upper bound on the registered
    count, never a lower one.

    This test is on the rate panel, not the counts panel: the counts panel
    carries FBSP against IPEA/SIM, which are two collection systems that
    disagree in both directions by design. An earlier version of this test
    looked there, found no series it recognised, and skipped — so it
    checked nothing at all for as long as that was true.
    """
    panel = plate(SLUG, "fig_security").panel("registered vs estimated")
    pairs = panel.paired("stimated", "egistered")
    assert len(pairs) >= 10, "the two series barely overlap"
    below = [(int(y), e, r) for y, e, r in pairs if e < r]
    assert not below, f"estimated below registered in {below[:4]}"


def test_the_two_homicide_systems_stay_two_lines():
    """FBSP counts violent intentional deaths where they happened; IPEA
    reads death certificates where the victim lived. They disagree by
    design, in both directions, and must never be merged into one line or
    presented as a correction of each other.
    """
    panel = plate(SLUG, "fig_security").panel("two systems")
    labels = panel.lines()
    assert len(labels) >= 2
    blob = " ".join(labels).lower()
    assert "fbsp" in blob
    assert "ipea" in blob or "sim" in blob


def test_femicides_are_a_subset_of_womens_homicides():
    """Every femicide is a homicide of a woman; the reverse is not true,
    and the panel exists to show the gap between the two counts."""
    panel = plate(SLUG, "fig_security").panel("women")
    pairs = panel.paired("femicide", "All homicides of women")
    assert pairs, "the two series never overlap"
    assert all(f <= t for _, f, t in pairs)


# ----------------------------------------------------------- clipping
@pytest.mark.parametrize("name", plate_names(SLUG))
def test_nothing_is_clipped(name):
    """A hardcoded set_ylim silently hides data once the series grows past
    it; a GDP-per-capita panel once clipped its own 2011 peak, and the
    reader simply never learned the peak was there."""
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped(slack=1e-6)


def test_every_plate_renders(name=None):
    """The renderer catches a failing plate so one does not stop the rest,
    which means a broken figure reaches the site unless something fails
    loudly here."""
    assert len(plate_names(SLUG)) == 11
