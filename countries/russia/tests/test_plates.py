"""The facts Russia's plates assert.

Each test states a claim a plate makes about the country's own data, so a
refetch that invalidates the claim fails loudly instead of quietly changing
a published chart. The claims that matter most here are the four seams:

- the 2014 → 2015 population step is territory (Crimea and Sevastopol), not
  a birth rate, and the Rosstat and UN lines are never spliced;
- Rosstat's December-to-December CPI and the World Bank's annual average
  are two series and no single line is stitched from them;
- the federal budget is not general government: its share of GDP is derived
  from Minfin's roubles over Rosstat's GDP and never added to the IMF line;
- the federal functional breakdown ends in 2021 and stays ended.

And the pending slots: they are asserted to stay pending, so a later pass
that finds the series must delete a test rather than leave a stale claim.
"""

from __future__ import annotations

import csv
import json

import pytest

from core.country import Country
from core import sitebuild
from tests.probe import plate

SLUG = "russia"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    """The data rows of one committed CSV, its '#' provenance lines skipped.

    The provenance sits above the header, so it has to be filtered before
    DictReader reads a line as the header — otherwise the first comment
    becomes the column name and every lookup fails.
    """
    with (DATA / rel).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(
            ln for ln in fh if not ln.lstrip().startswith("#")))


def num(r: dict, key: str) -> float:
    v = (r.get(key) or "").strip()
    return float(v) if v else float("nan")


def by_year(rel: str) -> dict[int, dict]:
    return {int(r["year"]): r for r in rows(rel)}


def texts(plate_name: str, panel: str) -> list[str]:
    return plate(SLUG, plate_name).panel(panel).texts()


def is_pending(plate_name: str, panel: str) -> None:
    p = plate(SLUG, plate_name).panel(panel)
    assert any("pending" in t.lower() or "не собраны" in t.lower()
               or "dados pendentes" in t.lower() for t in p.texts()), \
        f"{panel}: no pending marker"


# ----------------------------------------------------------------- economy
def test_the_three_contractions_are_the_published_index():
    g = by_year("macro/gdp.csv")
    assert num(g[2009], "real_growth_pct") == pytest.approx(-7.82, abs=0.01)
    assert num(g[2015], "real_growth_pct") == pytest.approx(-1.97, abs=0.01)
    assert num(g[2022], "real_growth_pct") == pytest.approx(-1.44, abs=0.01)
    # The World Bank's republication is the same index, not a second one:
    # every year agrees to 0.05 pp, which is what the plate's foot claims.
    e = by_year("macro/economy.csv")
    for y in g:
        assert num(g[y], "real_growth_pct") == pytest.approx(
            num(e[y], "gdp_growth_pct"), abs=0.05), y


def test_the_two_cpi_definitions_are_two_series():
    c = by_year("macro/cpi.csv")
    e = by_year("macro/economy.csv")
    assert num(c[2015], "cpi_dec_pct") == pytest.approx(12.91, abs=0.01)
    assert num(e[2015], "cpi_inflation_pct") == pytest.approx(15.53, abs=0.01)
    assert num(c[2022], "cpi_dec_pct") == pytest.approx(11.94, abs=0.01)
    assert num(e[2022], "cpi_inflation_pct") == pytest.approx(13.74, abs=0.01)
    # They differ in most years, so a single line would be a splice.
    differ = [y for y in c if abs(num(c[y], "cpi_dec_pct")
                                 - num(e[y], "cpi_inflation_pct")) > 0.1]
    assert len(differ) >= 10


def test_the_economy_panel_draws_both_cpi_definitions():
    p = plate(SLUG, "plate_economy").panel("Consumer price inflation")
    labels = p.lines()
    assert any("December to December" in k for k in labels)
    assert any("annual average" in k for k in labels)
    rosstat = p.series("December to December")
    assert rosstat[-1] == pytest.approx(5.59, abs=0.01)


def test_unemployment_is_the_ilo_model_and_says_so():
    e = by_year("macro/economy.csv")
    assert num(e[2009], "unemployment_pct") == pytest.approx(8.301, abs=0.001)
    assert num(e[2025], "unemployment_pct") == pytest.approx(2.133, abs=0.001)
    assert "ILO modelled estimate" in \
        plate(SLUG, "plate_economy").panel("Unemployment rate").legend_labels()


# -------------------------------------------------------------- demography
def test_the_2015_step_is_the_perimeter_and_not_a_demographic_event():
    p = by_year("demography/population.csv")
    step = num(p[2015], "population_mn") - num(p[2014], "population_mn")
    assert step == pytest.approx(2.7, abs=0.05)
    # The same step in the UN series is 0.4m: two territories, not one.
    w = by_year("demography/population_wb.csv")
    un = (num(w[2015], "population") - num(w[2014], "population")) / 1e6
    assert un == pytest.approx(0.40, abs=0.02)
    assert step - un > 2.0


def test_the_two_population_lines_are_never_spliced():
    p = by_year("demography/population.csv")
    w = by_year("demography/population_wb.csv")
    assert num(p[2021], "population_mn") == pytest.approx(147.4, abs=0.05)
    assert num(w[2021], "population") / 1e6 == pytest.approx(144.75, abs=0.01)
    # From 2015 the gap is territory plus the census rebase, and both lines
    # exist every year to 2025: neither is drawn from the other's values.
    gaps = [num(p[y], "population_mn") - num(w[y], "population") / 1e6
            for y in range(2015, 2026)]
    assert min(gaps) == pytest.approx(2.06, abs=0.02)
    assert max(gaps) == pytest.approx(2.76, abs=0.02)
    # The panel states the range it draws rather than a remembered one.
    note = " ".join(texts("plate_demography", "Population"))
    assert "2.1–2.8m people" in note


def test_rates_use_the_components_files_own_population():
    c = by_year("demography/components.csv")
    jan1 = num(c[2021], "population_jan1_thousand")
    natural = num(c[2021], "natural_change_thousand") / jan1 * 1000
    assert natural == pytest.approx(-7.14, abs=0.01)
    # 2014 is suppressed in the component columns and stays blank.
    assert num(c[2014], "natural_change_thousand") != \
        num(c[2014], "natural_change_thousand")
    assert num(c[2014], "population_dec31_thousand") == \
        pytest.approx(146267.3, abs=0.05)


def test_the_population_index_is_inside_the_shared_scale():
    from core import spine
    p = by_year("demography/population.csv")
    base = num(p[2006], "population_mn")
    idx = [num(p[y], "population_mn") / base * 100 for y in p]
    slot = spine.SLOTS["demography.population"]
    lo, hi = spine.fit(slot, (min(idx), max(idx)))[0]
    assert (lo, hi) == slot.ref


# ------------------------------------------------------------------- world
def test_nominal_gdp_hdi_and_reserves_are_the_staged_dollars():
    g = by_year("world/gdp_usd.csv")
    assert num(g[2013], "gdp_usd") / 1e9 == pytest.approx(2292, abs=1)
    assert num(g[2025], "gdp_usd") / 1e9 == pytest.approx(2561, abs=1)
    h = by_year("world/hdi.csv")
    assert max(h) == 2023
    assert num(h[2023], "hdi") == pytest.approx(0.832, abs=0.001)
    r = by_year("world/reserves.csv")
    assert num(r[2024], "reserves_usd") / 1e9 == pytest.approx(608, abs=1)


# ------------------------------------------------------------------ fiscal
def test_the_general_government_line_is_one_imf_vintage():
    f = by_year("fiscal/fiscal.csv")
    assert num(f[2020], "expenditure_pct_gdp") == pytest.approx(39.15, abs=0.01)
    assert num(f[2009], "balance_pct_gdp") == pytest.approx(-5.90, abs=0.01)
    assert num(f[2024], "debt_pct_gdp") == pytest.approx(14.80, abs=0.01)
    # Revenue and expenditure stop in 2024; the 2025 WEO row carries only
    # the balance and the debt, and no forecast is drawn as observed.
    assert num(f[2025], "revenue_pct_gdp") != num(f[2025], "revenue_pct_gdp")
    assert num(f[2025], "debt_pct_gdp") == pytest.approx(16.60, abs=0.01)
    assert num(f[2026], "debt_pct_gdp") != num(f[2026], "debt_pct_gdp")


def test_the_federal_balance_is_a_derived_share_and_not_general_government():
    gdp = by_year("macro/gdp.csv")
    fb = by_year("fiscal/federal_budget.csv")
    # Minfin's own published deficit for 2024 was 1.7% of GDP; the
    # derivation must reproduce it.
    share = num(fb[2024], "balance_bn_rub") / num(gdp[2024],
                                                  "nominal_bn_rub") * 100
    assert share == pytest.approx(-1.72, abs=0.02)
    # And it is a different number from the IMF's general-government line,
    # so the two are never added or substituted.
    f = by_year("fiscal/fiscal.csv")
    assert abs(share - num(f[2024], "balance_pct_gdp")) > 0.1


def test_the_non_oil_and_gas_deficit_is_the_ministrys_own_number():
    gdp = by_year("macro/gdp.csv")
    fb = by_year("fiscal/federal_budget.csv")
    assert num(fb[2025], "non_oil_gas_balance_bn_rub") == \
        pytest.approx(-14103.4, abs=0.05)
    share = num(fb[2025], "non_oil_gas_balance_bn_rub") / \
        num(gdp[2025], "nominal_bn_rub") * 100
    assert share == pytest.approx(-6.58, abs=0.02)


def test_the_fiscal_panel_draws_bars_and_a_labelled_federal_line():
    p = plate(SLUG, "plate_fiscal").panel("Overall balance")
    assert "Federal non-oil-and-gas balance (Minfin)" in p.lines()
    assert len(p.bars()) == 20


# ---------------------------------------------------------------- spending
SPEND_GROUPS = {
    "social_protection": ("social_policy",),
    "health": ("health",),
    "education": ("education",),
    "general_public_services": ("general_government", "debt_service"),
    "economic_affairs": ("national_economy",),
    "defence_order": ("national_defence", "security_law_order"),
    "other": ("housing_utilities", "environment", "culture_media", "media",
              "physical_culture", "interbudgetary"),
}


def test_the_fourteen_sections_reconcile_to_the_published_total():
    sp = by_year("spending/budget_function.csv")
    fb = by_year("fiscal/federal_budget.csv")
    columns = [c for c in rows("spending/budget_function.csv")[0]
               if c != "year"]
    assert len(columns) == 14
    for y in sp:
        total = sum(v for v in (num(sp[y], c) for c in columns) if v == v)
        assert total == pytest.approx(num(fb[y], "expenditure_bn_rub"),
                                      abs=0.25), y


def test_the_breakdown_stops_in_2021_and_stays_ended():
    sp = by_year("spending/budget_function.csv")
    assert max(sp) == 2021
    fb = by_year("fiscal/federal_budget.csv")
    assert max(fb) == 2025
    # The totals continue; only the sections stop. That is the finding.
    assert num(fb[2025], "expenditure_bn_rub") == pytest.approx(42910.3,
                                                               abs=0.05)


def test_the_spending_shares_are_on_the_federal_perimeter():
    gdp = by_year("macro/gdp.csv")
    fb = by_year("fiscal/federal_budget.csv")
    total = num(fb[2021], "expenditure_bn_rub") / \
        num(gdp[2021], "nominal_bn_rub") * 100
    assert total == pytest.approx(18.38, abs=0.02)
    # And the stacked panel states the same number, so the seven groups are
    # the whole of the federal expenditure and not a subset. (A stackplot
    # draws polygons, not bars, so the panel is read from its annotation.)
    note = " ".join(texts("plate_spending", "Spending by function"))
    assert "18.4% of GDP" in note


# ------------------------------------------------------------------- trade
def test_trade_is_the_national_accounts_series_and_its_gap():
    t = by_year("trade/trade.csv")
    assert num(t[2006], "exports_pct_gdp") == pytest.approx(33.73, abs=0.01)
    assert num(t[2025], "exports_pct_gdp") == pytest.approx(18.20, abs=0.01)
    assert num(t[2025], "imports_pct_gdp") == pytest.approx(15.51, abs=0.01)
    for y in t:
        assert num(t[y], "exports_pct_gdp") > num(t[y], "imports_pct_gdp"), y
    # The balance panel states the fall from 2021, computed, not remembered.
    drop = 100 * (1 - (num(t[2025], "exports_pct_gdp")
                       - num(t[2025], "imports_pct_gdp"))
                  / (num(t[2021], "exports_pct_gdp")
                     - num(t[2021], "imports_pct_gdp")))
    note = " ".join(texts("plate_trade", "Trade balance"))
    assert f"{drop:.0f}% smaller" in note


def test_the_trade_lens_is_a_derived_dollar_level():
    t = by_year("trade/trade.csv")
    g = by_year("world/gdp_usd.csv")
    surplus = (num(t[2022], "exports_pct_gdp")
               - num(t[2022], "imports_pct_gdp")) / 100 * \
        num(g[2022], "gdp_usd") / 1e9
    assert surplus == pytest.approx(290, abs=1)
    lens = " ".join(texts("plate_trade", "The surplus in dollars"))
    assert "290" in lens


# ----------------------------------------------------------------- markets
def test_the_key_rate_mean_and_its_peak_are_two_columns():
    k = by_year("markets/key_rate.csv")
    assert num(k[2022], "key_rate_pct") == pytest.approx(10.55, abs=0.01)
    assert num(k[2022], "key_rate_pct_peak") == pytest.approx(20.00, abs=0.01)
    # The instrument begins in 2013; nothing is back-filled onto the
    # refinancing rate before it.
    assert min(k) == 2013


def test_the_rouble_index_falls_and_the_equity_index_with_it():
    f = by_year("markets/usd_rub.csv")
    assert num(f[2006], "rub_per_usd") == pytest.approx(27.1355, abs=0.001)
    assert num(f[2025], "rub_per_usd") == pytest.approx(83.2108, abs=0.001)
    # 2006 = 100, up = stronger: 27.14/83.21 → about 33.
    assert 100 * num(f[2006], "rub_per_usd") / num(f[2025], "rub_per_usd") \
        == pytest.approx(32.6, abs=0.2)
    m = by_year("markets/imoex.csv")
    assert num(m[2025], "imoex_usd_avg") / num(m[2006], "imoex_usd_avg") \
        * 100 == pytest.approx(67, abs=1)
    # The dollar index is the rouble mean at the rate the currency panel
    # draws, so the two panels cannot disagree about a year.
    assert num(m[2025], "imoex_rub_avg") / num(f[2025], "rub_per_usd") == \
        pytest.approx(num(m[2025], "imoex_usd_avg"), abs=0.2)


def test_the_policy_rate_and_inflation_are_different_series():
    p = plate(SLUG, "plate_markets").panel("Policy rate vs inflation")
    assert len(p.lines()) == 2
    key = p.series("Key rate (annual mean)")
    cpi = p.series("CPI")
    assert key[-1] == pytest.approx(19.13, abs=0.01)
    assert cpi[-1] == pytest.approx(5.59, abs=0.01)


# ------------------------------------------------------------------ credit
def test_household_debt_is_the_bis_year_end_reading():
    h = by_year("credit/household_debt.csv")
    assert num(h[2006], "household_debt_pct_gdp") == pytest.approx(8.2, abs=0.05)
    assert num(h[2020], "household_debt_pct_gdp") == pytest.approx(22.0, abs=0.05)
    assert num(h[2024], "household_debt_pct_gdp") == pytest.approx(21.5, abs=0.05)


def test_the_lending_rate_starts_in_2014_and_is_not_extrapolated():
    lr = by_year("credit/household_lending_rate.csv")
    assert min(lr) == 2014
    assert num(lr[2015], "household_lending_rate_pct") == \
        pytest.approx(20.23, abs=0.01)
    assert 2013 not in lr
    # The panel quotes the last complete year, not the partial 2026 mean.
    note = " ".join(texts("plate_credit", "Household lending rate"))
    assert "2025" in note and "2026" not in note


def test_the_credit_lens_is_the_spread_over_the_key_rate():
    lr = by_year("credit/household_lending_rate.csv")
    k = by_year("markets/key_rate.csv")
    spread = num(lr[2014], "household_lending_rate_pct") - \
        num(k[2014], "key_rate_pct")
    assert spread == pytest.approx(10.3, abs=0.05)
    lens = " ".join(texts("plate_credit", "What banks charge above"))
    assert "+10.3" in lens


def test_npl_stops_in_2023_and_keeps_the_hole():
    n = by_year("credit/npl.csv")
    assert min(n) == 2008 and max(n) == 2023
    assert num(n[2023], "npl_pct_loans") == pytest.approx(4.51, abs=0.01)


# ------------------------------------------------------------------ people
def test_gini_and_poverty_stop_where_the_survey_stopped():
    g = by_year("people/gini.csv")
    assert max(g) == 2023
    assert num(g[2007], "gini") == pytest.approx(42.3, abs=0.05)
    assert num(g[2023], "gini") == pytest.approx(33.0, abs=0.05)
    pv = by_year("people/poverty.csv")
    assert num(pv[2024], "poverty_national_pct") == pytest.approx(7.2, abs=0.05)
    assert max(pv) == 2024


def test_the_price_level_is_the_chained_national_cpi():
    c = by_year("macro/cpi.csv")
    run = 100.0
    for y in sorted(c):
        run *= 1 + num(c[y], "cpi_dec_pct") / 100
    assert run / 100 == pytest.approx(4.54, abs=0.01)


def test_the_pending_slots_stay_pending():
    for name, panel in [
            ("plate_people", "Minimum wage"),
            ("plate_spending", "Public investment"),
            ("plate_world", "Corruption Perceptions Index"),
            ("plate_trade", "Top export destinations"),
            ("plate_mortality", "Excess deaths"),
            ("plate_mortality", "COVID-19 deaths"),
            ("plate_migration", "Immigration and emigration")]:
        is_pending(name, panel)


# ---------------------------------------------------------------- security
def test_security_rates_stop_where_the_carriers_stop():
    s = by_year("security/security.csv")
    assert num(s[2006], "homicide_per_100k") == pytest.approx(20.016, abs=0.001)
    assert num(s[2021], "homicide_per_100k") == pytest.approx(6.765, abs=0.001)
    assert num(s[2006], "suicide_per_100k") == pytest.approx(41.44, abs=0.001)
    assert max(y for y in s
               if num(s[y], "road_deaths_per_100k") ==
               num(s[y], "road_deaths_per_100k")) == 2019
    assert max(y for y in s if num(s[y], "homicide_per_100k") ==
               num(s[y], "homicide_per_100k")) == 2021


def test_the_suicide_panel_draws_the_whole_series_inside_the_scale():
    """41.4 per 100,000 now sits under the shared 45 ceiling."""
    from core import spine
    slot = spine.SLOTS["security.suicide"]
    assert slot.ref == (0, 45)
    s = by_year("security/security.csv")
    assert num(s[2006], "suicide_per_100k") <= slot.ref[1]
    p = plate(SLUG, "plate_security").panel("Suicide rate")
    years = [float(x) for ln in p.data_lines()
             for x in ln.get_xdata() if float(x) == float(x)]
    assert min(years) == 2006
    # And the lens draws 2006 for all three causes: six bars, the tallest
    # of which is suicide's 41.4.
    lens = plate(SLUG, "plate_security").panel("Violent and road deaths")
    assert len(lens.bars()) == 6
    assert max(lens.bars()) == pytest.approx(41.44, abs=0.01)


# --------------------------------------------------------------- mortality
def test_the_death_rate_and_life_expectancy():
    m = by_year("mortality/mortality.csv")
    assert num(m[2021], "death_rate_per_1000") == pytest.approx(16.70, abs=0.01)
    assert num(m[2024], "death_rate_per_1000") == pytest.approx(12.40, abs=0.01)
    assert num(m[2006], "life_expectancy") == pytest.approx(66.73, abs=0.01)
    assert num(m[2021], "life_expectancy") == pytest.approx(69.90, abs=0.01)
    assert num(m[2024], "life_expectancy") == pytest.approx(73.44, abs=0.01)


# --------------------------------------------------------------- migration
def test_net_migration_is_modelled_and_uses_its_own_population():
    m = by_year("migration/net_migration.csv")
    pop = by_year("demography/population_wb.csv")
    per = {y: num(m[y], "net_migration") / num(pop[y], "population") * 1000
           for y in m}
    assert per[2022] == pytest.approx(5.31, abs=0.02)
    assert per[2025] == pytest.approx(-1.75, abs=0.02)
    from core import spine
    slot = spine.SLOTS["migration.net"]
    assert slot.ref[0] <= min(per.values()) and max(per.values()) <= slot.ref[1]


def test_the_foreign_born_share_is_a_snapshot():
    m = by_year("migration/migrant_stock.csv")
    pop = by_year("demography/population_wb.csv")
    share = {y: num(m[y], "migrant_stock") / num(pop[y], "population") * 100
             for y in m}
    assert sorted(share) == [2010, 2015, 2020, 2024]
    assert share[2010] == pytest.approx(7.83, abs=0.02)
    assert share[2024] == pytest.approx(5.29, abs=0.02)


# ------------------------------------------------------------- the cards
def test_the_cards_read_the_committed_csvs():
    cards = {ch["id"]: ch for ch in sitebuild.chapters_for(Country.load(SLUG))}
    assert set(cards) == {
        "01-economy", "02-fiscal", "03-spending", "04-trade", "05-markets",
        "06-credit", "07-people", "08-world", "09-demography", "10-security",
        "11-mortality", "12-migration"}
    cpi = cards["01-economy"]["stats"][2]
    assert cpi["year"] == 2025
    e = by_year("macro/cpi.csv")
    assert cpi["value"]["en"].startswith(f"{num(e[2025], 'cpi_dec_pct'):.1f}")


def test_the_headline_strip_leads_gdp_income_population():
    strip = sitebuild.headline_for(Country.load(SLUG))
    labels = [h["label"]["en"] for h in strip]
    assert labels[0] == "GDP"
    assert labels[1].startswith("GDP per person")
    assert labels[2] == "Population"
    g = by_year("world/gdp_usd.csv")
    assert strip[0]["year"] == 2025
    assert num(g[2025], "gdp_usd") / 1e9 == pytest.approx(2561, abs=1)
    assert strip[2]["value"]["ru"].endswith("млн")


def test_the_page_copy_names_the_seams_it_draws():
    ui = json.loads((Country.load(SLUG).dir / "ui.json").read_text())
    for loc in ("en", "ru", "pt"):
        blob = " ".join(ui[loc]["notes"] + [ui[loc]["dek"]]
                        + [f"{u['term']} {u['detail']}"
                           for u in ui[loc]["unavailable"]])
        assert "Crime" in blob or "Крым" in blob or "Crimeia" in blob
        assert "2021" in blob
        assert "403" in blob
        assert len(ui[loc]["unavailable"]) >= 8
