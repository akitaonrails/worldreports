"""The taiwan plates, on the plate spine.

Every plate declares its topic and claims its four panels by slot key, in
the spine's order, so a Taiwanese panel sits over the same panel of every
other country in the comparison viewer: same indicator, same unit, same
y-scale (PLATE_SPINE.md, core/spine.py).

Twelve chapters. The World Bank, the IMF and the UN do not carry Taiwan, so
there is no harmonised second series to lean on: the canonical lines are
Taiwan's own publishers — DGBAS (行政院主計總處), the Central Bank (CBC),
the Ministry of Finance (MOF) — and each label names which. Where two
official publishers measure one idea differently (DGBAS vs CBC inflation,
customs vs balance-of-payments trade, accrual vs cash books, the index's
annual average vs its year-end close), both ride as clearly labelled
lines and are never spliced. Gaps are `ctx.pending` with the reason in
the panel's footer and DATA_NOTES.md; nothing is invented.

One convention worth naming:

- **Notes read their numbers from the CSVs** at build time, so a refetch
  that moves a figure moves the sentence with it.
"""
from __future__ import annotations

import matplotlib.ticker as mticker

from core import spine
from core.sideload import sibling

events = sibling(__file__, "events")

W0 = 2006        # the shared plate window opens here


# ------------------------------------------------------------- small helpers
def _yr(ctx, rel: str, col: str, since: int = W0, until: int | None = None):
    """(years, values) from a calendar-year CSV, blanks dropped."""
    t = ctx.table(rel)
    if not t or col not in t:
        return [], []
    yrs, vals = ctx.series(t, col)
    keep = [(y, v) for y, v in zip(yrs, vals)
            if y >= since and (until is None or y <= until)]
    return [y for y, _ in keep], [v for _, v in keep]


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


def _second(ctx, ax, years, vals, color, label, **kw):
    """A second official reading riding beside the canonical line.

    Thin, small markers, dotted: the named series stays the plate's line
    and the other publisher's number is visibly the second reading, never
    a continuation of the first.
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
    for a slot-1 panel whose data fill the bottom where add_recessions
    puts the names."""
    ig.add_recessions(ax, label=False)
    for start, end, name in ig.country.recessions:
        ax.text((start + end) / 2, y, name, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=8, color=p.MUTED,
                style="italic")


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(a)


def _pct_of_gdp(ctx, gdp_rel="economy/gdp.csv"):
    """{year: GDP, million NTD}, for every % of GDP division on the plate."""
    return dict(zip(*_yr(ctx, gdp_rel, "gdp_nominal_ntd_mn")))


# ------------------------------------------------------------------ economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p
    G = "economy/gdp.csv"
    C = "economy/cpi.csv"
    CC = "economy/cpi_yoy_cbc.csv"

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, G, "real_growth_pct")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.RED)
    _barkey(ax, p.GREEN, "DGBAS national accounts (A018101010)")
    _bands_labelled_at(ig, ax, 0.02, p)
    v09 = _at(gy, gv, 2009)
    ax.annotate(f"2009: {v09:.1f}%", (2009, v09), textcoords="offset points",
                xytext=(0, -4), ha="center", va="top", fontsize=8.6,
                fontweight="bold", color=p.RED)
    v25 = _at(gy, gv, 2025)
    ax.annotate(f"2025: {v25:+.1f}%", (2025, v25), textcoords="offset points",
                xytext=(-2, 4), ha="right", va="bottom", fontsize=8.6,
                fontweight="bold", color=p.GREEN_D)
    _note(p, ax, 0.30, 0.96, f"{_at(gy, gv, 2020):+.1f}% in 2020 — COVID never "
          "turned a year negative,\nso it gets no band (see DATA_NOTES)")
    ax.legend(loc="lower right", fontsize=7.6, frameon=False)
    _foot(p, ax, "DGBAS national accounts; the band is dated off the staged "
          "GDP vintage — 2008Q3–2009Q3 negative year on year")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, G, "gdp_per_capita_usd")
    ctx.line(ax, py, pv, p.RED)
    ctx.endlabel(ax, py, pv, p.RED, lambda v: f"{v:,.0f}", dy=8)
    _note(p, ax, 0.02, 0.30, f"more than doubles in the window: US${pv[0]:,.0f} "
          f"in {W0} to US${pv[-1]:,.0f} in {py[-1]}")
    _foot(p, ax, "DGBAS, at DGBAS's own average exchange rate")

    ax = ig.slot("economy.inflation", "Consumer price inflation (% per year)")
    dy_, dv = _yr(ctx, C, "cpi_inflation_pct")          # DGBAS, annual averages
    cy, cv = _yr(ctx, CC, "cpi_yoy_pct")                # CBC, period y/y
    ctx.line(ax, dy_, dv, p.RED, label="DGBAS (annual-average CPI y/y)")
    _second(ctx, ax, cy, cv, p.NAVY, "CBC (period CPI y/y)")
    ig.add_recessions(ax, label=False)
    v09 = _at(dy_, dv, 2009)
    ax.annotate(f"2009: {v09:.1f}%", (2009, v09), textcoords="offset points",
                xytext=(0, -6), ha="center", va="top", fontsize=8.4,
                fontweight="bold", color=p.RED)
    spread = max(abs(_at(dy_, dv, y) - _at(cy, cv, y))
                 for y in set(dy_) & set(cy))
    ysp = next(y for y in dy_
               if abs(_at(dy_, dv, y) - _at(cy, cv, y)) >= spread - 1e-9)
    _note(p, ax, 0.02, 0.96, f"the two official readings part most in "
          f"{ysp}: {_at(dy_, dv, ysp):.1f} vs {_at(cy, cv, ysp):.1f}")
    # The canonical scale leaves the upper half empty. Keep the two-row
    # Portuguese legend there: Liberation Sans (the Pages runner's Latin
    # fallback) is wider than Noto Sans and otherwise reaches the CBC line.
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _foot(p, ax, "two published rates on different bases, never spliced; the "
          "CBC has no formal CPI target to draw")

    ax = ig.slot("economy.unemployment", "Unemployment rate (% of labour force)")
    uy, uv = _yr(ctx, "economy/unemployment.csv", "unemployment_rate_pct")
    ctx.line(ax, uy, uv, p.NAVY, label="DGBAS total unemployment rate")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, uy, uv, p.NAVY, lambda v: f"{v:.2f}", dy=8)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _foot(p, ax, "DGBAS A040107010; total unemployment rate, annual average")

    _finish(ctx, ig)


# ------------------------------------------------------------------- fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p
    B = "fiscal/budget.csv"
    D = "fiscal/debt_central.csv"
    S = "spending/function.csv"

    # i0121 outlays are thousand NTD; the GDP table is million NTD. The
    # factor is explicit here and pinned in tests/test_plates.py.
    _TH = 1_000.0          # thousand NTD -> NTD
    _MN = 1_000_000.0      # million NTD -> NTD
    sly, debt_service = _yr(ctx, S, "spending_debt_service")
    gdp_mn = _pct_of_gdp(ctx)
    ds_y = list(sly)
    ds_v = [v * _TH / (gdp_mn[y] * _MN) * 100.0 for y, v in zip(sly, debt_service)]

    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure (% of GDP)")
    ry, rv = _yr(ctx, B, "revenue_pct_gdp")
    ey, ev = _yr(ctx, B, "expenditure_pct_gdp")
    ctx.line(ax, ry, rv, p.GREEN, label="Revenue")
    ctx.line(ax, ey, ev, p.RED, label="Expenditure")
    ig.add_recessions(ax, label=False)
    # The reference range runs to 70% of GDP and both lines sit near 15,
    # so their end labels would rest on the lines themselves; the note
    # states both endpoints instead, and the legend carries the names.
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96, f"both lines fall across the window: revenue "
          f"{rv[0]:.1f}% to {rv[-1]:.1f}%, expenditure {ev[0]:.1f}% to "
          f"{ev[-1]:.1f}%")
    _foot(p, ax, "MOF/DGBAS all-levels accrual final accounts, calendar years; "
          "the treasury's cash ledger is the second reading in DATA_NOTES")

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    by, bv = _yr(ctx, B, "balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.RED)
    _barkey(ax, p.RED, "Overall balance")
    gdp_mn2 = _pct_of_gdp(ctx)
    prim = [_at(by, bv, y) + v * _TH / (gdp_mn2[y] * _MN) * 100.0
            for y, v in zip(sly, debt_service)]
    ctx.line(ax, ds_y, prim, p.NAVY, label="Primary balance "
                                          "(balance + debt-category outlays)")
    ig.add_recessions(ax, label=False)
    w = min(zip(by, bv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, f"the stimulus year {w[0]}: {w[1]:.1f}% of GDP, "
          "the deepest gap of the window")
    ax.legend(loc="lower right", fontsize=7.4, frameon=False)
    _foot(p, ax, "primary = overall + MOF i0121 debt-category outlays — the "
          "closest published proxy, drawn as a line over the bars")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    dly, dlv = _yr(ctx, D, "debt_central_pct_gdp")
    ctx.line(ax, dly, dlv, p.NAVY, label="Central government gross debt (i0232)")
    ig.add_recessions(ax, label=False)
    peak = max(zip(dly, dlv), key=lambda t: t[1])
    ax.annotate(f"{peak[0]}: {peak[1]:.1f}%", peak, textcoords="offset points",
                xytext=(0, 6), ha="center", va="bottom", fontsize=8.6,
                fontweight="bold", color=p.NAVY)
    _note(p, ax, 0.02, 0.55, f"and down again: {peak[1]:.1f}% peak to "
          f"{dlv[-1]:.1f}% in {dly[-1]} — the debt ratio is shrinking")
    ctx.endlabel(ax, dly, dlv, p.NAVY, lambda v: f"{v:.0f}", dy=6)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _foot(p, ax, "MOF i0232, central government only — no general-government "
          "debt stock is published (labelled per the spine's perimeter rule)")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    ctx.line(ax, ds_y, ds_v, p.GOLD, label="Debt-category outlays (i0121)")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.55, f"the bill keeps falling: {ds_v[0]:.1f}% to "
          f"{ds_v[-1]:.1f}% of GDP — interest plus charges, the closest "
          "published proxy")
    ctx.endlabel(ax, ds_y, ds_v, p.GOLD, lambda v: f"{v:.1f}", dy=6)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _foot(p, ax, "i0121 debt-category outlays ÷ GDP — the proxy DATA_NOTES "
          "promises, not a general-government D41PAY")

    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
# The MOF final-accounts classification is its own, not COFOG: it separates
# pensions, has no health line, and there is no clean mapping for one. The
# eight groups ride under their own names, and the note says so.
MOF8 = [
    # the CSV's "social security & pension" column is a SUBTOTAL over social
    # welfare, pensions, and community & environment (DATA_NOTES: the plate
    # must not sum it with the items beside it), so the stack draws the
    # three components and never the subtotal.
    ("Social welfare", "spending_social_welfare", "RED"),
    ("Pensions", "spending_pension", "RED_D"),
    ("Education, science & culture", "spending_education_sci_culture", "GOLD"),
    ("Economic development", "spending_economic_development", "BLUE"),
    ("General administration", "spending_general_affairs", "PURPLE"),
    ("Defence", "spending_defence", "NAVY"),
    ("Community & environment", "spending_community_environment", "TEAL"),
    ("Debt service", "spending_debt_service", "BLUE_D"),
    ("Other", "spending_other", "FAINT"),
]


def _share_groups(ctx):
    """({name: [pct of GDP]}, years) from the functional final accounts."""
    t = ctx.table("spending/function.csv")
    gdp = _pct_of_gdp(ctx)
    yrs = [y for y in t["year"] if y >= W0 and y in gdp]
    out = {}
    for name, col, _ in MOF8:
        row = dict(zip(t["year"], t[col]))
        out[name] = [row[y] * 1_000.0 / (gdp[y] * 1_000_000.0) * 100.0
                     for y in yrs]
    return out, yrs


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    groups, yrs = _share_groups(ctx)

    ax = ig.slot("spending.by_function",
                 "Spending by function, stacked (% of GDP)")
    layers = [(name, groups[name], getattr(p, color))
              for name, _, color in MOF8]
    ax.stackplot(yrs, *[v for _, v, _ in layers],
                 labels=[n for n, _, _ in layers],
                 colors=[c for _, _, c in layers], alpha=0.9, lw=0)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=6.9, ncol=4, frameon=False)
    tot = [sum(layers[i][1][k] for i in range(len(layers)))
           for k in range(len(yrs))]
    ax.annotate(f"{tot[-1]:.1f}% of GDP ({yrs[-1]})", (yrs[-1], tot[-1]),
                textcoords="offset points", xytext=(-4, 8), ha="right",
                fontsize=8.4, fontweight="bold", color=p.INK)
    _note(p, ax, 0.02, 0.55, "the MOF classification, not COFOG: it separates "
          "pensions\nand has no health line of its own — nine groups, "
          "named")
    _foot(p, ax, "MOF i0121 final accounts ÷ GDP; total outlays follow the "
          "fiscal plate's expenditure line")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    soc = [a + b + c for a, b, c in zip(
        groups["Social welfare"], groups["Pensions"],
        groups["Community & environment"])]
    rest = [t - s for t, s in zip(tot, soc)]
    ctx.line(ax, yrs, rest, p.NAVY, label="Everything else")
    ctx.line(ax, yrs, soc, p.RED, label="Social security & pensions")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    ax.annotate(f"{soc[0]:.1f} to {soc[-1]:.1f}", (yrs[-1], soc[-1]),
                textcoords="offset points", xytext=(-4, 8), ha="right",
                fontsize=8.4, fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.75, f"the largest group and every other group both "
          f"shrink:\n{tot[0]:.1f}% of GDP in {yrs[0]} and {tot[-1]:.1f}% in "
          f"{yrs[-1]}")
    _foot(p, ax, "the COFOG pair, drawn on the national classification — "
          "pensions stay inside social security, where the accounts put them")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(% of GDP)")
    ctx.pending(ax)
    _foot(p, ax, "the staged DGBAS key table carries no capital-formation "
          "column — GFCF pending, not invented")

    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    ctx.pending(ax)
    _foot(p, ax, "no published government GFCF series was staged — pending")

    _finish(ctx, ig)


# -------------------------------------------------------------------- trade
def _trade(ctx):
    """(years, exports US$mn, imports US$mn, GDP US$mn) from the customs pair."""
    ey, ex = _yr(ctx, "trade/goods.csv", "exports_usd_thousands")
    iy, im = _yr(ctx, "trade/goods.csv", "imports_usd_thousands")
    gy, gv = _yr(ctx, "economy/gdp.csv", "gdp_nominal_usd_mn")
    gdp = dict(zip(gy, gv))
    xs = [v / 1_000.0 for v in ex]              # thousands -> millions
    ms = [v / 1_000.0 for v in im]
    return ey, xs, ms, gdp


PARTNERS = [("United States", "United States", "RED"),
            ("China_mainland", "Mainland China", "GOLD"),
            ("Singapore", "Singapore", "TEAL"),
            ("Japan", "Japan", "BLUE"),
            ("South_Korea", "South Korea", "PURPLE")]


def plate_trade(ctx, ig) -> None:
    p = ctx.p
    ty, ex, im, _ = _trade(ctx)

    ax = ig.slot("trade.exports_imports",
                 "Exports and imports, goods and services (% of GDP)")
    ctx.pending(ax)
    _foot(p, ax, "Only customs goods are staged; comparable national-accounts goods-and-services ratios are not available")

    ax = ig.slot("trade.balance", "Trade balance, goods and services (% of GDP)")
    ctx.pending(ax)
    _foot(p, ax, "The staged customs-goods balance is retained in the lens and is not relabelled as goods and services")

    PT = "trade/partners.csv"
    tot = dict(zip(ty, ex))
    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    shares = {}
    for key, name, color in PARTNERS:
        py_, pv_ = _yr(ctx, PT, "exports_usd_thousands")  # long table: see below
        rows = ctx.table(PT)
        cy, cv = [], []
        for y, partner, v in zip(rows["year"], rows["partner"],
                                 rows["exports_usd_thousands"]):
            if partner == key and y >= W0 and v == v and y in tot:
                cy.append(y)
                cv.append(v / 1_000.0 / tot[y] * 100)
        shares[key] = dict(zip(cy, cv))
        ctx.line(ax, cy, cv, getattr(p, color),
                 lw=2.2 if key in ("United States", "China_mainland") else 1.7,
                 ms=3.4, label=name)
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "ecfa")
    us, ch = shares["United States"], shares["China_mainland"]
    chpk = max(ch.items(), key=lambda t: t[1])
    ax.annotate(f"{ch[2025]:.0f}%", (2025, ch[2025]),
                textcoords="offset points", xytext=(0, -12), ha="center",
                va="top", fontsize=8.4, fontweight="bold", color=p.GOLD)
    ax.annotate(f"{us[2025]:.0f}%", (2025, us[2025]),
                textcoords="offset points", xytext=(0, 6), ha="center",
                va="bottom", fontsize=8.4, fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.55, f"Mainland China peaks at {chpk[1]:.0f}% in "
          f"{chpk[0]} and then halves;\nthe United States takes the lead "
          f"({us[2025]:.0f}% in 2025)")
    # The shared destination scale leaves clear air above these series.
    # Keep the legend there so its labels do not lie across the compressed
    # partner lines.
    ax.legend(loc="upper right", fontsize=6.9, frameon=False, ncol=2)
    _foot(p, ax, "customs records by partner, via MOF; ranked on 2025; the "
          "mainland share counts direct trade only")

    ax = ig.slot("trade.lens", "Lens — one goods flow, counted twice (US$ bn)")
    by_, bx = _yr(ctx, "world/bop_goods.csv", "bop_goods_exports_usd_mn")
    _, bi = _yr(ctx, "world/bop_goods.csv", "bop_goods_imports_usd_mn")
    # Both publishers quote US$ millions; the panel is labelled in bn, so
    # every series divides by 1,000 once, in one place.
    ctx.line(ax, ty, [v / 1_000.0 for v in ex], p.GREEN, label="Customs exports")
    _second(ctx, ax, by_, [v / 1_000.0 for v in bx], p.GREEN_D, "BoP exports")
    ctx.line(ax, ty, [v / 1_000.0 for v in im], p.RED, label="Customs imports")
    _second(ctx, ax, by_, [v / 1_000.0 for v in bi], p.RED_D, "BoP imports")
    ig.add_recessions(ax, label=False)
    ax.set_ylabel("US$ bn, goods", fontsize=8.6, color=p.MUTED)
    ax.set_ylim(0, max(max(ex), max(bx)) / 1_000.0 * 1.25)
    gap = (_at(ty, ex, 2025) - _at(by_, bx, 2025)) / 1_000.0
    _note(p, ax, 0.02, 0.96, f"customs FOB vs balance-of-payments: in 2025 "
          f"the two answers\ndiffer by US${gap:,.0f}bn on exports alone — "
          "two publishers, never one line")
    ax.legend(loc="lower left", fontsize=7.2, frameon=False, ncol=2)
    _foot(p, ax, "MOF customs compilation vs CBC balance of payments — "
          "different definitions of one flow, kept apart by rule 10")

    _finish(ctx, ig)


# ------------------------------------------------------------------ markets
def _fx(ctx):
    return dict(zip(*_yr(ctx, "markets/usdtwd.csv",
                         "usd_twd_interbank_annual_mean")))


def plate_markets(ctx, ig) -> None:
    p = ctx.p
    fx = _fx(ctx)

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ry, rv = _yr(ctx, "markets/policy_rate.csv", "rediscount_rate_pct")
    cy, cv = _yr(ctx, "economy/cpi.csv", "cpi_inflation_pct")
    ctx.line(ax, cy, cv, p.RED, lw=1.8, ms=3.2,
             label="CPI inflation, annual average (DGBAS)")
    ctx.line(ax, ry, rv, p.NAVY, label="CBC rediscount rate, year-end")
    _bands_labelled_at(ig, ax, 0.80, p)
    ctx.endlabel(ax, ry, rv, p.NAVY, lambda v: f"{v:.2f}%", dy=8)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    lo = min(zip(rv, ry))
    _note(p, ax, 0.02, 0.96, f"the rediscount rate is the policy rate — the "
          f"CBC runs no OMO\ntarget series; its low was {lo[0]:.2f}% in {lo[1]}")

    ax = ig.slot("markets.bond_10y",
                 "10-year government bond yield (%, annual average)")
    ctx.pending(ax)
    _foot(p, ax, "the CBC's CPMI strip was not verified end to end in Phase "
          "A — pending, not invented")

    ax = ig.slot("markets.currency", "Currency against the US$ "
                 "(index 2006 = 100, up = stronger)")
    iy, iv = ctx.fx_index(fx)
    ctx.line(ax, iy, iv, p.NAVY)
    ig.add_recessions(ax, label=False)
    pk = max(zip(iy, iv), key=lambda t: t[1])
    ax.annotate(f"{pk[0]}: {pk[1]:.0f}", pk, textcoords="offset points",
                xytext=(0, 7), ha="center", fontsize=8.4, fontweight="bold",
                color=p.NAVY)
    lo = min(iv)
    _note(p, ax, 0.02, 0.30, f"the whole window lies between {lo:.0f} and "
          f"{max(iv):.0f} — a managed, unusually\nsteady rate against the "
          "dollar (see DATA_NOTES)")
    ctx.endlabel(ax, iy, iv, p.NAVY, lambda v: f"{v:.0f}", dy=8)
    _foot(p, ax, "CBC interbank closing rates, annual means, inverted to "
          "index form by core/rates.py")

    ax = ig.slot("markets.equities", "Main equity index in US$ "
                 "(index 2006 = 100)")
    ay, av = _yr(ctx, "markets/stock_index_avg.csv", "taiex_annual_average")
    ey_, ev_ = _yr(ctx, "markets/stock_index_yearend.csv", "close")
    avg_usd = {y: v / fx[y] for y, v in zip(ay, av) if y in fx}
    end_usd = {y: v / fx[y] for y, v in zip(ey_, ev_) if y in fx}
    iy, iv = ctx.index_2006(avg_usd)
    ey2, ev2 = ctx.index_2006(end_usd)
    _second(ctx, ax, ey2, ev2, p.FAINT, "year-end close (Yahoo, not official)")
    ctx.line(ax, iy, iv, p.RED, label="TWSE index, annual average, in US$")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.RED, lambda v: f"{v:.0f}", dy=8)
    ctx.endlabel(ax, ey2, ev2, p.FAINT, lambda v: f"{v:.0f}", dy=-14)
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.30, "annual average and year-end close are two "
          "different quantities;\nboth are drawn, and the official one stays "
          "the plate's line")
    _foot(p, ax, "CBC EG27Y01 annual averages, converted at the staged "
          "average FX; Yahoo ^TWII closes as the labelled second reading")

    _finish(ctx, ig)


# ------------------------------------------------------------------- credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p
    gdp = _pct_of_gdp(ctx)

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    hy, hv = _yr(ctx, "credit/household_credit.csv", "consumer_loans_ntd_mn")
    share = [v / gdp[y] * 100 for y, v in zip(hy, hv)]
    ctx.line(ax, hy, share, p.RED, label="Consumer loans (CBC EF99Y01)")
    ig.add_recessions(ax, label=False)
    pk = max(zip(hy, share), key=lambda t: t[1])
    # The window's highest share is 2006 itself, the first year drawn:
    # the label runs right from the point so it cannot cross the axis.
    ax.annotate(f"{pk[1]:.0f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(12, 4), ha="left", va="bottom", fontsize=8.4,
                fontweight="bold", color=p.RED)
    _note(p, ax, 0.98, 0.20, f"from {share[0]:.0f}% of GDP in {hy[0]} to "
          f"{share[-1]:.0f}% in {hy[-1]} — a household\nbook that barely "
          "grows, and half the G7's ratio", ha="right")
    ctx.endlabel(ax, hy, share, p.RED, lambda v: f"{v:.0f}", dy=8)
    ax.legend(loc="upper left", fontsize=7.6, frameon=False)
    _foot(p, ax, "the CBC's national definition, not BIS: the BIS credit "
          "framework does not carry Taiwan (see DATA_NOTES)")

    ax = ig.slot("credit.lending_rate",
                 "Household lending rate vs policy rate (%)")
    ly, lv = _yr(ctx, "credit/new_housing_rate.csv",
                 "new_housing_loan_rate_pct")
    py, pv = _yr(ctx, "markets/policy_rate.csv", "rediscount_rate_pct")
    ctx.line(ax, ly, lv, p.RED, label="Five-bank new housing loans")
    _second(ctx, ax, py, pv, p.NAVY, "CBC rediscount rate")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    _foot(p, ax, "CBC EH45M01 annual mean of monthly new-business rates; "
          "policy line is December rediscount rate")

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    ny, nv = _yr(ctx, "credit/npl.csv", "bank_npl_ratio_pct")
    ctx.line(ax, ny, nv, p.PURPLE, label="Banks' overdue-to-loan ratio (CBC)")
    ig.add_recessions(ax, label=False)
    # No annotation at the final point: the end label already prints it,
    # and the note says the whole fall.
    _note(p, ax, 0.02, 0.62, f"{nv[0]:.2f}% in {ny[0]} to {nv[-1]:.2f}% — "
          "the banks cleaned up\nafter the 2008 collapse and never went back")
    ctx.endlabel(ax, ny, nv, p.PURPLE, lambda v: f"{v:.2f}", dy=10)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _foot(p, ax, "CBC EF07M01 overdue-to-loan ratio: loans overdue more "
          "than three months, the definition in the legend")

    ax = ig.slot("credit.lens", "Lens — developers' credit: building loans "
                 "(% of GDP)")
    by, bv = _yr(ctx, "credit/household_credit.csv", "building_loans_ntd_mn")
    bshare = [v / gdp[y] * 100 for y, v in zip(by, bv)]
    ctx.bars(ax, by, bshare, lambda v: p.GOLD)
    _barkey(ax, p.GOLD, "Building loans (CBC EF99Y01)")
    ig.add_recessions(ax, label=False)
    pk = max(zip(by, bshare), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=8.4, fontweight="bold",
                color=p.GOLD)
    _note(p, ax, 0.02, 0.96, "not household debt: this is credit to "
          "developers,\nkept out of slot 1 on purpose and doubled across "
          "the window")
    ax.set_ylabel("% of GDP", fontsize=8.6, color=p.MUTED)
    ax.set_ylim(0, max(bshare) * 1.45)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _foot(p, ax, "the lens DATA_NOTES promises: the property cycle is "
          "developer credit, and it lives here")

    _finish(ctx, ig)


# ------------------------------------------------------------------- people
def plate_people(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("people.gini", "Income inequality — Gini (0–100 points)")
    gy, gv = _yr(ctx, "people/gini.csv", "gini_points")
    ctx.line(ax, gy, gv, p.RED, label="DGBAS household disposable income")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.RED, lambda v: f"{v:.1f}", dy=8)
    ax.legend(loc="upper right", fontsize=7.5, frameon=False)
    _foot(p, ax, "DGBAS Family Income and Expenditure Survey; coefficient ×100")

    ax = ig.slot("people.poverty", "Relative poverty rate (% of people)")
    py, pv = _yr(ctx, "people/poverty.csv", "relative_poverty_pct")
    ctx.line(ax, py, pv, p.PURPLE,
             label="Below 50% of median equivalised disposable income")
    ctx.endlabel(ax, py, pv, p.PURPLE, lambda v: f"{v:.2f}%", dy=8)
    _note(p, ax, 0.02, 0.80, "official series begins in 2017; earlier years stay missing")
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    _foot(p, ax, "DGBAS National Well-being Indicators; people, square-root equivalence scale")

    ax = ig.slot("people.minimum_wage", "Statutory minimum wage (US$ per month)")
    wy, wv = _yr(ctx, "people/minimum_wage.csv", "monthly_usd_at_avg_fx")
    ctx.line(ax, wy, wv, p.NAVY, label="Calendar-average legal monthly wage")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, wy, wv, p.NAVY, lambda v: f"US${v:,.0f}", dy=8)
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    _foot(p, ax, "MOL effective-date history, day-weighted by calendar year; ÷ DGBAS annual-average FX")

    ax = ig.slot("people.lens", "Lens — highest / lowest household quintile ratio")
    qy, qv = _yr(ctx, "people/gini.csv", "quintile_ratio")
    ctx.line(ax, qy, qv, p.GOLD, label="Top-quintile income ÷ bottom-quintile income")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, qy, qv, p.GOLD, lambda v: f"{v:.2f}×", dy=8)
    ax.set_ylim(0, 8)
    ax.set_ylabel("ratio", fontsize=8.6, color=p.MUTED)
    ax.legend(loc="upper right", fontsize=7.5, frameon=False)
    _foot(p, ax, "same DGBAS survey and vintage as the Gini; a ratio, not another Gini")

    _finish(ctx, ig)


# -------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "economy/gdp.csv", "gdp_nominal_usd_mn")
    gv = [v / 1_000.0 for v in gv]
    ctx.line(ax, gy, gv, p.RED)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.RED, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.30, "the publisher's own US$ column, at DGBAS's "
          "average\nexchange rate — the World Bank does not carry Taiwan")

    ax = ig.slot("world.hdi", "Human Development Index (HDI, 0–1)")
    ctx.pending(ax)
    _foot(p, ax, "the UN does not carry Taiwan, and no national publisher "
          "computes the HDI — a true absence, drawn honestly")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (score, 0–100)")
    cy, cv = _yr(ctx, "world/corruption.csv", "cpi_score")
    ctx.line(ax, cy, cv, p.PURPLE, label="Taiwan")
    ctx.endlabel(ax, cy, cv, p.PURPLE, lambda v: f"{v:.0f}", dy=8)
    ax.legend(loc="lower right", fontsize=7.6, frameon=False)
    _foot(p, ax, "Transparency International CPI Historical; comparable "
          "2012 method, 0–100")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn, year-end)")
    ry, rv = _yr(ctx, "world/reserves.csv", "fx_reserves_usd_mn")
    rv = [v / 1_000.0 for v in rv]
    ctx.line(ax, ry, rv, p.GREEN_D)
    ig.add_recessions(ax, label=False)
    pk = max(zip(ry, rv), key=lambda t: t[1])
    ax.annotate(f"{pk[0]}: US${pk[1]:,.0f}bn", pk, textcoords="offset points",
                xytext=(-4, 7), ha="right", fontsize=8.4, fontweight="bold",
                color=p.GREEN_D)
    ctx.endlabel(ax, ry, rv, p.GREEN_D, lambda v: f"US${v:,.0f}bn", dy=-14)
    _note(p, ax, 0.02, 0.96, "among the largest reserves in the world, and "
          "rising every\nstretch of dollar strength — the CBC buys the "
          "difference")
    _foot(p, ax, "CBC EF07M01 foreign-exchange reserves, end of December")

    _finish(ctx, ig)


# --------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p
    py, pv = _yr(ctx, "demography/population.csv", "population")
    pop = dict(zip(py, pv))

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    iy, iv = ctx.index_2006({y: pop[y] for y in py})
    ctx.line(ax, iy, iv, p.BLUE)
    ig.add_recessions(ax, label=False)
    peak = max(zip(py, pv), key=lambda t: t[1])
    lo = min((v for y, v in pop.items() if y > peak[0]), default=iv[-1])
    ctx.endlabel(ax, iy, iv, p.BLUE, lambda v: f"{pop[max(py)] / 1e6:.1f}M",
                 dy=-14, ha="left")
    _note(p, ax, 0.02, 0.96, f"the register peaks at {peak[1]:,.0f} in "
          f"{peak[0]} and is falling:\n{pop[max(py)]:,.0f} by "
          f"{max(py)} — population loss, already under way")
    _foot(p, ax, "DGBAS annual population of the governed territory — the "
          "same series every rate on this plate divides by")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    ctx.pending(ax)
    _foot(p, ax, "the audited RIS population/birth endpoint returned no data; "
          "fertility is not inferred from a different table")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    cy, cv = _yr(ctx, "mortality/causes_of_death.csv", "deaths_all_cause")
    dy, dv = ctx.per_1000(dict(zip(cy, cv)), pop)
    ctx.line(ax, dy, dv, p.RED_D, label="Deaths (DGBAS registrations ÷ people)")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.RED_D, lambda v: f"{v:.1f}", dy=8)
    # The crude death rate never leaves the bottom third of this 0–25
    # range, so the note clears it and hangs from the open top, right of
    # the legend.
    _note(p, ax, 0.35, 0.90, "deaths only: the audited birth endpoint returned "
          "no data — the gap to the "
          "bottom of the axis is\nthe shape of the crisis, drawn honestly")
    ax.legend(loc="upper left", fontsize=7.6, frameon=False)
    _foot(p, ax, "DGBAS A170101020 all-cause deaths ÷ the same-year DGBAS "
          "population, by core/rates.py; the series starts in 2008")

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net migration (per 1,000 people)")
    ctx.pending(ax)
    _foot(p, ax, "natural increase needs births, still unavailable; registered "
          "international movement is kept on the migration plate")

    _finish(ctx, ig)


# ----------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    py, pv = _yr(ctx, "demography/population.csv", "population")
    pop = dict(zip(py, pv))
    C = "mortality/causes_of_death.csv"

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    ctx.pending(ax)
    # A pending axis is never put on the reference scale (core/plotting),
    # but this slot was already switched to log when it was claimed, and
    # the default log formatter publishes 10⁻²-style mathtext ticks.
    # Draw the spine slot's own plain-number ticks over its reference
    # range so the reader sees the scale the series will land on.
    slot = spine.SLOTS["security.homicide"]
    ax.set_ylim(*slot.ref)
    ax.yaxis.set_major_locator(mticker.FixedLocator(list(slot.ticks)))
    ax.yaxis.set_minor_locator(mticker.NullLocator())
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(spine.tick_label))
    _foot(p, ax, "the police (NPA) series is walled and the staged "
          "cause-of-death set carries no assault line — pending")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    sy, sv = _yr(ctx, C, "deaths_suicide")
    uy, uv = ctx.per_100k(dict(zip(sy, sv)), pop)
    ctx.line(ax, uy, uv, p.PURPLE, label="Certificates (DGBAS A170101020)")
    ig.add_recessions(ax, label=False)
    first, last = uv[0], uv[-1]
    low = min(zip(uy, uv), key=lambda t: t[1])
    ax.annotate(f"{low[1]:.1f} in {low[0]}", low, textcoords="offset points",
                xytext=(0, -12), ha="center", va="top", fontsize=8.2,
                fontweight="bold", color=p.PURPLE)
    ctx.endlabel(ax, uy, uv, p.PURPLE, lambda v: f"{v:.1f}", dy=8)
    _note(p, ax, 0.02, 0.55, f"from {first:.1f} to {last:.1f} per 100,000, "
          f"with a floor at {low[1]:.1f} —\nthe line never bends down for good")
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _foot(p, ax, "death certificates by underlying cause; the police "
          "place-of-occurrence series will be a second column, not a splice")

    ax = ig.slot("security.road_deaths", "Road traffic deaths (per 100,000)")
    ctx.pending(ax)
    _foot(p, ax, "traffic deaths are measured by the police and the "
          "transport ministry, both walled — the staged accidents line "
          "counts all accidents, so it goes to the lens, not here")

    ax = ig.slot("security.lens", "Lens — all accidental deaths (per 100,000)")
    ay, av = _yr(ctx, C, "deaths_accidents")
    wy, wv = ctx.per_100k(dict(zip(ay, av)), pop)
    ctx.bars(ax, wy, wv, lambda v: p.NAVY)
    _barkey(ax, p.NAVY, "Accidents, all kinds (DGBAS certificates)")
    ig.add_recessions(ax, label=False)
    pk = max(zip(wy, wv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f} in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=8.4, fontweight="bold",
                color=p.NAVY)
    _note(p, ax, 0.02, 0.96, "not a road-traffic count — the certificates "
          "lump every\naccident kind, and the honest label says so")
    ax.set_ylabel("per 100,000", fontsize=8.6, color=p.MUTED)
    ax.set_ylim(0, max(wv) * 1.45)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _foot(p, ax, "DGBAS death certificates ÷ the same population, per "
          "core/rates.py; falls as cars get safer, as everywhere")

    _finish(ctx, ig)


# ---------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    py, pv = _yr(ctx, "demography/population.csv", "population")
    pop = dict(zip(py, pv))
    C = "mortality/causes_of_death.csv"

    ax = ig.slot("mortality.death_rate", "Crude death rate (per 1,000 people)")
    cy, cv = _yr(ctx, C, "deaths_all_cause")
    dy, dv = ctx.per_1000(dict(zip(cy, cv)), pop)
    ctx.line(ax, dy, dv, p.RED_D, label="Registrations ÷ population (DGBAS)")
    ig.add_recessions(ax, label=False)
    pk = max(zip(dy, dv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.2f} in {pk[0]}", pk, textcoords="offset points",
                xytext=(-2, 7), ha="right", fontsize=8.4, fontweight="bold",
                color=p.RED_D)
    ctx.endlabel(ax, dy, dv, p.RED_D, lambda v: f"{v:.2f}", dy=-12)
    _note(p, ax, 0.02, 0.96, f"up {dv[0]:.1f} to {dv[-1]:.1f} per 1,000 as the "
          "population ages —\nthe series starts in 2008, where the "
          "certificate record does")
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _foot(p, ax, "DGBAS A170101020 ÷ the same-year population — the "
          "conversion DATA_NOTES names")

    ax = ig.slot("mortality.excess_deaths",
                 "Excess deaths (% above 2015–2019 average)")
    d = dict(zip(cy, cv))
    base = sum(d[y] for y in range(2015, 2020)) / 5
    ex_y = [y for y in cy if y >= 2015]
    ex_v = [(d[y] / base - 1) * 100 for y in ex_y]
    ctx.bars(ax, ex_y, ex_v, lambda v: p.RED if v > 0 else p.GREEN)
    _barkey(ax, p.RED, "Deaths above the 2015–2019 mean")
    ig.add_recessions(ax, label=False)
    pk = max(zip(ex_y, ex_v), key=lambda t: t[1])
    ax.annotate(f"+{pk[1]:.1f}%", pk, textcoords="offset points",
                xytext=(0, 5), ha="center", fontsize=8.6, fontweight="bold",
                color=p.RED)
    _note(p, ax, 0.02, 0.96, f"counted against {base:,.0f} deaths a year, the "
          "2015–2019 mean;\nnot adjusted for a population that grew and "
          "aged, and the wave\nthat most of the world lost in 2020 lands "
          "here in 2022")
    ax.legend(loc="lower left", fontsize=7.4, frameon=False)
    _foot(p, ax, "computed here from slot 1's own counts, the house rule "
          "unadjusted; the COVID code is a pending second column, not a merge")

    ax = ig.slot("mortality.covid",
                 "COVID-19 deaths, underlying cause (per 100,000)")
    ctx.pending(ax)
    _foot(p, ax, "the staged DGBAS cause set carries no COVID line — when "
          "HPA lands it rides beside the excess series as a second column, "
          "never merged")

    ax = ig.slot("mortality.lens", "Lens — the killers that grew "
                 "(per 100,000)")
    ky, kv = _yr(ctx, C, "deaths_cancer")
    hy, hv = _yr(ctx, C, "deaths_heart")
    ny, nv = _yr(ctx, C, "deaths_pneumonia")
    cy_, cv_ = ctx.per_100k(dict(zip(ky, kv)), pop)
    hy_, hv_ = ctx.per_100k(dict(zip(hy, hv)), pop)
    ny_, nv_ = ctx.per_100k(dict(zip(ny, nv)), pop)
    ctx.line(ax, cy_, cv_, p.NAVY, label="Cancer")
    ctx.line(ax, hy_, hv_, p.RED, label="Heart disease")
    ctx.line(ax, ny_, nv_, p.TEAL, label="Pneumonia")
    ig.add_recessions(ax, label=False)
    # Leave a real legend shelf above the three series. This lens does not use
    # a canonical comparison scale; 1.6× keeps both Noto Sans and the wider
    # Liberation Sans used by Pages clear of the heart-disease line.
    ax.set_ylim(0, max(cv_) * 1.6)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96, f"pneumonia doubles: {nv_[0]:.0f} to "
          f"{nv_[-1]:.0f} per 100,000 — the ageing\npopulation is the story "
          "behind all three lines")
    ax.set_ylabel("per 100,000", fontsize=8.6, color=p.MUTED)
    _foot(p, ax, "underlying cause, DGBAS certificates ÷ population; crude "
          "rates — age-standardised rates are not published here")

    _finish(ctx, ig)


# ---------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    fy, incoming = _yr(ctx, "migration/registration_flows.csv", "registered_immigration")
    _, outgoing = _yr(ctx, "migration/registration_flows.csv", "registered_emigration")
    _, net = _yr(ctx, "migration/registration_flows.csv", "registered_net")
    py, pv = _yr(ctx, "demography/population.csv", "population")
    pop = dict(zip(py, pv))

    iy, iv = ctx.per_1000(dict(zip(fy, incoming)), pop)
    ey, ev = ctx.per_1000(dict(zip(fy, outgoing)), pop)
    ax = ig.slot("migration.flows", "Registered international in and out (per 1,000 people)")
    ctx.line(ax, iy, iv, p.GREEN_D, label="In + initial household registration")
    ctx.line(ax, ey, ev, p.RED_D, label="Foreign deregistration")
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _foot(p, ax, "MOI/RIS household-register events; not all ARC-holder migration")

    ny, nv = ctx.per_1000(dict(zip(fy, net)), pop)
    ax = ig.slot("migration.net", "Net registered migration (per 1,000 people)")
    ctx.bars(ax, ny, nv, lambda v: p.GREEN if v >= 0 else p.RED)
    _note(p, ax, 0.02, 0.95, "2020–22 include ex-officio deregistration after two years abroad")
    _foot(p, ax, "same compatible RIS components: in + initial registration − out")

    ax = ig.slot("migration.foreign_born", "Foreign-born share of population (%)")
    ctx.pending(ax)
    _foot(p, ax, "no audited foreign-born series; ARC residents are a narrower legal stock, shown in the lens")

    ax = ig.slot("migration.lens", "Lens — foreign residents with a valid ARC (December)")
    ay, av = _yr(ctx, "migration/foreign_residents.csv", "arc_foreign_residents_dec")
    ly, lv = _yr(ctx, "migration/foreign_residents.csv", "foreign_labour_dec")
    av_m = [v / 1e6 for v in av]
    lv_m = [v / 1e6 for v in lv]
    ctx.line(ax, ay, av_m, p.NAVY, label="ARC residents actually in Taiwan")
    ctx.line(ax, ly, lv_m, p.GOLD, label="of whom foreign labour")
    ax.set_ylim(0, 1.2)
    ax.set_ylabel("million people", fontsize=8.6, color=p.MUTED)
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _note(p, ax, 0.02, 0.56, f"foreign labour is {lv[-1] / av[-1] * 100:.1f}% of the 2025 ARC stock")
    _foot(p, ax, "NIA valid ARC holders physically present at month-end; not foreign-born population")

    _finish(ctx, ig)


# The plates, in the order the page lists them; the ids are the spine's
# chapter numbers.
PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Open Economy's Roller Coaster",
         subtitle="Real growth and income from the DGBAS national accounts; "
                  "inflation published twice, by the DGBAS and by the Central "
                  "Bank; unemployment is DGBAS's annual total rate.",
         source="Sources: DGBAS A018101010 national-income key table · DGBAS "
                "CPI (2021=100) · DGBAS A040107010 unemployment · CBC EF07M01 CPI y/y",
         alt="Four panels on Taiwan's macroeconomy. Real growth falls to "
             "−1.6% in 2009 after the export collapse and rebounds to +8.8% "
             "in 2025, the window's fastest; 2020, pandemic or not, grew "
             "+3.4% and is not banded. GDP per person more than doubles, "
             "from US$16,934 in 2006 to US$39,515 in 2025. Inflation is "
             "drawn twice: the DGBAS sees −0.9% in 2009, the Central Bank's "
             "period rate −0.3%. Unemployment peaks at 5.85% in 2009 and "
             "falls to 3.35% in 2025."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="The Government's Books, Kept Twice",
         subtitle="All-levels accrual final accounts with the treasury's cash "
                  "ledger as a labelled second reading; central-government "
                  "debt is the published stock.",
         source="Sources: MOF i2101 / i0121 final accounts · MOF i0232 "
                "central debt · GDP: DGBAS A018101010",
         alt="Four panels on Taiwan's public finances. Revenue eases from "
             "17.3% of GDP in 2006 to 14.7% in 2025; the balance swings from "
             "−4.3% in the 2009 collapse to +0.3% in 2025; central debt "
             "peaks at 34.0% in 2012 and falls to 21.1%; debt-category "
             "outlays fall from 1.1% to 0.3% of GDP."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Where the Money Goes — Eight Groups, Not COFOG's Seven",
         subtitle="The MOF functional classification stacked over GDP, and "
                  "the social-versus-everything pair; both investment panels "
                  "are pending.",
         source="Sources: MOF i0121 expenditure by function · GDP: DGBAS "
                "A018101010",
         alt="Four panels on government spending. Stacked, the eight MOF "
             "groups total 17.6% of GDP in 2006 and 14.5% in 2025, social "
             "security and pensions the largest at 5.2% falling to 4.6%; "
             "social security and everything else both shrink across the "
             "window. The investment panels are pending — no capital-"
             "formation column was staged."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="The Shipping Lanes — and the Customer Switch",
         subtitle="Comparable goods-and-services totals remain pending; "
                  "MOF customs destinations and the two goods definitions stay visible.",
         source="Sources: MOF trade database (customs records) · CBC balance "
                "of payments · GDP: DGBAS A018101010",
         alt="Four panels on trade. Comparable goods-and-services totals "
             "and balances remain visibly pending. Mainland China's share of "
             "goods exports peaks near 30% in 2020 and halves to 16%, while "
             "the United States rises from 14% to 31%. The lens panel draws "
             "customs and balance-of-payments goods side by side, differing "
             "by about US$56 billion on 2025 exports."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Money & Markets — a Quiet Rate, a Loud Index",
         subtitle="The CBC rediscount rate against inflation; the bond panel "
                  "pending; a currency that barely moves; and TAIEX in US "
                  "dollars, average and year-end kept apart.",
         source="Sources: CBC EG2AM01 policy rate · CBC EG51M01 FX · CBC "
                "EG27Y01 index · Yahoo ^TWII (not an official statistic)",
         alt="Four panels on markets. The rediscount rate falls from 3.4% "
             "in 2007 to 1.1% in 2020 and returns to 2.0%; inflation stays "
             "under 4% throughout. The currency index, 2006 = 100, moves "
             "between 98 and 116 in twenty years. TAIEX in US dollars "
             "triples, the official annual average tripling to 364 while "
             "the year-end close reaches 385; the bond panel is pending."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — the Household Book That Barely Grew",
         subtitle="Consumer loans near half of GDP and falling bad debt, on "
                  "the CBC's own definitions (BIS does not carry Taiwan); "
                  "the lens panel is the developers' boom.",
         source="Sources: CBC EF99Y01 loan balances · CBC EH45M01 housing "
                "rate · CBC EF07M01 overdue ratio · GDP: DGBAS A018101010",
         alt="Four panels on credit. Consumer loans decline from their 52% "
             "of GDP peak in 2006 to 47% in 2025; bad loans fall "
             "from 2.1% of all loans to 0.15%. New-housing rates are compared "
             "with the rediscount rate. In the lens, building loans double, "
             "from 6.5% of GDP to 12.0%, peaking at 14.0% in 2023."),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="Income, the Floor, and the Distance Between",
         subtitle="Survey inequality and relative poverty beside the statutory monthly wage, converted with the same-year official exchange rate.",
         source="Sources: DGBAS household income survey and National Well-being Indicators · Ministry of Labor minimum-wage history · DGBAS FX",
         alt="Four panels on income distribution and the wage floor. The disposable-income Gini stays near 34 points; relative poverty is 7.57% in 2024 on the official 50%-of-median definition; the calendar-average statutory wage reaches US$917 a month in 2025; the top household quintile receives 6.17 times the bottom quintile's income."),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="In the World, on Uneven Statistical Ground",
         subtitle="Size and reserves from Taiwan's own publishers; HDI is "
                  "absent, while Transparency International does cover Taiwan.",
         source="Sources: DGBAS A018101010 GDP · CBC EF07M01 reserves · "
                "Transparency International CPI 2025",
         alt="Four panels on Taiwan in the world. GDP reaches US$922 billion "
             "in 2025 on the publisher's own US$ column; official reserves "
             "rise from US$266 billion to US$603 billion, among the world's "
             "largest. HDI remains unavailable because the UN does not carry "
             "Taiwan; TI's CPI rises from 61 in 2012 to 68 in 2025."),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography,
         title="The Population Line Has Turned",
         subtitle="A register that peaked in 2019 and is already falling; "
                  "the deaths half of the birth-and-death pair is available, "
                  "while the audited birth endpoint returns no data.",
         source="Sources: DGBAS A018101010 population · DGBAS A170101020 "
                "deaths by cause",
         alt="Four panels on demography. The population index peaks at 103 "
             "in 2019 (23,596,027 people) and falls to 102; the crude death "
             "rate rises from 6.2 to 8.6 per 1,000 between 2008 and 2025. "
             "The fertility and natural-increase panels are pending because "
             "the audited RIS birth endpoint returned no data; registered "
             "international movement is shown separately on migration."),
    dict(id="10", slug="security", topic="security", builder=plate_security,
         title="Deaths by Certificate — the Suicide Line and the Accidents",
         subtitle="Suicide never falls for good; all accidental deaths "
                  "fall; the homicide and road panels say exactly which "
                  "police series is missing.",
         source="Sources: DGBAS A170101020 deaths by cause, ÷ DGBAS "
                "population",
         alt="Four panels on violent and accidental death. Suicide runs "
             "between 15.1 and 17.9 per 100,000 and is 16.9 in 2025; all "
             "accidental deaths fall from 30.8 per 100,000 to 28.6. The "
             "homicide and road-traffic panels are pending — the police "
             "series are walled and the certificates lump accidents."),
    dict(id="11", slug="mortality", topic="mortality", builder=plate_mortality,
         title="Mortality — Ageing, and a Late Pandemic Wave",
         subtitle="Crude death rate, excess deaths against the 2015–2019 "
                  "mean, a pending COVID column, and the killers that grew "
                  "with the population.",
         source="Sources: DGBAS A170101020 deaths by cause, ÷ DGBAS "
                "population",
         alt="Four panels on mortality. The crude death rate rises from "
             "6.2 to 8.6 per 1,000; deaths run +21.7% above the 2015–2019 "
             "mean in 2022, not 2020, and stay above it through 2025. The "
             "COVID panel is pending. Cancer rises to 235 per 100,000, "
             "heart disease to 98, and pneumonia doubles to 75."),
    dict(id="12", slug="migration", topic="migration", builder=plate_migration,
         title="Movement on the Household Register — and the ARC Stock Beside It",
         subtitle="International registrations in and out are register events; valid ARC holders are a separate month-end legal stock, never relabelled foreign-born.",
         source="Sources: MOI Household Registration Department RIS ODRP011 · National Immigration Agency foreign-resident statistics",
         alt="Four panels on migration definitions. Household-register immigration and emigration are shown separately from 2018, with their net turning sharply negative during 2020–2022 ex-officio deregistrations and positive again in 2023. No audited foreign-born share is available. The lens shows 1,028,945 foreign residents with a valid ARC in December 2025, including 751,806 foreign labourers."),
)
