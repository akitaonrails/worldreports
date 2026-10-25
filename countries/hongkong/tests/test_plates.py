"""The facts Hong Kong's plates assert.

Each test states a claim a plate makes about the SAR's own data, so a refetch
that invalidates the claim fails loudly instead of quietly changing a
published chart. The generic checks — isolation, catalogs, data hygiene, the
built pages — live in tests/ and run against every country.

Everything numeric is read from the committed CSVs at test time. The ones
that matter most here are the definitional seams, because Hong Kong has more
of them than most: two fiscal perimeters, two fiscal calendars, three
population bases, customs trade against national accounts, and a police
series that restarts with a re-based classification.
"""
from __future__ import annotations

import csv

import pytest

from core.country import Country
from tests.probe import plate

SLUG = "hongkong"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(
            ln for ln in fh if not ln.lstrip().startswith("#")))


def _points(panel, needle: str) -> dict[float, float]:
    """Every drawn point labelled like `needle`, across the solid and the
    dashed segment: ctx.line splits a series at the last full year, so one
    series can arrive as two Line2D objects."""
    out = {}
    for ln in panel.data_lines():
        label = ln.get_label()
        if label.startswith("_") or needle.lower() not in label.lower():
            continue
        out.update({float(x): float(y) for x, y in
                    zip(ln.get_xdata(), ln.get_ydata()) if y == y})
    assert out, f"no line labelled like {needle!r} on {panel.title!r}"
    return out


def by_year(rel: str) -> dict[int, dict]:
    return {int(r["year"]): r for r in rows(rel)}


def num(row: dict, col: str) -> float | None:
    v = (row.get(col) or "").strip()
    return float(v) if v else None


# ------------------------------------------------------------- the economy
def test_growth_is_csd_chained_volume_and_pinned_twice():
    """The bars are C&SD's year-on-year chained-volume growth, not a
    difference of levels computed here. Pinned at the 2020 collapse and the
    2025 recovery."""
    g = by_year("macro/gdp.csv")
    panel = plate(SLUG, "plate_economy").panel("Real GDP growth")
    assert len(panel.bars()) == len(g)
    assert num(g[2020], "real_growth_pct") == pytest.approx(-6.5)
    assert num(g[2025], "real_growth_pct") == pytest.approx(3.6)
    assert any("-6.5%" in s for s in panel.texts()), \
        "the 2020 collapse is no longer labelled on the bar"


def test_gdp_per_person_is_the_world_bank_dollar_reading():
    """Slot 2 is the harmonised US$ reading, not the HK$ national figure:
    the peg is what makes the two agree, and on a log scale both would look
    the same, so the source is what the test holds."""
    w = by_year("world/gdp_usd.csv")
    panel = plate(SLUG, "plate_economy").panel("GDP per person")
    ys = [y for ln in panel.data_lines() for y in ln.get_ydata()]
    assert max(ys) == pytest.approx(num(w[2025], "gdp_per_person_usd"),
                                    rel=1e-6)
    assert min(ys) == pytest.approx(num(w[2006], "gdp_per_person_usd"),
                                    rel=1e-6)


def test_the_underlying_cpi_is_a_second_labelled_line():
    """Two CPIs, one panel: the composite index and the underlying index
    that strips the one-off relief measures. They must not be spliced into
    one line, and 2021 shows why — 1.6% against 0.6%."""
    c = by_year("macro/cpi.csv")
    panel = plate(SLUG, "plate_economy").panel("Consumer price inflation")
    labels = panel.legend_labels()
    assert any("composite" in s.lower() for s in labels)
    assert any("underlying" in s.lower() for s in labels)
    assert num(c[2021], "cpi_yoy_pct") == pytest.approx(1.6)
    assert num(c[2021], "underlying_cpi_yoy_pct") == pytest.approx(0.6)


# ---------------------------------------------------------------- the books
def test_the_two_fiscal_perimeters_are_never_joined():
    """The canonical lines are the IMF's general government on calendar
    years; the government's own cash account is a separate dotted line,
    drawn a quarter of a year right of the label it carries. The IMF series
    stops at the last observed year, the cash account runs one further, and
    the test holds both ends."""
    gg = by_year("fiscal/gg_imf.csv")
    gra = by_year("fiscal/govt.csv")
    assert max(gg) == 2024, "the IMF calendar series has moved"
    assert max(gra) == 2025, "the cash account has moved"
    panel = plate(SLUG, "plate_fiscal").panel("Overall and primary balance")
    cash = _points(panel, "Cash account")
    assert max(cash) == pytest.approx(2025 + 0.25), \
        "the cash balance is not drawn on its financial-year midpoint"
    assert min(cash) == pytest.approx(2006 + 0.25)


def test_the_cash_balance_is_the_government_account_over_calendar_gdp():
    """The dotted line is the GRA balance divided by that calendar year's
    GDP — an approximation at the March boundary, stated on the panel. The
    2020 reading is pinned against the two published files."""
    g = by_year("macro/gdp.csv")
    f = by_year("fiscal/govt.csv")
    expected = num(f[2020], "balance_hkd_mn") / num(g[2020],
                                                    "nominal_hkd_mn") * 100
    panel = plate(SLUG, "plate_fiscal").panel("Overall and primary balance")
    assert _points(panel, "Cash account")[2020.25] == pytest.approx(expected)
    assert expected == pytest.approx(-7.6, abs=0.05)


def test_the_imf_overall_balance_is_revenue_minus_expenditure():
    """The bars are derived here from the two IMF columns, not staged as a
    third. 2020 is the pandemic year: 20.68% in, 29.91% out."""
    gg = by_year("fiscal/gg_imf.csv")
    expected = (num(gg[2020], "revenue_pct_gdp")
                - num(gg[2020], "expenditure_pct_gdp"))
    assert expected == pytest.approx(-9.23, abs=0.01)
    bars = plate(SLUG, "plate_fiscal").panel(
        "Overall and primary balance").bars()
    assert len(bars) == len(gg)
    assert min(bars) == pytest.approx(expected)


def test_gross_debt_is_small_and_the_bond_programme_is_why_it_rises():
    """1.4% of GDP in 2006 and 9.2% in 2024: a net creditor issuing paper to
    build a curve. If a refetch turns this into a normal sovereign series,
    the panel's note is no longer true."""
    gg = by_year("fiscal/gg_imf.csv")
    assert num(gg[2006], "gross_debt_pct_gdp") == pytest.approx(1.4)
    assert num(gg[2024], "gross_debt_pct_gdp") == pytest.approx(9.2)
    assert num(gg[2024], "interest_pct_gdp") < 0.5


# -------------------------------------------------------------- what it buys
def test_gce_is_consumption_and_the_shares_still_sum_to_a_hundred():
    """C&SD's functional table is government consumption. Its nine shares
    sum to 100 every year, and the total is well under a fifth of GDP —
    which is why the panel says 'consumption, not total spending'."""
    t = rows("spending/gce_function.csv")
    shares: dict[int, float] = {}
    for r in t:
        if r["function"] == "GCE":
            continue
        shares[int(r["year"])] = shares.get(int(r["year"]), 0.0) \
            + float(r["share_pct"])
    for y, s in shares.items():
        assert s == pytest.approx(100.0, abs=0.35), f"{y}: shares sum to {s}"
    g = by_year("macro/gdp.csv")
    total = by_year("spending/gce_function.csv")
    assert (num(total[2025], "spending_hkd_mn")
            / num(g[2025], "nominal_hkd_mn")) < 0.2


def test_social_protection_reads_under_four_per_cent_of_consumption():
    """The number a reader is most likely to misread. If a future C&SD
    revision puts transfers inside the table, this fails and the panel's
    caption has to change with it."""
    t = {r["function"]: r for r in rows("spending/gce_function.csv")
         if r["year"] == "2025"}
    assert float(t["GCE_social"]["share_pct"]) == pytest.approx(3.7)
    assert float(t["GCE"]["share_pct"]) == pytest.approx(100.0)


# ---------------------------------------------------------------- the wide
def test_the_trade_ratio_is_drawn_where_the_shared_scale_cannot_hold_it():
    """Slot 1 is pending for a scale reason, not a data reason: the ratio
    runs past the atlas's shared 0-100%. The lens draws it, and the test
    holds the extent that blocks the canonical slot."""
    t = by_year("trade/trade_gdp.csv")
    xs = [num(r, "exports_gnfs_pct_gdp") for r in t.values()]
    assert max(xs) > 200 and min(xs) > 100
    canonical = plate(SLUG, "plate_trade").panel("Exports and imports (% of GDP)")
    assert getattr(canonical.ax, "spine_pending", False), \
        "the canonical exports panel is no longer visibly pending"
    lens = plate(SLUG, "plate_trade").panel("Openness")
    assert max(y for ln in lens.data_lines() for y in ln.get_ydata()) > 200


def test_customs_trade_and_national_accounts_are_two_measurements():
    """The merchandise balance is negative in every year; the goods-and-
    services balance is positive in 2025. The gap is services, and neither
    line is the other's continuation."""
    m = by_year("trade/merchandise.csv")
    t = by_year("trade/trade_gdp.csv")
    assert all(num(r, "balance_hkd_mn") < 0 for r in m.values())
    assert num(t[2025], "balance_pct_gdp") == pytest.approx(2.91, abs=0.01)


# ---------------------------------------------------------------- the money
def test_the_peg_is_flat_and_the_effective_rate_is_not():
    """Slot 3 draws the effective index (which moves) beside the bilateral
    rate (which cannot). The band is what makes the peg: 7.75-7.85."""
    fx = by_year("markets/fx.csv")
    rates = [num(r, "hkd_per_usd") for r in fx.values()]
    assert min(rates) > 7.7 and max(rates) < 7.9
    twi = [num(r, "twi_index_2020") for r in fx.values()]
    assert max(twi) - min(twi) > 10
    panel = plate(SLUG, "plate_markets").panel("Currency against the US$")
    assert set(panel.lines()) >= {"Effective rate, trade-weighted",
                                  "HKD per US$ — the peg"}
    assert panel.points("HKD per US$ — the peg")[2006] == pytest.approx(100.0)


def test_the_equity_panel_is_indexed_to_its_own_base_year():
    e = by_year("markets/equity.csv")
    assert num(e[2006], "hsi_usd_index_2006") == pytest.approx(100.0)
    assert num(e[2006], "sp500_usd_index_2006") == pytest.approx(100.0)
    assert num(e[2025], "hsi_usd_index_2006") == pytest.approx(127.89)


def test_base_rate_and_prime_are_annual_means_pinned_at_2024():
    b = by_year("markets/base_rate.csv")
    lr = by_year("markets/lending_rate.csv")
    assert num(b[2024], "base_rate_pct") == pytest.approx(5.57, abs=0.01)
    assert num(lr[2024], "best_lending_rate_pct") == pytest.approx(5.77)


# ------------------------------------------------------------------ people
def test_classified_loans_are_year_end_and_not_an_ifrs_stage_3_ratio():
    """The HKMA's table is ordered Q4, Q2, Q1, Q3 inside a year, so reading
    it by position publishes the third quarter as the year-end. The plate
    filters on Q4 and the card reads the same rows."""
    t = rows("credit/classified_loans.csv")
    q4 = {int(r["year"]): float(r["classified_loans_pct"])
          for r in t if r["quarter"] == "Q4"}
    assert q4[2018] == pytest.approx(0.55)
    assert q4[2025] == pytest.approx(2.01)
    panel = plate(SLUG, "plate_credit").panel("Classified loans")
    assert _points(panel, "Classified loans")[2018.0] == pytest.approx(0.55)


def test_the_household_debt_peak_is_2022_not_2020():
    h = by_year("credit/household_debt.csv")
    vals = {y: num(r, "household_debt_pct_gdp") for y, r in h.items()}
    peak = max(vals, key=vals.get)
    assert peak == 2022 and vals[peak] == pytest.approx(96.3)


# -------------------------------------------------------------- the numbers
def test_the_population_index_has_its_own_base_year():
    p = by_year("demography/population.csv")
    panel = plate(SLUG, "plate_demography").panel("Population (index")
    ys = [y for ln in panel.data_lines() for y in ln.get_ydata()]
    base = num(p[2006], "population")
    assert min(ys) == pytest.approx(100.0)
    assert max(ys) == pytest.approx(max(num(r, "population")
                                        for r in p.values()) / base * 100)


def test_fertility_is_the_fdh_excluded_headline_rate_divided_by_1000():
    """The publisher reports 841 per 1,000 women in 2024. The plate draws
    0.841 children per woman — the one rate comparable with other
    countries."""
    f = by_year("demography/fertility.csv")
    assert num(f[2024], "tfr") == pytest.approx(0.841)
    panel = plate(SLUG, "plate_demography").panel("Total fertility rate")
    assert max(y for ln in panel.data_lines() for y in ln.get_ydata()) \
        == pytest.approx(1.285)


def test_deaths_have_exceeded_births_since_2020():
    c = by_year("demography/components.csv")
    first = min(int(y) for y, r in c.items() if num(r, "natural_change_k") < 0)
    assert first == 2020
    assert num(c[2025], "natural_change_k") == pytest.approx(-18.9)


def test_the_natural_migration_panel_waits_on_the_shared_floor():
    """The panel is pending because -11.5 per 1,000 in 2020 is outside the
    shared -10..+40 scale, not because the data are missing. When the atlas
    widens the slot, this test and the panel both have to change."""
    m = by_year("migration/net_movement.csv")
    low = min(num(r, "net_movement_per_1000") for r in m.values())
    assert low == pytest.approx(-11.5)
    for name, needle in (("plate_demography", "Natural increase and net"),
                         ("plate_migration", "Net migration")):
        panel = plate(SLUG, name).panel(needle)
        assert getattr(panel.ax, "spine_pending", False), \
            f"{name}: the scale-blocked slot is no longer pending"


# --------------------------------------------------------------- the police
def test_the_homicide_rate_is_cases_over_mid_year_population():
    c = by_year("security/crime.csv")
    p = by_year("demography/population.csv")
    for y in (2021, 2024):
        expected = (num(c[y], "murder_and_manslaughter")
                    / num(p[y], "population") * 1e5)
        assert num(c[y], "homicide_rate_per_100k") == pytest.approx(
            expected, abs=0.001)
    assert num(c[2024], "homicide_rate_per_100k") == pytest.approx(0.253)


def test_the_2025_fourth_quarter_anomaly_is_published_as_recorded():
    """170 cases in one quarter against 19 in the other three. The plate
    annotates it; the annual row is 194, which is not what the quarters sum
    to — the publisher's own table, unrevised. Both numbers are read here
    from the committed files rather than copied into the test."""
    q = [r for r in rows("security/cases_from_censtatd.csv")
         if r["series"] == "PP_CASE_RPT"
         and r["dim1_desc"] == "Murder and manslaughter"
         and len(r["period"]) == 6 and r["period"].startswith("2025")]
    q.sort(key=lambda r: r["period"])
    vals = [int(r["value"]) for r in q]
    assert len(vals) == 4
    assert vals[3] == 170
    assert sum(vals[:3]) == 19
    annual = by_year("security/crime.csv")
    assert int(annual[2025]["murder_and_manslaughter"]) == 194
    assert sum(vals) == 189, "the quarters no longer under-sum the annual row"
    texts = plate(SLUG, "plate_security").panel("Homicide rate").texts()
    assert any("170" in t for t in texts) and any("194" in t for t in texts)


# ------------------------------------------------------------- the ordinary
def test_every_slot_that_has_no_series_says_so_on_the_panel():
    """Seven canonical slots have no official machine-readable series in
    Hong Kong at all. Each must be visibly pending rather than plotted from
    a convenient neighbour."""
    for name, needle in (
            ("plate_markets", "10-year government bond yield"),
            ("plate_people", "Income inequality"),
            ("plate_people", "Poverty rate"),
            ("plate_people", "Minimum wage"),
            ("plate_security", "Suicide rate"),
            ("plate_security", "Road traffic deaths"),
            ("plate_migration", "Immigration and emigration"),
            ("plate_migration", "Foreign-born share")):
        panel = plate(SLUG, name).panel(needle)
        assert getattr(panel.ax, "spine_pending", False), \
            f"{name}/{needle}: not pending, and no data were staged for it"
        assert not panel.data_lines() and not panel.bars(), \
            f"{name}/{needle}: something is drawn on a pending panel"


def test_covid_deaths_per_100k_are_computed_from_the_registered_count():
    d = by_year("mortality/deaths.csv")
    p = by_year("demography/population.csv")
    expected = num(d[2022], "covid_deaths") / num(p[2022], "population") * 1e5
    assert expected == pytest.approx(126.5, abs=0.2)
    panel = plate(SLUG, "plate_mortality").panel("COVID-19 deaths")
    assert max(panel.bars()) == pytest.approx(expected, rel=1e-3)


def test_excess_deaths_start_at_the_baseline_and_not_before():
    """The comparison only means something from 2015, the years the mean is
    drawn from; the staged column runs to 2006, where it reads -20.6% and
    would leave the shared -20 floor. The plate draws the window and the
    note says why."""
    d = by_year("mortality/deaths.csv")
    assert num(d[2006], "excess_deaths_pct_vs_2015_2019") == pytest.approx(
        -20.6)
    panel = plate(SLUG, "plate_mortality").panel("Excess deaths")
    xs = [x for ln in panel.data_lines()
          for x in ln.get_xdata()] + [2015]
    assert min(xs) >= 2015


def test_reserves_are_the_exchange_fund_and_the_world_bank_agrees_to_2023():
    """The national series is used because the World Bank stops in 2023; its
    2023 value is exactly the number the bank carries, which is what
    licenses the recent years. Pinned, because that agreement is the whole
    argument for the choice."""
    r = by_year("world/reserves.csv")
    assert num(r[2023], "reserves_usd_mn") == pytest.approx(425554)
    assert num(r[2025], "reserves_usd_mn") > 400000


def test_the_headline_leads_with_the_size_of_the_economy():
    """GDP, then GDP per person, then population — the atlas-wide order, and
    the reason a reader can move between countries without re-learning the
    page."""
    from core import sitebuild
    c = Country.load(SLUG)
    labels = [h["label"]["en"] for h in sitebuild.headline_for(c)]
    assert labels[0] == "GDP"
    assert labels[1].startswith("GDP per person")
    assert labels[2] == "Population"
    assert len(labels) >= 6
