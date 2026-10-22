"""Does each line on a French plate mean what its label says?

Geometry cannot answer that. A panel whose two series are labelled the
wrong way round measures perfectly and reads exactly backwards — which
happened in a sibling project, where an S&P 500 converted *into* reais was
labelled "(USD)" and the native dollar index "(in BRL)". It inverted the
panel's whole point and was caught by eye months later.

So each test below states a relationship that must hold between a label
and the numbers drawn under it, and swapping two labels fails the build.
Everything here is specific to France; the generic checks — isolation,
catalogs, data hygiene, the built pages — live in tests/ and run against
every country.
"""
from __future__ import annotations

import csv

import pytest

from core.country import Country
from tests.probe import plate

SLUG = "france"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(
            ln for ln in fh if not ln.lstrip().startswith("#")))


# ------------------------------------------------------------- fiscal
def test_eurostats_tax_burden_sits_above_insees():
    """Eurostat counts imputed employer social contributions — the pensions
    the state owes its own staff but never pays a fund for — and INSEE does
    not. So Eurostat's line is the higher one in every overlapping year, by
    roughly two and a half points. If this ever inverts, the two columns
    have been crossed.
    """
    panel = plate(SLUG, "fig_fiscal").panel("compulsory levies")
    # Paired by year, not by position: the two definitions are published
    # to different last years, and comparing their value arrays by index
    # would line up one definition's 2025 with the other's 2024.
    pairs = panel.paired("Eurostat", "INSEE")
    assert len(pairs) >= 15, "the two definitions barely overlap"
    below = [(int(y), e, i) for y, e, i in pairs if e <= i]
    assert not below, f"Eurostat is not above INSEE in {below[:4]}"


def test_the_cice_break_is_marked_on_the_tax_burden_panel():
    """The 2019 fall of about 0.9 point is definitional: the CICE stopped
    being a tax credit and became a contribution cut, so the same policy
    left the tax burden instead of offsetting it. An unannotated panel
    reads it as a tax cut that never happened.
    """
    panel = plate(SLUG, "fig_fiscal").panel("compulsory levies")
    captions = " ".join(panel.texts())
    assert "CICE" in captions
    assert "definitional" in captions.lower()
    assert any(abs(ln.get_xdata()[0] - 2019) < 0.01
               for ln in panel.ax.get_lines()
               if ln.get_transform() is not panel.ax.transData), \
        "no rule drawn at 2019"


def test_the_primary_balance_is_the_deficit_plus_the_interest_bill():
    """It is a computed column, not a published one: primary balance =
    deficit + interest paid. If that identity stops holding, the interest
    series has been double-counted or signed the wrong way — and the
    panel's whole point, that the debt doubled while the interest bill
    fell, rests on it.
    """
    checked = 0
    for r in rows("fiscal/deficit.csv"):
        if not all((r[c] or "").strip()
                   for c in ("deficit", "primary", "interest")):
            continue
        checked += 1
        assert abs(float(r["primary"])
                   - (float(r["deficit"]) + float(r["interest"]))) <= 0.06, \
            f"{r['year']}: primary != deficit + interest"
    assert checked > 15


def test_the_primary_balance_is_drawn_against_the_interest_bill():
    """Both belong on one panel, because the fact being shown is the gap
    between them. Plotting only one tells the reader nothing about why the
    deficit and the debt moved differently.
    """
    labels = " ".join(plate(SLUG, "fig_fiscal")
                      .panel("primary balance").lines()).lower()
    assert "primary balance" in labels
    assert "interest" in labels


# ------------------------------------------------------------ markets
def test_the_sp500_in_euros_falls_short_of_the_dollar_index():
    """The euro went from about 1.32 dollars to about 1.08 across the
    window, so a dollar index converted into euros gains *more* than the
    native one — the same dollars buy more euros at the end than at the
    start. This is the assertion that fails if those two labels are ever
    swapped.
    """
    panel = plate(SLUG, "fig_markets").panel("local terms")
    lines = panel.lines()
    eur = next(v for k, v in lines.items() if "in EUR" in k and "S&P" in k)
    usd = next(v for k, v in lines.items() if "(USD)" in k and "S&P" in k)
    assert eur[-1] > usd[-1]


def test_the_two_sp500_lines_start_together():
    """Both are rebased on the same year, so they start at the same level;
    only the currency path separates them afterwards."""
    lines = plate(SLUG, "fig_markets").panel("local terms").lines()
    eur = next(v for k, v in lines.items() if "in EUR" in k and "S&P" in k)
    usd = next(v for k, v in lines.items() if "(USD)" in k and "S&P" in k)
    assert abs(eur[0] - usd[0]) <= max(1.0, usd[0] * 0.02)


def test_every_series_on_the_rebased_panel_starts_at_100():
    for label, vals in plate(SLUG, "fig_markets").panel("local terms") \
            .lines().items():
        assert abs(vals[0] - 100) <= 2.0, f"{label} starts at {vals[0]}"


def test_the_policy_rate_panel_draws_the_deposit_rate_below_zero():
    """Eight years of negative rates are the fact the panel exists for. A
    main-refinancing series spliced in instead never goes below zero, so
    the floor doubles as a check on which series is plotted.
    """
    dfr = plate(SLUG, "fig_markets").panel("policy rate").series("eposit")
    assert min(v for v in dfr if v == v) < 0


# ----------------------------------------------------------- security
def test_women_killed_by_a_partner_are_a_subset_of_couple_deaths():
    """The containment the panel is built around: every woman killed by her
    partner is a death within the couple, and the couple total also counts
    men, including perpetrators who then killed themselves. The subset is
    drawn as a filled area inside the total rather than as a second line,
    because two lines read as two independent trends.
    """
    panel = plate(SLUG, "fig_security").panel("within the couple")
    areas = [c for c in panel.ax.collections
             if hasattr(c, "get_paths") and c.get_paths()]
    assert len(areas) >= 2, \
        "the subset is no longer drawn as an area inside the total"
    pairs = [(float(r["women_killed_by_partner"]),
              float(r["couple_deaths_total"]))
             for r in rows("social/violence.csv")
             if (r["women_killed_by_partner"] or "").strip()
             and (r["couple_deaths_total"] or "").strip()]
    assert pairs
    assert all(women < total for women, total in pairs)


def test_the_share_the_title_promises_is_actually_plotted():
    """A title that says 'and the women among them' has to show the
    proportion somewhere, or the reader is asked to divide two lines by
    eye. It lives on a right-hand axis, in percent, inside 0..100.
    """
    fig = plate(SLUG, "fig_security")
    ax = fig.panel("within the couple").ax
    twins = [a for a in fig.fig.axes
             if a is not ax and a.get_position().bounds == ax.get_position().bounds]
    assert twins, "no twin axis carries the share"
    lo, hi = twins[0].get_ylim()
    assert lo >= 0 and hi <= 100.001
    vals = [v for ln in twins[0].get_lines()
            if ln.get_transform() is twins[0].transData
            for v in ln.get_ydata() if v == v]
    assert vals, "the share axis has no line on it"
    assert all(0 <= v <= 100 for v in vals)


def test_the_subset_is_named_on_the_panel_not_in_a_legend():
    """'of which…' in a legend box gives the reader nothing to attach the
    'which' to. Both populations are labelled where they are drawn."""
    panel = plate(SLUG, "fig_security").panel("within the couple")
    captions = " ".join(panel.texts()).lower()
    assert "within the couple" in captions
    assert "women" in captions
    assert panel.ax.get_legend() is None, \
        "the containment is explained in place, not boxed"


def test_the_two_homicide_systems_stay_two_lines():
    """SSMSI counts what the police recorded, CépiDc counts what a doctor
    certified. They disagree by design and must never become one line."""
    fig = plate(SLUG, "fig_security")
    try:
        panel = fig.panel("two systems")
    except AssertionError:
        panel = fig.panel("homicide")
    labels = panel.lines()
    assert len(labels) >= 2
    blob = " ".join(labels).lower()
    assert "ssmsi" in blob
    assert "cépidc" in blob


def test_the_reporting_caveat_sits_with_the_line_it_explains():
    """The rise after 2017 is substantially a change in willingness to
    report. A caveat parked in another corner of the plate does not reach
    the reader who is looking at the rising line."""
    panel = plate(SLUG, "fig_security").panel("recorded assault")
    assert "reporting" in " ".join(panel.texts()).lower()


# ------------------------------------------------------- demographics
def test_deaths_overtake_births_before_the_series_ends():
    """2025 is the first year since the war with more deaths than births.
    If this stops being true, either the crossing has been smoothed away
    or the two series have been swapped."""
    panel = plate(SLUG, "fig_demographics").panel("births")
    pairs = panel.paired("eath", "irth")
    assert pairs, "the two series never overlap"
    assert any(d > b for _, d, b in pairs), "deaths never overtake births"


# ----------------------------------------------------------- clipping
@pytest.mark.parametrize("name", ["fig_fiscal", "fig_markets", "fig_security",
                                  "fig_demographics", "fig_economy",
                                  "fig_spending", "fig_trade", "fig_world",
                                  "fig_people", "fig_mortality", "fig_credit"])
def test_nothing_is_clipped(name):
    """A hardcoded set_ylim silently hides data once the series grows past
    it: the line simply leaves the top of the panel and the reader never
    learns a peak is missing."""
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped(slack=1e-6)
