"""The facts Canada's plates assert.

Each test states a claim a plate makes about the country's own data, so a
refetch that invalidates the claim fails loudly instead of quietly changing
a published chart. The generic checks — isolation, catalogs, data hygiene,
the built pages — live in tests/ and run against every country.
"""
from __future__ import annotations

import csv

import pytest

from core.country import Country
from tests.probe import plate

SLUG = "canada"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(
            ln for ln in fh if not ln.lstrip().startswith("#")))


def by_year(rel: str, key: str = "year") -> dict[int, dict]:
    return {int(r[key]): r for r in rows(rel)}


# ------------------------------------------------------------- fiscal
def test_the_pandemic_deficit_is_what_the_plate_says():
    """2020-21: a −14.8% of GDP federal budgetary balance, the largest in
    Canadian peacetime. The CSV says it and the panel prints it; if a
    refetch moves one without the other, this fails. On the spine the
    bars are the general-government balance and the federal fiscal-year
    series rides beside them as a labelled line — the federal number is
    read off that line and its printed label."""
    t = by_year("fiscal/transactions_pct_gdp.csv", key="fiscal_year")
    assert float(t[2020]["budgetary_balance"]) == pytest.approx(-14.8)
    assert float(t[2020]["program_expenses_excl_actuarial"]) == \
        pytest.approx(27.4)
    panel = plate(SLUG, "plate_fiscal").panel("Overall balance")
    fed = panel.points("Federal budgetary balance")
    low = min(fed, key=fed.get)
    assert fed[low] == pytest.approx(-14.8)
    assert low == pytest.approx(2020.25), \
        "the federal deficit is not drawn on its fiscal-year midpoint"
    assert any("-14.8%" in s for s in panel.texts())


def test_the_actuarial_split_is_never_back_filled():
    """balance_excl_actuarial exists only from 2008-09: the split was
    created in 2019-20 with 2008-09 onward reclassified. A back-fill from
    the undivided balance would invent the split for years that never
    had one. The spine's fiscal plate draws the undivided budgetary
    balance; if a future revision puts an actuarial-split line back on
    it, that line may not start before 2008-09 either."""
    t = by_year("fiscal/transactions_pct_gdp.csv", key="fiscal_year")
    for y, r in t.items():
        cell = (r["balance_excl_actuarial"] or "").strip()
        if y < 2008:
            assert not cell, f"{y}: actuarial split back-filled"
        else:
            assert cell, f"{y}: actuarial split missing after 2008-09"
    for panel in plate(SLUG, "plate_fiscal").panels():
        for ln in panel.data_lines():
            if "actuarial" in ln.get_label().lower():
                xs = [float(x) for x in ln.get_xdata() if float(x) == float(x)]
                assert min(xs) >= 2008 + 0.25 - 1e-9, (
                    f"{ln.get_label()!r} drawn before fiscal 2008-09")
    panel = plate(SLUG, "plate_fiscal").panel("Overall balance")
    fed = panel.points("Federal budgetary balance")
    assert min(fed) == pytest.approx(2006.25), (
        "the balance panel no longer draws the undivided federal series "
        "from 2006 — check what replaced it before trusting the split")


def test_the_federal_debt_panel_reads_the_liabilities_file():
    """The accumulated deficit — what budget documents call 'the federal
    debt' — closed fiscal 2024-25 at C$1,266,480mn; net debt at
    C$1,393,590mn. On the spine the fiscal debt panel holds the
    general-government measures; the federal accumulated deficit rides
    beside them as a labelled % GDP line, and the panel's note quotes
    the C$ trillion figure out of liabilities.csv — so a refetch that
    moves the level fails the note. Net debt is published only from
    1983; it must stay blank before that."""
    t = by_year("fiscal/liabilities.csv", key="fiscal_year")
    assert float(t[2024]["accumulated_deficit_mn"]) == pytest.approx(1266480)
    assert float(t[2024]["net_debt_mn"]) == pytest.approx(1393590)
    for y, r in t.items():
        if y < 1983:
            assert not (r["net_debt_mn"] or "").strip(), \
                f"{y}: net debt back-filled before its 1983 start"
    tx = by_year("fiscal/transactions_pct_gdp.csv", key="fiscal_year")
    panel = plate(SLUG, "plate_fiscal").panel("Gross debt")
    acc = panel.points("Federal accumulated deficit")
    assert acc[2024.25] == pytest.approx(float(tx[2024]["accumulated_deficit"])), \
        "the debt panel's federal line is not the ratio in transactions.csv"
    assert any("C$1.27tn" in s for s in panel.texts()), \
        "the panel no longer quotes the accumulated deficit in C$ from liabilities.csv"
    # And the net figure is still drawn only beside the gross one.
    panel.points("General government, gross")
    panel.points("net of CPP/QPP")


# ------------------------------------------------------------- markets
def test_the_policy_rate_fall_from_2007_is_on_the_plate():
    """V39079 alone would open the plate at 0.25% with the 2008 easing
    missing. The static monthly table runs from 1998, so the fall from the
    2007 year-end target of 4.25% to 0.25% in 2009 must be drawn — on the
    spine that is markets slot 1, policy rate vs inflation."""
    t = by_year("markets/rates.csv")
    assert float(t[2007]["target_rate_eoy"]) == pytest.approx(4.25)
    assert float(t[2009]["target_rate_eoy"]) == pytest.approx(0.25)
    assert float(t[2023]["target_rate_avg"]) == pytest.approx(4.77)
    assert float(t[2026]["target_rate_eoy"]) == pytest.approx(2.25)
    panel = plate(SLUG, "plate_markets").panel("Policy rate vs inflation")
    pts = panel.points("overnight rate")
    assert pts[2007.0] == pytest.approx(4.25)
    assert pts[2009.0] == pytest.approx(0.25)
    assert pts[2023.0] == pytest.approx(5.0)


def test_the_two_dollar_series_are_never_spliced():
    """The USD noon rate was retired in March 2017. The noon line covers
    2008-2016, the daily line 2017 onward, and 2006-07 are holes in the
    Bank's own series — a part-year average presented as annual would
    land inside the plausible range and nothing would catch it. On the
    spine the panel is an index (2006 = 100, up = stronger) rebased on
    the Federal Reserve H.10 annual averages; the H.10 line is the only
    one allowed to cover 2006-07, and the Bank's two series still never
    share a year or join across the break."""
    t = by_year("markets/usdcad.csv")
    for y in (2006, 2007):
        assert not (t[y]["usd_cad_noon_avg"] or "").strip()
        assert not (t[y]["usd_cad_daily_avg"] or "").strip()
    panel = plate(SLUG, "plate_markets").panel("Canadian dollar against")
    noon = panel.points("Bank of Canada noon rate")
    daily = panel.points("single daily")
    h10 = panel.points("H.10 noon rate")
    assert min(noon) == 2008 and max(noon) == 2016
    assert min(daily) == 2017
    assert not set(noon) & set(daily), "the two series share a year"
    assert min(h10) == 2006, "the H.10 base must cover the 2006-07 hole"
    assert any("never spliced" in s for s in panel.texts())


# ------------------------------------------------------------- the world
def test_the_two_g7_debts_are_drawn_together():
    """2024: Canada at 12.5% of GDP net, 111.3% gross on Finance Canada's
    G7 table. The net figure nets off CPP/QPP assets most of the G7 does
    not hold in that form, so net is never drawn alone — and never above
    gross. On the spine the pairing lives in fiscal slot 3: the IMF
    gross line and the net-of-CPP/QPP line on one panel, whatever the
    two publishers' vintages make of the same year."""
    gross = by_year("international/g7_gross_debt.csv")
    net = by_year("international/g7_net_debt.csv")
    assert float(net[2024]["canada"]) == pytest.approx(12.5, abs=0.05)
    assert float(gross[2024]["canada"]) == pytest.approx(111.3, abs=0.05)
    panel = plate(SLUG, "plate_fiscal").panel("Gross debt")
    pairs = panel.paired("General government, gross", "net of CPP/QPP")
    assert len(pairs) >= 15
    above = [(int(y), g, n) for y, g, n in pairs if n >= g]
    assert not above, f"net at or above gross in {above[:4]}"


def test_the_pandemic_balance_is_general_government_not_federal():
    """−10.9% of GDP in 2020 is the G7-comparable general-government
    balance — calendar years, all levels plus CPP/QPP — not the federal
    fiscal-year −14.8%. The two measure different things: on the spine
    the calendar one is the bar on the fiscal plate's canonical slot and
    the federal one is the labelled line beside it, drawn at its fiscal
    midpoint. The panel must carry both, and they must stay apart."""
    t = by_year("international/g7_balance.csv")
    assert float(t[2020]["canada"]) == pytest.approx(-10.9, abs=0.05)
    gg = by_year("fiscal/general_government.csv")
    assert float(gg[2020]["balance_pct_gdp"]) == pytest.approx(
        float(t[2020]["canada"]), abs=0.1), \
        "the drawn IMF general-government balance left the G7 table behind"
    panel = plate(SLUG, "plate_fiscal").panel("Overall balance")
    bars = {}
    for p in panel.ax.patches:
        if p.get_data_transform() is panel.ax.transData:
            bars[round(p.get_x() + p.get_width() / 2)] = \
                p.get_y() + p.get_height()
    assert bars[2020] == pytest.approx(-10.9, abs=0.05), \
        "the 2020 bar is not the general-government balance"
    fed = panel.points("Federal budgetary balance")
    assert fed[2020.25] == pytest.approx(-14.8), \
        "the federal line no longer carries the fiscal-year deficit"
    assert abs(bars[2020] - fed[2020.25]) > 2.0, \
        "the two balances are no longer visibly different quantities"


def test_the_hdi_is_one_vintage():
    """HDR 2025's complete time series: Canada 0.939 in 2023. A trend
    assembled from successive annual reports would be partly an artefact
    of the reports."""
    t = by_year("international/hdi.csv")
    assert float(t[2023]["hdi"]) == pytest.approx(0.939)
    panel = plate(SLUG, "plate_world").panel("Human Development")
    assert any("0.939" in s for s in panel.texts())


# ------------------------------------------------------------ migration
def test_the_admissions_series_visibly_starts_in_2015():
    """IRCC's open data begins in 2015. The plate must show the hole, not
    start the axis late: no bar before 2015, and an axis that still opens
    at 2006."""
    t = rows("migration/pr_admissions.csv")
    years = [int(r["year"]) for r in t]
    assert min(years) == 2015
    panel = plate(SLUG, "plate_migration").panel("Permanent residents")
    assert panel.ax.get_xlim()[0] < 2015, "the 2006-14 hole is not visible"
    assert any("begins in 2015" in s for s in panel.texts())


def test_the_admissions_peak_and_reversal():
    """481k admissions in 2024, cut to 391k in 2025: the policy reversal
    is the chapter's story and its numbers are IRCC's own."""
    t = by_year("migration/pr_admissions.csv")
    assert float(t[2020]["admissions"]) == 183075
    assert float(t[2024]["admissions"]) == 480955
    assert float(t[2025]["admissions"]) == 390625
    panel = plate(SLUG, "plate_migration").panel("Permanent residents")
    assert any("480,955" in s for s in panel.texts())


def test_the_top_ten_stays_a_subset_of_the_total():
    """The composition panel draws the ten largest countries of
    citizenship, ranked once. Their sum must stay below the admissions
    total in every year — if it ever exceeds it, a column has been
    mis-keyed."""
    total = by_year("migration/pr_admissions.csv")
    origin = by_year("migration/pr_by_origin.csv")
    for y, r in origin.items():
        if y not in total:
            continue
        s = sum(float(v) for k, v in r.items()
                if k != "year" and (v or "").strip())
        assert s <= float(total[y]["admissions"]), \
            f"{y}: top ten sum {s} exceeds the total"
    assert float(origin[2024]["india"]) == 127380


def test_study_permits_are_a_flow_and_say_so():
    """Permits signed in the period — 700k in 2023 — not the stock of
    students present, which is StatCan's non-permanent-resident estimate.
    A panel that drops the flow/stock distinction misstates the series by
    a factor of two or more. On the spine the lens slot draws the flow
    per 1,000 people: the bar must be the CSV's flow divided by that
    year's population, the peak count must be printed, and the title
    must keep saying flow."""
    t = by_year("migration/study_permits.csv")
    assert float(t[2023]["permit_holders"]) == 700210
    pop = by_year("international/population.csv")
    panel = plate(SLUG, "plate_migration").panel("Study permits")
    heights = [p.get_y() + p.get_height() for p in panel.ax.patches
               if p.get_data_transform() is panel.ax.transData]
    peak = 700210 / float(pop[2023]["population"]) * 1000
    assert max(heights) == pytest.approx(peak), (
        "the permit bar is not the signed flow over the population")
    assert any("700,210" in s for s in panel.texts()), \
        "the panel no longer prints the 2023 flow in people"
    assert "flow" in panel.title.lower(), "the title dropped the flow/stock distinction"


# ----------------------------------------------------------- clipping
@pytest.mark.parametrize("name", ["plate_economy", "plate_fiscal",
                                  "plate_spending", "plate_trade",
                                  "plate_markets", "plate_people",
                                  "plate_world", "plate_demography",
                                  "plate_security", "plate_mortality",
                                  "plate_credit", "plate_migration"])
def test_nothing_is_clipped(name):
    """A hardcoded set_ylim silently hides data once a series grows past
    it: the line leaves the top of the panel and the reader never learns a
    peak is missing. On the spine the canonical scales come from
    core/spine.py and grow with the data, but the lens slots and every
    annotation-bearing panel are still this country's own making."""
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped(slack=1e-6)
