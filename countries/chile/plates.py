"""The chile plates, on the plate spine.

Twelve chapters, one per spine topic the staged data can answer. Every
plate declares its topic and claims its four panels by slot key, in the
spine's order, so a Chilean panel sits over the same panel of every other
country in the comparison viewer: same indicator, same unit, same y-scale
(PLATE_SPINE.md, core/spine.py).

Phase A found that almost none of Chile's own publishers answer this
network as data: the Banco Central's series API is credentialled, INE
returns monthly PDFs, and Dipres, the CMF, Aduanas and the SII answer with
HTML or walls. The one official series here is MINSAL/DEIS's registered
deaths, which is why the mortality plate draws the national count and the
World Bank rate as two labelled lines on two denominators. Everything else
is the harmonised layer (World Bank, IMF, BIS, OECD, UNDP, TI, Comtrade),
each panel's footer and SOURCES.yaml naming whose national series it
republishes. No number is typed in here: every value a note prints is read
from the CSV at build time.

Method decisions that run through the file:

- **Two population series, never mixed.** The World Bank/UN figure is the
  denominator of its own rates and of net migration; DEIS's embedded INE
  projection is the denominator of the national crude death rate. The
  mortality plate says so.
- **Survey points stay points.** CASEN is biennial and was rebased twice;
  the Gini, the poverty lines and the UN migrant stock are drawn as
  markers, never joined by an annual line and never interpolated.
- **Short official windows stay short.** COFOG begins in 2018 and the OECD
  government-investment series ends in 2012; both panels label their window
  instead of borrowing another series' years.
- **A pending panel says why.** A slot with no staged data is claimed and
  `ctx.pending`-ed with the route result from DISCOVERY.md, never filled
  from a plausible-looking proxy.
"""
from __future__ import annotations

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


def _points(ax, years, vals, color, label="", ms=5.0):
    """A survey or stock series as markers only: no line implies a year
    the publisher never measured."""
    ax.plot(years, vals, ls="none", marker="o", ms=ms, color=color,
            label=label, zorder=4, markeredgecolor="white",
            markeredgewidth=0.8)


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(a, xticks_years=not getattr(a, "_categorical_x", False))


def _bands(ig, ax, y, p):
    """Recession bands with their names at height `y` (axes fraction).

    add_recessions puts the names just above the axes, where a long panel
    title in Spanish or Portuguese runs into them; this places them at a
    height the panel's own scale is known to leave empty.
    """
    ig.add_recessions(ax, label=False)
    for start, end, name in ig.country.recessions:
        ax.text((start + end) / 2, y, name, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=8, color=p.MUTED,
                style="italic")

def _mark(ig, ax, key, dy=0.97):
    x, label = events.MARKS[key]
    ig.add_event(ax, x, label, dy=dy)


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p
    E = "macro/economy.csv"

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, E, "real_growth_pct")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.BLOOD)
    _bands(ig, ax, 0.02, p)
    _note(p, ax, 0.02, 0.30,
          f"{_at(gy, gv, 2020):.1f}% in 2020, the pandemic; "
          f"{_at(gy, gv, 2019):.1f}% in 2019\nwas the weakest year "
          "outside a contraction", va="bottom")
    _foot(p, ax, "World Bank WDI, constant-price GDP")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "world/world.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.COBALT)
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "estallido", dy=0.97)
    _note(p, ax, 0.02, 0.96,
          f"US${_at(py, pv, 2006):,.0f} in 2006 to "
          f"US${pv[-1]:,.0f} in {py[-1]} —\ncurrent dollars, not adjusted "
          "for prices")
    _foot(p, ax, "World Bank NY.GDP.PCAP.CD")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year)")
    cy, cv = _yr(ctx, E, "inflation_pct")
    ctx.line(ax, cy, cv, p.BLOOD)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{_at(cy, cv, 2022):.1f}% in 2022, the highest of the window;\n"
          f"{_at(cy, cv, 2009):.1f}% in 2009")
    _foot(p, ax, "World Bank WDI, the INE CPI's annual average — INE's own "
          "index file is not machine-readable here")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    uy, uv = _yr(ctx, E, "unemployment_pct")
    ctx.line(ax, uy, uv, p.NAVY)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{_at(uy, uv, 2009):.1f}% in 2009, {_at(uy, uv, 2020):.1f}% in "
          "2020;\nILO modelled, not the INE survey")
    _foot(p, ax, "World Bank WDI (ILO modelled). The INE labour-force "
          "survey's own rate is pending")
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
    ctx.line(ax, ey, ev, p.BLOOD, label="Expenditure")
    _bands(ig, ax, 0.90, p)
    ax.legend(loc="lower left", fontsize=8.0, frameon=False)
    _note(p, ax, 0.98, 0.96,
          f"2021: spending {_at(ey, ev, 2021):.1f}% of GDP\nagainst revenue "
          f"of {_at(ry, rv, 2021):.1f}%", ha="right")
    _foot(p, ax, "IMF, general government, calendar years")

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    by, bv = _yr(ctx, F, "balance_pct_gdp")
    py, pv = _yr(ctx, F, "primary_balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.BLOOD if v < 0 else p.GREEN)
    ctx.line(ax, py, pv, p.NAVY, label="Primary balance")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower right", fontsize=8.0, frameon=False)
    _note(p, ax, 0.98, 0.96,
          f"2020 and 2021: {_at(by, bv, 2020):.1f}% and "
          f"{_at(by, bv, 2021):.1f}% of GDP", ha="right")
    _foot(p, ax, "IMF WEO. The primary balance is the overall balance "
          "before interest")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    dy, dv = _yr(ctx, F, "debt_pct_gdp")
    ctx.line(ax, dy, dv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{_at(dy, dv, 2006):.1f}% of GDP in 2006, {dv[-1]:.1f}% in "
          f"{dy[-1]} —\nthe copper surplus years left almost none")
    _foot(p, ax, "IMF WEO, general-government gross debt")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, "IMF DataMapper carries no general-government\n"
             "interest indicator for Chile, and Dipres' statistics\n"
             "are HTML behind article pages with no file index.")
    _foot(p, ax, "SOURCES.yaml meta.pending")
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
SPEND = [
    ("social_protection", "BLOOD", "social protection"),
    ("health", "COBALT", "health"),
    ("education", "TEAL", "education"),
    ("general_public_services", "NAVY", "general public services"),
    ("economic_affairs", "COPPER", "economic affairs"),
    ("defence", "PURPLE", "defence"),
    ("public_order", "COBALT_D", "public order"),
]


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    C = "spending/cofog.csv"
    t = ctx.table(C)

    ax = ig.slot("spending.by_function",
                 "Spending by function, stacked (% of GDP)")
    years = sorted(y for y, v in zip(t["year"], t["total"]) if v == v) \
        if t else []
    # Seven groups, the spine's: defence and public order are separate
    # lines here, and environment, housing and recreation are the
    # remainder the spine calls "other".
    series = {col: dict(zip(t["year"], t[col])) if t else {}
              for col, _, _ in SPEND}
    other = [sum(d[y] for d in (
        dict(zip(t["year"], t["environment"])),
        dict(zip(t["year"], t["housing"])),
        dict(zip(t["year"], t["recreation_culture"])))) for y in years]
    layers = [[series[col][y] for y in years] for col, _, _ in SPEND]
    ax.stackplot(years, *layers, other,
                 labels=[label for _, _, label in SPEND] + ["other"],
                 colors=[getattr(p, color) for _, color, _ in SPEND]
                 + [p.SAND],
                 alpha=0.9, lw=0)
    _bands(ig, ax, 0.92, p)
    ax.legend(loc="lower left", fontsize=6.4, ncol=3, frameon=False)
    tot = dict(zip(t["year"], t["total"])) if t else {}
    _foot(p, ax, "OECD COFOG table 11, general government — Chile reports it "
          "from 2018 only")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    soc = dict(zip(t["year"], t["social_protection"])) if t else {}
    ctx.line(ax, years, [soc[y] for y in years], p.BLOOD,
             label="Social protection")
    ctx.line(ax, years, [tot[y] - soc[y] for y in years], p.NAVY,
             label="Everything else")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"social protection {soc[years[0]]:.1f}% of GDP in {years[0]},\n"
          f"{soc[2021]:.1f}% in 2021, {soc[years[-1]]:.1f}% in {years[-1]}")
    _foot(p, ax, "Same COFOG series, two groups")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(% of GDP)")
    iy, iv = _yr(ctx, "macro/economy.csv", "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{_at(iy, iv, 2006):.1f}% in 2006, {_at(iy, iv, 2008):.1f}% in "
          f"2008,\n{_at(iy, iv, 2020):.1f}% in 2020")
    _foot(p, ax, "World Bank WDI, gross fixed capital formation, whole "
          "economy")

    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    gy, gv = _yr(ctx, "spending/public_investment.csv", "gov_gfcf_pct_gdp")
    ctx.line(ax, gy, gv, p.COPPER)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"the OECD series stops in {gy[-1]}: six years, not\ncontinued "
          "from the national accounts on another basis")
    _foot(p, ax, "OECD NAAG P51GS13, general government")
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
def plate_trade(ctx, ig) -> None:
    p = ctx.p
    T = "trade/trade.csv"

    ax = ig.slot("trade.exports_imports", "Exports and imports (% of GDP)")
    xy, xv = _yr(ctx, T, "exports_pct_gdp")
    my, mv = _yr(ctx, T, "imports_pct_gdp")
    ctx.line(ax, xy, xv, p.COBALT, label="Exports")
    ctx.line(ax, my, mv, p.BLOOD, label="Imports")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=8.0, frameon=False)
    _mark(ig, ax, "copper", dy=0.72)
    _note(p, ax, 0.02, 0.96,
          f"exports peaked at {max(xv):.1f}% of GDP in {xy[xv.index(max(xv))]};"
          f"\n{_at(xy, xv, 2025):.1f}% in 2025")
    _foot(p, ax, "World Bank national accounts, goods and services")

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    by, bv = _yr(ctx, T, "trade_balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.BLOOD)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.98, 0.96,
          f"2006-07: +{_at(by, bv, 2006):.1f}% and "
          f"+{_at(by, bv, 2007):.1f}% of GDP;\n{_at(by, bv, 2022):.1f}% in "
          "2022", ha="right")
    _foot(p, ax, "Derived: exports minus imports, same World Bank series")

    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    ctx.pending(ax)
    _pending(ig, ax, "No annual partner series is staged: the customs\n"
             "service's statistics answer as HTML, and Comtrade's free\n"
             "preview is a single recent period, not a time series.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("trade.lens", "Goods exports by destination, 2024 "
                 "(% of goods exports, one year)")
    pt = ctx.table("trade/partners_2024.csv")
    if pt and "partner" in pt:
        names = [str(n) for n in pt["partner"]][:10]
        shares = [float(v) for v in pt["share_pct"]][:10]
        ypos = list(range(len(names)))[::-1]
        ax.barh(ypos, shares,
                color=[p.COBALT if n != names[0] else p.BLOOD for n in names])
        ax.set_yticks(ypos)
        ax.set_yticklabels(names, fontsize=7.6)
        for y, v in zip(ypos, shares):
            ax.text(v + 0.6, y, f"{v:.1f}%", va="center", fontsize=7.4,
                    color=p.MUTED)
        ax.tick_params(axis="y", length=0)
        ax._categorical_x = True
        ax._lens_xlim = (0, max(shares) * 1.22)
    _foot(p, ax, "UN Comtrade, Chile as reporter, 2024 — one year; the "
          "customs declarations behind it")
    _finish(ctx, ig)
    if hasattr(ax, "_lens_xlim"):
        ax.set_xlim(*ax._lens_xlim)
        ax.set_xticks([0, 10, 20, 30, 40, 50])


# ----------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ky, kv = _yr(ctx, "markets/policy_rate.csv", "policy_rate_pct")
    cy, cv = _yr(ctx, "macro/economy.csv", "inflation_pct")
    ctx.line(ax, cy, cv, p.BLOOD, label="Inflation")
    ctx.line(ax, ky, kv, p.NAVY, label="Policy rate")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=8.0, frameon=False)
    _mark(ig, ax, "tightening", dy=0.62)
    _note(p, ax, 0.02, 0.96,
          f"the annual mean went from {_at(ky, kv, 2006):.1f}% in 2006 to "
          f"{_at(ky, kv, 2020):.1f}% in 2020\nand {_at(ky, kv, 2023):.1f}% in "
          "2023")
    _foot(p, ax, "BIS WS_CBPOL (the Banco Central's daily target, annual "
          "mean) and the INE CPI via the World Bank")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    ctx.pending(ax)
    _pending(ig, ax, "The Banco Central's series API is credentialled and\n"
             "answers an HTML error page without a token; BIS carries no\n"
             "10-year benchmark for Chile. No proxy is substituted.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("markets.currency", "The peso against the US$ "
                 "(index 2006 = 100, up = stronger)")
    fy, fv = _yr(ctx, "macro/fx.csv", "clp_per_usd")
    iy, iv = ctx.fx_index(dict(zip(fy, fv)))
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.98, 0.96,
          f"{_at(fy, fv, 2006):.0f} per dollar in 2006 to "
          f"{_at(fy, fv, 2025):.0f} in 2025:\n{iv[-1]:.1f} of the 2006 value",
          ha="right")
    _foot(p, ax, "World Bank PA.NUS.FCRF (the Banco Central's annual average), "
          "rebased and inverted so up is stronger")

    ax = ig.slot("markets.equities", "Main equity index in US$ "
                 "(index 2006 = 100, in US$)")
    ctx.pending(ax)
    _pending(ig, ax, "The Bolsa de Santiago's API answers a captcha page,\n"
             "Yahoo Finance has no ^IPSA symbol and stooq a challenge.\n"
             "No redistributor with a stable endpoint was found.")
    _foot(p, ax, "SOURCES.yaml meta.pending")
    _finish(ctx, ig)


# ------------------------------------------------------------------ credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p
    H = "credit/household_credit.csv"

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    dy, dv = _yr(ctx, H, "hh_debt_pct_gdp_q4")
    ctx.line(ax, dy, dv, p.COBALT)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{_at(dy, dv, 2006):.1f}% of GDP in 2006, {_at(dy, dv, 2020):.1f}% "
          f"in 2020,\n{dv[-1]:.1f}% in {dy[-1]} — the fourth-quarter stock")
    _foot(p, ax, "BIS total credit, all sources, Q4 of each year")

    ax = ig.slot("credit.lending_rate",
                 "Household lending rate vs policy rate (%)")
    ctx.pending(ax)
    _pending(ig, ax, "The CMF's statistics pages answer HTML with\n"
             "client-side grids and the historical archive returns 403;\n"
             "no machine-readable lending-rate series is staged.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    ctx.pending(ax)
    _pending(ig, ax, "The CMF publishes provisions in its bank statistics,\n"
             "not a non-performing ratio, and datos.gob.cl carries board\n"
             "lending rates but no arrears series.")
    _foot(p, ax, "SOURCES.yaml meta.pending")
    _finish(ctx, ig)


# ------------------------------------------------------------------ people
def plate_people(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100)")
    gy, gv = _yr(ctx, "people/gini.csv", "gini")
    _points(ax, gy, gv, p.PURPLE)
    _note(p, ax, 0.02, 0.96,
          f"{gv[-1]:.1f} in {gy[-1]}, from {gv[0]:.1f} in {gy[0]} —\n"
          f"nine CASEN surveys, never interpolated")
    _foot(p, ax, "World Bank WDI from CASEN, income per capita")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    ny, nv = _yr(ctx, "people/poverty.csv", "poverty_national_pct")
    uy, uv = _yr(ctx, "people/poverty.csv", "poverty_830_pct")
    _points(ax, ny, nv, p.BLOOD, label="National poverty line (CASEN)")
    _points(ax, uy, uv, p.COBALT, label="US$8.30 a day, 2021 PPP", ms=4.4)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"the national line reads {nv[-1]:.1f}% in {ny[-1]};\n"
          f"the US$8.30 line {uv[-1]:.1f}% in {uy[-1]} — two questions")
    _foot(p, ax, "CASEN via the World Bank; the line was rebased in 2013 and "
          "with the 2017 survey")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    ctx.pending(ax)
    _pending(ig, ax, "Chile's minimum wage is statutory and reajustado\n"
             "annually, but no machine-readable official series answered:\n"
             "Dirección del Trabajo and mintrab are HTML, the OECD's\n"
             "MW_CURP flow returns no record, ILOSTAT answers 403.")
    _foot(p, ax, "SOURCES.yaml meta.pending — next route: the statutes on "
          "bcn.cl/leychile, one law per reajuste")
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p
    W = "world/world.csv"

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, W, "gdp_usd_bn")
    ctx.line(ax, gy, gv, p.COBALT)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"US${_at(gy, gv, 2006):,.1f}bn in 2006,\n"
          f"US${gv[-1]:,.1f}bn in {gy[-1]} — nominal")
    _foot(p, ax, "World Bank NY.GDP.MKTP.CD, current US$")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, W, "hdi")
    ctx.line(ax, hy, hv, p.GREEN)
    _note(p, ax, 0.02, 0.96,
          f"{_at(hy, hv, 2006):.3f} in 2006, {hv[-1]:.3f} in {hy[-1]} —\n"
          "one HDR vintage recomputed each report")
    _foot(p, ax, "UNDP HDR 2025; the series stops in 2023")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (0–100)")
    cy, cv = _yr(ctx, W, "cpi_score")
    ctx.line(ax, cy, cv, p.COPPER)
    _note(p, ax, 0.02, 0.96,
          f"{cv[0]:.0f} in {cy[0]} to {cv[-1]:.0f} in {cy[-1]} —\n"
          "one 2012-method series, not an official statistic")
    _foot(p, ax, "Transparency International, 2012 method onwards")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn, year-end)")
    ry, rv = _yr(ctx, W, "reserves_usd_bn")
    ctx.line(ax, ry, rv, p.TEAL)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"US${rv[0]:,.1f}bn in {ry[0]},\nUS${rv[-1]:,.1f}bn in {ry[-1]}")
    _foot(p, ax, "World Bank FI.RES.TOTL.CD, total reserves including gold")
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p
    D = "demography/demography.csv"

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    wy, wv = _yr(ctx, D, "population")
    iy, iv = ctx.index_2006(dict(zip(wy, wv)))
    ctx.line(ax, iy, iv, p.COBALT)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{wv[-1] / 1e6:.1f}m people in {wy[-1]} —\n{iv[-1] / 100:.2f}× the "
          "2006 level")
    _foot(p, ax, "World Bank SP.POP.TOTL (UN WPP and the INE projection)")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    fy, fv = _yr(ctx, D, "fertility")
    ctx.line(ax, fy, fv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ax.axhline(2.1, color=p.FAINT, lw=0.9, ls=(0, (4, 3)), zorder=2)
    ax.text(2025.5, 2.16, "2.1", fontsize=7.6, color=p.MUTED, ha="right",
            va="bottom")
    _note(p, ax, 0.02, 0.96,
          f"{fv[0]:.2f} in {fy[0]} to {fv[-1]:.2f} in {fy[-1]} —\n"
          "below replacement through the whole window")
    _foot(p, ax, "World Bank SP.DYN.TFRT.IN")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    by, bv = _yr(ctx, D, "birth_rate_per_1000")
    dy, dv = _yr(ctx, D, "death_rate_per_1000")
    ctx.line(ax, by, bv, p.GREEN, label="Births")
    ctx.line(ax, dy, dv, p.BLOOD, label="Deaths")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=8.0, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"births {bv[0]:.1f} in {by[0]} to {bv[-1]:.1f} in {by[-1]};\n"
          f"deaths {_at(dy, dv, 2010):.1f} in 2010 to {dv[-1]:.1f} in {dy[-1]}")
    _foot(p, ax, "World Bank SP.DYN.CBRT.IN and SP.DYN.CDRT.IN")

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net migration (per 1,000 people)")
    ny, nv = _yr(ctx, D, "natural_increase_per_1000")
    my, mv = _yr(ctx, "migration/migration.csv", "net_migration_per_1000")
    ctx.line(ax, ny, nv, p.TEAL, label="Natural increase")
    ctx.line(ax, my, mv, p.COPPER, label="Net migration")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"natural increase {nv[0]:.1f} in {ny[0]} to {nv[-1]:.1f} in "
          f"{ny[-1]};\nnet migration peaks at {max(mv):.1f} in "
          f"{my[mv.index(max(mv))]}")
    _foot(p, ax, "Births minus deaths per 1,000, and UN net migration over "
          "the same population")
    _finish(ctx, ig)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    S = "security/security.csv"

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    hy, hv = _yr(ctx, S, "homicide_per_100k")
    ctx.line(ax, hy, hv, p.BLOOD)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{_at(hy, hv, 2015):.1f} in 2015, {_at(hy, hv, 2019):.1f} in "
          f"2019,\n{hv[-1]:.1f} in {hy[-1]} — the UNODC series stops there")
    _foot(p, ax, "UNODC via the World Bank. Carabineros/PDI and Fiscalía "
          "count on another basis and are pending")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    sy, sv = _yr(ctx, S, "suicide_per_100k")
    ctx.line(ax, sy, sv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{max(sv):.1f} in {sy[sv.index(max(sv))]} to {sv[-1]:.1f} in "
          f"{sy[-1]} —\nthe WHO series stops there")
    _foot(p, ax, "WHO via the World Bank, age-standardised")

    ax = ig.slot("security.road_deaths", "Road traffic deaths (per 100,000)")
    ry, rv = _yr(ctx, S, "road_deaths_per_100k")
    ctx.line(ax, ry, rv, p.COPPER)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{rv[0]:.1f} in {ry[0]} to {rv[-1]:.1f} in {ry[-1]} —\nthe WHO "
          "series stops there")
    _foot(p, ax, "WHO via the World Bank")
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    M = "mortality/mortality.csv"

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000 people)")
    ny, nv = _yr(ctx, M, "crude_death_rate_national")
    wy, wv = _yr(ctx, M, "crude_death_rate_wb")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.8, ms=3.0,
             label="World Bank, UN population")
    ctx.line(ax, ny, nv, p.INK, label="MINSAL/DEIS, INE population")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"national {_at(ny, nv, 2019):.2f} in 2019, "
          f"{_at(ny, nv, 2021):.2f} in 2021 —\ntwo denominators, two lines, "
          "never one")
    _foot(p, ax, "Deaths and population both from DEIS's own file")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above 2015–2019 average)")
    ey, ev = _yr(ctx, M, "excess_deaths_pct_vs_2015_2019")
    ctx.bars(ax, ey, ev, lambda v: p.BLOOD if v > 0 else p.GREEN)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.98, 0.96,
          f"+{max(ev):.1f}% in {ey[ev.index(max(ev))]}, "
          f"+{ev[-1]:.1f}% in {ey[-1]}\non a 2015–2019 baseline of 105,681 "
          "deaths", ha="right")
    _foot(p, ax, "Derived: registered deaths against the 2015–2019 mean")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    ctx.pending(ax)
    _pending(ig, ax, "The WHO global CSV now serves the dashboard's HTML;\n"
             "DEIS's weekly file carries no cause column, and INE's\n"
             "cause-of-death tables are annual PDFs. Not proxied by\n"
             "all-cause excess deaths.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("mortality.lens", "Deaths registered a year, against the "
                 "2015–2019 average", unit=False)
    dy, dv = _yr(ctx, M, "deaths")
    ctx.line(ax, dy, dv, p.INK)
    ig.add_recessions(ax, label=False)
    mean = sum(v for y, v in zip(dy, dv) if 2015 <= y <= 2019) / 5
    ax.axhline(mean, color=p.BLOOD, lw=1.0, ls=(0, (4, 3)), zorder=2)
    _note(p, ax, 0.02, 0.96,
          f"{dv[dy.index(2021)]:,.0f} deaths in 2021, the peak;\n"
          f"{dv[-1]:,.0f} in {dy[-1]} — still above the dashed baseline")
    _foot(p, ax, "MINSAL/DEIS; the baseline is the 2015–2019 mean of 105,681 "
          "deaths")
    _finish(ctx, ig)


# --------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    M = "migration/migration.csv"

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    ctx.pending(ax)
    _pending(ig, ax, "SERMIG publishes visas and permits granted, not\n"
             "arrivals and departures, and its statistics are PDF tables;\n"
             "INE's migration estimates are not exposed as a series.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    ny, nv = _yr(ctx, M, "net_migration_per_1000")
    ctx.line(ax, ny, nv, p.COBALT)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{nv[0]:.1f} in {ny[0]}, {max(nv):.1f} in "
          f"{ny[nv.index(max(nv))]},\n{nv[-1]:.1f} in {ny[-1]}")
    _foot(p, ax, "World Bank (UN WPP) net migration over mid-year population")

    ax = ig.slot("migration.foreign_born",
                 "Foreign-born share of the population (% of population)")
    fy, fv = [], []
    stock = dict(zip(*ctx.series(ctx.table(M), "migrant_stock")))
    pop = dict(zip(*ctx.series(ctx.table("demography/demography.csv"),
                               "population")))
    for y in sorted(stock):
        if stock[y] and y in pop:
            fy.append(y)
            fv.append(stock[y] / pop[y] * 100)
    _points(ax, fy, fv, p.PURPLE)
    _note(p, ax, 0.02, 0.96,
          f"{fv[0]:.1f}% in {fy[0]}, {fv[-1]:.1f}% in {fy[-1]} —\n"
          "foreign-born, five-year UN stock, drawn as points")
    _foot(p, ax, "UN migrant stock via the World Bank over UN population")

    ax = ig.slot("migration.lens", "Net migration, people a year "
                 "(own scale)", unit=False)
    cy, cv = _yr(ctx, M, "net_migration")
    ctx.bars(ax, cy, cv, lambda v: p.GREEN if v >= 0 else p.BLOOD)
    ig.add_recessions(ax, label=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96,
          f"{peak[1]:,.0f} people in {peak[0]}, {cv[-1]:,.0f} in {cy[-1]} —\n"
          "a residual of two badly measured numbers; departures are the "
          "weak side")
    _foot(p, ax, "World Bank (UN WPP) net migration, persons")
    _finish(ctx, ig)


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Economy — Copper, a Pandemic and 2022's Price Shock",
         subtitle="Growth, income, prices and jobs, 2006–2025, on the World "
                  "Bank's records of Chile's own accounts.",
         source="Sources: World Bank WDI (national accounts, the INE CPI "
                "and ILO-modelled unemployment) · IMF WEO as the growth check",
         alt="Four panels on the Chilean economy, 2006–2025. Real GDP grew "
             "6.1% in 2006, fell 1.1% in 2009 and 6.1% in 2020, then "
             "rebounded 11.3% in 2021; GDP per person in current dollars "
             "rose from about 9,300 to about 18,000; consumer price "
             "inflation was 11.6% in 2022, the highest of the window, "
             "against 0.4% in 2009; unemployment peaked at 11.3% in 2009 "
             "and 10.9% in 2020 on the ILO-modelled series."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — A Copper-Boom Surplus Spent Into Debt",
         subtitle="General government on the IMF's calendar-year basis, "
                  "2006–2025. The national central-government perimeter is "
                  "a different object and is not spliced in.",
         source="Sources: IMF WEO and Fiscal Monitor via DataMapper, general "
                "government · Dipres' national series pending",
         alt="Three drawn panels and one pending on Chilean public "
             "finances. Revenue ran 26.2% of GDP in 2006 and expenditure "
             "18.7%, a surplus of 7.5%; the balance was -7.1% in 2020 and "
             "-7.5% in 2021; gross debt rose from 5% of GDP in 2006 to "
             "41.5% in 2025. Interest paid stays pending: no "
             "general-government interest indicator is on an accessible "
             "official route."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Spending — What the State Buys, Function by Function",
         subtitle="COFOG for 2018–2024, the years Chile reports it, beside "
                  "the whole economy's investment rate and the government's "
                  "own, which stops in 2012.",
         source="Sources: OECD National Accounts at a Glance, table 11 "
                "(COFOG) and P51GS13 · World Bank WDI (GFCF)",
         alt="Four panels on spending. General-government spending by "
             "function reached 34.1% of GDP in 2021, when social protection "
             "alone took 15.5%, against 6.9% in 2018; whole-economy "
             "investment ran between 21.1% of GDP in 2006 and 26.9% in "
             "2008; public investment was 2.5% of GDP in the six years the "
             "OECD series covers, 2007–2012."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — One Customer Takes a Third of the Goods",
         subtitle="Exports and imports of goods and services on the "
                  "national-accounts basis, and the 2024 customs snapshot "
                  "of where the goods went.",
         source="Sources: World Bank WDI (national accounts) · UN Comtrade, "
                "Chile as reporter, 2024 (Aduanas declarations)",
         alt="Four panels on Chilean trade. Exports peaked at 45.1% of GDP "
             "in 2007 and were 34.6% in 2025; the balance swung from a "
             "surplus of 14.0% of GDP in 2006 to a deficit of 4.0% in 2022; "
             "the annual destination series is pending; the 2024 snapshot "
             "shows China taking 37.8% of goods exports, the United States "
             "15.9% and Japan 8.4%."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Markets — The Rate, the Peso, and Two Holes in the Record",
         subtitle="The Banco Central's policy rate and the peso, with the "
                  "two panels Chile's closed data routes leave pending.",
         source="Sources: BIS WS_CBPOL (the Banco Central's daily target) · "
                "World Bank PA.NUS.FCRF · Banco Central and Bolsa de "
                "Santiago pending",
         alt="Two drawn panels and two pending on Chilean markets. The "
             "policy rate averaged 5.0% in 2006, 0.8% in 2020 and 10.5% in "
             "2023 against inflation of 4.2% in 2025; the peso went from "
             "530 per dollar in 2006 to 951 in 2025, holding 56 of its 2006 "
             "value on the rebased index. The 10-year yield and the equity "
             "index stay pending."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — Households Borrowed More Every Year Until 2020",
         subtitle="Household credit from all sources, year-end stock, on "
                  "the BIS total-credit series. The CMF's lending rate and "
                  "arrears series are on closed routes.",
         source="Sources: BIS total credit WS_TC Q.CL.H.A.M.770.A · CMF "
                "lending rate and non-performing loans pending",
         alt="One drawn panel and two pending on Chilean credit. Household "
             "debt rose from 26.4% of GDP at the end of 2006 to a peak of "
             "48.3% in 2020, then fell to 43.8% in 2025; the household "
             "lending rate and the non-performing-loan ratio stay pending "
             "because the CMF's statistics are HTML or behind a 403."),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="People — Inequality and Poverty, Measured Nine Times",
         subtitle="CASEN's biennial observations, never interpolated: the "
                  "income Gini and both poverty lines. The statutory "
                  "minimum wage is pending.",
         source="Sources: World Bank WDI from CASEN (Gini, national poverty "
                "line) and PIP (US$8.30 a day) · Dirección del Trabajo "
                "pending",
         alt="Two drawn panels and one pending on Chile's people. The Gini "
             "fell from 47.7 in 2006 to 43.0 in 2024 across nine CASEN "
             "surveys, with a rise to 47.0 in 2020; poverty on the national "
             "line fell from 28.7% in 2006 to 6.5% in 2022, while the "
             "US$8.30-a-day line reads 4.5% in 2024; the minimum wage panel "
             "is pending."),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="Chile in the World — Size, Development and Reserves",
         subtitle="Nominal dollar GDP, the UNDP index, Transparency "
                  "International's score and the reserves, on international "
                  "definitions.",
         source="Sources: World Bank WDI (GDP, reserves) · UNDP HDR 2025 · "
                "Transparency International CPI 2025",
         alt="Four panels placing Chile among other countries. Nominal GDP "
             "in dollars went from US$153.8bn in 2006 to US$357.4bn in "
             "2025; the Human Development Index went from 0.804 in 2006 to "
             "0.878 in 2023; the Corruption Perceptions Index from 72 in "
             "2012 to 63 in 2025; reserves from US$19.4bn to US$49.4bn."),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — A Fertility Collapse and a Migration Wave",
         subtitle="Population, fertility, births and deaths, and the two "
                  "components of growth, on the UN and INE series the World "
                  "Bank republishes.",
         source="Sources: World Bank WDI (UN WPP and the INE projection) · "
                "UN net migration",
         alt="Four panels on Chile's demography. Population rose 20% over "
             "the window, to 19.9 million in 2025; the total fertility rate "
             "fell from 1.80 in 2006 to 1.14 in 2024, below replacement "
             "throughout; births fell from 14.0 to 8.7 per 1,000 while "
             "deaths rose from 5.8 in 2010 to 7.7 in 2021; natural increase "
             "fell from 8.6 to 2.1 per 1,000 as net migration peaked at "
             "12.6 in 2018."),
    dict(id="10", slug="security", topic="security", builder=plate_security,
         title="Security — Homicide Rose After 2019",
         subtitle="The UNODC and WHO series the World Bank carries: "
                  "homicide, suicide and road deaths, all per 100,000.",
         source="Sources: UNODC and WHO via the World Bank WDI · "
                "Carabineros/PDI and Fiscalía counts pending",
         alt="Three panels on Chilean security. The homicide rate fell to "
             "2.3 per 100,000 in 2015, then rose to 4.8 in 2019 and 6.8 in "
             "2022 before 6.4 in 2023, where the UNODC series stops; the "
             "suicide rate fell from 12.8 in 2009 to 7.7 in 2021; road "
             "deaths went from 18.7 in 2006 to 14.9 in 2019, where the WHO "
             "series stops."),
    dict(id="11", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — The Pandemic's Excess Deaths",
         subtitle="The one official series here: MINSAL/DEIS's registered "
                  "deaths, with the World Bank's rate on the UN population "
                  "beside it and never joined to it.",
         source="Sources: MINSAL/DEIS weekly deaths via datos.gob.cl "
                "(official) · World Bank SP.DYN.CDRT.IN · WHO and INE "
                "cause-of-death pending",
         alt="Three drawn panels and one pending on mortality. The national "
             "crude death rate was 5.72 per 1,000 in 2019 and 6.98 in 2021; "
             "registered deaths ran 29.9% above the 2015–2019 average in "
             "2021 and 21.5% in 2025; the fourth panel counts 137,267 deaths "
             "in 2021 against a baseline of 105,681. COVID-19 deaths by "
             "cause stay pending."),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — A Wave That Arrived in 2016",
         subtitle="The UN's net-migration estimate and foreign-born stock, "
                  "with the persons-per-year reading in the lens. The "
                  "register's gross flows are pending.",
         source="Sources: World Bank WDI (UN WPP net migration, UN migrant "
                "stock) · SERMIG and INE flows pending",
         alt="Three drawn panels and one pending on migration. Net "
             "migration rose from 1.1 per 1,000 in 2006 to 12.6 in 2018 and "
             "2.6 in 2025; the foreign-born share of the population rose "
             "from 2.1% in 2010 to 7.8% in 2024 on the five-year UN stock; "
             "the lens shows 237,807 net arrivals in 2018 and 26,042 in "
             "2020. Gross immigration and emigration flows stay pending."),
)
