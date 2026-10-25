"""The Hong Kong plates, on the plate spine.

Hong Kong is a Special Administrative Region of China, and every series drawn
here is the SAR's own: C&SD's national accounts, the HKMA's rates and reserves,
the Department of Health's registered deaths, the police's reported offences.
It is compared as an economy — the way every international publisher reports
it, as `HKG` — and no Chinese national series appears on any panel.

Four conventions run through the file:

- **Two fiscal perimeters, never spliced.** The canonical panels are the IMF's
  general government on calendar years, the only consolidated general-
  government series published for Hong Kong. The government's own General
  Revenue Account is cash, on a narrower perimeter, in a financial year that
  starts in April: it rides as a labelled dotted line at the financial year's
  midpoint and is converted at that year's calendar GDP, which the note says
  out loud.
- **GCE is not government spending.** C&SD's functional table covers
  government *consumption*, so cash transfers are outside it and social
  protection reads under 4% of the total. The spending plate says so on the
  panel, because a reader who takes those shares as shares of the budget is
  wrong by a wide margin.
- **The currency board is the markets story.** The Base Rate is the Fed funds
  target upper bound plus 50bp, and the spot rate is confined to 7.75-7.85 by
  the convertibility undertakings, so the currency panel draws the effective
  index (which moves) beside the pegged bilateral rate (which does not). That
  is the same choice the spine gives the United States' broad dollar index.
- **Bands are the staged quarterly vintage's own.** Every quarter with a
  negative year-on-year reading in C&SD's chained-volume GDP: 2008Q4-2009Q3,
  2019Q3-Q4, 2020, 2022. No band is inferred from an annual number.

Two slots are visibly pending for reasons that are not gaps in the research: a
ten-year sovereign benchmark does not exist continuously (documented in
`markets/efn_tenor_probe_from_hkma.csv` and `SOURCES.yaml`), and the Gini, the
poverty rate and the statutory minimum wage are published only inside reports
and Gazette notices, with no machine-readable official series this pass found.
Trade slot 1 is pending for a third reason, stated on the panel: the entrepot's
exports and imports of goods and services run 176-222% of GDP, past the atlas's
shared 0-100% scale, so the ratio is drawn in the lens at its own scale until
the one shared scale is widened for every country.
"""
from __future__ import annotations

from core.sideload import sibling

events = sibling(__file__, "events")

W0 = 2006        # the shared plate window opens here
FY_SHIFT = 0.25  # an April-March financial year, drawn at its midpoint


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


def _at(years, vals, year):
    return dict(zip(years, vals))[year]


def _cols(ctx, rel: str) -> dict:
    """{column: {year: value}} for a tidy CSV, blanks dropped."""
    t = ctx.table(rel)
    if not t:
        return {}
    years = t.get("year", [])
    return {k: {y: v for y, v in zip(years, t[k]) if v == v}
            for k in t if k != "year"}


def _note(p, ax, x, y, text, color=None, ha="left", va="top", size=8.0):
    """A short italic note in axes fractions."""
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=size, style="italic", color=color or p.MUTED, zorder=7)


def _foot(p, ax, text):
    """The provenance line under a panel. Keep it to one line."""
    ax.text(0.5, -0.07, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.2, color=p.FAINT, style="italic")


def _pending(ig, ax, why):
    ax.text(0.5, 0.34, why, transform=ax.transAxes, ha="center", va="top",
            fontsize=8.2, style="italic", color=ig.p.MUTED)


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(a, xticks_years=not getattr(a, "_categorical_x",
                                                      False))


def _fy_line(ctx, rel: str, col: str, gdp: dict):
    """A GRA cash figure as % of GDP, drawn at its financial year's midpoint.

    `fiscal/govt.csv` keys a year by the start of an April-March financial
    year; the divisor is that calendar year's GDP, which is the only GDP the
    publisher gives. The approximation is the March boundary — a quarter of a
    year — and the legend and the note say "financial year" on the line.
    """
    rows = ctx.rows(rel, key="year") or {}
    out = [(y + FY_SHIFT, float(r[col]) / gdp[y] * 100)
           for y, r in sorted(rows.items())
           if y in gdp and gdp[y] and (r.get(col) or "").strip()]
    return [y for y, _ in out], [v for _, v in out]


def _dual(ax, color, label):
    """A legend entry for a bar series drawn with ctx.bars."""
    ax.bar([], [], color=color, label=label)


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("economy.growth", "Real GDP growth, chain volume (% per year)")
    gy, gv = _yr(ctx, "macro/gdp.csv", "real_growth_pct")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    low = min(zip(gy, gv), key=lambda t: t[1])
    ax.annotate(f"{low[1]:.1f}%", (low[0], low[1]), textcoords="offset points",
                xytext=(0, -3), ha="center", va="top", fontsize=8.8,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96,
          "shaded: 2008-09 crisis · 2019 unrest · 2020 pandemic ·\n"
          "2022 fifth wave — the quarters C&SD measured negative")
    _foot(p, ax, "C&SD 310-30001, chained (2024) dollars. One vintage "
          "throughout; 2026 not staged")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "world/gdp_usd.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"US${_at(py, pv, 2006):,.0f} in 2006, US${pv[-1]:,.0f} in "
          f"{py[-1]} —\nat market rates, with the peg holding the divisor")
    _foot(p, ax, "World Bank NY.GDP.PCAP.CD (HKG, its own economy). "
          "Current US$, not per person present")

    ax = ig.slot("economy.inflation", "Consumer price inflation (% per year)")
    cy, cv = _yr(ctx, "macro/cpi.csv", "cpi_yoy_pct")
    uy, uv = _yr(ctx, "macro/cpi.csv", "underlying_cpi_yoy_pct")
    ctx.line(ax, cy, cv, p.ALERT, label="composite CPI")
    ctx.line(ax, uy, uv, p.NAVY, label="underlying CPI", lw=1.6, ms=3.0,
             ls=(0, (4, 2)), dashed_partial=False)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}%", (peak[0], peak[1]),
                textcoords="offset points", xytext=(0, 6), ha="center",
                fontsize=8.8, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.74,
          "no inflation target: the HKMA's objective is\nthe exchange rate, "
          "not the price level", size=7.8)
    _foot(p, ax, "C&SD 510-60001/60002. The underlying index strips the "
          "one-off relief measures")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    ly, lv = _yr(ctx, "macro/labour.csv", "unemployment_rate_pct")
    ctx.line(ax, ly, lv, p.NAVY)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ly, lv, p.NAVY, lambda v: f"{v:.1f}%", dy=8)
    hi = max(zip(ly, lv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96,
          f"peak {hi[1]:.1f}% in {hi[0]}; {lv[-1]:.1f}% in {ly[-1]}.\n"
          "The survey covers residents in households")
    _foot(p, ax, "C&SD 210-06101, General Household Survey annual averages. "
          "Foreign domestic helpers are outside it")
    _finish(ctx, ig)


# ------------------------------------------------------------------ fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p
    G = "fiscal/gg_imf.csv"
    gdp = _cols(ctx, "macro/gdp.csv").get("nominal_hkd_mn", {})

    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure "
                 "(% of GDP)")
    ry, rv = _yr(ctx, G, "revenue_pct_gdp")
    ey, ev = _yr(ctx, G, "expenditure_pct_gdp")
    ctx.line(ax, ry, rv, p.TEAL, label="Revenue")
    ctx.line(ax, ey, ev, p.ALERT, label="Expenditure")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.6, frameon=False)
    _note(p, ax, 0.98, 0.96,
          f"2024, the last year the IMF has observed:\nrevenue "
          f"{_at(ry, rv, 2024):.1f}% of GDP, spending "
          f"{_at(ey, ev, 2024):.1f}%", ha="right")
    _foot(p, ax, "IMF WEO general government, calendar years — the funds "
          "consolidated, intra-government transfers netted out")

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    oy = [y for y in ry if y in dict(zip(ey, ev))]
    overall = {y: dict(zip(ry, rv))[y] - dict(zip(ey, ev))[y] for y in oy}
    by, bv = oy, [overall[y] for y in oy]
    ctx.bars(ax, by, bv, lambda v: p.ALERT if v < 0 else p.GREEN)
    py, pv = _yr(ctx, G, "primary_balance_pct_gdp")
    ctx.line(ax, py, pv, p.NAVY, label="Primary balance")
    fy, fv = _fy_line(ctx, "fiscal/govt.csv", "balance_hkd_mn", gdp)
    # FY2025 is a closed set of accounts, so the dotted line stays solid to
    # its end: the partial-year convention belongs to a year still running.
    ctx.line(ax, fy, fv, p.GOLD, label="Cash account, financial year",
             lw=1.5, ms=2.6, ls=(0, (1, 1.6)), dashed_partial=False,
             split_year=2026)
    ig.add_recessions(ax, label=False)
    _dual(ax, p.ALERT, "Overall balance, general government")
    ax.legend(loc="lower left", fontsize=7.2, frameon=False)
    cash = {int(y): v for y, v in zip(fy, fv)}
    _note(p, ax, 0.98, 0.96,
          f"2024: the cash account is {cash[2024]:+.1f}% of GDP\n"
          f"and the consolidated perimeter {_at(by, bv, 2024):+.1f}%",
          ha="right")
    _foot(p, ax, "IMF WEO against C&SD 340-47001 (GRA, cash, Apr-Mar at its "
          "midpoint ÷ calendar GDP). Two perimeters")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    dy, dv = _yr(ctx, G, "gross_debt_pct_gdp")
    ctx.line(ax, dy, dv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.PURPLE, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"{dv[0]:.1f}% in {dy[0]} to {dv[-1]:.1f}% in {dy[-1]}: a net "
          "creditor's\ndebt, issued to build a yield curve, not to spend")
    _foot(p, ax, "IMF WEO GGXWDG_NGDP. Small because the government holds "
          "far more in reserves than it owes")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    iy, iv = _yr(ctx, G, "interest_pct_gdp")
    ctx.line(ax, iy, iv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.GOLD, lambda v: f"{v:.2f}%", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"{iv[-1]:.2f}% of GDP in {iy[-1]} — the whole debt service\nof "
          "the general government", size=7.8)
    _foot(p, ax, "IMF WEO, interest on the general-government debt")
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
#: C&SD's nine functions, mapped onto the spine's seven COFOG groups. The
#: mapping is clean for six of them; environment, housing and recreation are
#: carried together as "other" because C&SD splits them where COFOG does not.
SPEND_GROUPS = [
    ("GCE_social", "social protection", "GREEN_D"),
    ("GCE_health", "health", "PURPLE"),
    ("GCE_edu", "education", "BLUE"),
    ("GCE_public", "general public services", "NAVY"),
    ("GCE_econ", "economic affairs", "TEAL"),
    ("GCE_safety", "defence and public order", "ALERT"),
]
OTHER = (("GCE_envir", "GCE_housing", "GCE_recre"), "other", "GOLD")


def _gce_shares(ctx):
    """C&SD's GCE by function as % of GDP, from the HK$ million columns."""
    t = ctx.table("spending/gce_function.csv")
    gdp = _cols(ctx, "macro/gdp.csv").get("nominal_hkd_mn", {})
    out: dict[str, dict[int, float]] = {}
    if not t:
        return out, []
    for row_year, fn, mn in zip(t["year"], t["function"], t["spending_hkd_mn"]):
        if fn in gdp:
            continue
        y = row_year
        if y not in gdp or mn != mn:
            continue
        out.setdefault(fn, {})[y] = mn / gdp[y] * 100
    years = sorted(out.get("GCE", {}))
    return out, years


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    gce, years = _gce_shares(ctx)

    ax = ig.slot("spending.by_function",
                 "Government consumption by function (% of GDP)")
    layers, labels, colors = [], [], []
    for fn, label, colour in SPEND_GROUPS:
        layers.append([gce.get(fn, {}).get(y, 0.0) for y in years])
        labels.append(label)
        colors.append(getattr(p, colour))
    other = [sum(gce.get(f, {}).get(y, 0.0) for f in OTHER[0])
             for y in years]
    layers.append(other)
    labels.append(OTHER[1])
    colors.append(getattr(p, OTHER[2]))
    ax.stackplot(years, *layers, labels=labels, colors=colors, alpha=0.9, lw=0)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=6.6, ncol=4, frameon=False)
    tot = gce.get("GCE", {})
    _note(p, ax, 0.98, 0.52,
          f"{tot[years[-1]]:.1f}% of GDP in {years[-1]} — and this is\n"
          "government CONSUMPTION, not total spending:\n"
          "cash transfers are not in the table", ha="right", size=7.8)
    _foot(p, ax, "C&SD 310-32023 (national functional classification, not "
          "COFOG) ÷ nominal GDP. Seven groups, mapped")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    soc = gce.get("GCE_social", {})
    ctx.line(ax, years, [tot[y] - soc[y] for y in years], p.NAVY,
             label="Everything else")
    ctx.line(ax, years, [soc[y] for y in years], p.ALERT,
             label="Social protection")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.62,
          f"social protection is {soc[years[-1]] / tot[years[-1]] * 100:.1f}% "
          f"of government consumption\nand {soc[years[-1]]:.1f}% of GDP in "
          f"{years[-1]}: the elderly allowance and\nsocial security are cash "
          "transfers, and transfers sit\noutside GCE entirely", size=7.6)
    _foot(p, ax, "Same series as slot 1: one function against the remainder")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(% of GDP)")
    iy, iv = _yr(ctx, "spending/investment.csv", "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.TEAL, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"{iv[-1]:.1f}% in {iy[-1]}, down from {max(iv):.1f}% in "
          f"{iy[iv.index(max(iv))]}:\nwhole-economy fixed investment, not "
          "the budget")
    _foot(p, ax, "C&SD 310-32031, gross domestic fixed capital formation ÷ "
          "nominal GDP")

    ax = ig.slot("spending.public_investment",
                 "Public investment (% of GDP)")
    py, pv = _yr(ctx, "spending/investment.csv", "public_gfcf_pct_gdp")
    ctx.line(ax, py, pv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.GOLD, lambda v: f"{v:.1f}%", dy=-14)
    _note(p, ax, 0.02, 0.96,
          f"{pv[-1]:.1f}% of GDP in {py[-1]}; {pv[0]:.1f}% in {py[0]}.\n"
          "Public sector as C&SD defines it: government and\npublic "
          "corporations, not an SNA sector split", size=7.8)
    _foot(p, ax, "C&SD 310-32031, the publisher's own public/private split")
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
def plate_trade(ctx, ig) -> None:
    p = ctx.p
    T = "trade/trade_gdp.csv"

    ax = ig.slot("trade.exports_imports", "Exports and imports (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax,
             "Hong Kong's exports and imports of goods and services run\n"
             "176-222% of GDP: an entrepot re-exports what it imports.\n"
             "The atlas's shared scale ends at 100%, and one country may\n"
             "not carry its own. Drawn in the lens until it is widened.")
    _foot(p, ax, "C&SD 310-31002. The extent and the slot are in "
          "DATA_NOTES.md §10")

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    by, bv = _yr(ctx, T, "balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{bv[-1]:+.1f}%", (by[-1], bv[-1]),
                textcoords="offset points", xytext=(-4, 8), ha="right",
                fontsize=8.6, fontweight="bold", color=p.GREEN)
    _note(p, ax, 0.02, 0.96,
          "goods and services together: +2.9% of GDP in 2025\nwhile the "
          "customs goods balance is negative every year")
    _foot(p, ax, "C&SD 310-31002, exports minus imports of goods and "
          "services ÷ GDP — not the customs series")

    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    d = {}
    t = ctx.table("trade/destinations.csv")
    for y, name, share in zip(t["year"], t["destination"], t["share_pct"]):
        d.setdefault(name, {})[y] = share
    for name, colour in (("Chinese Mainland", p.RED), ("USA", p.BLUE),
                         ("Japan", p.GOLD), ("Vietnam", p.GREEN)):
        s = d.get(name, {})
        ys = sorted(s)
        if ys:
            ctx.line(ax, ys, [s[y] for y in ys], colour, label=name)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="center right", fontsize=7.4, frameon=False)
    mn = d["Chinese Mainland"]
    us = d["USA"]
    _note(p, ax, 0.02, 0.96,
          f"the Mainland takes {mn[max(mn)]:.0f}% of goods exports in "
          f"{max(mn)};\nthe United States {us[2006]:.0f}% in 2006, "
          f"{us[max(us)]:.1f}% in {max(us)}", size=7.8)
    _foot(p, ax, "C&SD 410-50013, total exports including re-exports. The "
          "ten destinations are the latest year's ten")

    ax = ig.slot("trade.lens", "Openness — goods and services against "
                 "customs goods (% of GDP, own scale)")
    xy, xv = _yr(ctx, T, "exports_gnfs_pct_gdp")
    my, mv = _yr(ctx, T, "imports_gnfs_pct_gdp")
    ctx.line(ax, xy, xv, p.BLUE, label="Exports, goods and services")
    ctx.line(ax, my, mv, p.ALERT, label="Imports, goods and services")
    gdp = _cols(ctx, "macro/gdp.csv").get("nominal_hkd_mn", {})
    mer = _cols(ctx, "trade/merchandise.csv")
    ey = [y for y in sorted(mer.get("exports_hkd_mn", {})) if y in gdp]
    ctx.line(ax, ey, [mer["exports_hkd_mn"][y] / gdp[y] * 100 for y in ey],
             p.FAINT, label="Merchandise exports, customs basis", lw=1.5,
             ms=2.6, ls=(0, (1, 1.6)), dashed_partial=False)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.0, frameon=False)
    ig.headroom(ax, top=0.22)
    _note(p, ax, 0.02, 0.96,
          "two measurements, not one: the national accounts count goods\n"
          "and services, customs counts goods and the re-export margin")
    _foot(p, ax, "C&SD 310-31002 and 410-50001. The panel the spine's scale "
          "cannot hold — see slot 1")
    _finish(ctx, ig)


# ----------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ky, kv = _yr(ctx, "markets/base_rate.csv", "base_rate_pct")
    cy, cv = _yr(ctx, "macro/cpi.csv", "cpi_yoy_pct")
    ctx.line(ax, ky, kv, p.NAVY, label="HKMA Base Rate")
    ctx.line(ax, cy, cv, p.ALERT, label="Composite CPI inflation")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    x, label = events.MARKS["fed_hikes"]
    ig.add_event(ax, x, label, dy=0.78)
    x, label = events.MARKS["fed_cuts"]
    ig.add_event(ax, x, label, dy=0.62)
    _note(p, ax, 0.02, 0.96,
          f"{kv[-1]:.2f}% averaged in {ky[-1]}. The Base Rate is the US "
          "Fed's\ntarget upper bound plus 50bp: a currency-board rule, not\n"
          "a local decision — the peg imports American policy", size=7.8)
    _foot(p, ax, "HKMA Base Rate (BIS WS_CBPOL, D.HK: a compilation) and "
          "C&SD's composite CPI")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    ctx.pending(ax)
    _pending(ig, ax,
             "No continuous ten-year benchmark exists. At every year-end\n"
             "2015-2023 the only 10Y-coded notes outstanding had under\n"
             "two years left, and from 2024 the HKMA issues 2- and\n"
             "15-year paper only. A 15-year tenor is not relabelled.")
    _foot(p, ax, "EFBN closing archive, probed year by year: "
          "markets/efn_tenor_probe_from_hkma.csv")

    ax = ig.slot("markets.currency", "Currency against the US$ "
                 "(index 2006 = 100, up = stronger)")
    fx = _cols(ctx, "markets/fx.csv")
    ny, nv = ctx.index_2006(fx.get("neer_index_2020", {}))
    iy, iv = ctx.fx_index(fx.get("hkd_per_usd", {}))
    ctx.line(ax, ny, nv, p.TEAL, label="Effective rate, trade-weighted")
    ctx.line(ax, iy, iv, p.FAINT, label="HKD per US$ — the peg", lw=1.5,
             ms=2.6, ls=(0, (1, 1.6)), dashed_partial=False)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.2, frameon=False)
    _note(p, ax, 0.02, 0.55,
          "the bilateral rate cannot move: the currency board holds it\n"
          "between 7.75 and 7.85. The effective index can, and does",
          size=7.8)
    _foot(p, ax, "C&SD 340-46001/46002, rebased to 2006 = 100 (a display "
          "transform). The peg is 7.798 in 2025")

    ax = ig.slot("markets.equities", "Main equity index in US$ "
                 "(index 2006 = 100, in US$)")
    z = _cols(ctx, "markets/equity.csv")
    hsi = z["hsi_usd_index_2006"]
    spx = z["sp500_usd_index_2006"]
    hy = sorted(hsi)
    sy = sorted(spx)
    ctx.line(ax, hy, [hsi[y] for y in hy], p.RED,
             label="Hang Seng Index, in US$")
    ctx.line(ax, sy, [spx[y] for y in sy], p.NAVY,
             label="S&P 500", lw=1.6, ms=3.0, ls=(0, (4, 2)),
             dashed_partial=False)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    _note(p, ax, 0.98, 0.96,
          f"{hsi[hy[-1]] / 100:.2f}× its 2006 level in {hy[-1]} against\n"
          f"{spx[sy[-1]] / 100:.2f}× for the S&P 500", ha="right", size=7.6)
    _foot(p, ax, "Hang Seng Indexes Company via Yahoo Finance (not an "
          "official statistic). Year-end closes, not averages")
    _finish(ctx, ig)


# ------------------------------------------------------------------ credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    hy, hv = _yr(ctx, "credit/household_debt.csv", "household_debt_pct_gdp")
    ctx.line(ax, hy, hv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, hy, hv, p.PURPLE, lambda v: f"{v:.0f}%", dy=8)
    peak = max(zip(hy, hv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96,
          f"{_at(hy, hv, 2006):.0f}% in 2006, a peak of {peak[1]:.0f}% in "
          f"{peak[0]},\n{hv[-1]:.0f}% at the end of {hy[-1]}")
    _foot(p, ax, "BIS total credit, credit to households and NPISHs, "
          "end-Q4, % of GDP (a compilation)")

    ax = ig.slot("credit.lending_rate",
                 "Household lending rate vs policy rate (%)")
    by, bv = _yr(ctx, "markets/lending_rate.csv", "best_lending_rate_pct")
    ky, kv = _yr(ctx, "markets/base_rate.csv", "base_rate_pct")
    ctx.line(ax, by, bv, p.RED, label="Best lending rate (prime)")
    ctx.line(ax, ky, kv, p.NAVY, label="HKMA Base Rate")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"prime {bv[-1]:.2f}% against a Base Rate of {kv[-1]:.2f}% in "
          f"{by[-1]}.\nMortgages are priced at prime minus a spread",
          size=7.8)
    _foot(p, ax, "C&SD 340-45021, annual averages. The effective "
          "new-mortgage rate is published in prose only")

    ax = ig.slot("credit.npl", "Classified loans (% of loans)")
    t = ctx.table("credit/classified_loans.csv")
    rows = sorted((y, v) for y, q, v in
                  zip(t["year"], t["quarter"], t["classified_loans_pct"])
                  if q == "Q4")
    ctx.line(ax, [y for y, _ in rows], [v for _, v in rows], p.ALERT,
             label="Classified loans at each year-end")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, [y for y, _ in rows], [v for _, v in rows], p.ALERT,
                 lambda v: f"{v:.2f}%", dy=8)
    _note(p, ax, 0.02, 0.96,
          "the HKMA's own asset-quality measure, at each year-end:\n"
          "substandard, doubtful and loss together — not IFRS 9 stage 3",
          size=7.8)
    _foot(p, ax, "HKMA Monthly Statistical Bulletin 3.6.1, authorised "
          "institutions, Q4 of each year")

    ax = ig.slot("credit.lens", "What a deposit pays — savings rate against "
                 "prime (%, annual averages)")
    sv = _cols(ctx, "markets/lending_rate.csv").get("savings_deposit_rate_pct",
                                                    {})
    sy = sorted(sv)
    ctx.line(ax, sy, [sv[y] for y in sy], p.TEAL, label="Savings deposit rate")
    ctx.line(ax, by, bv, p.RED, label="Best lending rate (prime)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    ig.headroom(ax, top=0.20)
    flat = [y for y in sy if sv[y] < 0.05]
    _note(p, ax, 0.98, 0.96,
          f"a savings account paid {min(sv.values()):.2f}% in "
          f"{flat[0]}-{flat[-1]}\nwhile prime stayed at "
          f"{dict(zip(by, bv))[flat[0]]:.2f}%: the spread is the\n"
          "banks' margin, and depositors are the ones paying it",
          ha="right", size=7.4)
    _foot(p, ax, "C&SD 340-45021, annual averages of the advertised rates. "
          "Neither is a market yield")
    _finish(ctx, ig)


# ------------------------------------------------------------------ people
def plate_people(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("people.gini", "Income inequality, Gini (0-100)")
    ctx.pending(ax)
    _pending(ig, ax,
             "Published in the 2021 census thematic report and the\n"
             "Household Expenditure Survey reports as PDF tables. Not one\n"
             "of C&SD's 590 web tables, absent from data.gov.hk, empty in\n"
             "the World Bank, and the HDR carries none.")
    _foot(p, ax, "SOURCES.yaml meta.pending — the number exists, the route "
          "does not")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    ctx.pending(ax)
    _pending(ig, ax,
             "The relative poverty rate (50% of median household income)\n"
             "is published annually in the Hong Kong Poverty Situation\n"
             "Report, as PDF and XLSX attachments. Hong Kong is not a\n"
             "World Bank PIP country, so no harmonised line exists either.")
    _foot(p, ax, "SOURCES.yaml meta.pending — report-only, not staged")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    ctx.pending(ax)
    _pending(ig, ax,
             "The statutory minimum is an HOURLY rate set by the Minimum\n"
             "Wage Commission and published in the Gazette; the Labour\n"
             "Department's pages answer 404 and data.gov.hk has nothing.\n"
             "A monthly US$ figure would be an assumption, not a statistic.")
    _foot(p, ax, "SOURCES.yaml meta.pending — statutory, hourly, no machine "
          "route found")

    ax = ig.slot("people.lens", "Median household income, HK$ per month at "
                 "2024 prices", unit=False)
    iy, iv = _yr(ctx, "people/income.csv",
                 "median_household_income_real_2024_hkd")
    iy2, iv2 = _yr(ctx, "people/income.csv", "median_household_income_hkd")
    ctx.line(ax, iy, iv, p.GOLD, label="At 2024 prices")
    ctx.line(ax, iy2, iv2, p.FAINT, label="Cash, as paid", lw=1.5, ms=2.6,
             ls=(0, (1, 1.6)), dashed_partial=False)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower right", fontsize=7.2, frameon=False)
    ig.headroom(ax, top=0.22)
    _note(p, ax, 0.02, 0.96,
          f"HK${iv2[0]:,.0f} a month in 2006 and HK${iv2[-1]:,.0f} in "
          f"{iy2[-1]}, which buys\nHK${iv[-1]:,.0f} of 2024 — the "
          "household median, not a person's")
    _foot(p, ax, "C&SD 130-06102. The real column is deflated by the "
          "composite CPI — a display transform, not a published figure")
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "world/gdp_usd.csv", "gdp_usd_bn")
    ctx.line(ax, gy, gv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.BLUE, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"US${gv[0]:,.0f}bn in {gy[0]}, US${gv[-1]:,.0f}bn in {gy[-1]} —\n"
          "at market rates, so the line moves with the peg as well as output")
    _foot(p, ax, "World Bank NY.GDP.MKTP.CD. Hong Kong is HKG in every "
          "international dataset, never CHN")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "world/hdi.csv", "hdi")
    ctx.line(ax, hy, hv, p.GREEN)
    ctx.endlabel(ax, hy, hv, p.GREEN, lambda v: f"{v:.3f}", dy=-14)
    _note(p, ax, 0.02, 0.30,
          f"{hv[0]:.3f} in {hy[0]} to {hv[-1]:.3f} in {hy[-1]} — one HDR\n"
          "vintage (2025) throughout, so no revision step sits in the line")
    _foot(p, ax, "UNDP HDR 2025. The file runs to 2023; 2024 and 2025 are "
          "empty until the next report")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (0-100)")
    cy, cv = _yr(ctx, "world/corruption.csv", "cpi_score")
    ctx.line(ax, cy, cv, p.PURPLE)
    ctx.endlabel(ax, cy, cv, p.PURPLE, lambda v: f"{v:.0f}", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"{cv[0]:.0f} in {cy[0]} to {cv[-1]:.0f} in {cy[-1]}. The 0-10\n"
          "scores before 2012 are a different method and are not staged")
    _foot(p, ax, "Transparency International CPI 2025 workbook (a "
          "compilation). Higher is cleaner")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn, year-end)")
    ry, rv = _yr(ctx, "world/reserves.csv", "reserves_usd_mn")
    rb = [v / 1000 for v in rv]
    ctx.line(ax, ry, rb, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rb, p.TEAL, lambda v: f"US${v:,.0f}bn", dy=8)
    hi = max(zip(ry, rb), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96,
          f"peak US${hi[1]:,.0f}bn in {hi[0]}; US${rb[-1]:,.0f}bn at the "
          f"end of {ry[-1]}.\nMore than the whole economy's annual output")
    _foot(p, ax, "HKMA 8.4, Exchange Fund foreign currency assets — not the "
          "government's fiscal reserves and not the monetary base")
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    wy, wv = _yr(ctx, "demography/population.csv", "population")
    iy, iv = ctx.index_2006(dict(zip(wy, wv)))
    ctx.line(ax, iy, iv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.BLUE, lambda v: f"{v:.0f}", dy=8)
    x, label = events.MARKS["reopening"]
    ig.add_event(ax, x, label, dy=0.70)
    _note(p, ax, 0.02, 0.96,
          f"{wv[0] / 1e6:.2f}m mid-{wy[0]} to {wv[-1] / 1e6:.2f}m "
          f"mid-{wy[-1]};\nthe 2022 trough is the year the border was shut",
          size=7.8)
    _foot(p, ax, "C&SD 110-01001, mid-year population. Includes foreign "
          "domestic helpers; the FDH-excluded variant is separate")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    fy, fv = _yr(ctx, "demography/fertility.csv", "tfr")
    ctx.line(ax, fy, fv, p.RED)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, fy, fv, p.RED, lambda v: f"{v:.2f}", dy=-14)
    ax.axhline(2.1, color=p.FAINT, lw=1.0, ls=(0, (4, 3)), zorder=2)
    _note(p, ax, 0.02, 0.96,
          f"{fv[0]:.2f} in {fy[0]}, {fv[-1]:.2f} in {fy[-1]}. The dashed "
          "line is\nreplacement (2.1) — no year in this window comes near "
          "it", size=7.8)
    _foot(p, ax, "C&SD 115-01011, the headline rate EXCLUDING foreign "
          "domestic helpers — the one comparable with other countries")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    by, bv = _yr(ctx, "demography/vital.csv", "birth_rate_per_1000")
    dy, dv = _yr(ctx, "demography/vital.csv", "death_rate_per_1000")
    ctx.line(ax, by, bv, p.TEAL, label="Births")
    ctx.line(ax, dy, dv, p.ALERT, label="Deaths")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    cross = min((y for y in by if y in dict(zip(dy, dv))
                 and dict(zip(dy, dv))[y] > dict(zip(by, bv))[y]),
                default=None)
    _note(p, ax, 0.02, 0.96,
          f"births {bv[-1]:.1f}, deaths {dv[-1]:.1f} per 1,000 in "
          f"{by[-1]}. Deaths have\nexceeded births since {cross if cross else '-'}"
          " — and the birth rate fell by two thirds", size=7.8)
    _foot(p, ax, "C&SD 115-01011, the publisher's own rates per 1,000 "
          "mid-year population")

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net movement (per 1,000 people)")
    c = _cols(ctx, "demography/components.csv")
    pop = dict(zip(*ctx.series(ctx.table("demography/population.csv"),
                              "population")))
    nat = {y: v * 1000 for y, v in c.get("natural_change_k", {}).items()}
    ny, nv = ctx.per_1000(nat, pop)
    my, mv = _yr(ctx, "migration/net_movement.csv", "net_movement_per_1000")
    low = min(mv)
    ctx.pending(ax)
    _pending(ig, ax,
             f"Net movement is {low:+.1f} per 1,000 in "
             f"{my[mv.index(low)]}, outside the\nshared -10 to +40 scale, "
             "and the two series share this panel.\nNet movement is drawn "
             "in the migration chapter's lens at its\nown scale; this slot "
             "fills when the shared scale is widened.")
    _foot(p, ax, f"Deaths outnumber births since 2020 ({nv[-1]:+.1f} per "
          "1,000 in 2025). C&SD 110-01003")
    _finish(ctx, ig)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    hy, hv = _yr(ctx, "security/crime.csv", "homicide_rate_per_100k")
    cy, cv = _yr(ctx, "security/crime.csv", "murder_and_manslaughter")
    ctx.line(ax, hy, hv, p.ALERT, label="Murder and manslaughter, police")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower right", fontsize=7.2, frameon=False)
    ig.headroom(ax, top=0.32)
    ax.annotate(f"{cv[-1]:.0f} cases", (hy[-1], hv[-1]),
                textcoords="offset points", xytext=(-6, 10), ha="right",
                fontsize=8.8, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96,
          f"the police re-based the offence classification in 2021, so the "
          f"line\nstarts there. {hy[-1]}'s {cv[-1]:.0f} cases are not a trend: "
          "170 of them\nwere reported in the fourth quarter, against 19 "
          "across the first\nthree — published exactly as recorded, the "
          "annual row reading 194\nwhere the quarters sum to 189", size=7.2)
    _foot(p, ax, "Hong Kong Police via C&SD 940-92033, cases ÷ mid-year "
          "population")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    ctx.pending(ax)
    _pending(ig, ax,
             "The Department of Health publishes one 'external causes\n"
             "(V01-Y89)' row holding suicides, road deaths and falls\n"
             "together. Hong Kong is not a WHO member state, so the GHO\n"
             "has no row; the World Bank is empty. Not guessed.")
    _foot(p, ax, "SOURCES.yaml meta.pending — the Coroner's reports are PDF "
          "only")

    ax = ig.slot("security.road_deaths", "Road traffic deaths "
                 "(per 100,000)")
    ctx.pending(ax)
    _pending(ig, ax,
             "The Transport Department publishes road accident statistics\n"
             "in reports and a one-off feature article; no annual series\n"
             "is staged, and the World Bank and WHO both have no HKG row.\n"
             "The slot stays pending rather than borrowing another cause.")
    _foot(p, ax, "SOURCES.yaml meta.pending — data.gov.hk has no series")

    ax = ig.slot("security.lens", "Reported offences, all types "
                 "(per 100,000, own scale)", unit=False)
    t = ctx.table("security/crime.csv")
    pop = dict(zip(*ctx.series(ctx.table("demography/population.csv"),
                              "population")))
    ty = [int(y) for y in t["year"]]
    cases = dict(zip(ty, t["total_cases"]))
    violent = dict(zip(ty, t["violent_crime_cases"]))
    yrs = sorted(y for y in cases if y in pop and cases[y] == cases[y])
    xs = list(range(len(yrs)))
    ax.bar(xs, [cases[y] / pop[y] * 1e5 for y in yrs], width=0.66,
           color=p.BLUE, edgecolor="white", linewidth=0.6, zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(y) for y in yrs])
    ax.set_xlim(-0.6, len(yrs) - 0.4)
    ax._categorical_x = True
    ig.headroom(ax, top=0.26)
    for x, y in zip(xs, yrs):
        ax.annotate(f"{cases[y] / pop[y] * 1e5:,.0f}", (x, cases[y]
                    / pop[y] * 1e5), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=8.4,
                    color=p.MUTED)
    _note(p, ax, 0.02, 0.96,
          f"all reported offences, {cases[yrs[-1]] / pop[yrs[-1]] * 1e5:,.0f} "
          f"per 100,000 in {yrs[-1]} against\n"
          f"{cases[yrs[0]] / pop[yrs[0]] * 1e5:,.0f} in {yrs[0]}; violent "
          "crime is "
          f"{violent[yrs[-1]] / cases[yrs[-1]] * 100:.0f}% of it.\n"
          "Five years is all the re-based classification allows",
          size=7.4)
    _foot(p, ax, "C&SD 940-92033 ÷ mid-year population. A lens: the range "
          "is country-local by design")
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000 people)")
    dy, dv = _yr(ctx, "mortality/deaths.csv", "crude_death_rate_per_1000")
    ctx.line(ax, dy, dv, p.INK)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.INK, lambda v: f"{v:.1f}", dy=8)
    peak = max(zip(dy, dv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96,
          f"{dv[0]:.1f} in {dy[0]}, {peak[1]:.1f} in {peak[0]} — the "
          f"pandemic\nyear — and {dv[-1]:.1f} in {dy[-1]}")
    _foot(p, ax, "Department of Health registered deaths ÷ mid-year "
          "population. C&SD's vital rate agrees in trend")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above 2015-2019 average)")
    ey, ev = _yr(ctx, "mortality/deaths.csv",
                 "excess_deaths_pct_vs_2015_2019", since=2015)
    ctx.bars(ax, ey, ev, lambda v: p.ALERT if v > 5 else p.BLUE)
    ig.add_recessions(ax, label=False)
    peak = max(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:+.0f}%", (peak[0], peak[1]),
                textcoords="offset points", xytext=(0, 6), ha="center",
                fontsize=8.8, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96,
          f"from 2015, the years the baseline is drawn from: "
          f"{peak[1]:+.0f}% in {peak[0]},\nthe fifth wave. Earlier years "
          "would be a comparison with a\nbaseline that had not happened yet")
    _foot(p, ax, "Computed from the Department of Health's all-cause "
          "counts ÷ mean(2015-2019) - 1")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    c = _cols(ctx, "mortality/deaths.csv").get("covid_deaths", {})
    pop = dict(zip(*ctx.series(ctx.table("demography/population.csv"),
                              "population")))
    cy, cv = ctx.per_100k(dict(c), pop)
    ctx.bars(ax, cy, cv, lambda v: p.ALERT)
    ig.add_recessions(ax, label=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.0f}", (peak[0], peak[1]),
                textcoords="offset points", xytext=(0, 6), ha="center",
                fontsize=8.8, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96,
          f"{peak[1]:.0f} per 100,000 in {peak[0]}; {cv[-1]:.0f} in "
          f"{cy[-1]}.\nCoded to J98.8 to 2023, U07.1/U07.2 from 2024")
    _foot(p, ax, "Department of Health, registered deaths with COVID-19 as "
          "the underlying cause. 2025 is not published yet")

    ax = ig.slot("mortality.lens", "Life expectancy at birth (years)",
                 unit=False)
    my, mv = _yr(ctx, "demography/vital.csv", "life_expectancy_male")
    fy, fv = _yr(ctx, "demography/vital.csv", "life_expectancy_female")
    ctx.line(ax, fy, fv, p.TEAL, label="Women")
    ctx.line(ax, my, mv, p.BLUE, label="Men")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower right", fontsize=7.2, frameon=False)
    ig.headroom(ax, top=0.20)
    _note(p, ax, 0.02, 0.96,
          f"{fv[-1]:.1f} years for women, {mv[-1]:.1f} for men in {fy[-1]}. "
          "The 2022\ndip — {:.1f} for men — is the pandemic's own".format(
              dict(zip(my, mv))[2022]))
    _foot(p, ax, "C&SD 115-01011, period life tables published with the "
          "vital events")
    _finish(ctx, ig)


# --------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    ctx.pending(ax)
    _pending(ig, ax,
             "Hong Kong publishes no gross immigration or emigration on a\n"
             "residence basis: there is no counterpart to Eurostat's\n"
             "migr_imm/migr_emi. The Immigration Department counts\n"
             "passenger movements, which are journeys, not migrants.")
    _foot(p, ax, "SOURCES.yaml meta.pending — the residual is in slot 2")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    ny, nv = _yr(ctx, "migration/net_movement.csv", "net_movement_per_1000")
    worst = min(zip(ny, nv), key=lambda t: t[1])
    ctx.pending(ax)
    _pending(ig, ax,
             f"C&SD's net movement reads {worst[1]:+.1f} per 1,000 in "
             f"{worst[0]} —\noutside the shared -10 to +40 scale. It is the "
             "publisher's\nown net measure: population change minus births "
             "plus deaths,\na residual, not an arrivals count. Drawn in the "
             "lens below.")
    _foot(p, ax, "C&SD 110-01003, 12 months to 31 December ÷ mid-year "
          "population")

    ax = ig.slot("migration.foreign_born", "Foreign-born share of the "
                 "population (%)")
    ctx.pending(ax)
    _pending(ig, ax,
             "The 2021 census gives a single foreign-born share; C&SD's\n"
             "web tables carry no annual birthplace series. One census\n"
             "point is not a time series, and the atlas does not\n"
             "interpolate between census points.")
    _foot(p, ax, "SOURCES.yaml meta.pending — census points only")

    ax = ig.slot("migration.lens", "Net movement and the publisher's own "
                 "split (thousands, 12 months to December)")
    c = _cols(ctx, "migration/net_movement.csv")
    oy = sorted(c.get("net_movement_k", {}))
    ctx.bars(ax, oy, [c["net_movement_k"][y] for y in oy],
             lambda v: p.GREEN if v >= 0 else p.ALERT)
    ctx.line(ax, oy, [c["one_way_permit_k"][y] for y in oy], p.RED,
             label="One-way permit holders")
    ctx.line(ax, oy, [c["others_k"][y] for y in oy], p.NAVY,
             label="Everyone else")
    _dual(ax, p.FAINT, "Net movement, total")
    ig.add_recessions(ax, label=False)
    ax.axhline(0, color=p.MUTED, lw=0.8, zorder=2)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    ig.headroom(ax, top=0.20, bottom=0.10)
    low = min(zip(oy, [c["others_k"][y] for y in oy]), key=lambda t: t[1])
    _note(p, ax, 0.98, 0.96,
          f"{low[0]}: {low[1]:+.0f} thousand net, everyone but permit\n"
          "holders — what a residual of this kind can tell you,\n"
          "and no more", ha="right", size=7.4)
    _foot(p, ax, "C&SD 110-01003. All three are NET figures within their "
          "category, not arrivals and departures")
    _finish(ctx, ig)


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Economy — A Pegged Price Level and Four Downturns",
         subtitle="C&SD's national accounts on one chained-volume vintage, "
                  "with the World Bank's dollar reading of the same output.",
         source="Sources: Census and Statistics Department 310-30001, "
                "510-60001/60002, 210-06101 · World Bank WDI",
         alt="Four panels on Hong Kong's economy, 2006-2026. Real GDP growth "
             "averaged about 3% a year and fell in three episodes plus one "
             "quarter: -2.5% in 2009, -1.7% in 2019, -6.5% in 2020 and -3.7% "
             "in 2022, recovering to +3.6% in 2025; GDP per person in US "
             "dollars doubled from 28,224 to 56,983; consumer price "
             "inflation stayed between 0.3% and 5.3% and is 1.4% in 2025, with "
             "no target line because Hong Kong has no inflation target; "
             "unemployment ran 2.8-5.8% and is 3.7% in 2025."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — Two Perimeters, Never Joined",
         subtitle="The IMF's consolidated general government on calendar "
                  "years, with the government's own cash account beside it "
                  "by financial year.",
         source="Sources: IMF World Economic Outlook (October 2026) · C&SD "
                "340-47001, General Revenue Account",
         alt="Four panels on Hong Kong's public finances. General-government "
             "revenue ran 17-25% of GDP and expenditure 14-30%, with a "
             "primary deficit of 5.6% of GDP in 2024; the cash account shows "
             "a surplus that year on its own narrower perimeter; gross debt "
             "rose from 1.4% of GDP in 2006 to 9.2% in 2024 as the bond "
             "programme issued; interest paid is 0.19% of GDP, the whole debt "
             "service of a government that is a large net creditor."),
    dict(id="03", slug="spending", topic="spending",
         builder=plate_spending,
         title="Spending — Government Consumption, Function by Function",
         subtitle="C&SD's national functional classification mapped onto the "
                  "spine's seven groups: consumption only, not the budget.",
         source="Sources: C&SD 310-32023 (government consumption by "
                "function) and 310-32031 (fixed capital formation)",
         alt="Four panels on what Hong Kong's government consumes. Health "
             "takes about 30% of government consumption and public order "
             "22%; social protection is 3.7% of government consumption because "
             "cash transfers sit outside it altogether; whole-economy "
             "investment "
             "fell from 25.4% of GDP in 2012 to 16.9% in 2025; public "
             "investment is 6.0% of GDP."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — An Entrepot's Two Measurements",
         subtitle="Goods and services on the national accounts, goods alone "
                  "at customs, and the destinations that dominate both.",
         source="Sources: C&SD 310-31002, 410-50001, 410-50013",
         alt="Four panels on Hong Kong's trade. The canonical exports and "
             "imports panel is pending because the ratio runs 176-222% of "
             "GDP and the atlas's shared scale ends at 100%; the lens draws "
             "both measurements instead, the national-accounts ratio above "
             "the customs goods ratio; the goods-and-services surplus is "
             "+2.9% of GDP in 2025 while the customs goods balance is "
             "negative every year; the Chinese Mainland takes 59.7% of goods "
             "exports in 2025 and the United States 6.2%, down from 15%."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Money & Markets — A Currency Board's Rates",
         subtitle="The Base Rate that follows the Fed, the effective "
                  "exchange rate, and the peg that does not move.",
         source="Sources: HKMA Base Rate via BIS WS_CBPOL · C&SD "
                "340-46001/46002 · Hang Seng Indexes via Yahoo Finance "
                "(not official)",
         alt="Four panels on Hong Kong's markets. The Base Rate averaged "
             "0.50% from 2009 to 2014, rose to 5.57% in 2024 and is 4.62% in "
             "2025, tracking the Fed at a fixed 50 basis point wedge; the "
             "ten-year yield panel is pending because no continuous "
             "benchmark exists; the trade-weighted effective rate fell to 85 "
             "in 2011 and is back near 100 while the pegged bilateral rate "
             "holds inside 7.75-7.85; the Hang Seng Index in US dollars is "
             "1.28 times its 2006 level against 4.8 times for the S&P 500."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — Household Debt and What a Deposit Pays",
         subtitle="BIS household credit, the prime rate, the HKMA's "
                  "classified loans, and the margin between what a "
                  "deposit earns and what a loan costs.",
         source="Sources: BIS total credit · C&SD 340-45021/45022 · HKMA "
                "Monthly Statistical Bulletin 3.6.1",
         alt="Four panels on credit. Household debt rose from 52% of GDP in "
             "2006 to a peak of 96% in 2022 and is 88%; the best lending "
             "rate is 5.19% against a Base Rate of 4.62%; classified loans "
             "rose from 0.55% in 2018 to 2.01% at the end of 2025; a savings "
             "account paid 0.01% from 2009 to 2018 while prime stayed at "
             "5.00%."),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="People — Where the Income Distribution Is Not Published",
         subtitle="Three canonical panels have no machine-readable official "
                  "series; the lens carries the household median that does.",
         source="Sources: C&SD 130-06102 · SOURCES.yaml meta.pending",
         alt="Four panels on living standards. The Gini, the poverty rate "
             "and the statutory minimum wage are visibly pending, each with "
             "the publication it appears in; the lens draws the median "
             "household income, HK$17,000 a month in 2006 and HK$30,000 in "
             "2025, which is HK$27,548 in 2024 prices — barely above its "
             "2006 level in real terms."),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="Hong Kong in the World — An Economy, Not a Nation",
         subtitle="GDP and reserves in dollars, the UNDP's development index "
                  "and Transparency International's score.",
         source="Sources: World Bank WDI · UNDP HDR 2025 · Transparency "
                "International CPI 2025 · HKMA 8.4",
         alt="Four panels on Hong Kong among the world's economies. GDP rose "
             "from US$194bn in 2006 to US$427bn in 2025; the Human "
             "Development Index is 0.955 in 2023; the corruption score is 76 "
             "of 100 in 2025, measured on the 2012 method only; reserves are "
             "US$428bn, more than the economy's annual output."),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — A Population That Stopped Growing",
         subtitle="Mid-year population, fertility, births and deaths, and the "
                  "components of change on the publisher's own 12-month basis.",
         source="Sources: C&SD 110-01001, 110-01003, 115-01011",
         alt="Four panels on Hong Kong's population. It rose from 6.86 "
             "million in 2006 to a 2021 trough and is 7.50 million in 2025, "
             "an index of 109; the fertility rate is 0.73 children per woman "
             "in 2025, a third of replacement; deaths have exceeded births "
             "since 2020 and the birth rate fell from 13.5 to 4.1 per 1,000; "
             "net movement swings from -86 thousand in 2020 to +101 thousand "
             "in 2022."),
    dict(id="10", slug="security", topic="security", builder=plate_security,
         title="Security — A Short Police Series and One Anomalous Quarter",
         subtitle="Reported offences from the 2021 re-base, and the quarterly "
                  "table that carries a single unexplained spike.",
         source="Sources: Hong Kong Police via C&SD 940-92033",
         alt="Four panels on violent and accidental death. The homicide rate "
             "runs 0.25-0.41 per 100,000 from 2021 to 2024 and 2.59 in 2025; "
             "the suicide and road-death panels are pending because neither "
             "has a separate official series; the lens shows 170 murder and "
             "manslaughter cases reported in 2025's fourth quarter against "
             "5, 2 and 12 in the first three, published as recorded."),
    dict(id="11", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — The Fifth Wave and the Years It Took",
         subtitle="Registered deaths by cause from the Department of Health, "
                  "and the life tables published beside the vital events.",
         source="Sources: Department of Health registered deaths "
                "(data.gov.hk) · C&SD 115-01011",
         alt="Four panels on mortality. The crude death rate rose from 5.5 "
             "per 1,000 in 2006 to 8.7 in 2022 and is 7.0; deaths ran 31% "
             "above the 2015-2019 average in 2022; COVID-19 as the "
             "underlying cause killed 126 per 100,000 that year against 10 in "
             "2024; life expectancy is 88.7 years for women and 83.1 for men, "
             "after a 2.5-year dip for men in 2022."),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — A Residual, and the Publisher's Own Split",
         subtitle="No gross flows exist on a residence basis; the net "
                  "movement and the one-way permit share are what is "
                  "published.",
         source="Sources: C&SD 110-01003 (population growth by component)",
         alt="Four panels on migration. Gross immigration and emigration and "
             "the foreign-born share are pending, with the reason stated; net "
             "movement swings from +13.7 per 1,000 in 2022 to -11.5 in 2020; "
             "the lens splits it into one-way permit holders from the "
             "Mainland, who are consistently positive, and everyone else, who "
             "left 96 thousand in 2020."),
)
