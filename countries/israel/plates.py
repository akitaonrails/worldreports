"""The israel plates, on the plate spine.

Every plate declares its topic and claims its panels by slot key, in the
spine's order (PLATE_SPINE.md, core/spine.py). Israel is the atlas's
first right-to-left country: the `he` plates draw with the same geometry
as every other locale — no hand-mirroring, no fake bidi (DATA_NOTES.md
records the font gate).

Where the national statistical office (CBS) remains unreachable, the macro,
trade and demography slots use the named harmonised layer. Newly staged OECD,
Bank of Israel and vital-registration series keep every method break visible:
no incompatible definitions are spliced into a single line.

Notes read their numbers from the CSVs at build time, so a refetch that
moves a figure moves the sentence with it.
"""
from __future__ import annotations

from core.sideload import sibling

events = sibling(__file__, "events")

W0 = 2006

# PIBA residence and work permit classes drawn in the migration lens:
# residence (א/…) plus work (ב/1…) permit families. Everything else the
# file carries is excluded by name and the exclusion is said on the panel
# (visitor/tourist classes dominate the raw totals; the עולה/חוזר classes
# would double-count the olim line; the rest are diplomatic or definitions
# this pass could not verify). ASCII codes are the join keys — the Hebrew
# display strings stay data, never keys (DISCOVERY.md).
RES_CLASSES = {"A2", "A2KLLY", "A3", "A4", "A5", "B1", "B1KLLY", "B1XVCf",
               "B3", "B4"}


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


def _note(p, ax, x, y, text, color=None, ha="left", va="top", size=8.0):
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=size, style="italic", color=color or p.MUTED, zorder=7)


def _foot(p, ax, text):
    ax.text(0.5, -0.07, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.2, color=p.FAINT, style="italic")


def _mark(ig, ax, key, dy=0.97):
    x, label = events.MARKS[key]
    ig.add_event(ax, x, label, dy=dy)


def _pending(ig, ax, why):
    """The reason beside the "data pending" marker: ctx.pending marks the
    slot (so the spine leaves its scale alone); this says why, and where
    the route to the data is recorded (SOURCES.yaml meta.pending)."""
    ax.text(0.5, 0.32, why, transform=ax.transAxes, ha="center", va="top",
            fontsize=8.2, style="italic", color=ig.p.MUTED)


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(a, xticks_years=not getattr(a, "_categorical_x", False))


def _pop(ctx):
    """The WB mid-year population — the denominator for every count→rate
    conversion on these plates (DATA_NOTES.md, spine rule 5)."""
    return dict(zip(*_yr(ctx, "demography/demography.csv",
                         "population", since=2005)))


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p
    G = "macro/gdp_growth.csv"

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, G, "gdp_growth_pct")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax)
    v20 = _at(gy, gv, 2020)
    ax.annotate(f"{v20:.1f}%", (2020, v20), textcoords="offset points",
                xytext=(0, -4), ha="center", va="top", fontsize=8.6,
                fontweight="bold", color=p.ALERT)
    _mark(ig, ax, "oct7", dy=0.80)
    _note(p, ax, 0.02, 0.96, f"the crisis years grew: {_at(gy, gv, 2008):.1f}% "
          f"and {_at(gy, gv, 2009):.1f}% — no band;\nthe war years, too — "
          f"{_at(gy, gv, 2023):.1f}% and {_at(gy, gv, 2024):.1f}%")
    _foot(p, ax, "IMF WEO (the staged annual vintage). The CBS national "
          "accounts line when CBS returns")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "international/world.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    _note(p, ax, 0.02, 0.30, f"US$ at market rates — the {_at(py, pv, 2023):,.0f} "
          f"dip in {2023}\nis the shekel's move, not output falling")
    _foot(p, ax, "World Bank, current US$. The CBS national line when CBS "
          "returns")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year) and the target")
    ax.axhspan(1, 3, color=p.GREEN, alpha=0.07, zorder=0)
    ax.axhline(2, color=p.GREEN, lw=1.0, ls=":", zorder=2)
    iy, iv = _yr(ctx, "macro/cpi_inflation.csv", "cpi_inflation_pct")
    wy, wv = _yr(ctx, "macro/economy.csv", "cpi_inflation_pct")
    ctx.line(ax, iy, iv, p.ALERT, label="IMF WEO")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.6, ms=3.0, label="World Bank "
             "(republication of the CBS CPI)")
    ig.add_recessions(ax, label=False)
    peak = max(zip(iy, iv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(8, 4), ha="left",
                fontsize=8.8, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, "Bank of Israel target: 2%, inside a 1–3% band")
    _foot(p, ax, "Two republications of the CBS index — the CBS line when "
          "CBS returns")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    oy, ov = _yr(ctx, "social/labour.csv", "unemployment_pct")
    wy, wv = _yr(ctx, "macro/economy.csv", "unemployment_pct")
    ctx.line(ax, oy, ov, p.NAVY, label="Israel's LFS, via the OECD")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.6, ms=3.0,
             label="ILO modelled estimate (World Bank)")
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{ov[0]:.1f}% in {oy[0]}", xy=(oy[0], ov[0]),
                xytext=(2007.2, 1.4), textcoords="data",
                fontsize=8.8, fontweight="bold", color=p.NAVY, ha="left",
                va="bottom",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    _note(p, ax, 0.02, 0.96, f"a survey, not the payroll register: {ov[-1]:.1f}% "
          f"in {oy[-1]}\nagainst {ov[0]:.1f}% in {oy[0]} — the CBS LFS line "
          "when CBS returns", size=7.8)
    _finish(ctx, ig)


# ------------------------------------------------------------------ fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p
    GG = "fiscal/general_government.csv"

    ax = ig.slot("fiscal.revenue_expenditure",
                 "Revenue and expenditure (% of GDP)")
    ry, rv = _yr(ctx, GG, "revenue_pct_gdp")
    ey, ev = _yr(ctx, GG, "expenditure_pct_gdp")
    ctx.line(ax, ey, ev, p.ALERT, label="Expenditure")
    ctx.line(ax, ry, rv, p.NAVY, label="Revenue")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    ax.annotate(f"{_at(ry, rv, 2024):.1f}% vs {_at(ey, ev, 2024):.1f}%",
                (2024, _at(ey, ev, 2024)), textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=8.4,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, "general government, IMF WEO; the MoF's own D7 "
          "definition\nlands as a second labelled line, never a splice")
    _foot(p, ax, "IMF WEO (WEO vintage). The CBS national-accounts basis is "
          "parked with CBS")

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    by, bv = _yr(ctx, GG, "balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    py, pv = _yr(ctx, GG, "primary_balance_pct_gdp")
    ctx.line(ax, py, pv, p.NAVY, label="Primary balance")
    ig.add_recessions(ax, label=False)
    lo = min(zip(by, bv), key=lambda t: t[1])
    ax.annotate(f"{lo[1]:.1f}%", lo, textcoords="offset points",
                xytext=(0, -4), ha="center", va="top", fontsize=8.6,
                fontweight="bold", color=p.ALERT)
    ax.annotate(f"{_at(by, bv, 2024):.1f}%", (2024, _at(by, bv, 2024)),
                textcoords="offset points", xytext=(0, -4), ha="center",
                va="top", fontsize=8.6, fontweight="bold", color=p.ALERT)
    _mark(ig, ax, "war_budget", dy=0.86)
    _note(p, ax, 0.02, 0.96, f"the pandemic year ({lo[1]:.1f}% in {lo[0]}) and "
          f"the war year\n({_at(by, bv, 2024):.1f}% in 2024) read as deficits; "
          "GDP never contracted\nin the war years — no band "
          "(see DATA_NOTES.md)", size=7.8)
    ax.legend(loc="lower left", fontsize=7.5, frameon=False)
    _foot(p, ax, "IMF Fiscal Monitor; both balances are from one vintage")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    dy, dv = _yr(ctx, GG, "gross_debt_pct_gdp")
    ctx.line(ax, dy, dv, p.ALERT)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.ALERT, lambda v: f"{v:.1f}%", dy=8)
    _mark(ig, ax, "oct7", dy=0.30)
    low = min(zip(dy, dv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, f"{dv[0]:.1f}% ({dy[0]}) — the long fall to "
          f"{low[1]:.1f}% in {low[0]};\nthe pandemic and the war pushed it back: "
          f"{_at(dy, dv, 2023):.1f}% to {_at(dy, dv, 2024):.1f}% "
          f"to {dv[-1]:.1f}%", size=7.8)
    _foot(p, ax, "IMF WEO general-government debt. MoF's cash-basis D7 debt "
          "is parked — its own column when it lands")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    iy, iv = _yr(ctx, GG, "interest_pct_gdp")
    ctx.line(ax, iy, iv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.GOLD, lambda v: f"{v:.1f}%", dy=8)
    _foot(p, ax, "Derived within one IMF Fiscal Monitor vintage: primary "
          "balance minus overall balance")
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
def plate_spending(ctx, ig) -> None:
    p = ctx.p
    C = "spending/cofog.csv"
    t = ctx.table(C) or {}
    years = [y for y in t.get("year", []) if y >= W0]

    groups = (
        ("Social protection", "social_protection_pct_gdp", p.PURPLE),
        ("Health", "health_pct_gdp", p.GREEN),
        ("Education", "education_pct_gdp", p.GOLD),
        ("General public services", "general_public_services_pct_gdp", p.NAVY),
        ("Economic affairs", "economic_affairs_pct_gdp", p.BLUE),
        ("Defence + public order", "defence_public_order_pct_gdp", p.ALERT),
        ("Other", "other_pct_gdp", p.TEAL),
    )

    def values(column):
        return [float(t[column][t["year"].index(y)]) for y in years]

    ax = ig.slot("spending.by_function", "Government spending by function "
                 "(% of GDP)")
    layers = [(label, values(column), color)
              for label, column, color in groups]
    ax.stackplot(years, *[v for _, v, _ in layers],
                 labels=[label for label, _, _ in layers],
                 colors=[color for _, _, color in layers], alpha=0.9, lw=0)
    ig.add_recessions(ax)
    ax.legend(loc="upper left", fontsize=7.0, ncol=3, frameon=False)
    totals = dict(zip(*_yr(ctx, C, "total_pct_gdp")))
    ax.annotate(f"{totals[2024]:.1f}% in 2024",
                (2024, totals[2024]), textcoords="offset points",
                xytext=(-4, 7), ha="right", fontsize=8.4,
                fontweight="bold", color=p.INK)
    _note(p, ax, 0.02, 0.69, "OECD COFOG, general government; the seven "
          "colours sum to the published total", size=7.5)

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    sy, sv = _yr(ctx, C, "social_protection_pct_gdp")
    rest = [totals[y] - v for y, v in zip(sy, sv)]
    ctx.line(ax, sy, rest, p.NAVY, label="Everything else")
    ctx.line(ax, sy, sv, p.PURPLE, label="Social protection")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    ax.annotate(f"{_at(sy, sv, 2020):.1f}% in 2020",
                (2020, _at(sy, sv, 2020)), textcoords="offset points",
                xytext=(0, 7), ha="center", fontsize=8.4,
                fontweight="bold", color=p.PURPLE)
    _foot(p, ax, "Exact partition of the same OECD COFOG total; no residual "
          "or second perimeter")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(GFCF, % of GDP)")
    iy, iv = _yr(ctx, "spending/whole_economy_investment.csv", "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.BLUE, label="Whole-economy GFCF")
    ig.add_recessions(ax, label=False)
    peak = max(zip(iy, iv), key=lambda point: point[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(0, 8), ha="center",
                fontsize=8.4, fontweight="bold", color=p.BLUE)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    _foot(p, ax, "World Bank national accounts; whole-economy GFCF, not "
          "government investment")

    ax = ig.slot("spending.public_investment", "Public investment "
                 "(government GFCF, % of GDP)")
    gy, gv = _yr(ctx, "spending/public_investment.csv", "gov_gfcf_pct_gdp")
    ctx.line(ax, gy, gv, p.TEAL, label="General government GFCF")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.TEAL, lambda v: f"{v:.1f}%", dy=8)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    _note(p, ax, 0.98, 0.12, "general-government investment only; kept "
          "separate from the whole-economy rate", ha="right", va="bottom")
    _foot(p, ax, "OECD National Accounts at a Glance, general government")
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
def plate_trade(ctx, ig) -> None:
    p = ctx.p
    T = "trade/trade.csv"

    ax = ig.slot("trade.exports_imports", "Exports and imports of goods "
                 "and services (% of GDP)")
    xy, xv = _yr(ctx, T, "exports_pct_gdp")
    my, mv = _yr(ctx, T, "imports_pct_gdp")
    ctx.line(ax, xy, xv, p.GREEN, label="Exports")
    ctx.line(ax, my, mv, p.ALERT, label="Imports")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower right", fontsize=8.0, frameon=False)
    _note(p, ax, 0.02, 0.96, f"{xv[-1] + mv[-1]:.0f}% of GDP crosses the "
          f"border each way combined ({xy[-1]});\nthe 2020 dent is services — "
          "tourism and Tech exports held")
    _foot(p, ax, "World Bank, national-accounts basis. The CBS "
          "national-accounts line when CBS returns")

    ax = ig.slot("trade.balance", "Trade balance, goods and services "
                 "(% of GDP)")
    bal = [x - m for x, m in zip(xv, mv)]
    ctx.bars(ax, xy, bal, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    deficits = [y for y, b in zip(xy, bal) if b < 0]
    _note(p, ax, 0.02, 0.34, f"in balance {len(bal) - len(deficits)} of the "
          f"{len(bal)} years — high-tech services\ncarry a goods deficit")
    _foot(p, ax, "Computed from slot 1. The CBS line when CBS returns")

    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    ctx.pending(ax)
    _foot(p, ax, "a comparable annual partner series is not staged; the "
          "reviewed 2023 customs snapshot is retained in the lens")

    ax = ig.slot("trade.lens", "Top export destinations, 2023 "
                 "(% of goods exports)", unit=False)
    destinations_ax = ax
    t = ctx.table("trade/trade_partners_comtrade.csv") or {}
    short = {"United States": "US", "United Kingdom": "UK",
             "Hong Kong SAR, China": "Hong Kong"}
    names = [short.get(name, name) for name in t.get("partner", [])][::-1]
    shares = [float(v) for v in t.get("share_of_exports_pct", [])][::-1]
    positions = list(range(len(names)))
    ax.bar(positions, shares, color=p.BLUE, alpha=0.88)
    _foot(p, ax, "UN Comtrade 2023; customs goods, not the services-inclusive "
          "national-accounts line above")

    _finish(ctx, ig)
    destinations_ax.set_xlim(-0.6, len(names) - 0.4)
    destinations_ax.set_xticks(positions, names, fontsize=6.8)


# ----------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ry, rv = _yr(ctx, "markets/policy_rate.csv", "policy_rate_pct")
    old = [(y, v) for y, v in zip(ry, rv) if y <= 2016]
    new = [(y, v) for y, v in zip(ry, rv) if y >= 2017]
    ctx.line(ax, [y for y, _ in old], [v for _, v in old], p.NAVY,
             label="Policy rate: mean of monthly liquidity-period averages")
    ctx.line(ax, [y for y, _ in new], [v for _, v in new], p.BLUE,
             label="Policy rate: day-weighted declared rate")
    iy, iv = _yr(ctx, "macro/cpi_inflation.csv", "cpi_inflation_pct")
    ctx.line(ax, iy, iv, p.ALERT, lw=1.8, ms=3.0, label="Consumer inflation")
    ig.add_recessions(ax)
    ax.axvline(2016.5, color=p.FAINT, lw=0.9, ls=":")
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    _foot(p, ax, "Bank of Israel: 2006–16 liquidity-period monthly means; "
          "2017–25 day-weighted declared rates; IMF WEO inflation")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    by, bv = _yr(ctx, "markets/government_bond_10y.csv",
                 "government_bond_10y_yield_pct")
    ctx.line(ax, by, bv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, by, bv, p.GOLD, lambda v: f"{v:.2f}%", dy=18)
    _foot(p, ax, "Bank of Israel; annual mean of monthly observations for "
          "the longest government bond with 8–11 years remaining")

    ax = ig.slot("markets.currency", "The shekel against the US$ "
                 "(index 2006 = 100, up = stronger)")
    fy, fv = _yr(ctx, "markets/usdils.csv", "ils_per_usd")
    ix_y, ix_v = ctx.fx_index(dict(zip(fy, fv)))
    ctx.line(ax, ix_y, ix_v, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ix_y, ix_v, p.BLUE, lambda v: f"{v:.0f}", dy=8)
    pk = max(zip(ix_y, ix_v), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.0f} in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=8.4, fontweight="bold",
                color=p.BLUE)
    t = ctx.table("markets/usdils_boi.csv") or {}
    usd = [i for i, c in enumerate(t.get("currency", [])) if c == "USD"]
    if usd:
        i = usd[0]
        snap = float(t["ils_per_unit"][i])
        stamp = str(t["last_update_utc"][i])[:10]
        _note(p, ax, 0.02, 0.34, f"BoI representative rate — a snapshot of "
              f"{stamp}, not history:\nILS {snap:.3f} per US$; the BoI daily "
              "file is dead (404)", size=7.6)
    _foot(p, ax, "World Bank official annual averages (PA.NUS.FCRF) until the "
          "BoI FX history lands")

    ax = ig.slot("markets.equities", "TA-125 in US$ vs the S&P 500 "
                 "(index 2006 = 100)")
    ty, tv = _yr(ctx, "markets/ta125.csv", "close")
    sy, sv = _yr(ctx, "markets/sp500.csv", "close")
    fx = dict(zip(fy, fv))
    tu = {y: v / fx[y] for y, v in zip(ty, tv) if y in fx}
    tiy, tiv = ctx.index_2006(tu)
    siy, siv = ctx.index_2006(dict(zip(sy, sv)))
    keep = [i for i, y in enumerate(siy) if y in fx]
    siy = [siy[i] for i in keep]
    siv = [siv[i] for i in keep]
    ctx.line(ax, siy, siv, p.FAINT, lw=1.8, ms=3.0, ls="--",
             dashed_partial=False, label="S&P 500 (US$)")
    ctx.line(ax, tiy, tiv, p.BLUE, label="TA-125, converted to US$")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, tiy, tiv, p.BLUE, lambda v: f"{v:.0f}", dy=10)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.30, "Yahoo year-end closes (not official): levels run a "
          "few percent\noff TASE's own closes; 2026 is not converted — no "
          "staged 2026 FX", size=7.6)
    _foot(p, ax, "Yahoo Finance redistributed index, official: false; US$ "
          "conversion at the staged World Bank FX")
    _finish(ctx, ig)


# ------------------------------------------------------------------ credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP, "
                 "year-end)")
    hy, hv = _yr(ctx, "credit/household_debt.csv", "household_debt_pct_gdp")
    ctx.line(ax, hy, hv, p.ALERT)
    ig.add_recessions(ax)
    ctx.endlabel(ax, hy, hv, p.ALERT, lambda v: f"{v:.1f}%", dy=8)
    peak = max(zip(hy, hv), key=lambda point: point[1])
    _note(p, ax, 0.02, 0.96, f"Bank of Israel household debt at Q4 over "
          f"nominal GDP; peak {peak[1]:.1f}% in {peak[0]}")
    _foot(p, ax, "Bank of Israel debt stock divided by World Bank nominal "
          "GDP in NIS")

    ax = ig.slot("credit.lending_rate", "New mortgage rate vs the policy "
                 "rate (%)")
    my, mv = _yr(ctx, "credit/mortgage_rate.csv",
                 "new_unindexed_mortgage_rate_pct")
    py, pv = _yr(ctx, "markets/policy_rate.csv", "policy_rate_pct", since=2014)
    ctx.line(ax, my, mv, p.ALERT,
             label="New unindexed-shekel housing loans")
    ctx.line(ax, py, pv, p.NAVY, lw=1.8, ms=3.2,
             label="Policy rate, annual average")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    _foot(p, ax, "Bank of Israel; fixed and variable new-loan rates, monthly "
          "weighted-average effective rates; series begins in 2014")

    ax = ig.slot("credit.npl", "Non-performing loans (% of gross loans)")
    ny, nv = _yr(ctx, "credit/npl_ratio.csv",
                 "npl_to_total_gross_loans_pct")
    old = [(y, v) for y, v in zip(ny, nv) if y <= 2021]
    new = [(y, v) for y, v in zip(ny, nv) if y >= 2022]
    ctx.line(ax, [y for y, _ in old], [v for _, v in old], p.PURPLE,
             label="IMF FSI 2006 Guide")
    ctx.line(ax, [y for y, _ in new], [v for _, v in new], p.GOLD,
             label="IMF FSI 2019 Guide transition")
    ig.add_recessions(ax, label=False)
    ax.axvline(2021.5, color=p.FAINT, lw=0.9, ls=":")
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _foot(p, ax, "Banking-system ratio reported to IMF FSI; November 2022 "
          "guide transition; Q4 segments are not joined")

    # No credit.lens claim: BIS does not publish an Israeli household DSR,
    # and a locally defined substitute would not be the same indicator.
    _finish(ctx, ig)


# ------------------------------------------------------------------ people
def plate_people(ctx, ig) -> None:
    p = ctx.p
    I = "social/income_distribution.csv"

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100, higher "
                 "= more unequal)")
    g1y, g1v = _yr(ctx, I, "gini_meth2011_current")
    g2y, g2v = _yr(ctx, I, "gini_meth2012_previous")
    g3y, g3v = _yr(ctx, I, "gini_meth2012_current")
    g1v = [v * 100 for v in g1v]
    g2v = [v * 100 for v in g2v]
    g3v = [v * 100 for v in g3v]
    ctx.line(ax, g1y, g1v, p.FAINT, lw=1.8, ms=3.0,
             label="2011 method, current definition")
    ctx.line(ax, g2y, g2v, p.NAVY,
             label="2012 method, previous definition")
    ax.scatter(g3y, g3v, s=34, color=p.GOLD, zorder=5,
               label="2012 method, current definition (2023 only)")
    ig.add_recessions(ax, inside=True)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    _note(p, ax, 0.02, 0.16, "three OECD IDD definitions, three separate "
          "segments; the 2023 current-definition value stands alone",
          va="bottom", size=7.4)

    ax = ig.slot("people.poverty", "Poverty rate (% below half the median "
                 "disposable income)")
    p1y, p1v = _yr(ctx, I, "poverty50_pct_meth2011_current")
    p2y, p2v = _yr(ctx, I, "poverty50_pct_meth2012_previous")
    p3y, p3v = _yr(ctx, I, "poverty50_pct_meth2012_current")
    ctx.line(ax, p1y, p1v, p.FAINT, lw=1.8, ms=3.0,
             label="2011 method, current definition")
    ctx.line(ax, p2y, p2v, p.ALERT,
             label="2012 method, previous definition")
    ax.scatter(p3y, p3v, s=34, color=p.GOLD, zorder=5,
               label="2012 method, current definition (2023 only)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    _foot(p, ax, "OECD Income Distribution Database; household disposable "
          "income, 50% relative threshold; definitions never spliced")

    ax = ig.slot("people.minimum_wage", "Statutory minimum wage "
                 "(US$ per month)")
    wy, wv = _yr(ctx, "social/minimum_wage.csv", "monthly_usd_avg")
    ctx.line(ax, wy, wv, p.GREEN, label="Statutory monthly minimum (US$)")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, wy, wv, p.GREEN, lambda v: f"US${v:,.0f}", dy=8)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    _note(p, ax, 0.98, 0.12, "adult monthly minimum, weighted by months at "
          "each statutory level and converted at annual-average FX",
          ha="right", va="bottom", size=7.5)
    _foot(p, ax, "National Insurance Institute; committed annual-average "
          "ILS/US$ conversion")

    ax = ig.slot("people.lens", "Lens — child and old-age poverty "
                 "(% below half the median income)")
    cy, cv = _yr(ctx, I, "child_poverty50_pct_meth2012_previous")
    oy, ov = _yr(ctx, I, "old_age_poverty50_pct_meth2012_previous")
    ccy, ccv = _yr(ctx, I, "child_poverty50_pct_meth2012_current")
    coy, cov = _yr(ctx, I, "old_age_poverty50_pct_meth2012_current")
    ctx.line(ax, cy, cv, p.GOLD, label="Children, previous definition")
    ctx.line(ax, oy, ov, p.PURPLE, label="Age 65+, previous definition")
    ax.scatter(ccy, ccv, s=34, color=p.GOLD, marker="s", zorder=5,
               label="Children, current definition (2023)")
    ax.scatter(coy, cov, s=34, color=p.PURPLE, marker="s", zorder=5,
               label="Age 65+, current definition (2023)")
    ig.add_recessions(ax, label=False)
    ax.set_ylim(0, max(cv + ov + ccv + cov) * 1.55)
    ax.legend(loc="upper left", fontsize=7.0, frameon=False)
    _note(p, ax, 0.98, 0.12, "the lone 2023 current-definition points remain "
          "separate from the previous-definition lines", ha="right",
          va="bottom", size=7.3)
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "international/world.csv", "gdp_usd")
    gv = [v / 1e9 for v in gv]
    ctx.line(ax, gy, gv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.BLUE, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.30, "in US dollars at market rates: the 2025 jump is "
          "partly the\nstronger shekel, and the 2023 dip partly its fall")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "international/hdi.csv", "hdi")
    ctx.line(ax, hy, hv, p.GREEN, split_year=max(hy))
    ax.axhline(0.8, color=p.FAINT, lw=0.9, ls=":")
    ctx.endlabel(ax, hy, hv, p.GREEN, lambda v: f"{v:.3f}", dy=8)
    rank = ctx.rows("international/hdi.csv") or {}
    last = max(rank)
    _note(p, ax, 0.98, 0.50, f"0.800 and above = very high development; "
          f"rank {int(float(rank[last]['hdi_rank_2023']))} in the 2023 table",
          ha="right", va="top", size=7.8)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "one vintage (HDR 2025) throughout — the HDR recomputes the "
          "whole back-series")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (0–100)")
    cy, cv = _yr(ctx, "international/cpi_ti.csv", "cpi_score")
    ctx.line(ax, cy, cv, p.PURPLE)
    ctx.endlabel(ax, cy, cv, p.PURPLE, lambda v: f"{v:.0f}", dy=8)
    _foot(p, ax, "Transparency International; comparable 2012 method only")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn, year-end)")
    ry, rv = _yr(ctx, "international/world.csv", "reserves_usd")
    rv = [v / 1e9 for v in rv]
    ctx.line(ax, ry, rv, p.GREEN)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.GREEN, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, "one of the largest reserve build-ups per person "
          "among\nopen economies; WB adds IMF-related items — 1.2% above\n"
          "the BoI's own end-2024 release", size=7.8)
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p
    D = "demography/demography.csv"
    pop = _pop(ctx)

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    iy, iv = ctx.index_2006(pop)
    iy, iv = zip(*[(y, v) for y, v in zip(iy, iv) if y >= W0])
    ctx.line(ax, iy, iv, p.BLUE)
    ig.add_recessions(ax, label=False)
    last = max(pop)
    ax.text(0.98, 0.10, f"{pop[last] / 1e6:.1f}M",
            transform=ax.transAxes, fontsize=9.5, fontweight="bold",
            color=p.BLUE, ha="right", va="bottom", zorder=6)
    crossed = [y for y in sorted(pop) if pop[y] >= 10_000_000]
    _note(p, ax, 0.02, 0.96, f"the ten-millionth resident registered in "
          f"{crossed[0]};\nthe axis grew past the shared range — the marker "
          "says so", size=7.8)
    _foot(p, ax, "World Bank mid-year, the stand-in for the CBS register — "
          "published each Rosh Hashanah when CBS returns")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    ty, tv = _yr(ctx, D, "fertility")
    ax.axhline(2.1, color=p.FAINT, lw=1.0, ls=":")
    ctx.line(ax, ty, tv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ty, tv, p.PURPLE, lambda v: f"{v:.2f}", dy=-14)
    _note(p, ax, 0.98, 0.72, "2.1 = replacement", ha="right", size=7.8)
    _note(p, ax, 0.02, 0.18, f"never below {min(tv):.2f} across the window — "
          f"{tv[-1]:.2f} in {ty[-1]}", va="bottom", size=7.8)
    _foot(p, ax, "World Bank. The CBS vital-statistics line when CBS returns")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    by, bv = _yr(ctx, D, "birth_rate_per_1000")
    dy, dv = _yr(ctx, D, "death_rate_per_1000")
    ctx.line(ax, by, bv, p.GREEN, label="Births")
    ctx.line(ax, dy, dv, p.ALERT, label="Deaths")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=8.0, frameon=False)
    _note(p, ax, 0.98, 0.13, f"natural increase: {bv[0] - dv[0]:.1f} per 1,000 "
          f"in {by[0]}, {bv[-1] - dv[-1]:.1f} in {by[-1]} —\nthe births line "
          f"keeps falling and the deaths line keeps rising",
          ha="right", va="top", size=7.8)
    _foot(p, ax, "World Bank. The CBS vital-statistics line when CBS returns")

    ax = ig.slot("demography.natural_migration", "Natural increase and net "
                 "migration (per 1,000 people)")
    nmap = dict(zip(dy, dv))
    ni_y = [y for y in by if y in nmap]
    ni_v = [_at(by, bv, y) - nmap[y] for y in ni_y]
    ctx.bars(ax, ni_y, ni_v, lambda v: p.GREEN)
    ax.plot([], [], color=p.GREEN, lw=6, label="Natural increase")
    my, mv = _yr(ctx, D, "net_migration")
    ry, rv = ctx.per_1000(dict(zip(my, mv)), pop)
    ctx.line(ax, ry, rv, p.BLUE, label="Net migration (UN estimate)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    pk = max(zip(ry, rv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f} in {pk[0]}: the wave the UN's\nestimate misses "
                "entirely", pk, xytext=(2015.5, 19),
                textcoords="data", fontsize=8.0, fontweight="bold",
                color=p.BLUE, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    _foot(p, ax, "World Bank (UN WPP) ÷ the mid-year population; the UN net "
          "figure is not the olim flow — see migration")
    _finish(ctx, ig)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    S = "security/security.csv"
    pop = _pop(ctx)

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000, log "
                 "scale) — two records, never one line")
    hy, hv = _yr(ctx, S, "homicide_per_100k")
    ctx.line(ax, hy, hv, p.NAVY, label="UNODC count as a published rate, via "
             "the World Bank (to 2022)")
    py_, pv_ = _yr(ctx, "security/homicide_police.csv",
                   "murder_301")
    pry, prv = ctx.per_100k(dict(zip(py_, pv_)), pop)
    ctx.line(ax, pry, prv, p.ALERT, marker="s", ms=5,
             label="Israel Police type-301 files ÷ the WB mid-year population "
                   "(2021 only and later)")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "oct7", dy=0.30)
    spike = max(zip(pry, prv), key=lambda t: t[1])
    ax.annotate(f"{spike[1]:.1f} in {spike[0]}", spike,
                textcoords="offset points", xytext=(0, 8), ha="center",
                fontsize=8.4, fontweight="bold", color=p.ALERT)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    _note(p, ax, 0.98, 0.12, "two publishers, two definitions (occurrence vs "
          "residence),\ntwo colour-coded series — the police window opens in "
          "2021;\nnothing is spliced and nothing is extrapolated",
          ha="right", va="bottom", size=7.4)

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    wy, wv = _yr(ctx, S, "suicide_per_100k")
    ctx.line(ax, wy, wv, p.PURPLE, split_year=max(wy))
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, wy, wv, p.PURPLE, lambda v: f"{v:.1f}", dy=8)
    lo = min(zip(wy, wv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, f"one of the low-suicide-rate club among OECD "
          f"countries:\na low of {lo[1]:.1f} in {lo[0]}; the WHO series stops "
          f"in {max(wy)} —\nthe hole stays a hole (CBS causes of death: parked)",
          size=7.8)

    ax = ig.slot("security.road_deaths", "Road traffic deaths (per 100,000)")
    ry, rv = _yr(ctx, S, "road_deaths_per_100k")
    ctx.line(ax, ry, rv, p.NAVY, split_year=max(ry))
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.NAVY, lambda v: f"{v:.1f}", dy=8)
    pk = max(zip(ry, rv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, f"{pk[1]:.1f} per 100,000 in {pk[0]}, falling to "
          f"{rv[-1]:.1f} in {ry[-1]};\nWHO's series stops there — the CBS road "
          "safety file is parked", size=7.8)

    ax = ig.slot("security.lens", "Lens — homicide cases recorded by police")
    ctx.bars(ax, py_, pv_, lambda v: p.ALERT)
    ax.set_ylabel("recorded files", fontsize=8.6, color=p.MUTED)
    ig.add_recessions(ax, label=False)
    for y, v in zip(py_, pv_):
        ax.annotate(f"{v:,.0f}", (y, v), textcoords="offset points",
                    xytext=(0, 3), ha="center", fontsize=8.0,
                    fontweight="bold", color=p.ALERT)
    _mark(ig, ax, "oct7", dy=0.55)
    n302 = dict(zip(*_yr(ctx, "security/homicide_police.csv",
                         "hostile_activity_302")))
    _note(p, ax, 0.02, 0.96, "recorded cases, not people: the 2023 column "
          "includes 7 October\ncases under police type 301; hostile-action "
          f"cases (type 302, {n302[2023]:.0f} in {2023}) are a separate "
          "column\nand are never added to the bars — the series starts in "
          "2021", size=7.4)
    _foot(p, ax, "Israel Police open data, place-of-occurrence; CBS "
          "death-certificate homicide is the second count — parked")
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    M = "mortality/mortality.csv"

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000 people)")
    dy, dv = _yr(ctx, M, "death_rate_per_1000")
    ctx.line(ax, dy, dv, p.ALERT, split_year=max(dy))
    ig.add_recessions(ax)
    peak = max(zip(dy, dv), key=lambda point: point[1])
    ax.annotate(f"{peak[1]:.2f} in {peak[0]}", peak,
                textcoords="offset points", xytext=(0, 8), ha="center",
                fontsize=8.4, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.17, "crude registered-death rate: population ageing "
          "remains in the measure", va="bottom", size=7.7)
    _foot(p, ax, "OECD vital-registration series; crude, not age-standardised")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above the 2015–2019 average)")
    ey, ev = _yr(ctx, M, "excess_pct")
    ctx.bars(ax, ey, ev, lambda value: p.ALERT if value > 0 else p.GREEN)
    ig.add_recessions(ax, label=False)
    peak = max(zip(ey, ev), key=lambda point: point[1])
    ax.annotate(f"+{peak[1]:.1f}%", peak, textcoords="offset points",
                xytext=(0, 7), ha="center", fontsize=8.6,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, "annual registered deaths against the fixed "
          "2015–2019 mean; not adjusted for population growth or ageing",
          size=7.6)

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    cy, cv = _yr(ctx, M, "covid_per_100k")
    ctx.bars(ax, cy, cv, lambda value: p.PURPLE)
    ax.plot([], [], color=p.PURPLE, lw=6, label="Underlying cause")
    ig.add_recessions(ax, label=False)
    peak = max(zip(cy, cv), key=lambda point: point[1])
    ax.annotate(f"{peak[1]:.1f} in {peak[0]}", peak,
                textcoords="offset points", xytext=(0, 7), ha="center",
                fontsize=8.6, fontweight="bold", color=p.PURPLE)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.96, "underlying cause in the death registration, "
          "not every death involving a positive test", size=7.6)
    _foot(p, ax, "WHO Mortality Database; 4,800 underlying-cause deaths in "
          "2021")

    ax = ig.slot("mortality.lens", "Lens — malignant neoplasms and "
                 "circulatory diseases (crude rate per 100,000)")
    ny, nv = _yr(ctx, M, "malignant_neoplasms_per_100k")
    vy, vv = _yr(ctx, M, "circulatory_per_100k")
    ctx.line(ax, ny, nv, p.NAVY, split_year=max(ny),
             label="Malignant neoplasms")
    ctx.line(ax, vy, vv, p.ALERT, split_year=max(vy),
             label="Circulatory diseases")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.7, frameon=False)
    _foot(p, ax, "WHO Mortality Database, national vital registration; "
          "underlying-cause crude rates retain the population age structure")
    _finish(ctx, ig)


# --------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    pop = _pop(ctx)

    oy, ov = _yr(ctx, "migration/olim_flow.csv", "olim")
    ry, rv = ctx.per_1000(dict(zip(oy, ov)), pop)
    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    ctx.pending(ax)
    _foot(p, ax, "no verified comparable immigration/emigration pair is "
          "staged; the Law of Return subset is retained in the lens")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    D = "demography/demography.csv"
    my, mv = _yr(ctx, D, "net_migration")
    ny, nv = ctx.per_1000(dict(zip(my, mv)), pop)
    ctx.bars(ax, ny, nv, lambda v: p.TEAL)
    ig.add_recessions(ax, label=False)
    pk = max(zip(ny, nv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}", pk, textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=8.6, fontweight="bold",
                color=p.TEAL)
    _note(p, ax, 0.02, 0.96, "the UN's net estimate is not the Law of Return "
          "subset retained in the lens;\nthe two objects are never added",
          size=7.8)
    _foot(p, ax, "World Bank (UN WPP) ÷ the mid-year population. The CBS "
          "register line when CBS returns")

    ax = ig.slot("migration.foreign_born", "Foreign-born share of the "
                 "population (%)")
    sy, sv = _yr(ctx, "migration/migrant_stock_wb.csv", "migrant_stock_pct")
    ctx.line(ax, sy, sv, p.TEAL)
    _foot(p, ax, "World Bank / UN DESA snapshot years; no interpolation and "
          "not the CBS register")

    ax = ig.slot("migration.lens", "Lens — new residence and work permits: a "
                 "flow (per 1,000 people)")
    t = ctx.table("migration/permits.csv") or {}
    new_by_year: dict[int, float] = {}
    ext_by_year: dict[int, float] = {}
    for y, cls, n_, e_ in zip(t.get("year", []), t.get("visa_class", []),
                              t.get("new_permits", []),
                              t.get("extensions", [])):
        if cls not in RES_CLASSES or y > ctx.LAST_FULL_YEAR:
            continue
        new_by_year[y] = new_by_year.get(y, 0) + float(n_)
        ext_by_year[y] = ext_by_year.get(y, 0) + float(e_)
    nyrs = sorted(new_by_year)
    nfy, nfv = ctx.per_1000(new_by_year, pop)
    efy, efv = ctx.per_1000(ext_by_year, pop)
    ctx.bars(ax, nfy, nfv, lambda v: p.GOLD)
    ctx.line(ax, ry, rv, p.BLUE, lw=1.8, ms=3.2,
             label="new olim under the Law of Return")
    ctx.line(ax, efy, efv, p.NAVY, lw=1.8, ms=3.2, label="extensions of "
             "permits already issued")
    ig.add_recessions(ax, label=False)
    ax.set_ylabel("per 1,000 people", fontsize=8.6, color=p.MUTED)
    ax.set_ylim(0, max(nfv + efv) * 1.35)
    pk = max(zip(nfy, nfv), key=lambda t: t[1])
    permit_label = ax.annotate(
        f"{int(new_by_year[pk[0]]):,}", (pk[0], pk[1]),
        textcoords="offset points", xytext=(12, 18), ha="left",
        fontsize=8.4, fontweight="bold", color=p.GOLD)
    ax.legend(loc="upper left", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.24, "new permits only — extensions are the second "
          "flow and amendments\nare in the file but off this panel; visitor "
          "classes, diplomatic\nclasses and the aliyah-named classes are "
          "excluded by name;\nrecords, not people, and never added to the "
          "olim line", size=7.4)
    _foot(p, ax, "PIBA stats_rish ÷ the WB mid-year population; permit stocks "
          "and asylum figures are parked (four numbers, never one line)")
    _finish(ctx, ig)


# The plates, in canonical spine order; ids and chapter stems match.
_PENDING_SRC = "CBS Israel unreachable (SOURCES.yaml meta.pending)"
PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Israeli Economy — Growth, Income, Prices and Jobs",
         subtitle="Built from the IMF WEO and World Bank vintages while the "
                  "CBS portal stays unreachable; the annual vintage shows "
                  "one contraction year, 2020.",
         source="Sources: IMF WEO · World Bank WDI · OECD LFS (Israel) · "
                + _PENDING_SRC,
         alt="Four panels on the Israeli economy, 2006–2025. Real GDP growth "
             "is positive every year except 2020 (-1.9%), and the world crisis "
             "years of 2008 and 2009 grew +3.2 and +1.2; GDP per person in US "
             "dollars rises from about 22,500 to 60,300, the mid-2020s wiggle "
             "the shekel's; consumer price inflation touched deflation in the "
             "mid-2010s, peaked at 4.4% in 2022 against the Bank of Israel's "
             "1–3% target band, and unemployment falls from 8.4% to about "
             "3%. All from the international vintages while CBS is down."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — the Long Fall in Debt, and the War Years",
         subtitle="General government on the IMF's basis. The war of 2023- "
                  "shows in the balance and the debt, not in a growth band.",
         source="Sources: IMF Fiscal Monitor and WEO (general government) · "
                + _PENDING_SRC,
         alt="Four panels on Israeli public finances. Revenue runs 35-40% of "
             "GDP and expenditure 37-45%; the overall balance reaches -10.7% "
             "of GDP in 2020 and -8.1% in 2024, the war year; gross debt falls "
             "from 85.7% of GDP in 2005 to 59.5% in 2019, jumps to 71.4% in "
             "2020 and sits near 68% in 2025; primary balance and derived "
             "interest use the same IMF Fiscal Monitor vintage."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Government Spending — Functions and Investment",
         subtitle="OECD general-government COFOG and public investment, "
                  "beside whole-economy investment from the national accounts.",
         source="Sources: OECD National Accounts at a Glance · World Bank WDI",
         alt="Four panels on spending and investment in Israel. Seven COFOG "
             "groups sum to general-government spending, which rises from "
             "42.7% of GDP in 2006 to 44.3% in 2024 and peaks at 45.7% in "
             "2020; social protection is separated from all other functions; "
             "whole-economy fixed investment and general-government fixed "
             "investment remain separate series and separate panels."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — A Services Surplus Carrying a Goods Deficit",
         subtitle="Exports and imports on the World Bank's national-accounts "
                  "basis; the CBS national-accounts line returns with CBS.",
         source="Sources: World Bank WDI · UN Comtrade · " + _PENDING_SRC,
         alt="Four panels drawn. Exports and imports each "
             "run a third of GDP or more and the balance swings between about "
             "-3% and +5% of GDP; the comparable annual destination slot is "
             "pending, while the lens retains a 2023 UN Comtrade customs-"
             "goods snapshot excluding special category 837."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Markets — Rates, the Shekel and the Tel Aviv Exchange",
         subtitle="Bank of Israel rates and yields, with the policy-rate "
                  "aggregation seam shown rather than joined.",
         source="Sources: Bank of Israel · World Bank WDI (PA.NUS.FCRF) · "
                "Yahoo Finance (index, not official)",
         alt="Four panels on Israeli markets. The policy rate is split into "
             "2006–2016 monthly-liquidity-period averages and 2017–2025 "
             "day-weighted declared rates, beside inflation; the annual "
             "average yield on the longest government bond with 8–11 years "
             "remaining falls below 1% in 2020 and reaches 4.2% in 2025; the "
             "shekel, indexed to "
             "2006, strengthens to about 129 by 2025 on the World Bank's "
             "official annual averages, with the Bank of Israel's intraday "
             "representative rate quoted as a labelled snapshot; in US dollars "
             "the TA-125 index reaches about 510 while the S&P 500 reaches "
             "about 483, both indexed 2006 = 100."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Household Credit — Debt, Mortgage Rates and Loan Quality",
         subtitle="Household debt and new-mortgage rates from the Bank of "
                  "Israel; the banking-system NPL guide change stays visible.",
         source="Sources: Bank of Israel · World Bank WDI (nominal GDP)",
         alt="Three canonical panels on Israeli credit. Household debt rises "
             "from 34.8% of GDP in 2006 to 42.9% in 2025; annual rates on new "
             "unindexed-shekel mortgages begin in 2014 and are shown beside "
             "the policy rate; banking-system non-performing loans fall from "
             "3.45% in 2012 to 0.64% in 2025, with the transition from the IMF "
             "FSI 2006 Guide to the 2019 Guide split at 2022. The optional DSR "
             "lens is omitted because no comparable Israeli series is published."),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="People — Inequality, Relative Poverty and the Minimum Wage",
         subtitle="OECD income definitions remain separate; the statutory "
                  "minimum is converted at the committed annual-average FX.",
         source="Sources: OECD Income Distribution Database · National "
                "Insurance Institute · World Bank WDI",
         alt="Four panels on living standards in Israel. Gini and relative-"
             "poverty series are split by the OECD's METH2011 and METH2012 "
             "definitions, with the lone 2023 current-definition observation "
             "shown as a separate point; the adult statutory minimum wage "
             "rises from about US$786 a month in 2006 to US$1,783 in 2025; "
             "child and old-age poverty use the same separated definitions."),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="Israel in the World — Size, Development and Reserves",
         subtitle="GDP and reserves in US dollars, UNDP development and "
                  "Transparency International's comparable CPI.",
         source="Sources: World Bank WDI · UNDP HDR 2025 · Transparency "
                "International CPI 2025",
         alt="Four panels drawn. GDP in US dollars rises from "
             "about 159bn to 611bn; the Human Development Index climbs from "
             "0.867 to 0.919 (2023, rank 27); official reserves climb from "
             "about 29bn to 229bn dollars; the Corruption Perceptions Index "
             "runs from 60 in 2012 to 62 in 2025."),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — Ten Million, and the Highest Fertility in the "
                "OECD Club",
         subtitle="World Bank (UN WPP) while the CBS register, published each "
                  "Rosh Hashanah, is unreachable.",
         source="Sources: World Bank WDI (UN WPP) · " + _PENDING_SRC,
         alt="Four panels on Israel's population. The index 2006 = 100 runs "
             "to about 144 by 2025 — the ten-millionth resident registered in "
             "2024, and the panel carries the scale-extended marker; fertility "
             "stays between 2.84 and 3.11 children per woman; crude births "
             "fall from 21.0 to 18.6 while deaths rise toward 5.3 per 1,000; "
             "natural increase bars sit near 13 per 1,000 with the UN's net-"
             "migration line well below them."),
    dict(id="10", slug="security", topic="security", builder=plate_security,
         title="Security — Two Homicide Records and the 7 October Cases",
         subtitle="UNODC rates fill 2006-2020; the Israel Police open-data "
                  "window opens in 2021. Two series, never one spliced line.",
         source="Sources: UNODC and WHO via the World Bank · Israel Police "
                "open data · " + _PENDING_SRC,
         alt="Four panels on violent and accidental death in Israel. On the "
             "log homicide panel the UNODC rate runs near 1.3 to 2.2 per "
             "100,000 while police type-301 cases converted per 100,000 "
             "start only in 2021 (1.6) and spike to about 12.3 in 2023, the "
             "October-7 year; suicide stays near 5 per 100,000 to 2021; road "
             "deaths fall from 6.4 to 3.4 before WHO's series stops; the lens "
             "panel counts homicide cases recorded by Israel Police — 156 (2021), "
             "112 (2022), 1,209 (2023), 458 (2024), 345 (2025) — stating that "
             "the 2023 column includes 7 October cases under type 301."),
    dict(id="11", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — Registered Deaths and Underlying Causes",
         subtitle="Crude vital-registration rates, a fixed 2015–2019 excess-"
                  "death baseline and underlying-cause mortality.",
         source="Sources: OECD vital statistics · WHO Mortality Database",
         alt="Four panels on mortality in Israel. The crude death rate remains "
             "near 5–5.6 per 1,000 through 2023; registered deaths reach 15.9% "
             "above the fixed 2015–2019 mean in 2022; COVID-19 as the underlying "
             "cause peaks at 51.2 deaths per 100,000 in 2021, or 4,800 deaths; "
             "crude underlying-cause rates for malignant neoplasms and "
             "circulatory diseases are shown separately."),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — Comparable Gaps, Net Estimates and Policy Flows",
         subtitle="Two official open-data series: new olim by the Ministry of "
                  "Aliyah and Integration (from 2015), PIBA permit issuance "
                  "(from 2019). Never summed into one line.",
         source="Sources: Ministry of Aliyah and Integration open data · "
                "Population and Immigration Authority open data · World Bank "
                "WDI (UN WPP) · " + _PENDING_SRC,
         alt="Four panels on Israeli migration. Comparable gross immigration "
             "and emigration remain pending; the UN's net-"
             "migration estimate peaks near 5.2 per 1,000 the same year, and "
             "the panel keeps it distinct from olim; the UN DESA "
             "foreign-born share falls from 26.6% in 2010 to 22.3% in 2024; "
             "the lens panel "
             "draws new residence and work permits issued (records, not "
             "people), extensions, and the distinct Law of Return subset, "
             "with visitor and "
             "diplomatic classes excluded by name."),
)
