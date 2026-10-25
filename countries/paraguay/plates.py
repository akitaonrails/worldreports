"""Paraguay's twelve plates, born on the shared plate spine.

Twelve chapters, and every canonical slot in them is either drawn from a
committed CSV or visibly pending, with the route that failed recorded in
`SOURCES.yaml` -> `meta.pending`. Nothing is filled from a neighbouring
country, a proxy or a model of our own.

Three seams run through the file and are drawn as seams, never joined:

- **Two fiscal perimeters.** The IMF's general government on an accrual
  basis (revenue 15-19% of GDP) and the MEF's *Administración Central* on
  a cash basis (13-15%) sit about four points of GDP apart. They are two
  labelled pairs of lines in one slot, and the national line is the one
  that carries Itaipú and Yacyretá.
- **Two population denominators, 9% apart.** INE's revision-2024 series
  is anchored on the 2022 census (6,417,076 in 2025); the UN World
  Population Prospects series the World Bank carries is not (7,013,000).
  The demography plate draws both as indices, and the migration plate
  divides each publisher's net migration by that publisher's own
  population, so no rate here mixes the two.
- **Itaipú and Yacyretá are fiscal revenue, not hydro output.** The
  royalties and the energy-cession compensation are revenue lines of the
  central administration under the binational treaties. They are drawn in
  the trade lens because that is where a reader looks for the
  electricity, and labelled there as fiscal revenue rather than as a
  share of GDP produced by water.

Every note is written as complete clauses on separate lines: a line is
the unit `core.i18n` translates, and a sentence broken mid-word cannot be
translated into Spanish or Portuguese without inventing the join. A line
also never ends on a number, because the number carries the punctuation
into the catalog key.
"""
from __future__ import annotations

from core.sideload import sibling

events = sibling(__file__, "events")

W0 = 2006   # the shared plate window opens here
W1 = 2026   # and closes here; the INE projection runs to 2050


# ------------------------------------------------------------ small helpers
def _yr(ctx, rel: str, col: str, since: int = W0, until: int = W1):
    """(years, values) from a calendar-year CSV, blanks dropped.

    Both ends are clipped: the INE projection file runs to 2050 and the
    poverty column starts in 2002, and neither belongs on a plate whose
    axis is 2006-2026.
    """
    t = ctx.table(rel)
    if not t or col not in t:
        return [], []
    yrs, vals = ctx.series(t, col)
    keep = [(y, v) for y, v in zip(yrs, vals) if since <= y <= until]
    return [y for y, _ in keep], [v for _, v in keep]


def _at(years, vals, year):
    return dict(zip(years, vals))[year]


def _note(p, ax, x, y, text, ha="left", va="top", size=8.0):
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=size, style="italic", color=p.MUTED, zorder=7)


def _foot(p, ax, text):
    ax.text(0.5, -0.07, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.2, color=p.FAINT, style="italic")


def _pending(ig, ax, *lines):
    """The reason a canonical slot has no series, in the panel itself."""
    ax.text(0.5, 0.36, "\n".join(lines), transform=ax.transAxes, ha="center",
            va="top", fontsize=8.2, style="italic", color=ig.p.MUTED)


def _mark(ig, ax, key, dy=0.55):
    x, label = events.MARKS[key]
    ig.add_event(ax, x, label, dy=dy)


def _barkey(ax, color, label):
    """A legend entry for a bar series (bars themselves carry no label)."""
    ax.bar([], [], color=color, label=label)


def _bands_named(ig, ax, y, p):
    """The recession bands with their names at `y` axes fraction.

    `add_recessions(label=True)` writes the names just above the axes,
    where they compete with the panel title; slot 1 of the economy plate
    has room inside the frame instead, above the tallest bar and below
    the title.
    """
    ig.add_recessions(ax, label=False)
    for start, end, name in ig.country.recessions:
        ax.text((start + end) / 2, y, name,
                transform=ax.get_xaxis_transform(), ha="center",
                va="bottom", fontsize=7.8, color=p.MUTED, style="italic")


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(a)


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p
    E = "macro/economy.csv"

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, E, "gdp_growth_pct")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.RED)
    _bands_named(ig, ax, 0.93, p)
    v20 = _at(gy, gv, 2020)
    ax.annotate(f"{v20:.1f}%", (2020, v20), textcoords="offset points",
                xytext=(0, -3), ha="center", va="top", fontsize=8.8,
                fontweight="bold", color=p.RED)
    peak = max(zip(gy, gv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.04, f"The {peak[0]} rebound reached {peak[1]:.1f}%, "
          "after the 2009 drought.\n"
          f"{_at(gy, gv, 2022):.2f}% in 2022 was a stagnation, not a "
          "recession:\nit is not banded.", va="bottom")
    _foot(p, ax, "World Bank national accounts; the IMF WEO is the "
          "independent check")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, E, "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=9)
    _note(p, ax, 0.02, 0.04,
          f"US${pv[0]:,.0f} in {py[0]} — the dollar value is flat\n"
          "where output grew, because the guaraní went the other way.",
          va="bottom")
    _foot(p, ax, "World Bank, current US$. Divided by the UN population, "
          "not INE's")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year)")
    cy, cv = _yr(ctx, E, "cpi_inflation_pct")
    ctx.line(ax, cy, cv, p.RED)
    ig.add_recessions(ax, label=False)
    pk = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}%", pk, textcoords="offset points",
                xytext=(0, 7), ha="center", va="bottom", fontsize=8.8,
                fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.96,
          f"The peak of {pk[1]:.1f}% came in {pk[0]} before the "
          f"{_at(cy, cv, 2022):.1f}% spike —\nno year in the window "
          "deflated.")
    _foot(p, ax, "The BCP's CPI as the IMF IFS carries it, identical to the "
          "World Bank's series")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of labour force)")
    uy, uv = _yr(ctx, E, "unemployment_pct")
    iy, iv = _yr(ctx, E, "unemployment_ine_pct")
    ctx.line(ax, uy, uv, p.INDIGO, label="ILO modelled")
    ctx.line(ax, iy, iv, p.GOLD, label="INE EPHC, from 2017")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    _note(p, ax, 0.02, 0.96, "Two measures of one thing: the survey starts "
          "at the\n2017 redesign, so the ILO model carries the earlier "
          "years.", size=7.8)
    _foot(p, ax, "World Bank (ILO modelled) and INE's EPHC annual mean")
    _finish(ctx, ig)


# ------------------------------------------------------------------ fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p
    F = "fiscal/fiscal.csv"
    N = "fiscal/fiscal_national.csv"

    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure "
                 "(% of GDP)")
    ry, rv = _yr(ctx, F, "revenue_pct_gdp")
    ey, ev = _yr(ctx, F, "expenditure_pct_gdp")
    ny, nv = _yr(ctx, N, "revenue_pct_gdp")
    my, mv = _yr(ctx, N, "expenditure_pct_gdp")
    ctx.line(ax, ry, rv, p.TEAL, label="General government, revenue")
    ctx.line(ax, ey, ev, p.RED, label="General government, expenditure")
    ctx.line(ax, ny, nv, p.TEAL, lw=1.5, ms=2.8, ls=(0, (1, 1.5)),
             dashed_partial=False, label="Central administration, revenue")
    ctx.line(ax, my, mv, p.RED, lw=1.5, ms=2.8, ls=(0, (1, 1.5)),
             dashed_partial=False, label="Central administration, spending")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=6.6, ncol=2, frameon=False)
    _note(p, ax, 0.98, 0.52,
          f"The gap in {ey[-1]} is the perimeter: {_at(ey, ev, ey[-1]):.1f}% "
          "of GDP\n"
          f"on an accrual basis against {_at(my, mv, ey[-1]):.1f}% in the "
          "Treasury's\ncash books. Two definitions, never spliced.", ha="right")
    _foot(p, ax, "IMF WEO general government; MEF MEFP 2001 central "
          "administration, cash")

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    by, bv = _yr(ctx, F, "balance_pct_gdp")
    py, pv = _yr(ctx, F, "primary_balance_pct_gdp")
    ly, lv = _yr(ctx, N, "net_lending_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.RED)
    ctx.line(ax, py, pv, p.INDIGO, label="Primary balance (before interest)")
    ctx.line(ax, ly, lv, p.GOLD, lw=1.5, ms=2.8, ls=(0, (1, 1.5)),
             dashed_partial=False, label="MEF net lending, cash")
    _barkey(ax, p.RED, "Overall balance, accrual")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=6.8, frameon=False)
    low = min(zip(by, bv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.55, f"{low[0]} was the pandemic year: the only "
          f"deficit\nbeyond {abs(low[1]):.0f}% of GDP in the window, and "
          "the cash line\ngoes further still.")
    _foot(p, ax, "IMF WEO general government; the third line is the MEF's "
          "own cash balance")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    dy, dv = _yr(ctx, F, "debt_pct_gdp")
    ctx.line(ax, dy, dv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.PURPLE, lambda v: f"{v:.0f}%", dy=-16)
    _note(p, ax, 0.02, 0.96, f"{_at(dy, dv, 2008):.0f}% in 2008 to "
          f"{_at(dy, dv, 2024):.0f}% in 2024 —\n"
          f"{_at(dy, dv, 2024) - _at(dy, dv, 2008):.0f} points up in sixteen "
          "years, and still rising.")
    _foot(p, ax, "IMF WEO general government gross debt, one vintage")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    iy, iv = _yr(ctx, F, "interest_pct_gdp")
    ctx.line(ax, iy, iv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.GOLD, lambda v: f"{v:.1f}%", dy=9)
    _note(p, ax, 0.02, 0.96,
          f"Interest cost {iv[0]:.1f}% of GDP in {iy[0]} against "
          f"{iv[-1]:.1f}% in {iy[-1]} —\nit rose with the debt, and it is "
          "not going away.")
    _foot(p, ax, "IMF WEO general government")
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
def plate_spending(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("spending.by_function",
                 "Spending by function, stacked (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax,
             "No functional (COFOG) series is published for Paraguay.",
             "The IMF's GFS_COFOG answers for 2023-24 only,",
             "the MEF prints the classification in budget documents,",
             "and datos.gov.py has been on a maintenance page.",
             "Two years is not a panel, and no national mapping",
             "is invented to fill one.")
    _foot(p, ax, "SOURCES.yaml meta.pending — every route tried, with dates")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax,
             "This panel needs the same missing classification.",
             "Without the COFOG split it cannot say what social",
             "protection costs. The two investment panels beside",
             "it are drawn, so the chapter is not empty.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(% of GDP)")
    iy, iv = _yr(ctx, "spending/spending.csv", "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.TEAL, lambda v: f"{v:.1f}%", dy=9)
    _note(p, ax, 0.02, 0.96, f"{iv[-1]:.1f}% of GDP in {iy[-1]} —\n"
          "whole-economy fixed investment, not the budget.")
    _foot(p, ax, "World Bank national accounts (gross fixed capital "
          "formation)")

    ax = ig.slot("spending.public_investment",
                 "Public investment (% of GDP)")
    cy, cv = _yr(ctx, "spending/spending.csv", "public_investment_pct_gdp")
    ctx.line(ax, cy, cv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, cy, cv, p.GOLD, lambda v: f"{v:.1f}%", dy=-16)
    _note(p, ax, 0.02, 0.96,
          "The central government's own fixed assets: "
          f"{cv[-1]:.1f}%\nof GDP in {cy[-1]} — a subset of the panel on the "
          "left.", size=7.8)
    _foot(p, ax, "MEF 'Activos fijos' — net acquisition of fixed assets, "
          "central administration")
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
def plate_trade(ctx, ig) -> None:
    p = ctx.p
    T = "trade/trade.csv"

    ax = ig.slot("trade.exports_imports", "Exports and imports (% of GDP)")
    xy, xv = _yr(ctx, T, "exports_pct_gdp")
    my, mv = _yr(ctx, T, "imports_pct_gdp")
    ctx.line(ax, xy, xv, p.BLUE, label="Exports")
    ctx.line(ax, my, mv, p.RED, label="Imports")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.05,
          f"Exports were {xv[0]:.1f}% of GDP in {xy[0]} and "
          f"{xv[-1]:.1f}% in {xy[-1]} —\ngoods AND services, so Itaipú's "
          "electricity to Brazil\nand Argentina is inside them.", va="bottom")
    _foot(p, ax, "World Bank national accounts; the partner panel is customs "
          "goods")

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    by, bv = _yr(ctx, T, "balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.RED)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{bv[-1]:.1f}%", (by[-1], bv[-1]), textcoords="offset points",
                xytext=(-4, -3), ha="right", va="top", fontsize=8.6,
                fontweight="bold", color=p.RED)
    first_deficit = next(y for y, v in zip(by, bv) if v < 0)
    _note(p, ax, 0.02, 0.96, "A surplus every year to 2021\n"
          f"then a deficit in {first_deficit}: imports rose while\n"
          "exports fell.")
    _foot(p, ax, "Derived: exports minus imports, same World Bank columns")

    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    for _, col, colour, label in (
            ("bg", "brazil_pct", p.BLUE, "Brazil"),
            ("ar", "argentina_pct", p.RED, "Argentina"),
            ("cl", "chile_pct", p.GOLD, "Chile"),
            ("us", "usa_pct", p.INDIGO, "United States"),
            ("rw", "rest_pct", p.TEAL, "Rest of the world")):
        y, v = _yr(ctx, "trade/partners.csv", col)
        ctx.line(ax, y, v, colour, lw=1.9, ms=3.4, label=label)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=6.4, ncol=2, frameon=False)
    ay, av = _yr(ctx, "trade/partners.csv", "argentina_pct")
    peak = max(zip(ay, av), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}%", peak, textcoords="offset points",
                xytext=(4, 5), ha="left", va="bottom", fontsize=8.2,
                fontweight="bold", color=p.RED)
    _note(p, ax, 0.98, 0.96, "Customs goods only: five shares of the\n"
          "world total the Fund reports.", ha="right", size=7.6)
    _foot(p, ax, "IMF DOTS (IMTS), exports of goods FOB. See DATA_NOTES on "
          "Argentina's 2016-20 shares")

    ax = ig.slot("trade.lens", "Itaipú and Yacyretá — treaty revenue "
                 "(% of GDP)")
    ry, rv = _yr(ctx, "fiscal/fiscal_national.csv", "itaipu_royalties_pct_gdp")
    cy, cv = _yr(ctx, "fiscal/fiscal_national.csv", "itaipu_cession_pct_gdp")
    ctx.line(ax, ry, rv, p.TEAL, label="Royalties")
    ctx.line(ax, cy, cv, p.GOLD, label="Energy-cession compensation")
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    _mark(ig, ax, "annex_c", dy=0.52)
    _note(p, ax, 0.98, 0.72, f"{rv[0]:.2f}% of GDP in {ry[0]} and "
          f"{rv[-1]:.2f}% in {ry[-1]}:\n"
          "fiscal revenue under the treaties,\n"
          "not a hydro share of output.", ha="right", size=7.6)
    _foot(p, ax, "MEF central administration, cash. The electricity itself "
          "is in the exports panel")
    _finish(ctx, ig)


# ----------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ctx.pending(ax)
    _pending(ig, ax,
             "The BCP's tasa de política monetaria is behind a",
             "Cloudflare block. The IMF's MFS_IR carries Paraguay's",
             "rates only to 2022 and has no policy-rate indicator.",
             "A series stopping in 2022 beside 2025 inflation",
             "would imply a stance nobody holds.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    ctx.pending(ax)
    _pending(ig, ax,
             "No continuous official annual yield is published on",
             "any reachable route: the BCP is blocked, the MEF",
             "publishes auction results and international bond terms",
             "but no secondary-market curve, and the domestic market",
             "is thin and short-dated. Possibly nonexistent,",
             "rather than merely blocked.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("markets.currency", "Currency against the US$ "
                 "(index 2006 = 100, up = stronger)")
    fy, fv = _yr(ctx, "markets/fx.csv", "pyg_per_usd")
    iy, iv = ctx.fx_index(dict(zip(fy, fv)))
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.TEAL, lambda v: f"{v:.0f}", dy=9)
    pk = max(zip(iy, iv), key=lambda t: t[1])
    # The 2023 redenomination proposal, abandoned. Year named once, in the
    # note, because it is a date in the country's monetary history rather
    # than a value in this series.
    abandoned = 2023
    _note(p, ax, 0.02, 0.12,
          f"The strongest year was {pk[0]} at {pk[1]:.0f}; the line ends at "
          f"{iv[-1]:.0f} on the index.\n"
          "No minor unit in practice, and no redenomination:\n"
          f"the {abandoned} proposal was abandoned.",
          va="bottom", size=7.8)
    _foot(p, ax, "IMF IFS (PRY.USD_XDC.PA_RT), annual average, reciprocated "
          "so up is stronger")

    ax = ig.slot("markets.equities", "Main equity index in US$ "
                 "(index 2006 = 100, in US$)")
    ctx.pending(ax)
    _pending(ig, ax,
             "The Bolsa de Valores de Asociación publishes trades",
             "and a market summary, not a continuous capitalisation-",
             "weighted index, and no redistributor carries a",
             "Paraguayan index. An index built from a handful of",
             "trades would not be an index.")
    _foot(p, ax, "SOURCES.yaml meta.pending")
    _finish(ctx, ig)


# ------------------------------------------------------------------ credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p
    C = "credit/credit.csv"

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax,
             "BIS total credit has no Paraguay series at all, and",
             "the BCP's household split is behind the block.",
             "The private-sector credit that IS staged is drawn in",
             "the lens beside this panel, labelled as what it is —",
             "not as household debt.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("credit.lending_rate",
                 "Household lending rate vs policy rate (%)")
    ctx.pending(ax)
    _pending(ig, ax,
             "The IMF's MFS_IR carries lending and deposit rates",
             "only to 2022 and does not separate households from",
             "firms; the BCP's own table is behind the same block.",
             "A rate that stopped three years ago is not",
             "a current lending rate.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    ny, nv = _yr(ctx, C, "npl_ratio")
    ctx.line(ax, ny, nv, p.RED)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ny, nv, p.RED, lambda v: f"{v:.1f}%", dy=9)
    _note(p, ax, 0.02, 0.96, f"{nv[0]:.1f}% in {ny[0]} and "
          f"{nv[-1]:.1f}% in {ny[-1]}:\n"
          f"the ratio never reaches {max(nv) + 0.5:.0f}% in the window.")
    _foot(p, ax, "The BCP's supervisory ratio as the World Bank records it")

    ax = ig.slot("credit.lens", "Private-sector credit (% of GDP) — not "
                 "household debt")
    cy, cv = _yr(ctx, C, "private_credit_pct_gdp")
    ctx.line(ax, cy, cv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, cy, cv, p.BLUE, lambda v: f"{v:.0f}%", dy=-16)
    _note(p, ax, 0.02, 0.96, f"{cv[0]:.1f}% of GDP in {cy[0]} and "
          f"{cv[-1]:.1f}% in {cy[-1]}:\n"
          "credit to firms and households together,\n"
          "on its own scale.", size=7.8)
    _foot(p, ax, "World Bank FS.AST.PRVT.GD.ZS. Not the household-debt slot, "
          "which stays pending")
    _finish(ctx, ig)


# ------------------------------------------------------------------ people
def plate_people(ctx, ig) -> None:
    p = ctx.p
    I = "people/income.csv"

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100)")
    gy, gv = _yr(ctx, I, "gini")
    ctx.line(ax, gy, gv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.PURPLE, lambda v: f"{v:.1f}", dy=-16)
    _note(p, ax, 0.02, 0.96, f"{gv[0]:.1f} in {gy[0]} and {gv[-1]:.1f} in "
          f"{gy[-1]}:\n"
          f"{gv[0] - gv[-1]:.1f} points in {gy[-1] - gy[0]} years.", size=7.8)
    _foot(p, ax, "World Bank harmonisation of INE's EPHC; INE's own file is "
          "a legacy .xls")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    py, pv = _yr(ctx, I, "poverty_rate_pct")
    ey, ev = _yr(ctx, I, "extreme_poverty_rate_pct")
    ctx.line(ax, py, pv, p.RED, label="National poverty line")
    ctx.line(ax, ey, ev, p.GOLD, label="Extreme poverty")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    _mark(ig, ax, "survey_break", dy=0.45)
    _note(p, ax, 0.02, 0.96, f"{pv[0]:.1f}% in {py[0]} against "
          f"{pv[-1]:.1f}% in {py[-1]} —\n"
          "the 2017 step is a survey redesign, not a fall.")
    _foot(p, ax, "INE, EPH to 2016 and EPHC from 2017: one series, one break")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    wy, wv = _yr(ctx, I, "minimum_wage_usd_month")
    ctx.line(ax, wy, wv, p.GREEN)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, wy, wv, p.GREEN, lambda v: f"US${v:,.0f}", dy=9)
    _note(p, ax, 0.02, 0.96, f"US${wv[0]:,.0f} in {wy[0]} against "
          f"US${wv[-1]:,.0f} in {wy[-1]} —\n"
          f"The {wy[-1] + 1} decree is not in the staged vintage, so the "
          "line\nstops rather than carrying a value forward.", size=7.8)
    _foot(p, ax, "ILOSTAT statutory monthly rate, converted at the same "
          "year's average")

    ax = ig.slot("people.lens", "What the statutory minimum is worth "
                 "(index 2006 = 100)")
    cpi_y, cpi_v = _yr(ctx, "macro/economy.csv", "cpi_inflation_pct")
    level, run = {}, 100.0
    for y, v in sorted(zip(cpi_y, cpi_v)):
        if y > W0:
            run *= 1 + v / 100
        level[y] = run
    # The lens indexes the statutory rate in GUARANÍES, not the dollar
    # series on the panel to its left: the point of the lens is what the
    # law sets against what prices did, and the dollar rate already moves
    # with the exchange rate.
    gy, gv = _yr(ctx, I, "minimum_wage_pyg_month")
    base = gv[0]
    nom = [(y, v / base * 100) for y, v in zip(gy, gv)]
    real = [(y, (v / base) * 100 / (level[y] / 100)) for y, v in zip(gy, gv)
            if y in level]
    ctx.line(ax, [y for y, _ in nom], [v for _, v in nom], p.GREEN,
             label="In guaraníes, nominal")
    ctx.line(ax, [y for y, _ in real], [v for _, v in real], p.RED,
             label="Deflated by the CPI")
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    ig.headroom(ax, top=0.30)
    _mark(ig, ax, "minimum_wage", dy=0.55)
    _note(p, ax, 0.98, 0.96,
          f"The nominal minimum rose {nom[-1][1] / 100:.1f}× and prices "
          f"{level[gy[-1]] / 100:.1f}×:\n"
          f"the real minimum is {real[-1][1]:.0f} on the same 2006 base.",
          ha="right", size=7.6)
    _foot(p, ax, "Derived: the statutory rate chained against the CPI of "
          "one vintage, not a published real wage")
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "world/gdp_usd.csv", "gdp_usd_bn")
    ctx.line(ax, gy, gv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.BLUE, lambda v: f"US${v:,.0f}bn", dy=9)
    _note(p, ax, 0.02, 0.96, f"US${gv[0]:,.0f}bn in {gy[0]} and "
          f"US${gv[-1]:,.0f}bn in {gy[-1]} —\n"
          "nominal growth: real output plus the CPI, with\n"
          "the exchange rate roughly flat.", size=7.8)
    _foot(p, ax, "World Bank, current US$")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "world/hdi.csv", "hdi")
    ctx.line(ax, hy, hv, p.GREEN)
    ctx.endlabel(ax, hy, hv, p.GREEN, lambda v: f"{v:.3f}", dy=9)
    _note(p, ax, 0.02, 0.96, f"{hv[0]:.3f} in {hy[0]} and {hv[-1]:.3f} in "
          f"{hy[-1]} — rank 99 of 193 "
          "countries.\n"
          "One HDR vintage for the whole series.")
    _foot(p, ax, "UNDP HDR 2025; the series has no later value")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (score, 0–100)")
    ctx.pending(ax)
    _pending(ig, ax,
             "Transparency International's CDN answers 403 to this",
             "network on 2026-10-25, the same block Ukraine's lane",
             "recorded. The landing page carries one year, and one",
             "year is not a panel. No proxy is substituted.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn)")
    ry, rv = _yr(ctx, "world/gdp_usd.csv", "reserves_usd_bn")
    ctx.line(ax, ry, rv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.TEAL, lambda v: f"US${v:,.1f}bn", dy=9)
    _note(p, ax, 0.02, 0.96, f"US${rv[0]:,.1f}bn in {ry[0]} and "
          f"US${rv[-1]:,.1f}bn in {ry[-1]}:\n"
          "about five months of imports at that level.", size=7.8)
    _foot(p, ax, "World Bank FI.RES.TOTL.CD, year-end, gold included. No "
          "2025 value in this vintage")
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    ay, av = _yr(ctx, "demography/population.csv", "population")
    wy, wv = _yr(ctx, "demography/population_un_wpp.csv", "population")
    ay_i, av_i = ctx.index_2006(dict(zip(ay, av)))
    wy_i, wv_i = ctx.index_2006(dict(zip(wy, wv)))
    ctx.line(ax, ay_i, av_i, p.RED,
             label="INE, revision 2024 (2022 census inside)")
    ctx.line(ax, wy_i, wv_i, p.BLUE, lw=1.8, ms=3.2, ls=(0, (4, 2)),
             dashed_partial=False, label="UN WPP, as the World Bank carries it")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=6.8, frameon=False)
    # Compared at the last complete year, not at the projection's end.
    yr = min(ay[-1], wy[-1], ctx.LAST_FULL_YEAR)
    ine_n, un_n = _at(ay, av, yr), _at(wy, wv, yr)
    _note(p, ax, 0.02, 0.06, f"{ine_n / 1e6:.3f}m against {un_n / 1e6:.3f}m "
          f"in {yr}:\n"
          f"the {(un_n / ine_n - 1) * 100:.0f}% gap is the census. Two "
          "perimeters, two lines.", va="bottom", size=7.6)
    _foot(p, ax, "INE Revisión 2024 and World Bank SP.POP.TOTL (UN WPP). "
          "Never spliced")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    fy, fv = _yr(ctx, "demography/population.csv", "fertility_rate")
    ctx.line(ax, fy, fv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ax.axhline(2.1, color=p.FAINT, lw=1.0, ls=":", zorder=2)
    _mark(ig, ax, "replacement", dy=0.68)
    _note(p, ax, 0.02, 0.96, f"{fv[0]:.2f} in {fy[0]} and {fv[-1]:.2f} by "
          f"{fy[-1]} — the dotted line\n"
          "is replacement, 2.1 children per woman.")
    _foot(p, ax, "INE revision-2024 projection, not a registered birth count")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    by, bv = _yr(ctx, "demography/population.csv", "birth_rate_per_1000")
    dy, dv = _yr(ctx, "demography/population.csv", "death_rate_per_1000")
    ctx.line(ax, by, bv, p.GREEN, label="Births")
    ctx.line(ax, dy, dv, p.RED, label="Deaths")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.2, frameon=False)
    ax.annotate(f"{_at(dy, dv, 2021):.1f}", (2021, _at(dy, dv, 2021)),
                textcoords="offset points", xytext=(2, 6), ha="left",
                va="bottom", fontsize=8.4, fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.55, "The 2021 spike is the pandemic inside the\n"
          "projection, not a registered death count.")
    _foot(p, ax, "INE revision 2024")

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net migration (per 1,000 people)")
    ny, nv = _yr(ctx, "demography/population.csv",
                 "natural_increase_rate_per_1000")
    my, mv = _yr(ctx, "demography/population.csv",
                 "net_migration_rate_per_1000")
    ctx.line(ax, ny, nv, p.TEAL, label="Natural increase")
    ctx.line(ax, my, mv, p.PURPLE, label="Net migration")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    _note(p, ax, 0.02, 0.96, f"Net migration is negative every year: "
          f"{mv[0]:.1f} per 1,000\n"
          f"in {my[0]} and {mv[-1]:.1f} by {my[-1]} — Paraguay exports "
          "people.", size=7.8)
    _foot(p, ax, "INE revision 2024, both rates on INE's own mid-year "
          "population")
    _finish(ctx, ig)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    S = "security/security.csv"

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    hy, hv = _yr(ctx, S, "homicide_per_100k")
    ctx.line(ax, hy, hv, p.RED)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, hy, hv, p.RED, lambda v: f"{v:.1f}", dy=9)
    _note(p, ax, 0.02, 0.06, f"The rate fell from {hv[0]:.1f} in {hy[0]} "
          f"to {hv[-1]:.1f} in {hy[-1]} —\n"
          "The Ministerio Público publishes its own count as\n"
          "PDF tables; the definitions differ in both directions.",
          va="bottom", size=7.6)
    _foot(p, ax, "UNODC via the World Bank; the harmonised series only")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    sy, sv = _yr(ctx, S, "suicide_per_100k")
    ctx.line(ax, sy, sv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, sy, sv, p.PURPLE, lambda v: f"{v:.1f}", dy=9)
    _note(p, ax, 0.02, 0.96, f"{sv[0]:.1f} in {sy[0]} and {sv[-1]:.1f} in "
          f"{sy[-1]} — where the WHO series\n"
          "stops in this vintage.", size=7.8)
    _foot(p, ax, "WHO via the World Bank")

    ax = ig.slot("security.road_deaths", "Road traffic deaths "
                 "(per 100,000)")
    ry, rv = _yr(ctx, S, "road_deaths_per_100k")
    ctx.line(ax, ry, rv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.GOLD, lambda v: f"{v:.1f}", dy=9)
    _note(p, ax, 0.02, 0.96, f"{rv[0]:.1f} in {ry[0]} and {rv[-1]:.1f} in "
          f"{ry[-1]} —\n"
          "the highest of the three rates in every year it covers.")
    _foot(p, ax, "WHO via the World Bank; no later value in this vintage")

    ax = ig.slot("security.lens", "The three causes side by side "
                 "(per 100,000)")
    for (col, colour, label) in (("homicide_per_100k", p.RED, "Homicide"),
                                 ("suicide_per_100k", p.PURPLE, "Suicide"),
                                 ("road_deaths_per_100k", p.GOLD,
                                  "Road traffic")):
        y, v = _yr(ctx, S, col)
        ctx.line(ax, y, v, colour, label=label)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    ig.headroom(ax, top=0.24)
    _note(p, ax, 0.02, 0.96, "The same three staged series on one axis:\n"
          "the road kills more Paraguayans than homicide.", size=7.6)
    _foot(p, ax, "No new source — a comparison of this plate's three panels")
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    M = "mortality/mortality.csv"

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000 people)")
    dy, dv = _yr(ctx, M, "death_rate_per_1000")
    ctx.line(ax, dy, dv, p.INDIGO)
    ig.add_recessions(ax, label=False)
    pk = max(zip(dy, dv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}", pk, textcoords="offset points",
                xytext=(4, 6), ha="left", va="bottom", fontsize=8.6,
                fontweight="bold", color=p.INDIGO)
    _note(p, ax, 0.02, 0.96, f"The rate runs {dv[0]:.1f} in {dy[0]} to "
          f"{pk[1]:.1f} in {pk[0]};\n"
          "the projection already contains the pandemic,\n"
          "so nothing is smoothed.")
    _foot(p, ax, "INE revision-2024 estimates and projections, not "
          "registered deaths")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above 2015–2019 average)")
    ctx.pending(ax)
    _pending(ig, ax,
             "Excess deaths need a registered annual death count.",
             "INE's vital-statistics workbooks stop at 2017 as",
             "machine-readable releases, and the revision-2024",
             "series is a smoothed estimate that already contains",
             "the pandemic: a baseline subtracted from it would",
             "measure the model, not the deaths.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    ctx.pending(ax)
    _pending(ig, ax,
             "WHO's GHO catalogue carries no general COVID-19 death",
             "indicator for Paraguay, only in-prison diagnoses,",
             "and covid19.who.int now serves an HTML page.",
             "No official underlying-cause count is drawn, and no",
             "model is put in its place.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("mortality.lens", "Life expectancy at birth (years)",
                 unit=False)
    ly, lv = _yr(ctx, M, "life_expectancy")
    ctx.line(ax, ly, lv, p.TEAL)
    ig.add_recessions(ax, label=False)
    low = min(zip(ly, lv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, f"{lv[0]:.1f} years in {ly[0]} and "
          f"{lv[-1]:.1f} in {ly[-1]} —\n"
          f"{low[1]:.1f} in {low[0]} is the pandemic's mark on the\n"
          "projection, not a registered count.", size=7.8)
    _foot(p, ax, "INE revision 2024")
    _finish(ctx, ig)


# --------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    M = "migration/migration.csv"

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    ctx.pending(ax)
    _pending(ig, ax,
             "No reachable publisher gives an annual immigration",
             "and emigration flow count. INE's vital statistics stop",
             "at 2017 as machine-readable files, and the Dirección",
             "General de Migraciones publishes entries and exits as",
             "PDFs. Only the net is drawn, labelled as a net.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    iy, iv = _yr(ctx, M, "net_migration_rate_per_1000")
    py, pv = _yr(ctx, "demography/population_un_wpp.csv", "population")
    ny, nv = _yr(ctx, M, "net_migration_persons")
    pw = dict(zip(py, pv))
    un = [(y, v / pw[y] * 1000) for y, v in zip(ny, nv) if y in pw]
    ctx.line(ax, iy, iv, p.PURPLE, label="INE, per 1,000 of INE's population")
    ctx.line(ax, [y for y, _ in un], [v for _, v in un], p.BLUE, lw=1.8,
             ms=3.2, ls=(0, (4, 2)), dashed_partial=False,
             label="UN WPP, per 1,000 of the UN population")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=6.8, frameon=False)
    _note(p, ax, 0.02, 0.96, f"{iv[0]:.1f} per 1,000 in {iy[0]}: "
          "the outflow's peak.\n"
          "Each line divides by its own publisher's population,\n"
          "so the two denominators are never mixed.", va="top", size=7.6)
    _foot(p, ax, "INE revision 2024 and World Bank SM.POP.NETM (UN WPP)")

    ax = ig.slot("migration.foreign_born",
                 "Foreign-born share of the population (%)")
    sy, sv = _yr(ctx, M, "migrant_stock")
    share = [(y, v / pw[y] * 100) for y, v in zip(sy, sv) if y in pw]
    ctx.line(ax, [y for y, _ in share], [v for _, v in share], p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, [y for y, _ in share], [v for _, v in share], p.GOLD,
                 lambda v: f"{v:.1f}%", dy=9)
    _note(p, ax, 0.02, 0.96, "Four snapshots only: the years the UN publishes\n"
          "the stock for, never interpolated between.", size=7.6)
    _foot(p, ax, "UN DESA migrant stock ÷ UN WPP population")

    ax = ig.slot("migration.lens", "Net migration in persons "
                 "(UN WPP model)")
    ly, lv = _yr(ctx, M, "net_migration_persons")
    ctx.bars(ax, ly, lv, lambda v: p.RED)
    low = min(zip(ly, lv), key=lambda t: t[1])
    ig.headroom(ax, top=0.26)
    _note(p, ax, 0.02, 0.96, f"A net outflow every year, from "
          f"{abs(low[1]):,.0f} people in\n"
          f"{low[0]} to {abs(lv[-1]):,.0f} in {ly[-1]}: the size of the "
          "flow,\nwhich no stock panel can show.", size=7.6)
    _foot(p, ax, "World Bank SM.POP.NETM (UN WPP), persons — a level, on "
          "its own scale")
    _finish(ctx, ig)


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Economy — Soy, Hydro and a Long Prices Record",
         subtitle="Growth, income, prices and jobs in comparable World Bank "
                  "and IMF series, with the BCP's CPI as the Fund carries it.",
         source="Sources: World Bank · IMF · INE",
         alt="Four panels on Paraguay's economy: real growth with the 2009, "
             "2012 and 2019-20 downturns banded; GDP per person in current "
             "dollars; consumer price inflation; and unemployment in the ILO "
             "model beside INE's survey from 2017.",
         filename="01-economy"),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — Two Perimeters, One Country",
         subtitle="The IMF's general government on an accrual basis and the "
                  "MEF's central administration on the Treasury's cash books.",
         source="Sources: IMF WEO · Ministerio de Economía y Finanzas",
         alt="Four panels on Paraguay's public finances: revenue and "
             "expenditure for general government and for central "
             "administration, about four points of GDP apart; the overall and "
             "primary balance; gross debt; and interest paid.",
         filename="02-fiscal"),
    dict(id="03", slug="spending", topic="spending",
         builder=plate_spending,
         title="Spending — Investment Drawn, Functions Pending",
         subtitle="The functional classification is not published as a "
                  "series; the two investment panels are.",
         source="Sources: World Bank · Ministerio de Economía y Finanzas",
         alt="Four panels on spending: two visibly pending functional panels "
             "with the routes that failed, the whole-economy investment rate, "
             "and the central government's own fixed investment.",
         filename="03-spending"),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — Soy Out, Power Out, Two Definitions",
         subtitle="Goods and services in the national accounts, customs goods "
                  "by destination, and the treaties' revenue kept separate.",
         source="Sources: World Bank · IMF DOTS · MEF",
         alt="Four panels on Paraguay's trade: exports and imports of goods "
             "and services as a share of GDP; their balance; the destinations "
             "of customs goods exports since 2006; and Itaipú-Yacyretá "
             "royalties as fiscal revenue.",
         filename="04-trade"),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Markets — One Panel the Blocked Bank Cannot Hide",
         subtitle="The guaraní's twenty-year path is comparable; the policy "
                  "rate, the yield curve and an index are not stageable.",
         source="Sources: IMF IFS (the BCP's reference rate)",
         alt="Four panels on markets: three visibly pending panels for the "
             "policy rate, the ten-year yield and an equity index, and the "
             "guaraní against the dollar indexed to 2006.",
         filename="05-markets"),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — What Is Bank Credit and What Is Household Debt",
         subtitle="Non-performing loans and private-sector credit are drawn; "
                  "household debt and the lending rate are not published.",
         source="Sources: World Bank (the BCP's supervisory data)",
         alt="Four panels on credit: household debt and the household lending "
             "rate visibly pending, the non-performing loan ratio, and "
             "private-sector credit as a share of GDP labelled as not "
             "household debt.",
         filename="06-credit"),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="People — A Slow Gini and a Minimum Wage in Guaraníes",
         subtitle="Inequality and poverty from INE's survey, the statutory "
                  "minimum in dollars, and what it is worth in guaraníes.",
         source="Sources: INE · World Bank · ILOSTAT · IMF",
         alt="Four panels on people: the Gini coefficient; the national "
             "poverty rate with its 2017 survey break marked; the statutory "
             "minimum wage in dollars per month; and its value in guaraníes "
             "against the CPI.",
         filename="07-people"),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="Paraguay in the World — Small, Landlocked, Improving",
         subtitle="Nominal size, human development and reserves; the "
                  "corruption index is blocked at the publisher.",
         source="Sources: World Bank · UNDP",
         alt="Four panels placing Paraguay in the world: nominal GDP in "
             "dollars, the Human Development Index, a pending corruption "
             "index with its reason, and official reserves.",
         filename="08-world"),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — The Census and the UN, Nine Per Cent Apart",
         subtitle="INE's revision 2024 is anchored on the 2022 census; the UN "
                  "series the World Bank carries is not.",
         source="Sources: INE (Revisión 2024) · World Bank (UN WPP)",
         alt="Four panels on demography: the population index on two "
             "perimeters nine per cent apart; the fertility rate falling "
             "below replacement in 2022; crude birth and death rates; and "
             "natural increase against net migration.",
         filename="09-demography"),
    dict(id="10", slug="security", topic="security", builder=plate_security,
         title="Security — The Road Kills More Than the Gun",
         subtitle="Homicide, suicide and road deaths on the harmonised "
                  "series, then the three beside each other.",
         source="Sources: UNODC · WHO, via the World Bank",
         alt="Four panels on security: the homicide rate on a log scale, the "
             "suicide rate, road traffic deaths, and the three rates drawn "
             "together on one axis.",
         filename="10-security"),
    dict(id="11", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — A Projection With a Pandemic Inside It",
         subtitle="The death rate and life expectancy from INE's projection; "
                  "excess and COVID-19 deaths stay pending.",
         source="Source: INE (Revisión 2024)",
         alt="Four panels on mortality: the crude death rate with its 2021 "
             "spike, two visibly pending panels for excess and COVID-19 "
             "deaths with their reasons, and life expectancy.",
         filename="11-mortality"),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — A Country That Exports People",
         subtitle="Net migration on each publisher's own denominator, the "
                  "foreign-born stock, and the outflow in persons.",
         source="Sources: INE · World Bank (UN WPP, UN DESA)",
         alt="Four panels on migration: gross flows visibly pending, net "
             "migration from INE and from the UN each on its own population, "
             "the foreign-born share in four snapshots, and net migration in "
             "persons.",
         filename="12-migration"),
)
