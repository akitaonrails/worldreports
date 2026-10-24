"""The usa plates, drawn on the plate spine.

Every plate declares its topic and claims its four panels by spine key, so
each sits on the same indicator, unit and scale as every other country's
(PLATE_SPINE.md, core/spine.py). The national series the United States
argues about — the federal budget on its fiscal year, U-6, the
supplemental poverty measure, the Census vintages — ride beside the
canonical lines as second, labelled lines, and the country's own stories
take the lens slots: overdoses, child poverty and the Child Tax Credit,
where the goods come from, household debt by type, life expectancy.

Every number printed in a note is read from the committed CSVs when the
plate is drawn, so a refresh moves the note with the line. Rates per
100,000 or per 1,000 are the publisher's where one is published; where
only a count is, it is divided by the Census 1 July resident population
(social/population_july1.csv) through ctx.per_100k / ctx.per_1000, which
match the two series year by year. DATA_NOTES.md lists each conversion.
"""
from __future__ import annotations

import numpy as np
from matplotlib.patches import Patch

from countries.usa import events

# 40 hours a week for 52 weeks, over 12 months: the convention that turns
# an hourly wage floor into the spine's US$ per month.
HOURS_PER_MONTH = 40 * 52 / 12


# ---------------------------------------------------------------- reading
def _d(ctx, rel: str, col: str, key: str = "year", window: bool = True
       ) -> dict[int, float]:
    """{year: value} for one column, blanks dropped (never zero-filled).

    Only the plates' window (country.yaml years) unless `window=False`,
    which a projection read for a note needs.
    """
    t = ctx.table(rel)
    lo, hi = (ctx.YEARS[0], ctx.YEARS[-1]) if window else (-1e9, 1e9)
    out = {}
    for y, v in zip(t[key], t[col]):
        if isinstance(v, float) and v == v and y == y and lo <= y <= hi:
            out[int(y)] = v
    return out


def _s(ctx, rel: str, col: str, key: str = "year") -> dict[int, str]:
    """{year: text} for a label column (a vintage, a basis)."""
    t = ctx.table(rel)
    return {int(y): v for y, v in zip(t[key], t[col])
            if isinstance(v, str) and y == y}


def _xy(d: dict[int, float], lo: int | None = None, hi: int | None = None):
    ys = [y for y in sorted(d) if (lo is None or y >= lo)
          and (hi is None or y <= hi)]
    return ys, [d[y] for y in ys]


def _scale(d: dict[int, float], k: float) -> dict[int, float]:
    return {y: v * k for y, v in d.items()}


def _ratio(num: dict[int, float], den: dict[int, float], k: float = 100.0
           ) -> dict[int, float]:
    """num / den × k for the years both have, matched by year."""
    return {y: num[y] / den[y] * k for y in num if y in den and den[y]}


def _pop(ctx) -> dict[int, float]:
    """The Census 1 July resident population: the denominator of every
    rate these plates compute. See DATA_NOTES.md."""
    return _d(ctx, "social/population_july1.csv", "population")


def _rate(fn, count: dict[int, float], pop: dict[int, float]):
    """A rate through core.rates, for the years the population covers.

    The running year has a count and no population yet; it is left out
    here, by name, rather than letting a missing denominator raise.
    """
    ys, vs = fn({y: v for y, v in count.items() if y in pop}, pop)
    return dict(zip(ys, vs))


# ---------------------------------------------------------------- drawing
def _note(ctx, ax, text, x=0.015, y=0.04, ha="left", va="bottom",
          color=None, size=8.0):
    ax.text(x, y, text, transform=ax.transAxes, fontsize=size,
            color=color or ctx.p.muted, style="italic", ha=ha, va=va,
            zorder=6, parse_math=False)


def _label(ctx, ax, x, y, text, color, offset=(0, 8), ha="center",
           size=8.6, va="bottom"):
    ax.annotate(text, (x, y), textcoords="offset points", xytext=offset,
                fontsize=size, fontweight="bold", color=color, ha=ha,
                va=va, zorder=6, parse_math=False)


def _legend(ctx, ax, loc="upper left", ncol=1, handles=None, **kw):
    kw.setdefault("fontsize", 8.6)
    if handles is not None:
        kw["handles"] = handles
    ax.legend(loc=loc, ncol=ncol, frameon=False, labelcolor=ctx.p.ink,
              handlelength=1.6, borderaxespad=0.3, columnspacing=1.2, **kw)


def _proxy(color, label, hatch=None):
    return Patch(facecolor=color, edgecolor="white", hatch=hatch,
                 label=label)


def _line(ctx, ax, d, color, label="", lw=2.4, ls="-", ms=3.6, **kw):
    ys, vs = _xy(d, **kw)
    if ys:
        ctx.line(ax, ys, vs, color, label=label, lw=lw, ls=ls, ms=ms)


def _thin(ctx, ax, d, color, label="", **kw):
    """The second line beside a canonical one: thinner, dashed, smaller."""
    _line(ctx, ax, d, color, label=label, lw=1.6, ls=(0, (4, 2)), ms=2.6,
          **kw)


def _frame(ig, ax, slot1=False):
    """Year ticks and the recession bands. Slot 1 carries the band names,
    inside the axes along the bottom: above it they collide with the panel
    title, which sits over the same left-hand years."""
    ig.style_axis(ax)
    ig.add_recessions(ax, label=slot1, inside=slot1)


def _subset(child: str, parent: str) -> str:
    """A legend label that says one series is contained in another."""
    return f"{child} (subset of {parent})"


def _fmt_bn(v: float) -> str:
    return f"US$ {v / 1000:.1f}tn" if abs(v) >= 1000 else f"US$ {v:,.0f}bn"


# ================================================================ economy
def plate_economy(ctx, ig):
    gdp = "macro/gdp.csv"
    growth = _d(ctx, gdp, "real_growth")

    ax = ig.slot("economy.growth", "Real GDP growth")
    ys, vs = _xy(growth)
    ctx.bars(ax, ys, vs, lambda v: ctx.p.NAVY if v >= 0 else ctx.p.RED,
             width=0.68)
    _frame(ig, ax, slot1=True)
    for y in (2020, 2021):
        if y in growth:
            v = growth[y]
            _label(ctx, ax, y, v, f"{v:+.1f}%",
                   ctx.p.RED if v < 0 else ctx.p.NAVY,
                   offset=(0, 4 if v > 0 else -4),
                   va="bottom" if v > 0 else "top")
    _note(ctx, ax, "BEA, chained dollars. Hatched: 2026 so far,\n"
                   "against the same quarters of 2025.", y=0.96, va="top")

    ax = ig.slot("economy.gdp_per_person", "GDP per person, current US$")
    wb = _d(ctx, "international/world.csv", "gdp_per_person_usd")
    _line(ctx, ax, wb, ctx.p.NAVY, label="World Bank (NY.GDP.PCAP.CD)",
          lw=2.6)
    _frame(ig, ax)
    last = max(wb)
    _label(ctx, ax, last, wb[last], f"US$ {wb[last]:,.0f}", ctx.p.NAVY,
           offset=(-4, 7), ha="right")
    bea = _d(ctx, gdp, "gdp_per_capita_usd")
    if last in bea:
        _note(ctx, ax, f"BEA's own figure for {last}: US$ {bea[last]:,.0f}\n"
                       f"(a slightly different population).", y=0.05)
    _legend(ctx, ax, loc="lower right")

    ax = ig.slot("economy.inflation", "Consumer prices, change on a year earlier")
    cpi = "macro/cpi.csv"
    head, core = _d(ctx, cpi, "value"), _d(ctx, cpi, "core")
    _line(ctx, ax, head, ctx.p.RED, label="CPI-U, all items", lw=2.6)
    _thin(ctx, ax, core, ctx.p.NAVY, label="core, less food and energy")
    _frame(ig, ax)
    ax.axhline(2.0, color=ctx.p.TEAL, lw=1.0, ls=(0, (2, 2)), zorder=2,
               label="Fed's 2% goal")
    peak = max(head, key=head.get)
    _label(ctx, ax, peak, head[peak], f"{head[peak]:.1f}% in {peak}",
           ctx.p.RED, offset=(0, 6))
    _legend(ctx, ax, loc="upper left")

    ax = ig.slot("economy.unemployment", "Unemployment: the headline rate and the broad one")
    une = "macro/unemployment.csv"
    u3, u6 = _d(ctx, une, "value"), _d(ctx, une, "u6")
    _thin(ctx, ax, u6, ctx.p.GOLD,
          label="U-6, adding part-time for economic reasons")
    _line(ctx, ax, u3, ctx.p.NAVY, label=_subset("U-3, the headline rate",
                                                "U-6"), lw=2.6)
    _frame(ig, ax)
    year, text = events.BREAKS["unemployment_2025"]
    ax.annotate(text, xy=(year, u3[year]), xytext=(2019.0, 20.0),
                fontsize=7.8, color=ctx.p.RED, style="italic",
                arrowprops=dict(arrowstyle="-", color=ctx.p.RED, lw=0.8,
                                shrinkA=2, shrinkB=4))
    _legend(ctx, ax, loc="upper right")


# ================================================================= fiscal
def plate_fiscal(ctx, ig):
    gg = "fiscal/general_government.csv"
    bud = "fiscal/budget.csv"
    fy = "fiscal_year"

    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure")
    _line(ctx, ax, _d(ctx, gg, "expenditure_pct_gdp"), ctx.p.RED,
          label="general government: expenditure", lw=2.6)
    _line(ctx, ax, _d(ctx, gg, "revenue_pct_gdp"), ctx.p.NAVY,
          label="general government: revenue", lw=2.6)
    _thin(ctx, ax, _d(ctx, bud, "outlays_pct_gdp", fy), ctx.p.RED,
          label="federal outlays, fiscal year")
    _thin(ctx, ax, _d(ctx, bud, "receipts_pct_gdp", fy), ctx.p.NAVY,
          label="federal receipts, fiscal year")
    _frame(ig, ax, slot1=True)
    _legend(ctx, ax, loc="upper left", ncol=2, fontsize=8.0)
    _note(ctx, ax, "General government is federal, state and local, by calendar\n"
                   "year (IMF). The federal budget runs October to September.",
          y=0.86, va="top")

    ax = ig.slot("fiscal.balance", "Overall balance and primary balance")
    bal = _d(ctx, gg, "balance_pct_gdp")
    ys, vs = _xy(bal)
    ctx.bars(ax, ys, vs, lambda v: ctx.p.RED if v < 0 else ctx.p.GREEN,
             width=0.68)
    _line(ctx, ax, _d(ctx, gg, "primary_balance_pct_gdp"), ctx.p.GOLD,
          label="primary balance, excluding interest", lw=2.2)
    fed = _d(ctx, bud, "deficit_pct_gdp", fy)
    _thin(ctx, ax, fed, ctx.p.NAVY, label="federal deficit, fiscal year")
    _frame(ig, ax)
    worst = min(bal, key=bal.get)
    _label(ctx, ax, worst, bal[worst], f"{bal[worst]:.1f}%", ctx.p.RED,
           offset=(-12, -2), va="top", ha="right")
    _legend(ctx, ax, loc="upper right", fontsize=8.0, handles=[
        _proxy(ctx.p.RED, "general government overall balance"),
        *ax.get_legend_handles_labels()[0]])

    ax = ig.slot("fiscal.debt", "Gross debt")
    debt = "fiscal/debt.csv"
    g = _d(ctx, gg, "gross_debt_pct_gdp")
    _line(ctx, ax, g, ctx.p.NAVY, label="general government, gross (IMF)",
          lw=2.6)
    _thin(ctx, ax, _d(ctx, debt, "gross_pct_gdp", fy), ctx.p.GOLD,
          label="federal gross debt, 30 September")
    _thin(ctx, ax, _d(ctx, debt, "public_pct_gdp", fy), ctx.p.TEAL,
          label=_subset("federal debt held by the public",
                        "federal gross debt"))
    _frame(ig, ax)
    last = max(g)
    _label(ctx, ax, last, g[last], f"{g[last]:.0f}%", ctx.p.NAVY,
           offset=(-4, 7), ha="right")
    _legend(ctx, ax, loc="upper left", fontsize=8.0)
    _note(ctx, ax, "Federal gross debt includes what the Social Security\n"
                   "and Medicare trust funds hold; held by the public does not.",
          x=0.985, y=0.96, ha="right", va="top")

    ax = ig.slot("fiscal.interest", "Interest paid")
    gdp = _d(ctx, "macro/gdp.csv", "nominal_usdbn")
    paid = _ratio(_d(ctx, "fiscal/interest.csv", "interest_paid_usdmn"),
                  _scale(gdp, 1000))
    _line(ctx, ax, paid, ctx.p.NAVY,
          label="general government, interest paid (OECD)", lw=2.6)
    sp = "fiscal/spending.csv"
    est = _d(ctx, sp, "estimate", fy)
    net = {y: v for y, v in _d(ctx, sp, "net_interest_usdbn", fy).items()
           if not est.get(y)}
    fed_net = _ratio(net, _d(ctx, bud, "gdp_usdbn", fy))
    _thin(ctx, ax, fed_net, ctx.p.PURPLE,
          label="federal net interest, fiscal year (OMB)")
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left", fontsize=8.0)
    defense = _d(ctx, sp, "defense_usdbn", fy)
    cross = next((y for y in sorted(net) if y in defense
                  and net[y] > defense[y]), None)
    if cross:
        _note(ctx, ax, f"FY{cross}: federal net interest, {_fmt_bn(net[cross])},\n"
                       f"passed national defense, {_fmt_bn(defense[cross])}.",
              x=0.985, y=0.96, ha="right", va="top")


# =============================================================== spending
COFOG = (  # (columns summed, label, colour name)
    (("social_protection",), "social protection", "NAVY"),
    (("health",), "health", "RED"),
    (("education",), "education", "GOLD"),
    (("general_public_services",), "general public services", "TEAL"),
    (("economic_affairs",), "economic affairs", "BLUE"),
    (("defence", "public_order"), "defence and public order", "PURPLE"),
)


def plate_spending(ctx, ig):
    cf = "fiscal/cofog.csv"
    total = _d(ctx, cf, "total")

    ax = ig.slot("spending.by_function", "General-government spending by function")
    years = sorted(total)
    bottom = np.zeros(len(years))
    handles = []
    named = {y: 0.0 for y in years}
    for cols, label, colour in COFOG:
        parts = [_d(ctx, cf, c) for c in cols]
        vals = np.array([sum(p[y] for p in parts) for y in years])
        for y, v in zip(years, vals):
            named[y] += v
        ax.bar(years, vals, bottom=bottom, width=0.7, zorder=3,
               color=getattr(ctx.p, colour), edgecolor="white", linewidth=0.4)
        bottom = bottom + vals
        handles.append(_proxy(getattr(ctx.p, colour), label))
    other = np.array([total[y] - named[y] for y in years])
    ax.bar(years, other, bottom=bottom, width=0.7, zorder=3,
           color=ctx.p.faint, edgecolor="white", linewidth=0.4)
    handles.append(_proxy(ctx.p.faint, "other"))
    # Unlabelled on purpose: inside the axes the band names would sit on
    # the stacked bars, and above it they collide with the title.
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left", ncol=4, handles=handles, fontsize=7.6)

    ax = ig.slot("spending.social_protection", "Social protection and everything else")
    sp = _d(ctx, cf, "social_protection")
    rest = {y: total[y] - sp[y] for y in sp if y in total}
    _line(ctx, ax, rest, ctx.p.TEAL, label="everything else", lw=2.6)
    _line(ctx, ax, sp, ctx.p.NAVY, label="social protection", lw=2.6)
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left")
    health = _d(ctx, cf, "health")
    last = max(sp)
    if last in health and health[last] > sp[last]:
        _note(ctx, ax, f"{last}: health, {health[last]:.1f}% of GDP, is a larger\n"
                       f"function than social protection, {sp[last]:.1f}%.",
              y=0.05)

    ax = ig.slot("spending.investment", "Investment, whole economy")
    inv = _d(ctx, "macro/economy_wdi.csv", "gfcf_pct_gdp")
    _line(ctx, ax, inv, ctx.p.NAVY, label="gross fixed capital formation",
          lw=2.6)
    _frame(ig, ax)
    lo = min(inv, key=inv.get)
    _label(ctx, ax, lo, inv[lo], f"{inv[lo]:.1f}% in {lo}", ctx.p.NAVY,
           offset=(0, -6), va="top")
    _legend(ctx, ax, loc="upper right")

    ax = ig.slot("spending.public_investment", "Public investment")
    pub = _d(ctx, "fiscal/public_investment.csv", "gov_gfcf_pct_gdp")
    _line(ctx, ax, pub, ctx.p.TEAL,
          label="general-government gross fixed capital formation", lw=2.6)
    _frame(ig, ax)
    hi = max(pub, key=pub.get)
    _label(ctx, ax, hi, pub[hi], f"{pub[hi]:.1f}% in {hi}", ctx.p.TEAL,
           offset=(0, 7))
    _legend(ctx, ax, loc="upper right")
    _note(ctx, ax, "Roads, buildings, equipment and research, by federal,\n"
                   "state and local government together.", y=0.05)


# ================================================================== trade
def plate_trade(ctx, ig):
    tr = "trade/trade.csv"
    gdp = _d(ctx, "macro/gdp.csv", "nominal_usdbn")

    ax = ig.slot("trade.exports_imports", "Exports and imports of goods and services")
    imp = _ratio(_d(ctx, tr, "imports"), gdp)
    exp = _ratio(_d(ctx, tr, "exports"), gdp)
    _line(ctx, ax, imp, ctx.p.RED, label="imports", lw=2.6)
    _line(ctx, ax, exp, ctx.p.NAVY, label="exports", lw=2.6)
    _frame(ig, ax, slot1=True)
    _legend(ctx, ax, loc="upper right")
    _note(ctx, ax, "BEA national accounts. The US trades little relative\n"
                   "to its size: a large, continental economy.", y=0.80,
          va="top", x=0.015)

    ax = ig.slot("trade.balance", "Trade balance")
    bal = _ratio(_d(ctx, tr, "balance"), gdp)
    ys, vs = _xy(bal)
    ctx.bars(ax, ys, vs, lambda v: ctx.p.RED if v < 0 else ctx.p.GREEN,
             width=0.68)
    _line(ctx, ax, _ratio(_d(ctx, tr, "goods_balance"), gdp), ctx.p.NAVY,
          label="goods", lw=2.0)
    _line(ctx, ax, _ratio(_d(ctx, tr, "services_balance"), gdp), ctx.p.TEAL,
          label="services", lw=2.0)
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left", ncol=3, handles=[
        _proxy(ctx.p.RED, "total balance"),
        *ax.get_legend_handles_labels()[0]])
    census = _d(ctx, "trade/goods.csv", "balance")
    bea_goods = _d(ctx, tr, "goods_balance")
    y = ctx.LAST_FULL_YEAR
    if y in census and y in bea_goods:
        _note(ctx, ax, f"{y} goods deficit, two official bases: Census customs\n"
                       f"US$ {-census[y]:,.1f}bn, BEA balance of payments "
                       f"US$ {-bea_goods[y]:,.1f}bn.", y=0.04)

    ax = ig.slot("trade.destinations", "Where US goods are sold")
    exports_total = _d(ctx, "trade/goods.csv", "exports")
    t = ctx.table("trade/partners.csv")
    by: dict[str, dict[int, float]] = {}
    for yr, name, v in zip(t["year"], t["country"], t["exports"]):
        if isinstance(v, float) and v == v:
            by.setdefault(name, {})[int(yr)] = v
    for name, colour in (("Canada", "TEAL"), ("Mexico", "GOLD"),
                         ("European Union", "NAVY"), ("China", "RED"),
                         ("Japan", "PURPLE")):
        _line(ctx, ax, _ratio(by.get(name, {}), exports_total),
              getattr(ctx.p, colour), label=name, lw=2.2)
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left", ncol=3, fontsize=8.0)
    _note(ctx, ax, "Census, goods on the customs basis.", y=0.96,
          x=0.985, ha="right", va="top")

    ax = ig.slot("trade.lens", "Where the goods come from")
    imports_total = _d(ctx, "trade/goods.csv", "imports")
    byi: dict[str, dict[int, float]] = {}
    for yr, name, v in zip(t["year"], t["country"], t["imports"]):
        if isinstance(v, float) and v == v:
            byi.setdefault(name, {})[int(yr)] = v
    shares = {}
    for name, colour in (("China", "RED"), ("Mexico", "GOLD"),
                         ("European Union", "NAVY"), ("Canada", "TEAL"),
                         ("Vietnam", "PURPLE")):
        shares[name] = _ratio(byi.get(name, {}), imports_total)
        _line(ctx, ax, shares[name], getattr(ctx.p, colour), label=name,
              lw=2.2)
    _frame(ig, ax)
    yr, txt = events.MARKS["china_tariffs"]
    ig.add_event(ax, yr, txt, dy=0.97)
    ax.set_ylim(0, 30)
    ax.set_ylabel("% of goods imports", fontsize=8.6, color=ctx.p.muted)
    _legend(ctx, ax, loc="upper left", ncol=3, fontsize=8.0,
            bbox_to_anchor=(0.0, 0.90))
    china = shares["China"]
    peak = max((y for y in china if y <= ctx.LAST_FULL_YEAR), key=china.get)
    last = ctx.LAST_FULL_YEAR
    if last in china:
        _note(ctx, ax, f"China's share: {china[peak]:.1f}% in {peak}, "
                       f"{china[last]:.1f}% in {last}.", y=0.84, x=0.985,
              ha="right", va="top")


# ================================================================ markets
def plate_markets(ctx, ig):
    ff = "macro/fed_funds.csv"
    lo, hi = _d(ctx, ff, "target_eop"), _d(ctx, ff, "target_hi")
    mid = {y: (v + hi[y]) / 2 if y in hi else v for y, v in lo.items()}
    cpi = _d(ctx, "macro/cpi.csv", "value")

    ax = ig.slot("markets.policy_rate", "The policy rate against inflation")
    _line(ctx, ax, mid, ctx.p.NAVY, label="federal funds target, year end",
          lw=2.6)
    _thin(ctx, ax, cpi, ctx.p.RED, label="CPI inflation, yearly average")
    both = [y for y in sorted(mid) if y in cpi]
    ax.fill_between(both, [mid[y] for y in both], [cpi[y] for y in both],
                    where=[mid[y] < cpi[y] for y in both], interpolate=True,
                    color=ctx.p.RED, alpha=0.10, zorder=1)
    # Unlabelled on purpose: the names would sit on the zero-rate line.
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left")
    _note(ctx, ax, "Shaded where the policy rate sat below inflation.\n"
                   "Midpoint of the target range.", y=0.62, x=0.985,
          ha="right")

    ax = ig.slot("markets.bond_10y", "10-year Treasury yield")
    tre = "macro/treasury.csv"
    _line(ctx, ax, _d(ctx, tre, "ten_year_avg"), ctx.p.NAVY,
          label="10-year Treasury, yearly average", lw=2.6)
    _thin(ctx, ax, _d(ctx, tre, "two_year_avg"), ctx.p.GOLD,
          label="2-year Treasury, yearly average")
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left")
    spread = _d(ctx, tre, "spread_10y_2y_avg")
    inverted = [str(y) for y in sorted(spread) if spread[y] < 0]
    if inverted:
        _note(ctx, ax, "2-year above 10-year on average (inverted):\n"
                       + ", ".join(inverted), y=0.60, x=0.985, ha="right")

    ax = ig.slot("markets.currency", "The dollar against its trading partners")
    ys, vs = ctx.index_2006(_d(ctx, "macro/dollar.csv", "broad_index_avg"))
    usd = dict(zip(ys, vs))
    _line(ctx, ax, usd, ctx.p.NAVY,
          label="broad dollar index, yearly average", lw=2.6)
    _frame(ig, ax)
    last = max(usd)
    peak = max(usd, key=usd.get)
    _label(ctx, ax, peak, usd[peak], f"{usd[peak]:.0f} in {peak}",
           ctx.p.NAVY, offset=(0, -8), va="top")
    _legend(ctx, ax, loc="lower right")
    _note(ctx, ax, "Federal Reserve H.10, trade-weighted. The dollar is the\n"
                   "base currency, so the US line is a basket, not a rate.",
          y=0.05)

    ax = ig.slot("markets.equities", "The S&P 500")
    sp = "markets/sp500.csv"
    ys, vs = ctx.index_2006(_d(ctx, sp, "average"))
    eq = dict(zip(ys, vs))
    _line(ctx, ax, eq, ctx.p.NAVY, label="S&P 500, yearly average", lw=2.6)
    _frame(ig, ax)
    last = max(eq)
    _label(ctx, ax, last, eq[last], f"{eq[last]:.0f}", ctx.p.NAVY,
           offset=(-4, 7), ha="right")
    dd = _d(ctx, sp, "drawdown_pct")
    worst = min(dd, key=dd.get)
    _note(ctx, ax, f"{worst}: down {-dd[worst]:.0f}% from peak to trough within\n"
                   f"the year. A yearly average smooths that away.", y=0.70,
          va="top")
    _legend(ctx, ax, loc="upper left")


# ================================================================= credit
def plate_credit(ctx, ig):
    gdp = _d(ctx, "macro/gdp.csv", "nominal_usdbn")

    ax = ig.slot("credit.household_debt", "Household debt")
    bis = _d(ctx, "credit/household_credit.csv", "hh_credit_pct_gdp_q4")
    _line(ctx, ax, bis, ctx.p.NAVY, label="BIS, households and non-profits",
          lw=2.6)
    hh = "credit/household_debt.csv"
    q = _d(ctx, hh, "quarters")
    total = {y: v for y, v in _d(ctx, hh, "total").items() if q.get(y) == 4}
    _thin(ctx, ax, _ratio(_scale(total, 1000), gdp), ctx.p.GOLD,
          label="FRBNY credit reports, year end")
    _frame(ig, ax, slot1=True)
    peak = max(bis, key=bis.get)
    _label(ctx, ax, peak, bis[peak], f"{bis[peak]:.0f}% in {peak}",
           ctx.p.NAVY, offset=(0, 7))
    _legend(ctx, ax, loc="upper right")

    ax = ig.slot("credit.lending_rate", "What households pay to borrow")
    _line(ctx, ax, _d(ctx, "macro/mortgage.csv", "thirty_year_avg"),
          ctx.p.NAVY, label="30-year fixed mortgage, new loans", lw=2.6)
    rates = "credit/rates.csv"
    _line(ctx, ax, _d(ctx, rates, "cc_apr_all"), ctx.p.RED,
          label="credit card, all accounts", lw=2.2)
    ff = "macro/fed_funds.csv"
    lo, hi = _d(ctx, ff, "target_eop"), _d(ctx, ff, "target_hi")
    _thin(ctx, ax, {y: (v + hi[y]) / 2 if y in hi else v
                    for y, v in lo.items()}, ctx.p.TEAL,
          label="federal funds target, year end")
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left", fontsize=8.0,
            bbox_to_anchor=(0.0, 0.86))
    _note(ctx, ax, "The policy rate returned to about its 2006 level.\n"
                   "The credit card rate did not.", y=0.97, va="top")

    ax = ig.slot("credit.npl", "Balances 90 days or more delinquent")
    dq = "credit/delinquency.csv"
    _line(ctx, ax, _d(ctx, dq, "all"), ctx.p.INK, label="all household debt, % of balances",
          lw=2.8)
    stu = _d(ctx, dq, "student")
    for col, label, colour in (("credit_card", "credit card", "RED"),
                               ("student", "student", "GOLD"),
                               ("mortgage", "mortgage", "NAVY")):
        _thin(ctx, ax, _d(ctx, dq, col), getattr(ctx.p, colour), label=label)
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left", ncol=2, fontsize=8.0)
    year, text = events.BREAKS["student_delinquency"]
    ax.annotate(text.replace(" — ", "\n— "), xy=(year, stu[year]),
                xytext=(2012.6, 16.2), fontsize=7.6, color=ctx.p.RED,
                style="italic",
                arrowprops=dict(arrowstyle="-", color=ctx.p.RED, lw=0.8,
                                shrinkA=2, shrinkB=4))

    ax = ig.slot("credit.lens", "Household debt by type")
    parts = (("mortgage", "mortgage", "NAVY"), ("heloc", "home equity", "BLUE"),
             ("auto", "auto", "TEAL"), ("credit_card", "credit card", "RED"),
             ("student", "student", "GOLD"), ("other", "other", "PURPLE"))
    years = ctx.YEARS
    bottom = np.zeros(len(years))
    handles = []
    for col, label, colour in parts:
        d = _d(ctx, hh, col)
        vals = np.array([d.get(y, np.nan) for y in years])
        part = [y > ctx.LAST_FULL_YEAR for y in years]
        bars = ax.bar(years, np.nan_to_num(vals), bottom=bottom, width=0.7,
                      color=getattr(ctx.p, colour), edgecolor="white",
                      linewidth=0.4, zorder=3)
        for b, p in zip(bars, part):
            if p:
                b.set_alpha(0.62)
                b.set_hatch("//")
        bottom = bottom + np.nan_to_num(vals)
        handles.append(_proxy(getattr(ctx.p, colour), label))
    _frame(ig, ax)
    ax.set_ylim(0, max(bottom) * 1.45)
    ax.set_ylabel("US$ tn", fontsize=8.6, color=ctx.p.muted)
    _legend(ctx, ax, loc="upper left", ncol=3, handles=handles, fontsize=8.0)
    tot = _d(ctx, hh, "total")
    last = ctx.LAST_FULL_YEAR
    _label(ctx, ax, last, tot[last], f"US$ {tot[last]:.1f}tn", ctx.p.INK,
           offset=(-2, 4), ha="right")
    _note(ctx, ax, "FRBNY Consumer Credit Panel, fourth quarter.\n"
                   "Hatched: 2026 so far.", y=0.84, x=0.985, ha="right",
          va="top")


# ================================================================= people
def plate_people(ctx, ig):
    ax = ig.slot("people.gini", "Income inequality, Gini index")
    g = "social/gini.csv"
    segs = (("gini_to_2013", "Census, household money income"),
            ("gini_2013_2017", "_nolegend_"), ("gini_from_2017", "_nolegend_"))
    for col, label in segs:
        _line(ctx, ax, _d(ctx, g, col), ctx.p.NAVY, label=label, lw=2.6)
    _thin(ctx, ax, _d(ctx, "international/worldbank.csv", "gini_wb"),
          ctx.p.GOLD, label="World Bank, disposable income")
    _frame(ig, ax, slot1=True)
    _legend(ctx, ax, loc="upper right")
    _note(ctx, ax, "Census method breaks in 2013 (new income questions) and\n"
                   "2017 (new processing): each year drawn on both bases.",
          y=0.80, va="top")

    ax = ig.slot("people.poverty", "Poverty rate, all people")
    pov = "social/poverty.csv"
    _line(ctx, ax, _d(ctx, pov, "opm_all"), ctx.p.NAVY,
          label="official measure (OPM)", lw=2.6)
    _line(ctx, ax, _d(ctx, pov, "spm_all"), ctx.p.RED,
          label="supplemental measure (SPM)", lw=2.6)
    _thin(ctx, ax, _d(ctx, "social/poverty_intl.csv", "poverty_830_pct"),
          ctx.p.GOLD, label="World Bank, under US$8.30 a day")
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper right")
    _note(ctx, ax, "OPM counts pre-tax cash only. SPM adds tax credits and\n"
                   "benefits and takes off medical and work costs.", y=0.60,
          x=0.985, ha="right")

    ax = ig.slot("people.minimum_wage", "The federal minimum wage, a month of full-time work")
    mw = _d(ctx, "social/minimum_wage.csv", "federal_min_jan1")
    month = _scale(mw, HOURS_PER_MONTH)
    _line(ctx, ax, month, ctx.p.NAVY, label="in the dollars of the day",
          lw=2.6)
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper right")
    changed = _s(ctx, "social/minimum_wage.csv", "changed_on")
    since = max(changed)
    hourly = _d(ctx, "social/minimum_wage.csv", "federal_min_dec31")[since]
    _note(ctx, ax, f"US$ {hourly:.2f} an hour since {changed[since]}, at 40 hours\n"
                   f"a week. Most states set a higher floor of their own.",
          y=0.60, x=0.985, ha="right")

    ax = ig.slot("people.lens", "Child poverty: what the official measure cannot see")
    copm = _d(ctx, pov, "opm_under18")
    cspm = _d(ctx, pov, "spm_under18")
    _line(ctx, ax, copm, ctx.p.NAVY, label="official measure (OPM)", lw=2.6)
    _line(ctx, ax, cspm, ctx.p.RED, label="supplemental measure (SPM)",
          lw=2.6)
    _frame(ig, ax)
    yr, txt = events.MARKS["arp"]
    ig.add_event(ax, yr, txt, dy=0.97)
    ax.set_ylim(0, 30)
    ax.set_ylabel("% of people under 18", fontsize=8.6, color=ctx.p.muted)
    _legend(ctx, ax, loc="upper left", bbox_to_anchor=(0.0, 0.92))
    low = min(cspm, key=cspm.get)
    ax.annotate(f"{low}: the expanded Child Tax Credit cut SPM child\n"
                f"poverty to {cspm[low]:.1f}%. The official measure, which counts\n"
                f"no tax credit, read {copm[low]:.1f}%.",
                xy=(low, cspm[low]), xytext=(2006.6, 2.0), fontsize=7.8,
                color=ctx.p.RED, style="italic",
                arrowprops=dict(arrowstyle="-", color=ctx.p.RED, lw=0.8,
                                shrinkA=2, shrinkB=4))


# ================================================================== world
def plate_world(ctx, ig):
    wb = "international/worldbank.csv"

    ax = ig.slot("world.gdp", "GDP at current prices")
    gdp = _scale(_d(ctx, wb, "gdp_usd"), 1e-9)
    _line(ctx, ax, gdp, ctx.p.NAVY, label="World Bank, current US$", lw=2.6)
    _frame(ig, ax, slot1=True)
    last = max(gdp)
    _label(ctx, ax, last, gdp[last], _fmt_bn(gdp[last]), ctx.p.NAVY,
           offset=(0, -8), ha="center", va="top")
    share = _d(ctx, wb, "us_share_world_gdp")
    s_last = max(share)
    _note(ctx, ax, f"{share[s_last]:.1f}% of world GDP in {s_last}, at market\n"
                   f"exchange rates; less at purchasing-power parity.",
          y=0.60, x=0.985, ha="right")
    _legend(ctx, ax, loc="lower center")

    ax = ig.slot("world.hdi", "Human Development Index")
    hdi = _d(ctx, "social/hdi.csv", "hdi")
    _line(ctx, ax, hdi, ctx.p.NAVY, label="UNDP, 2025 report", lw=2.6)
    _frame(ig, ax)
    lo = min((y for y in hdi if y >= 2019), key=hdi.get)
    _label(ctx, ax, lo, hdi[lo], f"{hdi[lo]:.3f} in {lo}", ctx.p.NAVY,
           offset=(0, -6), va="top")
    _legend(ctx, ax, loc="lower right")
    _note(ctx, ax, "One UNDP vintage throughout: each report recomputes\n"
                   "its own history.", y=0.05)

    ax = ig.slot("world.cpi", "Corruption Perceptions Index")
    tic = "international/corruption.csv"
    cpi = _d(ctx, tic, "score")
    _line(ctx, ax, cpi, ctx.p.NAVY, label="Transparency International",
          lw=2.6)
    old = _d(ctx, tic, "score_pre2012")
    for y, v in old.items():
        ax.plot([y], [v * 10], ls="none", marker="o", ms=6, mfc="none",
                mec=ctx.p.NAVY, mew=1.6, zorder=4,
                label="before 2012, old method ×10")
    _frame(ig, ax)
    first, last = min(cpi), max(cpi)
    _label(ctx, ax, last, cpi[last], f"{cpi[last]:.0f}", ctx.p.NAVY,
           offset=(-4, -6), ha="right", va="top")
    _legend(ctx, ax, loc="lower left")
    _note(ctx, ax, f"Higher is cleaner. {first}: {cpi[first]:.0f}, {last}: "
                   f"{cpi[last]:.0f}.\nThe old 0–10 scale is not joined to "
                   f"the 2012 method.", y=0.05, x=0.985, ha="right")

    ax = ig.slot("world.reserves", "Official reserves")
    res = _scale(_d(ctx, "international/world.csv", "reserves_usd"), 1e-9)
    _line(ctx, ax, res, ctx.p.GOLD, label="World Bank, including gold",
          lw=2.6)
    _frame(ig, ax)
    last = max(res)
    _label(ctx, ax, last, res[last], _fmt_bn(res[last]), ctx.p.GOLD,
           offset=(-4, 7), ha="right")
    _legend(ctx, ax, loc="lower right")
    _note(ctx, ax, "Gold is valued at year-end London prices, so the line\n"
                   "moves with the gold price as much as with policy.",
          y=0.05)


# ============================================================= demography
def plate_demographics(ctx, ig):
    pop = _pop(ctx)

    ax = ig.slot("demography.population", "Resident population")
    ys, vs = ctx.index_2006(pop)
    idx = dict(zip(ys, vs))
    _line(ctx, ax, idx, ctx.p.NAVY, label="Census, 1 July", lw=2.8)
    _frame(ig, ax, slot1=True)
    last = max(pop)
    _label(ctx, ax, last, idx[last], f"{pop[last] / 1e6:.1f}M", ctx.p.NAVY,
           offset=(-4, 7), ha="right")
    proj = _d(ctx, "social/projections.csv", "population", window=False)
    peak = max(proj, key=proj.get)
    _note(ctx, ax, f"Census 2023 projection, middle series: a peak of\n"
                   f"{proj[peak] / 1e6:.0f}M in {peak}, then a slow decline.",
          y=0.13, x=0.985, ha="right")
    _legend(ctx, ax, loc="upper left")

    ax = ig.slot("demography.fertility", "Total fertility rate")
    tfr = _d(ctx, "international/worldbank.csv", "fertility")
    _line(ctx, ax, tfr, ctx.p.NAVY, label="World Bank (NCHS births)", lw=2.6)
    _frame(ig, ax)
    ax.axhline(2.1, color=ctx.p.faint, lw=0.9, ls=(0, (2, 2)), zorder=2)
    ax.text(2023.2, 2.18, "replacement, 2.1", fontsize=7.8, color=ctx.p.muted,
            va="bottom")
    last = max(tfr)
    _label(ctx, ax, last, tfr[last], f"{tfr[last]:.2f}", ctx.p.NAVY,
           offset=(-4, -6), ha="right", va="top")
    _legend(ctx, ax, loc="lower left")

    ax = ig.slot("demography.birth_death", "Births and deaths")
    w = "social/demography_wdi.csv"
    _line(ctx, ax, _d(ctx, w, "birth_rate_per_1000"), ctx.p.NAVY,
          label="crude birth rate", lw=2.6)
    _line(ctx, ax, _d(ctx, w, "death_rate_per_1000"), ctx.p.RED,
          label="crude death rate", lw=2.6)
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper right")
    _note(ctx, ax, "NCHS vital statistics, via the World Bank.", y=0.05)

    ax = ig.slot("demography.natural_migration", "Natural increase and net migration")
    comp = "social/components.csv"
    vint = _s(ctx, comp, "vintage")
    for col, label, colour in (("net_migration_rate", "net international migration (Census)", "TEAL"),
                               ("natural_rate", "natural increase (Census)", "NAVY")):
        d = _d(ctx, comp, col)
        for i, tag in enumerate(("v2019", "v2025")):
            seg = {y: v for y, v in d.items() if vint.get(y) == tag}
            _line(ctx, ax, seg, getattr(ctx.p, colour),
                  label=label if i == 0 else "_nolegend_", lw=2.6)
    un = _rate(ctx.per_1000, _d(ctx, w, "net_migration"), pop)
    _thin(ctx, ax, un, ctx.p.GOLD, label="net migration, UN estimate")
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left")
    nm = _d(ctx, comp, "net_migration_rate")
    peak = max(nm, key=nm.get)
    _label(ctx, ax, peak, nm[peak], f"{nm[peak]:.1f}", ctx.p.TEAL,
           offset=(0, 6))
    _note(ctx, ax, "Census years run July to June; two vintages, not joined\n"
                   "across 2020, the census year.", y=0.05, x=0.985,
          ha="right")


# ============================================================== mortality
def plate_mortality(ctx, ig):
    pop = _pop(ctx)
    m = "social/mortality.csv"
    deaths = {y: v for y, v in _d(ctx, m, "total_deaths").items()
              if y <= ctx.LAST_FULL_YEAR}

    ax = ig.slot("mortality.death_rate", "Crude death rate")
    nchs = _d(ctx, "social/demography_wdi.csv", "death_rate_per_1000")
    _line(ctx, ax, nchs, ctx.p.NAVY, label="NCHS, final", lw=2.6)
    computed = _rate(ctx.per_1000, deaths, pop)
    newer = {y: v for y, v in computed.items() if y > max(nchs)}
    for y, v in newer.items():
        ax.plot([y], [v], ls="none", marker="o", ms=6, mfc="none",
                mec=ctx.p.NAVY, mew=1.6, zorder=4,
                label="provisional count ÷ population")
    _frame(ig, ax, slot1=True)
    peak = max(nchs, key=nchs.get)
    _label(ctx, ax, peak, nchs[peak], f"{nchs[peak]:.1f} in {peak}",
           ctx.p.NAVY, offset=(0, 7))
    _legend(ctx, ax, loc="upper left")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths")
    base = [deaths[y] for y in range(2015, 2020)]
    mean = sum(base) / len(base)
    excess = {y: (v / mean - 1) * 100 for y, v in deaths.items()}
    ys, vs = _xy(excess)
    ctx.bars(ax, ys, vs, lambda v: ctx.p.RED if v > 0 else ctx.p.faint,
             width=0.68)
    _frame(ig, ax)
    peak = max(excess, key=excess.get)
    _label(ctx, ax, peak, excess[peak], f"+{excess[peak]:.0f}%", ctx.p.RED,
           offset=(0, 4))
    _note(ctx, ax, "All deaths against the 2015–2019 average. A flat baseline:\n"
                   "a growing, ageing population puts earlier years below it.",
          y=0.96, va="top")

    ax = ig.slot("mortality.covid", "COVID-19 deaths")
    dr = "social/death_rates.csv"
    pub = _d(ctx, dr, "covid_underlying_rate")
    cnt = _d(ctx, dr, "covid_underlying")
    under = dict(pub)
    under.update({y: v for y, v in _rate(ctx.per_100k, cnt, pop).items()
                  if y not in pub})
    ys, vs = _xy(under)
    ctx.bars(ax, ys, vs, ctx.p.RED, width=0.68)
    inv = {y: v for y, v in _rate(ctx.per_100k, _d(ctx, m, "covid_involved"),
                                  pop).items()}
    _thin(ctx, ax, inv, ctx.p.NAVY, label="any mention on the certificate")
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper right", handles=[
        _proxy(ctx.p.RED, "underlying cause"),
        *ax.get_legend_handles_labels()[0]])
    peak = max(under, key=under.get)
    _label(ctx, ax, peak, under[peak], f"{under[peak]:.0f}", ctx.p.RED,
           offset=(-8, 0), ha="right", va="center")
    _note(ctx, ax, "None before 2020: the disease did not exist, which\n"
                   "is not a zero.", y=0.55, x=0.985, ha="right")

    ax = ig.slot("mortality.lens", "Life expectancy at birth", unit=False)
    le = _d(ctx, "international/worldbank.csv", "life_expectancy")
    _line(ctx, ax, le, ctx.p.NAVY, label="World Bank (NCHS life tables)",
          lw=2.6)
    _frame(ig, ax)
    ax.set_ylim(74, 81)
    ax.set_ylabel("years", fontsize=8.6, color=ctx.p.muted)
    lo = min(le, key=le.get)
    _label(ctx, ax, lo, le[lo], f"{le[lo]:.1f} years in {lo}", ctx.p.NAVY,
           offset=(0, -6), va="top")
    _legend(ctx, ax, loc="upper left")
    pre = max(y for y in le if y < 2020)
    last = max(le)
    _note(ctx, ax, f"{pre}, before COVID-19: {le[pre]:.1f} years. "
                   f"{last}: {le[last]:.1f}.", y=0.05, x=0.985, ha="right")


# =============================================================== security
def plate_violence(ctx, ig):
    pop = _pop(ctx)
    v = "social/violence.csv"
    intl = "social/security_intl.csv"

    ax = ig.slot("security.homicide", "Homicide rate")
    _line(ctx, ax, _d(ctx, v, "homicide_rate"), ctx.p.NAVY,
          label="CDC, death certificates", lw=2.6)
    _thin(ctx, ax, _d(ctx, intl, "homicide_per_100k"), ctx.p.GOLD,
          label="UNODC, police records")
    _frame(ig, ax, slot1=True)
    hr = _d(ctx, v, "homicide_rate")
    peak = max(hr, key=hr.get)
    _label(ctx, ax, peak, hr[peak], f"{hr[peak]:.1f} in {peak}", ctx.p.NAVY,
           offset=(0, 7))
    _legend(ctx, ax, loc="upper left")

    ax = ig.slot("security.suicide", "Suicide rate")
    dr = "social/death_rates.csv"
    _line(ctx, ax, _d(ctx, dr, "suicide_rate"), ctx.p.NAVY,
          label="CDC, crude rate", lw=2.6)
    _thin(ctx, ax, _d(ctx, intl, "suicide_per_100k"), ctx.p.GOLD,
          label="WHO, age-standardised")
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left")
    _note(ctx, ax, "More Americans die by suicide than by homicide,\n"
                   "and most of them with a firearm.", y=0.05, x=0.985,
          ha="right")

    ax = ig.slot("security.road_deaths", "Road traffic deaths")
    road = _rate(ctx.per_100k, _d(ctx, "social/road_deaths.csv",
                                  "road_deaths"), pop)
    _line(ctx, ax, road, ctx.p.NAVY, label="NHTSA FARS, within 30 days",
          lw=2.6)
    _thin(ctx, ax, _d(ctx, intl, "road_deaths_per_100k"), ctx.p.GOLD,
          label="WHO, modelled")
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper right")
    lo = min(road, key=road.get)
    _label(ctx, ax, lo, road[lo], f"{road[lo]:.1f} in {lo}", ctx.p.NAVY,
           offset=(0, -6), va="top")

    ax = ig.slot("security.lens", "Overdoses and firearms")
    fa, fah = _d(ctx, v, "firearm_deaths"), _d(ctx, v, "firearm_homicides")
    od = _rate(ctx.per_100k, _d(ctx, v, "overdoses"), pop)
    syn = _rate(ctx.per_100k, _d(ctx, v, "synthetic_opioid_overdoses"), pop)
    fdr = _rate(ctx.per_100k, fa, pop)
    _line(ctx, ax, od, ctx.p.RED, label="drug overdose deaths", lw=2.6)
    _thin(ctx, ax, syn, ctx.p.RED, label=_subset(
        "synthetic opioids, mainly fentanyl", "overdoses"))
    _line(ctx, ax, fdr, ctx.p.NAVY, label="firearm deaths, all intents",
          lw=2.4)
    _frame(ig, ax)
    ax.set_ylim(0, max(od.values()) * 1.40)
    ax.set_ylabel("per 100,000", fontsize=8.6, color=ctx.p.muted)
    _legend(ctx, ax, loc="upper left")
    peak = max(od, key=od.get)
    _label(ctx, ax, peak, od[peak], f"{od[peak]:.1f} in {peak}", ctx.p.RED,
           offset=(0, 6))
    last = max(y for y in fa if y in fah)
    share = (fa[last] - fah[last]) / fa[last] * 100
    _note(ctx, ax, f"{last}: {share:.0f}% of firearm deaths were not homicides,\n"
                   f"most of them suicides.", y=0.05, x=0.985, ha="right")


# ============================================================= migration
def plate_migration(ctx, ig):
    ax = ig.slot("migration.flows",
                 "Gross PEP immigration and emigration — unpublished")
    ctx.pending(ax)
    _frame(ig, ax, slot1=True)
    _note(ctx, ax,
          "Census publishes the adjusted net component, but not its\n"
          "gross components separately. DHS events are not substitutes.",
          x=0.5, y=0.34, ha="center")
    ax = ig.slot("migration.net",
                 "Net international migration — Census PEP")
    rate = _d(ctx, "social/components.csv", "net_migration_rate")
    _line(ctx, ax, rate, ctx.p.NAVY, label="Census PEP, per 1,000", lw=2.6)
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left")
    stock = "migration/stock_acs.csv"
    total = _d(ctx, stock, "total_population")
    foreign = _d(ctx, stock, "foreign_born")
    noncitizen = _d(ctx, stock, "noncitizen")
    ax = ig.slot("migration.foreign_born", "Foreign-born and noncitizen share")
    _line(ctx, ax, _ratio(foreign, total), ctx.p.NAVY, label="foreign-born", lw=2.6)
    _thin(ctx, ax, _ratio(noncitizen, total), ctx.p.RED, label="noncitizen")
    _frame(ig, ax)
    _legend(ctx, ax, loc="upper left")
    _note(ctx, ax,
          "ACS B05002; birthplace and citizenship are different cuts.",
          y=0.05)
    ax = ig.slot("migration.lens",
                 "Lens: citizenship within the foreign-born stock")
    naturalized = _d(ctx, stock, "naturalized")
    _line(ctx, ax, _ratio(naturalized, foreign), ctx.p.NAVY,
          label="naturalized US citizens", lw=2.6)
    _line(ctx, ax, _ratio(noncitizen, foreign), ctx.p.RED,
          label="not US citizens", lw=2.2)
    _frame(ig, ax)
    ax.set_ylabel("% of foreign-born", fontsize=8.6, color=ctx.p.muted)
    ax.set_ylim(0, 100)
    _legend(ctx, ax, loc="upper left")


# ------------------------------------------------------------- the plates
def _src(*parts: str) -> str:
    return "Sources: " + " · ".join(parts)


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The American economy",
         subtitle="Growth, income per person, prices and jobs",
         source=_src("BEA, NIPA tables 1.1.1 and 7.1",
                     "World Bank, NY.GDP.PCAP.CD",
                     "BLS, CPI-U and the Current Population Survey"),
         alt=("Four panels. Real GDP growth by year, with the 2020 fall and "
              "the 2021 rebound labelled; GDP per person in current dollars "
              "on a log scale; consumer-price inflation, headline and core, "
              "against the Fed's 2% goal, peaking in 2022; and the U-3 "
              "unemployment rate inside the broader U-6, with the October "
              "2025 month that was never collected marked.")),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="What government takes in, spends and owes",
         subtitle="General government by calendar year, with the federal budget beside it",
         source=_src("IMF, World Economic Outlook and Fiscal Monitor",
                     "OECD national accounts, table 12",
                     "OMB Historical Tables and Treasury Fiscal Data, "
                     "federal fiscal years"),
         alt=("Four panels, all as a share of GDP. General-government revenue "
              "and expenditure with federal receipts and outlays beside "
              "them; the overall balance as bars with the primary balance "
              "and the federal deficit as lines; gross general-government "
              "debt against federal gross debt and debt held by the public; "
              "and interest paid by general government against federal net "
              "interest, which passed defense spending in fiscal 2024.")),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Where the money goes",
         subtitle="General-government spending by function, and what is invested",
         source=_src("OECD, National Accounts at a Glance (COFOG and "
                     "government investment)",
                     "World Bank, NE.GDI.FTOT.ZS"),
         alt=("Four panels, all as a share of GDP. General-government "
              "spending stacked by function, with health the largest; "
              "social protection against everything else; whole-economy "
              "investment; and public investment.")),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="What America buys and sells",
         subtitle="Trade as a share of GDP, who buys American goods and who sells to America",
         source=_src("BEA, NIPA tables 1.1.5 and 4.1",
                     "Census Bureau, trade in goods by country"),
         alt=("Four panels. Exports and imports of goods and services as a "
              "share of GDP; the trade balance as bars with the goods "
              "deficit and services surplus as lines; the share of US goods "
              "exports going to Canada, Mexico, the EU, China and Japan; and "
              "the share of goods imports from each, with China's falling "
              "after the 2018 tariffs.")),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Money and markets",
         subtitle="The policy rate, the long rate, the dollar and the stock market",
         source=_src("Federal Reserve Board H.10 and FOMC target (NY Fed)",
                     "US Treasury par yield curve", "BLS CPI-U",
                     "S&P 500 via Yahoo Finance, a redistributor"),
         alt=("Four panels. The federal funds target against CPI inflation, "
              "shaded where the rate sat below inflation; the 10-year "
              "Treasury yield with the 2-year beside it; the broad dollar "
              "index rebased to 2006 = 100; and the S&P 500 rebased to "
              "2006 = 100, both on log scales.")),
    dict(id="06", slug="people", topic="people", builder=plate_people,
         title="Households",
         subtitle="Inequality, poverty on three measures, the wage floor and the children",
         source=_src("Census Bureau, CPS ASEC (tables H-4 and P60)",
                     "World Bank, Poverty and Inequality Platform",
                     "Department of Labor", "BLS CPI-U"),
         alt=("Four panels. The Census Gini index in three segments split at "
              "its 2013 and 2017 method breaks, with the World Bank Gini "
              "beside it; the official and supplemental poverty rates and "
              "the World Bank's US$8.30-a-day line; the federal minimum wage "
              "as a month of full-time work in current dollars; and child "
              "poverty on the official and supplemental "
              "measures, where the 2021 Child Tax Credit shows on one and "
              "not the other.")),
    dict(id="07", slug="world", topic="world", builder=plate_world,
         title="The United States in the world",
         subtitle="The size of the economy, human development, corruption and reserves",
         source=_src("World Bank, World Development Indicators",
                     "UNDP, Human Development Report 2025",
                     "Transparency International"),
         alt=("Four panels. GDP in current US dollars on a log scale; the "
              "Human Development Index, which dipped in 2020-2021; the "
              "Corruption Perceptions Index, falling since 2015; and "
              "official reserves including gold, on a log scale.")),
    dict(id="08", slug="demographics", topic="demography",
         builder=plate_demographics,
         title="How many Americans",
         subtitle="Population, fertility, births and deaths, and what changes the total",
         source=_src("Census Bureau, intercensal and Vintage 2019 and 2025 "
                     "estimates, 2023 projections",
                     "World Bank, World Development Indicators (NCHS)"),
         alt=("Four panels. The resident population as an index with 2006 = "
              "100; the total fertility rate against the replacement level "
              "of 2.1; crude birth and death rates per 1,000; and natural "
              "increase and net international migration per 1,000, which "
              "surged in 2022-2024.")),
    dict(id="09", slug="mortality", topic="mortality", builder=plate_mortality,
         title="Deaths",
         subtitle="How many die, how many more than usual, COVID-19, and how long people live",
         source=_src("CDC WONDER and NCHS provisional mortality",
                     "World Bank, World Development Indicators (NCHS)",
                     "Census Bureau population"),
         alt=("Four panels. The crude death rate per 1,000, peaking in 2021; "
              "deaths against the 2015-2019 average; COVID-19 deaths per "
              "100,000 as the underlying cause, with deaths that involved "
              "it as a line; and life expectancy at birth, which fell to its "
              "low in 2021.")),
    dict(id="10", slug="violence", topic="security", builder=plate_violence,
         title="Violent and accidental death",
         subtitle="Homicide, suicide, the roads, overdoses and firearms, per 100,000 people",
         source=_src("CDC WONDER and NCHS provisional injury and overdose "
                     "counts", "NHTSA FARS", "UNODC and WHO via the World "
                     "Bank", "Census Bureau population"),
         alt=("Four panels, all per 100,000 people. The homicide rate on a "
              "log scale, from death certificates and from police records; "
              "the suicide rate; road traffic deaths; and drug overdose "
              "deaths with the synthetic opioids among them, beside all "
              "firearm deaths.")),
    dict(id="11", slug="credit", topic="credit", builder=plate_credit,
         title="What households owe",
         subtitle="Household debt, what it costs, who falls behind, and what it is made of",
         source=_src("BIS total credit statistics",
                     "Federal Reserve Bank of New York, Household Debt and "
                     "Credit", "Freddie Mac PMMS", "Federal Reserve G.19"),
         alt=("Four panels. Household debt as a share of GDP, peaking in "
              "2007; the 30-year mortgage rate and the credit card rate "
              "against the policy rate; the share of balances 90 days or "
              "more delinquent, by type; and household debt by type in US "
              "dollars.")),
    dict(id="12", slug="migration", topic="migration", builder=plate_migration,
         title="Migration, without mixing unlike measures",
         subtitle="Census net migration and ACS birthplace and citizenship stocks",
         source=_src("Census Bureau, Population Estimates Program",
                     "Census Bureau, ACS 1-year table B05002"),
         alt=("Gross Census PEP immigration and emigration are visibly pending because Census does not publish the components separately. The PEP net migration rate is shown per 1,000. ACS B05002 shows foreign-born and noncitizen shares, and the lens divides the foreign-born stock into naturalized citizens and noncitizens.")),
)
