"""Counts into the spine's shared units: rates and 2006 indices.

PLATE_SPINE.md rule 4 puts every canonical slot in one unit: deaths and
violence per 100,000 people, births, deaths and flows per 1,000, currencies
and equities as an index with 2006 = 100. These are the conversions, in one
place, so every country makes them the same way.

Every function takes a series as any of the shapes the plates already
hold:

    {2006: 1.2, 2007: 1.3}                 a mapping, year → value
    ([2006, 2007], [1.2, 1.3])             (years, values), as ctx.series
    [(2006, 1.2), (2007, 1.3)]             a list of pairs, as SiteContext.col

A tuple of exactly two is always read as (years, values), so pass pairs as
a list.

and returns `(years, values)`, sorted by year, ready for `ctx.line`.
Blanks (NaN or None) are dropped, never zero-filled.

The two series of a rate are matched **by year, never by position**. A
count that starts in 2010 and a population that starts in 2006 zipped by
index would divide 2010's deaths by 2006's people, and nothing would look
wrong. A year with a count and no population raises instead of being
skipped: a rate that silently loses a year is a hole someone has to notice.

Rule 5's other half — that the population covers the same territory and
the same legal scope as the count — is the caller's to get right, and the
panel or DATA_NOTES names the series used. Where the publisher already
publishes the rate, use theirs rather than these.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

BASE_YEAR = 2006


def _pairs(series, what: str) -> dict[int, float]:
    """{year: value} with the blanks dropped, from any accepted shape."""
    if isinstance(series, Mapping):
        items = list(series.items())
    elif isinstance(series, tuple) and len(series) == 2:
        years, vals = series
        if len(years) != len(vals):
            raise ValueError(f"{what}: {len(years)} years for "
                             f"{len(vals)} values")
        items = list(zip(years, vals))
    else:
        items = list(series)
    out: dict[int, float] = {}
    for y, v in items:
        if v is None or isinstance(v, str):
            continue
        v = float(v)
        if math.isnan(v):
            continue
        y = int(y)
        if y in out:
            raise ValueError(f"{what}: year {y} appears twice")
        out[y] = v
    return out


def _out(d: dict[int, float]) -> tuple[list[int], list[float]]:
    ys = sorted(d)
    return ys, [d[y] for y in ys]


def per(count, population, base: float) -> tuple[list[int], list[float]]:
    """count ÷ population × base, year by year.

    Raises if any year that has a count has no population, or a
    population that is not positive.
    """
    c = _pairs(count, "count")
    p = _pairs(population, "population")
    lacking = sorted(y for y in c if y not in p)
    if lacking:
        raise ValueError(
            f"no population for {lacking}: a rate needs the population of "
            f"the same year, and these years would otherwise be dropped "
            f"or divided by another year's")
    bad = sorted(y for y in c if p[y] <= 0)
    if bad:
        raise ValueError(f"population is not positive in {bad}")
    return _out({y: v / p[y] * base for y, v in c.items()})


def per_100k(count, population) -> tuple[list[int], list[float]]:
    """Per 100,000 people: deaths and violence."""
    return per(count, population, 100_000)


def per_1000(count, population) -> tuple[list[int], list[float]]:
    """Per 1,000 people: births, deaths and migration flows."""
    return per(count, population, 1_000)


def index_2006(series, base_year: int = BASE_YEAR
               ) -> tuple[list[int], list[float]]:
    """The series as an index with base_year = 100.

    For a level that should read the same way it moves: population,
    an equity index already in US$, the broad dollar index.
    """
    d = _pairs(series, "series")
    b = d.get(base_year)
    if b is None:
        raise ValueError(f"no value for {base_year}, the index's base year")
    if b == 0:
        raise ValueError(f"the {base_year} value is zero; nothing to index on")
    return _out({y: v / b * 100 for y, v in d.items()})


def fx_index(lc_per_usd, base_year: int = BASE_YEAR
             ) -> tuple[list[int], list[float]]:
    """An exchange rate as an index, base_year = 100, up = stronger.

    Takes local currency per US dollar — the way most central banks quote
    it, where a bigger number is a weaker currency — and inverts it, so
    the line rises when the local currency gains against the dollar, the
    same direction on every country's plate. A currency that buys twice
    as many dollars as in 2006 reads 200; one that buys half, 50.

    A rate already quoted the other way round (US$ per unit, or a broad
    trade-weighted index of the currency itself) is not inverted: pass it
    to index_2006 instead.
    """
    d = _pairs(lc_per_usd, "lc_per_usd")
    b = d.get(base_year)
    if b is None:
        raise ValueError(f"no rate for {base_year}, the index's base year")
    bad = sorted(y for y, v in d.items() if v <= 0)
    if bad:
        raise ValueError(f"exchange rate is not positive in {bad}")
    return _out({y: b / v * 100 for y, v in d.items()})
