"""The spain plates.

Each builder draws one plate from this country's committed CSVs. The plates
are declared in the declarative shape — id, slug, title, subtitle, alt in
PLATES — so the title and the alt text are reviewable without reading the
drawing code; core.render creates the figure and the builder only fills its
panels.

Twelve plates, on the shared spine. The migration plate is the atlas's
first full treatment of the twelfth chapter and carries the hardest seam
in this country's data: Eurostat's immigration series changes methodology
at 2021 (EM → EMCR), which the INE publishes on both — the plate draws the
two segments and marks the seam rather than joining them. See
DATA_NOTES.md.
"""
from __future__ import annotations

import numpy as np


# ------------------------------------------------------------ small helpers
def _yr(ctx, rel: str, col: str, since: int = 0):
    """(years, values) from a calendar-year CSV, blanks dropped."""
    t = ctx.table(rel)
    if not t or col not in t:
        return [], []
    yrs, vals = ctx.series(t, col)
    keep = [(y, v) for y, v in zip(yrs, vals) if y >= since]
    return [y for y, _ in keep], [v for _, v in keep]


def _cause(ctx, name: str):
    """(years, deaths) for one cause out of the long-format ECM file."""
    t = ctx.table("social/causes_of_death.csv")
    if not t:
        return [], []
    out = [(int(y), float(v)) for y, c, v in zip(t["year"], t["cause"],
                                                 t["deaths"])
           if c == name and v == v]
    out.sort()
    return [y for y, _ in out], [v for _, v in out]


W0 = 2006   # the shared plate window opens here


def plate_economy(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("GDP at current prices (€ billion)")
    ey, ev = _yr(ctx, "macro/gdp.csv", "nominal_eurbn")
    ny, nv = _yr(ctx, "macro/gdp.csv", "nominal_eurbn_ine")
    ctx.bars(ax, ey, ev, lambda v: p.NAVY)
    ig.add_recessions(ax, label=False)
    ctx.line(ax, ny, nv, p.GUALDA, lw=1.6, marker="", dashed_partial=False,
             label="INE's own release (CNTR)")
    for y, v in zip(ey, ev):
        if y in (2008, 2013, 2024):
            ax.annotate(f"{v:,.0f}", (y, v), textcoords="offset points",
                        xytext=(0, 5), ha="center", fontsize=8.8,
                        fontweight="bold", color=p.NAVY)
    ax.legend(loc="upper left", fontsize=8.4)
    ax.text(0.5, -0.125, "the two read the same to the decimal today; both are "
            "drawn because a revision can reopen the seam",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ig.mark_partial(ax, 2026, "n/a")
    ax.set_ylim(0, 1950)

    ax = ig.next_panel("Real GDP growth (% per year)")
    gy, gv = _yr(ctx, "macro/gdp.csv", "real_growth")
    ax.axhline(0, color=p.MUTED, lw=1.0)
    ig.add_recessions(ax, label=False)
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.ROJO)
    for y, v in zip(gy, gv):
        if v < -2 or v > 5.4 or y == 2025:
            va = "bottom" if v >= 0 else "top"
            off = 4 if v >= 0 else -6
            if y == 2020:   # the band caption owns the space below the bar
                ax.annotate(f"{v:+.1f}", (y, v), textcoords="offset points",
                            xytext=(14, 12), ha="left", va="center",
                            fontsize=8.8, fontweight="bold", color=p.ROJO)
                continue
            ax.annotate(f"{v:+.1f}", (y, v), textcoords="offset points",
                        xytext=(0, off), ha="center", va=va, fontsize=8.8,
                        fontweight="bold",
                        color=p.GREEN_D if v >= 0 else p.ROJO)
    ig.mark_partial(ax, 2026, "n/a")
    ax.set_ylim(-12.5, 8.5)

    ax = ig.next_panel("GDP per person (US$, current — World Bank)")
    cy, cv = _yr(ctx, "macro/gdp.csv", "gdp_per_capita_usd")
    ctx.line(ax, cy, cv, p.BLUE)
    ctx.endlabel(ax, cy, cv, p.BLUE, lambda v: f"US$ {v:,.0f}", dy=10)
    ig.add_event(ax, 2015.0, "euro slump, not a recession", dy=0.13)
    ax.text(0.5, -0.125, "current US$: the dips are the exchange rate as "
            "much as the economy", transform=ax.transAxes, ha="center",
            fontsize=7.6, color=p.FAINT, style="italic")
    ax.set_ylim(22000, 44000)

    ax = ig.next_panel("Inflation — consumer prices (% per year) vs the "
                       "ECB's 2% aim")
    iy, iv = _yr(ctx, "macro/inflation.csv", "ipc")
    hy, hv = _yr(ctx, "macro/inflation.csv", "hicp")
    ax.axhline(2.0, color=p.BLUE, lw=1.3, ls="--", label="ECB aim: 2%")
    ax.axhline(0, color=p.MUTED, lw=0.9)
    ctx.line(ax, hy, hv, p.FAINT, lw=1.8, dashed_partial=False,
             label="Harmonised HICP (Eurostat)")
    ctx.line(ax, iy, iv, p.ROJO, label="Spanish IPC (INE)")
    for y, v in zip(iy, iv):
        if v > 3.9 or y == 2025:
            ax.annotate(f"{v:.1f}", (y, v), textcoords="offset points",
                        xytext=(0, 6), ha="center", fontsize=8.8,
                        fontweight="bold", color=p.ROJO)
    ax.legend(loc="upper left", fontsize=8.4)
    ig.add_recessions(ax, inside=True)
    ax.text(0.5, -0.125, "different baskets, two series, never spliced; the "
            "IPC is INE's linked index, published today in base 2025",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(-1.6, 9.6)

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_fiscal(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("What the state takes and what it spends (% of GDP)")
    ry, rv = _yr(ctx, "fiscal/revenue.csv", "revenue")
    ey, ev = _yr(ctx, "fiscal/revenue.csv", "expenditure")
    ctx.line(ax, ey, ev, p.ROJO, label="Total expenditure")
    ctx.line(ax, ry, rv, p.NAVY, label="Total revenue")
    ax.fill_between(ry, rv, ev, color=p.ROJO, alpha=0.09, zorder=1)
    ax.legend(loc="upper right", fontsize=8.6)
    ax.text(2010.5, 47.5, "the gap is the deficit",
            fontsize=8.2, color=p.MUTED, style="italic", ha="center")
    ig.add_recessions(ax, label=False)
    ax.set_ylim(32, 56)

    ax = ig.next_panel("Net lending (+) or borrowing (−), general government "
                       "(% of GDP)")
    dy, dv = _yr(ctx, "fiscal/deficit.csv", "deficit")
    py, pv = _yr(ctx, "fiscal/deficit.csv", "primary")
    ax.axhline(0, color=p.MUTED, lw=1.0)
    ax.axhline(-3.0, color=p.BLUE, lw=1.2, ls="--",
               label="Maastricht 3% limit")
    ctx.bars(ax, dy, dv, lambda v: p.GREEN if v >= 0 else p.ROJO)
    ctx.line(ax, py, pv, p.GUALDA, lw=1.8, marker="",
             label="primary balance (deficit + interest, computed)")
    for y, v in zip(dy, dv):
        if y in (2009, 2012, 2020, 2025):
            ax.annotate(f"{v:.1f}", (y, v), textcoords="offset points",
                        xytext=(0, -5), ha="center", va="top", fontsize=8.6,
                        fontweight="bold", color=p.ROJO)
    ax.annotate("2012 includes the bank bailout;\nwithout it: about −7%",
                xy=(2012, -11.5), xytext=(2014.3, -10.4), fontsize=8.0,
                color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.legend(loc="upper right", fontsize=8.2)
    ig.mark_partial(ax, 2026, "n/a")
    ax.set_ylim(-13.5, 4.4)

    ax = ig.next_panel("Gross public debt — Maastricht (% of GDP)")
    gy, gv = _yr(ctx, "fiscal/debt.csv", "gross_pct_gdp")
    ctx.line(ax, gy, gv, p.ROJO)
    ax.fill_between(gy, 0, gv, color=p.ROJO, alpha=0.07, zorder=1)
    ax.axhline(60.0, color=p.BLUE, lw=1.2, ls="--")
    ax.text(2026.3, 61.5, "Maastricht 60% limit", fontsize=8.2,
            color=p.BLUE, style="italic", va="bottom", ha="right")
    ctx.endlabel(ax, gy, gv, p.ROJO, lambda v: f"{v:.1f}%", dy=10)
    ax.annotate("69.5% to 100.0% in two years:\nthe bailout and the slump",
                xy=(2013, 100.0), xytext=(2006.6, 108), fontsize=8.0,
                color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.text(0.5, -0.125, "consolidated, all levels of government — the "
            "Tesoro's state-only figure is a smaller, different number",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ig.mark_partial(ax, 2026, "n/a")
    ax.set_ylim(0, 128)

    ax = ig.next_panel("The interest bill vs the tax take (% of GDP)")
    iy, iv = _yr(ctx, "fiscal/deficit.csv", "interest")
    ty, tv = _yr(ctx, "fiscal/tax_burden.csv", "estat")
    ctx.line(ax, ty, tv, p.TEAL, label="Taxes and social contributions "
             "(Eurostat harmonised)")
    ctx.line(ax, iy, iv, p.GUALDA, label="Interest paid on the debt")
    ctx.endlabel(ax, iy, iv, p.GUALDA, lambda v: f"{v:.1f}%", dy=12)
    ax.legend(loc="center right", fontsize=8.4)
    ax.annotate("the debt tripled while the interest\nbill halved — rates "
                "fell faster", xy=(2016, 2.2), xytext=(2006.4, 22),
                fontsize=8.0, color=p.MUTED, style="italic", va="top",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ig.mark_partial(ax, 2026, "n/a")
    ax.set_ylim(0, 44)

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_spending(ctx, ig) -> None:
    p = ctx.p

    ORDER = ["social_protection", "health", "general_services", "education",
             "economic_affairs", "defence_order", "other"]
    LABEL = {"social_protection": "Social protection", "health": "Health",
             "general_services": "General public services (incl. debt interest)",
             "education": "Education", "economic_affairs": "Economic affairs",
             "defence_order": "Defence & public order", "other": "Other functions"}
    COLORS = {"social_protection": p.NAVY, "health": p.TEAL,
              "general_services": p.ROJO, "education": p.BLUE,
              "economic_affairs": p.GUALDA, "defence_order": p.PURPLE,
              "other": "#B9BDC7"}

    ax = ig.next_panel("Public spending by function (% of GDP, COFOG)")
    spend = ctx.table("fiscal/spending_by_function.csv")
    yrs = [y for y, v in zip(spend["year"], spend["social_protection"])
           if v == v]
    stack = [[v for y, v in zip(spend["year"], spend[c]) if y in yrs]
             for c in ORDER]
    ax.stackplot(yrs, *stack, labels=[LABEL[c] for c in ORDER],
                 colors=[COLORS[c] for c in ORDER], alpha=0.92, lw=0)
    ax.legend(loc="upper left", fontsize=8.0, ncol=2)
    ig.add_event(ax, 2020.25, "COVID-19", dy=0.42)
    ax.set_ylim(0, 64)

    ax = ig.next_panel("Social protection vs everything else (% of GDP)")
    sy, sv = _yr(ctx, "fiscal/spending_by_function.csv", "social_protection")
    ty, tv = _yr(ctx, "fiscal/spending_by_function.csv", "total")
    rest = [t - s for s, t in zip(sv, tv)]
    ax.plot(sy, sv, color=p.NAVY, lw=2.6, label="Social protection alone")
    ax.fill_between(sy, 0, sv, color=p.NAVY, alpha=0.10)
    ax.plot(ty, rest, color=p.TEAL, lw=2.6, label="All other functions")
    ax.fill_between(ty, 0, rest, color=p.TEAL, alpha=0.10)
    ax.legend(loc="lower left", fontsize=8.6)
    ax.annotate("pensions are most of it; the 2012-13 peak is unemployment",
                xy=(2013, 18.5), xytext=(2006.5, 40.0), fontsize=8.0,
                color=p.MUTED, style="italic", va="top",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(0, 42)

    ax = ig.next_panel("Investment rate — whole economy (% of GDP)")
    gy, gv = _yr(ctx, "fiscal/investment.csv", "gfcf_pct_gdp")
    ctx.line(ax, gy, gv, p.BLUE)
    ctx.endlabel(ax, gy, gv, p.BLUE, lambda v: f"{v:.1f}%", dy=10)
    peak = max(zip(gy, gv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% — the brick years", peak,
                textcoords="offset points", xytext=(6, 10), ha="left",
                fontsize=8.8, fontweight="bold", color=p.BLUE)
    ig.add_recessions(ax, label=False)
    ax.set_ylim(15, 35)

    ax = ig.next_panel("Public investment — general government (% of GDP)")
    py, pv = _yr(ctx, "fiscal/investment.csv", "gov_gfcf_pct_gdp")
    ctx.line(ax, py, pv, p.GREEN_D)
    ax.fill_between(py, 0, pv, color=p.GREEN_D, alpha=0.10)
    ctx.endlabel(ax, py, pv, p.GREEN_D, lambda v: f"{v:.1f}%", dy=10)
    ax.annotate("the austerity years took it\nto half its pre-crisis level",
                xy=(2016, 2.1), xytext=(2007.0, 1.3), fontsize=8.0,
                color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(0, 5.6)

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_trade(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("Exports vs imports, goods and services (€ billion)")
    ey, ev = _yr(ctx, "trade/trade.csv", "exports_eurbn")
    iy, iv = _yr(ctx, "trade/trade.csv", "imports_eurbn")
    ctx.line(ax, ey, ev, p.GREEN_D, label="Exports")
    ctx.line(ax, iy, iv, p.BLUE, label="Imports")
    ctx.endlabel(ax, ey, ev, p.GREEN_D, lambda v: f"€{v:,.0f}bn", dy=10)
    ctx.endlabel(ax, iy, iv, p.BLUE, lambda v: f"€{v:,.0f}bn", dy=-26)
    ax.legend(loc="upper left", fontsize=8.6)
    ig.add_recessions(ax, label=False)
    ax.text(0.5, -0.125, "national-accounts basis, services included — the "
            "customs goods-only figures are a different universe (pending)",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(220, 700)

    ax = ig.next_panel("The external balance (€ billion, goods and services)")
    ey2, ev2 = ey, ev
    bal = [(y, e - i) for y, e, i in zip(ey2, ev2, iv)]
    by, bv = [y for y, _ in bal], [v for _, v in bal]
    ax.axhline(0, color=p.MUTED, lw=1.0)
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ROJO)
    cross = next(y for y, v in bal if v > 0)
    ax.annotate(f"surplus since {cross:.0f} — tourism\nand the post-crisis "
                "export turn", xy=(2014, 30), xytext=(2007.0, 52),
                fontsize=8.0, color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    worst = min(bal, key=lambda t: t[1])
    ax.annotate(f"{worst[1]:+,.0f}", worst, textcoords="offset points",
                xytext=(0, -6), ha="center", va="top", fontsize=8.8,
                fontweight="bold", color=p.ROJO)
    ax.set_ylim(-80, 100)

    ax = ig.next_panel("Openness — exports + imports (% of GDP, World Bank)")
    oy, ov = _yr(ctx, "international/openness.csv", "trade_pct_gdp")
    ctx.line(ax, oy, ov, p.TEAL)
    ctx.endlabel(ax, oy, ov, p.TEAL, lambda v: f"{v:.0f}%", dy=10)
    ax.annotate("the least open large economy in\nwestern Europe, opening",
                xy=(2019, 66.4), xytext=(2006.6, 74), fontsize=8.0,
                color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(40, 85)

    ax = ig.next_panel("Who Spain trades with — partners and products")
    ctx.pending(ax)
    ax.text(0.5, 0.36, "customs values by partner and product: DataComex is "
            "the source,\nstaged for a later edition (see SOURCES.yaml, "
            "pending)", transform=ax.transAxes, ha="center", fontsize=8.2,
            color=p.FAINT, style="italic")

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("The policy rate is set in Frankfurt (%)")
    dy, dv = _yr(ctx, "markets/policy_rate.csv", "dfr")
    my, mv = _yr(ctx, "markets/policy_rate.csv", "mro")
    ax.axhline(0, color=p.MUTED, lw=1.0)
    ax.axhspan(-0.6, 0, color=p.BAND, zorder=0)
    ctx.line(ax, dy, dv, p.NAVY, label="Deposit facility rate (year-end)")
    ctx.line(ax, my, mv, p.FAINT, lw=1.8, marker="", dashed_partial=False,
             label="Main refinancing rate (from Oct 2008)")
    ax.legend(loc="upper left", fontsize=8.4)
    ax.text(2015.7, -0.88, "eight years below zero", fontsize=8.4,
            color=p.MUTED, style="italic", va="top")
    ig.add_recessions(ax, label=False)
    ax.set_ylim(-1.1, 5.4)

    ax = ig.next_panel("The 10-year benchmark yield (%, annual average)")
    ty, tv = _yr(ctx, "markets/yield_10y.csv", "yield_10y")
    ctx.line(ax, ty, tv, p.ROJO)
    ax.fill_between(ty, 0, tv, color=p.ROJO, alpha=0.07)
    ctx.endlabel(ax, ty, tv, p.ROJO, lambda v: f"{v:.2f}%", dy=10)
    peak = max(zip(ty, tv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.2f}% in {peak[0]:.0f}", peak,
                textcoords="offset points", xytext=(-14, 10), ha="right",
                fontsize=9, fontweight="bold", color=p.ROJO)
    ig.add_event(ax, 2012.55, "“whatever it takes”", dy=0.88)
    ax.set_ylim(0, 6.8)

    ax = ig.next_panel("US dollars per euro (annual average) — falling = "
                       "a weaker euro")
    fy, fv = _yr(ctx, "markets/eurusd.csv", "avg")
    ctx.line(ax, fy, fv, p.TEAL)
    ctx.endlabel(ax, fy, fv, p.TEAL, lambda v: f"{v:.2f}", dy=10)
    for y, v in zip(fy, fv):
        if y in (2008, 2022):
            ax.annotate(f"{v:.2f}", (y, v), textcoords="offset points",
                        xytext=(0, -15), ha="center", fontsize=8.6,
                        color=p.MUTED)
    ig.mark_partial(ax, 2026, "to Oct")
    ax.set_ylim(0.95, 1.5)

    ax = ig.next_panel("IBEX 35 — annual close (price index)")
    by, bv = _yr(ctx, "markets/ibex.csv", "close")
    ctx.line(ax, by, bv, p.NAVY)
    ax.fill_between(by, 0, bv, color=p.NAVY, alpha=0.06)
    peak = max(((y, v) for y, v in zip(by, bv) if y <= ctx.LAST_FULL_YEAR),
               key=lambda t: t[1])
    ax.annotate(f"{peak[1]:,.0f} ({peak[0]:.0f})", peak,
                textcoords="offset points", xytext=(0, 10), ha="center",
                fontsize=9, fontweight="bold", color=p.NAVY)
    latest = max(zip(by, bv), key=lambda t: t[0])
    ax.annotate(f"{latest[1]:,.0f} — latest close,\nnot a year-end",
                xy=latest, xytext=(2018.6, 17600), fontsize=8.0,
                color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.text(0.5, -0.125, "a price index via a redistributor — dividends "
            "excluded, and the IBEX yields among the most in Europe",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(6000, 20500)

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_people(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("Unemployment rate, 15–74 (%, annual average)")
    ey, ev = _yr(ctx, "macro/unemployment.csv", "epa")
    ly, lv = _yr(ctx, "macro/unemployment.csv", "estat")
    ctx.line(ax, ly, lv, p.FAINT, lw=1.8, marker="", dashed_partial=False,
             label="Eurostat LFS (no values before 2009)")
    ctx.line(ax, ey, ev, p.ROJO, label="EPA (INE)")
    peak = max(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]:.0f} — one worker in four",
                peak, textcoords="offset points", xytext=(0, 10),
                ha="center", fontsize=8.8, fontweight="bold", color=p.ROJO)
    ax.legend(loc="lower right", fontsize=8.4)
    ig.add_recessions(ax, label=False)
    ax.set_ylim(5, 29)

    ax = ig.next_panel("Employment (millions, EPA annual average)")
    my, mv = _yr(ctx, "macro/employment.csv", "employed_thousands_avg")
    mv = [v / 1000 for v in mv]
    ctx.line(ax, my, mv, p.NAVY)
    ax.fill_between(my, 0, mv, color=p.NAVY, alpha=0.06)
    ctx.endlabel(ax, my, mv, p.NAVY, lambda v: f"{v:.1f}M", dy=10)
    trough = min(zip(my, mv), key=lambda t: t[1])
    ax.annotate(f"{trough[1]:.1f}M ({trough[0]:.0f})", trough,
                textcoords="offset points", xytext=(12, -8), ha="left",
                va="top", fontsize=8.8, fontweight="bold", color=p.ROJO)
    ax.annotate("five million jobs destroyed,\nthen twelve years to rebuild "
                "them", xy=(trough[0], trough[1]), xytext=(2006.6, 16.2),
                fontsize=8.0, color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(15, 24)

    ax = ig.next_panel("Income inequality — Gini (lower = more equal)")
    sy, sv = _yr(ctx, "social/gini.csv", "silc")
    wy, wv = _yr(ctx, "social/gini.csv", "wb")
    ctx.line(ax, sy, sv, p.PURPLE, label="Eurostat (EU-SILC)")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.8, dashed_partial=False,
             label="World Bank (EU-SILC-derived)")
    ax.invert_yaxis()
    ax.legend(loc="upper left", fontsize=8.2)
    ax.text(0.5, -0.125, "two cuts of one survey, not two measurements; "
            "disposable income, equivalised",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")

    ax = ig.next_panel("At risk of poverty (% below 60% of the median income)")
    py, pv = _yr(ctx, "social/poverty.csv", "arop60")
    ctx.line(ax, py, pv, p.TEAL)
    ax.fill_between(py, 0, pv, color=p.TEAL, alpha=0.08)
    ctx.endlabel(ax, py, pv, p.TEAL, lambda v: f"{v:.1f}%", dy=10)
    ax.annotate("a relative threshold: it did not fall when\nincomes fell "
                "together — a property of the\nmeasure, not a finding about "
                "poverty", xy=(2013, 20.4), xytext=(2010.6, 23.4),
                fontsize=8.0, color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(15, 25)

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("GDP in current US$ (trillion)")
    gy, gv = _yr(ctx, "international/gdp_usd.csv", "gdp_usd")
    gv = [v / 1e12 for v in gv]
    ctx.line(ax, gy, gv, p.NAVY)
    ax.fill_between(gy, 0, gv, color=p.NAVY, alpha=0.07)
    ctx.endlabel(ax, gy, gv, p.NAVY, lambda v: f"US$ {v:.2f}tn", dy=10)
    ax.annotate("2015: the euro fell 20% —\nthe economy did not",
                xy=(2015, gv[gy.index(2015)]), xytext=(2008.3, 0.72),
                fontsize=8.0, color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(0, 2.1)

    ax = ig.next_panel("GDP per person (US$, current)")
    cy, cv = _yr(ctx, "macro/gdp.csv", "gdp_per_capita_usd")
    ctx.line(ax, cy, cv, p.BLUE)
    ctx.endlabel(ax, cy, cv, p.BLUE, lambda v: f"US$ {v:,.0f}", dy=10)
    ax.set_ylim(22000, 44000)

    ax = ig.next_panel("Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "international/hdi.csv", "hdi")
    ctx.line(ax, hy, hv, p.GREEN_D, marker="o", ms=4.6,
             split_year=max(hy) if hy else None)
    ctx.endlabel(ax, hy, hv, p.GREEN_D, lambda v: f"{v:.3f}", dy=10)
    ax.axhline(0.9, color=p.FAINT, lw=0.9, ls=":")
    ax.text(2026.4, 0.9015, "0.900 = very high development", fontsize=8.0,
            color=p.MUTED, style="italic", ha="right", va="bottom")
    ax.text(0.5, -0.125, "one vintage throughout — the HDR recomputes the "
            "whole back-series at each methodology change",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(0.84, 0.95)

    ax = ig.next_panel("Official reserves incl. gold (US$ billion, year-end)")
    ry, rv = _yr(ctx, "international/reserves.csv", "reserves_usd")
    rv = [v / 1e9 for v in rv]
    ctx.line(ax, ry, rv, p.GUALDA)
    ax.fill_between(ry, 0, rv, color=p.GUALDA, alpha=0.10)
    ctx.endlabel(ax, ry, rv, p.GUALDA, lambda v: f"US$ {v:,.0f}bn", dy=10)
    ax.annotate("small for a large economy — the euro area's\nbuffer sits at "
                "the ECB, not in Madrid; much of\nthis is gold, revalued at "
                "market price", xy=(2012, rv[ry.index(2012)]),
                xytext=(2013.3, 30), fontsize=8.0, color=p.MUTED,
                style="italic", va="top",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(0, 150)

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_demography(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("Resident population at 1 January (millions)")
    py, pv = _yr(ctx, "social/population.csv", "population")
    pv = [v / 1e6 for v in pv]
    ctx.line(ax, py, pv, p.BLUE)
    ax.fill_between(py, 40, pv, color=p.BLUE, alpha=0.06)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"{v:.1f}M", dy=10)
    ax.annotate("2012–16: the only years the register\nshrank — emigration in "
                "the slump", xy=(2015, 46.4), xytext=(2006.5, 47.6),
                fontsize=8.0, color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.text(0.5, -0.125, "INE's Estadística Continua de Población — one "
            "vintage back to 1971; 2026 is a genuine 1-January level",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(40, 52)

    ax = ig.next_panel("Births and deaths per year (thousands)")
    by, bv = _yr(ctx, "social/demography.csv", "births")
    dy, dv = _yr(ctx, "social/demography.csv", "deaths")
    ctx.line(ax, by, [v / 1000 for v in bv], p.GREEN_D, label="Births")
    ctx.line(ax, dy, [v / 1000 for v in dv], p.INK, label="Deaths")
    ax.legend(loc="upper center", fontsize=8.6, ncol=2)
    cross = 2015
    ax.axvline(cross, color=p.FAINT, lw=0.9, ls=(0, (4, 3)), zorder=1)
    ax.text(cross + 0.3, 0.06, f"deaths overtake\nbirths in {cross}",
            transform=ax.get_xaxis_transform(), fontsize=8.0,
            color=p.MUTED, style="italic")
    ax.annotate("COVID-19", xy=(2020, 493.8), xytext=(2021.2, 505),
                fontsize=8.2, color=p.ROJO, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=p.ROJO, lw=0.8))
    ax.text(0.5, -0.125, "INE's definitive vital statistics; 2025 exists "
            "only as provisional estimates and is left blank",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(290, 590)
    ax.set_yticks(range(300, 600, 100))

    ax = ig.next_panel("Total fertility rate — children per woman")
    ty, tv = _yr(ctx, "social/demography.csv", "tfr")
    ax.axhline(2.1, color=p.MUTED, lw=1.1, ls=(0, (5, 4)))
    ax.text(2006.2, 2.13, "replacement level 2.1", fontsize=8.2,
            color=p.MUTED, style="italic")
    ctx.line(ax, ty, tv, p.ROJO)
    ctx.endlabel(ax, ty, tv, p.ROJO, lambda v: f"{v:.2f}", dy=10)
    lo = min(zip(ty, tv), key=lambda t: t[1])
    ax.annotate(f"{lo[1]:.2f} ({lo[0]:.0f}) — among the\nlowest ever "
                "recorded in Europe", lo, textcoords="offset points",
                xytext=(-10, 46), ha="right", fontsize=8.4,
                fontweight="bold", color=p.ROJO)
    ax.set_ylim(0.9, 2.3)

    ax = ig.next_panel("Natural increase vs net migration (thousands)")
    births = {y: v for y, v in zip(*_yr(ctx, "social/demography.csv", "births"))}
    deaths = {y: v for y, v in zip(*_yr(ctx, "social/demography.csv", "deaths"))}
    nat = [(y, (births[y] - deaths[y]) / 1000) for y in sorted(births)
           if y in deaths]
    sy, sv = _yr(ctx, "migration/migration_flows_ine.csv", "balance")
    cy, cv = _yr(ctx, "migration/migration_flows_emcr_ine.csv",
                 "immigration_emcr")
    ey2, ev2 = _yr(ctx, "migration/migration_flows_emcr_ine.csv",
                   "emigration_emcr")
    emi_by_year = dict(zip(ey2, ev2))
    emcr_net = [(y, (i - emi_by_year[y]) / 1000) for y, i in zip(cy, cv)
                if y in emi_by_year]
    ax.axhline(0, color=p.INK, lw=1.0, zorder=2)
    ctx.bars(ax, [y for y, _ in nat], [v for _, v in nat],
             lambda v: p.GREEN_D if v >= 0 else p.ROJO)
    ctx.line(ax, sy, [v / 1000 for v in sv], p.NAVY, lw=2.0, marker="",
             label="net migration, old methodology (EM, to 2021)")
    ctx.line(ax, [y for y, _ in emcr_net], [v for _, v in emcr_net],
             p.GUALDA, lw=2.0, marker="",
             label="net migration, EMCR (from 2021; computed as the "
             "difference of the flows)")
    ax.legend(loc="upper right", fontsize=7.8)
    ax.annotate("the population has grown on migration\nalone since 2016",
                xy=(2022, 727), xytext=(2007.4, 640), fontsize=8.0,
                color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.text(0.5, -0.125, "bars: births minus deaths, computed here; the two "
            "net-migration methodologies are never joined",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(-260, 990)

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_security(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("Homicides per year — by death certificate (INE/ECM)")
    hy, hv = _yr(ctx, "social/homicides.csv", "ecm_deaths")
    ctx.line(ax, hy, hv, p.ROJO, marker="o", ms=4.0)
    ctx.endlabel(ax, hy, hv, p.ROJO, lambda v: f"{v:,.0f}", dy=10)
    ax.annotate("the count a death certificate makes: assault\n(ICD-10 "
                "X85–Y09) as the underlying cause", xy=(2008, 378),
                xytext=(2009.4, 420), fontsize=8.0, color=p.MUTED,
                style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(200, 500)

    ax = ig.next_panel("Homicide rate per 100,000 (computed)")
    pop = {y: v for y, v in zip(*_yr(ctx, "social/population.csv",
                                     "population"))}
    rate = [(y, v / pop[y] * 100000) for y, v in zip(hy, hv) if y in pop]
    ry, rv = [y for y, _ in rate], [v for _, v in rate]
    ctx.line(ax, ry, rv, p.INK)
    ctx.endlabel(ax, ry, rv, p.INK, lambda v: f"{v:.2f}", dy=10)
    ax.text(0.5, -0.125, "computed here: ECM deaths against the 1-January "
            "population of the SAME year — among the lowest rates in Europe",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(0.4, 1.0)

    ax = ig.next_panel("Homicides recorded by the police (Ministerio del "
                       "Interior)")
    ctx.pending(ax)
    ax.text(0.5, 0.30, "the Interior ministry's crime portal answers every\n"
            "automated request with an error page served as HTTP 200;\n"
            "curated by hand in a later edition — the two counts disagree\n"
            "in both directions and neither is wrong (SOURCES.yaml, pending)",
            transform=ax.transAxes, ha="center", va="top", fontsize=8.2,
            color=p.FAINT, style="italic")

    ax = ig.next_panel("Violent deaths in context (per year)")
    ty, tv = _cause(ctx, "Accidentes de tráfico")
    xy, xv = _cause(ctx, "Suicidio y lesiones autoinfligidas")
    ctx.line(ax, xy, xv, p.PURPLE, label="Suicide and self-harm")
    ctx.line(ax, ty, tv, p.GUALDA, label="Road-traffic accidents")
    ctx.line(ax, hy, hv, p.ROJO, label="Homicide (same series as left)")
    ax.legend(loc="center right", fontsize=8.4)
    ax.annotate("traffic deaths fell by half while\nsuicide became the "
                "largest violent death", xy=(2019, 3671),
                xytext=(2006.5, 4300), fontsize=8.0, color=p.MUTED,
                style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(0, 4700)

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_mortality(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("All deaths registered per year (thousands)")
    dy, dv = _yr(ctx, "social/demography.csv", "deaths")
    dv = [v / 1000 for v in dv]
    ctx.line(ax, dy, dv, p.INK)
    ctx.endlabel(ax, dy, dv, p.INK, lambda v: f"{v:,.0f}", dy=10)
    peak = max(zip(dy, dv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:,.0f} ({peak[0]:.0f})", peak,
                textcoords="offset points", xytext=(0, 14), ha="center",
                fontsize=8.8, fontweight="bold", color=p.ROJO)
    ax.set_ylim(360, 540)

    ax = ig.next_panel("The two big killers (deaths per year, thousands)")
    ty, tv = _cause(ctx, "II.Tumores")
    cy, cv = _cause(ctx, "IX.Enfermedades del sistema circulatorio")
    ctx.line(ax, ty, [v / 1000 for v in tv], p.NAVY, label="Tumours")
    ctx.line(ax, cy, [v / 1000 for v in cv], p.ROJO, label="Circulatory diseases")
    ax.legend(loc="lower right", fontsize=8.6)
    ax.annotate("cancer overtakes the heart\nonly in 2024",
                xy=(2024, 115.6), xytext=(2015.2, 128.5), fontsize=8.0,
                color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(95, 135)

    ax = ig.next_panel("COVID-19 as the certified cause (deaths per year)")
    ci_y, ci_v = _cause(ctx, "COVID-19. Virus identificado")
    cu_y, cu_v = _cause(ctx, "COVID-19. Virus no identificado (sospechoso)")
    identified = {y: v for y, v in zip(ci_y, ci_v)}
    suspected = {y: v for y, v in zip(cu_y, cu_v)}
    yrs = sorted(y for y in set(identified) | set(suspected) if y >= 2020)
    iv = [identified.get(y, 0) for y in yrs]
    uv = [suspected.get(y, 0) for y in yrs]
    ax.bar(yrs, iv, width=0.58, color=p.ROJO, label="virus identified",
           zorder=3)
    ax.bar(yrs, uv, width=0.58, bottom=iv, color=p.ROJO, alpha=0.35,
           label="suspected, not identified", zorder=3)
    ax.legend(loc="upper right", fontsize=8.2)
    ax.annotate("60,358 certified with the virus identified in 2020 —\n"
                "and the certified count still sees only part of the "
                "excess", xy=(2020, 60358), xytext=(2020.6, 58000),
                fontsize=8.0, color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_xlim(2019.3, 2026.6)
    ax.set_ylim(0, 82000)

    ax = ig.next_panel("Deaths above the 2015–2019 average (thousands)")
    base = sum(v for y, v in zip(dy, dv) if 2015 <= y <= 2019) / 5
    ex = [(y, v - base) for y, v in zip(dy, dv) if y >= 2015]
    ax.axhline(0, color=p.INK, lw=1.0, zorder=2)
    ctx.bars(ax, [y for y, _ in ex], [v for _, v in ex],
             lambda v: p.ROJO if v > 0 else p.GREEN_D)
    for y, v in ex:
        if abs(v) > 15:
            ax.annotate(f"{v:+.0f}k", (y, v), textcoords="offset points",
                        xytext=(0, 6 if v > 0 else -14), ha="center",
                        fontsize=8.6, fontweight="bold", color=p.ROJO)
    ax.text(0.5, -0.125, "computed here, not published: the baseline is the "
            "mean of the five years before 2020.\nNo age standardisation — "
            "part of every bar is simply an older population",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.4,
            color=p.FAINT, style="italic")
    ax.set_xlim(2014.3, 2026.6)
    ax.set_ylim(-30, 90)

    for i, a in enumerate(ig.axes_flat):
        # Panels (c) and (d) carry their own x window: COVID does not exist
        # before 2020 and the excess baseline starts in 2015.
        ig.style_axis(a, xticks_years=i not in (2, 3))
    for i in (2, 3):
        a = ig.axes_flat[i]
        a.set_xticks(list(range(2016, 2027, 2) if i == 3 else
                              range(2020, 2027, 1)))


def plate_credit(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("What a mortgage costs (%, annual average)")
    ey, ev = _yr(ctx, "credit/lending_rates.csv", "euribor_12m")
    my, mv = _yr(ctx, "credit/lending_rates.csv", "mortgage_new")
    ax.axhline(0, color=p.MUTED, lw=0.9)
    ctx.line(ax, ey, ev, p.GUALDA, label="Euribor 12m")
    ctx.line(ax, my, mv, p.NAVY, label="new housing loans (TEDR)")
    ax.legend(loc="upper right", fontsize=8.2)
    ax.annotate("most Spanish mortgages are variable-rate,\nso the 2022-23 "
                "shock hit the stock, not just\nnew borrowers",
                xy=(2023, 3.9), xytext=(2008.0, 6.0), fontsize=8.0,
                color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.text(0.5, -0.125, "the new-business compilation changed with Circular "
            "5/2012 — pre/post-2014 levels are not strictly one definition",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(-0.8, 7.2)

    ax = ig.next_panel("Household debt (% of gross disposable income)")
    ay, av = _yr(ctx, "credit/household_debt.csv", "debt_pct_income_avg")
    ctx.line(ax, ay, av, p.ROJO)
    ax.fill_between(ay, 0, av, color=p.ROJO, alpha=0.07)
    peak = max(zip(ay, av), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.0f}% in {peak[0]:.0f}", peak,
                textcoords="offset points", xytext=(0, 12), ha="center",
                fontsize=9, fontweight="bold", color=p.ROJO)
    ctx.endlabel(ax, ay, av, p.ROJO, lambda v: f"{v:.0f}%", dy=10)
    ax.annotate("fifteen years of deleveraging:\nfrom 141% of income to 75%",
                xy=(2025, 75.6), xytext=(2016.3, 52), fontsize=8.0,
                color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(0, 160)

    ax = ig.next_panel("Doubtful loans as a share of all credit (%, December)")
    ny, nv = _yr(ctx, "credit/npl.csv", "npl_ratio")
    ctx.line(ax, ny, nv, p.PURPLE)
    ax.fill_between(ny, 0, nv, color=p.PURPLE, alpha=0.08)
    peak = max(zip(ny, nv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in December {peak[0]:.0f}", peak,
                textcoords="offset points", xytext=(0, 12), ha="center",
                fontsize=9, fontweight="bold", color=p.PURPLE)
    ig.add_event(ax, 2014.0, "", dy=0.56)
    ax.text(2015.8, 1.7, "2014: reporting change —\na level step, not "
            "behaviour", fontsize=7.8, color=p.MUTED, style="italic",
            va="top")
    ax.text(0.5, -0.125, "computed here as doubtful ÷ total credit to "
            "resident sectors (credit institutions in Spain), December stocks",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(0, 15.5)

    ax = ig.next_panel("Loans to households, stock (€ billion, Q4)")
    sy, sv = _yr(ctx, "credit/household_loans.csv", "loans_eurbn_q4")
    ctx.line(ax, sy, sv, p.BLUE)
    ax.fill_between(sy, 0, sv, color=p.BLUE, alpha=0.08)
    ctx.endlabel(ax, sy, sv, p.BLUE, lambda v: f"€{v:,.0f}bn", dy=10)
    ax.annotate("the stock is still below its 2010 peak —\nSpain borrows "
                "again, but it does not\nre-leverage", xy=(2010, sv[sy.index(2010)]),
                xytext=(2012.4, 852), fontsize=8.0, color=p.MUTED,
                style="italic", va="top",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(550, 950)

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_migration(ctx, ig) -> None:
    p = ctx.p

    # The seam panel. Eurostat's series changes methodology at 2021; the
    # INE publishes 2021 on both. The Eurostat line itself is split at the
    # seam — nothing on this panel draws a segment across 2020-2021.
    ax = ig.next_panel("Immigration per year — one series, two methodologies")
    ey, ev = _yr(ctx, "migration/immigration.csv", "by_citizenship_total")
    my, mv = _yr(ctx, "migration/migration_flows_ine.csv", "immigration")
    cy, cv = _yr(ctx, "migration/migration_flows_emcr_ine.csv",
                 "immigration_emcr")
    e_old = [(y, v / 1000) for y, v in zip(ey, ev) if y <= 2020]
    e_new = [(y, v / 1000) for y, v in zip(ey, ev) if y >= 2021]
    ctx.line(ax, [y for y, _ in e_old], [v for _, v in e_old], p.FAINT,
             lw=2.4, marker="", dashed_partial=False,
             label="Eurostat (carries EM to 2020,")
    ctx.line(ax, [y for y, _ in e_new], [v for _, v in e_new], p.FAINT,
             lw=2.4, marker="", dashed_partial=False,
             label="then EMCR from 2021)")
    ctx.line(ax, my, [v / 1000 for v in mv], p.NAVY, lw=2.2, marker="o",
             ms=4.0, dashed_partial=False,
             label="INE, old methodology (EM) — ends 2021")
    ctx.line(ax, cy, [v / 1000 for v in cv], p.ROJO, lw=2.2, marker="o",
             ms=4.0, dashed_partial=False,
             label="INE, new methodology (EMCR) — from 2021")
    ax.axvline(2021, color=p.INK, lw=1.2, ls=(0, (4, 3)), zorder=1)
    ax.annotate("2021 on both: 528,856 vs 887,960 —\na 68% jump that is pure "
                "methodology", xy=(2021, 888), xytext=(2009.2, 700),
                fontsize=8.2, color=p.INK, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.INK, lw=0.8))
    ax.legend(loc="upper left", fontsize=8.0)
    ax.set_ylim(0, 1450)

    ax = ig.next_panel("Who arrives and who leaves (Eurostat, thousands "
                       "per year)")
    iy, iv = ey, [v / 1000 for v in ev]
    gy, gv = _yr(ctx, "migration/emigration.csv", "by_citizenship_total")
    ctx.line(ax, iy, iv, p.GREEN_D, label="Immigration")
    ctx.line(ax, gy, [v / 1000 for v in gv], p.ROJO, label="Emigration")
    ax.legend(loc="upper left", fontsize=8.6)
    ax.annotate("the net is the reader's to see: departures\nneed no "
                "paperwork and are the worse-\nmeasured of the two",
                xy=(2013, 532), xytext=(2009.6, 60), fontsize=8.0,
                color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.text(0.5, -0.125, "the same 2021 methodology seam runs through both "
            "series (see the left panel)",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(0, 1450)

    ax = ig.next_panel("The resident stock, two definitions (millions, "
                       "1 January)")
    ny, nv = _yr(ctx, "migration/stock.csv", "by_birth_national")
    ty, tv = _yr(ctx, "migration/stock.csv", "by_citizenship_national")
    ctx.line(ax, ty, [v / 1e6 for v in tv], p.NAVY, marker="",
             label="Spanish citizens")
    ctx.line(ax, ny, [v / 1e6 for v in nv], p.GUALDA, marker="",
             dashed_partial=False, label="born in Spain")
    ax.fill_between(ty, [v / 1e6 for v in nv], [v / 1e6 for v in tv],
                    color=p.PURPLE, alpha=0.16, zorder=1)
    ax.legend(loc="upper left", fontsize=8.6)
    ax.annotate("the gap is people who became Spanish:\n2.5 million by 2025 — "
                "naturalisation, not\nemigration, is why the foreign-citizen\n"
                "count grows slowly in record-arrival years",
                xy=(2022, 40.5), xytext=(2006.5, 37.4), fontsize=8.0,
                color=p.PURPLE, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.PURPLE, lw=0.8))
    ax.set_ylim(36, 44)

    ax = ig.next_panel("The year's paperwork: asylum, permits, citizenship "
                       "(persons)")
    ay, av = _yr(ctx, "migration/asylum.csv", "applications")
    dy, dv = _yr(ctx, "migration/asylum.csv", "decisions")
    oy, ov = _yr(ctx, "migration/asylum.csv", "positive")
    fy, fv = _yr(ctx, "migration/permits.csv", "first_permits")
    qy, qv = _yr(ctx, "migration/naturalisation.csv", "acquisitions")
    ctx.line(ax, fy, fv, p.NAVY, lw=2.0, marker="", label="first residence "
             "permits issued")
    ctx.line(ax, qy, qv, p.PURPLE, lw=2.0, marker="", label="acquired "
             "Spanish citizenship")
    ctx.line(ax, ay, av, p.ROJO, lw=2.0, marker="", label="asylum applications")
    ctx.line(ax, dy, dv, p.GUALDA, lw=1.8, marker="", dashed_partial=False,
             label="first-instance decisions")
    ctx.line(ax, oy, ov, p.TEAL, lw=1.8, marker="", dashed_partial=False,
             label="of which positive")
    ax.legend(loc="upper left", fontsize=7.6, ncol=2)
    ax.text(0.5, -0.125, "five series, five different questions: applications "
            "are not arrivals, permits are not people,\ndecisions lag "
            "applications by years — asylum and permits start 2008; the hole "
            "is the source's",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.4,
            color=p.FAINT, style="italic")
    ax.set_ylim(0, 820000)

    for a in ig.axes_flat:
        ig.style_axis(a)


# The plates, in spine order.
PLATES = (
    dict(id="01", slug="economy", builder=plate_economy,
         title="The Spanish Economy — Size, Growth and Prices, 2006–2026",
         subtitle="A €1.7 trillion economy that fell twice before COVID and "
                  "outgrew the euro area after it.",
         source="Sources: Eurostat — ESA 2010 national accounts · INE — "
                "CNTR and IPC (base 2025) · World Bank WDI",
         alt="Four panels on the Spanish economy. Nominal GDP rises from "
             "€1,005 billion in 2006 to €1,599 billion in 2024 with the "
             "INE's own release drawn on top; real growth falls to −3.8% in "
             "2009, −2.9% in 2012 and −10.9% in 2020, then rebounds above "
             "2.5%; GDP per person reads US$33,493 in 2023; IPC inflation "
             "peaks at 8.4% in 2022 beside the harmonised HICP."),
    dict(id="02", slug="fiscal", builder=plate_fiscal,
         title="The Public Books — Deficits, the Bailout and the Debt",
         subtitle="General government on the Maastricht definition: the "
                  "state took in less than it spent every single year of "
                  "the window.",
         source="Source: Eurostat — EDP notification and gov_10a_main "
                "(Spain's own transmission)",
         alt="Four panels on Spanish public finances. Revenue runs near 41% "
             "of GDP against expenditure spiking to 51% in 2020; the deficit "
             "reaches −11.2% in 2009 and −11.5% in 2012, the bank-bailout "
             "year; gross debt jumps from 69.5% to 100.0% of GDP in "
             "2011-2013 and reads 101.4% in 2024; the interest bill halves "
             "while the debt triples."),
    dict(id="03", slug="spending", builder=plate_spending,
         title="Where the Money Goes — Spending by Function, 2006–2024",
         subtitle="Social protection alone outweighs every other function "
                  "of the Spanish state combined; investment tells the "
                  "bubble and the cuts.",
         source="Source: Eurostat — gov_10a_exp (COFOG) and gov_10a_main",
         alt="Four panels on public spending. Social protection rises to "
             "21.9% of GDP in 2020 against health near 7.6% and education "
             "near 4.6%; the whole-economy investment rate falls from "
             "30.9% in the construction bubble to 20%; public investment "
             "halves in the austerity years."),
    dict(id="04", slug="trade", builder=plate_trade,
         title="Foreign Trade — a Deficit That Flipped, 2006–2026",
         subtitle="Goods and services on the national-accounts basis: in "
                  "surplus every year since 2011, on tourism and the "
                  "export turn.",
         source="Sources: Eurostat — nama_10_gdp (P6/P7) · World Bank WDI "
                "(openness)",
         alt="Four panels on trade. Exports of goods and services rise from "
             "€253 billion in 2006 to €595 billion in 2024, passing imports "
             "in 2011; the balance swings from −€62 billion in 2007 to "
             "+€69 billion in 2024; openness reaches 72% of GDP; the "
             "partners-and-products panel is pending the customs source."),
    dict(id="05", slug="markets", builder=plate_markets,
         title="Money & Markets — Frankfurt's Rate, the Yield and the IBEX",
         subtitle="Spain has no monetary policy of its own: the deposit "
                  "facility, the 10-year benchmark, the euro and the IBEX 35.",
         source="Sources: ECB Data Portal · Eurostat (Maastricht yield) · "
                "Yahoo Finance — a redistributor (IBEX, price index)",
         alt="Four panels on money and markets. The deposit facility rate "
             "sits below zero from 2014 to 2022 and peaks at 4% in 2023; "
             "the 10-year yield spikes to 5.85% in 2012; the euro weakens "
             "from 1.26 to 1.08 dollars; the IBEX 35's 2007 close of "
             "15,182 is not regained within the window on a price basis."),
    dict(id="06", slug="people", builder=plate_people,
         title="People — Work, Inequality and Poverty, 2006–2026",
         subtitle="The labour market that lost one worker in four, and the "
                  "slow rebuilding since.",
         source="Sources: INE — EPA · Eurostat — LFS and EU-SILC · World Bank",
         alt="Four panels on work and income. Unemployment peaks at 26.1% "
             "in 2013 and returns to 10.5% by 2025; employment falls to "
             "17.1 million and rebuilds to 22.2 million; the Gini holds "
             "near 33; the at-risk-of-poverty rate stays near one in five."),
    dict(id="07", slug="world", builder=plate_world,
         title="Spain in the World — Size, Development and Reserves",
         subtitle="The comparables layer: the same quantities, computed the "
                  "same way, for everyone.",
         source="Sources: World Bank WDI · UNDP Human Development Report "
                "2025 · IMF IFS via the World Bank",
         alt="Four panels on Spain in the world. GDP in current dollars "
             "moves between US$1.2 and US$1.7 trillion with the exchange "
             "rate; GDP per person reads US$33,493 in 2023; the Human "
             "Development Index reaches 0.918; reserves including gold "
             "reach US$103 billion, small because the euro area's buffer "
             "sits at the ECB."),
    dict(id="08", slug="demography", builder=plate_demography,
         title="Demography — Deaths Overtook Births in 2015",
         subtitle="The population grows anyway, on migration alone; "
                  "fertility is among the lowest ever recorded in Europe.",
         source="Sources: INE — Estadística Continua de Población, MNP, "
                "EM/EMCR · Eurostat demo_find",
         alt="Four panels on demography. The population at 1 January grows "
             "from 44.0 to 49.6 million, shrinking only in 2012-16; deaths "
             "overtake births in 2015 and reach 493,776 in 2020; fertility "
             "falls to 1.10 children per woman; natural increase turns "
             "negative while net migration reaches 727,000 in 2022 on the "
             "new methodology."),
    dict(id="09", slug="security", builder=plate_security,
         title="Security — Homicide on the Death Certificate",
         subtitle="The police count is pending (the ministry's portal "
                  "blocks automated access); what the certificates show is "
                  "one of Europe's lowest rates.",
         source="Source: INE — Estadística de Defunciones según la Causa de "
                "Muerte (ICD-10 X85–Y09)",
         alt="Four panels on violence. Homicides by death certificate fall "
             "from 378 in 2008 to 324 in 2024; the computed rate reads "
             "0.66 per 100,000; the police-recorded panel is pending; "
             "suicide at about 4,000 a year is the largest violent death, "
             "ahead of road accidents, with homicide far below both."),
    dict(id="10", slug="mortality", builder=plate_mortality,
         title="Mortality — COVID-19 and the Two Big Killers",
         subtitle="What people die of: cancer and the heart trade the lead, "
                  "and 2020 breaks every trend on the plate.",
         source="Sources: INE — MNP (deaths) and ECM (certified causes)",
         alt="Four panels on mortality. All deaths rise from 371,000 in "
             "2006 to 493,776 in 2020; tumours at 115,578 and circulatory "
             "diseases at 113,620 in 2024 are the two big killers; "
             "certified COVID-19 deaths total 74,839 in 2020 with the "
             "virus identified or suspected; excess over the 2015-19 "
             "average reaches +76,000 in 2020."),
    dict(id="11", slug="credit", builder=plate_credit,
         title="Credit — Variable-Rate Country",
         subtitle="What a mortgage costs when most mortgages reprice every "
                  "year, and fifteen years of deleveraging.",
         source="Source: Banco de España — financial accounts and interest-"
                "rate statistics",
         alt="Four panels on credit. Euribor 12 months runs from 3.4% in "
             "2006 to negative in 2016-2021 and 3.6% in 2023, with new "
             "housing-loan rates beside it; household debt falls from 138% "
             "of disposable income in 2010 to 75% in 2025; doubtful loans "
             "peak at 13.6% of credit in December 2013; the loan stock "
             "stays below its 2010 peak."),
    dict(id="12", slug="migration", builder=plate_migration,
         title="Migration — Who Arrives, Who Leaves, Who Becomes Spanish",
         subtitle="The flows, the stocks on both definitions, and one "
                  "methodology seam drawn as a seam.",
         source="Sources: Eurostat — migr_imm1ctz/imm3ctb, migr_emi1ctz, "
                "migr_pop1ctz/pop3ctb, migr_asyappctza, migr_asydcfsta, "
                "migr_resfirst, migr_acq · INE — EM and EMCR",
         alt="Four panels on migration. Immigration reads 750,480 in 2019 "
             "and 1,288,562 in 2024, with the 2021 methodology change "
             "drawn as a break: the INE counts 528,856 for 2021 on the old "
             "methodology and 887,960 on the new; emigration runs near "
             "half a million; Spanish citizens exceed people born in Spain "
             "by 2.5 million, the naturalisation gap; asylum applications "
             "reach 167,750 in 2024 beside permits and naturalisations."),
)
