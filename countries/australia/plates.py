"""The australia plates, on the plate spine.

Twelve chapters, one per spine topic the staged data supports, and every
panel claimed by slot key in the spine's order so an Australian panel sits
over the same panel of every other country in the comparison viewer. The
canonical panels use the spine's exact indicator, unit and atlas-wide scale;
nothing here sets a canonical y-limit.

Four conventions run through the file, and each one is drawn rather than
merely stated in a note:

- **Calendar years, except the fiscal chapter.** Calendar-year series are
  built from the ABS quarters by the rule DATA_NOTES.md records (flows
  summed, rates averaged, population the 30 June stock), and a year with
  fewer than four quarters is not emitted at all — which is why every line
  stops in 2025 inside a window that runs to 2026. The fiscal chapter is
  July–June and its `year` column is the year the year *ends*, so each value
  is drawn at its year's midpoint (`year − 0.5`, i.e. FY2024/25 at 2024.5)
  and every panel there says FY on its face. Nothing calendar-year is drawn
  on that plate.
- **Two publishers, two lines.** National and harmonised series — the ABS's
  Gini beside the World Bank's, the ABS's GFS beside the IMF's, police
  records beside death certificates — are separate, labelled lines. None is
  spliced into another, and two credit series on different definitions are
  drawn as two segments with the break marked.
- **The rates are the publisher's**, or the atlas's own division of a
  published count by the ABS estimated resident population at 30 June of the
  same year (DATA_NOTES.md). Every count that needed dividing is divided by
  ctx.per_100k / ctx.per_1000, which matches the year, never the list
  position.
- **A hole stays a hole.** Road deaths stop in 2022, the CPI of Transparency
  International starts in 2012, the household lending rate does not exist on
  a reachable endpoint. Each of those is drawn as an ending, a start or a
  pending panel with the reason on it; none is forward-filled, and none is
  filled with a different series.
"""
from __future__ import annotations

from core.sideload import sibling

events = sibling(__file__, "events")

W0 = 2006        # the shared plate window opens here
FY = 0.5         # fiscal years are drawn at their midpoint: year − FY


# ------------------------------------------------------------ small helpers
def _yr(ctx, rel: str, col: str, since: int = W0, until: int | None = None):
    """(years, values) from a calendar-year CSV, blanks dropped."""
    t = ctx.table(rel)
    if not t or col not in t:
        return [], []
    yrs, vals = ctx.series(t, col)
    keep = [(y, v) for y, v in zip(yrs, vals)
            if y >= since and (until is None or y <= until)]
    return [y for y, _ in keep], [v for _, v in keep]


def _fy(ctx, rel: str, col: str, since: int = W0):
    """(x, values) from a fiscal-year CSV, drawn at the year's midpoint.

    The `year` column of every fiscal file in this country is the year the
    July-June year ENDS, so FY2024/25 is `2025` and sits at 2024.5.
    """
    y, v = _yr(ctx, rel, col, since=since)
    return [x - FY for x in y], v


def _at(years, vals, year):
    return dict(zip(years, vals))[year]


def _note(p, ax, x, y, text, ha="left", va="top", size=7.8):
    """A short italic note in axes fractions."""
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=size, style="italic", color=p.MUTED, zorder=7)


def _foot(p, ax, text):
    """The provenance line under a panel."""
    ax.text(0.5, -0.075, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.0, color=p.FAINT, style="italic")


def _pending(ig, ax, why):
    ax.text(0.5, 0.36, why, transform=ax.transAxes, ha="center", va="top",
            fontsize=8.0, style="italic", color=ig.p.MUTED)


def _mark(ig, ax, key, dy=0.62):
    """One of events.MARKS on a panel."""
    x, label = events.MARKS[key]
    ig.add_event(ax, x, label, dy=dy)


def _barkey(ax, color, label):
    """An invisible bar carrying a legend entry for a bar series."""
    ax.bar([], [], color=color, label=label)


def _natl(ctx, ax, years, vals, color, label, **kw):
    """A labelled national line riding beside a harmonised one.

    Thin, small markers and dotted: the shared slot's line stays the
    envelope's, the national reading is visibly the second one.
    """
    kw.setdefault("lw", 1.6)
    kw.setdefault("ms", 2.8)
    ctx.line(ax, years, vals, color, label=label, ls=(0, (1, 1.4)),
             dashed_partial=False, **kw)


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(a)


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p
    E = "macro/economy.csv"
    I = "macro/gdp_growth_imf.csv"

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, E, "real_growth_pct")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    iy, iv = _yr(ctx, I, "real_growth_pct")
    _barkey(ax, p.GREEN, "ABS national accounts, calendar years")
    _natl(ctx, ax, iy, iv, p.NAVY, "IMF WEO, same calendar years")
    ig.add_recessions(ax, label=False)
    lo = min(zip(gy, gv), key=lambda t: t[1])
    ax.annotate(f"{lo[1]:.1f}%", lo, textcoords="offset points",
                xytext=(0, -3), ha="center", va="top", fontsize=8.6,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.55, "Australia had no technical recession in the "
          "GFC: one negative\nquarter in 2008 and none in 2009",
          va="top")
    ax.legend(loc="upper left", fontsize=7.4, ncol=2, frameon=False)
    _foot(p, ax, "ABS ANA calendar years (four quarters summed); IMF WEO "
          "NGDP_RPCH agrees to a tenth of a point")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "world/gdp_and_reserves.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    _note(p, ax, 0.02, 0.10, f"US$ at market rates: {_at(py, pv, 2012):,.0f} "
          f"in 2012, {_at(py, pv, 2022):,.0f} in 2022 —\nthe exchange rate "
          "moves this line as much as output", va="bottom")
    _foot(p, ax, "World Bank WDI, current US$; the real story is on slot 1")

    ax = ig.slot("economy.inflation", "Consumer price inflation (% per year)")
    cy, cv = _yr(ctx, E, "cpi_inflation_pct")
    ctx.line(ax, cy, cv, p.ALERT)
    ig.add_recessions(ax, label=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(6, 4), ha="left",
                fontsize=8.8, fontweight="bold", color=p.ALERT)
    _mark(ig, ax, "hikes", dy=0.40)
    _note(p, ax, 0.02, 0.55, "one vintage of the ABS linked all-groups index, "
          "annual mean\nagainst the previous year's mean", va="top")
    _foot(p, ax, "ABS CPI (linked series, so the 2012, 2014 and 2017 "
          "rebases are comparable)")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    uy, uv = _yr(ctx, E, "unemployment_pct")
    ctx.line(ax, uy, uv, p.NAVY)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, uy, uv, p.NAVY, lambda v: f"{v:.1f}%", dy=8)
    hi = max(zip(uy, uv), key=lambda t: t[1])
    ax.annotate(f"{hi[1]:.1f}% in {hi[0]}", hi, textcoords="offset points",
                xytext=(2, 6), ha="left", fontsize=8.4, fontweight="bold",
                color=p.NAVY)
    _note(p, ax, 0.02, 0.55, "monthly Labour Force figures, averaged over "
          "the twelve months", va="top")
    _foot(p, ax, "ABS Labour Force, persons, seasonally adjusted (monthly "
          "mean of the year)")
    _finish(ctx, ig)


# ------------------------------------------------------------------- fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p
    F = "fiscal/fiscal.csv"

    ax = ig.slot("fiscal.revenue_expenditure",
                 "Revenue and expenditure (% of GDP, fiscal years)")
    ry, rv = _fy(ctx, F, "revenue_pct_gdp")
    ey, ev = _fy(ctx, F, "expenditure_pct_gdp")
    ctx.line(ax, ry, rv, p.TEAL, label="Revenue (IMF Fiscal Monitor)")
    ctx.line(ax, ey, ev, p.ALERT, label="Expenditure (IMF Fiscal Monitor)")
    ig.add_recessions(ax, label=False)
    pk = max(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}%", pk, textcoords="offset points",
                xytext=(4, 6), ha="left", fontsize=8.6, fontweight="bold",
                color=p.ALERT)
    ax.legend(loc="lower right", fontsize=7.2, frameon=False)
    _note(p, ax, 0.02, 0.96, "fiscal years, July–June, drawn at the year's "
          "midpoint:\n2024.5 is FY2024/25")
    _foot(p, ax, "IMF Fiscal Monitor, general government, accrual")

    ax = ig.slot("fiscal.balance", "Overall balance (bars) and primary "
                 "balance (% of GDP, fiscal years)")
    by, bv = _fy(ctx, F, "balance_pct_gdp")
    py, pv = _fy(ctx, F, "primary_balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ctx.line(ax, py, pv, p.NAVY, lw=1.8, ms=3.2, label="Primary balance")
    gfy, gfv = _fy(ctx, F, "gfs_net_operating_balance_pct_gdp")
    _natl(ctx, ax, gfy, gfv, p.GOLD, "ABS GFS net operating balance")
    _barkey(ax, p.ALERT, "Overall balance (IMF Fiscal Monitor)")
    ig.add_recessions(ax, label=False)
    lo = min(zip(by, bv), key=lambda t: t[1])
    ax.annotate(f"{lo[1]:.1f}%", lo, textcoords="offset points",
                xytext=(0, -3), ha="center", va="top", fontsize=8.6,
                fontweight="bold", color=p.ALERT)
    ax.legend(loc="lower left", fontsize=7.0, ncol=1, frameon=False)
    _note(p, ax, 0.98, 0.96, f"FY2024/25: {_at(by, bv, by[-1]):.1f}% on the "
          "Fund's basis,\n"
          f"{_at(gfy, gfv, by[-1]):.1f}% on the ABS's narrower one",
          ha="right")
    _foot(p, ax, "IMF general government and the ABS GFS 5512.0 all levels "
          "of government — two definitions, two lines")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP, fiscal years)")
    dy, dv = _fy(ctx, F, "gross_debt_pct_gdp")
    ctx.line(ax, dy, dv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.PURPLE, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"from {dv[0]:.0f}% of GDP in FY2005/06, when "
          f"the Commonwealth\nwas net debt-free, to {_at(dy, dv, 2020.5):.0f}% "
          "in the pandemic; 51.9% in FY2024/25")
    _foot(p, ax, "IMF Fiscal Monitor, general government gross debt")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP, fiscal years)")
    iy, iv = _fy(ctx, F, "interest_pct_gdp")
    ctx.line(ax, iy, iv, p.GOLD, split_year=2026,
             label="Derived: (interest ÷ revenue) × (revenue ÷ GDP)")
    gy, gv = _fy(ctx, F, "gfs_interest_pct_gdp")
    _natl(ctx, ax, gy, gv, p.NAVY, "ABS GFS interest paid")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.NAVY, lambda v: f"{v:.2f}%", dy=8)
    ax.legend(loc="upper left", fontsize=7.0, frameon=False)
    _note(p, ax, 0.02, 0.62, "the derived line stops in FY2021/22, where the\n"
          "World Bank's revenue ratio stops", va="top")
    _foot(p, ax, "Derived from World Bank GC.XPN.INTP.RV.ZS × IMF revenue; "
          "the ABS's own interest row from FY2015/16")
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
COFOG7 = [
    ("Social protection", "social_protection_pct_gdp", "RED"),
    ("Health", "health_pct_gdp", "TEAL"),
    ("Education", "education_pct_gdp", "GOLD"),
    ("General public services", "general_public_services_pct_gdp", "PURPLE"),
    ("Economic affairs", "economic_affairs_pct_gdp", "BLUE"),
    ("Defence and public order", "defence_public_order_pct_gdp", "NAVY"),
    ("Other", "other_pct_gdp", "FAINT"),
]


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    t = ctx.table("spending/cofog.csv")
    idx = {y: i for i, y in enumerate(t["year"])}
    tot_col = t["total_expenditure_pct_gdp"]
    yrs = [y for y in t["year"] if y >= W0 and tot_col[idx[y]] == tot_col[idx[y]]]
    series = {col: [t[col][idx[y]] for y in yrs] for _, col, _ in COFOG7}
    total = [tot_col[idx[y]] for y in yrs]

    ax = ig.slot("spending.by_function",
                 "Spending by function, general government (% of GDP)")
    ax.stackplot(yrs, *[series[c] for _, c, _ in COFOG7],
                 labels=[n for n, _, _ in COFOG7],
                 colors=[getattr(p, col) for _, _, col in COFOG7],
                 alpha=0.9, lw=0)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=6.8, ncol=4, frameon=False)
    _note(p, ax, 0.98, 0.44, "calendar years, OECD COFOG —\nnot the ABS's "
          "fiscal-year table", ha="right", va="top")
    _foot(p, ax, "OECD COFOG (general government, accrual) ÷ ABS calendar-"
          "year GDP at current prices")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    soc = series["social_protection_pct_gdp"]
    rest = [a - b for a, b in zip(total, soc)]
    ctx.line(ax, yrs, rest, p.NAVY, label="Everything else")
    ctx.line(ax, yrs, soc, p.ALERT, label="Social protection")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96, f"social protection {soc[0]:.1f}% of GDP in "
          f"{yrs[0]}, {soc[-1]:.1f}% in {yrs[-1]};\nthe pandemic year "
          f"{max(soc):.1f}%")
    _foot(p, ax, "same series, two groups: the function and the remainder")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(% of GDP)")
    iy, iv = _yr(ctx, "spending/investment.csv", "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.TEAL, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, "gross fixed capital formation, all sectors, "
          "current prices")
    _foot(p, ax, "ABS ANA calendar years (four quarters summed) ÷ same-year "
          "GDP")

    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    gy, gv = _yr(ctx, "spending/investment.csv", "public_gfcf_pct_gdp")
    ctx.line(ax, gy, gv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.GOLD, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, "general government only: most infrastructure "
          "sits in\nstate-owned corporations outside this perimeter")
    _foot(p, ax, "ABS ANA, general government GFCF ÷ GDP")
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
def plate_trade(ctx, ig) -> None:
    p = ctx.p
    T = "trade/trade.csv"
    D = "trade/destinations.csv"

    ax = ig.slot("trade.exports_imports",
                 "Exports and imports of goods and services (% of GDP)")
    xy, xv = _yr(ctx, T, "exports_pct_gdp")
    my, mv = _yr(ctx, T, "imports_pct_gdp")
    ctx.line(ax, xy, xv, p.GREEN, label="Exports")
    ctx.line(ax, my, mv, p.ALERT, label="Imports")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96, f"{xv[-1] + mv[-1]:.0f}% of GDP crosses the "
          f"border each way combined\nin {xy[-1]}, on the national-accounts "
          "basis")
    _foot(p, ax, "ABS ANA, goods and services, current prices ÷ same-year GDP")

    ax = ig.slot("trade.balance", "Trade balance, goods and services "
                 "(% of GDP)")
    by, bv = _yr(ctx, T, "balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    pk = max(zip(by, bv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 7), ha="center", fontsize=8.4, fontweight="bold",
                color=p.GREEN)
    _note(p, ax, 0.02, 0.96, "the iron-ore and gas years, then the terms of\n"
          "trade turning back")
    _foot(p, ax, "exports minus imports, same ABS series — computed here, "
          "never stored")

    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    for col, color, label in (
            ("china_pct", p.RED, "China"),
            ("japan_pct", p.GOLD, "Japan"),
            ("korea_pct", p.GREEN, "Korea, Rep. of"),
            ("us_pct", p.BLUE, "United States")):
        dy, dv = _yr(ctx, D, col)
        ctx.line(ax, dy, dv, color, label=label)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    cy, cv = _yr(ctx, D, "china_pct")
    ax.annotate(f"{cv[0]:.0f}% to {cv[-1]:.0f}%", (cy[-1], cv[-1]),
                textcoords="offset points", xytext=(-4, -12), ha="right",
                va="top", fontsize=8.2, fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.96, "the four largest destinations of 2025, ranked "
          "once and\nheld fixed through the back-series")
    _foot(p, ax, "ABS MERCH_EXP, customs basis; total goods exports A$523.6bn "
          "in 2025")

    ax = ig.slot("trade.lens", "Goods exports by destination, 2025 "
                 "(% of goods exports, one year)")
    t = ctx.table("trade/destinations_2025.csv")
    names = [str(n).split(" (")[0].split(",")[0] for n in t["country"]]
    shares = [float(v) for v in t["share_pct"]]
    ypos = list(range(len(names)))[::-1]
    ax.barh(ypos, shares,
            color=[p.BLUE if i else p.RED for i in range(len(names))],
            height=0.68)
    for y, v, n in zip(ypos, shares, names):
        ax.text(-1.0, y, n, ha="right", va="center", fontsize=7.6,
                color=p.INK)
        ax.text(v + 0.7, y, f"{v:.1f}%", ha="left", va="center",
                fontsize=7.4, color=p.MUTED)
    ax.set_yticks([])
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(-24, 42)
    ax.set_ylim(-0.7, len(names) - 0.3)
    ax._categorical_x = True
    _foot(p, ax, "ABS merchandise exports, 2025. Publisher's country labels "
          "abbreviated; one year, a lens not a trend")
    _finish(ctx, ig)
    # style_axis resets every x axis to the country's year window; this lens
    # is categorical, so its own scale goes back after the styling.
    ax.set_xlim(-24, 42)
    ax.set_xticks([0, 10, 20, 30, 40])
    ax.set_yticks([])


# ----------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ky, kv = _yr(ctx, "markets/policy_rate.csv", "policy_rate_pct")
    cy, cv = _yr(ctx, "macro/economy.csv", "cpi_inflation_pct")
    ctx.line(ax, ky, kv, p.NAVY, label="Cash rate target")
    ctx.line(ax, cy, cv, p.ALERT, label="Consumer price inflation")
    ig.add_recessions(ax, label=False)
    pk = max(zip(ky, kv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.2f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(4, 6), ha="left", fontsize=8.4, fontweight="bold",
                color=p.NAVY)
    _mark(ig, ax, "gfc", dy=0.55)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.96, "the cash rate is the RBA's, republished by the "
          "BIS:\nthe RBA's own site answers 403 to this network")
    _foot(p, ax, "BIS WS_CBPOL, annual mean of monthly values (RBA series); "
          "inflation from the ABS CPI")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    by, bv = _yr(ctx, "markets/bond_10y.csv", "bond_10y_pct_annual_avg")
    ctx.line(ax, by, bv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, by, bv, p.BLUE, lambda v: f"{v:.2f}%", dy=8)
    lo = min(zip(by, bv), key=lambda t: t[1])
    ax.annotate(f"{lo[1]:.2f}% in {lo[0]}", lo, textcoords="offset points",
                xytext=(2, -12), ha="left", va="top", fontsize=8.2,
                fontweight="bold", color=p.BLUE)
    _note(p, ax, 0.02, 0.96, "the RBA's F2 table is the national publisher "
          "and is blocked;\nthis is the OECD series on the same instrument")
    _foot(p, ax, "OECD Financial market statistics, monthly, annual mean "
          "(years with twelve months only)")

    ax = ig.slot("markets.currency", "The Australian dollar against the US$ "
                 "(index 2006 = 100, up = stronger)")
    fy, fv = _yr(ctx, "markets/currency.csv", "aud_per_usd")
    iy, iv = ctx.fx_index(dict(zip(fy, fv)))
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    pk = max(zip(iy, iv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.0f} in {pk[0]}", pk, textcoords="offset points",
                xytext=(-4, -14), ha="right", va="top", fontsize=8.4,
                fontweight="bold", color=p.TEAL)
    _mark(ig, ax, "mining_boom", dy=0.52)
    _note(p, ax, 0.02, 0.14, f"US$1 bought A${_at(fy, fv, 2011):.2f} at the "
          f"2011 peak and A${fv[-1]:.2f}\nin {fy[-1]}: the index is "
          "2006 AUD/US$ ÷ the year's", va="bottom")
    _foot(p, ax, "World Bank PA.NUS.FCRF, annual average; 2006 = 100")

    ax = ig.slot("markets.equities", "Main equity index in US$ vs the "
                 "S&P 500 (index 2006 = 100)")
    ay, av = _yr(ctx, "markets/equities.csv", "asx200_usd_index_2006")
    sy, sv = _yr(ctx, "markets/equities.csv", "sp500_usd_index_2006")
    ctx.line(ax, sy, sv, p.FAINT, lw=1.8, ms=3.0, ls="--",
             dashed_partial=False, label="S&P 500, in US$")
    ctx.line(ax, ay, av, p.RED, label="ASX 200, in US$")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ay, av, p.RED, lambda v: f"{v:.0f}", dy=-14)
    ctx.endlabel(ax, sy, sv, p.MUTED, lambda v: f"{v:.0f}", dy=6)
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.16, "a redistributor's series, not an official "
          "statistic:\nannual mean of month-end closes, in US$", va="bottom")
    _foot(p, ax, "Yahoo Finance (not official), converted at the World Bank's "
          "annual-average AUD/USD")
    _finish(ctx, ig)


# ------------------------------------------------------------------ credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP, "
                 "year-end)")
    hy, hv = _yr(ctx, "credit/household_debt.csv", "household_debt_pct_gdp")
    ctx.line(ax, hy, hv, p.RED)
    ig.add_recessions(ax, label=False)
    pk = max(zip(hy, hv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(-4, 8), ha="right", fontsize=8.4, fontweight="bold",
                color=p.RED)
    _note(p, ax, 0.02, 0.30, "among the highest household debt ratios in "
          "the world,\nand it has barely fallen with the rate rises",
          va="bottom")
    _foot(p, ax, "BIS total credit, households and NPISH, market value, "
          "fourth-quarter reading")

    ax = ig.slot("credit.lending_rate", "Household lending rate vs the "
                 "policy rate (%)")
    ctx.pending(ax)
    _pending(ig, ax, "No reachable publisher carries this series: the RBA's "
             "F5\ntable answers 403 on every path, IMF IFS stops in 2019\n"
             "and APRA publishes no interest rate. Nothing is substituted.")
    _foot(p, ax, "SOURCES.yaml meta.pending — household lending rate")

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    a_y, a_v = _yr(ctx, "credit/npl.csv", "npl_impaired_pct")
    b_y, b_v = _yr(ctx, "credit/npl.csv", "npl_nonperforming_pct")
    ctx.line(ax, a_y, a_v, p.PURPLE, label="Impaired facilities (to 2021)")
    ctx.line(ax, b_y, b_v, p.ALERT, split_year=max(b_y),
             label="Non-performing (2022 measure)")
    ig.add_recessions(ax, label=False)
    ax.axvline(2021.5, color=p.MUTED, lw=0.9, ls=":", zorder=2)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    _note(p, ax, 0.02, 0.96, "the step at 2022 is APRA's new definition, "
          "which adds\nfacilities 90+ days past due — not a credit event")
    _foot(p, ax, "APRA quarterly ADI performance, all ADIs, December "
          "quarter; two definitions, never spliced")

    ax = ig.slot("credit.lens", "Lens — what servicing the debt costs "
                 "(% of disposable income)")
    dy, dv = _yr(ctx, "credit/household_debt.csv", "debt_service_ratio_pct")
    ctx.line(ax, dy, dv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ax.set_ylabel("% of disposable income", fontsize=8.4, color=p.MUTED)
    ax.set_ylim(0, max(dv) * 1.35)
    ctx.endlabel(ax, dy, dv, p.GOLD, lambda v: f"{v:.1f}%", dy=-15)
    _note(p, ax, 0.02, 0.96, f"{max(dv):.1f}% at the {dy[dv.index(max(dv))]} "
          "peak, 13.4% in 2021;\nthe ratio falls as rates rise only because "
          "incomes grew faster")
    _foot(p, ax, "BIS household debt-service ratio, fourth-quarter reading")
    _finish(ctx, ig)


# ------------------------------------------------------------------ people
def plate_people(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100, higher = "
                 "more unequal)")
    gy, gv = _yr(ctx, "people/gini.csv", "gini_hies")
    ctx.line(ax, gy, gv, p.NAVY, ms=5.0, label="ABS household survey (HIES)")
    wy, wv = _yr(ctx, "people/gini.csv", "gini_wb")
    _natl(ctx, ax, wy, wv, p.FAINT, "World Bank, same survey")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.96, "a biennial survey that has not run since "
          "2019–20, so the\nline stops there; the World Bank's cut sits "
          "about a point above")
    _foot(p, ax, "ABS Household Income and Wealth 6523.0 (coefficient × 100); "
          "World Bank SI.POV.GINI beside it")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    py, pv = _yr(ctx, "people/poverty.csv", "poverty_4_20_usd")
    ctx.line(ax, py, pv, p.RED, ms=5.0)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.RED, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, "Australia has no official poverty line, so this "
          "is the World\nBank's US$4.20-a-day line, labelled as the "
          "international one")
    _foot(p, ax, "World Bank SI.POV.UMIC (2021 PPP), 2008–2020 only; no "
          "national series exists")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    my, mv = _yr(ctx, "people/minimum_wage.csv", "minimum_wage_usd_month")
    ctx.line(ax, my, mv, p.GREEN_D)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, my, mv, p.GREEN_D, lambda v: f"US${v:,.0f}", dy=8)
    lo = min(zip(my, mv), key=lambda t: t[1])
    ax.annotate(f"US${lo[1]:,.0f} in {lo[0]}", lo, textcoords="offset points",
                xytext=(4, -12), ha="left", va="top", fontsize=8.2,
                fontweight="bold", color=p.GREEN_D)
    _note(p, ax, 0.02, 0.14, "the same award in US$: the 2015 dip is the "
          "Australian dollar\nfalling, not the pay award being cut", va="bottom")
    _foot(p, ax, "OECD statutory minimum wage, AUD/week × 52/12 ÷ the World "
          "Bank's annual-average FX")

    ax = ig.slot("people.lens", "Lens — the minimum wage as it is actually "
                 "paid (A$ per week)")
    ay, av = _yr(ctx, "people/minimum_wage.csv", "minimum_wage_aud_week")
    ctx.line(ax, ay, av, p.GOLD)
    ig.add_recessions(ax, label=False)
    ax.set_ylabel("A$ per week", fontsize=8.4, color=p.MUTED)
    ax.set_ylim(0, max(av) * 1.25)
    ctx.endlabel(ax, ay, av, p.GOLD, lambda v: f"A${v:,.0f}", dy=8)
    _note(p, ax, 0.02, 0.96, "the wage the Fair Work Commission sets each "
          "1 July, in the\ncurrency it is paid in — it rises every year")
    _foot(p, ax, "OECD MW_CURP, national currency, statutory federal minimum")
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "world/gdp_and_reserves.csv", "gdp_usd_bn")
    ctx.line(ax, gy, gv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.BLUE, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, "in US dollars at market rates: the 2015 dip is "
          "the currency,\nnot the economy, which grew through it")
    _foot(p, ax, "World Bank WDI, current US$")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "world/hdi.csv", "hdi")
    ax.axhline(0.8, color=p.FAINT, lw=0.9, ls=":")
    ctx.line(ax, hy, hv, p.GREEN_D, split_year=max(hy))
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, hy, hv, p.GREEN_D, lambda v: f"{v:.3f}", dy=-14)
    _note(p, ax, 0.02, 0.18, "0.800 and above is very high development;\n"
          "one HDR vintage (2025) throughout", va="bottom")
    _foot(p, ax, "UNDP HDR 2025; the series stops in 2023")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (0–100, higher = "
                 "cleaner)")
    cy, cv = _yr(ctx, "world/cpi.csv", "score")
    ctx.line(ax, cy, cv, p.NAVY, split_year=max(cy))
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{cv[0]:.0f} in {cy[0]}", (cy[0], cv[0]),
                textcoords="offset points", xytext=(4, 6), ha="left",
                fontsize=8.4, fontweight="bold", color=p.NAVY)
    ctx.endlabel(ax, cy, cv, p.NAVY, lambda v: f"{v:.0f}", dy=8)
    _note(p, ax, 0.02, 0.55, "the 0–100 method starts in 2012; TI's retired "
          "0–10 scores\nare not comparable and are not drawn")
    _foot(p, ax, "Transparency International CPI 2025 — a think tank's index, "
          "not a statistical office's")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn, year-end)")
    ry, rv = _yr(ctx, "world/gdp_and_reserves.csv", "reserves_usd_bn")
    ctx.line(ax, ry, rv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.TEAL, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, "no peg to defend, so the stock is modest and "
          "moves with\nthe valuation of the reserves themselves")
    _foot(p, ax, "World Bank WDI FI.RES.TOTL.CD, including gold")
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p
    P = "demography/population.csv"

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    py, pv = _yr(ctx, P, "population_jun30")
    iy, iv = ctx.index_2006(dict(zip(py, pv)))
    ctx.line(ax, iy, iv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.BLUE, lambda v: f"{v:.1f}", dy=8)
    _mark(ig, ax, "census", dy=0.16)
    _note(p, ax, 0.02, 0.96, f"{_at(py, pv, 2006) / 1e6:.1f}m in 2006, "
          f"{pv[-1] / 1e6:.1f}m in {py[-1]}:\nnet overseas migration did "
          "most of the growth")
    _foot(p, ax, "ABS estimated resident population at 30 June; the 2021 step "
          "is the Census rebase, a revision")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    ty, tv = _yr(ctx, "demography/fertility.csv", "tfr")
    ax.axhline(2.1, color=p.FAINT, lw=1.0, ls=":")
    ctx.line(ax, ty, tv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ty, tv, p.PURPLE, lambda v: f"{v:.2f}", dy=-14)
    _note(p, ax, 0.02, 0.96, "2.1 is replacement; the rate has been below it "
          "for the\nwhole window and is 1.48 in 2024")
    _foot(p, ax, "World Bank SP.DYN.TFRT.IN; the ABS's own rate agrees to "
          "about 0.02")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    by, bv = _yr(ctx, "demography/births_deaths.csv", "crude_birth_rate")
    dy, dv = _yr(ctx, "demography/births_deaths.csv", "crude_death_rate")
    ctx.line(ax, by, bv, p.GREEN, label="Births")
    ctx.line(ax, dy, dv, p.RED_D, label="Deaths")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96, "the gap is natural increase and it has closed "
          "from\n6.7 per 1,000 in 2006 to 3.9 in 2024")
    _foot(p, ax, "ABS published crude rates, births and deaths, against the "
          "same 30 June population")

    ax = ig.slot("demography.natural_migration", "Natural increase and net "
                 "migration (per 1,000 people)")
    ny, nv = _yr(ctx, "demography/natural_increase.csv",
                 "natural_increase_per_1000")
    my, mv = _yr(ctx, "demography/natural_increase.csv",
                 "net_migration_per_1000")
    ctx.bars(ax, ny, nv, lambda v: p.GREEN)
    ctx.line(ax, my, mv, p.BLUE, label="Net overseas migration")
    _barkey(ax, p.GREEN, "Natural increase")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    pk = max(zip(my, mv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f} in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=8.4, fontweight="bold",
                color=p.BLUE)
    _mark(ig, ax, "borders", dy=0.30)
    _foot(p, ax, "ABS births − deaths, and NOM net, each ÷ the 30 June "
          "population; NOM stops at its last final year")
    _finish(ctx, ig)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    S = "security/security.csv"

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000, log "
                 "scale)")
    hy, hv = _yr(ctx, S, "homicide_per_100k")
    ctx.line(ax, hy, hv, p.RED)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, hy, hv, p.RED, lambda v: f"{v:.1f}", dy=8)
    _note(p, ax, 0.02, 0.92, "police-recorded victims where the offence "
          "occurred:\na police count, not the death-certificate count")
    _foot(p, ax, "ABS Recorded Crime — Victims 4510.0, published victimisation "
          "rate")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    sy, sv = _yr(ctx, S, "suicide_per_100k")
    ctx.line(ax, sy, sv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, sy, sv, p.PURPLE, lambda v: f"{v:.1f}", dy=8)
    _note(p, ax, 0.02, 0.96, "the WHO's age-standardised cut of the same "
          "registration data;\n2024 and 2025 are not yet published")
    _foot(p, ax, "WHO Global Health Observatory MH_12, age-standardised")

    ax = ig.slot("security.road_deaths", "Road traffic deaths "
                 "(per 100,000)")
    ry, rv = _yr(ctx, S, "road_deaths_per_100k")
    ctx.line(ax, ry, rv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.GOLD, lambda v: f"{v:.1f}", dy=8)
    _note(p, ax, 0.02, 0.96, "the count of people killed on the road, over "
          "the 30 June\npopulation; the series stops in 2022")
    _foot(p, ax, "BITRE Australian Road Deaths Database ÷ ABS ERP; the mirror "
          "ends October 2023")

    ax = ig.slot("security.lens", "Lens — the same two deaths as counts "
                 "(persons a year)")
    hy, hv = _yr(ctx, S, "homicide_victims")
    ry, rv = _yr(ctx, S, "road_deaths")
    ctx.line(ax, ry, rv, p.GOLD, split_year=max(ry), label="Road deaths")
    ctx.line(ax, hy, hv, p.RED, label="Homicide victims")
    ig.add_recessions(ax, label=False)
    ax.set_ylabel("persons a year", fontsize=8.4, color=p.MUTED)
    ax.set_ylim(0, max(rv) * 1.25)
    ax.legend(loc="center right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96, f"road deaths fell from {rv[0]:,.0f} to "
          f"{rv[-1]:,.0f} while the\npopulation grew 35%; homicide victims "
          f"from {hv[0]:,.0f} to {hv[-1]:,.0f}")
    _foot(p, ax, "BITRE ARDD and ABS recorded crime, counts — the numerators "
          "of the panels above")
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    M = "mortality/mortality.csv"

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000 people)")
    dy, dv = _yr(ctx, M, "crude_death_rate")
    ctx.line(ax, dy, dv, p.INK)
    ig.add_recessions(ax, label=False)
    pk = max(zip(dy, dv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.2f} in {pk[0]}", pk, textcoords="offset points",
                xytext=(2, 8), ha="left", fontsize=8.4, fontweight="bold",
                color=p.INK)
    _note(p, ax, 0.02, 0.55, "registered deaths over the 30 June population; "
          "the 2022\npeak is the pandemic and an ageing population together",
          va="top")
    _foot(p, ax, "ABS Deaths, Australia, year of registration")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above the 2015–2019 average)")
    ey, ev = _yr(ctx, M, "excess_deaths_pct")
    base_y = [y for y in dy if 2015 <= y <= 2019]
    base = sum(_at(dy, dv, y) for y in base_y) / len(base_y)
    ctx.bars(ax, ey, ev, lambda v: p.ALERT if v > 0 else p.GREEN)
    ig.add_recessions(ax, label=False)
    pk = max(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}%", pk, textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=8.6, fontweight="bold",
                color=p.ALERT)
    _note(p, ax, 0.02, 0.96, f"against the {base:.2f} per 1,000 mean of "
          "2015–2019 — the baseline\nis the measurement, and this one is "
          "unadjusted for age")
    _foot(p, ax, "derived from the ABS crude death rate, one vintage, no "
          "population adjustment")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    cy, cv = _yr(ctx, M, "covid_deaths_per_100k")
    ctx.bars(ax, cy, cv, lambda v: p.PURPLE)
    ig.add_recessions(ax, label=False)
    pk = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f} in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 6), ha="center", fontsize=8.4, fontweight="bold",
                color=p.PURPLE)
    _note(p, ax, 0.02, 0.96, "U07.1–U07.2 as the UNDERLYING cause; deaths "
          "involving\nCOVID are a much larger number and a different "
          "question")
    _foot(p, ax, "ABS Causes of Death 2024, one vintage, ÷ the same year's "
          "ERP")

    ax = ig.slot("mortality.lens", "Lens — COVID-19 as a share of all "
                 "registered deaths (%)")
    rate = dict(zip(cy, cv))
    deaths = dict(zip(dy, dv))
    sy = [y for y in dy if y in rate and y >= 2020]
    sv = [rate[y] / (deaths[y] * 100) * 100 for y in sy]
    ctx.bars(ax, sy, sv, lambda v: p.PURPLE)
    ig.add_recessions(ax, label=False)
    ax.set_ylabel("% of registered deaths", fontsize=8.4, color=p.MUTED)
    ax.set_ylim(0, max(sv) * 1.45)
    pk = max(zip(sy, sv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}%", pk, textcoords="offset points",
                xytext=(0, 5), ha="center", fontsize=8.6, fontweight="bold",
                color=p.PURPLE)
    _note(p, ax, 0.02, 0.96, "the share of all deaths, not of the population:\n"
          "2022 was the worst year, not 2020")
    _foot(p, ax, "derived: COVID-19 per 100,000 ÷ deaths per 100,000, same "
          "registration year")
    _finish(ctx, ig)


# --------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    M = "migration/migration.csv"

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    iy, iv = _yr(ctx, M, "immigration_per_1000")
    ey, ev = _yr(ctx, M, "emigration_per_1000")
    ctx.line(ax, iy, iv, p.BLUE, label="Arrivals")
    ctx.line(ax, ey, ev, p.ALERT, label="Departures")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96, "NOM is a definition, not a visa count: present "
          "12 of the\nnext 16 months. 2020–21 is the border closure")
    _foot(p, ax, "ABS Net Overseas Migration, calendar years ÷ 30 June "
          "population")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    ny, nv = _yr(ctx, M, "net_migration_per_1000")
    ctx.bars(ax, ny, nv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    pk = max(zip(ny, nv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f} in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 7), ha="center", fontsize=8.4, fontweight="bold",
                color=p.GREEN)
    _mark(ig, ax, "borders", dy=0.30)
    _foot(p, ax, "ABS NOM net ÷ 30 June population; the last final year is "
          "2024")

    ax = ig.slot("migration.foreign_born", "Overseas-born share of the "
                 "population (% of population)")
    fy, fv = _yr(ctx, M, "overseas_born_share_pct")
    ctx.line(ax, fy, fv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, fy, fv, p.TEAL, lambda v: f"{v:.0f}%", dy=8)
    _note(p, ax, 0.02, 0.96, "a stock from a different question — who is "
          "here — not\nthe arrivals on the panels beside it")
    _foot(p, ax, "ABS ERP by country of birth: total minus Australia-born, "
          "30 June")

    ax = ig.slot("migration.lens", "Lens — net overseas migration, persons "
                 "a year")
    py, pv = _yr(ctx, "demography/population.csv", "population_jun30")
    pop = dict(zip(py, pv))
    ly = [y for y in ny if y in pop]
    lv = [_at(ny, nv, y) / 1000 * pop[y] / 1000 for y in ly]
    ctx.bars(ax, ly, lv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    ax.set_ylabel("thousand persons a year", fontsize=8.4, color=p.MUTED)
    ax.set_ylim(min(0, min(lv)) * 1.3, max(lv) * 1.3)
    pk = max(zip(ly, lv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:,.0f}k", pk, textcoords="offset points",
                xytext=(0, 6), ha="center", fontsize=8.4, fontweight="bold",
                color=p.GREEN)
    _note(p, ax, 0.02, 0.96, "the same NOM series as a count: the rate on "
          "slot 2 hides\nthat Australia's population is 35% larger than in "
          "2006")
    _foot(p, ax, "nets to persons: per-1,000 rate × 30 June population")
    _finish(ctx, ig)


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Australian Economy — Growth Without a Recession",
         subtitle="Calendar-year national accounts built from the ABS "
                  "quarters, with the IMF's growth line as the check.",
         source="Sources: ABS ANA, CPI and Labour Force · IMF WEO",
         alt="Four panels on the Australian economy, 2006–2025. Real GDP "
             "grew 2.7% in 2006, fell 2.1% in 2020 and grew 5.4% in 2021; "
             "GDP per person in US dollars runs from about 36,700 to "
             "65,100; inflation peaked at 6.6% in 2022 from 0.9% in 2020; "
             "unemployment peaked at 6.5% in 2020 and is 4.2% in 2025."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — A July–June Year, Twice Measured",
         subtitle="General government on the IMF's fiscal-year basis, with "
                  "the ABS's own GFS accounts beside it.",
         source="Sources: IMF Fiscal Monitor · ABS Government Finance "
                "Statistics 5512.0 · World Bank",
         alt="Four panels on Australian public finances, on July–June years "
             "drawn at their midpoints. Revenue is 36.7% of GDP in "
             "FY2024/25 and expenditure 39.6%; the overall balance reaches "
             "−8.7% of GDP in FY2019/20; gross debt rises from 9.9% to "
             "56.9% and is 51.9%; interest paid is about 1.7% of GDP on the "
             "ABS measure."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Where the Money Goes — Social Protection and the Rest",
         subtitle="General-government spending by function (OECD COFOG) and "
                  "the economy's and the state's investment rates.",
         source="Sources: OECD COFOG · ABS ANA",
         alt="Four panels on Australian spending. Outlays by function reach "
             "48.4% of GDP in 2020 with social protection the largest group "
             "at 11.5%; the rest of government runs between 27% and 36% of "
             "GDP; whole-economy investment runs between 22.6% and 28.2% of "
             "GDP; public investment is 3.9%."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — One Customer Buying a Third of the Goods",
         subtitle="Goods and services on the national-accounts basis, and "
                  "the customs-basis destinations of the goods themselves.",
         source="Sources: ABS ANA · ABS MERCH_EXP",
         alt="Four panels on Australian trade. Exports and imports of goods "
             "and services run near a quarter of GDP each and the balance "
             "peaks at 5.0% of GDP in 2022; China takes 33.6% of goods "
             "exports in 2025, Japan 11.6%, Korea 7.9% and the United "
             "States 7.7%; the one-year ranking puts China, Japan and Korea "
             "first."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Money & Markets — the Cash Rate, the Bond, the Dollar and "
               "the ASX",
         subtitle="The Reserve Bank's cash rate as the BIS republishes it, "
                  "the OECD's bond series and the ASX 200 in US dollars.",
         source="Sources: BIS (RBA series) · OECD · World Bank · Yahoo "
                "Finance (index, not official)",
         alt="Four panels on Australian markets. The cash rate falls from "
             "6.65% in 2008 to 0.10% in 2021 and rises to 4.35% in 2024 "
             "against inflation that peaked at 6.6%; the ten-year yield "
             "falls to 0.92% in 2020 and is 4.37%; the dollar peaks at 137 "
             "against its 2006 level in 2012 and is 86; the ASX 200 in US "
             "dollars is 140 against 476 for the S&P 500."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — Household Debt, Two Loan Definitions and a Gap",
         subtitle="BIS household credit on the canonical GDP basis, APRA's "
                  "two asset-quality measures, and the debt-service burden.",
         source="Sources: BIS total credit · APRA quarterly ADI performance",
         alt="Four panels on household credit. Debt is 114% of GDP in 2025 "
             "after a 123% peak in 2016; the household lending rate is "
             "pending because no reachable publisher carries it; impaired "
             "facilities run 0.3–1.5% to 2021 and APRA's non-performing "
             "measure 0.8–1.1% from 2022, a definition change; the "
             "debt-service ratio is 15.5% of disposable income."),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="People — Inequality, a Proxy for Poverty, and the Award "
               "Wage",
         subtitle="The ABS's biennial Gini beside the World Bank's, the "
                  "international poverty line, and the minimum wage in two "
                  "currencies.",
         source="Sources: ABS Household Income and Wealth 6523.0 · World "
                "Bank · OECD",
         alt="Four panels on living standards. The Gini moves between 32.0 "
             "and 33.6 and the survey stops in 2019–20; the World Bank's "
             "US$4.20-a-day line reads 0.9% in 2008 and 1.5% in 2020, with "
             "no national rate existing; the minimum wage is US$2,602 a "
             "month in 2025 and A$931.95 a week."),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="Australia in the World — Size, Development, Integrity and "
               "Reserves",
         subtitle="GDP and reserves in US dollars, the UNDP's development "
                  "index and Transparency International's score.",
         source="Sources: World Bank WDI · UNDP HDR 2025 · Transparency "
                "International CPI 2025",
         alt="Four panels on Australia among the world's economies. GDP is "
             "US$1.80 trillion in 2025; the Human Development Index is "
             "0.968 in 2023; the Corruption Perceptions Index is 76 in 2025 "
             "against 85 in 2012; official reserves are US$72.6 billion."),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — Growth From Arrivals, Not From Births",
         subtitle="Population, fertility, births, deaths and the two "
                  "components of growth, from the ABS's own estimates.",
         source="Sources: ABS ERP, Births, Deaths and NOM · World Bank",
         alt="Four panels on Australia's population. It grows from 20.5 "
             "million in 2006 to 27.6 million in 2025, an index of 135; "
             "fertility falls from 1.91 to 1.48 against a replacement rate "
             "of 2.1; births fall from 13.2 to 10.7 per 1,000 while deaths "
             "rise from 6.5 to 6.8; net migration peaks at 19.9 per 1,000 "
             "in 2023 while natural increase shrinks to 3.9."),
    dict(id="10", slug="security", topic="security", builder=plate_security,
         title="Security — Homicide, Suicide and the Road Toll",
         subtitle="Police-recorded homicide, the WHO's suicide rate and "
                  "BITRE's road-death count, each on its own definition.",
         source="Sources: ABS Recorded Crime 4510.0 · WHO GHO · BITRE ARDD",
         alt="Four panels on violent and accidental death. Homicide falls "
             "from 2.7 to 1.6 per 100,000; suicide runs between 10.8 and "
             "13.3 and stops in 2023; road deaths fall from 7.8 to 4.5 per "
             "100,000 and stop in 2022; in counts, road deaths fall from "
             "1,598 to 1,180 and homicide victims from 562 to 435."),
    dict(id="11", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — the Pandemic Wave and What It Was Measured "
               "Against",
         subtitle="Registered deaths, excess deaths against a quoted "
                  "baseline, and COVID-19 as the underlying cause.",
         source="Sources: ABS Deaths and Causes of Death 3303.0",
         alt="Four panels on mortality. The crude death rate rises from 6.5 "
             "to 7.3 per 1,000 in 2022; excess deaths are 11.9% above the "
             "2015–2019 average that year and 4.0% in 2025; COVID-19 as the "
             "underlying cause peaks at 37.9 per 100,000 in 2022; it was "
             "5.2% of all registered deaths that year."),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — the Border, the Rebound and Who Is Here",
         subtitle="Net overseas migration and its two gross flows, the "
                  "overseas-born stock, and the count behind the rate.",
         source="Sources: ABS Net Overseas Migration · ABS ERP by country "
                "of birth",
         alt="Four panels on Australian migration, per 1,000 people. "
             "Arrivals peak at 27.7 in 2023 and departures fall to 7.8; net "
             "migration goes from −0.2 in 2020 to 19.9 in 2023; the "
             "overseas-born share rises from 24.6% to 32.0%; in persons, net "
             "migration is about 531,000 in 2023."),
)
