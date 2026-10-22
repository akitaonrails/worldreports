"""The France plates, drawn on the plate spine.

Every plate declares its topic and claims its four panels by slot key, in
spine order (PLATE_SPINE.md, core/spine.py), so the comparison viewer can
wipe a French plate over any other country's and growth sits over growth,
a homicide rate over a homicide rate. The canonical slots carry the
spine's indicator in the spine's unit; the reference scale is applied by
the spine when the plate is saved, never here. The lens slot is France's
own story.

Every number written on a panel is read from this country's CSVs at draw
time. Counts become rates with core/rates.py, over the population of the
same year and the same scope (DATA_NOTES.md, "The spine").
"""
from __future__ import annotations

import matplotlib.ticker as mticker
import numpy as np

from core.sideload import sibling

events = sibling(__file__, "events")

LENS_TAG = "France's own story"


# ------------------------------------------------------------- helpers
def _d(table, col) -> dict[int, float]:
    """{year: value} for one column, blanks dropped."""
    if not table or col not in table:
        return {}
    return {int(y): float(v) for y, v in zip(table["year"], table[col])
            if v == v and not isinstance(v, str)}


def _xy(d: dict[int, float]):
    ys = sorted(d)
    return ys, [d[y] for y in ys]


def _upto(d: dict[int, float], last: int) -> dict[int, float]:
    return {y: v for y, v in d.items() if y <= last}


def _note(ctx, ax, text, x=0.02, y=0.96, ha="left", va="top", size=7.8,
          color=None):
    """A short comment in axes coordinates, so it stays where it was put
    whatever range the spine gives the panel."""
    return ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
                   fontsize=size, color=color or ctx.p.muted,
                   style="italic", zorder=7)


def _foot(ctx, ax, text):
    """A caveat under the panel's year axis."""
    # The bottom row has the plate's source rule below it, so its caveat
    # sits just under the year labels instead.
    bottom = ax.get_subplotspec().rowspan.start > 0
    ax.text(0.5, -0.082 if bottom else -0.125, text, transform=ax.transAxes,
            ha="center", va="top", fontsize=7.3, color=ctx.p.faint,
            style="italic")


def _lens(ctx, ax):
    """Say that this panel is France's own, not a shared indicator."""
    ax.text(1.0, 1.0, LENS_TAG, transform=ax.transAxes, ha="right",
            va="bottom", fontsize=7.4, color=ctx.p.faint, style="italic",
            clip_on=False)


def _pending(ctx, ax, reason):
    ctx.pending(ax)
    _note(ctx, ax, reason, x=0.5, y=0.36, ha="center", va="top", size=8.2)


def _bands(ig, ax, first=False, y=0.06, va="bottom"):
    """The recession bands from country.yaml, on every time-series panel.

    Labelled on slot 1 only, and inside the panel at height `y` (axes
    fraction) rather than above it, where the label would meet the panel
    title. Each plate puts it where its own slot 1 has room.
    """
    ig.add_recessions(ax, label=False)
    if first:
        for start, end, name in ig.country.recessions:
            ax.text((start + end) / 2, y, name,
                    transform=ax.get_xaxis_transform(), ha="center", va=va,
                    fontsize=7.8, color=ig.p.muted, style="italic", zorder=7)


def _seam(ctx, ax, d, at, color, label="", **kw):
    """One series drawn as two segments either side of a break.

    A definitional break is a seam, never a splice: the line stops before
    the year the definition changes and starts again on it, so no segment
    joins two different quantities.
    """
    before = {y: v for y, v in d.items() if y < at}
    after = {y: v for y, v in d.items() if y >= at}
    if before:
        ctx.line(ax, *_xy(before), color, label=label, **kw)
    if after:
        ctx.line(ax, *_xy(after), color,
                 label="_nolegend_" if before else label, **kw)


def _swatch(ax, color, label):
    """Name the bars in the legend: bars are drawn one per year,
    unlabelled, so the first bar of the colour carries the entry."""
    from matplotlib.colors import to_rgba
    for patch in ax.patches:
        if to_rgba(patch.get_facecolor())[:3] == to_rgba(color)[:3]:
            patch.set_label(label)
            return


def _avg_pop(ctx) -> dict[int, float]:
    """The average population of each year, France including the DROM
    (Mayotte from 2014): the denominator of every rate France computes."""
    return _d(ctx.table("social/vital_rates.csv"), "pop_avg")


def _style(ig):
    for ax in ig.axes_flat:
        ig.style_axis(ax)


# ============================================================== economy
def fig_economy(ctx, ig) -> None:
    gdp = ctx.table("macro/gdp.csv")
    wb = ctx.table("international/world_wb.csv")
    infl = ctx.table("macro/inflation.csv")
    unemp = ctx.table("macro/unemployment.csv")

    ax = ig.slot("economy.growth", "Real GDP growth")
    g = _d(gdp, "real_growth")
    if g:
        ctx.bars(ax, *_xy(g), lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED)
        for y, v in g.items():
            if abs(v) > 2.4:
                ax.annotate(f"{v:+.1f}", (y, v), textcoords="offset points",
                            xytext=(0, 4 if v >= 0 else -5), ha="center",
                            va="bottom" if v >= 0 else "top", fontsize=8.4,
                            fontweight="bold",
                            color=ctx.p.GREEN_D if v >= 0 else ctx.p.RED)
        lo = min(g, key=g.get)
        _note(ctx, ax, f"{lo}: {g[lo]:+.1f}%, the one deep recession; "
              f"{lo + 1}: {g[lo + 1]:+.1f}%")
    else:
        _pending(ctx, ax, "national accounts not staged")
    _bands(ig, ax, first=True)

    ax = ig.slot("economy.gdp_per_person", "GDP per person")
    pp = _d(wb, "gdp_per_person_usd")
    if pp:
        ctx.line(ax, *_xy(pp), ctx.p.BLUE, label="World Bank, current US$")
        ctx.endlabel(ax, *_xy(pp), ctx.p.BLUE, lambda v: f"US$ {v:,.0f}",
                     dy=10)
        # The dips are the dollar, not the economy: in euros GDP per
        # person fell only in the two recessions.
        eur = {y: n / p for y, n, p in zip(gdp["year"], gdp["nominal_eurbn"],
                                           gdp["population_mn"])
               if n == n and p == p}
        fell = [y for y in sorted(eur) if y - 1 in eur and eur[y] < eur[y - 1]]
        ig.add_event(ax, 2015.0, "euro slump, not a recession", dy=0.30)
        _note(ctx, ax, "in euros it fell only in "
              + " and ".join(str(y) for y in fell), x=0.02, y=0.06,
              va="bottom")
    else:
        _pending(ctx, ax, "World Bank series not staged")
    _bands(ig, ax)

    ax = ig.slot("economy.inflation",
                 "Consumer price inflation, and the ECB's 2% aim")
    ipc, hicp = _d(infl, "ipc"), _d(infl, "hicp")
    if ipc:
        ax.axhline(2.0, color=ctx.p.BLUE, lw=1.2, ls="--", zorder=2,
                   label="ECB aim: 2%")
        if hicp:
            ctx.line(ax, *_xy(hicp), ctx.p.FAINT, lw=1.8,
                     label="Harmonised HICP (Eurostat)", dashed_partial=False)
        ctx.line(ax, *_xy(ipc), ctx.p.RED, label="French IPC (INSEE)")
        peak = max(ipc, key=ipc.get)
        ax.annotate(f"{ipc[peak]:.1f}", (peak, ipc[peak]),
                    textcoords="offset points", xytext=(-9, -3), ha="right",
                    fontsize=8.6, fontweight="bold", color=ctx.p.RED)
        ax.legend(loc="upper left", fontsize=8.2)
        ig.add_event(ax, 2015.0, "deflation scare", dy=0.62)
    else:
        _pending(ctx, ax, "IPC not staged")
    _bands(ig, ax)

    ax = ig.slot("economy.unemployment", "Unemployment rate (ILO)")
    u = _d(unemp, "value")
    if u:
        ctx.line(ax, *_xy(u), ctx.p.RED, label="INSEE, Labour Force Survey")
        ctx.endlabel(ax, *_xy(u), ctx.p.RED, lambda v: f"{v:.1f}%", dy=10)
        top = max(u, key=u.get)
        back = next((y for y in sorted(u) if y > top and u[y] < u[2008]),
                    None)
        _note(ctx, ax, f"peak {u[top]:.1f}% in {top}; back below the "
              f"2008 level ({u[2008]:.1f}%) only in {back}")
        _note(ctx, ax, "France excluding Mayotte", y=0.86, size=7.4,
              color=ctx.p.faint)
    else:
        _pending(ctx, ax, "unemployment not staged")
    _bands(ig, ax)
    _style(ig)


# =============================================================== fiscal
def fig_fiscal(ctx, ig) -> None:
    rev = ctx.table("fiscal/revenue.csv")
    tax = ctx.table("fiscal/tax_burden.csv")
    deficit = ctx.table("fiscal/deficit.csv")
    debt = ctx.table("fiscal/debt.csv")
    gdp = ctx.table("macro/gdp.csv")
    last = ctx.LAST_FULL_YEAR

    ax = ig.slot("fiscal.revenue_expenditure",
                 "Revenue and expenditure, and the compulsory levies")
    r, e = _d(rev, "revenue"), _d(rev, "expenditure")
    if r and e:
        ctx.line(ax, *_xy(e), ctx.p.RED, label="Expenditure")
        ctx.line(ax, *_xy(r), ctx.p.BLUE_D, label="Revenue")
        # The compulsory levies are France's own measure of the tax take
        # and the number French politics argues about. Revenue is wider
        # (sales, property income), so the levies sit inside it. The
        # 2026 row is a budget forecast and is not drawn.
        po = _upto(_d(tax, "insee"), last)
        _seam(ctx, ax, po, 2019, ctx.p.TEAL, lw=1.9, ms=3.2,
              label="Compulsory levies (INSEE)")
        # The one real discontinuity: in 2019 the CICE stopped being a
        # tax credit booked as spending and became a cut in employer
        # contributions, which lowers the levies ratio by ~0.9 pt with
        # no change in policy. A seam, and a rule on it.
        ax.axvline(2019, color=ctx.p.FAINT, lw=0.9, ls=(0, (4, 3)),
                   zorder=1)
        ax.legend(loc="lower left", bbox_to_anchor=(0.0, 0.40),
                  fontsize=8.0, ncol=3)
        _note(ctx, ax, "2019: CICE becomes a contribution cut\n"
              "(−0.9pt, definitional — not a tax cut)", x=0.99, y=0.30,
              ha="right", va="bottom", size=7.4)
        est = _d(tax, "estat")
        gap = [est[y] - po[y] for y in est if y in po]
        _note(ctx, ax, f"Eurostat's harmonised tax ratio runs "
              f"{min(gap):.1f}–{max(gap):.1f}pt above INSEE's: it counts "
              f"imputed contributions", x=0.99, y=0.18, ha="right",
              va="bottom", size=7.2, color=ctx.p.faint)
    else:
        _pending(ctx, ax, "Eurostat gov_10a_main not staged")
    _bands(ig, ax, first=True)

    ax = ig.slot("fiscal.balance", "Overall balance and primary balance")
    bal, prim = _d(deficit, "deficit"), _d(deficit, "primary")
    if bal:
        ax.axhline(-3.0, color=ctx.p.BLUE, lw=1.1, ls="--", zorder=2)
        ctx.bars(ax, *_xy(bal), lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED)
        if prim:
            ctx.line(ax, *_xy(prim), ctx.p.PURPLE, lw=2.0, ms=3.4,
                     label="Primary balance (before interest)")
        _swatch(ax, ctx.p.RED, "Overall balance (EDP)")
        for y, v in bal.items():
            if v < -6:
                ax.annotate(f"{v:.1f}", (y, v), textcoords="offset points",
                            xytext=(0, -4), ha="center", va="top",
                            fontsize=8.2, fontweight="bold", color=ctx.p.RED)
        ax.legend(loc="upper right", fontsize=8.0)
        _note(ctx, ax, "dashed: the Maastricht limit, −3%", y=0.96,
              size=7.6, color=ctx.p.BLUE)
        _note(ctx, ax, "last balanced budget: 1974", x=0.02, y=0.06,
              va="bottom")
    else:
        _pending(ctx, ax, "EDP notification not staged")
    _bands(ig, ax)

    ax = ig.slot("fiscal.debt", "Gross public debt (Maastricht)")
    dd = _d(debt, "gross")
    if dd:
        ctx.line(ax, *_xy(dd), ctx.p.RED)
        ax.fill_between(*_xy(dd), 0, color=ctx.p.RED, alpha=0.06, zorder=1)
        ax.axhline(60.0, color=ctx.p.BLUE, lw=1.1, ls="--", zorder=2)
        ctx.endlabel(ax, *_xy(dd), ctx.p.RED, lambda v: f"{v:.1f}%", dy=10)
        y0 = min(dd)
        _note(ctx, ax, f"{dd[y0]:.0f}% of GDP in {y0}; the 2009 and 2020 "
              f"steps never came back down", y=0.96)
        _note(ctx, ax, "Maastricht limit: 60%", x=0.02, y=0.34, size=7.6,
              color=ctx.p.BLUE)
    else:
        _pending(ctx, ax, "EDP notification not staged")
    _bands(ig, ax)

    ax = ig.slot("fiscal.interest", "Interest paid on the debt")
    it = _d(deficit, "interest")
    if it:
        ctx.line(ax, *_xy(it), ctx.p.GOLD, label="Interest paid (D.41)")
        ctx.endlabel(ax, *_xy(it), ctx.p.GOLD, lambda v: f"{v:.1f}%", dy=10)
        # The fact of the period: the stock more than doubled in euros
        # while the bill fell, because rates fell faster.
        nom = _d(gdp, "nominal_eurbn")
        low = min((y for y in it if y <= 2021), key=it.get)
        a, b = min(dd), low
        _note(ctx, ax, f"the debt went from €{dd[a] * nom[a] / 100:,.0f}bn "
              f"({a}) to €{dd[b] * nom[b] / 100:,.0f}bn ({b}) while "
              f"interest fell from {it[a]:.1f}% to {it[b]:.1f}% of GDP")
    else:
        _pending(ctx, ax, "Eurostat D.41 not staged")
    _bands(ig, ax)
    _style(ig)


# ============================================================= spending
COFOG = ["social_protection", "health", "general_services", "education",
         "economic_affairs", "defence_order", "other"]
COFOG_LABEL = {"social_protection": "Social protection", "health": "Health",
               "general_services": "General services (incl. interest)",
               "education": "Education",
               "economic_affairs": "Economic affairs",
               "defence_order": "Defence & public order",
               "other": "Other functions"}


def fig_spending(ctx, ig) -> None:
    spend = ctx.table("fiscal/spending_by_function.csv")
    inv = ctx.table("fiscal/investment.csv")
    colors = {"social_protection": ctx.p.NAVY, "health": ctx.p.TEAL,
              "education": ctx.p.BLUE, "general_services": ctx.p.RED,
              "economic_affairs": ctx.p.GOLD, "defence_order": ctx.p.PURPLE,
              "other": "#B9BDC7"}

    ax = ig.slot("spending.by_function", "Public spending by function")
    cols = [c for c in COFOG if spend and c in spend]
    if cols:
        yrs = sorted(set.intersection(*(set(_d(spend, c)) for c in cols)))
        stack = [[_d(spend, c)[y] for y in yrs] for c in cols]
        ax.stackplot(yrs, *stack, colors=[colors[c] for c in cols],
                     alpha=0.92, lw=0, zorder=3)
        # Labelled inside its own band where the band is thick enough to
        # hold a line of text; the two thin ones get a leader from above.
        first = yrs[0]
        base = 0.0
        for c, vals in zip(cols, stack):
            mid = base + vals[0] / 2
            if c in ("defence_order", "other"):
                pass
            else:
                ax.text(first + 0.15, mid, COFOG_LABEL[c], fontsize=7.4,
                        va="center", ha="left", zorder=6,
                        color=ctx.p.INK if c == "economic_affairs"
                        else "white",
                        fontweight="bold", gid="qa-on-data")
            base += vals[0]
        tops = np.cumsum(stack, axis=0)
        i_def, i_oth = cols.index("defence_order"), cols.index("other")
        k = yrs.index(2008) if 2008 in yrs else 0
        x = yrs[k]
        ax.annotate(COFOG_LABEL["defence_order"],
                    xy=(x, tops[i_def][k] - stack[i_def][k] / 2),
                    xytext=(yrs[0] + 0.15, 59.0), fontsize=7.4,
                    color=ctx.p.PURPLE,
                    fontweight="bold", va="center",
                    arrowprops=dict(arrowstyle="-", color=ctx.p.PURPLE,
                                    lw=0.8))
        k2 = yrs.index(2014) if 2014 in yrs else len(yrs) // 2
        ax.annotate(COFOG_LABEL["other"],
                    xy=(yrs[k2], tops[i_oth][k2] - stack[i_oth][k2] / 2),
                    xytext=(yrs[k2] + 0.4, 61.6), fontsize=7.4,
                    color=ctx.p.MUTED, fontweight="bold", va="center",
                    arrowprops=dict(arrowstyle="-", color=ctx.p.FAINT,
                                    lw=0.8))
        _foot(ctx, ax, f"COFOG, general government; the last year "
              f"published is {yrs[-1]}")
    else:
        _pending(ctx, ax, "COFOG not staged")
    _bands(ig, ax, first=True, y=0.995, va="top")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else")
    sp, tot = _d(spend, "social_protection"), _d(spend, "total")
    if sp and tot:
        rest = {y: tot[y] - sp[y] for y in sp if y in tot}
        ctx.line(ax, *_xy(rest), ctx.p.TEAL, label="All other functions")
        ctx.line(ax, *_xy(sp), ctx.p.NAVY, label="Social protection alone")
        ax.fill_between(*_xy(sp), 0, color=ctx.p.NAVY, alpha=0.08, zorder=1)
        ax.legend(loc="upper left", fontsize=8.2, ncol=2)
        y1 = max(sp)
        share = {y: sp[y] / tot[y] * 100 for y in sp if y in tot}
        _note(ctx, ax, f"social protection is {share[y1]:.0f}% of all "
              f"public spending in {y1} (peak {max(share.values()):.0f}%, "
              f"{max(share, key=share.get)})", y=0.42)
    else:
        _pending(ctx, ax, "COFOG not staged")
    _bands(ig, ax)

    ax = ig.slot("spending.investment",
                 "Investment rate, whole economy (GFCF)")
    gf = _d(inv, "gfcf_pct_gdp")
    if gf:
        ctx.line(ax, *_xy(gf), ctx.p.BLUE, label="INSEE national accounts")
        ctx.endlabel(ax, *_xy(gf), ctx.p.BLUE, lambda v: f"{v:.1f}%", dy=10)
        lo = min(gf, key=gf.get)
        hi = max(gf, key=gf.get)
        _note(ctx, ax, f"a narrow band: {gf[lo]:.1f}% ({lo}) to "
              f"{gf[hi]:.1f}% ({hi})", y=0.96)
    else:
        _pending(ctx, ax, "national accounts not staged")
    _bands(ig, ax)

    ax = ig.slot("spending.public_investment",
                 "Public investment (government GFCF)")
    gg = _d(inv, "gov_gfcf_pct_gdp")
    if gg:
        ctx.line(ax, *_xy(gg), ctx.p.GREEN_D)
        ax.fill_between(*_xy(gg), 0, color=ctx.p.GREEN_D, alpha=0.10,
                        zorder=1)
        ctx.endlabel(ax, *_xy(gg), ctx.p.GREEN_D, lambda v: f"{v:.1f}%",
                     dy=10)
        # Local authorities do most public investment in France, and it
        # dips in the years after each municipal election.
        _note(ctx, ax, "local authorities invest least in the years after "
              "a municipal election (2014, 2020)", y=0.96)
    else:
        _pending(ctx, ax, "government GFCF not staged")
    _bands(ig, ax)
    _style(ig)


# ================================================================ trade
def fig_trade(ctx, ig) -> None:
    na = ctx.table("trade/trade_na.csv")
    tr = ctx.table("trade/trade.csv")
    gdp = ctx.table("macro/gdp.csv")
    prods = ctx.table("trade/exports_products.csv")
    dest = ctx.table("trade/destinations.csv")
    last = ctx.LAST_FULL_YEAR

    ax = ig.slot("trade.exports_imports",
                 "Exports and imports of goods and services")
    x, m = _d(na, "exports_pct_gdp"), _d(na, "imports_pct_gdp")
    if x and m:
        ctx.line(ax, *_xy(x), ctx.p.GREEN_D, label="Exports")
        ctx.line(ax, *_xy(m), ctx.p.BLUE, label="Imports")
        ax.legend(loc="upper left", fontsize=8.4, ncol=2)
        ex, im = _upto(_d(tr, "exports"), last), _upto(_d(tr, "imports"), last)
        y1 = max(ex)
        _note(ctx, ax, f"goods alone, customs basis, {y1}: exports "
              f"€{ex[y1]:,.0f}bn, imports €{im[y1]:,.0f}bn", x=0.02, y=0.86)
    else:
        _pending(ctx, ax, "national accounts P6/P7 not staged")
    _bands(ig, ax, first=True)

    ax = ig.slot("trade.balance",
                 "Trade balance: goods and services, and goods alone")
    b = _d(na, "balance_pct_gdp")
    if b:
        ctx.bars(ax, *_xy(b), lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED)
        _swatch(ax, ctx.p.RED, "Goods and services")
        # The customs goods balance over nominal GDP: the structural
        # deficit France argues about, which services partly offset.
        nom = _d(gdp, "nominal_eurbn")
        gb = {y: v / nom[y] * 100
              for y, v in _upto(_d(tr, "balance"), last).items() if y in nom}
        ctx.line(ax, *_xy(gb), ctx.p.INK, lw=1.9, ms=3.4,
                 label="Goods alone (customs)")
        ax.legend(loc="lower left", fontsize=8.2)
        worst = min(gb, key=gb.get)
        ax.annotate(f"{worst}: the energy bill ({gb[worst]:.1f}%)",
                    xy=(worst, gb[worst]), xytext=(2008.0, -8.6),
                    fontsize=8.0, color=ctx.p.MUTED, style="italic",
                    arrowprops=dict(arrowstyle="-", color=ctx.p.FAINT,
                                    lw=0.8))
        _note(ctx, ax, "services run a surplus that covers most of the "
              "goods deficit", y=0.96)
    else:
        _pending(ctx, ax, "national accounts P6/P7 not staged")
    _bands(ig, ax)

    ax = ig.slot("trade.destinations", "Top export destinations")
    if dest:
        rows = list(zip(dest["year"], dest["destiny"], dest["share_pct"]))
        latest = max(int(y) for y, _, _ in rows if int(y) <= last)
        rank = sorted({n for _, n, _ in rows},
                      key=lambda n: -next(s for y, nn, s in rows
                                          if nn == n and int(y) == latest))
        pal = {"Germany": ctx.p.BLUE, "Italy": ctx.p.GREEN,
               "Spain": ctx.p.GOLD, "Belgium": ctx.p.PURPLE,
               "United States": ctx.p.RED, "United Kingdom": ctx.p.TEAL,
               "China": ctx.p.INK}
        for name in rank[:7]:
            pts = {int(y): s for y, n, s in rows if n == name
                   and int(y) <= last}
            ctx.line(ax, *_xy(pts), pal.get(name, ctx.p.FAINT), label=name,
                     marker="D", ms=4, lw=1.9)
        ax.legend(loc="upper right", fontsize=7.8, ncol=3)
        _foot(ctx, ax, f"share of goods exports in snapshot years "
              f"({', '.join(str(y) for y in sorted({int(y) for y, _, _ in rows if int(y) <= last}))}); "
              f"the 2026 half year is not drawn")
    else:
        _pending(ctx, ax, "destinations not staged")
    _bands(ig, ax)

    ax = ig.slot("trade.lens", "What France exports — top groups (€ bn)")
    _lens(ctx, ax)
    if prods:
        years = sorted({int(y) for y in prods["year"]})
        pick = [y for y in (2006, 2010, 2015, 2020, 2025) if y in years]
        order = ["aeronautics", "chemicals", "electrical", "vehicles",
                 "machinery", "agrifood", "pharma", "metals", "beverages"]
        label = {"aeronautics": "Aeronautics", "pharma": "Pharmaceuticals",
                 "chemicals": "Chemicals & cosmetics",
                 "agrifood": "Agri-food", "beverages": "Wines & spirits",
                 "machinery": "Machinery", "vehicles": "Vehicles",
                 "metals": "Metals", "electrical": "Electrical & electronic"}
        pal = {"aeronautics": ctx.p.BLUE, "pharma": ctx.p.TEAL,
               "chemicals": ctx.p.PURPLE, "agrifood": ctx.p.GREEN,
               "beverages": "#8E2F4A", "machinery": "#7A828E",
               "vehicles": ctx.p.RED, "metals": "#8A6D3B",
               "electrical": ctx.p.GOLD}
        eurbn = {(int(y), p): v for y, p, v
                 in zip(prods["year"], prods["product"], prods["eurbn"])}
        # A snapshot panel, allowed only in the lens slot: the years are
        # unevenly spaced, so the groups sit at categorical positions.
        xs = np.arange(len(pick))
        width = 0.82 / len(order)
        for i, p in enumerate(order):
            vals = [eurbn.get((y, p), 0) for y in pick]
            ax.bar(xs + i * width - 0.82 / 2 + width / 2, vals, width=width,
                   label=label[p], color=pal[p], edgecolor="white",
                   linewidth=0.5, zorder=3)
        ax.legend(fontsize=7.2, ncol=3, loc="upper left")
        ax.set_ylim(0, 108)
        ax.set_ylabel("€ bn", fontsize=8.6, color=ctx.p.muted)
        resid = eurbn.get((pick[-1], "others"), 0)
        if resid:
            _foot(ctx, ax, f"excludes the 'others' residual "
                  f"(€{resid:,.0f}bn in {pick[-1]})")
        ax._pick = pick
    else:
        _pending(ctx, ax, "product detail not staged")

    for i, a in enumerate(ig.axes_flat):
        ig.style_axis(a, xticks_years=i != 3)
    a = ig.axes_flat[3]
    pick = getattr(a, "_pick", None)
    if pick:
        a.set_xticks(np.arange(len(pick)))
        a.set_xticklabels([str(y) for y in pick])
        a.set_xlim(-0.5, len(pick) - 0.5)


# ============================================================== markets
def fig_markets(ctx, ig) -> None:
    rate = ctx.table("macro/policy_rate.csv")
    infl = ctx.table("macro/inflation.csv")
    bonds = ctx.table("markets/bond_yields.csv")
    fx = ctx.table("macro/eurusd.csv")
    cac = ctx.table("markets/cac40.csv")
    sp = ctx.table("markets/sp500.csv")

    ax = ig.slot("markets.policy_rate",
                 "ECB policy rate vs French inflation")
    dfr, ipc = _d(rate, "dfr"), _d(infl, "ipc")
    if dfr:
        ctx.line(ax, *_xy(dfr), ctx.p.NAVY,
                 label="ECB deposit facility rate (year end)")
        if ipc:
            ctx.line(ax, *_xy(ipc), ctx.p.RED, label="Inflation (IPC)")
        ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.90),
                  fontsize=8.2)
        neg = sorted(y for y, v in dfr.items() if v < 0)
        _note(ctx, ax, f"{len(neg)} year ends below zero, "
              f"{neg[0]}–{neg[-1]}", x=0.40, y=0.50, va="bottom")
    else:
        _pending(ctx, ax, "ECB rates not staged")
    _bands(ig, ax, first=True, y=0.97, va="top")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield")
    oat, bund = _d(bonds, "fr_10y"), _d(bonds, "de_10y")
    if oat:
        ctx.line(ax, *_xy(oat), ctx.p.BLUE_D, label="France (OAT)")
        if bund:
            ctx.line(ax, *_xy(bund), ctx.p.FAINT, lw=1.8, ls=(0, (5, 3)),
                     ms=3, label="Germany (Bund), for reference",
                     dashed_partial=False)
        ax.legend(loc="upper right", fontsize=8.2)
        y1 = max(y for y in oat if y in bund)
        spread = {y: oat[y] - bund[y] for y in oat if y in bund}
        _note(ctx, ax, f"spread over the Bund: {spread[2019]:.2f}pt in "
              f"2019, {spread[y1]:.2f}pt in {y1} after the dissolution",
              y=0.80, x=0.98, ha="right")
        yr, what = events.MARKS["dissolution"]
        # The rule is drawn as add_event draws it; the label hangs to its
        # left, because to the right it would leave the panel.
        ax.axvline(yr, color=ctx.p.faint, lw=0.9, ls=(0, (4, 3)),
                   alpha=0.85, zorder=1)
        ax.text(yr - 0.15, 0.62, what, transform=ax.get_xaxis_transform(),
                fontsize=7.8, color=ctx.p.muted, ha="right", va="top")
    else:
        _pending(ctx, ax, "Eurostat irt_lt_mcby_a not staged")
    _bands(ig, ax)

    ax = ig.slot("markets.currency", "The euro against the US$")
    avg = _d(fx, "avg")
    if avg:
        # Quoted as US$ per euro, so a rise is already a stronger euro:
        # rebased, not inverted.
        yrs, idx = ctx.index_2006(avg)
        ctx.line(ax, yrs, idx, ctx.p.TEAL, label="US$ per euro, annual average")
        ctx.endlabel(ax, yrs, idx, ctx.p.TEAL, lambda v: f"{v:.0f}", dy=10)
        hi = max(avg, key=avg.get)
        _note(ctx, ax, f"US$ {avg[2006]:.2f} per euro in 2006, "
              f"{avg[hi]:.2f} at the {hi} peak, "
              f"{avg[ctx.LAST_FULL_YEAR]:.2f} in {ctx.LAST_FULL_YEAR}",
              x=0.02, y=0.06, va="bottom")
    else:
        _pending(ctx, ax, "ECB reference rate not staged")
    _bands(ig, ax)

    ax = ig.slot("markets.equities", "CAC 40 in US$, against the S&P 500")
    usd = _d(fx, "eop")
    c, s = _d(cac, "close"), _d(sp, "close")
    if c and s and usd:
        # Year-end closes at the year-end rate: a dollar investor's CAC.
        cu = {y: c[y] * usd[y] for y in c if y in usd}
        yrs, idx = ctx.index_2006(cu)
        ctx.line(ax, yrs, idx, ctx.p.BLUE_D, label="CAC 40 in US$")
        sy, sv = ctx.index_2006({y: v for y, v in s.items() if y >= 2006})
        ctx.line(ax, sy, sv, ctx.p.RED, lw=2.0, ls=(0, (5, 3)), ms=3,
                 label="S&P 500 (US$)")
        ce, cv = ctx.index_2006({y: v for y, v in c.items() if y >= 2006})
        ctx.line(ax, ce, cv, ctx.p.FAINT, lw=1.6, ms=2.6,
                 label="CAC 40 in euros", dashed_partial=False)
        ax.legend(loc="upper left", fontsize=8.0)
        _foot(ctx, ax, "price indices, dividends excluded; year-end "
              "closes, converted at the year-end rate")
    else:
        _pending(ctx, ax, "index closes not staged")
    _bands(ig, ax)
    _style(ig)


# =============================================================== people
def fig_people(ctx, ig) -> None:
    gini = ctx.table("social/gini.csv")
    pov = ctx.table("social/poverty.csv")
    pwb = ctx.table("social/poverty_wb.csv")
    smic = ctx.table("macro/smic.csv")
    fx = ctx.table("macro/eurusd.csv")
    infl = ctx.table("macro/inflation.csv")

    ax = ig.slot("people.gini", "Income inequality: the Gini coefficient")
    gi, gs = _d(gini, "insee"), _d(gini, "silc")
    if gi:
        ctx.line(ax, *_xy({y: v * 100 for y, v in gi.items()}),
                 ctx.p.PURPLE, label="INSEE (tax-based ERFS survey)")
        if gs:
            ctx.line(ax, *_xy({y: v * 100 for y, v in gs.items()}),
                     ctx.p.FAINT, lw=1.8, label="Eurostat (EU-SILC)",
                     dashed_partial=False)
        ax.legend(loc="upper left", fontsize=8.2)
        y0, y1 = min(gi), max(gi)
        _note(ctx, ax, f"INSEE: {gi[y0] * 100:.1f} in {y0}, "
              f"{gi[y1] * 100:.1f} in {y1}; higher = more unequal",
              x=0.02, y=0.72)
    else:
        _pending(ctx, ax, "Gini not staged")
    _bands(ig, ax, first=True)

    ax = ig.slot("people.poverty", "Poverty rate")
    r60, r50, arop = (_d(pov, "rate60"), _d(pov, "rate50"),
                      _d(pov, "arop60"))
    if r60:
        ctx.line(ax, *_xy(r60), ctx.p.TEAL,
                 label="INSEE, below 60% of the median")
        if arop:
            ctx.line(ax, *_xy(arop), ctx.p.FAINT, lw=1.8,
                     label="Eurostat AROP, 60% (EU-SILC)",
                     dashed_partial=False)
        if r50:
            ctx.line(ax, *_xy(r50), ctx.p.RED, lw=1.9, ms=3.4,
                     label="INSEE, below 50% of the median")
        w = _d(pwb, "poverty_830_pct")
        if w:
            ctx.line(ax, *_xy(w), ctx.p.GOLD, lw=1.8, ms=3.2,
                     label="World Bank, below US$8.30 a day")
        ax.legend(loc="upper left", fontsize=7.8, ncol=2)
        _note(ctx, ax, "relative lines: they move with the median, not "
              "with hardship alone", x=0.98, y=0.52, ha="right",
              va="bottom", size=7.4)
    else:
        _pending(ctx, ax, "poverty not staged")
    _bands(ig, ax)

    ax = ig.slot("people.minimum_wage", "Minimum wage (SMIC), in US$")
    mw, avg = _d(smic, "monthly_eur"), _d(fx, "avg")
    if mw and avg:
        usd = {y: mw[y] * avg[y] for y in mw if y in avg}
        ctx.line(ax, *_xy(usd), ctx.p.GOLD, lw=2.6,
                 label="SMIC, gross, per month, at the annual average rate")
        ctx.endlabel(ax, *_xy(usd), ctx.p.GOLD, lambda v: f"US$ {v:,.0f}",
                     dy=10)
        ax.legend(loc="upper left", fontsize=8.0)
        y1 = ctx.LAST_FULL_YEAR
        _note(ctx, ax, f"€{mw[y1]:,.0f} gross a month in {y1}, for a "
              f"35-hour week", x=0.02, y=0.80)
    else:
        _pending(ctx, ax, "SMIC or exchange rate not staged")
    _bands(ig, ax)

    ax = ig.slot("people.lens", "The SMIC in euros, before and after inflation")
    _lens(ctx, ax)
    ipc = _d(infl, "ipc")
    if mw and ipc:
        ax.set_ylabel("€ per month, gross", fontsize=8.6, color=ctx.p.muted)
        ctx.line(ax, *_xy(mw), ctx.p.GOLD, lw=2.6, label="Nominal")
        # Deflated with the IPC to euros of the last full year, which is
        # the index the SMIC itself is indexed on.
        base = ctx.LAST_FULL_YEAR
        # The price level of each year, from the IPC's annual-average
        # changes: P(y) = P(y-1) × (1 + inflation in y).
        level = {min(ipc): 1.0}
        for y in sorted(ipc)[1:]:
            level[y] = level[y - 1] * (1 + ipc[y] / 100)
        real = {y: mw[y] * level[base] / level[y]
                for y in mw if y in level and y <= base}
        ctx.line(ax, *_xy(real), "#8A6D3B", lw=2.2,
                 label=f"In {base} euros (IPC-deflated)")
        ctx.endlabel(ax, *_xy(mw), ctx.p.GOLD, lambda v: f"€{v:,.0f}", dy=10)
        ax.legend(loc="upper left", fontsize=8.2)
        y0 = min(real)
        _note(ctx, ax, f"in real terms: €{real[y0]:,.0f} in {y0}, "
              f"€{real[base]:,.0f} in {base}", x=0.98, y=0.08, ha="right",
              va="bottom")
        ax.set_ylim(1000, 2100)
    else:
        _pending(ctx, ax, "SMIC or IPC not staged")
    _bands(ig, ax)
    _style(ig)


# ================================================================ world
def fig_world(ctx, ig) -> None:
    wb = ctx.table("international/world_wb.csv")
    hdi = ctx.table("social/hdi.csv")
    cpi = ctx.table("international/cpi.csv")
    res = ctx.table("macro/reserves.csv")

    ax = ig.slot("world.gdp", "GDP at current prices")
    g = _d(wb, "gdp_usd_bn")
    if g:
        ctx.line(ax, *_xy(g), ctx.p.BLUE_D, label="World Bank, current US$")
        ctx.endlabel(ax, *_xy(g), ctx.p.BLUE_D, lambda v: f"US$ {v:,.0f}bn",
                     dy=10)
        drop = min((y for y in g if y - 1 in g),
                   key=lambda y: g[y] / g[y - 1])
        _note(ctx, ax, f"{drop}: {(g[drop] / g[drop - 1] - 1) * 100:+.0f}% "
              f"in dollars, from the euro alone", x=0.02, y=0.20,
              va="bottom")
    else:
        _pending(ctx, ax, "World Bank series not staged")
    _bands(ig, ax, first=True)

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    h = _d(hdi, "value")
    if h:
        ctx.line(ax, *_xy(h), ctx.p.GREEN_D, split_year=max(h))
        ctx.endlabel(ax, *_xy(h), ctx.p.GREEN_D, lambda v: f"{v:.3f}", dy=10)
        ax.axhline(0.9, color=ctx.p.FAINT, lw=0.9, ls=":", zorder=1)
        _note(ctx, ax, "0.900 = very high development", x=0.98, y=0.78,
              ha="right", size=7.4)
        ig.add_event(ax, events.MARKS["covid"][0], "pandemic dip", dy=0.42)
        _note(ctx, ax, f"the HDR 2025, the latest edition, runs to {max(h)}", x=0.02, y=0.06, va="bottom", size=7.4,
              color=ctx.p.faint)
    else:
        _pending(ctx, ax, "HDI not staged")
    _bands(ig, ax)

    ax = ig.slot("world.cpi", "Corruption Perceptions Index")
    sc = _d(cpi, "score")
    if sc:
        # 2006-2011 came on a 0-10 scale and TI says only 2012 onwards are
        # comparable: the old scores are shown ×10 as their own segment.
        old = {y: v * 10 for y, v in sc.items() if y < 2012}
        new = {y: v for y, v in sc.items() if y >= 2012}
        if old:
            ctx.line(ax, *_xy(old), ctx.p.FAINT, lw=1.9, ms=3.4,
                     label="2006–11 score ×10 (old method)",
                     dashed_partial=False)
        ctx.line(ax, *_xy(new), ctx.p.TEAL, split_year=max(new),
                 label="2012 method, 0–100")
        ctx.endlabel(ax, *_xy(new), ctx.p.TEAL, lambda v: f"{v:.0f}", dy=-18)
        ax.legend(loc="lower left", fontsize=8.0)
        y1 = max(new)
        if new[y1] == min(new.values()):
            text = (f"{new[y1]:.0f} in {y1}, the lowest since the 2012 "
                    f"method; higher = cleaner")
        else:
            text = f"{new[y1]:.0f} in {y1}; higher = cleaner"
        _note(ctx, ax, text, x=0.98, y=0.96, ha="right")
    else:
        _pending(ctx, ax, "CPI not staged")
    _bands(ig, ax)

    ax = ig.slot("world.reserves", "Official reserves, gold included")
    rv = _d(res, "eop_usdbn")
    if rv:
        ctx.line(ax, *_xy(rv), ctx.p.GREEN_D, label="IMF reserve template, "
                 "year end")
        ctx.endlabel(ax, *_xy(rv), ctx.p.GREEN_D,
                     lambda v: f"US$ {v:,.0f}bn", dy=10)
        y1 = max(rv)
        _note(ctx, ax, f"mostly gold, revalued at market prices: "
              f"{(rv[y1] / rv[y1 - 1] - 1) * 100:+.0f}% in {y1}",
              x=0.02, y=0.06, va="bottom")
    else:
        _pending(ctx, ax, "reserves not staged")
    _bands(ig, ax)
    _style(ig)


# ========================================================== demography
def fig_demographics(ctx, ig) -> None:
    vit = ctx.table("social/vital_rates.csv")
    pop = ctx.table("social/population.csv")
    last = ctx.LAST_FULL_YEAR

    ax = ig.slot("demography.population", "Population")
    jan = _d(vit, "pop_jan")
    if jan:
        yrs, idx = ctx.index_2006(jan)
        d = dict(zip(yrs, idx))
        # Mayotte enters the count on 1 January 2014: a seam, not growth.
        _seam(ctx, ax, d, 2014, ctx.p.BLUE, label="1 January, INSEE")
        ctx.endlabel(ax, yrs, idx, ctx.p.BLUE,
                     lambda v: f"{jan[yrs[-1]] / 1e6:.1f}M", dy=10)
        proj = _d(pop, "pop_mn")
        peak = max((y for y in proj if y > yrs[-1]), key=proj.get)
        _note(ctx, ax, f"INSEE central projection: peak {proj[peak]:.1f}M "
              f"in {peak}, then decline", y=0.96)
        _note(ctx, ax, "2014: Mayotte enters the count", x=0.02, y=0.86,
              size=7.4, color=ctx.p.faint)
    else:
        _pending(ctx, ax, "population not staged")
    _bands(ig, ax, first=True)

    ax = ig.slot("demography.fertility", "Total fertility rate")
    tfr = {y: v for y, v in _upto(_d(pop, "tfr"), last).items()
           if y >= ctx.YEARS[0]}
    if tfr:
        ax.axhline(2.1, color=ctx.p.MUTED, lw=1.1, ls=(0, (5, 4)), zorder=2)
        ctx.line(ax, *_xy(tfr), ctx.p.RED)
        lo, hi = min(tfr, key=tfr.get), max(tfr, key=tfr.get)
        ax.annotate(f"{tfr[lo]:.2f} ({lo})", (lo, tfr[lo]),
                    textcoords="offset points", xytext=(-4, -16),
                    ha="right", fontsize=8.6, fontweight="bold",
                    color=ctx.p.RED)
        _note(ctx, ax, "replacement level 2.1", y=0.75, size=7.6)
        _note(ctx, ax, f"from {tfr[hi]:.2f} in {hi}: the lowest since the "
              f"Second World War", x=0.02, y=0.10, va="bottom")
    else:
        _pending(ctx, ax, "fertility not staged")
    _bands(ig, ax)

    ax = ig.slot("demography.birth_death", "Crude birth and death rates")
    br, dr = _d(vit, "birth_rate"), _d(vit, "death_rate")
    if br and dr:
        ctx.line(ax, *_xy(br), ctx.p.GREEN_D, label="Births per 1,000")
        ctx.line(ax, *_xy(dr), ctx.p.INK, label="Deaths per 1,000")
        ax.legend(loc="upper right", fontsize=8.2)
        cross = next((y for y in sorted(dr) if y in br and dr[y] > br[y]),
                     None)
        if cross:
            ax.axvline(cross, color=ctx.p.FAINT, lw=0.9, ls=(0, (4, 3)),
                       zorder=1)
            _note(ctx, ax, f"{cross}: deaths overtake births, a first "
                  f"since the war", x=0.98, y=0.16, ha="right",
                  va="bottom")
    else:
        _pending(ctx, ax, "vital statistics not staged")
    _bands(ig, ax)

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net migration")
    nat, mig = _d(vit, "natural_rate"), _d(vit, "net_migration_rate")
    if nat:
        ctx.line(ax, *_xy(nat), ctx.p.GREEN_D,
                 label="Natural increase (births − deaths)")
        if mig:
            ctx.line(ax, *_xy(mig), ctx.p.PURPLE, label="Net migration")
        ax.legend(loc="upper right", fontsize=8.2)
        y1 = max(nat)
        _note(ctx, ax, f"{y1}: natural increase {nat[y1]:+.1f} per 1,000, "
              f"migration {mig[y1]:+.1f}", x=0.02, y=0.06, va="bottom")
        _foot(ctx, ax, "net migration as Eurostat publishes it, statistical "
              "adjustment included")
    else:
        _pending(ctx, ax, "vital statistics not staged")
    _bands(ig, ax)
    _style(ig)


# ============================================================ security
def fig_security(ctx, ig) -> None:
    hom = ctx.table("social/homicides.csv")
    who = ctx.table("social/security_wb.csv")
    cod = ctx.table("social/causes.csv")
    vio = ctx.table("social/violence.csv")
    fem = ctx.table("social/population_wb.csv")
    pop = _avg_pop(ctx)

    ax = ig.slot("security.homicide",
                 "Homicide rate — the two systems, and UNODC")
    ss, cc = _d(hom, "ssmsi_rate"), _d(hom, "cepidc_rate")
    un = _d(who, "homicide_unodc")
    if ss or cc:
        if un:
            ctx.line(ax, *_xy(un), ctx.p.FAINT, lw=1.7, ms=3,
                     label="UNODC (harmonised)", dashed_partial=False)
        if ss:
            ctx.line(ax, *_xy(ss), ctx.p.RED, label="SSMSI — recorded by police")
        if cc:
            ctx.line(ax, *_xy(cc), ctx.p.INK, lw=2.0, ls=(0, (5, 3)), ms=3.4,
                     label="CépiDc — death certificates",
                     dashed_partial=False)
        ax.legend(loc="upper left", fontsize=8.0)
        ig.add_event(ax, 2015, "2015: November attacks (130 deaths)",
                     dy=0.70)
        _note(ctx, ax, "two systems, never spliced: what the police "
              "recorded, and what a doctor certified", x=0.98, y=0.14,
              ha="right", va="bottom", size=7.4)
    else:
        _pending(ctx, ax, "homicides not staged")
    _bands(ig, ax, first=True)

    ax = ig.slot("security.suicide", "Suicide rate")
    sn, sw = _d(cod, "suicide_rate"), _d(who, "suicide_who")
    if sn or sw:
        if sw:
            ctx.line(ax, *_xy(sw), ctx.p.FAINT, lw=1.8, ms=3,
                     label="WHO estimate, age-standardised",
                     dashed_partial=False)
        if sn:
            ctx.line(ax, *_xy(sn), ctx.p.PURPLE,
                     label="CépiDc death certificates, crude")
        ax.legend(loc="upper right", fontsize=8.2)
        y1 = max(sn)
        _note(ctx, ax, f"{_d(cod, 'suicide_count')[y1]:,.0f} certified "
              f"suicides in {y1}; WHO adds a correction for under-recording",
              x=0.02, y=0.10, va="bottom")
    else:
        _pending(ctx, ax, "suicide not staged")
    _bands(ig, ax)

    ax = ig.slot("security.road_deaths", "Road traffic deaths")
    rp, rw = _d(cod, "road_per_million"), _d(who, "road_who")
    if rp:
        if rw:
            ctx.line(ax, *_xy(rw), ctx.p.FAINT, lw=1.8, ms=3,
                     label="WHO estimate", dashed_partial=False)
        # Eurostat publishes the rate per million; ÷10 is per 100,000.
        ctx.line(ax, *_xy({y: v / 10 for y, v in rp.items()}), ctx.p.GOLD,
                 label="ONISR, killed within 30 days")
        ax.legend(loc="upper right", fontsize=8.2)
        k = _d(cod, "road_killed")
        y1 = max(k)
        _note(ctx, ax, f"{k[2006]:,.0f} killed in 2006, {k[y1]:,.0f} in "
              f"{y1}; metropolitan France", x=0.02, y=0.10, va="bottom")
    else:
        _pending(ctx, ax, "road deaths not staged")
    _bands(ig, ax)

    # The lens: deaths within the couple. The count of women killed is put
    # over the female population of the same year; the share is the women
    # among all deaths within the couple, which also counts men.
    ax = ig.slot("security.lens",
                 "Deaths within the couple: women killed per 100,000 women")
    _lens(ctx, ax)
    women = _d(vio, "women_killed_by_partner")
    total = _d(vio, "couple_deaths_total")
    fpop = _d(fem, "population_female")
    if women and fpop:
        ax.set_ylabel("per 100,000 women", fontsize=8.6, color=ctx.p.muted)
        wy, wr = ctx.per_100k(women, fpop)
        ax.fill_between(wy, 0, wr, color=ctx.p.RED, alpha=0.45, lw=0,
                        zorder=3)
        ax.plot(wy, wr, color=ctx.p.RED, lw=2.2, zorder=4)
        ax.text(0.02, 0.52, "women killed by a partner or ex-partner",
                transform=ax.transAxes, fontsize=8.2, fontweight="bold",
                color=ctx.p.RED, va="bottom")
        ax.set_ylim(0, 1.2)
        share_ax = ax.twinx()
        share = {y: women[y] / total[y] * 100 for y in women
                 if y in total and total[y]}
        shy, shv = _xy(share)
        share_ax.plot(shy, shv, color=ctx.p.PURPLE, lw=1.8, ls=(0, (4, 2)),
                      zorder=5)
        share_ax.text(0.98, 0.73, "women's share of all deaths within "
                      "the couple, % (right axis)", transform=ax.transAxes,
                      ha="right", va="top", fontsize=7.8, fontweight="bold",
                      color=ctx.p.PURPLE)
        share_ax.set_ylim(0, 100)
        share_ax.tick_params(axis="y", colors=ctx.p.PURPLE, labelsize=8.2,
                             length=0)
        share_ax.spines[["top", "left", "right"]].set_visible(False)
        share_ax.grid(False)
        share_ax.set_xlim(ctx.YEARS[0] - 0.6, ctx.YEARS[-1] + 0.6)
        share_ax.xaxis.set_visible(False)
        share_ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
        y1 = max(women)
        _note(ctx, ax, f"{y1}: {women[y1]:.0f} women and "
              f"{total[y1] - women[y1]:.0f} men killed within the couple",
              x=0.02, y=0.60, size=7.6)
        # Recorded assault, per 1,000 people: a police count of complaints,
        # so it measures reporting as much as violence.
        a = _d(vio, "assaults")
        sx = _d(vio, "sexual_violence")
        if a:
            ay, ar = ctx.per_1000(a, pop)
            xy_, xr = ctx.per_1000(sx, pop)
            _note(ctx, ax, f"recorded assault: {ar[0]:.1f} victims per "
                  f"1,000 people in {ay[0]}, {ar[-1]:.1f} in {ay[-1]}; "
                  f"sexual violence {xr[0]:.1f} to {xr[-1]:.1f}",
                  x=0.02, y=0.66, size=7.4)
            _foot(ctx, ax, "recorded offences: the rise since 2017 is "
                  "substantially a change in reporting, not a measured rate")
    else:
        _pending(ctx, ax, "couple deaths or female population not staged")
    _bands(ig, ax)
    _style(ig)


# =========================================================== mortality
def fig_mortality(ctx, ig) -> None:
    """All-cause deaths, excess deaths, COVID-19 and influenza.

    Almost every number here is a different quantity wearing the same
    word. "COVID deaths" is a count of infected patients who died in one
    series and an underlying cause of death in another; "flu deaths" is a
    coded certificate in one column and a modelled attribution in the
    next. None of them is added, averaged or drawn as one line.
    """
    vit = ctx.table("social/vital_rates.csv")
    allc = ctx.table("social/all_cause_deaths.csv")
    covid = ctx.table("social/covid_deaths.csv")
    flu = ctx.table("social/flu_deaths.csv")
    pop = _avg_pop(ctx)
    last = ctx.LAST_FULL_YEAR

    ax = ig.slot("mortality.death_rate", "Crude death rate")
    dr = _d(vit, "death_rate")
    if dr:
        ctx.line(ax, *_xy(dr), ctx.p.INK, label="Deaths per 1,000 people")
        ctx.endlabel(ax, *_xy(dr), ctx.p.INK, lambda v: f"{v:.1f}", dy=10)
        peak = max(dr, key=dr.get)
        _note(ctx, ax, f"{dr[peak]:.1f} in {peak}, the first COVID year; "
              f"the trend rises as the population ages", x=0.02, y=0.30)
        _note(ctx, ax, "2014: Mayotte enters the count and its population",
              x=0.02, y=0.20, size=7.4, color=ctx.p.faint)
    else:
        _pending(ctx, ax, "vital statistics not staged")
    _bands(ig, ax, first=True)

    ax = ig.slot("mortality.excess_deaths", "Excess deaths")
    deaths = _upto(_d(allc, "insee"), last)
    base_years = [y for y in range(2015, 2020) if y in deaths]
    if len(base_years) == 5:
        base = sum(deaths[y] for y in base_years) / 5
        ex = {y: (v / base - 1) * 100 for y, v in deaths.items() if y >= 2015}
        ctx.bars(ax, *_xy(ex), lambda v: ctx.p.RED if v > 0 else ctx.p.GREEN_D)
        for y, v in ex.items():
            if v >= 10:
                ax.annotate(f"{v:+.1f}%", (y, v), textcoords="offset points",
                            xytext=(0, 4), ha="center", fontsize=8.2,
                            fontweight="bold", color=ctx.p.RED)
        _note(ctx, ax, f"all deaths against the 2015–19 mean "
              f"({base:,.0f} a year)", x=0.02, y=0.96)
        _note(ctx, ax, "no age standardisation: part of every bar after "
              "2019 is an older population", x=0.02, y=0.86, size=7.4,
              color=ctx.p.faint)
    else:
        _pending(ctx, ax, "all-cause deaths not staged")
    _bands(ig, ax)

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause")
    cep = _d(covid, "deaths_cepidc")
    tot, hosp = _d(covid, "deaths_total"), _d(covid, "deaths_hospital")
    if cep:
        ty, tv = ctx.per_100k(tot, pop)
        hy, hv = ctx.per_100k(hosp, pop)
        cy, cv = ctx.per_100k(cep, pop)
        ax.bar(ty, tv, width=0.58, color=ctx.p.BLUE, alpha=0.28,
               edgecolor=ctx.p.BLUE, linewidth=0.8, zorder=2,
               label="SPF surveillance: hospital + care homes")
        ax.bar(hy, hv, width=0.58, color=ctx.p.BLUE_D, zorder=3,
               label="SPF surveillance: in hospital")
        ctx.line(ax, cy, cv, ctx.p.RED, lw=2.6, zorder=4,
                 label="CépiDc: COVID-19 as the underlying cause")
        ax.legend(loc="upper left", fontsize=7.8)
        _note(ctx, ax, "the certified count is the larger one: it sees "
              "deaths at home,\nwhich the surveillance never did; it "
              "stopped on 30 June 2023", x=0.02, y=0.62, size=7.4)
        _foot(ctx, ax, "CépiDc covers metropolitan France and five DROM, "
              "SPF all of France; both over the whole population")
    else:
        _pending(ctx, ax, "COVID deaths not staged")
    _bands(ig, ax)

    ax = ig.slot("mortality.lens", "Influenza deaths — certified vs estimated")
    _lens(ctx, ax)
    fc = _d(flu, "deaths_cepidc")
    fm = _d(flu, "excess_deaths_spf")
    fx = {y: v for y, v in _d(flu, "excess_all_cause_epidemic_spf").items()
          if v > 0}
    if fc:
        # Seasons are labelled by the year they end in and put over that
        # calendar year's average population.
        xy_, xv = ctx.per_100k({y: v for y, v in fx.items() if y in pop}, pop)
        my, mv = ctx.per_100k(fm, pop)
        cy, cv = ctx.per_100k(fc, pop)
        ax.plot(xy_, xv, ls="none", marker="s", ms=6.5, mfc="none",
                mec=ctx.p.FAINT, mew=1.4, zorder=3,
                label="SPF: all-cause excess in the epidemic window")
        ax.plot(my, mv, ls="none", marker="D", ms=7, color=ctx.p.GOLD,
                zorder=4, label="SPF model: deaths attributable to flu")
        ax.bar(cy, cv, width=0.6, color=ctx.p.PURPLE, zorder=5,
               label="CépiDc: certified as the underlying cause")
        ax.legend(loc="upper left", fontsize=7.8)
        ax.set_ylim(0, max(xv + mv + cv) * 1.45)
        if my:
            ax.axvline(max(my) + 0.5, color=ctx.p.FAINT, lw=0.9,
                       ls=(0, (4, 3)), zorder=1)
            _note(ctx, ax, f"SPF dropped the model after the "
                  f"{max(my) - 1}-{str(max(my))[2:]} season", x=0.98,
                  y=0.80, ha="right", size=7.4)
        _foot(ctx, ax, "an order of magnitude apart because they answer "
              "different questions; seasons by the year they end")
    else:
        _pending(ctx, ax, "influenza deaths not staged")
    _bands(ig, ax)
    _style(ig)


# ============================================================== credit
def fig_credit(ctx, ig) -> None:
    """What borrowing costs, how much households carry, and who is
    drowning in it. Every leverage ratio fell after 2022 while
    over-indebtedness filings rose by about a third; both are true, and
    the plate shows both."""
    debt = ctx.table("credit/household_debt.csv")
    rates = ctx.table("credit/lending_rates.csv")
    pol = ctx.table("macro/policy_rate.csv")
    npl = ctx.table("credit/npl.csv")
    sur = ctx.table("credit/overindebtedness.csv")

    ax = ig.slot("credit.household_debt", "Household debt")
    hd = _d(debt, "hh_debt_pct_gdp_bis_q4")
    if hd:
        ctx.line(ax, *_xy(hd), ctx.p.RED, label="BIS, credit to households, Q4")
        ctx.endlabel(ax, *_xy(hd), ctx.p.RED, lambda v: f"{v:.1f}%", dy=10)
        peak = max(hd, key=hd.get)
        gdi = _d(debt, "hh_debt_pct_gdi_ecb_nco_q4")
        y1 = max(gdi)
        ax.legend(loc="upper left", fontsize=8.2)
        _note(ctx, ax, f"peak {hd[peak]:.1f}% in {peak}; {gdi[y1]:.0f}% of "
              f"disposable income in {y1}, the Banque de France's measure",
              x=0.02, y=0.20, va="bottom", size=7.6)
    else:
        _pending(ctx, ax, "BIS household credit not staged")
    _bands(ig, ax, first=True)

    ax = ig.slot("credit.lending_rate",
                 "Mortgage rates, new and on the stock, vs the ECB rate")
    if rates:
        hy, hv = ctx.full_years(*ctx.series(rates, "housing_new_total_pct"))
        sy, sv = ctx.full_years(*ctx.series(rates,
                                            "housing_outstanding_stock_pct"))
        ctx.line(ax, hy, hv, ctx.p.BLUE_D, label="New housing loans")
        ctx.line(ax, sy, sv, ctx.p.GOLD, lw=2.0, ls=(0, (5, 3)),
                 label="Rate carried by the outstanding stock",
                 dashed_partial=False)
        dfr = _d(pol, "dfr")
        if dfr:
            ctx.line(ax, *_xy(dfr), ctx.p.NAVY, lw=1.6, ms=3,
                     label="ECB deposit rate (year end)")
        ax.legend(loc="upper right", fontsize=7.8)
        _note(ctx, ax, "98.5% of the stock is fixed-rate, so a rate shock "
              "barely touches it", x=0.02, y=0.96, size=7.6)
        _foot(ctx, ax, "MIR annual averages of monthly rates; the 2026 "
              "part-year is not drawn")
    else:
        _pending(ctx, ax, "MIR rates not staged")
    _bands(ig, ax)

    ax = ig.slot("credit.npl", "Non-performing loans")
    fsi, ssm = _d(npl, "npl_fsi_pct"), _d(npl, "npl_ssm_pct")
    if fsi or ssm:
        if fsi:
            ctx.line(ax, *_xy(fsi), ctx.p.RED,
                     label="IMF FSI, all deposit takers")
        if ssm:
            ctx.line(ax, *_xy(ssm), ctx.p.NAVY, lw=2.0, ls=(0, (5, 3)),
                     label="ECB supervision, significant banks",
                     dashed_partial=False)
        ax.legend(loc="upper right", fontsize=8.0)
        peak = max(fsi, key=fsi.get)
        _note(ctx, ax, f"peak {fsi[peak]:.1f}% in {peak}, after the euro "
              f"crisis; % of gross loans, year end", x=0.02, y=0.62,
              size=7.6)
    else:
        _pending(ctx, ax, "NPL ratios not staged")
    _bands(ig, ax)

    ax = ig.slot("credit.lens", "Over-indebtedness filings (thousands)")
    _lens(ctx, ax)
    if sur:
        ax.set_ylabel("dossiers filed, thousands", fontsize=8.6,
                      color=ctx.p.muted)
        fy, fv = ctx.full_years(*ctx.series(sur, "dossiers_deposes_published"))
        wy, wv = ctx.full_years(*ctx.series(sur, "dossiers_deposes_webstat"))
        # Two sources for one count, drawn as two kinds of bar: the
        # printed figure (2007-18, 2022-25) and the machine-readable
        # series that covers the years in between.
        only_web = [(y, v) for y, v in zip(wy, wv) if y not in set(fy)]
        if only_web:
            ctx.bars(ax, [y for y, _ in only_web],
                     [v / 1000 for _, v in only_web], lambda v: ctx.p.paper,
                     hatch_partial=False, edge=ctx.p.GOLD)
        ctx.bars(ax, fy, [v / 1000 for v in fv], lambda v: ctx.p.GOLD,
                 hatch_partial=False)
        peak = max(zip(fy, fv), key=lambda t: t[1])
        ax.annotate(f"{peak[1] / 1000:,.0f}k", (peak[0], peak[1] / 1000),
                    textcoords="offset points", xytext=(0, 4), ha="center",
                    fontsize=8.4, fontweight="bold", color=ctx.p.INK)
        if only_web:
            _note(ctx, ax, f"hollow bars, {only_web[0][0]}–{only_web[-1][0]}: "
                  f"no printed figure,\nthe Banque de France's Webstat "
                  f"series instead", x=0.98, y=0.96, ha="right", size=7.4)
        dsr = _d(debt, "hh_debt_service_ratio_pct_bis_qavg")
        y1 = max(y for y in dsr if y <= ctx.LAST_FULL_YEAR)
        _note(ctx, ax, f"filings rose after 2022 while the debt-service "
              f"ratio fell to {dsr[y1]:.1f}% of income ({y1}):\ndifferent "
              f"households, not a contradiction", x=0.98, y=0.84,
              ha="right", size=7.4)
        ax.set_ylim(0, 340)
    else:
        _pending(ctx, ax, "filings not staged")
    _bands(ig, ax)
    _style(ig)


# ============================================================ migration
def fig_migration(ctx, ig) -> None:
    mig = ctx.table("migration/migration.csv")
    vit = ctx.table("social/vital_rates.csv")
    pop = _avg_pop(ctx)

    ax = ig.slot("migration.flows", "Immigration and emigration")
    imm, emi = _d(mig, "immigration"), _d(mig, "emigration")
    if imm and emi:
        iy, ir = ctx.per_1000(imm, pop)
        ey, er = ctx.per_1000(emi, pop)
        ctx.line(ax, iy, ir, ctx.p.BLUE_D, label="Immigration")
        ctx.line(ax, ey, er, ctx.p.RED, label="Emigration")
        ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.90),
                  fontsize=8.2, ncol=2)
        y1 = max(imm)
        _note(ctx, ax, f"{y1}: {imm[y1]:,.0f} arrivals and {emi[y1]:,.0f} "
              f"departures, French citizens included", x=0.02, y=0.74,
              size=7.6)
        _foot(ctx, ax, "INSEE estimates reported to Eurostat; over the "
              "average population of the year")
    else:
        _pending(ctx, ax, "Eurostat migration flows not staged")
    _bands(ig, ax, first=True, y=0.97, va="top")

    ax = ig.slot("migration.net", "Net migration")
    net = _d(vit, "net_migration_rate")
    if net:
        ctx.line(ax, *_xy(net), ctx.p.PURPLE,
                 label="Eurostat, adjustment included")
        if imm and emi:
            ny, nv = ctx.per_1000({y: imm[y] - emi[y] for y in imm
                                   if y in emi}, pop)
            ctx.line(ax, ny, nv, ctx.p.FAINT, lw=1.7, ms=3,
                     label="Immigration minus emigration",
                     dashed_partial=False)
        ax.legend(loc="upper left", fontsize=8.2)
        lo = min(net, key=net.get)
        _note(ctx, ax, f"{lo}: {net[lo]:+.1f} per 1,000, the low of the "
              f"window; the gap between the lines is the statistical "
              f"adjustment", x=0.02, y=0.08, va="bottom", size=7.4)
    else:
        _pending(ctx, ax, "net migration not staged")
    _bands(ig, ax)

    ax = ig.slot("migration.foreign_born",
                 "Foreign-born and foreign-citizen shares")
    fb, tb = _d(mig, "foreign_born"), _d(mig, "pop_by_birth")
    nat, tc = _d(mig, "nationals"), _d(mig, "pop_by_citizenship")
    if fb and tb:
        born = {y: fb[y] / tb[y] * 100 for y in fb if y in tb}
        ctx.line(ax, *_xy(born), ctx.p.TEAL, label="Born abroad")
        cit = {y: (tc[y] - nat[y]) / tc[y] * 100 for y in nat if y in tc}
        ctx.line(ax, *_xy(cit), ctx.p.GOLD, label="Foreign citizens")
        ctx.endlabel(ax, *_xy(born), ctx.p.TEAL, lambda v: f"{v:.1f}%",
                     dy=8)
        ax.legend(loc="upper left", fontsize=8.2, ncol=2)
        _note(ctx, ax, "born abroad includes French citizens born abroad; "
              "INSEE's 'immigrés'\n(born abroad as foreigners) is a "
              "narrower count", x=0.02, y=0.80, size=7.4)
        _foot(ctx, ax, "1 January stocks, Eurostat migr_pop3ctb and "
              "migr_pop1ctz")
    else:
        _pending(ctx, ax, "population by birth not staged")
    _bands(ig, ax)

    ax = ig.slot("migration.lens",
                 "Permits, asylum and citizenship (thousands a year)")
    _lens(ctx, ax)
    per = _d(mig, "first_permits")
    asy = _d(mig, "asylum_first_time")
    acq = _d(mig, "citizenship_acquired")
    if per or asy:
        ax.set_ylabel("thousands", fontsize=8.6, color=ctx.p.muted)
        k = lambda d: {y: v / 1000 for y, v in d.items()}  # noqa: E731
        ctx.line(ax, *_xy(k(per)), ctx.p.BLUE_D,
                 label="First residence permits")
        ctx.line(ax, *_xy(k(asy)), ctx.p.RED,
                 label="First-time asylum applicants")
        ctx.line(ax, *_xy(k(acq)), ctx.p.GREEN_D,
                 label="Acquisitions of citizenship")
        ax.legend(loc="upper left", fontsize=8.0)
        ax.set_ylim(0, 420)
        y1 = max(per)
        _note(ctx, ax, f"{per[y1]:,.0f} first permits in {y1}", x=0.98,
              y=0.08, ha="right", va="bottom", size=7.6)
    else:
        _pending(ctx, ax, "permits and asylum not staged")
    _bands(ig, ax)
    _style(ig)


# --------------------------------------------------------------- plates
_SRC = {
    "economy": ("INSEE / Eurostat — national accounts (ESA 2010)",
                "World Bank WDI (US$)", "INSEE (IPC) · Eurostat (HICP)",
                "INSEE — enquête Emploi"),
    "fiscal": ("Eurostat — gov_10a_main, EDP notification",
               "INSEE — prélèvements obligatoires"),
    "spending": ("Eurostat gov_10a_exp — COFOG, general government",
                 "Eurostat nama_10_gdp / gov_10a_main (investment)"),
    "trade": ("INSEE / Eurostat — national accounts (P6, P7)",
              "Douanes/DGDDI — goods, FAB/FAB, A129, destinations"),
    "markets": ("ECB — deposit facility and reference rates",
                "Eurostat irt_lt_mcby_a", "INSEE (IPC)",
                "Euronext / S&P — index closes (price indices)"),
    "people": ("INSEE ERFS / Eurostat EU-SILC",
               "World Bank PIP", "INSEE / Légifrance (SMIC)", "ECB"),
    "world": ("World Bank WDI", "UNDP HDR 2025",
              "Transparency International", "IMF reserve template"),
    "demography": ("INSEE via Eurostat demo_gind",
                   "INSEE — Bilan démographique, Projections 2021-2070"),
    "security": ("SSMSI", "Inserm-CépiDc (via Eurostat)",
                 "UNODC / WHO via World Bank", "ONISR via Eurostat CARE",
                 "Ministère de l'Intérieur"),
    "mortality": ("INSEE — état civil", "Santé publique France",
                  "Inserm-CépiDc via DREES"),
    "credit": ("BIS", "ECB — MIR, supervisory statistics",
               "IMF FSI via World Bank", "Banque de France"),
    "migration": ("Eurostat — migr_imm1ctz, migr_emi1ctz, migr_pop3ctb, "
                  "migr_pop1ctz, migr_resfirst, migr_asyappctza, migr_acq",),
}


def _src(topic):
    return "Sources: " + " · ".join(_SRC[topic])


# The plates, in the order the page lists them. The slug is the chapter
# id, so the files keep the names the page and the links already use.
PLATES = (
    dict(slug="01_economy", topic="economy", builder=fig_economy,
         title="The French Economy, 2006–2026",
         subtitle="Two recessions in twenty years, a decade of near-zero "
                  "inflation ended by the energy shock, and unemployment "
                  "back to its pre-crisis level only in 2022.",
         source=_src("economy"),
         alt="Four panels: real GDP growth by year, GDP per person in "
             "current US dollars, consumer price inflation against the "
             "ECB's 2% aim, and the unemployment rate."),
    dict(slug="02_fiscal", topic="fiscal", builder=fig_fiscal,
         title="Taxes, the Deficit & Public Debt, 2006–2026",
         subtitle="France collects more of its economy in tax than any "
                  "other EU country, and has still not balanced a budget "
                  "since 1974.",
         source=_src("fiscal"),
         alt="Four panels: general-government revenue, expenditure and "
             "compulsory levies as a share of GDP; the overall and primary "
             "balance; gross Maastricht debt; and interest paid."),
    dict(slug="03_spending", topic="spending", builder=fig_spending,
         title="Where the Money Goes — Public Spending by Function, "
               "2006–2024",
         subtitle="Social protection is about two-fifths of everything the "
                  "state spends; investment has barely moved in twenty "
                  "years.",
         source=_src("spending"),
         alt="Four panels: public spending by COFOG function, stacked; "
             "social protection against all other functions; whole-economy "
             "investment; and public investment, all as a share of GDP."),
    dict(slug="04_trade", topic="trade", builder=fig_trade,
         title="Foreign Trade — a Deficit That Became Structural, 2006–2026",
         subtitle="France ran a goods surplus until 2003. Services now cover "
                  "most of a goods deficit that the 2022 energy bill turned "
                  "into a record.",
         source=_src("trade"),
         alt="Four panels: exports and imports of goods and services as a "
             "share of GDP; the trade balance, with goods alone; the share "
             "of goods exports going to the largest destinations; and "
             "exports by product group in five snapshot years."),
    dict(slug="05_markets", topic="markets", builder=fig_markets,
         title="Money & Markets — ECB Rates, the OAT, the Euro and the "
               "CAC 40",
         subtitle="Eight years of negative policy rates, a bond spread "
                  "that widened with the 2024 dissolution, and a stock "
                  "market that trailed Wall Street in any currency.",
         source=_src("markets"),
         alt="Four panels: the ECB deposit rate against French inflation; "
             "the ten-year OAT yield with the Bund; the euro against the "
             "dollar as an index; and the CAC 40 in dollars against the "
             "S&P 500."),
    dict(slug="06_people", topic="people", builder=fig_people,
         title="People — Inequality, Poverty and the Minimum Wage, "
               "2006–2026",
         subtitle="Slowly rising inequality, a poverty rate that has not "
                  "improved in twenty years, and a minimum wage that kept "
                  "pace with prices.",
         source=_src("people"),
         alt="Four panels: the Gini coefficient from INSEE and EU-SILC; "
             "poverty rates at 60% and 50% of the median and at US$8.30 a "
             "day; the SMIC in US dollars; and the SMIC in euros before and "
             "after inflation."),
    dict(slug="07_world", topic="world", builder=fig_world,
         title="France in the World — Size, Development, Corruption & "
               "Reserves",
         subtitle="The world's seventh-largest economy in dollars, very "
                  "high human development, a slipping corruption score, and "
                  "reserves that are mostly gold.",
         source=_src("world"),
         alt="Four panels: GDP in current US dollars; the Human Development "
             "Index; Transparency International's Corruption Perceptions "
             "Index; and official reserves including gold."),
    dict(slug="08_demographics", topic="demography",
         builder=fig_demographics,
         title="France's Demographic Transition — Deaths Have Overtaken "
               "Births",
         subtitle="Fertility has fallen to its lowest level since the "
                  "Second World War, and in 2025 the population grew by "
                  "migration alone.",
         source=_src("demography"),
         alt="Four panels: population as an index of 2006; the total "
             "fertility rate against replacement; crude birth and death "
             "rates; natural increase and net migration per 1,000."),
    dict(slug="09_security", topic="security", builder=fig_security,
         title="Violence — Homicide, Suicide, the Roads, and the Couple",
         subtitle="Two counting systems for homicide, deliberately not "
                  "spliced; suicide, which kills far more people; and the "
                  "women killed by a partner.",
         source=_src("security"),
         alt="Four panels: homicide rates from police records, death "
             "certificates and UNODC; suicide rates; road deaths; and women "
             "killed by a partner per 100,000 women."),
    dict(slug="10_mortality", topic="mortality", builder=fig_mortality,
         title="Mortality — All Causes, COVID-19 and Influenza",
         subtitle="Three ways to count a death, and why they disagree. "
                  "Surveillance ended in July 2023; causes of death are "
                  "published 18 months late.",
         source=_src("mortality"),
         alt="Four panels: the crude death rate; deaths above the "
             "2015-2019 average; COVID-19 deaths per 100,000 by underlying "
             "cause and in surveillance; and influenza deaths, certified "
             "and estimated."),
    dict(slug="11_credit", topic="credit", builder=fig_credit,
         title="Credit — What It Costs, Who Owes It, Who Drowns In It",
         subtitle="French mortgages are almost entirely fixed-rate, so the "
                  "rate shock of 2022-24 hit new borrowers and left the "
                  "existing stock alone.",
         source=_src("credit"),
         alt="Four panels: household debt as a share of GDP; new and "
             "outstanding mortgage rates against the ECB rate; "
             "non-performing loans; and over-indebtedness filings."),
    dict(slug="12_migration", topic="migration", builder=fig_migration,
         title="Migration — Arrivals, Departures and the Foreign-Born",
         subtitle="Immigration has run at six to seven per 1,000 a year since "
                  "2022, and one resident in seven was born abroad.",
         source=_src("migration"),
         alt="Four panels: immigration and emigration per 1,000 people; "
             "net migration; the foreign-born and foreign-citizen shares "
             "of the population; and residence permits, asylum "
             "applications and naturalisations."),
)
