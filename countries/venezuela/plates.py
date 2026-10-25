"""The Venezuela plates, on the plate spine.

Eleven chapters: the economy, the public books, what the state spends, trade,
markets, people and prices, the country among the others, demography,
security, mortality and the exodus. Every canonical slot is either drawn from
the committed CSVs or visibly pending with the route that failed, and the two
series that leave their shared ranges on purpose — the hyperinflation and the
emigration wave — are drawn in lens panels on their own scales, labelled.

Three things this country makes unavoidable:

* **The publishers are harmonised, not national.** The Central Bank's site
  does not answer over TLS from this network, the INE publishes no CPI and no
  national accounts, and what is left is the IMF's staff estimate and the
  World Bank's compilation of it. Every panel says which kind of number it
  draws; where the two disagree they are two labelled lines, never one.
* **The bolívar was redenominated three times.** No local-currency level is
  drawn anywhere: money is a share of GDP, US$ or an index, and the one series
  that crosses a redenomination — the official exchange rate — is converted
  through the documented divisor in DATA_NOTES.md and stops where the
  publisher stops (2017).
* **Some holes are structural.** Homicide has no UNODC observation for 2013
  or 2018, the reserves stop in 2017, the official rate stops in 2017. The
  panels keep those holes open; they are never zero, never carried forward.
"""
from __future__ import annotations

from matplotlib import ticker as mticker

from core import spine
from core.sideload import sibling

events = sibling(__file__, "events")

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


def _gapped(ctx, rel: str, col: str):
    """(years, values) with the blanks kept as NaN, so a hole stays a hole.

    `ctx.line` drops empty years, which draws a straight segment across them:
    right for a series that starts late, wrong for one that is missing in the
    middle. Homicide is missing in 2013 and 2018 and the panel must show it.
    """
    t = ctx.table(rel)
    if not t:
        return [], []
    return list(t.get("year", [])), list(t.get(col, []))


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
            ig.style_axis(a, xticks_years=not getattr(a, "_categorical_x",
                                                     False))


def _log_ladder(ax, ticks, lo, hi, fmt=None):
    """A lens on its own log scale, with the ticks written as plain numbers.

    A canonical log slot gets this from `core.spine`; a lens has no shared
    range, so the panel sets its own — and says so in its title.
    """
    ax.set_yscale("log")
    ax.set_ylim(lo, hi)
    ax.yaxis.set_major_locator(mticker.FixedLocator(list(ticks)))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt or spine.tick_label))
    ax.yaxis.set_minor_locator(mticker.NullLocator())


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p
    E = "macro/economy.csv"

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    wy, wv = _yr(ctx, E, "gdp_growth_pct_wb")
    iy, iv = _yr(ctx, E, "gdp_growth_pct_imf")
    ctx.bars(ax, wy, wv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ctx.line(ax, iy, iv, p.NAVY, label="IMF WEO (staff estimate)")
    ig.add_recessions(ax, inside=True)
    ax.annotate(f"{_at(iy, iv, 2020):.1f}%", (2020, _at(iy, iv, 2020)),
                textcoords="offset points", xytext=(7, 8), ha="left",
                va="bottom", fontsize=8.8, fontweight="bold", color=p.NAVY)
    _note(p, ax, 0.02, 0.96, "two staff estimates of a rebased series, never "
          "one line:\n"f"the Bank's bars ({_at(wy, wv, 2020):.1f}% in 2020), "
          f"the Fund's line ({_at(iy, iv, 2020):.1f}%), the same sign every "
          "year")
    _foot(p, ax, "World Bank NY.GDP.MKTP.KD.ZG (bars) and IMF WEO NGDP_RPCH "
          "(line). Venezuela submits no national accounts: both are estimates")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "world/gdp_per_person.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE, label="GDP per person, World Bank")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=-14)
    _note(p, ax, 0.02, 0.96, f"US$ at market rates: {_at(py, pv, 2010):,.0f} "
          f"in 2010,\n{_at(py, pv, 2025):,.0f} in 2025 — nominal, converted "
          "at the official rate of each year")
    _foot(p, ax, "World Bank, current US$, over the UN mid-year population")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year)")
    ctx.pending(ax)
    _pending(ig, ax, "65,374% in 2018 and 19,906% in 2019 cannot share a\n"
             "linear comparable scale. The series is not clipped: it is\n"
             "drawn in the prices lens on a log axis, labelled by source.")
    _foot(p, ax, "IMF WEO PCPIPCH, a staff estimate — see plate 06")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    uy, uv = _yr(ctx, E, "unemployment_pct_ilo")
    my, mv = _yr(ctx, E, "unemployment_pct_imf")
    ctx.line(ax, uy, uv, p.TEAL, label="ILO modelled estimate")
    ctx.line(ax, my, mv, p.NAVY, label="IMF WEO (national definition)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96, f"{uv[-1]:.1f}% in {uy[-1]}: the ILO model of a\n"
          "labour market whose own survey has no legible code list")
    _foot(p, ax, "World Bank (ILO modelled), 2006–2025; IMF WEO LUR, "
          "2006–2018")
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    ty = ctx.table("world/gdp_usd.csv")
    wy, wv = ctx.series(ty, "gdp_usd_bn_wb")
    iy, iv = ctx.series(ty, "gdp_usd_bn_imf")
    ctx.line(ax, wy, wv, p.BLUE, label="World Bank (official rate of record)")
    ctx.line(ax, iy, iv, p.GOLD, label="IMF WEO")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.6, frameon=False)
    _note(p, ax, 0.98, 0.96, f"US${_at(wy, wv, 2010):,.0f}bn in 2010 and "
          f"US${_at(wy, wv, 2020):,.0f}bn in 2020;\nthe gap between the lines "
          "is which official rate each used", ha="right")
    _foot(p, ax, "World Bank NY.GDP.MKTP.CD and IMF WEO NGDPD. Nominal: the "
          "fall is the collapse and the exchange rate together")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "world/hdi.csv", "hdi")
    ctx.line(ax, hy, hv, p.GREEN, label="HDI (UNDP)")
    ctx.endlabel(ax, hy, hv, p.GREEN, lambda v: f"{v:.3f}", dy=8)
    _note(p, ax, 0.02, 0.96, f"{_at(hy, hv, 2013):.3f} at the 2013 peak, "
          f"{hv[-1]:.3f} in {hy[-1]} —\none HDR vintage (2025) for the whole "
          "back-series")
    _foot(p, ax, "UNDP HDR 2025. The series stops in 2023")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (score, 0–100)")
    ctx.pending(ax)
    _pending(ig, ax, "Transparency International's workbook answers 403\n"
             "to this network (2026-10-25), the same block the Ukraine\n"
             "lane found. No proxy is substituted.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn, year-end)")
    ry, rv = _yr(ctx, "world/reserves.csv", "reserves_usd_bn")
    ctx.line(ax, ry, rv, p.TEAL, label="Reserves (World Bank)")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.TEAL, lambda v: f"US${v:,.0f}bn", dy=-14)
    _note(p, ax, 0.02, 0.96, f"US${_at(ry, rv, 2008):,.0f}bn at the 2008 "
          "peak —\nUS$9.8bn in 2017, where the Central Bank stopped reporting")
    _foot(p, ax, "World Bank FI.RES.TOTL.CD (the BCV's series). 2018–2025 are "
          "holes: the BCV is unreachable")
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p
    V = "demography/vital.csv"

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    wy, wv = _yr(ctx, "demography/population.csv", "population")
    iy, iv = ctx.index_2006(dict(zip(wy, wv)))
    ctx.line(ax, iy, iv, p.BLUE, label="Population index (UN WPP)")
    ig.add_recessions(ax, label=False)
    ax.axhline(100, color=p.FAINT, lw=0.8, ls=":")
    ax.annotate(f"{_at(iy, iv, 2016):.0f}", (2016, _at(iy, iv, 2016)),
                textcoords="offset points", xytext=(0, 7), ha="center",
                va="bottom", fontsize=8.6, fontweight="bold", color=p.BLUE)
    _note(p, ax, 0.02, 0.96, f"{_at(wy, wv, 2016) / 1e6:.1f}m at the 2016 "
          f"peak,\n{wv[-1] / 1e6:.1f}m in {wy[-1]} — modelled "
          "emigration, not a census count")
    _foot(p, ax, "World Bank SP.POP.TOTL (UN WPP), mid-year, whole territory. "
          "No census since 2011")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    fy, fv = _yr(ctx, V, "fertility_rate")
    ctx.line(ax, fy, fv, p.PURPLE, label="Fertility (UN WPP)")
    ctx.endlabel(ax, fy, fv, p.PURPLE, lambda v: f"{v:.2f}", dy=-14)
    ax.axhline(2.1, color=p.FAINT, lw=0.8, ls=":")
    _note(p, ax, 0.02, 0.30, f"{fv[0]:.2f} in {fy[0]} to {fv[-1]:.2f} in "
          f"{fy[-1]}; the dotted line is\nreplacement, 2.1 — modelled by the "
          "UN, not registered births")
    _foot(p, ax, "World Bank SP.DYN.TFRT.IN (UN WPP). The INE's birth "
          "tabulados are legacy .xls and not staged")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    by, bv = _yr(ctx, V, "birth_rate_per_1000")
    dy, dv = _yr(ctx, V, "death_rate_per_1000")
    ctx.line(ax, by, bv, p.GREEN, label="Births")
    ctx.line(ax, dy, dv, p.ALERT, label="Deaths")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="center right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.60, f"births {bv[-1]:.1f} and deaths {dv[-1]:.1f} "
          f"per 1,000 in {by[-1]} —\nthe gap is still open, but it closed by "
          "half in twenty years")
    _foot(p, ax, "World Bank SP.DYN.CBRT.IN / SP.DYN.CDRT.IN (UN WPP), one "
          "vintage")

    ax = ig.slot("demography.natural_migration",
                 "Natural increase (births − deaths, per 1,000)")
    ni = [b - d for b, d in zip(bv, dv)]
    ctx.bars(ax, by, ni, lambda v: p.TEAL if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{ni[0]:.1f}", (by[0], ni[0]), textcoords="offset points",
                xytext=(0, 6), ha="center", va="bottom", fontsize=8.4,
                fontweight="bold", color=p.TEAL)
    _note(p, ax, 0.02, 0.96, "net migration leaves this scale: −45 per 1,000 "
          "in 2018.\nIt is drawn on the migration plate, on its own axis, "
          "not folded in here")
    _foot(p, ax, "Derived: birth rate minus death rate, the same UN WPP "
          "vintage. Not a register count")
    _finish(ctx, ig)


# ------------------------------------------------------------------ people
def plate_people(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100 points)")
    gy, gv = _yr(ctx, "people/gini.csv", "gini")
    ctx.line(ax, gy, gv, p.PURPLE, label="Gini, INE survey")
    ctx.endlabel(ax, gy, gv, p.PURPLE, lambda v: f"{v:.1f}", dy=-14)
    _note(p, ax, 0.02, 0.96, f"{_at(gy, gv, 2006):.1f} in 2006, {gv[-1]:.1f} "
          f"in {gy[-1]} —\nflat through the collapse: the publisher's claim, "
          "not this atlas's", size=7.8)
    _foot(p, ax, "INE household-survey Gini (0–1 in the workbook, ×100 here). "
          "Coverage and non-response are undocumented")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    ctx.pending(ax)
    _pending(ig, ax, "The World Bank's PIP series ends in 2006; the INE\n"
             "publishes no poverty tabulado. ENCOVI is a university\n"
             "survey, not an official statistic, and is not substituted.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    ctx.pending(ax)
    _pending(ig, ax, "Set in bolívares across three redenominations; the\n"
             "official rate that would convert it to US$ stops in 2017,\n"
             "and the Gaceta's publisher does not resolve in DNS.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("people.lens", "Prices — consumer inflation on its own "
                 "scale (%, log axis)")
    iy, iv = _yr(ctx, "macro/economy.csv", "cpi_inflation_pct_imf")
    by, bv = _yr(ctx, "macro/economy.csv", "cpi_inflation_pct_bcv")
    ctx.line(ax, iy, iv, p.ALERT, label="IMF WEO, staff estimate")
    ctx.line(ax, by, bv, p.NAVY, label="BCV INPC (via the World Bank)")
    ig.add_recessions(ax, label=False)
    _log_ladder(ax, (10, 30, 100, 300, 1_000, 3_000, 10_000, 30_000, 100_000),
                10, 100_000)
    ax.set_ylabel("%, log scale", fontsize=8.6, color=p.MUTED)
    peak = max(zip(iy, iv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:,.0f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(-6, -6), ha="right",
                va="top", fontsize=8.6, fontweight="bold", color=p.ALERT)
    ax.legend(loc="center left", fontsize=7.2, frameon=False)
    _note(p, ax, 0.02, 0.72, "a log axis, because a hyperinflation has no\n"
          "comparable linear scale: the canonical slot is left pending")
    _foot(p, ax, "IMF WEO PCPIPCH (2006–2025) and the BCV's INPC as the World "
          "Bank republishes it (2009–2016): two lines, never joined")
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
    ax.legend(loc="center right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96, f"2018: revenue {_at(ry, rv, 2018):.1f}% of GDP "
          f"against\nexpenditure {_at(ey, ev, 2018):.1f}% — the state that "
          "stopped collecting")
    _foot(p, ax, "IMF WEO (October 2026), general government. One vintage for "
          "every fiscal panel; no projection past 2025")

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    by, bv = _yr(ctx, F, "balance_pct_gdp")
    py, pv = _yr(ctx, F, "primary_balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.ALERT if v < 0 else p.GREEN)
    ctx.line(ax, py, pv, p.NAVY, label="Primary balance")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.6, frameon=False)
    ax.annotate(f"{_at(by, bv, 2018):.1f}%", (2018, _at(by, bv, 2018)),
                textcoords="offset points", xytext=(-2, -4), ha="right",
                va="top", fontsize=8.4, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.98, 0.96, f"{_at(by, bv, 2018):.1f}% in 2018 — the overall "
          f"balance,\nprimary {_at(py, pv, 2018):.1f}% on the Fund's own "
          "definition", ha="right")
    _foot(p, ax, "IMF WEO GGXCNL_NGDP and the primary balance it publishes "
          "beside it")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, "GGXWDG_NGDP has no Venezuelan observation in the\n"
             "October 2026 vintage, the World Bank's debt indicator returns\n"
             "zero rows, and the BCV is unreachable. Not a zero: a hole.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    iy, iv = _yr(ctx, F, "interest_pct_gdp")
    ctx.line(ax, iy, iv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.GOLD, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{iv[-1]:.1f}% of GDP in {iy[-1]} —\nthe one "
          "line the collapse eased, by shrinking the debt it was paid on")
    _foot(p, ax, "IMF WEO (interest paid, general government)")
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
def plate_spending(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("spending.by_function",
                 "Spending by function, stacked (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, "Venezuela reports no COFOG table to the IMF, and the\n"
             "finance ministry's functional budget stops in 2009 — in\n"
             "nominal bolívares of three different currencies.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, "Same COFOG route as the panel beside it: there is no\n"
             "functional breakdown to divide into a social-protection\n"
             "line and a remainder. Nothing is invented to fill it.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(% of GDP)")
    iy, iv = _yr(ctx, "spending/spending.csv", "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.TEAL, label="Investment rate, whole economy")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.TEAL, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{_at(iy, iv, 2013):.1f}% in 2013, {iv[-1]:.1f}% "
          f"in {iy[-1]} —\nwhat is left of investment after the collapse")
    _foot(p, ax, "World Bank NE.GDI.FTOT.ZS. The series starts in 2012: "
          "2006–2011 are gateway placeholder zeros, dropped")

    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, "Government GFCF is not published on any route tried:\n"
             "no COFOG to the IMF, and the ministry's own capital line\n"
             "ends in 2009. The whole-economy rate is not a substitute.")
    _foot(p, ax, "SOURCES.yaml meta.pending")
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
    ax.legend(loc="center right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96, f"exports {_at(xy, xv, 2019):.1f}% of GDP in "
          f"2019\nagainst imports of {_at(my, mv, 2019):.1f}%")
    _foot(p, ax, "World Bank national accounts, goods and services. The series "
          "starts in 2012 (2006–2011 are placeholder zeros)")

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    by = [y for y in xy if y in dict(zip(my, mv))]
    bv = [dict(zip(xy, xv))[y] - dict(zip(my, mv))[y] for y in by]
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    peak = max(zip(by, bv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:+.1f}%", peak, textcoords="offset points",
                xytext=(-6, 0), ha="right", va="center", fontsize=8.6,
                fontweight="bold", color=p.GREEN)
    _note(p, ax, 0.02, 0.96, "the oil surplus of an economy that had stopped\n"
          "importing — not an export boom")
    _foot(p, ax, "Derived: exports minus imports, the same World Bank series "
          "and vintage")

    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    ctx.pending(ax)
    _pending(ig, ax, "Venezuela's own Comtrade reporting stops after 2013,\n"
             "and that submission puts US$82bn of US$88bn into \"nes\"\n"
             "residual buckets. A chart of a code list is not a chart.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("trade.lens", "Exports and imports in US$ bn (derived)")
    g = dict(zip(*ctx.series(ctx.table("world/gdp_usd.csv"),
                             "gdp_usd_bn_wb")))
    ex, im_ = dict(zip(xy, xv)), dict(zip(my, mv))
    ey = [y for y in xy if y in g and y in im_]
    ev = [ex[y] / 100 * g[y] for y in ey]
    iv_ = [im_[y] / 100 * g[y] for y in ey]
    # Plain ax.plot, not ctx.line: the derived series ends in the country's
    # last full year, so there is no partial tail to dash.
    ax.plot(ey, ev, color=p.BLUE, lw=2.4, marker="o", ms=4.2,
            label="Exports")
    ax.plot(ey, iv_, color=p.ALERT, lw=2.4, marker="o", ms=4.2,
            label="Imports")
    ax.set_ylim(0, max(ev + iv_) * 1.18)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    ax.annotate(f"US${ev[0]:,.0f}bn", (ey[0], ev[0]), textcoords="offset points",
                xytext=(0, 7), ha="left", va="bottom", fontsize=8.6,
                fontweight="bold", color=p.BLUE)
    _note(p, ax, 0.02, 0.55, "the same two ratios times the same vintage's\n"
          "dollar GDP: a level, derived on the plate and stated as derived")
    _foot(p, ax, "Derived: % of GDP × World Bank GDP in current US$. Not a "
          "published dollar series")
    _finish(ctx, ig)
    ax.set_xlim(ctx.YEARS[0] - 0.6, ctx.YEARS[-1] + 0.6)


# ----------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ctx.pending(ax)
    _pending(ig, ax, "The BCV sets the rate and its site does not answer\n"
             "(TLS); the IMF carries no Venezuelan policy-rate indicator.\n"
             "A rate-versus-inflation panel cannot be drawn from one side.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    ctx.pending(ax)
    _pending(ig, ax, "No official bolívar yield curve is published, and the\n"
             "domestic market is thin enough that a secondary-market\n"
             "quote would need its own definition note. Not drawn.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("markets.currency", "Currency against the US$ "
                 "(index 2006 = 100, up = stronger)")
    fy, fv = _yr(ctx, "markets/fx_official.csv", "fx_index_2006_100")
    ctx.line(ax, fy, fv, p.TEAL, label="Official rate, index 2006 = 100")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, fy, fv, p.TEAL, lambda v: f"{v:.1f}", dy=8)
    ig.add_event(ax, *events.MARKS["redenomination"])
    _note(p, ax, 0.02, 0.30, "the official rate, not the parallel market:\n"
          f"{_at(fy, fv, 2006):.0f} in 2006, {fv[-1]:.1f} in {fy[-1]}, where "
          "the publisher stops")
    _foot(p, ax, "World Bank PA.NUS.FCRF, annual mean, 2006–2017 only: the "
          "BCV's own rate is unreachable after that")

    ax = ig.slot("markets.equities", "Main equity index in US$ "
                 "(index 2006 = 100, in US$)")
    ctx.pending(ax)
    _pending(ig, ax, "No verified machine-readable series exists for the\n"
             "Caracas exchange's index, and no redistributor is\n"
             "substituted for a market this thin.")
    _foot(p, ax, "SOURCES.yaml meta.pending")
    _finish(ctx, ig)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    S = "security/security.csv"

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    hy, hv = _gapped(ctx, S, "homicide_per_100k")
    ax.plot(hy, hv, color=p.ALERT, lw=2.4, marker="o", ms=4.2, zorder=3,
            label="UNODC (via the World Bank)")
    ig.add_recessions(ax, label=False)
    peak = max(((y, v) for y, v in zip(hy, hv) if v == v),
               key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f} in {peak[0]}", peak,
                textcoords="offset points", xytext=(-4, 6), ha="right",
                va="bottom", fontsize=8.6, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.26, "2013 and 2018 are holes, not falls: UNODC has\n"
          "no observation there, and the line breaks rather than bridges")
    _foot(p, ax, "UNODC via the World Bank (VC.IHR.PSRC.P5), 2012–2022. The "
          "last years are estimates, not police counts")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    sy, sv = _yr(ctx, S, "suicide_per_100k")
    ctx.line(ax, sy, sv, p.PURPLE, label="Suicide (WHO)")
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{_at(sy, sv, 2016):.1f}", (2016, _at(sy, sv, 2016)),
                textcoords="offset points", xytext=(0, 7), ha="center",
                va="bottom", fontsize=8.4, fontweight="bold", color=p.PURPLE)
    _note(p, ax, 0.98, 0.96, "the 2016 spike from 6.1 to 10.5 and back is a\n"
          "change of WHO estimate vintage, not behaviour", ha="right")
    _foot(p, ax, "WHO via the World Bank. The series stops in 2021")

    ax = ig.slot("security.road_deaths", "Road traffic deaths (per 100,000)")
    ry, rv = _yr(ctx, S, "road_deaths_per_100k")
    ctx.line(ax, ry, rv, p.GOLD, label="Road deaths (WHO)")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.30, f"{rv[0]:.1f} in {ry[0]} to {rv[-1]:.1f} in "
          f"{ry[-1]} —\nthe road got deadlier as the traffic got thinner")
    _foot(p, ax, "WHO via the World Bank. The series stops in 2019")
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    V = "demography/vital.csv"

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000 people)")
    dy, dv = _yr(ctx, V, "death_rate_per_1000")
    ctx.line(ax, dy, dv, p.INK, label="Death rate (UN WPP)")
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{_at(dy, dv, 2021):.2f}", (2021, _at(dy, dv, 2021)),
                textcoords="offset points", xytext=(0, 7), ha="center",
                va="bottom", fontsize=8.4, fontweight="bold", color=p.INK)
    ig.add_event(ax, *events.MARKS["covid"])
    _note(p, ax, 0.02, 0.96, f"{dv[0]:.1f} in {dy[0]}, {dv[-1]:.1f} in "
          f"{dy[-1]}; {_at(dy, dv, 2021):.1f} in 2021,\nthe pandemic year "
          "inside a modelled series")
    _foot(p, ax, "World Bank SP.DYN.CDRT.IN (UN WPP model). The INE's death "
          "counts are legacy .xls and not staged")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above 2015–2019 average)")
    ctx.pending(ax)
    _pending(ig, ax, "Excess deaths need registered death counts, and the\n"
             "INE's defunciones tabulados are legacy .xls with no coverage\n"
             "statement. A model is not a count: nothing is drawn.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    ctx.pending(ax)
    _pending(ig, ax, "WHO's GHO catalogue now carries no general COVID-19\n"
             "death indicator and covid19.who.int serves HTML for its CSV\n"
             "(2026-10-25). No official Venezuelan file is staged.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("mortality.lens", "Life expectancy at birth (years)",
                 unit=False)
    ly, lv = _yr(ctx, V, "life_expectancy")
    ctx.line(ax, ly, lv, p.TEAL, label="Life expectancy (UN WPP)")
    ig.add_recessions(ax, label=False)
    ax.set_ylim(70.5, 74.5)
    _note(p, ax, 0.02, 0.96, f"{lv[0]:.1f} years in {ly[0]}, {_at(ly, lv, 2021):.1f} "
          f"in 2021,\n{lv[-1]:.1f} in {ly[-1]} — modelled, and it barely "
          "moved")
    _foot(p, ax, "World Bank SP.DYN.LE00.IN (UN WPP life tables)")
    _finish(ctx, ig)


# --------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    M = "migration/migration.csv"

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    ctx.pending(ax)
    _pending(ig, ax, "Gross flows need a residence register, and the INE's\n"
             "migration tabulados are not published as a series. UNHCR's\n"
             "origin-country caseload is not a register flow.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    ctx.pending(ax)
    _pending(ig, ax, "−45.5 per 1,000 in 2018 does not fit a −10…+40\n"
             "comparable scale, and the value is not clipped. The whole\n"
             "series is drawn in the lens on its own axis.")
    _foot(p, ax, "SOURCES.yaml meta.pending; the series is on plate 11's lens")

    ax = ig.slot("migration.foreign_born", "Foreign-born share of the "
                 "population (%)")
    t = ctx.table(M)
    stock = dict(zip(*ctx.series(t, "migrant_stock")))
    pop = dict(zip(*ctx.series(t, "population"))) if "population" in t else {}
    if not pop:
        pop = dict(zip(*ctx.series(ctx.table("demography/population.csv"),
                                   "population")))
    fy = [y for y in sorted(stock) if y in pop and stock[y] == stock[y]]
    fv = [stock[y] / pop[y] * 100 for y in fy]
    ctx.line(ax, fy, fv, p.PURPLE, label="Foreign-born share")
    ctx.endlabel(ax, fy, fv, p.PURPLE, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{fv[0]:.1f}% in {fy[0]}, {fv[-1]:.1f}% in "
          f"{fy[-1]} —\nsnapshot years only; this counts people coming in, "
          "not leaving", size=7.8)
    _foot(p, ax, "World Bank (UN DESA migrant stock) ÷ UN WPP population. "
          "2010, 2015, 2020, 2024: never interpolated")

    ax = ig.slot("migration.lens", "The exodus — net migration (bars, left) "
                 "and the caseload abroad (line, right)")
    my, mv = _yr(ctx, M, "net_migration_per_1000")
    ctx.bars(ax, my, mv, p.ALERT)
    ax.axhline(0, color=p.MUTED, lw=0.9, zorder=2)
    ax.set_ylim(min(-50.0, min(mv) * 1.1), 18)
    ax.set_ylabel("per 1,000 (bars)", fontsize=8.6, color=p.MUTED)
    worst = min(zip(my, mv), key=lambda x: x[1])
    ax.text(worst[0] + 0.45, worst[1] + 1.5, f"{worst[1]:.1f} in {worst[0]}",
            fontsize=8.4, fontweight="bold", color=p.ALERT, va="bottom")
    right = ax.twinx()
    dy, dv = _yr(ctx, "migration/displacement.csv",
                 "refugees_and_asylum_seekers")
    right.plot(dy, [v / 1e6 for v in dv], color=p.GOLD, lw=2.2,
               marker="o", ms=3.6, zorder=4)
    right.set_ylim(0, 2.2)
    right.set_xlim(ctx.YEARS[0] - 0.6, ctx.YEARS[-1] + 0.6)
    right.yaxis.set_major_locator(mticker.FixedLocator([0, 0.5, 1.0, 1.5, 2.0]))
    right.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"{v:g}"))
    right.tick_params(axis="y", colors=p.GOLD, labelsize=8.2, length=0)
    right.spines[["top", "left", "right"]].set_visible(False)
    right.grid(False)
    right.xaxis.set_visible(False)
    peak = max(zip(dy, dv), key=lambda x: x[1])
    right.annotate(f"{peak[1] / 1e6:.2f}m in {peak[0]}", (peak[0], peak[1] / 1e6),
                   textcoords="offset points", xytext=(-8, 4), ha="right",
                   va="bottom", fontsize=8.4, fontweight="bold", color=p.GOLD)
    _note(p, ax, 0.02, 0.96, "UN WPP net migration, per 1,000; and UNHCR's\n"
          "origin-country caseload, in millions (gold, right). Two\n"
          "publishers, two scales, neither clipped to fit the other")
    _foot(p, ax, "World Bank SM.POP.NETM ÷ UN WPP population; UNHCR Refugee "
          "Data Finder (coo=VEN). A caseload is not a rate")
    _finish(ctx, ig)


# --------------------------------------------------------------------------
PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Economy — A Collapse Measured From Outside",
         subtitle="Growth, income, jobs and the inflation that left the "
                  "comparable scale",
         source="Sources: World Bank WDI · IMF WEO October 2026",
         alt="Four panels: real GDP growth as World Bank bars with the IMF's "
             "line over them, collapsing to about −30% in 2020; GDP per "
             "person on a log axis from US$13,646 in 2010 to US$3,495 in "
             "2025; a pending inflation panel, because 65,374% cannot share "
             "the linear scale; and unemployment from the ILO model against "
             "the IMF series that ends in 2018.",
         filename="01-economy"),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — A State That Stopped Collecting",
         subtitle="General government on the Fund's staff estimate, because "
                  "the national books stop in 2009",
         source="Sources: IMF WEO October 2026, general government",
         alt="Four panels: revenue and expenditure falling as a share of GDP, "
             "revenue to 6.9% against expenditure of 37.9% in 2018; an overall "
             "balance of −31.9% that year with the primary line beside it; a "
             "pending debt panel because the vintage carries no Venezuelan "
             "debt stock; and interest paid near zero.",
         filename="02-fiscal"),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Spending — What the Budget Does Not Say",
         subtitle="The investment rate is drawable; the functional breakdown "
                  "is not published anywhere reachable",
         source="Sources: World Bank WDI (GFCF) · SOURCES.yaml meta.pending",
         alt="Four panels: three are pending for the functional stack, the "
             "social-protection split and public investment, because "
             "Venezuela reports no COFOG; the fourth draws whole-economy "
             "investment, which fell from 25.6% of GDP in 2013 to 3.8% in "
             "2024.",
         filename="03-spending"),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — The Oil Surplus of an Economy That Stopped Importing",
         subtitle="Exports held while imports vanished; the partners panel is "
                  "a hole the customs service left",
         source="Sources: World Bank WDI national accounts "
                "(NE.EXP/IMP.GNFS.ZS)",
         alt="Four panels: exports and imports as a share of GDP from 2012; a "
             "trade surplus reaching +36.3% of GDP in 2019; a pending export "
             "destinations panel, because Venezuela's Comtrade reporting stops "
             "in 2013 and is mostly residual buckets; and a lens deriving "
             "exports and imports in US$ billion, from about US$110bn to "
             "US$15bn.",
         filename="04-trade"),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Markets — The Currency the State Stopped Pricing",
         subtitle="The official rate to 2017; no policy rate, no bond, no "
                  "index survives any route tried",
         source="Sources: World Bank WDI (official exchange rate) · "
                "SOURCES.yaml meta.pending",
         alt="Four panels: the policy rate, the ten-year yield and the equity "
             "index are pending because the Central Bank is unreachable and no "
             "official series exists; the currency panel draws the official "
             "rate as an index from 100 in 2006 to 21.5 in 2017, where the "
             "series stops.",
         filename="05-markets"),
    dict(id="06", slug="people", topic="people", builder=plate_people,
         title="People & Prices — A Flat Gini and a Hyperinflation",
         subtitle="The one national series that runs the whole window, and the "
                  "one that cannot share a linear scale",
         source="Sources: INE household survey (Gini) · IMF WEO and the BCV's "
                "INPC (prices)",
         alt="Four panels: the INE's Gini moving between 44.2 and 37.7 points "
             "without a break through the collapse; pending poverty and "
             "minimum-wage panels with their reasons; and a prices lens on a "
             "log axis, where the IMF staff estimate runs from 13.7% in 2006 "
             "to 65,374% in 2018 and the BCV's INPC sits beside it to 2016.",
         filename="06-people"),
    dict(id="07", slug="world", topic="world", builder=plate_world,
         title="Venezuela in the World — Size, Development and What Is Left",
         subtitle="Dollar GDP on two exchange-rate conventions, and reserves "
                  "that stop where the Central Bank stopped",
         source="Sources: World Bank WDI · IMF WEO · UNDP HDR 2025",
         alt="Four panels: GDP in current dollars on a log axis, the World "
             "Bank's line and the IMF's, falling from US$393bn in 2010 to "
             "US$43bn in 2020; the Human Development Index from 0.773 in 2013 "
             "to 0.709 in 2023; a pending corruption index; and reserves "
             "falling from US$43bn in 2008 to US$9.8bn in 2017, where the "
             "series ends.",
         filename="07-world"),
    dict(id="08", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — A Population That Began to Leave",
         subtitle="Births, deaths and a modelled exodus — no census since 2011",
         source="Sources: World Bank WDI (UN World Population Prospects)",
         alt="Four panels: the population index peaking at 113 in 2016 and "
             "settling at 105 in 2025; the fertility rate falling from 2.60 to "
             "2.08 children per woman against the 2.1 replacement line; crude "
             "birth and death rates converging; and natural increase falling "
             "from 16.9 to 7.6 per 1,000, with net migration left to the "
             "migration plate.",
         filename="08-demography"),
    dict(id="09", slug="security", topic="security", builder=plate_security,
         title="Security — Homicide, Suicide and the Road",
         subtitle="UNODC and WHO series, with the 2013 and 2018 holes left "
                  "open",
         source="Sources: UNODC and WHO via the World Bank",
         alt="Three panels: the homicide rate on a log axis, peaking at 62.9 "
             "per 100,000 in 2014 and falling to 12.7 in 2022 with holes in "
             "2013 and 2018; the suicide rate with a 2016 estimate-vintage "
             "spike from 6.1 to 10.5; and road deaths rising from 30.8 to 39.0 "
             "per 100,000 by 2019.",
         filename="09-security"),
    dict(id="10", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — A Death Rate That Barely Moved",
         subtitle="The UN model is what is published; the registered counts "
                  "are not staged",
         source="Sources: World Bank WDI (UN WPP life tables) · "
                "SOURCES.yaml meta.pending",
         alt="Four panels: the crude death rate rising from 5.2 to 7.7 per "
             "1,000 with 7.9 in 2021; pending excess-death and COVID-19 "
             "panels with their routes; and life expectancy as a lens, from "
             "73.0 years in 2006 to 72.7 in 2024 with a dip to 71.5 in 2021.",
         filename="10-mortality"),
    dict(id="11", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — The Exodus, on Its Own Scale",
         subtitle="Net migration leaves the comparable range in 2017; the "
                  "caseload abroad is a different publisher and a different "
                  "measure",
         source="Sources: World Bank WDI (UN WPP) · UNHCR Refugee Data Finder",
         alt="Four panels: pending immigration and emigration flows; a pending "
             "net-migration slot, because −45.5 per 1,000 in 2018 is outside "
             "the comparable scale; the foreign-born share near 4.5% in "
             "snapshot years; and a lens with net migration as bars on the "
             "left and UNHCR's protection caseload abroad rising to 1.73 "
             "million in 2024 on the right.",
         filename="11-migration"),
)
