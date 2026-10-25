"""The facts Paraguay's plates assert.

Each test states a claim a plate makes about the country's own data, so a
refetch that invalidates the claim fails loudly instead of quietly
changing a published chart. The four that matter most here:

- the two fiscal perimeters (IMF general government, accrual; MEF central
  administration, cash) are two labelled pairs of lines, never spliced;
- the two population denominators are 9% apart and every per-person and
  per-1,000 figure names which one it used;
- Itaipú and Yacyretá are drawn as fiscal revenue under the treaties, not
  as a hydro share of GDP;
- a slot with no published series stays visibly pending, with the reason.
"""

from __future__ import annotations

import csv

import pytest

from core.country import Country
from core import sitebuild, spine
from core.render import load_plates
from tests.probe import plate

SLUG = "paraguay"
COUNTRY = Country.load(SLUG)
DATA = COUNTRY.data_dir


def rows(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(x for x in fh if not x.startswith("#")))


def num(r: dict, key: str) -> float:
    v = (r.get(key) or "").strip()
    return float(v) if v else float("nan")


def by_year(rel: str) -> dict[int, dict]:
    return {int(r["year"]): r for r in rows(rel)}


def pending(name: str, panel: str) -> None:
    p = plate(SLUG, name).panel(panel)
    assert not p.data_lines(), f"{name}/{panel}: a pending panel has data"
    assert any("pending" in t.lower() or "pendiente" in t.lower()
               or "pendente" in t.lower() for t in p.texts()), \
        f"{name}/{panel}: no pending marker"


# --------------------------------------------------------------- registry
def test_registry_is_twelve_spine_topics():
    plates = load_plates(COUNTRY)
    assert [p.filename for p in plates] == [
        f"{i:02d}-{t}.png" for i, t in enumerate(
            ["economy", "fiscal", "spending", "trade", "markets", "credit",
             "people", "world", "demography", "security", "mortality",
             "migration"], start=1)]
    assert [p.topic for p in plates] == [
        "economy", "fiscal", "spending", "trade", "markets", "credit",
        "people", "world", "demography", "security", "mortality",
        "migration"]


def test_the_headline_leads_with_gdp_then_people_then_population():
    h = sitebuild.headline_for(COUNTRY)
    labels = [x["label"]["en"] for x in h]
    assert labels[:3] == ["GDP", "GDP per person, US$", "Population"]
    # The population reading is the last complete year, not the 2050
    # projection sitting in the same file.
    assert h[2]["year"] == COUNTRY.last_full_year
    pop = by_year("demography/population.csv")
    assert h[2]["value"]["en"].startswith(
        f"{num(pop[COUNTRY.last_full_year], 'population') / 1e6:.1f}")


# ------------------------------------------------------- the fiscal seams
def test_the_two_fiscal_perimeters_are_four_lines_never_joined():
    p = plate(SLUG, "plate_fiscal").panel("Revenue and expenditure")
    gg = by_year("fiscal/fiscal.csv")
    nat = by_year("fiscal/fiscal_national.csv")
    assert p.points("General government, revenue")[2024] == \
        pytest.approx(num(gg[2024], "revenue_pct_gdp"))
    assert p.points("Central administration, revenue")[2024] == \
        pytest.approx(num(nat[2024], "revenue_pct_gdp"))
    # The perimeter gap is real and about four points of GDP: the accrual
    # line is the wider one in every year both publish.
    gap = num(gg[2024], "revenue_pct_gdp") - num(nat[2024], "revenue_pct_gdp")
    assert gap == pytest.approx(3.84, abs=0.05)
    # The national line runs past the general-government one: the MEF has
    # 2025, the IMF vintage does not.
    assert max(p.points("Central administration, revenue")) == 2025
    assert max(p.points("General government, revenue")) == 2024


def test_the_cash_balance_is_a_second_line_not_a_continuation():
    p = plate(SLUG, "plate_fiscal").panel("Overall and primary balance")
    nat = by_year("fiscal/fiscal_national.csv")
    gg = by_year("fiscal/fiscal.csv")
    assert p.points("MEF net lending")[2025] == \
        pytest.approx(num(nat[2025], "net_lending_pct_gdp"))
    assert p.points("Primary balance")[2024] == \
        pytest.approx(num(gg[2024], "primary_balance_pct_gdp"))
    # 2025 is a general-government figure in the staged vintage; the cash
    # line differs from it, which is the point of drawing both.
    assert num(nat[2025], "net_lending_pct_gdp") != \
        num(gg[2025], "balance_pct_gdp")


# ------------------------------------------------ the population seam
def test_the_two_population_denominators_are_two_lines():
    p = plate(SLUG, "plate_demography").panel("Population")
    ine = by_year("demography/population.csv")
    un = by_year("demography/population_un_wpp.csv")
    ine_2025 = num(ine[2025], "population") / num(ine[2006], "population") * 100
    un_2025 = num(un[2025], "population") / num(un[2006], "population") * 100
    assert p.points("revision 2024")[2025] == pytest.approx(ine_2025, abs=0.01)
    assert p.points("UN WPP")[2025] == pytest.approx(un_2025, abs=0.01)
    # 6,417,076 against 7,013,078: the gap is the 2022 census, and the
    # series are never joined into one line.
    assert num(un[2025], "population") > num(ine[2025], "population")
    assert num(un[2025], "population") / num(ine[2025], "population") == \
        pytest.approx(1.0929, abs=0.0005)
    labels = {ln.get_label() for ln in p.data_lines()
              if not ln.get_label().startswith("_")}
    assert len(labels) == 2, f"two population lines expected, got {labels}"


def test_gdp_per_person_uses_the_un_denominator_and_says_so():
    p = plate(SLUG, "plate_economy").panel("GDP per person")
    assert any("UN population" in t for t in p.texts())
    e = by_year("macro/economy.csv")
    # The staged per-person column is the World Bank's, divided by the UN
    # series — not by INE's population, which gives about 9% more.
    world = by_year("world/gdp_usd.csv")
    gdp_usd = num(world[2025], "gdp_usd_bn") * 1e9
    un_pop = num(by_year("demography/population_un_wpp.csv")[2025],
                 "population")
    ine_pop = num(by_year("demography/population.csv")[2025], "population")
    staged = num(e[2025], "gdp_per_person_usd")
    assert staged == pytest.approx(gdp_usd / un_pop, rel=0.01)
    assert gdp_usd / ine_pop > staged * 1.08


# ------------------------------------------------------ the migration rates
def test_each_migration_rate_divides_by_its_own_publishers_population():
    p = plate(SLUG, "plate_migration").panel("Net migration (per 1,000")
    m = by_year("migration/migration.csv")
    un_pop = by_year("demography/population_un_wpp.csv")
    assert p.points("INE, per")[2025] == \
        pytest.approx(num(m[2025], "net_migration_rate_per_1000"))
    un_rate = num(m[2025], "net_migration_persons") / \
        num(un_pop[2025], "population") * 1000
    assert p.points("UN WPP, per")[2025] == pytest.approx(un_rate, abs=0.01)
    # Dividing the UN count by INE's population would give a third,
    # different rate — 9% larger, because INE's denominator is smaller.
    # That is exactly what is not done: the UN line uses the UN series.
    ine_pop = by_year("demography/population.csv")
    wrong = num(m[2025], "net_migration_persons") / \
        num(ine_pop[2025], "population") * 1000
    assert wrong / un_rate == pytest.approx(
        num(un_pop[2025], "population") / num(ine_pop[2025], "population"),
        abs=0.001)
    assert any("never mixed" in t for t in p.texts())


def test_the_migration_flow_slot_stays_pending():
    pending("plate_migration", "Immigration and emigration")
    p = plate(SLUG, "plate_migration").panel("Net migration in persons")
    assert p.bars(), "the persons lens should carry the UN level"
    assert any("net" in t.lower() for t in p.texts())


# ---------------------------------------------------- the hydro revenue
def test_the_hydro_revenue_is_fiscal_revenue_not_a_share_of_gdp():
    p = plate(SLUG, "plate_trade").panel("Itaipú and Yacyretá")
    nat = by_year("fiscal/fiscal_national.csv")
    assert p.points("Royalties")[2006] == \
        pytest.approx(num(nat[2006], "itaipu_royalties_pct_gdp"))
    assert p.points("Energy-cession")[2025] == \
        pytest.approx(num(nat[2025], "itaipu_cession_pct_gdp"))
    joined = " ".join(p.texts())
    assert "fiscal revenue" in joined
    assert "not a hydro share" in joined
    # The trade panels carry national-accounts trade and customs partner
    # shares; the royalties are a lens of their own and appear in no
    # other slot's series.
    for name in ("Exports and imports", "Trade balance",
                 "Top export destinations"):
        assert "Royalties" not in plate(SLUG, "plate_trade") \
            .panel(name).legend_labels()


# --------------------------------------------------------- the conversions
def test_the_minimum_wage_conversion_uses_the_same_year_rate():
    p = plate(SLUG, "plate_people").panel("Minimum wage")
    inc = by_year("people/income.csv")
    fx = by_year("markets/fx.csv")
    for year in (2006, 2019, 2024):
        expected = num(inc[year], "minimum_wage_pyg_month") / \
            num(fx[year], "pyg_per_usd")
        assert num(inc[year], "minimum_wage_usd_month") == \
            pytest.approx(expected, abs=0.01)
        line = p.data_lines()[0]
        drawn = dict(zip(line.get_xdata(), line.get_ydata()))
        assert float(drawn[year]) == pytest.approx(expected, abs=0.01)
    # 2025 is blank, not carried forward from 2024.
    assert num(inc[2025], "minimum_wage_usd_month") != \
        num(inc[2025], "minimum_wage_usd_month")


def test_the_price_level_lens_chains_the_cpi_from_2006():
    p = plate(SLUG, "plate_people").panel("What the statutory minimum")
    e = by_year("macro/economy.csv")
    inc = by_year("people/income.csv")
    level, run = {2006: 100.0}, 100.0
    for y in range(2007, 2025):
        run *= 1 + num(e[y], "cpi_inflation_pct") / 100
        level[y] = run
    base = num(inc[2006], "minimum_wage_pyg_month")
    nominal = num(inc[2024], "minimum_wage_pyg_month") / base * 100
    real = nominal / (level[2024] / 100)
    assert p.points("nominal")[2024] == pytest.approx(nominal, abs=0.01)
    assert p.points("Deflated")[2024] == pytest.approx(real, abs=0.01)
    # The statutory minimum rose about 2.3-fold and prices as much, so
    # in real terms the 2024 minimum is just BELOW its 2006 level — the
    # panel's finding, and not what a nominal chart would suggest.
    assert nominal == pytest.approx(229.4, abs=0.5)
    assert real == pytest.approx(98, abs=1)


def test_the_people_panel_carries_the_survey_break():
    p = plate(SLUG, "plate_people").panel("Poverty rate")
    assert any("EPH" in t for t in p.texts())
    inc = by_year("people/income.csv")
    assert num(inc[2006], "poverty_rate_pct") == pytest.approx(47.26, abs=0.01)
    assert num(inc[2025], "poverty_rate_pct") == pytest.approx(16.0, abs=0.01)


# ------------------------------------------------ recession bands and 2022
def test_only_the_negative_episodes_are_banded():
    bands = [(a, b) for a, b, _ in COUNTRY.recessions]
    assert (2019.0, 2021.0) in bands
    assert not any(a <= 2022 < b for a, b in bands)
    e = by_year("macro/economy.csv")
    # 2019 and 2020 are the two consecutive negative years; 2022 is a
    # stagnation of three hundredths of a point and is not banded.
    assert num(e[2019], "gdp_growth_pct") < 0
    assert num(e[2020], "gdp_growth_pct") < 0
    assert num(e[2022], "gdp_growth_pct") == pytest.approx(-0.03, abs=0.001)


# ------------------------------------------------------ the partner shares
def test_the_partner_shares_sum_to_100_and_argentina_is_not_zero():
    t = by_year("trade/partners.csv")
    for year, r in t.items():
        total = sum(num(r, c) for c in ("argentina_pct", "brazil_pct",
                                        "chile_pct", "usa_pct", "rest_pct"))
        assert total == pytest.approx(100.0, abs=0.05), year
    # The first curation pass published 0.00 for five years; the payload
    # carries these, and the fetcher now pins the 2016 value.
    assert num(t[2016], "argentina_pct") == pytest.approx(10.18, abs=0.01)
    assert num(t[2020], "argentina_pct") == pytest.approx(26.00, abs=0.01)
    p = plate(SLUG, "plate_trade").panel("Top export destinations")
    assert p.points("Argentina")[2018] == pytest.approx(28.99, abs=0.01)


# ------------------------------------------------------------- the pendings
def test_parked_slots_stay_parked():
    for name, panel in [
            ("plate_spending", "Spending by function"),
            ("plate_spending", "Social protection"),
            ("plate_markets", "Policy rate"),
            ("plate_markets", "10-year government bond"),
            ("plate_markets", "Main equity index"),
            ("plate_credit", "Household debt"),
            ("plate_credit", "Household lending rate"),
            ("plate_world", "Corruption Perceptions"),
            ("plate_mortality", "Excess deaths"),
            ("plate_mortality", "COVID-19 deaths"),
            ("plate_migration", "Immigration and emigration")]:
        pending(name, panel)


def test_the_lethally_pending_ones_name_the_route_that_failed():
    for name, panel, needle in [
            ("plate_markets", "Policy rate", "MFS_IR"),
            ("plate_spending", "Spending by function", "GFS_COFOG"),
            ("plate_credit", "Household debt", "BIS"),
            ("plate_mortality", "Excess deaths", "2017"),
            ("plate_markets", "Main equity index", "index")]:
        texts = " ".join(plate(SLUG, name).panel(panel).texts())
        assert needle in texts, f"{name}/{panel}: no route evidence"


# ------------------------------------------------------------ the spine
def test_no_slot_leaves_the_shared_scale():
    for key in ("economy.growth", "fiscal.revenue_expenditure",
                "fiscal.balance", "fiscal.debt", "trade.exports_imports",
                "trade.balance", "people.gini", "people.poverty",
                "demography.population", "demography.fertility",
                "security.homicide", "security.suicide",
                "credit.npl", "migration.net"):
        slot = spine.SLOTS[key]
        assert slot.ref is not None
    # The four plates whose data come closest to a shared edge.
    assert spine.fit(spine.SLOTS["people.gini"], (42.9, 53.0))[0] == \
        spine.SLOTS["people.gini"].ref
    assert spine.fit(spine.SLOTS["demography.population"], (100, 127.4))[0] == \
        spine.SLOTS["demography.population"].ref


# ------------------------------------------------------------- the page
def test_no_plate_reads_fetch_sidecars():
    import json
    prov = json.loads((COUNTRY.dir / "provenance.json")
                      .read_text(encoding="utf-8"))
    bad = [f for files in prov.values() for f in files
           if "_from_" in f or "_check" in f]
    assert not bad, f"plates read sidecars: {bad}"


def test_every_locale_discloses_the_gaps_and_the_currency():
    import json
    ui = json.loads((COUNTRY.dir / "ui.json").read_text(encoding="utf-8"))
    assert set(ui) == set(COUNTRY.locale_codes)
    for code in COUNTRY.locale_codes:
        assert len(ui[code]["unavailable"]) == 10, code
        assert ui[code]["notes"], code
        # The guaraní's missing minor unit and the absence of a
        # redenomination are stated on the page, not only in the notes.
        joined = " ".join(ui[code]["notes"] + [ui[code]["dek"]])
        assert "1.000" in joined or "1,000" in joined or "1 000" in joined


def test_the_catalog_covers_the_spine_units_in_both_languages():
    import json
    cat = json.loads((COUNTRY.dir / "i18n.json").read_text(encoding="utf-8"))
    for unit in spine.strings():
        for code in ("es", "pt"):
            assert cat.get(unit, {}).get(code), f"{unit}/{code}"
