"""The Singapore plates, on the plate spine.

Twelve chapters, one per spine topic this city-state can carry. Three of
them are shaped by what Singapore is rather than by what the atlas usually
expects of a country, and those decisions are made here rather than in the
page copy:

  * **A city-state's trade does not fit a country's scale.** Exports of
    goods and services run at 163-229% of GDP, because a refinery-port
    re-exports what it imports. The canonical slot's shared range is
    0-100% of GDP, so the slot stays visibly pending with the extent on
    the panel and both lines are drawn in the lens, on their own axis.
    Extending one country's scale would put every other country's line in
    the bottom third of the same pixels.

  * **Two counts, two denominators, one country.** Vital rates are per
    RESIDENT (the publisher's own definition); murder, suicide and every
    crime rate here are per TOTAL population, because those counts cover
    everyone present. The plates name the denominator on the panel, and
    DATA_NOTES.md section 6 records the two checks that pinned it.

  * **There is no policy interest rate.** MAS manages a trade-weighted
    exchange-rate band. The markets slot says so instead of borrowing
    another country's rate.

Two more canonical slots are staged and correct but cannot be drawn on the
shared scales at all — homicide drops to 0.068 per 100,000 in 2023, below
the atlas-wide log floor of 0.1, and net migration runs from -25.6 to
+41.9 per 1,000 against a -10..+40 range. Both are reported to the
orchestrator as shared-scale requests and kept pending here rather than
clipped, and net migration is drawn in the migration lens where a
country-local axis is allowed.

Pending is a statement, not a hole: every pending panel carries the route
that was tried and the reason the number is not there, in both locales,
and the same reason appears in ui.json.
"""
from __future__ import annotations

import os
import sys

W0 = 2006

# events.py sits beside this file; render.py loads plates by path, so the
# country directory is not on sys.path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import events  # noqa: E402


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
    return dict(zip(years, vals)).get(year)


def _note(p, ax, x, y, text, ha="left", va="top", size=7.9):
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=size, style="italic", color=p.MUTED, zorder=7)


def _foot(p, ax, text):
    ax.text(0.5, -0.075, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.1, color=p.FAINT, style="italic")


def _pending(ig, ax, why):
    ax.text(0.5, 0.33, why, transform=ax.transAxes, ha="center", va="top",
            fontsize=8.0, style="italic", color=ig.p.MUTED,
            linespacing=1.35)


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(a, xticks_years=not getattr(a, "_categorical_x",
                                                      False))


def _mark(p, ax, key: str, dy: float = 0.5) -> None:
    """One of events.MARKS, drawn as a break line and its label."""
    x, label = events.MARKS[key]
    ax.axvline(x, color=p.FAINT, lw=0.9, ls=(0, (2, 2)), zorder=2)
    ax.text(x + 0.25, dy, label, transform=ax.get_xaxis_transform(),
            fontsize=7.2, color=p.MUTED, style="italic", ha="left",
            va="bottom")


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p
    E = "macro/economy.csv"

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, E, "real_growth_pct")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=True, inside=True)
    v20 = _at(gy, gv, 2020)
    ax.annotate(f"{v20:+.1f}%", (2020, v20), textcoords="offset points",
                xytext=(0, -4), ha="center", va="top", fontsize=8.8,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.30,
          f"{_at(gy, gv, 2009):+.2f}% in 2009, not a negative year —\n"
          "the recession was two quarters, banded below")
    _foot(p, ax, "SingStat chained 2015-dollar GDP, one vintage; IMF agrees "
          f"({_at(gy, gv, 2025):.1f}% in 2025)")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "world/world.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=9)
    _note(p, ax, 0.98, 0.06,
          f"US${pv[0]:,.0f} in {py[0]}, US${pv[-1]:,.0f} in {py[-1]}\n"
          "over everyone present, not residents only", ha="right",
          va="bottom")
    _foot(p, ax, "World Bank NY.GDP.PCAP.CD, current US$; the total "
          "population is the denominator")

    ax = ig.slot("economy.inflation", "Consumer price inflation (% per year)")
    cy, cv = _yr(ctx, E, "inflation_pct")
    ctx.line(ax, cy, cv, p.ALERT)
    ig.add_recessions(ax, label=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.80,
          f"peak {peak[1]:.1f}% in {peak[0]} — and no inflation target:\n"
          "MAS runs monetary policy through the exchange-rate\n"
          "band, not a rate", size=7.6)
    _foot(p, ax, "SingStat 2024-base CPI, calendar-year mean, one vintage; "
          f"IMF agrees ({cv[-1]:.1f}% in {cy[-1]})")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    uy, uv = _yr(ctx, E, "unemployment_total_sa_pct")
    ctx.line(ax, uy, uv, p.BLUE_D)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, uy, uv, p.BLUE_D, lambda v: f"{v:.1f}%", dy=9)
    _note(p, ax, 0.02, 0.55,
          f"{uv[-1]:.1f}% at end-June {uy[-1]} — a point reading,\n"
          "dashed; the annual line ends in 2025", size=7.6)
    _, iv = _yr(ctx, E, "unemployment_ilo_pct_wb")
    _foot(p, ax, "SingStat seasonally adjusted LFS; the ILO-modeled series "
          f"is higher — {iv[iv.index(max(iv))]:.1f}% in 2006")
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p
    W = "world/world.csv"

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, W, "gdp_usd")
    gb = [v / 1e9 for v in gv]
    ctx.line(ax, gy, gb, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gb, p.BLUE, lambda v: f"US${v:,.0f}bn", dy=9)
    _note(p, ax, 0.02, 0.22,
          f"US${gb[0]:,.0f}bn in {gy[0]},\nUS${gb[-1]:,.0f}bn in {gy[-1]}",
          size=7.6)
    _foot(p, ax, "World Bank current US$; the S$ line is in the fiscal and "
          "credit panels")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, W, "hdi")
    ctx.line(ax, hy, hv, p.GREEN)
    ctx.endlabel(ax, hy, hv, p.GREEN, lambda v: f"{v:.3f}", dy=9)
    _note(p, ax, 0.02, 0.30, f"{hv[0]:.3f} in {hy[0]}, {hv[-1]:.3f} in "
          f"{hy[-1]} —\none HDR vintage, and it stops there", size=7.6)
    _foot(p, ax, "UNDP Human Development Report 2025")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (0–100)")
    ctx.pending(ax)
    _pending(ig, ax, "Transparency International's workbook answers 403\n"
             "(S3 AccessDenied) to this network on 2026-10-25.\n"
             "No proxy is substituted for a perception index.")
    _foot(p, ax, "SOURCES.yaml meta.pending — retry at fetch time")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn, year-end)")
    ry, rv = _yr(ctx, W, "reserves_usd")
    rb = [v / 1e9 for v in rv]
    ctx.line(ax, ry, rb, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rb, p.TEAL, lambda v: f"US${v:,.0f}bn", dy=9)
    _note(p, ax, 0.02, 0.22,
          f"US${rb[0]:,.0f}bn in {ry[0]},\nUS${rb[-1]:,.0f}bn in {ry[-1]}",
          size=7.6)
    _foot(p, ax, "World Bank (MAS year-end reserves, converted at the "
          "year's average rate)")
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p
    D = "demography/demography.csv"

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    series = [("population_total", p.BLUE, "Everyone present"),
              ("population_resident", p.GOLD, "Residents (citizens + PRs)"),
              ("population_citizen", p.TEAL, "Citizens")]
    last = {}
    for col, colour, label in series:
        ys, vs = _yr(ctx, D, col)
        iy, iv = ctx.index_2006(dict(zip(ys, vs)))
        ctx.line(ax, iy, iv, colour, label=label)
        last[col] = (ys[-1], vs[-1], iv[-1])
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    _note(p, ax, 0.98, 0.06,
          f"{last['population_total'][1] / 1e6:.2f}m present in "
          f"{last['population_total'][0]},\n"
          f"{last['population_resident'][1] / 1e6:.2f}m resident, "
          f"{last['population_citizen'][1] / 1e6:.2f}m citizens",
          ha="right", va="bottom", size=7.5)
    _foot(p, ax, "SingStat mid-year population; the non-resident stock "
          "alone more than doubled")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    ty, tv = _yr(ctx, D, "tfr")
    ctx.line(ax, ty, tv, p.CRIMSON)
    ax.axhline(2.1, color=p.FAINT, lw=0.9, ls=(0, (5, 3)), zorder=2)
    ax.text(2006.4, 2.16, "replacement, 2.1", fontsize=7.4, color=p.MUTED,
            style="italic")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ty, tv, p.CRIMSON, lambda v: f"{v:.2f}", dy=-16)
    _note(p, ax, 0.02, 0.55, f"{tv[0]:.2f} in {ty[0]} to {tv[-1]:.2f} in "
          f"{ty[-1]} —\nthe lowest in the atlas", size=7.6)
    _foot(p, ax, "SingStat; the World Bank republication agrees for 2024")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    by, bv = _yr(ctx, D, "crude_birth_rate_per_1000")
    dy, dv = _yr(ctx, D, "crude_death_rate_per_1000")
    ctx.line(ax, by, bv, p.GREEN, label="Births")
    ctx.line(ax, dy, dv, p.ALERT, label="Deaths")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="center right", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.97, "per resident — the publisher's own\n"
          "denominator, not everyone present", size=7.5)
    _foot(p, ax, "SingStat resident rates; deaths per 1,000 of everyone "
          "present would be 4.3 in 2025, not 6.0")

    ax = ig.slot("demography.natural_migration",
                 "Natural increase (per 1,000 people)")
    ni_y, ni_v = _yr(ctx, D, "natural_increase_residents")
    rs_y, rs_v = _yr(ctx, D, "population_resident")
    res = dict(zip(rs_y, rs_v))
    pts = [(y, v / res[y] * 1000) for y, v in zip(ni_y, ni_v) if y in res]
    ctx.line(ax, [y for y, _ in pts], [v for _, v in pts], p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, [y for y, _ in pts], [v for _, v in pts], p.PURPLE,
                 lambda v: f"{v:+.1f}", dy=9)
    _note(p, ax, 0.02, 0.97, "net migration cannot share this scale —\n"
          "it is in the migration plate's lens", size=7.5)
    _foot(p, ax, "Natural increase of residents ÷ mid-year resident "
          "population; births minus deaths, same table")
    _finish(ctx, ig)


# ------------------------------------------------------------------- people
def plate_people(ctx, ig) -> None:
    p = ctx.p
    I = "people/income.csv"

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100)")
    by, bv = _yr(ctx, I, "gini_before_taxes_transfers")
    ay, av = _yr(ctx, I, "gini_after_taxes_transfers")
    ctx.line(ax, by, [v * 100 for v in bv], p.CRIMSON,
             label="Before taxes and transfers")
    ctx.line(ax, ay, [v * 100 for v in av], p.TEAL,
             label="After taxes and transfers")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    gap = bv[-1] * 100 - av[-1] * 100
    _note(p, ax, 0.02, 0.30,
          f"{bv[-1] * 100:.1f} before, {av[-1] * 100:.1f} after in {ay[-1]}:\n"
          f"the {gap:.1f}-point gap is the transfers' effect", size=7.6)
    _foot(p, ax, "SingStat M810361, resident employed households, employment "
          "income; published 0–1, ×100 here. No World Bank Gini exists")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    ctx.pending(ax)
    _pending(ig, ax, "Not applicable: Singapore has no official poverty\n"
             "line and publishes no poverty headcount. It reports income\n"
             "deciles, ComCare caseloads and Workfare instead.")
    _foot(p, ax, "A finding, not a fetch failure — SOURCES.yaml meta.pending")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    ctx.pending(ax)
    _pending(ig, ax, "Not applicable: Singapore has no statutory\n"
             "national minimum wage. The Progressive Wage Model sets\n"
             "sectoral floors and is not converted into one.")
    _foot(p, ax, "A finding, not a fetch failure — SOURCES.yaml meta.pending")

    ax = ig.slot("people.lens", "Median monthly income per household member "
                 "(S$)", unit=False)
    my, mv = _yr(ctx, I, "median_income_per_member_sgd")
    ctx.line(ax, my, mv, p.GOLD)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.97,
          f"S${mv[0]:,.0f} in {my[0]}, S${mv[-1]:,.0f} in {my[-1]} —\n"
          "nominal, so it is not a real-income series", size=7.6)
    _foot(p, ax, "SingStat median employment income per household member, "
          "resident employed households")
    _finish(ctx, ig)


# ------------------------------------------------------------------ fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p
    I = "fiscal/imf_general_government.csv"

    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure "
                 "(% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, "The IMF carries expenditure, balance and debt for\n"
             "Singapore but publishes no revenue series (DataMapper `rev`\n"
             "and the Fiscal Monitor revenue line are empty). The national\n"
             "cash budget is a 1 April–31 March cash series, so it cannot\n"
             "fill a calendar-year general-government slot.")
    _foot(p, ax, "Revenue is not derived as expenditure minus balance — "
          "that would invent precision")

    ax = ig.slot("fiscal.balance", "Overall balance (% of GDP)")
    by, bv = _yr(ctx, I, "balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    v20 = _at(by, bv, 2020)
    ax.annotate(f"{v20:+.1f}%", (2020, v20), textcoords="offset points",
                xytext=(0, -4), ha="center", va="top", fontsize=8.6,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.30, "a surplus in every year but 2009 and 2020:\n"
          "the budget is not where the debt comes from", size=7.5)
    _foot(p, ax, "IMF WEO general government, calendar years. No primary "
          "balance is published for Singapore")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    gy, gv = _yr(ctx, I, "debt_pct_gdp")
    ctx.line(ax, gy, gv, p.PURPLE, label="IMF general government")
    n_y, n_v = _yr(ctx, "fiscal/debt_national.csv", "total_debt_sgd_mn")
    gdp = dict(zip(*_yr(ctx, "macro/economy.csv", "gdp_current_sgd_mn")))
    nat = [(y, v / gdp[y] * 100) for y, v in zip(n_y, n_v) if y in gdp]
    ctx.line(ax, [y for y, _ in nat], [v for _, v in nat], p.GOLD,
             label="National gross stock ÷ calendar GDP")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _note(p, ax, 0.98, 0.06,
          "GROSS, NO OFFSET: the securities are issued to hold\n"
          "CPF liabilities and build the reserves — no net\n"
          "debt series is published on any route probed",
          ha="right", va="bottom", size=7.4)
    _foot(p, ax, "IMF GGXWDG_NGDP and the national end-year stock over "
          "calendar GDP; two perimeters, drawn apart")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, "The IMF's interest indicator (`ie`) is empty for\n"
             "Singapore while expenditure, balance and debt are populated,\n"
             "and no national interest-paid ratio is staged. Not derived\n"
             "from the debt stock.")
    _foot(p, ax, "The budget's return comes from the Net Investment "
          "Returns Contribution, not from interest")
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
def plate_spending(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("spending.by_function", "Spending by function, stacked "
                 "(% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, "No COFOG: OECD table 11 returns NoRecordsFound for\n"
             "Singapore — it is not an OECD member — and the IMF's COFOG\n"
             "route exposes no artefact. The national ministry\n"
             "classification is not relabelled as COFOG.")
    _foot(p, ax, "SOURCES.yaml meta.pending — the ministry heads are the "
          "national presentation, a different function set")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, "Without COFOG there is no social-protection\n"
             "function. In Singapore's own classification that spending\n"
             "runs through Education, Health, Social and Family\n"
             "Development and Manpower, so a two-way split would invent\n"
             "a perimeter the publisher does not use.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(% of GDP)")
    iy, iv = _yr(ctx, "macro/economy.csv", "gfcf_pct_gdp_wb")
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.TEAL, lambda v: f"{v:.1f}%", dy=9)
    _note(p, ax, 0.02, 0.30,
          f"{iv[-1]:.1f}% in {iy[-1]} —\ngross fixed capital formation, "
          "whole economy", size=7.6)
    _foot(p, ax, "World Bank NE.GDI.FTOT.ZS, a harmonised comparator in "
          "macro/economy.csv; not a national-accounts series")

    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, "No government fixed-capital-formation series is\n"
             "published. The capital budget — development expenditure —\n"
             "is on a 1 April–31 March year with no published fiscal-year\n"
             "GDP, and a fiscal-year flow is not put over a calendar-year\n"
             "denominator here.")
    _foot(p, ax, "SOURCES.yaml meta.pending — spending/development_by_head.csv "
          "is staged and undrawn")
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
def plate_trade(ctx, ig) -> None:
    p = ctx.p
    T = "trade/trade.csv"

    xy, xv = _yr(ctx, T, "exports_pct_gdp")
    my, mv = _yr(ctx, T, "imports_pct_gdp")

    ax = ig.slot("trade.exports_imports", "Exports and imports (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, f"Staged and correct, but outside the shared scale:\n"
             f"exports run {max(xv):.0f}% of GDP and imports {max(mv):.0f}% "
             f"at their peak,\n"
             "against an atlas-wide 0–100% range for this slot. Both\n"
             "lines are drawn in the lens below, on their own axis.")
    _foot(p, ax, "SingStat national accounts, goods AND services, one "
          "vintage; not customs merchandise trade")

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    by, bv = _yr(ctx, T, "balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    peak = max(zip(by, bv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.30,
          f"a surplus throughout, {peak[1]:.1f}% in {peak[0]}: the\n"
          "re-export margin, not a goods-producing surplus", size=7.5)
    _foot(p, ax, "Derived: exports minus imports, same SingStat table and "
          "vintage")

    ax = ig.slot("trade.destinations",
                 "Top export destinations (% of goods exports)")
    t = ctx.table("trade/partners.csv")
    regions = {"America", "Asia", "Europe", "Oceania", "Africa"}
    shares = {}
    if t:
        for y, mk, sh in zip(t["year"], t["market"], t["share_of_exports_pct"]):
            if mk in regions or sh != sh:
                continue
            shares.setdefault(mk, {})[y] = sh
    latest = max(y for mk in shares for y in shares[mk])
    top = sorted(shares, key=lambda k: shares[k].get(latest, 0),
                 reverse=True)[:5]
    for i, name in enumerate(top):
        pts = sorted(shares[name].items())
        ctx.line(ax, [y for y, _ in pts], [v for _, v in pts], p.cycle(i),
                 label=name)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.1, ncol=2, frameon=False)
    _note(p, ax, 0.98, 0.30,
          "region rows are aggregates of the markets\n"
          "beneath them and are never added to them",
          ha="right", va="top", size=7.3)
    _foot(p, ax, "SingStat M451521 customs exports — domestic plus "
          "re-exports — over Total All Markets, same year")

    ax = ig.slot("trade.lens", "Lens — exports and imports of goods and "
                 "services (% of GDP, own scale)", unit=False)
    ctx.line(ax, xy, xv, p.BLUE, label="Exports")
    ctx.line(ax, my, mv, p.ALERT, label="Imports")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.4, frameon=False)
    _note(p, ax, 0.98, 0.97,
          f"{xv[-1]:.0f}% and {mv[-1]:.0f}% of GDP in {xy[-1]}:\n"
          "a port that re-exports what it imports", ha="right", size=7.6)
    _foot(p, ax, "The canonical slot's series, drawn here because the "
          "shared 0–100% scale cannot hold them")
    _finish(ctx, ig)


# ----------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p
    M = "markets/markets.csv"

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ctx.pending(ax)
    _pending(ig, ax, "There is no policy interest rate. MAS sets the\n"
             "slope, width and level of a trade-weighted exchange-rate\n"
             "band (S$NEER). SORA is a money-market benchmark the\n"
             "publisher reports, and it is not relabelled as a policy\n"
             "rate here; nor is another country's rate imported.")
    _foot(p, ax, "A finding, not a gap — SOURCES.yaml meta.pending")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    by, bv = _yr(ctx, M, "govt_bond_10y_pct")
    ctx.line(ax, by, bv, p.BLUE_D)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.28,
          f"{bv[-1]:.2f}% in {by[-1]}, from {max(bv):.2f}% in "
          f"{by[bv.index(max(bv))]} —\na market series, not a policy rate",
          size=7.6)
    _foot(p, ax, "SingStat M700071, annual mean of the benchmark 10-year "
          "SGS yield")

    ax = ig.slot("markets.currency", "S$ against the US$ "
                 "(index 2006 = 100, up = stronger)")
    fy, fv = _yr(ctx, M, "sgd_per_usd")
    iy, iv = ctx.fx_index(dict(zip(fy, fv)))
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.98, 0.06,
          f"S${_at(fy, fv, fy[0]):.2f} per dollar in {fy[0]},\n"
          f"S${fv[-1]:.2f} in {fy[-1]}: index {iv[-1]:.0f} — the band did the work",
          ha="right", va="bottom", size=7.5)
    _foot(p, ax, "SingStat annual average, inverted so a rise is a "
          "stronger Singapore dollar")

    ax = ig.slot("markets.equities", "Main equity index in US$ "
                 "(index 2006 = 100, in US$)")
    ctx.pending(ax)
    _pending(ig, ax, "The Straits Times Index is not staged: a US$ index\n"
             "at 2006 = 100 needs the index history and each year's\n"
             "exchange rate reconciled on one vintage, and it would be a\n"
             "redistributor (official: false).")
    _foot(p, ax, "SOURCES.yaml meta.pending — Yahoo answers, stooq is "
          "JavaScript-walled from this network")
    _finish(ctx, ig)


# ------------------------------------------------------------------ credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p
    C = "credit/household.csv"

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    ny, nv = _yr(ctx, C, "liabilities_pct_gdp")
    by, bv = _yr(ctx, C, "credit_pct_gdp_bis")
    ctx.line(ax, ny, nv, p.CRIMSON, label="National balance sheet")
    ctx.line(ax, by, bv, p.BLUE, label="BIS harmonised credit")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    _note(p, ax, 0.02, 0.30,
          f"{nv[-1]:.1f}% and {bv[-1]:.1f}% in {ny[-1]}: seven points,\n"
          "two perimeters, both official", size=7.6)
    _foot(p, ax, "SingStat M700981 liabilities ÷ same-year GDP, and BIS "
          "WS_TC Q4; HDB loans and non-bank lending sit in the national line")

    ax = ig.slot("credit.lending_rate", "Household lending rate vs policy "
                 "rate (%)")
    ctx.pending(ax)
    _pending(ig, ax, "MAS's statistics API serves an HTML maintenance page\n"
             "under HTTP 200 from this network, which blocks the bank\n"
             "lending-rate series. An HTML body is not parsed as data.\n"
             "Retry is one fetch from an unblocked network.")
    _foot(p, ax, "SOURCES.yaml meta.pending — and there is no policy rate "
          "to compare it with in any case")

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    ctx.pending(ax)
    _pending(ig, ax, "The same blocked MAS API carries the banks'\n"
             "non-performing-loan ratio. Nothing from that host is\n"
             "cached, and no proxy from a bank's own annual report is\n"
             "substituted for the system aggregate.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("credit.lens", "Household net worth (S$ bn)", unit=False)
    wy, wv = _yr(ctx, C, "net_worth_sgd_mn")
    wb = [v / 1000 for v in wv]
    ctx.line(ax, wy, wb, p.GOLD)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.97,
          f"S${wb[0]:,.0f}bn in {wy[0]}, S${wb[-1]:,.0f}bn in {wy[-1]} —\n"
          "the asset side the gross-debt ratio leaves out", size=7.6)
    _foot(p, ax, "SingStat household balance sheet, end-year, nominal S$")
    _finish(ctx, ig)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    S = "security/security.csv"

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    hy, hv = _yr(ctx, S, "murder_per_100k")
    ctx.line(ax, hy, hv, p.ALERT)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, hy, hv, p.ALERT, lambda v: f"{v:.2f}", dy=-14)
    _note(p, ax, 0.02, 0.96, f"{hv[-1]:.2f} per 100,000 in {hy[-1]}: four "
          "murders\non a denominator of everyone present")
    _foot(p, ax, "C&SD recorded offences ÷ total population; verified "
          "against UNODC to three decimals")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    sy, sv = _yr(ctx, S, "suicide_per_100k")
    ctx.line(ax, sy, sv, p.PURPLE, split_year=2024)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{_at(sy, sv, 2025):.1f} — preliminary", (2025, sv[-1]),
                textcoords="offset points", xytext=(-6, -2), ha="right",
                va="top", fontsize=8.2, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.97,
          f"{_at(sy, sv, 2025):.1f} in 2025 is not a decline: 256 deaths\n"
          "are coroner's cases still being assigned at publication",
          size=7.5)
    _foot(p, ax, "SingStat cause-of-death counts ÷ everyone present; the "
          "WHO series differs on the denominator")

    ax = ig.slot("security.road_deaths", "Road traffic deaths "
                 "(per 100,000)")
    ry, rv = _yr(ctx, S, "road_death_per_100k")
    ctx.line(ax, ry, rv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.GOLD, lambda v: f"{v:.2f}", dy=9)
    _note(p, ax, 0.02, 0.30,
          f"{rv[0]:.2f} in {ry[0]} to {rv[-1]:.2f} in {ry[-1]} —\n"
          "the 2025 count is not published yet", size=7.6)
    _foot(p, ax, "SingStat road-death count ÷ everyone present; WHO's "
          "modelled estimate is higher")

    ax = ig.slot("security.lens", "Recorded offences (per 100,000 people)",
                 unit=False)
    pop = dict(zip(*_yr(ctx, "demography/demography.csv", "population_total")))
    for col, colour, label in (("robbery_count", p.ALERT, "Robbery"),
                               ("housebreaking_count", p.BLUE,
                                "Housebreaking"),
                               ("serious_hurt_count", p.GOLD,
                                "Serious hurt")):
        ys, vs = _yr(ctx, S, col)
        pts = [(y, v / pop[y] * 100000) for y, v in zip(ys, vs) if y in pop]
        ctx.line(ax, [y for y, _ in pts], [v for _, v in pts], colour,
                 label=label)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    _note(p, ax, 0.02, 0.30,
          "robbery fell by an order of magnitude; violence\n"
          "did not", size=7.5)
    _foot(p, ax, "Police counts ÷ mid-year total population — everyone "
          "present, the basis the publisher's own crime rate uses")
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    M = "mortality/mortality.csv"

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000 people)")
    dy, dv = _yr(ctx, M, "crude_death_rate_per_1000")
    ctx.line(ax, dy, dv, p.INK)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.INK, lambda v: f"{v:.1f}", dy=9)
    _note(p, ax, 0.02, 0.30,
          "per resident, the publisher's own rate; an ageing\n"
          "population, not a health shock", size=7.5)
    _foot(p, ax, "SingStat resident deaths ÷ mid-year resident population; "
          "over everyone present it is 4.3 in 2025")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above 2015–2019 average)")
    dvals = dict(zip(*_yr(ctx, M, "deaths_total_by_cause")))
    base = sum(dvals[y] for y in range(2015, 2020)) / 5
    ey = [y for y in sorted(dvals) if y >= W0]
    ev = [(dvals[y] / base - 1) * 100 for y in ey]
    ctx.line(ax, ey, ev, p.ALERT)
    ig.add_recessions(ax, label=False)
    peak = max(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:+.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(-6, 6), ha="right",
                fontsize=8.4, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.98, 0.06,
          "baseline 2015–2019, unadjusted for age: deaths rise\n"
          "every year here, so part of the gap is age structure",
          ha="right", va="bottom", size=7.4)
    _foot(p, ax, "Derived from the death count, same table. Staged from "
          "2006, drawn from the baseline period: 2006 is −20.8%")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    ctx.pending(ax)
    _pending(ig, ax, "No COVID-19 line exists for Singapore. The\n"
             "publisher's broad cause groups predate the ICD-10-COVID\n"
             "code, so pandemic deaths sit inside the respiratory and\n"
             "infective groups and cannot be separated without microdata;\n"
             "WHO's GHO carries no such indicator here.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("mortality.lens", "The three big killers "
                 "(deaths per 100,000 people)")
    pop = dict(zip(*_yr(ctx, "demography/demography.csv", "population_total")))
    for col, colour, label in (("deaths_circulatory", p.CRIMSON,
                                "Circulatory"),
                               ("deaths_neoplasms", p.PURPLE, "Cancers"),
                               ("deaths_respiratory", p.TEAL,
                                "Respiratory")):
        ys, vs = _yr(ctx, M, col)
        pts = [(y, v / pop[y] * 100000) for y, v in zip(ys, vs) if y in pop]
        before = [(y, v) for y, v in pts if y <= 2011]
        after = [(y, v) for y, v in pts if y >= 2012]
        # The 2012 break is ICD-9 to ICD-10: two segments with a gap
        # between them, never one joined line.
        ax.plot([y for y, _ in before], [v for _, v in before], color=colour,
                lw=1.7, ls=(0, (1, 1)), marker="o", ms=3.4, zorder=3,
                label=label)
        ctx.line(ax, [y for y, _ in after], [v for _, v in after], colour,
                 label="_nolegend_", split_year=2024)
    ig.add_recessions(ax, label=False)
    _mark(p, ax, "icd")
    ax.legend(loc="lower right", fontsize=7.2, frameon=False)
    ax.set_ylim(0, 190)
    _note(p, ax, 0.02, 0.97,
          "2025 is preliminary: the natural-cause groups hold\n"
          "steady while the external causes are still assigned",
          size=7.4)
    _foot(p, ax, "SingStat M810131 counts ÷ everyone present; dotted is "
          "the ICD-9 coding, solid the ICD-10 one")
    _finish(ctx, ig)


# --------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    M = "migration/migration.csv"

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    ctx.pending(ax)
    _pending(ig, ax, "Not published: Singapore releases population STOCKS\n"
             "by legal status, and counts of citizenships and PRs granted,\n"
             "but no annual arrival or departure flow comparable with a\n"
             "migration register. Granting PR is not an arrival.")
    _foot(p, ax, "A finding, not a fetch failure — SOURCES.yaml meta.pending")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    mn, mv = _net(ctx)
    ctx.line(ax, mn, mv, p.BLUE)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "World Bank SM.POP.NETM (UN WPP) ÷ mid-year population — "
          "a modelled estimate, not a register count; 2020 is the border "
          "closure")

    ax = ig.slot("migration.foreign_born",
                 "Foreign citizens (% of the population)")
    dem = ctx.table("demography/demography.csv")
    ptot = dict(zip(*ctx.series(dem, "population_total")))
    pcos = dict(zip(*ctx.series(dem, "population_citizen")))
    fy = [y for y in sorted(ptot) if y in pcos and y >= W0]
    fv = [(ptot[y] - pcos[y]) / ptot[y] * 100 for y in fy]
    ctx.line(ax, fy, fv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, fy, fv, p.PURPLE, lambda v: f"{v:.1f}%", dy=9)
    _note(p, ax, 0.02, 0.30,
          f"{fv[-1]:.1f}% in {fy[-1]}: everyone who is not a citizen,\n"
          "permanent residents included", size=7.5)
    _foot(p, ax, "Derived: total population minus citizens, same table and "
          "year. No foreign-BORN count is published")

    ax = ig.slot("migration.lens", "Lens — net migration, persons per 1,000 "
                 "(own scale)", unit=False)
    ny, nv = _yr(ctx, M, "net_migration_wb")
    pop = dict(zip(*_yr(ctx, "demography/demography.csv", "population_total")))
    pts = [(y, v / pop[y] * 1000) for y, v in zip(ny, nv) if y in pop]
    ctx.bars(ax, [y for y, _ in pts], [v for _, v in pts],
             lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    low = min(pts, key=lambda t: t[1])
    high = max(pts, key=lambda t: t[1])
    _note(p, ax, 0.98, 0.97,
          f"{high[1]:+.0f} in {high[0]}, {low[1]:+.0f} in {low[0]} —\n"
          "the pass-holder cycle, then the border closure",
          ha="right", size=7.5)
    _foot(p, ax, "World Bank (UN WPP) net migration ÷ mid-year total "
          "population — modelled, not a register")
    _finish(ctx, ig)


def _net(ctx):
    ny, nv = _yr(ctx, "migration/migration.csv", "net_migration_wb")
    pop = dict(zip(*_yr(ctx, "demography/demography.csv", "population_total")))
    years = [y for y, v in zip(ny, nv) if y in pop]
    return years, [v / pop[y] * 1000 for y, v in zip(ny, nv) if y in pop]


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         filename="01-economy.png",
         title="The Economy — A City-State's Output and Its Prices",
         subtitle="Growth, income per person, prices and jobs on the shared "
                  "scale, with the exchange-rate band where a policy rate "
                  "would be.",
         source="Sources: SingStat · World Bank · IMF",
         alt="Four panels on Singapore's economy: real GDP growth bars over "
             "2006–2025 with the 2008–09 and 2020 contractions banded, GDP "
             "per person on a log scale rising from US$33,768 to US$98,814, "
             "consumer price inflation peaking at 6.6% in 2008, and the "
             "seasonally adjusted unemployment rate."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         filename="02-fiscal.png",
         title="Public Finances — A Surplus and a 166% Gross Debt",
         subtitle="General-government accounts on calendar years, with the "
                  "gross debt shown beside the national stock it comes from.",
         source="Sources: IMF WEO · SingStat",
         alt="Four panels on Singapore's public finances: revenue and "
             "expenditure pending because the IMF publishes no revenue "
             "series, the overall balance in surplus except 2009 and 2020, "
             "gross debt at 165.7% of GDP in 2025 with the no-offset note, "
             "and interest paid pending."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         filename="03-spending.png",
         title="Spending — What Has No COFOG Table and What Does",
         subtitle="The whole-economy investment rate is comparable; the "
                  "functional split has no COFOG table for a non-OECD "
                  "city-state.",
         source="Sources: World Bank · SingStat",
         alt="Four panels on spending in Singapore: spending by function "
             "pending for want of a COFOG table, social protection pending "
             "for the same reason, the whole-economy investment rate near "
             "22% of GDP, and public investment pending."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         filename="04-trade.png",
         title="Trade — Exports at 178% of a Small Economy",
         subtitle="A port re-exports what it imports, so the canonical "
                  "0–100% scale cannot hold the lines: they are drawn in "
                  "the lens, labelled.",
         source="Sources: SingStat",
         alt="Four panels on Singapore's trade: exports and imports pending "
             "because they exceed the shared percentage-of-GDP scale, the "
             "trade balance in surplus throughout, the top five goods "
             "export destinations, and a lens drawing exports and imports "
             "of goods and services on their own scale."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         filename="05-markets.png",
         title="Markets — A Band, Not a Rate",
         subtitle="Monetary policy runs through the Singapore dollar's "
                  "trade-weighted band, so the policy-rate panel says so "
                  "and the bond, the currency and the index stand alone.",
         source="Sources: SingStat M700071 and M700851",
         alt="Four panels on Singapore's markets: the policy rate pending "
             "with the exchange-rate band explained, the 10-year "
             "government bond yield falling from 3.36% to 2.30%, the "
             "Singapore dollar 22% stronger against the US dollar than in "
             "2006, and the equity index pending."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         filename="06-credit.png",
         title="Credit — Household Debt on Two Perimeters",
         subtitle="The national balance sheet and the BIS aggregate, seven "
                  "points apart, beside the assets that make the debt "
                  "serviceable.",
         source="Sources: SingStat M700981 · BIS",
         alt="Four panels on credit in Singapore: household debt at 51.6% "
             "of GDP nationally and 44.0% on the BIS aggregate, the "
             "lending rate and the non-performing ratio pending at the "
             "blocked MAS API, and household net worth reaching S$3,297 "
             "billion."),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         filename="07-people.png",
         title="People — Inequality Before and After the Transfers",
         subtitle="One survey, two coefficients, and the income per "
                  "household member behind them. Poverty and the minimum "
                  "wage have no national definition to draw.",
         source="Sources: SingStat M810361",
         alt="Four panels on people and incomes in Singapore: the Gini "
             "before and after taxes and transfers, poverty pending "
             "because no official line exists, the minimum wage pending "
             "for the same reason, and median monthly income per household "
             "member rising from S$1,448 to S$3,909."),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         filename="08-world.png",
         title="Singapore in the World — Size, Development and Reserves",
         subtitle="Current-dollar size, human development and the reserves "
                  "that back a managed currency.",
         source="Sources: World Bank · UNDP",
         alt="Four panels placing Singapore in the world: GDP at current "
             "prices rising from US$149bn to US$604bn on a log scale, the "
             "Human Development Index at 0.946 in 2023, the Corruption "
             "Perceptions Index pending, and official reserves at US$432bn."),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography, filename="09-demography.png",
         title="Demography — Three Populations, One Island",
         subtitle="Citizens, residents and everyone present are three "
                  "different denominators and are drawn as three lines.",
         source="Sources: SingStat",
         alt="Four panels on Singapore's demography: population indices for "
             "everyone present, residents and citizens; the total fertility "
             "rate falling to 0.87 against a replacement line of 2.1; crude "
             "birth and death rates per resident; and natural increase."),
    dict(id="10", slug="security", topic="security",
         builder=plate_security, filename="10-security.png",
         title="Security — A Homicide Rate Below the Atlas's Floor",
         subtitle="Per 100,000 people, on a log scale for homicide; the "
                  "2025 suicide count is preliminary and is annotated as "
                  "such.",
         source="Sources: SingStat · Singapore Police Force",
         alt="Four panels on security in Singapore: the homicide rate "
             "pending because 2023 falls below the shared log floor, the "
             "suicide rate with 2025 marked preliminary, road traffic "
             "deaths, and recorded robbery, housebreaking and serious hurt "
             "offences per 100,000 people."),
    dict(id="11", slug="mortality", topic="mortality",
         builder=plate_mortality, filename="11-mortality.png",
         title="Mortality — The Death Rate, Excess Deaths and the Causes",
         subtitle="An ageing population lifts the crude rate; the cause "
                  "groups carry the 2012 coding break as a visible seam.",
         source="Sources: SingStat M810131",
         alt="Four panels on mortality in Singapore: the crude death rate "
             "per resident rising from 4.4 to 6.0 per 1,000, excess deaths "
             "over the 2015–2019 baseline peaking at 29.9%, COVID-19 "
             "deaths pending, and circulatory, cancer and respiratory "
             "deaths per 100,000 with the 2012 ICD-9 to ICD-10 break "
             "drawn."),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration, filename="12-migration.png",
         title="Migration — Stocks by Status, Not Flows",
         subtitle="Singapore publishes who is here and on what pass, not "
                  "how many arrived; the UN estimate is drawn in a lens "
                  "outside the shared scale.",
         source="Sources: SingStat · World Bank / UN WPP",
         alt="Four panels on migration in Singapore: immigration and "
             "emigration flows pending because no register flow is "
             "published, net migration pending outside the shared scale, "
             "foreign citizens at 40% of the population, and a lens "
             "drawing net migration per 1,000 on its own scale."),
)
