"""The france plates.

Each function draws one plate from this country's committed CSVs and saves it
through the context, which resolves every path under countries/france/ and
knows this country's palette, year span and last complete year. Ported from
the standalone france-reports scripts/charts.py; the drawing is unchanged.
"""
from __future__ import annotations

import matplotlib.ticker as mticker
import numpy as np


def fig_economy(ctx) -> None:
    gdp = ctx.table("macro/gdp.csv")
    infl = ctx.table("macro/inflation.csv")
    ig = ctx.fig(
        "The French Economy, 2006–2026",
        "Nominal size, real growth, income per person and inflation — the "
        "four numbers that frame everything else.",
        source=ctx.source("INSEE / Eurostat — comptes nationaux annuels (ESA 2010)",
                      "INSEE (IPC) · Eurostat (HICP)", "ECB (reference rate)"),
    )

    ax = ig.next_panel("GDP — nominal size (€ billion)")
    if gdp and "nominal_eurbn" in gdp:
        yrs, vals = ctx.series(gdp, "nominal_eurbn")
        ctx.bars(ax, yrs, vals, lambda v: ctx.p.BLUE_D)
        for y, v in zip(yrs, vals):
            if y in (2006, 2010, 2014, 2019, 2022, 2025):
                ax.annotate(f"{v:,.0f}", (y, v), textcoords="offset points",
                            xytext=(0, 4), ha="center", fontsize=9,
                            fontweight="bold", color=ctx.p.INK)
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 3400)

    ax = ig.next_panel("Real GDP growth (% per year)")
    if gdp and "real_growth" in gdp:
        yrs, vals = ctx.series(gdp, "real_growth")
        ax.axhline(0, color=ctx.p.MUTED, lw=1.0)
        for b0, b1 in ((2008.6, 2009.9), (2020.0, 2020.9)):
            ax.axvspan(b0, b1, color=ctx.p.BAND, zorder=0)
        ctx.bars(ax, yrs, vals, lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED)
        for y, v in zip(yrs, vals):
            if abs(v) > 2.4 or y in (2006, 2025):
                va = "bottom" if v >= 0 else "top"
                off = 4 if v >= 0 else -6
                ax.annotate(f"{v:+.1f}", (y, v), textcoords="offset points",
                            xytext=(0, off), ha="center", va=va, fontsize=9,
                            fontweight="bold",
                            color=ctx.p.GREEN_D if v >= 0 else ctx.p.RED)
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(-8.6, 8.2)

    ax = ig.next_panel("GDP per capita (US$, current)")
    if gdp and "gdp_per_capita_usd" in gdp:
        yrs, vals = ctx.series(gdp, "gdp_per_capita_usd")
        ctx.line(ax, yrs, vals, ctx.p.BLUE)
        ctx.endlabel(ax, yrs, vals, ctx.p.BLUE, lambda v: f"US$ {v:,.0f}", dy=10)
        # The dips are the dollar, not the economy: 2015 and 2022 are euro
        # weakness, which is why the panel says "US$, current".
        ig.add_event(ax, 2015.0, "euro slump, not a recession", dy=0.30)
    else:
        ctx.pending(ax)
    ax.set_ylim(32000, 53000)

    ax = ig.next_panel(
        "Inflation — consumer prices (% per year) vs the ECB's 2% aim")
    if infl:
        ax.axhline(2.0, color=ctx.p.BLUE, lw=1.3, ls="--", label="ECB aim: 2%")
        ax.axhline(0, color=ctx.p.MUTED, lw=0.9)
        iy, iv = ctx.series(infl, "ipc")
        hy, hv = ctx.series(infl, "hicp")
        if hy:
            ctx.line(ax, hy, hv, ctx.p.FAINT, label="Harmonised HICP (Eurostat)",
                 lw=1.8, dashed_partial=False)
        if iy:
            ctx.line(ax, iy, iv, ctx.p.RED, label="French IPC (INSEE)")
            for y, v in zip(iy, iv):
                if v > 3 or y == 2026:
                    ax.annotate(f"{v:.1f}", (y, v),
                                textcoords="offset points", xytext=(0, 6),
                                ha="center", fontsize=9, fontweight="bold",
                                color=ctx.p.RED)
        ax.legend(loc="upper left", fontsize=8.6)
        ig.add_event(ax, 2015.0, "deflation scare", dy=0.55)
        ig.mark_partial(ax, 2026, "Sep")
    else:
        ctx.pending(ax)
    ax.set_ylim(-1.0, 7.0)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("01_economy.png"))

def fig_fiscal(ctx) -> None:
    tax = ctx.table("fiscal/tax_burden.csv")
    deficit = ctx.table("fiscal/deficit.csv")
    debt = ctx.table("fiscal/debt.csv")
    ig = ctx.fig(
        "Taxes, the Deficit & Public Debt, 2006–2026",
        "France collects more of its economy in tax than any other EU "
        "country, and has still not balanced a budget since 1974.",
        source=ctx.source("INSEE — comptes nationaux (prélèvements obligatoires)",
                      "Eurostat — EDP / Maastricht notification",
                      "Eurostat gov_10a_main (interest)"),
    )

    ax = ig.next_panel(
        "Compulsory levies — prélèvements obligatoires (% of GDP)")
    if tax:
        ny, nv = ctx.series(tax, "insee")
        ey, ev = ctx.series(tax, "estat")
        if ny:
            ctx.line(ax, ny, nv, ctx.p.BLUE_D, label="INSEE (national definition)")
            ctx.endlabel(ax, ny, nv, ctx.p.BLUE_D, lambda v: f"{v:.1f}%", dy=10)
        if ey:
            ctx.line(ax, ey, ev, ctx.p.FAINT, label="Eurostat (harmonised)", lw=1.8,
                 dashed_partial=False)
        # Two definitions of the same idea, kept apart: Eurostat's harmonised
        # total includes imputed social contributions, which the French
        # national concept excludes, so it sits 2-3pt higher. Averaging them
        # would invent a third number that nobody publishes.
        ax.legend(loc="lower right", fontsize=8.6)
        # Unlike Brazil's tax series, this one needs NO base-vintage break:
        # INSEE retropolates the whole national accounts at every base change,
        # so base 2020 runs unbroken from 1959. The one real discontinuity is
        # 2019, when the CICE stopped being a tax credit booked as spending
        # and became a cut in employer contributions — which lowers the
        # numerator by ~0.9pt without any change in tax policy.
        ax.axvline(2019, color=ctx.p.FAINT, lw=0.9, ls=(0, (4, 3)))
        ax.text(2018.85, 40.4, "2019: CICE becomes a contribution cut\n"
                "(−0.9pt, definitional — not a tax cut)", fontsize=7.6,
                color=ctx.p.MUTED, style="italic", ha="right", va="bottom")
    else:
        ctx.pending(ax)
    ax.set_ylim(40, 50)

    ax = ig.next_panel("Public deficit (% of GDP)")
    if deficit and "deficit" in deficit:
        yrs, vals = ctx.series(deficit, "deficit")
        ax.axhline(0, color=ctx.p.MUTED, lw=1.0)
        ax.axhline(-3.0, color=ctx.p.BLUE, lw=1.2, ls="--")
        ax.text(2006.2, 0.95, "Maastricht 3% limit", fontsize=8.2,
                color=ctx.p.BLUE, style="italic", va="top")
        ctx.bars(ax, yrs, vals, lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED)
        for y, v in zip(yrs, vals):
            if v < -5 or y == 2025:
                ax.annotate(f"{v:.1f}", (y, v), textcoords="offset points",
                            xytext=(0, -5), ha="center", va="top",
                            fontsize=8.8, fontweight="bold", color=ctx.p.RED)
        ax.text(2016.5, -8.4, "last balanced budget: 1974", fontsize=8.4,
                color=ctx.p.MUTED, style="italic")
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(-10.2, 1.2)

    ax = ig.next_panel("Gross public debt — Maastricht (% of GDP)")
    if debt and "gross" in debt:
        yrs, vals = ctx.series(debt, "gross")
        ctx.line(ax, yrs, vals, ctx.p.RED)
        ax.fill_between(yrs, 0, vals, color=ctx.p.RED, alpha=0.06, zorder=1)
        ax.axhline(60.0, color=ctx.p.BLUE, lw=1.2, ls="--")
        ax.text(2006.2, 58.5, "Maastricht 60% limit", fontsize=8.2,
                color=ctx.p.BLUE, style="italic", va="top")
        ctx.endlabel(ax, yrs, vals, ctx.p.RED, lambda v: f"{v:.1f}%", dy=10)
        for y, v in zip(yrs, vals):
            if y in (2008, 2014, 2020):
                ax.annotate(f"{v:.0f}%", (y, v), textcoords="offset points",
                            xytext=(0, -15), ha="center", fontsize=8.6,
                            color=ctx.p.MUTED)
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(50, 125)

    ax = ig.next_panel(
        "Interest on the debt vs the primary balance (% of GDP)")
    if deficit and "interest" in deficit:
        iy, iv = ctx.series(deficit, "interest")
        py, pv = ctx.series(deficit, "primary")
        ax.axhline(0, color=ctx.p.MUTED, lw=1.0)
        ctx.line(ax, iy, iv, ctx.p.GOLD, label="Interest paid")
        ctx.line(ax, py, pv, ctx.p.PURPLE, label="Primary balance")
        ctx.endlabel(ax, iy, iv, ctx.p.GOLD, lambda v: f"{v:.1f}%", dy=8)
        ctx.endlabel(ax, py, pv, ctx.p.PURPLE, lambda v: f"{v:.1f}%", dy=-21)
        ax.legend(loc="lower left", fontsize=8.6)
        # The interesting fact of the period: the debt roughly doubled while
        # the interest bill fell, because rates fell faster. It is now rising
        # again with the stock unchanged.
        ax.text(2012.4, 1.05, "the debt doubled while the interest bill fell",
                fontsize=8.2, color=ctx.p.MUTED, style="italic")
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(-8.2, 3.6)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("02_fiscal.png"))

def fig_spending(ctx) -> None:
    spend = ctx.table("fiscal/spending_by_function.csv")
    inv = ctx.table("fiscal/investment.csv")
    ig = ctx.fig(
        "Where the Money Goes — Public Spending by Function, 2006–2024",
        "The highest public-spending ratio in the OECD, and what it is spent "
        "on. COFOG data stops at 2024.",
        source=ctx.source("Eurostat gov_10a_exp — COFOG, general government",
                      "Eurostat nama_10_gdp / gov_10a_main (investment)"),
    )

    ORDER = ["social_protection", "health", "general_services", "education",
             "economic_affairs", "defence_order", "other"]
    LABEL = {"social_protection": "Social protection", "health": "Health",
             "general_services": "General public services (incl. debt interest)",
             "education": "Education", "economic_affairs": "Economic affairs",
             "defence_order": "Defence & public order",
             "other": "Other functions"}
    COLORS = {"social_protection": ctx.p.NAVY, "health": ctx.p.TEAL, "education": ctx.p.BLUE,
              "general_services": ctx.p.RED, "economic_affairs": ctx.p.GOLD,
              "defence_order": ctx.p.PURPLE, "other": "#B9BDC7"}

    ax = ig.next_panel("Public spending by function (% of GDP)")
    cols = [c for c in ORDER if spend and c in spend] if spend else []
    if spend and cols:
        yrs = [y for y, v in zip(spend["year"], spend[cols[0]]) if v == v]
        stack = [[v for y, v in zip(spend["year"], spend[c]) if y in yrs]
                 for c in cols]
        ax.stackplot(yrs, *stack, labels=[LABEL[c] for c in cols],
                     colors=[COLORS[c] for c in cols], alpha=0.92, lw=0)
        ax.legend(loc="upper left", fontsize=8.0, ncol=2)
        ig.add_event(ax, 2020.25, "COVID-19", dy=0.56)
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 86)

    ax = ig.next_panel("Social protection vs everything else (% of GDP)")
    if spend and "social_protection" in spend and "total" in spend:
        sy, sv = ctx.series(spend, "social_protection")
        ty, tv = ctx.series(spend, "total")
        rest = [t - s for s, t in zip(sv, tv)]
        ax.plot(sy, sv, color=ctx.p.NAVY, lw=2.6, label="Social protection alone")
        ax.fill_between(sy, 0, sv, color=ctx.p.NAVY, alpha=0.10)
        ax.plot(ty, rest, color=ctx.p.TEAL, lw=2.6, label="All other functions")
        ax.fill_between(ty, 0, rest, color=ctx.p.TEAL, alpha=0.10)
        ax.legend(loc="lower right", fontsize=8.6)
        # Worth saying plainly: social protection on its own is larger than
        # the entire rest of the French state.
        ax.text(2006.3, 30.5, "social protection alone outweighs the whole "
                "rest of the state", fontsize=8.2, color=ctx.p.MUTED, style="italic")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 38)

    ax = ig.next_panel("Investment rate — whole economy (% of GDP)")
    if inv and "gfcf_pct_gdp" in inv:
        yrs, vals = ctx.series(inv, "gfcf_pct_gdp")
        ctx.line(ax, yrs, vals, ctx.p.BLUE)
        ctx.endlabel(ax, yrs, vals, ctx.p.BLUE, lambda v: f"{v:.1f}%", dy=10)
        for y, v in zip(yrs, vals):
            if y in (2008, 2015):
                ax.annotate(f"{v:.1f}%", (y, v), textcoords="offset points",
                            xytext=(0, -15), ha="center", fontsize=8.8,
                            color=ctx.p.MUTED)
    else:
        ctx.pending(ax)
    ax.set_ylim(18, 25)

    ax = ig.next_panel(
        "Public investment — general government GFCF (% of GDP)")
    if inv and "gov_gfcf_pct_gdp" in inv:
        yrs, vals = ctx.series(inv, "gov_gfcf_pct_gdp")
        ctx.line(ax, yrs, vals, ctx.p.GREEN_D)
        ax.fill_between(yrs, 0, vals, color=ctx.p.GREEN_D, alpha=0.10)
        ctx.endlabel(ax, yrs, vals, ctx.p.GREEN_D, lambda v: f"{v:.1f}%", dy=10)
        # The local-election cycle is visible in this series and nowhere else
        # on the plate, which is why it gets its own panel.
        ax.text(2006.3, 1.0, "the dips track the local-election cycle",
                fontsize=8.2, color=ctx.p.MUTED, style="italic")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 6)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("03_spending.png"))

def fig_trade(ctx) -> None:
    tr = ctx.table("trade/trade.csv")
    prods = ctx.table("trade/exports_products.csv")
    dest = ctx.table("trade/destinations.csv")
    ig = ctx.fig(
        "Foreign Trade — a Deficit That Became Structural, 2006–2026",
        "France ran a goods surplus until 2003. Twenty years later the "
        "deficit is one of the largest in the EU.",
        source=ctx.source("Douanes/DGDDI — Le chiffre du commerce extérieur (FAB/FAB)",
                      "DGDDI open data, nomenclature A129 (composition)"),
    )

    # 2026 is a HALF year in this source. Drawn as a point on an annual
    # series it reads as exports collapsing by half, which is what a reader
    # takes away however the axis is footnoted — so the annual panels stop at
    # the last complete year and the partial figure is stated in words.
    ax = ig.next_panel("Exports vs imports of goods (€ billion)")
    if tr and "exports" in tr:
        ey, ev = ctx.full_years(*ctx.series(tr, "exports"))
        iy, iv = ctx.full_years(*ctx.series(tr, "imports"))
        ctx.line(ax, ey, ev, ctx.p.GREEN_D, label="Exports")
        ctx.line(ax, iy, iv, ctx.p.BLUE, label="Imports")
        ctx.endlabel(ax, ey, ev, ctx.p.GREEN_D, lambda v: f"€{v:,.0f}bn", dy=-18)
        ctx.endlabel(ax, iy, iv, ctx.p.BLUE, lambda v: f"€{v:,.0f}bn", dy=8)
        ax.legend(loc="upper left")
        part = ctx.partial_row(tr)
        if part:
            ax.text(0.5, -0.125,
                    f"{part['year']:.0f} is a half year and is not drawn: "
                    f"Jan–Jun exports €{part['exports']:,.0f}bn, "
                    f"imports €{part['imports']:,.0f}bn",
                    transform=ax.transAxes, ha="center", fontsize=7.6,
                    color=ctx.p.FAINT, style="italic")
    else:
        ctx.pending(ax)
    ax.set_ylim(250, 850)

    ax = ig.next_panel("Goods trade balance (€ billion)")
    if tr and "balance" in tr:
        yrs, vals = ctx.full_years(*ctx.series(tr, "balance"))
        ax.axhline(0, color=ctx.p.MUTED, lw=1.0)
        ctx.bars(ax, yrs, vals, lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED)
        for y, v in zip(yrs, vals):
            if y in (2006, 2022, 2025):
                ax.annotate(f"{v:+,.0f}", (y, v), textcoords="offset points",
                            xytext=(0, -5), ha="center", va="top",
                            fontsize=8.8, fontweight="bold", color=ctx.p.RED)
        ax.annotate("2022: the energy bill", xy=(2022, -161.7),
                    xytext=(2013.5, -138), fontsize=8.4, color=ctx.p.MUTED,
                    style="italic",
                    arrowprops=dict(arrowstyle="-", color=ctx.p.FAINT, lw=0.8))
        part = ctx.partial_row(tr)
        if part:
            ax.text(0.5, -0.125,
                    f"{part['year']:.0f} is a half year and is not drawn: "
                    f"Jan–Jun balance −€{abs(part['balance']):,.0f}bn",
                    transform=ax.transAxes, ha="center", fontsize=7.6,
                    color=ctx.p.FAINT, style="italic")
    else:
        ctx.pending(ax)
    ax.set_ylim(-185, 25)

    ax = ig.next_panel("What France exports — top groups (€ bn)")
    pick: list[int] = []
    if prods:
        years = sorted({int(y) for y in prods["year"]})
        pick = [y for y in (2006, 2010, 2015, 2020, 2025) if y in years]
        ORDER = ["aeronautics", "chemicals", "electrical", "vehicles",
                 "machinery", "agrifood", "pharma", "metals", "beverages"]
        LABEL = {"aeronautics": "Aeronautics", "pharma": "Pharmaceuticals",
                 "chemicals": "Chemicals & cosmetics", "agrifood": "Agri-food",
                 "beverages": "Wines & spirits", "machinery": "Machinery",
                 "vehicles": "Vehicles", "metals": "Metals",
                 "electrical": "Electrical & electronic"}
        pal = {"aeronautics": ctx.p.BLUE, "pharma": ctx.p.TEAL, "chemicals": ctx.p.PURPLE,
               "agrifood": ctx.p.GREEN, "beverages": "#8E2F4A",
               "machinery": "#7A828E", "vehicles": ctx.p.RED, "metals": "#8A6D3B",
               "electrical": ctx.p.GOLD}
        eurbn = {(int(y), p): v for y, p, v
                 in zip(prods["year"], prods["product"], prods["eurbn"])}
        # The snapshot years are unevenly spaced, so the bars sit at
        # categorical positions: plotted at year coordinates the whole group
        # spans 0.82 of a 21-year axis and renders as hairlines.
        xs = np.arange(len(pick))
        width = 0.82 / len(ORDER)
        for i, p in enumerate(ORDER):
            vals = [eurbn.get((y, p), 0) for y in pick]
            ax.bar(xs + i * width - 0.82 / 2 + width / 2, vals, width=width,
                   label=LABEL[p], color=pal.get(p, "#B9BDC7"),
                   edgecolor="white", linewidth=0.5, zorder=3)
        ax.legend(fontsize=7.4, ncol=3, loc="upper left")
        resid = eurbn.get((pick[-1], "others"), 0) if pick else 0
        if resid:
            ax.text(0.5, -0.125, f"excludes the 'others' residual "
                    f"(€{resid:,.0f}bn in {pick[-1]})", transform=ax.transAxes,
                    ha="center", fontsize=7.6, color=ctx.p.FAINT, style="italic")
        ax.set_ylim(0, 108)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Export destinations — share of total (%)")
    if dest:
        names = set(dest["destiny"])
        for cname, color in (("Germany", ctx.p.BLUE), ("Italy", ctx.p.GREEN),
                             ("Spain", ctx.p.GOLD), ("Belgium", ctx.p.PURPLE),
                             ("United States", ctx.p.RED), ("China", ctx.p.TEAL)):
            if cname in names:
                yrs, vals = [], []
                for y, name, share in zip(dest["year"], dest["destiny"],
                                          dest["share_pct"]):
                    # A half-year share is a ratio rather than a total, so it
                    # is not absurd — but sitting next to 2025 on the same
                    # line it still reads as "the 2026 share", which is not
                    # what it is.
                    if name == cname and int(y) <= ctx.LAST_FULL_YEAR:
                        yrs.append(int(y))
                        vals.append(share)
                ctx.line(ax, yrs, vals, color, label=cname, marker="D", ms=4)
        ax.legend(loc="upper right", fontsize=8.2, ncol=2)
        if max((int(y) for y in dest["year"]), default=0) > ctx.LAST_FULL_YEAR:
            ax.text(0.5, -0.125, "snapshot years; the 2026 half-year share "
                    "is not drawn", transform=ax.transAxes, ha="center",
                    fontsize=7.6, color=ctx.p.FAINT, style="italic")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 22)

    for i, ax in enumerate(ig.axes_flat):
        # Panel (c) is categorical (snapshot years), not a continuous axis.
        ig.style_axis(ax, xticks_years=i != 2)
    if pick:
        ax_c = ig.axes_flat[2]
        ax_c.set_xticks(np.arange(len(pick)))
        ax_c.set_xticklabels([str(y) for y in pick])
        ax_c.set_xlim(-0.5, len(pick) - 0.5)
    ig.save(ctx.out("04_trade.png"))

def fig_markets(ctx) -> None:
    cac = ctx.table("markets/cac40.csv")
    sp = ctx.table("markets/sp500.csv")
    fx = ctx.table("macro/eurusd.csv")
    rate = ctx.table("macro/policy_rate.csv")
    infl = ctx.table("macro/inflation.csv")
    ig = ctx.fig(
        "Money & Markets — the CAC 40, the Euro and ECB Rates",
        "French equities against the S&P 500, the euro against the dollar, "
        "and eight years of negative policy rates.",
        source=ctx.source("Euronext / S&P — index closes (price indices)",
                      "ECB — reference rate and deposit facility rate",
                      "INSEE (IPC)"),
    )

    # The FX series starts in 2006, the indices in 2005: rebase on the first
    # year both cover, so the baseline is a real USD-converted close.
    usd = {int(y): v for y, v in zip(fx["year"], fx["eop"]) if v == v} if fx else {}

    base_all = min(set(int(y) for y in cac["year"]) &
                   set(int(y) for y in sp["year"]) & set(usd),
                   default=None) if (cac and sp and usd) else None
    ax = ig.next_panel(
        f"€100 invested in {base_all} — CAC 40 vs S&P 500 (local terms)"
        if base_all else "CAC 40 vs S&P 500 (local terms)")
    if cac and sp and usd:
        def closes_of(t):
            return {int(y): v for y, v in zip(t["year"], t["close"]) if v == v}
        c_raw, s_raw = closes_of(cac), closes_of(sp)
        # Every line on this panel is rebased on the SAME year — the first
        # one all three series cover. Rebasing each on its own first year
        # looks right until one of them starts a year earlier: the euro
        # conversion then begins at whatever level the dollar index had
        # reached by the time the FX series starts, and three lines that
        # claim a common base start at three different places.
        base_year = min(set(c_raw) & set(s_raw) & set(usd))
        c_idx = {y: v / c_raw[base_year] * 100 for y, v in c_raw.items()
                 if y >= base_year}
        s_idx = {y: v / s_raw[base_year] * 100 for y, v in s_raw.items()
                 if y >= base_year}
        u_base = usd[base_year]
        # s_eur is the dollar index converted *into* euro, s_idx is the
        # native USD index. Getting these two labels the wrong way round
        # inverts the whole panel, so they are named at the point of use.
        s_eur = {y: v * u_base / usd[y] for y, v in s_idx.items() if y in usd}
        cy = sorted(c_idx)
        ax.semilogy(cy, [c_idx[y] for y in cy], color=ctx.p.BLUE_D, lw=2.5,
                    marker="o", ms=3.6, label="CAC 40 (EUR)")
        ey = sorted(s_eur)
        ax.semilogy(ey, [s_eur[y] for y in ey], color=ctx.p.RED, lw=2.5,
                    marker="o", ms=3.6, label="S&P 500 (in EUR)")
        sy = sorted(s_idx)
        ax.semilogy(sy, [s_idx[y] for y in sy], color=ctx.p.FAINT, lw=2.0, ls="--",
                    marker="o", ms=3.2, label="S&P 500 (USD)")
        ax.legend(loc="upper left", fontsize=8.6)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.yaxis.set_minor_formatter(mticker.NullFormatter())
        ax.text(0.5, -0.125, "price indices — dividends excluded",
                transform=ax.transAxes, ha="center", fontsize=7.6,
                color=ctx.p.FAINT, style="italic")
        ig.mark_partial(ax, 2026, "Oct 21")
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Exchange rate — US dollars per euro (year-end)")
    if fx and "eop" in fx:
        yrs, vals = ctx.series(fx, "eop")
        ctx.line(ax, yrs, vals, ctx.p.TEAL)
        ctx.endlabel(ax, yrs, vals, ctx.p.TEAL, lambda v: f"{v:.2f}", dy=10)
        for y, v in zip(yrs, vals):
            if y in (2008, 2016, 2022):
                ax.annotate(f"{v:.2f}", (y, v), textcoords="offset points",
                            xytext=(0, -16), ha="center", fontsize=8.8,
                            color=ctx.p.MUTED)
        ig.mark_partial(ax, 2026, "Oct 21")
    else:
        ctx.pending(ax)
    ax.set_ylim(0.95, 1.55)

    ax = ig.next_panel("ECB policy rate vs French inflation (%)")
    if rate and infl:
        ry, rv = ctx.series(rate, "dfr")
        iy, iv = ctx.series(infl, "ipc")
        ax.axhline(0, color=ctx.p.MUTED, lw=1.0)
        ax.axhspan(-0.6, 0, color=ctx.p.BAND, zorder=0)
        ctx.line(ax, ry, rv, ctx.p.NAVY, label="Deposit facility rate")
        if iy:
            ctx.line(ax, iy, iv, ctx.p.RED, label="Inflation (IPC)")
        ax.legend(loc="upper left", fontsize=8.6)
        ax.text(2014.3, -0.52, "eight years below zero", fontsize=8.4,
                color=ctx.p.MUTED, style="italic", va="bottom")
        ig.mark_partial(ax, 2026, "Oct 21")
    else:
        ctx.pending(ax)
    ax.set_ylim(-1.0, 7.0)

    closes = ({int(y): c for y, c in zip(cac["year"], cac["close"])
               if c == c and int(y) in usd} if cac else {})
    base_year = min(closes, default=None)
    ax = ig.next_panel(f"CAC 40 in US dollars (rebased {base_year} = 100)"
                       if base_year else "CAC 40 in US dollars")
    if base_year:
        base, u_base = closes[base_year], usd[base_year]
        yy = sorted(closes)
        vals = [closes[y] / base * usd[y] / u_base * 100 for y in yy]
        ctx.line(ax, yy, vals, ctx.p.BLUE)
        ctx.endlabel(ax, yy, vals, ctx.p.BLUE, lambda v: f"{v:,.0f}", dy=10)
        ax.axhline(100, color=ctx.p.MUTED, lw=1.0, ls=":")
        ig.mark_partial(ax, 2026, "Oct 21")
    else:
        ctx.pending(ax)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("05_markets.png"))

def fig_people(ctx) -> None:
    hdi = ctx.table("social/hdi.csv")
    gini = ctx.table("social/gini.csv")
    unemp = ctx.table("macro/unemployment.csv")
    smic = ctx.table("macro/smic.csv")
    pov = ctx.table("social/poverty.csv")
    infl = ctx.table("macro/inflation.csv")
    ig = ctx.fig(
        "People — Development, Inequality, Jobs, Wages & Poverty, 2006–2026",
        "A rich country with stubborn unemployment, slowly rising inequality "
        "and a poverty rate that has not improved in twenty years.",
        ncols=3, nrows=2,
        source=ctx.source("UNDP HDR 2025 (HDI)", "INSEE ERFS / Eurostat EU-SILC",
                      "INSEE — taux de chômage BIT",
                      "Légifrance / INSEE (SMIC)"),
    )

    ax = ig.next_panel("Human Development Index (UNDP)")
    if hdi:
        yrs, vals = ctx.series(hdi, "value")
        ctx.line(ax, yrs, vals, ctx.p.GREEN_D, marker="o", ms=4.6,
             split_year=max(yrs) if yrs else None)
        ctx.endlabel(ax, yrs, vals, ctx.p.GREEN_D, lambda v: f"{v:.3f}", dy=10)
        ax.axhline(0.9, color=ctx.p.FAINT, lw=0.9, ls=":")
        ax.text(2026.4, 0.9015, "0.900 = very high development",
                fontsize=8.0, color=ctx.p.MUTED, style="italic", ha="right",
                va="bottom")
        ig.add_event(ax, 2020.1, "pandemic dip", dy=0.42)
    else:
        ctx.pending(ax)
    ax.set_ylim(0.86, 0.94)

    ax = ig.next_panel("Income inequality — Gini (lower = better)")
    if gini:
        ny, nv = ctx.series(gini, "insee")
        ey, ev = ctx.series(gini, "silc")
        if ny:
            ctx.line(ax, ny, nv, ctx.p.PURPLE, label="INSEE (ERFS)")
        if ey:
            ctx.line(ax, ey, ev, ctx.p.FAINT, label="Eurostat (EU-SILC)", lw=1.8,
                 dashed_partial=False)
        ax.invert_yaxis()   # lower Gini is better: put 'better' at the top
        ax.legend(loc="lower left", fontsize=8.2)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Unemployment rate (%, annual average)")
    if unemp:
        yrs, vals = ctx.series(unemp, "value")
        ctx.line(ax, yrs, vals, ctx.p.RED)
        ctx.endlabel(ax, yrs, vals, ctx.p.RED, lambda v: f"{v:.1f}%", dy=10)
        ax.annotate("post-crisis peak", xy=(2015, 10.4), xytext=(2011.0, 11.3),
                    fontsize=8.4, color=ctx.p.RED, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=ctx.p.RED, lw=0.8))
    else:
        ctx.pending(ax)
    ax.set_ylim(5.5, 12.0)

    ax = ig.next_panel("Minimum wage — SMIC (€/month, gross)")
    if smic and "monthly_eur" in smic:
        yrs, vals = ctx.series(smic, "monthly_eur")
        ctx.line(ax, yrs, vals, ctx.p.GOLD, lw=2.8, label="Nominal")
        if infl:
            ipc = {y: v for y, v in zip(infl["year"], infl["ipc"]) if v == v}
            factors, base = {}, 1.0
            for y in sorted(ipc):
                factors[y] = base
                base *= 1 + ipc[y] / 100
            if factors:
                top = max(factors)
                ryr = [y for y in yrs if y in factors]
                real = [v * factors[top] / factors[y]
                        for y, v in zip(yrs, vals) if y in factors]
                ctx.line(ax, ryr, real, "#8A6D3B", lw=2.4,
                     label="In 2026 euros (IPC-deflated)")
        ax.legend(loc="upper left", fontsize=8.4)
        ctx.endlabel(ax, yrs, vals, ctx.p.GOLD, lambda v: f"€{v:,.0f}", dy=10)
    else:
        ctx.pending(ax)
    ax.set_ylim(1000, 2100)

    ax = ig.next_panel("Monetary poverty rate (% below 60% of median)")
    if pov and "rate60" in pov:
        ny, nv = ctx.series(pov, "rate60")
        ey, ev = ctx.series(pov, "arop60")
        if ny:
            ctx.line(ax, ny, nv, ctx.p.TEAL, label="INSEE (ERFS)")
            ctx.endlabel(ax, ny, nv, ctx.p.TEAL, lambda v: f"{v:.1f}%", dy=10)
        if ey:
            ctx.line(ax, ey, ev, ctx.p.FAINT, label="Eurostat (EU-SILC)", lw=1.8,
                 dashed_partial=False)
        ax.legend(loc="lower left", fontsize=8.2)
    else:
        ctx.pending(ax)
    ax.set_ylim(11, 19)

    ax = ig.next_panel("Poverty at the 50% threshold (%)")
    if pov and "rate50" in pov:
        yrs, vals = ctx.series(pov, "rate50")
        ctx.line(ax, yrs, vals, ctx.p.RED)
        ctx.endlabel(ax, yrs, vals, ctx.p.RED, lambda v: f"{v:.1f}%", dy=10)
    else:
        ctx.pending(ax)
    ax.set_ylim(5, 10)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("06_people.png"))

def fig_world(ctx) -> None:
    wef = ctx.table("international/wef.csv")
    cpi = ctx.table("international/cpi.csv")
    res = ctx.table("macro/reserves.csv")
    gdp = ctx.table("macro/gdp.csv")
    tr = ctx.table("trade/trade.csv")
    ig = ctx.fig(
        "France in the World — Competitiveness, Corruption & Openness",
        "How the outside world scores France — and how open its economy is.",
        source=ctx.source("World Economic Forum — GCI",
                      "Transparency International — CPI",
                      "Douanes + INSEE/Eurostat (openness)",
                      "Banque de France / IMF (reserves)"),
    )

    ax = ig.next_panel(
        "WEF Global Competitiveness — France rank (lower is better)")
    if wef and "rank" in wef:
        yrs, vals = ctx.series(wef, "rank")
        ctx.line(ax, yrs, vals, ctx.p.BLUE, marker="D", ms=4,
             split_year=max(yrs) if yrs else None)
        ax.invert_yaxis()
        ctx.endlabel(ax, yrs, vals, ctx.p.BLUE, lambda v: f"#{v:.0f}", dy=10)
        ax.text(2006.3, 32, "methodology changes 2008/2018;\n"
                "GCI discontinued after 2019", fontsize=7.8, color=ctx.p.FAINT,
                style="italic", va="top")
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)

    ax = ig.next_panel(
        "Corruption Perceptions Index — score (higher = cleaner)")
    if cpi and "score" in cpi:
        yrs, vals = ctx.series(cpi, "score")
        # 2006-2011 came on a 0-10 scale: rescale so the panel has one axis,
        # and say so, rather than drawing two incomparable segments.
        vals = [v * 10 if v <= 10 else v for v in vals]
        ctx.line(ax, yrs, vals, ctx.p.TEAL, split_year=max(yrs) if yrs else None)
        ctx.endlabel(ax, yrs, vals, ctx.p.TEAL, lambda v: f"{v:.0f}", dy=10)
        ax.text(2006.3, 82, "2012: scale rebased 0–100", fontsize=7.8,
                color=ctx.p.FAINT, style="italic")
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(55, 85)

    ax = ig.next_panel(
        "Trade openness — exports + imports of goods (% of GDP)")
    if gdp and tr:
        nominal = {int(y): v for y, v in zip(gdp["year"], gdp["nominal_eurbn"])
                   if v == v}
        ox, oy = [], []
        for y, e, i in zip(tr["year"], tr["exports"], tr["imports"]):
            y = int(y)
            if e == e and i == i and y in nominal and y <= ctx.LAST_FULL_YEAR:
                ox.append(y)
                oy.append((e + i) / nominal[y] * 100)
        ctx.line(ax, ox, oy, ctx.p.TEAL)
        ctx.endlabel(ax, ox, oy, ctx.p.TEAL, lambda v: f"{v:.0f}%", dy=10)
        ax.text(2006.3, 51.5, "goods only — services would add about a third",
                fontsize=8.2, color=ctx.p.MUTED, style="italic")
        # 2026 GDP is not published yet, so openness stops at 2025.
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(38, 54)

    ax = ig.next_panel("Official reserve assets (US$ billion, year-end)")
    if res and "eop_usdbn" in res:
        yrs, vals = ctx.series(res, "eop_usdbn")
        ctx.line(ax, yrs, vals, ctx.p.GREEN_D)
        ax.fill_between(yrs, 0, vals, color=ctx.p.GREEN_D, alpha=0.08)
        ctx.endlabel(ax, yrs, vals, ctx.p.GREEN_D, lambda v: f"US$ {v:,.0f}bn", dy=-18)
        ax.text(2006.3, 395, "mostly gold, revalued at market price",
                fontsize=8.2, color=ctx.p.MUTED, style="italic")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 480)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("07_world.png"))

def fig_demographics(ctx) -> None:
    """The only figure that leaves the 2006-2026 window: the point of the
    demographic story is what happens after it."""
    pop = ctx.table("social/population.csv")
    ig = ctx.fig(
        "France's Demographic Transition — Deaths Have Overtaken Births",
        "Fertility has fallen to its lowest level since the Second World "
        "War. Dashed = INSEE projection.",
        source=ctx.source("INSEE — Bilan démographique (observed)",
                      "INSEE — Projections de population, scénario central"),
    )
    SPLIT = 2025   # last observed year; everything after is model output
    X0, X1 = 2000, 2070

    ax = ig.next_panel("Population (millions)")
    if pop and "pop_mn" in pop:
        yrs, vals = ctx.series(pop, "pop_mn")
        ctx.line(ax, yrs, vals, ctx.p.BLUE, split_year=SPLIT, marker="")
        peak = max(zip(yrs, vals), key=lambda t: t[1])
        ax.plot([peak[0]], [peak[1]], marker="o", ms=7, mfc="none",
                mec=ctx.p.RED, mew=2, zorder=5)
        ax.annotate(f"peak {peak[1]:.1f}M in {peak[0]:.0f}", peak,
                    textcoords="offset points", xytext=(-8, 14), ha="right",
                    fontsize=9, fontweight="bold", color=ctx.p.RED)
        ctx.endlabel(ax, yrs, vals, ctx.p.BLUE, lambda v: f"{v:.0f}M", dy=-18)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Total fertility rate — children per woman")
    if pop and "tfr" in pop:
        yrs, vals = ctx.series(pop, "tfr")
        ax.axhline(2.1, color=ctx.p.MUTED, lw=1.1, ls=(0, (5, 4)))
        ax.text(X0 + 1, 2.13, "replacement level 2.1", fontsize=8.2,
                color=ctx.p.MUTED, style="italic")
        ctx.line(ax, yrs, vals, ctx.p.RED, split_year=SPLIT, marker="")
        obs = [(y, v) for y, v in zip(yrs, vals) if y <= SPLIT]
        if obs:
            lo = min(obs, key=lambda t: t[1])
            ax.annotate(f"{lo[1]:.2f} ({lo[0]:.0f})", lo,
                        textcoords="offset points", xytext=(0, -18),
                        ha="center", fontsize=8.8, fontweight="bold",
                        color=ctx.p.RED)
        ax.set_ylim(1.4, 2.3)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Births and deaths per year (thousands)")
    if pop and "births" in pop and "deaths" in pop:
        by, bv = ctx.series(pop, "births")
        dy_, dv = ctx.series(pop, "deaths")
        bv = [v / 1000 for v in bv]
        dv = [v / 1000 for v in dv]
        ctx.line(ax, by, bv, ctx.p.GREEN_D, label="Births", split_year=SPLIT, marker="")
        ctx.line(ax, dy_, dv, ctx.p.INK, label="Deaths", split_year=SPLIT, marker="")
        ax.legend(loc="lower right")
        cross = next((y for y in dy_ if y in by
                      and dv[dy_.index(y)] > bv[by.index(y)]), None)
        if cross:
            ax.axvline(cross, color=ctx.p.FAINT, lw=0.9, ls=(0, (4, 3)), zorder=1)
            ax.text(cross + 1.5, 0.06, f"deaths overtake\nbirths in {cross:.0f}",
                    transform=ax.get_xaxis_transform(), fontsize=8.2,
                    color=ctx.p.MUTED, style="italic")
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Annual population growth (%)")
    if pop and "growth_pct" in pop:
        yrs, vals = ctx.series(pop, "growth_pct")
        ax.axhline(0, color=ctx.p.INK, lw=1.0, zorder=2)
        ctx.line(ax, yrs, vals, ctx.p.TEAL, split_year=SPLIT, marker="")
        neg = next((y for y, v in zip(yrs, vals) if v < 0), None)
        if neg:
            ax.annotate(f"turns negative\nin {neg:.0f}", (neg, 0),
                        textcoords="offset points", xytext=(4, -32),
                        fontsize=8.6, color=ctx.p.MUTED, ha="left")
        ctx.endlabel(ax, yrs, vals, ctx.p.TEAL, lambda v: f"{v:.2f}%", dy=12)
    else:
        ctx.pending(ax)

    for ax in ig.axes_flat:
        ig.style_axis(ax, xticks_years=False)
        ax.set_xticks(list(range(X0, X1 + 1, 10)))
        ax.set_xlim(X0 - 1.5, X1 + 1.5)
    ig.save(ctx.out("08_demographics.png"))

def fig_security(ctx) -> None:
    hom = ctx.table("social/homicides.csv")
    vio = ctx.table("social/violence.csv")
    ig = ctx.fig(
        "Violence — Homicides, Femicides & Recorded Assault",
        "Two counting systems, deliberately not spliced: police records of "
        "offences, and death certificates by cause.",
        source=ctx.source("SSMSI — Insécurité et délinquance, bilan statistique",
                      "Inserm/CépiDc — causes de décès (X85–Y09)",
                      "Ministère de l'Intérieur — morts violentes au sein du couple"),
    )

    ax = ig.next_panel("Homicide rate per 100k — the two systems")
    if hom and ("ssmsi_rate" in hom or "cepidc_rate" in hom):
        sy, sv = ctx.series(hom, "ssmsi_rate")
        cy, cv = ctx.series(hom, "cepidc_rate")
        if sy:
            ctx.line(ax, sy, sv, ctx.p.RED, label="SSMSI — recorded by police")
            ctx.endlabel(ax, sy, sv, ctx.p.RED, lambda v: f"{v:.2f}", dy=10)
        if cy:
            ctx.line(ax, cy, cv, ctx.p.INK, label="CépiDc — death certificates",
                 lw=2.0, ls=(0, (5, 3)), marker="o", ms=3.4,
                 dashed_partial=False)
        ax.legend(loc="upper left", fontsize=8.4)
        ig.add_event(ax, 2015, "2015: November attacks (130 deaths)", dy=0.62)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Homicides per year — the two systems")
    if hom and ("ssmsi_count" in hom or "cepidc_count" in hom):
        sy, sv = ctx.series(hom, "ssmsi_count")
        cy, cv = ctx.series(hom, "cepidc_count")
        if sy:
            ctx.line(ax, sy, sv, ctx.p.RED, label="SSMSI — recorded by police")
            ctx.endlabel(ax, sy, sv, ctx.p.RED, lambda v: f"{v:,.0f}", dy=10)
        if cy:
            ctx.line(ax, cy, cv, ctx.p.INK, label="CépiDc — death certificates",
                 lw=2.0, ls=(0, (5, 3)), marker="o", ms=3.4,
                 dashed_partial=False)
        ax.legend(loc="upper left", fontsize=8.4)
    else:
        ctx.pending(ax)

    # The subset panel. A line drawn inside another line reads as two
    # independent trends unless the containment is visual, and a title that
    # promises a share has to actually plot one — so the subset is a filled
    # area inside the total, labelled in place, and the share gets its own
    # right-hand axis instead of being left to the reader's eye.
    ax = ig.next_panel("Deaths within the couple, and the women among them")
    if vio and "couple_deaths_total" in vio and "women_killed_by_partner" in vio:
        ty, tv = ctx.series(vio, "couple_deaths_total")
        wy, wv = ctx.series(vio, "women_killed_by_partner")
        ax.fill_between(ty, 0, tv, color=ctx.p.INK, alpha=0.13, lw=0)
        ax.plot(ty, tv, color=ctx.p.INK, lw=2.4, zorder=4)
        shared = [(y, v) for y, v in zip(wy, wv) if y in ty]
        sy2 = [y for y, _ in shared]
        sv2 = [v for _, v in shared]
        if shared:
            ax.fill_between(sy2, 0, sv2, color=ctx.p.RED, alpha=0.55, lw=0, zorder=3)
        # Labelled in place rather than through a legend: "of which…" in a
        # legend box gives the reader nothing to attach the "which" to.
        if ty:
            ax.annotate("All deaths within the couple", (ty[0], tv[0]),
                        textcoords="offset points", xytext=(6, 12),
                        fontsize=8.6, fontweight="bold", color=ctx.p.INK)
        if shared:
            ax.annotate("of whom women", (sy2[0], sv2[0]),
                        textcoords="offset points", xytext=(6, -16),
                        fontsize=8.6, fontweight="bold", color=ctx.p.RED)
        ax.set_ylim(0, 300)

        share_ax = ax.twinx()
        share = [(y, wv[wy.index(y)] / tv[ty.index(y)] * 100)
                 for y in wy if y in ty and tv[ty.index(y)]]
        if share:
            shy = [y for y, _ in share]
            shv = [v for _, v in share]
            share_ax.plot(shy, shv, color=ctx.p.PURPLE, lw=1.8, ls=(0, (4, 2)),
                          zorder=5)
            share_ax.set_ylim(0, 100)
            share_ax.set_ylabel("women as a share of couple deaths (right axis)",
                                fontsize=8.0, color=ctx.p.PURPLE)
            share_ax.tick_params(axis="y", colors=ctx.p.PURPLE, labelsize=8.5,
                                 length=0)
            share_ax.spines[["top", "left", "right"]].set_visible(False)
            share_ax.grid(False)
            share_ax.set_xlim(ctx.YEARS[0] - 0.6, ctx.YEARS[-1] + 0.6)
            # A twin axis draws its own x ticks over the host's: the year
            # labels end up rendered twice, which reads as a smudge.
            share_ax.xaxis.set_visible(False)
            share_ax.yaxis.set_major_formatter(
                mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    else:
        ctx.pending(ax)

    ax = ig.next_panel(
        "Recorded assault and sexual violence (thousands of victims)")
    if vio and ("assault" in vio or "sexual_violence" in vio):
        ay, av = ctx.series(vio, "assaults")
        xy, xv = ctx.series(vio, "sexual_violence")
        if ay:
            ctx.line(ax, ay, [v / 1000 for v in av], ctx.p.GOLD,
                 label="Assault (coups et blessures volontaires)")
            ctx.endlabel(ax, ay, [v / 1000 for v in av], ctx.p.GOLD,
                     lambda v: f"{v:,.0f}", dy=10)
        if xy:
            ctx.line(ax, xy, [v / 1000 for v in xv], ctx.p.PURPLE,
                 label="Sexual violence")
            ctx.endlabel(ax, xy, [v / 1000 for v in xv], ctx.p.PURPLE,
                     lambda v: f"{v:,.0f}", dy=10)
        ax.legend(loc="upper left", fontsize=8.4)
        # These are offences REPORTED to the police. The post-2017 climb is
        # substantially a change in the propensity to report, which is not
        # the same thing as a change in how much violence there is.
        ax.text(0.5, -0.125, "recorded offences: the rise after 2017 is "
                "substantially a change in reporting, not a measured rate",
                transform=ax.transAxes, ha="center", fontsize=7.6,
                color=ctx.p.FAINT, style="italic")
        ax.set_ylim(0, 520)
    else:
        ctx.pending(ax)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("09_security.png"))

def fig_mortality(ctx) -> None:
    """COVID, influenza and all-cause deaths.

    The hardest plate in the atlas to draw honestly, because almost every
    number on it is a different quantity wearing the same word. "COVID
    deaths" means a place-of-death count of infected patients in one series
    and an underlying cause of death in another; "flu deaths" means a coded
    certificate in one column and a modelled attribution in the next, an
    order of magnitude apart. None of them may be added, averaged or drawn
    as one line, so each panel names what it is counting.
    """
    allc = ctx.table("social/all_cause_deaths.csv")
    covid = ctx.table("social/covid_deaths.csv")
    flu = ctx.table("social/flu_deaths.csv")
    ig = ctx.fig(
        "Mortality — COVID-19, Influenza and All Causes",
        "Three ways to count a death, and why they disagree. Surveillance "
        "ended in July 2023; causes of death are published 18 months late.",
        source=ctx.source("INSEE — état civil (décès)",
                      "Santé publique France — SI-VIC / SurvESMS, BEH",
                      "Inserm-CépiDc via DREES — causes de décès"),
    )

    ax = ig.next_panel("All deaths registered per year (thousands)")
    if allc and "insee" in allc:
        yrs, vals = ctx.full_years(*ctx.series(allc, "insee"))
        vals = [v / 1000 for v in vals]
        ctx.line(ax, yrs, vals, ctx.p.INK)
        ctx.endlabel(ax, yrs, vals, ctx.p.INK, lambda v: f"{v:,.0f}", dy=10)
        # Mayotte enters the état civil series in 2014. The step is small —
        # INSEE publishes both figures for that year and they differ by 566
        # deaths — but it is a break, not a trend, and an unmarked break is
        # the kind of thing a reader later finds and distrusts the whole
        # plate for.
        ax.axvline(2014, color=ctx.p.FAINT, lw=0.9, ls=(0, (4, 3)), zorder=1)
        ax.text(2014.2, 0.06, "2014: Mayotte enters\nthe series (+566)",
                transform=ax.get_xaxis_transform(), fontsize=7.8,
                color=ctx.p.MUTED, style="italic")
        peak = max(zip(yrs, vals), key=lambda t: t[1])
        ax.annotate(f"{peak[1]:,.0f} ({peak[0]:.0f})", peak,
                    textcoords="offset points", xytext=(0, 14), ha="center",
                    fontsize=8.8, fontweight="bold", color=ctx.p.RED)
        ax.set_ylim(500, 720)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("COVID-19 deaths — three counts, three questions")
    if covid:
        hy, hv = ctx.series(covid, "deaths_hospital")
        ty, tv = ctx.series(covid, "deaths_total")
        cy, cv = ctx.series(covid, "deaths_cepidc")
        k = lambda xs: [v / 1000 for v in xs]  # noqa: E731
        if ty:
            ax.bar(ty, k(tv), width=0.58, color=ctx.p.BLUE, alpha=0.30,
                   edgecolor=ctx.p.BLUE, linewidth=0.8, zorder=2)
        if hy:
            ax.bar(hy, k(hv), width=0.58, color=ctx.p.BLUE_D, zorder=3)
        if cy:
            ctx.line(ax, cy, k(cv), ctx.p.RED, lw=2.6, zorder=4)
        # Labelled on the panel. A legend reading "hospital / hospital+ESMS /
        # CépiDc" would be three abbreviations where the reader needs three
        # definitions.
        if hy:
            # Centred over its own bar rather than hung off the left of it:
            # "à l'hôpital" and "no hospital" are longer than "in hospital"
            # and ran into the y axis.
            ax.annotate("in hospital", (hy[0], k(hv)[0]),
                        textcoords="offset points", xytext=(0, 7),
                        fontsize=8.4, fontweight="bold", color=ctx.p.BLUE_D,
                        ha="center")
        if ty:
            # Set out to the right with a leader, because the CépiDc line
            # runs straight through every position next to the bar it names.
            ax.annotate("+ care homes (SPF total)",
                        xy=(ty[0] + 0.28, k(tv)[0] - 4), xytext=(2023.7, 66),
                        fontsize=8.4, fontweight="bold", color=ctx.p.BLUE,
                        arrowprops=dict(arrowstyle="-", color=ctx.p.BLUE, lw=0.8))
        if cy:
            ax.annotate("certified cause of death (CépiDc)",
                        (cy[0], k(cv)[0]), textcoords="offset points",
                        xytext=(16, 16), fontsize=8.4, fontweight="bold",
                        color=ctx.p.RED)
        # The counterintuitive part, said where the lines cross rather than
        # in a corner: the cause-of-death count is the LARGER one in 2020-21,
        # because it sees deaths at home and the surveillance never did.
        ax.text(0.5, -0.125,
                "no 28-day rule in France: the bars count deaths of "
                "infected patients, the line counts COVID as the\n"
                "underlying cause — and it is the larger one, because it "
                "sees deaths at home",
                transform=ax.transAxes, ha="center", va="top",
                fontsize=7.4, color=ctx.p.FAINT, style="italic")
        ax.text(2023.0, 24, "2023: surveillance\nstops 30 June\n(half year)",
                fontsize=7.8, color=ctx.p.MUTED, style="italic", ha="center")
        ax.set_xlim(2019.3, 2026.6)
        ax.set_ylim(0, 80)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Influenza deaths — certified vs estimated (thousands)")
    if flu:
        cy, cv = ctx.series(flu, "deaths_cepidc")
        my, mv = ctx.series(flu, "excess_deaths_spf")
        xy, xv = ctx.series(flu, "excess_all_cause_epidemic_spf")
        k = lambda xs: [v / 1000 for v in xs]  # noqa: E731
        if xy:
            ax.plot(xy, k(xv), ls="none", marker="s", ms=6.5, mfc="none",
                    mec=ctx.p.FAINT, mew=1.4, zorder=3)
        if my:
            ax.plot(my, k(mv), ls="none", marker="D", ms=7, color=ctx.p.GOLD,
                    zorder=4)
        if cy:
            ax.bar(cy, k(cv), width=0.6, color=ctx.p.PURPLE, zorder=5)
        if cy:
            ax.annotate("certified as the\nunderlying cause",
                        (cy[-1], k(cv)[-1]),
                        textcoords="offset points", xytext=(6, 10),
                        fontsize=8.2, fontweight="bold", color=ctx.p.PURPLE)
        if my:
            ax.annotate("SPF model: deaths\nattributable to flu",
                        (my[0], k(mv)[0]), textcoords="offset points",
                        xytext=(-10, -4), ha="right", fontsize=8.2,
                        fontweight="bold", color=ctx.p.GOLD)
        if xy:
            ax.annotate("all-cause excess during\nthe epidemic window",
                        (xy[-1], k(xv)[-1]), textcoords="offset points",
                        xytext=(-6, 8), ha="right", fontsize=8.2,
                        fontweight="bold", color=ctx.p.MUTED)
        if my:
            ax.axvline(max(my) + 0.5, color=ctx.p.FAINT, lw=0.9, ls=(0, (4, 3)),
                       zorder=1)
            ax.text(max(my) + 0.7, 0.55,
                    "SPF discontinued\nthe model after\n2019-20",
                    transform=ax.get_xaxis_transform(), fontsize=7.6,
                    color=ctx.p.MUTED, style="italic", va="top")
        ax.text(0.5, -0.125,
                "an order of magnitude apart because they answer different "
                "questions — the certified count is not the estimate's lower "
                "bound, it is a different thing",
                transform=ax.transAxes, ha="center", fontsize=7.4,
                color=ctx.p.FAINT, style="italic")
        ax.set_ylim(0, 24)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Deaths above the 2015–2019 average (thousands)")
    if allc and "insee" in allc:
        yrs, vals = ctx.full_years(*ctx.series(allc, "insee"))
        base_years = [y for y in yrs if 2015 <= y <= 2019]
        if base_years:
            base = sum(vals[yrs.index(y)] for y in base_years) / len(base_years)
            ex = [(y, (v - base) / 1000) for y, v in zip(yrs, vals)
                  if y >= 2015]
            ax.axhline(0, color=ctx.p.INK, lw=1.0, zorder=2)
            ctx.bars(ax, [y for y, _ in ex], [v for _, v in ex],
                 lambda v: ctx.p.RED if v > 0 else ctx.p.GREEN_D)
            for y, v in ex:
                if abs(v) > 20:
                    ax.annotate(f"{v:+,.0f}k", (y, v),
                                textcoords="offset points", xytext=(0, 6),
                                ha="center", fontsize=8.6,
                                fontweight="bold", color=ctx.p.RED)
            # This is the one number on the plate computed here rather than
            # published, and the comparison is deliberately crude: no age
            # standardisation, so part of every bar after 2019 is simply a
            # larger and older population, not an epidemic.
            ax.text(0.5, -0.125,
                    "computed here, not published: the baseline is the "
                    "mean of the five years before 2020.\nNo age "
                    "standardisation, so part of every bar is simply an "
                    "older population",
                    transform=ax.transAxes, ha="center", fontsize=7.4,
                    color=ctx.p.FAINT, style="italic")
            ax.set_xlim(2014.3, 2026.6)
            ax.set_ylim(-20, 80)
    else:
        ctx.pending(ax)

    for i, ax in enumerate(ig.axes_flat):
        # Panels (b) and (d) carry their own x window: the COVID series does
        # not exist before 2020 and an axis that starts in 2006 draws
        # fourteen years of empty paper.
        ig.style_axis(ax, xticks_years=i not in (1, 3))
    ig.save(ctx.out("10_mortality.png"))

def fig_credit(ctx) -> None:
    """What borrowing costs, how much of it households carry, and who is
    drowning in it.

    The trap this plate exists to avoid: every leverage ratio in it fell
    between 2023 and 2025 while over-indebtedness filings rose by about a
    third. Both are true. They describe different things — a ratio against a
    nominal income that kept growing, and a count of households that reached
    a statutory insolvency commission — and a plate that showed only one of
    them would be telling half a story in either direction.
    """
    rates = ctx.table("credit/lending_rates.csv")
    debt = ctx.table("credit/household_debt.csv")
    stock = ctx.table("credit/credit_outstanding.csv")
    sur = ctx.table("credit/overindebtedness.csv")
    ocm = ctx.table("credit/credit_holding_ocm.csv")
    ig = ctx.fig(
        "Credit — What It Costs, Who Owes It, Who Drowns In It",
        "French mortgages are almost entirely fixed-rate, so the rate shock "
        "of 2022-24 hit new borrowers and left the existing stock alone.",
        source=ctx.source("ECB Data Portal — MIR, BSI, QSA (reported by the Banque de France)",
                      "Eurostat nasa_10_f_bs · BIS",
                      "Banque de France — surendettement; OCM (industry survey)"),
    )

    ax = ig.next_panel("Interest rates on loans to households (%)")
    if rates:
        hy, hv = ctx.full_years(*ctx.series(rates, "housing_new_total_pct"))
        cy, cv = ctx.full_years(*ctx.series(rates, "consumer_new_total_pct"))
        ny, nv = ctx.full_years(*ctx.series(rates, "nfc_new_total_pct"))
        sy, sv = ctx.full_years(*ctx.series(rates, "housing_outstanding_stock_pct"))
        if cy:
            ctx.line(ax, cy, cv, ctx.p.PURPLE, label="New consumer credit")
        if hy:
            ctx.line(ax, hy, hv, ctx.p.BLUE_D, label="New housing loans")
        if ny:
            ctx.line(ax, ny, nv, ctx.p.TEAL, label="New loans to companies", lw=1.9)
        if sy:
            ctx.line(ax, sy, sv, ctx.p.GOLD, label="Rate carried by the existing "
                 "housing stock", lw=2.0, ls=(0, (5, 3)), marker="",
                 dashed_partial=False)
            ctx.endlabel(ax, sy, sv, ctx.p.GOLD, lambda v: f"{v:.2f}%", dy=-18)
        # Two columns at the top: a four-entry legend in a corner of this
        # panel is a tall box, and the only free corner is the one the
        # annotation needs.
        ax.legend(loc="upper left", fontsize=8.0, ncol=2)
        # The fact the whole plate turns on, said next to the line it is
        # about: new rates tripled and the stock barely moved, because the
        # stock is fixed-rate. ACPR puts it at 98.5% of outstanding in 2024.
        ax.annotate("98.5% of the outstanding stock is fixed-rate,\n"
                    "so a rate shock barely touches it",
                    xy=(2023, 1.9), xytext=(2008.0, 1.0), fontsize=8.0,
                    color=ctx.p.MUTED, style="italic",
                    arrowprops=dict(arrowstyle="-", color=ctx.p.FAINT, lw=0.8))
        part = ctx.partial_row(rates)
        if part and part.get("housing_new_total_pct") == part.get("housing_new_total_pct"):
            ax.text(0.5, -0.125, f"annual averages; {part['year']:.0f} is "
                    "a part-year and is not drawn",
                    transform=ax.transAxes, ha="center", fontsize=7.4,
                    color=ctx.p.FAINT, style="italic")
        ax.set_ylim(0, 9)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Household debt, and what it costs to service (%)")
    if debt:
        gy, gv = ctx.series(debt, "hh_debt_pct_gdi_ecb_nco_q4")
        if gy:
            ctx.line(ax, gy, gv, ctx.p.RED)
            ax.fill_between(gy, 40, gv, color=ctx.p.RED, alpha=0.07, lw=0)
            ctx.endlabel(ax, gy, gv, ctx.p.RED, lambda v: f"{v:.1f}%", dy=-20)
            peak = max(zip(gy, gv), key=lambda t: t[1])
            ax.annotate(f"{peak[1]:.1f}% ({peak[0]:.0f})", peak,
                        textcoords="offset points", xytext=(0, 12),
                        ha="center", fontsize=8.8, fontweight="bold",
                        color=ctx.p.RED)
            ax.annotate("debt as a share of disposable income",
                        (gy[0], gv[0]), textcoords="offset points",
                        xytext=(8, 10), fontsize=8.4, fontweight="bold",
                        color=ctx.p.RED)
        ax.set_ylim(40, 115)

        # The debt-service ratio belongs beside the stock rather than on its
        # own panel: the whole point is that one tripled over the period
        # while the other did not move at all.
        serv = ax.twinx()
        dy_, dv = ctx.full_years(*ctx.series(debt, "hh_debt_service_ratio_pct_bis_qavg"))
        if dy_:
            serv.plot(dy_, dv, color=ctx.p.NAVY, lw=2.0, ls=(0, (4, 2)), zorder=5)
            serv.annotate("share of income spent servicing it (right axis)",
                          (dy_[len(dy_) // 2], dv[len(dv) // 2]),
                          textcoords="offset points", xytext=(-4, -26),
                          ha="center", fontsize=8.2, fontweight="bold",
                          color=ctx.p.NAVY)
        serv.set_ylim(0, 20)
        serv.tick_params(axis="y", colors=ctx.p.NAVY, labelsize=8.5, length=0)
        serv.spines[["top", "left", "right"]].set_visible(False)
        serv.grid(False)
        serv.set_xlim(ctx.YEARS[0] - 0.6, ctx.YEARS[-1] + 0.6)
        serv.xaxis.set_visible(False)
        serv.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
        ax.text(0.5, -0.125, "non-consolidated, against adjusted gross "
                "disposable income - the Banque de France's own definition",
                transform=ax.transAxes, ha="center", fontsize=7.4,
                color=ctx.p.FAINT, style="italic")
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Outstanding credit to households (€ billion)")
    if stock:
        ay, av = ctx.full_years(*ctx.series(stock, "hh_loans_total_adj_eur_bn"))
        uy, uv = ctx.full_years(*ctx.series(stock, "hh_loans_total_eur_bn"))
        if ay:
            ctx.line(ax, ay, av, ctx.p.BLUE, marker="")
            ax.fill_between(ay, 0, av, color=ctx.p.BLUE, alpha=0.08, lw=0)
            ctx.endlabel(ax, ay, av, ctx.p.BLUE, lambda v: f"€{v:,.0f}bn", dy=-20)
            # Anchored near the start rather than a third of the way in:
            # the Portuguese of this label is half as long again as the
            # English and ran into the one at the other end of the line.
            ax.annotate("including loans sold on or securitised",
                        (ay[min(2, len(ay) - 1)], av[min(2, len(av) - 1)]),
                        textcoords="offset points", xytext=(6, 14),
                        fontsize=8.2, fontweight="bold", color=ctx.p.BLUE)
        if uy:
            ctx.line(ax, uy, uv, ctx.p.FAINT, lw=1.8, ls=(0, (5, 3)), marker="",
                 dashed_partial=False)
            ax.annotate("still on the banks' own books",
                        (uy[-1], uv[-1]), textcoords="offset points",
                        xytext=(-6, -28), ha="right", fontsize=8.2,
                        fontweight="bold", color=ctx.p.MUTED)
        gy, gv = ctx.full_years(*ctx.series(stock, "growth_total_adj_pct"))
        if gy:
            # The credit flow, which the stock alone hides: it grew in double
            # digits before the crisis and has barely moved since 2023. Shown
            # as two value labels under one static caption, so the panel does
            # not need re-translating every time the numbers move.
            ax.text(2006.0, 2130, "annual growth of the stock", fontsize=8.2,
                    color=ctx.p.MUTED, style="italic")
            ax.text(2006.0, 1990, f"{gv[0]:+.1f}%", fontsize=9.6,
                    fontweight="bold", color=ctx.p.MUTED)
            ax.text(float(gy[-1]), 1990, f"{gv[-1]:+.1f}%", fontsize=9.6,
                    fontweight="bold", color=ctx.p.MUTED, ha="right")
        part = ctx.partial_row(stock)
        if part and part.get("hh_loans_total_adj_eur_bn") == part.get("hh_loans_total_adj_eur_bn"):
            ax.text(0.5, -0.125, "December stocks; the latest reading is "
                    f"mid-{part['year']:.0f}, which is not a year end "
                    "and is not drawn",
                    transform=ax.transAxes, ha="center", fontsize=7.4,
                    color=ctx.p.FAINT, style="italic")
        ax.set_ylim(0, 2250)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Over-indebtedness filings, and who holds credit")
    if sur:
        fy, fv = ctx.full_years(*ctx.series(sur, "dossiers_deposes_published"))
        wy, wv = ctx.full_years(*ctx.series(sur, "dossiers_deposes_webstat"))
        # Two sources for one count, drawn as two kinds of bar rather than
        # one merged series: the Banque de France printed a figure for
        # 2007-2018 and 2022-2025, and its machine-readable series — which
        # starts only in January 2019 — covers the years in between. A single
        # gold run would claim a continuity that the sources do not have; a
        # gap would claim three years with no filings.
        only_web = [(y, v) for y, v in zip(wy, wv) if y not in set(fy)]
        if only_web:
            ctx.bars(ax, [y for y, _ in only_web],
                 [v / 1000 for _, v in only_web], lambda v: ctx.p.paper,
                 hatch_partial=False, edge=ctx.p.GOLD)
            # Inside the hollow bars, above everything: placed over them it
            # was drawn behind the neighbouring solid bars and came out cut
            # in half.
            ax.text(only_web[len(only_web) // 2][0], 52,
                    "no published figure\nfor these years —\n"
                    "the Banque de France's\nmachine-readable series\n"
                    "is used instead",
                    ha="center", va="center", fontsize=7.4, color=ctx.p.MUTED,
                    style="italic", zorder=6)
        if fy:
            ctx.bars(ax, fy, [v / 1000 for v in fv], lambda v: ctx.p.GOLD,
                 hatch_partial=False)
            peak = max(zip(fy, fv), key=lambda t: t[1])
            # Inside the bar, not above it: the share line runs just over the
            # 2011 peak, and a label above the bar lands on top of it.
            ax.annotate(f"{peak[1] / 1000:,.0f}k",
                        (peak[0], peak[1] / 1000),
                        textcoords="offset points", xytext=(0, -7),
                        ha="center", va="top", fontsize=8.6,
                        fontweight="bold", color=ctx.p.INK)
            ax.annotate("dossiers filed with a commission\nde surendettement "
                        "(thousands)", (fy[-1], fv[-1] / 1000),
                        textcoords="offset points", xytext=(-4, 16),
                        ha="right", fontsize=8.2, fontweight="bold",
                        color=ctx.p.GOLD)
        ax.set_ylim(0, 300)

        if ocm:
            share = ax.twinx()
            oy, ov = ctx.series(ocm, "share_any_credit_pct")
            if oy:
                share.plot(oy, ov, color=ctx.p.GREEN_D, lw=2.2, marker="o", ms=3.6,
                           zorder=5)
                share.annotate("households holding any credit, %\n"
                               "(industry survey, right axis)",
                               (oy[len(oy) // 2], ov[len(ov) // 2]),
                               textcoords="offset points", xytext=(0, 14),
                               ha="center", fontsize=8.2, fontweight="bold",
                               color=ctx.p.GREEN_D)
            share.set_ylim(0, 60)
            share.tick_params(axis="y", colors=ctx.p.GREEN_D, labelsize=8.5,
                              length=0)
            share.spines[["top", "left", "right"]].set_visible(False)
            share.grid(False)
            share.set_xlim(ctx.YEARS[0] - 0.6, ctx.YEARS[-1] + 0.6)
            share.xaxis.set_visible(False)
            share.yaxis.set_major_formatter(
                mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
        # The reading to be careful with, stated on the panel rather than
        # left for the reader to be caught by.
        ax.text(0.5, -0.125, "filings rose after 2022 while every debt ratio "
                "fell: different populations, not a contradiction",
                transform=ax.transAxes, ha="center", fontsize=7.4,
                color=ctx.p.FAINT, style="italic")
    else:
        ctx.pending(ax)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("11_credit.png"))


# The plates, in the order the page lists them.
PLATES = (

    ("fig_economy", fig_economy),

    ("fig_fiscal", fig_fiscal),

    ("fig_spending", fig_spending),

    ("fig_trade", fig_trade),

    ("fig_markets", fig_markets),

    ("fig_people", fig_people),

    ("fig_world", fig_world),

    ("fig_demographics", fig_demographics),

    ("fig_security", fig_security),

    ("fig_mortality", fig_mortality),

    ("fig_credit", fig_credit),

)
