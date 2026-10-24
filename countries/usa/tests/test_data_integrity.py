"""Invariants the American plates rely on. If one breaks, a plate lies.

These are facts about the data rather than about the drawing: a series
labelled "subset of" has to be one, a part year has to be recorded as a
part year, and two series on different bases have to stay two series. The
generic data hygiene — ordered years, no duplicates, no placeholders —
lives in tests/test_data.py and runs against every country.
"""
from __future__ import annotations

import csv

import pytest

from core.country import Country

DATA = Country.load("usa").data_dir


def read(rel: str, key: str = "year") -> dict[int, dict[str, str]]:
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        rows = csv.DictReader(ln for ln in fh if not ln.lstrip().startswith("#"))
        return {int(r[key]): r for r in rows if (r.get(key) or "").strip()}


def num(row: dict, name: str):
    try:
        return float((row.get(name) or "").strip())
    except ValueError:
        return None


def contained(rel, child, parent, key="year"):
    """Every year where both are published, child <= parent."""
    bad = []
    for year, row in sorted(read(rel, key).items()):
        c, p = num(row, child), num(row, parent)
        if c is None or p is None:
            continue
        if c > p + 1e-9:
            bad.append((year, c, p))
    assert not bad, f"{child} exceeds {parent} in {bad[:4]}"


# ------------------------------------------------------------- subsets
# The plates say "subset of" in so many words. If the arithmetic stops
# agreeing with the label, the label becomes the lie.
@pytest.mark.parametrize("rel,child,parent,key", [
    ("fiscal/debt.csv", "public_tn", "gross_tn", "fiscal_year"),
    ("social/violence.csv", "firearm_homicides", "firearm_deaths", "year"),
    ("social/violence.csv", "synthetic_opioid_overdoses", "overdoses", "year"),
    ("social/violence.csv", "opioid_overdoses", "overdoses", "year"),
    ("macro/unemployment.csv", "value", "u6", "year"),
    ("credit/credit_access.csv", "cc_balance", "cc_limit", "year"),
])
def test_a_series_labelled_a_subset_really_is_one(rel, child, parent, key):
    contained(rel, child, parent, key)


def test_named_spending_functions_are_within_total_outlays():
    """The parts are drawn as a share of the whole, so they must be it."""
    for year, row in sorted(read("fiscal/spending.csv", "fiscal_year").items()):
        total = num(row, "total_usdbn")
        if total is None:
            continue
        named = [num(row, c) for c in row
                 if c.endswith("_usdbn") and c != "total_usdbn"]
        got = sum(v for v in named if v is not None)
        assert abs(got - total) <= 0.5, \
            f"{year}: the parts ({got}) no longer add up to {total}"


# -------------------------------------------------------- partial years
def test_unemployment_2025_has_eleven_months():
    """October 2025 was never collected and never will be. If this ever
    reads 12, something has invented a month."""
    assert read("macro/unemployment.csv")[2025]["months"] == "11"


@pytest.mark.parametrize("rel,column,full", [
    ("macro/unemployment.csv", "months", 12),
    ("trade/goods.csv", "months", 12),
    ("markets/sp500.csv", "trading_days", 240),
    ("credit/household_debt.csv", "quarters", 4),
])
def test_counts_are_present_where_a_year_is_incomplete(rel, column, full):
    """A part year has to be recorded as one, or a plate cannot say so —
    and an annual total for a year still running, drawn on the same line
    as the complete ones, renders a collapse that never happened."""
    row = read(rel)[2026]
    assert row[column].strip(), f"{rel}: no coverage count for 2026"
    assert float(row[column]) < full, f"{rel}: 2026 reported as complete"


# --------------------------------------------------------------- bases
def test_census_and_bea_goods_balances_differ():
    """They measure the same trade under two definitions. If they ever
    match exactly, one has been overwritten with the other."""
    census, bea = read("trade/goods.csv"), read("trade/trade.csv")
    same = [y for y in census
            if y in bea
            and num(census[y], "balance") is not None
            and num(census[y], "balance") == num(bea[y], "goods_balance")]
    assert same == [], "the two bases have been conflated"


def test_covid_underlying_and_involved_are_separate_columns():
    """Died *of* and died *with* are different counts and must not merge."""
    header = set(read("social/mortality.csv")[2020])
    for column in ("covid_underlying", "covid_involved",
                   "influenza_underlying", "influenza_involved"):
        assert column in header, f"{column} is gone"


def test_budget_rows_name_their_publisher():
    """OMB and Treasury publish the same year differently; a row that does
    not say which one it came from cannot be checked against either."""
    for year, row in sorted(read("fiscal/budget.csv", "fiscal_year").items()):
        if not (row.get("receipts_usdbn") or "").strip():
            continue
        assert row["source"] in ("omb", "treasury"), \
            f"{year}: source {row['source']!r}"


def test_acs_migration_stock_uses_one_survey_universe():
    rows = read("migration/stock_acs.csv")
    row = rows[2024]
    assert num(row, "total_population") == 340_110_990
    assert num(row, "foreign_born") == 50_234_858
    assert num(row, "naturalized") + num(row, "noncitizen") == num(row, "foreign_born")
    assert 2020 not in rows
