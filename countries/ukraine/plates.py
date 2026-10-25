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


# ------------------------------------------------------------------ fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p
    F = "fiscal/fiscal.csv"

    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure "
                 "(% of GDP)")
    ry, rv = _yr(ctx, F, "revenue_pct_gdp")
    ey, ev = _yr(ctx, F, "expenditure_pct_gdp")
    ctx.line(ax, ry, rv, p.TEAL, label="Revenue")
    ctx.line(ax, ey, ev, p.ALERT, label="Expenditure")
    ig.add_recessions(ax, label=False)
    peak = max(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(6, 2), ha="left",
                fontsize=8.8, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, f"the war budget: expenditure "
          f"{_at(ey, ev, 2023):.1f}% of GDP in 2023\nagainst revenue of "
          f"{_at(ry, rv, 2023):.1f}%")
    _foot(p, ax, "IMF WEO (October 2026 vintage), general government. One "
          "vintage for every fiscal panel")

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    by, bv = _yr(ctx, F, "balance_pct_gdp")
    py, pv = _yr(ctx, F, "primary_balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.ALERT if v < 0 else p.GREEN)
    ctx.line(ax, py, pv, p.NAVY, label="Primary balance")
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{_at(by, bv, 2023):.1f}%", (2023, _at(by, bv, 2023)),
                textcoords="offset points", xytext=(0, -2), ha="center",
                va="top", fontsize=8.6, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, f"{_at(by, bv, 2023):.1f}% in 2023 — the "
          f"overall balance,\nprimary {_at(py, pv, 2023):.1f}% after interest")
    _foot(p, ax, "IMF WEO. The primary balance is the overall balance "
          "before interest paid")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    dy, dv = _yr(ctx, F, "debt_pct_gdp")
    ctx.line(ax, dy, dv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.PURPLE, lambda v: f"{v:.0f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{_at(dy, dv, 2015):.0f}% after the 2014-15 "
          f"crisis,\n{_at(dy, dv, 2021):.0f}% in 2021, {dv[-1]:.0f}% in {dy[-1]}")
    _foot(p, ax, "IMF WEO general government gross debt")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    iy, iv = _yr(ctx, F, "interest_pct_gdp")
    ctx.line(ax, iy, iv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.GOLD, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{iv[-1]:.1f}% of GDP in {iy[-1]} —\nthe "
          "cost of the debt, before any reconstruction")
    _foot(p, ax, "IMF WEO")
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
def plate_trade(ctx, ig) -> None:
    p = ctx.p
    T = "trade/trade.csv"

    ax = ig.slot("trade.exports_imports", "Exports and imports (% of GDP)")
    xy, xv = _yr(ctx, T, "exports_pct_gdp")
    my, mv = _yr(ctx, T, "imports_pct_gdp")
    ctx.line(ax, xy, xv, p.BLUE, label="Exports")
    ctx.line(ax, my, mv, p.ALERT, label="Imports")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"imports {_at(my, mv, 2025):.1f}% of GDP in "
          f"2025\nagainst exports of {_at(xy, xv, 2025):.1f}%")
    _foot(p, ax, "World Bank national accounts, goods and services")

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    ex, im = dict(zip(xy, xv)), dict(zip(my, mv))
    by = [y for y in xy if y in im]
    bv = [ex[y] - im[y] for y in by]
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{bv[-1]:.1f}%", (by[-1], bv[-1]), textcoords="offset points",
                xytext=(0, -2), ha="center", va="top", fontsize=8.6,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, "the gap widens with the war:\n"
          "a goods deficit carried by services before it")
    _foot(p, ax, "Derived: exports minus imports, same World Bank series")

    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    ctx.pending(ax)
    _pending(ig, ax, "No annual partner series is staged: the customs\n"
             "service answers 403, and the 2023 UN Comtrade snapshot is\n"
             "a single year, not the slot's time series.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("trade.lens", "Top goods-export destinations, 2023 "
                 "(% of goods exports, one year)")
    t = ctx.table("trade/partners_2023.csv")
    if t and "partner" in t:
        # The file has no year column; the column order is the fetcher's
        # ranking, kept as written.
        names = list(t["partner"])
        shares = [float(v) for v in t["share_pct"]]
        ypos = list(range(len(names)))[::-1]
        ax.barh(ypos, shares, color=[p.BLUE if n != "Rest of the world"
                                     else p.FAINT for n in names])
        ax.set_yticks(ypos)
        ax.set_yticklabels(names, fontsize=7.6)
        for y, v in zip(ypos, shares):
            ax.text(v + 0.6, y, f"{v:.1f}%", va="center", fontsize=7.4,
                    color=p.MUTED)
        ax.tick_params(axis="y", length=0)
        ax._categorical_x = True
        ax._lens_xlim = (0, max(shares) * 1.18)
    _foot(p, ax, "UN Comtrade, Ukraine as reporter, 2023 — one year; the "
          "annual series the canonical slot needs is not on an official feed")
    _finish(ctx, ig)
    # style_axis resets every x axis to the country's year window; this lens
    # is categorical, so its own scale goes back after the styling.
    if hasattr(ax, "_lens_xlim"):
        ax.set_xlim(*ax._lens_xlim)
        ax.set_xticks([0, 10, 20, 30, 40, 50, 60])


# ----------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ky, kv = _yr(ctx, "markets/key_rate.csv", "policy_rate_pct")
    cy, cv = _yr(ctx, "macro/economy.csv", "cpi_inflation_pct")
    ctx.line(ax, ky, kv, p.NAVY, label="NBU key rate")
    ctx.line(ax, cy, cv, p.ALERT, label="Inflation")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"the key rate averaged "
          f"{_at(ky, kv, 2025):.1f}% in 2025;\ninflation "
          f"{_at(cy, cv, 2022):.1f}% in 2022")
    _foot(p, ax, "NBU key policy rate (annual mean of the daily rate) and the "
          "Ukrstat CPI")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    ctx.pending(ax)
    _pending(ig, ax, "No continuous official hryvnia 10-year series is\n"
             "staged: the pre-2022 domestic market was thin and short-\n"
             "dated, and the NBU API carries no yield curve.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("markets.currency", "Currency against the US$ "
                 "(index 2006 = 100, up = stronger)")
    fy, fv = _yr(ctx, "markets/usd_uah.csv", "uah_per_usd")
    base = _at(fy, fv, 2006)
    iy, iv = ctx.fx_index(dict(zip(fy, fv)))
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.TEAL, lambda v: f"{v:.0f}", dy=8)
    _note(p, ax, 0.98, 0.96, f"the hryvnia fell from {base:.2f} per dollar "
          f"in 2006\nto {_at(fy, fv, 2025):.2f} in 2025", ha="right")
    _foot(p, ax, "NBU official rate, annual mean of the daily rate")

    ax = ig.slot("markets.equities", "Main equity index in US$ "
                 "(index 2006 = 100, in US$)")
    ctx.pending(ax)
    _pending(ig, ax, "Trading was suspended from 24 February 2022 and the\n"
             "index is not published on an official machine feed;\n"
             "no unofficial redistributor is substituted.")
    _foot(p, ax, "SOURCES.yaml meta.pending")
    _finish(ctx, ig)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    hy, hv = _yr(ctx, "security/security.csv", "homicide_per_100k")
    ctx.line(ax, hy, hv, p.ALERT)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, hy, hv, p.ALERT, lambda v: f"{v:.1f}", dy=8)
    _note(p, ax, 0.02, 0.96, f"{hv[0]:.1f} in {hy[0]}, {hv[-1]:.1f} in "
          f"{hy[-1]} —\nthe UNODC series stops before the invasion")
    _foot(p, ax, "UNODC via the World Bank. No 2022+ value")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    sy, sv = _yr(ctx, "security/security.csv", "suicide_per_100k")
    ctx.line(ax, sy, sv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, sy, sv, p.PURPLE, lambda v: f"{v:.1f}", dy=-14)
    _note(p, ax, 0.02, 0.96, f"{sv[0]:.1f} in {sy[0]} — one of the highest\n"
          f"rates in the window; {sv[-1]:.1f} in {sy[-1]}")
    _foot(p, ax, "WHO via the World Bank. No 2022+ value")

    ax = ig.slot("security.road_deaths", "Road traffic deaths "
                 "(per 100,000)")
    ry, rv = _yr(ctx, "security/security.csv", "road_deaths_per_100k")
    ctx.line(ax, ry, rv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.GOLD, lambda v: f"{v:.1f}", dy=8)
    _note(p, ax, 0.02, 0.96, f"{rv[0]:.1f} in {ry[0]} to {rv[-1]:.1f} in "
          f"{ry[-1]};\nthe WHO series stops there")
    _foot(p, ax, "WHO via the World Bank")
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    M = "mortality/mortality.csv"

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000 people)")
    dy, dv = _yr(ctx, M, "death_rate_per_1000")
    ctx.line(ax, dy, dv, p.INK)
    ig.add_recessions(ax, label=False)
    peak = max(zip(dy, dv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f} in {peak[0]}", peak,
                textcoords="offset points", xytext=(6, 2), ha="left",
                fontsize=8.8, fontweight="bold", color=p.INK)
    _note(p, ax, 0.02, 0.96, f"{dv[0]:.1f} in {dy[0]}, {dv[-1]:.1f} in "
          f"{dy[-1]};\n{_at(dy, dv, 2021):.1f} in 2021")
    _foot(p, ax, "World Bank (Ukrstat vital registration)")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above 2015–2019 average)")
    ctx.pending(ax)
    _pending(ig, ax, "Excess deaths need the registered-death count, not\n"
             "the rate: Ukrstat's deaths dataflow is cached but its\n"
             "dimension code list is not yet pinned, so no count is drawn.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    ctx.pending(ax)
    _pending(ig, ax, "WHO's COVID-19 series answers from a redirect that\n"
             "does not resolve here, and no official Ukrainian\n"
             "underlying-cause file is staged.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("mortality.lens", "Life expectancy at birth (years)",
                 unit=False)
    ly, lv = _yr(ctx, M, "life_expectancy")
    ctx.line(ax, ly, lv, p.TEAL)
    ig.add_recessions(ax, label=False)
    # No end label: at the right edge it clips; the note carries the value.
    _note(p, ax, 0.02, 0.96, f"{lv[0]:.1f} years in {ly[0]}, {lv[-1]:.1f} "
          f"in {ly[-1]};\nthe 2021 dip is the war's first year")
    _foot(p, ax, "World Bank (UN WPP life tables)")
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
SPEND_FUNCS = [
    ("general_public_services_million_uah", "AZURE"),
    ("defence_million_uah", "ALERT"),
    ("public_order_safety_judiciary_million_uah", "NAVY"),
    ("economic_affairs_million_uah", "TEAL"),
    ("environment_million_uah", "GREEN"),
    ("housing_community_million_uah", "GOLD"),
    ("health_million_uah", "PURPLE"),
    ("culture_recreation_religion_million_uah", "BLUE_D"),
    ("education_million_uah", "BLUE"),
    ("social_protection_million_uah", "GREEN_D"),
]
SPEND_FILE = "fiscal/treasury_functional.csv"


def _gdp(ctx):
    t = ctx.table("macro/gdp_uah.csv")
    return dict(zip(*ctx.series(t, "gdp_uah"))) if t else {}


def _spend_share(ctx):
    """The Treasury's functional outturn as % of GDP, year by year.

    The dataset's `year` is the execution year: the NBU's January-1 stamp
    (20240101) carries 2023 (PR #6's finding, checked against the MoF
    annual workbook). The column names are the publisher's.
    """
    t = ctx.table(SPEND_FILE)
    gdp = _gdp(ctx)
    out = {name: {} for name, _ in SPEND_FUNCS}
    out["total"] = {}
    out["capital"] = {}
    if not t:
        return out, []
    for name in [n for n, _ in SPEND_FUNCS] + ["total_million_uah",
                                               "capital_million_uah"]:
        if name not in t:
            continue
        ys, vs = ctx.series(t, name)
        key = {"total_million_uah": "total",
               "capital_million_uah": "capital"}.get(name, name)
        for y, v in zip(ys, vs):
            if y in gdp and gdp[y] and v:
                out[key][y] = v * 1e6 / gdp[y] * 100
    return out, sorted(out["total"])


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    shares, years = _spend_share(ctx)

    ax = ig.slot("spending.by_function",
                 "Spending by function, stacked (% of GDP)")
    layers = [([shares[name][y] for y in years], getattr(p, color))
              for name, color in SPEND_FUNCS]
    labels = ["state administration", "defence", "public order",
              "economic activity", "environment", "housing", "health",
              "culture and sport", "education", "social protection"]
    ax.stackplot(years, *[v for v, _ in layers], labels=labels,
                 colors=[c for _, c in layers], alpha=0.9, lw=0)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=6.4, ncol=3, frameon=False)
    tot = [shares["total"][y] for y in years]
    ax.annotate(f"{tot[-1]:.1f}% of GDP ({years[-1]})", (years[-1], tot[-1]),
                textcoords="offset points", xytext=(-4, 8), ha="right",
                fontsize=8.2, fontweight="bold", color=p.INK)
    _note(p, ax, 0.98, 0.55, f"defence took {shares['defence_million_uah'][2023]:.0f}% "
          f"of GDP in 2023,\nup from {shares['defence_million_uah'][2021]:.1f}% "
          "in 2021", ha="right")
    _foot(p, ax, "Treasury consolidated budget, cash basis (NBU). Not the "
          "IMF accrual layer")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    soc = [shares["social_protection_million_uah"][y] for y in years]
    rest = [t - s for t, s in zip(tot, soc)]
    ctx.line(ax, years, rest, p.NAVY, label="Everything else")
    ctx.line(ax, years, soc, p.ALERT, label="Social protection")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="center right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.55, f"social protection {soc[0]:.1f}% of GDP in "
          f"{years[0]},\n{soc[-1]:.1f}% in {years[-1]} — the war squeezed "
          "everything else")
    _foot(p, ax, "Same series, two groups: the function and the remainder")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(% of GDP)")
    iy, iv = _yr(ctx, "macro/economy.csv", "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.TEAL, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{iv[-1]:.1f}% in {iy[-1]} —\nwhole-economy "
          "fixed investment, not the budget")
    _foot(p, ax, "World Bank national accounts (GFCF)")

    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    capital = [shares["capital"][y] for y in years if y in shares["capital"]]
    cy = [y for y in years if y in shares["capital"]]
    ctx.line(ax, cy, capital, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, cy, capital, p.GOLD, lambda v: f"{v:.1f}%", dy=-14)
    _note(p, ax, 0.98, 0.96, "capital expenditure of the consolidated\n"
          "budget — the closest official public-investment line", ha="right")
    _foot(p, ax, "Treasury capital expenditure ÷ GDP")
    _finish(ctx, ig)


def plate_migration(ctx, ig) -> None:
    p = ctx.p
    M = "migration/migration.csv"

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    ctx.pending(ax)
    _pending(ig, ax, "Ukrstat's migration dataflow is cached but its\n"
             "dimension code list is not pinned; UNHCR displacement is\n"
             "not a residence-register flow and is not substituted.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    t = ctx.table(M)
    yrs, vals = ctx.series(t, "net_migration")
    pop = dict(zip(*ctx.series(t, "population")))
    per = [(y, v / pop[y] * 1000) for y, v in zip(yrs, vals)
           if y in pop and y <= 2021]
    ctx.line(ax, [y for y, _ in per], [v for _, v in per], p.BLUE)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{per[-1][1]:+.1f}", per[-1], textcoords="offset points",
                xytext=(-4, 8), ha="right", fontsize=8.6,
                fontweight="bold", color=p.BLUE)
    _note(p, ax, 0.02, 0.96, "the UN/WB estimate to 2021: the wartime\n"
          "displacement is in the lens, on its own scale")
    _foot(p, ax, "World Bank (UN WPP) net migration ÷ mid-year population")

    ax = ig.slot("migration.foreign_born", "Foreign-born share of the "
                 "population (%)")
    fy, fv = [], []
    stock = dict(zip(*ctx.series(t, "migrant_stock"))) if "migrant_stock" in t else {}
    for y in sorted(stock):
        if stock[y] and y in pop:
            fy.append(y)
            fv.append(stock[y] / pop[y] * 100)
    ctx.line(ax, fy, fv, p.PURPLE)
    ctx.endlabel(ax, fy, fv, p.PURPLE, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{fv[0]:.1f}% in {fy[0]}, {fv[-1]:.1f}% in "
          f"{fy[-1]};\nsnapshot years only — the stock is a UN estimate")
    _foot(p, ax, "World Bank (UN DESA migrant stock) ÷ population")

    ax = ig.slot("migration.lens", "Wartime displacement — net migration, "
                 "persons per 1,000 (own scale)")
    wy, wv = [], []
    for y, v in zip(yrs, vals):
        if y >= 2022 and y in pop:
            wy.append(y)
            wv.append(v / pop[y] * 1000)
    ctx.bars(ax, wy, wv, lambda v: p.ALERT if v < 0 else p.GREEN)
    worst = min(zip(wy, wv), key=lambda t: t[1])
    best = max(zip(wy, wv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, f"{worst[1]:+.0f} per 1,000 in {worst[0]} — "
          f"outside the comparable\nslot's range on purpose: a war is not a "
          f"migration rate; {best[1]:+.0f} in {best[0]}")
    _foot(p, ax, "World Bank (UN WPP) — modelled, includes refugees abroad")
    _finish(ctx, ig)


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Economy — a War-Shrunk Output and a Long Inflation",
         filename="01-economy"),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — The War Budget and the Debt It Leaves",
         filename="02-fiscal"),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Spending — The War Budget, Function by Function",
         filename="03-spending"),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — A Widening Gap Where the Surplus Used to Be",
         filename="04-trade"),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Markets — The Key Rate, Inflation and the Hryvnia",
         filename="05-markets"),
    dict(id="06", slug="people", topic="people", builder=plate_people,
         title="People — Inequality Before the War, and What the Hryvnia Buys",
         filename="06-people"),
    dict(id="07", slug="world", topic="world", builder=plate_world,
         title="Ukraine in the World — Size, Development and Reserves",
         filename="07-world"),
    dict(id="08", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — Two Perimeters, and the Line Between Them",
         filename="08-demography"),
    dict(id="09", slug="security", topic="security", builder=plate_security,
         title="Security — Homicide, Suicide and the Road",
         filename="09-security"),
    dict(id="10", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — The Death Rate and the Years Lost in 2021",
         filename="10-mortality"),
    dict(id="11", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — The Register's Hole and the Wartime Displacement",
         filename="11-migration"),
)
