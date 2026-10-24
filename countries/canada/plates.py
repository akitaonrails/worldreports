"""The canada plates, on the plate spine.

Every plate declares its topic and claims its four panels by slot key, in
the spine's order, so a Canadian panel sits over the same panel of every
other country in the comparison viewer: same indicator, same unit, same
y-scale (PLATE_SPINE.md, core/spine.py).

Twelve chapters. Five rest on Canadian publishers: the Department of
Finance's Fiscal Reference Tables, the Bank of Canada, IRCC and PHAC.
The other seven — economy, trade, people, demography, security,
mortality and credit — keep the harmonised publishers (World Bank, IMF,
OECD, BIS, UNODC/WHO) as the spine's canonical lines, and the curated
Statistics Canada series (`data/**/*_statcan.csv`) ride beside them as
labelled national lines, exactly in the slots HANDOFF.md maps. Where a
published rate exists (the police-reported homicide rate, the LFS, the
crude birth rate) the plate uses it; where only counts exist (deaths,
components of growth) the plate divides them by the matching July 1
population, the conversions DATA_NOTES.md documents. Definitional pairs
— MBM bases, police-reported vs UNODC homicide, debt to GDP vs debt to
disposable income, BIS vs StatCan debt service — are always two clearly
labelled lines, never one joined series. No Statistics Canada number is
typed in here.

Two conventions run through the file:

- **Federal fiscal years** (April to March, `fiscal_year` = the starting
  year) are drawn at their midpoint, 1 October, i.e. a quarter of a year
  right of the calendar year they start in (`FY_SHIFT`). The calendar
  recession bands then sit where they happened relative to both kinds of
  year, instead of a 2020-21 deficit being drawn as if it were calendar
  2020.
- **Notes read their numbers from the CSVs** at build time, so a refetch
  that moves a figure moves the sentence with it.
"""
from __future__ import annotations

from core.sideload import sibling

events = sibling(__file__, "events")

W0 = 2006        # the shared plate window opens here
FY_SHIFT = 0.25  # an April-March fiscal year, drawn at its midpoint


# ------------------------------------------------------------ small helpers
def _yr(ctx, rel: str, col: str, since: int = W0, until: int | None = None):
    """(years, values) from a calendar-year CSV, blanks dropped."""
    t = ctx.table(rel)
    if not t or col not in t:
        return [], []
    yrs, vals = ctx.series(t, col)
    keep = [(y, v) for y, v in zip(yrs, vals)
            if y >= since and (until is None or y <= until)]
    return [y for y, _ in keep], [v for _, v in keep]


def _fy(ctx, rel: str, col: str, since: int = W0):
    """(x, values) from a federal fiscal-year CSV, drawn at the midpoint.

    The FRT files are keyed by `fiscal_year`, the STARTING year of an
    April-March year, which ctx.series cannot see; ctx.rows takes the key
    and skips the '#' provenance header.
    """
    rows = ctx.rows(rel, key="fiscal_year") or {}
    out = [(y + FY_SHIFT, float(r[col])) for y, r in sorted(rows.items())
           if y >= since and (r.get(col) or "").strip()]
    return [y for y, _ in out], [v for _, v in out]


def _at(years, vals, year):
    return dict(zip(years, vals))[year]


def _note(p, ax, x, y, text, color=None, ha="left", va="top", size=8.0):
    """A short italic note in axes fractions, placed where the reference
    scale is known to leave room."""
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=size, style="italic", color=color or p.MUTED, zorder=7)


def _foot(p, ax, text):
    """The provenance line under a panel."""
    ax.text(0.5, -0.07, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.2, color=p.FAINT, style="italic")


def _natl(ctx, ax, years, vals, color, label, **kw):
    """A labelled Statistics Canada line riding beside the canonical one.

    Thin, small markers, dotted (the fiscal plate's convention): the
    harmonised series stays the spine's line and the national one is
    visibly the second reading, never a continuation of the first.
    """
    kw.setdefault("lw", 1.6)
    kw.setdefault("ms", 2.6)
    ctx.line(ax, years, vals, color, label=label, ls=(0, (1, 1.4)),
             dashed_partial=False, **kw)


def _barkey(ax, color, label):
    """An invisible bar carrying a legend entry for a bar series."""
    ax.bar([], [], color=color, label=label)


def _mark(ig, ax, key, dy=0.97):
    """One of events.MARKS on a panel."""
    x, label = events.MARKS[key]
    ig.add_event(ax, x, label, dy=dy)


def _bands_labelled_at(ig, ax, y, p):
    """The recession bands with their names at height `y` (axes fraction),
    for a slot-1 panel whose data fill the bottom where add_recessions puts
    the names."""
    ig.add_recessions(ax, label=False)
    for start, end, name in ig.country.recessions:
        ax.text((start + end) / 2, y, name, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=8, color=p.MUTED,
                style="italic")


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(a)


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p
    G = "macro/growth_prices.csv"

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, G, "real_growth_pct")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.RED)
    sy, sv = _yr(ctx, "macro/economy_statcan.csv", "real_growth_pct")
    _natl(ctx, ax, sy, sv, p.NAVY, "Statistics Canada (36-10-0699)")
    _barkey(ax, p.GREEN, "World Bank (redistribution)")
    ig.add_recessions(ax, inside=True)
    for y in (2009, 2020):
        v = _at(gy, gv, y)
        ax.annotate(f"{v:.1f}%", (y, v), textcoords="offset points",
                    xytext=(0, -4), ha="center", va="top", fontsize=8.6,
                    fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.96, "the 2015 oil-price contraction never shows in "
          "an annual figure:\n2015 still grew "
          f"{_at(gy, gv, 2015):.1f}% — it is not banded (see DATA_NOTES)")
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _foot(p, ax, "World Bank series of Statistics Canada's national accounts "
          "(bars); the line is StatCan cube 36-10-0699, never spliced into it")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "international/gdp_pc.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    _note(p, ax, 0.02, 0.30, f"US$ per person, 2014 to 2015: {_at(py, pv, 2014):,.0f} to "
          f"{_at(py, pv, 2015):,.0f} — the oil price\ntaking the "
          "Canadian dollar down with it, not output")
    _foot(p, ax, "World Bank, current US$ at market exchange rates")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year) and the 2% target")
    ax.axhspan(1, 3, color=p.GREEN, alpha=0.07, zorder=0)
    ax.axhline(2, color=p.GREEN_D, lw=1.0, ls=":", zorder=2)
    cy, cv = _yr(ctx, G, "cpi_inflation_pct")
    ctx.line(ax, cy, cv, p.RED, label="CPI, annual average (World Bank)")
    sy, sv = _yr(ctx, "macro/economy_statcan.csv", "cpi_inflation_pct")
    _natl(ctx, ax, sy, sv, p.NAVY, "CPI change (StatCan 18-10-0005)")
    ig.add_recessions(ax, label=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(-8, 4), ha="right",
                fontsize=8.8, fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.96, "Bank of Canada target: 2%, inside a 1–3% band")
    ax.legend(loc="upper right", fontsize=7.6, frameon=False,
              bbox_to_anchor=(1.0, 0.90))
    _foot(p, ax, "World Bank redistribution of StatCan's CPI and StatCan's "
          "own 18-10-0005 annual average — one statistic, two publishers")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    uy, uv = _yr(ctx, "macro/economy.csv", "unemployment_pct")
    ctx.line(ax, uy, uv, p.NAVY, label="ILO modelled estimate")
    ly, lv = _yr(ctx, "macro/economy_statcan.csv", "lfs_unemployment_pct")
    _natl(ctx, ax, ly, lv, p.GOLD, "Labour Force Survey (StatCan, annual)")
    ig.add_recessions(ax, label=False)
    peak = max(zip(uy, uv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(8, 2), ha="left",
                fontsize=8.8, fontweight="bold", color=p.NAVY)
    low = min(zip(uy, uv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, f"low of {low[1]:.1f}% in {low[0]}; "
          f"{uv[-1]:.1f}% in {uy[-1]}")
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _foot(p, ax, "ILO estimate via the World Bank, beside StatCan's LFS "
          "annual table (14-10-0327) — they agree by calibration, not identity")
    _finish(ctx, ig)


# ------------------------------------------------------------------ fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p
    GG = "fiscal/general_government.csv"
    TX = "fiscal/transactions_pct_gdp.csv"

    ax = ig.slot("fiscal.revenue_expenditure",
                 "Revenue and expenditure (% of GDP)")
    ry, rv = _yr(ctx, GG, "revenue_pct_gdp")
    ey, ev = _yr(ctx, GG, "expenditure_pct_gdp")
    ctx.line(ax, ey, ev, p.RED, label="General government, expenditure")
    ctx.line(ax, ry, rv, p.NAVY, label="General government, revenue")
    fy_r = _fy(ctx, TX, "revenues")
    fy_e = _fy(ctx, "fiscal/expenses_pct_gdp.csv", "total_expenses")
    ctx.line(ax, *fy_e, p.RED, lw=1.4, ms=2.6, ls=(0, (1, 1.4)),
             dashed_partial=False, label="Federal, expenses (fiscal years)")
    ctx.line(ax, *fy_r, p.NAVY, lw=1.4, ms=2.6, ls=(0, (1, 1.4)),
             dashed_partial=False, label="Federal, revenues (fiscal years)")
    ig.add_recessions(ax, inside=True)
    ax.legend(loc="upper left", fontsize=7.6, ncol=2, frameon=False)
    pk = max(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}%", pk, textcoords="offset points",
                xytext=(9, 0), ha="left", va="center", fontsize=8.6,
                fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.47, "all governments plus the CPP/QPP, calendar "
          "years;\nfederal lines: fiscal years (April–March) drawn at "
          "their midpoint", size=7.6)

    ax = ig.slot("fiscal.balance", "Overall balance (bars) and primary "
                 "balance (% of GDP)")
    by, bv = _yr(ctx, GG, "balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.RED)
    py_, pv = _yr(ctx, GG, "primary_balance_pct_gdp")
    ctx.line(ax, py_, pv, p.NAVY, lw=1.8, ms=3.2,
             label="General government, primary")
    fy_b = _fy(ctx, TX, "budgetary_balance")
    ctx.line(ax, *fy_b, p.GOLD, lw=1.8, ms=3.2, dashed_partial=False,
             label="Federal budgetary balance (fiscal years)")
    ig.add_recessions(ax, label=False)
    gw = min(zip(by, bv), key=lambda t: t[1])
    ax.annotate(f"{gw[1]:.1f}%", gw, textcoords="offset points",
                xytext=(-10, -2), ha="right", va="top", fontsize=8.6,
                fontweight="bold", color=p.RED)
    fw = min(zip(*fy_b), key=lambda t: t[1])
    ax.annotate(f"{fw[1]:.1f}%", fw, textcoords="offset points",
                xytext=(9, -2), ha="left", va="top", fontsize=8.6,
                fontweight="bold", color=p.GOLD)
    ax.legend(loc="lower left", fontsize=7.6, frameon=False)
    _note(p, ax, 0.98, 0.10, "2020-21: the largest federal deficit\n"
          "in Canadian peacetime", ha="right", va="bottom", size=7.8)

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    gy, gv = _yr(ctx, GG, "gross_debt_pct_gdp")
    ctx.line(ax, gy, gv, p.RED, label="General government, gross")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.RED, lambda v: f"{v:.1f}%", dy=7)
    ax.legend(loc="upper left", fontsize=7.6, frameon=False)
    acc = ctx.rows("fiscal/liabilities.csv", key="fiscal_year") or {}
    last = max(acc)
    _note(p, ax, 0.02, 0.40, f"federal accumulated deficit {last}-"
          f"{(last + 1) % 100:02d}: C${float(acc[last]['accumulated_deficit_mn']) / 1e6:.2f}tn;\n"
          "federal accumulated deficit (not gross debt); quoted here as "
          "context, not overlaid", ha="left", va="bottom", size=7.6)

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    iy, iv = _yr(ctx, "fiscal/gfs_operations.csv", "interest_payable")
    ctx.line(ax, iy, iv, p.PURPLE, label="General government, interest "
             "payable (IMF GFS)")
    fy_i = _fy(ctx, TX, "public_debt_charges")
    ctx.line(ax, *fy_i, p.GOLD, lw=1.8, ms=3.2, dashed_partial=False,
             label="Federal public debt charges (fiscal years)")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.PURPLE, lambda v: f"{v:.1f}%", dy=8)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    low = min(zip(iy, iv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.58, f"cheap money: a {low[1]:.1f}% trough in "
          f"{low[0]};\n{iv[-1]:.1f}% again by {iy[-1]}", size=7.8)
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
COFOG7 = [
    ("Social protection", ["social_protection"], "RED"),
    ("Health", ["health"], "TEAL"),
    ("Education", ["education"], "GOLD"),
    ("General public services", ["general_public_services"], "PURPLE"),
    ("Economic affairs", ["economic_affairs"], "BLUE"),
    ("Defence and public order", ["defence", "public_order"], "NAVY"),
    ("Other", ["environment", "housing", "recreation_culture"], "FAINT"),
]


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    C = "fiscal/cofog.csv"
    t = ctx.table(C)
    yrs = [y for y in t["year"] if y >= W0]

    def group(cols):
        return [sum(t[c][t["year"].index(y)] for c in cols) for y in yrs]

    ax = ig.slot("spending.by_function", "Spending by function, general "
                 "government (% of GDP)")
    layers = [(name, group(cols), getattr(p, col)) for name, cols, col in COFOG7]
    ax.stackplot(yrs, *[v for _, v, _ in layers],
                 labels=[n for n, _, _ in layers],
                 colors=[c for _, _, c in layers], alpha=0.9, lw=0)
    _bands_labelled_at(ig, ax, 0.80, p)
    ax.legend(loc="upper left", fontsize=7.2, ncol=4, frameon=False)
    tot = dict(zip(yrs, [sum(v) for v in zip(*[v for _, v, _ in layers])]))
    ax.annotate(f"{tot[2020]:.1f}%", (2020, tot[2020]),
                textcoords="offset points", xytext=(12, -2), ha="left",
                va="center", fontsize=8.6, fontweight="bold", color=p.INK)
    _note(p, ax, 0.02, 0.70, f"IMF COFOG, from {yrs[0]}; total outlays, "
          "2-4 points below\nthe expenditure line on the fiscal plate",
          size=7.4)

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    sp = group(["social_protection"])
    rest = [tot[y] - s for y, s in zip(yrs, sp)]
    ctx.line(ax, yrs, rest, p.NAVY, label="Everything else")
    ctx.line(ax, yrs, sp, p.RED, label="Social protection")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    ax.annotate(f"{sp[yrs.index(2020)]:.1f}%: the pandemic benefits",
                (2020, sp[yrs.index(2020)]), textcoords="offset points",
                xytext=(-8, 6), ha="right", fontsize=8.4, fontweight="bold",
                color=p.RED)
    tx = ctx.rows("fiscal/expenses_pct_gdp.csv", key="fiscal_year") or {}
    _note(p, ax, 0.98, 0.04, "federal transfers to persons alone: "
          f"{float(tx[2020]['transfers_to_persons']):.1f}% of GDP in 2020-21",
          ha="right", va="bottom", size=7.6)

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(GFCF, % of GDP)")
    iy, iv = _yr(ctx, "macro/economy.csv", "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.BLUE)
    ig.add_recessions(ax, label=False)
    pk = max(zip(iy, iv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}: the oil-sands boom",
                pk, textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=8.4, fontweight="bold", color=p.BLUE)
    _foot(p, ax, "World Bank series of Statistics Canada's national accounts")

    ax = ig.slot("spending.public_investment", "Public investment "
                 "(government GFCF, % of GDP)")
    gy, gv = _yr(ctx, "fiscal/public_investment.csv", "gov_gfcf_pct_gdp")
    ctx.line(ax, gy, gv, p.TEAL)
    ig.add_recessions(ax, label=False)
    pk = max(zip(gy, gv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}: the stimulus\ninfrastructure "
                "programme", pk, textcoords="offset points", xytext=(6, 8),
                ha="left", fontsize=8.2, fontweight="bold", color=p.TEAL)
    ctx.endlabel(ax, gy, gv, p.TEAL, lambda v: f"{v:.1f}%", dy=8)
    _foot(p, ax, "OECD, general government")
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
PARTNERS = [("usa", "United States", "RED"), ("gbr", "United Kingdom", "NAVY"),
            ("chn", "China", "GOLD"), ("jpn", "Japan", "TEAL"),
            ("nld", "Netherlands", "PURPLE")]


def plate_trade(ctx, ig) -> None:
    p = ctx.p
    T = "trade/trade.csv"

    ax = ig.slot("trade.exports_imports", "Exports and imports of goods "
                 "and services (% of GDP)")
    xy, xv = _yr(ctx, T, "exports_pct_gdp")
    my, mv = _yr(ctx, T, "imports_pct_gdp")
    ctx.line(ax, xy, xv, p.GREEN, label="Exports (World Bank)")
    ctx.line(ax, my, mv, p.RED, label="Imports (World Bank)")
    sy, sv = _yr(ctx, "trade/trade_statcan.csv", "exports_pct_gdp")
    sy2, sv2 = _yr(ctx, "trade/trade_statcan.csv", "imports_pct_gdp")
    _natl(ctx, ax, sy, sv, p.GREEN_D, "Exports (StatCan national accounts)")
    _natl(ctx, ax, sy2, sv2, p.RED_D, "Imports (StatCan national accounts)")
    ig.add_recessions(ax, inside=True)
    ax.legend(loc="upper right", fontsize=7.6, ncol=2, frameon=False)
    _note(p, ax, 0.02, 0.96, f"{xv[-1] + mv[-1]:.0f}% of GDP crosses the border "
          f"each way combined ({xy[-1]})")
    _foot(p, ax, "World Bank, national-accounts basis; the dotted pair is "
          "StatCan cube 36-10-0699 — the same statistic, not a customs series")

    ax = ig.slot("trade.balance", "Trade balance, goods and services "
                 "(% of GDP)")
    bal = [x - m for x, m in zip(xv, mv)]
    ctx.bars(ax, xy, bal, lambda v: p.GREEN if v >= 0 else p.RED)
    sexp, simp = dict(zip(sy, sv)), dict(zip(sy2, sv2))
    sby = [y for y in sorted(sexp) if y in simp]
    _natl(ctx, ax, sby, [sexp[y] - simp[y] for y in sby], p.NAVY,
          "Balance (StatCan difference)")
    _barkey(ax, p.GREEN, "Balance (World Bank difference)")
    ig.add_recessions(ax, label=False)
    deficits = [y for y, b in zip(xy, bal) if b < 0]
    _note(p, ax, 0.02, 0.96, f"in deficit in {len(deficits)} of the "
          f"{len(bal)} years since {xy[0]}: the oil price largely\n"
          "decides the sign")
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _foot(p, ax, "their difference, computed here and never stored; both "
          "publishers' differences are drawn, never averaged")

    PT = "trade/partners.csv"
    t = ctx.table(PT)
    wy, wv = _yr(ctx, PT, "exports_world_usd")
    world = dict(zip(wy, wv))

    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    shares = {}
    for code, name, col in PARTNERS:
        cy, cv = _yr(ctx, PT, f"exports_{code}_usd")
        sy = [y for y in cy if y in world]
        sv = [v / world[y] * 100 for y, v in zip(cy, cv) if y in world]
        shares[code] = dict(zip(sy, sv))
        ctx.line(ax, sy, sv, getattr(p, col), lw=2.2 if code == "usa" else 1.7,
                 ms=3.4, label=name)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="center left", fontsize=7.6, frameon=False, ncol=1,
              bbox_to_anchor=(0.0, 0.45))
    us = shares["usa"]
    y0, y1 = min(us), max(us)
    # The first year holds the peak of the grown axis: its label goes
    # under the point, where the line falls away fast enough to leave the
    # text clear. The last year sits well below the top, so its label
    # rides above the point.
    ax.annotate(f"{us[y0]:.0f}%", (y0, us[y0]), textcoords="offset points",
                xytext=(0, -12), ha="center", va="top", fontsize=8.4,
                fontweight="bold", color=p.RED)
    ax.annotate(f"{us[y1]:.0f}%", (y1, us[y1]), textcoords="offset points",
                xytext=(0, -12), ha="center", va="top", fontsize=8.4,
                fontweight="bold", color=p.RED)
    _foot(p, ax, f"IMF IMTS, goods only; partners ranked once on {y1}")

    ax = ig.slot("trade.lens", "Lens — goods balance: the United States "
                 "vs the rest (% of GDP)")
    gdp = dict(zip(*_yr(ctx, "international/gdp_usd.csv", "gdp_usd")))
    usd = dict(zip(*_yr(ctx, PT, "balance_usa_usd")))
    bwd = dict(zip(*_yr(ctx, PT, "balance_world_usd")))
    yrs = [y for y in sorted(usd) if y in gdp and y in bwd]
    us_b = [usd[y] / gdp[y] * 100 for y in yrs]
    rest_b = [(bwd[y] - usd[y]) / gdp[y] * 100 for y in yrs]
    ax.axhline(0, color=p.MUTED, lw=0.9, zorder=2)
    ctx.line(ax, yrs, us_b, p.GREEN, label="with the United States")
    ctx.line(ax, yrs, rest_b, p.RED, label="with the rest of the world")
    ig.add_recessions(ax, label=False)
    ax.set_ylabel("% of GDP", fontsize=8.6, color=p.MUTED)
    ax.legend(loc="center left", fontsize=8.0, frameon=False,
              bbox_to_anchor=(0.0, 0.33))
    _mark(ig, ax, "us_tariffs")
    ax.set_ylim(min(rest_b) * 1.25, max(us_b) * 1.25)
    _note(p, ax, 0.02, 0.96, "a surplus with one customer pays for a deficit "
          "with all the others", size=7.8)
    _finish(ctx, ig)


# ----------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p
    R = "markets/rates.csv"

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ey, ev = _yr(ctx, R, "target_rate_eoy")
    cy, cv = _yr(ctx, "macro/growth_prices.csv", "cpi_inflation_pct")
    ctx.line(ax, cy, cv, p.RED, lw=1.8, ms=3.2, label="CPI inflation, "
             "annual average")
    ctx.line(ax, ey, ev, p.NAVY, label="Target for the overnight rate, "
             "year-end")
    _bands_labelled_at(ig, ax, 0.80, p)
    ctx.endlabel(ax, ey, ev, p.NAVY, lambda v: f"{v:.2f}%", dy=8)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    _note(p, ax, 0.98, 0.90,
          f"{_at(ey, ev, 2007):.2f}% to {_at(ey, ev, 2009):.2f}% "
          "in sixteen months", ha="right")
    _mark(ig, ax, "hikes", dy=0.62)

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    y10, v10 = _yr(ctx, R, "yield_10y_avg")
    y2, v2 = _yr(ctx, R, "yield_2y_avg")
    ctx.line(ax, y2, v2, p.BLUE, lw=1.6, ms=3.0, label="2-year")
    ctx.line(ax, y10, v10, p.NAVY, label="10-year")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, y10, v10, p.NAVY, lambda v: f"{v:.2f}%", dy=8)
    ax.legend(loc="upper right", fontsize=8.0, frameon=False)
    ax.annotate("the curve inverted through the hikes",
                xy=(2023, _at(y2, v2, 2023)), xytext=(2011.0, 7.4),
                fontsize=8.0, color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    _foot(p, ax, "Bank of Canada, Government of Canada benchmark bonds")

    ax = ig.slot("markets.currency", "The Canadian dollar against the "
                 "US$ (index 2006 = 100, up = stronger)")
    H = "markets/usdcad_h10.csv"
    hy, hv = _yr(ctx, H, "cad_per_usd_avg")
    base = _at(hy, hv, W0)
    ix_y, ix_v = ctx.fx_index(dict(zip(hy, hv)))
    ctx.line(ax, ix_y, ix_v, p.FAINT, lw=1.3, ms=2.6,
             label="Federal Reserve H.10 noon rate (covers 2006–07)")
    # The Bank of Canada's own two series, each on the H.10 2006 base and
    # never joined: the noon rate to 2016 and the single daily rate from
    # 2017, computed differently.
    ny, nv = _yr(ctx, "markets/usdcad.csv", "usd_cad_noon_avg")
    dy, dv = _yr(ctx, "markets/usdcad.csv", "usd_cad_daily_avg")
    ctx.line(ax, ny, [base / v * 100 for v in nv], p.NAVY,
             dashed_partial=False, label="Bank of Canada noon rate "
             "(retired March 2017)")
    ctx.line(ax, dy, [base / v * 100 for v in dv], p.RED,
             label="Bank of Canada single daily rate (from 2017)")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "fx_break", dy=0.30)
    ax.legend(loc="lower left", fontsize=7.4, frameon=False)
    pk = max(zip(ix_y, ix_v), key=lambda t: t[1])
    ax.annotate(f"{pk[0]}: parity and above", pk,
                textcoords="offset points", xytext=(0, 8), ha="center",
                fontsize=8.2, fontweight="bold", color=p.NAVY)
    _foot(p, ax, "Bank of Canada series: two, computed differently, never "
          "spliced; both indexed on the H.10 2006 average")

    ax = ig.slot("markets.equities", "S&P/TSX composite in US$ vs the "
                 "S&P 500 (index 2006 = 100)")
    E = "markets/equities.csv"
    ty, tv = _yr(ctx, E, "tsx_usd_avg")
    sy, sv = _yr(ctx, E, "spx_usd_avg")
    tiy, tiv = ctx.index_2006(dict(zip(ty, tv)))
    siy, siv = ctx.index_2006(dict(zip(sy, sv)))
    ctx.line(ax, siy, siv, p.FAINT, lw=1.8, ms=3.0, ls="--",
             dashed_partial=False, label="S&P 500 (US$)")
    ctx.line(ax, tiy, tiv, p.RED, label="S&P/TSX composite, in US$")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, tiy, tiv, p.RED, lambda v: f"{v:.0f}", dy=-14)
    ctx.endlabel(ax, siy, siv, p.MUTED, lambda v: f"{v:.0f}", dy=6)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    m = ctx.rows(E) or {}
    months = int(float(m[max(m)]["months"]))
    _foot(p, ax, f"Yahoo Finance (not an official statistic); annual mean of "
          f"month-end closes, {max(m)}: {months} months")
    _finish(ctx, ig)


# ------------------------------------------------------------------ people
def plate_people(ctx, ig) -> None:
    p = ctx.p
    I = "social/income.csv"

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100, higher "
                 "= more unequal)")
    gy, gv = _yr(ctx, I, "gini")
    gv = [v * 100 for v in gv]
    wy, wv = _yr(ctx, "social/gini.csv", "gini")
    sy, sv = _yr(ctx, "social/gini_statcan.csv", "gini_aftertax")
    sv = [v * 100 for v in sv]
    ctx.line(ax, gy, gv, p.NAVY, label="OECD, disposable income "
             "(Canadian Income Survey)")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.6, ms=3.0, label="World Bank")
    ctx.line(ax, sy, sv, p.GOLD, lw=1.8, ms=3.2,
             label="StatCan, after-tax adjusted income")
    ig.add_recessions(ax, inside=True)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    # The dip is the panel's lowest point and the axes bottom is the
    # reference Gini floor: the label rides under the point, where the
    # lines never follow it.
    ax.annotate(f"{_at(gy, gv, 2020):.1f} in 2020: the pandemic "
                "benefits", (2020, _at(gy, gv, 2020)),
                textcoords="offset points", xytext=(0, -10), ha="center",
                va="top", fontsize=8.2, fontweight="bold", color=p.NAVY)
    _foot(p, ax, "three income definitions, three lines: the legend names "
          "each; they measure adjacent things, never one series twice")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    py, pv = _yr(ctx, I, "poverty_50_pct")
    ctx.line(ax, py, pv, p.RED, label="below half the median income (OECD)")
    wy, wv = _yr(ctx, "social/poverty.csv", "poverty_830_pct")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.6, ms=3.0,
             label="below US$8.30 a day (World Bank)")
    m1y, m1v = _yr(ctx, "social/poverty_statcan.csv", "mbm_2018_pct")
    m2y, m2v = _yr(ctx, "social/poverty_statcan.csv", "mbm_2023_pct")
    ctx.line(ax, m1y, m1v, p.GOLD, lw=2.0, ms=3.6,
             label="Market Basket Measure, 2018 base (StatCan)")
    ctx.line(ax, m2y, m2v, p.TEAL, lw=2.0, ms=3.6,
             label="Market Basket Measure, 2023 base (StatCan)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    both = [y for y in m1y if y in dict(zip(m2y, m2v))]
    gap = sum(_at(m2y, m2v, y) - _at(m1y, m1v, y) for y in both) / len(both)
    _note(p, ax, 0.02, 0.62, f"the official line is StatCan's Market Basket "
          "Measure — its 2018 and\n2023 bases are two lines, never one: "
          f"the newer basket reads {gap:.1f}\npoints higher across "
          f"{both[0]}–{both[-1]}", size=7.6)
    _foot(p, ax, "relative poverty from the OECD and the World Bank; the "
          "national definition (MBM) on its two bases, never rebased onto one line")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    M = "social/minimum_wage.csv"
    my, mv = _yr(ctx, M, "annual_cad")
    fx = dict(zip(*_yr(ctx, "markets/usdcad_h10.csv", "cad_per_usd_avg")))
    usd = [v / 12 / fx[y] for y, v in zip(my, mv)]
    ctx.line(ax, my, usd, p.GREEN_D, label="employment-weighted average of "
             "the provincial minimums")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, my, usd, p.GREEN_D, lambda v: f"US${v:,.0f}", dy=8)
    hy, hv = _yr(ctx, M, "hourly_cad")
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    _note(p, ax, 0.98, 0.04, f"C${hv[-1]:.2f} an hour in {hy[-1]}; no single "
          "national minimum —\neach province sets its own, converted at "
          "the annual average rate", ha="right", va="bottom", size=7.6)
    _foot(p, ax, "OECD minimum wages, at the Federal Reserve H.10 rate")

    ax = ig.slot("people.lens", "Lens — child and old-age poverty "
                 "(% below half the median income)")
    cy, cv = _yr(ctx, I, "child_poverty_50_pct")
    oy, ov = _yr(ctx, I, "old_age_poverty_50_pct")
    ctx.line(ax, cy, cv, p.GOLD, label="under 18")
    ctx.line(ax, oy, ov, p.PURPLE, label="over 65")
    ax.set_ylabel("% of people", fontsize=8.6, color=p.MUTED)
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "ccb")
    ax.set_ylim(0, max(cv + ov) * 1.3)
    ax.legend(loc="lower left", fontsize=7.8, frameon=False)
    _note(p, ax, 0.98, 0.04, f"under-18s: {_at(cy, cv, 2015):.1f}% in 2015, "
          f"{_at(cy, cv, 2020):.1f}% in 2020, {cv[-1]:.1f}% in {cy[-1]}",
          ha="right", va="bottom", size=7.6)
    _foot(p, ax, "OECD Income Distribution Database")
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "international/gdp_usd.csv", "gdp_usd")
    gv = [v / 1e9 for v in gv]
    ctx.line(ax, gy, gv, p.RED)
    ig.add_recessions(ax, inside=True)
    ctx.endlabel(ax, gy, gv, p.RED, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.30, "in US dollars at market rates: the 2015 dip "
          "is the Canadian\ndollar falling with the oil price, not output",
          size=7.8)

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "international/hdi.csv", "hdi")
    ctx.line(ax, hy, hv, p.GREEN_D, split_year=max(hy))
    ax.axhline(0.8, color=p.FAINT, lw=0.9, ls=":")
    ctx.endlabel(ax, hy, hv, p.GREEN_D, lambda v: f"{v:.3f}", dy=8)
    _note(p, ax, 0.98, 0.50, "0.800 and above = very high development",
          ha="right", va="top", size=7.8)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "one vintage (HDR 2025) throughout — the HDR recomputes the "
          "whole back-series")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index "
                 "(0–100, higher = cleaner)")
    cy, cv = _yr(ctx, "international/cpi.csv", "cpi_score")
    ctx.line(ax, cy, cv, p.NAVY, split_year=max(cy))
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{cv[0]:.0f} in {cy[0]}", (cy[0], cv[0]),
                textcoords="offset points", xytext=(0, 8), ha="center",
                fontsize=8.4, fontweight="bold", color=p.NAVY)
    ctx.endlabel(ax, cy, cv, p.NAVY, lambda v: f"{v:.0f}", dy=8)
    _note(p, ax, 0.02, 0.30, "2012 method; the earlier 0–10 scores are not\n"
          "in Transparency International's time series", size=7.6)

    ax = ig.slot("world.reserves", "Official reserves (US$ bn, year-end)")
    ry, rv = _yr(ctx, "international/reserves.csv", "reserves_usd")
    rv = [v / 1e9 for v in rv]
    ctx.line(ax, ry, rv, p.GREEN_D)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.GREEN_D, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, "modest for a G7 economy — the dollar floats, "
          "so there is\nno peg to defend", size=7.8)
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p
    D = "social/demography.csv"
    POP = "social/population_statcan.csv"
    COMP = "social/components_statcan.csv"
    pop = dict(zip(*_yr(ctx, "international/population.csv", "population",
                        since=2005)))
    npop = dict(zip(*_yr(ctx, POP, "population_july1", since=2005)))

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    iy, iv = ctx.index_2006(pop)
    iy, iv = zip(*[(y, v) for y, v in zip(iy, iv) if y >= W0])
    ctx.line(ax, iy, iv, p.BLUE, label="World Bank mid-year (UN WPP)")
    niy, niv = ctx.index_2006(npop)
    niy, niv = zip(*[(y, v) for y, v in zip(niy, niv) if y >= W0])
    ctx.line(ax, niy, niv, p.NAVY, lw=1.6,
             ms=2.6, ls=(0, (1, 1.4)), dashed_partial=False,
             label="StatCan July 1 estimate (17-10-0009)")
    ig.add_recessions(ax, label=False)
    last = max(pop)
    # The index line runs at the top of the reference range by 2025, so
    # the level label goes under the line's end and hangs right of it —
    # inside the axes, clear of both the line and the ceiling.
    ctx.endlabel(ax, iy, iv, p.BLUE, lambda v: f"{pop[last] / 1e6:.1f}M",
                 dy=-14, ha="left")
    g23 = (pop[2023] / pop[2022] - 1) * 100
    _note(p, ax, 0.02, 0.96, f"+{g23:.1f}% in 2023 alone, unmatched in the "
          "G7 —\nmost of it non-permanent residents")
    ax.legend(loc="lower right", fontsize=7.6, frameon=False)
    _foot(p, ax, "the national line is StatCan's July 1 vintage — the one "
          "that separates non-permanent residents; the UN line is mid-year")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    ty, tv = _yr(ctx, D, "fertility")
    ax.axhline(2.1, color=p.FAINT, lw=1.0, ls=":")
    ctx.line(ax, ty, tv, p.PURPLE, label="World Bank")
    sty, stv = _yr(ctx, "social/demography_statcan.csv", "total_fertility_rate")
    _natl(ctx, ax, sty, stv, p.NAVY, "StatCan (13-10-0418)")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ty, tv, p.PURPLE, lambda v: f"{v:.2f}", dy=-14)
    _note(p, ax, 0.98, 0.74, "2.1 = replacement", ha="right", size=7.8)
    _note(p, ax, 0.02, 0.18, f"{max(tv):.2f} at the {ty[tv.index(max(tv))]} "
          f"peak; {tv[-1]:.2f} in {ty[-1]}, among the lowest in the G7",
          va="bottom", size=7.8)
    ax.legend(loc="upper left", fontsize=7.6, frameon=False)
    _foot(p, ax, "World Bank redistribution; StatCan's own registration-"
          "based rate — the two agree to a hundredth")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    by, bv = _yr(ctx, D, "birth_rate_per_1000")
    dy, dv = _yr(ctx, D, "death_rate_per_1000")
    ctx.line(ax, by, bv, p.GREEN, label="Births (World Bank)")
    ctx.line(ax, dy, dv, p.RED_D, label="Deaths (World Bank)")
    sby, sbv = _yr(ctx, "social/demography_statcan.csv", "birth_rate_per_1000")
    _natl(ctx, ax, sby, sbv, p.GREEN_D, "Births (StatCan, published rate)")
    sdy, sdv = ctx.per_1000(_yr(ctx, COMP, "deaths", since=W0), npop)
    _natl(ctx, ax, sdy, sdv, p.GOLD,
          "Deaths (StatCan July–June ÷ July 1 population)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.96, "the gap is natural increase, and it is closing: "
          f"{bv[0] - dv[0]:.1f} per 1,000 in {by[0]},\n"
          f"{bv[-1] - dv[-1]:.1f} in {by[-1]}", size=7.8)
    _foot(p, ax, "World Bank rates; StatCan's crude birth rate as published, "
          "its deaths counted July–June over that period's July 1 estimate")

    ax = ig.slot("demography.natural_migration", "Natural increase and net "
                 "migration (per 1,000 people)")
    ni_y = [y for y in by if y in dict(zip(dy, dv))]
    ni_v = [_at(by, bv, y) - _at(dy, dv, y) for y in ni_y]
    my, mv = _yr(ctx, D, "net_migration")
    ry, rv = ctx.per_1000(dict(zip(my, mv)), pop)
    ctx.bars(ax, ni_y, ni_v, lambda v: p.GREEN)
    ctx.line(ax, ry, rv, p.BLUE, label="Net migration (UN estimate)")
    _barkey(ax, p.GREEN, "Natural increase (World Bank rates)")
    comp = ctx.table(COMP)
    inc, mig = {}, {}
    for y, b, d, im, ne, npr in zip(comp["year"], comp["births"],
                                    comp["deaths"], comp["immigrants"],
                                    comp["net_emigration"],
                                    comp["net_non_permanent_residents"]):
        if y >= W0:
            inc[y] = b - d
            mig[y] = im - ne + npr
    sny, snv = ctx.per_1000(inc, npop)
    smy, smv = ctx.per_1000(mig, npop)
    _natl(ctx, ax, sny, snv, p.GREEN_D,
          "Natural increase (StatCan components)")
    _natl(ctx, ax, smy, smv, p.NAVY,
          "Net migration (StatCan components)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    pk = max(zip(ry, rv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f} in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 7), ha="center", fontsize=8.4, fontweight="bold",
                color=p.BLUE)
    spk = max(zip(smy, smv), key=lambda t: t[1])
    ax.annotate(f"{spk[1]:.1f} in {spk[0]}", spk, textcoords="offset points",
                xytext=(0, -13), ha="center", va="top", fontsize=8.4,
                fontweight="bold", color=p.NAVY)
    _note(p, ax, 0.98, 0.04, "StatCan components are July–June years over "
          "the July 1 population\nof the same period start — the vintage "
          "the record 2023 peak lives in", ha="right", va="bottom", size=7.6)
    _foot(p, ax, "World Bank and UN estimates, beside StatCan's own "
          "components of growth (17-10-0008) — each pair, never one line")
    _finish(ctx, ig)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    S = "social/security.csv"
    C = "social/causes_of_death.csv"

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000, log "
                 "scale)")
    hy, hv = _yr(ctx, S, "homicide_per_100k")
    ctx.line(ax, hy, hv, p.RED, split_year=max(hy), label="UNODC")
    sy, sv = _yr(ctx, "social/security_statcan.csv", "homicide_rate_per_100k")
    ctx.line(ax, sy, sv, p.NAVY, lw=1.6, ms=2.6, ls=(0, (1, 1.4)),
             split_year=max(sy), label="Police-reported (StatCan UCR)")
    ig.add_recessions(ax, inside=True)
    lo = min(zip(hy, hv), key=lambda t: t[1])
    hi = max(zip(hy, hv), key=lambda t: t[1])
    ax.annotate(f"{lo[1]:.2f} in {lo[0]}", lo, textcoords="offset points",
                xytext=(0, -12), ha="center", va="top", fontsize=8.2,
                fontweight="bold", color=p.RED)
    ax.annotate(f"{hi[1]:.2f} in {hi[0]}", hi, textcoords="offset points",
                xytext=(0, 12), ha="center", va="bottom", fontsize=8.2,
                fontweight="bold", color=p.RED)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    apart = max(abs(_at(sy, sv, y) - v) for y, v in zip(hy, hv) if y in sy)
    _note(p, ax, 0.98, 0.10, f"police-reported incidents and UNODC's "
          "harmonised count differ\nby at most "
          f"{apart:.2f} per 100,000 — two counts of an adjacent thing, "
          "never one line", ha="right", va="bottom", size=7.6)
    _foot(p, ax, "UNODC via the World Bank, beside StatCan's police-reported "
          "table (35-10-0068); the coroner-registered count is a third")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    wy, wv = _yr(ctx, S, "suicide_per_100k")
    oy, ov = _yr(ctx, C, "self_harm_per_100k")
    ctx.line(ax, oy, ov, p.PURPLE, split_year=max(oy),
             label="death registrations, crude (OECD)")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.6, ms=3.0, split_year=max(wy),
             label="WHO estimate, age-standardised")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.10, "the latest registration years can rise as "
          "coroners'\ninvestigations close", va="bottom", size=7.6)
    _foot(p, ax, "OECD (Statistics Canada's registrations) and WHO")

    ax = ig.slot("security.road_deaths", "Road traffic deaths "
                 "(per 100,000)")
    ry, rv = _yr(ctx, S, "road_deaths_per_100k")
    ty, tv = _yr(ctx, C, "transport_per_100k")
    ctx.line(ax, ry, rv, p.NAVY, split_year=max(ry),
             label="road traffic, WHO estimate")
    ctx.line(ax, ty, tv, p.FAINT, lw=1.6, ms=3.0, split_year=max(ty),
             label="all transport accidents, death registrations (OECD)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.64, f"WHO's road series ends in {max(ry)}; the "
          "registrations include\nrail, water and air, so they sit a "
          "little above it", size=7.6)
    _foot(p, ax, "WHO via the World Bank, and the OECD")

    ax = ig.slot("security.lens", "Lens — apparent opioid toxicity deaths "
                 "(per 100,000)")
    O = "social/opioids.csv"
    py, pv = _yr(ctx, O, "rate_per_100k")
    ctx.bars(ax, py, pv, lambda v: p.RED_D)
    ax.set_ylabel("per 100,000", fontsize=8.6, color=p.MUTED)
    ig.add_recessions(ax, label=False)
    ny, nv = _yr(ctx, O, "deaths")
    pk = max(zip(py, pv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}", pk, textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=8.6, fontweight="bold",
                color=p.RED_D)
    ax.set_ylim(0, pk[1] * 1.45)
    hom = dict(zip(hy, hv))
    ratio = pk[1] / hom[pk[0]] if pk[0] in hom else None
    _note(p, ax, 0.02, 0.96, f"{_at(ny, nv, pk[0]):,.0f} deaths in {pk[0]}"
          + (f", {ratio:.0f} times the homicide rate" if ratio else "")
          + f";\nthe national count begins in {py[0]}", size=7.8)
    _foot(p, ax, "PHAC and the provincial coroners; published crude rate")
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    C = "social/causes_of_death.csv"
    npop_m = dict(zip(*_yr(ctx, "social/population_statcan.csv",
                           "population_july1", since=2005)))

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000 people)")
    cy, cv = _yr(ctx, C, "all_causes_per_100k")
    cv = [v / 100 for v in cv]
    ctx.line(ax, cy, cv, p.RED_D, split_year=max(cy),
             label="OECD (registrations ÷ its own population)")
    scy = dict(zip(*_yr(ctx, "social/mortality_statcan.csv",
                        "deaths_all_causes", since=2005)))
    scy2, scv2 = ctx.per_1000(scy, npop_m)
    _natl(ctx, ax, scy2, scv2, p.NAVY,
          "StatCan deaths ÷ July 1 population")
    ig.add_recessions(ax, inside=True)
    # The line falls away from the 2022 peak into its last year: the end
    # label clears the tail it would otherwise sit on.
    ctx.endlabel(ax, cy, cv, p.RED_D, lambda v: f"{v:.2f}", dy=18)
    _note(p, ax, 0.02, 0.96, "rising for twenty years as the baby boom ages, "
          f"with a {max(cv):.2f}\npeak in {cy[cv.index(max(cv))]}")
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _foot(p, ax, "Statistics Canada's death registrations, as published by "
          "the OECD — and divided again here by StatCan's own July 1 counts")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above the 2015–2019 average)")
    dy, dv = _yr(ctx, C, "deaths")
    d = dict(zip(dy, dv))
    base = sum(d[y] for y in range(2015, 2020)) / 5
    ex_y = [y for y in dy if y >= 2015]
    ex_v = [(d[y] / base - 1) * 100 for y in ex_y]
    ctx.bars(ax, ex_y, ex_v, lambda v: p.RED if v > 0 else p.GREEN)
    sd = dict(zip(*_yr(ctx, "social/mortality_statcan.csv",
                       "deaths_all_causes", since=2015)))
    sbase = sum(sd[y] for y in range(2015, 2020)) / 5
    _natl(ctx, ax, sorted(sd), [(sd[y] / sbase - 1) * 100 for y in sorted(sd)],
          p.NAVY, "StatCan's own registrations, same house rule")
    _barkey(ax, p.RED, "OECD's redistribution of the same registrations")
    ig.add_recessions(ax, label=False)
    pk = max(zip(ex_y, ex_v), key=lambda t: t[1])
    ax.annotate(f"+{pk[1]:.1f}%", pk, textcoords="offset points",
                xytext=(0, 9), ha="center", fontsize=8.6, fontweight="bold",
                color=p.RED)
    _note(p, ax, 0.02, 0.96, f"deaths counted against {base:,.0f} a year, the "
          "2015–2019 mean;\nnot adjusted for a population that grew and "
          "aged", size=7.8)
    ax.legend(loc="lower right", fontsize=7.4, frameon=False)
    _foot(p, ax, "both bases are 2015–2019 means of their own counts; the "
          "house rule is unadjusted, and the panel says so")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    vy, vv = _yr(ctx, C, "covid19_per_100k")
    ctx.bars(ax, vy, vv, lambda v: p.PURPLE)
    _barkey(ax, p.PURPLE, "OECD's published rate")
    cvy, cvv = ctx.per_100k(dict(zip(*_yr(ctx, "social/mortality_statcan.csv",
                                          "deaths_covid_19", since=2020))),
                            npop_m)
    _natl(ctx, ax, cvy, cvv, p.NAVY, "StatCan deaths ÷ July 1 population")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"the worst year was {vy[vv.index(max(vv))]}, "
          "the year of Omicron,\nnot the first year of the pandemic",
          size=7.8)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _foot(p, ax, "OECD (Statistics Canada's registrations) and StatCan's own "
          "counts over the July 1 estimate — the codes follow the coroner")

    ax = ig.slot("mortality.lens", "Lens — the two big killers "
                 "(per 100,000)")
    ky, kv = _yr(ctx, C, "cancer_per_100k")
    hy, hv = _yr(ctx, C, "circulatory_per_100k")
    ctx.line(ax, ky, kv, p.NAVY, split_year=max(ky), label="Cancer")
    ctx.line(ax, hy, hv, p.RED, split_year=max(hy),
             label="Heart and circulatory diseases")
    ig.add_recessions(ax, label=False)
    ax.set_ylim(0, max(kv + hv) * 1.3)
    ax.legend(loc="lower left", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.96, "crude rates: an ageing population holds them "
          "up even as\nage-specific risk falls", size=7.8)
    _foot(p, ax, "OECD (Statistics Canada's registrations)")
    _finish(ctx, ig)


# ------------------------------------------------------------------ credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP, "
                 "year-end)")
    hy, hv = _yr(ctx, "credit/household_credit.csv", "hh_credit_pct_gdp_q4")
    ctx.line(ax, hy, hv, p.RED, label="BIS, share of GDP")
    ig.add_recessions(ax, label=False)
    pk = max(zip(hy, hv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=8.6, fontweight="bold",
                color=p.RED)
    _note(p, ax, 0.98, 0.16, f"{hv[0]:.0f}% in {hy[0]}: cheap credit put "
          "Canada\namong the most indebted\nhouseholds in the G7", size=7.8,
          ha="right")
    ax.legend(loc="lower left", fontsize=7.4, frameon=False)
    _foot(p, ax, "BIS credit to households over GDP; StatCan's disposable-"
          "income ratio is retained in the source file but not mixed onto "
          "this canonical GDP axis")

    ax = ig.slot("credit.lending_rate", "Mortgage rates vs the policy "
                 "rate (%)")
    M = "credit/mortgage_rates.csv"
    sy, sv = _yr(ctx, M, "posted_5y_avg")
    ny, nv = _yr(ctx, M, "new_mortgage_rate")
    ay, av = _yr(ctx, "markets/rates.csv", "target_rate_avg")
    ctx.line(ax, sy, sv, p.FAINT, lw=1.6, ms=3.0,
             label="5-year rate the banks post")
    ctx.line(ax, ny, nv, p.RED, label="rate charged on new mortgages")
    ctx.line(ax, ay, av, p.NAVY, lw=1.8, ms=3.2,
             label="policy rate, annual average")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    _foot(p, ax, f"Bank of Canada; new-mortgage rates from {ny[0]}, weighted "
          "by the funds advanced")

    ax = ig.slot("credit.npl", "Non-performing loans (% of bank loans)")
    qy, qv = _yr(ctx, "credit/npl.csv", "npl_pct")
    ctx.line(ax, qy, qv, p.PURPLE, label="banks, IMF Financial Soundness "
             "Indicators")
    ig.add_recessions(ax, label=False)
    pk = max(zip(qy, qv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.2f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=8.4, fontweight="bold",
                color=p.PURPLE)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    lo = min(zip(qy, qv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, f"never above {pk[1]:.1f}% of loans; {qv[-1]:.2f}% "
          f"in {qy[-1]},\nup from a low of {lo[1]:.2f}% in {lo[0]}", size=7.8)
    _foot(p, ax, "World Bank / IMF FSI")

    ax = ig.slot("credit.lens", "Lens — what servicing the debt costs "
                 "(% of disposable income)")
    dy, dv = _yr(ctx, "credit/debt_service.csv", "hh_dsr_pct_q4")
    ax.set_ylabel("% of disposable income", fontsize=8.6, color=p.MUTED)
    ctx.line(ax, dy, dv, p.GOLD, label="BIS model, interest + principal")
    sy, sv = _yr(ctx, "credit/debt_service_statcan.csv", "hh_dsr_pct_q4")
    my, mv = _yr(ctx, "credit/debt_service_statcan.csv",
                 "mortgage_dsr_pct_q4")
    _natl(ctx, ax, sy, sv, p.NAVY, "StatCan's own payments measure")
    ctx.line(ax, my, mv, p.BLUE, lw=1.8, ms=3.2,
             label="the mortgage payments alone (StatCan)")
    ig.add_recessions(ax, label=False)
    ax.set_ylim(0, max(dv + sv) * 1.35)
    ax.legend(loc="lower left", fontsize=7.4, frameon=False)
    pk = max(zip(dy, dv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, f"{pk[1]:.1f}% in {pk[0]}: the hikes reached "
          "the payments as mortgages renewed", size=7.8)
    ym = max(set(sy) & set(my))
    _note(p, ax, 0.98, 0.045, f"in {ym}, mortgages alone are "
          f"{mv[my.index(ym)]:.1f} of the {sv[sy.index(ym)]:.1f} points "
          "StatCan counts", size=7.8, ha="right", va="bottom")
    _foot(p, ax, "BIS models the ratio on an assumed maturity; StatCan "
          "measures what was actually paid — the two disagree by design")
    _finish(ctx, ig)


# --------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    pop = dict(zip(*_yr(ctx, "international/population.csv", "population",
                        since=2005)))
    last_pop = max(pop)

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    ctx.pending(ax)
    _foot(p, ax, "StatCan gross flows not staged; PR admissions stay in "
          "the lens")

    ay, av = _yr(ctx, "migration/pr_admissions.csv", "admissions",
                 until=last_pop)
    ry, rv = ctx.per_1000(dict(zip(ay, av)), pop)

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    D = "social/demography.csv"
    my, mv = _yr(ctx, D, "net_migration")
    ny, nv = ctx.per_1000(dict(zip(my, mv)), pop)
    ctx.bars(ax, ny, nv, lambda v: p.BLUE)
    ig.add_recessions(ax, label=False)
    pk = max(zip(ny, nv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}", pk, textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=8.6, fontweight="bold",
                color=p.BLUE)
    _note(p, ax, 0.02, 0.96, "UN estimate, permanent and temporary residents "
          "together;\nStatCan's own components of growth are in the "
          "demography plate", size=7.8)
    _foot(p, ax, "World Bank (UN World Population Prospects) ÷ the mid-year "
          "population")

    ax = ig.slot("migration.foreign_born", "Foreign-born share of the "
                 "population (%)")
    fy, fv = _yr(ctx, "social/migrant_stock.csv", "migrant_share_pct")
    ctx.line(ax, fy, fv, p.TEAL, marker="o", ms=6, split_year=max(fy),
             label="international migrant stock (UN DESA)")
    ig.add_recessions(ax, label=False)
    for y, v in zip(fy, fv):
        ax.annotate(f"{v:.1f}%", (y, v), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8.2,
                    fontweight="bold", color=p.TEAL)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    _foot(p, ax, "UN DESA via the World Bank, five-yearly. The census "
          "share is Statistics Canada's — pending")

    ax = ig.slot("migration.lens", "Study permits signed per year — "
                 "a flow (per 1,000 people)")
    sy, sv = _yr(ctx, "migration/study_permits.csv", "permit_holders",
                 until=last_pop)
    py, pv = ctx.per_1000(dict(zip(sy, sv)), pop)
    ctx.bars(ax, py, pv, lambda v: p.TEAL)
    ctx.line(ax, ry, rv, p.RED, lw=1.8, ms=3.2,
             label="Permanent residents admitted per year")
    ax.set_ylabel("per 1,000 people", fontsize=8.6, color=p.MUTED)
    ig.add_recessions(ax, label=False)
    pk = max(zip(sy, sv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:,.0f}", (pk[0], _at(py, pv, pk[0])),
                textcoords="offset points", xytext=(0, 4), ha="center",
                fontsize=8.6, fontweight="bold", color=p.TEAL)
    _mark(ig, ax, "permit_cap")
    ax.set_ylim(0, max(pv) * 1.45)
    _note(p, ax, 0.02, 0.96, "permits signed in the year — a permit runs "
          "for years, so the\nstock of students present is several times "
          "larger", size=7.8)
    ax.legend(loc="lower left", fontsize=7.5, frameon=False)
    _foot(p, ax, "IRCC policy flows ÷ the mid-year population; admissions "
          "are a subset of immigration, not the canonical gross flow")
    _finish(ctx, ig)


# The plates, in the order the page lists them; the ids are the spine's
# chapter numbers, and the five that existed before keep theirs.
PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Canadian Economy — Growth, Income, Prices and Jobs",
         subtitle="World Bank and ILO lines with Statistics Canada's own "
                  "series beside them — growth, prices and the Labour "
                  "Force Survey.",
         source="Sources: World Bank WDI · ILO · Statistics Canada "
                "36-10-0699, 18-10-0005, 14-10-0327",
         alt="Four panels on the Canadian economy, 2006–2025. Real GDP "
             "fell 2.9% in 2009 and 5.0% in 2020, on StatCan's own "
             "chained-FCE2017 series 4.7% in 2022; GDP per person in US "
             "dollars dropped from about 51,000 to 44,000 between 2014 and "
             "2015 as the oil price took the Canadian dollar down, and "
             "stands near 55,700 in 2025; consumer price inflation peaked "
             "at 6.8% in 2022 against the Bank of Canada's 2% target; "
             "unemployment peaked at 9.7% in 2020, and the Labour Force "
             "Survey reads 5.7% in 2019."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — All Governments, and Ottawa's Own Books",
         subtitle="General government on the IMF's basis, calendar years; "
                  "the federal accounts beside it, by fiscal year.",
         source="Sources: IMF WEO, Fiscal Monitor and GFS · Department of "
                "Finance Canada — Fiscal Reference Tables, November 2025",
         alt="Four panels on Canadian public finances. General-government "
             "expenditure jumps to 52.4% of GDP in 2020 against revenue near "
             "41%; the general-government balance reaches −10.9% of GDP in "
             "2020 while the federal budgetary balance reaches −14.8% in "
             "fiscal 2020-21, the largest federal deficit in peacetime; "
             "gross general-government debt is 113.6% of GDP in 2025; the "
             "federal accumulated-deficit level is quoted only as context, "
             "not overlaid on the canonical gross axis; interest paid by all "
             "governments returns to 3.5% of GDP."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Where the Money Goes — Spending by Function and Investment",
         subtitle="General-government spending by function (IMF COFOG), "
                  "and the economy's and the state's investment rates.",
         source="Sources: IMF GFS (COFOG) · World Bank WDI · OECD National "
                "Accounts · Department of Finance Canada",
         alt="Four panels on spending. General-government outlays by "
             "function reach 50.5% of GDP in 2020, social protection the "
             "largest group at about 12% of GDP in 2024; whole-economy "
             "investment runs between 22% and 25% of GDP; public "
             "investment peaks at 4.8% of GDP in 2010 and is 4.2% in 2025."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — One Customer, and Everyone Else",
         subtitle="Exports and imports on the national-accounts basis, "
                  "StatCan's own pair beside them, and where the goods go.",
         source="Sources: World Bank WDI · IMF International Trade in "
                "Goods (IMTS) · Statistics Canada 36-10-0699",
         alt="Four panels on Canadian trade. Exports and imports of goods "
             "and services each run near a third of GDP; the balance swings "
             "with the oil price, and on StatCan's own national accounts "
             "the goods-and-services gap is −0.2% of GDP in 2024; the "
             "United States takes about 82% of "
             "Canada's goods exports in 2006 and 72% in 2025, with the "
             "United Kingdom, China, Japan and the Netherlands far behind; "
             "the goods surplus with the US pays for a deficit with the rest "
             "of the world."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Money & Markets — the Policy Rate, Bonds, the Dollar and "
               "the TSX",
         subtitle="The Bank of Canada's rates, the Canadian dollar on two "
                  "never-spliced series, and Toronto's index in US dollars.",
         source="Sources: Bank of Canada — Valet · Federal Reserve H.10 · "
                "World Bank WDI · Yahoo Finance (index, not official)",
         alt="Four panels on Canadian markets. The overnight target falls "
             "from 4.25% in 2007 to 0.25% in 2009, rises to 5% by 2023 "
             "against inflation that peaked at 6.8%, and is 2.25% in 2026; "
             "ten-year yields follow; the Canadian dollar, indexed to 2006, "
             "peaks above parity in 2011 and weakens to about 81 by 2025; "
             "the S&P/TSX in US dollars more than doubles from 2006 while "
             "the S&P 500 rises more than fivefold."),
    dict(id="06", slug="people", topic="people", builder=plate_people,
         title="People — Inequality, Poverty and the Minimum Wage",
         subtitle="The OECD's and the World Bank's readings beside "
                  "Statistics Canada's own survey lines — three Gini "
                  "readings and two MBM bases.",
         source="Sources: OECD income and minimum-wage tables · World "
                "Bank PIP · Federal Reserve H.10 · Statistics Canada "
                "11-10-0134, 11-10-0135",
         alt="Four panels on living standards. The Gini of disposable "
             "income falls from about 32 to 28 in 2020 and is near 31 in "
             "2023, while StatCan's own after-tax Gini reads 28.1 in 2020 "
             "and 30.1 in 2023; relative poverty dips to 8.6% in 2020, and "
             "StatCan's own Market Basket Measure is drawn on two bases "
             "that are never joined; the employment-weighted minimum wage "
             "reaches about US$2,050 a "
             "month in 2025; child poverty falls from 17% in 2015 to 7% in "
             "2020 after the Canada Child Benefit, and is back at 14% in "
             "2023."),
    dict(id="07", slug="world", topic="world", builder=plate_world,
         title="Canada in the World — Size, Development, Integrity and "
               "Reserves",
         subtitle="GDP and reserves in US dollars, the UNDP's development "
                  "index and Transparency International's score.",
         source="Sources: World Bank WDI · UNDP HDR 2025 · Transparency "
                "International CPI 2025",
         alt="Four panels on Canada among the world's economies. GDP is "
             "about US$2.3 trillion in 2025; the Human Development Index "
             "is 0.939 in 2023; the Corruption Perceptions Index falls "
             "from 84 in 2012 to 75 in 2025; official reserves reach "
             "US$126 billion."),
    dict(id="08", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — the Fastest-Growing Population in the G7",
         subtitle="Population, fertility, births, deaths and migration: "
                  "the World Bank's lines with StatCan's July 1 vintage "
                  "and growth components beside them.",
         source="Sources: World Bank WDI (UN World Population Prospects) "
                "· Statistics Canada 17-10-0009, 17-10-0008, 13-10-0418",
         alt="Four panels on Canada's population. It grows from 32.6 "
             "million in 2006 to 41.7 million in 2025, an index of 128, "
             "with 2.8% growth in 2023 alone; fertility falls from 1.70 in "
             "2008 to 1.25 in 2024, StatCan's own rate reading 1.26; "
             "births and deaths per 1,000 converge, StatCan's crude rates "
             "computed over its July 1 counts; "
             "net migration reaches about 12 per 1,000 people in 2022 while "
             "natural increase shrinks toward one, and StatCan's components "
             "show the non-permanent-resident surge."),
    dict(id="09", slug="security", topic="security", builder=plate_security,
         title="Security — Homicide, Suicide, the Roads and the Opioid "
               "Crisis",
         subtitle="Deaths per 100,000 people from UNODC, the WHO, the "
                  "OECD's cause-of-death tables and PHAC.",
         source="Sources: UNODC and WHO via the World Bank · OECD Health "
                "Statistics · Public Health Agency of Canada · Statistics "
                "Canada 35-10-0068",
         alt="Four panels on violent and accidental death. The homicide "
             "rate runs between about 1.4 and 2.3 per 100,000; suicide "
             "near 11 to 12; road deaths fall from 9 to about 5; apparent "
             "opioid toxicity deaths rise from 7.8 per 100,000 in 2016 to "
             "20.2 in 2023, then fall to 13.7 in 2025."),
    dict(id="10", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — Deaths, the Pandemic Excess and the Big Killers",
         subtitle="Registered deaths by underlying cause, as Statistics "
                  "Canada reports them to the OECD.",
         source="Sources: OECD Health Statistics (Statistics Canada death "
                "registrations) · Statistics Canada 13-10-0394, 17-10-0009",
         alt="Four panels on mortality. The crude death rate rises from 7.0 "
             "per 1,000 in 2006 to 8.7 in 2022; deaths run 22% above the "
             "2015–2019 average in 2022; COVID-19 as the underlying cause "
             "kills 51 per 100,000 in 2022, more than in 2020; cancer and "
             "circulatory diseases stay near 210–220 and 190–200 per "
             "100,000."),
    dict(id="11", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — Household Debt and What It Costs",
         subtitle="Household debt from the BIS on the canonical GDP basis, "
                  "and servicing costs measured twice.",
         source="Sources: BIS · Bank of Canada — Valet · World Bank / IMF "
                "Financial Soundness Indicators · Statistics Canada "
                "38-10-0235, 11-10-0065",
         alt="Four panels on household credit. Household debt climbs from "
             "76% of GDP in 2006 to 113% in 2020 and is about 100% in 2025, "
             "with StatCan's differently denominated debt-to-income ratio "
             "kept in the source file rather than overlaid; "
             "the rate on new mortgages rises from about 2% in 2021 to 5.8% "
             "in 2023; non-performing bank loans peak at 1.3% in 2009; the "
             "debt service ratio reaches 14.6% of disposable income in "
             "2023, and StatCan's own payments measure shows mortgages as "
             "about half of it."),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — Who Arrives, and How the Policy Reversed",
         subtitle="Comparable gross flows are pending; admissions, permits "
                  "and net migration remain distinct measures.",
         source="Sources: IRCC open data · World Bank WDI (UN WPP, "
                "UN DESA)",
         alt="Four panels on Canadian migration, per 1,000 people. The "
             "canonical gross immigration and emigration pair is pending; "
             "permanent-resident admissions are retained in the policy lens, "
             "rising to 480,955 people in 2024 before being cut; net "
             "migration peaks near 12 per 1,000 in 2022; the foreign-born "
             "share is about 22% of the population; study permits signed "
             "peak at 17.5 per 1,000 in 2023, a flow, not the stock."),
)
