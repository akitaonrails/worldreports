"""Does each line on a French plate mean what its label says?

Geometry cannot answer that. A panel whose two series are labelled the
wrong way round measures perfectly and reads exactly backwards — which
happened in a sibling project, where an S&P 500 converted *into* reais was
labelled "(USD)" and the native dollar index "(in BRL)". It inverted the
panel's whole point and was caught by eye months later.

So each test below states a relationship that must hold between a label
and the numbers drawn under it, and swapping two labels fails the build.
The plates are on the shared spine (PLATE_SPINE.md), so several counts are
now drawn as rates: each conversion is pinned here against the CSVs it was
made from, by year. Everything here is specific to France; the generic
checks — the spine itself, isolation, catalogs, data hygiene, the built
pages — live in tests/ and run against every country.
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


def col(rel: str, column: str) -> dict[int, float]:
    return {int(r["year"]): float(r[column]) for r in rows(rel)
            if (r.get(column) or "").strip()}


def pop_avg() -> dict[int, float]:
    return col("social/vital_rates.csv", "pop_avg")


def near(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(b))


# ------------------------------------------------------------- fiscal
def test_eurostats_tax_burden_sits_above_insees():
    """Eurostat counts imputed employer social contributions — the pensions
    the state owes its own staff but never pays a fund for — and INSEE does
    not. So Eurostat's ratio is the higher one in every overlapping year.
    If this ever inverts, the two columns have been crossed. The plate now
    draws INSEE's levies and states the gap in a note, which must be the
    gap these two columns actually have.
    """
    est, insee = col("fiscal/tax_burden.csv", "estat"), \
        col("fiscal/tax_burden.csv", "insee")
    pairs = [(y, est[y], insee[y]) for y in est if y in insee]
    assert len(pairs) >= 15, "the two definitions barely overlap"
    below = [p for p in pairs if p[1] <= p[2]]
    assert not below, f"Eurostat is not above INSEE in {below[:4]}"
    gaps = [e - i for _, e, i in pairs]
    note = " ".join(plate(SLUG, "fig_fiscal").panel("compulsory levies")
                    .texts())
    assert f"{min(gaps):.1f}–{max(gaps):.1f}pt above INSEE" in note


def test_the_cice_break_is_marked_and_drawn_as_a_seam():
    """The 2019 fall of about 0.9 point is definitional: the CICE stopped
    being a tax credit and became a contribution cut, so the same policy
    left the tax burden instead of offsetting it. An unannotated panel
    reads it as a tax cut that never happened, and a line joined across
    the break draws one. So: a note, a rule at 2019, and no segment of the
    levies line that spans 2018 to 2019.
    """
    panel = plate(SLUG, "fig_fiscal").panel("compulsory levies")
    captions = " ".join(panel.texts())
    assert "CICE" in captions
    assert "definitional" in captions.lower()
    assert any(abs(ln.get_xdata()[0] - 2019) < 0.01
               for ln in panel.ax.get_lines()
               if ln.get_transform() is not panel.ax.transData), \
        "no rule drawn at 2019"
    levy_color = panel.ax.get_legend().get_lines()[2].get_color()
    segments = [list(ln.get_xdata()) for ln in panel.data_lines()
                if ln.get_color() == levy_color]
    assert len(segments) >= 2, "the levies line is one piece across 2019"
    for xs in segments:
        assert not (min(xs) <= 2018 and max(xs) >= 2019), \
            f"a levies segment joins 2018 to 2019: {xs}"


def test_the_levies_are_insees_own_ratio_and_stop_before_the_forecast():
    panel = plate(SLUG, "fig_fiscal").panel("compulsory levies")
    insee = col("fiscal/tax_burden.csv", "insee")
    drawn = {}
    levy_color = panel.ax.get_legend().get_lines()[2].get_color()
    for ln in panel.data_lines():
        if ln.get_color() == levy_color:
            drawn.update(zip(ln.get_xdata(), ln.get_ydata()))
    assert drawn and all(near(v, insee[int(y)]) for y, v in drawn.items())
    assert max(drawn) <= Country.load(SLUG).last_full_year, \
        "the budget forecast is drawn as though it were a result"


def test_the_primary_balance_is_the_deficit_plus_the_interest_bill():
    """It is a computed column, not a published one: primary balance =
    deficit + interest paid. If that identity stops holding, the interest
    series has been double-counted or signed the wrong way.
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


def test_the_primary_balance_is_drawn_against_the_overall_balance():
    """The spine puts the overall balance (bars) and the primary balance
    (line) on one panel, and the interest bill on its own: the gap between
    the first two is the interest the third draws."""
    fig = plate(SLUG, "fig_fiscal")
    bal = fig.panel("primary balance")
    labels = " ".join(bal.legend_labels()).lower()
    assert "primary balance" in labels and "overall balance" in labels
    prim = col("fiscal/deficit.csv", "primary")
    drawn = bal.points("primary")
    assert drawn and all(near(v, prim[int(y)]) for y, v in drawn.items())
    interest = fig.panel("interest paid")
    assert "interest" in " ".join(interest.lines()).lower()


def test_the_interest_note_says_what_the_data_say():
    """'The debt more than doubled while the interest bill fell': both
    halves are read off the CSVs, in euros and in % of GDP."""
    note = " ".join(plate(SLUG, "fig_fiscal").panel("interest paid").texts())
    debt, nom = col("fiscal/debt.csv", "gross"), \
        col("macro/gdp.csv", "nominal_eurbn")
    it = col("fiscal/deficit.csv", "interest")
    a = min(debt)
    b = min((y for y in it if y <= 2021), key=it.get)
    assert debt[b] * nom[b] > 2 * debt[a] * nom[a], "the debt did not double"
    assert it[b] < it[a]
    assert f"€{debt[a] * nom[a] / 100:,.0f}bn ({a})" in note
    assert f"{it[a]:.1f}% to {it[b]:.1f}%" in note


# ----------------------------------------------------------- spending
def test_the_social_protection_note_is_a_true_share():
    """The old plate said social protection outweighed the rest of the
    state. It never did (about 24% of GDP against 33%). The note now gives
    its share of all spending, which must be the share in the CSV."""
    sp = col("fiscal/spending_by_function.csv", "social_protection")
    tot = col("fiscal/spending_by_function.csv", "total")
    y = max(sp)
    assert sp[y] < tot[y] - sp[y]
    note = " ".join(plate(SLUG, "fig_spending")
                    .panel("social protection vs").texts())
    assert f"{sp[y] / tot[y] * 100:.0f}% of all public spending in {y}" in note


# ------------------------------------------------------------ markets
def test_the_policy_rate_panel_draws_the_deposit_rate_below_zero():
    """Eight years of negative rates are the fact the panel exists for. A
    main-refinancing series spliced in instead never goes below zero, so
    the floor doubles as a check on which series is plotted.
    """
    dfr = plate(SLUG, "fig_markets").panel("policy rate").series("eposit")
    assert min(v for v in dfr if v == v) < 0


def test_every_series_on_the_equity_panel_starts_at_100_in_2006():
    for label, pts in ((k, plate(SLUG, "fig_markets").panel("CAC 40 in US$")
                        .points(k))
                       for k in plate(SLUG, "fig_markets")
                       .panel("CAC 40 in US$").lines()):
        assert near(pts[2006.0], 100.0), f"{label} starts at {pts[2006.0]}"


def test_the_cac_in_dollars_is_the_euro_index_times_the_dollars_move():
    """The label-swap guard of the old 'local terms' panel, re-expressed:
    a dollar investor's CAC is the euro index times the change in dollars
    per euro. The euro ended the window weaker against the dollar than it
    started, so the dollar line must finish below the euro line — swap
    the two labels and this fails."""
    panel = plate(SLUG, "fig_markets").panel("CAC 40 in US$")
    usd, eur = panel.points("CAC 40 in US$"), panel.points("CAC 40 in euros")
    close, eop = col("markets/cac40.csv", "close"), col("macro/eurusd.csv",
                                                        "eop")
    y = 2025
    want = close[y] / close[2006] * eop[y] / eop[2006] * 100
    assert near(usd[float(y)], want)
    assert eop[y] < eop[2006] and usd[float(y)] < eur[float(y)]


def test_the_currency_index_rises_when_the_euro_strengthens():
    """US$ per euro is already quoted so that up is a stronger euro: it is
    rebased, not inverted. 2008 was the euro's peak year."""
    pts = plate(SLUG, "fig_markets").panel("euro against").points("per euro")
    avg = col("macro/eurusd.csv", "avg")
    assert near(pts[2006.0], 100.0)
    assert near(pts[2008.0], avg[2008] / avg[2006] * 100)
    assert pts[2008.0] > 100


def test_the_bund_is_the_reference_and_the_oat_the_country():
    panel = plate(SLUG, "fig_markets").panel("10-year")
    oat, bund = panel.points("OAT"), panel.points("Bund")
    assert all(oat[y] >= bund[y] for y in oat if y in bund), \
        "France's yield below Germany's: the two columns are crossed"


# ----------------------------------------------------------- security
def test_women_killed_by_a_partner_are_a_subset_of_couple_deaths():
    """Every woman killed by her partner is a death within the couple, and
    the couple total also counts men, including perpetrators who then
    killed themselves. The plate states both counts for the last year."""
    women = col("social/violence.csv", "women_killed_by_partner")
    total = col("social/violence.csv", "couple_deaths_total")
    assert women and all(women[y] < total[y] for y in women if y in total)
    y = max(women)
    note = " ".join(plate(SLUG, "fig_security").panel("within the couple")
                    .texts())
    assert (f"{women[y]:.0f} women and {total[y] - women[y]:.0f} men"
            in note)


def test_the_couple_rate_is_women_killed_over_the_female_population():
    """Per 100,000 WOMEN, over the female population of the same year: a
    rate over all people would halve it."""
    panel = plate(SLUG, "fig_security").panel("within the couple")
    women = col("social/violence.csv", "women_killed_by_partner")
    fem = col("social/population_wb.csv", "population_female")
    line = next(ln for ln in panel.data_lines() if len(ln.get_xdata()) > 2)
    drawn = dict(zip(line.get_xdata(), line.get_ydata()))
    for y in (2006, 2019, 2025):
        assert near(drawn[y], women[y] / fem[y] * 1e5), y


def test_the_share_the_title_promises_is_actually_plotted():
    """The women among all deaths within the couple, as a share, on a
    right-hand axis in percent inside 0..100."""
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
    panel = plate(SLUG, "fig_security").panel("within the couple")
    captions = " ".join(panel.texts()).lower()
    assert "women killed by a partner" in captions
    assert "within the couple" in captions
    assert panel.ax.get_legend() is None, \
        "the containment is explained in place, not boxed"


def test_the_two_homicide_systems_stay_two_lines():
    """SSMSI counts what the police recorded, CépiDc counts what a doctor
    certified. They disagree by design and must never become one line."""
    panel = plate(SLUG, "fig_security").panel("two systems")
    blob = " ".join(panel.lines()).lower()
    assert "ssmsi" in blob and "cépidc" in blob
    ss, cc = panel.points("SSMSI"), panel.points("CépiDc")
    assert ss and cc
    assert all(near(v, col("social/homicides.csv", "ssmsi_rate")[int(y)])
               for y, v in ss.items())


def test_recorded_assault_is_per_1000_and_carries_its_caveat():
    """Recorded assault victims over the average population of the same
    year, per 1,000; and the reporting caveat beside the number, because
    the rise after 2017 is substantially more people reporting."""
    a, pop = col("social/violence.csv", "assaults"), pop_avg()
    y0, y1 = min(a), max(a)
    texts = " ".join(plate(SLUG, "fig_security").panel("within the couple")
                     .texts())
    assert (f"{a[y0] / pop[y0] * 1000:.1f} victims per 1,000 people in {y0}, "
            f"{a[y1] / pop[y1] * 1000:.1f} in {y1}") in texts
    assert "reporting" in texts.lower()


def test_road_deaths_are_eurostats_published_rate():
    pts = plate(SLUG, "fig_security").panel("road").points("ONISR")
    per_m = col("social/causes.csv", "road_per_million")
    assert all(near(v, per_m[int(y)] / 10) for y, v in pts.items())


# ------------------------------------------------------- demographics
def test_deaths_overtake_births_before_the_series_ends():
    """2025 is the first year since the war with more deaths than births.
    If this stops being true, either the crossing has been smoothed away
    or the two series have been swapped."""
    panel = plate(SLUG, "fig_demographics").panel("birth and death")
    pairs = panel.paired("Deaths", "Births")
    assert pairs, "the two series never overlap"
    assert any(d > b for _, d, b in pairs), "deaths never overtake births"
    assert not any(d > b for x, d, b in pairs if x < 2025)


def test_the_published_crude_rates_agree_with_the_counts():
    """The plate draws Eurostat's published crude rates; they must be
    INSEE's counts over the average population, or a column is crossed."""
    v = pop_avg()
    dr = col("social/vital_rates.csv", "death_rate")
    deaths = col("social/all_cause_deaths.csv", "insee")
    for y in dr:
        if y in deaths:
            assert abs(dr[y] - deaths[y] / v[y] * 1000) < 0.06, y


def test_the_population_seam_is_not_spliced():
    """Mayotte enters the count on 1 January 2014: the index is drawn as
    two segments, and no segment joins 2013 to 2014."""
    panel = plate(SLUG, "fig_demographics").panel("population")
    segs = [list(ln.get_xdata()) for ln in panel.data_lines()]
    assert not any(min(x) <= 2013 and max(x) >= 2014 for x in segs)
    assert "Mayotte" in " ".join(panel.texts())


# ---------------------------------------------------------- mortality
def test_covid_deaths_are_per_100k_of_the_same_years_population():
    panel = plate(SLUG, "fig_mortality").panel("COVID-19")
    pts = panel.points("CépiDc")
    cep = col("social/covid_deaths.csv", "deaths_cepidc")
    pop = pop_avg()
    for y in (2020, 2024):
        assert near(pts[float(y)], cep[y] / pop[y] * 1e5), y


def test_excess_deaths_are_against_the_2015_19_mean():
    panel = plate(SLUG, "fig_mortality").panel("excess")
    deaths = col("social/all_cause_deaths.csv", "insee")
    base = sum(deaths[y] for y in range(2015, 2020)) / 5
    tops = {round(p.get_x() + p.get_width() / 2): p.get_y() + p.get_height()
            for p in panel.ax.patches
            if p.get_data_transform() is panel.ax.transData
            and p.get_height() != 0}
    assert near(tops[2020], (deaths[2020] / base - 1) * 100)


# -------------------------------------------------------------- credit
def test_household_debt_is_the_bis_share_of_gdp():
    pts = plate(SLUG, "fig_credit").panel("household debt").points("BIS")
    bis = col("credit/household_debt.csv", "hh_debt_pct_gdp_bis_q4")
    assert all(near(v, bis[int(y)]) for y, v in pts.items())


def test_the_stock_rate_moved_far_less_than_new_loans():
    """The plate's whole point: new mortgage rates roughly tripled after
    2021 while the rate on the fixed-rate stock barely moved."""
    panel = plate(SLUG, "fig_credit").panel("mortgage rates")
    new, stock = panel.points("New housing"), panel.points("outstanding")
    assert new[2023.0] - new[2021.0] > 3 * (stock[2023.0] - stock[2021.0])


# ----------------------------------------------------------- migration
def test_immigration_is_per_1000_of_the_average_population():
    pts = plate(SLUG, "fig_migration").panel("immigration and").points(
        "Immigration")
    imm, pop = col("migration/migration.csv", "immigration"), pop_avg()
    for y in (2006, 2022, 2024):
        assert near(pts[float(y)], imm[y] / pop[y] * 1000), y


def test_the_foreign_born_share_uses_its_own_total():
    pts = plate(SLUG, "fig_migration").panel("foreign-born").points(
        "Born abroad")
    fb = col("migration/migration.csv", "foreign_born")
    tot = col("migration/migration.csv", "pop_by_birth")
    assert near(pts[2025.0], fb[2025] / tot[2025] * 100)


# ----------------------------------------------------------- clipping
@pytest.mark.parametrize("name", ["fig_fiscal", "fig_markets", "fig_security",
                                  "fig_demographics", "fig_economy",
                                  "fig_spending", "fig_trade", "fig_world",
                                  "fig_people", "fig_mortality", "fig_credit",
                                  "fig_migration"])
def test_nothing_is_clipped(name):
    """A hardcoded set_ylim silently hides data once the series grows past
    it: the line simply leaves the top of the panel and the reader never
    learns a peak is missing."""
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped(slack=1e-6)
