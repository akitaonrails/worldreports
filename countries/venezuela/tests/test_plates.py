"""The facts Venezuela's plates assert.

Every test states a claim a plate makes about this country's own data, and
computes the number from the committed CSVs at test time — so a refetch that
invalidates the claim fails the build instead of quietly changing a published
chart. The four that matter most:

- the two publishers of growth, dollar GDP and unemployment are drawn as two
  labelled series and never stitched into one, and the collapse is inside the
  shared comparison scale that was widened for it;
- the inflation panel in the canonical slot is visibly pending, and the series
  is drawn in the prices lens on a log axis with the IMF's and the BCV's lines
  kept apart;
- net migration is `pending` in the canonical slot because −45.5 per 1,000
  does not fit, and the series and the UNHCR caseload are drawn in the
  migration lens on their own two axes;
- a hole stays a hole: homicide has no 2013 or 2018 observation and the line
  breaks rather than bridging it, and the exchange rate and reserves stop in
  2017 where the publisher stopped.
"""

from __future__ import annotations

import csv
import re

import pytest

from core.country import Country
from core import spine, sitebuild
from tests.probe import plate

SLUG = "venezuela"
COUNTRY = Country.load(SLUG)
DATA = COUNTRY.data_dir


def rows(rel: str) -> list[dict]:
    path = DATA / rel
    assert path.exists(), f"{rel} is missing"
    with path.open(encoding="utf-8-sig", newline="") as fh:
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def num(r: dict, key: str) -> float:
    v = (r.get(key) or "").strip()
    return float(v) if v else float("nan")


def by_year(rel: str) -> dict[int, dict]:
    return {int(r["year"]): r for r in rows(rel)}


def col(rel: str, key: str) -> dict[int, float]:
    return {y: num(r, key) for y, r in by_year(rel).items()}


def texts(plate_name: str, panel: str) -> list[str]:
    return plate(SLUG, plate_name).panel(panel).texts()


def panel(plate_name: str, title: str):
    return plate(SLUG, plate_name).panel(title)


def is_pending(plate_name: str, title: str) -> None:
    p = panel(plate_name, title)
    assert getattr(p.ax, "spine_pending", False), f"{title}: not marked pending"
    assert any("data pending" in t.lower() for t in p.texts()), \
        f"{title}: the placeholder is missing"


# ----------------------------------------------------------------- economy
def test_growth_is_drawn_from_both_publishers_and_never_spliced():
    pan = panel("plate_economy", "Real GDP growth")
    eco = by_year("macro/economy.csv")
    imf = [(y, num(eco[y], "gdp_growth_pct_imf")) for y in sorted(eco)]
    drawn = pan.points("IMF WEO")
    # The Fund's line covers the whole window, in its own object, and reads
    # the same values as the CSV — it is not a segment of one merged line.
    assert [y for y, v in imf if v == v] == sorted(drawn)
    for y, v in imf:
        if v == v:
            assert drawn[y] == pytest.approx(v, abs=1e-9)
    # The bars are the World Bank's independent estimate: 2020 is its trough.
    wb = col("macro/economy.csv", "gdp_growth_pct_wb")
    assert min(pan.bars()) == pytest.approx(wb[2020], abs=1e-6)
    assert wb[2020] == pytest.approx(-29.82, abs=0.01)
    assert dict(imf)[2020] == pytest.approx(-33.2, abs=0.01)


def test_the_collapse_is_inside_the_widened_shared_scale():
    slot = spine.SLOTS["economy.growth"]
    assert slot.ref[0] <= -33.2
    assert spine.fit(slot, (-33.2, 15.1))[0] == slot.ref


def test_the_inflation_slot_is_pending_and_says_why():
    is_pending("plate_economy", "Consumer price inflation")
    note = " ".join(texts("plate_economy", "Consumer price inflation"))
    # The reason names the number that cannot fit and where it is drawn.
    assert "65,374" in note and "lens" in note


def test_the_prices_lens_is_logarithmic_and_keeps_the_two_publishers_apart():
    pan = panel("plate_people", "Prices —")
    assert pan.ax.get_yscale() == "log"
    eco = by_year("macro/economy.csv")
    imf = {y: num(r, "cpi_inflation_pct_imf") for y, r in eco.items()}
    bcv = {y: num(r, "cpi_inflation_pct_bcv") for y, r in eco.items()
           if num(r, "cpi_inflation_pct_bcv") ==
           num(r, "cpi_inflation_pct_bcv")}
    # The Fund's estimate is continuous for the whole window; the BCV's INPC
    # survives only for 2009-2016 and is a second, shorter line.
    fund = pan.series("IMF WEO")
    assert len(fund) == len([v for v in imf.values() if v == v]) == 20
    national = pan.series("BCV INPC")
    assert len(national) == len(bcv) == 8
    # The 2009 seam the plate annotates: 26.00 against 27.08.
    assert imf[2009] == pytest.approx(26.00, abs=0.001)
    assert bcv[2009] == pytest.approx(27.08, abs=0.001)
    # And the curve is inside its own lens range, not clipped.
    lo, hi = sorted(pan.ax.get_ylim())
    assert hi >= max(v for v in imf.values()) >= 65_000
    assert lo <= min(v for v in imf.values() if v == v)


def test_gdp_per_person_is_on_the_shared_log_scale():
    pan = panel("plate_economy", "GDP per person")
    assert pan.ax.get_yscale() == "log"
    pc = col("world/gdp_per_person.csv", "gdp_per_person_usd")
    assert pan.points("")[2025] == pytest.approx(pc[2025], abs=0.05)
    lo, hi = sorted(pan.ax.get_ylim())
    assert (lo, hi) == spine.SLOTS["economy.gdp_per_person"].ref


def test_unemployment_keeps_the_two_lines_and_their_different_ends():
    pan = panel("plate_economy", "Unemployment rate")
    ilo = col("macro/economy.csv", "unemployment_pct_ilo")
    imf = col("macro/economy.csv", "unemployment_pct_imf")
    assert max(pan.points("ILO modelled")) == 2025
    assert max(pan.points("national definition")) == 2018
    assert pan.points("ILO modelled")[2006] == pytest.approx(ilo[2006], abs=1e-6)
    assert pan.points("national definition")[2018] == pytest.approx(
        imf[2018], abs=1e-6)


# ------------------------------------------------------------------ fiscal
def test_the_fiscal_plates_are_one_imf_vintage():
    rev = col("fiscal/fiscal.csv", "revenue_pct_gdp")
    exp = col("fiscal/fiscal.csv", "expenditure_pct_gdp")
    revp = panel("plate_fiscal", "Revenue and expenditure")
    assert revp.points("Revenue")[2018] == pytest.approx(rev[2018], abs=1e-6)
    assert revp.points("Expenditure")[2018] == pytest.approx(exp[2018], abs=1e-6)
    assert rev[2018] == pytest.approx(6.88, abs=0.01)
    assert exp[2018] == pytest.approx(37.86, abs=0.01)


def test_the_balance_is_bars_and_the_primary_a_line_on_the_same_vintage():
    bal = col("fiscal/fiscal.csv", "balance_pct_gdp")
    pri = col("fiscal/fiscal.csv", "primary_balance_pct_gdp")
    pan = panel("plate_fiscal", "Overall and primary balance")
    assert min(pan.bars()) == pytest.approx(bal[2018], abs=1e-6)
    assert bal[2018] == pytest.approx(-31.9, abs=0.01)
    assert pan.points("Primary balance")[2018] == pytest.approx(
        pri[2018], abs=1e-6)
    # The primary balance is less negative than the overall one in every
    # year — but the vintage's own published primary does NOT reconcile to
    # its own interest line (2018: -31.9 + 0.69 = -31.21 against a published
    # -30.29), so the plates call it "the Fund's own definition" and never
    # derive it. Asserted here so a future vintage that reconciles is noticed.
    interest = col("fiscal/fiscal.csv", "interest_pct_gdp")
    for y in bal:
        if bal[y] == bal[y] and pri[y] == pri[y]:
            assert pri[y] >= bal[y], y
    assert pri[2018] != pytest.approx(bal[2018] + interest[2018], abs=0.5)


def test_debt_stays_pending_and_the_file_has_no_debt_column():
    is_pending("plate_fiscal", "Gross debt")
    assert not [c for c in rows("fiscal/fiscal.csv")[0] if "debt" in c.lower()]


# ---------------------------------------------------------------- spending
def test_investment_starts_where_the_gateway_stops_faking_a_zero():
    gfcf = col("spending/spending.csv", "gfcf_pct_gdp")
    pan = panel("plate_spending", "Investment rate")
    assert min(pan.points("")) == 2012
    assert 2006 not in gfcf, "2006 must be a hole, not a zero"
    assert pan.points("")[2013] == pytest.approx(25.57, abs=0.01)
    assert pan.points("")[2024] == pytest.approx(3.80, abs=0.01)


def test_the_functional_budget_slots_stay_pending():
    for title in ("Spending by function", "Social protection vs everything",
                  "Public investment"):
        is_pending("plate_spending", title)


# ------------------------------------------------------------------- trade
def test_the_trade_balance_is_derived_from_the_same_two_columns():
    xp = col("trade/trade.csv", "exports_pct_gdp")
    im = col("trade/trade.csv", "imports_pct_gdp")
    pan = panel("plate_trade", "Trade balance")
    years = sorted(xp)
    derived = sorted(xp[y] - im[y] for y in years)
    assert sorted(pan.bars()) == pytest.approx(derived, abs=1e-6)
    assert xp[2019] - im[2019] == pytest.approx(36.27, abs=0.01)
    # The balance is inside the shared range that was widened for it.
    slot = spine.SLOTS["trade.balance"]
    assert slot.ref[1] >= 36.27


def test_the_trade_lens_is_the_same_ratios_times_the_same_vintage_gdp():
    xp = col("trade/trade.csv", "exports_pct_gdp")
    gdp = col("world/gdp_usd.csv", "gdp_usd_bn_wb")
    pan = panel("plate_trade", "Exports and imports in US$ bn")
    drawn = pan.points("Exports")
    for y in (2012, 2019, 2025):
        assert drawn[y] == pytest.approx(xp[y] / 100 * gdp[y], abs=1e-6)
    assert drawn[2012] == pytest.approx(110, abs=1)
    assert drawn[2025] == pytest.approx(14.85, abs=0.05)


def test_export_destinations_stay_pending():
    is_pending("plate_trade", "Top export destinations")


# ----------------------------------------------------------------- markets
def test_the_currency_index_is_the_documented_divisor_and_stops_in_2017():
    fx = by_year("markets/fx_official.csv")
    pan = panel("plate_markets", "Currency against the US$")
    idx = pan.points("")
    assert max(idx) == 2017
    assert idx[2006] == pytest.approx(100.0, abs=1e-6)
    assert idx[2017] == pytest.approx(21.5238, abs=1e-3)
    for y, r in fx.items():
        assert num(r, "fx_index_2006_100") == pytest.approx(
            2.147 / num(r, "lcu_per_usd") * 100, rel=1e-4), y
        # 1 VES = 100,000,000,000 bolívares fuertes: one divisor, written
        # down, for the whole 2006-2017 run.
        assert num(r, "ves_per_usd") == pytest.approx(
            num(r, "lcu_per_usd") / 1e11, rel=1e-9), y
    assert pan.ax.get_yscale() == "log"


def test_the_unpriced_market_panels_stay_pending():
    for title in ("Policy rate vs inflation", "10-year government bond yield",
                  "Main equity index in US$"):
        is_pending("plate_markets", title)


# ------------------------------------------------------------------ people
def test_the_gini_is_the_ine_series_on_the_atlas_scale():
    gini = col("people/gini.csv", "gini")
    pan = panel("plate_people", "Income inequality, Gini")
    drawn = pan.points("")
    assert drawn[2006] == pytest.approx(gini[2006], abs=1e-6)
    assert min(drawn.values()) == pytest.approx(gini[2018], abs=1e-6)
    assert all(20 <= v <= 60 for v in drawn.values())
    lo, hi = pan.ax.get_ylim()
    assert (lo, hi) == spine.SLOTS["people.gini"].ref


def test_poverty_and_the_minimum_wage_stay_pending():
    is_pending("plate_people", "Poverty rate")
    is_pending("plate_people", "Minimum wage")


# ------------------------------------------------------------------- world
def test_dollar_gdp_is_two_lines_and_the_gap_is_the_exchange_rate():
    wb = col("world/gdp_usd.csv", "gdp_usd_bn_wb")
    imf = col("world/gdp_usd.csv", "gdp_usd_bn_imf")
    pan = panel("plate_world", "GDP at current prices")
    a, b = pan.points("World Bank"), pan.points("IMF WEO")
    assert a[2010] == pytest.approx(wb[2010], abs=1e-6)
    assert b[2014] == pytest.approx(imf[2014], abs=1e-6)
    # 2014: the two lines are 86bn apart, and that gap is the convention.
    assert wb[2014] - imf[2014] == pytest.approx(85.8, abs=0.1)
    assert pan.ax.get_yscale() == "log"


def test_hdi_is_one_vintage_and_reserves_end_where_the_bcv_stops():
    hdi = col("world/hdi.csv", "hdi")
    pan = panel("plate_world", "Human Development Index")
    assert max(pan.points("")) == 2023
    assert pan.points("")[2013] == pytest.approx(hdi[2013], abs=1e-9)
    res = panel("plate_world", "Official reserves")
    assert max(res.points("")) == 2017
    assert res.points("")[2017] == pytest.approx(9.794, abs=1e-3)
    is_pending("plate_world", "Corruption Perceptions Index")


# -------------------------------------------------------------- demography
def test_the_population_line_is_one_index_on_one_series():
    pop = col("demography/population.csv", "population")
    pan = panel("plate_demography", "Population")
    drawn = pan.points("")
    base = pop[2006]
    for y in (2006, 2016, 2021, 2025):
        assert drawn[y] == pytest.approx(pop[y] / base * 100, abs=1e-6)
    assert drawn[2016] == pytest.approx(113.0, abs=0.05)
    # One series, not two spliced perimeters: every drawn segment comes
    # from the same World Bank column, and there is no second series here.
    segments = [ln for ln in pan.data_lines()]
    years = sorted({int(x) for ln in segments for x in ln.get_xdata()})
    assert years == sorted(pop)
    assert len(segments) <= 2, "one series, at most split at the last year"
    for ln in segments:
        assert ln.get_color() == COUNTRY.palette.BLUE


def test_natural_increase_is_births_minus_deaths_and_not_a_migration_rate():
    birth = col("demography/vital.csv", "birth_rate_per_1000")
    death = col("demography/vital.csv", "death_rate_per_1000")
    pan = panel("plate_demography", "Natural increase")
    tops = sorted(pan.bars())
    derived = sorted(birth[y] - death[y] for y in birth)
    assert tops == pytest.approx(derived, abs=1e-6)
    assert birth[2006] - death[2006] == pytest.approx(16.90, abs=0.01)
    # Net migration is not folded in: the panel says where it is drawn.
    assert "migration plate" in " ".join(pan.texts())


def test_the_vital_rates_are_the_un_model_and_stop_in_2024():
    pan = panel("plate_demography", "Crude birth and death rates")
    assert max(pan.points("Births")) == 2024
    assert pan.points("Deaths")[2024] == pytest.approx(7.678, abs=0.001)
    fert = panel("plate_demography", "Total fertility rate")
    assert max(fert.points("")) == 2024


# ---------------------------------------------------------------- security
def test_homicide_keeps_its_two_holes_open():
    hom = col("security/security.csv", "homicide_per_100k")
    pan = panel("plate_security", "Homicide rate")
    line = [ln for ln in pan.data_lines()
            if ln.get_label().startswith("UNODC")][0]
    ys = list(line.get_ydata())
    xs = list(line.get_xdata())
    assert sorted(xs) == sorted(hom)
    gaps = [x for x, v in zip(xs, ys) if v != v]
    assert gaps == [2013, 2018], "the holes must break the line, not bridge it"
    assert max(v for v in ys if v == v) == pytest.approx(62.90, abs=0.01)
    assert hom[2018] != hom[2018]


def test_the_suicide_vintage_shift_is_annotated():
    sui = col("security/security.csv", "suicide_per_100k")
    pan = panel("plate_security", "Suicide rate")
    assert pan.points("")[2015] == pytest.approx(sui[2015], abs=1e-6)
    assert sui[2016] - sui[2015] == pytest.approx(4.37, abs=0.01)
    note = " ".join(pan.texts())
    assert "estimate vintage" in note


def test_road_deaths_stop_in_2019():
    pan = panel("plate_security", "Road traffic deaths")
    drawn = pan.points("")
    assert max(drawn) == 2019
    assert drawn[2019] == pytest.approx(39.00, abs=0.01)


# --------------------------------------------------------------- mortality
def test_mortality_draws_the_model_and_parks_the_counts():
    death = col("demography/vital.csv", "death_rate_per_1000")
    pan = panel("plate_mortality", "Crude death rate")
    assert pan.points("")[2021] == pytest.approx(death[2021], abs=1e-6)
    assert death[2021] == pytest.approx(7.862, abs=0.001)
    is_pending("plate_mortality", "Excess deaths")
    is_pending("plate_mortality", "COVID-19 deaths")


def test_life_expectancy_is_the_lens_on_its_own_range():
    life = col("demography/vital.csv", "life_expectancy")
    pan = panel("plate_mortality", "Life expectancy at birth")
    drawn = pan.points("")
    lo, hi = sorted(pan.ax.get_ylim())
    assert lo < min(life.values()) and hi > max(life.values())
    assert drawn[2006] == pytest.approx(life[2006], abs=1e-6)
    assert min(drawn.values()) == pytest.approx(life[2021], abs=1e-6)


# --------------------------------------------------------------- migration
def test_net_migration_is_pending_and_the_hole_is_disclosed():
    is_pending("plate_migration", "Net migration")
    note = " ".join(texts("plate_migration", "Net migration"))
    assert "45.5" in note and "lens" in note
    is_pending("plate_migration", "Immigration and emigration")


def test_the_migration_lens_draws_the_wave_on_its_own_axis():
    mig = by_year("migration/migration.csv")
    pop = col("demography/population.csv", "population")
    per = {y: num(r, "net_migration") / pop[y] * 1000
           for y, r in mig.items()}
    pan = panel("plate_migration", "The exodus")
    tops = pan.bars()
    assert min(tops) == pytest.approx(per[2018], abs=0.01)
    assert per[2018] == pytest.approx(-45.48, abs=0.01)
    # Drawn below the comparable scale on purpose, and not clipped.
    assert per[2018] < spine.SLOTS["migration.net"].ref[0]
    assert sorted(pan.ax.get_ylim())[0] <= per[2018]


def test_the_unhcr_caseload_is_a_second_axis_and_never_a_rate():
    dis = by_year("migration/displacement.csv")
    fig = plate(SLUG, "plate_migration").fig
    twins = [ax for ax in fig.axes if ax.get_ylim() == (0.0, 2.2)]
    assert len(twins) == 1, "the caseload needs exactly one second axis"
    lines = [ln for ln in twins[0].lines
             if ln.get_transform() is twins[0].transData]
    assert len(lines) == 1
    peak = max(lines[0].get_ydata())
    assert peak == pytest.approx(
        num(dis[2024], "refugees_and_asylum_seekers") / 1e6, abs=1e-9)
    assert peak == pytest.approx(1.730, abs=0.001)


def test_the_foreign_born_share_is_a_snapshot_never_interpolated():
    stock = col("migration/migration.csv", "migrant_stock")
    pop = col("demography/population.csv", "population")
    pan = panel("plate_migration", "Foreign-born share")
    drawn = pan.points("")
    assert sorted(drawn) == [2010, 2015, 2020, 2024]
    for y, v in drawn.items():
        assert v == pytest.approx(stock[y] / pop[y] * 100, abs=1e-6)
    assert drawn[2024] == pytest.approx(4.45, abs=0.01)


# ------------------------------------------------------------ the events
def test_the_redenomination_event_is_where_it_belongs():
    pan = panel("plate_markets", "Currency against the US$")
    rules = [ln for ln in pan.ax.lines
             if len(ln.get_xydata()) == 2 and ln.get_linestyle() != "-"]
    assert any(abs(float(r.get_xdata()[0]) - 2018.55) < 1e-9 for r in rules), \
        "the 2018 redenomination rule is missing"
    assert any("1,000,000 BsS" in t for t in pan.texts())


# -------------------------------------------------------------- the slots
PENDING = [
    ("plate_economy", "Consumer price inflation"),
    ("plate_fiscal", "Gross debt"),
    ("plate_spending", "Spending by function"),
    ("plate_spending", "Social protection vs everything"),
    ("plate_spending", "Public investment"),
    ("plate_trade", "Top export destinations"),
    ("plate_markets", "Policy rate vs inflation"),
    ("plate_markets", "10-year government bond yield"),
    ("plate_markets", "Main equity index in US$"),
    ("plate_people", "Poverty rate"),
    ("plate_people", "Minimum wage"),
    ("plate_world", "Corruption Perceptions Index"),
    ("plate_mortality", "Excess deaths"),
    ("plate_mortality", "COVID-19 deaths"),
    ("plate_migration", "Immigration and emigration"),
    ("plate_migration", "Net migration"),
]


def test_every_parked_slot_stays_parked_with_a_reason():
    for name, title in PENDING:
        is_pending(name, title)
        why = " ".join(texts(name, title))
        assert len(why.split()) > 12, f"{title}: the reason is too thin"


def test_every_pending_panel_keeps_its_place_on_the_shared_scale():
    for name, title in PENDING:
        ax = panel(name, title).ax
        slot = ax.spine_slot
        assert slot.canonical
        lo, hi = ax.get_ylim()
        assert (lo, hi) == pytest.approx(slot.ref), title


# --------------------------------------------------------------- the cards
def test_the_headline_leads_gdp_then_income_then_population():
    head = sitebuild.headline_for(COUNTRY)
    labels = [h["label"]["en"] for h in head]
    assert labels[0].startswith("GDP")
    assert labels[1].startswith("GDP per person")
    assert labels[2].startswith("Population")
    # The three country readings that follow are this country's own.
    assert "Inflation" in labels[3]
    assert "growth" in labels[4]
    assert "protection status" in labels[5]
    gdp = col("world/gdp_usd.csv", "gdp_usd_bn_wb")
    assert head[0]["year"] == max(gdp)
    assert head[0]["value"]["en"] == f"US$ {gdp[max(gdp)]:,.0f}bn"


def test_every_card_reads_the_committed_csvs():
    cards = {ch["id"]: ch for ch in sitebuild.chapters_for(COUNTRY)}
    assert set(cards) == {
        "01-economy", "02-fiscal", "03-spending", "04-trade", "05-markets",
        "06-people", "07-world", "08-demography", "09-security",
        "10-mortality", "11-migration"}
    topics = {ch["topic"] for ch in cards.values()}
    assert topics == {"economy", "fiscal", "spending", "trade", "markets",
                      "people", "world", "demography", "security",
                      "mortality", "migration"}
    # No card's copy carries a number the data does not:
    gini = col("people/gini.csv", "gini")
    people = cards["06-people"]
    assert people["stats"][0]["value"]["en"] == f"{gini[2025]:,.2f}"
    # Every card describes its figure for a screen reader.
    for ch in cards.values():
        for loc in COUNTRY.locale_codes:
            assert len((ch["alt"] or {}).get(loc, "").split()) >= 8, ch["id"]


def test_the_plate_reads_only_declared_curated_files():
    import json
    listed = {d["file"] for d in sitebuild.datasets_for(COUNTRY)}
    recorded = json.loads(
        (COUNTRY.dir / "provenance.json").read_text(encoding="utf-8"))
    read = {f for files in recorded.values() for f in files}
    assert read, "provenance recorded nothing"
    assert read <= listed, sorted(read - listed)
    assert not [f for f in read if "_from_" in f], \
        "a plate must never draw from a fetcher sidecar"
    assert len(recorded) == 11


def test_no_local_currency_level_is_drawn_anywhere():
    """A bolívar amount is meaningless across three redenominations.

    The prose may explain them — and does, on three plates — but no panel
    may plot a number in bolívares of any vintage. The one identity drawn is
    the 2018 redenomination itself, which is an exchange rule and not a
    level; the only series that crosses a redenomination is the exchange
    rate, and it is drawn as an index.
    """
    amount = re.compile(r"\d[\d.,]*\s*(Bs|VES|bolívar)")
    for name in ("plate_economy", "plate_fiscal", "plate_spending",
                 "plate_trade", "plate_markets", "plate_world",
                 "plate_people", "plate_migration"):
        for p in plate(SLUG, name).panels():
            for t in p.texts():
                if amount.search(t):
                    assert "1,000,000 BsS = 1 VES" in t, t
    # The exchange rate is the only file with a VES column, and the plate
    # draws its index, not its units.
    assert "ves_per_usd" in rows("markets/fx_official.csv")[0]
    assert "ves_per_usd" not in rows("world/gdp_usd.csv")[0]
    drawn = panel("plate_markets", "Currency against the US$").points("")
    assert max(drawn.values()) == pytest.approx(100.0, abs=1e-6)
