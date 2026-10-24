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


def test_the_canonical_debt_panel_draws_only_general_government_gross():
    """The accumulated deficit — what budget documents call 'the federal
    debt' — closed fiscal 2024-25 at C$1,266,480mn; net debt at
    C$1,393,590mn. On the spine the fiscal debt panel holds the
    canonical panel draws only general-government gross debt. The federal
    level remains a contextual note sourced from liabilities.csv, so a
    refetch that moves it still fails the note. Net debt is published only
    from 1983; it must stay blank before that."""
    t = by_year("fiscal/liabilities.csv", key="fiscal_year")
    assert float(t[2024]["accumulated_deficit_mn"]) == pytest.approx(1266480)
    assert float(t[2024]["net_debt_mn"]) == pytest.approx(1393590)
    for y, r in t.items():
        if y < 1983:
            assert not (r["net_debt_mn"] or "").strip(), \
                f"{y}: net debt back-filled before its 1983 start"
    panel = plate(SLUG, "plate_fiscal").panel("Gross debt")
    panel.points("General government, gross")
    labels = panel.legend_labels()
    assert not any("accumulated deficit" in label.lower() for label in labels)
    assert not any("net of CPP/QPP" in label for label in labels)
    assert any("C$1.27tn" in s for s in panel.texts()), \
        "the panel no longer quotes the accumulated deficit in C$ from liabilities.csv"


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
def test_g7_net_debt_is_kept_out_of_the_canonical_gross_debt_slot():
    """2024: Canada at 12.5% of GDP net, 111.3% gross on Finance Canada's
    G7 table. The net figure nets off CPP/QPP assets most of the G7 does
    not hold in that form. It remains verified source context but does not
    ride on the canonical gross-debt axis."""
    gross = by_year("international/g7_gross_debt.csv")
    net = by_year("international/g7_net_debt.csv")
    assert float(net[2024]["canada"]) == pytest.approx(12.5, abs=0.05)
    assert float(gross[2024]["canada"]) == pytest.approx(111.3, abs=0.05)
    panel = plate(SLUG, "plate_fiscal").panel("Gross debt")
    panel.points("General government, gross")
    assert not any("net of CPP/QPP" in label for label in panel.legend_labels())


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
    panel = plate(SLUG, "plate_migration").panel("Study permits")
    admissions = panel.points("Permanent residents admitted per year")
    assert min(admissions) == 2015


def test_the_admissions_peak_and_reversal():
    """481k admissions in 2024, cut to 391k in 2025: the policy reversal
    is the chapter's story and its numbers are IRCC's own."""
    t = by_year("migration/pr_admissions.csv")
    assert float(t[2020]["admissions"]) == 183075
    assert float(t[2024]["admissions"]) == 480955
    assert float(t[2025]["admissions"]) == 390625
    panel = plate(SLUG, "plate_migration").panel("Study permits")
    admissions = panel.points("Permanent residents admitted per year")
    pop = by_year("international/population.csv")
    assert admissions[2024] == pytest.approx(
        480955 / float(pop[2024]["population"]) * 1000)


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


# ------------------------------------------------- Statistics Canada national lines
# The seven spine chapters that ride a curated national line beside the
# harmonised one (HANDOFF's switch map). Each test pins at least one
# StatCan number in the slot it switched, including every re-expression
# the plate computes itself (per-1,000 and per-100,000 conversions, the
# two publishers' differences, the excess-deaths house rule), and each
# definitional pair must stay two labelled lines.

def test_statcan_growth_line_is_the_national_accounts_reading():
    """01 economy 1: the bar stays the World Bank redistribution; the
    dotted line is cube 36-10-0699's own chained-FCE2017 growth. 2022 =
    4.7%, 2020 = -5.0% are the fetcher's verified spots."""
    t = by_year("macro/economy_statcan.csv")
    assert float(t[2022]["real_growth_pct"]) == pytest.approx(4.7)
    assert float(t[2020]["real_growth_pct"]) == pytest.approx(-5.0)
    panel = plate(SLUG, "plate_economy").panel("Real GDP growth")
    line = panel.points("Statistics Canada (36-10-0699)")
    assert line[2022] == pytest.approx(4.7)
    assert line[2020] == pytest.approx(-5.0)
    assert any("never spliced" in s for s in panel.texts())


def test_statcan_cpi_line_rides_the_redistribution_and_keeps_the_target():
    """01 economy 3: WB's redistribution and StatCan's own 18-10-0005
    annual-average change (a documented conversion, not a published
    column). 2022 = 6.78% on StatCan's own index."""
    t = by_year("macro/economy_statcan.csv")
    assert float(t[2022]["cpi_inflation_pct"]) == pytest.approx(6.78)
    assert float(t[2009]["cpi_inflation_pct"]) == pytest.approx(0.26)
    panel = plate(SLUG, "plate_economy").panel("Consumer price inflation")
    line = panel.points("18-10-0005")
    assert line[2022] == pytest.approx(6.78)
    assert line[2009] == pytest.approx(0.26)
    assert any("2%" in s and "band" in s for s in panel.texts()), \
        "the 2% target note must survive the second line"


def test_the_lfs_line_never_stitches_onto_the_ilo_estimate():
    """01 economy 4: both series run the full window as two complete
    lines. They agree by calibration, so a stitched hybrid would look
    plausible; the only defence is two unbroken labelled lines."""
    t = by_year("macro/economy_statcan.csv")
    assert float(t[2019]["lfs_unemployment_pct"]) == pytest.approx(5.7)
    assert float(t[2024]["lfs_unemployment_pct"]) == pytest.approx(6.3)
    panel = plate(SLUG, "plate_economy").panel("Unemployment")
    ilo = panel.points("ILO modelled estimate")
    lfs = panel.points("Labour Force Survey")
    assert lfs[2019] == pytest.approx(5.7)
    assert min(lfs) == 2006 and max(lfs) == 2025, "the LFS line is broken"
    assert set(lfs) == set(ilo), "the two lines no longer cover the same years"
    assert any(abs(lfs[y] - ilo[y]) > 0.05 for y in lfs), \
        "the two series came out identical — a splice, not a comparison"
    assert any("calibration, not identity" in s for s in panel.texts())


def test_statcan_trade_pair_and_the_balance_is_a_difference_not_a_column():
    """04 trade 1-2: the national pair is the same national-accounts
    statistic from StatCan's own cube; the balance is computed on the
    plate and must never be stored as a column anywhere."""
    t = by_year("trade/trade_statcan.csv")
    assert float(t[2024]["exports_pct_gdp"]) == pytest.approx(32.47)
    assert float(t[2024]["imports_pct_gdp"]) == pytest.approx(32.65)
    assert not any("balance" in c for c in t[2024]), \
        "the trade balance was stored instead of computed"
    panel = plate(SLUG, "plate_trade").panel("Exports and imports")
    assert panel.points("Exports (StatCan")[2024] == pytest.approx(32.47)
    assert panel.points("Imports (StatCan")[2024] == pytest.approx(32.65)
    panel = plate(SLUG, "plate_trade").panel("Trade balance")
    bal = panel.points("Balance (StatCan difference)")
    assert bal[2024] == pytest.approx(
        float(t[2024]["exports_pct_gdp"]) - float(t[2024]["imports_pct_gdp"]),
        abs=0.01)
    assert any("never averaged" in s for s in panel.texts())


def test_the_three_ginis_are_three_lines_and_the_legend_names_each():
    """06 people 1: market, total and after-tax measure adjacent things;
    StatCan's after-tax line (11-10-0134, ×100) must read 28.1 in 2020
    and 30.1 in 2023 — the values the fetcher verified."""
    g = by_year("social/gini_statcan.csv")
    assert float(g[2020]["gini_aftertax"]) == pytest.approx(0.281)
    assert float(g[2023]["gini_aftertax"]) == pytest.approx(0.301)
    panel = plate(SLUG, "plate_people").panel("Income inequality")
    sc = panel.points("StatCan, after-tax")
    assert sc[2020] == pytest.approx(28.1, abs=0.05)
    assert sc[2023] == pytest.approx(30.1, abs=0.05)
    assert len(panel.legend_labels()) == 3, \
        "the panel must name all three income definitions"


def test_the_two_mbm_bases_are_never_joined_into_one_line():
    """06 people 2: the 2018-base series ends where the 2023-base series
    begins its overlap; joining them would be a rebase seam. In the
    overlapping years the newer basket must read higher on average —
    the panel quotes that gap, so it must not vanish."""
    p = by_year("social/poverty_statcan.csv")
    assert float(p[2018]["mbm_2018_pct"]) == pytest.approx(11.2)
    assert float(p[2024]["mbm_2023_pct"]) == pytest.approx(11.0)
    panel = plate(SLUG, "plate_people").panel("Poverty rate")
    a = panel.points("2018 base")
    b = panel.points("2023 base")
    assert max(a) == 2023, "the 2018-base line grew a year the file never published"
    assert min(b) == 2020, "the 2023-base line predates its own basket"
    assert a[2020] == pytest.approx(6.5) and b[2020] == pytest.approx(7.0)
    assert a[2023] == pytest.approx(10.4) and b[2023] == pytest.approx(11.1)
    both = sorted(set(a) & set(b))
    assert 2020 in both and 2023 in both, "the two bases must visibly overlap"
    gap = sum(b[y] - a[y] for y in both) / len(both)
    assert gap > 0.3, "the newer basket no longer reads higher — check the file"
    assert any("never one" in s for s in panel.texts())


def test_the_national_population_index_is_the_july_vintage():
    """08 demography 1: StatCan's 17-10-0009 July 1 estimate as its own
    2006 = 100 index beside the UN mid-year one — the vintage that
    separates non-permanent residents. 2024 = 41,162,593 is the fetcher's spot."""
    t = by_year("social/population_statcan.csv")
    assert float(t[2024]["population_july1"]) == pytest.approx(41162593)
    panel = plate(SLUG, "plate_demography").panel("Population (index")
    nat = panel.points("StatCan July 1 estimate")
    assert nat[2006] == pytest.approx(100.0)
    assert nat[2024] == pytest.approx(
        100 * float(t[2024]["population_july1"]) / float(t[2006]["population_july1"]),
        abs=0.05)


def test_statcan_fertility_is_the_registration_based_rate():
    """08 demography 2: 13-10-0418 reads 1.26 in 2024, a hundredth from
    the World Bank redistribution — close, but a separate line."""
    t = by_year("social/demography_statcan.csv")
    assert float(t[2024]["total_fertility_rate"]) == pytest.approx(1.26)
    panel = plate(SLUG, "plate_demography").panel("Total fertility")
    sc = panel.points("StatCan (13-10-0418)")
    assert sc[2024] == pytest.approx(1.26)


def test_statcan_crude_rates_the_published_birth_the_computed_death():
    """08 demography 3: the crude birth rate is published (2024 = 8.9);
    the death rate is not a column anywhere — it is the components file's
    July–June death count over that period's July 1 population."""
    d = by_year("social/demography_statcan.csv")
    assert float(d[2024]["birth_rate_per_1000"]) == pytest.approx(8.9)
    comp = by_year("social/components_statcan.csv")
    assert not any("death_rate" in c for c in comp[2024]), \
        "a death-rate column would bypass the documented conversion"
    pop = by_year("social/population_statcan.csv")
    panel = plate(SLUG, "plate_demography").panel("Crude birth and death")
    assert panel.points("Births (StatCan")[2024] == pytest.approx(8.9)
    deaths = panel.points("Deaths (StatCan")
    for y in (2015, 2023):
        want = (float(comp[y]["deaths"])
                / float(pop[y]["population_july1"]) * 1000)
        assert deaths[y] == pytest.approx(want, abs=0.01), \
            f"the {y} death rate is not deaths ÷ that year's July 1 population"


def test_statcan_components_use_the_same_vintage_july_denominator():
    """08 demography 4: components years run July–June, so the rate
    divides by the July 1 population at the period START. Dividing by the
    end-year population would shrink the record 2023-24 migration peak —
    the test pins both readings and asserts the plate chose the vintage
    the panel's note names."""
    comp = by_year("social/components_statcan.csv")
    pop = by_year("social/population_statcan.csv")
    y = 2023

    def per1000(year_pop: int) -> float:
        base = float(pop[year_pop]["population_july1"])
        return ((float(comp[y]["immigrants"]) - float(comp[y]["net_emigration"])
                 + float(comp[y]["net_non_permanent_residents"]))
                / base * 1000)

    ni = (float(comp[y]["births"]) - float(comp[y]["deaths"])
          ) / float(pop[y]["population_july1"]) * 1000
    panel = plate(SLUG, "plate_demography").panel("Natural increase and net")
    inc = panel.points("Natural increase (StatCan")
    mig = panel.points("Net migration (StatCan")
    assert inc[y] == pytest.approx(ni, abs=0.01)
    assert mig[y] == pytest.approx(per1000(y), abs=0.01)
    assert abs(mig[y] - per1000(y + 1)) > 0.2, \
        "the rate no longer depends on which July population is chosen"


def test_statcan_homicide_beside_unodc_two_counts_never_one_line():
    """09 security 1: the police-reported rate (35-10-0068, published
    per 100k) rides beside UNODC's harmonised count. The coroner-
    registered homicide count is a third number — it must not appear
    under either label."""
    t = by_year("social/security_statcan.csv")
    assert float(t[2024]["homicide_rate_per_100k"]) == pytest.approx(1.93)
    panel = plate(SLUG, "plate_security").panel("Homicide rate")
    pol = panel.points("Police-reported")
    uno = panel.points("UNODC")
    assert pol[2024] == pytest.approx(1.93)
    assert min(pol) == 2006 and max(pol) == 2025, "the UCR line is broken"
    assert any(abs(pol[y] - uno[y]) > 0.01 for y in set(pol) & set(uno)), \
        "the two counts came out identical — they are not the same count"
    assert any("never one line" in s for s in panel.texts())


def test_statcan_mortality_the_crude_rate_and_the_house_rule_excess():
    """10 mortality 1-2: the crude death rate divides StatCan's own
    registrations by the July 1 population (2024: 326,779); the excess
    recomputes on the same counts with the house rule — 2015-2019 mean
    of that publisher's own series, never the other's base."""
    m = by_year("social/mortality_statcan.csv")
    pop = by_year("social/population_statcan.csv")
    assert float(m[2024]["deaths_all_causes"]) == pytest.approx(326779)
    panel = plate(SLUG, "plate_mortality").panel("Crude death rate")
    line = panel.points("StatCan deaths ÷")
    for y in (2019, 2024):
        assert line[y] == pytest.approx(
            float(m[y]["deaths_all_causes"])
            / float(pop[y]["population_july1"]) * 1000, abs=0.01)
    base = (sum(float(m[y]["deaths_all_causes"]) for y in range(2015, 2020))
            / 5)
    panel = plate(SLUG, "plate_mortality").panel("Excess deaths")
    ex = panel.points("same house rule")
    for y in (2020, 2022):
        assert ex[y] == pytest.approx(
            (float(m[y]["deaths_all_causes"]) / base - 1) * 100, abs=0.1)
    assert any("2015–2019" in s for s in panel.texts())


def test_statcan_covid_counts_over_the_july_population_per_100k():
    """10 mortality 3: 13-10-0394's U07.1/U07.2/U10.9 counts (2022 =
    19,948) divided by the July 1 population, per 100,000 — beside the
    OECD's published rate, both drawn, never one series."""
    m = by_year("social/mortality_statcan.csv")
    pop = by_year("social/population_statcan.csv")
    assert float(m[2022]["deaths_covid_19"]) == pytest.approx(19948)
    panel = plate(SLUG, "plate_mortality").panel("COVID-19 deaths")
    line = panel.points("StatCan deaths ÷")
    for y in (2021, 2022):
        assert line[y] == pytest.approx(
            float(m[y]["deaths_covid_19"])
            / float(pop[y]["population_july1"]) * 1e5, abs=1.0)


def test_disposable_income_debt_ratio_stays_off_the_canonical_gdp_axis():
    """11 credit 1: BIS over GDP, StatCan over disposable income
    (38-10-0235). 2025 Q4 = 171.89, peak 181.88 in 2022; the ratio must
    never touches the canonical GDP scale."""
    t = by_year("credit/household_credit_statcan.csv")
    assert float(t[2025]["hh_debt_to_disp_income_q4"]) == pytest.approx(171.89)
    panel = plate(SLUG, "plate_credit").panel("Household debt")
    assert max(float(r["hh_debt_to_disp_income_q4"]) for r in t.values()
               if r["hh_debt_to_disp_income_q4"].strip()) == \
        pytest.approx(181.88)
    panel.points("BIS, share of GDP")
    assert not any("disposable" in label.lower()
                   for label in panel.legend_labels())


def test_debt_service_measured_twice_and_mortgages_stay_a_part():
    """11 credit 4: BIS models the ratio on an assumed maturity, StatCan
    measures actual payments (11-10-0065): 2025 Q4 total 14.68, mortgage
    share 7.83. The mortgage line is a part of StatCan's total — it must
    stay under it, and the two publishers must stay apart."""
    t = by_year("credit/debt_service_statcan.csv")
    assert float(t[2025]["hh_dsr_pct_q4"]) == pytest.approx(14.68)
    assert float(t[2025]["mortgage_dsr_pct_q4"]) == pytest.approx(7.83)
    panel = plate(SLUG, "plate_credit").panel("servicing the debt")
    tot = panel.points("StatCan's own payments measure")
    mort = panel.points("mortgage payments alone")
    bis = panel.points("BIS model")
    assert tot[2025] == pytest.approx(14.68)
    assert mort[2025] == pytest.approx(7.83)
    shared = sorted(set(tot) & set(mort))
    assert shared and all(mort[y] < tot[y] for y in shared), \
        "the mortgage share exceeds the total it is a part of"
    assert any(tot[y] != pytest.approx(bis[y], abs=0.05)
               for y in set(tot) & set(bis)), \
        "the modelled and measured ratios came out identical"


def test_the_switched_plates_no_longer_promise_a_pending_line():
    """A stale pending footnote above a drawn national line is the page
    lying about its own data: no switched plate may still say so."""
    for name in ("plate_economy", "plate_spending", "plate_trade",
                 "plate_people", "plate_demography", "plate_security",
                 "plate_mortality", "plate_credit"):
        for s in plate(SLUG, name).texts():
            low = s.lower()
            assert " platform returns" not in low \
                and not any(w in low for w in
                            (" is pending", "are pending", "— pending",
                             "- pending", "pending its outage",
                             "pending (data")), \
                f"{name}: {s!r}"


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
