"""The brasil plates.

Each function draws one plate from this country's committed CSVs and saves it
through the context, which resolves every path under countries/brasil/ and
knows this country's palette, year span and last complete year. Ported from
the standalone brasil-reports scripts/charts.py; the drawing is unchanged.
"""
from __future__ import annotations

import matplotlib.ticker as mticker
import numpy as np

from countries.brasil.events import EVENTS

# Defined here rather than in the palette because it is only ever the
# "previdência" slice and the Selic line — two specific series, not a role.
NAVY_C = "#12355B"


def fig_economy(ctx) -> None:
    gdp = ctx.table("macro/gdp.csv")
    ipca = ctx.table("macro/ipca.csv")
    ig = ctx.fig(
        "The Brazilian Economy, 2006–2026",
        "Nominal size, real growth, income per person and inflation — the four "
        "numbers that frame everything else.",
        source=ctx.source("IBGE Contas Nacionais / Sistema SGS-BCB (IPCA)", "IPCA target: CMN/Banco Central"),
    )

    # (a) nominal GDP
    ax = ig.next_panel("GDP — nominal size (R$ trillion)")
    if gdp and "nominal_rbi" in gdp:
        yrs, vals = ctx.series(gdp, "nominal_rbi")
        vals_tn = [v / 1000 for v in vals]
        ctx.bars(ax, yrs, vals_tn, lambda v: ctx.p.GREEN_D)
        for y, v in zip(yrs, vals_tn):
            if y in (2006, 2010, 2014, 2019, 2023, 2025, 2026):
                ax.annotate(f"{v:.1f}", (y, v), textcoords="offset points",
                            xytext=(0, 4), ha="center", fontsize=9,
                            fontweight="bold", color=ctx.p.INK)
        ig.mark_partial(ax, 2026)
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 14)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}"))

    # (b) real growth
    ax = ig.next_panel("Real GDP growth (% per year)")
    if gdp and "real_growth" in gdp:
        yrs, vals = ctx.series(gdp, "real_growth")
        ax.axhline(0, color=ctx.p.MUTED, lw=1.0)
        ctx.bars(ax, yrs, vals, lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED)
        for b0, b1, lab in ((2014, 2016.9, "recession"), (2020, 2020.9, "COVID")):
            ax.axvspan(b0, b1, color=ctx.p.BAND, zorder=0)
        for y, v in zip(yrs, vals):
            if abs(v) > 3 or y in (2006, 2025):
                va = "bottom" if v >= 0 else "top"
                off = 4 if v >= 0 else -6
                ax.annotate(f"{v:+.1f}", (y, v), textcoords="offset points",
                            xytext=(0, off), ha="center", va=va, fontsize=9,
                            fontweight="bold",
                            color=ctx.p.GREEN_D if v >= 0 else ctx.p.RED)
        ig.mark_partial(ax, 2026, "est.")
    else:
        ctx.pending(ax)
    ax.set_ylim(-4.6, 8.6)

    # (c) GDP per capita
    ax = ig.next_panel("GDP per capita (US$, current)")
    if gdp and "gdp_per_capita_usd" in gdp:
        yrs, vals = ctx.series(gdp, "gdp_per_capita_usd")
        ctx.line(ax, yrs, vals, ctx.p.BLUE)
        ctx.endlabel(ax, yrs, vals, ctx.p.BLUE, lambda v: f"US$ {v:,.0f}")
        ig.add_event(ax, 2010.9, "commodity boom peak", dy=0.95)
        ig.add_event(ax, 2020.1, "COVID + BRL slump", dy=0.95)
    else:
        ctx.pending(ax)
    # the series peaks at US$ 13,323 (2011): a tighter ceiling clipped the
    # whole commodity-boom hump the annotation above points at.
    ax.set_ylim(4000, 14600)

    # (d) IPCA vs target
    ax = ig.next_panel("Inflation — IPCA (% per year) vs target band")
    if ipca:
        yrs, vals = ctx.series(ipca, "value")
        tgt = {2006: 4.5, 2007: 4.5, 2008: 4.5, 2009: 4.5, 2010: 4.5, 2011: 4.5,
               2012: 4.5, 2013: 4.5, 2014: 4.5, 2015: 4.5, 2016: 4.5, 2017: 4.5,
               2018: 4.5, 2019: 4.25, 2020: 4.0, 2021: 3.75, 2022: 3.5,
               2023: 3.25, 2024: 3.0, 2025: 3.0, 2026: 3.0}
        tg = [tgt.get(y, np.nan) for y in ctx.YEARS]
        lo = [t - 2.0 if y < 2017 else t - 1.5 for y, t in zip(ctx.YEARS, tg)]
        hi = [t + 2.0 if y < 2017 else t + 1.5 for y, t in zip(ctx.YEARS, tg)]
        ax.fill_between(ctx.YEARS, lo, hi, color=ctx.p.BLUE, alpha=0.12, lw=0)
        ax.plot(ctx.YEARS, tg, color=ctx.p.BLUE, lw=1.3, ls="--", label="target center")
        ctx.line(ax, yrs, vals, ctx.p.RED, label="IPCA")
        for y, v in zip(yrs, vals):
            if v > 6 or y in (2025,):
                ax.annotate(f"{v:.1f}", (y, v), textcoords="offset points",
                            xytext=(0, 5), ha="center", fontsize=9,
                            fontweight="bold", color=ctx.p.RED)
        ax.legend(loc="upper right")
        ig.mark_partial(ax, 2026, "YTD Sep")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 12)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("01_economy.png"))

def fig_fiscal(ctx) -> None:
    tax = ctx.table("fiscal/tax_burden.csv")
    prim = ctx.table("fiscal/primary_result.csv")
    debt = ctx.table("fiscal/debt.csv")
    ig = ctx.fig(
        "Taxes, Primary Balance & Public Debt, 2006–2026",
        "How much of the economy the state collects, whether it spends more than "
        "it raises, and what that does to debt — all relative to GDP.",
        source=ctx.source("Receita Federal/IBGE (carga tributária)", "Tesouro Nacional / BCB (debt, primary result)"),
    )

    ax = ig.next_panel("Tax burden — carga tributária (% of GDP)")
    if tax:
        yrs, vals = ctx.series(tax, "value")
        old_y = [y for y, v in zip(tax["year"], tax["value"])
                 if v == v and "methodology" in tax and tax["methodology"][tax["year"].index(y)] == "old"]
        old_v = [v for y, v in zip(tax["year"], tax["value"])
                 if v == v and "methodology" in tax and tax["methodology"][tax["year"].index(y)] == "old"]
        ctx.line(ax, yrs, vals, ctx.p.GREEN_D)
        ax.fill_between(yrs, 0, vals, color=ctx.p.GREEN_D, alpha=0.08, zorder=1)
        if old_y:  # old-methodology segment (higher level): hollow markers
            ax.plot(old_y, old_v, ls="none", marker="o", mfc="none",
                    mec=ctx.p.GREEN_D, ms=6, mew=1.4, zorder=4)
        ax.axvline(2010, color=ctx.p.FAINT, lw=0.9, ls=(0, (4, 3)))
        ax.text(2010.15, 34.9, "2010: series break — FGTS/Sistema S\nexcluded (level −1.8pp, methodology only)",
                fontsize=7.8, color=ctx.p.MUTED, style="italic", va="top")
        ctx.endlabel(ax, yrs, vals, ctx.p.GREEN_D, lambda v: f"{v:.1f}%")
        for y, v in zip(yrs, vals):
            if y in (2014, 2020):
                ax.annotate(f"{v:.1f}%", (y, v), textcoords="offset points",
                            xytext=(0, -14), ha="center", fontsize=8.6, color=ctx.p.MUTED)
    else:
        ctx.pending(ax)
    ax.set_ylim(28, 36)

    ax = ig.next_panel("Primary result — central government (% of GDP)")
    if prim:
        yrs, vals = ctx.series(prim, "value")
        ax.axhline(0, color=ctx.p.MUTED, lw=1.0)
        ctx.bars(ax, yrs, vals, lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED)
        ig.mark_partial(ax, 2026)
    else:
        ctx.pending(ax)
    ax.set_ylim(-12, 5)

    ax = ig.next_panel("Gross general government debt (% of GDP, year-end)")
    if debt and "gross" in debt:
        yrs, vals = ctx.series(debt, "gross")
        ctx.line(ax, yrs, vals, ctx.p.RED)
        ax.fill_between(yrs, 0, vals, color=ctx.p.RED, alpha=0.06, zorder=1)
        ctx.endlabel(ax, yrs, vals, ctx.p.RED, lambda v: f"{v:.1f}%")
        for y, v in zip(yrs, vals):
            if y in (2010, 2016, 2020, 2024, 2026):
                ax.annotate(f"{v:.0f}%", (y, v), textcoords="offset points",
                            xytext=(0, -14), ha="center", fontsize=8.6, color=ctx.p.MUTED)
        ig.mark_partial(ax, 2026, "Aug")
    else:
        ctx.pending(ax)
    ax.set_ylim(40, 95)

    ax = ig.next_panel("Net public sector debt — DLSP (% of GDP, year-end)")
    if debt and "net" in debt:
        yrs, vals = ctx.series(debt, "net")
        ctx.line(ax, yrs, vals, ctx.p.PURPLE)
        ctx.endlabel(ax, yrs, vals, ctx.p.PURPLE, lambda v: f"{v:.1f}%")
        ax.text(2015.6, 49.0, "2015-16: nominal deficits\nnear 10% of GDP",
                fontsize=7.8, color=ctx.p.MUTED, style="italic")
        ig.mark_partial(ax, 2026, "Aug")
    else:
        ctx.pending(ax)
    ax.set_ylim(25, 72)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("02_fiscal.png"))

def fig_spending(ctx) -> None:
    spend = ctx.table("fiscal/spending_by_function.csv")
    inv = ctx.table("fiscal/investment.csv")
    ig = ctx.fig(
        "Where the Money Goes — Federal Spending vs Investment, 2006–2025",
        "Federal outlays by area (as % of GDP) and the small slice that is "
        "actual public investment.",
        source=ctx.source("Tesouro Nacional — Balanço Geral da União / IBGE (FBCF)"),
    )

    ORDER = ["previdencia", "encargos_especiais", "assistencia", "saude",
             "educacao", "defesa_seguranca", "outras"]
    LABEL = {"previdencia": "Social security (INSS)", "saude": "Health",
             "educacao": "Education", "assistencia": "Welfare / aid",
             "encargos_especiais": "Special charges (interest, transfers)",
             "defesa_seguranca": "Defense & security", "outras": "Other functions"}
    COLORS = {"previdencia": NAVY_C, "saude": ctx.p.TEAL, "educacao": ctx.p.BLUE,
              "assistencia": ctx.p.YELLOW, "encargos_especiais": ctx.p.RED,
              "defesa_seguranca": ctx.p.PURPLE, "outras": "#B9BDC7"}
    if spend:
        cols = [c for c in ORDER if c in spend]
    else:
        cols = []

    ax = ig.next_panel("Federal spending by function (% of GDP)")
    if spend and cols:
        years = spend["year"]
        stack = {c: spend[c] for c in cols}
        ax.stackplot(years, *[stack[c] for c in cols],
                     labels=[LABEL[c] for c in cols],
                     colors=[COLORS[c] for c in cols], alpha=0.92, lw=0)
        ax.set_ylim(0, 42)
        ax.legend(loc="upper left", fontsize=8.2, ncol=2)
        ig.add_event(ax, 2020.25, "emergency aid", dy=0.55)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Mandates vs investment (% of GDP)")
    if spend and cols and "investimento_gnd4" in spend:
        mand = [(p if p == p else 0) + (s if s == s else 0) + (e if e == e else 0)
                + (a if a == a else 0)
                for p, s, e, a in zip(spend["previdencia"], spend["saude"],
                                      spend["educacao"], spend["assistencia"])]
        invf = spend["investimento_gnd4"]
        ax.plot(spend["year"], mand, color=ctx.p.RED, lw=2.6,
                label="Social mandates (pensions, health, education, aid)")
        ax.fill_between(spend["year"], 0, mand, color=ctx.p.RED, alpha=0.07)
        ax.plot(spend["year"], invf, color=ctx.p.GREEN_D, lw=2.6,
                label="Federal investment (GND4)")
        ax.fill_between(spend["year"], 0, invf, color=ctx.p.GREEN_D, alpha=0.16)
        ax.legend(loc="center right", fontsize=8.6)
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 20)

    ax = ig.next_panel("Investment rate — whole economy FBCF (% of GDP)")
    if inv and "fbcf_pib" in inv:
        yrs, vals = ctx.series(inv, "fbcf_pib")
        ctx.line(ax, yrs, vals, ctx.p.BLUE)
        ctx.endlabel(ax, yrs, vals, ctx.p.BLUE, lambda v: f"{v:.1f}%")
        for y, v in zip(yrs, vals):
            if y in (2013, 2017, 2025):
                ax.annotate(f"{v:.1f}%", (y, v), textcoords="offset points",
                            xytext=(0, -15), ha="center", fontsize=8.8,
                            color=ctx.p.MUTED)
    else:
        ctx.pending(ax)
    ax.set_ylim(12, 23)

    ax = ig.next_panel("Federal investment — Tesouro RTN, paid (% of GDP)")
    if inv and "federal_rtn_gnd45_pib" in inv:
        yrs, vals = ctx.series(inv, "federal_rtn_gnd45_pib")
        ctx.line(ax, yrs, vals, ctx.p.GREEN_D)
        ctx.endlabel(ax, yrs, vals, ctx.p.GREEN_D, lambda v: f"{v:.2f}%")
        ax.text(2010.3, 0.05, "series starts 2008 (Tesouro RTN)", fontsize=8,
                color=ctx.p.FAINT, style="italic")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 1.6)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("03_spending.png"))

def fig_trade(ctx) -> None:
    tr = ctx.table("trade/trade.csv")
    prods = ctx.table("trade/exports_products.csv")
    dest = ctx.table("trade/destinations.csv")
    ig = ctx.fig(
        "Foreign Trade — Exports, Imports & the Surplus, 2006–2026",
        "Brazil's commodity-heavy export machine: soybeans, iron ore and oil "
        "versus a diversified import bill. 2026 = Jan–Sep.",
        source=ctx.source("MDIC/SECEX — consolidated historical series (US$ FOB)",
               "SECEX restates 2012–19 vs. first-published figures"),
    )

    ax = ig.next_panel("Exports vs imports (US$ billion, FOB)")
    if tr and "exports" in tr and "imports" in tr:
        ey, ev = ctx.series(tr, "exports")
        iy, iv = ctx.series(tr, "imports")
        ctx.line(ax, ey, ev, ctx.p.GREEN_D, label="Exports")
        ctx.line(ax, iy, iv, ctx.p.BLUE, label="Imports")
        ctx.endlabel(ax, ey, ev, ctx.p.GREEN_D, lambda v: f"US$ {v:,.0f}bn", dy=-16)
        ctx.endlabel(ax, iy, iv, ctx.p.BLUE, lambda v: f"US$ {v:,.0f}bn")
        ax.legend(loc="upper left")
        ig.mark_partial(ax, 2026, "YTD")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 400)

    ax = ig.next_panel("Trade balance (US$ billion)")
    if tr and "balance" in tr:
        yrs, vals = ctx.series(tr, "balance")
        ax.axhline(0, color=ctx.p.MUTED, lw=1.0)
        ctx.bars(ax, yrs, vals, lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED)
        for y, v in zip(yrs, vals):
            if y in (2014, 2023, 2025, 2026):
                if v >= 0:
                    ax.annotate(f"{v:+,.0f}", (y, v), textcoords="offset points",
                                xytext=(0, 4), ha="center", va="bottom",
                                fontsize=9, fontweight="bold", color=ctx.p.GREEN_D)
                else:
                    ax.annotate(f"{v:+,.0f}", (y, v), textcoords="offset points",
                                xytext=(0, -4), ha="center", va="top",
                                fontsize=9, fontweight="bold", color=ctx.p.RED)
        ig.mark_partial(ax, 2026, "YTD")
    else:
        ctx.pending(ax)
    ax.set_ylim(-16, 115)

    ax = ig.next_panel("What Brazil exports — top groups (US$ bn)")
    pick: list[int] = []
    if prods:
        years = sorted({int(y) for y in prods["year"]})
        pick = [y for y in (2006, 2010, 2015, 2020, 2025) if y in years]
        # "others" is a residual bucket, not a product group: it is bigger than
        # any named group and would flatten the rest of the panel. The note
        # below keeps the omission visible.
        ORDER = ["oil", "soy", "iron", "meat", "sugar", "coffee", "corn",
                 "pulp", "steel", "autos", "aircraft"]
        LABEL = {"oil": "Oil & refined", "soy": "Soy complex", "iron": "Iron ore",
                 "meat": "Meats", "sugar": "Sugar & ethanol", "coffee": "Coffee",
                 "corn": "Corn", "pulp": "Pulp", "steel": "Steel",
                 "autos": "Automobiles", "aircraft": "Aircraft"}
        pal = {"soy": ctx.p.GREEN_D, "iron": "#8A6D3B", "oil": ctx.p.INK, "meat": ctx.p.RED,
               "sugar": ctx.p.YELLOW, "coffee": "#6F4E37", "corn": "#D4A017",
               "pulp": ctx.p.TEAL, "steel": "#7A828E", "autos": ctx.p.PURPLE,
               "aircraft": ctx.p.BLUE}
        usbi = {(int(y), p): v for y, p, v
                in zip(prods["year"], prods["product"], prods["usbi"])}
        # the snapshot years are unevenly spaced (2006, 2010, 2015, 2020, 2025),
        # so the bars sit at categorical positions: plotted at year coordinates
        # the whole group spans 0.82 of a 21-year axis and renders as hairlines.
        xs = np.arange(len(pick))
        width = 0.82 / len(ORDER)
        for i, p in enumerate(ORDER):
            vals = [usbi.get((y, p), 0) for y in pick]
            ax.bar(xs + i * width - 0.82 / 2 + width / 2,
                   vals, width=width, label=LABEL[p], color=pal.get(p, "#B9BDC7"),
                   edgecolor="white", linewidth=0.5, zorder=3)
        ax.legend(fontsize=7.6, ncol=4, loc="upper left")
        resid = usbi.get((pick[-1], "others"), 0) if pick else 0
        ax.text(0.5, -0.125, f"excludes the 'others' residual "
                f"(US$ {resid:,.0f}bn in {pick[-1]})" if resid else "",
                transform=ax.transAxes, ha="center", fontsize=7.6,
                color=ctx.p.FAINT, style="italic")
        ax.set_ylim(0, 78)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Export destinations — share of total (%)")
    if dest:
        # the country is a value in the "destiny" column, not a column itself
        names = set(dest["destiny"])
        for cname, color in (("China", ctx.p.RED), ("United States", ctx.p.BLUE),
                             ("European Union", ctx.p.TEAL), ("Argentina", ctx.p.YELLOW)):
            if cname in names:
                yrs, vals = [], []
                for y, name, share in zip(dest["year"], dest["destiny"], dest["share_pct"]):
                    if name == cname:
                        yrs.append(int(y))
                        vals.append(share)
                ctx.line(ax, yrs, vals, color, label=cname, marker="D", ms=4)
        ax.legend(loc="upper left")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 36)

    for i, ax in enumerate(ig.axes_flat):
        # panel (c) is categorical (snapshot years), not a continuous year axis
        ig.style_axis(ax, xticks_years=i != 2)
    # panel (c): one evenly-spaced tick per snapshot year
    ax_c = ig.axes_flat[2]
    if pick:
        ax_c.set_xticks(np.arange(len(pick)))
        ax_c.set_xticklabels([str(y) for y in pick])
        ax_c.set_xlim(-0.5, len(pick) - 0.5)
    # panel (b): balance panel reads better with integer ticks
    ig.axes_flat[1].yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ig.save(ctx.out("06_trade.png"))

def fig_markets(ctx) -> None:
    ibov = ctx.table("markets/ibov.csv")
    sp = ctx.table("markets/sp500.csv")
    usd = ctx.table("macro/dollar.csv")
    selic = ctx.table("macro/selic.csv")
    ipca = ctx.table("macro/ipca.csv")
    ig = ctx.fig(
        "Money & Markets — IBOV vs S&P 500, the Real and Interest Rates",
        "Brazilian equities in reais, in dollars, and next to the S&P 500: the "
        "currency is half of the story.",
        source=ctx.source("B3 / S&P (index closes)", "Banco Central SGS (PTAX, Selic)", "IBGE (IPCA)"),
    )

    ax = ig.next_panel("R$100 invested in 2005 — IBOV vs S&P 500 (local terms)")
    if ibov and sp and usd:
        base_year = min(ibov["year"])
        def idx(t, col, base_col):
            base = next(v for y, v in zip(t["year"], t[base_col]) if v == v)
            return {y: v / base * 100 for y, v in zip(t["year"], t[col]) if v == v}
        i_idx = idx(ibov, "close", "close")
        s_idx = idx(sp, "close", "close")
        u_eop = {int(y): v for y, v in zip(usd["year"], usd["eop"]) if v == v}
        # never default this: a missing base year used to fall back to 1,
        # which multiplied the line by the nominal rate instead of its ratio
        # to the base and inflated it by the whole 2005 exchange rate
        if base_year not in u_eop:
            raise SystemExit(
                f"dollar.csv has no {base_year} end-of-period rate, so the "
                f"'R$100 invested in {base_year}' panel cannot be rebased")
        u_base = u_eop[base_year]
        s_brl = {y: v * u_eop[y] / u_base for y, v in s_idx.items() if y in u_eop}
        yy = sorted(set(i_idx) & set(s_brl))
        ax.semilogy(sorted(i_idx), [i_idx[y] for y in sorted(i_idx)],
                    ctx.p.GREEN_D, lw=2.5, marker="o", ms=3.6, label="IBOV (BRL)")
        # s_brl is the index converted *into* reais (multiplied by the FX
        # ratio), s_idx is the native USD index — the labels were swapped.
        ax.semilogy(yy, [s_brl[y] for y in yy], ctx.p.BLUE, lw=2.5, marker="o",
                    ms=3.6, label="S&P 500 (in BRL)")
        ax.semilogy(yy, [s_idx[y] for y in yy], ctx.p.TEAL, lw=2.0, ls="--",
                    marker="o", ms=3.2, label="S&P 500 (USD)")
        ax.legend(loc="lower right")
        fmt = mticker.FuncFormatter(lambda v, _: f"{v:,.0f}")
        ax.yaxis.set_major_formatter(fmt)
        ax.yaxis.set_minor_formatter(mticker.NullFormatter())
        for y in (2008, 2021, 2026):
            if y in i_idx:
                ax.annotate(f"{i_idx[y]:,.0f}", (y, i_idx[y]),
                            textcoords="offset points", xytext=(0, 6),
                            fontsize=8.8, fontweight="bold", color=ctx.p.GREEN_D,
                            ha="center")
        ig.add_event(ax, 2008.75, "crisis", dy=0.98)
        ig.add_event(ax, 2020.9, "2020-21 BRL crash", dy=0.72)
        ig.mark_partial(ax, 2026, "Oct 20")
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Exchange rate — USD/BRL (PTAX, year-end)")
    if usd and "eop" in usd:
        yrs, vals = ctx.series(usd, "eop")
        ctx.line(ax, yrs, vals, ctx.p.RED)
        ctx.endlabel(ax, yrs, vals, ctx.p.RED, lambda v: f"R$ {v:.2f}", dy=10)
        for y, v in zip(yrs, vals):
            if y in (2007, 2011, 2015, 2020, 2024):
                ax.annotate(f"{v:.2f}", (y, v), textcoords="offset points",
                            xytext=(0, -16), ha="center", fontsize=8.8,
                            color=ctx.p.MUTED)
        ig.mark_partial(ax, 2026, "Oct")
    else:
        ctx.pending(ax)
    ax.set_ylim(1.4, 6.6)

    ax = ig.next_panel("Policy rate vs inflation — Selic (% a.a., year-end) vs IPCA")
    if selic and ipca:
        sy, sv = ctx.series(selic, "value")
        iy, iv = ctx.series(ipca, "value")
        ctx.line(ax, sy, sv, NAVY_C, label="Selic")
        ctx.line(ax, iy, iv, ctx.p.RED, label="IPCA")
        # upper right collides with the 2025 "20-year high" annotation
        ax.legend(loc="upper left")
        ax.annotate("15% — 20-year high\n(2025)", (2025, 15), textcoords="offset points",
                    xytext=(-30, -34), fontsize=8.6, color=NAVY_C,
                    fontweight="bold", ha="center")
        ig.mark_partial(ax, 2026, "Selic: level Oct")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 17)

    # rebase on the first year both the index and the FX series cover, so the
    # baseline is always a real USD-converted close and the title says which
    # year it is rather than asserting one the data may not have.
    u_eop = {int(y): v for y, v in zip(usd["year"], usd["eop"]) if v == v} if usd else {}
    closes = {int(y): c for y, c in zip(ibov["year"], ibov["close"])
              if c == c and int(y) in u_eop} if ibov else {}
    base_year = min(closes, default=None)
    ax = ig.next_panel(f"IBOV in US dollars (rebased {base_year} = 100)"
                       if base_year else "IBOV in US dollars")
    if base_year:
        base, u_base = closes[base_year], u_eop[base_year]
        yy = sorted(closes)
        vals = [closes[y] / base * u_base / u_eop[y] * 100 for y in yy]
        ctx.line(ax, yy, vals, ctx.p.GREEN)
        ctx.endlabel(ax, yy, vals, ctx.p.GREEN, lambda v: f"{v:,.0f}", dy=10)
        ax.axhline(100, color=ctx.p.MUTED, lw=1.0, ls=":")
        ig.mark_partial(ax, 2026, "Oct 20")
    else:
        ctx.pending(ax)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("04_markets.png"))

def fig_people(ctx) -> None:
    hdi = ctx.table("social/hdi.csv")
    gini = ctx.table("social/gini.csv")
    unemp = ctx.table("macro/unemployment.csv")
    mw = ctx.table("macro/minimum_wage.csv")
    pov = ctx.table("social/poverty.csv")
    ipca = ctx.table("macro/ipca.csv")
    ig = ctx.fig(
        "People — Development, Inequality, Jobs, Wages & Poverty, 2006–2026",
        "Slow, steady social progress: HDI up, inequality down, unemployment at "
        "record lows, minimum wage up in real terms, poverty cut by half.",
        ncols=3, nrows=2,
        source=ctx.source("UNDP HDR 2025 (HDI)", "IBGE PNAD-C / World Bank PIP (Gini, poverty)",
                      "IBGE PNAD-C/PME (unemployment)", "planalto.gov.br (minimum wage)"),
    )

    ax = ig.next_panel("Human Development Index (UNDP)")
    if hdi:
        yrs, vals = ctx.series(hdi, "value")
        ctx.line(ax, yrs, vals, ctx.p.GREEN_D, marker="o", ms=4.6)
        ctx.endlabel(ax, yrs, vals, ctx.p.GREEN_D, lambda v: f"{v:.3f}", dy=10)
        ax.axhline(0.8, color=ctx.p.FAINT, lw=0.9, ls=":")
        ax.text(2006.4, 0.795, "0.800 = very high development", fontsize=8.2,
                color=ctx.p.MUTED, style="italic", va="bottom")
        ig.add_event(ax, 2020.1, "pandemic dip", dy=0.95)
    else:
        ctx.pending(ax)
    ax.set_ylim(0.66, 0.85)

    ax = ig.next_panel("Income inequality — Gini (lower = better)")
    if gini:
        yrs, ib = ctx.series(gini, "ibge")
        yrs2, wb = ctx.series(gini, "wb")
        ctx.line(ax, yrs, ib, ctx.p.PURPLE, label="IBGE (official, 2012+)")
        ctx.line(ax, yrs2, wb, ctx.p.FAINT, label="World Bank harmonized", lw=1.8,
             dashed_partial=False)
        ax.set_ylim(0.480, 0.562)
        ax.invert_yaxis()  # lower gini = better; put 'better' up
        ax.legend(loc="lower left", fontsize=8.2)
        ax.text(2006.3, 0.487, "2010: no survey (census year)", fontsize=7.6,
                color=ctx.p.FAINT, style="italic", va="center")
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Unemployment rate (%, annual average)")
    if unemp:
        yrs, vals = ctx.series(unemp, "value")
        pyr, pv = ctx.series(unemp, "pme")
        ctx.line(ax, pyr, pv, ctx.p.FAINT, lw=1.8, dashed_partial=False,
             label="PME — 6 metro regions (old survey)")
        ctx.line(ax, yrs, vals, ctx.p.RED, label="PNAD Contínua (national)")
        ctx.endlabel(ax, yrs, vals, ctx.p.RED, lambda v: f"{v:.1f}%", dy=10)
        ax.legend(loc="lower left", fontsize=8.2)
        ax.annotate("peak 14.0%", xy=(2021, 14.0), xytext=(2018.2, 14.9),
                    fontsize=8.6, color=ctx.p.RED, fontweight="bold", ha="right",
                    arrowprops=dict(arrowstyle="-", color=ctx.p.RED, lw=0.8))
    else:
        ctx.pending(ax)
    ax.set_ylim(4, 16.5)

    ax = ig.next_panel("Minimum wage (R$/month)")
    if mw:
        yrs, vals = ctx.series(mw, "value")
        ctx.line(ax, yrs, vals, ctx.p.YELLOW, lw=2.8, label="Nominal")
        if ipca:  # deflate to 2026 R$
            infl = {y: v for y, v in zip(ipca["year"], ipca["value"]) if v == v}
            base = 1.0
            factors = {}
            for y in sorted(infl):
                factors[y] = base
                base *= 1 + infl[y] / 100
            real = [v * factors[2026] / factors[y] for y, v in zip(yrs, vals)
                    if y in factors]
            ryr = [y for y in yrs if y in factors]
            ctx.line(ax, ryr, real, "#8A6D3B", lw=2.4, label="In 2026 reais (IPCA-deflated)")
        ax.legend(loc="upper left", fontsize=8.6)
        ctx.endlabel(ax, yrs, vals, "#B07E00", lambda v: f"R$ {v:,.0f}", dy=10)
    else:
        ctx.pending(ax)
    ax.set_ylim(250, 1900)

    ax = ig.next_panel("Poverty — below US$ 8.30/day (%, PPP 2021)")
    if pov and "poverty_pct" in pov:
        yrs, vals = ctx.series(pov, "poverty_pct")
        ctx.line(ax, yrs, vals, ctx.p.TEAL)
        ctx.endlabel(ax, yrs, vals, ctx.p.TEAL, lambda v: f"{v:.1f}%", dy=10)
        ig.add_event(ax, 2020.1, "emergency aid", dy=0.95)
        ig.add_event(ax, 2021.1, "aid withdrawn", dy=0.62)
        ax.text(2009.7, 47.5, "2010: no survey", fontsize=7.6, color=ctx.p.FAINT,
                style="italic")
    else:
        ctx.pending(ax)
    ax.set_ylim(15, 50)

    ax = ig.next_panel("Extreme poverty — below US$ 3.00/day (%, PPP 2021)")
    if pov and "extreme_pct" in pov:
        yrs, vals = ctx.series(pov, "extreme_pct")
        ctx.line(ax, yrs, vals, ctx.p.RED)
        ctx.endlabel(ax, yrs, vals, ctx.p.RED, lambda v: f"{v:.1f}%", dy=10)
        ax.text(2020.0, 4.1, "2.8% — emergency aid", fontsize=8.2, color=ctx.p.RED,
                fontweight="bold")
        ax.text(2009.7, 11.8, "2010: no survey", fontsize=7.6, color=ctx.p.FAINT,
                style="italic")
    else:
        ctx.pending(ax)
    ax.set_ylim(2, 13)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("08_people.png"))

def fig_world(ctx) -> None:
    wef = ctx.table("international/wef.csv")
    cpi = ctx.table("international/cpi.csv")
    res = ctx.table("macro/reserves.csv")
    ig = ctx.fig(
        "Brazil in the World — Competitiveness, Corruption & Trade Openness",
        "How the outside world scores Brazil — and how relatively closed its "
        "economy is.",
        source=ctx.source("World Economic Forum — GCI", "Transparency International — CPI",
                      "MDIC/SECEX + IBGE/BCB (openness)",
                      "Banco Central — reserves (SGS 3546)"),
    )

    ax = ig.next_panel("WEF Global Competitiveness — Brazil rank (lower is better)")
    if wef and "rank" in wef:
        yrs, vals = ctx.series(wef, "rank")
        ctx.line(ax, yrs, vals, ctx.p.BLUE, marker="D", ms=4)
        ax.invert_yaxis()
        ctx.endlabel(ax, yrs, vals, ctx.p.BLUE, lambda v: f"#{v:.0f}", dy=10)
        ax.text(2006.3, 58, "methodology changes 2008/2018;\nGCI discontinued after 2019",
                fontsize=7.8, color=ctx.p.FAINT, style="italic", va="top")
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Corruption Perceptions Index — score (higher = cleaner)")
    if cpi and "score" in cpi:
        yrs, vals = ctx.series(cpi, "score")
        # 2006-2011 came on 0-10 scale: rescale to /100
        vals = [v * 10 if v <= 10 else v for v in vals]
        ctx.line(ax, yrs, vals, ctx.p.TEAL)
        ctx.endlabel(ax, yrs, vals, ctx.p.TEAL, lambda v: f"{v:.0f}", dy=10)
        ax.text(2006.3, 78, "2012: scale rebased 0–100", fontsize=7.8,
                color=ctx.p.FAINT, style="italic")
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(25, 80)

    ax = ig.next_panel("Trade openness — exports + imports (% of GDP)")
    gdp = ctx.table("macro/gdp.csv")
    dollar = ctx.table("macro/dollar.csv")
    tr = ctx.table("trade/trade.csv")
    if gdp and dollar and tr and "nominal_rbi" in gdp:
        usd_avg = {y: v for y, v in zip(dollar["year"], dollar["avg"]) if v == v}
        gdp_usbi = {y: (g / usd_avg[y]) if y in usd_avg and g == g else None
                    for y, g in zip(gdp["year"], gdp["nominal_rbi"])}
        ox, oy = [], []
        for y, e, i in zip(tr["year"], tr["exports"], tr["imports"]):
            g = gdp_usbi.get(int(y))
            if e == e and i == i and g:
                ox.append(int(y))
                oy.append((e + i) / g * 100)
        ctx.line(ax, ox, oy, ctx.p.TEAL)
        ctx.endlabel(ax, ox, oy, ctx.p.TEAL, lambda v: f"{v:.0f}%", dy=10)
        ax.text(2006.3, 13.2, "Brazil trades far less than the world average",
                fontsize=8.2, color=ctx.p.MUTED, style="italic")
        # 2026 nominal GDP is not published yet, so openness stops at 2025.
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(10, 34)

    ax = ig.next_panel("International reserves (US$ billion, year-end)")
    if res and "eop_usbi" in res:
        yrs, vals = ctx.series(res, "eop_usbi")
        ctx.line(ax, yrs, vals, ctx.p.GREEN_D)
        ax.fill_between(yrs, 0, vals, color=ctx.p.GREEN_D, alpha=0.08)
        ctx.endlabel(ax, yrs, vals, ctx.p.GREEN_D, lambda v: f"US$ {v:,.0f}bn", dy=10)
        ig.add_event(ax, 2008.75, "crisis: BCB sold reserves", dy=0.95)
        ig.mark_partial(ax, 2026)
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 460)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("07_world.png"))

def fig_demographics(ctx) -> None:
    """The only figure that leaves the 2006-2026 window: the point of the
    demographic story is what happens after it."""
    pop = ctx.table("social/population.csv")
    ig = ctx.fig(
        "Brazil's Demographic Transition — the Peak Is in Sight",
        "Fertility has fallen by a third since 2000. On IBGE's 2024 projection "
        "the population peaks in 2041 and shrinks from 2042. Dashed = projected.",
        source=ctx.source("IBGE — Projeções da População, revisão 2024"),
    )
    SPLIT = 2024  # last year with observed births/deaths; the rest is model
    X0, X1 = 2000, 2070

    ax = ig.next_panel("Population (millions)")
    if pop and "pop_mn" in pop:
        yrs, vals = ctx.series(pop, "pop_mn")
        ctx.line(ax, yrs, vals, ctx.p.BLUE, split_year=SPLIT, marker="")
        peak = max(zip(yrs, vals), key=lambda t: t[1])
        ax.plot([peak[0]], [peak[1]], marker="o", ms=7, mfc="none",
                mec=ctx.p.RED, mew=2, zorder=5)
        ax.annotate(f"peak {peak[1]:.1f}M in {peak[0]:.0f}",
                    peak, textcoords="offset points", xytext=(-8, 14),
                    ha="right", fontsize=9, fontweight="bold", color=ctx.p.RED)
        ctx.endlabel(ax, yrs, vals, ctx.p.BLUE, lambda v: f"{v:.0f}M", dy=-16)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Total fertility rate — children per woman")
    if pop and "tfr" in pop:
        yrs, vals = ctx.series(pop, "tfr")
        ax.axhline(2.1, color=ctx.p.MUTED, lw=1.1, ls=(0, (5, 4)))
        ax.text(X0 + 1, 2.16, "replacement level 2.1", fontsize=8.2,
                color=ctx.p.MUTED, style="italic")
        ctx.line(ax, yrs, vals, ctx.p.RED, split_year=SPLIT, marker="")
        lo = min(zip(yrs, vals), key=lambda t: t[1])
        for y, lab in ((X0, "left"), (2023, "right")):
            if y in yrs:
                v = vals[yrs.index(y)]
                ax.annotate(f"{v:.2f}", (y, v), textcoords="offset points",
                            xytext=(6 if lab == "left" else 0, 9),
                            fontsize=9, fontweight="bold", color=ctx.p.RED,
                            ha=lab if lab == "left" else "center")
        ax.annotate(f"floor {lo[1]:.2f} ({lo[0]:.0f})", lo,
                    textcoords="offset points", xytext=(0, -18), ha="center",
                    fontsize=8.6, color=ctx.p.MUTED)
        ax.set_ylim(1.2, 2.5)
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Births and deaths per year (millions)")
    if pop and "births" in pop and "deaths" in pop:
        by, bv = ctx.series(pop, "births")
        dy_, dv = ctx.series(pop, "deaths")
        bv = [v / 1e6 for v in bv]
        dv = [v / 1e6 for v in dv]
        ctx.line(ax, by, bv, ctx.p.GREEN_D, label="Births", split_year=SPLIT, marker="")
        ctx.line(ax, dy_, dv, ctx.p.INK, label="Deaths", split_year=SPLIT, marker="")
        ax.legend(loc="lower right")
        cross = next((y for y in dy_ if y in by
                      and dv[dy_.index(y)] > bv[by.index(y)]), None)
        if cross:
            ax.axvline(cross, color=ctx.p.FAINT, lw=0.9, ls=(0, (4, 3)), zorder=1)
            ax.text(cross + 1, 0.06, f"deaths overtake\nbirths in {cross:.0f}",
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
                        textcoords="offset points", xytext=(4, -30),
                        fontsize=8.6, color=ctx.p.MUTED, ha="left")
        # below the line would sit on the 2070 tick label
        ctx.endlabel(ax, yrs, vals, ctx.p.TEAL, lambda v: f"{v:.2f}%", dy=12)
    else:
        ctx.pending(ax)

    for ax in ig.axes_flat:
        ig.style_axis(ax, xticks_years=False)
        ax.set_xticks(list(range(X0, X1 + 1, 10)))
        ax.set_xlim(X0 - 1.5, X1 + 1.5)
    ig.save(ctx.out("09_demographics.png"))

def fig_security(ctx) -> None:
    hom = ctx.table("social/homicides.csv")
    fb = ctx.table("social/violence_fbsp.csv")
    ig = ctx.fig(
        "Violence — Homicides, Police Lethality & Femicides",
        "Two systems, deliberately not spliced: IPEA/SIM counts death "
        "certificates by residence (to 2024), FBSP police records by "
        "occurrence (to 2025).",
        source=ctx.source("IPEA — Atlas da Violência (SIM/DATASUS)",
                      "FBSP — Anuário Brasileiro de Segurança Pública 2026"),
    )

    ax = ig.next_panel("Homicide rate per 100k — registered vs estimated")
    if hom and "rate" in hom:
        yrs, vals = ctx.series(hom, "rate")
        ctx.line(ax, yrs, vals, ctx.p.RED, label="Registered (SIM)")
        ctx.endlabel(ax, yrs, vals, ctx.p.RED, lambda v: f"{v:.1f}", dy=-16)
        if "est_rate" in hom:
            ey, ev = ctx.series(hom, "est_rate")
            ax.plot(ey, ev, color=ctx.p.INK, lw=2.0, ls=(0, (5, 3)), marker="o",
                    ms=3.4, zorder=3, label="Estimated (incl. hidden)")
        ax.legend(loc="lower left")
        ig.add_event(ax, 2019, "2019: deaths reclassified\nas undetermined intent",
                     dy=0.99)
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(15, 36)

    ax = ig.next_panel("Homicides per year — the two systems")
    if hom and fb:
        hy, hv = ctx.series(hom, "count")
        ctx.line(ax, hy, [v / 1000 for v in hv], ctx.p.RED, label="IPEA/SIM (residence)")
        fy, fv = ctx.series(fb, "mvi")
        ctx.line(ax, fy, [v / 1000 for v in fv], ctx.p.BLUE,
             label="FBSP MVI (occurrence)")
        ax.legend(loc="lower left")
        ax.set_ylabel("thousands")
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(30, 72)

    ax = ig.next_panel("Deaths from police intervention (FBSP)")
    if fb and "police_killings" in fb:
        yrs, vals = ctx.series(fb, "police_killings")
        ctx.bars(ax, yrs, vals, lambda v: ctx.p.PURPLE)
        ctx.endlabel(ax, yrs, vals, ctx.p.PURPLE, lambda v: f"{v:,.0f}", dy=8)
        ax.text(2006.3, 5900, "SIM records only about a third of these:\n"
                "the ICD code follows the death certificate,\nnot the police "
                "classification", fontsize=8, color=ctx.p.MUTED, style="italic",
                va="top")
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 7600)

    ax = ig.next_panel("Homicides of women, and the femicide share")
    if fb and "femicides" in fb:
        wy, wv = ctx.series(fb, "women_homicides")
        fy2, fv2 = ctx.series(fb, "femicides")
        # the femicide series starts later than the homicide one, so every
        # year-by-year comparison below runs over the overlap only
        total = dict(zip(wy, wv))
        band = [(y, total[y], f) for y, f in zip(fy2, fv2) if y in total]

        # the red series is a subset of the black one, which two bare lines
        # do not say; the filled band between them is the remainder, so
        # containment is visible rather than inferred from the legend
        if band:
            yrs, tops, bottoms = zip(*band)
            ax.fill_between(yrs, tops, bottoms, color=ctx.p.INK, alpha=0.07,
                            lw=0, zorder=1)
        ctx.line(ax, wy, wv, ctx.p.INK, label="All homicides of women")
        ctx.line(ax, fy2, fv2, ctx.p.RED, label="of these, classified as femicide")
        ctx.endlabel(ax, wy, wv, ctx.p.INK, lambda v: f"{v:,.0f}", dy=8)
        ctx.endlabel(ax, fy2, fv2, ctx.p.RED, lambda v: f"{v:,.0f}", dy=8)
        ax.legend(loc="center left")

        # the share is what the panel is titled after, so state it at both
        # ends instead of leaving the reader to divide one line by the other
        for y, t, f in {band[0], band[-1]} if band else ():
            ax.annotate(f"{f / t * 100:.0f}%", (y, f),
                        textcoords="offset points", xytext=(0, -14),
                        ha="center", fontsize=8.5, fontweight="bold",
                        color=ctx.p.RED)
        ax.text(2006.3, 800, "the rising share is substantially a\n"
                "classification effect — the qualifier\ndates from 2015 and "
                "took years to apply", fontsize=8, color=ctx.p.MUTED, style="italic",
                va="top")
        ig.mark_partial(ax, 2026, "n/a")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, 5200)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("10_security.png"))

def fig_credit(ctx) -> None:
    cr = ctx.table("macro/credit.csv")
    hh = ctx.table("macro/household_debt.csv")
    ig = ctx.fig(
        "Credit & Household Debt — Supply, Price and Burden",
        "Credit grew faster than the economy, and households now owe half "
        "a year's income. Year-end values from Banco Central.",
        source=ctx.source("Banco Central — SGS (credit statistics, SCR-based "
                      "from 2011)"),
    )

    ax = ig.next_panel("Credit outstanding, % of GDP")
    if cr:
        yy, vv = ctx.series(cr, "credit_gdp")
        ctx.line(ax, yy, vv, ctx.p.GREEN)
        ctx.endlabel(ax, yy, vv, ctx.p.GREEN, lambda v: f"{v:,.1f}%", dy=-18)
        ig.mark_partial(ax, 2026, "Aug")
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Average interest rate on credit, % a year")
    if cr:
        for col, colour, label in (("rate_pf", ctx.p.RED, "Households"),
                                   ("rate_total", ctx.p.INK, "All credit"),
                                   ("rate_pj", ctx.p.BLUE, "Firms")):
            yy, vv = ctx.series(cr, col)
            ctx.line(ax, yy, vv, colour, label=label)
            ctx.endlabel(ax, yy, vv, colour, lambda v: f"{v:,.1f}", dy=6)
        ax.legend(loc="center left")
        ax.text(0.03, 0.06, "the series begins in 2011, when BCB rebuilt "
                "these statistics on SCR microdata",
                transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED,
                style="italic")
        ig.mark_partial(ax, 2026, "Aug")
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Household debt, % of annual income")
    if hh:
        ty, tv = ctx.series(hh, "debt_income")
        ey, ev = ctx.series(hh, "debt_income_ex_housing")
        # the gap between the two is housing credit, which is the part that
        # buys an asset — worth separating before calling the total alarming
        both = dict(zip(ey, ev))
        band = [(y, v, both[y]) for y, v in zip(ty, tv) if y in both]
        if band:
            yrs, tops, bottoms = zip(*band)
            ax.fill_between(yrs, tops, bottoms, color=ctx.p.PURPLE, alpha=0.10,
                            lw=0, zorder=1)
        ctx.line(ax, ty, tv, ctx.p.PURPLE, label="All debt")
        ctx.line(ax, ey, ev, ctx.p.TEAL, label="Excluding housing credit")
        ctx.endlabel(ax, ty, tv, ctx.p.PURPLE, lambda v: f"{v:,.1f}%", dy=8)
        ctx.endlabel(ax, ey, ev, ctx.p.TEAL, lambda v: f"{v:,.1f}%", dy=-18)
        ax.legend(loc="upper left")
        ax.text(0.03, 0.06, "the shaded gap is housing credit — debt that "
                "buys an asset", transform=ax.transAxes, fontsize=8,
                color=ctx.p.MUTED, style="italic")
        ig.mark_partial(ax, 2026, "Aug")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, None)

    ax = ig.next_panel("Debt service and arrears, %")
    if hh and cr:
        sy, sv = ctx.series(hh, "debt_service")
        ny, nv = ctx.series(cr, "npl_pf")
        ctx.line(ax, sy, sv, ctx.p.PURPLE, label="Income going to debt service")
        ctx.line(ax, ny, nv, ctx.p.RED, label="Household loans 90+ days overdue")
        ctx.endlabel(ax, sy, sv, ctx.p.PURPLE, lambda v: f"{v:,.1f}%", dy=8)
        ctx.endlabel(ax, ny, nv, ctx.p.RED, lambda v: f"{v:,.1f}%", dy=8)
        ax.legend(loc="center left")
        ax.text(0.03, 0.06, "both are at or near their series highs",
                transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED,
                style="italic")
        ig.mark_partial(ax, 2026, "Aug")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, None)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("05_credit.png"))

def fig_epidemics(ctx) -> None:
    ep = ctx.table("social/epidemic_deaths.csv")
    ig = ctx.fig(
        "Epidemics — COVID-19, Influenza and Dengue Deaths",
        "One instrument throughout: SIM death certificates, by the "
        "underlying cause a doctor certified, counted by residence.",
        source=ctx.source("Ministério da Saúde — SIM/DATASUS (TabNet, CID-10)"),
    )

    # this panel is the one place the plate leaves the house 2006-2026
    # window: seven bars spread over twenty years are too thin to label,
    # and every value here is pandemic-era anyway
    ax_covid = ax = ig.next_panel("COVID-19 deaths per year")
    covid_years = (2019, 2025)
    if ep:
        cy, cv = ctx.series(ep, "covid")
        recent = [(y, v) for y, v in zip(cy, cv)
                  if covid_years[0] <= y <= covid_years[1]]
        ctx.bars(ax, [y for y, _ in recent], [v for _, v in recent],
             lambda v: ctx.p.RED, hatch_partial=False)
        for y, v in recent:
            ax.annotate(f"{v:,.0f}", (y, v), textcoords="offset points",
                        xytext=(0, 6), ha="center", fontsize=9,
                        fontweight="bold", color=ctx.p.INK)
        ax.set_ylim(0, max(v for _, v in recent) * 1.14)
        # the pre-pandemic years are a real part of this series and would be
        # invisible against 425,218, so the baseline is stated instead
        base = [v for y, v in zip(cy, cv) if y < 2020]
        if base:
            ax.text(0.46, 0.60, "B34 averaged "
                    f"{sum(base) / len(base):,.0f} deaths a year\nbefore 2020 "
                    f"— 2019 is the bar\nat the left, not an empty slot",
                    transform=ax.transAxes, fontsize=8.2, color=ctx.p.MUTED,
                    style="italic", va="top")
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Influenza deaths (J09–J11)")
    if ep:
        fy, fv = ctx.series(ep, "influenza")
        ctx.line(ax, fy, fv, ctx.p.BLUE)
        ax.annotate(f"{fv[-1]:,.0f}", (fy[-1], fv[-1]),
                    textcoords="offset points", xytext=(-10, -4), ha="right",
                    fontsize=9.5, fontweight="bold", color=ctx.p.BLUE, zorder=6)
        ig.add_event(ax, 2009, "H1N1")
        ax.set_ylim(0, max(fv) * 1.26)
        ax.text(0.30, 0.97, "2025 is the deadliest influenza year here —\n"
                "above both H1N1 and 2022",
                transform=ax.transAxes, fontsize=8.2, color=ctx.p.MUTED,
                style="italic", va="top")
    else:
        ctx.pending(ax)

    ax = ig.next_panel("Dengue deaths (A90/A91 → A97)")
    if ep:
        dy_, dv = ctx.series(ep, "dengue")
        ctx.line(ax, dy_, dv, ctx.p.PURPLE)
        ctx.endlabel(ax, dy_, dv, ctx.p.PURPLE, lambda v: f"{v:,.0f}", dy=-16)
        peak = max(zip(dy_, dv), key=lambda p: p[1])
        ax.annotate(f"{peak[1]:,.0f}", peak, textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9.5,
                    fontweight="bold", color=ctx.p.PURPLE)
        ax.text(0.03, 0.88, "dengue changed ICD code mid-series: A90/A91\n"
                "until 2024, A97 from 2025. The column sums both,\n"
                "or 2025 would read as a year with no deaths",
                transform=ax.transAxes, fontsize=8, color=ctx.p.MUTED,
                style="italic", va="top")
    else:
        ctx.pending(ax)
    ax.set_ylim(0, None)

    ax = ig.next_panel("All three together — note the log scale")
    if ep:
        # COVID starts at 2020 here. Before the pandemic B34 is a bucket of
        # unspecified viral deaths, and drawing those under a "COVID-19"
        # legend would put a decade of mislabelled points on the plate.
        for col, colour, label, first in (
                ("covid", ctx.p.RED, "COVID-19", 2020),
                ("influenza", ctx.p.BLUE, "Influenza", None),
                ("dengue", ctx.p.PURPLE, "Dengue", None)):
            yy, vv = ctx.series(ep, col)
            pts = [(y, v) for y, v in zip(yy, vv)
                   if v > 0 and (first is None or y >= first)]
            ax.semilogy([p[0] for p in pts], [p[1] for p in pts],
                        color=colour, lw=2.4, marker="o", ms=3.6,
                        label=label, zorder=3)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.yaxis.set_minor_formatter(mticker.NullFormatter())
        ax.legend(loc="upper left")
        ax.text(0.03, 0.03, "a linear axis would flatten influenza and "
                "dengue into the baseline", transform=ax.transAxes,
                fontsize=8, color=ctx.p.MUTED, style="italic")
    else:
        ctx.pending(ax)

    for ax in ig.axes_flat:
        ig.style_axis(ax)
    # style_axis pins every panel to the shared window, so the COVID panel's
    # own range has to be restored after it rather than before
    if ep:
        lo, hi = covid_years
        ax_covid.set_xticks(range(lo, hi + 1))
        ax_covid.set_xlim(lo - 0.6, hi + 0.6)
    ig.save(ctx.out("11_epidemics.png"))


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

    ("fig_credit", fig_credit),

    ("fig_epidemics", fig_epidemics),

)
