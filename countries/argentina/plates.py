"""The Argentina plates, drawn on the plate spine.

Every plate declares its topic and claims its four panels by slot key in
spine order (PLATE_SPINE.md, core/spine.py), so the comparison viewer can
lay any of them over another country's plate for the same topic. The
canonical slots carry the shared indicator in the shared unit and are put
on the shared scale at save time; the lens slots carry what only Argentina
has to say.

Three things recur on almost every panel, and are drawn by the helpers at
the top of this file rather than by hand:

  - the INDEC intervention, 2007-2016, as a hatched band behind every
    series INDEC produced or that is built on INDEC's national accounts or
    CPI (the IMF and the World Bank republish what INDEC published);
  - the recession bands from country.yaml, every year INDEC's real GDP
    fell, behind every time series;
  - the running year, dashed or hatched, through ctx.line and ctx.bars.

A series with a hole in it is drawn as separate segments, never joined
across the hole: a line from 2006 to 2016 across the intervened decade
would assert that the years between were measured. Methodology breaks are
the same: separate segments, separate labels, a note.

Every number a note quotes is read from the CSVs as the plate is drawn.
"""
from __future__ import annotations

from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

from core.sideload import sibling

ds = sibling(__file__, "datasets")
events = sibling(__file__, "events")

FIRST, LAST = ds.FIRST_YEAR, ds.LAST_YEAR


# ================================================================ data
def col(ctx, rel: str, column: str) -> dict[int, float]:
    """{year: value} for one column, blanks dropped, inside the window."""
    yrs, vals = ctx.series(ctx.table(rel), column)
    return {int(y): float(v) for y, v in zip(yrs, vals) if FIRST <= y <= LAST}


def pairs(d: dict) -> tuple[list[int], list[float]]:
    ys = sorted(d)
    return ys, [d[y] for y in ys]


def runs(d: dict) -> list[dict]:
    """The series cut wherever a year is missing, so no gap is bridged."""
    out: list[dict] = []
    for y in sorted(d):
        if out and y - max(out[-1]) == 1:
            out[-1][y] = d[y]
        else:
            out.append({y: d[y]})
    return out


def full(ctx, d: dict) -> dict:
    """Only complete years: an annual flow for the running year is not one."""
    return {y: v for y, v in d.items() if y <= ctx.LAST_FULL_YEAR}


def population(ctx) -> dict[int, float]:
    """INDEC's national population, persons, mid-year (macro/gdp.csv).

    The denominator of every computed rate on these plates: the same
    projection the Ministerio de Seguridad divides by for its published
    homicide rate, national in scope like the DEIS registers it is
    divided into. See DATA_NOTES.md, "Rates".
    """
    return {y: v * 1e6 for y, v in col(ctx, "macro/gdp.csv",
                                         "population_mn").items()}


# ============================================================ drawing
def line(ctx, ax, d, color, label="", **kw):
    """ctx.line per unbroken run, the legend entry on the first only."""
    for i, seg in enumerate(runs(d)):
        ctx.line(ax, *pairs(seg), color, label=label if i == 0 else "",
                 **kw)


def bars(ctx, ax, d, color):
    ctx.bars(ax, *pairs(d), color)


def signed(ctx):
    return lambda v: ctx.p.GREEN if v >= 0 else ctx.p.RED


def indec(ax, ctx):
    """The intervened decade, hatched and behind everything (zorder 0)."""
    a, b = events.INDEC_GAP
    ax.axvspan(a, b, facecolor="none", edgecolor=ctx.p.spine, hatch="////",
               lw=0, zorder=0, alpha=0.55)


def finish(ig, ax, ctx, intervened=False):
    """Year axis, recession bands and (where it applies) the INDEC hatch."""
    ig.style_axis(ax)
    ig.add_recessions(ax, label=False)
    if intervened:
        indec(ax, ctx)


def key(ctx, intervened=False) -> list:
    """Legend handles for the bands, added to every slot-1 legend.

    The bands are labelled once per plate, here, rather than one caption
    per band: six recession captions and the intervention would sit on the
    panel title.
    """
    out = [Patch(facecolor=ctx.p.band, edgecolor="none",
                 label="years real GDP fell")]
    if intervened:
        out.append(Patch(facecolor="none", edgecolor=ctx.p.spine,
                         hatch="////", lw=0, label="INDEC intervened, 2007–16"))
    return out


def legend(ctx, ax, loc="upper left", extra=(), ncol=1, **kw):
    handles, labels = ax.get_legend_handles_labels()
    handles = list(handles) + list(extra)
    labels = list(labels) + [h.get_label() for h in extra]
    ax.legend(handles, labels, loc=loc, ncol=ncol, frameon=False,
              fontsize=8.4, labelcolor=ctx.p.muted, handlelength=1.6,
              columnspacing=1.0, borderaxespad=0.3, **kw)


def note(ctx, ax, x, y, text, ha="left", va="top"):
    """A caveat placed where the thing it explains is, in axes fraction."""
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va, fontsize=7.9,
            color=ctx.p.muted, style="italic", zorder=8, linespacing=1.25,
            bbox=dict(boxstyle="round,pad=0.35", facecolor=ctx.p.paper,
                      edgecolor=ctx.p.spine, linewidth=0.6, alpha=0.95))


def pct(decimals=0):
    return FuncFormatter(lambda v, _: f"{v:,.{decimals}f}")


def peak(d):
    y = max(d, key=d.get)
    return y, d[y]


def trough(d):
    y = min(d, key=d.get)
    return y, d[y]


# ============================================================ 01 economy
def plate_output(ctx, ig) -> None:
    p = ctx.p
    gdp = ctx.table("macro/gdp.csv")
    growth = col(ctx, "macro/gdp.csv", "real_growth")

    ax = ig.slot("economy.growth", "Real GDP growth")
    bars(ctx, ax, growth, signed(ctx))
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="lower center", extra=key(ctx, True))
    lo_y, lo_v = trough(growth)
    hi_y, hi_v = peak(full(ctx, {y: v for y, v in growth.items()
                                 if y > lo_y}))
    note(ctx, ax, 0.98, 0.97,
         f"{lo_v:.1f}% in {lo_y},\n{hi_v:+.1f}% in {hi_y}.\n"
         f"Fell in {sum(v < 0 for v in growth.values())} "
         f"of {len(growth)} years.", ha="right")

    ax = ig.slot("economy.gdp_per_person", "GDP per person")
    wb = col(ctx, "macro/world.csv", "gdp_per_person_usd")
    nat = col(ctx, "macro/gdp.csv", "gdp_per_capita_usd")
    line(ctx, ax, nat, p.FAINT, label="INDEC, current US$", lw=1.6, ms=2.6)
    line(ctx, ax, wb, p.NAVY, label="World Bank, current US$")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="lower right")
    gap = {y: (nat[y] / wb[y] - 1) * 100 for y in nat if y in wb}
    gy, gv = peak(gap)
    note(ctx, ax, 0.02, 0.97,
         f"Both at the official rate, which under the cepos most\n"
         f"people could not buy at. INDEC's is {gv:.0f}% higher in {gy}.")

    ax = ig.slot("economy.inflation", "Consumer price inflation (Dec/Dec)")
    ipc = col(ctx, "macro/ipc.csv", "official")
    alt = col(ctx, "macro/ipc.csv", "alternative")
    line(ctx, ax, alt, p.ASTERISK, label="IPC San Luis, provincial (official)")
    line(ctx, ax, ipc, p.CELESTE_D, label="INDEC, national CPI")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper left")
    py, pv = peak(ipc)
    note(ctx, ax, 0.02, 0.80,
         f"The axis grows to hold {pv:.0f}% in {py}.\n"
         f"No inflation target since 2018.\n"
         f"{ctx.LAST_FULL_YEAR + 1}: rise since December, year to date.")

    ax = ig.slot("economy.unemployment", "Unemployment")
    eph = col(ctx, "macro/unemployment.csv", "value")
    ilo = col(ctx, "macro/economy_intl.csv", "unemployment_ilo_pct")
    line(ctx, ax, ilo, p.FAINT, label="ILO modelled estimate", lw=1.6, ms=2.6)
    line(ctx, ax, eph, p.CELESTE, label="INDEC EPH, 31 urban areas")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper right")
    py, pv = peak(eph)
    note(ctx, ax, 0.02, 0.97,
         f"The EPH surveys the cities only, about two\n"
         f"thirds of the population. Peak {pv:.1f}% in {py}.")


# ============================================================= 02 prices
def plate_prices(ctx, ig) -> None:
    p = ctx.p
    ipc = col(ctx, "macro/ipc.csv", "official")
    alt = col(ctx, "macro/ipc.csv", "alternative")
    eop = col(ctx, "macro/dollar.csv", "official_eop")
    blue = col(ctx, "markets/parallel_fx.csv", "blue")
    res = col(ctx, "macro/reserves.csv", "eop_usbi")
    m = events.MARKS

    ax = ig.slot("prices.lens1", "Consumer price inflation, % per year")
    bars(ctx, ax, alt, p.ASTERISK)
    bars(ctx, ax, ipc, p.CELESTE)
    finish(ig, ax, ctx, intervened=True)
    ig.headroom(ax, top=0.30)
    legend(ctx, ax, loc="upper left", extra=[
        Patch(color=p.CELESTE, label="INDEC, national index"),
        Patch(color=p.ASTERISK, label="IPC San Luis (official, provincial)"),
        *key(ctx, True)])
    py, pv = peak(ipc)
    ctx.annotate_value(ax, py, pv, f"{pv:.0f}%", p.CELESTE_D, offset=(0, 4))
    note(ctx, ax, 0.98, 0.97,
         f"{ctx.LAST_FULL_YEAR + 1}, hatched: the rise since\n"
         f"December, year to date.",
         ha="right")

    ax = ig.slot("prices.lens2", "Pesos per US dollar, year end, log scale")
    line(ctx, ax, eop, p.NAVY, label="official rate")
    line(ctx, ax, blue, p.ASTERISK, label="parallel (blue)", ls=(0, (5, 2)))
    finish(ig, ax, ctx)
    ax.set_yscale("log")
    ax.set_ylim(1.5, 9000)
    ax.yaxis.set_major_formatter(pct())
    legend(ctx, ax, loc="lower right")
    for k in ("cepo1", "cepo2"):
        x, text = m[k]
        ig.add_event(ax, x, text, dy=0.97)

    ax = ig.slot("prices.lens3", "The gap: parallel over official, %")
    gap = {y: (blue[y] / eop[y] - 1) * 100 for y in blue if y in eop}
    bars(ctx, ax, gap, p.SUN)
    finish(ig, ax, ctx)
    for a, b, label in ((m["cepo1"][0], m["cepo_off"][0], "cepo I"),
                        (m["cepo2"][0], m["cepo_off2"][0], "cepo II")):
        ax.axvspan(a, b, facecolor="none", edgecolor=p.SUN, hatch="..",
                   lw=0, zorder=0, alpha=0.5)
        ax.text((a + b) / 2, 0.97, label, transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=8.4, color=p.muted,
                style="italic", zorder=4)
    ig.headroom(ax, top=0.22)
    py, pv = peak(gap)
    ctx.annotate_value(ax, py, pv, f"{pv:.0f}%", p.NAVY, offset=(0, 3))
    note(ctx, ax, 0.02, 0.80,
         "Blue at year end over the official\nrate at year end. Dotted: "
         "the cepos.")

    ax = ig.slot("prices.lens4", "Central bank gross reserves, US$ bn, "
                                 "year end")
    bars(ctx, ax, res, p.TEAL)
    finish(ig, ax, ctx)
    ig.headroom(ax, top=0.18)
    ty, tv = trough(res)
    ctx.annotate_value(ax, ty, tv, f"{tv:.1f}", p.RED, offset=(0, 3))
    hy, hv = peak(full(ctx, res))
    ctx.annotate_value(ax, hy, hv, f"{hv:.1f}", p.NAVY, offset=(0, 3))
    note(ctx, ax, 0.02, 0.97,
         f"{ctx.LAST_FULL_YEAR + 1}: latest reading, hatched.\n"
         f"Gross reserves; the same series meets\n"
         f"other countries on the world plate.")


# ============================================================= 03 people
def plate_living(ctx, ig) -> None:
    p = ctx.p
    s1 = col(ctx, "social/poverty.csv", "s1")
    s2 = col(ctx, "social/poverty.csv", "s2")

    ax = ig.slot("people.gini", "Income inequality, Gini (higher = less "
                                "equal)")
    gini = {y: v * 100 for y, v in col(ctx, "social/gini.csv",
                                       "indec").items()}
    wb = col(ctx, "social/gini_intl.csv", "wb")
    line(ctx, ax, wb, p.FAINT, label="World Bank (PIP), from the EPH",
         lw=1.6, ms=2.6)
    line(ctx, ax, gini, p.PURPLE, label="INDEC, per-capita family income")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper right", extra=key(ctx, True))
    note(ctx, ax, 0.02, 0.06,
         f"INDEC's coefficient (0–1) × 100. Urban EPH only.\n"
         f"{gini[FIRST]:.1f} in {FIRST}, {gini[ctx.LAST_FULL_YEAR]:.1f} in "
         f"{ctx.LAST_FULL_YEAR}.", va="bottom")

    ax = ig.slot("people.poverty", "Poverty rate")
    avg = {y: (s1[y] + s2[y]) / 2 for y in s1 if y in s2}
    wb = col(ctx, "social/poverty_intl.csv", "poverty_830_pct")
    line(ctx, ax, wb, p.FAINT, label="World Bank, below US$8.30 a day",
         lw=1.6, ms=2.6)
    line(ctx, ax, avg, p.NAVY, label="INDEC, national basket (both halves)")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper left")
    py, pv = peak(avg)
    note(ctx, ax, 0.98, 0.04,
         f"31 urban areas, about two thirds of the people.\n"
         f"Withdrawn 2007–15. Peak {pv:.1f}% in {py}.",
         ha="right", va="bottom")

    ax = ig.slot("people.minimum_wage", "Minimum wage, at the official rate")
    wage = col(ctx, "macro/minimum_wage.csv", "usd_official")
    bars(ctx, ax, wage, p.CELESTE_D)
    finish(ig, ax, ctx)
    py, pv = peak(wage)
    last = ctx.LAST_FULL_YEAR
    note(ctx, ax, 0.02, 0.97,
         f"Monthly SMVM at the year's average official rate,\n"
         f"in US$: {pv:,.0f} in {py}, {wage[last]:,.0f} in {last}. In pesos it\n"
         f"rises every year; prices rose faster.")

    ax = ig.slot("people.lens", "Lens: poverty each half year, %")
    halves = {}
    for y, v in s1.items():
        halves[y + 0.25] = v
    for y, v in s2.items():
        halves[y + 0.75] = v
    segs: list[dict] = []
    for x in sorted(halves):
        if segs and x - max(segs[-1]) <= 0.5 + 1e-9:
            segs[-1][x] = halves[x]
        else:
            segs.append({x: halves[x]})
    last_half = max(halves)
    for i, seg in enumerate(segs):
        ctx.line(ax, *pairs(seg), p.CELESTE, label="" if i else
                 "first and second half of each year",
                 split_year=last_half - 0.5)
    finish(ig, ax, ctx, intervened=True)
    ig.headroom(ax, top=0.25)
    hy = max((y for y in s1), key=s1.get)
    ctx.annotate_value(ax, hy + 0.25, s1[hy], f"{s1[hy]:.1f}%", p.RED,
                       offset=(-6, 2), ha="right")
    legend(ctx, ax, loc="upper left")
    note(ctx, ax, 0.02, 0.86,
         f"First half of {hy}, after the December {hy - 1}\n"
         f"devaluation: {s1[hy]:.1f}%. Second half: {s2[hy]:.1f}%.")


# ============================================================= 04 fiscal
def plate_state(ctx, ig) -> None:
    p = ctx.p
    gg = "fiscal/general_government.csv"
    rev = col(ctx, gg, "revenue_pct_gdp")
    exp = col(ctx, gg, "expenditure_pct_gdp")
    bal = col(ctx, gg, "balance_pct_gdp")
    prim = col(ctx, gg, "primary_balance_pct_gdp")
    debt = col(ctx, gg, "gross_debt_pct_gdp")
    tax = col(ctx, "fiscal/tax_revenue.csv", "total_pct_gdp")

    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure")
    line(ctx, ax, exp, p.RED, label="expenditure, general government (IMF)")
    line(ctx, ax, rev, p.GREEN, label="revenue, general government (IMF)")
    line(ctx, ax, tax, p.FAINT, label="national tax collection (Hacienda)",
         lw=1.6, ms=2.6)
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper left", extra=key(ctx, True))
    ed = col(ctx, "fiscal/tax_revenue.csv", "export_duties_pct_gdp")
    ey, ev = peak(ed)
    last = max(ed)
    note(ctx, ax, 0.98, 0.04,
         f"Export duties: {ev:.1f}% of GDP in {ey}, {ed[last]:.1f}% in "
         f"{last}.", ha="right", va="bottom")

    ax = ig.slot("fiscal.balance", "Overall and primary balance")
    bars(ctx, ax, bal, signed(ctx))
    line(ctx, ax, prim, p.NAVY, label="primary, general government (IMF)",
         lw=2.0)
    nat = ds.load("fiscal/primary_result.csv")
    # Three methodologies, three segments, one legend entry: never joined.
    for k in ("m1993", "m2007", "m2017"):
        seg = {y: v for y, v in nat[k].items() if FIRST <= y <= LAST}
        ctx.line(ax, *pairs(seg), p.ASTERISK, lw=1.4, ms=2.4,
                 ls=(0, (3, 2)),
                 label=("primary, national public sector (3 methods)"
                        if k == "m2017" else ""))
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="lower left", extra=[
        Patch(color=p.GREEN, label="overall balance, IMF (bars)")])
    deficits = [y for y, v in prim.items() if v < 0]
    turn = min(y for y, v in prim.items() if v > 0 and y > min(deficits))
    before = max(y for y, v in prim.items() if v > 0 and y < turn)
    note(ctx, ax, 0.98, 0.97,
         f"IMF primary surplus {prim[turn]:+.1f}% of GDP in {turn}, the\n"
         f"first since {before}. National series: three methods.",
         ha="right")

    ax = ig.slot("fiscal.debt", "Gross debt, general government")
    line(ctx, ax, debt, p.NAVY, label="IMF WEO")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper left")
    py, pv = peak(debt)
    note(ctx, ax, 0.02, 0.86,
         f"{pv:.0f}% in {py}: debt mostly in dollars, measured\n"
         f"after the December devaluation against a GDP\n"
         f"earned at the year's average prices.")

    ax = ig.slot("fiscal.interest", "Interest paid")
    interest = {y: prim[y] - bal[y] for y in prim if y in bal}
    line(ctx, ax, interest, p.RED,
         label="general government, primary − overall (IMF)")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper left")
    note(ctx, ax, 0.98, 0.97,
         "Net interest: the IMF's primary balance less its\n"
         "overall balance, which it rounds to 0.1 point.", ha="right")


# ============================================================== 05 trade
def plate_trade(ctx, ig) -> None:
    p = ctx.p
    x = col(ctx, "trade/trade_gns.csv", "exports_pct_gdp")
    m = col(ctx, "trade/trade_gns.csv", "imports_pct_gdp")

    ax = ig.slot("trade.exports_imports", "Exports and imports, goods and "
                                         "services")
    line(ctx, ax, x, p.GREEN, label="exports (World Bank)")
    line(ctx, ax, m, p.RED, label="imports (World Bank)")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper right", extra=key(ctx, True))
    goods = col(ctx, "trade/trade.csv", "exports")
    last = ctx.LAST_FULL_YEAR
    note(ctx, ax, 0.02, 0.97,
         f"National-accounts basis. Goods exports by customs:\n"
         f"US${goods[last]:,.1f}bn in {last}.")

    ax = ig.slot("trade.balance", "Trade balance")
    bal = {y: x[y] - m[y] for y in x if y in m}
    bars(ctx, ax, bal, signed(ctx))
    usd = col(ctx, "trade/trade.csv", "balance")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper left", extra=[
        Patch(color=p.GREEN, label="goods and services (bars)")])
    yy = ctx.LAST_FULL_YEAR + 1
    note(ctx, ax, 0.98, 0.04,
         f"{yy} goods, year to date: US${usd[yy]:+,.1f}bn, not drawn\n"
         f"until the year's GDP exists.", ha="right", va="bottom")

    ax = ig.slot("trade.destinations", "Top export destinations, goods")
    dest = "trade/destinations.csv"
    for c, label, colour in (("brazil", "Brazil", p.GREEN),
                             ("china", "China", p.RED),
                             ("usa", "United States", p.NAVY),
                             ("chile", "Chile", p.SUN)):
        line(ctx, ax, col(ctx, dest, c), colour, label=label, lw=2.0, ms=3)
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper right", ncol=2)
    br = col(ctx, dest, "brazil")
    note(ctx, ax, 0.02, 0.97,
         f"UN Comtrade. Brazil: {br[FIRST]:.1f}% in {FIRST},\n"
         f"{br[max(br)]:.1f}% in {max(br)}.")

    ax = ig.slot("trade.lens", "Lens: exports by category, US$ bn")
    rub = ds.load_long("trade/exports_rubros.csv", "rubro", "usbi")
    order = [("primarios", "primary products", p.GREEN),
             ("moa", "agricultural manufactures", p.TEAL),
             ("moi", "industrial manufactures", p.CELESTE),
             ("combustibles", "fuel and energy", p.SUN)]
    years = sorted(y for y in set.intersection(
        *(set(rub[k]) for k, _, _ in order)) if FIRST <= y <= LAST)
    bottom = {y: 0.0 for y in years}
    for k, label, colour in order:
        for y in years:
            part = y > ctx.LAST_FULL_YEAR
            ax.bar(y, rub[k][y], bottom=bottom[y], width=0.78, color=colour,
                   label=label if y == years[0] else "_nolegend_",
                   alpha=0.62 if part else 1.0, hatch="//" if part else None,
                   edgecolor="white", linewidth=0.5, zorder=3)
            bottom[y] += rub[k][y]
    finish(ig, ax, ctx)
    ig.headroom(ax, top=0.55)
    legend(ctx, ax, loc="upper left", ncol=2)
    share = {y: rub["combustibles"][y] / bottom[y] * 100 for y in years}
    last = ctx.LAST_FULL_YEAR
    lowy, lowv = trough(share)
    note(ctx, ax, 0.02, 0.84,
         f"Fuel: {lowv:.1f}% of exports in {lowy},\n{share[last]:.1f}% in "
         f"{last}. Industrial is the\nresidual of the other three.")


# ============================================================= 06 credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p
    cr = "macro/credit.csv"

    ax = ig.slot("credit.household_debt", "Household debt")
    bis = col(ctx, "macro/household_credit.csv", "bis_q4_pct_gdp")
    hh = col(ctx, cr, "households_pct_gdp")
    line(ctx, ax, bis, p.NAVY, label="BIS, all lenders, year end")
    line(ctx, ax, hh, p.CELESTE, label="BCRA, bank retail lines, December",
         lw=1.6, ms=2.6)
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper right", extra=key(ctx))
    mort = col(ctx, cr, "mortgage_pct_gdp")
    my, mv = peak(mort)
    ty, tv = trough(mort)
    note(ctx, ax, 0.02, 0.97,
         f"Mortgages: {mv:.2f}% of GDP in {my},\n"
         f"{tv:.2f}% in {ty}.")

    ax = ig.slot("credit.lending_rate", "Personal-loan rate vs policy rate")
    loan = col(ctx, "macro/rates.csv", "personal_loan")
    pol = col(ctx, "macro/policy_rate.csv", "policy_avg")
    line(ctx, ax, loan, p.RED, label="personal loans, annual average")
    line(ctx, ax, pol, p.NAVY, label="BCRA policy rate, annual average")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper left")
    note(ctx, ax, 0.02, 0.80,
         "Nominal, % a year. No policy rate before 2016;\n"
         "the BCRA dropped it in July 2025.")

    ax = ig.slot("credit.npl", "Non-performing loans")
    npl = col(ctx, "macro/credit_quality.csv", "npl_private_pct")
    bars(ctx, ax, npl, p.RED)
    finish(ig, ax, ctx)
    ax.legend(handles=[Patch(color=p.RED,
                             label="private-sector loans, BCRA, December")],
              loc="upper left", frameon=False, fontsize=8.4,
              labelcolor=p.muted)
    py, pv = peak(npl)
    prev = npl[py - 1]
    note(ctx, ax, 0.98, 0.97,
         f"{prev:.2f}% in {py - 1}, {pv:.2f}% in {py}: the lending\n"
         f"boom and its bad loans, a year apart.", ha="right")

    ax = ig.slot("credit.lens", "Lens: real interest rates, % per year")
    dep = col(ctx, "macro/rates.csv", "deposit_30d_real")
    per = col(ctx, "macro/rates.csv", "personal_loan_real")
    line(ctx, ax, dep, p.GREEN, label="paid on a 30-day deposit")
    line(ctx, ax, per, p.RED, label="charged on a personal loan")
    ax.axhline(0, color=p.muted, lw=0.9, zorder=2)
    finish(ig, ax, ctx)
    ax.set_xlim(FIRST - 0.6, LAST + 0.6)
    legend(ctx, ax, loc="lower left")
    neg = [y for y, v in full(ctx, dep).items() if v < 0]
    dy, dv = trough(dep)
    note(ctx, ax, 0.02, 0.97,
         f"Deflated by the national CPI, so from {min(dep)} only.\n"
         f"Saving lost in real terms {min(neg)}–{max(neg)}; "
         f"{dv:.1f}% in {dy}.")


# ============================================================ 07 markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation")
    ipc = col(ctx, "macro/ipc.csv", "official")
    alt = col(ctx, "macro/ipc.csv", "alternative")
    pol = col(ctx, "macro/policy_rate.csv", "policy_avg")
    bad = col(ctx, "macro/policy_rate.csv", "badlar_avg")
    line(ctx, ax, bad, p.FAINT, label="BADLAR, private banks (proxy, "
                                      "not a policy rate)", lw=1.6, ms=2.6)
    line(ctx, ax, pol, p.NAVY, label="BCRA policy rate, annual average")
    line(ctx, ax, ipc, p.RED, label="inflation, INDEC (Dec/Dec)", lw=1.8)
    line(ctx, ax, alt, p.ASTERISK, label="inflation, IPC San Luis", lw=1.8)
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper left", extra=key(ctx, True))
    note(ctx, ax, 0.02, 0.38,
         "No single policy rate existed before December\n"
         "2015, and none after July 2025.")

    ax = ig.slot("markets.bond_10y", "Government bond yield, US$ debt")
    ust = col(ctx, "markets/us_treasury_10y.csv", "avg")
    embi = col(ctx, "markets/country_risk.csv", "avg_bp")
    usd = {y: ust[y] + embi[y] / 100 for y in ust if y in embi}
    line(ctx, ax, usd, p.CELESTE_D, label="US 10-year Treasury + EMBI+ "
                                          "Argentina spread")
    line(ctx, ax, ust, p.FAINT, label="US 10-year Treasury", lw=1.6, ms=2.6,
         ls=(0, (3, 2)))
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper left")
    py, pv = peak(full(ctx, usd))
    note(ctx, ax, 0.02, 0.84,
         f"No peso 10-year benchmark exists. The gap\n"
         f"between the lines is country risk: {embi[py]:,.0f}bp\n"
         f"on average in {py}.")

    ax = ig.slot("markets.currency", "Peso against the US$ (official)")
    fx = col(ctx, "macro/dollar.csv", "official_avg")
    idx = dict(zip(*ctx.fx_index(fx)))
    line(ctx, ax, idx, p.NAVY, label="official rate, annual average")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="lower left")
    last = ctx.LAST_FULL_YEAR
    note(ctx, ax, 0.98, 0.97,
         f"{fx[FIRST]:.2f} pesos per dollar in {FIRST}, "
         f"{fx[last]:,.0f} in {last}:\n"
         f"the peso buys {idx[last]:.2f}% of the dollars it did.\n"
         f"The parallel rate is on the prices plate.", ha="right")

    ax = ig.slot("markets.equities", "Merval in US$ against the S&P 500")
    merval = col(ctx, "markets/merval.csv", "close")
    eop = col(ctx, "macro/dollar.csv", "official_eop")
    musd = {y: merval[y] / eop[y] for y in merval if y in eop}
    mi = dict(zip(*ctx.index_2006(musd)))
    si = dict(zip(*ctx.index_2006(col(ctx, "markets/sp500.csv", "close"))))
    line(ctx, ax, si, p.MUTED, label="S&P 500", ls=(0, (5, 2)), lw=1.8)
    line(ctx, ax, mi, p.CELESTE, label="Merval, at the official year-end rate")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper left")
    note(ctx, ax, 0.98, 0.04,
         "Year-end closes from a vendor (Yahoo): BYMA publishes\n"
         "no open history. Neither is an official statistic.",
         ha="right", va="bottom")


# ========================================================= 08 demography
def plate_people(ctx, ig) -> None:
    p = ctx.p
    pop = population(ctx)
    births = col(ctx, "social/vitals.csv", "births")
    deaths = col(ctx, "social/vitals.csv", "deaths")
    natural = col(ctx, "social/vitals.csv", "natural_growth")
    intl = "social/demography_intl.csv"

    ax = ig.slot("demography.population", "Population")
    ind = dict(zip(*ctx.index_2006(pop)))
    wpop = col(ctx, intl, "population")
    wi = dict(zip(*ctx.index_2006(wpop)))
    line(ctx, ax, wi, p.FAINT, label="UN WPP via the World Bank", lw=1.6,
         ms=2.6)
    line(ctx, ax, ind, p.NAVY, label="INDEC projection")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper left", extra=key(ctx))
    last = max(pop)
    note(ctx, ax, 0.98, 0.04,
         f"{pop[FIRST] / 1e6:.1f} million in {FIRST}, "
         f"{pop[last] / 1e6:.1f} million in {last}.", ha="right",
         va="bottom")

    ax = ig.slot("demography.fertility", "Total fertility rate")
    tfr = col(ctx, intl, "fertility")
    line(ctx, ax, tfr, p.PURPLE, label="World Bank / UN WPP")
    ax.axhline(2.1, color=p.muted, lw=0.9, ls=(0, (4, 3)), zorder=2)
    ax.text(FIRST, 2.15, "replacement, 2.1", fontsize=7.8, color=p.muted,
            va="bottom")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="lower left")
    last = max(tfr)
    note(ctx, ax, 0.98, 0.97,
         f"{tfr[FIRST]:.2f} children per woman in {FIRST},\n"
         f"{tfr[last]:.2f} in {last}.", ha="right")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates")
    cbr = dict(zip(*ctx.per_1000(births, pop)))
    cdr = dict(zip(*ctx.per_1000(deaths, pop)))
    line(ctx, ax, cbr, p.CELESTE, label="births (DEIS)")
    line(ctx, ax, cdr, p.NAVY, label="deaths (DEIS)")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper right")
    by, bv = peak(births)
    last = max(births)
    note(ctx, ax, 0.02, 0.04,
         f"Registered births: {bv:,.0f} in {by}, {births[last]:,.0f}\n"
         f"in {last}, down {(1 - births[last] / bv) * 100:.1f}%.",
         va="bottom")

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net migration")
    nat = dict(zip(*ctx.per_1000(natural, pop)))
    bars(ctx, ax, nat, p.GREEN)
    mig = col(ctx, intl, "net_migration")
    mr = dict(zip(*ctx.per_1000(mig, wpop)))
    line(ctx, ax, mr, p.SUN, label="net migration, UN WPP estimate")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper right", extra=[
        Patch(color=p.GREEN, label="natural increase, DEIS (bars)")])
    last = max(natural)
    ny, nv = peak(natural)
    note(ctx, ax, 0.02, 0.97,
         f"{nv:,.0f} more births than deaths in {ny},\n"
         f"{natural[last]:,.0f} in {last}.")


# ========================================================== 09 security
def plate_violence(ctx, ig) -> None:
    p = ctx.p
    pop = population(ctx)
    intl = "social/security_intl.csv"
    causes = "social/causes.csv"

    ax = ig.slot("security.homicide", "Homicide rate")
    snic = col(ctx, "social/homicides.csv", "rate")
    unodc = col(ctx, intl, "homicide_per_100k")
    line(ctx, ax, unodc, p.FAINT, label="UNODC", lw=1.6, ms=2.6)
    line(ctx, ax, snic, p.NAVY, label="SNIC, Ministerio de Seguridad")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="lower left", extra=key(ctx))
    hy, hv = peak(snic)
    last = max(snic)
    count = col(ctx, "social/homicides.csv", "count")
    note(ctx, ax, 0.98, 0.97,
         f"{hv:.2f} in {hy}, {snic[last]:.2f} in {last}:\n"
         f"{count[hy]:,.0f} victims, then {count[last]:,.0f}.", ha="right")

    ax = ig.slot("security.suicide", "Suicide rate")
    sui = dict(zip(*ctx.per_100k(col(ctx, causes, "suicide"), pop)))
    who = col(ctx, intl, "suicide_per_100k")
    line(ctx, ax, who, p.FAINT, label="WHO, age-standardised estimate",
         lw=1.6, ms=2.6)
    line(ctx, ax, sui, p.PURPLE, label="DEIS deaths X60–X84, crude")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper right")
    last = max(sui)
    note(ctx, ax, 0.02, 0.97,
         f"Registered deaths over INDEC's population:\n"
         f"{sui[last]:.1f} per 100,000 in {last}.")

    ax = ig.slot("security.road_deaths", "Road traffic deaths")
    road = dict(zip(*ctx.per_100k(col(ctx, causes, "transport"), pop)))
    who = col(ctx, intl, "road_deaths_per_100k")
    line(ctx, ax, who, p.FAINT, label="WHO estimate, road traffic", lw=1.6,
         ms=2.6)
    line(ctx, ax, road, p.SUN, label="DEIS deaths V01–V89, all land transport")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper right")
    note(ctx, ax, 0.02, 0.04,
         "The register codes many crash deaths as undetermined;\n"
         "WHO models them back in. The two do not measure alike.",
         va="bottom")

    ax = ig.slot("security.lens", "Lens: direct femicide victims, per "
                                  "100,000 women")
    fem = col(ctx, "social/femicides.csv", "rate_per_100k_women")
    line(ctx, ax, fem, p.PURPLE, label="Registro Nacional de Femicidios (CSJN)",
         lw=2.6)
    finish(ig, ax, ctx)
    ax.set_ylim(0, max(fem.values()) * 1.6)
    ax.axvline(2017, color=p.faint, lw=1.0, ls=(0, (4, 3)), zorder=1)
    ax.text(2017.15, 0.04, "method changed, 2017", fontsize=7.8,
            color=p.muted, transform=ax.get_xaxis_transform(), va="bottom")
    legend(ctx, ax, loc="upper left")
    d = col(ctx, "social/femicides.csv", "direct_victims")
    k = col(ctx, "social/femicides.csv", "linked_victims")
    counted = ", ".join(f"{y}: {d[y]:,.0f}" + (f" + {k[y]:,.0f} linked"
                                              if y in k else "")
                        for y in sorted(d))
    note(ctx, ax, 0.98, 0.97,
         "Rates either side of 2017 are not strictly comparable.\n"
         f"Victims counted, where a report states them —\n{counted}.",
         ha="right")


# ========================================================== 10 spending
SOCIAL = ("prevision", "asistencia", "asignaciones")
COFOG = (  # national functions mapped onto the spine's seven groups
    ("social protection", SOCIAL),
    ("health", ("salud", "salud_obras", "salud_inssjp")),
    ("education", ("educacion_basica", "educacion_superior")),
    ("general public services", ("funcionamiento", "deuda")),
    ("economic affairs", ("energia", "transporte")),
    ("defence and public order", ("defensa_seguridad",)),
)
# The seventh group, "other", is what the published total holds beyond the
# thirteen functions the gateway itemises: total minus their sum, never
# negative in this file (0.1 to 1.8 points of GDP).


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    sp = ds.load("fiscal/spending_by_function.csv")
    years = sorted(y for y in sp["total"] if FIRST <= y <= LAST)
    colours = (p.NAVY, p.TEAL, p.CELESTE, p.MUTED, p.SUN, p.PURPLE)
    listed = [k for _, keys in COFOG for k in keys]
    other = {y: sp["total"][y] - sum(sp[k][y] for k in listed) for y in years}

    ax = ig.slot("spending.by_function", "Spending by function, stacked")
    bottom = {y: 0.0 for y in years}
    for (label, keys), colour in zip(COFOG, colours):
        for y in years:
            v = sum(sp[k][y] for k in keys)
            ax.bar(y, v, bottom=bottom[y], width=0.78, color=colour,
                   label=label if y == years[0] else "_nolegend_",
                   edgecolor="white", linewidth=0.4, zorder=3)
            bottom[y] += v
    for y in years:
        ax.bar(y, other[y], bottom=bottom[y], width=0.78, color=p.FAINT,
               label="other" if y == years[0] else "_nolegend_",
               edgecolor="white", linewidth=0.4, zorder=3)
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper left", ncol=2, extra=key(ctx, True))
    last = max(years)
    note(ctx, ax, 0.98, 0.60,
         f"National government only (provinces run schools and\n"
         f"hospitals). Functions mapped onto COFOG groups.\n"
         f"Series ends {last}: {sp['total'][last]:.1f}% of GDP.",
         ha="right")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else")
    soc = {y: sum(sp[k][y] for k in SOCIAL) for y in years}
    rest = {y: sp["total"][y] - soc[y] for y in years}
    line(ctx, ax, soc, p.NAVY, label="social protection: pensions and "
                                     "transfers")
    line(ctx, ax, rest, p.MUTED, label="everything else")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper left")
    py, pv = peak(sp["prevision"])
    note(ctx, ax, 0.98, 0.97,
         f"Pensions alone: {sp['prevision'][FIRST]:.1f}% of GDP in "
         f"{FIRST},\n{pv:.1f}% at the {py} peak.", ha="right")

    ax = ig.slot("spending.investment", "Investment rate, whole economy")
    gfcf = col(ctx, "macro/economy_intl.csv", "gfcf_pct_gdp")
    line(ctx, ax, gfcf, p.CELESTE_D, label="gross fixed capital formation "
                                           "(World Bank)")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper right")
    hy, hv = peak(gfcf)
    ly, lv = trough(gfcf)
    note(ctx, ax, 0.02, 0.06,
         f"{hv:.1f}% of GDP in {hy}, {lv:.1f}% in {ly}.", va="bottom")

    ax = ig.slot("spending.public_investment", "Public investment")
    inv = ds.load("fiscal/public_investment.csv")
    for k, lab in (("m1993", "1993 method"), ("m2007", "2007 method"),
                   ("m2017", "2015 method")):
        seg = {y: v for y, v in inv[k].items() if FIRST <= y <= LAST}
        line(ctx, ax, seg, p.TEAL if k == "m2017" else p.ASTERISK,
             label=f"national public sector, {lab}")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper right")
    m17 = inv["m2017"]
    last = max(y for y in m17 if y <= LAST)
    note(ctx, ax, 0.02, 0.97,
         f"Direct investment by the nation only, not the\n"
         f"provinces. {m17[last]:.2f}% of GDP in {last}.")


# ============================================================= 11 world
def plate_world(ctx, ig) -> None:
    p = ctx.p
    w = "macro/world.csv"

    ax = ig.slot("world.gdp", "GDP at current prices")
    gdp = col(ctx, w, "gdp_usd_bn")
    line(ctx, ax, gdp, p.NAVY, label="World Bank, at the official rate")
    finish(ig, ax, ctx, intervened=True)
    legend(ctx, ax, loc="upper left", extra=key(ctx, True))
    last = max(gdp)
    note(ctx, ax, 0.98, 0.04,
         f"US${gdp[last]:,.0f}bn in {last}.", ha="right", va="bottom")

    ax = ig.slot("world.hdi", "Human Development Index")
    hdi = col(ctx, "social/hdi.csv", "undp")
    line(ctx, ax, hdi, p.GREEN, label="UNDP")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="lower right")
    last = max(hdi)
    note(ctx, ax, 0.02, 0.97,
         f"{hdi[FIRST]:.3f} in {FIRST}, {hdi[last]:.3f} in {last}.\n"
         f"0.800 and above is \"very high\".")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index")
    cpi = col(ctx, "social/corruption.csv", "score")
    line(ctx, ax, cpi, p.PURPLE, label="Transparency International, "
                                       "2012 method")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper left")
    rank = col(ctx, "social/corruption.csv", "rank")
    hy, hv = peak(cpi)
    last = max(cpi)
    note(ctx, ax, 0.98, 0.04,
         f"Higher is cleaner. {hv:.0f} in {hy}, {cpi[last]:.0f} in {last}\n"
         f"(rank {rank[last]:.0f}). Scores before 2012 are on another\n"
         f"scale and method, and are not drawn.", ha="right", va="bottom")

    ax = ig.slot("world.reserves", "Official reserves")
    wb = col(ctx, w, "reserves_usd_bn")
    bcra = col(ctx, "macro/reserves.csv", "eop_usbi")
    line(ctx, ax, bcra, p.FAINT, label="BCRA gross reserves, year end",
         lw=1.6, ms=2.6)
    line(ctx, ax, wb, p.TEAL, label="World Bank, total incl. gold")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="lower left")
    ty, tv = trough(wb)
    note(ctx, ax, 0.98, 0.04,
         f"Low of US${tv:.1f}bn in {ty}. Gross: the BCRA's\n"
         f"own swap and repo debts are not netted out.",
         ha="right", va="bottom")


# ========================================================== 12 mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    pop = population(ctx)
    c = "social/causes.csv"
    deaths = col(ctx, c, "deaths_total")

    ax = ig.slot("mortality.death_rate", "Crude death rate")
    cdr = dict(zip(*ctx.per_1000(deaths, pop)))
    line(ctx, ax, cdr, p.NAVY, label="DEIS deaths over INDEC population")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="lower left", extra=key(ctx))
    hy, hv = peak(cdr)
    note(ctx, ax, 0.98, 0.04,
         f"{hv:.2f} per 1,000 in {hy}: {deaths[hy]:,.0f} deaths.",
         ha="right", va="bottom")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths")
    base = sum(deaths[y] for y in range(2015, 2020)) / 5
    exc = {y: (deaths[y] / base - 1) * 100 for y in deaths if y >= 2015}
    bars(ctx, ax, exc, signed(ctx))
    finish(ig, ax, ctx)
    hy, hv = peak(exc)
    note(ctx, ax, 0.02, 0.97,
         f"All registered deaths against their 2015–19 mean,\n"
         f"{base:,.0f}. Not adjusted for an older population.\n"
         f"{hy}: {hv:+.1f}%.")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause")
    cov = {y: v for y, v in col(ctx, c, "covid").items() if y >= 2020}
    rate = dict(zip(*ctx.per_100k(cov, pop)))
    bars(ctx, ax, rate, p.RED)
    finish(ig, ax, ctx)
    ax.legend(handles=[Patch(color=p.RED,
                             label="ICD-10 U07, confirmed and probable")],
              loc="upper left", frameon=False, fontsize=8.4,
              labelcolor=p.muted)
    total = sum(cov.values())
    note(ctx, ax, 0.98, 0.97,
         f"{total:,.0f} deaths in all, {min(cov)}–{max(cov)}. The\n"
         f"published file truncates the code, so confirmed\n"
         f"and probable cannot be told apart.", ha="right")

    ax = ig.slot("mortality.lens", "Lens: pneumonia and influenza")
    pn = dict(zip(*ctx.per_100k(col(ctx, c, "pneumonia"), pop)))
    fl = dict(zip(*ctx.per_100k(col(ctx, c, "influenza"), pop)))
    line(ctx, ax, pn, p.NAVY, label="pneumonia, J12–J18")
    line(ctx, ax, fl, p.SUN, label="influenza, J09–J11")
    finish(ig, ax, ctx)
    ig.headroom(ax, top=0.35)
    legend(ctx, ax, loc="upper left")
    flu = col(ctx, c, "influenza")
    fy, fv = peak(flu)
    note(ctx, ax, 0.98, 0.30,
         f"Influenza is barely coded: {fv:,.0f} deaths in {fy}\n"
         f"(H1N1) is its highest. A fatal flu is certified\n"
         f"as the pneumonia it became.", ha="right")


# ========================================================== 13 migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    ax = ig.slot("migration.flows",
                 "Resident immigration and emigration — not verified")
    ctx.pending(ax)
    finish(ig, ax, ctx)
    note(ctx, ax, 0.50, 0.34,
         "DNM movements count trips; residence grants count decisions.\n"
         "Neither is a comparable resident-flow pair.", ha="center")
    ax = ig.slot("migration.net", "Net migration — UN WPP estimate")
    t = ctx.table("social/demography_intl.csv")
    counts = {int(y): float(v)
              for y, v in zip(t["year"], t["net_migration"]) if v == v}
    pop = {int(y): float(v)
           for y, v in zip(t["year"], t["population"]) if v == v}
    net = dict(zip(*ctx.per_1000(counts, pop)))
    line(ctx, ax, net, p.CELESTE_D, label="UN WPP, modelled")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper left")
    ax = ig.slot("migration.foreign_born", "Foreign-born share — census")
    stock = col(ctx, "migration/foreign_born_census.csv", "foreign_born_pct")
    line(ctx, ax, stock, p.CELESTE_D, label="INDEC, private dwellings")
    finish(ig, ax, ctx)
    legend(ctx, ax, loc="upper left")
    for y, value in stock.items():
        ax.text(y, value, f"{value:.1f}%", ha="center", va="bottom",
                fontsize=8.4, fontweight="bold", color=p.CELESTE_D)
    note(ctx, ax, 0.98, 0.97,
         "Country of birth, not citizenship. Census snapshots only.",
         ha="right")
    ax = ig.slot("migration.lens", "Lens: largest countries of birth, 2022")
    t = ctx.table("migration/origins_census_2022.csv")
    names = list(t["origin"])
    values = [float(v) / 1000 for v in t["count"]]
    ax.bar(names, values, color=[p.CELESTE_D, p.SUN, p.PURPLE], width=0.62)
    ax.set_ylabel("thousand residents", fontsize=8.6, color=p.muted)
    for i, value in enumerate(values):
        ax.text(i, value, f"{value:,.0f}k", ha="center", va="bottom",
                fontsize=8.5, fontweight="bold", color=p.ink)
    ig.style_axis(ax)
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.set_xticks(range(len(names)), names)


# ============================================================== registry
# The plates, in page order. `alt` is what a screen-reader user gets
# instead of the figure, so it states what the panels show.
SRC_GDP = ("Sources: INDEC (national accounts, CPI, EPH); World Bank; "
           "IPC San Luis")
PLATES = [
    dict(id="01", slug="output", topic="economy", builder=plate_output,
         title="Twenty years of Argentine output",
         subtitle="Growth, income per head, inflation and unemployment, "
                  "2006–2026",
         source="Sources: INDEC, national accounts (base 2004), IPC and EPH; "
                "DPEyC San Luis; World Bank WDI",
         alt="Four panels on the Argentine economy, 2006 to 2026. Real GDP "
             "growth swings between -9.9% in 2020 and +10.4% in 2021, and "
             "output fell in nine of the twenty years. GDP per person in "
             "current dollars, on a log scale, peaks at US$14,898 in 2025 "
             "after a trough of US$8,536 in 2020. Consumer price inflation "
             "runs at 18% to 39% a year on the San Luis provincial index "
             "while the national index was intervened, then 25% to 211% on "
             "INDEC's restored index, peaking in 2023, before 31.5% in "
             "2025. Urban unemployment falls from 10.1% to 6.1% in 2023, "
             "after peaking at 11.5% in 2020."),
    dict(id="02", slug="prices", topic="prices", builder=plate_prices,
         title="Prices, the peso and the two dollars",
         subtitle="Inflation, the official and parallel dollar, the gap and "
                  "reserves",
         source="Sources: INDEC (national CPI, from Dec 2016); DPEyC San "
                "Luis (2007–2016); BCRA; parallel rate via Ámbito Financiero",
         alt="Four panels on Argentine prices. Annual inflation on a log "
             "scale in two colours, because no usable national index exists "
             "for 2007 to 2016: the provincial San Luis index stands in at "
             "18% to 39% a year. The national index peaks at 211% in 2023 "
             "and falls to 31.5% in 2025. The peso goes from 3.06 to the "
             "dollar at the end of 2006 to 1,447 at the end of 2025, drawn "
             "against the parallel blue rate. The gap between the two "
             "reaches 104% in 2021, under the second cepo. Gross reserves "
             "fall to US$21.9 billion in 2023 from US$57 billion in 2018."),
    dict(id="03", slug="living", topic="people", builder=plate_living,
         title="Work, wages and who is poor",
         subtitle="Inequality, poverty and the minimum wage",
         source="Sources: INDEC, Encuesta Permanente de Hogares; Ministerio "
                "de Trabajo (SMVM); World Bank PIP",
         alt="Four panels on Argentine living standards, all from the urban "
             "household survey. The Gini coefficient, times 100, falls from "
             "48.1 in 2006 to 41.5 in 2015 and is 42.9 in 2025. Poverty on "
             "the national basket averages 45.5% in 2024 against 15.2% "
             "below the World Bank's US$8.30 a day line; the official series "
             "was withdrawn for 2007 to 2015. The minimum wage at the "
             "official rate peaks at US$603 in 2015 and is US$269 in 2025. "
             "Half by half, poverty reaches 52.9% in the first half of 2024, "
             "after the December 2023 devaluation, and 38.1% in the second."),
    dict(id="04", slug="state", topic="fiscal", builder=plate_state,
         title="What the state takes and what it spends",
         subtitle="General government revenue, balance, debt and interest",
         source="Sources: IMF, World Economic Outlook and Fiscal Monitor; "
                "Secretaría de Hacienda, Esquema AIF and recursos tributarios",
         alt="Four panels on Argentine public finances. General government "
             "revenue rises from 28% to 35% of GDP by 2015 while spending "
             "rises from 27% to 41.5% in 2016 and 42.5% in 2020, and both "
             "fall to about 31% in 2024-25. The overall balance is in deficit every year from "
             "2009 to 2023, reaching -8.7% of GDP in 2020, and the primary "
             "balance turns to a surplus of 2.2% in 2024; the national "
             "public sector's own primary result is drawn beside it in "
             "three unjoined methodologies. Gross debt runs from 39% of GDP "
             "in 2011 to 153% in 2023, then 80% in 2025. Net interest peaks "
             "at 4.0% of GDP in 2019."),
    dict(id="05", slug="trade", topic="trade", builder=plate_trade,
         title="What Argentina sells to the world",
         subtitle="Exports, imports, destinations and what is sold",
         source="Sources: World Bank WDI (national accounts); INDEC, "
                "Intercambio Comercial Argentino; UN Comtrade",
         alt="Four panels on Argentine trade. Exports of goods and services "
             "fall from 23% of GDP in 2006 to 10.7% in 2015 and are 15.6% in "
             "2025; imports move from 17% to 15%. The balance is negative "
             "in 2013, 2015 to 2018 and 2023. Brazil takes 14.3% to 21.2% "
             "of goods exports, China, the United States and Chile 4% to "
             "11% each. Exports by category are stacked in dollars: primary "
             "products, agricultural and industrial manufactures, and fuel, "
             "whose share falls to 3.5% in 2016 and rises to 12.7% in 2025."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="A banking system that barely lends",
         subtitle="Household debt, what money costs and what goes bad",
         source="Sources: BIS total credit statistics; BCRA, "
                "api.bcra.gob.ar and Principales Indicadores del Sistema "
                "Financiero",
         alt="Four panels on Argentine credit. Household debt, all lenders, "
             "never exceeds 6.9% of GDP; mortgage lending falls from 1.56% "
             "of GDP in 2007 to 0.28% in 2024. The nominal personal-loan "
             "rate runs between 29% and 102% a year against a policy rate "
             "that exists only from 2016 to mid-2025. Non-performing private "
             "loans jump from 1.54% in 2024 to 5.54% in 2025. Real deposit "
             "rates are negative every year from 2017 to 2024, reaching "
             "-37.1% in 2023, and real borrowing costs pass 30% in 2025."),
    dict(id="07", slug="markets", topic="markets", builder=plate_markets,
         title="What the market charged Argentina",
         subtitle="The policy rate, the price of dollar debt, the peso and "
                  "the Merval",
         source="Sources: BCRA; US Treasury; J.P. Morgan EMBI+ via Ámbito "
                "Financiero; Merval and S&P 500 closes via Yahoo Finance "
                "(market references, not official statistics)",
         alt="Four panels on Argentine markets. The BCRA's policy rate, which "
             "exists only from December 2015 to July 2025, averages 26% to "
             "100% a year against inflation of 25% to 211%, with the BADLAR "
             "deposit rate drawn across the whole window as a proxy. The "
             "yield on Argentine dollar debt, the US 10-year Treasury plus "
             "the EMBI+ spread, reaches 26% on average in 2023. The official "
             "peso, as an index of 2006 = 100, falls to 0.25 in 2025, a "
             "currency that buys a four-hundredth of the dollars it did. The "
             "Merval in dollars ends 2025 about three times its 2006 level, "
             "the S&P 500 nearly five times."),
    dict(id="08", slug="people", topic="demography", builder=plate_people,
         title="Fewer births, a population still growing",
         subtitle="Population, fertility, birth and death rates",
         source="Sources: Ministerio de Salud, DEIS (births and deaths); "
                "INDEC (population); World Bank / UN World Population "
                "Prospects",
         alt="Four panels on Argentine demography. The population grows from "
             "39.1 million in 2006 to 46.4 million in 2025, 18.6% more. "
             "Fertility falls from 2.40 children per woman to 1.50 in 2024, "
             "well under the 2.1 replacement line. The crude birth rate "
             "falls from 18 per 1,000 to 8.9 in 2024 while the death rate "
             "rises from 7.5 to 8.1, with a COVID-19 peak of 9.5 in 2021. "
             "Natural increase falls from 451,473 more births than deaths in "
             "2014 to 36,730 in 2024; net migration is close to zero."),
    dict(id="09", slug="violence", topic="security", builder=plate_violence,
         title="Homicide, suicide, the roads and femicide",
         subtitle="Lethal violence and accidents, per 100,000 people",
         source="Sources: Ministerio de Seguridad, SNIC; Ministerio de "
                "Salud, DEIS; UNODC and WHO via the World Bank; CSJN, "
                "Registro Nacional de Femicidios",
         alt="Four panels on lethal violence in Argentina, per 100,000 "
             "people. The homicide rate peaks at 7.62 in 2014 and falls to "
             "3.61 in 2025, on a log scale beside UNODC's series. Registered "
             "suicides run at 6.3 to 8.0 per 100,000, below WHO's "
             "age-standardised estimate. Registered land-transport deaths "
             "fall from 13.1 in 2013 to 5.2 in 2020, well under WHO's road "
             "estimate of 13 to 15. The direct femicide rate per 100,000 "
             "women is near 1.0 to 1.14 until 2023 and falls to 0.85 in "
             "2025, with a method change marked at 2017."),
    dict(id="10", slug="spending", topic="spending", builder=plate_spending,
         title="Where the national budget goes",
         subtitle="Spending by function, social protection, investment",
         source="Sources: Secretaría de Política Económica, Gasto Público "
                "Nacional por finalidad; Secretaría de Hacienda, Esquema AIF; "
                "World Bank WDI",
         alt="Four panels on Argentine spending. National government spending "
             "by function, grouped like COFOG, rises from 14.5% of GDP in "
             "2006 to 27.5% in 2020 and is 22.3% in 2023, when the series "
             "ends. Social protection, pensions and transfers, goes from 5.2% "
             "to 12.8% of GDP in 2020. Whole-economy investment runs between "
             "14.2% and 19.5% of GDP. Direct investment by the national "
             "public sector peaks at 1.24% of GDP in 2009 and falls to 0.27% "
             "in 2025, in three methodologies drawn apart."),
    dict(id="11", slug="world", topic="world", builder=plate_world,
         title="Argentina among the others",
         subtitle="Dollar GDP, human development, corruption perceptions, "
                  "reserves",
         source="Sources: World Bank WDI; UNDP Human Development Report; "
                "Transparency International; BCRA",
         alt="Four panels placing Argentina among other countries. GDP at "
             "current prices rises from US$233 billion in 2006 to US$683 "
             "billion in 2025, on a log scale. The Human Development Index "
             "rises from 0.822 to 0.865 in 2023, in the very high band "
             "throughout. Transparency International's corruption score "
             "peaks at 45 in 2019 and is 36 in 2025, rank 104. Total "
             "reserves fall to a low of US$23.1 billion in 2023, drawn "
             "beside the BCRA's gross figure."),
    dict(id="12", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="One bad year of deaths",
         subtitle="Death rate, excess deaths, COVID-19, pneumonia",
         source="Sources: Ministerio de Salud, DEIS, defunciones por causa "
                "(CIE-10); INDEC (population)",
         alt="Four panels on Argentine mortality. The crude death rate runs "
             "near 7.5 per 1,000 people and peaks at 9.5 in 2021, 436,799 "
             "deaths. Against the 2015-2019 average of 341,328, deaths were "
             "10.2% higher in 2020 and 28.0% higher in 2021. COVID-19 deaths "
             "are 117 per 100,000 in 2020 and 185 in 2021, 164,785 in all, "
             "confirmed and probable together. Pneumonia kills 40 to 87 "
             "per 100,000 a year; influenza barely appears, because a fatal "
             "flu is certified as pneumonia."),
    dict(id="13", slug="migration", topic="migration", builder=plate_migration,
         title="Migration on the definitions that survive scrutiny",
         subtitle="Modelled net movement, census birthplace and origins",
         source="Sources: INDEC, Censo 2022; UN World Population Prospects via World Bank WDI",
         alt="Gross resident immigration and emigration remain visibly pending because DNM movements count trips and residence grants count administrative decisions, not changes of usual residence. UN WPP supplies modelled net migration per 1,000. INDEC census snapshots show 4.5% foreign-born in 2010 and 4.2% in 2022; Paraguay, Bolivia and Venezuela are the origins shown."),
]
