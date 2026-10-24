"""The ukraine plates, on the plate spine.

Four chapters: the war economy, Ukraine's place in the world, the
population (the national register and the international estimate as two
labelled lines), and what the hryvnia buys. Every other canonical topic
is either blocked at the publisher or not yet definition-checked; those
slots are drawn pending with the reason on the panel and the route in
SOURCES.yaml meta.pending, never filled with a number from somewhere
else.

The 2015 step in the national population line is the publisher's own
perimeter change (Ukrstat excludes the temporarily occupied territories
from that year on) and is annotated as such — the two population lines
are never spliced.
"""
from __future__ import annotations

W0 = 2006


# ------------------------------------------------------------ small helpers
def _yr(ctx, rel: str, col: str, since: int = W0):
    """(years, values) from a calendar-year CSV, blanks dropped."""
    t = ctx.table(rel)
    if not t or col not in t:
        return [], []
    yrs, vals = ctx.series(t, col)
    keep = [(y, v) for y, v in zip(yrs, vals) if y >= since]
    return [y for y, _ in keep], [v for _, v in keep]


def _at(years, vals, year):
    return dict(zip(years, vals))[year]


def _note(p, ax, x, y, text, ha="left", va="top", size=8.0):
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=size, style="italic", color=p.MUTED, zorder=7)


def _foot(p, ax, text):
    ax.text(0.5, -0.07, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.2, color=p.FAINT, style="italic")


def _pending(ig, ax, why):
    ax.text(0.5, 0.34, why, transform=ax.transAxes, ha="center", va="top",
            fontsize=8.2, style="italic", color=ig.p.MUTED)


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(a, xticks_years=not getattr(a, "_categorical_x", False))


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p
    E = "macro/economy.csv"
    I = "macro/gdp_growth_imf.csv"

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, E, "gdp_growth_pct")
    iy, iv = _yr(ctx, I, "gdp_growth_pct")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    v22 = _at(gy, gv, 2022)
    ax.annotate(f"{v22:.1f}%", (2022, v22), textcoords="offset points",
                xytext=(0, -2), ha="center", va="top", fontsize=8.8,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, f"the invasion year: {v22:.1f}% — the deepest "
          f"of the window;\n{_at(gy, gv, 2023):.1f}% and "
          f"{_at(gy, gv, 2024):.1f}% since, on a smaller base")
    _foot(p, ax, "World Bank national accounts; IMF WEO agrees "
          f"({_at(iy, iv, 2022):.1f}% in 2022)")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "world/gdp_per_person.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    _note(p, ax, 0.02, 0.96, f"US$ at market rates: {_at(py, pv, 2022):,.0f} "
          f"in 2022,\n{_at(py, pv, py[-1]):,.0f} in {py[-1]} — nominal, "
          "not per person present")
    _foot(p, ax, "World Bank, current US$. The UN population includes "
          "refugees abroad")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year)")
    cy, cv = _yr(ctx, E, "cpi_inflation_pct")
    ctx.line(ax, cy, cv, p.ALERT)
    ig.add_recessions(ax, label=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(6, 2), ha="left",
                fontsize=8.8, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, f"{_at(cy, cv, 2022):.1f}% in 2022 and "
          f"{_at(cy, cv, 2023):.1f}% in 2023:\nthe war's price shock, after "
          "the 2015 hryvnia collapse")
    _foot(p, ax, "World Bank republication of the Ukrstat CPI — the SSSU "
          "line when its API answers")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    uy, uv = _yr(ctx, E, "unemployment_pct")
    ctx.line(ax, uy, uv, p.NAVY)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, uy, uv, p.NAVY, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{uv[-1]:.1f}% in {uy[-1]} is the last "
          "modelled value —\nthe ILO series stops there: no survey was run "
          "in the war years", size=7.8)
    _foot(p, ax, "World Bank (ILO modelled), 2006–2021. The Ukrstat LFS "
          "line when the survey resumes")
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "world/gdp_usd.csv", "gdp_usd")
    gb = [v / 1e9 for v in gv]
    ctx.line(ax, gy, gb, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gb, p.BLUE, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, f"US${_at(gy, gb, 2021):,.0f}bn in 2021, "
          f"US${_at(gy, gb, 2022):,.0f}bn in 2022")
    _foot(p, ax, "World Bank, current US$ — nominal, so the fall is the "
          "war and the exchange rate together")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "world/hdi.csv", "hdi")
    ctx.line(ax, hy, hv, p.GREEN)
    ctx.endlabel(ax, hy, hv, p.GREEN, lambda v: f"{v:.3f}", dy=8)
    _note(p, ax, 0.02, 0.96, f"{_at(hy, hv, 2021):.3f} in 2021, "
          f"{hv[-1]:.3f} in {hy[-1]} —\none HDR vintage (2025) throughout")
    _foot(p, ax, "UNDP HDR 2025. The series stops in 2023")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index "
                 "(0–100)")
    ctx.pending(ax)
    _pending(ig, ax, "Transparency International's workbook answers\n"
             "403 to this network (2026-10-24). Retry at fetch time;\n"
             "no proxy is substituted.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn, year-end)")
    ry, rv = _yr(ctx, "world/reserves.csv", "reserves_usd")
    rb = [v / 1e9 for v in rv]
    ctx.line(ax, ry, rb, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rb, p.TEAL, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, f"US${_at(ry, rb, 2021):,.0f}bn in 2021 —\n"
          f"US${_at(ry, rb, ry[-1]):,.0f}bn in {ry[-1]}: the wartime build-up")
    _foot(p, ax, "World Bank (the NBU's reserves, year-end)")
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    wy, wv = _yr(ctx, "demography/population.csv", "population")
    uy, uv = _yr(ctx, "demography/population_ukrstat.csv", "population")
    wi_y, wi_v = ctx.index_2006(dict(zip(wy, wv)))
    ui_y, ui_v = ctx.index_2006(dict(zip(uy, uv)))
    ctx.line(ax, ui_y, ui_v, p.GOLD, label="Ukrstat register (excl. TOT "
             "from 2015)")
    ctx.line(ax, wi_y, wi_v, p.BLUE, label="World Bank (UN WPP, incl. Crimea)")
    ig.add_recessions(ax, label=False)
    ax.axvline(2015, color=p.FAINT, lw=0.9, ls=":", zorder=2)
    ax.annotate("2015: the register drops\nthe occupied territories",
                xy=(2015, 100), xytext=(2007.4, 78),
                fontsize=7.8, color=p.MUTED, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    _note(p, ax, 0.02, 0.96, f"{_at(uy, uv, 2021) / 1e6:.1f}m registered in "
          f"2021, {_at(wy, wv, 2021) / 1e6:.1f}m on the UN estimate")
    _foot(p, ax, "Two perimeters, two lines. Never spliced")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    ctx.pending(ax)
    _pending(ig, ax, "Ukrstat's fertility dataflow is cached but its\n"
             "dimension code list does not identify the total-births\n"
             "series unambiguously — not yet definition-checked.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    ctx.pending(ax)
    _pending(ig, ax, "Births and deaths are published by Ukrstat to 2022;\n"
             "the routing is pending with the same code-list check.\n"
             "Holes are not filled.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net migration (per 1,000 people)")
    ctx.pending(ax)
    _pending(ig, ax, "Wartime displacement is measured by UNHCR and IOM,\n"
             "not in a residence register: no comparable official\n"
             "net-migration series is staged.")
    _foot(p, ax, "SOURCES.yaml meta.pending")
    _finish(ctx, ig)


# ------------------------------------------------------------------ people
def plate_people(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100)")
    gy, gv = _yr(ctx, "people/gini.csv", "gini")
    ctx.line(ax, gy, gv, p.PURPLE)
    ctx.endlabel(ax, gy, gv, p.PURPLE, lambda v: f"{v:.1f}", dy=-14)
    _note(p, ax, 0.02, 0.96, f"{_at(gy, gv, 2015):.1f} in 2015, "
          f"{gv[-1]:.1f} in {gy[-1]} —\nthe household survey stopped with "
          "the invasion", size=7.8)
    _foot(p, ax, "World Bank (Ukrstat household survey). No 2022+ value")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    ctx.pending(ax)
    _pending(ig, ax, "The household survey that measures poverty has not\n"
             "published since 2021; the wartime rate is modelled by\n"
             "others and is not an official statistic.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    ctx.pending(ax)
    _pending(ig, ax, "The statutory minimum is set in hryvnia (8,647 UAH\n"
             "from 2026); no official monthly US$ series is staged, and\n"
             "the law portal does not answer from here.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("people.lens", "What the hryvnia buys — the price level "
                 "since 2006 (index 2006 = 100)")
    cy, cv = _yr(ctx, "macro/economy.csv", "cpi_inflation_pct")
    level, run = [], 100.0
    for v in cv:
        run *= 1 + v / 100
        level.append(run)
    ctx.line(ax, cy, level, p.ALERT)
    ig.add_recessions(ax, label=False)
    # No end label: at the right edge it clips; the note carries the value.
    _note(p, ax, 0.02, 0.96, f"prices {level[-1] / 100:.1f}× the 2006 level "
          f"by {cy[-1]} —\nchained from the annual CPI, one vintage")
    _foot(p, ax, "Derived: annual CPI chained from 2006. Not a published "
          "index")
    _finish(ctx, ig)


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Economy — a War-Shrunk Output and a Long Inflation",
         filename="01-economy"),
    dict(id="02", slug="world", topic="world", builder=plate_world,
         title="Ukraine in the World — Size, Development and Reserves",
         filename="02-world"),
    dict(id="03", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — Two Perimeters, and the Line Between Them",
         filename="03-demography"),
    dict(id="04", slug="people", topic="people", builder=plate_people,
         title="People — Inequality Before the War, and What the Hryvnia Buys",
         filename="04-people"),
)
