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
    refetch moves one without the other, this fails."""
    t = by_year("fiscal/transactions_pct_gdp.csv", key="fiscal_year")
    assert float(t[2020]["budgetary_balance"]) == pytest.approx(-14.8)
    assert float(t[2020]["program_expenses_excl_actuarial"]) == \
        pytest.approx(27.4)
    panel = plate(SLUG, "plate_fiscal").panel("budgetary balance")
    # Panel.bars() can't see the patches (their transform is a composite on
    # this matplotlib), so ask the patches directly: the deepest bar on the
    # panel is the 2020-21 deficit.
    heights = [p.get_height() for p in panel.ax.patches]
    assert min(heights) == pytest.approx(-14.8)
    assert any("-14.8%" in s for s in panel.texts())


def test_the_actuarial_split_is_never_back_filled():
    """balance_excl_actuarial exists only from 2008-09: the split was
    created in 2019-20 with 2008-09 onward reclassified. A back-fill from
    the undivided balance would invent the split for years that never
    had one."""
    t = by_year("fiscal/transactions_pct_gdp.csv", key="fiscal_year")
    for y, r in t.items():
        cell = (r["balance_excl_actuarial"] or "").strip()
        if y < 2008:
            assert not cell, f"{y}: actuarial split back-filled"
        else:
            assert cell, f"{y}: actuarial split missing after 2008-09"
    panel = plate(SLUG, "plate_fiscal").panel("budgetary balance")
    pts = panel.points("before net actuarial losses")
    assert min(pts) == 2008


def test_the_federal_debt_panel_reads_the_liabilities_file():
    """The accumulated deficit — what budget documents call 'the federal
    debt' — closed fiscal 2024-25 at C$1,266,480mn; net debt at
    C$1,393,590mn. The panel draws both in C$ trillions."""
    t = by_year("fiscal/liabilities.csv", key="fiscal_year")
    assert float(t[2024]["accumulated_deficit_mn"]) == pytest.approx(1266480)
    assert float(t[2024]["net_debt_mn"]) == pytest.approx(1393590)
    panel = plate(SLUG, "plate_fiscal").panel("federal debt, two measures")
    acc = panel.points("Accumulated deficit")
    net = panel.points("Net debt")
    assert acc[2024.0] == pytest.approx(1.26648)
    assert net[2024.0] == pytest.approx(1.39359)
    # Net debt is published only from 1983; the line must not start earlier.
    assert min(net) == 1983


# ------------------------------------------------------------- markets
def test_the_policy_rate_fall_from_2007_is_on_the_plate():
    """V39079 alone would open the plate at 0.25% with the 2008 easing
    missing. The static monthly table runs from 1998, so the fall from the
    2007 year-end target of 4.25% to 0.25% in 2009 must be drawn."""
    t = by_year("markets/rates.csv")
    assert float(t[2007]["target_rate_eoy"]) == pytest.approx(4.25)
    assert float(t[2009]["target_rate_eoy"]) == pytest.approx(0.25)
    assert float(t[2023]["target_rate_avg"]) == pytest.approx(4.77)
    assert float(t[2026]["target_rate_eoy"]) == pytest.approx(2.25)
    panel = plate(SLUG, "plate_markets").panel("overnight rate")
    pts = panel.points("year-end target")
    assert pts[2007.0] == pytest.approx(4.25)
    assert pts[2009.0] == pytest.approx(0.25)
    assert pts[2023.0] == pytest.approx(5.0)


def test_the_two_dollar_series_are_never_spliced():
    """The USD noon rate was retired in March 2017. The noon line covers
    2008-2016, the daily line 2017 onward, and 2006-07 are holes — a
    part-year average presented as annual would land inside the plausible
    range and nothing would catch it."""
    t = by_year("markets/usdcad.csv")
    for y in (2006, 2007):
        assert not (t[y]["usd_cad_noon_avg"] or "").strip()
        assert not (t[y]["usd_cad_daily_avg"] or "").strip()
    panel = plate(SLUG, "plate_markets").panel("CAD per USD")
    noon = panel.points("noon rate")
    daily = panel.points("daily rate")
    assert min(noon) == 2008 and max(noon) == 2016
    assert min(daily) == 2017
    assert not set(noon) & set(daily), "the two series share a year"
    assert any("never spliced" in s for s in panel.texts())


# ------------------------------------------------------------- the world
def test_the_two_g7_debts_are_drawn_together():
    """2024: Canada at 12.5% of GDP net, 111.3% gross. The net figure nets
    off CPP/QPP assets most of the G7 does not hold in that form, so net is
    never drawn alone — and never above gross."""
    gross = by_year("international/g7_gross_debt.csv")
    net = by_year("international/g7_net_debt.csv")
    assert float(net[2024]["canada"]) == pytest.approx(12.5, abs=0.05)
    assert float(gross[2024]["canada"]) == pytest.approx(111.3, abs=0.05)
    panel = plate(SLUG, "plate_world").panel("two measures")
    pairs = panel.paired("gross", "net of CPP/QPP")
    assert len(pairs) >= 15
    above = [(int(y), g, n) for y, g, n in pairs if n >= g]
    assert not above, f"net at or above gross in {above[:4]}"


def test_the_pandemic_balance_is_general_government_not_federal():
    """−10.9% of GDP in 2020 is the G7-comparable general-government
    balance — calendar years, all levels plus CPP/QPP — not the federal
    fiscal-year −14.8%. The two measure different things and the panel
    must carry the calendar-year one."""
    t = by_year("international/g7_balance.csv")
    assert float(t[2020]["canada"]) == pytest.approx(-10.9, abs=0.05)
    panel = plate(SLUG, "plate_world").panel("balance")
    canada = panel.points("Canada")
    assert canada[2020.0] == pytest.approx(-10.9, abs=0.05)


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
    a factor of two or more."""
    t = by_year("migration/study_permits.csv")
    assert float(t[2023]["permit_holders"]) == 700210
    panel = plate(SLUG, "plate_migration").panel("Study permits")
    heights = [p.get_height() for p in panel.ax.patches]
    assert max(heights) == pytest.approx(700.21)  # drawn in thousands
    assert "flow" in panel.title.lower(), "the title dropped the flow/stock distinction"


# ----------------------------------------------------------- clipping
@pytest.mark.parametrize("name", ["plate_fiscal", "plate_spending",
                                  "plate_markets", "plate_world",
                                  "plate_migration"])
def test_nothing_is_clipped(name):
    """A hardcoded set_ylim silently hides data once a series grows past
    it: the line leaves the top of the panel and the reader never learns a
    peak is missing."""
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped(slack=1e-6)
