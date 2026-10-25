"""The facts Venezuela's plates will assert, checked on the committed CSVs.

Each test here is a claim a plate makes about this country's own data, so a
refetch that invalidates the claim fails loudly instead of quietly changing a
published chart. The four that matter most:

- the collapse is drawn at its real size, and the two publishers' estimates
  agree on its direction while disagreeing about how deep it was;
- the hyperinflation is a continuous staff-estimate series and the national
  CPI is a separate short line that is never spliced into it;
- the exchange rate is converted across three redenominations by exactly the
  documented divisor, and stops in 2017 where the official rate stops;
- a year the publisher does not cover stays blank — in trade, in investment,
  in homicide — and never becomes a zero.

No plate is rendered here: this is the Phase A data contract.
"""
from __future__ import annotations

import csv
import math

from core.country import Country

SLUG = "venezuela"
COUNTRY = Country.load(SLUG)
DATA = COUNTRY.data_dir


def table(rel: str) -> list[dict[str, str]]:
    path = DATA / rel
    assert path.exists(), f"{rel} is missing"
    with path.open(encoding="utf-8", newline="") as fh:
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def by_year(rel: str) -> dict[int, dict[str, str]]:
    return {int(r["year"]): r for r in table(rel)}


def num(row: dict[str, str], column: str) -> float | None:
    cell = (row.get(column) or "").strip()
    if not cell:
        return None
    return float(cell)


# ------------------------------------------------------------- the collapse


def test_the_collapse_is_drawn_at_its_real_size():
    eco = by_year("macro/economy.csv")
    assert num(eco[2020], "gdp_growth_pct_wb") == -29.82
    assert num(eco[2020], "gdp_growth_pct_imf") == -33.2
    # 2019 and 2020 are the trough; nothing between 2006 and 2025 is deeper
    # than 2020 on either line, and 2014 is the first negative year.
    for column in ("gdp_growth_pct_wb", "gdp_growth_pct_imf"):
        values = {y: num(r, column) for y, r in eco.items()
                  if num(r, column) is not None}
        assert min(values, key=lambda y: values[y]) == 2020, column
        assert values[2014] < 0, f"{column}: 2014 should be negative"
        assert values[2021] > 0, f"{column}: 2021 is the recovery year"


def test_the_two_growth_estimates_never_disagree_about_direction():
    eco = by_year("macro/economy.csv")
    for year, row in eco.items():
        wb = num(row, "gdp_growth_pct_wb")
        imf = num(row, "gdp_growth_pct_imf")
        if wb is None or imf is None or year > COUNTRY.last_full_year:
            continue
        assert (wb > 0) == (imf > 0) or (abs(wb) < 0.5 and abs(imf) < 0.5), (
            f"{year}: World Bank {wb} and IMF {imf} disagree about the sign")


# --------------------------------------------------------- the hyperinflation


def test_the_hyperinflation_series_is_continuous_and_the_national_line_is_not():
    eco = by_year("macro/economy.csv")
    imf = [y for y, r in eco.items() if num(r, "cpi_inflation_pct_imf") is not None]
    bcv = [y for y, r in eco.items() if num(r, "cpi_inflation_pct_bcv") is not None]
    # The staff estimate covers every year of the window: it is interpolated
    # by the Fund's model, not by this repository, and a gap would mean the
    # fetcher dropped a year.
    assert imf == list(range(2006, COUNTRY.last_full_year + 1)), imf
    # The national CPI is the BCV's INPC as the World Bank republishes it,
    # and it stops in 2016 — a short, separate line.
    assert bcv == list(range(2009, 2017)), bcv
    assert num(eco[2018], "cpi_inflation_pct_imf") > 60_000
    assert num(eco[2019], "cpi_inflation_pct_imf") > 15_000
    # And the two are never the same column: 2016 exists in both and differs
    # only by rounding, which is the evidence they measure the same thing
    # for the years they overlap.
    overlap = num(eco[2016], "cpi_inflation_pct_imf") - \
        num(eco[2016], "cpi_inflation_pct_bcv")
    assert abs(overlap) < 0.2, f"2016 overlap differs by {overlap}"


# ------------------------------------------------------- the three bolívares


def test_the_exchange_rate_is_converted_by_exactly_the_documented_divisor():
    fx = by_year("markets/fx_official.csv")
    for year, row in fx.items():
        lcu = num(row, "lcu_per_usd")
        ves = num(row, "ves_per_usd")
        assert lcu and ves, f"{year}: both columns must be filled together"
        # 1 VES = 1,000,000 bolívares soberanos = 100,000,000,000 BsF.
        assert math.isclose(lcu / 1e11, ves, rel_tol=1e-9), (
            f"{year}: {lcu} lcu/1e11 is not {ves}")
        assert math.isclose(num(row, "fx_index_2006_100"),
                            2.147 / lcu * 100, rel_tol=1e-4), year


def test_the_exchange_rate_stops_where_the_official_rate_stops():
    fx = by_year("markets/fx_official.csv")
    assert max(fx) == 2017, (
        "the official rate series must not be extended past 2017 without a "
        "documented official source")
    assert num(fx[2006], "fx_index_2006_100") == 100.0
    # The index rises when the bolívar strengthens; by 2017 it has fallen.
    assert num(fx[2017], "fx_index_2006_100") < 25


# -------------------------------------------------- holes are holes, not zeros


def test_placeholder_zeros_in_the_world_bank_ratios_were_dropped():
    for rel, column in (("trade/trade.csv", "exports_pct_gdp"),
                        ("trade/trade.csv", "imports_pct_gdp"),
                        ("spending/spending.csv", "gfcf_pct_gdp")):
        rows = by_year(rel)
        filled = [y for y, r in rows.items() if num(r, column) is not None]
        assert min(filled) == 2012, (
            f"{rel}:{column} starts in {min(filled)}; the World Bank's "
            f"2006-2011 placeholders must be a hole, not a zero")
        assert all(num(r, column) > 0 for r in rows.values()
                   if num(r, column) is not None), (
            f"{rel}:{column} contains a zero, which this publisher uses to "
            f"mean 'no observation'")


def test_homicide_holes_are_left_blank():
    sec = by_year("security/security.csv")
    assert 2013 not in sec or num(sec[2013], "homicide_per_100k") is None
    assert 2018 not in sec or num(sec[2018], "homicide_per_100k") is None
    assert num(sec[2012], "homicide_per_100k") == 54.38


def test_no_series_is_extended_past_what_the_publisher_covers():
    assert max(by_year("world/reserves.csv")) == 2017
    assert max(by_year("world/hdi.csv")) == 2023
    assert max(by_year("security/security.csv")) <= 2022
    assert max(by_year("demography/vital.csv")) == 2024


# ---------------------------------------------------------------- the people


def test_the_national_gini_is_on_the_atlas_scale_and_agrees_with_the_crosscheck():
    gin = by_year("people/gini.csv")
    values = [num(r, "gini") for r in gin.values() if num(r, "gini") is not None]
    assert all(20 <= v <= 60 for v in values), values
    # The INE publishes 0-1; the atlas draws 0-100. 2006 is the one year the
    # World Bank's harmonised Gini also covers, and the two agree within a
    # point — the evidence the unit conversion is right.
    assert abs(num(gin[2006], "gini") - num(gin[2006], "gini_wdi_crosscheck")) < 1
    assert max(gin) == 2025


def test_net_migration_per_1000_is_derived_from_the_two_staged_columns():
    mig = by_year("migration/migration.csv")
    pop = by_year("demography/population.csv")
    for year, row in mig.items():
        net = num(row, "net_migration")
        rate = num(row, "net_migration_per_1000")
        if net is None or rate is None or year not in pop:
            continue
        expected = net / num(pop[year], "population") * 1000
        assert math.isclose(rate, expected, rel_tol=1e-6, abs_tol=0.005), year
    # The emigration wave, at its real size.
    assert num(mig[2018], "net_migration_per_1000") < -40


def test_displacement_adds_up_and_is_labelled_as_a_lens():
    dis = by_year("migration/displacement.csv")
    for year, row in dis.items():
        refugees = num(row, "refugees")
        seekers = num(row, "asylum_seekers")
        total = num(row, "refugees_and_asylum_seekers")
        assert total == refugees + seekers, year
        assert total == int(total), f"{year}: a count with a fraction"
    # The peak of the series is 2024 (1,730,210), not the latest year: in
    # 2025 refugee registrations rose while asylum-seeker registrations fell,
    # which is a status/registration pattern and not a reversal of the flow.
    totals = {y: num(r, "refugees_and_asylum_seekers") for y, r in dis.items()}
    assert max(totals, key=lambda y: totals[y]) == 2024, totals
    assert totals[2025] > 1_500_000


# ------------------------------------------------------------ bookkeeping


def test_every_curated_year_is_inside_the_plate_window():
    for path in sorted(DATA.rglob("*.csv")):
        if "_from_" in path.stem:
            continue
        for row in table(str(path.relative_to(DATA))):
            year = int(row["year"])
            assert COUNTRY.years[0] <= year <= COUNTRY.years[-1], (
                f"{path.name}: {year} is outside {COUNTRY.years[0]}-"
                f"{COUNTRY.years[-1]}")


def test_the_fiscal_file_has_no_debt_column():
    """Debt is pending, and the file must not grow one silently.

    GGXWDG_NGDP has no Venezuelan observations in the October 2026 WEO
    vintage, and no other official route produced a debt stock. If a later
    refetch finds one, this test fails and the manifest has to gain the
    source before the column appears on a plate.
    """
    rows = table("fiscal/fiscal.csv")
    assert rows
    assert not [c for c in rows[0] if "debt" in c.lower()]
