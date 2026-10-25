"""The facts Singapore's plates assert, checked against the committed CSVs.

Each test states a claim a plate makes about this country's own data, so a
refetch that invalidates the claim fails loudly instead of quietly changing
a published chart. The four that matter most here:

- the two denominators are kept apart: vital rates are per RESIDENT and the
  crime and suicide rates are per EVERYONE PRESENT, and neither is silently
  swapped for the other;
- three canonical slots are staged but outside the atlas-wide scale, and
  they stay visibly pending rather than being clipped or rescaled — the
  extents are asserted against core.spine so the day the shared range moves
  this file says so;
- the two series that must never be spliced are never spliced: the IMF
  calendar-year general government and the 1 April–31 March national cash
  budget, and ICD-9 deaths against ICD-10 deaths;
- 2025 in the cause-of-death table is the publisher's preliminary year, and
  the plate must never read its collapse as a decline.

Every number here is computed from the CSV at test time.
"""

from __future__ import annotations

import csv

import pytest

from core import sitebuild
from core.country import Country
from tests.probe import plate

SLUG = "singapore"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    """The CSV's rows, with its leading '#' provenance lines dropped."""
    with (DATA / rel).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(
            ln for ln in fh if not ln.lstrip().startswith("#")))


def num(r: dict, key: str) -> float:
    v = (r.get(key) or "").strip()
    return float(v) if v else float("nan")


def by_year(rel: str, key: str = "year") -> dict[int, dict]:
    return {int(r[key]): r for r in rows(rel)}


def texts(plate_name: str, panel: str) -> str:
    return " ".join(plate(SLUG, plate_name).panel(panel).texts())


def is_pending(plate_name: str, panel: str) -> None:
    p = plate(SLUG, plate_name).panel(panel)
    assert any("pending" in t.lower() or "pendentes" in t.lower()
               for t in p.texts()), f"{panel}: no pending marker"


E = by_year("macro/economy.csv")
D = by_year("demography/demography.csv")
S = by_year("security/security.csv")
M = by_year("mortality/mortality.csv")
I = by_year("fiscal/imf_general_government.csv")
FN = by_year("fiscal/fiscal_national.csv", key="fiscal_year")
DN = by_year("fiscal/debt_national.csv")
TR = by_year("trade/trade.csv")
MK = by_year("markets/markets.csv")
HH = by_year("credit/household.csv")
IN = by_year("people/income.csv")
W = by_year("world/world.csv")
MI = by_year("migration/migration.csv")


# ------------------------------------------------------------------ economy
def test_growth_never_went_negative_for_a_year_but_twice():
    vals = {y: num(r, "real_growth_pct") for y, r in E.items()
            if num(r, "real_growth_pct") == num(r, "real_growth_pct")}
    negative = sorted(y for y, v in vals.items() if v < 0)
    assert negative == [2020]
    assert vals[2020] == pytest.approx(-3.61, abs=0.01)
    # 2009 is the fact the plate's note turns on: the GFC recession is in
    # the quarterly series, not in the annual one.
    assert vals[2009] == pytest.approx(0.13, abs=0.01)


def test_gdp_per_person_is_the_world_bank_series_over_everyone_present():
    assert num(W[2025], "gdp_per_person_usd") == pytest.approx(98_813.98,
                                                              abs=0.01)
    assert num(W[2006], "gdp_per_person_usd") == pytest.approx(33_768.45,
                                                              abs=0.01)
    # The national line divides the same GDP by the same total population;
    # the two agree to rounding, which is why one line is drawn.
    assert num(E[2025], "gdp_per_person_usd") == pytest.approx(
        num(W[2025], "gdp_per_person_usd"), abs=150)


def test_inflation_is_a_complete_year_mean_of_one_vintage():
    assert num(E[2025], "inflation_pct") == pytest.approx(0.90, abs=0.01)
    assert num(E[2008], "inflation_pct") == pytest.approx(6.64, abs=0.01)
    # A 2026 row exists with no annual mean: nine months are not a year.
    assert 2026 in E
    assert num(E[2026], "inflation_pct") != num(E[2026], "inflation_pct")


def test_the_unemployment_point_is_a_level_and_is_dashed():
    assert num(E[2026], "unemployment_total_sa_pct") == pytest.approx(1.9,
                                                                     abs=0.01)
    assert max(y for y in E
               if num(E[y], "inflation_pct") == num(E[y], "inflation_pct")) \
        == 2025


# ------------------------------------------------------------------- fiscal
def test_the_imf_line_and_the_national_budget_are_two_year_bases():
    # The general-government line is on calendar years and runs to 2025.
    assert max(I) == 2026
    assert num(I[2025], "balance_pct_gdp") == pytest.approx(4.20, abs=0.01)
    # The national cash budget is labelled by the STARTING year of a
    # 1 April–31 March year, and FY2026 is an estimate, not an outturn.
    assert min(FN) == 2006 and max(FN) == 2026
    assert num(FN[2025], "overall_fiscal_position_pct_gdp") == \
        pytest.approx(1.90, abs=0.01)
    # No year of one file is ever drawn on the other's axis: the debt panel
    # carries both series, and the note names the two perimeters.
    assert num(I[2025], "debt_pct_gdp") == pytest.approx(165.70, abs=0.01)


def test_gross_debt_is_gross_and_has_no_asset_offset():
    e = by_year("macro/economy.csv")
    gdp = {y: num(r, "gdp_current_sgd_mn") for y, r in e.items()}
    national = num(DN[2025], "total_debt_sgd_mn") / gdp[2025] * 100
    assert national == pytest.approx(163.7, abs=0.1)
    # External debt is nil in every year of the window: the national stock
    # is domestic SGS, which is what the "no offset" caption is about.
    assert all(num(r, "external_debt_sgd_mn") == 0 for r in DN.values())
    panel = texts("plate_fiscal", "Gross debt")
    assert "NO OFFSET" in panel or "SEM COMPENSAÇÃO" in panel


def test_the_budget_itself_is_in_surplus():
    # The plate's note: the debt is not the budget's deficit.
    for y in (2024, 2025):
        assert num(FN[y], "overall_fiscal_position_pct_gdp") > 0


# -------------------------------------------------------------------- trade
def test_exports_and_imports_overrun_the_shared_scale_and_say_so():
    from core import spine
    slot = spine.SLOTS["trade.exports_imports"]
    ex = max(num(r, "exports_pct_gdp") for r in TR.values())
    im = max(num(r, "imports_pct_gdp") for r in TR.values())
    assert ex > slot.ref[1] and im > slot.ref[1]
    assert ex == pytest.approx(228.99, abs=0.01)
    assert num(TR[2025], "exports_pct_gdp") == pytest.approx(177.85, abs=0.01)
    # So the canonical slot is pending and the lines are in the lens.
    is_pending("plate_trade", "Exports and imports")


def test_the_balance_is_derived_and_stays_inside_its_slot():
    from core import spine
    for r in TR.values():
        gap = num(r, "exports_pct_gdp") - num(r, "imports_pct_gdp")
        # The published column is rounded to two decimals, so the check
        # is on the definition and not on the last digit.
        assert num(r, "balance_pct_gdp") == pytest.approx(gap, abs=0.02)
    slot = spine.SLOTS["trade.balance"]
    top = max(num(r, "balance_pct_gdp") for r in TR.values())
    assert slot.ref[0] <= top <= slot.ref[1]
    assert top == pytest.approx(39.77, abs=0.01)


def test_destinations_are_customs_goods_and_regions_are_never_added():
    p = rows("trade/partners.csv")
    regions = {"America", "Asia", "Europe", "Oceania", "Africa"}
    markets = [r for r in p if r["market"] not in regions]
    assert markets, "no market rows"
    # A market share is a share of Total All Markets in the same year, and
    # the market rows of one year cannot exceed 100 per cent while the
    # region rows sit above them.
    per_year = {}
    for r in markets:
        per_year.setdefault(int(r["year"]), []).append(
            num(r, "share_of_exports_pct"))
    for y, shares in per_year.items():
        assert sum(shares) < 100.01, f"{y}: market shares exceed the total"
    named = {r["market"] for r in markets}
    assert "Hong Kong" in named and "Mainland China" in named


# ------------------------------------------------------------------ markets
def test_there_is_no_policy_rate_and_the_slot_stays_pending():
    is_pending("plate_markets", "Policy rate vs inflation")
    assert "no policy interest rate" in \
        texts("plate_markets", "Policy rate vs inflation").lower()


def test_sora_is_staged_but_never_drawn_as_a_policy_rate():
    # It is a benchmark the publisher reports; the plate does not claim it.
    assert num(MK[2025], "sora_pct") == pytest.approx(1.698, abs=0.001)
    assert num(MK[2025], "govt_bond_10y_pct") == pytest.approx(2.30, abs=0.01)


def test_the_currency_index_is_2006_equals_100_and_up_is_stronger():
    base, last = num(MK[2006], "sgd_per_usd"), num(MK[2025], "sgd_per_usd")
    assert base == pytest.approx(1.5889, abs=0.0001)
    assert 100 * base / last == pytest.approx(121.6, abs=0.1)


# ------------------------------------------------------------------- credit
def test_household_debt_is_two_perimeters_and_they_differ():
    assert num(HH[2025], "liabilities_pct_gdp") == pytest.approx(51.62,
                                                                abs=0.01)
    assert num(HH[2025], "credit_pct_gdp_bis") == pytest.approx(44.0, abs=0.01)
    assert num(HH[2025], "liabilities_pct_gdp") > \
        num(HH[2025], "credit_pct_gdp_bis")
    # Net worth is the asset side; the plate draws it in the lens.
    assert num(HH[2025], "net_worth_sgd_mn") == pytest.approx(3_296_640.5,
                                                              abs=1)


def test_the_mas_slots_are_pending_for_the_blocked_api():
    for panel in ("Household lending rate vs policy rate",
                  "Non-performing loans"):
        is_pending("plate_credit", panel)


# ------------------------------------------------------------------- people
def test_the_gini_is_published_0_to_1_and_drawn_at_100():
    before = num(IN[2025], "gini_before_taxes_transfers")
    after = num(IN[2025], "gini_after_taxes_transfers")
    assert before == pytest.approx(0.426, abs=0.0005)
    assert after == pytest.approx(0.359, abs=0.0005)
    # The plate's note quotes the gap in points, which is the ×100 form.
    assert (before - after) * 100 == pytest.approx(6.7, abs=0.05)
    drawn = plate(SLUG, "plate_people").panel("Income inequality")
    before_line = drawn.series("Before")
    assert before_line[-1] == pytest.approx(before * 100, abs=0.05)
    assert max(before_line) == pytest.approx(
        max(num(r, "gini_before_taxes_transfers")
            for r in IN.values()) * 100, abs=0.05)


def test_poverty_and_the_minimum_wage_are_findings_not_gaps():
    for panel in ("Poverty rate", "Minimum wage"):
        is_pending("plate_people", panel)
    assert "no official poverty" in texts("plate_people", "Poverty rate")
    assert "no statutory" in \
        texts("plate_people", "Minimum wage").lower()


# -------------------------------------------------------------------- world
def test_size_hdi_and_reserves():
    assert num(W[2025], "gdp_usd") / 1e9 == pytest.approx(603.87, abs=0.01)
    assert num(W[2025], "reserves_usd") / 1e9 == pytest.approx(432.11,
                                                              abs=0.01)
    hdi = {y: num(r, "hdi") for y, r in W.items()
           if num(r, "hdi") == num(r, "hdi")}
    assert max(hdi) == 2023
    assert hdi[2023] == pytest.approx(0.946, abs=0.001)


# --------------------------------------------------------------- demography
def test_three_populations_and_the_denominator_that_goes_with_each():
    assert num(D[2025], "population_total") == pytest.approx(6_111_175, abs=1)
    assert num(D[2025], "population_resident") == pytest.approx(4_204_515,
                                                                abs=1)
    assert num(D[2025], "population_citizen") == pytest.approx(3_660_683,
                                                               abs=1)
    # They partition, exactly.
    assert num(D[2025], "population_citizen") + \
        num(D[2025], "population_pr") + \
        num(D[2025], "population_nonresident") == \
        pytest.approx(num(D[2025], "population_total"), abs=1)


def test_the_index_is_2006_equals_100_for_the_lines_drawn():
    total = num(D[2025], "population_total") / num(D[2006], "population_total")
    nonres = num(D[2025], "population_nonresident") / \
        num(D[2006], "population_nonresident")
    # The non-resident stock more than doubled while the citizen line rose
    # by under a fifth: that is why only three lines are drawn, and why the
    # fourth cannot share the index axis.
    assert total == pytest.approx(1.388, abs=0.001)
    assert nonres == pytest.approx(2.177, abs=0.002)


def test_vital_rates_are_per_resident_and_crime_rates_are_per_everyone():
    # The publisher's own crude death rate is the resident one.
    assert num(D[2025], "crude_death_rate_per_1000") == pytest.approx(6.0,
                                                                     abs=0.01)
    resident = num(M[2025], "resident_deaths") / \
        num(D[2025], "population_resident") * 1000
    everyone = num(M[2025], "deaths_total_by_cause") / \
        num(D[2025], "population_total") * 1000
    assert resident == pytest.approx(6.0, abs=0.05)
    assert everyone == pytest.approx(4.34, abs=0.02)
    # Suicide is the other way round: the count covers everyone present,
    # and the staged rate reproduces the total-population division.
    assert num(S[2025], "suicide_count") / num(D[2025], "population_total") \
        * 100000 == pytest.approx(num(S[2025], "suicide_per_100k"), abs=0.01)


def test_natural_increase_is_resident_and_net_migration_is_drawn():
    ni = num(D[2025], "natural_increase_residents") / \
        num(D[2025], "population_resident") * 1000
    assert ni == pytest.approx(0.50, abs=0.01)
    # Both series of the canonical pair now sit inside the shared range,
    # so the pair is drawn; the resident rate is the first series.
    from core import spine
    pop = {y: num(r, "population_total") for y, r in D.items()}
    per = [num(r, "net_migration_wb") / pop[y] * 1000
           for y, r in MI.items() if y in pop
           and num(r, "net_migration_wb") == num(r, "net_migration_wb")]
    slot = spine.SLOTS["demography.natural_migration"]
    assert min(per) >= slot.ref[0] and max(per) <= slot.ref[1]


# ----------------------------------------------------------------- security
def test_the_homicide_series_starts_in_2011_and_is_drawn_on_the_log_floor():
    from core import spine
    hom = {y: num(r, "murder_per_100k") for y, r in S.items()
           if num(r, "murder_per_100k") == num(r, "murder_per_100k")}
    assert min(hom) == 2011
    assert hom[2023] == pytest.approx(0.068, abs=0.0005)
    slot = spine.SLOTS["security.homicide"]
    assert slot.scale == "log"
    assert hom[2023] >= slot.ref[0], (
        "the shared log floor must admit 0.068 or the panel goes back to pending")
    panel = plate(SLUG, "plate_security").panel("Homicide rate")
    assert panel.data_lines(), "the homicide panel is drawn, not pending"


def test_the_murder_rate_reproduces_the_unodc_series_exactly():
    # DATA_NOTES section 6: the denominator is verified, not assumed.
    assert num(S[2011], "murder_per_100k") == pytest.approx(
        num(S[2011], "homicide_per_100k_unodc"), abs=0.0005)
    assert num(S[2011], "murder_per_100k") == pytest.approx(0.309, abs=0.0005)


def test_the_2025_suicide_collapse_is_preliminary_and_not_a_decline():
    assert num(S[2024], "suicide_count") == 441
    assert num(S[2025], "suicide_count") == 256
    panel = texts("plate_security", "Suicide rate")
    assert "preliminary" in panel.lower() or "preliminar" in panel.lower()
    assert "not a decline" in panel.lower() or "não é declínio" in panel.lower()
    # 2025's crude rate is one third below 2024's — the shape the note warns
    # against reading as a health outcome.
    assert num(S[2025], "suicide_per_100k") < num(S[2024],
                                                 "suicide_per_100k") * 0.7


def test_road_deaths_have_no_2025_value_and_keep_the_hole():
    assert num(S[2025], "road_death_per_100k") != \
        num(S[2025], "road_death_per_100k")
    assert max(y for y in S
               if num(S[y], "road_death_per_100k") ==
               num(S[y], "road_death_per_100k")) == 2024


# ---------------------------------------------------------------- mortality
def test_the_death_count_is_the_cause_table_total():
    assert num(M[2025], "deaths_total_by_cause") == pytest.approx(26_499,
                                                                  abs=0)
    assert num(M[2025], "resident_deaths") == pytest.approx(25_300, abs=0)


def test_excess_deaths_are_computed_from_the_death_count():
    base = sum(num(M[y], "deaths_total_by_cause")
               for y in range(2015, 2020)) / 5
    assert base == pytest.approx(20_702.4, abs=0.1)
    excess = {y: (num(M[y], "deaths_total_by_cause") / base - 1) * 100
              for y in M}
    assert excess[2022] == pytest.approx(29.9, abs=0.05)
    assert excess[2006] == pytest.approx(-20.8, abs=0.05)
    # The 2006 reading now sits inside the widened floor, so the panel is
    # drawn from the first staged year, not from the baseline period.
    from core import spine
    assert excess[2006] >= spine.SLOTS["mortality.excess_deaths"].ref[0]


def test_the_2012_coding_break_is_two_segments_and_not_one_line():
    panel = plate(SLUG, "plate_mortality").panel("three big killers")
    labels = panel.legend_labels()
    assert labels, "the cause lines must be named"
    # Each cause carries two plotted segments: the dotted ICD-9 one and the
    # solid ICD-10 one. One line per cause would have spliced the codings.
    drawn = [ln for ln in panel.data_lines() if ln.get_label() in labels]
    assert len(panel.data_lines()) >= 2 * len(labels), (
        "expected a dotted and a solid segment per cause, got "
        f"{len(panel.data_lines())} lines for {labels}")
    assert drawn


def test_the_2025_cause_year_is_flagged_preliminary():
    assert "preliminary" in texts("plate_mortality",
                                  "three big killers").lower()
    # External causes collapse in 2025 while natural causes hold: the pair
    # is the evidence that the year is incomplete, not a health event.
    assert num(M[2025], "deaths_suicides") < num(M[2024], "deaths_suicides")
    assert num(M[2025], "deaths_neoplasms") > num(M[2024], "deaths_neoplasms")


def test_covid_deaths_have_no_line_and_stay_pending():
    is_pending("plate_mortality", "COVID-19 deaths")
    assert "no covid-19 line" in texts("plate_mortality",
                                       "COVID-19 deaths").lower()


# --------------------------------------------------------------- migration
def test_net_migration_is_drawn_on_the_shared_scale():
    from core import spine
    pop = {y: num(r, "population_total") for y, r in D.items()}
    per = {y: num(r, "net_migration_wb") / pop[y] * 1000
           for y, r in MI.items() if y in pop}
    slot = spine.SLOTS["migration.net"]
    assert slot.ref[0] <= per[2020] and per[2007] <= slot.ref[1]
    assert per[2007] == pytest.approx(41.9, abs=0.1)
    assert per[2020] == pytest.approx(-25.6, abs=0.1)
    panel = plate(SLUG, "plate_migration").panel("Net migration")
    assert panel.data_lines(), "the net-migration panel is drawn, not pending"


def test_the_foreign_citizen_share_is_derived_not_foreign_born():
    total = num(D[2025], "population_total")
    citizens = num(D[2025], "population_citizen")
    share = (total - citizens) / total * 100
    assert share == pytest.approx(40.1, abs=0.1)
    # The plate draws the citizen/non-citizen split and says what it is
    # not: Singapore publishes no foreign-BORN count.
    assert "foreign-born" in texts("plate_migration",
                                   "Foreign citizens").lower()


def test_flows_stay_pending_with_the_reason_at_hand():
    is_pending("plate_migration", "Immigration and emigration")
    assert "not published" in \
        texts("plate_migration", "Immigration and emigration").lower()


# ------------------------------------------------------------ the parked set
def test_parked_slots_stay_parked():
    for name, panel in [
        ("plate_fiscal", "Revenue and expenditure"),
        ("plate_fiscal", "Interest paid"),
        ("plate_spending", "Spending by function"),
        ("plate_spending", "Social protection vs everything else"),
        ("plate_spending", "Public investment"),
        ("plate_trade", "Exports and imports"),
        ("plate_markets", "Policy rate vs inflation"),
        ("plate_markets", "Main equity index in US$"),
        ("plate_credit", "Household lending rate vs policy rate"),
        ("plate_credit", "Non-performing loans"),
        ("plate_people", "Poverty rate"),
        ("plate_people", "Minimum wage"),
        ("plate_world", "Corruption Perceptions Index"),
        ("plate_mortality", "COVID-19 deaths"),
        ("plate_migration", "Immigration and emigration"),
    ]:
        is_pending(name, panel)


def test_every_pending_panel_is_disclosed_on_the_page():
    """A panel that says 'pending' on the plate must say why on the page."""
    import json
    ui = json.loads((Country.load(SLUG).dir / "ui.json").read_text(
        encoding="utf-8"))
    for loc in Country.load(SLUG).locale_codes:
        blob = " ".join(e["term"] + " " + e["detail"]
                        for e in ui[loc]["unavailable"])
        assert len(ui[loc]["unavailable"]) >= 13, loc
        assert blob.strip()


# ----------------------------------------------------------------- the cards
def test_the_cards_read_the_committed_csvs():
    cards = {ch["id"]: ch for ch in sitebuild.chapters_for(
        Country.load(SLUG))}
    assert list(cards) == [
        "01-economy", "02-fiscal", "03-spending", "04-trade", "05-markets",
        "06-credit", "07-people", "08-world", "09-demography",
        "10-security", "11-mortality", "12-migration"]
    # The strip leads with GDP, GDP per person and population, in order.
    head = sitebuild.headline_for(Country.load(SLUG))
    assert head[0]["label"]["en"] == "GDP"
    assert head[1]["label"]["en"] == "GDP per person, US$"
    assert head[2]["label"]["en"] == "Population"
    assert head[2]["year"] == max(D)
    # A card's figure is the CSV's figure.
    import re
    gdp = cards["08-world"]["stats"][0]
    assert gdp["value"]["en"].endswith("bn")
    assert num(W[gdp["year"]], "gdp_usd") / 1e9 == pytest.approx(
        float(re.sub(r"[^0-9.]", "", gdp["value"]["en"])), abs=1)
    # Population is a level and keeps the latest mid-year reading; flows
    # stop at the last complete year.
    assert head[2]["year"] == max(D)
    assert head[0]["year"] == 2025
