"""The facts Italy's plates assert.

Each test states a claim a plate makes about the country's own data, so a
refetch that invalidates the claim fails loudly instead of quietly changing
a published chart. The recession bands in particular are pinned to the
quarter-on-quarter sign runs of the staged vintage (DATA_NOTES) — a band
re-cut off a different vintage must be a deliberate edit here, not a drift.
The generic checks — isolation, catalogs, data hygiene, layout, the built
pages — live in tests/ and run against every country.
"""
from __future__ import annotations

import csv
import math

import pytest

from core.country import Country
from tests.probe import plate

SLUG = "italy"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(
            ln for ln in fh if not ln.lstrip().startswith("#")))


def by_year(rel: str, key: str = "year") -> dict[int, dict]:
    return {int(r[key]): r for r in rows(rel)}


def fnum(row: dict, col: str) -> float | None:
    cell = (row.get(col) or "").strip()
    return float(cell) if cell else None


# ---------------------------------------------------------------- bands
def test_the_recession_bands_are_the_staged_vintages_sign_runs():
    """Dated off Eurostat namq_10_gdp quarter-on-quarter signs, vintage
    2026-10-22 — not off headlines. Five negative quarters into 2009 Q2;
    eight into 2013 Q1; the two pandemic quarters. The 2019 Q3-Q4 negatives
    touch the pandemic run on this vintage but belong to the stall, which
    is an event annotation, not a band; 2013 Q4/2014 Q1 at -0.1 stay out."""
    assert Country.load(SLUG).recessions == (
        (2008.25, 2009.5, "2008–09 crisis"),
        (2011.25, 2013.0, "2011–13 euro crisis"),
        (2020.0, 2020.5, "COVID-19"),
    )


# ----------------------------------------------------------- demography
def test_crude_rates_are_computed_on_the_same_files_population():
    """CBR 6.27 and CDR 11.08 per 1,000 for 2024, both from demo_gind
    counts over the same file's 1-January population — the footnote prints
    them, so a refetch that moves either fails here and on the plate."""
    d = by_year("social/demography.csv")
    pop24 = float(d[2024]["population"])
    assert float(d[2024]["births"]) / pop24 * 1000 == pytest.approx(6.273, abs=5e-4)
    assert float(d[2024]["deaths"]) / pop24 * 1000 == pytest.approx(11.075, abs=5e-4)
    panel = plate(SLUG, "plate_demography").panel("Crude birth and death rates")
    assert any("CBR 2024 6.27, CDR 11.08 per 1,000" in s for s in panel.texts())


def test_the_natural_cross_is_2007_and_the_collapse_is_pinned():
    """576,659 births in 2008 against 355,435 in 2025 (provisional); from
    2007 on these series print more deaths than births, every year."""
    d = by_year("social/demography.csv")
    assert float(d[2008]["births"]) == 576659
    assert float(d[2025]["births"]) == 355435
    cross = next(y for y in sorted(d) if float(d[y]["births"]) < float(d[y]["deaths"]))
    assert cross == 2007
    for y in range(2007, 2026):
        assert float(d[y]["births"]) < float(d[y]["deaths"]), f"{y} broke the cross"
    panel = plate(SLUG, "plate_demography").panel("Crude birth and death rates")
    assert any("the lines cross in 2007 and never meet again" in s
               for s in panel.texts())


def test_fertility_ends_at_the_last_final_year():
    """TFR 1.37 (2006) to 1.18 (2024): the plate stops at 2024, the last
    final year — the 2025 provisional agrees on direction but is not drawn."""
    d = by_year("social/demography.csv")
    assert float(d[2006]["tfr"]) == pytest.approx(1.37)
    assert float(d[2024]["tfr"]) == pytest.approx(1.18)
    panel = plate(SLUG, "plate_demography").panel("Total fertility rate")
    lns = panel.data_lines()
    assert len(lns) == 1, "the fertility panel grew a second line"
    xs = [float(x) for x in lns[0].get_xdata() if not math.isnan(float(x))]
    assert max(xs) == pytest.approx(2024.0), "the 2025 provisional got drawn"


# -------------------------------------------------------------- prices
def test_the_nic_line_never_splices_bases():
    """The NIC plate line is year-over-year change of index_b2015 only,
    which the file keeps filled for 2016–2025; 2026 lives on the 2025=100
    base in index_b2025 and no rate is ever computed across the rebase."""
    nic = by_year("macro/nic.csv")
    for y, r in nic.items():
        if y < 2016 or y > 2025:
            assert not (r["index_b2015"] or "").strip(), f"{y}: b2015 outside its span"
        if y != 2026:
            assert not (r["index_b2025"] or "").strip(), f"{y}: b2025 outside its span"
    panel = plate(SLUG, "plate_economy").panel("Consumer price inflation")
    pts = panel.points("NIC, national index")
    assert min(pts) == 2017 and max(pts) == 2025, (
        "the NIC rate line left the base-2015 years it is computed inside")


def test_eurostat_unemployment_starts_where_the_series_starts():
    """Eurostat's harmonised unemployment is blank 2006–08 for Italy; the
    ISTAT national series is backcast to 2006. Where both run they sit
    within 0.1 point — the note quotes the end pair, so both must hold."""
    ue = by_year("macro/unemployment.csv")
    for y in (2006, 2007, 2008):
        assert not (ue[y]["estat"] or "").strip(), f"{y}: Eurostat rate back-filled"
    panel = plate(SLUG, "plate_economy").panel("Unemployment rate")
    nat = panel.points("ISTAT labour survey")
    est = panel.points("Eurostat")
    assert min(nat) == 2006
    assert min(est) == 2009
    shared = sorted(set(nat) & set(est))
    assert max(abs(nat[y] - est[y]) for y in shared) <= 0.15


# ---------------------------------------------------------------- people
def test_the_silc_lines_start_where_italys_silc_starts():
    """Eurostat's Italy SILC series (Gini, and the at-risk lines) start in
    2014; nothing is back-filled before the survey existed here."""
    g = by_year("social/gini.csv")
    for y, r in g.items():
        if y < 2014:
            assert not (r["silc"] or "").strip(), f"{y}: SILC Gini back-filled"
        elif y <= 2025:  # 2026 is the staged blank tail of the file
            assert (r["silc"] or "").strip(), f"{y}: SILC Gini blank"
    panel = plate(SLUG, "plate_people").panel("Income inequality")
    pts = panel.points("EU-SILC via Eurostat")
    assert min(pts) == 2014


def test_the_sofferenze_series_stops_at_its_end():
    """BdI's sofferenze ratio (bad_loans_ratio_computed) ended in March
    2024: the 2024 row is a mixed part-year and is NOT drawn, and the
    FSI ratio (harmonised, 2011+) is never joined to it."""
    npl = by_year("credit/npl.csv")
    for y in (2025, 2026):
        assert not (npl[y]["bad_loans_ratio_computed"] or "").strip()
    panel = plate(SLUG, "plate_credit").panel("Non-performing loans")
    assert max(panel.points("sofferenze ratio")) == 2023, (
        "the discontinued series' mixed 2024 row got drawn")
    assert min(panel.points("Gross NPL ratio")) == 2011
    assert any("the 2024 mixed row of the discontinued series is not drawn" in s
               for s in panel.texts())


# ------------------------------------------------------------ migration
def test_two_publishers_of_the_same_flow_agree_except_in_2008_10():
    """Eurostat migr_imm1ctz / migr_emi1ctz equal ISTAT 28_185 to the
    person for 2006–07 and 2011–24; in 2008–10, the first Regulation
    years, Eurostat runs higher — by +40,318 on immigration in 2008."""
    imm = by_year("migration/immigration.csv")
    emi = by_year("migration/emigration.csv")
    ist = by_year("migration/migration_flows.csv")
    for y in list(range(2006, 2008)) + list(range(2011, 2025)):
        assert float(imm[y]["by_citizenship_total"]) == float(ist[y]["immigration"])
        assert float(emi[y]["by_citizenship_total"]) == float(ist[y]["emigration"])
    assert (float(imm[2008]["by_citizenship_total"])
            - float(ist[2008]["immigration"])) == 40318
    panel = plate(SLUG, "plate_migration").panel("Immigration and emigration")
    assert any("two lines, one statistic, never spliced" in s for s in panel.texts())


def test_the_2025_balance_is_quoted_as_a_number_not_a_drawn_point():
    """Eurostat flows stop at 2024; ISTAT's 2025 register balance
    (+295,759) is the honest number in the note, and the drawn line
    still stops at 2024."""
    ist = by_year("migration/migration_flows.csv")
    assert float(ist[2025]["balance"]) == 295759
    panel = plate(SLUG, "plate_migration").panel("Net migration")
    assert max(panel.points("Eurostat, computed")) == 2024
    assert any("+295,759" in s.replace(" ", " ") for s in panel.texts())


# -------------------------------------------------------------- mortality
def test_the_excess_base_is_the_plain_2015_19_mean():
    """Excess deaths over the simple five-year mean of register deaths,
    as the spine prescribes: +16.4% in 2020, and the bar panel prints it."""
    d = by_year("social/demography.csv")
    deaths = {y: float(d[y]["deaths"]) for y in d
              if (d[y]["deaths"] or "").strip()}
    base = sum(deaths[y] for y in range(2015, 2020)) / 5
    assert (deaths[2020] / base - 1) * 100 == pytest.approx(16.4, abs=0.05)
    panel = plate(SLUG, "plate_mortality").panel("Excess deaths")
    assert any("+16.4% in 2020" in s for s in panel.texts())


def test_covid_is_shortlist_code_20_and_only_from_2020():
    """78,408 certificate deaths with COVID as underlying cause (code 20,
    identified + not identified) in 2020 = 131.5 per 100,000; the
    shortlist carries 20* codes from 2020 only, and 2023 is the staged
    end — the bar panel prints both numbers and stops there."""
    causes = rows("social/causes_of_death.csv")
    c20 = {int(r["year"]): float(r["deaths"]) for r in causes if r["code"] == "20"}
    assert min(c20) == 2020 and max(c20) == 2023
    assert c20[2020] == 78408
    d = by_year("social/demography.csv")
    assert c20[2020] / float(d[2020]["population"]) * 1e5 == pytest.approx(131.5, abs=0.05)
    panel = plate(SLUG, "plate_mortality").panel("COVID-19 deaths")
    assert any("131.5 in 2020" in s for s in panel.texts())
    assert any("78,408 with COVID as underlying cause" in s for s in panel.texts())


def test_the_big_killers_are_peers_not_a_sum():
    """Circulatory diseases fall from 376 to 348 per 100,000 (2006→2023)
    while dementia climbs toward 41 — codes 7, 2_1 and 5_1 of the same
    nested shortlist, drawn beside each other, never added."""
    causes = {}
    for r in rows("social/causes_of_death.csv"):
        causes.setdefault(r["code"], {})[int(r["year"])] = float(r["deaths"])
    d = by_year("social/demography.csv")
    pop = {y: float(d[y]["population"]) for y in d}
    heart06 = causes["7"][2006] / pop[2006] * 1e5
    heart23 = causes["7"][2023] / pop[2023] * 1e5
    dem23 = causes["5_1"][2023] / pop[2023] * 1e5
    assert round(heart06) == 376 and round(heart23) == 348
    assert round(dem23) == 41
    panel = plate(SLUG, "plate_mortality").panel("Lens — who actually dies")
    assert any("circulatory deaths fall from 376 to 348" in s for s in panel.texts())
    assert panel.points("Malignant neoplasms"), "the tumour line vanished"


# -------------------------------------------------------------- security
def test_the_two_homicide_counts_are_both_drawn_and_never_spliced():
    """341 homicides in 2023 by the police register against 239 on death
    certificates; both lines, both labelled, and the note prints the pair."""
    pol = by_year("security/homicide_police.csv")
    vit = by_year("security/homicide_vital.csv")
    assert int(pol[2023]["intenhom"]) == 341
    assert int(vit[2023]["assault_deaths"]) == 239
    panel = plate(SLUG, "plate_security").panel("Homicide rate")
    assert panel.points("Police count") and panel.points("Death certificates")
    assert any("341 against 239" in s for s in panel.texts())


def test_the_road_panel_rejects_the_all_transport_proxy():
    """All-transport deaths cannot occupy the canonical road-only slot."""
    panel = plate(SLUG, "plate_security").panel("Road traffic deaths")
    assert not panel.data_lines()
    assert any("road-only series is not staged" in s for s in panel.texts())
    assert any("all transport modes" in s for s in panel.texts())


def test_the_mafia_slot_is_pending_and_draws_nothing():
    """ISTAT 73_67 carries MAFFIAHOM/ATTEMPHOM columns, but the ISTAT
    endpoints were down all through staging: the lens slot says so and
    holds no data line, no substituted number."""
    panel = plate(SLUG, "plate_security").panel("Lens — mafia")
    assert not panel.data_lines()
    assert any("data pending" in s for s in panel.texts())
    assert any("73_67 MAFFIAHOM/ATTEMPHOM" in s for s in panel.texts())


# --------------------------------------------------------------- credit
def test_the_bis_substitute_is_labelled_as_a_substitute():
    """The spine's BIS household-debt series is not staged; slot 1 shows
    BdI's loans over Eurostat GDP instead — 36.1% for 2024, where the
    published BIS and Eurostat measures read 36.0 and 36.1. The label and
    the note both say what the line is."""
    hd = by_year("credit/household_debt.csv")
    gdp = by_year("macro/gdp.csv")
    assert float(hd[2024]["loans_eurbn"]) / float(gdp[2024]["nominal_eurbn"]) * 100 \
        == pytest.approx(36.108, abs=5e-3)
    panel = plate(SLUG, "plate_credit").panel("Household debt")
    assert any("BdI loans" in ln.get_label()
               and "Eurostat GDP" in ln.get_label()
               for ln in panel.data_lines()), \
        "the substitute line is not labelled for what it is"
    note = " ".join(" ".join(panel.texts()).split())
    assert "against BIS 36.0 and Eurostat 36.1 for 2024" in note


def test_the_debt_to_income_lens_is_one_computed_column():
    """The lens divides BdI's loans by Eurostat's household disposable
    income (B6G S14_S15); the staged _computed column must equal that
    division, and it is never joined with the GDP ratio of slot 1."""
    hd = by_year("credit/household_debt.csv")
    for y in sorted(hd):
        loans = fnum(hd[y], "loans_eurbn")
        gdi = fnum(hd[y], "gdi_estat_eurbn")
        ratio = fnum(hd[y], "debt_pct_gdi_computed")
        if loans is not None and gdi is not None:
            assert ratio == pytest.approx(loans / gdi * 100, abs=0.05), y
        else:
            assert ratio is None, f"{y}: _computed filled from blank inputs"
    panel = plate(SLUG, "plate_credit").panel("Lens — the same debt")
    assert any("never joined" in s for s in panel.texts())


# --------------------------------------------------------------- markets
def test_the_milan_loss_and_the_spread_peak_are_pinned():
    """The FTSE MIB in US$ (close × ECB mean rate, dividends excluded)
    troughs at index 40 in 2012; the 10-year BTP average peaks at 5.49%
    the same year — the spread crisis, priced by both plates."""
    ft = by_year("markets/ftsemib.csv")
    fx = by_year("markets/eurusd.csv")
    idx = {y: float(ft[y]["close"]) * float(fx[y]["avg"]) for y in ft if y in fx}
    base = idx[2006]
    trough = min(idx, key=idx.get)
    assert trough == 2012 and round(idx[trough] / base * 100) == 40
    assert round(idx[2025] / base * 100) == 98  # a flat decade, still below 2006
    eq = plate(SLUG, "plate_markets").panel("Main equity index")
    assert any("40 in 2012" in s for s in eq.texts())
    yv = by_year("markets/yield_10y.csv")
    assert float(yv[2012]["yield_10y"]) == pytest.approx(5.49)
    bond = plate(SLUG, "plate_markets").panel("10-year government bond yield")
    assert any("5.49% in 2012" in s for s in bond.texts())


# ---------------------------------------------------- newly staged sources
def test_trade_destinations_use_comtrade_world_as_the_denominator():
    """The customs-goods bars are the reviewed Italy-reporter snapshot;
    they are not divided by the national-accounts exports series."""
    table = rows("trade/trade_comtrade_partner.csv")
    world = next(r for r in table if r["partner"] == "World")
    germany = next(r for r in table if r["partner"] == "Germany")
    expected = float(germany["value_usd"]) / float(world["value_usd"]) * 100
    assert float(germany["share_of_flow_pct"]) == pytest.approx(expected, abs=.005)
    panel = plate(SLUG, "plate_trade").panel("Top export destinations, 2023")
    heights = [float(patch.get_height()) for patch in panel.ax.patches]
    assert max(heights) == pytest.approx(float(germany["share_of_flow_pct"]))
    assert any("customs goods" in text for text in panel.texts())


def test_cpi_is_the_complete_comparable_2012_2025_run():
    cpi = by_year("international/cpi.csv")
    assert sorted(cpi) == list(range(2012, 2026))
    assert float(cpi[2012]["score"]) == 42
    assert float(cpi[2025]["score"]) == 53
    panel = plate(SLUG, "plate_world").panel("Corruption Perceptions Index")
    line = panel.data_lines()[0]
    points = dict(zip(map(int, line.get_xdata()), map(float, line.get_ydata())))
    assert points[2012] == 42 and points[2025] == 53


def test_minimum_wage_remains_explicitly_not_applicable():
    panel = plate(SLUG, "plate_people").panel("Minimum wage")
    assert not panel.data_lines()
    assert any("no statutory minimum wage" in text.lower()
               for text in panel.texts())
