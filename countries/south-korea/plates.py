"""The south-korea plates, drawn on the plate spine.

Every plate declares its topic and claims its four panels by slot key, in
spine order (PLATE_SPINE.md, core/spine.py): the same indicator in the
same unit on the same scale as every other country's plate for that
topic, so the comparison viewer can wipe Korea over France panel for
panel. The last slot of a topic that has one is Korea's own lens.

Every number in a note is read from the committed CSVs when the plate is
drawn, never typed in, so a refetch that moves a figure moves its note
with it. Where Korea publishes a rate the published rate is drawn; where
a count has to become a rate, the population is the same year and the
same scope as the count, and DATA_NOTES.md §9 names it.
"""
from __future__ import annotations

import csv

import matplotlib.ticker as mticker
import numpy as np

# The Minimum Wage Commission's monthly conversion: a 40-hour week plus
# the paid weekly rest day, 48 hours × 365/7/12 ≈ 209. The government
# quotes the monthly minimum wage at exactly this many hours.
MONTHLY_HOURS = 209
# The excess-deaths baseline the spine fixes for every country.
BASELINE = range(2015, 2020)


# ---------------------------------------------------------------- reading
def _read(ctx, rel: str) -> list[dict[str, str]]:
    """Rows of a long-format CSV (one row per year and category)."""
    path = ctx.c.data(rel)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(ln for ln in f
                                   if not ln.lstrip().startswith("#")))


def _series(ctx, rel: str, column: str, first: int | None = None,
            last: int | None = None) -> dict[int, float]:
    """{year: value} for one column, blanks dropped.

    A blank is a year the publisher has not covered and it stays a gap:
    nothing here interpolates across it or fills it with zero.
    """
    table = ctx.table(rel)
    if not table or column not in table:
        return {}
    out = {}
    for y, v in zip(*ctx.series(table, column)):
        if isinstance(v, str):
            continue
        if (first is None or y >= first) and (last is None or y <= last):
            out[int(y)] = float(v)
    return out


def _xy(data: dict[int, float], years=None) -> tuple[list[int], list[float]]:
    years = sorted(data) if years is None else [y for y in years if y in data]
    return years, [data[y] for y in years]


def _last(data: dict[int, float]) -> tuple[int, float] | tuple[None, None]:
    if not data:
        return None, None
    year = max(data)
    return year, data[year]


def _peak(data: dict[int, float]) -> tuple[int, float]:
    year = max(data, key=lambda y: data[y])
    return year, data[year]


def _low(data: dict[int, float]) -> tuple[int, float]:
    year = min(data, key=lambda y: data[y])
    return year, data[year]


# ------------------------------------------------------------ conversions
def kostat_population(ctx) -> dict[int, float]:
    """The population the Causes of Death release divides by, recovered.

    Statistics Korea's cause-of-death rates are deaths of Korean nationals
    over 주민등록 연앙인구, the mid-year registered population of Korean
    nationals (index.go.kr 1012, 수치해석 방법). The release does not print
    that denominator, but it prints the all-cause rate to four significant
    figures beside the total it was computed from, so the denominator is
    total deaths ÷ (all-cause rate / 100,000), same year, same scope. A
    count from the same release — homicide — goes over this, not over the
    projection population in macro/gdp.csv, which includes foreign
    residents the count does not.
    """
    deaths = _series(ctx, "social/vital.csv", "deaths")
    rate = _series(ctx, "social/mortality.csv", "all_causes")
    return {y: deaths[y] / rate[y] * 100_000 for y in deaths if y in rate}


def homicide_rate(ctx) -> tuple[list[int], list[float]]:
    """Deaths from assault per 100,000, on the release's own denominator."""
    return ctx.per_100k(_series(ctx, "social/homicide.csv", "deaths"),
                        kostat_population(ctx))


def minimum_wage_usd(ctx) -> dict[int, float]:
    """The hourly minimum wage as US$ a month.

    ₩ per hour × 209 hours (the government's own monthly conversion),
    over the year's average won-dollar rate. The running year's rate is
    an average of the months published so far, which is why ctx.line
    draws that year dashed.
    """
    hourly = _series(ctx, "macro/minimum_wage.csv", "value")
    fx = _series(ctx, "macro/won.csv", "avg")
    return {y: hourly[y] * MONTHLY_HOURS / fx[y] for y in hourly if y in fx}


def excess_deaths(ctx) -> dict[int, float]:
    """Deaths each year as % above the 2015–2019 average count.

    The spine's definition for every country: crude, no age adjustment,
    so a country ageing as fast as Korea drifts upward even without an
    epidemic, and the years before 2015 sit below zero.
    """
    deaths = _series(ctx, "social/vital.csv", "deaths")
    base = sum(deaths[y] for y in BASELINE) / len(BASELINE)
    return {y: (v / base - 1) * 100 for y, v in deaths.items()}


def net_migration_rate(ctx) -> tuple[list[int], list[float]]:
    """Net international migration per 1,000 residents.

    The count covers Korean nationals and foreigners alike, so the
    denominator is the population that includes both: Statistics Korea's
    mid-year population (social/population.csv), not the registered
    Korean-national one the vital rates use.
    """
    net = _series(ctx, "social/migration.csv", "net")
    pop = {y: v * 1e6 for y, v in
           _series(ctx, "social/population.csv", "pop_mn").items()}
    return ctx.per_1000(net, pop)


def migration_flow_rates(ctx) -> tuple[tuple[list[int], list[float]],
                                       tuple[list[int], list[float]]]:
    """Gross >90-day immigration and emigration per 1,000 residents."""
    flows = "social/migration.csv"
    pop = {y: v * 1e6 for y, v in
           _series(ctx, "social/population.csv", "pop_mn").items()}
    return (ctx.per_1000(_series(ctx, flows, "arrivals"), pop),
            ctx.per_1000(_series(ctx, flows, "departures"), pop))


def migration_citizenship_net_rates(ctx) -> tuple[dict[int, float],
                                                    dict[int, float]]:
    """Each citizenship group's contribution to total net migration.

    Both are counts on the same >90-day definition as the canonical total;
    dividing by the total resident population makes the two lines additive.
    """
    rel = "migration/flows_by_citizenship.csv"
    pop = {y: v * 1e6 for y, v in
           _series(ctx, "social/population.csv", "pop_mn").items()}
    out = []
    for column in ("korean_net", "foreign_net"):
        years, values = ctx.per_1000(_series(ctx, rel, column), pop)
        out.append(dict(zip(years, values)))
    return out[0], out[1]


# ---------------------------------------------------------------- drawing
def _note(ctx, ax, x, y, text, color=None, ha="left", va="center",
          axes=False, size=8.2, weight="normal", style="normal"):
    """A short note. `axes=True` places it in panel fractions."""
    kw = dict(transform=ax.transAxes) if axes else {}
    return ax.text(x, y, text, ha=ha, va=va, fontsize=size,
                   color=color or ctx.p.MUTED, fontweight=weight,
                   style=style, zorder=7, **kw)


def _legend(ax, loc="upper left", ncol=1, size=8.4, **kw):
    ax.legend(loc=loc, ncol=ncol, fontsize=size, handlelength=1.8,
              columnspacing=1.2, labelspacing=0.35, borderaxespad=0.4, **kw)


def _tick(v, _pos=None) -> str:
    """A plain tick: whole numbers bare, a 2.5 step with its decimal."""
    return f"{v:,.0f}" if abs(v - round(v)) < 1e-9 else f"{v:,.1f}"


def _pct(ax, decimals=0):
    """Plain numbers on the y-axis; the unit is in the axis label."""
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_tick))


def _signed(ctx, positive=None, negative=None):
    positive = positive or ctx.p.BLUE
    negative = negative or ctx.p.RED
    return lambda v: positive if v >= 0 else negative


def _finish(ig, ax, slot_one=False, band_y=0.035):
    """Year ticks and the recession bands, named on slot 1 only.

    The names sit inside the panel at `band_y` (a fraction of its
    height): above the axes they collide with the panel title, and each
    plate picks the strip its own data leave free.
    """
    ig.style_axis(ax)
    ig.add_recessions(ax, label=False)
    if slot_one:
        for start, end, name in ig.country.recessions:
            ax.text((start + end) / 2, band_y, name,
                    transform=ax.get_xaxis_transform(), ha="center",
                    va="bottom", fontsize=7.6, color=ig.p.muted,
                    style="italic", zorder=6)


# ---------------------------------------------------------------- economy
def plate_economy(ctx, ig):
    p = ctx.p
    growth = _series(ctx, "macro/gdp.csv", "real_growth")
    percap = _series(ctx, "intl/world.csv", "gdp_per_person_usd")
    cpi = _series(ctx, "macro/cpi.csv", "value")
    unemp = _series(ctx, "macro/unemployment.csv", "value")

    ax = ig.slot("economy.growth", "Real GDP growth")
    ctx.bars(ax, *_xy(growth), _signed(ctx))
    _finish(ig, ax, slot_one=True)
    y, v = _low(growth)
    _note(ctx, ax, y + 0.6, -3.2, f"{y}: {v:.1f}%, the only contraction",
          color=p.RED)
    y, v = _last(growth)
    slower = sorted(k for k, g in growth.items() if g < v)
    text = (f"{y}: {v:.1f}%, slower only in {slower[0]} and {slower[1]}"
            if len(slower) == 2 else f"{y}: {v:.1f}%")
    _note(ctx, ax, 0.98, 0.16, text, ha="right", axes=True)

    ax = ig.slot("economy.gdp_per_person", "GDP per person")
    ctx.line(ax, *_xy(percap), p.BLUE, label="World Bank, current US$")
    _finish(ig, ax)
    y, v = _last(percap)
    _note(ctx, ax, 0.98, 0.30, f"{y}: US${v:,.0f}", ha="right", axes=True,
          color=p.BLUE_D, weight="bold", size=9)
    _note(ctx, ax, 0.98, 0.20, "the dips in 2009 and 2022 are the won, "
          "not output", ha="right", axes=True)

    ax = ig.slot("economy.inflation", "Consumer price inflation")
    ax.plot([2015.5, 2026.6], [2.0, 2.0], color=p.TEAL, lw=1.3,
            ls=(0, (5, 3)), zorder=2)
    ctx.line(ax, *_xy(cpi), p.RED, label="CPI, % change on a year earlier")
    _finish(ig, ax)
    _note(ctx, ax, 0.02, 0.92, "2% target (since 2016)", color=p.TEAL,
          axes=True, va="top")
    y, v = _peak(cpi)
    _note(ctx, ax, 0.02, 0.82, f"{y}: {v:.1f}%", color=p.RED,
          axes=True, va="top", weight="bold")
    y, v = _low(cpi)
    _note(ctx, ax, 0.02, 0.72, f"{y}: {v:.1f}%, the floor so far",
          axes=True, va="top")

    ax = ig.slot("economy.unemployment", "Unemployment rate")
    ctx.line(ax, *_xy(unemp), p.PURPLE, label="Labour force survey, 15+")
    _finish(ig, ax)
    lo, hi = min(unemp.values()), max(unemp.values())
    _note(ctx, ax, 0.02, 0.62, f"never outside {lo:.1f}–{hi:.1f}% in "
          f"{min(unemp)}–{max(unemp)}", axes=True)
    _legend(ax, loc="upper left")
    for a in (ig.axes_flat[0], ig.axes_flat[2], ig.axes_flat[3]):
        _pct(a, 0)


# ----------------------------------------------------------------- fiscal
def plate_fiscal(ctx, ig):
    p = ctx.p
    imf = {c: _series(ctx, "fiscal/general_government_imf.csv", c)
           for c in ("revenue_pct_gdp", "expenditure_pct_gdp",
                     "balance_pct_gdp", "primary_balance_pct_gdp",
                     "gross_debt_pct_gdp")}
    first_imf = min(imf["revenue_pct_gdp"])
    nat = {c: _series(ctx, "fiscal/government.csv", c, last=first_imf - 1)
           for c in ("revenue", "expenditure", "balance")}
    interest = _series(ctx, "fiscal/government.csv", "interest_paid")
    d1 = _series(ctx, "fiscal/debt.csv", "d1")
    tax = _series(ctx, "fiscal/tax_burden.csv", "value")

    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure")
    ctx.line(ax, *_xy(imf["revenue_pct_gdp"]), p.BLUE, label="Revenue, IMF")
    ctx.line(ax, *_xy(imf["expenditure_pct_gdp"]), p.RED,
             label="Expenditure, IMF")
    ctx.line(ax, *_xy(nat["revenue"]), p.BLUE, lw=1.4, ms=3,
             ls=(0, (2, 1.5)), label="Revenue, BOK national accounts")
    ctx.line(ax, *_xy(nat["expenditure"]), p.RED, lw=1.4, ms=3,
             ls=(0, (2, 1.5)), label="Expenditure, BOK national accounts")
    _finish(ig, ax, slot_one=True)
    _legend(ax, loc="upper left", ncol=2, size=8.0)
    _note(ctx, ax, 0.02, 0.24, f"general government; the IMF series starts "
          f"in {first_imf}, the Bank of Korea's own covers the years before",
          axes=True, size=7.8)
    y, v = _peak(tax)
    _note(ctx, ax, 0.02, 0.16, f"tax revenue alone: {v:.1f}% of GDP at its "
          f"{y} peak", axes=True, size=7.8)

    ax = ig.slot("fiscal.balance", "Overall and primary balance")
    ctx.bars(ax, *_xy(imf["balance_pct_gdp"]), _signed(ctx))
    ctx.bars(ax, *_xy(nat["balance"]),
             _signed(ctx, "#8FB0D9", "#E79AA0"))
    ctx.line(ax, *_xy(imf["primary_balance_pct_gdp"]), p.NAVY, lw=1.6,
             ms=3, label="Primary balance, IMF")
    _finish(ig, ax)
    _legend(ax, loc="upper right")
    y, v = _low(imf["balance_pct_gdp"])
    _note(ctx, ax, y, v - 1.2, f"{y}: {v:.1f}%", color=p.RED, ha="center",
          va="top", weight="bold")
    _note(ctx, ax, 0.02, 0.08, f"bars: overall balance, IMF; paler bars "
          f"before {first_imf}: Bank of Korea", axes=True, size=7.8)

    ax = ig.slot("fiscal.debt", "Gross debt")
    ctx.line(ax, *_xy(imf["gross_debt_pct_gdp"]), p.BLUE,
             label="General government (IMF = Korea's D2)")
    ctx.line(ax, *_xy(d1), p.BLUE_D, lw=1.6, ms=3, ls=(0, (2, 1.5)),
             label="D1, central and local government (MOEF)")
    _finish(ig, ax)
    _legend(ax, loc="upper left")
    y, v = _last(imf["gross_debt_pct_gdp"])
    _note(ctx, ax, 0.98, 0.82, f"{y}: {v:.1f}%", color=p.BLUE_D,
          ha="right", axes=True, weight="bold")

    ax = ig.slot("fiscal.interest", "Interest paid")
    ctx.line(ax, *_xy(interest), p.PURPLE,
             label="General government, gross (BOK national accounts)")
    _finish(ig, ax)
    _legend(ax, loc="upper left")
    net = {y: imf["primary_balance_pct_gdp"][y] - imf["balance_pct_gdp"][y]
           for y in imf["balance_pct_gdp"]
           if y in imf["primary_balance_pct_gdp"]}
    y, v = _last(net)
    _note(ctx, ax, 0.02, 0.70, f"net of interest received (IMF): {v:.1f}% "
          f"in {y}; the pension fund earns most of it back", axes=True,
          size=7.8)
    for a in ig.axes_flat:
        _pct(a, 0)


# --------------------------------------------------------------- spending
def _functions(ctx):
    p = ctx.p
    return [
        (("social_protection",), "Social protection", p.BLUE),
        (("health",), "Health", p.TEAL),
        (("education",), "Education", p.YELLOW),
        (("general_public",), "General public services", p.MUTED),
        (("economic_affairs",), "Economic affairs", p.PURPLE),
        (("defence", "public_order"), "Defence and public order", p.NAVY),
        (("other",), "Other", p.FAINT),
    ]


def plate_spending(ctx, ig):
    p = ctx.p
    rel = "fiscal/spending_by_function.csv"
    cols = {c: _series(ctx, rel, c) for c in
            ("social_protection", "health", "education", "general_public",
             "economic_affairs", "defence", "public_order", "other", "total")}
    years = sorted(set.intersection(*[set(v) for v in cols.values()]))
    gfcf = _series(ctx, "fiscal/investment.csv", "gfcf_pct_gdp")
    gov = _series(ctx, "fiscal/government.csv", "gov_gfcf")
    rnd = _series(ctx, "fiscal/rnd.csv", "value")

    ax = ig.slot("spending.by_function", "Spending by function, stacked")
    base = np.zeros(len(years))
    for keys, label, color in _functions(ctx):
        vals = np.array([sum(cols[k][y] for k in keys) for y in years])
        ax.fill_between(years, base, base + vals, color=color, alpha=0.88,
                        lw=0, zorder=2, label=label)
        base = base + vals
    _finish(ig, ax, slot_one=True, band_y=0.93)
    _legend(ax, loc="upper left", ncol=3, size=7.8,
            bbox_to_anchor=(0.0, 0.91))
    _note(ctx, ax, years[-1], base[-1] + 1.4, f"{years[-1]}: "
          f"{base[-1]:.1f}%", ha="right", va="bottom", color=p.INK,
          weight="bold")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else")
    social = cols["social_protection"]
    rest = {y: cols["total"][y] - social[y] for y in years}
    ctx.line(ax, *_xy(social), p.BLUE, label="Social protection")
    ctx.line(ax, *_xy(rest), p.MUTED, ls=(0, (6, 3)),
             label="All other functions")
    _finish(ig, ax)
    _legend(ax, loc="upper left")
    a, b = social[years[0]], social[years[-1]]
    _note(ctx, ax, 0.98, 0.06, f"social protection {years[0]}–{years[-1]}: "
          f"{a:.1f}% to {b:.1f}% of GDP", ha="right", axes=True)

    ax = ig.slot("spending.investment", "Investment rate, whole economy")
    ctx.line(ax, *_xy(gfcf), p.PURPLE,
             label="Gross fixed capital formation (BOK)")
    _finish(ig, ax)
    _legend(ax, loc="upper left")
    y, v = _last(rnd)
    _note(ctx, ax, 0.02, 0.10, f"of which R&D, all sectors: {v:.2f}% of "
          f"GDP in {y}, second only to Israel", axes=True)

    ax = ig.slot("spending.public_investment", "Public investment")
    ctx.line(ax, *_xy(gov), p.TEAL,
             label="General government GFCF (BOK national accounts)")
    _finish(ig, ax)
    _legend(ax, loc="upper left")
    y, v = _peak(gov)
    _note(ctx, ax, y + 0.4, v + 0.25, f"{y}: {v:.1f}%, the stimulus year",
          va="bottom", color=p.TEAL)
    for a in ig.axes_flat:
        _pct(a, 0)


# ------------------------------------------------------------------ trade
def _export_products(ctx):
    p = ctx.p
    return [
        ("semiconductors", "Semiconductors", p.BLUE),
        ("cars", "Cars", p.RED),
        ("petroleum", "Petroleum products", p.YELLOW),
        ("petrochemicals", "Petrochemicals", p.PURPLE),
        ("ships", "Ships", p.TEAL),
        ("steel", "Steel", p.NAVY),
        ("car_parts", "Car parts", p.MUTED),
        ("telecom", "Phones & telecom gear", p.FAINT),
    ]


def _partners(ctx):
    p = ctx.p
    return [("China", p.RED), ("United States", p.BLUE),
            ("Vietnam", p.TEAL), ("Japan", p.PURPLE)]


def plate_trade(ctx, ig):
    p = ctx.p
    exp = _series(ctx, "trade/trade_gdp.csv", "exports_pct_gdp")
    imp = _series(ctx, "trade/trade_gdp.csv", "imports_pct_gdp")
    bal = {y: exp[y] - imp[y] for y in exp if y in imp}
    goods = _series(ctx, "trade/trade.csv", "balance",
                    last=ctx.LAST_FULL_YEAR)

    ax = ig.slot("trade.exports_imports", "Exports and imports")
    ctx.line(ax, *_xy(exp), p.BLUE, label="Exports")
    ctx.line(ax, *_xy(imp), p.RED, label="Imports")
    _finish(ig, ax, slot_one=True)
    _legend(ax, loc="upper left")
    _note(ctx, ax, 0.98, 0.16, "goods and services, national accounts "
          "(World Bank)", ha="right", axes=True)

    ax = ig.slot("trade.balance", "Trade balance")
    ctx.bars(ax, *_xy(bal), _signed(ctx))
    _finish(ig, ax)
    y, v = _last(goods)
    _note(ctx, ax, 0.02, 0.92, f"customs goods balance, {y}: US${v:.1f}bn",
          axes=True)
    y = min((y for y in bal if y >= 2020), key=lambda y: bal[y])
    _note(ctx, ax, y, -3.0, f"{y}: {bal[y]:.1f}%, the energy bill",
          ha="center", va="top", color=p.RED)

    ax = ig.slot("trade.destinations", "Top export destinations")
    shares: dict[str, dict[int, float]] = {}
    for row in _read(ctx, "trade/destinations.csv"):
        value = (row.get("share_pct") or "").strip()
        if value:
            shares.setdefault(row["destiny"], {})[int(row["year"])] = \
                float(value)
    for name, color in _partners(ctx):
        ctx.line(ax, *_xy(shares[name]), color, lw=2.0, ms=3.4, label=name)
    _finish(ig, ax)
    ig.add_event(ax, 2017.2, "THAAD: China retaliates", dy=0.97)
    _legend(ax, loc="upper left", ncol=4, size=7.8,
            bbox_to_anchor=(0.0, 0.88))
    china = shares["China"]
    y, v = _peak(china)
    y2, v2 = _last(china)
    _note(ctx, ax, 0.98, 0.70, f"China: {v:.1f}% at the {y} peak, "
          f"{v2:.1f}% in {y2}", ha="right", axes=True, color=p.RED)

    ax = ig.slot("trade.lens", "Lens: what Korea exports, US$ bn")
    rows = _read(ctx, "trade/exports_products.csv")
    snaps = sorted({int(r["year"]) for r in rows})
    values = {(int(r["year"]), r["product"]): float(r["usbi"]) for r in rows}
    items = _export_products(ctx)
    width = 0.8 / len(items)
    xs = np.arange(len(snaps))
    for i, (key, label, color) in enumerate(items):
        ax.bar(xs + i * width - 0.4 + width / 2,
               [values.get((y, key), 0.0) for y in snaps], width * 0.92,
               color=color, zorder=3, label=label)
    ig.style_axis(ax, xticks_years=False)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(y) for y in snaps])
    ax.set_xlim(-0.6, len(snaps) - 0.4)
    peak = max(values.values())
    ax.set_ylim(0, peak * 1.55)
    ax.set_ylabel("US$ bn", fontsize=8.6, color=p.MUTED)
    _legend(ax, loc="upper left", ncol=2, size=7.6)
    semi = values[(snaps[-1], "semiconductors")]
    _note(ctx, ax, 0.98, 0.93, f"semiconductors, {snaps[-1]}: "
          f"US${semi:.0f}bn", ha="right", axes=True, color=p.BLUE_D,
          weight="bold")
    _note(ctx, ax, 0.98, 0.85, "snapshot years; HS headings, "
          "UN Comtrade", ha="right", axes=True, size=7.6)
    for a in ig.axes_flat[:3]:
        _pct(a, 0)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))


# ---------------------------------------------------------------- markets
def plate_markets(ctx, ig):
    p = ctx.p
    base = _series(ctx, "macro/base_rate.csv", "value")
    cpi = _series(ctx, "macro/cpi.csv", "value")
    ktb = _series(ctx, "markets/bond_10y.csv", "ktb_10y")
    avg = _series(ctx, "macro/won.csv", "avg")
    eop = _series(ctx, "macro/won.csv", "eop")
    kospi = _series(ctx, "markets/kospi.csv", "close")
    sp500 = _series(ctx, "markets/sp500.csv", "close", first=2006)

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation")
    ctx.line(ax, *_xy(base), p.BLUE, label="BOK base rate, year-end")
    ctx.line(ax, *_xy(cpi), p.RED, lw=1.8, ms=3, ls=(0, (4, 2)),
             label="CPI inflation")
    _finish(ig, ax, slot_one=True, band_y=0.93)
    _legend(ax, loc="center right")
    y, v = _low(base)
    _note(ctx, ax, 0.02, 0.80, f"{y}: {v:.2f}%", axes=True, va="top",
          color=p.BLUE_D, weight="bold")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield")
    ctx.line(ax, *_xy(ktb), p.NAVY, label="Korea Treasury Bond, 10 years")
    _finish(ig, ax)
    _legend(ax, loc="upper right")
    y, v = _low(ktb)
    _note(ctx, ax, y, v - 0.9, f"{y}: {v:.2f}%, the low", ha="center",
          va="top", color=p.NAVY)

    ax = ig.slot("markets.currency", "Currency against the US$")
    idx = dict(zip(*ctx.fx_index(avg)))
    ctx.line(ax, *_xy(idx), p.BLUE, label="Won, annual average")
    _finish(ig, ax)
    ig.add_event(ax, 2024.92, "martial law", dy=0.97)
    _legend(ax, loc="lower left")
    y = ctx.LAST_FULL_YEAR
    _note(ctx, ax, 0.98, 0.20, f"{y}: ₩{avg[y]:,.0f} per US$, against "
          f"₩{avg[min(avg)]:,.0f} in {min(avg)}", ha="right", axes=True)

    ax = ig.slot("markets.equities", "Main equity index in US$")
    kospi_usd = {y: kospi[y] / eop[y] for y in kospi if y in eop}
    ctx.line(ax, *ctx.index_2006(kospi_usd), p.BLUE, label="KOSPI in US$")
    ctx.line(ax, *ctx.index_2006(sp500), p.MUTED, lw=1.8, ms=3,
             ls=(0, (5, 3)), label="S&P 500")
    _finish(ig, ax)
    _legend(ax, loc="upper left")
    y = ctx.LAST_FULL_YEAR
    _note(ctx, ax, 0.98, 0.08, f"year-end close in won, {y}: "
          f"{kospi[y]:,.0f}", ha="right", axes=True)
    for a in ig.axes_flat[:2]:
        _pct(a, 0)


# ----------------------------------------------------------------- credit
def plate_credit(ctx, ig):
    p = ctx.p
    bis = _series(ctx, "macro/household_bis.csv", "credit_pct_gdp_q4")
    dsr = _series(ctx, "macro/household_bis.csv", "dsr_pct_q4")
    nat = _series(ctx, "macro/household_credit.csv", "credit_pct_gdp")
    stock = _series(ctx, "macro/household_credit.csv", "credit_krw_tn")
    rel = "macro/credit_terms.csv"
    mortgage = _series(ctx, rel, "mortgage_rate")
    unsecured = _series(ctx, rel, "unsecured_rate")
    base = _series(ctx, "macro/base_rate.csv", "value")
    hh_late = _series(ctx, rel, "household_late")
    co_late = _series(ctx, rel, "corporate_late")

    ax = ig.slot("credit.household_debt", "Household debt")
    ctx.line(ax, *_xy(bis), p.BLUE, label="BIS: households and NPISHs, "
             "all lenders, Q4")
    ctx.line(ax, *_xy(nat), p.BLUE_D, lw=1.6, ms=3, ls=(0, (2, 1.5)),
             label="BOK household credit, year-end")
    _finish(ig, ax, slot_one=True)
    _legend(ax, loc="upper left")
    y, v = _peak(bis)
    _note(ctx, ax, y, v + 6, f"{y}: {v:.1f}%", ha="center", va="bottom",
          color=p.BLUE_D, weight="bold")
    y, v = _last(stock)
    _note(ctx, ax, 0.98, 0.16, f"₩{v:,.0f}tn owed at the end of {y}",
          ha="right", axes=True)

    ax = ig.slot("credit.lending_rate", "Household lending rate vs policy "
                 "rate")
    ctx.line(ax, *_xy(mortgage), p.RED, label="New mortgage loans")
    ctx.line(ax, *_xy(unsecured), p.YELLOW, lw=1.8, ms=3,
             label="New unsecured loans")
    ctx.line(ax, *_xy(base), p.BLUE, lw=1.6, ms=3, ls=(0, (4, 2)),
             label="BOK base rate, year-end")
    _finish(ig, ax)
    _legend(ax, loc="upper right")
    _note(ctx, ax, 0.02, 0.92, "bank lending rates on new loans, annual "
          "average", axes=True, size=7.8)

    ax = ig.slot("credit.npl", "Non-performing loans")
    ctx.line(ax, *_xy(co_late), p.PURPLE, label="Businesses")
    ctx.line(ax, *_xy(hh_late), p.RED, label="Households")
    _finish(ig, ax)
    _legend(ax, loc="upper right")
    _note(ctx, ax, 0.02, 0.92, "bank loans overdue a month or more "
          "(delinquency rate)", axes=True, size=7.8)
    y, v = _peak(hh_late)
    _note(ctx, ax, y, 3.0, f"households peaked at {v:.1f}% in {y}",
          ha="center", va="bottom", color=p.RED)

    ax = ig.slot("credit.lens", "Lens: debt service, households")
    ctx.line(ax, *_xy(dsr), p.TEAL,
             label="Interest and principal, % of disposable income (BIS)")
    _finish(ig, ax)
    ax.set_ylim(0, 18)
    ax.set_ylabel("% of disposable income", fontsize=8.6, color=p.MUTED)
    _legend(ax, loc="upper left")
    y, v = _peak(dsr)
    y2, v2 = _low(dsr)
    _note(ctx, ax, 0.98, 0.08, f"{y2}: {v2:.1f}% to {y}: {v:.1f}%",
          ha="right", axes=True, color=p.TEAL, weight="bold")
    for a in ig.axes_flat:
        _pct(a, 0)


# ----------------------------------------------------------------- people
def plate_people(ctx, ig):
    p = ctx.p
    hfws = {y: v * 100 for y, v in _series(ctx, "social/gini.csv",
                                           "hfws").items()}
    hies = {y: v * 100 for y, v in _series(ctx, "social/gini.csv",
                                           "hies").items()}
    wb = _series(ctx, "social/gini_wb.csv", "gini_wb")
    rel_pov = _series(ctx, "social/poverty.csv", "relative")
    wb_pov = _series(ctx, "social/poverty_wb.csv", "poverty_830")
    wage = minimum_wage_usd(ctx)
    hourly = _series(ctx, "macro/minimum_wage.csv", "value")
    old = _series(ctx, "social/poverty.csv", "elderly_65")
    old_mkt = _series(ctx, "social/poverty.csv", "elderly_65_market")

    ax = ig.slot("people.gini", "Income inequality, Gini")
    ctx.line(ax, *_xy(hfws), p.BLUE,
             label="Household Finance and Welfare Survey (2011–)")
    ctx.line(ax, *_xy(hies), p.YELLOW, lw=1.8, ms=3,
             label="Household Income and Expenditure Survey (–2016)")
    ctx.line(ax, *_xy(wb), p.MUTED, lw=1.2, ms=3, ls=(0, (2, 2)),
             label="World Bank")
    _finish(ig, ax, slot_one=True)
    ig.add_event(ax, 2011, "2011: new survey basis", dy=0.97)
    _legend(ax, loc="upper left", size=7.8, bbox_to_anchor=(0.0, 0.9))
    _note(ctx, ax, 0.98, 0.93, "disposable income; two surveys, never "
          "joined", ha="right", axes=True, size=7.8)

    ax = ig.slot("people.poverty", "Poverty rate")
    ctx.line(ax, *_xy(rel_pov), p.RED,
             label="Below half the median income (national)")
    ctx.line(ax, *_xy(wb_pov), p.MUTED, lw=1.6, ms=3, ls=(0, (2, 2)),
             label="Below US$8.30 a day (World Bank)")
    _finish(ig, ax)
    _legend(ax, loc="upper right")
    y, v = _last(rel_pov)
    _note(ctx, ax, y, v + 2.5, f"{y}: {v:.1f}%", ha="center", va="bottom",
          color=p.RED, weight="bold")

    ax = ig.slot("people.minimum_wage", "Minimum wage")
    ctx.line(ax, *_xy(wage), p.TEAL,
             label="209 hours a month, at the year's average ₩/US$")
    _finish(ig, ax)
    _legend(ax, loc="upper left")
    y, v = _last(hourly)
    _note(ctx, ax, 0.98, 0.83, f"{y}: ₩{v:,.0f} an hour = "
          f"₩{v * MONTHLY_HOURS:,.0f} a month", ha="right", axes=True,
          color=p.TEAL, weight="bold")
    y0 = min(hourly)
    _note(ctx, ax, 0.98, 0.75, f"{y0}: ₩{hourly[y0]:,.0f} an hour",
          ha="right", axes=True)

    ax = ig.slot("people.lens", "Lens: poverty at 65 and over")
    yrs = sorted(set(old) & set(old_mkt))
    ax.fill_between(yrs, [old[y] for y in yrs], [old_mkt[y] for y in yrs],
                    color=p.YELLOW, alpha=0.18, lw=0, zorder=1)
    ctx.line(ax, *_xy(old_mkt), p.MUTED, ls=(0, (5, 3)),
             label="Before transfers (market income)")
    ctx.line(ax, *_xy(old), p.RED, label="After transfers (disposable)")
    _finish(ig, ax)
    ax.set_ylim(0, 75)
    ax.set_ylabel("% of people aged 65+", fontsize=8.6, color=p.MUTED)
    _legend(ax, loc="upper left", ncol=2, size=7.8)
    mid = yrs[len(yrs) // 2]
    _note(ctx, ax, mid, (old[mid] + old_mkt[mid]) / 2,
          "the gap is what pensions and benefits do", ha="center")
    y, v = _last(old)
    _note(ctx, ax, y, v - 3, f"{y}: {v:.1f}%", ha="center", va="top",
          color=p.RED, weight="bold")
    for a in ig.axes_flat:
        _pct(a, 0)
    ig.axes_flat[2].yaxis.set_major_formatter(
        mticker.StrMethodFormatter("{x:,.0f}"))


# ------------------------------------------------------------------ world
def plate_world(ctx, ig):
    p = ctx.p
    gdp = _series(ctx, "intl/world.csv", "gdp_usd_bn")
    krw = _series(ctx, "macro/gdp.csv", "nominal_krw_tn")
    hdi = _series(ctx, "social/hdi.csv", "value")
    score = _series(ctx, "intl/cpi.csv", "score")
    old = {y: v * 10 for y, v in _series(ctx, "intl/cpi.csv",
                                         "score_0_10").items()}
    res = _series(ctx, "macro/reserves.csv", "eop_usbi")
    niip = _series(ctx, "macro/external.csv", "net_usbi")

    ax = ig.slot("world.gdp", "GDP at current prices")
    ctx.line(ax, *_xy(gdp), p.BLUE, label="World Bank, current US$")
    _finish(ig, ax, slot_one=True)
    _legend(ax, loc="upper left")
    y, v = _last(gdp)
    _note(ctx, ax, 0.98, 0.30, f"{y}: US${v:,.0f}bn", ha="right",
          axes=True, color=p.BLUE_D, weight="bold", size=9)
    _note(ctx, ax, 0.98, 0.21, f"₩{krw[y]:,.0f}tn in won", ha="right",
          axes=True)

    ax = ig.slot("world.hdi", "Human Development Index")
    ax.plot([2005.4, 2026.6], [0.9, 0.9], color=p.TEAL, lw=1.0,
            ls=(0, (4, 3)), zorder=2)
    ctx.line(ax, *_xy(hdi), p.TEAL, label="UNDP")
    _finish(ig, ax)
    _note(ctx, ax, 2014.3, 0.894, "0.900 = very high human development",
          color=p.TEAL, va="top", size=7.8)
    y, v = _last(hdi)
    _note(ctx, ax, 0.98, 0.10, f"{y}: {v:.3f}", ha="right", axes=True,
          color=p.TEAL, weight="bold")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index")
    ctx.bars(ax, *_xy(score), p.BLUE)
    ctx.bars(ax, *_xy(old), "#A9BEDC")
    _finish(ig, ax)
    first = min(score)
    _note(ctx, ax, 0.02, 0.93, f"before {first}: the old 0–10 score ×10, "
          f"a different method (paler)", axes=True, size=7.8)
    y, v = _last(score)
    _note(ctx, ax, y, v + 3, f"{v:.0f}", ha="center", va="bottom",
          color=p.BLUE_D, weight="bold")
    _note(ctx, ax, 0.02, 0.85, "higher = cleaner", axes=True, size=7.8)

    ax = ig.slot("world.reserves", "Official reserves")
    ctx.line(ax, *_xy(res), p.PURPLE, label="Bank of Korea, end of period")
    _finish(ig, ax)
    _legend(ax, loc="upper left")
    y, v = _last(_series(ctx, "macro/reserves.csv", "eop_usbi",
                         last=ctx.LAST_FULL_YEAR))
    _note(ctx, ax, 0.98, 0.30, f"{y}: US${v:,.0f}bn", ha="right",
          axes=True, color=p.PURPLE, weight="bold")
    turn = min(y for y in niip if niip[y] > 0)
    y2, v2 = _last(niip)
    _note(ctx, ax, 0.98, 0.21, f"net foreign assets: US${v2:,.0f}bn in "
          f"{y2}, a creditor since {turn}", ha="right", axes=True,
          size=7.8)
    ig.axes_flat[2].yaxis.set_major_formatter(
        mticker.StrMethodFormatter("{x:,.0f}"))
    ig.axes_flat[1].yaxis.set_major_formatter(
        mticker.StrMethodFormatter("{x:.2f}"))


# ------------------------------------------------------------- demography
def plate_demography(ctx, ig):
    p = ctx.p
    last = ctx.LAST_FULL_YEAR
    pop = _series(ctx, "social/population.csv", "pop_mn", first=2006,
                  last=last)
    proj = _series(ctx, "social/population.csv", "pop_mn", first=last + 1)
    elderly = _series(ctx, "social/population.csv", "elderly_pct")
    tfr = _series(ctx, "social/vital.csv", "tfr")
    cbr = _series(ctx, "social/vital.csv", "crude_birth_rate")
    cdr = _series(ctx, "social/vital.csv", "crude_death_rate")
    births = _series(ctx, "social/vital.csv", "births")
    deaths = _series(ctx, "social/vital.csv", "deaths")
    natural = {y: cbr[y] - cdr[y] for y in cbr if y in cdr}

    ax = ig.slot("demography.population", "Population")
    ctx.line(ax, *ctx.index_2006(pop), p.BLUE,
             label="Mid-year population, Statistics Korea")
    _finish(ig, ax, slot_one=True)
    _legend(ax, loc="upper left")
    y, v = _peak(pop)
    py, pv = _last(proj)
    _note(ctx, ax, 0.98, 0.24, f"peak {y}: {v:.2f} mn; the 2024 projection "
          f"has {pv:.1f} mn by {py}", ha="right", axes=True, size=7.8)
    _note(ctx, ax, 0.98, 0.16, f"aged 65 and over: {elderly[last]:.1f}% in "
          f"{last}", ha="right", axes=True, size=7.8)

    ax = ig.slot("demography.fertility", "Total fertility rate")
    ax.plot([2005.4, 2026.6], [2.1, 2.1], color=p.MUTED, lw=1.0,
            ls=(0, (4, 3)), zorder=2)
    ctx.line(ax, *_xy(tfr), p.RED, label="Statistics Korea")
    _finish(ig, ax)
    _note(ctx, ax, 2006.0, 2.16, "2.1 = replacement", va="bottom", size=7.8)
    y, v = _low(tfr)
    _note(ctx, ax, y, v - 0.12, f"{y}: {v:.3f}, the world's lowest",
          ha="center", va="top", color=p.RED, weight="bold")
    y, v = _last(tfr)
    _note(ctx, ax, 0.98, 0.55, f"{y}: {v:.3f}", ha="right", axes=True,
          color=p.RED)

    ax = ig.slot("demography.birth_death", "Crude birth and death rates")
    ctx.line(ax, *_xy(cbr), p.BLUE, label="Births per 1,000")
    ctx.line(ax, *_xy(cdr), p.RED, label="Deaths per 1,000")
    _finish(ig, ax)
    _legend(ax, loc="upper right")
    cross = min(y for y in births if y in deaths and deaths[y] > births[y])
    _note(ctx, ax, cross, 13.0, f"deaths overtake births in {cross}",
          ha="center", va="bottom", color=p.INK)
    ax.plot([cross, cross], [cbr[cross] + 0.4, 12.6], color=p.FAINT,
            lw=0.8, ls=(0, (3, 3)), zorder=2)

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net migration")
    ctx.bars(ax, *_xy(natural), _signed(ctx, "#8FB0D9", "#E79AA0"))
    yrs, mig = net_migration_rate(ctx)
    ctx.line(ax, yrs, mig, p.TEAL, label="Net international migration")
    _finish(ig, ax)
    _legend(ax, loc="upper right")
    y, v = _last(natural)
    _note(ctx, ax, 0.02, 0.72, f"bars: births minus deaths, {v:.1f} per "
          f"1,000 in {y}", axes=True, size=7.8)
    m = dict(zip(yrs, mig))
    y = min(m, key=lambda k: m[k])
    _note(ctx, ax, y, m[y] - 1.0, f"{y}: borders closed, {m[y]:.1f}",
          ha="center", va="top", color=p.TEAL, size=7.8)


# --------------------------------------------------------------- security
def plate_safety(ctx, ig):
    p = ctx.p
    intl = {c: _series(ctx, "social/security_intl.csv", c)
            for c in ("homicide_unodc", "suicide_who", "road_who")}
    yrs, hom = homicide_rate(ctx)
    count = _series(ctx, "social/homicide.csv", "deaths")
    suicide = _series(ctx, "social/mortality.csv", "suicide")
    road = _series(ctx, "social/road.csv", "road_rate")
    work = {y: v * 10 for y, v in
            _series(ctx, "social/workplace.csv", "fatal_rate").items()}
    work_n = _series(ctx, "social/workplace.csv", "deaths")

    ax = ig.slot("security.homicide", "Homicide rate")
    ctx.line(ax, yrs, hom, p.NAVY,
             label="Deaths from assault, Statistics Korea")
    ctx.line(ax, *_xy(intl["homicide_unodc"]), p.MUTED, lw=1.6, ms=3,
             ls=(0, (2, 2)), label="UNODC")
    _finish(ig, ax, slot_one=True)
    _legend(ax, loc="upper left")
    y, v = yrs[-1], hom[-1]
    _note(ctx, ax, 0.98, 0.12, f"{y}: {v:.2f} per 100k, {count[y]:,.0f} "
          f"deaths", ha="right", axes=True, color=p.NAVY, weight="bold")

    ax = ig.slot("security.suicide", "Suicide rate")
    ctx.line(ax, *_xy(suicide), p.RED, label="Statistics Korea, crude")
    ctx.line(ax, *_xy(intl["suicide_who"]), p.MUTED, lw=1.6, ms=3,
             ls=(0, (2, 2)), label="WHO estimate")
    _finish(ig, ax)
    _legend(ax, loc="lower right")
    y, v = _peak(suicide)
    _note(ctx, ax, y, 37.0, f"{y}: {v:.1f}, the peak", ha="center",
          va="bottom", color=p.RED, weight="bold")
    _note(ctx, ax, 0.02, 0.12, "the OECD's highest rate", axes=True)

    ax = ig.slot("security.road_deaths", "Road traffic deaths")
    ctx.line(ax, *_xy(road), p.YELLOW,
             label="Police count, death within 30 days")
    ctx.line(ax, *_xy(intl["road_who"]), p.MUTED, lw=1.6, ms=3,
             ls=(0, (2, 2)), label="WHO estimate")
    _finish(ig, ax)
    _legend(ax, loc="upper right")
    a, b = min(road), ctx.LAST_FULL_YEAR
    _note(ctx, ax, 0.98, 0.62, f"{a}: {road[a]:.1f} to {b}: {road[b]:.1f}",
          ha="right", axes=True, color=p.INK, weight="bold")

    ax = ig.slot("security.lens", "Lens: workplace accident deaths")
    ctx.line(ax, *_xy(work), p.PURPLE,
             label="Per 100,000 workers insured against industrial "
                   "accidents")
    _finish(ig, ax)
    ax.set_ylim(0, 12)
    ax.set_ylabel("per 100,000 insured workers", fontsize=8.6,
                  color=p.MUTED)
    _legend(ax, loc="upper right", size=7.8)
    y = ctx.LAST_FULL_YEAR
    a = min(work_n)
    _note(ctx, ax, 0.02, 0.22, f"the rate fell by more than half; deaths "
          f"did not: {work_n[a]:,.0f} in {a}, {work_n[y]:,.0f} in {y}",
          axes=True, size=7.8)
    _note(ctx, ax, 0.02, 0.13, "the count includes occupational disease, "
          "the rate accidents only", axes=True, size=7.8)


# -------------------------------------------------------------- mortality
def plate_mortality(ctx, ig):
    p = ctx.p
    cdr = {y: v / 100 for y, v in
           _series(ctx, "social/mortality.csv", "all_causes").items()}
    excess = excess_deaths(ctx)
    deaths = _series(ctx, "social/vital.csv", "deaths")
    covid = _series(ctx, "social/covid.csv", "rate")
    covid_n = _series(ctx, "social/covid.csv", "deaths")
    rel = "social/mortality.csv"
    causes = [("cancer", "Cancer", p.NAVY), ("heart", "Heart disease", p.RED),
              ("pneumonia", "Pneumonia", p.TEAL),
              ("cerebrovascular", "Stroke", p.YELLOW)]

    ax = ig.slot("mortality.death_rate", "Crude death rate")
    ctx.line(ax, *_xy(cdr), p.INK, label="All causes, Statistics Korea")
    _finish(ig, ax, slot_one=True)
    _legend(ax, loc="upper left")
    y, v = _peak(cdr)
    _note(ctx, ax, y, v + 1.0, f"{y}: {v:.2f}", ha="center", va="bottom",
          weight="bold", color=p.INK)
    _note(ctx, ax, 0.98, 0.16, "an older population, not a sicker one: "
          "crude, not age-adjusted", ha="right", axes=True, size=7.8)

    ax = ig.slot("mortality.excess_deaths", "Excess deaths")
    ctx.bars(ax, *_xy(excess), _signed(ctx, p.RED, p.BLUE))
    _finish(ig, ax)
    base = sum(deaths[y] for y in BASELINE) / len(BASELINE)
    _note(ctx, ax, 0.02, 0.93, f"deaths vs the 2015–19 average of "
          f"{base:,.0f} a year", axes=True)
    y, v = _peak(excess)
    _note(ctx, ax, y, v + 2, f"{y}: +{v:.1f}%", ha="center", va="bottom",
          color=p.RED, weight="bold")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause")
    ctx.bars(ax, *_xy(covid), p.RED)
    _finish(ig, ax)
    y, v = _peak(covid)
    _note(ctx, ax, y, v + 8, f"{y}: {v:.1f} ({covid_n[y]:,.0f} deaths)",
          ha="center", va="bottom", color=p.RED, weight="bold")
    _note(ctx, ax, 0.02, 0.93, "death certificates, not the KDCA "
          "surveillance count", axes=True, size=7.8)

    ax = ig.slot("mortality.lens", "Lens: the big killers")
    for col, label, color in causes:
        ctx.line(ax, *_xy(_series(ctx, rel, col)), color, lw=2.0, ms=3.2,
                 label=label)
    _finish(ig, ax)
    ax.set_ylim(0, 230)
    _legend(ax, loc="upper left", ncol=4, size=7.8)
    pn = _series(ctx, rel, "pneumonia")
    a, b = min(pn), max(pn)
    _note(ctx, ax, 0.98, 0.58, f"pneumonia: {pn[a]:.1f} to {pn[b]:.1f}, "
          f"an ageing country's cause", ha="right", axes=True,
          color=p.TEAL, size=7.8)
    for a in ig.axes_flat:
        a.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))


# --------------------------------------------------------------- migration
def plate_migration(ctx, ig):
    p = ctx.p
    (iy, immigration), (ey, emigration) = migration_flow_rates(ctx)
    ny, net = net_migration_rate(ctx)
    stock = _series(ctx, "migration/foreign_residents_census.csv",
                    "foreign_citizen_share_pct")
    stock_n = _series(ctx, "migration/foreign_residents_census.csv",
                      "foreign_citizens_thousands")
    korean, foreign = migration_citizenship_net_rates(ctx)

    ax = ig.slot("migration.flows", "Immigration and emigration")
    ctx.line(ax, iy, immigration, p.BLUE, label="Immigration")
    ctx.line(ax, ey, emigration, p.RED, label="Emigration")
    _finish(ig, ax, slot_one=True)
    _legend(ax, loc="upper left", ncol=2)
    _note(ctx, ax, 0.98, 0.83,
          "more than 90 days; Koreans and foreigners together",
          ha="right", axes=True, size=7.8)
    y = max(set(iy) & set(ey))
    _note(ctx, ax, 0.98, 0.74,
          f"{y}: {immigration[iy.index(y)]:.1f} in, "
          f"{emigration[ey.index(y)]:.1f} out per 1,000",
          ha="right", axes=True, weight="bold")

    ax = ig.slot("migration.net", "Net migration")
    ctx.bars(ax, ny, net, _signed(ctx, p.BLUE, p.RED))
    _finish(ig, ax)
    net_map = dict(zip(ny, net))
    _note(ctx, ax, 2021, net_map[2021] - 1.0,
          f"2021: borders closed, {net_map[2021]:.1f}", ha="center",
          va="top", color=p.RED, weight="bold")
    y = max(net_map)
    _note(ctx, ax, 0.98, 0.18, f"{y}: +{net_map[y]:.1f} per 1,000",
          ha="right", axes=True, color=p.BLUE_D, weight="bold")

    ax = ig.slot("migration.foreign_born", "Foreign-citizen share")
    ctx.line(ax, *_xy(stock), p.TEAL,
             label="Resident foreigners at 1 November")
    _finish(ig, ax)
    _legend(ax, loc="upper left")
    _note(ctx, ax, 0.02, 0.82,
          "register census; citizenship, not birthplace",
          axes=True, size=7.8)
    y, v = _last(stock)
    _note(ctx, ax, 0.98, 0.18,
          f"{y}: {stock_n[y] / 1000:.3f} million, {v:.1f}%",
          ha="right", axes=True, color=p.TEAL, weight="bold")

    ax = ig.slot("migration.lens", "Lens: net migration by citizenship")
    ctx.line(ax, *_xy(korean), p.BLUE, label="Korean citizens")
    ctx.line(ax, *_xy(foreign), p.RED, label="Foreign citizens")
    _finish(ig, ax)
    ax.axhline(0, color=p.spine, lw=0.8, zorder=1)
    ax.set_ylim(-3.5, 5.5)
    ax.set_ylabel("per 1,000 people", fontsize=8.6, color=p.MUTED)
    _legend(ax, loc="upper left", ncol=2)
    _note(ctx, ax, 0.98, 0.80,
          "the two lines sum to total net migration",
          ha="right", axes=True, size=7.8)
    for a in ig.axes_flat:
        a.yaxis.set_major_formatter(mticker.FuncFormatter(_tick))


PLATES = (
    dict(slug="01_economy", topic="economy", builder=plate_economy,
         title="The Korean Economy, 2006–2026",
         subtitle="Real growth, income per person, prices and jobs. The "
                  "economy's size in dollars is in the world chapter.",
         source="Sources: Bank of Korea ECOS (national accounts) · "
                "Statistics Korea (CPI, labour force survey) · World Bank",
         alt="Four panels on the Korean economy from 2006 to 2026: real "
             "growth, positive every year except 2020; GDP per person in "
             "current dollars on a log scale; consumer price inflation "
             "against the 2% target; and the unemployment rate."),
    dict(slug="02_fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances, 2006–2026",
         subtitle="General government revenue, spending, balance, debt and "
                  "interest, all as a share of GDP.",
         source="Sources: IMF World Economic Outlook and Fiscal Monitor · "
                "Bank of Korea ECOS (SNA) · MOEF / e-National Indicators "
                "(D1)",
         alt="Four panels on Korean public finances: general government "
             "revenue and expenditure, the overall and primary balance, "
             "gross debt next to the national D1 measure, and the interest "
             "bill, all as a share of GDP."),
    dict(slug="03_spending", topic="spending", builder=plate_spending,
         title="Where the Money Goes, 2006–2026",
         subtitle="General government outlays by function, and the "
                  "investment the economy and the state make.",
         source="Sources: Bank of Korea ECOS — general government by COFOG "
                "function, national accounts · World Bank (R&D)",
         alt="Four panels on Korean government spending: outlays by "
             "function stacked as a share of GDP, social protection against "
             "everything else, the whole-economy investment rate, and "
             "government investment."),
    dict(slug="04_trade", topic="trade", builder=plate_trade,
         title="Foreign Trade, 2006–2026",
         subtitle="Exports and imports of goods and services against GDP, "
                  "where the goods go, and what they are.",
         source="Sources: World Bank (national accounts) · Korea Customs "
                "Service via Bank of Korea ECOS · UN Comtrade (HS headings)",
         alt="Four panels on Korean trade: exports and imports as a share "
             "of GDP, the trade balance, the shares of goods exports going "
             "to China, the United States, Vietnam and Japan, and the main "
             "export products at five snapshot years."),
    dict(slug="05_markets", topic="markets", builder=plate_markets,
         title="Money & Markets, 2006–2026",
         subtitle="The base rate, the ten-year yield, the won and the "
                  "KOSPI, the last two against the US dollar.",
         source="Sources: Bank of Korea ECOS · KRX and S&P DJI via Yahoo "
                "Finance (not official)",
         alt="Four panels on Korean markets: the Bank of Korea base rate "
             "against inflation, the ten-year government bond yield, the "
             "won against the dollar as an index, and the KOSPI in dollars "
             "next to the S&P 500, both indexed to 2006."),
    dict(slug="06_people", topic="people", builder=plate_people,
         title="People — Inequality, Poverty & Wages, 2006–2026",
         subtitle="A rich country with a poor old age.",
         source="Sources: Statistics Korea via e-National Indicators · "
                "Minimum Wage Commission · Bank of Korea ECOS · World Bank",
         alt="Four panels on living standards in Korea: the Gini "
             "coefficient from two surveys drawn separately, relative "
             "poverty against the World Bank line, the minimum wage in "
             "dollars a month, and poverty among people aged 65 and over "
             "before and after transfers."),
    dict(slug="07_world", topic="world", builder=plate_world,
         title="Korea in the World, 2006–2026",
         subtitle="The size of the economy in dollars, human development, "
                  "perceived integrity and the reserves.",
         source="Sources: World Bank · UNDP · Transparency International · "
                "Bank of Korea ECOS",
         alt="Four panels placing Korea internationally: GDP in current "
             "dollars, the Human Development Index, the Corruption "
             "Perceptions Index score, and official reserves."),
    dict(slug="08_demography", topic="demography", builder=plate_demography,
         title="Korea's Demographic Transition, 2006–2026",
         subtitle="The peak has passed: the lowest fertility on record, and "
                  "more deaths than births since 2020.",
         source="Sources: Statistics Korea (vital statistics, international "
                "migration, population projections) via e-National "
                "Indicators and Bank of Korea ECOS",
         alt="Four panels on Korean demography: the population indexed to "
             "2006, the total fertility rate against replacement, the crude "
             "birth and death rates, and natural increase next to net "
             "international migration per 1,000 people."),
    dict(slug="09_safety", topic="security", builder=plate_safety,
         title="Safety — Homicide, Suicide, Roads & Work, 2006–2026",
         subtitle="One of the safest countries in the world from other "
                  "people, and the most dangerous in the OECD from oneself.",
         source="Sources: Statistics Korea (Causes of Death) · National "
                "Police Agency · MOEL via e-National Indicators · UNODC and "
                "WHO via the World Bank",
         alt="Four panels on violent and accidental death in Korea: the "
             "homicide rate on a log scale, the suicide rate, road deaths, "
             "and workplace accident deaths per 100,000 insured workers."),
    dict(slug="10_credit", topic="credit", builder=plate_credit,
         title="Household Debt & the Price of Credit, 2006–2026",
         subtitle="Korean households owe almost as much as the economy "
                  "produces in a year.",
         source="Sources: BIS total credit and debt service statistics · "
                "Bank of Korea ECOS",
         alt="Four panels on Korean household credit: household debt as a "
             "share of GDP on the BIS and the Bank of Korea measures, new "
             "lending rates against the base rate, loan delinquency, and "
             "the household debt service ratio."),
    dict(slug="11_mortality", topic="mortality", builder=plate_mortality,
         title="Mortality — the Pandemic and an Ageing Country, 2006–2026",
         subtitle="Deaths per head rise because Korea is older; the "
                  "pandemic sits on top of that.",
         source="Sources: Statistics Korea — Causes of Death and Birth and "
                "Death Statistics, via e-National Indicators",
         alt="Four panels on deaths in Korea: the crude death rate, deaths "
             "as a share above the 2015–2019 average, COVID-19 deaths per "
             "100,000, and the death rates from cancer, heart disease, "
             "pneumonia and stroke."),
    dict(slug="12_migration", topic="migration", builder=plate_migration,
         title="Migration — Who Arrives, Who Leaves, Who Is Here, 2006–2026",
         subtitle="International moves lasting more than 90 days, and the "
                  "resident foreign-citizen population counted by the census.",
         source="Sources: Statistics Korea — International Migration "
                "Statistics and the register-based Population and Housing "
                "Census",
         alt="Four panels on migration in South Korea. Immigration and "
             "emigration count Korean and foreign citizens moving for more "
             "than 90 days, shown per 1,000 residents; net migration is "
             "negative only in 2021. The register census counts resident "
             "foreign citizens, 3.9% of the population in 2024. The lens "
             "splits net migration into Korean- and foreign-citizen "
             "contributions on the same definition."),
)
