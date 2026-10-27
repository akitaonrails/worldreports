"""The brasil plates, drawn on the shared plate spine.

Every plate declares its topic and claims its four panels by slot key in
the order core/spine.py lists them, so a Brazilian panel sits in the same
place, in the same unit and on the same scale as every other country's
(PLATE_SPINE.md). The canonical slots carry the harmonised series where
the spine asks for one — IMF general government, World Bank GDP per
person and trade, BIS household credit — and the Brazilian series the
country actually argues about rides beside them as a labelled second
line: the Tesouro's central-government primary result, the BCB's gross
DBGG debt, and the NFSP interest bill. The lens slot is Brazil's own
story.

Counts are rates (PLATE_SPINE.md rule 5). Every per-100k and per-1,000
figure here divides a count by the population of the same year and the
same scope: SIM and FBSP counts of Brazilian residents over IBGE's
1 July resident population (social/population.csv, projection rev.
2024), and FBSP's women victims over the World Bank's mid-year female
population (social/demography.csv). DATA_NOTES.md names each one.

Every number written in a note is read from the CSVs when the plate is
drawn, so a refetch moves the note with the line.
"""
from __future__ import annotations

import numpy as np
from matplotlib.patches import Patch

from countries.brasil.events import MARKS

# Defined here rather than in the palette because it is only ever the
# Selic line and the pensions slice — two specific series, not a role.
NAVY_C = "#12355B"


# ------------------------------------------------------------ helpers
def col(t, name) -> dict[int, float]:
    """{year: value} for one column, blanks dropped."""
    if not t or name not in t:
        return {}
    return {int(y): float(v) for y, v in zip(t["year"], t[name])
            if v is not None and v == v}


def xy(d: dict[int, float], lo: int | None = None, hi: int | None = None):
    ys = sorted(y for y in d if (lo is None or y >= lo)
                and (hi is None or y <= hi))
    return ys, [d[y] for y in ys]


def note(ax, text, x=0.02, y=0.96, ha="left", va="top", color=None,
         size=8.0, weight="normal"):
    """A short italic caption in axes coordinates."""
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=size, color=color or "#5A6072", style="italic",
            fontweight=weight, zorder=6, parse_math=False)


def legend(ax, loc="upper left", extra=(), **kw):
    kw.setdefault("fontsize", 8.2)
    kw.setdefault("frameon", False)
    handles, labels = ax.get_legend_handles_labels()
    for h, lab in extra:
        handles.append(h)
        labels.append(lab)
    ax.legend(handles, labels, loc=loc, **kw)


def series_per(count: dict, pop_mn: dict, base: float, ctx) -> dict:
    """count ÷ (population in millions × 1e6) × base, matched by year."""
    pop = {y: v * 1e6 for y, v in pop_mn.items()}
    ys, vs = (ctx.per_100k if base == 1e5 else ctx.per_1000)(count, pop)
    return dict(zip(ys, vs))


def recessions(ig, ax, first=False, y=0.06, color="#5A6072"):
    """The country.yaml downturn bands; named on slot 1 only (rule 8).

    The names are written at a height chosen per plate, inside the panel,
    where that plate's data leave room — the shared helper puts them
    either above the axes, on the panel title, or at the very bottom, on
    the notes.
    """
    ig.add_recessions(ax, label=False)
    if first:
        for start, end, name in ig.country.recessions:
            ax.text((start + end) / 2, y, name, transform=ax.get_xaxis_transform(),
                    ha="center", va="center", fontsize=7.8,
                    color=color, style="italic", zorder=6)


def finish(ig, skip=()):
    for i, ax in enumerate(ig.axes_flat):
        ig.style_axis(ax, xticks_years=i not in skip)


def ibge_pop(ctx) -> dict[int, float]:
    """IBGE resident population, 1 July, millions (projection rev. 2024)."""
    return col(ctx.table("social/population.csv"), "pop_mn")


# ------------------------------------------------------------ economy
def fig_economy(ctx, ig) -> None:
    gdp = ctx.table("macro/gdp.csv")
    world = ctx.table("international/world.csv")
    ipca = col(ctx.table("macro/ipca.csv"), "value")
    tgt_t = ctx.table("macro/inflation_target.csv")
    un = ctx.table("macro/unemployment.csv")

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    g = col(gdp, "real_growth")
    ctx.bars(ax, *xy(g), lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED)
    best = max(g, key=g.get)
    ax.annotate(f"{g[best]:+.1f}", (best, g[best]), textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=8.6, fontweight="bold",
                color=ctx.p.GREEN_D)
    worst = min(g, key=g.get)
    note(ax, f"{best}: the window's fastest year · "
         f"{worst}: {g[worst]:+.1f}%", y=0.97)
    recessions(ig, ax, first=True)

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    pc = col(world, "gdp_per_person_usd")
    yrs, vals = xy(pc, 2006)
    ctx.line(ax, yrs, vals, ctx.p.BLUE, label="World Bank (NY.GDP.PCAP.CD)")
    peak = max(yrs, key=pc.get)
    trough = min((y for y in yrs if y > peak), key=pc.get)
    fx = col(ctx.table("macro/dollar.csv"), "avg")
    note(ax, f"{peak} peak US${pc[peak]:,.0f} · {trough}: US${pc[trough]:,.0f}, "
         f"with the real at R${fx[trough]:.2f} per US$", y=0.97)
    ctx.endlabel(ax, yrs, vals, ctx.p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    recessions(ig, ax)

    ax = ig.slot("economy.inflation", "Consumer prices — IPCA vs the target")
    tgt, tol = col(tgt_t, "target"), col(tgt_t, "tolerance")
    ty = sorted(tgt)
    ax.fill_between(ty, [tgt[y] - tol[y] for y in ty],
                    [tgt[y] + tol[y] for y in ty], color=ctx.p.BLUE,
                    alpha=0.10, lw=0, step="mid", label="Tolerance band (CMN)")
    ax.step(ty, [tgt[y] for y in ty], where="mid", color=ctx.p.BLUE, lw=1.2,
            ls="--", label="Target (CMN)")
    ctx.line(ax, *xy(ipca), ctx.p.RED, label="IPCA, Dec/Dec (IBGE)")
    over = [y for y in ipca if y <= ctx.LAST_FULL_YEAR
            and ipca[y] > tgt[y] + tol[y]]
    hot = max(ipca, key=ipca.get)
    note(ax, f"above the ceiling in {len(over)} of "
         f"{sum(1 for y in ipca if y <= ctx.LAST_FULL_YEAR)} years · "
         f"peak {ipca[hot]:.1f}% in {hot}", y=0.97)
    legend(ax, loc="upper left", bbox_to_anchor=(0.0, 0.90))
    ig.mark_partial(ax, ctx.YEARS[-1], f"{ctx.YEARS[-1]}: Jan–Sep")
    recessions(ig, ax)

    ax = ig.slot("economy.unemployment", "Unemployment rate")
    pnad, pme = col(un, "value"), col(un, "pme")
    ilo = col(ctx.table("macro/economy.csv"), "unemployment_pct")
    ctx.line(ax, *xy(ilo, 2006), ctx.p.FAINT, lw=1.4, ms=2.6,
             label="ILO modelled estimate (World Bank)")
    ctx.line(ax, *xy(pme), ctx.p.YELLOW, lw=1.8, ms=3.2,
             label="PME — six metro areas, old survey")
    ctx.line(ax, *xy(pnad), ctx.p.RED, label="PNAD Contínua — national")
    top = max(pnad, key=pnad.get)
    last = max(pnad)
    note(ax, f"PNAD-C: {pnad[top]:.1f}% in {top} to {pnad[last]:.1f}% in "
         f"{last}, the series low · not spliced to PME", y=0.97)
    legend(ax, loc="upper left", bbox_to_anchor=(0.0, 0.90))
    recessions(ig, ax)
    finish(ig)


# ------------------------------------------------------------- fiscal
def fig_fiscal(ctx, ig) -> None:
    gg = ctx.table("fiscal/general_government.csv")
    tax = ctx.table("fiscal/tax_burden.csv")
    prim = col(ctx.table("fiscal/primary_result.csv"), "value")
    debt = ctx.table("fiscal/debt.csv")
    nfsp = ctx.table("fiscal/nfsp.csv")

    ax = ig.slot("fiscal.revenue_expenditure",
                 "Revenue and expenditure — general government")
    rev, exp_ = col(gg, "revenue_pct_gdp"), col(gg, "expenditure_pct_gdp")
    ctx.line(ax, *xy(exp_, 2006), ctx.p.RED, label="Expenditure (IMF)")
    ctx.line(ax, *xy(rev, 2006), ctx.p.GREEN_D, label="Revenue (IMF)")
    # the tax burden changed method in 2010 (STN, GFSM 2014: FGTS and
    # Sistema S out) and has no recalculation before it: two segments,
    # never one line across the seam
    tv = col(tax, "value")
    meth = dict(zip(tax["year"], tax["methodology"])) if tax else {}
    old = {y: v for y, v in tv.items() if meth.get(y) == "old"}
    new = {y: v for y, v in tv.items() if meth.get(y) != "old"}
    ctx.line(ax, *xy(new), ctx.p.TEAL, lw=1.6, ms=3,
             label="Tax burden — carga tributária (STN)")
    ctx.line(ax, *xy(old), ctx.p.TEAL, lw=1.6, ms=3, ls=":")
    gap = max(exp_) if exp_ else None
    note(ax, f"{gap}: spending {exp_[gap] - rev[gap]:.1f} points of GDP "
         f"above revenue · tax burden: method break at {min(new)}, "
         f"not drawn across", y=0.06, va="bottom")
    legend(ax, loc="upper left", bbox_to_anchor=(0.0, 0.99), ncol=2)
    recessions(ig, ax, first=True, y=0.30)

    ax = ig.slot("fiscal.balance", "Overall balance (bars) and primary balance")
    bal, pb = col(gg, "balance_pct_gdp"), col(gg, "primary_balance_pct_gdp")
    ctx.bars(ax, *xy(bal, 2006), lambda v: ctx.p.RED if v < 0 else ctx.p.GREEN,
             width=0.62)
    ctx.line(ax, *xy(pb, 2006), ctx.p.INK, lw=1.8, ms=3,
             label="Primary balance, general government (IMF)")
    ctx.line(ax, *xy(prim), ctx.p.YELLOW, lw=1.8, ms=3, ls="--",
             label="Primary result, central government (Tesouro)")
    low = min(bal, key=bal.get)
    note(ax, f"{low}: overall deficit {abs(bal[low]):.1f}% of GDP", x=0.98,
         y=0.06, ha="right", va="bottom")
    legend(ax, loc="lower left",
           extra=[(Patch(color=ctx.p.RED),
                   "Overall balance, general government (IMF)")])
    recessions(ig, ax)

    ax = ig.slot("fiscal.debt", "Gross debt — two Brazilian definitions")
    imf = col(gg, "gross_debt_pct_gdp")
    dbgg = col(debt, "gross")
    ctx.line(ax, *xy(imf, 2006), ctx.p.RED, label="Gross, general government (IMF)")
    ctx.line(ax, *xy(dbgg), ctx.p.PURPLE, lw=1.8, ms=3,
             label="Gross, DBGG (BCB concept)")
    y = max(imf)
    note(ax, f"{y}: IMF {imf[y]:.1f}% vs DBGG {dbgg[y]:.1f}% — the IMF counts "
         f"the Treasury bonds the BCB holds", y=0.06, va="bottom")
    legend(ax, loc="upper left", bbox_to_anchor=(0.0, 0.99))
    ig.mark_partial(ax, ctx.YEARS[-1], f"{ctx.YEARS[-1]}: Aug (BCB)")
    recessions(ig, ax)

    ax = ig.slot("fiscal.interest", "Interest paid")
    imf_int = {y: pb[y] - bal[y] for y in bal if y in pb and y >= 2006}
    juros = col(nfsp, "interest")
    ctx.line(ax, *xy(imf_int), ctx.p.RED,
             label="Net interest, general government (IMF: primary − overall)")
    ctx.line(ax, *xy(juros), NAVY_C, lw=1.8, ms=3, ls="--",
             label="Nominal interest, public sector — NFSP (BCB)")
    hi = max(juros, key=juros.get)
    note(ax, f"{hi}: {juros[hi]:.1f}% of GDP on the BCB measure · "
         f"{max(juros)}: {juros[max(juros)]:.1f}%", y=0.03, va="bottom")
    legend(ax, loc="lower left", bbox_to_anchor=(0.0, 0.08))
    recessions(ig, ax)
    finish(ig)


# ----------------------------------------------------------- spending
COFOG = ("social_protection", "health", "education", "general_public",
         "economic_affairs", "defence_order", "other")
COFOG_LABEL = {"social_protection": "Social protection", "health": "Health",
               "education": "Education",
               "general_public": "General public services (incl. interest)",
               "economic_affairs": "Economic affairs",
               "defence_order": "Defence and public order", "other": "Other"}


def spending_groups(ctx):
    """The seven COFOG groups, % of GDP, for the general government.

    The Tesouro compiles COFOG for the whole general government (central,
    state, municipal) from 2010; fiscal/cofog.csv has its ten divisions
    already summed into the spine's seven groups (SOURCES.yaml says how).
    """
    cof = ctx.table("fiscal/cofog.csv")
    groups = {g: col(cof, g) for g in COFOG}
    return groups, (f"Tesouro COFOG, general government, from "
                    f"{min(groups['health'])}")


def fig_spending(ctx, ig) -> None:
    inv = ctx.table("fiscal/investment.csv")
    pub = col(ctx.table("fiscal/public_investment.csv"), "gov_gfcf_pct_gdp")
    colors = {"social_protection": NAVY_C, "health": ctx.p.TEAL,
              "education": ctx.p.BLUE, "general_public": ctx.p.RED,
              "economic_affairs": ctx.p.YELLOW, "defence_order": ctx.p.PURPLE,
              "other": "#B9BDC7"}

    ax = ig.slot("spending.by_function", "Spending by function, stacked")
    groups, basis = spending_groups(ctx)
    drawn = [g for g in COFOG if groups[g]]
    yrs = sorted(groups["social_protection"])
    ax.stackplot(yrs, *[[groups[g].get(y, 0.0) for y in yrs] for g in drawn],
                 labels=[COFOG_LABEL[g] for g in drawn],
                 colors=[colors[g] for g in drawn], alpha=0.92, lw=0)
    tot = {y: sum(groups[g].get(y, 0.0) for g in drawn) for y in yrs}
    last = yrs[-1]
    note(ax, f"{basis} · {last}: {tot[last]:.1f}% of GDP (preliminary)",
         y=0.97, size=7.8)
    legend(ax, loc="upper left", ncol=2, fontsize=7.4,
           bbox_to_anchor=(0.0, 0.90))
    recessions(ig, ax, first=True, y=0.06, color="#FFFFFF")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else")
    sp = groups["social_protection"]
    rest = {y: tot[y] - sp[y] for y in yrs}
    ctx.line(ax, yrs, [sp[y] for y in yrs], NAVY_C,
             label="Social protection (pensions, BPC, Bolsa Família)")
    ctx.line(ax, yrs, [rest[y] for y in yrs], ctx.p.FAINT,
             label="Everything else")
    peak = max(sp, key=sp.get)
    note(ax, f"{peak}: {sp[peak]:.1f}% of GDP — emergency aid", x=0.98,
         y=0.06, ha="right", va="bottom")
    legend(ax, loc="upper left")
    recessions(ig, ax)

    ax = ig.slot("spending.investment",
                 "Investment rate — gross fixed capital formation")
    fb = col(inv, "fbcf_pib")
    ctx.line(ax, *xy(fb), ctx.p.BLUE, label="Whole economy (IBGE)")
    hi = max(fb, key=fb.get)
    lo = min(fb, key=fb.get)
    note(ax, f"{hi}: {fb[hi]:.1f}% · {lo}: {fb[lo]:.1f}% · "
         f"{max(fb)}: {fb[max(fb)]:.1f}%", y=0.06, va="bottom")
    legend(ax, loc="upper left")
    recessions(ig, ax)

    ax = ig.slot("spending.public_investment", "Public investment")
    rtn = col(inv, "federal_rtn_gnd45_pib")
    ctx.line(ax, *xy(pub, 2006), ctx.p.GREEN_D,
             label="General government GFCF (OECD)")
    ctx.line(ax, *xy(rtn), ctx.p.YELLOW, lw=1.8, ms=3, ls="--",
             label="Federal investment paid, GND 4+5 (Tesouro RTN)")
    note(ax, f"the OECD series stops in {max(pub)} · federal: "
         f"{rtn[max(rtn)]:.2f}% of GDP in {max(rtn)}", y=0.97)
    legend(ax, loc="upper right")
    recessions(ig, ax)
    finish(ig)


# -------------------------------------------------------------- trade
PRODUCTS = ["oil", "soy", "iron", "meat", "sugar", "coffee", "corn",
            "pulp", "steel", "autos", "aircraft"]
PRODUCT_LABEL = {"oil": "Oil & refined", "soy": "Soy complex",
                 "iron": "Iron ore", "meat": "Meats",
                 "sugar": "Sugar & ethanol", "coffee": "Coffee",
                 "corn": "Corn", "pulp": "Pulp", "steel": "Steel",
                 "autos": "Automobiles", "aircraft": "Aircraft"}


def fig_trade(ctx, ig) -> None:
    na = ctx.table("trade/national_accounts.csv")
    tr = ctx.table("trade/trade.csv")
    dest = ctx.table("trade/destinations.csv")
    prods = ctx.table("trade/exports_products.csv")
    x, m = col(na, "exports_pct_gdp"), col(na, "imports_pct_gdp")
    gx, gm, gb = col(tr, "exports"), col(tr, "imports"), col(tr, "balance")
    full = ctx.LAST_FULL_YEAR

    ax = ig.slot("trade.exports_imports",
                 "Exports and imports of goods and services")
    ctx.line(ax, *xy(x, 2006), ctx.p.GREEN_D, label="Exports (World Bank)")
    ctx.line(ax, *xy(m, 2006), ctx.p.BLUE, label="Imports (World Bank)")
    note(ax, f"goods alone, {full} (SECEX): exports US${gx[full]:,.0f}bn, "
         f"imports US${gm[full]:,.0f}bn", y=0.97)
    legend(ax, loc="upper left", bbox_to_anchor=(0.0, 0.90))
    recessions(ig, ax, first=True, y=0.5)

    ax = ig.slot("trade.balance", "Trade balance, goods and services")
    bal = {y: x[y] - m[y] for y in x if y in m and y >= 2006}
    ctx.bars(ax, *xy(bal), lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED)
    note(ax, f"the goods surplus alone was US${gb[full]:+,.0f}bn in {full} "
         f"(SECEX);\nthe services deficit takes most of it back", y=0.97)
    recessions(ig, ax)

    ax = ig.slot("trade.destinations", "Top export destinations")
    if dest:
        rows = list(zip(dest["year"], dest["destiny"], dest["share_pct"]))
        for name, colour in (("China", ctx.p.RED),
                             ("United States", ctx.p.BLUE),
                             ("European Union", ctx.p.TEAL),
                             ("Argentina", ctx.p.YELLOW)):
            d = {int(y): v for y, n, v in rows if n == name and v == v}
            ctx.line(ax, *xy(d), colour, label=name, marker="D", ms=4)
        cn = {int(y): v for y, n, v in rows if n == "China"}
        note(ax, f"SECEX snapshot years, joined · China {cn[2006]:.0f}% in "
             f"2006 to {cn[full]:.0f}% in {full}", y=0.97)
        legend(ax, loc="upper left", bbox_to_anchor=(0.0, 0.90))
        ig.mark_partial(ax, ctx.YEARS[-1], f"{ctx.YEARS[-1]}: Jan–Sep")
    else:
        ctx.pending(ax)
    recessions(ig, ax)

    # the lens: what Brazil sells, in snapshot years. A snapshot panel is
    # allowed only here (PLATE_SPINE.md rule 2), on categorical positions,
    # because five uneven years spread over a 21-year axis render as
    # hairlines.
    ax = ig.slot("trade.lens", "What Brazil exports — top groups (US$ bn)")
    years = sorted({int(y) for y in prods["year"]})
    pick = [y for y in (2006, 2010, 2015, 2020, 2025) if y in years]
    usbi = {(int(y), p): v for y, p, v
            in zip(prods["year"], prods["product"], prods["usbi"])}
    pal = {"soy": ctx.p.GREEN_D, "iron": "#8A6D3B", "oil": ctx.p.INK,
           "meat": ctx.p.RED, "sugar": ctx.p.YELLOW, "coffee": "#6F4E37",
           "corn": "#D4A017", "pulp": ctx.p.TEAL, "steel": "#7A828E",
           "autos": ctx.p.PURPLE, "aircraft": ctx.p.BLUE}
    xs = np.arange(len(pick))
    width = 0.82 / len(PRODUCTS)
    for i, p in enumerate(PRODUCTS):
        ax.bar(xs + i * width - 0.41 + width / 2,
               [usbi.get((y, p), 0) for y in pick], width=width,
               label=PRODUCT_LABEL[p], color=pal[p], edgecolor="white",
               linewidth=0.4, zorder=3)
    # opaque, so the 70 gridline does not run through the legend text
    legend(ax, loc="upper left", ncol=4, fontsize=7.2, frameon=True,
           facecolor="white", framealpha=1, edgecolor="none")
    resid = usbi.get((pick[-1], "others"), 0)
    note(ax, f"excludes the 'others' residual (US${resid:,.0f}bn in "
         f"{pick[-1]})", x=0.5, y=-0.13, ha="center", size=7.6)
    ax.set_ylabel("US$ bn, goods (SECEX)", fontsize=8.6, color=ctx.p.MUTED)
    finish(ig, skip=(3,))
    ax.set_xticks(xs)
    ax.set_xticklabels([str(y) for y in pick])
    ax.set_xlim(-0.5, len(pick) - 0.5)
    ax.set_ylim(0, max(usbi.get((y, p), 0) for y in pick for p in PRODUCTS)
                * 1.45)


# ------------------------------------------------------------ markets
def fig_markets(ctx, ig) -> None:
    selic = col(ctx.table("macro/selic.csv"), "value")
    ipca = col(ctx.table("macro/ipca.csv"), "value")
    usd = ctx.table("macro/dollar.csv")
    avg, eop = col(usd, "avg"), col(usd, "eop")
    ibov = col(ctx.table("markets/ibov.csv"), "close")
    sp = col(ctx.table("markets/sp500.csv"), "close")
    bond = ctx.table("markets/bond_10y.csv")
    full = ctx.LAST_FULL_YEAR

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation")
    ctx.line(ax, *xy(selic), NAVY_C, label="Selic target, year-end (BCB)")
    ctx.line(ax, *xy(ipca), ctx.p.RED, lw=1.8, ms=3,
             label="IPCA, Dec/Dec (IBGE)")
    note(ax, f"{full}: Selic {selic[full]:.2f}%,\nIPCA {ipca[full]:.2f}%",
         x=0.56, y=0.75)
    legend(ax, loc="upper center", bbox_to_anchor=(0.5, 0.90), ncol=2)
    ig.mark_partial(ax, ctx.YEARS[-1], f"{ctx.YEARS[-1]}: Oct")
    recessions(ig, ax, first=True, y=0.60)

    ax = ig.slot("markets.bond_10y", "10-year government bond yield")
    b = col(bond, "yield_10y")
    # a year with no NTN-F near ten years out is a hole, not a line
    # across it: each run of consecutive years is its own segment
    runs, run = [], []
    for y in sorted(b):
        if run and y != run[-1] + 1:
            runs.append(run)
            run = []
        run.append(y)
    runs.append(run)
    for i, r in enumerate(runs):
        ctx.line(ax, r, [b[y] for y in r], ctx.p.PURPLE,
                 label="" if i else "NTN-F nearest 10 years, Tesouro Direto")
    gaps = [y for y in range(min(ctx.YEARS), max(b)) if y not in b]
    note(ax, "the Tesouro's retail offer rate, not ANBIMA's curve · "
         + ", ".join(str(y) for y in gaps) + ": no bond near ten years",
         y=0.03, va="bottom")
    legend(ax, loc="lower left", bbox_to_anchor=(0.0, 0.08))
    ig.mark_partial(ax, ctx.YEARS[-1], f"{ctx.YEARS[-1]}: Jan–Aug")
    recessions(ig, ax)

    ax = ig.slot("markets.currency", "The real against the US$")
    ctx.line(ax, *ctx.fx_index({y: v for y, v in avg.items() if y >= 2006}),
             ctx.p.GREEN_D, label="BRL, annual average PTAX (BCB)")
    note(ax, f"R${avg[2006]:.2f} per US$ in 2006 to R${avg[full]:.2f} in "
         f"{full}", y=0.06, va="bottom")
    legend(ax, loc="upper right")
    recessions(ig, ax)

    ax = ig.slot("markets.equities", "Main equity index in US$")
    base = 2006
    ib_usd = {y: ibov[y] / eop[y] for y in ibov if y in eop and y >= base}
    ctx.line(ax, *ctx.index_2006(ib_usd), ctx.p.GREEN,
             label="Ibovespa in US$, year-end")
    ctx.line(ax, *ctx.index_2006({y: v for y, v in sp.items() if y >= base}),
             ctx.p.BLUE, lw=1.8, ms=3, ls="--", label="S&P 500")
    note(ax, f"in reais the Ibovespa is {ibov[full] / ibov[base]:.1f}× its "
         f"{base} level by {full};\nin dollars, "
         f"{ib_usd[full] / ib_usd[base]:.1f}× — the currency is half the story",
         y=0.06, va="bottom")
    legend(ax, loc="upper left")
    ig.mark_partial(ax, ctx.YEARS[-1], f"{ctx.YEARS[-1]}: Oct 20")
    recessions(ig, ax)
    finish(ig)


# ------------------------------------------------------------- credit
def fig_credit(ctx, ig) -> None:
    bis = col(ctx.table("macro/household_credit.csv"), "hh_credit_pct_gdp_q4")
    cr = ctx.table("macro/credit.csv")
    hh = ctx.table("macro/household_debt.csv")
    selic = col(ctx.table("macro/selic.csv"), "value")
    full = ctx.LAST_FULL_YEAR

    ax = ig.slot("credit.household_debt", "Household debt")
    ctx.line(ax, *xy(bis, 2006), ctx.p.PURPLE,
             label="Households, all lenders, Q4 (BIS)")
    allc = col(cr, "credit_gdp")
    note(ax, f"{bis[2006]:.0f}% of GDP in 2006 to {bis[full]:.0f}% in {full} · "
         f"all bank credit, firms included: {allc[full]:.0f}% (BCB)", y=0.97)
    legend(ax, loc="upper left", bbox_to_anchor=(0.0, 0.90))
    recessions(ig, ax, first=True, y=0.5)

    ax = ig.slot("credit.lending_rate", "Household lending rate vs policy rate")
    pf = col(cr, "rate_pf")
    ctx.line(ax, *xy(pf), ctx.p.RED,
             label="Household credit, average rate, Dec (BCB)")
    ctx.line(ax, *xy(selic), NAVY_C, lw=1.8, ms=3, label="Selic target, year-end")
    note(ax, f"BCB rebuilt these statistics on SCR microdata in {min(pf)}"
         f"\n{full}: {pf[full]:.1f}% a year", y=0.97)
    legend(ax, loc="center left", bbox_to_anchor=(0.0, 0.52))
    ig.mark_partial(ax, ctx.YEARS[-1], f"{ctx.YEARS[-1]}: Aug")
    recessions(ig, ax)

    ax = ig.slot("credit.npl", "Non-performing loans")
    npl_pf, npl = col(cr, "npl_pf"), col(cr, "npl_total")
    ctx.line(ax, *xy(npl_pf), ctx.p.RED, label="Households, 90+ days overdue (BCB)")
    ctx.line(ax, *xy(npl), ctx.p.FAINT, lw=1.6, ms=3,
             label="All borrowers, 90+ days overdue")
    note(ax, f"{full}: {npl_pf[full]:.1f}% of household loans · "
         f"{max(npl_pf)}: {npl_pf[max(npl_pf)]:.1f}% (Aug)", y=0.97)
    legend(ax, loc="upper left", bbox_to_anchor=(0.0, 0.90))
    ig.mark_partial(ax, ctx.YEARS[-1], f"{ctx.YEARS[-1]}: Aug")
    recessions(ig, ax)

    # the lens: the BCB's own burden measures, both over household income
    ax = ig.slot("credit.lens", "Household debt and debt service, % of income")
    di, dx = col(hh, "debt_income"), col(hh, "debt_income_ex_housing")
    ds = col(hh, "debt_service")
    ys = [y for y in sorted(di) if y in dx and y >= 2006]
    ax.fill_between(ys, [di[y] for y in ys], [dx[y] for y in ys],
                    color=ctx.p.PURPLE, alpha=0.10, lw=0, zorder=1)
    ctx.line(ax, *xy(di, 2006), ctx.p.PURPLE, label="Debt, % of 12-month income")
    ctx.line(ax, *xy(dx, 2006), ctx.p.TEAL, lw=1.8, ms=3,
             label="Debt excluding housing")
    ctx.line(ax, *xy(ds, 2006), ctx.p.RED, lw=1.8, ms=3,
             label="Income going to debt service")
    note(ax, "the shaded gap is housing credit — debt that buys an asset",
         y=0.06, va="bottom")
    legend(ax, loc="upper left")
    ax.set_ylabel("% of household income", fontsize=8.6, color=ctx.p.MUTED)
    ax.set_ylim(0, max(di.values()) * 1.25)
    ig.mark_partial(ax, ctx.YEARS[-1], f"{ctx.YEARS[-1]}: Aug")
    recessions(ig, ax)
    finish(ig)


# ------------------------------------------------------------- people
def real_reais(nominal: dict, ipca: dict, to: int) -> dict:
    """Nominal R$ restated in `to`'s prices, compounding Dec/Dec IPCA."""
    out = {}
    for y, v in nominal.items():
        if y > to:
            continue
        factor = 1.0
        for k in range(y + 1, to + 1):
            factor *= 1 + ipca[k] / 100
        out[y] = v * factor
    return out


def fig_people(ctx, ig) -> None:
    gini = ctx.table("social/gini.csv")
    pov = ctx.table("social/poverty.csv")
    mw = col(ctx.table("macro/minimum_wage.csv"), "value")
    fx = col(ctx.table("macro/dollar.csv"), "avg")
    ipca = col(ctx.table("macro/ipca.csv"), "value")
    full = ctx.LAST_FULL_YEAR

    ax = ig.slot("people.gini", "Income inequality — Gini (higher = more unequal)")
    ib = {y: v * 100 for y, v in col(gini, "ibge").items()}
    wb = {y: v * 100 for y, v in col(gini, "wb").items()}
    ctx.line(ax, *xy(wb), ctx.p.FAINT, lw=1.8, ms=3,
             label="World Bank PIP (harmonised)")
    ctx.line(ax, *xy(ib), ctx.p.PURPLE, label="IBGE PNAD Contínua (official, 2012+)")
    note(ax, f"2010: no survey (census year) · {min(wb, key=wb.get)}: "
         f"{min(wb.values()):.1f} on the World Bank line — emergency aid",
         y=0.06, va="bottom")
    legend(ax, loc="upper right")
    recessions(ig, ax, first=True, y=0.35)

    ax = ig.slot("people.poverty", "Poverty rate — World Bank lines")
    p830, p300 = col(pov, "poverty_pct"), col(pov, "extreme_pct")
    ctx.line(ax, *xy(p830), ctx.p.TEAL, label="Below US$8.30 a day (PPP 2021)")
    ctx.line(ax, *xy(p300), ctx.p.RED, label="Below US$3.00 a day (PPP 2021)")
    last = max(p830)
    note(ax, "Brazil sets no official poverty line; IBGE reports the World "
         f"Bank's · {last}: {p830[last]:.1f}% and {p300[last]:.1f}%",
         y=0.97)
    ig.add_event(ax, *MARKS["emergency_aid"], dy=0.64)
    legend(ax, loc="upper right", bbox_to_anchor=(1.0, 0.88))
    recessions(ig, ax)

    ax = ig.slot("people.minimum_wage", "Minimum wage")
    usd = {y: v / fx[y] for y, v in mw.items() if y in fx}
    ctx.line(ax, *xy(usd), ctx.p.YELLOW,
             label="Monthly, at the year's average PTAX")
    note(ax, f"{full}: R${mw[full]:,.0f} a month = US${usd[full]:,.0f} · "
         f"peak in dollars: {max(usd, key=usd.get)}", y=0.97)
    legend(ax, loc="upper left", bbox_to_anchor=(0.0, 0.90))
    recessions(ig, ax)

    # the lens: the same wage in reais, nominal and in today's prices —
    # the real gain is the Brazilian story, and the dollar line hides it
    ax = ig.slot("people.lens", "Minimum wage in reais — nominal and real")
    real = real_reais(mw, ipca, full)
    ctx.line(ax, *xy(mw), ctx.p.YELLOW, lw=1.8, ms=3, label="Nominal R$ a month")
    ctx.line(ax, *xy(real), "#8A6D3B", label=f"In {full} reais (IPCA)")
    gain = real[full] / real[2006] - 1
    note(ax, f"+{gain * 100:.0f}% in real terms, 2006–{full}", y=0.06,
         va="bottom", weight="bold")
    legend(ax, loc="upper left")
    ax.set_ylabel("R$ per month", fontsize=8.6, color=ctx.p.MUTED)
    ax.set_ylim(0, max(max(mw.values()), max(real.values())) * 1.2)
    recessions(ig, ax)
    finish(ig)


# -------------------------------------------------------------- world
def fig_world(ctx, ig) -> None:
    world = ctx.table("international/world.csv")
    hdi = col(ctx.table("social/hdi.csv"), "value")
    cpi = col(ctx.table("international/cpi.csv"), "score")
    res = col(ctx.table("macro/reserves.csv"), "eop_usbi")
    brl = col(ctx.table("macro/gdp.csv"), "nominal_rbi")
    full = ctx.LAST_FULL_YEAR

    ax = ig.slot("world.gdp", "GDP at current prices")
    gdp = {y: v / 1e9 for y, v in col(world, "gdp_usd").items() if y >= 2006}
    ctx.line(ax, *xy(gdp), ctx.p.GREEN_D, label="US$ bn (World Bank)")
    peak = max(gdp, key=gdp.get)
    note(ax, f"{peak} peak US${gdp[peak]:,.0f}bn · {full}: "
         f"US${gdp[full]:,.0f}bn = R${brl[full] / 1000:.1f}tn (IBGE)", y=0.97)
    recessions(ig, ax, first=True, y=0.25)

    ax = ig.slot("world.hdi", "Human Development Index")
    ax.axhline(0.8, color=ctx.p.FAINT, lw=0.9, ls=":")
    ctx.line(ax, *xy(hdi), ctx.p.GREEN_D, label="HDI (UNDP)")
    note(ax, "0.800 = very high human development", y=0.62, va="bottom")
    dip = min((y for y in hdi if 2019 < y), key=hdi.get)
    note(ax, f"{max(hdi)}: {hdi[max(hdi)]:.3f} · pandemic dip to "
         f"{hdi[dip]:.3f} in {dip}", y=0.06, va="bottom")
    recessions(ig, ax)

    # TI rebased the index in 2012 and says only 2012+ is comparable: the
    # earlier 0-10 scores ×10 are drawn as their own segment, not joined
    ax = ig.slot("world.cpi", "Corruption Perceptions Index (higher = cleaner)")
    old = {y: v * 10 for y, v in cpi.items() if y < 2012}
    new = {y: v for y, v in cpi.items() if y >= 2012}
    ctx.line(ax, *xy(new), ctx.p.TEAL, label="Score, 2012+ method (TI)")
    ctx.line(ax, *xy(old), ctx.p.FAINT, lw=1.6, ms=3, ls=":",
             label="2006–11 on the old 0–10 scale, ×10")
    note(ax, f"2012: {new[2012]:.0f} to {full}: {new[full]:.0f}", y=0.06,
         va="bottom")
    legend(ax, loc="upper right")
    recessions(ig, ax)

    ax = ig.slot("world.reserves", "Official reserves")
    ctx.line(ax, *xy(res), ctx.p.BLUE, label="US$ bn, year-end (BCB)")
    note(ax, f"US${res[2006]:,.0f}bn in 2006 to US${res[full]:,.0f}bn in {full}",
         y=0.06, va="bottom")
    ig.add_event(ax, *MARKS["reserves_sold"], dy=0.97)
    ig.mark_partial(ax, ctx.YEARS[-1], f"{ctx.YEARS[-1]}: latest month")
    recessions(ig, ax)
    finish(ig)


# --------------------------------------------------------- demography
def fig_demographics(ctx, ig) -> None:
    pop_t = ctx.table("social/population.csv")
    wb = ctx.table("social/demography.csv")
    lo, hi = ctx.YEARS[0], ctx.YEARS[-1]
    split = 2024     # the last year with observed births and deaths in it
    pop = col(pop_t, "pop_mn")
    births, deaths = col(pop_t, "births"), col(pop_t, "deaths")
    window = {y: v for y, v in pop.items() if lo <= y <= hi}

    ax = ig.slot("demography.population", "Population")
    ctx.line(ax, *ctx.index_2006(window), ctx.p.BLUE, split_year=split,
             label="IBGE, 1 July (projection rev. 2024)")
    peak = max(pop, key=pop.get)
    full = ctx.LAST_FULL_YEAR
    note(ax, f"{full}: {pop[full]:.1f}M · IBGE projects a peak of {pop[peak]:.1f}M "
         f"in {peak},\nthen decline", y=0.97)
    legend(ax, loc="lower right")
    recessions(ig, ax, first=True, y=0.25)

    ax = ig.slot("demography.fertility", "Total fertility rate")
    tfr = {y: v for y, v in col(pop_t, "tfr").items() if lo <= y <= hi}
    ax.axhline(2.1, color=ctx.p.MUTED, lw=1.0, ls=(0, (5, 4)))
    note(ax, "replacement level 2.1", y=0.74)
    ctx.line(ax, *xy(tfr), ctx.p.RED, split_year=split, label="IBGE")
    note(ax, f"{lo}: {tfr[lo]:.2f} to {split}: {tfr[split]:.2f}", y=0.06,
         va="bottom")
    legend(ax, loc="upper right")
    recessions(ig, ax)

    ax = ig.slot("demography.birth_death", "Crude birth and death rates")
    br = series_per(births, pop, 1e3, ctx)
    dr = series_per(deaths, pop, 1e3, ctx)
    ctx.line(ax, *xy(br, lo, hi), ctx.p.GREEN_D, split_year=split,
             label="Births per 1,000")
    ctx.line(ax, *xy(dr, lo, hi), ctx.p.INK, split_year=split,
             label="Deaths per 1,000")
    note(ax, "IBGE projection model; registered deaths are on the "
         "mortality plate", y=0.97)
    legend(ax, loc="upper right", bbox_to_anchor=(1.0, 0.90))
    recessions(ig, ax)

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net migration")
    nat = {y: br[y] - dr[y] for y in br}
    wpop, mig = col(wb, "population"), col(wb, "net_migration")
    nm = dict(zip(*ctx.per_1000({y: v for y, v in mig.items() if y >= lo},
                                wpop)))
    ctx.line(ax, *xy(nat, lo, hi), ctx.p.GREEN_D, split_year=split,
             label="Natural increase (IBGE)")
    ctx.line(ax, *xy(nm), ctx.p.PURPLE, lw=1.8, ms=3,
             label="Net migration (UN WPP via World Bank)")
    cross = next((y for y in sorted(births)
                  if y > split and deaths[y] > births[y]), None)
    if cross:
        note(ax, f"on IBGE's projection deaths overtake births in {cross}",
             y=0.97)
    legend(ax, loc="upper right", bbox_to_anchor=(1.0, 0.90))
    recessions(ig, ax)
    finish(ig)


# ----------------------------------------------------------- security
def fig_security(ctx, ig) -> None:
    hom = ctx.table("social/homicides.csv")
    fb = ctx.table("social/violence_fbsp.csv")
    deaths = ctx.table("social/deaths.csv")
    who = ctx.table("social/security.csv")
    wb = ctx.table("social/demography.csv")
    pop = ibge_pop(ctx)

    ax = ig.slot("security.homicide", "Homicide rate — two systems, not spliced")
    reg, est = col(hom, "rate"), col(hom, "est_rate")
    mvi = col(fb, "mvi_rate")
    ctx.line(ax, *xy(reg), ctx.p.RED, label="IPEA/SIM registered (residence)")
    ctx.line(ax, *xy(est), ctx.p.INK, lw=1.8, ms=3, ls="--",
             label="IPEA/SIM estimated, incl. hidden homicides")
    ctx.line(ax, *xy(mvi), ctx.p.BLUE, lw=1.8, ms=3,
             label="FBSP violent deaths, MVI (occurrence)")
    ig.add_event(ax, *MARKS["reclassified"], dy=0.30)
    legend(ax, loc="lower left")
    recessions(ig, ax, first=True, y=0.55)

    ax = ig.slot("security.suicide", "Suicide rate")
    sim = series_per(col(deaths, "suicide"), pop, 1e5, ctx)
    whs = col(who, "suicide_per_100k")
    sim = {y: v for y, v in sim.items() if y >= 2006}
    ctx.line(ax, *xy(sim), ctx.p.PURPLE, label="SIM, X60–X84, crude")
    ctx.line(ax, *xy(whs, 2006), ctx.p.FAINT, lw=1.6, ms=3,
             label="WHO estimate, age-standardised")
    last = max(sim)
    note(ax, f"{sim[2006]:.1f} per 100,000 in 2006 to {sim[last]:.1f} in {last}"
         f" — up {sim[last] / sim[2006] * 100 - 100:.0f}%", y=0.97)
    legend(ax, loc="upper left", bbox_to_anchor=(0.0, 0.90))
    recessions(ig, ax)

    ax = ig.slot("security.road_deaths", "Road traffic deaths")
    road = series_per(col(deaths, "road"), pop, 1e5, ctx)
    road = {y: v for y, v in road.items() if y >= 2006}
    whr = col(who, "road_deaths_per_100k")
    ctx.line(ax, *xy(road), ctx.p.YELLOW, label="SIM, land transport V01–V89")
    ctx.line(ax, *xy(whr, 2006), ctx.p.FAINT, lw=1.6, ms=3,
             label="WHO estimate")
    top = max(road, key=road.get)
    note(ax, f"{top}: {road[top]:.1f} per 100,000 to {road[max(road)]:.1f} in "
         f"{max(road)}", y=0.06, va="bottom")
    legend(ax, loc="upper right")
    recessions(ig, ax)

    # the lens: deaths following police intervention and violence against women, both FBSP
    # police records, each over its own population
    ax = ig.slot("security.lens", "Deaths following police intervention and homicides of women, per 100,000")
    pk = series_per(col(fb, "police_killings"), pop, 1e5, ctx)
    fem_pop = {y: v / 1e6 for y, v in col(wb, "population_female").items()}
    wh = series_per(col(fb, "women_homicides"), fem_pop, 1e5, ctx)
    fe = series_per(col(fb, "femicides"), fem_pop, 1e5, ctx)
    ys = sorted(set(wh) & set(fe))
    ax.fill_between(ys, [wh[y] for y in ys], [fe[y] for y in ys],
                    color=ctx.p.INK, alpha=0.07, lw=0, zorder=1)
    ctx.line(ax, *xy(pk), ctx.p.PURPLE,
             label="Deaths following police intervention, per 100k people")
    ctx.line(ax, *xy(wh), ctx.p.INK, lw=1.8, ms=3,
             label="All homicides of women, per 100k women")
    ctx.line(ax, *xy(fe), ctx.p.RED, lw=1.8, ms=3,
             label="of these, classified as femicide")
    note(ax, "the femicide qualifier dates from 2015\nand took years to "
         "apply:\nmuch of the rise is classification", y=0.42, va="center")
    legend(ax, loc="upper left", fontsize=7.8)
    ax.set_ylabel("per 100,000 (FBSP)", fontsize=8.6, color=ctx.p.MUTED)
    ax.set_ylim(0, max(max(pk.values()), max(wh.values())) * 1.55)
    recessions(ig, ax)
    finish(ig)


# ---------------------------------------------------------- mortality
def fig_epidemics(ctx, ig) -> None:
    deaths = col(ctx.table("social/deaths.csv"), "registered")
    ep = ctx.table("social/epidemic_deaths.csv")
    model = col(ctx.table("social/population.csv"), "deaths")
    pop = ibge_pop(ctx)
    lo = ctx.YEARS[0]
    full = ctx.LAST_FULL_YEAR

    ax = ig.slot("mortality.death_rate", "Crude death rate")
    rate = series_per({y: v for y, v in deaths.items() if y >= lo}, pop,
                      1e3, ctx)
    ctx.line(ax, *xy(rate), ctx.p.INK,
             label="Registered deaths, SIM (residence)")
    mrate = series_per({y: v for y, v in model.items() if lo <= y <= 2024},
                       pop, 1e3, ctx)
    ctx.line(ax, *xy(mrate), ctx.p.FAINT, lw=1.4, ms=2.6,
             label="IBGE projection model (corrects under-registration)")
    top = max(rate, key=rate.get)
    note(ax, f"{top}: {rate[top]:.1f} per 1,000 · {full} is preliminary",
         y=0.06, va="bottom")
    legend(ax, loc="upper left")
    recessions(ig, ax, first=True, y=0.2)

    ax = ig.slot("mortality.excess_deaths", "Excess deaths")
    base = sum(deaths[y] for y in range(2015, 2020)) / 5
    # from the baseline years on: before them the gap to a 2015-19 mean is
    # population growth, not a shortfall of deaths
    exc = {y: (v / base - 1) * 100 for y, v in deaths.items() if y >= 2015}
    ctx.bars(ax, *xy(exc), lambda v: ctx.p.RED if v > 0 else ctx.p.FAINT)
    top = max(exc, key=exc.get)
    ax.annotate(f"{exc[top]:+.0f}%", (top, exc[top]), textcoords="offset points",
                xytext=(0, -5), ha="center", va="top", fontsize=8.6,
                fontweight="bold", color="#FFFFFF", gid="qa-on-data")
    note(ax, f"registered deaths against their 2015–19 average "
         f"({base:,.0f} a year);\nno age adjustment, so an ageing "
         f"population drifts upward", y=0.97, x=0.02)
    recessions(ig, ax)

    # B34 before 2020 is a bucket of unspecified viral deaths; drawing it
    # under a COVID-19 title would mislabel a decade of points
    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause")
    cv = {y: v for y, v in col(ep, "covid").items() if y >= 2020}
    rate = series_per(cv, pop, 1e5, ctx)
    ctx.bars(ax, *xy(rate), lambda v: ctx.p.RED)
    top = max(rate, key=rate.get)
    ax.annotate(f"{rate[top]:.0f}", (top, rate[top]), textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=8.6, fontweight="bold",
                color=ctx.p.RED)
    note(ax, f"SIM, ICD-10 B34 from 2020 · {top}: {cv[top]:,.0f} deaths",
         y=0.97)
    recessions(ig, ax)

    ax = ig.slot("mortality.lens", "Influenza and dengue deaths")
    fl = series_per({y: v for y, v in col(ep, "influenza").items() if y >= lo},
                    pop, 1e5, ctx)
    dg = series_per({y: v for y, v in col(ep, "dengue").items() if y >= lo},
                    pop, 1e5, ctx)
    ctx.line(ax, *xy(fl), ctx.p.BLUE, label="Influenza, J09–J11")
    ctx.line(ax, *xy(dg), ctx.p.PURPLE, label="Dengue, A90/A91 + A97")
    ig.add_event(ax, *MARKS["h1n1"], dy=0.97)
    dp = max(dg, key=dg.get)
    note(ax, f"dengue record {dp}: {dg[dp]:.2f} per 100,000 · dengue moved "
         f"to ICD A97 in 2025;\nthe line sums old and new codes", y=0.86)
    legend(ax, loc="upper left", bbox_to_anchor=(0.0, 0.72))
    ax.set_ylabel("per 100,000", fontsize=8.6, color=ctx.p.MUTED)
    ax.set_ylim(0, max(max(fl.values()), max(dg.values())) * 1.6)
    recessions(ig, ax)
    finish(ig)


# ----------------------------------------------------------- migration
def fig_migration(ctx, ig) -> None:
    ax = ig.slot("migration.flows",
                 "Immigration and emigration — incompatible components")
    ctx.pending(ax)
    recessions(ig, ax, first=True)
    note(ax, "IBGE estimates imply impossible negative emigration in 2020;\n"
             "the gross pair stays pending until the method is reconciled.",
         x=0.5, y=0.34, ha="center")
    ax = ig.slot("migration.net", "Net migration — UN WPP estimate")
    demo = ctx.table("social/demography.csv")
    rate = dict(zip(*ctx.per_1000(col(demo, "net_migration"),
                                  col(demo, "population"))))
    ctx.line(ax, *xy(rate), ctx.p.BLUE, label="UN WPP, modelled")
    recessions(ig, ax)
    legend(ax, loc="upper left")
    ax = ig.slot("migration.foreign_born",
                 "Foreign-born and foreign-citizen share")
    stock = ctx.table("migration/stock_census.csv")
    ctx.line(ax, *xy(col(stock, "foreign_born_pct")), ctx.p.BLUE,
             label="born abroad")
    ctx.line(ax, *xy(col(stock, "foreign_citizens_pct")), ctx.p.YELLOW,
             label="foreign citizens")
    for value, colour in ((col(stock, "foreign_born_pct")[2022], ctx.p.BLUE),
                          (col(stock, "foreign_citizens_pct")[2022], ctx.p.YELLOW)):
        ax.text(2022, value, f"{value:.2f}%", ha="center", va="bottom",
                fontsize=8.4, fontweight="bold", color=colour)
    recessions(ig, ax)
    legend(ax, loc="upper left")
    note(ax, "Censo 2022, same-census denominator. Birthplace and\n"
             "citizenship are different stocks.", x=0.985, y=0.08,
         ha="right", va="bottom")
    ax = ig.slot("migration.lens", "Lens: residents born in Latin America")
    origins = col(ctx.table("migration/origins_census.csv"),
                  "latin_america_born")
    ys, vals = xy(origins)
    vals = [v / 1000 for v in vals]
    ax.bar([str(y) for y in ys], vals,
           color=[ctx.p.YELLOW, ctx.p.GREEN_D], width=0.58)
    ax.set_ylabel("thousand residents", fontsize=8.6, color=ctx.p.MUTED)
    for i, value in enumerate(vals):
        ax.text(i, value, f"{value:,.0f}k", ha="center", va="bottom",
                fontsize=8.5, fontweight="bold", color=ctx.p.INK)
    finish(ig, skip=(3,))
    ax.set_xlim(-0.6, len(ys) - 0.4)


# The plates, in the order the page lists them. `slug` is the chapter id
# the files have always been saved under, so no link breaks.
SOURCE = {
    "economy": ("IBGE (national accounts, IPCA, PNAD-C/PME) · World Bank WDI "
                "(GDP per person, ILO unemployment) · CMN (inflation target)"),
    "fiscal": ("IMF WEO / Fiscal Monitor (general government) · Tesouro "
               "Nacional (central-government primary result, carga "
               "tributária) · Banco Central (DBGG, NFSP)"),
    "spending": ("Tesouro Nacional (COFOG, general government; RTN) · IBGE "
                 "(FBCF) · OECD National Accounts at a Glance (government GFCF)"),
    "trade": ("World Bank WDI (goods and services, % of GDP) · MDIC/SECEX "
              "(goods, destinations, products)"),
    "markets": ("Banco Central (Selic, PTAX) · IBGE (IPCA) · B3 (Ibovespa) · "
                "S&P 500 via Yahoo Finance"),
    "credit": ("BIS total credit statistics · Banco Central SGS (rates, "
               "arrears, household indebtedness)"),
    "people": ("IBGE PNAD Contínua / World Bank PIP (Gini, poverty) · "
               "planalto.gov.br (minimum wage) · Banco Central (PTAX) · IBGE (IPCA)"),
    "world": ("World Bank WDI (GDP) · UNDP HDR 2025 · Transparency "
              "International · Banco Central (reserves) · IBGE"),
    "demography": ("IBGE — Projeções da População, revisão 2024 · UN WPP via "
                   "World Bank (net migration)"),
    "security": ("IPEA Atlas da Violência (SIM) · FBSP Anuário 2026 · "
                 "SIM/DATASUS · WHO via World Bank · IBGE and World Bank "
                 "populations"),
    "mortality": ("Ministério da Saúde — SIM/DATASUS (TabNet, ICD-10) · IBGE "
                  "(population, projection model)"),
    "migration": ("IBGE, Censos Demográficos 2010 e 2022 · UN World "
                  "Population Prospects via World Bank WDI"),
}

PLATES = (
    dict(slug="01_economy", topic="economy", builder=fig_economy,
         title="The Brazilian Economy, 2006–2026",
         subtitle=("Growth, income per person, inflation against its target "
                   "and unemployment — on the scales every country shares."),
         source="Sources: " + SOURCE["economy"],
         alt=("Four panels on the Brazilian economy: real GDP growth bars "
              "with the 2014–16 recession and 2020; GDP per person in US$ "
              "on a log scale, peaking in 2011; IPCA inflation against the "
              "target band; and unemployment from PNAD Contínua, the old "
              "PME survey and the ILO estimate.")),
    dict(slug="02_fiscal", topic="fiscal", builder=fig_fiscal,
         title="Public Finances — Balance, Debt and Interest, 2006–2025",
         subtitle=("General government on the IMF's basis, with the "
                   "Brazilian measures beside it: the central-government "
                   "primary result, DBGG gross debt and the NFSP interest bill."),
         source="Sources: " + SOURCE["fiscal"],
         alt=("Four panels on Brazilian public finances: general-government "
              "revenue and expenditure with the tax burden; the overall "
              "balance as bars with the general-government and "
              "central-government primary balances; gross debt on two "
              "definitions; and interest paid, IMF and BCB.")),
    dict(slug="03_spending", topic="spending", builder=fig_spending,
         title="Where the Money Goes — Spending and Investment",
         subtitle=("General-government spending by COFOG function — federal, "
                   "state and municipal — the social-protection share, and how "
                   "little of the economy is invested, publicly or at all."),
         source="Sources: " + SOURCE["spending"],
         alt=("Four panels: general-government spending by COFOG function, "
              "stacked, from 2010; social protection against everything else; "
              "whole-economy investment as a share of GDP; and public "
              "investment, general government to 2020 and federal to 2025.")),
    dict(slug="06_trade", topic="trade", builder=fig_trade,
         title="Foreign Trade — Openness, the Surplus and China",
         subtitle=("Goods and services as a share of GDP, on the national-"
                   "accounts basis every country shares, then the "
                   "commodity-heavy goods trade behind it."),
         source="Sources: " + SOURCE["trade"],
         alt=("Four panels: exports and imports of goods and services as a "
              "share of GDP; the trade balance as bars; the share of goods "
              "exports going to China, the United States, the European "
              "Union and Argentina; and Brazil's top export groups in "
              "snapshot years.")),
    dict(slug="04_markets", topic="markets", builder=fig_markets,
         title="Money & Markets — the Selic, the Real and the Ibovespa",
         subtitle=("The policy rate against inflation, the real as an index "
                   "where up means stronger, and Brazilian equities in "
                   "dollars beside the S&P 500."),
         source="Sources: " + SOURCE["markets"],
         alt=("Four panels: the Selic against IPCA inflation; the "
              "ten-year government bond yield; the real against the US "
              "dollar as an index, 2006 = 100; and the Ibovespa in dollars "
              "against the S&P 500, both indexed to 2006.")),
    dict(slug="08_people", topic="people", builder=fig_people,
         title="People — Inequality, Poverty and the Minimum Wage",
         subtitle=("Inequality and poverty fell, with a lurch in 2020–21; "
                   "the minimum wage gained in reais far more than in dollars."),
         source="Sources: " + SOURCE["people"],
         alt=("Four panels: the Gini index from IBGE and the World Bank; "
              "poverty at the US$8.30 and US$3.00 lines; the minimum wage "
              "in US$ a month; and the minimum wage in reais, nominal and "
              "in constant prices.")),
    dict(slug="07_world", topic="world", builder=fig_world,
         title="Brazil in the World — Size, Development, Corruption, Reserves",
         subtitle=("How big the economy is in dollars, how the UNDP and "
                   "Transparency International score it, and the reserves "
                   "behind the real."),
         source="Sources: " + SOURCE["world"],
         alt=("Four panels: GDP in US$ billion on a log scale; the Human "
              "Development Index; the Corruption Perceptions Index with the "
              "pre-2012 scale drawn apart; and official reserves in US$ "
              "billion.")),
    dict(slug="09_demographics", topic="demography", builder=fig_demographics,
         title="Brazil's Demographic Transition — the Peak Is in Sight",
         subtitle=("Population growth slowing toward a peak IBGE projects "
                   "for the 2040s, fertility well below replacement, and "
                   "deaths closing on births."),
         source="Sources: " + SOURCE["demography"],
         alt=("Four panels: population as an index, 2006 = 100; the total "
              "fertility rate against the replacement level; crude birth "
              "and death rates per 1,000; and natural increase and net "
              "migration per 1,000.")),
    dict(slug="10_security", topic="security", builder=fig_security,
         title="Violence — Homicides, Suicide, Roads and Police Intervention",
         subtitle=("Two homicide systems drawn side by side, never spliced: "
                   "IPEA/SIM death certificates by residence and FBSP police "
                   "records by occurrence. Everything per 100,000."),
         source="Sources: " + SOURCE["security"],
         alt=("Four panels: homicide rates on a log scale from IPEA/SIM, "
              "registered and estimated, and from FBSP; the suicide rate; "
              "road traffic deaths; and deaths resulting from police intervention per 100,000 people "
              "beside homicides of women and femicides per 100,000 women.")),
    dict(slug="05_credit", topic="credit", builder=fig_credit,
         title="Credit & Household Debt — Supply, Price and Burden",
         subtitle=("Household debt is modest against GDP and heavy against "
                   "income, because Brazilian credit is so expensive."),
         source="Sources: " + SOURCE["credit"],
         alt=("Four panels: household debt as a share of GDP; the average "
              "household lending rate against the Selic; non-performing "
              "loans; and household debt and debt service as a share of "
              "income.")),
    dict(slug="11_epidemics", topic="mortality", builder=fig_epidemics,
         title="Mortality and Epidemics — COVID-19, Influenza and Dengue",
         subtitle=("Registered deaths per 1,000, the excess over 2015–19, and "
                   "the epidemics per 100,000 — SIM death certificates by "
                   "underlying cause, counted by residence."),
         source="Sources: " + SOURCE["mortality"],
         alt=("Four panels: the crude death rate from registered deaths; "
              "excess deaths against the 2015–19 average; COVID-19 deaths "
              "per 100,000; and influenza and dengue deaths per 100,000.")),
    dict(slug="12_migration", topic="migration", builder=fig_migration,
         title="Brazilian migration, on compatible definitions",
         subtitle="Modelled net movement and census stocks; gross flows remain pending",
         source="Sources: " + SOURCE["migration"],
         alt="Gross immigration and emigration remain visibly pending because the published components imply impossible negative emigration in 2020. UN WPP supplies modelled net migration per 1,000. The 2022 census shows foreign-born and foreign-citizen shares, and the lens compares Latin-America-born residents in 2010 and 2022."),
)
