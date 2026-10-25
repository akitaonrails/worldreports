"""The facts Chile's plates assert.

Each test states a claim a plate makes about the country's own data, so a
refetch that invalidates it fails loudly instead of quietly changing a
published chart. The claims that matter most here:

- the national layer is MINSAL/DEIS's registered deaths and the rest is the
  harmonised layer, and the two population denominators never meet in one
  rate;
- the mortality plate draws the national count on DEIS's INE population and
  the World Bank's rate on the UN population as two lines, never joined;
- a survey or a five-year stock keeps its holes and its spacing: CASEN's
  nine observations and the UN migrant stock are markers, not annual lines;
- COFOG begins in 2018 and government investment ends in 2012, and neither
  panel borrows another series' years;
- every slot with no reachable series stays visibly pending, with the Phase
  A route result on the panel rather than a proxy.
"""

from __future__ import annotations

import csv

import pytest

from core.country import Country
from core import sitebuild
from tests.probe import plate

SLUG = "chile"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    """A CSV's data rows, skipping the '#' provenance header it carries."""
    with (DATA / rel).open(encoding="utf-8-sig", newline="") as fh:
        body = [ln for ln in fh if not ln.lstrip().startswith("#")]
    return list(csv.DictReader(body))


def num(r: dict, key: str) -> float:
    v = (r.get(key) or "").strip()
    return float(v) if v else float("nan")


def has(r: dict, key: str) -> bool:
    return (r.get(key) or "").strip() != ""


def by_year(rel: str) -> dict[int, dict]:
    return {int(r["year"]): r for r in rows(rel)}


def texts(plate_name: str, panel: str) -> list[str]:
    return plate(SLUG, plate_name).panel(panel).texts()


def joined(plate_name: str, panel: str) -> str:
    return " ".join(texts(plate_name, panel))


def is_pending(plate_name: str, panel: str) -> None:
    p = plate(SLUG, plate_name).panel(panel)
    assert any("pending" in t.lower() for t in p.texts()), \
        f"{panel}: no pending marker"


# ----------------------------------------------------------------- economy
def test_the_pandemic_year_and_the_rebound_are_the_staged_values():
    e = by_year("macro/economy.csv")
    assert num(e[2020], "real_growth_pct") == pytest.approx(-6.14, abs=0.005)
    assert num(e[2021], "real_growth_pct") == pytest.approx(11.34, abs=0.005)
    assert num(e[2019], "real_growth_pct") == pytest.approx(0.64, abs=0.005)


def test_the_growth_panel_prints_the_numbers_the_csv_holds():
    e = by_year("macro/economy.csv")
    note = joined("plate_economy", "Real GDP growth")
    assert f"{num(e[2020], 'real_growth_pct'):.1f}%" in note
    assert f"{num(e[2019], 'real_growth_pct'):.1f}%" in note


def test_the_growth_bars_are_inside_the_shared_comparison_scale():
    from core import spine
    slot = spine.SLOTS["economy.growth"]
    lo, hi = spine.fit(slot, (-6.14, 11.34))[0]
    assert (lo, hi) == slot.ref


def test_2022_inflation_is_the_window_peak_and_the_note_says_so():
    e = by_year("macro/economy.csv")
    vals = {y: num(r, "inflation_pct") for y, r in e.items()}
    assert max(vals, key=vals.get) == 2022
    assert vals[2022] == pytest.approx(11.64, abs=0.005)
    assert "11.6%" in joined("plate_economy", "Consumer price inflation")


def test_gdp_per_person_is_the_world_banks_current_dollar_level():
    w = by_year("world/world.csv")
    assert num(w[2006], "gdp_per_person_usd") == pytest.approx(9318.66,
                                                              abs=0.01)
    assert num(w[2025], "gdp_per_person_usd") == pytest.approx(17994.59,
                                                              abs=0.01)
    assert "17,995" in joined("plate_economy", "GDP per person")


def test_unemployment_is_the_ilo_modelled_series_and_not_a_national_one():
    e = by_year("macro/economy.csv")
    assert num(e[2020], "unemployment_pct") == pytest.approx(10.93, abs=0.005)
    note = joined("plate_economy", "Unemployment rate")
    assert "ILO" in note
    # The plate draws the modelled column, not the INE survey that Phase A
    # could not reach, so the note must name the modelled basis.
    assert "INE" in note


# ------------------------------------------------------------------ fiscal
def test_the_fiscal_layer_is_general_government_on_imf_numbers():
    f = by_year("fiscal/fiscal.csv")
    assert num(f[2006], "revenue_pct_gdp") == pytest.approx(26.24, abs=0.005)
    assert num(f[2006], "expenditure_pct_gdp") == pytest.approx(18.73,
                                                               abs=0.005)
    assert num(f[2006], "balance_pct_gdp") == pytest.approx(7.50, abs=0.005)
    assert num(f[2021], "balance_pct_gdp") == pytest.approx(-7.50, abs=0.005)
    assert num(f[2025], "debt_pct_gdp") == pytest.approx(41.5, abs=0.05)
    # The primary balance is the overall balance before interest, so it is
    # never the same line.
    assert num(f[2021], "primary_balance_pct_gdp") > num(f[2021],
                                                         "balance_pct_gdp")


def test_the_fiscal_note_prints_the_covid_deficits():
    f = by_year("fiscal/fiscal.csv")
    note = joined("plate_fiscal", "Overall and primary balance")
    assert f"{num(f[2020], 'balance_pct_gdp'):.1f}%" in note
    assert f"{num(f[2021], 'balance_pct_gdp'):.1f}%" in note


def test_the_perimeter_is_named_and_not_spliced():
    """No central-government series is drawn beside the general one."""
    title = joined("plate_fiscal", "Revenue and expenditure")
    assert "IMF" in title or "% of GDP" in title
    # The manifest's national perimeter is pending; the plate draws one
    # perimeter only, so no second revenue line can sit on the panel.
    p = plate(SLUG, "plate_fiscal").panel("Revenue and expenditure")
    assert len(p.lines()) == 2, p.lines()          # revenue, expenditure


def test_interest_paid_stays_pending():
    is_pending("plate_fiscal", "Interest paid")


# ---------------------------------------------------------------- spending
def test_cofog_starts_in_2018_and_ends_in_2024():
    c = by_year("spending/cofog.csv")
    assert min(c) == 2018 and max(c) == 2024
    # 2006-2017 are absent, not zero-filled: the file has no rows for them.
    assert 2017 not in c


def test_the_cofog_divisions_sum_to_the_published_total():
    c = by_year("spending/cofog.csv")
    parts = ("social_protection", "health", "education",
             "general_public_services", "economic_affairs", "defence",
             "public_order", "environment", "housing", "recreation_culture")
    for y, r in c.items():
        assert sum(num(r, k) for k in parts) == pytest.approx(
            num(r, "total"), abs=0.15), y


def test_social_protection_is_the_2021_spike_and_the_note_prints_it():
    c = by_year("spending/cofog.csv")
    assert num(c[2021], "social_protection") == pytest.approx(15.48, abs=0.005)
    note = joined("plate_spending", "Social protection vs everything else")
    assert "15.5%" in note and "6.9%" in note


def test_public_investment_keeps_its_six_year_window():
    i = by_year("spending/public_investment.csv")
    assert sorted(i) == [2007, 2008, 2009, 2010, 2011, 2012]
    assert num(i[2012], "gov_gfcf_pct_gdp") == pytest.approx(2.49, abs=0.005)
    p = plate(SLUG, "plate_spending").panel("Public investment")
    drawn = [ln for ln in p.data_lines()]
    xs = [float(x) for ln in drawn for x in ln.get_xdata()]
    assert max(xs) == 2012, "the panel must not extend past the series"


def test_the_stacked_spend_is_inside_the_shared_scale():
    from core import spine
    slot = spine.SLOTS["spending.by_function"]
    c = by_year("spending/cofog.csv")
    top = max(num(r, "total") for r in c.values())
    assert spine.fit(slot, (0, top))[0] == slot.ref


# ------------------------------------------------------------------- trade
def test_trade_is_the_national_accounts_pair_and_its_derived_gap():
    t = by_year("trade/trade.csv")
    assert num(t[2007], "exports_pct_gdp") == pytest.approx(45.13, abs=0.005)
    assert num(t[2025], "imports_pct_gdp") == pytest.approx(30.42, abs=0.005)
    gap = num(t[2022], "exports_pct_gdp") - num(t[2022], "imports_pct_gdp")
    assert gap == pytest.approx(-3.99, abs=0.005)
    assert num(t[2022], "trade_balance_pct_gdp") == pytest.approx(gap,
                                                                 abs=0.005)


def test_the_destination_slot_is_pending_and_the_lens_is_one_year():
    is_pending("plate_trade", "Top export destinations")
    rows_ = rows("trade/partners_2024.csv")
    shares = [float(r["share_pct"]) for r in rows_]
    assert rows_[0]["partner"] == "China"
    assert shares[0] == pytest.approx(37.75, abs=0.005)
    # The committed file is the top fifteen of 177 partners, 87.05% of the
    # US$98.9bn world total: a snapshot, not the whole customs universe.
    assert len(rows_) == 15
    assert sum(shares) == pytest.approx(87.05, abs=0.02)
    # A snapshot lives in the lens, names its year and draws the top ten.
    panel = plate(SLUG, "plate_trade").panel("Goods exports by destination")
    assert "2024" in panel.title
    assert len(panel.bars()) == 10


# ----------------------------------------------------------------- markets
def test_the_policy_rate_is_the_annual_mean_of_the_daily_target():
    k = by_year("markets/policy_rate.csv")
    assert num(k[2020], "policy_rate_pct") == pytest.approx(0.79, abs=0.005)
    assert num(k[2023], "policy_rate_pct") == pytest.approx(10.50, abs=0.005)
    # 2026 is a running year: it has fewer trading days than any full year.
    assert num(k[2026], "days_observed") < 210
    assert min(num(r, "days_observed") for y, r in k.items() if y < 2026) > 240


def test_the_peso_index_is_2006_base_and_inverted_so_up_is_stronger():
    f = by_year("macro/fx.csv")
    idx = 100 * num(f[2006], "clp_per_usd") / num(f[2025], "clp_per_usd")
    assert idx == pytest.approx(55.74, abs=0.02)
    note = joined("plate_markets", "The peso against the US$")
    assert "55.7" in note
    assert "530" in note and "951" in note


def test_bonds_and_equities_stay_pending():
    is_pending("plate_markets", "10-year government bond yield")
    is_pending("plate_markets", "Main equity index in US$")


# ------------------------------------------------------------------ credit
def test_household_debt_is_the_q4_stock_and_not_the_annual_mean():
    h = by_year("credit/household_credit.csv")
    assert num(h[2006], "hh_debt_pct_gdp_q4") == pytest.approx(26.4, abs=0.05)
    assert num(h[2020], "hh_debt_pct_gdp_q4") == pytest.approx(48.3, abs=0.05)
    assert num(h[2025], "hh_debt_pct_gdp_q4") == pytest.approx(43.8, abs=0.05)
    p = plate(SLUG, "plate_credit").panel("Household debt")
    drawn = {float(x) for ln in p.data_lines() for x in ln.get_xdata()}
    # 2026 has one quarter and no Q4 stock: it cannot be a year on this
    # panel, and the annual mean is never drawn as the year's result.
    assert max(drawn) == 2025
    assert 2026.0 not in drawn


def test_the_cmf_panels_stay_pending():
    is_pending("plate_credit", "Household lending rate")
    is_pending("plate_credit", "Non-performing loans")


# ------------------------------------------------------------------ people
def test_gini_is_nine_survey_observations_never_interpolated():
    g = by_year("people/gini.csv")
    assert sorted(g) == [2006, 2009, 2011, 2013, 2015, 2017, 2020, 2022, 2024]
    assert num(g[2006], "gini") == pytest.approx(47.7, abs=0.05)
    assert num(g[2024], "gini") == pytest.approx(43.0, abs=0.05)
    p = plate(SLUG, "plate_people").panel("Income inequality, Gini")
    markers = [ln for ln in p.data_lines()]
    assert markers, "the survey points are missing"
    for ln in markers:
        assert ln.get_linestyle() in ("None", "none", ""), \
            "a survey series must not be joined by a line"


def test_the_two_poverty_lines_are_two_questions():
    p_ = by_year("people/poverty.csv")
    assert num(p_[2022], "poverty_national_pct") == pytest.approx(6.5,
                                                                 abs=0.05)
    assert not has(p_[2024], "poverty_national_pct")
    assert num(p_[2024], "poverty_830_pct") == pytest.approx(4.5, abs=0.05)
    panel = plate(SLUG, "plate_people").panel("Poverty rate")
    labels = panel.lines()
    assert len(labels) == 2, labels
    assert any("CASEN" in k for k in labels)
    assert any("8.30" in k for k in labels)


def test_the_minimum_wage_is_pending_with_its_next_route_named():
    is_pending("plate_people", "Minimum wage")
    note = joined("plate_people", "Minimum wage")
    assert "bcn.cl" in note


# ------------------------------------------------------------------- world
def test_nominal_gdp_reserves_hdi_and_cpi_are_the_staged_values():
    w = by_year("world/world.csv")
    assert num(w[2006], "gdp_usd_bn") == pytest.approx(153.8, abs=0.05)
    assert num(w[2025], "gdp_usd_bn") == pytest.approx(357.4, abs=0.05)
    assert num(w[2006], "reserves_usd_bn") == pytest.approx(19.4, abs=0.05)
    assert num(w[2025], "reserves_usd_bn") == pytest.approx(49.4, abs=0.05)
    assert num(w[2006], "hdi") == pytest.approx(0.804, abs=0.0005)
    assert num(w[2023], "hdi") == pytest.approx(0.878, abs=0.0005)
    # HDI stops in 2023 with the HDR vintage; CPI starts with the 2012
    # method. Neither is extended.
    assert max(y for y, r in w.items() if has(r, "hdi")) == 2023
    assert min(y for y, r in w.items() if has(r, "cpi_score")) == 2012
    assert num(w[2012], "cpi_score") == 72
    assert num(w[2025], "cpi_score") == 63


# -------------------------------------------------------------- demography
def test_the_population_index_is_2006_base():
    d = by_year("demography/demography.csv")
    idx = 100 * num(d[2025], "population") / num(d[2006], "population")
    assert idx == pytest.approx(120.30, abs=0.01)
    note = joined("plate_demography", "Population (index")
    assert "1.20" in note and "19.9m" in note


def test_fertility_is_below_replacement_throughout():
    d = by_year("demography/demography.csv")
    vals = {y: num(r, "fertility") for y, r in d.items()
            if has(r, "fertility")}
    assert max(vals.values()) < 2.1
    assert vals[2006] == pytest.approx(1.798, abs=0.0005)
    assert vals[2024] == pytest.approx(1.140, abs=0.0005)


def test_natural_increase_is_births_minus_deaths_per_thousand():
    d = by_year("demography/demography.csv")
    for y, r in d.items():
        if has(r, "natural_increase_per_1000"):
            expected = num(r, "birth_rate_per_1000") - num(r, "death_rate_per_1000")
            assert num(r, "natural_increase_per_1000") == pytest.approx(
                expected, abs=0.006), y


def test_the_two_growth_components_are_aligned_by_year():
    d = by_year("demography/demography.csv")
    m = by_year("migration/migration.csv")
    panel = plate(SLUG, "plate_demography").panel(
        "Natural increase and net migration")
    for x, natural, net in panel.paired("Natural increase", "Net migration"):
        y = int(round(x))
        assert natural == pytest.approx(num(d[y], "natural_increase_per_1000"),
                                        abs=0.006)
        assert net == pytest.approx(num(m[y], "net_migration_per_1000"),
                                    abs=0.006)


# ---------------------------------------------------------------- security
def test_homicide_rises_after_2019_and_stops_in_2023():
    s = by_year("security/security.csv")
    assert num(s[2015], "homicide_per_100k") == pytest.approx(2.32, abs=0.005)
    assert num(s[2019], "homicide_per_100k") == pytest.approx(4.81, abs=0.005)
    assert num(s[2022], "homicide_per_100k") == pytest.approx(6.80, abs=0.005)
    assert num(s[2023], "homicide_per_100k") == pytest.approx(6.35, abs=0.005)
    assert max(y for y, r in s.items() if has(r, "homicide_per_100k")) == 2023


def test_the_degree_of_the_rise_is_in_the_note():
    note = joined("plate_security", "Homicide rate")
    assert "2.3" in note and "4.8" in note and "6.3" in note


def test_suicide_and_road_deaths_keep_their_last_published_years():
    s = by_year("security/security.csv")
    assert max(y for y, r in s.items() if has(r, "suicide_per_100k")) == 2021
    assert max(y for y, r in s.items() if has(r, "road_deaths_per_100k")) == 2019


def test_the_rates_are_drawn_as_published_not_recomputed():
    """UNODC and WHO publish rates on their own population basis."""
    s = by_year("security/security.csv")
    panel = plate(SLUG, "plate_security").panel("Homicide rate")
    ln = panel.data_lines()[0]
    got = {float(x): float(y) for x, y in zip(ln.get_xdata(), ln.get_ydata())}
    for y in (2006, 2019, 2023):
        assert got[y] == pytest.approx(num(s[y], "homicide_per_100k"),
                                       abs=1e-9)


# --------------------------------------------------------------- mortality
def test_the_national_rate_is_deaths_over_deis_population():
    m = by_year("mortality/mortality.csv")
    for y in (2010, 2019, 2021, 2025):
        expected = num(m[y], "deaths") / num(m[y], "population") * 1000
        assert num(m[y], "crude_death_rate_national") == pytest.approx(
            expected, abs=0.0051), y
    assert num(m[2019], "crude_death_rate_national") == pytest.approx(5.72,
                                                                     abs=0.005)
    assert num(m[2021], "crude_death_rate_national") == pytest.approx(6.98,
                                                                     abs=0.005)


def test_the_two_death_rate_lines_have_different_denominators():
    m = by_year("mortality/mortality.csv")
    panel = plate(SLUG, "plate_mortality").panel("Crude death rate")
    labels = panel.lines()
    assert len(labels) == 2, labels
    national = panel.points("MINSAL")
    bank = panel.points("World Bank")
    for y in (2019, 2021):
        assert national[float(y)] == pytest.approx(
            num(m[y], "crude_death_rate_national"), abs=1e-9)
        assert bank[float(y)] == pytest.approx(
            num(m[y], "crude_death_rate_wb"), abs=1e-9)
    # One series is DEIS's count on DEIS's population, the other is the
    # World Bank's estimate on the UN population: they are not one line.
    assert national[2019.0] != bank[2019.0]
    d = by_year("demography/demography.csv")
    pop_ratio = num(m[2019], "population") / num(d[2019], "population")
    assert pop_ratio == pytest.approx(0.9953, abs=0.0002)


def test_excess_deaths_use_the_2015_2019_baseline_and_stay_blank_before():
    m = by_year("mortality/mortality.csv")
    base = sum(num(m[y], "deaths") for y in range(2015, 2020)) / 5
    assert base == pytest.approx(105_681, abs=1)
    for y in range(2010, 2020):
        assert not has(m[y], "excess_deaths_pct_vs_2015_2019"), y
    assert num(m[2021], "excess_deaths_pct_vs_2015_2019") == pytest.approx(
        29.9, abs=0.05)
    assert num(m[2025], "excess_deaths_pct_vs_2015_2019") == pytest.approx(
        21.5, abs=0.05)


def test_the_deaths_lens_counts_the_deaths_and_marks_the_baseline():
    m = by_year("mortality/mortality.csv")
    panel = plate(SLUG, "plate_mortality").panel("Deaths registered a year")
    ln = panel.data_lines()[0]
    pts = {float(x): float(y) for x, y in zip(ln.get_xdata(), ln.get_ydata())}
    assert pts[2021.0] == pytest.approx(num(m[2021], "deaths"), abs=0.01)
    note = joined("plate_mortality", "Deaths registered a year")
    assert "137,267" in note
    assert "105,681" in joined("plate_mortality", "Deaths registered a year")


def test_covid_deaths_stay_pending():
    is_pending("plate_mortality", "COVID-19 deaths")


# --------------------------------------------------------------- migration
def test_net_migration_per_thousand_is_the_count_over_population():
    m = by_year("migration/migration.csv")
    d = by_year("demography/demography.csv")
    for y in (2006, 2018, 2025):
        expected = num(m[y], "net_migration") / num(d[y], "population") * 1000
        assert num(m[y], "net_migration_per_1000") == pytest.approx(
            expected, abs=0.006), y
    assert num(m[2018], "net_migration_per_1000") == pytest.approx(12.59,
                                                                  abs=0.005)


def test_the_foreign_born_share_is_a_five_year_stock_and_not_a_line():
    m = by_year("migration/migration.csv")
    d = by_year("demography/demography.csv")
    years = sorted(y for y, r in m.items() if has(r, "migrant_stock"))
    assert years == [2010, 2015, 2020, 2024]
    for y in years:
        expected = num(m[y], "migrant_stock") / num(d[y], "population") * 100
        assert num(m[y], "foreign_born_share_pct") == pytest.approx(
            expected, abs=0.01), y
    panel = plate(SLUG, "plate_migration").panel("Foreign-born share")
    for ln in panel.data_lines():
        assert ln.get_linestyle() in ("None", "none", "")


def test_the_migration_lens_is_persons_a_year():
    m = by_year("migration/migration.csv")
    panel = plate(SLUG, "plate_migration").panel(
        "Net migration, people a year")
    heights = panel.bars()
    assert max(heights) == pytest.approx(num(m[2018], "net_migration"),
                                        abs=0.01)
    note = joined("plate_migration", "Net migration, people a year")
    assert "237,807" in note


def test_the_register_flows_stay_pending():
    is_pending("plate_migration", "Immigration and emigration")


# ------------------------------------------------------------- the cards
def test_the_twelve_cards_and_the_headline_order():
    cards = {ch["id"]: ch for ch in sitebuild.chapters_for(Country.load(SLUG))}
    assert set(cards) == {
        "01-economy", "02-fiscal", "03-spending", "04-trade", "05-markets",
        "06-credit", "07-people", "08-world", "09-demography", "10-security",
        "11-mortality", "12-migration"}
    from core import sitebuild as sb
    head = sb.headline_for(Country.load(SLUG))
    labels = [h["label"]["en"] for h in head]
    assert labels[0] == "GDP"
    assert labels[1].startswith("GDP per person")
    assert labels[2] == "Population"
    assert len(head) >= 6


def test_every_card_figure_comes_from_a_committed_csv():
    cards = sitebuild.chapters_for(Country.load(SLUG))
    e = by_year("macro/economy.csv")
    cpi = cards[0]["stats"][1]
    assert cpi["year"] == 2025
    assert cpi["value"]["en"].startswith(f"{num(e[2025], 'inflation_pct'):.1f}")
    gdp = cards[0]["stats"][3]
    assert gdp["value"]["en"].startswith("17,994") or \
        gdp["value"]["en"].startswith("17,995")


def test_the_chilean_peso_is_written_in_each_locale():
    """CLP must not collide with another peso in the atlas."""
    from core import sitebuild as sb
    c = Country.load(SLUG)
    out = sb.SiteContext(c).render(357.4, "money_bn")
    assert out["en"].startswith("CLP ")
    assert out["es"].startswith("$ ")
    assert out["pt"].startswith("CLP$ ")

def test_the_recession_bands_are_exactly_the_negative_growth_years():
    """country.yaml's bands are read off the staged GDP vintage."""
    import yaml
    conf = yaml.safe_load((DATA.parent / "country.yaml").read_text(
        encoding="utf-8"))
    bands = {(int(round(b["from"] + 0.5)), int(round(b["to"] - 0.5)))
             for b in conf["bands"]}
    e = by_year("macro/economy.csv")
    fell = {y for y, r in e.items() if num(r, "real_growth_pct") < 0}
    assert fell == {y for a, b in bands for y in range(a, b + 1)}


def test_the_2021_gap_above_the_baseline_is_the_number_the_notes_quote():
    m = by_year("mortality/mortality.csv")
    base = sum(num(m[y], "deaths") for y in range(2015, 2020)) / 5
    assert num(m[2021], "deaths") - base == pytest.approx(31_586, abs=1)
