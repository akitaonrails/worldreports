"""The spain plates, on the plate spine.

Each builder draws one plate from this country's committed CSVs, and each
plate declares its spine topic and claims its four panels by slot key in
spine order (PLATE_SPINE.md, core/spine.py). The canonical slots carry the
same indicator in the same unit as every other country, on the reference
scale the spine applies at save time, so the comparison viewer can wipe
Spain over France and the reader sees only the difference. The fourth slot
of trade, credit, people, security, mortality and migration is Spain's own
lens.

The migration plate is the atlas's reference treatment of a definitional
seam: Eurostat's flow series changes methodology at 2021 (EM → EMCR), the
INE publishes 2021 on both, and the plate draws the two segments apart and
says what the jump is rather than joining them. See DATA_NOTES.md.

Rates. Every count drawn as a rate is divided by the population of the
same year from the same source: INE's Estadística Continua de Población at
1 July (social/population.csv, population_jul), the mid-year population
INE uses for its own crude rates. The 1 January level is quoted only as a
level. ctx.per_100k and ctx.per_1000 match the two series by year.

Every number in a note is read from the CSVs at draw time.
"""
from __future__ import annotations

from core.sideload import sibling

events = sibling(__file__, "events")
MARKS = events.MARKS


# ------------------------------------------------------------ small helpers
def _yr(ctx, rel: str, col: str, since: int = 0):
    """(years, values) from a calendar-year CSV, blanks dropped."""
    t = ctx.table(rel)
    if not t or col not in t:
        return [], []
    yrs, vals = ctx.series(t, col)
    keep = [(y, v) for y, v in zip(yrs, vals) if y >= since and v == v]
    return [y for y, _ in keep], [v for _, v in keep]


def _d(ctx, rel: str, col: str) -> dict[int, float]:
    """{year: value} from a calendar-year CSV, blanks dropped."""
    return dict(zip(*_yr(ctx, rel, col)))


def _long(ctx, rel: str, key: str, name: str, col: str = "share_pct"):
    """(years, values) for one category of a long-format CSV."""
    t = ctx.table(rel)
    out = sorted((int(y), float(v)) for y, k, v in zip(t["year"], t[key],
                                                       t[col])
                 if k == name and v == v)
    return [y for y, _ in out], [v for _, v in out]


def _cause(ctx, name: str) -> dict[int, float]:
    """{year: deaths} for one cause out of the long-format ECM file."""
    t = ctx.table("social/causes_of_death.csv")
    return {int(y): float(v) for y, c, v in zip(t["year"], t["cause"],
                                               t["deaths"])
            if c == name and v == v}


def _midyear(ctx) -> dict[int, float]:
    """The 1 July resident population: the denominator of every rate."""
    return _d(ctx, "social/population.csv", "population_jul")


def _bands(ig, ax, first: bool = False, y: float = 0.965,
           va: str = "top", color=None) -> None:
    """The downturn bands; captioned only on a plate's first panel.

    The captions are written inside the panel at a height the caller
    picks, where that panel's data leave room. Above the axes they would
    share a row with the panel title.
    """
    ig.add_recessions(ax, label=False)
    if not first:
        return
    for start, end, name in ig.country.recessions:
        ax.text((start + end) / 2, y, name, transform=ax.get_xaxis_transform(),
                ha="center", va=va, fontsize=7.4, style="italic",
                color=color or ig.p.muted)


def _note(ctx, ax, x: float, y: float, text: str, ha: str = "left",
          va: str = "top", color=None, size: float = 7.9) -> None:
    """A short italic note, placed in axes fractions."""
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va, fontsize=size,
            color=color or ctx.p.MUTED, style="italic")


def _foot(ctx, ax, text: str) -> None:
    """A source or method line under the panel."""
    ax.text(0.5, -0.095, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.2, color=ctx.p.FAINT, style="italic")


def _peak(pairs):
    return max(pairs, key=lambda t: t[1])


def _low(pairs):
    return min(pairs, key=lambda t: t[1])


# ------------------------------------------------------------------ economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, "macro/gdp.csv", "real_growth")
    _bands(ig, ax, first=True)
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.ROJO)
    for y, v in zip(gy, gv):
        if v < -2 or v > 5.4 or y == gy[-1]:
            if y == 2020:   # no room under the bar: write it beside
                ax.annotate(f"{v:+.1f}", (y, v), textcoords="offset points",
                            xytext=(12, 4), ha="left", va="center",
                            fontsize=8.6, fontweight="bold", color=p.ROJO)
                continue
            ax.annotate(f"{v:+.1f}", (y, v), textcoords="offset points",
                        xytext=(0, 4 if v >= 0 else -5), ha="center",
                        va="bottom" if v >= 0 else "top", fontsize=8.6,
                        fontweight="bold",
                        color=p.GREEN_D if v >= 0 else p.ROJO)
    _note(ctx, ax, 0.015, 0.20, "2020: the deepest fall in the G20 —\n"
          "an economy that leans on tourism")

    ax = ig.slot("economy.gdp_per_person",
                 "GDP per person (US$, current — World Bank)")
    cy, cv = _yr(ctx, "macro/gdp.csv", "gdp_per_capita_usd")
    _bands(ig, ax)
    ctx.line(ax, cy, cv, p.BLUE)
    ctx.endlabel(ax, cy, cv, p.BLUE, lambda v: f"US$ {v:,.0f}", dy=10)
    ig.add_event(ax, 2015.0, "2015: the euro fell, the economy grew",
                 dy=0.36)
    _note(ctx, ax, 0.015, 0.20, "in current dollars: the dips are the "
          "exchange rate\nas much as the economy")

    ax = ig.slot("economy.inflation",
                 "Consumer prices (% per year) vs the ECB's 2% target")
    iy, iv = _yr(ctx, "macro/inflation.csv", "ipc")
    hy, hv = _yr(ctx, "macro/inflation.csv", "hicp")
    _bands(ig, ax)
    ax.axhline(2.0, color=p.BLUE, lw=1.2, ls="--", label="ECB target: 2%")
    ctx.line(ax, hy, hv, p.FAINT, lw=1.8, marker="", dashed_partial=False,
             label="Harmonised HICP (Eurostat)")
    ctx.line(ax, iy, iv, p.ROJO, label="Spanish IPC (INE)")
    pk = _peak(zip(iy, iv))
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(-8, 4), ha="right", va="bottom", fontsize=8.6,
                fontweight="bold", color=p.ROJO)
    ax.legend(loc="upper left", fontsize=8.2)
    _note(ctx, ax, 0.985, 0.97, "two baskets, never spliced; the IPC\nis "
          "INE's linked index, base 2025", ha="right")

    ax = ig.slot("economy.unemployment",
                 "Unemployment rate, 15–74 (% of labour force)")
    ey, ev = _yr(ctx, "macro/unemployment.csv", "epa")
    ly, lv = _yr(ctx, "macro/unemployment.csv", "estat")
    _bands(ig, ax)
    ctx.line(ax, ly, lv, p.FAINT, lw=1.8, marker="", dashed_partial=False,
             label="Eurostat LFS (no values before 2009)")
    ctx.line(ax, ey, ev, p.ROJO, label="EPA (INE), annual average")
    pk = _peak(zip(ey, ev))
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]} — one worker in four", pk,
                textcoords="offset points", xytext=(0, 8), ha="center",
                fontsize=8.6, fontweight="bold", color=p.ROJO)
    ax.legend(loc="lower right", fontsize=8.2)
    lower = max(y for y, v in zip(ey, ev) if y < ey[-1] and v <= ev[-1])
    since = min(y for y in ey if y > lower)
    _note(ctx, ax, 0.015, 0.20, f"{ev[-1]:.1f}% in {ey[-1]}: the lowest "
          f"since {since},\nand still above where it began")

    for a in ig.axes_flat:
        ig.style_axis(a)


# ------------------------------------------------------------------- fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("fiscal.revenue_expenditure",
                 "Revenue and expenditure, general government (% of GDP)")
    ry, rv = _yr(ctx, "fiscal/revenue.csv", "revenue")
    ey, ev = _yr(ctx, "fiscal/revenue.csv", "expenditure")
    _bands(ig, ax, first=True, y=0.05, va="bottom")
    ctx.line(ax, ey, ev, p.ROJO, label="Total expenditure")
    ctx.line(ax, ry, rv, p.NAVY, label="Total revenue")
    ax.fill_between(ry, rv, ev, color=p.ROJO, alpha=0.09, zorder=1)
    ax.legend(loc="upper right", fontsize=8.4, ncol=2)
    e20 = dict(zip(ey, ev))[2020]
    _note(ctx, ax, 0.015, 0.97, "the gap between the lines is the "
          f"deficit;\nspending reached {e20:.1f}% of GDP in 2020")

    ax = ig.slot("fiscal.balance",
                 "Net lending (+) or borrowing (−), and the primary balance "
                 "(% of GDP)")
    dy, dv = _yr(ctx, "fiscal/deficit.csv", "deficit")
    py, pv = _yr(ctx, "fiscal/deficit.csv", "primary")
    _bands(ig, ax)
    ax.axhline(-3.0, color=p.BLUE, lw=1.1, ls="--",
               label="Maastricht 3% limit")
    ctx.bars(ax, dy, dv, lambda v: p.GREEN if v >= 0 else p.ROJO)
    ctx.line(ax, py, pv, p.GUALDA, lw=1.8, marker="",
             label="primary balance (net of interest)")
    for y, v in zip(dy, dv):
        if y in (2006, 2009, 2012, 2020) or y == dy[-1]:
            ax.annotate(f"{v:+.1f}", (y, v), textcoords="offset points",
                        xytext=(0, 4 if v >= 0 else -4), ha="center",
                        va="bottom" if v >= 0 else "top", fontsize=8.4,
                        fontweight="bold",
                        color=p.GREEN_D if v >= 0 else p.ROJO)
    surplus = [y for y, v in zip(dy, dv) if v >= 0]
    _note(ctx, ax, 0.985, 0.97, "2012 includes the bank bailout;\n"
          f"the last surplus was {max(surplus)}", ha="right")
    ax.legend(loc="lower right", fontsize=8.0)

    ax = ig.slot("fiscal.debt", "Gross public debt, Maastricht (% of GDP)")
    gy, gv = _yr(ctx, "fiscal/debt.csv", "gross_pct_gdp")
    debt = dict(zip(gy, gv))
    _bands(ig, ax)
    ctx.line(ax, gy, gv, p.ROJO)
    ax.fill_between(gy, 0, gv, color=p.ROJO, alpha=0.07, zorder=1)
    ax.axhline(60.0, color=p.BLUE, lw=1.1, ls="--")
    ax.text(2026.3, 58, "Maastricht 60% limit", fontsize=8.0, color=p.BLUE,
            style="italic", va="top", ha="right")
    ctx.endlabel(ax, gy, gv, p.ROJO, lambda v: f"{v:.1f}%", dy=10)
    _note(ctx, ax, 0.015, 0.97, f"{debt[2011]:.1f}% to {debt[2013]:.1f}% in "
          "two years:\nthe bailout and the slump")
    _foot(ctx, ax, "consolidated, all levels of government — the Tesoro's "
          "state-only figure is a smaller number")

    ax = ig.slot("fiscal.interest", "Interest paid on the debt (% of GDP)")
    iy, iv = _yr(ctx, "fiscal/deficit.csv", "interest")
    _bands(ig, ax)
    ctx.line(ax, iy, iv, p.GUALDA)
    ctx.endlabel(ax, iy, iv, p.GUALDA, lambda v: f"{v:.1f}%", dy=10)
    pk = _peak(zip(iy, iv))
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=8.6, fontweight="bold",
                color=p.GUALDA)
    _note(ctx, ax, 0.015, 0.97, f"the debt went from {debt[2007]:.0f}% to "
          f"{debt[iy[-1]]:.0f}% of GDP;\nthe bill is lower than at its "
          f"{pk[0]} peak —\nrates fell faster than the debt grew")

    for a in ig.axes_flat:
        ig.style_axis(a)


# ----------------------------------------------------------------- spending
_COFOG = ["social_protection", "health", "general_services", "education",
          "economic_affairs", "defence_order", "other"]
_COFOG_LABEL = {"social_protection": "Social protection", "health": "Health",
                "general_services": "General services (incl. interest)",
                "education": "Education",
                "economic_affairs": "Economic affairs",
                "defence_order": "Defence & public order",
                "other": "Other functions"}


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    colors = {"social_protection": p.NAVY, "health": p.TEAL,
              "general_services": p.ROJO, "education": p.BLUE,
              "economic_affairs": p.GUALDA, "defence_order": p.PURPLE,
              "other": "#B9BDC7"}

    ax = ig.slot("spending.by_function",
                 "Public spending by function (% of GDP, COFOG)")
    spend = ctx.table("fiscal/spending_by_function.csv")
    yrs = [y for y, v in zip(spend["year"], spend["social_protection"])
           if v == v]
    stack = [[v for y, v in zip(spend["year"], spend[c]) if y in yrs]
             for c in _COFOG]
    _bands(ig, ax, first=True, y=0.035, va="bottom", color=p.paper)
    ax.stackplot(yrs, *stack, labels=[_COFOG_LABEL[c] for c in _COFOG],
                 colors=[colors[c] for c in _COFOG], alpha=0.92, lw=0,
                 zorder=2)
    ax.legend(loc="upper left", fontsize=7.3, ncol=4, columnspacing=0.9,
              handlelength=1.2, borderaxespad=0.3)

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    sy, sv = _yr(ctx, "fiscal/spending_by_function.csv", "social_protection")
    tot = _d(ctx, "fiscal/spending_by_function.csv", "total")
    rest = [tot[y] - s for y, s in zip(sy, sv)]
    _bands(ig, ax)
    ctx.line(ax, sy, rest, p.TEAL, label="All other functions")
    ax.fill_between(sy, 0, rest, color=p.TEAL, alpha=0.08)
    ctx.line(ax, sy, sv, p.NAVY, label="Social protection alone")
    ax.fill_between(sy, 0, sv, color=p.NAVY, alpha=0.10)
    ax.legend(loc="upper left", fontsize=8.4, ncol=2)
    sp = dict(zip(sy, sv))
    _note(ctx, ax, 0.985, 0.80, f"{sp[2006]:.1f}% in 2006, {sp[sy[-1]]:.1f}% "
          f"in {sy[-1]}: pensions are most of it;\nthe 2012–13 bulge is "
          "unemployment, 2020 the furloughs", ha="right")

    ax = ig.slot("spending.investment",
                 "Investment rate, whole economy (% of GDP)")
    gy, gv = _yr(ctx, "fiscal/investment.csv", "gfcf_pct_gdp")
    _bands(ig, ax)
    ctx.line(ax, gy, gv, p.BLUE)
    ctx.endlabel(ax, gy, gv, p.BLUE, lambda v: f"{v:.1f}%", dy=10)
    pk = _peak(zip(gy, gv))
    ax.annotate(f"{pk[1]:.1f}% — the brick years", pk,
                textcoords="offset points", xytext=(6, 8), ha="left",
                fontsize=8.6, fontweight="bold", color=p.BLUE)
    lo = _low(zip(gy, gv))
    _note(ctx, ax, 0.985, 0.30, f"the construction bust: {lo[1]:.1f}% by "
          f"{lo[0]}", ha="right")

    ax = ig.slot("spending.public_investment",
                 "Public investment, general government (% of GDP)")
    py, pv = _yr(ctx, "fiscal/investment.csv", "gov_gfcf_pct_gdp")
    _bands(ig, ax)
    ctx.line(ax, py, pv, p.GREEN_D)
    ax.fill_between(py, 0, pv, color=p.GREEN_D, alpha=0.10)
    ctx.endlabel(ax, py, pv, p.GREEN_D, lambda v: f"{v:.1f}%", dy=10)
    pk, lo = _peak(zip(py, pv)), _low(zip(py, pv))
    _note(ctx, ax, 0.985, 0.97, f"austerity cut it from {pk[1]:.1f}% in "
          f"{pk[0]}\nto {lo[1]:.1f}% by {lo[0]}", ha="right")

    for a in ig.axes_flat:
        ig.style_axis(a)


# -------------------------------------------------------------------- trade
_PARTNER_COLOR = ("NAVY", "ROJO", "GREEN_D", "TEAL", "PURPLE", "BLUE",
                  "GUALDA")
_PARTNERS = ("France", "Germany", "Italy", "Portugal", "United Kingdom",
             "United States", "Morocco")
_PRODUCTS = {"agrifood": ("Food and farm goods (HS 01–24)", "GREEN_D"),
             "vehicles": ("Vehicles and parts (HS 87)", "NAVY"),
             "machinery": ("Machinery and electrical (HS 84–85)", "BLUE"),
             "fuels": ("Fuels, mostly refined (HS 27)", "GUALDA"),
             "pharma": ("Medicines (HS 30)", "PURPLE")}


def plate_trade(ctx, ig) -> None:
    p = ctx.p
    gdp = _d(ctx, "macro/gdp.csv", "nominal_eurbn")

    def share(col):
        s = _d(ctx, "trade/trade.csv", col)
        ys = [y for y in sorted(s) if y in gdp]
        return ys, [s[y] / gdp[y] * 100 for y in ys]

    ax = ig.slot("trade.exports_imports",
                 "Exports and imports, goods and services (% of GDP)")
    xy, xv = share("exports_eurbn")
    my, mv = share("imports_eurbn")
    _bands(ig, ax, first=True, y=0.53, va="bottom")
    ctx.line(ax, xy, xv, p.GREEN_D, label="Exports")
    ctx.line(ax, my, mv, p.BLUE, label="Imports")
    ctx.endlabel(ax, xy, xv, p.GREEN_D, lambda v: f"{v:.1f}%", dy=8)
    ctx.endlabel(ax, my, mv, p.BLUE, lambda v: f"{v:.1f}%", dy=-16)
    ax.legend(loc="upper left", fontsize=8.4, ncol=2)
    x, m = dict(zip(xy, xv)), dict(zip(my, mv))
    eur = _d(ctx, "trade/trade.csv", "exports_eurbn")
    _note(ctx, ax, 0.985, 0.97, f"openness, exports + imports: "
          f"{x[2006] + m[2006]:.0f}% of GDP in 2006,\n"
          f"{x[xy[-1]] + m[xy[-1]]:.0f}% in {xy[-1]} — €{eur[xy[-1]]:,.0f}bn "
          "of exports", ha="right")
    _foot(ctx, ax, "national accounts (ESA 2010), services included; "
          "the customs panels below are goods only")

    ax = ig.slot("trade.balance",
                 "Trade balance, goods and services (% of GDP)")
    _bands(ig, ax)
    by = [y for y in xy if y in m]
    bv = [x[y] - m[y] for y in by]
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ROJO)
    gx, gxv = share("exports_goods_eurbn")
    _, gmv = share("imports_goods_eurbn")
    _, sxv = share("exports_services_eurbn")
    _, smv = share("imports_services_eurbn")
    goods = [a - b for a, b in zip(gxv, gmv)]
    services = [a - b for a, b in zip(sxv, smv)]
    ctx.line(ax, gx, services, p.GUALDA, lw=1.9, marker="",
             label="services alone (tourism, mostly)")
    ctx.line(ax, gx, goods, p.NAVY, lw=1.9, marker="", label="goods alone")
    ax.legend(loc="lower right", fontsize=8.0)
    cross = next(y for y, v in zip(by, bv) if v > 0)
    sv, gv = dict(zip(gx, services)), dict(zip(gx, goods))
    _note(ctx, ax, 0.015, 0.97, f"in surplus since {cross}, on services: in "
          f"{gx[-1]}\nservices {sv[gx[-1]]:+.1f}% of GDP, goods "
          f"{gv[gx[-1]]:+.1f}%")

    ax = ig.slot("trade.destinations",
                 "Where Spain's goods go (% of goods exports)")
    _bands(ig, ax)
    last = {}
    for name, col in zip(_PARTNERS, _PARTNER_COLOR):
        ys, vs = _long(ctx, "trade/destinations.csv", "destination", name)
        ctx.line(ax, ys, vs, getattr(p, col), lw=2.0, marker="", label=name)
        last[name] = (ys, vs)
    ax.legend(loc="upper right", fontsize=7.8, ncol=2)
    fy, fv = last["France"]
    my2, mv2 = last["Morocco"]
    _note(ctx, ax, 0.015, 0.97, f"France still takes {fv[-1]:.1f}% "
          f"({fy[-1]}), down from {fv[0]:.1f}%;\nMorocco has gone from "
          f"{mv2[0]:.1f}% to {mv2[-1]:.1f}%")
    _foot(ctx, ax, "customs goods exports, Eurostat Comext (community "
          "concept); shares of the total to the world")

    ax = ig.slot("trade.lens", "Lens: what Spain sells (% of goods exports)")
    _bands(ig, ax)
    ser = {}
    for key, (label, col) in _PRODUCTS.items():
        ys, vs = _long(ctx, "trade/export_products.csv", "product", key)
        ctx.line(ax, ys, vs, getattr(p, col), lw=2.0, marker="", label=label)
        ser[key] = dict(zip(ys, vs))
    ax.set_ylim(0, 36)
    ax.set_ylabel("% of goods exports", fontsize=8.6, color=p.MUTED)
    ax.legend(loc="upper right", fontsize=7.6, ncol=2)
    food, cars = ser["agrifood"], ser["vehicles"]
    yrs = sorted(set(food) & set(cars))
    since = next(y for y in yrs if all(food[z] > cars[z] for z in yrs
                                       if z >= y))
    _note(ctx, ax, 0.015, 0.80, f"food has outsold cars every year since "
          f"{since}:\n{food[yrs[-1]]:.1f}% against {cars[yrs[-1]]:.1f}% in "
          f"{yrs[-1]}")

    for a in ig.axes_flat:
        ig.style_axis(a)


# ------------------------------------------------------------------ markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("markets.policy_rate",
                 "The policy rate is set in Frankfurt, vs Spanish inflation "
                 "(%)")
    dy, dv = _yr(ctx, "markets/policy_rate.csv", "dfr")
    my, mv = _yr(ctx, "markets/policy_rate.csv", "mro")
    iy, iv = _yr(ctx, "macro/inflation.csv", "ipc")
    _bands(ig, ax, first=True, y=0.60, va="bottom")
    ctx.line(ax, iy, iv, p.ROJO, lw=1.9, marker="",
             label="Spanish inflation (IPC)")
    ctx.line(ax, my, mv, p.FAINT, lw=1.8, marker="", dashed_partial=False,
             label="Main refinancing rate (from Oct 2008)")
    ctx.line(ax, dy, dv, p.NAVY, label="ECB deposit facility rate (year-end)")
    ax.legend(loc="upper left", fontsize=8.0)
    below = [y for y, v in zip(dy, dv) if v < 0]
    _note(ctx, ax, 0.985, 0.97, f"{len(below)} year-ends below zero, "
          f"{min(below)}–{max(below)}", ha="right")

    ax = ig.slot("markets.bond_10y",
                 "The 10-year benchmark yield (%, annual average)")
    ty, tv = _yr(ctx, "markets/yield_10y.csv", "yield_10y")
    _bands(ig, ax)
    ctx.line(ax, ty, tv, p.ROJO)
    ax.fill_between(ty, 0, tv, color=p.ROJO, alpha=0.07)
    ctx.endlabel(ax, ty, tv, p.ROJO, lambda v: f"{v:.2f}%", dy=10)
    pk = _peak(zip(ty, tv))
    ax.annotate(f"{pk[1]:.2f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(-12, 8), ha="right", fontsize=8.8, fontweight="bold",
                color=p.ROJO)
    ig.add_event(ax, MARKS["whatever_it_takes"][0],
                 MARKS["whatever_it_takes"][1], dy=0.62)
    _note(ctx, ax, 0.985, 0.97, "the euro crisis in one number: the "
          "Maastricht\nconvergence yield, Eurostat", ha="right")

    ax = ig.slot("markets.currency",
                 "The euro against the US$ (index 2006 = 100, annual "
                 "average)")
    fx = _d(ctx, "markets/eurusd.csv", "avg")
    # Quoted as US$ per euro, so up is already a stronger euro: rebase it,
    # do not invert it.
    xy, xv = ctx.index_2006(fx)
    _bands(ig, ax)
    ctx.line(ax, xy, xv, p.TEAL)
    ctx.endlabel(ax, xy, xv, p.TEAL, lambda v: f"{v:.0f}", dy=10)
    _note(ctx, ax, 0.015, 0.22, f"US$ {fx[2006]:.2f} per euro in 2006, "
          f"{fx[2022]:.2f} in 2022, {fx[ctx.LAST_FULL_YEAR]:.2f} in "
          f"{ctx.LAST_FULL_YEAR};\na currency Spain shares — no peseta "
          "since 2002", va="bottom")

    ax = ig.slot("markets.equities",
                 "IBEX 35 in US$, with the S&P 500 (index 2006 = 100)")
    ibex = _d(ctx, "markets/ibex.csv", "close")
    eop = _d(ctx, "markets/eurusd.csv", "eop")
    spx = _d(ctx, "markets/sp500.csv", "close")
    usd = {y: v * eop[y] for y, v in ibex.items() if y in eop}
    by, bv = ctx.index_2006(usd)
    sy, sv = ctx.index_2006({y: v for y, v in spx.items() if y >= 2006})
    _bands(ig, ax)
    ctx.line(ax, sy, sv, p.FAINT, lw=1.9, marker="", ls="--",
             label="S&P 500, US$")
    ctx.line(ax, by, bv, p.NAVY, label="IBEX 35, in US$ at the year-end rate")
    ax.legend(loc="upper left", fontsize=8.0)
    b, s = dict(zip(by, bv)), dict(zip(sy, sv))
    full = ctx.LAST_FULL_YEAR
    _note(ctx, ax, 0.985, 0.06, f"{full}: IBEX {b[full]:.0f}, S&P 500 "
          f"{s[full]:.0f} — price indices, dividends\nexcluded; 2026 is the "
          "latest close, not a year-end", ha="right", va="bottom")

    for a in ig.axes_flat:
        ig.style_axis(a)


# ------------------------------------------------------------------- credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("credit.household_debt",
                 "Household debt, all lenders (% of GDP, year-end)")
    hy, hv = _yr(ctx, "credit/household_credit.csv", "hh_credit_pct_gdp_q4")
    _bands(ig, ax, first=True, y=0.965)
    ctx.line(ax, hy, hv, p.ROJO)
    ax.fill_between(hy, 0, hv, color=p.ROJO, alpha=0.07)
    pk = _peak(zip(hy, hv))
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=8.8, fontweight="bold",
                color=p.ROJO)
    ctx.endlabel(ax, hy, hv, p.ROJO, lambda v: f"{v:.1f}%", dy=10)
    gdi = _d(ctx, "credit/household_debt.csv", "debt_pct_income_avg")
    gpk = _peak(gdi.items())
    last = max(gdi)
    _note(ctx, ax, 0.985, 0.80, "on the Banco de España's own measure:\n"
          f"{gpk[1]:.0f}% of disposable income in {gpk[0]}, "
          f"{gdi[last]:.0f}% in {last}", ha="right")
    _foot(ctx, ax, "BIS total credit to households and NPISHs, every "
          "lender, adjusted for breaks")

    ax = ig.slot("credit.lending_rate",
                 "What a new mortgage costs, vs the policy rate (%)")
    ey, ev = _yr(ctx, "credit/lending_rates.csv", "euribor_12m")
    my, mv = _yr(ctx, "credit/lending_rates.csv", "mortgage_new")
    dy, dv = _yr(ctx, "markets/policy_rate.csv", "dfr")
    _bands(ig, ax)
    ctx.line(ax, dy, dv, p.FAINT, lw=1.8, marker="", dashed_partial=False,
             label="ECB deposit facility rate")
    ctx.line(ax, ey, ev, p.GUALDA, label="Euribor 12m, the mortgage index")
    ctx.line(ax, my, mv, p.NAVY, label="new housing loans (TEDR)")
    ax.legend(loc="upper right", fontsize=8.0)
    _note(ctx, ax, 0.015, 0.97, "most Spanish mortgages reprice on Euribor "
          "every year,\nso the 2022–23 shock hit the stock, not just new "
          "loans")
    _foot(ctx, ax, "the new-business compilation changed with Circular "
          "5/2012: pre- and post-2014 levels differ")

    ax = ig.slot("credit.npl",
                 "Doubtful loans (% of all credit to residents, December)")
    ny, nv = _yr(ctx, "credit/npl.csv", "npl_ratio")
    _bands(ig, ax)
    ctx.line(ax, ny, nv, p.PURPLE)
    ax.fill_between(ny, 0, nv, color=p.PURPLE, alpha=0.08)
    pk = _peak(zip(ny, nv))
    ax.annotate(f"{pk[1]:.1f}% in December {pk[0]}", pk,
                textcoords="offset points", xytext=(0, 8), ha="center",
                fontsize=8.8, fontweight="bold", color=p.PURPLE)
    ctx.endlabel(ax, ny, nv, p.PURPLE, lambda v: f"{v:.1f}%", dy=-18)
    ig.add_event(ax, 2014.0, "2014: reporting change,\na level step",
                 dy=0.22)
    _foot(ctx, ax, "computed here as doubtful ÷ total credit to resident "
          "sectors (credit institutions in Spain)")

    ax = ig.slot("credit.lens",
                 "Lens: what servicing the debt takes (% of income)")
    sy, sv = _yr(ctx, "credit/debt_service.csv", "hh_dsr_pct_q4")
    _bands(ig, ax)
    ctx.line(ax, sy, sv, p.NAVY)
    ax.fill_between(sy, 0, sv, color=p.NAVY, alpha=0.07)
    pk = _peak(zip(sy, sv))
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=8.8, fontweight="bold",
                color=p.NAVY)
    ctx.endlabel(ax, sy, sv, p.NAVY, lambda v: f"{v:.1f}%", dy=10)
    ds = dict(zip(sy, sv))
    ax.set_ylim(0, 14)
    ax.set_ylabel("% of disposable income", fontsize=8.6, color=p.MUTED)
    _note(ctx, ax, 0.985, 0.97, f"deleveraging beat the rate shock: "
          f"{ds[2021]:.1f}% in 2021,\n{ds[2023]:.1f}% in 2023", ha="right")
    _foot(ctx, ax, "BIS debt service ratio, households: interest plus "
          "repayments, Q4")

    for a in ig.axes_flat:
        ig.style_axis(a)


# ------------------------------------------------------------------- people
def plate_people(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("people.gini",
                 "Income inequality, Gini (0–100, higher = less equal)")
    sy, sv = _yr(ctx, "social/gini.csv", "silc")
    wy, wv = _yr(ctx, "social/gini.csv", "wb")
    _bands(ig, ax, first=True, y=0.05, va="bottom")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.8, dashed_partial=False,
             label="World Bank (EU-SILC-derived)")
    ctx.line(ax, sy, sv, p.PURPLE, label="Eurostat (EU-SILC)")
    ax.legend(loc="center right", fontsize=8.2)
    pk = _peak(zip(wy, wv))
    _note(ctx, ax, 0.015, 0.97, f"two cuts of one survey: the World Bank's "
          f"peaks at {pk[1]:.1f} in {pk[0]};\nEurostat's starts in {sy[0]} "
          f"and reads {sv[-1]:.1f} in {sy[-1]}")

    ax = ig.slot("people.poverty",
                 "Poverty: below 60% of the median income, and below "
                 "US$8.30 a day (%)")
    py, pv = _yr(ctx, "social/poverty.csv", "arop60")
    by, bv = _yr(ctx, "social/poverty.csv", "wb_830")
    _bands(ig, ax)
    ctx.line(ax, py, pv, p.TEAL, label="at risk of poverty, 60% of the "
             "median (EU-SILC)")
    ax.fill_between(py, 0, pv, color=p.TEAL, alpha=0.08)
    ctx.line(ax, by, bv, p.GUALDA, lw=1.9, marker="", dashed_partial=False,
             label="below US$8.30 a day, 2021 PPP (World Bank)")
    ctx.endlabel(ax, py, pv, p.TEAL, lambda v: f"{v:.1f}%", dy=10)
    ax.legend(loc="upper right", fontsize=8.0)
    _note(ctx, ax, 0.015, 0.80, "a relative line: it barely moves when "
          "incomes\nfall together — a property of the measure")

    ax = ig.slot("people.minimum_wage",
                 "Minimum wage (US$ per month, 12-month basis)")
    w = _d(ctx, "social/minimum_wage.csv", "eur_month_jul")
    fx = _d(ctx, "markets/eurusd.csv", "avg")
    wy2 = [y for y in sorted(w) if y in fx]
    wv2 = [w[y] * fx[y] for y in wy2]
    _bands(ig, ax)
    ctx.line(ax, wy2, wv2, p.ROJO)
    ctx.endlabel(ax, wy2, wv2, p.ROJO, lambda v: f"US$ {v:,.0f}", dy=10)
    rise = (w[2019] / w[2018] - 1) * 100
    ig.add_event(ax, 2019.0, f"2019: +{rise:.0f}% in one decree", dy=0.82)
    full = ctx.LAST_FULL_YEAR
    _note(ctx, ax, 0.015, 0.97, "the SMI is paid in fourteen instalments; "
          f"shown over twelve:\n€{w[full]:,.0f} a month in {full}, at the "
          "year's average dollar rate")

    ax = ig.slot("people.lens", "Lens: people in work (millions, EPA)")
    my, mv = _yr(ctx, "macro/employment.csv", "employed_thousands_avg")
    mv = [v / 1000 for v in mv]
    _bands(ig, ax)
    ctx.line(ax, my, mv, p.NAVY)
    # shaded down to the axis floor, not to zero: this lens starts at 14
    # million and a fill to zero would be data drawn below the plate.
    ax.fill_between(my, 14, mv, color=p.NAVY, alpha=0.06)
    ctx.endlabel(ax, my, mv, p.NAVY, lambda v: f"{v:.1f}M", dy=10)
    tr, pk = _low(zip(my, mv)), _peak((y, v) for y, v in zip(my, mv)
                                      if y <= 2010)
    ax.annotate(f"{tr[1]:.1f}M ({tr[0]})", tr, textcoords="offset points",
                xytext=(10, -8), ha="left", va="top", fontsize=8.6,
                fontweight="bold", color=p.ROJO)
    ax.set_ylim(14, 24)
    ax.set_ylabel("millions employed", fontsize=8.6, color=p.MUTED)
    _note(ctx, ax, 0.015, 0.97, f"{pk[1] - tr[1]:.1f} million jobs lost "
          f"from {pk[0]} to {tr[0]},\nthen a decade to win them back")

    for a in ig.axes_flat:
        ig.style_axis(a)


# -------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ billion)")
    gy, gv = _yr(ctx, "international/gdp_usd.csv", "gdp_usd", since=2006)
    gv = [v / 1e9 for v in gv]
    _bands(ig, ax, first=True, y=0.05, va="bottom")
    ctx.line(ax, gy, gv, p.NAVY)
    ctx.endlabel(ax, gy, gv, p.NAVY, lambda v: f"US$ {v:,.0f}bn", dy=10)
    fx = _d(ctx, "markets/eurusd.csv", "avg")
    eur = _d(ctx, "macro/gdp.csv", "nominal_eurbn")
    fall = (fx[2015] / fx[2014] - 1) * 100
    last = max(eur)
    _note(ctx, ax, 0.015, 0.97, f"2015: the euro fell {-fall:.0f}% against "
          "the dollar — the economy did not;\nin euros, "
          f"€{eur[last]:,.0f}bn in {last}")
    _foot(ctx, ax, "World Bank WDI, current US$ at the annual average "
          "exchange rate")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "international/hdi.csv", "hdi", since=2006)
    _bands(ig, ax)
    ax.axhline(0.8, color=p.FAINT, lw=0.9, ls=":")
    ax.text(2006.0, 0.795, "0.800 = very high human development",
            fontsize=7.8, color=p.MUTED, style="italic", ha="left",
            va="top")
    ctx.line(ax, hy, hv, p.GREEN_D, marker="o", ms=4.4,
             split_year=max(hy))
    ctx.endlabel(ax, hy, hv, p.GREEN_D, lambda v: f"{v:.3f}", dy=10)
    _foot(ctx, ax, "one vintage throughout — the HDR recomputes the whole "
          "back-series at each methodology change")

    ax = ig.slot("world.cpi",
                 "Corruption Perceptions Index (0–100, higher = cleaner)")
    cy, cv = _yr(ctx, "international/cpi.csv", "score")
    _bands(ig, ax)
    ctx.line(ax, cy, cv, p.PURPLE, split_year=max(cy))
    ctx.endlabel(ax, cy, cv, p.PURPLE, lambda v: f"{v:.0f}", dy=10)
    lo = _low(zip(cy, cv))
    _note(ctx, ax, 0.015, 0.20, f"{cv[0]:.0f} in {cy[0]}, {lo[1]:.0f} in "
          f"{lo[0]}: the lowest score Spain has had\non the current method",
          va="top")
    _note(ctx, ax, 0.015, 0.97, "from 2012 only: the earlier 0–10 index "
          "was\ncomputed another way, and TI does not compare them")

    ax = ig.slot("world.reserves",
                 "Official reserves incl. gold (US$ billion, year-end)")
    ry, rv = _yr(ctx, "international/reserves.csv", "reserves_usd", since=2006)
    rv = [v / 1e9 for v in rv]
    _bands(ig, ax)
    ctx.line(ax, ry, rv, p.GUALDA)
    ctx.endlabel(ax, ry, rv, p.GUALDA, lambda v: f"US$ {v:,.0f}bn", dy=10)
    _note(ctx, ax, 0.015, 0.97, "small for a large economy: the euro "
          "area's buffer sits\nat the ECB, not in Madrid; much of this is "
          "gold,\nrevalued at the market price")

    for a in ig.axes_flat:
        ig.style_axis(a)


# --------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p
    mid = _midyear(ctx)

    ax = ig.slot("demography.population",
                 "Resident population, 1 January (index 2006 = 100)")
    pop = _d(ctx, "social/population.csv", "population")
    iy, iv = ctx.index_2006(pop)
    _bands(ig, ax, first=True, y=0.05, va="bottom")
    ctx.line(ax, iy, iv, p.BLUE)
    ctx.endlabel(ax, iy, iv, p.BLUE, lambda v: f"{v:.1f}", dy=10)
    last = max(pop)
    shrank = [y for y in sorted(pop) if y - 1 in pop and pop[y] < pop[y - 1]]
    _note(ctx, ax, 0.015, 0.97, f"{pop[2006] / 1e6:.1f} million in 2006, "
          f"{pop[last] / 1e6:.1f} million on 1 January {last};\n"
          f"{min(shrank) - 1}–{max(shrank)}: the only years the register "
          "shrank")
    _foot(ctx, ax, "INE's Estadística Continua de Población — one vintage "
          "back to 1971")

    ax = ig.slot("demography.fertility",
                 "Total fertility rate (children per woman)")
    ty, tv = _yr(ctx, "social/demography.csv", "tfr")
    _bands(ig, ax)
    ax.axhline(2.1, color=p.MUTED, lw=1.1, ls=(0, (5, 4)))
    ax.text(2006.0, 2.16, "replacement level 2.1", fontsize=8.0,
            color=p.MUTED, style="italic")
    ctx.line(ax, ty, tv, p.ROJO)
    ctx.endlabel(ax, ty, tv, p.ROJO, lambda v: f"{v:.2f}", dy=10)
    lo = _low(zip(ty, tv))
    _note(ctx, ax, 0.985, 0.22, f"{lo[1]:.2f} in {lo[0]} — among the "
          "lowest ever\nrecorded in Europe", ha="right")

    ax = ig.slot("demography.birth_death",
                 "Births and deaths (per 1,000 people)")
    births = _d(ctx, "social/demography.csv", "births")
    deaths = _d(ctx, "social/demography.csv", "deaths")
    by, bv = ctx.per_1000(births, mid)
    dy, dv = ctx.per_1000(deaths, mid)
    _bands(ig, ax)
    ctx.line(ax, by, bv, p.GREEN_D, label="Births")
    ctx.line(ax, dy, dv, p.INK, label="Deaths")
    ax.legend(loc="upper right", fontsize=8.4, ncol=2)
    cross = next(y for y in sorted(births) if deaths[y] > births[y])
    ig.add_event(ax, cross, f"deaths overtake\nbirths in {cross}", dy=0.18)
    d20 = dict(zip(dy, dv))[2020]
    _note(ctx, ax, 0.015, 0.97, f"COVID: {deaths[2020]:,.0f} deaths in "
          f"2020, {d20:.1f} per 1,000;\n{max(births)} is the last "
          "definitive year")
    _foot(ctx, ax, "INE vital statistics (MNP) per 1,000 residents at 1 "
          "July of the same year (ECP)")

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net migration (per 1,000 people)")
    nat = {y: births[y] - deaths[y] for y in births if y in deaths}
    ny, nv = ctx.per_1000(nat, mid)
    _bands(ig, ax)
    ctx.bars(ax, ny, nv, lambda v: p.GREEN_D if v >= 0 else p.ROJO)
    imm = _d(ctx, "migration/immigration.csv", "by_citizenship_total")
    emi = _d(ctx, "migration/emigration.csv", "by_citizenship_total")
    net = {y: imm[y] - emi[y] for y in imm if y in emi}
    seam = MARKS["emcr_seam"][0]
    for part, label in (
            ({y: v for y, v in net.items() if y < seam},
             "net migration, Eurostat — old method, to 2020"),
            ({y: v for y, v in net.items() if y >= seam},
             "net migration, Eurostat — new method, from 2021")):
        ctx.line(ax, *ctx.per_1000(part, mid), p.NAVY, lw=2.0,
                 marker="o", ms=3.4, label=label,
                 ls="-" if "old" in label else (0, (1, 1.5)))
    ax.axvline(seam, color=p.INK, lw=0.9, ls=(0, (4, 3)), zorder=1)
    ax.legend(loc="upper right", fontsize=7.6)
    first_neg = next(y for y, v in zip(ny, nv) if v < 0)
    _note(ctx, ax, 0.015, 0.97, f"natural increase negative since "
          f"{first_neg}:\nthe population grows on migration alone")
    _foot(ctx, ax, "bars: births minus deaths; the two migration methods "
          "are never joined (see Migration)")

    for a in ig.axes_flat:
        ig.style_axis(a)


# ----------------------------------------------------------------- security
_SUICIDE = "Suicidio y lesiones autoinfligidas"
_ROAD = "Accidentes de tráfico"


def plate_security(ctx, ig) -> None:
    p = ctx.p
    mid = _midyear(ctx)
    wb = {c: _d(ctx, "social/security.csv", c)
          for c in ("homicide_per_100k", "suicide_per_100k",
                    "road_deaths_per_100k")}

    ax = ig.slot("security.homicide",
                 "Homicide rate, by death certificate (per 100,000)")
    hom = _d(ctx, "social/homicides.csv", "ecm_deaths")
    hy, hv = ctx.per_100k(hom, mid)
    _bands(ig, ax, first=True, y=0.05, va="bottom")
    ctx.line(ax, *zip(*sorted(wb["homicide_per_100k"].items())), p.FAINT,
             lw=1.8, marker="", dashed_partial=False,
             label="UNODC, intentional homicide")
    ctx.line(ax, hy, hv, p.ROJO, label="INE death certificates "
             "(ICD-10 X85–Y09)")
    ctx.endlabel(ax, hy, hv, p.ROJO, lambda v: f"{v:.2f}", dy=10)
    ax.legend(loc="upper right", fontsize=8.0)
    last = max(hom)
    _note(ctx, ax, 0.015, 0.97, f"{hom[last]:,.0f} deaths by assault in "
          f"{last}: one of Europe's\nlowest rates; the police count is "
          "pending")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    sui = _cause(ctx, _SUICIDE)
    sy, sv = ctx.per_100k(sui, mid)
    _bands(ig, ax)
    ctx.line(ax, *zip(*sorted(wb["suicide_per_100k"].items())), p.FAINT,
             lw=1.8, marker="", dashed_partial=False,
             label="WHO, age-standardised")
    ctx.line(ax, sy, sv, p.PURPLE, label="INE death certificates, crude")
    ctx.endlabel(ax, sy, sv, p.PURPLE, lambda v: f"{v:.1f}", dy=10)
    ax.legend(loc="upper right", fontsize=8.0)
    _note(ctx, ax, 0.015, 0.97, f"{sui[max(sui)]:,.0f} suicides in "
          f"{max(sui)}: the largest violent death,\nfar above homicide")

    ax = ig.slot("security.road_deaths",
                 "Road traffic deaths (per 100,000)")
    road = _cause(ctx, _ROAD)
    ry, rv = ctx.per_100k(road, mid)
    _bands(ig, ax)
    ctx.line(ax, *zip(*sorted(wb["road_deaths_per_100k"].items())), p.FAINT,
             lw=1.8, marker="", dashed_partial=False,
             label="WHO estimate (to 2019)")
    ctx.line(ax, ry, rv, p.GUALDA, label="INE death certificates")
    ctx.endlabel(ax, ry, rv, p.GUALDA, lambda v: f"{v:.1f}", dy=10)
    ax.legend(loc="upper right", fontsize=8.0)
    r = dict(zip(ry, rv))
    _note(ctx, ax, 0.985, 0.62, f"{r[2006]:.1f} in 2006, {r[ry[-1]]:.1f} in "
          f"{ry[-1]}: down "
          f"{(1 - r[ry[-1]] / r[2006]) * 100:.0f}%\nsince the points licence "
          "of July 2006", ha="right")

    ax = ig.slot("security.lens",
                 "Lens: violent deaths side by side (per 100,000)")
    _bands(ig, ax)
    ctx.line(ax, sy, sv, p.PURPLE, lw=2.0, marker="", label="Suicide")
    ctx.line(ax, ry, rv, p.GUALDA, lw=2.0, marker="", label="Road traffic")
    ctx.line(ax, hy, hv, p.ROJO, lw=2.0, marker="", label="Homicide")
    ax.set_ylim(0, 12)
    ax.set_ylabel("per 100,000", fontsize=8.6, color=p.MUTED)
    ax.legend(loc="upper right", fontsize=8.0)
    s, rr = dict(zip(sy, sv)), dict(zip(ry, rv))
    passed = next(y for y in sorted(s) if y in rr and s[y] > rr[y])
    ig.add_event(ax, passed, f"{passed}: suicide passes road deaths",
                 dy=0.97)
    _note(ctx, ax, 0.985, 0.50, "the police-recorded count is pending: the "
          "Interior\nministry's portal answers automated requests with\nan "
          "error page served as HTTP 200", ha="right", color=p.FAINT)

    for a in ig.axes_flat:
        ig.style_axis(a)


# ---------------------------------------------------------------- mortality
_COVID_ID = "COVID-19. Virus identificado"
_COVID_SUS = "COVID-19. Virus no identificado (sospechoso)"


def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    mid = _midyear(ctx)
    deaths = _d(ctx, "social/demography.csv", "deaths")

    ax = ig.slot("mortality.death_rate",
                 "Crude death rate (deaths per 1,000 people)")
    dy, dv = ctx.per_1000(deaths, mid)
    _bands(ig, ax, first=True, y=0.05, va="bottom")
    ctx.line(ax, dy, dv, p.INK)
    ctx.endlabel(ax, dy, dv, p.INK, lambda v: f"{v:.1f}", dy=10)
    pk = _peak(zip(dy, dv))
    ax.annotate(f"{pk[1]:.1f} in {pk[0]} — {deaths[pk[0]]:,.0f} deaths", pk,
                textcoords="offset points", xytext=(-8, 8), ha="right",
                fontsize=8.6, fontweight="bold", color=p.ROJO)
    _note(ctx, ax, 0.015, 0.97, "an ageing population lifts the crude "
          "rate\neven as each age group dies later")
    _foot(ctx, ax, "INE vital statistics (MNP) per 1,000 residents at 1 "
          "July (ECP); 2025 not yet definitive")

    ax = ig.slot("mortality.excess_deaths",
                 "Deaths above the 2015–2019 average (%)")
    base = sum(deaths[y] for y in range(2015, 2020)) / 5
    ex = {y: (v / base - 1) * 100 for y, v in deaths.items() if y >= 2015}
    _bands(ig, ax)
    ctx.bars(ax, sorted(ex), [ex[y] for y in sorted(ex)],
             lambda v: p.ROJO if v > 0 else p.GREEN_D)
    for y, v in ex.items():
        if abs(v) > 5:
            ax.annotate(f"{v:+.1f}%", (y, v), textcoords="offset points",
                        xytext=(0, 4 if v >= 0 else -4), ha="center",
                        va="bottom" if v >= 0 else "top", fontsize=8.4,
                        fontweight="bold", color=p.ROJO)
    _note(ctx, ax, 0.015, 0.97, f"baseline: {base:,.0f} deaths a year, the "
          "mean of 2015–19;\nnot age-standardised — part of every bar is an "
          "older population")

    ax = ig.slot("mortality.covid",
                 "COVID-19 as the certified cause (deaths per 100,000)")
    ci, cu = _cause(ctx, _COVID_ID), _cause(ctx, _COVID_SUS)
    iy, iv = ctx.per_100k(ci, mid)
    uy, uv = ctx.per_100k({y: cu.get(y, 0.0) for y in ci}, mid)
    _bands(ig, ax)
    ax.bar(iy, iv, width=0.62, color=p.ROJO, zorder=3,
           label="virus identified")
    ax.bar(uy, uv, width=0.62, bottom=iv, color=p.ROJO, alpha=0.35,
           zorder=3, label="suspected, not identified")
    ax.legend(loc="upper right", fontsize=8.2)
    _note(ctx, ax, 0.015, 0.97, f"2020: {ci[2020]:,.0f} certified with the "
          f"virus identified, {cu[2020]:,.0f} suspected;\n"
          f"{deaths[2020] - base:,.0f} deaths above the 2015–19 average that "
          "year")

    ax = ig.slot("mortality.lens",
                 "Lens: the two big killers (deaths per 100,000)")
    tum = _cause(ctx, "II.Tumores")
    cir = _cause(ctx, "IX.Enfermedades del sistema circulatorio")
    ty, tv = ctx.per_100k(tum, mid)
    cy, cv = ctx.per_100k(cir, mid)
    _bands(ig, ax)
    ctx.line(ax, cy, cv, p.ROJO, label="Circulatory diseases")
    ctx.line(ax, ty, tv, p.NAVY, label="Tumours")
    ax.set_ylim(150, 300)
    ax.set_ylabel("per 100,000", fontsize=8.6, color=p.MUTED)
    ax.legend(loc="upper right", fontsize=8.2)
    first = next(y for y in sorted(tum) if y in cir and tum[y] > cir[y])
    _note(ctx, ax, 0.015, 0.06, f"cancer overtakes the heart only in "
          f"{first}:\n{tum[first]:,.0f} against {cir[first]:,.0f} deaths",
          va="bottom")

    for a in ig.axes_flat:
        ig.style_axis(a)


# ---------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    mid = _midyear(ctx)
    seam = int(MARKS["emcr_seam"][0])
    imm = _d(ctx, "migration/immigration.csv", "by_citizenship_total")
    emi = _d(ctx, "migration/emigration.csv", "by_citizenship_total")
    em = _d(ctx, "migration/migration_flows_ine.csv", "immigration")
    emcr = _d(ctx, "migration/migration_flows_emcr_ine.csv",
              "immigration_emcr")

    def halves(series):
        return ({y: v for y, v in series.items() if y < seam},
                {y: v for y, v in series.items() if y >= seam})

    # The seam panel. Eurostat carries the old EM method to 2020 and the
    # new EMCR one from 2021; the INE publishes 2021 on both. Nothing on
    # this panel draws a segment across 2020-2021.
    ax = ig.slot("migration.flows",
                 "Immigration and emigration (per 1,000 people) — one "
                 "seam, two methods")
    _bands(ig, ax, first=True, y=0.965)
    for series, color, name in ((imm, p.GREEN_D, "Immigration"),
                                (emi, p.ROJO, "Emigration")):
        old, new = halves(series)
        ctx.line(ax, *ctx.per_1000(old, mid), color, lw=2.3, marker="",
                 label=f"{name}, Eurostat — EM method, to 2020")
        ctx.line(ax, *ctx.per_1000(new, mid), color, lw=2.3, marker="o",
                 ms=3.6, label=f"{name}, Eurostat — EMCR method, from 2021")
    # The INE's old-method count is Eurostat's to 2020, so only the step
    # it adds — what EM said for 2021 — is drawn, from 2020.
    ey, ev = ctx.per_1000({y: em[y] for y in (seam - 1, seam)}, mid)
    ctx.line(ax, ey, ev, p.NAVY, lw=1.6, marker="o", ms=3.8, ls="--",
             dashed_partial=False,
             label="Immigration, INE — old method (EM), 2021")
    ax.axvline(seam, color=p.INK, lw=1.1, ls=(0, (4, 3)), zorder=1)
    lines = {ln.get_label(): ln for ln in ax.get_lines()}
    handles = [lines[k] for k in (
        "Immigration, Eurostat — EM method, to 2020",
        "Immigration, Eurostat — EMCR method, from 2021",
        "Emigration, Eurostat — EM method, to 2020",
        "Emigration, Eurostat — EMCR method, from 2021",
        "Immigration, INE — old method (EM), 2021")]
    ax.legend(handles=handles, loc="upper left", fontsize=7.3,
              bbox_to_anchor=(0.24, 0.925))
    e21, c21 = em[seam], emcr[seam]
    r = dict(zip(ey, ev))
    rc = dict(zip(*ctx.per_1000({seam: c21}, mid)))
    _note(ctx, ax, 0.715, 0.025, f"{seam} on both: {e21:,.0f} vs {c21:,.0f} "
          f"arrivals —\n{r[seam]:.1f} vs {rc[seam]:.1f} per 1,000, a "
          f"{(c21 / e21 - 1) * 100:.0f}% jump of method alone",
          ha="right", va="bottom", color=p.INK)

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    _bands(ig, ax)
    net = {y: imm[y] - emi[y] for y in imm if y in emi}
    old, new = halves(net)
    ctx.line(ax, *ctx.per_1000(old, mid), p.NAVY, lw=2.3, marker="",
             label="Eurostat — EM method, to 2020")
    ctx.line(ax, *ctx.per_1000(new, mid), p.NAVY, lw=2.3, marker="o",
             ms=3.6, label="Eurostat — EMCR method, from 2021")
    bal = _d(ctx, "migration/migration_flows_ine.csv", "balance")
    by, bv = ctx.per_1000({y: bal[y] for y in (seam - 1, seam)}, mid)
    ctx.line(ax, by, bv, p.GUALDA, lw=1.6, marker="o", ms=3.8, ls="--",
             dashed_partial=False, label="INE — old method (EM), 2021")
    ax.axvline(seam, color=p.INK, lw=1.1, ls=(0, (4, 3)), zorder=1)
    ax.legend(loc="upper left", fontsize=7.6)
    lo = _low(zip(*ctx.per_1000(old, mid)))
    out = [y for y, v in old.items() if v < 0]
    hi_old = _peak(zip(*ctx.per_1000(old, mid)))
    hi_new = _peak(zip(*ctx.per_1000(new, mid)))
    _note(ctx, ax, 0.715, 0.72, f"net emigration {min(out)}–{max(out)}, "
          f"bottoming at {lo[1]:.1f} in {lo[0]};\n{hi_new[1]:.1f} in "
          f"{hi_new[0]}, against {hi_old[1]:.1f} at the {hi_old[0]} peak",
          ha="right")

    ax = ig.slot("migration.foreign_born",
                 "Born abroad, and foreign citizens (% of population, "
                 "1 January)")
    stock = ctx.table("migration/stock.csv")
    rows = [(int(y), bt, bn, ct, cn) for y, bt, bn, ct, cn in zip(
        stock["year"], stock["by_birth_total"], stock["by_birth_national"],
        stock["by_citizenship_total"], stock["by_citizenship_national"])
        if bt == bt and bn == bn and ct == ct and cn == cn]
    yrs = [r[0] for r in rows]
    born = [(bt - bn) / bt * 100 for _, bt, bn, _, _ in rows]
    cit = [(ct - cn) / ct * 100 for _, _, _, ct, cn in rows]
    _bands(ig, ax)
    ctx.line(ax, yrs, born, p.GUALDA, label="born abroad")
    ctx.line(ax, yrs, cit, p.NAVY, label="foreign citizens")
    ax.fill_between(yrs, cit, born, color=p.PURPLE, alpha=0.14, zorder=1)
    ctx.endlabel(ax, yrs, born, p.GUALDA, lambda v: f"{v:.1f}%", dy=8)
    ctx.endlabel(ax, yrs, cit, p.NAVY, lambda v: f"{v:.1f}%", dy=-16)
    ax.legend(loc="upper left", fontsize=8.4)
    gap = rows[-1][4] - rows[-1][2]
    acq = _d(ctx, "migration/naturalisation.csv", "acquisitions")
    _note(ctx, ax, 0.985, 0.80, f"the shaded gap is people who became "
          f"Spanish:\n{gap / 1e6:.1f} million by {yrs[-1]}, {acq[max(acq)]:,.0f} "
          f"in {max(acq)} alone", ha="right", color=p.PURPLE)

    ax = ig.slot("migration.lens",
                 "Lens: the year's paperwork (per 1,000 people)")
    _bands(ig, ax)
    for rel, col, color, label, lw in (
            ("migration/permits.csv", "first_permits", p.NAVY,
             "first residence permits issued", 2.0),
            ("migration/naturalisation.csv", "acquisitions", p.PURPLE,
             "acquired Spanish citizenship", 2.0),
            ("migration/asylum.csv", "applications", p.ROJO,
             "asylum applications", 2.0),
            ("migration/asylum.csv", "decisions", p.GUALDA,
             "first-instance asylum decisions", 1.7),
            ("migration/asylum.csv", "positive", p.TEAL,
             "of which positive", 1.7)):
        ys, vs = ctx.per_1000(_d(ctx, rel, col), mid)
        ctx.line(ax, ys, vs, color, lw=lw, marker="", label=label,
                 dashed_partial=lw > 1.8)
    ax.set_ylim(0, 16)
    ax.set_ylabel("per 1,000 people", fontsize=8.6, color=p.MUTED)
    ax.legend(loc="upper left", fontsize=7.4, ncol=2)
    _foot(ctx, ax, "five different questions: applications are not "
          "arrivals, permits are not people; asylum and permits start 2008")

    for a in ig.axes_flat:
        ig.style_axis(a)


# The plates, in spine order. Every one declares its topic.
PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Spanish Economy — Growth, Income, Prices and Jobs",
         subtitle="An economy that fell twice before COVID, fell hardest "
                  "of all in 2020, and outgrew the euro area after it.",
         source="Sources: Eurostat — ESA 2010 national accounts and LFS · "
                "INE — IPC (base 2025) and EPA · World Bank WDI",
         alt="Four panels on the Spanish economy. Real growth falls to "
             "−3.8% in 2009, −2.9% in 2012 and −10.9% in 2020, then "
             "rebounds; GDP per person reads US$38,627 in 2025 on a log "
             "scale; IPC inflation peaks at 8.4% in 2022 beside the "
             "harmonised HICP and the ECB's 2% target; unemployment peaks "
             "at 26.1% in 2013 and is 10.5% in 2025."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="The Public Books — Deficits, the Bailout and the Debt",
         subtitle="General government on the Maastricht definition: small "
                  "surpluses in 2006–07, then deficits every year since.",
         source="Source: Eurostat — EDP notification and gov_10a_main "
                "(Spain's own transmission)",
         alt="Four panels on Spanish public finances. Revenue runs near "
             "40% of GDP against expenditure that reaches 51.6% in 2020; "
             "the balance swings from +2.1% in 2006 to −11.2% in 2009 and "
             "−11.5% in 2012, the bank-bailout year; gross debt jumps from "
             "69.5% to 100.0% of GDP in 2011–2013 and reads 100.5% in "
             "2025; interest paid peaks at 3.6% of GDP in 2013 and is "
             "2.4% in 2025."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Where the Money Goes — Spending by Function, 2006–2024",
         subtitle="Social protection alone is two-fifths of what the state "
                  "spends; investment tells the bubble and the cuts.",
         source="Source: Eurostat — gov_10a_exp (COFOG), gov_10a_main and "
                "nama_10_gdp",
         alt="Four panels on public spending. Social protection rises from "
             "12.7% of GDP in 2006 to 21.9% in 2020 and 18.7% in 2024, "
             "against health near 6.5% and education near 4%; the "
             "whole-economy investment rate falls from 30.1% in 2006 to "
             "17.6% in 2013; public investment falls from 5.2% in 2009 to "
             "2.0% in 2016."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Foreign Trade — a Deficit That Flipped, 2006–2025",
         subtitle="In surplus every year since 2011 on the national "
                  "accounts — a services surplus, tourism mostly, over a "
                  "goods deficit.",
         source="Sources: Eurostat — nama_10_gdp (P6/P7, P61/P62, P71/P72) "
                "and Comext DS-045409 (customs goods)",
         alt="Four panels on trade. Exports of goods and services rise "
             "from 25.2% of GDP in 2006 to 36.5% in 2025 and imports from "
             "30.9% to 32.6%; the balance moves from −6.2% of GDP in 2006 "
             "to +4.4% in 2024, a services surplus over a goods deficit; "
             "France takes 14.5% of goods exports in 2025, down from "
             "18.7%; food and farm goods overtake vehicles as the largest "
             "export group."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Money & Markets — Frankfurt's Rate, the Yield and the IBEX",
         subtitle="Spain has no monetary policy of its own: the ECB's rate "
                  "against Spanish inflation, the 10-year benchmark, the "
                  "euro and the IBEX 35 in dollars.",
         source="Sources: ECB Data Portal · Eurostat (Maastricht yield) · "
                "INE (IPC) · Yahoo Finance — a redistributor (IBEX 35, "
                "S&P 500, price indices)",
         alt="Four panels on money and markets. The ECB deposit facility "
             "rate sits below zero at eight year-ends, 2014–2021, while "
             "Spanish inflation peaks at 8.4% in 2022; the 10-year yield "
             "spikes to 5.85% in 2012; the euro, indexed to 2006, falls "
             "to 84 in 2022; the IBEX 35 in dollars ends 2025 near its "
             "2006 level while the S&P 500 is almost five times higher."),
    dict(id="06", slug="people", topic="people", builder=plate_people,
         title="People — Inequality, Poverty, Pay and Work",
         subtitle="Inequality that rose with the crisis and fell back, one "
                  "person in five below the relative poverty line, and a "
                  "minimum wage that doubled in euros.",
         source="Sources: Eurostat — EU-SILC and earn_mw_cur · World Bank "
                "(Gini, PIP) · ECB (US$ rate) · INE — EPA",
         alt="Four panels on people. The World Bank Gini peaks at 36.2 in "
             "2013 and Eurostat's EU-SILC Gini, from 2014, reads 30.8 in "
             "2025; the at-risk-of-poverty rate stays near "
             "20% while the World Bank's US$8.30-a-day line stays under "
             "5%; the minimum wage rises from about US$790 a month in "
             "2006 to US$1,560 in 2025; employment falls to 17.1 million "
             "in 2013 and rebuilds to 22.2 million."),
    dict(id="07", slug="world", topic="world", builder=plate_world,
         title="Spain in the World — Size, Development, Integrity and "
               "Reserves",
         subtitle="The comparables layer: the same quantities, computed the "
                  "same way, for everyone.",
         source="Sources: World Bank WDI · UNDP Human Development Report "
                "2025 · Transparency International CPI 2025 · IMF IFS via "
                "the World Bank",
         alt="Four panels on Spain in the world. GDP in current dollars "
             "moves between US$1.2 and US$1.9 trillion with the exchange "
             "rate; the Human Development Index reaches 0.918; the "
             "Corruption Perceptions Index falls from 65 in 2012 to 55 in "
             "2025; reserves including gold reach US$129 billion, small "
             "because the euro area's buffer sits at the ECB."),
    dict(id="08", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — Deaths Overtook Births in 2015",
         subtitle="The population grows anyway, on migration alone; "
                  "fertility is among the lowest ever recorded in Europe.",
         source="Sources: INE — Estadística Continua de Población and MNP · "
                "Eurostat — migr_imm1ctz, migr_emi1ctz",
         alt="Four panels on demography. The population at 1 January rises "
             "to 112.7 on an index of 2006 = 100, 49.6 million people, "
             "shrinking only in 2013–16; fertility falls to 1.10 children "
             "per woman; births fall from 10.9 to 6.5 per 1,000 while "
             "deaths reach 10.4 per 1,000 in 2020; natural increase turns "
             "negative while net migration reaches 15 per 1,000 on the "
             "new method."),
    dict(id="09", slug="security", topic="security", builder=plate_security,
         title="Security — Violent Death on the Death Certificate",
         subtitle="One of Europe's lowest homicide rates; suicide is the "
                  "largest violent death, and road deaths fell by more than "
                  "half.",
         source="Sources: INE — Estadística de Defunciones según la Causa de "
                "Muerte · UNODC and WHO via the World Bank",
         alt="Four panels on violent death, per 100,000 people. Homicide "
             "by death certificate falls from 0.85 in 2006 to 0.66 in "
             "2024, beside the UNODC series on a log scale; suicide runs "
             "near 8 per 100,000; road deaths fall from 9.3 to 3.8; side "
             "by side, suicide passes road deaths in 2008 and homicide is "
             "a small fraction of both."),
    dict(id="10", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — COVID-19 and the Two Big Killers",
         subtitle="What people die of: cancer and the heart trade the lead, "
                  "and 2020 breaks every trend on the plate.",
         source="Sources: INE — MNP (deaths), ECM (certified causes) and "
                "ECP (mid-year population)",
         alt="Four panels on mortality. The crude death rate rises from "
             "8.4 per 1,000 in 2006 to 10.4 in 2020; deaths run 17% above "
             "the 2015–19 average in 2020; certified COVID-19 deaths reach "
             "158 per 100,000 in 2020 with the virus identified or "
             "suspected; tumours pass circulatory diseases only in 2024, "
             "at about 237 per 100,000."),
    dict(id="11", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — Variable-Rate Country",
         subtitle="What a mortgage costs when most mortgages reprice every "
                  "year, and fifteen years of deleveraging.",
         source="Sources: BIS — total credit and debt service ratios · "
                "Banco de España — interest-rate and credit statistics · "
                "ECB",
         alt="Four panels on credit. Household debt peaks at 85.0% of GDP "
             "in 2009 and falls to 42.9% in 2025; new housing-loan rates "
             "follow Euribor from 5.7% in 2008 down to 1.5% in 2021 and "
             "back to 3.7% in 2023; doubtful loans peak at 13.6% of "
             "credit in December 2013; the debt service ratio falls from "
             "11.3% of income in 2008 to 5.1% in 2025."),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — Who Arrives, Who Leaves, Who Becomes Spanish",
         subtitle="The flows per 1,000 people, the foreign-born share, and "
                  "one methodology seam drawn as a seam.",
         source="Sources: Eurostat — migr_imm1ctz, migr_emi1ctz, "
                "migr_pop1ctz/pop3ctb, migr_asyappctza, migr_asydcfsta, "
                "migr_resfirst, migr_acq · INE — EM, EMCR and ECP",
         alt="Four panels on migration, per 1,000 people. Immigration "
             "falls to 6 per 1,000 in 2013 and reaches 26 in 2024, with "
             "the 2021 methodology change drawn as a break: the INE counts "
             "528,856 arrivals for 2021 on the old method and 887,960 on "
             "the new; net migration is negative in 2010–2015; the "
             "foreign-born share rises from 10.5% to 19.3% of the "
             "population against 14% foreign citizens; first permits reach "
             "13 per 1,000 in 2025."),
)
