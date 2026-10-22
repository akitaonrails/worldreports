"""The facts Spain's plates assert.

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

SLUG = "spain"
DATA = Country.load(SLUG).data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(
            ln for ln in fh if not ln.lstrip().startswith("#")))


def by_year(rel: str, key: str = "year") -> dict[int, dict]:
    return {int(r[key]): r for r in rows(rel)}


# ------------------------------------------------------------- economy
def test_gdp_2024_is_the_same_on_both_publishers():
    """Eurostat's transmission and the INE's own release read €1,598.59bn
    for 2024 — same vintage today. The columns stay apart because a
    revision can reopen the seam."""
    t = by_year("macro/gdp.csv")
    assert float(t[2024]["nominal_eurbn"]) == pytest.approx(1598.59, abs=0.05)
    assert float(t[2024]["nominal_eurbn_ine"]) == pytest.approx(1598.59,
                                                               abs=0.05)
    assert float(t[2006]["nominal_eurbn"]) == pytest.approx(1004.98, abs=0.05)
    panel = plate(SLUG, "plate_economy").panel("GDP at current prices")
    # Panel.bars() matches no patches on this matplotlib (composite
    # transform), so ask the patches directly, as Canada's tests do.
    heights = [p.get_height() for p in panel.ax.patches]
    assert max(heights) == pytest.approx(1690.01, abs=0.05)  # 2025 bar
    ine = panel.points("INE's own release")
    assert ine[2024.0] == pytest.approx(1598.59, abs=0.05)


def test_the_three_contractions_are_what_the_bands_claim():
    """The band dating follows q/q real GDP: 2009 −3.8%, 2012 −2.9%,
    2020 −10.9% — the G20's deepest COVID fall."""
    t = by_year("macro/gdp.csv")
    assert float(t[2009]["real_growth"]) == pytest.approx(-3.8, abs=0.1)
    assert float(t[2012]["real_growth"]) == pytest.approx(-2.9, abs=0.05)
    assert float(t[2020]["real_growth"]) == pytest.approx(-10.9, abs=0.1)
    panel = plate(SLUG, "plate_economy").panel("Real GDP growth")
    assert any("-10.9" in s for s in panel.texts())


def test_the_ipc_rate_reproduces_the_official_media_anual():
    """The staged rate is the year-on-year change of the annual mean of
    INE's linked index (base 2025): 2008 = 4.08, 2024 = 2.77 — the
    official figures are 4.1 and 2.8."""
    t = by_year("macro/inflation.csv")
    assert float(t[2008]["ipc"]) == pytest.approx(4.08, abs=0.01)
    assert float(t[2024]["ipc"]) == pytest.approx(2.77, abs=0.01)
    assert float(t[2020]["hicp"]) == pytest.approx(-0.3, abs=0.01)
    panel = plate(SLUG, "plate_economy").panel("Inflation")
    ipc = panel.points("Spanish IPC")
    assert ipc[2022.0] == pytest.approx(8.39, abs=0.01)
    assert any("never spliced" in s for s in panel.texts())


# ------------------------------------------------------------- fiscal
def test_the_bailout_year_deficit():
    """2009 −11.2% and 2012 −11.5% of GDP; the 2012 figure includes the
    bank recapitalisation, which the plate says next to the bar."""
    t = by_year("fiscal/deficit.csv")
    assert float(t[2009]["deficit"]) == pytest.approx(-11.2, abs=0.05)
    assert float(t[2012]["deficit"]) == pytest.approx(-11.5, abs=0.05)
    assert float(t[2024]["deficit"]) == pytest.approx(-3.2, abs=0.05)
    panel = plate(SLUG, "plate_fiscal").panel("Net lending")
    assert any("bank bailout" in s for s in panel.texts())


def test_the_debt_jump_of_2011_to_2013():
    """69.5% → 89.6% → 100.0% of GDP in three years; 2024 reads 101.4%,
    down from 105.3% partly because the GDP denominator was revised up."""
    t = by_year("fiscal/debt.csv")
    assert float(t[2011]["gross_pct_gdp"]) == pytest.approx(69.5, abs=0.05)
    assert float(t[2013]["gross_pct_gdp"]) == pytest.approx(100.0, abs=0.05)
    assert float(t[2024]["gross_pct_gdp"]) == pytest.approx(101.4, abs=0.05)
    assert float(t[2024]["gross_eurbn_q4"]) == pytest.approx(1620.6, abs=0.5)


# ------------------------------------------------------------- people
def test_unemployment_peak_and_the_lfs_hole():
    """EPA: 26.09% in 2013, 11.34% in 2024. Eurostat's harmonised LFS rate
    has no ES values before 2009 — the CSV keeps the hole and the panel's
    LFS line starts in 2009."""
    t = by_year("macro/unemployment.csv")
    assert float(t[2013]["epa"]) == pytest.approx(26.09, abs=0.01)
    assert float(t[2024]["epa"]) == pytest.approx(11.34, abs=0.01)
    for y in (2006, 2007, 2008):
        assert not (t[y]["estat"] or "").strip(), f"{y}: LFS hole filled"
    assert float(t[2013]["estat"]) == pytest.approx(26.1, abs=0.05)
    panel = plate(SLUG, "plate_people").panel("Unemployment rate")
    lfs = panel.points("Eurostat LFS")
    assert min(lfs) == 2009
    assert panel.ax.get_xlim()[0] < 2009, "the 2006-08 hole is not visible"


def test_the_employment_trough_and_rebuild():
    """17,139k employed in 2013, 22,221k in 2025 — the annual mean of the
    four quarterly EPA readings, thousands."""
    t = by_year("macro/employment.csv")
    assert float(t[2013]["employed_thousands_avg"]) == pytest.approx(17139.0,
                                                                     abs=0.5)
    assert float(t[2025]["employed_thousands_avg"]) == pytest.approx(22221.1,
                                                                     abs=0.5)


# ------------------------------------------------------------- markets
def test_the_mro_stays_blank_before_october_2008():
    """The MRO fixed-rate series starts October 2008; earlier years are a
    hole, not a zero. France's file has the same blanks."""
    t = by_year("markets/policy_rate.csv")
    for y in (2006, 2007):
        assert not (t[y]["mro"] or "").strip(), f"{y}: MRO back-filled"
    assert float(t[2024]["dfr"]) == pytest.approx(3.00, abs=0.01)
    assert float(t[2025]["dfr"]) == pytest.approx(2.00, abs=0.01)
    panel = plate(SLUG, "plate_markets").panel("policy rate")
    mro = panel.points("Main refinancing")
    assert min(mro) == 2008


def test_the_2012_yield_spike():
    """5.85% annual average in 2012 — the euro crisis in one number."""
    t = by_year("markets/yield_10y.csv")
    assert float(t[2012]["yield_10y"]) == pytest.approx(5.85, abs=0.01)
    panel = plate(SLUG, "plate_markets").panel("10-year benchmark")
    assert any("5.85%" in s for s in panel.texts())


def test_the_ibex_is_a_redistributor_price_index_and_says_so():
    """2007 close 15,182.30; 2026 is a live reading, not a year-end."""
    t = by_year("markets/ibex.csv")
    assert float(t[2007]["close"]) == pytest.approx(15182.30, abs=0.1)
    assert float(t[2012]["close"]) == pytest.approx(8167.50, abs=0.1)
    panel = plate(SLUG, "plate_markets").panel("IBEX 35")
    assert any("latest close" in s for s in panel.texts())
    assert any("price index" in s for s in panel.texts())


# ------------------------------------------------------------- credit
def test_the_npl_peak_is_december_2013():
    """Doubtful ÷ total credit, December stocks: 13.6% in Dec 2013, 3.3%
    in Dec 2024. The ratio is computed and the plate says so."""
    t = by_year("credit/npl.csv")
    assert float(t[2013]["npl_ratio"]) == pytest.approx(13.616, abs=0.01)
    assert float(t[2013]["doubtful_eur_mn"]) == pytest.approx(197198, abs=1)
    assert float(t[2024]["npl_ratio"]) == pytest.approx(3.321, abs=0.01)
    panel = plate(SLUG, "plate_credit").panel("Doubtful loans")
    assert any("13.6%" in s for s in panel.texts())
    assert any("computed here" in s for s in panel.texts())


def test_the_household_debt_peak():
    """141% of gross disposable income in 2008 (annual mean), 75% by
    2025 — the deleveraging is the chapter's story."""
    t = by_year("credit/household_debt.csv")
    assert float(t[2008]["debt_pct_income_avg"]) == pytest.approx(140.71,
                                                                  abs=0.1)
    assert float(t[2025]["debt_pct_income_q4"]) == pytest.approx(75.46,
                                                                 abs=0.1)


# ----------------------------------------------------------- demography
def test_vital_statistics_stop_at_the_definitive_year():
    """MNP definitive runs to 2024; 2025 exists only as provisional
    estimates, a different vintage, and stays blank."""
    t = by_year("social/demography.csv")
    assert float(t[2024]["births"]) == 318005
    assert float(t[2024]["deaths"]) == 436118
    for col in ("births", "deaths"):
        assert not (t[2025][col] or "").strip(), f"2025 {col} filled"
    panel = plate(SLUG, "plate_demography").panel("Births and deaths")
    deaths = panel.points("Deaths")
    assert max(deaths) == 2024


def test_population_and_the_2012_16_decline():
    """ECP at 1 January: 44.0mn in 2006, 49.1mn in 2025, 49.6mn in 2026 —
    and the only decline runs between 1-Jan-2013 and 1-Jan-2017."""
    t = by_year("social/population.csv")
    assert float(t[2025]["population"]) == 49128297
    assert float(t[2026]["population"]) == 49596376
    vals = {y: float(r["population"]) for y, r in t.items()}
    declines = [y for y in sorted(vals) if y - 1 in vals
                and vals[y] < vals[y - 1]]
    assert declines == [2013, 2014, 2015, 2016]


# ------------------------------------------------------------- security
def test_homicide_by_death_certificate():
    """ECM 'Agresiones (homicidio)': 378 in 2008, 324 in 2024. The police
    count is pending — the plate's third panel says why."""
    t = by_year("social/homicides.csv")
    assert float(t[2008]["ecm_deaths"]) == 378
    assert float(t[2024]["ecm_deaths"]) == 324
    panel = plate(SLUG, "plate_security").panel("death certificate")
    assert any("324" in s for s in panel.texts())
    pending = plate(SLUG, "plate_security").panel("recorded by the police")
    assert any("HTTP 200" in s for s in pending.texts())


def test_suicide_is_the_largest_violent_death():
    """Every year on the plate, suicide deaths exceed road deaths and both
    dwarf homicide — the context panel's claim."""
    t = rows("social/causes_of_death.csv")
    by_c = {}
    for r in t:
        by_c.setdefault(r["cause"], {})[int(r["year"])] = float(r["deaths"])
    sui = by_c["Suicidio y lesiones autoinfligidas"]
    road = by_c["Accidentes de tráfico"]
    hom = by_c["Agresiones (homicidio)"]
    for y in set(sui) & set(road) & set(hom):
        assert sui[y] > hom[y] and road[y] > hom[y], y
    assert sui[2024] > road[2024], "suicide passed road deaths by 2024"


# ------------------------------------------------------------- mortality
def test_covid_certified_deaths_split_identified_from_suspected():
    """2020: 60,358 with the virus identified plus 14,481 suspected — two
    rows, never summed silently."""
    t = rows("social/causes_of_death.csv")
    covid = {r["cause"]: float(r["deaths"]) for r in t
             if int(r["year"]) == 2020 and r["cause"].startswith("COVID-19")}
    assert covid["COVID-19. Virus identificado"] == 60358
    assert covid["COVID-19. Virus no identificado (sospechoso)"] == 14481


def test_the_two_big_killers_crossed_only_in_2024():
    """Tumours 115,578 vs circulatory 113,620 in 2024 — the first year
    cancer leads on the certified causes."""
    t = rows("social/causes_of_death.csv")
    by_c = {}
    for r in t:
        by_c.setdefault(r["cause"], {})[int(r["year"])] = float(r["deaths"])
    tum = by_c["II.Tumores"]
    cir = by_c["IX.Enfermedades del sistema circulatorio"]
    assert tum[2024] > cir[2024]
    assert tum[2023] < cir[2023], "the crossover is 2024, not earlier"
    assert tum[2024] == 115578 and cir[2024] == 113620


# ------------------------------------------------------------- migration
def test_the_2021_seam_is_published_on_both_methodologies():
    """The chapter's central fact: INE counts 2021 immigration as 528,856
    on the EM and 887,960 on the EMCR. Eurostat carries EM to 2020 and
    EMCR from 2021, so its series is spliced at 2021 — and the plate
    splits the Eurostat line there rather than drawing a segment across
    the seam."""
    em = by_year("migration/migration_flows_ine.csv")
    emcr = by_year("migration/migration_flows_emcr_ine.csv")
    assert float(em[2021]["immigration"]) == 528856
    assert float(emcr[2021]["immigration_emcr"]) == 887960
    for y in (2022, 2023, 2024):
        assert not (em[y]["immigration"] or "").strip(), \
            f"{y}: EM spliced past its end"
    for y in (2019, 2020):
        assert not (emcr[y]["immigration_emcr"] or "").strip(), \
            f"{y}: EMCR back-filled"
    eu = by_year("migration/immigration.csv")
    assert float(eu[2020]["by_citizenship_total"]) == 467918
    assert float(eu[2021]["by_citizenship_total"]) == 887960
    panel = plate(SLUG, "plate_migration").panel("two methodologies")
    em_line = panel.points("old methodology")
    emcr_line = panel.points("new methodology")
    assert max(em_line) == 2021 and min(emcr_line) == 2021
    estat_old = panel.points("carries EM")
    estat_new = panel.points("then EMCR")
    assert max(estat_old) == 2020 and min(estat_new) == 2021
    assert any("528,856" in s and "887,960" in s for s in panel.texts())


def test_emigration_is_drawn_beside_immigration_never_as_a_net():
    """2024: 1,288,562 arrivals against 662,294 departures — two series;
    the net is the reader's to see."""
    t = by_year("migration/emigration.csv")
    assert float(t[2024]["by_citizenship_total"]) == 662294
    assert float(t[2013]["by_citizenship_total"]) == 532303
    panel = plate(SLUG, "plate_migration").panel("Who arrives")
    assert len(panel.paired("Immigration", "Emigration")) >= 15


def test_the_two_stock_cuts_and_the_naturalisation_gap():
    """1-Jan-2025: 42.2mn Spanish citizens vs 39.7mn born in Spain — the
    ~2.5mn gap is naturalised citizens, and migr_acq says 252,476 became
    Spanish in 2024 alone."""
    t = by_year("migration/stock.csv")
    nat_cit = float(t[2025]["by_citizenship_national"])
    born_es = float(t[2025]["by_birth_national"])
    assert nat_cit - born_es == pytest.approx(2.55e6, abs=1e5)
    acq = by_year("migration/naturalisation.csv")
    assert float(acq[2024]["acquisitions"]) == 252476
    panel = plate(SLUG, "plate_migration").panel("resident stock")
    pairs = panel.paired("Spanish citizens", "born in Spain")
    assert len(pairs) >= 15
    below = [y for y, cit, born in pairs if cit < born]
    assert not below, f"citizens below Spain-born in {below[:4]}"


def test_asylums_four_numbers_stay_four():
    """2024: 167,750 applications, 89,880 first-instance decisions, 50,700
    positive, 561,640 first permits — four different questions on one
    panel, each labelled."""
    t = by_year("migration/asylum.csv")
    assert float(t[2024]["applications"]) == 167750
    assert float(t[2024]["decisions"]) == 89880
    assert float(t[2024]["positive"]) == 50700
    p = by_year("migration/permits.csv")
    assert float(p[2024]["first_permits"]) == 561640
    panel = plate(SLUG, "plate_migration").panel("paperwork")
    pos = panel.points("of which positive")
    dec = panel.points("first-instance decisions")
    shared = [y for y in pos if y in dec]
    assert shared and all(pos[y] <= dec[y] for y in shared), \
        "positive decisions above decisions: the subset is mislabelled"


# --------------------------------------------------------------- trade
def test_the_balance_flipped_in_2011():
    """Goods and services, national accounts: the last deficit year is
    2010 and 2024 reads +€69bn. A customs-basis series would say
    something else — the panel footnote says which basis this is."""
    t = by_year("trade/trade.csv")
    bal = {y: float(r["exports_eurbn"]) - float(r["imports_eurbn"])
           for y, r in t.items() if r["exports_eurbn"]}
    assert bal[2010] < 0 < bal[2011]
    assert bal[2024] == pytest.approx(68.96, abs=0.05)
    panel = plate(SLUG, "plate_trade").panel("external balance")
    assert any("since 2011" in s for s in panel.texts())


# ---------------------------------------------------------------- world
def test_the_comparables_layer():
    """GDP US$1.73tn in 2024, HDI 0.918 in 2023, reserves US$103bn in
    2023 — the WB/UNDP layer, official: false in SOURCES.yaml."""
    t = by_year("international/gdp_usd.csv")
    assert float(t[2024]["gdp_usd"]) == pytest.approx(1.7257e12, rel=1e-3)
    h = by_year("international/hdi.csv")
    assert float(h[2023]["hdi"]) == pytest.approx(0.918, abs=0.001)
    panel = plate(SLUG, "plate_world").panel("Human Development")
    assert any("0.918" in s for s in panel.texts())


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
    peak is missing."""
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped(slack=1e-6)
