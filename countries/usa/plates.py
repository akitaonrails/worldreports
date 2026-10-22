"""The usa plates.

Each function draws one plate from this country's committed CSVs and saves it
through the context, which resolves every path under countries/usa/ and
knows this country's palette, year span and last complete year. Ported from
the standalone usa-reports scripts/charts.py; the drawing is unchanged.
"""
from __future__ import annotations

import matplotlib.ticker as mticker
import csv

import numpy as np



# ---------------------------------------------------------------- usa only
# These were in the standalone project's style.py, but no other country uses
# them and their wording and styling had drifted from the look-alikes
# elsewhere, so they live with the plates that depend on them. Moving any of
# them into core/ would change a printed string on this plate or another's.

def _subset(child: str, parent: str) -> str:
    """A legend label that says a series is contained in another.

    A line drawn inside another line has to say so in its own label. "of
    which firearm homicides" asks the reader to work out what "which"
    refers to, and if they read the legend out of order they will take two
    nested series for two independent ones and conclude the wrong thing.
    """
    return f"{child} (subset of {parent})"


def _share_panel(ctx, ax, years, child, parent, color=None, label="",
                 annotate_last=True):
    """Draw child/parent as a percentage, on its own axis.

    Whenever a title or a caption promises a share, the share gets drawn.
    Two stacked lines do not show their own ratio: a reader cannot divide
    by eye, and when the subset rises while the total falls the picture
    says the opposite of the arithmetic.
    """
    color = color or ctx.p.RED
    pts = [(y, c / p * 100) for y, c, p in zip(years, child, parent)
           if c is not None and p]
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=color, lw=2.2, label=label, zorder=3)
    ax.fill_between(xs, 0, ys, color=color, alpha=0.08, zorder=2)
    if annotate_last:
        _annotate_value(ctx, ax, xs[-1], ys[-1], f"{ys[-1]:.1f}%",
                        color=color, offset=(0, 8))
    return ys


def _fmt_usd(v: float) -> str:
    """Compact dollars: 30,861 -> 'US$ 30.9tn'."""
    if abs(v) >= 1000:
        return f"US$ {v / 1000:.1f}tn"
    return f"US$ {v:,.0f}bn"


def _fmt_count(v: float) -> str:
    """A count with a thousands separator, or a compact one past a million."""
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.2f}M"
    return f"{v:,.0f}"


def _twin_legend(ctx, ax, ax2, loc="upper left", ncol=1):
    """One legend for a panel with a right-hand axis.

    Only artists that carry a real label are listed. `axhline` adds a
    Line2D to the axes with matplotlib's own placeholder name, so handing
    `ax.get_lines()` straight to `legend()` puts an entry reading
    "_child1" on the plate — which is what it did.
    """
    handles = []
    for a in (ax, ax2):
        handles.extend(a.get_lines())
        handles.extend(a.containers)
    handles = [h for h in handles
               if not (h.get_label() or "").startswith("_")]
    ax.legend(handles, [h.get_label() for h in handles], loc=loc, ncol=ncol,
              frameon=False, fontsize=9, labelcolor=ctx.p.INK,
              handlelength=1.6, borderaxespad=0.2)


def _legend(ctx, ax, loc="upper left", ncol=1, **kw):
    ax.legend(loc=loc, ncol=ncol, frameon=False, fontsize=9,
              labelcolor=ctx.p.INK, handlelength=1.6, borderaxespad=0.2, **kw)


def _annotate_value(ctx, ax, x, y, text, color=None, offset=(0, 10),
                    fontsize=9, weight="bold", ha="center"):
    """Print a value beside its point. Defaults to this country's ink."""
    ax.annotate(text, (x, y), textcoords="offset points", xytext=offset,
                fontsize=fontsize, fontweight=weight,
                color=color or ctx.p.INK, ha=ha, va="bottom", zorder=6)


from countries.usa import events
from countries.usa.events import EVENTS


def _table(ctx, rel: str, key: str = "year") -> dict[int, dict[str, str]]:
    """{year: row} for one committed CSV."""
    rows: dict[int, dict[str, str]] = {}
    # Routed through the country so the path is resolved — and
    # refused if it escapes — under countries/usa/data.
    with ctx.c.data(rel).open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                rows[int((r[key] or "").strip())] = r
            except (KeyError, TypeError, ValueError):
                continue
    return rows

def _col(ctx, tbl: dict[int, dict[str, str]], name: str, scale: float = 1.0,
        years=None) -> list[float | None]:
    """One column, aligned to YEARS, with a missing year as None.

    None rather than zero, and never interpolated: a year the publisher did
    not cover is a hole in the chart, and filling it would invent data.
    """
    out: list[float | None] = []
    for y in (years or ctx.YEARS):
        raw = ((tbl.get(y) or {}).get(name) or "").strip()
        try:
            out.append(float(raw) * scale)
        except ValueError:
            out.append(None)
    return out

def _nan(ctx, vals: list[float | None]) -> np.ndarray:
    """None -> nan, so bars and fills leave a gap instead of dropping to 0."""
    return np.array([np.nan if v is None else v for v in vals], dtype=float)

def _xy(ctx, vals: list[float | None], years=None):
    """The (x, y) pairs that exist, for a line that should not bridge a gap."""
    ys = years or ctx.YEARS
    pts = [(x, v) for x, v in zip(ys, vals) if v is not None]
    return [p[0] for p in pts], [p[1] for p in pts]

def _line(ctx, ax, vals, years=None, **kw):
    xs, ys = _xy(ctx, vals, years)
    if xs:
        ax.plot(xs, ys, **kw)
    return xs, ys

def _last_point(ctx, vals, years=None):
    xs, ys = _xy(ctx, vals, years)
    return (xs[-1], ys[-1]) if xs else (None, None)

def _partial_years(ctx, tbl, column: str, full: float) -> dict[int, float]:
    """{year: how much of it exists} for the years that are incomplete."""
    out = {}
    for y in ctx.YEARS:
        raw = ((tbl.get(y) or {}).get(column) or "").strip()
        try:
            got = float(raw)
        except ValueError:
            continue
        if 0 < got < full:
            out[y] = got
    return out

def _hatch_partial(ctx, ax, bars, tbl, column: str, full: float) -> None:
    """Hatch the bars of any year the source has not finished publishing."""
    partial = _partial_years(ctx, tbl, column, full)
    for x, bar in zip(ctx.YEARS, bars):
        if x in partial:
            bar.set_hatch("////")
            bar.set_edgecolor(ctx.p.FAINT)
            bar.set_linewidth(0.6)

def _estimate_years(ctx, tbl) -> set[int]:
    """The years a table marks as a projection rather than an actual."""
    return {y for y in ctx.YEARS
            if ((tbl.get(y) or {}).get("estimate") or "").strip() == "1"}

def _line_with_estimate(ctx, ax, vals, est: set[int], color, label, lw=2.4):
    """Draw actuals solid and the projected tail dashed.

    An estimate joined seamlessly onto measured history is the easiest way
    to make a forecast look like a fact, so the tail changes to a dashed
    line and the legend of the plate says which years are projected.
    """
    actual = [v if y not in est else None for y, v in zip(ctx.YEARS, vals)]
    _line(ctx, ax, actual, color=color, lw=lw, label=label)
    tail_years = sorted(est)
    if tail_years:
        first = min(tail_years)
        prior = [y for y in ctx.YEARS if y < first and vals[ctx.YEARS.index(y)] is not None]
        span = ([max(prior)] if prior else []) + tail_years
        seg = [vals[ctx.YEARS.index(y)] if y in span else None for y in ctx.YEARS]
        _line(ctx, ax, seg, color=color, lw=lw, ls=(0, (4, 2.5)))

def plate_economy(ctx) -> None:
    gdp = _table(ctx, "macro/gdp.csv")
    cpi = _table(ctx, "macro/cpi.csv")
    une = _table(ctx, "macro/unemployment.csv")

    g = ctx.fig(
        "The American economy, 2006-2026",
        "Output, prices and work, from the agencies that measure them",
        source=("Sources: Bureau of Economic Analysis, NIPA tables 1.1.1, "
                "1.1.5 and 7.1 · Bureau of Labor Statistics, CPI-U and "
                "Current Population Survey"),
        # A right-hand axis in the right-hand column: its ticks and
        # its label need room the shared margin does not leave, and
        # without this they are drawn off the canvas. See Context.fig.
        right=0.955,
    )

    # ---- real growth ----------------------------------------------------
    ax = g.next_panel("Real GDP growth")
    growth = _col(ctx, gdp, "real_growth")
    vals = _nan(ctx, growth)
    colors = [ctx.p.RED if (v is not None and v < 0) else ctx.p.NAVY for v in growth]
    bars = ax.bar(ctx.YEARS, vals, color=colors, width=0.68)
    g.style_axis(ax)
    g.add_recessions(ax)
    ax.axhline(0, color=ctx.p.INK, lw=0.9)
    ax.set_ylabel("% a year")
    for x, v in zip(ctx.YEARS, growth):
        if v is None:
            continue
        if v in (max(p for p in growth if p is not None),
                 min(p for p in growth if p is not None)):
            _annotate_value(ctx, ax, x, v, f"{v:+.1f}%",
                           color=ctx.p.RED if v < 0 else ctx.p.NAVY,
                           offset=(0, 8 if v > 0 else -18))
    g.headroom(ax, top=0.22, bottom=0.16)
    ax.text(0.985, 0.045, "2020 and 2021 are one event: the collapse\n"
                          "and the rebound off it.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="bottom", ha="right")

    # ---- the level ------------------------------------------------------
    ax = g.next_panel("GDP and GDP per person")
    nominal = _col(ctx, gdp, "nominal_usdbn")
    percap = _col(ctx, gdp, "gdp_per_capita_usd")
    _line(ctx, ax, nominal, color=ctx.p.NAVY, lw=2.6, label="GDP, current US$")
    g.style_axis(ax)
    g.add_recessions(ax, label=False)
    ax.set_ylabel("US$ bn")
    x, y = _last_point(ctx, nominal)
    if x:
        _annotate_value(ctx, ax, x, y, _fmt_usd(y), color=ctx.p.NAVY, ha="right",
                       offset=(-6, 8))
    ax2 = ax.twinx()
    _line(ctx, ax2, percap, color=ctx.p.GOLD, lw=2.0, ls=(0, (5, 2)),
         label="GDP per person (right)")
    ax2.spines[["top", "left"]].set_visible(False)
    ax2.set_ylabel("US$ per person", color=ctx.p.GOLD)
    ax2.tick_params(colors=ctx.p.GOLD, length=0)
    ax2.grid(False)
    x, y = _last_point(ctx, percap)
    if x:
        _annotate_value(ctx, ax2, x, y, f"US$ {y:,.0f}", color=ctx.p.GOLD, ha="right",
                       offset=(-8, -24))
    _twin_legend(ctx, ax, ax2, loc="upper left")
    g.mark_partial(ax, 2026, "2026: 2 of 4 quarters")

    # ---- inflation ------------------------------------------------------
    ax = g.next_panel("Consumer price inflation")
    headline = _col(ctx, cpi, "value")
    core = _col(ctx, cpi, "core")
    _line(ctx, ax, headline, color=ctx.p.RED, lw=2.6, label="CPI-U, all items")
    _line(ctx, ax, core, color=ctx.p.NAVY, lw=2.0, ls=(0, (5, 2)),
         label="core (less food and energy)")
    g.style_axis(ax)
    g.add_recessions(ax, label=False)
    ax.axhline(2.0, color=ctx.p.TEAL, lw=1.0, ls=(0, (2, 2)))
    ax.text(ctx.YEARS[0] + 0.2, 2.0, "Fed's 2% goal", fontsize=7.8, color=ctx.p.TEAL,
            va="bottom")
    ax.set_ylabel("% a year")
    peak = max((v, x) for x, v in zip(ctx.YEARS, headline) if v is not None)
    _annotate_value(ctx, ax, peak[1], peak[0], f"{peak[0]:.1f}%", color=ctx.p.RED)
    _legend(ctx, ax)

    # ---- unemployment ---------------------------------------------------
    ax = g.next_panel("Unemployment: the headline rate and the broad one")
    u3 = _col(ctx, une, "value")
    u6 = _col(ctx, une, "u6")
    _line(ctx, ax, u6, color=ctx.p.GOLD, lw=2.4,
         label="U-6, including part-time for economic reasons")
    _line(ctx, ax, u3, color=ctx.p.NAVY, lw=2.6,
         label=_subset("U-3, the headline rate", "U-6"))
    xs6, ys6 = _xy(ctx, u6)
    xs3, ys3 = _xy(ctx, u3)
    if xs3 and xs6:
        common = [x for x in xs3 if x in xs6]
        ax.fill_between(common,
                        [ys3[xs3.index(x)] for x in common],
                        [ys6[xs6.index(x)] for x in common],
                        color=ctx.p.GOLD, alpha=0.12, zorder=1)
    g.style_axis(ax)
    g.add_recessions(ax, label=False)
    ax.set_ylabel("% of the labour force")
    _legend(ctx, ax)
    # The break goes next to the series it is about, not in a corner.
    ax.annotate(events.BREAKS["unemployment_2025"][1],
                xy=(2025, ys3[-1] if ys3 else 4.0),
                xytext=(2019.4, (max(ys6) if ys6 else 10) * 0.92),
                fontsize=8, color=ctx.p.RED, style="italic",
                arrowprops=dict(arrowstyle="-", color=ctx.p.RED, lw=0.8,
                                shrinkA=2, shrinkB=4))
    g.mark_partial(ax, 2022, "2025: 11 months · 2026: 9 months")

    g.save(ctx.out("01-economy.png"))

def plate_fiscal(ctx) -> None:
    bud = _table(ctx, "fiscal/budget.csv", key="fiscal_year")
    debt = _table(ctx, "fiscal/debt.csv", key="fiscal_year")

    g = ctx.fig(
        "What Washington takes in and what it owes",
        "Federal receipts, outlays and debt, by fiscal year ending 30 September",
        source=("Sources: OMB Historical Tables 1.1 and 1.2 (FY2027 edition) "
                "for FY2006-2025 · Treasury Fiscal Data, Monthly Treasury "
                "Statement and Debt to the Penny, for FY2026"),
        # A right-hand axis in the right-hand column: its ticks and
        # its label need room the shared margin does not leave, and
        # without this they are drawn off the canvas. See Context.fig.
        right=0.955,
    )

    # ---- receipts and outlays -------------------------------------------
    ax = g.next_panel("Receipts and outlays, share of GDP")
    rec = _col(ctx, bud, "receipts_pct_gdp")
    out = _col(ctx, bud, "outlays_pct_gdp")
    _line(ctx, ax, out, color=ctx.p.RED, lw=2.6, label="outlays")
    _line(ctx, ax, rec, color=ctx.p.NAVY, lw=2.6, label="receipts")
    xs, _ = _xy(ctx, out)
    ax.fill_between(xs, [v for v in rec if v is not None],
                    [v for v in out if v is not None],
                    color=ctx.p.RED, alpha=0.10, zorder=1)
    g.style_axis(ax)
    g.add_recessions(ax)
    ax.set_ylabel("% of GDP")
    _legend(ctx, ax)
    ax.text(0.98, 0.04, "The shaded gap is the deficit.", ha="right",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic")

    # ---- the deficit ----------------------------------------------------
    ax = g.next_panel("Deficit, share of GDP")
    def_ = _col(ctx, bud, "deficit_pct_gdp")
    bars = ax.bar(ctx.YEARS, _nan(ctx, def_), color=ctx.p.RED, width=0.68)
    for x, bar, v in zip(ctx.YEARS, bars, def_):
        if v is not None and v > 0:
            bar.set_color(ctx.p.GREEN)
    _hatch_partial(ctx, ax, bars, bud, "gdp_quarters", 4)
    g.style_axis(ax)
    ax.axhline(0, color=ctx.p.INK, lw=0.9)
    ax.set_ylabel("% of GDP")
    g.headroom(ax, top=0.0, bottom=0.14)
    for x, v in zip(ctx.YEARS, def_):
        if v is not None and v < -9:
            _annotate_value(ctx, ax, x, v, f"{v:.1f}%", color=ctx.p.RED, offset=(0, -16),
                           fontsize=8.5)
    g.mark_partial(ax, 2021, "2026 deficit ratio uses GDP from 3 of 4 quarters")

    # ---- the debt stock -------------------------------------------------
    ax = g.next_panel("Debt outstanding: gross, and the part held by the public")
    gross = _col(ctx, debt, "gross_tn")
    public = _col(ctx, debt, "public_tn")
    xs, ys = _xy(ctx, gross)
    ax.bar(xs, ys, color=ctx.p.NAVY, width=0.68, label="gross federal debt")
    xs2, ys2 = _xy(ctx, public)
    ax.bar(xs2, ys2, color=ctx.p.GOLD, width=0.40,
           label=_subset("held by the public", "gross federal debt"))
    g.style_axis(ax)
    ax.set_ylabel("US$ tn")
    _legend(ctx, ax)
    x, y = _last_point(ctx, gross)
    if x:
        _annotate_value(ctx, ax, x, y, f"US$ {y:.1f}tn", color=ctx.p.NAVY, ha="right",
                       offset=(-4, 6))
    ax.text(0.015, 0.78, "The rest is held inside government, mostly by the\n"
                         "Social Security and Medicare trust funds.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="top")

    # ---- debt to GDP, and the share held by the public -------------------
    ax = g.next_panel("Debt as a share of GDP, and the public share of it")
    gross_pct = _col(ctx, debt, "gross_pct_gdp")
    public_pct = _col(ctx, debt, "public_pct_gdp")
    _line(ctx, ax, gross_pct, color=ctx.p.NAVY, lw=2.6, label="gross debt, % of GDP")
    _line(ctx, ax, public_pct, color=ctx.p.GOLD, lw=2.2, ls=(0, (5, 2)),
         label=_subset("held by the public, % of GDP", "gross debt"))
    g.style_axis(ax)
    g.add_recessions(ax, label=False)
    ax.set_ylabel("% of GDP")
    ax.axhline(100, color=ctx.p.FAINT, lw=0.9, ls=(0, (2, 2)))
    ax.text(ctx.YEARS[0] + 0.2, 100, "100% of GDP", fontsize=7.8, color=ctx.p.FAINT,
            va="bottom")
    _legend(ctx, ax, loc="lower right")
    # The title promises a share, so the share is drawn.
    ax2 = ax.twinx()
    _share_panel(ctx, ax2, ctx.YEARS, public, gross, color=ctx.p.TEAL,
                label="public debt as % of gross", annotate_last=False)
    ax2.spines[["top", "left"]].set_visible(False)
    ax2.set_ylabel("public share of gross, %", color=ctx.p.TEAL)
    ax2.tick_params(colors=ctx.p.TEAL, length=0)
    ax2.set_ylim(50, 100)
    ax2.grid(False)

    g.save(ctx.out("02-fiscal.png"))

def plate_spending(ctx) -> None:
    sp = _table(ctx, "fiscal/spending.csv", key="fiscal_year")
    est = _estimate_years(ctx, sp)

    g = ctx.fig(
        "Where the money goes",
        "Federal outlays by function, in dollars and as a share of the budget",
        source=("Source: OMB Historical Tables 3.2, outlays by function and "
                "subfunction (FY2027 edition). Dashed segments are OMB "
                "estimates, not actuals."),
        # A right-hand axis in the right-hand column: its ticks and
        # its label need room the shared margin does not leave, and
        # without this they are drawn off the canvas. See Context.fig.
        right=0.955,
    )

    FUNCS = (("social_security_usdbn", "Social Security", ctx.p.NAVY),
             ("medicare_usdbn", "Medicare", ctx.p.RED),
             ("health_usdbn", "Health (incl. Medicaid)", ctx.p.GOLD),
             ("defense_usdbn", "National defense", ctx.p.TEAL),
             ("net_interest_usdbn", "Net interest", ctx.p.PURPLE),
             ("income_security_usdbn", "Income security", ctx.p.BLUE))

    # ---- the big functions ----------------------------------------------
    ax = g.next_panel("The largest functions, in dollars")
    for name, label, color in FUNCS:
        _line_with_estimate(ctx, ax, _col(ctx, sp, name), est, color, label)
    g.style_axis(ax)
    g.add_recessions(ax, label=False)
    ax.set_ylabel("US$ bn")
    _legend(ctx, ax, ncol=2)
    g.headroom(ax, top=0.26)
    g.mark_partial(ax, 2021, f"{min(est)} is an OMB estimate" if est else "")

    # ---- interest overtakes defence --------------------------------------
    ax = g.next_panel("Net interest has overtaken national defense")
    interest = _col(ctx, sp, "net_interest_usdbn")
    defense = _col(ctx, sp, "defense_usdbn")
    _line_with_estimate(ctx, ax, defense, est, ctx.p.TEAL, "National defense", lw=2.6)
    _line_with_estimate(ctx, ax, interest, est, ctx.p.PURPLE, "Net interest", lw=2.6)
    g.style_axis(ax)
    ax.set_ylabel("US$ bn")
    _legend(ctx, ax)
    cross = next((y for y in ctx.YEARS
                  if (i := interest[ctx.YEARS.index(y)]) is not None
                  and (d := defense[ctx.YEARS.index(y)]) is not None and i > d), None)
    if cross:
        g.add_event(ax, cross, f"interest passes defense\nin FY{cross}",
                    dy=0.30, color=ctx.p.PURPLE)
    g.headroom(ax, top=0.18)

    # ---- shares ----------------------------------------------------------
    ax = g.next_panel("Share of all federal outlays")
    total = _col(ctx, sp, "total_usdbn")
    for name, label, color in FUNCS:
        vals = _col(ctx, sp, name)
        shares = [None if (v is None or not t) else v / t * 100
                  for v, t in zip(vals, total)]
        _line_with_estimate(ctx, ax, shares, est, color, label, lw=2.2)
    g.style_axis(ax)
    ax.set_ylabel("% of total outlays")
    _legend(ctx, ax, ncol=2)
    g.headroom(ax, top=0.26)

    # ---- the education break ---------------------------------------------
    ax = g.next_panel("Education, training and employment: a break, not a cut")
    edu = _col(ctx, sp, "education_usdbn")
    bars = ax.bar(ctx.YEARS, _nan(ctx, edu), color=ctx.p.GOLD, width=0.68)
    for y, bar in zip(ctx.YEARS, bars):
        if y in est:
            bar.set_hatch("////")
            bar.set_edgecolor(ctx.p.FAINT)
        v = edu[ctx.YEARS.index(y)]
        if v is not None and v < 0:
            bar.set_color(ctx.p.RED)
    g.style_axis(ax)
    ax.axhline(0, color=ctx.p.INK, lw=0.9)
    ax.set_ylabel("US$ bn")
    g.headroom(ax, top=0.30, bottom=0.08)
    peak = max((v, y) for y, v in zip(ctx.YEARS, edu) if v is not None)
    ax.annotate(events.BREAKS["education_outlays"][1],
                xy=(2023, min(v for v in edu if v is not None)),
                xytext=(2010.5, peak[0] * 0.62),
                fontsize=8.2, color=ctx.p.RED, style="italic",
                arrowprops=dict(arrowstyle="-", color=ctx.p.RED, lw=0.8,
                                shrinkA=2, shrinkB=6))
    _annotate_value(ctx, ax, peak[1], peak[0], f"US$ {peak[0]:,.0f}bn", color=ctx.p.GOLD)

    g.save(ctx.out("03-spending.png"))

def plate_trade(ctx) -> None:
    bea = _table(ctx, "trade/trade.csv")
    goods = _table(ctx, "trade/goods.csv")
    partners_rows: dict[str, dict[int, float]] = {}
    with ctx.c.data("trade/partners.csv").open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                partners_rows.setdefault(r["country"], {})[int(r["year"])] = \
                    float(r["import_share"])
            except (KeyError, TypeError, ValueError):
                continue

    g = ctx.fig(
        "What America buys and sells",
        "Trade in goods and services, and who the goods come from",
        source=("Sources: Bureau of Economic Analysis, NIPA table 4.1 "
                "(goods and services, balance-of-payments basis) · Census "
                "Bureau, country trade balances (goods, customs basis)"))

    # ---- the overall balance ---------------------------------------------
    ax = g.next_panel("Exports, imports and the balance")
    exp, imp = _col(ctx, bea, "exports"), _col(ctx, bea, "imports")
    bal = _col(ctx, bea, "balance")
    _line(ctx, ax, imp, color=ctx.p.RED, lw=2.6, label="imports")
    _line(ctx, ax, exp, color=ctx.p.NAVY, lw=2.6, label="exports")
    xs, _ = _xy(ctx, imp)
    ax.fill_between(xs, [v for v in exp if v is not None],
                    [v for v in imp if v is not None],
                    color=ctx.p.RED, alpha=0.10, zorder=1)
    g.style_axis(ax)
    g.add_recessions(ax, label=False)
    ax.set_ylabel("US$ bn")
    _legend(ctx, ax)
    x, y = _last_point(ctx, bal)
    if x:
        ax.text(0.985, 0.04, f"balance {_fmt_usd(y)}", transform=ax.transAxes,
                ha="right", fontsize=9, color=ctx.p.RED, fontweight="bold")
    g.mark_partial(ax, 2021, "2026: 2 of 4 quarters")

    # ---- goods against services ------------------------------------------
    ax = g.next_panel("The goods deficit and the services surplus")
    gb, sb = _col(ctx, bea, "goods_balance"), _col(ctx, bea, "services_balance")
    ax.bar(ctx.YEARS, _nan(ctx, gb), color=ctx.p.RED, width=0.68,
           label=_subset("goods balance", "the total balance"))
    ax.bar(ctx.YEARS, _nan(ctx, sb), color=ctx.p.TEAL, width=0.68,
           label=_subset("services balance", "the total balance"))
    _line(ctx, ax, bal, color=ctx.p.INK, lw=2.2, label="total balance")
    g.style_axis(ax)
    ax.axhline(0, color=ctx.p.INK, lw=0.9)
    ax.set_ylabel("US$ bn")
    _legend(ctx, ax, loc="lower left")
    g.headroom(ax, top=0.12, bottom=0.14)

    # ---- partners ---------------------------------------------------------
    ax = g.next_panel("Share of US goods imports, by partner")
    PICK = (("China", ctx.p.RED), ("European Union", ctx.p.NAVY), ("Mexico", ctx.p.GOLD),
            ("Canada", ctx.p.TEAL), ("Vietnam", ctx.p.PURPLE), ("Taiwan", ctx.p.BLUE))
    for name, color in PICK:
        series = partners_rows.get(name, {})
        vals = [series.get(y) for y in ctx.YEARS]
        _line(ctx, ax, vals, color=color, lw=2.4, label=name)
    # No end-of-line labels here: in 2026 three of these partners land
    # within half a percentage point of each other, so the labels collide
    # and have to be read against the wrong line. The legend carries it.
    g.style_axis(ax)
    ax.set_ylabel("% of goods imports")
    _legend(ctx, ax, ncol=2)
    g.headroom(ax, top=0.24)

    # ---- the two bases ----------------------------------------------------
    ax = g.next_panel("Two official goods deficits, measured differently")
    census = _col(ctx, goods, "balance")
    _line(ctx, ax, census, color=ctx.p.GOLD, lw=2.6,
         label="Census: goods at customs value")
    _line(ctx, ax, gb, color=ctx.p.NAVY, lw=2.6,
         label="BEA: goods, balance-of-payments basis")
    g.style_axis(ax)
    ax.set_ylabel("US$ bn")
    _legend(ctx, ax, loc="lower right")
    ax.text(0.015, 0.96,
            "The same trade, counted under two definitions. They are never\n"
            "added together and never spliced into one line.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="top")
    g.mark_partial(ax, 2021, "2026: Census 8 of 12 months, BEA 2 of 4 quarters")

    g.save(ctx.out("04-trade.png"))

def plate_markets(ctx) -> None:
    sp = _table(ctx, "markets/sp500.csv")
    ff = _table(ctx, "macro/fed_funds.csv")
    cpi = _table(ctx, "macro/cpi.csv")
    ten = _table(ctx, "macro/treasury.csv")
    usd = _table(ctx, "macro/dollar.csv")
    mort = _table(ctx, "macro/mortgage.csv")

    g = ctx.fig(
        "Money and markets",
        "The policy rate, the yield curve, the dollar and the stock market",
        source=("Sources: NY Fed (federal funds target) · US Treasury par "
                "yield curve · Federal Reserve Board H.10 · Freddie Mac "
                "PMMS · S&P 500 via Yahoo Finance, a redistributor"),
        # A right-hand axis in the right-hand column: its ticks and
        # its label need room the shared margin does not leave, and
        # without this they are drawn off the canvas. See Context.fig.
        right=0.955,
    )

    # ---- the index and what it cost to hold ------------------------------
    ax = g.next_panel("The S&P 500, and the fall inside each year")
    close = _col(ctx, sp, "close")
    _line(ctx, ax, close, color=ctx.p.NAVY, lw=2.6, label="year-end close")
    g.style_axis(ax)
    g.add_recessions(ax, label=False)
    ax.set_ylabel("index")
    x, y = _last_point(ctx, close)
    if x:
        _annotate_value(ctx, ax, x, y, f"{y:,.0f}", color=ctx.p.NAVY, ha="right",
                       offset=(-6, 8))
    ax2 = ax.twinx()
    dd = _col(ctx, sp, "drawdown_pct")
    ax2.bar(ctx.YEARS, _nan(ctx, dd), color=ctx.p.RED, width=0.62, alpha=0.5,
            label="largest fall within the year (right)")
    ax2.set_ylim(-110, 0)
    ax2.spines[["top", "left", "right"]].set_visible(False)
    ax2.set_ylabel("peak-to-trough, %", color=ctx.p.RED)
    ax2.tick_params(colors=ctx.p.RED, length=0)
    ax2.grid(False)
    worst = min((v, y2) for y2, v in zip(ctx.YEARS, dd) if v is not None)
    _annotate_value(ctx, ax2, worst[1], worst[0], f"{worst[0]:.0f}%", color=ctx.p.RED,
                   offset=(0, -16))
    _twin_legend(ctx, ax, ax2, loc="upper left")
    ax.text(0.015, 0.60, "2008 ended 38% down and fell 48% on the way.\n"
                         "A year-end close alone hides the drawdown.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="top")
    g.mark_partial(ax, 2021, "2026: 202 of about 250 trading days")

    # ---- policy against prices -------------------------------------------
    ax = g.next_panel("The policy rate against inflation")
    target = _col(ctx, ff, "target_eop")
    hi = _col(ctx, ff, "target_hi")
    mid = [t if h is None else (t + h) / 2 for t, h in zip(target, hi)]
    infl = _col(ctx, cpi, "value")
    _line(ctx, ax, mid, color=ctx.p.NAVY, lw=2.6, label="FOMC target at year end")
    _line(ctx, ax, infl, color=ctx.p.RED, lw=2.4, ls=(0, (5, 2)), label="CPI inflation")
    xs, _ = _xy(ctx, mid)
    ax.fill_between(xs, [v for v in mid if v is not None],
                    [v for v in infl if v is not None],
                    where=[m < i for m, i in zip(
                        [v for v in mid if v is not None],
                        [v for v in infl if v is not None])],
                    color=ctx.p.RED, alpha=0.12, interpolate=True)
    g.style_axis(ax)
    ax.axhline(0, color=ctx.p.INK, lw=0.9)
    ax.set_ylabel("%")
    _legend(ctx, ax)
    ax.text(0.985, 0.04, "Shaded where the policy rate sat below inflation.",
            transform=ax.transAxes, ha="right", fontsize=8, color=ctx.p.MUTED,
            style="italic")
    g.headroom(ax, top=0.16)

    # ---- the curve --------------------------------------------------------
    ax = g.next_panel("The yield curve: 10-year minus 2-year")
    spread = _col(ctx, ten, "spread_10y_2y_avg")
    xs, ys = _xy(ctx, spread)
    ax.plot(xs, ys, color=ctx.p.NAVY, lw=2.6)
    ax.fill_between(xs, 0, ys, where=[v >= 0 for v in ys], color=ctx.p.NAVY,
                    alpha=0.12, interpolate=True)
    ax.fill_between(xs, 0, ys, where=[v < 0 for v in ys], color=ctx.p.RED,
                    alpha=0.22, interpolate=True)
    g.style_axis(ax)
    g.add_recessions(ax, label=False)
    ax.axhline(0, color=ctx.p.INK, lw=1.0)
    ax.set_ylabel("percentage points, yearly average")
    inverted = [y2 for y2, v in zip(ctx.YEARS, spread) if v is not None and v < 0]
    if inverted:
        ax.text(0.015, 0.06,
                "Inverted (red) in these years:\n"
                + ", ".join(str(y2) for y2 in inverted)
                + "\nAn inversion has preceded each recession shaded here, "
                  "but\nthe lag has run from several months to over two years.",
                transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED,
                style="italic", va="bottom")
    g.headroom(ax, top=0.30, bottom=0.10)

    # ---- the dollar and the mortgage --------------------------------------
    ax = g.next_panel("The dollar, and what a mortgage costs")
    broad = _col(ctx, usd, "broad_index_avg")
    _line(ctx, ax, broad, color=ctx.p.NAVY, lw=2.6, label="broad dollar index (Jan 2006 = 100)")
    g.style_axis(ax)
    ax.set_ylabel("index")
    ax.axhline(100, color=ctx.p.FAINT, lw=0.9, ls=(0, (2, 2)))
    ax2 = ax.twinx()
    thirty = _col(ctx, mort, "thirty_year_avg")
    _line(ctx, ax2, thirty, color=ctx.p.GOLD, lw=2.4, ls=(0, (5, 2)),
         label="30-year fixed mortgage (right)")
    ax2.spines[["top", "left"]].set_visible(False)
    ax2.set_ylabel("% a year", color=ctx.p.GOLD)
    ax2.tick_params(colors=ctx.p.GOLD, length=0)
    ax2.grid(False)
    x, y = _last_point(ctx, thirty)
    if x:
        _annotate_value(ctx, ax2, x, y, f"{y:.2f}%", color=ctx.p.GOLD, ha="right",
                       offset=(-6, 6))
    _twin_legend(ctx, ax, ax2, loc="upper left")
    g.headroom(ax, top=0.18)

    g.save(ctx.out("05-markets.png"))

def plate_people(ctx) -> None:
    inc = _table(ctx, "social/income.csv")
    pov = _table(ctx, "social/poverty.csv")
    mw = _table(ctx, "social/minimum_wage.csv")
    cpi = _table(ctx, "macro/cpi.csv")

    g = ctx.fig(
        "Households",
        "What a typical household earns, who is counted as poor, and the wage floor",
        source=("Sources: Census Bureau, Current Population Survey ASEC — "
                "table H-8 and the P60 poverty report · Department of Labor, "
                "Wage and Hour Division · deflated with BLS CPI-U"))

    # ---- income -----------------------------------------------------------
    ax = g.next_panel("Median household income")
    nominal = _col(ctx, inc, "median_household_income")
    real = _col(ctx, inc, "median_household_income_2025usd")
    _line(ctx, ax, nominal, color=ctx.p.FAINT, lw=2.2, ls=(0, (5, 2)),
         label="in the dollars of the day")
    _line(ctx, ax, real, color=ctx.p.NAVY, lw=2.8, label="in 2025 dollars")
    g.style_axis(ax)
    g.add_recessions(ax, label=False)
    ax.set_ylabel("US$ a year")
    _legend(ctx, ax, loc="upper left")
    for vals, color in ((real, ctx.p.NAVY),):
        x, y = _last_point(ctx, vals)
        if x:
            _annotate_value(ctx, ax, x, y, f"US$ {y:,.0f}", color=color, ha="right",
                           offset=(-6, 8))
    pre = real[ctx.YEARS.index(2019)]
    now = _last_point(ctx, real)[1]
    if pre and now:
        ax.text(0.985, 0.06,
                f"Adjusted for prices, the median household\n"
                f"has gained {((now / pre) - 1) * 100:.1f}% since 2019.",
                transform=ax.transAxes, fontsize=8.2, color=ctx.p.MUTED,
                style="italic", va="bottom", ha="right")
    g.headroom(ax, top=0.18)

    # ---- the two poverty measures ----------------------------------------
    ax = g.next_panel("Two official poverty rates, all people")
    opm = _col(ctx, pov, "opm_all")
    spm = _col(ctx, pov, "spm_all")
    _line(ctx, ax, opm, color=ctx.p.NAVY, lw=2.6, label="official measure (OPM)")
    _line(ctx, ax, spm, color=ctx.p.RED, lw=2.6, label="supplemental measure (SPM)")
    g.style_axis(ax)
    g.add_recessions(ax, label=False)
    ax.set_ylabel("% of people")
    _legend(ctx, ax)
    ax.text(0.015, 0.06,
            "The official measure counts pre-tax cash only. The supplemental\n"
            "measure adds tax credits and benefits and subtracts medical and\n"
            "work costs. Census publishes it from 2009; they are different\n"
            "definitions, not a revision of one another.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="bottom")
    g.headroom(ax, top=0.16, bottom=0.42)

    # ---- children ---------------------------------------------------------
    ax = g.next_panel("Child poverty: what the official measure cannot see")
    copm = _col(ctx, pov, "opm_under18")
    cspm = _col(ctx, pov, "spm_under18")
    _line(ctx, ax, copm, color=ctx.p.NAVY, lw=2.6, label="official measure (OPM)")
    _line(ctx, ax, cspm, color=ctx.p.RED, lw=2.8, label="supplemental measure (SPM)")
    g.style_axis(ax)
    ax.set_ylabel("% of people under 18")
    _legend(ctx, ax)
    trough = min((v, y) for y, v in zip(ctx.YEARS, cspm) if v is not None)
    ax.annotate("2021: the expanded Child Tax Credit cuts SPM child\n"
                "poverty to 5.1%. The official measure, which counts no\n"
                "tax credit, reads 15.3% and shows nothing at all.",
                xy=(trough[1], trough[0]), xytext=(2009.6, 3.0),
                fontsize=8.2, color=ctx.p.RED, style="italic",
                arrowprops=dict(arrowstyle="-", color=ctx.p.RED, lw=0.9,
                                shrinkA=2, shrinkB=6))
    g.headroom(ax, top=0.12, bottom=0.46)

    # ---- the wage floor ---------------------------------------------------
    ax = g.next_panel("The federal minimum wage, nominal and real")
    jan = _col(ctx, mw, "federal_min_jan1")
    idx = _col(ctx, cpi, "index")
    base = idx[ctx.YEARS.index(2025)]
    real_mw = [None if (v is None or i is None or not i) else v * base / i
               for v, i in zip(jan, idx)]
    ax.step(ctx.YEARS, _nan(ctx, jan), where="post", color=ctx.p.NAVY, lw=2.6,
            label="in the dollars of the day")
    _line(ctx, ax, real_mw, color=ctx.p.RED, lw=2.6, label="in 2025 dollars")
    g.style_axis(ax)
    ax.set_ylabel("US$ an hour")
    _legend(ctx, ax)
    x, y = _last_point(ctx, real_mw)
    if x:
        _annotate_value(ctx, ax, x, y, f"US$ {y:.2f}", color=ctx.p.RED, ha="right",
                       offset=(-6, -20))
    ax.text(0.015, 0.06,
            "Unchanged at US$ 7.25 since 24 July 2009. The nominal line is\n"
            "flat by law; the real line falls because prices did not stop.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="bottom")
    g.headroom(ax, top=0.14, bottom=0.30)

    g.save(ctx.out("06-people.png"))

def plate_world(ctx) -> None:
    wb = _table(ctx, "international/worldbank.csv")
    hdi = _table(ctx, "social/hdi.csv")

    g = ctx.fig(
        "The United States in the world",
        "Share of world output, what health costs, and how long people live",
        source=("Sources: World Bank, World Development Indicators · UN "
                "Development Programme, Human Development Report 2025 "
                "composite indices"),
        # A right-hand axis in the right-hand column: its ticks and
        # its label need room the shared margin does not leave, and
        # without this they are drawn off the canvas. See Context.fig.
        right=0.955,
    )

    ax = g.next_panel("US share of world GDP, at market exchange rates")
    share = _col(ctx, wb, "us_share_world_gdp")
    xs, ys = _xy(ctx, share)
    ax.plot(xs, ys, color=ctx.p.NAVY, lw=2.8)
    ax.fill_between(xs, 0, ys, color=ctx.p.NAVY, alpha=0.10)
    g.style_axis(ax)
    g.add_recessions(ax, label=False)
    ax.set_ylabel("% of world GDP")
    ax.set_ylim(0, max(ys) * 1.25 if ys else 1)
    lo = min((v, y) for y, v in zip(ctx.YEARS, share) if v is not None)
    _annotate_value(ctx, ax, lo[1], lo[0], f"{lo[0]:.1f}% ({lo[1]})", color=ctx.p.NAVY,
                   offset=(0, -20))
    x, y = _last_point(ctx, share)
    if x:
        _annotate_value(ctx, ax, x, y, f"{y:.1f}%", color=ctx.p.NAVY, ha="right",
                       offset=(-4, 8))
    ax.text(0.015, 0.06, "Measured at market exchange rates. On a "
                         "purchasing-power basis\nthe share is markedly "
                         "lower; the two are not interchangeable.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="bottom")

    ax = g.next_panel("Health spending against life expectancy")
    health = _col(ctx, wb, "health_spending_pct_gdp")
    life = _col(ctx, wb, "life_expectancy")
    _line(ctx, ax, health, color=ctx.p.RED, lw=2.8, label="health spending, % of GDP")
    g.style_axis(ax)
    ax.set_ylabel("% of GDP", color=ctx.p.RED)
    ax.tick_params(axis="y", colors=ctx.p.RED)
    ax2 = ax.twinx()
    _line(ctx, ax2, life, color=ctx.p.NAVY, lw=2.6, ls=(0, (5, 2)),
         label="life expectancy at birth (right)")
    ax2.spines[["top", "left"]].set_visible(False)
    ax2.set_ylabel("years", color=ctx.p.NAVY)
    ax2.tick_params(colors=ctx.p.NAVY, length=0)
    ax2.grid(False)
    _twin_legend(ctx, ax, ax2, loc="lower left")
    drop = [(y, v) for y, v in zip(ctx.YEARS, life) if v is not None]
    if drop:
        worst = min(drop, key=lambda p: p[1])
        # beside the point, not under it: below sits the axis, where the
        # label lands on a tick
        _annotate_value(ctx, ax2, worst[0], worst[1], f"{worst[1]:.1f} yrs",
                       color=ctx.p.NAVY, offset=(10, -4), ha="left", fontsize=8.5)
    g.headroom(ax, top=0.22)

    ax = g.next_panel("Human Development Index")
    h = _col(ctx, hdi, "hdi")
    _line(ctx, ax, h, color=ctx.p.NAVY, lw=2.8)
    g.style_axis(ax)
    ax.set_ylabel("index, 0-1")
    x, y = _last_point(ctx, h)
    if x:
        _annotate_value(ctx, ax, x, y, f"{y:.3f}", color=ctx.p.NAVY, ha="right",
                       offset=(-4, 8))
    ax.text(0.015, 0.06, "One UNDP vintage throughout: the 2025 report "
                         "recomputes its\nown history, so mixing report "
                         "years would create steps that\nare methodology "
                         "rather than development.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="bottom")
    g.headroom(ax, top=0.16, bottom=0.40)

    ax = g.next_panel("Births per woman, and trade as a share of GDP")
    fert = _col(ctx, wb, "fertility")
    _line(ctx, ax, fert, color=ctx.p.NAVY, lw=2.8, label="total fertility rate")
    g.style_axis(ax)
    ax.set_ylabel("births per woman", color=ctx.p.NAVY)
    ax.axhline(2.1, color=ctx.p.FAINT, lw=0.9, ls=(0, (2, 2)))
    ax.text(ctx.YEARS[0] + 0.2, 2.1, "replacement, 2.1", fontsize=7.8,
            color=ctx.p.FAINT, va="bottom")
    ax2 = ax.twinx()
    _line(ctx, ax2, _col(ctx, wb, "trade_openness"), color=ctx.p.GOLD, lw=2.4, ls=(0, (5, 2)),
         label="trade (exports + imports), % of GDP (right)")
    ax2.spines[["top", "left"]].set_visible(False)
    ax2.set_ylabel("% of GDP", color=ctx.p.GOLD)
    ax2.tick_params(colors=ctx.p.GOLD, length=0)
    ax2.grid(False)
    _twin_legend(ctx, ax, ax2, loc="lower left")
    g.headroom(ax, top=0.18)

    g.save(ctx.out("07-world.png"))

def plate_demographics(ctx) -> None:
    pop = _table(ctx, "social/population.csv")
    proj = _table(ctx, "social/projections.csv")

    g = ctx.fig(
        "How many Americans",
        "Population, what changes it, and where the Census Bureau expects it to go",
        source=("Sources: Census Bureau population estimates, vintages 2019 "
                "and 2025 · Census Bureau 2023 National Population "
                "Projections, middle series"))

    # ---- the level, by vintage -------------------------------------------
    ax = g.next_panel("Resident population")
    vint = {y: ((pop.get(y) or {}).get("vintage") or "").strip() for y in ctx.YEARS}
    total = _col(ctx, pop, "population", scale=1 / 1e6)
    for tag, color, label in (("v2019", ctx.p.BLUE, "vintage 2019 estimates"),
                              ("v2025", ctx.p.NAVY, "vintage 2025 estimates")):
        seg = [v if vint.get(y) == tag else None for y, v in zip(ctx.YEARS, total)]
        _line(ctx, ax, seg, color=color, lw=2.8, label=label)
    g.style_axis(ax)
    ax.set_ylabel("million people")
    _legend(ctx, ax, loc="upper left")
    ax.axvline(2019.5, color=ctx.p.RED, lw=1.0, ls=(0, (3, 2)))
    ax.annotate(events.BREAKS["population_vintage"][1],
                xy=(2019.5, (total[ctx.YEARS.index(2019)] or 330)),
                xytext=(2006.4, (total[-1] or 342) * 0.995),
                fontsize=8.2, color=ctx.p.RED, style="italic",
                arrowprops=dict(arrowstyle="-", color=ctx.p.RED, lw=0.8,
                                shrinkA=2, shrinkB=6))
    g.headroom(ax, top=0.22)

    # ---- births and deaths -----------------------------------------------
    ax = g.next_panel("Births and deaths")
    births = _col(ctx, pop, "births", scale=1 / 1e6)
    deaths = _col(ctx, pop, "deaths", scale=1 / 1e6)
    _line(ctx, ax, births, color=ctx.p.NAVY, lw=2.8, label="births")
    _line(ctx, ax, deaths, color=ctx.p.RED, lw=2.8, label="deaths")
    xs, _ = _xy(ctx, births)
    common = [y for y in xs if deaths[ctx.YEARS.index(y)] is not None]
    ax.fill_between(common,
                    [births[ctx.YEARS.index(y)] for y in common],
                    [deaths[ctx.YEARS.index(y)] for y in common],
                    color=ctx.p.NAVY, alpha=0.10)
    g.style_axis(ax)
    ax.set_ylabel("million a year")
    _legend(ctx, ax, loc="lower left")
    ax.text(0.015, 0.95, "The gap is natural increase. Census years run "
                         "1 July to 30 June,\nand components before 2010 are "
                         "not published, so they are left empty.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="top")
    g.headroom(ax, top=0.30)

    # ---- migration --------------------------------------------------------
    ax = g.next_panel("Net international migration")
    mig = _col(ctx, pop, "net_migration", scale=1 / 1e6)
    bars = ax.bar(ctx.YEARS, _nan(ctx, mig), color=ctx.p.TEAL, width=0.68)
    g.style_axis(ax)
    ax.set_ylabel("million a year")
    peak = max(((v, y) for y, v in zip(ctx.YEARS, mig) if v is not None),
               default=(None, None))
    if peak[0]:
        _annotate_value(ctx, ax, peak[1], peak[0], f"{peak[0]:.2f}M", color=ctx.p.TEAL)
    x, y = _last_point(ctx, mig)
    if x:
        _annotate_value(ctx, ax, x, y, f"{y:.2f}M", color=ctx.p.TEAL)
    g.headroom(ax, top=0.26)
    ax.text(0.015, 0.95, "Not published before 2010 in these vintages.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="top")

    # ---- projections ------------------------------------------------------
    ax = g.next_panel("Projected to 2100, Census Bureau middle series")
    pyears = sorted(proj)
    pvals = [float((proj[y].get("population") or 0)) / 1e6 for y in pyears]
    ax.plot(pyears, pvals, color=ctx.p.NAVY, lw=2.8)
    ax.fill_between(pyears, 0, pvals, color=ctx.p.NAVY, alpha=0.08)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(ctx.p.spine)
    ax.tick_params(length=0)
    ax.grid(axis="y", color=ctx.p.grid, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_ylabel("million people")
    ax.set_ylim(min(pvals) * 0.9, max(pvals) * 1.08)
    top = max(zip(pvals, pyears))
    ax.axvline(top[1], color=ctx.p.RED, lw=1.0, ls=(0, (3, 2)))
    _annotate_value(ctx, ax, top[1], top[0], f"peak of {top[0]:.0f}M in {top[1]}",
                   color=ctx.p.RED, offset=(0, 10))
    ax.text(0.015, 0.06, "A projection, not a measurement: it is one "
                         "vintage's middle\nassumption, and the migration "
                         "assumption moves the peak\nby decades.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="bottom")

    g.save(ctx.out("08-demographics.png"))

def plate_mortality(ctx) -> None:
    m = _table(ctx, "social/mortality.csv")

    g = ctx.fig(
        "Deaths",
        "All causes, COVID-19 and the respiratory diseases — on two definitions",
        source=("Sources: CDC WONDER, Underlying Cause of Death 1999-2020 "
                "(final) · CDC provisional COVID-19 death counts "
                "(deaths involving a condition). The two count differently "
                "and are never joined."))

    # ---- all cause --------------------------------------------------------
    ax = g.next_panel("Deaths from all causes")
    total = _col(ctx, m, "total_deaths", scale=1 / 1e6)
    bars = ax.bar(ctx.YEARS, _nan(ctx, total), color=ctx.p.NAVY, width=0.68)
    for y, bar in zip(ctx.YEARS, bars):
        if ((m.get(y) or {}).get("total_vintage") or "") == "provisional":
            bar.set_color(ctx.p.BLUE)
    _hatch_partial(ctx, ax, bars, m, "total_deaths", 1e9)
    g.style_axis(ax)
    ax.set_ylabel("million deaths")
    ax.set_ylim(2.0, max(v for v in total if v is not None) * 1.10)
    pre = total[ctx.YEARS.index(2019)]
    for y in (2020, 2021):
        v = total[ctx.YEARS.index(y)]
        if v and pre:
            _annotate_value(ctx, ax, y, v, f"+{(v - pre) / pre * 100:.0f}% vs 2019",
                           color=ctx.p.RED, fontsize=8.2)
    ax.text(0.015, 0.95,
            "Final counts to 2020, provisional after. The two agree to 0.2%,\n"
            "so this one series is continuous. 2026 is a part year.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="top")
    g.mark_partial(ax, 2021, "2026: a part year, not a fall in deaths")

    # ---- covid ------------------------------------------------------------
    ax = g.next_panel("Deaths involving COVID-19")
    covid = _col(ctx, m, "covid_involved", scale=1 / 1000)
    bars = ax.bar(ctx.YEARS, _nan(ctx, covid), color=ctx.p.RED, width=0.68)
    g.style_axis(ax)
    ax.set_ylabel("thousand deaths")
    for y, v in zip(ctx.YEARS, covid):
        if v is not None and v > 100:
            _annotate_value(ctx, ax, y, v, f"{v:,.0f}k", color=ctx.p.RED, fontsize=8.5)
    g.headroom(ax, top=0.20)
    ax.text(0.015, 0.95,
            "Counted as deaths that INVOLVED COVID-19. On the\n"
            "underlying-cause definition 2020 is 350,831 rather\n"
            "than 385,676 — 10% fewer. Years before 2020 are empty\n"
            "because the disease did not exist, which is not a zero.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="top", ha="left")
    g.mark_partial(ax, 2021, "2026: a part year")

    # ---- influenza, on two definitions ------------------------------------
    for panel, key, name, color in (
            (2, "influenza", "Influenza", ctx.p.GOLD),
            (3, "pneumonia", "Pneumonia", ctx.p.TEAL)):
        ax = g.next_panel(f"{name}: the same disease, two measures")
        under = _col(ctx, m, f"{key}_underlying", scale=1 / 1000)
        invol = _col(ctx, m, f"{key}_involved", scale=1 / 1000)
        _line(ctx, ax, under, color=color, lw=2.8,
             label="underlying cause (CDC WONDER, to 2020)")
        _line(ctx, ax, invol, color=ctx.p.RED, lw=2.8,
             label="deaths involving it (provisional, from 2020)")
        g.style_axis(ax)
        ax.set_ylabel("thousand deaths")
        _legend(ctx, ax, loc="upper left")
        both = [(y, u, i) for y, u, i in zip(ctx.YEARS, under, invol)
                if u is not None and i is not None]
        if both:
            y0, u0, i0 = both[0]
            ax.annotate(f"{y0}: {u0 * 1000:,.0f} against {i0 * 1000:,.0f} — "
                        f"{(i0 / u0 - 1) * 100:+.0f}%.\nA change of definition, "
                        f"not a change in the disease.",
                        xy=(y0, i0), xytext=(2007.0, max(
                            v for v in invol if v is not None) * 0.62),
                        fontsize=8.2, color=ctx.p.RED, style="italic",
                        arrowprops=dict(arrowstyle="-", color=ctx.p.RED, lw=0.8,
                                        shrinkA=2, shrinkB=6))
        g.headroom(ax, top=0.26)
        if key == "influenza":
            trough = min(((v, y) for y, v in zip(ctx.YEARS, invol)
                          if v is not None), default=(None, None))
            if trough[0]:
                _annotate_value(ctx, ax, trough[1], trough[0],
                               f"{trough[0] * 1000:,.0f}", color=ctx.p.RED,
                               offset=(0, -18), fontsize=8.2)
        g.mark_partial(ax, 2021, "2026: a part year")

    g.save(ctx.out("09-mortality.png"))

def plate_violence(ctx) -> None:
    v = _table(ctx, "social/violence.csv")

    g = ctx.fig(
        "Violent and accidental death",
        "Homicide, firearms, suicide and overdose",
        source=("Sources: CDC WONDER, Underlying Cause of Death 1999-2020 "
                "(final) · CDC provisional injury counts and VSRR "
                "provisional overdose counts. The seam was measured: "
                "the two agree to about 1%."),
        # A right-hand axis in the right-hand column: its ticks and
        # its label need room the shared margin does not leave, and
        # without this they are drawn off the canvas. See Context.fig.
        right=0.955,
    )

    # ---- homicide ---------------------------------------------------------
    ax = g.next_panel("Homicides, and the rate per 100,000")
    hom = _col(ctx, v, "homicides", scale=1 / 1000)
    rate = _col(ctx, v, "homicide_rate")
    bars = ax.bar(ctx.YEARS, _nan(ctx, hom), color=ctx.p.NAVY, width=0.68, label="homicides")
    g.style_axis(ax)
    ax.set_ylabel("thousand")
    ax2 = ax.twinx()
    _line(ctx, ax2, rate, color=ctx.p.RED, lw=2.6, label="rate per 100k (right)")
    ax2.spines[["top", "left"]].set_visible(False)
    ax2.set_ylabel("per 100k", color=ctx.p.RED)
    ax2.tick_params(colors=ctx.p.RED, length=0)
    ax2.grid(False)
    peak = max(((x, y2) for y2, x in zip(ctx.YEARS, hom) if x is not None),
               default=(None, None))
    if peak[0]:
        _annotate_value(ctx, ax, peak[1], peak[0], f"{peak[0] * 1000:,.0f}",
                       color=ctx.p.NAVY, fontsize=8.5)
    _twin_legend(ctx, ax, ax2, loc="upper left")
    g.headroom(ax, top=0.22)

    # ---- firearms ---------------------------------------------------------
    ax = g.next_panel("Firearm deaths, and the homicides among them")
    fa = _col(ctx, v, "firearm_deaths", scale=1 / 1000)
    fah = _col(ctx, v, "firearm_homicides", scale=1 / 1000)
    _line(ctx, ax, fa, color=ctx.p.NAVY, lw=2.8, label="all firearm deaths")
    _line(ctx, ax, fah, color=ctx.p.RED, lw=2.6,
         label=_subset("firearm homicides", "all firearm deaths"))
    xs, _ = _xy(ctx, fa)
    common = [y for y in xs if fah[ctx.YEARS.index(y)] is not None]
    ax.fill_between(common, [fah[ctx.YEARS.index(y)] for y in common],
                    [fa[ctx.YEARS.index(y)] for y in common],
                    color=ctx.p.NAVY, alpha=0.10)
    g.style_axis(ax)
    ax.set_ylabel("thousand deaths")
    _legend(ctx, ax, loc="upper left")
    # the title names a relationship, so the relationship is drawn
    ax2 = ax.twinx()
    _share_panel(ctx, ax2, ctx.YEARS, fah, fa, color=ctx.p.TEAL,
                label="homicides as % of firearm deaths")
    ax2.spines[["top", "left"]].set_visible(False)
    ax2.set_ylabel("% of firearm deaths", color=ctx.p.TEAL)
    ax2.tick_params(colors=ctx.p.TEAL, length=0)
    ax2.set_ylim(0, 100)
    ax2.grid(False)
    ax.text(0.015, 0.06, "Most firearm deaths are suicides, not homicides.\n"
                         "The shaded area is the difference.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="bottom")
    g.headroom(ax, top=0.26)

    # ---- suicide and police intervention ----------------------------------
    ax = g.next_panel("Suicides, and deaths by police intervention")
    sui = _col(ctx, v, "suicides", scale=1 / 1000)
    _line(ctx, ax, sui, color=ctx.p.NAVY, lw=2.8, label="suicides, all means")
    g.style_axis(ax)
    ax.set_ylabel("thousand deaths")
    ax2 = ax.twinx()
    pol = _col(ctx, v, "police_killings")
    xs, ys = _xy(ctx, pol)
    ax2.bar(xs, ys, color=ctx.p.RED, width=0.62, alpha=0.75,
            label="legal intervention, Y35 (right)")
    ax2.spines[["top", "left"]].set_visible(False)
    ax2.set_ylabel("deaths", color=ctx.p.RED)
    ax2.tick_params(colors=ctx.p.RED, length=0)
    ax2.grid(False)
    _twin_legend(ctx, ax, ax2, loc="upper left")
    ax.text(0.015, 0.06,
            "The Y35 count is a known undercount and stops at 2020: the code\n"
            "follows whoever certifies the death, and research puts roughly\n"
            "half of these deaths under ordinary homicide instead. It is\n"
            "drawn because it is the official series, not because it is right.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="bottom")
    g.headroom(ax, top=0.24, bottom=0.46)

    # ---- overdose ---------------------------------------------------------
    ax = g.next_panel("Overdose deaths, and the synthetic opioids among them")
    od = _col(ctx, v, "overdoses", scale=1 / 1000)
    syn = _col(ctx, v, "synthetic_opioid_overdoses", scale=1 / 1000)
    _line(ctx, ax, od, color=ctx.p.NAVY, lw=2.8, label="all drug overdose deaths")
    _line(ctx, ax, syn, color=ctx.p.RED, lw=2.6,
         label=_subset("synthetic opioids, mainly fentanyl",
                      "all overdose deaths"))
    g.style_axis(ax)
    ax.set_ylabel("thousand deaths")
    _legend(ctx, ax, loc="upper left")
    peak = max(((x, y2) for y2, x in zip(ctx.YEARS, od) if x is not None),
               default=(None, None))
    if peak[0]:
        _annotate_value(ctx, ax, peak[1], peak[0], f"{peak[0] * 1000:,.0f} ({peak[1]})",
                       color=ctx.p.NAVY, fontsize=8.5)
    x, y = _last_point(ctx, od)
    if x:
        _annotate_value(ctx, ax, x, y, f"{y * 1000:,.0f}", color=ctx.p.NAVY, ha="right",
                       offset=(-4, 8), fontsize=8.5)
    g.headroom(ax, top=0.24)

    g.save(ctx.out("10-violence.png"))

def plate_credit(ctx) -> None:
    hh = _table(ctx, "credit/household_debt.csv")
    acc = _table(ctx, "credit/credit_access.csv")
    dq = _table(ctx, "credit/delinquency.csv")
    rates = _table(ctx, "credit/rates.csv")
    ff = _table(ctx, "macro/fed_funds.csv")

    g = ctx.fig(
        "What households owe",
        "Household debt, the credit available to draw on, and what it costs",
        source=("Sources: Federal Reserve Bank of New York, Quarterly Report "
                "on Household Debt and Credit (Consumer Credit Panel) · "
                "Federal Reserve Board G.19 terms of credit"))

    # ---- the stack --------------------------------------------------------
    ax = g.next_panel("Household debt by type, at year end")
    parts = (("mortgage", "Mortgage", ctx.p.NAVY), ("heloc", "Home equity", ctx.p.BLUE),
             ("auto", "Auto", ctx.p.TEAL), ("credit_card", "Credit card", ctx.p.RED),
             ("student", "Student", ctx.p.GOLD), ("other", "Other", ctx.p.PURPLE))
    bottom = np.zeros(len(ctx.YEARS))
    for name, label, color in parts:
        vals = _nan(ctx, _col(ctx, hh, name))
        ax.bar(ctx.YEARS, vals, bottom=bottom, color=color, width=0.68, label=label)
        bottom = bottom + np.nan_to_num(vals)
    g.style_axis(ax)
    ax.set_ylabel("US$ tn")
    _legend(ctx, ax, loc="upper left", ncol=2)
    total = _col(ctx, hh, "total")
    x, y = _last_point(ctx, total)
    if x:
        _annotate_value(ctx, ax, x, y, f"US$ {y:.1f}tn", color=ctx.p.INK, ha="right",
                       offset=(-4, 6))
    g.headroom(ax, top=0.26)
    g.mark_partial(ax, 2021, "2026: through Q2, not a year end")

    # ---- availability -----------------------------------------------------
    ax = g.next_panel("Credit card limits, balances and unused credit")
    limit = _col(ctx, acc, "cc_limit")
    bal = _col(ctx, acc, "cc_balance")
    _line(ctx, ax, limit, color=ctx.p.NAVY, lw=2.8, label="total credit limit")
    _line(ctx, ax, bal, color=ctx.p.RED, lw=2.6,
         label=_subset("balances drawn", "the total limit"))
    xs, _ = _xy(ctx, limit)
    common = [y for y in xs if bal[ctx.YEARS.index(y)] is not None]
    ax.fill_between(common, [bal[ctx.YEARS.index(y)] for y in common],
                    [limit[ctx.YEARS.index(y)] for y in common],
                    color=ctx.p.NAVY, alpha=0.10, label="unused credit")
    g.style_axis(ax)
    ax.set_ylabel("US$ tn")
    _legend(ctx, ax, loc="upper left")
    ax2 = ax.twinx()
    _line(ctx, ax2, _col(ctx, acc, "cc_utilisation"), color=ctx.p.TEAL, lw=2.2, ls=(0, (5, 2)))
    ax2.spines[["top", "left"]].set_visible(False)
    ax2.set_ylabel("balances as % of limit", color=ctx.p.TEAL)
    ax2.tick_params(colors=ctx.p.TEAL, length=0)
    ax2.set_ylim(0, 60)
    ax2.grid(False)
    g.headroom(ax, top=0.24)

    # ---- delinquency ------------------------------------------------------
    ax = g.next_panel("Share of balances 90+ days delinquent")
    for name, label, color in (("credit_card", "Credit card", ctx.p.RED),
                               ("student", "Student", ctx.p.GOLD),
                               ("auto", "Auto", ctx.p.TEAL),
                               ("mortgage", "Mortgage", ctx.p.NAVY)):
        _line(ctx, ax, _col(ctx, dq, name), color=color, lw=2.4, label=label)
    g.style_axis(ax)
    ax.set_ylabel("% of balances")
    _legend(ctx, ax, loc="upper left", ncol=2)
    stu = _col(ctx, dq, "student")
    ax.annotate(events.BREAKS["student_delinquency"][1],
                xy=(2025, stu[ctx.YEARS.index(2025)] or 9.2),
                xytext=(2010.4, (max(v for v in stu if v is not None)) * 0.86),
                fontsize=8.2, color=ctx.p.RED, style="italic",
                arrowprops=dict(arrowstyle="-", color=ctx.p.RED, lw=0.8,
                                shrinkA=2, shrinkB=6))
    g.headroom(ax, top=0.28)

    # ---- the price --------------------------------------------------------
    ax = g.next_panel("What borrowing costs, against the policy rate")
    _line(ctx, ax, _col(ctx, rates, "cc_apr_all"), color=ctx.p.RED, lw=2.8,
         label="credit card APR, all accounts")
    _line(ctx, ax, _col(ctx, rates, "auto_60m"), color=ctx.p.TEAL, lw=2.4,
         label="60-month new car loan")
    target = _col(ctx, ff, "target_eop")
    hi = _col(ctx, ff, "target_hi")
    mid = [t if h is None else (t + h) / 2 for t, h in zip(target, hi)]
    _line(ctx, ax, mid, color=ctx.p.NAVY, lw=2.4, ls=(0, (5, 2)),
         label="FOMC target at year end")
    g.style_axis(ax)
    ax.set_ylabel("% a year")
    _legend(ctx, ax, loc="upper left", ncol=2)
    x, y = _last_point(ctx, _col(ctx, rates, "cc_apr_all"))
    if x:
        _annotate_value(ctx, ax, x, y, f"{y:.1f}%", color=ctx.p.RED, ha="right",
                       offset=(-4, 6))
    ax.text(0.985, 0.06,
            "The policy rate returned to roughly its 2006 level.\n"
            "The credit card rate did not.",
            transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED, style="italic",
            va="bottom", ha="right")
    g.headroom(ax, top=0.26)

    g.save(ctx.out("11-credit.png"))


# The plates, in the order the page lists them.
PLATES = (

    ("plate_economy", plate_economy),

    ("plate_fiscal", plate_fiscal),

    ("plate_spending", plate_spending),

    ("plate_trade", plate_trade),

    ("plate_markets", plate_markets),

    ("plate_people", plate_people),

    ("plate_world", plate_world),

    ("plate_demographics", plate_demographics),

    ("plate_mortality", plate_mortality),

    ("plate_violence", plate_violence),

    ("plate_credit", plate_credit),

)
