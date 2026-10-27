"""The plate spine, as data: every topic's slots, units and scales.

PLATE_SPINE.md is the decision record; this is its executable form, and
the two are meant to be read side by side. Every country draws a chapter
on the same 2 × 2 frame, with the same indicator in the same slot, in the
same unit, on the same y-scale, so the comparison viewer can wipe one
country's plate over another's and the reader sees only the difference.

A plate opts in by declaring its topic (`ctx.fig(..., topic="economy")`,
or `topic=` in a declarative PLATES entry) and then claims its panels by
slot key instead of by position:

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")

`Infographic.slot` checks the order against the table below, titles the
panel, tags it with its key and, when the plate is saved, puts the axis on
the atlas-wide scale here. Data outside that shared scale fail the render:
the maintainer must widen the one scale and regenerate every peer rather
than publish two incompatible pixel transforms. `tests/test_spine.py`
holds every country with `spine: true` in its country.yaml to the same table.

What each field means:

  key     "<topic>.<name>", stable: tests, translations and the viewer
          address a panel by it.
  kind    CANONICAL: the same indicator in every country, which must
          register in the overlay. LENS: the country's own story, which
          is not expected to, and so gets no forced scale.
  unit    the shared unit, in English. It is drawn as the panel's y-axis
          label and translated like every other string, so a country on
          the spine carries it in its i18n.json.
  ref     the shared atlas-wide y-range (lo, hi). None on a lens slot.
  grow    retained as decision metadata for which end historically needed
          room; it never authorizes country-local scaling.
  scale   LINEAR or LOG. Log is used only where the spine says so, for
          every country at once.
  ticks   the fixed major ticks of a log slot across its shared range.
  zero    True for a signed series: a zero line is drawn under the data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

CANONICAL, LENS = "canonical", "lens"
UP, DOWN, BOTH, NONE = "up", "down", "both", "none"
LINEAR, LOG = "linear", "log"

#: The only frame a spine plate is drawn in (PLATE_SPINE.md rule 1).
FRAME = {"nrows": 2, "ncols": 2, "figsize": (16.0, 10.2), "right": 0.955}
#: Label every second year (rule 2).
TICK_EVERY = 2

#: What each panel's drawing occupies on the plate, as (left, bottom, right,
#: top) in figure fractions with y up, in reading order. It is the envelope of
#: everything every country draws for that slot — axes, title, tick labels,
#: axis labels, partial-year captions — measured over all the spine plates, so
#: the cell a viewer cuts out of a plate is the panel and nothing around it:
#: no blank margin, none of the footer. The two columns and the two rows are
#: given the same size (the narrower column is widened to the wider), so the
#: four panels lift and isolate at the same size and sit alike in the plate's
#: margins. tests/test_spine.py draws every plate and fails if one ink strays
#: outside its cell, which is how a panel that outgrows this gets noticed;
#: re-measure with the same check.
PANEL_INK = (
    (0.0133, 0.4686, 0.4811, 0.8705),
    (0.5070, 0.4686, 0.9748, 0.8705),
    (0.0133, 0.0395, 0.4811, 0.4414),
    (0.5070, 0.0395, 0.9748, 0.4414),
)
#: Room kept around that envelope: (left, bottom, right, top). Little at the
#: bottom, where the line of sources starts just below the lowest caption.
INK_PAD = (0.004, 0.0005, 0.004, 0.004)


@dataclass(frozen=True)
class Slot:
    key: str
    kind: str
    indicator: str
    unit: str | None = None
    ref: tuple[float, float] | None = None
    grow: str = NONE
    scale: str = LINEAR
    ticks: tuple[float, ...] = ()
    zero: bool = False

    @property
    def topic(self) -> str:
        return self.key.split(".", 1)[0]

    @property
    def canonical(self) -> bool:
        return self.kind == CANONICAL


def _c(key, indicator, unit, ref, grow=NONE, scale=LINEAR, ticks=(),
       zero=False) -> Slot:
    return Slot(key, CANONICAL, indicator, unit, ref, grow, scale,
                tuple(ticks), zero)


def _lens(key, indicator="the country's own story", unit=None) -> Slot:
    return Slot(key, LENS, indicator, unit)


# Fixed log ticks. A 1-2-5 ladder where the range spans two decades or
# fewer, decades (plus the listed top) where it spans more.
_LADDER_GDP_PC = (500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000,
                  200_000)
_LADDER_FX = (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200)
_LADDER_EQUITY = (10, 20, 50, 100, 200, 500, 1_000)
_LADDER_GDP = (10, 100, 1_000, 10_000, 50_000)
_LADDER_RESERVES = (1, 10, 100, 1_000, 5_000)
_LADDER_HOMICIDE = (0.05, 0.1, 0.3, 1, 3, 10, 30, 100)

#: topic → its slots, in reading order (1 top-left … 4 bottom-right).
SPINE: dict[str, tuple[Slot, ...]] = {
    "economy": (
        _c("economy.growth", "Real GDP growth", "% per year",
           (-35, 18), BOTH, zero=True),
        _c("economy.gdp_per_person", "GDP per person", "US$, current",
           (500, 200_000), NONE, LOG, _LADDER_GDP_PC),
        _c("economy.inflation", "Consumer price inflation", "% per year",
           (-5, 225), UP, zero=True),
        _c("economy.unemployment", "Unemployment rate",
           "% of labour force", (0, 30), UP),
    ),
    "fiscal": (
        _c("fiscal.revenue_expenditure", "Revenue and expenditure",
           "% of GDP", (0, 80)),
        _c("fiscal.balance", "Overall and primary balance", "% of GDP",
           (-35, 10), BOTH, zero=True),
        _c("fiscal.debt", "Gross debt", "% of GDP", (0, 300), UP),
        _c("fiscal.interest", "Interest paid", "% of GDP", (0, 10), UP),
    ),
    "spending": (
        _c("spending.by_function", "Spending by function, stacked",
           "% of GDP", (0, 75)),
        _c("spending.social_protection",
           "Social protection vs everything else", "% of GDP", (0, 70)),
        _c("spending.investment", "Investment rate, whole economy",
           "% of GDP", (0, 50)),
        _c("spending.public_investment", "Public investment", "% of GDP",
           (0, 12), UP),
    ),
    "trade": (
        _c("trade.exports_imports", "Exports and imports", "% of GDP",
           (0, 100), UP),
        _c("trade.balance", "Trade balance", "% of GDP", (-30, 40), BOTH,
           zero=True),
        _c("trade.destinations", "Top export destinations",
           "% of goods exports", (0, 90), UP),
        _lens("trade.lens"),
    ),
    "markets": (
        _c("markets.policy_rate", "Policy rate vs inflation", "%",
           (-5, 225), UP, zero=True),
        _c("markets.bond_10y", "10-year government bond yield",
           "%, annual average", (-2, 30), UP),
        _c("markets.currency", "Currency against the US$",
           "index 2006 = 100, up = stronger", (0.1, 200), NONE, LOG,
           _LADDER_FX),
        _c("markets.equities", "Main equity index in US$",
           "index 2006 = 100, in US$", (10, 1_000), NONE, LOG,
           _LADDER_EQUITY),
    ),
    "credit": (
        _c("credit.household_debt", "Household debt", "% of GDP",
           (0, 140)),
        _c("credit.lending_rate", "Household lending rate vs policy rate",
           "%", (-2, 110), UP),
        _c("credit.npl", "Non-performing loans", "% of loans", (0, 20), UP),
        _lens("credit.lens"),
    ),
    "people": (
        _c("people.gini", "Income inequality, Gini", "Gini, 0–100",
           (20, 60)),
        _c("people.poverty", "Poverty rate", "% of people", (0, 80), UP),
        _c("people.minimum_wage", "Minimum wage", "US$ per month",
           (0, 3_000), UP),
        _lens("people.lens"),
    ),
    "world": (
        _c("world.gdp", "GDP at current prices", "US$ bn", (10, 50_000),
           NONE, LOG, _LADDER_GDP),
        _c("world.hdi", "Human Development Index", "HDI, 0–1", (0.5, 1.0)),
        _c("world.cpi", "Corruption Perceptions Index", "score, 0–100",
           (0, 100)),
        _c("world.reserves", "Official reserves", "US$ bn", (1, 5_000),
           NONE, LOG, _LADDER_RESERVES),
    ),
    "demography": (
        _c("demography.population", "Population", "index 2006 = 100",
           (75, 150), BOTH),
        _c("demography.fertility", "Total fertility rate",
           "children per woman", (0, 3.5)),
        _c("demography.birth_death", "Crude birth and death rates",
           "per 1,000 people", (0, 25)),
        _c("demography.natural_migration",
           "Natural increase and net migration", "per 1,000 people",
           (-30, 45), BOTH, zero=True),
    ),
    "security": (
        _c("security.homicide", "Homicide rate", "per 100,000", (0.05, 100),
           NONE, LOG, _LADDER_HOMICIDE),
        _c("security.suicide", "Suicide rate", "per 100,000", (0, 45)),
        _c("security.road_deaths", "Road traffic deaths", "per 100,000",
           (0, 40)),
        _lens("security.lens"),
    ),
    "mortality": (
        _c("mortality.death_rate", "Crude death rate", "per 1,000 people",
           (0, 22)),
        _c("mortality.excess_deaths", "Excess deaths",
           "% above 2015–2019 average", (-25, 40), UP, zero=True),
        _c("mortality.covid", "COVID-19 deaths, underlying cause",
           "per 100,000", (0, 300), UP),
        _lens("mortality.lens", unit="per 100,000"),
    ),
    "migration": (
        _c("migration.flows", "Immigration and emigration",
           "per 1,000 people", (0, 50), UP),
        _c("migration.net", "Net migration", "per 1,000 people", (-30, 45),
           BOTH, zero=True),
        _c("migration.foreign_born", "Foreign-born share of the population",
           "% of population", (0, 50), UP),
        _lens("migration.lens"),
    ),
    # One country's national lens (PLATE_SPINE.md, "prices"). Its CPI, its
    # currency and its reserves also meet everyone else on economy slot 3,
    # markets slot 3 and world slot 4.
    "prices": (
        _lens("prices.lens1", "inflation"),
        _lens("prices.lens2", "the official and parallel exchange rates"),
        _lens("prices.lens3", "the gap between them"),
        _lens("prices.lens4"),
    ),
}

#: Every slot by key.
SLOTS: dict[str, Slot] = {s.key: s for slots in SPINE.values() for s in slots}
TOPICS = frozenset(SPINE)


def slots(topic: str) -> tuple[Slot, ...]:
    try:
        return SPINE[topic]
    except KeyError:
        raise SpineError(f"{topic!r} is not a spine topic; the spine has "
                         f"{sorted(SPINE)}") from None


def panel_cell(index: int) -> tuple[float, float, float, float]:
    """Where one slot's panel is, and answers a click: (left, top, width, height).

    As fractions of the image, measured from its top-left corner, so a
    viewer can place it over the plate at any size. `index` is the slot's
    place in reading order (0 top-left … 3 bottom-right).

    The cell is the panel with everything it draws around the axes — its
    title, the y-axis label and tick labels, the year ticks — and not the
    axes rectangle alone, so a click on a panel's title lands on that panel
    and a copy of the cell shows the whole panel. It is the measured
    envelope in PANEL_INK plus INK_PAD. The frame is the same for every
    spine plate in every country, so this is one table for all of them.
    """
    if not 0 <= index < len(PANEL_INK):
        raise IndexError(f"a spine plate has {len(PANEL_INK)} panels, "
                         f"not a panel {index}")
    x0, y0, x1, y1 = PANEL_INK[index]
    pl, pb, pr, pt = INK_PAD
    left, right = max(0.0, x0 - pl), min(1.0, x1 + pr)
    bottom, top = max(0.0, y0 - pb), min(1.0, y1 + pt)
    return left, 1 - top, right - left, top - bottom


def strings() -> list[str]:
    """Every English string the spine itself can put on a plate.

    A country on the spine needs each of these in its i18n.json for every
    language it publishes in that isn't English.
    """
    out = {s.unit for s in SLOTS.values() if s.unit}
    return sorted(out)


class SpineError(AssertionError):
    """A plate that does not keep to the spine. Raised, never warned."""


# ------------------------------------------------------------ the data
def data_extent(ax) -> tuple[float, float] | None:
    """(min, max) of every y value drawn in data coordinates, or None.

    Lines, bars (a bar spans its bottom to its top, so a stacked segment
    counts at the height it reaches), filled areas and scatter points.
    Reference marks drawn in a blended transform — axhline, axvline,
    axvspan, which is what a recession band is — are not data and are
    left out, as are texts.
    """
    ys: list[np.ndarray] = []
    data = ax.transData
    for ln in ax.get_lines():
        if ln.get_transform() is data:
            ys.append(np.asarray(ln.get_ydata(), dtype=float))
    for patch in ax.patches:
        # get_data_transform, not get_transform: a Rectangle's own
        # transform is its patch transform composed onto the data one, so
        # an identity test against transData never matches a bar.
        if (patch.get_data_transform() is data
                and hasattr(patch, "get_height")):
            y, h = float(patch.get_y()), float(patch.get_height())
            ys.append(np.array([y, y + h]))
    for coll in ax.collections:
        if coll.get_transform() is not data:
            if coll.get_offset_transform() is data:
                off = np.asarray(coll.get_offsets(), dtype=float)
                if off.size:
                    ys.append(off[:, 1])
            continue
        for path in coll.get_paths():
            v = np.asarray(path.vertices, dtype=float)
            if v.size:
                ys.append(v[:, 1])
    if not ys:
        return None
    allv = np.concatenate([np.ravel(y) for y in ys])
    allv = allv[np.isfinite(allv)]
    if not allv.size:
        return None
    return float(allv.min()), float(allv.max())


def fit(slot: Slot, extent: tuple[float, float] | None
        ) -> tuple[tuple[float, float], bool]:
    """Validate data against and return a canonical slot's shared limits.

    A pixel wipe is truthful only when every country uses exactly the same
    transform. Overflow therefore fails loudly and asks the maintainer to
    widen the single atlas-wide range instead of extending one country.
    The boolean is retained for API compatibility and is always false.
    """
    lo, hi = slot.ref
    if extent is None:
        return (lo, hi), False
    dmin, dmax = extent
    if slot.scale == LOG:
        if dmin <= 0:
            raise SpineError(
                f"{slot.key}: a value of {dmin} cannot be drawn on a log "
                f"axis; it would vanish rather than show")
    tol = 1e-9 * max(1.0, abs(lo), abs(hi), abs(dmin), abs(dmax))
    if dmin < lo - tol or dmax > hi + tol:
        raise SpineError(
            f"{slot.key}: data extent ({dmin:g}, {dmax:g}) is outside the "
            f"shared comparison scale ({lo:g}, {hi:g}); widen the slot's "
            "atlas-wide range and regenerate every country in this topic")
    return (lo, hi), False


def log_ticks(slot: Slot, lo: float, hi: float) -> list[float]:
    """The slot's fixed ticks over its atlas-wide log range.

    The mantissas of the declared ticks (1-2-5, or 1-3, or decades) are
    repeated across every decade between lo and hi rather than delegated
    to Matplotlib's context-sensitive locator.
    """
    mantissas = sorted({round(t / 10 ** math.floor(math.log10(t)), 6)
                        for t in slot.ticks})
    out = set(t for t in slot.ticks if lo <= t <= hi)
    for d in range(math.floor(math.log10(lo)), math.ceil(math.log10(hi)) + 1):
        for m in mantissas:
            v = m * 10 ** d
            outside = v < min(slot.ticks) or v > max(slot.ticks)
            if outside and lo <= v <= hi:
                out.add(float(f"{v:.6g}"))
    return sorted(out)


def tick_label(v: float, _pos=None) -> str:
    """A plain number for a log tick: 0.1, 30, 1,000 — never 10³."""
    if v >= 1:
        return f"{v:,.0f}"
    return f"{v:.6g}"
