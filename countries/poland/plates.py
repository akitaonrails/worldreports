"""Poland's plates, on the plate spine.

Twelve chapters. Every plate declares its topic and claims its four panels
by slot key, in the spine's order, so a Polish panel wipes over the same
panel of every other country: same indicator, same unit, same y-scale
(PLATE_SPINE.md, core/spine.py).

Four conventions run through the file.

- **Definitions are never spliced.** The registered unemployment rate and
  the BAEL survey are two lines, not one; CPI and HICP ride together with
  both named; GUS's customs goods and the national accounts' goods and
  services are two perimeters, drawn on their own panels; the police's
  confirmed offences and the vital-statistics assault deaths answer
  different questions and are drawn as such. Every seam has a note.
- **Population is the revised residence series** (`demography.csv`
  → `population_jan`, GUS post-2021-census, the one Eurostat carries).
  Every per-person figure in the country divides by it. Rates that a
  publisher already publishes (the police homicide rate, the LFS, the
  crude rates) are used as published rather than recomputed.
- **Notes read their numbers from the CSVs** at build time, so a refetch
  that moves a figure moves the sentence with it.
- **Two slots stay visibly pending.** The household lending rate has no
  official machine route (NBP answers 403, Eurostat has no new-business
  MIR series for Poland) and the WIG20 archive is per-session and
  JS-driven. Both say so on the panel and in `ui.json`, and neither is
  filled with a proxy.

The 2020 excursion in Poland's net-migration series is a scale conflict,
not a data gap: see `plate_migration`, `DATA_NOTES.md` and the pending
notes there.
"""
from __future__ import annotations

from core.sideload import sibling

events = sibling(__file__, "events")

W0 = 2006        # the shared plate window opens here
LAST_FULL = 2024


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


def _note(p, ax, x, y, text, ha="left", va="top", size=8.0):
    """A short italic note in axes fractions."""
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=size, style="italic", color=p.MUTED, zorder=7)


def _foot(p, ax, text):
    """The provenance line under a panel."""
    ax.text(0.5, -0.07, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.2, color=p.FAINT, style="italic")


def _legend(ax, loc="upper left", ncol=1, size=7.8):
    ax.legend(loc=loc, ncol=ncol, fontsize=size, frameon=False,
              handlelength=1.6, borderaxespad=0.2)


def _pending(ig, ax, why):
    """The reason a canonical slot is empty, in the panel and in words."""
    ax.text(0.5, 0.34, why, transform=ax.transAxes, ha="center", va="top",
            fontsize=8.2, style="italic", color=ig.p.MUTED)


def _mark(ig, ax, key, dy=0.72):
    """One of events.MARKS on a panel."""
    x, label = events.MARKS[key]
    ig.add_event(ax, x, label, dy=dy)


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(a)


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p
    E = "macro/economy.csv"

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, E, "gdp_growth_pct")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=True)
    v20 = _at(gy, gv, 2020)
    ax.annotate(f"{v20:.1f}%", (2020, v20), textcoords="offset points",
                xytext=(0, -2), ha="center", va="top", fontsize=8.8,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.55, "the only decline in the window: "
          f"{v20:.1f}% in 2020.\nIn 2009, when the Union fell, "
          f"Poland grew {_at(gy, gv, 2009):.1f}%.")
    _foot(p, ax, "GUS national accounts (ESA 2010); Eurostat's harmonised "
          "growth agrees to the decimal")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "macro/gdp_per_person.csv", "gdp_per_capita_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    _note(p, ax, 0.02, 0.96, f"US${_at(py, pv, 2006):,.0f} in 2006, "
          f"US${pv[-1]:,.0f} in {py[-1]}:\nnominal dollars at market rates")
    _foot(p, ax, "World Bank, current US$ per resident — the revised "
          "population, not the old register balance")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year)")
    cy, cv = _yr(ctx, E, "cpi_pct")
    hy, hv = _yr(ctx, E, "hicp_pct")
    ctx.line(ax, cy, cv, p.ALERT, label="CPI")
    ctx.line(ax, hy, hv, p.NAVY, label="HICP")
    ig.add_recessions(ax, label=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(6, 2), ha="left",
                fontsize=8.8, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, "the highest rate in the Union, and the\n"
          f"deflation year {_at(cy, cv, 2015):+.1f}%, six years later")
    _legend(ax, "upper right", size=7.6)
    _foot(p, ax, "GUS annual CPI with Eurostat's HICP beside it — the "
          "harmonised index has different housing weights")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    by, bv = _yr(ctx, E, "unemployment_lfs_pct")
    ry, rv = _yr(ctx, E, "unemployment_registered_pct")
    uy, uv = _yr(ctx, E, "unemployment_estat_pct")
    ctx.line(ax, by, bv, p.BLUE, label="LFS (BAEL) survey")
    ctx.line(ax, ry, rv, p.ALERT, label="Registered, administrative")
    ctx.line(ax, uy, uv, p.NAVY, label="Eurostat LFS, annual average")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.62, "the survey and the register differ by about\n"
          "two points in every year: two definitions, two lines")
    _legend(ax, "upper right", size=7.4)
    _foot(p, ax, "GUS BAEL (last survey of the year) and GUS register; "
          "Eurostat's LFS is the annual average")
    _finish(ctx, ig)


# ------------------------------------------------------------------ fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p
    F = "fiscal/fiscal.csv"

    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure "
                 "(% of GDP)")
    ry, rv = _yr(ctx, F, "revenue_pct_gdp")
    ey, ev = _yr(ctx, F, "expenditure_pct_gdp")
    ctx.line(ax, ey, ev, p.ALERT, label="Expenditure")
    ctx.line(ax, ry, rv, p.TEAL, label="Revenue")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ey, ev, p.ALERT, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.30, f"revenue {_at(ry, rv, 2025):.1f}% of GDP in "
          f"2025 against\nexpenditure {_at(ey, ev, 2025):.1f}% — the widest "
          "gap since 2020")
    _legend(ax, "lower right", size=7.6)
    _foot(p, ax, "Eurostat EDP notification, general government (ESA 2010), "
          "calendar years")

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    by, bv = _yr(ctx, F, "deficit_pct_gdp")
    py, pv = _yr(ctx, F, "primary_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ctx.line(ax, py, pv, p.NAVY, label="Primary balance")
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{_at(by, bv, 2025):.1f}%", (2025, _at(by, bv, 2025)),
                textcoords="offset points", xytext=(0, -2), ha="center",
                va="top", fontsize=8.6, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, f"{_at(by, bv, 2025):.1f}% in 2025 is GUS's "
          f"preliminary estimate;\nprimary {_at(py, pv, 2025):.1f}% after "
          "interest")
    _legend(ax, "lower left", size=7.6)
    _foot(p, ax, "Overall balance and the primary balance: the same series "
          "before the interest bill")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    dy, dv = _yr(ctx, F, "debt_pct_gdp")
    ctx.line(ax, dy, dv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.PURPLE, lambda v: f"{v:.0f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{_at(dy, dv, 2006):.1f}% in 2006, "
          f"{dv[-1]:.1f}% in {dy[-1]};\nthe 2020 jump is the pandemic, "
          "not new borrowing")
    _foot(p, ax, "Eurostat EDP gross debt; GUS publishes the same "
          "aggregate (59.7% in 2025)")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    iy, iv = _yr(ctx, F, "interest_pct_gdp")
    ctx.line(ax, iy, iv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.GOLD, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{_at(iy, iv, 2021):.1f}% of GDP in 2021 — "
          "the cheapest\ndebt service in the window; "
          f"{iv[-1]:.1f}% in {iy[-1]}")
    _foot(p, ax, "Eurostat D41PAY, general government")
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
SPEND = [
    ("social_protection_pct_gdp", "social protection", "ALERT"),
    ("health_pct_gdp", "health", "PURPLE"),
    ("general_services_pct_gdp", "general public services", "NAVY"),
    ("education_pct_gdp", "education", "BLUE"),
    ("economic_affairs_pct_gdp", "economic affairs", "TEAL"),
    ("defence_order_pct_gdp", "defence and public order", "GREEN"),
    ("other_pct_gdp", "other", "GOLD"),
]
SPEND_FILE = "spending/spending.csv"


def plate_spending(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("spending.by_function",
                 "Spending by function, stacked (% of GDP)")
    cols = [(lab, col, getattr(p, colour)) for col, lab, colour in SPEND]
    series, years = [], None
    for _lab, col, _colour in cols:
        y, v = _yr(ctx, SPEND_FILE, col)
        if years is None:
            years = y
        elif y != years:
            # Every COFOG column shares the publisher's year list; a
            # mismatch would stack a year against another's components.
            raise AssertionError("poland: COFOG columns disagree on years")
        series.append(v)
    ax.stackplot(years, *series, labels=[lab for lab, _, _ in cols],
                 colors=[c for _, _, c in cols], alpha=0.9, lw=0)
    ig.add_recessions(ax, label=False)
    _legend(ax, "upper left", ncol=2, size=6.6)
    tot = [sum(v[i] for v in series) for i in range(len(years))]
    ax.annotate(f"{tot[-1]:.1f}% of GDP ({years[-1]})",
                (years[-1], tot[-1]), textcoords="offset points",
                xytext=(-4, 6), ha="right", fontsize=8.2,
                fontweight="bold", color=p.INK)
    _foot(p, ax, "Eurostat COFOG general government, seven groups; general "
          "public services includes the interest bill")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    sy, sv = _yr(ctx, SPEND_FILE, "social_protection_pct_gdp")
    ty, tv = _yr(ctx, SPEND_FILE, "total_pct_gdp")
    rest = [t - s for t, s in zip(tv, sv)]
    ctx.line(ax, ty, tv, p.NAVY, label="Everything else")
    ctx.line(ax, sy, sv, p.ALERT, label="Social protection")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"{sv[-1]:.1f}% of GDP on social protection in "
          f"{sy[-1]},\n{rest[-1]:.1f}% on everything else")
    _legend(ax, "lower right", size=7.6)
    _foot(p, ax, "Same COFOG totals, two groups: the function and the "
          "remainder")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(% of GDP)")
    iy, iv = _yr(ctx, SPEND_FILE, "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.TEAL, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{max(iv):.1f}% at the 2008 peak, "
          f"{iv[-1]:.1f}% in {iy[-1]}:\nthe rate never returned to its "
          "pre-crisis level")
    _foot(p, ax, "Eurostat nama_10_gdp: gross fixed capital formation, "
          "whole economy")

    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    gy, gv = _yr(ctx, SPEND_FILE, "public_investment_pct_gdp")
    ctx.line(ax, gy, gv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.GOLD, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{min(gv):.1f}% in 2016 was the low; "
          f"{gv[-1]:.1f}% in {gy[-1]}\nis EU-funded infrastructure")
    _foot(p, ax, "Eurostat P51G, general government gross fixed capital "
          "formation")
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
DEST = [
    ("share_germany_pct", "Germany", "NAVY"),
    ("share_china_pct", "China", "ALERT"),
    ("share_czechia_pct", "Czechia", "BLUE"),
    ("share_russia_pct", "Russia", "GOLD"),
    ("share_ukraine_pct", "Ukraine", "TEAL"),
]


def plate_trade(ctx, ig) -> None:
    p = ctx.p
    T = "trade/trade.csv"

    ax = ig.slot("trade.exports_imports", "Exports and imports (% of GDP)")
    xy, xv = _yr(ctx, T, "exports_pct_gdp")
    my, mv = _yr(ctx, T, "imports_pct_gdp")
    ctx.line(ax, xy, xv, p.BLUE, label="Exports")
    ctx.line(ax, my, mv, p.ALERT, label="Imports")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"{_at(xy, xv, 2022):.1f}% of GDP in 2022, the "
          f"highest\nin the window; {xv[-1]:.1f}% in {xy[-1]}")
    _legend(ax, "lower right", size=7.6)
    _foot(p, ax, "Eurostat national accounts P6/P7: goods and services, "
          "ownership-change basis")

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    by, bv = _yr(ctx, T, "balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    peak = max(zip(by, bv), key=lambda t: t[1])
    pos_from = min(y for y, v in zip(by, bv) if y >= 2015 and v > 0)
    ax.annotate(f"{peak[1]:.1f}%", peak, textcoords="offset points",
                xytext=(0, 6), ha="center", fontsize=8.6,
                fontweight="bold", color=p.GREEN)
    _note(p, ax, 0.02, 0.96, f"positive every year since {pos_from}: "
          "goods and services\ntogether, which is why this line and the "
          f"customs one differ")
    _foot(p, ax, "Derived: exports minus imports, same Eurostat series")

    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    for col, label, colour in DEST:
        dy, dv = _yr(ctx, "trade/partners.csv", col)
        ctx.line(ax, dy, dv, getattr(p, colour), label=label, lw=1.9, ms=3.2)
    ig.add_recessions(ax, label=False)
    ry, rv = _yr(ctx, "trade/partners.csv", "share_russia_pct")
    _note(p, ax, 0.02, 0.96, f"Germany takes a quarter of goods exports;\n"
          f"Russia fell from {max(rv):.1f}% in {ry[rv.index(max(rv))]} to "
          f"{rv[-1]:.1f}%")
    _legend(ax, "center right", size=7.4)
    _foot(p, ax, "Eurostat Comext DS-045409, customs goods, share of "
          "Poland's world total")

    ax = ig.slot("trade.lens", "Goods balance, customs basis (EUR bn)")
    cy, cv = _yr(ctx, T, "goods_balance_mln_eur")
    cb = [v / 1000 for v in cv]
    ctx.bars(ax, cy, cb, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"−EUR {abs(_at(cy, cb, 2022)):.1f}bn in 2022, "
          f"+EUR {_at(cy, cb, 2023):.1f}bn in 2023:\nservices are not in "
          "this perimeter")
    _foot(p, ax, "GUS external trade (INTRASTAT + EXTRASTAT), customs "
          "goods only — a different perimeter from the panels above")
    _finish(ctx, ig)


# ------------------------------------------------------------------ markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p
    M = "markets/markets.csv"

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ky, kv = _yr(ctx, M, "nbp_reference_rate_year_end_pct")
    cy, cv = _yr(ctx, "macro/economy.csv", "cpi_pct")
    ctx.line(ax, cy, cv, p.ALERT, label="Inflation (CPI)")
    ctx.line(ax, ky, kv, p.NAVY, label="Reference rate, 31 December")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "hikes", dy=0.55)
    _note(p, ax, 0.02, 0.96, f"{_at(ky, kv, 2020):.2f}% until October 2021, "
          f"{_at(ky, kv, 2022):.2f}%\nat the end of 2022: the fastest "
          "tightening here")
    _legend(ax, "upper right", size=7.4)
    _foot(p, ax, "NBP reference rate at 31 December — the atlas's other "
          "countries draw an annual mean; GUS CPI")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    yy, yv = _yr(ctx, M, "yield_10y_pct")
    ctx.line(ax, yy, yv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, yy, yv, p.PURPLE, lambda v: f"{v:.2f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{max(yv):.2f}% in "
          f"{yy[yv.index(max(yv))]} — the highest annual\n"
          f"average of the window; {_at(yy, yv, 2020):.2f}% in 2020")
    _foot(p, ax, "Eurostat EMU convergence criterion, 10-year benchmark "
          "bond, annual average")

    ax = ig.slot("markets.currency", "Currency against the US$ "
                 "(index 2006 = 100, up = stronger)")
    fy, fv = _yr(ctx, M, "pln_index_usd_2006")
    ctx.line(ax, fy, fv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, fy, fv, p.TEAL, lambda v: f"{v:.0f}", dy=8)
    _mark(ig, ax, "franc", dy=0.50)
    _note(p, ax, 0.02, 0.22, f"up is stronger: {max(fv):.0f} in "
          f"{fy[fv.index(max(fv))]},\n{min(fv):.0f} in "
          f"{fy[fv.index(min(fv))]}, {fv[-1]:.0f} in {fy[-1]}")
    _foot(p, ax, "NBP Table A, annual mean of the daily mid-rates; "
          "2006 mean = 100")

    ax = ig.slot("markets.equities", "Main equity index in US$ "
                 "(index 2006 = 100, in US$)")
    ctx.pending(ax)
    _pending(ig, ax, "The WIG20 is not on an official machine feed: GPW's\n"
             "archive is per-session and JS-driven, stooq is walled, and\n"
             "Yahoo returns a single point. No proxy is substituted.")
    _foot(p, ax, "SOURCES.yaml meta.pending — route record in DATA_NOTES.md")
    _finish(ctx, ig)


# ------------------------------------------------------------------- credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p
    C = "credit/credit.csv"

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    hy, hv = _yr(ctx, C, "household_debt_pct_gdp")
    ctx.line(ax, hy, hv, p.ALERT)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, hy, hv, p.ALERT, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{max(hv):.1f}% of GDP in "
          f"{hy[hv.index(max(hv))]}, {hv[-1]:.1f}% in {hy[-1]}:\n"
          "the one convergence running backwards")
    _foot(p, ax, "BIS total credit, households and NPIs, all lenders, "
          "break-adjusted, Q4")

    ax = ig.slot("credit.lending_rate", "Household lending rate vs "
                 "policy rate (%)")
    ctx.pending(ax)
    _pending(ig, ax, "No official new-business lending rate for Poland:\n"
             "NBP's rates sit behind a site challenge, Eurostat's MIR\n"
             "table has no Polish series, and the World Bank's is empty.")
    _foot(p, ax, "SOURCES.yaml meta.pending — five routes tried and recorded")

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    ny, nv = _yr(ctx, C, "npl_ratio_pct_q4")
    ctx.line(ax, ny, nv, p.NAVY)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ny, nv, p.NAVY, lambda v: f"{v:.2f}%", dy=8)
    _note(p, ax, 0.02, 0.96, f"{max(nv):.2f}% in "
          f"{ny[nv.index(max(nv))]}, {nv[-1]:.2f}% in {ny[-1]} —\n"
          "EBA reporting banks, not the whole sector")
    _foot(p, ax, "EBA Risk Dashboard AQT_3.2, year-end; large banks only, "
          "so it sits below the NBP's sector ratio")

    ax = ig.slot("credit.lens", "NPL ratio, two compilations (%)")
    ey, ev = _yr(ctx, C, "npl_ratio_pct_q4")
    wy, wv = _yr(ctx, C, "npl_pct_wb_crosscheck")
    ctx.line(ax, ey, ev, p.NAVY, label="EBA, reporting banks")
    ctx.line(ax, wy, wv, p.GOLD, label="World Bank FSI, all banks",
             split_year=2020)
    ig.add_recessions(ax, label=False)
    ax.set_ylim(0, 9.5)
    _note(p, ax, 0.02, 0.96, f"the Bank's figure stops in {wy[-1]}; the\n"
          "EBA's starts in 2014 — never one line")
    _legend(ax, "upper right", size=7.4)
    _foot(p, ax, "Two compilations, two reporting populations, two scopes")
    _finish(ctx, ig)


# ------------------------------------------------------------------- people
def plate_people(ctx, ig) -> None:
    p = ctx.p
    P = "people/people.csv"

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100)")
    ey, ev = _yr(ctx, P, "gini_eurostat")
    wy, wv = _yr(ctx, P, "gini_wb")
    ctx.line(ax, wy, wv, p.GOLD, label="World Bank compilation")
    ctx.line(ax, ey, ev, p.PURPLE, label="EU-SILC")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"EU-SILC {ev[0]:.1f} in {ey[0]}, "
          f"{ev[-1]:.1f} in {ey[-1]};\nthe Bank's compilation runs lower")
    _legend(ax, "center right", size=7.4)
    _foot(p, ax, "Eurostat ilc_di12 and the World Bank's harmonised Gini — "
          "two compilations, never spliced")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    ay, av = _yr(ctx, P, "arop60_pct")
    ny, nv = _yr(ctx, P, "relative_poverty_after_transfers_pct")
    by, bv = _yr(ctx, P, "relative_poverty_before_transfers_pct")
    ctx.line(ax, by, bv, p.FAINT, label="GUS, 50% of median, before "
             "transfers")
    ctx.line(ax, ay, av, p.TEAL, label="Eurostat, 60% of median")
    ctx.line(ax, ny, nv, p.ALERT, label="GUS, 50% of median, after "
             "transfers")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"transfers cut the national rate from "
          f"{bv[-1]:.1f}%\nto {nv[-1]:.1f}% in {ny[-1]}; three thresholds, "
          "three lines")
    _legend(ax, "upper right", size=6.8)
    _foot(p, ax, "Three thresholds and two publishers: Eurostat's EU "
          "headline and GUS's national 50% series")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    my, mv = _yr(ctx, P, "minimum_wage_usd_month")
    ctx.line(ax, my, mv, p.GREEN)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, my, mv, p.GREEN, lambda v: f"US${v:,.0f}", dy=8)
    _note(p, ax, 0.02, 0.96, f"US${_at(my, mv, 2006):,.0f} a month in 2006, "
          f"US${mv[-1]:,.0f} in {my[-1]} —\nstatutory gross, converted at "
          "the annual mean rate")
    _foot(p, ax, "Statutory monthly gross minimum at NBP's mean USD/PLN; "
          "the 2023 and 2024 mid-year rises are averaged")

    ax = ig.slot("people.lens", "Statutory minimum wage (PLN per month)")
    zy, zv = _yr(ctx, P, "minimum_wage_pln_month")
    ctx.line(ax, zy, zv, p.RED_D)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"PLN {zv[0]:,.0f} in 2006, {zv[-1]:,.0f} in "
          f"{zy[-1]}:\nin zloty the wage rose in every single year")
    _foot(p, ax, "The same statutory wage in the currency it is legislated "
          "in — the dollar panel moves with the exchange rate")
    _finish(ctx, ig)


# -------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "world/world.csv", "gdp_usd_bn")
    ctx.line(ax, gy, gv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.BLUE, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, f"US${_at(gy, gv, 2006):,.0f}bn in 2006, "
          f"US${gv[-1]:,.0f}bn in {gy[-1]} —\na tripling in nominal dollars")
    _foot(p, ax, "World Bank, current US$ — nominal, so the exchange rate "
          "moves with the price level")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "world/world.csv", "hdi")
    ctx.line(ax, hy, hv, p.GREEN)
    ctx.endlabel(ax, hy, hv, p.GREEN, lambda v: f"{v:.3f}", dy=8)
    _note(p, ax, 0.02, 0.96, f"{hv[0]:.3f} in {hy[0]}, {hv[-1]:.3f} in "
          f"{hy[-1]} —\none Human Development Report vintage throughout")
    _foot(p, ax, "UNDP Human Development Report; the series stops in 2023")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (0–100 score)")
    cy, cv = _yr(ctx, "world/world.csv", "cpi_score")
    ctx.line(ax, cy, cv, p.GOLD)
    ctx.endlabel(ax, cy, cv, p.GOLD, lambda v: f"{v:.0f}", dy=8)
    _note(p, ax, 0.02, 0.96, f"{max(cv):.0f} in "
          f"{cy[cv.index(max(cv))]}, {cv[-1]:.0f} in {cy[-1]}:\nthe 2012+ "
          "method only, never spliced to the old scale")
    _foot(p, ax, "Transparency International; the score is a perception "
          "index, not a measurement")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn)")
    ry, rv = _yr(ctx, "world/world.csv", "reserves_usd_bn")
    ctx.line(ax, ry, rv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.TEAL, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, f"US${rv[0]:,.0f}bn in {ry[0]}, "
          f"US${rv[-1]:,.0f}bn in {ry[-1]} —\nsix times the 2006 stock")
    _foot(p, ax, "World Bank FI.RES.TOTL.CD (the NBP's year-end reserves)")
    _finish(ctx, ig)


# --------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p
    D = "demography/demography.csv"

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    iy, iv = _yr(ctx, D, "population_index_2006")
    py, pv = _yr(ctx, D, "population_jan")
    ctx.line(ax, iy, iv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.BLUE, lambda v: f"{v:.1f}", dy=8)
    _mark(ig, ax, "census", dy=0.55)
    _note(p, ax, 0.02, 0.96, f"{_at(py, pv, 2006) / 1e6:.1f}m on 1 January "
          f"2006,\n{pv[-1] / 1e6:.1f}m on 1 January {py[-1]}")
    _foot(p, ax, "Eurostat demo_gind (GUS's revised residence series); the "
          "unrevised balance is about 1.0m higher")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    ty, tv = _yr(ctx, D, "tfr")
    ctx.line(ax, ty, tv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ax.axhline(2.1, color=p.FAINT, lw=0.9, ls=":", zorder=2)
    ax.text(2024.6, 2.16, "replacement: 2.1", fontsize=7.6, color=p.MUTED,
            style="italic", ha="right")
    _note(p, ax, 0.02, 0.96, f"{max(tv):.2f} at the {ty[tv.index(max(tv))]} "
          f"peak, {tv[-1]:.2f} in {ty[-1]} —\nwell under the level that "
          "replaces a generation")
    _foot(p, ax, "GUS / Eurostat demo_find (TOTFERRT), children per woman")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    by, bv = _yr(ctx, D, "birth_rate_per_1000")
    dy, dv = _yr(ctx, D, "death_rate_per_1000")
    ctx.line(ax, dy, dv, p.ALERT, label="Deaths")
    ctx.line(ax, by, bv, p.BLUE, label="Births")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.30, f"births fell from {bv[0]:.1f} to {bv[-1]:.1f} "
          f"per 1,000 while\ndeaths rose from {dv[0]:.1f} to "
          f"{max(dv):.1f} in 2020")
    _legend(ax, "center left", size=7.4)
    _foot(p, ax, "Eurostat demo_gind (GUS vital statistics), per 1,000 "
          "residents")

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net migration (per 1,000 people)")
    ny, nv = _yr(ctx, "demography/demography.csv",
                 "natural_change_rate_per_1000")
    ry, rv = _yr(ctx, "demography/demography.csv",
                 "net_migration_registered_per_1000")
    by, bv = _yr(ctx, "demography/demography.csv",
                 "net_migration_residual_per_1000")
    ctx.line(ax, ny, nv, p.NAVY, label="Natural change")
    ctx.line(ax, ry, rv, p.BLUE, label="Net migration (register)")
    ctx.line(ax, by, bv, p.GOLD, label="Net migration (balance)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.2, frameon=False)
    _note(p, ax, 0.02, 0.96, f"the register's 2020 collapse ({_at(ry, rv, 2020):.1f} "
          f"per 1,000)\nand the balance's {_at(by, bv, 2020):.1f}: two definitions, "
          "never one line")
    _foot(p, ax, "Eurostat demo_gind (GUS vital statistics and population "
          "balance), per 1,000 residents")
    _finish(ctx, ig)


# ----------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    S = "security/security.csv"

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    py, pv = _yr(ctx, S, "homicides_police_per_100k")
    uy, uv = _yr(ctx, S, "homicide_unodc_per_100k")
    ctx.line(ax, uy, uv, p.GOLD, label="UNODC", split_year=2023)
    ctx.line(ax, py, pv, p.ALERT, label="Polish Police, confirmed offences")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"police-confirmed offences, attempts "
          f"included:\n{pv[0]:.2f} in {py[0]}, {pv[-1]:.2f} in {py[-1]}")
    _legend(ax, "lower left", size=7.2)
    _foot(p, ax, "Polish Police (confirmed offences, attempts included) and "
          "UNODC's homicide count — different definitions")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    sy, sv = _yr(ctx, S, "suicides_per_100k")
    wy, wv = _yr(ctx, S, "suicide_who_per_100k")
    ctx.line(ax, wy, wv, p.GOLD, label="WHO estimate", split_year=2021)
    ctx.line(ax, sy, sv, p.PURPLE, label="National cause of death")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"{sv[0]:.1f} in {sy[0]}, {sv[-1]:.1f} in "
          f"{sy[-1]}:\nthe national count, from the cause-of-death table")
    _legend(ax, "lower left", size=7.2)
    _foot(p, ax, "Eurostat hlth_cd_aro (ICD X60–X84) and the WHO estimate "
          "via the World Bank")

    ax = ig.slot("security.road_deaths", "Road traffic deaths "
                 "(per 100,000)")
    ty, tv = _yr(ctx, S, "transport_deaths_per_100k")
    wy, wv = _yr(ctx, S, "road_deaths_who_per_100k")
    ctx.line(ax, wy, wv, p.GOLD, label="WHO, road only", split_year=2019)
    ctx.line(ax, ty, tv, p.NAVY, label="National, all transport")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"all transport accidents, V–Y85: {tv[0]:.1f} in "
          f"{ty[0]},\n{tv[-1]:.1f} in {ty[-1]}; the WHO line stops in 2019")
    _legend(ax, "center right", size=7.2)
    _foot(p, ax, "Eurostat transport accidents (road, rail, air, water) and "
          "the WHO's road-only estimate")

    ax = ig.slot("security.lens", "Homicide, two definitions (per 100,000)")
    py, pv = _yr(ctx, S, "homicides_police_per_100k")
    ay, av = _yr(ctx, S, "assault_deaths_per_100k")
    ctx.line(ax, py, pv, p.ALERT, label="Police offences, attempts included",
             split_year=2023)
    ctx.line(ax, ay, av, p.NAVY, label="Assault deaths, ICD X85–Y09")
    ig.add_recessions(ax, label=False)
    ax.set_ylim(0, 3.0)
    ratio = _at(py, pv, 2023) / _at(ay, av, 2023)
    _note(p, ax, 0.02, 0.96, "offences include attempts, so in 2023 the\n"
          f"police line runs {ratio:.1f} times the death count "
          f"({av[-1]:.2f} in {ay[-1]})")
    _legend(ax, "upper right", size=7.2)
    _foot(p, ax, "Two official answers to one word: an offence count and a "
          "cause-of-death count")
    _finish(ctx, ig)


# ---------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    M = "mortality/mortality.csv"

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000 people)")
    dy, dv = _yr(ctx, M, "death_rate_per_1000")
    ctx.line(ax, dy, dv, p.INK)
    ig.add_recessions(ax, label=False)
    peak = max(zip(dy, dv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f} in {peak[0]}", peak,
                textcoords="offset points", xytext=(6, 2), ha="left",
                fontsize=8.8, fontweight="bold", color=p.INK)
    _note(p, ax, 0.02, 0.96, f"{dv[0]:.1f} in {dy[0]}, {dv[-1]:.1f} in "
          f"{dy[-1]}:\nthe pandemic years are the spike, not a trend")
    _foot(p, ax, "Eurostat demo_gind (GUS vital statistics), per 1,000 "
          "residents")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above 2015–2019 average)")
    ey, ev = _yr(ctx, M, "excess_deaths_pct_vs_2015_2019")
    ctx.bars(ax, ey, ev, lambda v: p.ALERT if v > 0 else p.BLUE)
    ig.add_recessions(ax, label=False)
    peak = max(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}%", peak, textcoords="offset points",
                xytext=(0, 5), ha="center", fontsize=8.6,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, f"{peak[1]:.1f}% in {peak[0]}; "
          f"{_at(ey, ev, 2024):.1f}% in 2024 —\n"
          "one formula, the 2015–2019 mean of this series")
    _foot(p, ax, "Derived from deaths_all against the 2015–2019 mean, one "
          "vintage; not a published index")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    cy, cv = _yr(ctx, M, "covid_deaths_per_100k")
    ctx.bars(ax, cy, cv, p.ALERT)
    ig.add_recessions(ax, label=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.0f}", peak, textcoords="offset points",
                xytext=(0, 5), ha="center", fontsize=8.6,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96, f"{peak[1]:.0f} per 100,000 in {peak[0]} —\n"
          "the largest single feature of this chapter")
    _foot(p, ax, "Eurostat hlth_cd_aro, U071 + U072 as the underlying "
          "cause; the table starts in 2011")

    ax = ig.slot("mortality.lens", "Circulatory and cancer deaths "
                 "(per 100,000)")
    iy, iv = _yr(ctx, M, "deaths_circulatory")
    ky, kv = _yr(ctx, M, "deaths_cancer")
    py, pv = _yr(ctx, "demography/demography.csv", "population_jan")
    pop = dict(zip(py, pv))
    iv = [v / pop[y] * 100000 for y, v in zip(iy, iv)]
    kv = [v / pop[y] * 100000 for y, v in zip(ky, kv)]
    ctx.line(ax, iy, iv, p.ALERT, label="Circulatory disease")
    ctx.line(ax, ky, kv, p.NAVY, label="Cancer")
    ig.add_recessions(ax, label=False)
    ax.set_ylim(0, 620)
    covid_peak = max(_yr(ctx, M, "covid_deaths_per_100k")[1])
    _note(p, ax, 0.02, 0.96, f"circulatory disease killed "
          f"{iv[-1] / covid_peak:.1f} times as many people\nas COVID-19 did "
          "in its worst year")
    _legend(ax, "lower left", size=7.4)
    _foot(p, ax, "Eurostat cause-of-death counts ÷ the revised population, "
          "ICD I and C")
    _finish(ctx, ig)


# ---------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    M = "migration/migration.csv"

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    iy, iv = _yr(ctx, M, "immigration_per_1000")
    ey, ev = _yr(ctx, M, "emigration_per_1000")
    ctx.line(ax, iy, iv, p.GREEN, label="Immigration")
    ctx.line(ax, ey, ev, p.ALERT, label="Emigration")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"{_at(iy, iv, 2022):.1f} arrivals per 1,000 in "
          "2022 —\nthe register did not see the million refugees")
    _legend(ax, "center right", size=7.4)
    _foot(p, ax, "Eurostat migr_imm1ctz / migr_emi1ctz: meldunek residence "
          "registrations, divided by the revised population")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    ry, rv = _yr(ctx, M, "net_migration_registered_per_1000")
    by, bv = _yr(ctx, M, "net_migration_residual_per_1000")
    ctx.line(ax, ry, rv, p.BLUE, label="Register (meldunek)")
    ctx.line(ax, by, bv, p.GOLD, label="Population balance")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.2, frameon=False)
    _note(p, ax, 0.02, 0.96, "two official definitions: the register counts "
          "meldunek\nregistrations, the balance is the population residual")
    _foot(p, ax, "Eurostat migr_imm1ctz / migr_emi1ctz and demo_gind, per "
          "1,000 residents")

    ax = ig.slot("migration.foreign_born", "Foreign-born share of the "
                 "population (%)")
    fy, fv = _yr(ctx, M, "foreign_born_pct")
    cy, cv = _yr(ctx, M, "foreign_citizens_pct")
    ty, tv = _yr(ctx, M, "temporary_protection_beneficiaries")
    py, pv = _yr(ctx, "demography/demography.csv", "population_jan")
    pop = dict(zip(py, pv))
    tp = [(y, v / pop[y] * 100) for y, v in zip(ty, tv) if y in pop]
    tps = dict(tp)
    ctx.line(ax, fy, fv, p.PURPLE, label="Foreign-born")
    ctx.line(ax, cy, cv, p.GOLD, label="Foreign citizens")
    ctx.line(ax, [y for y, _ in tp], [v for _, v in tp], p.ALERT,
             label="Temporary protection", ls=(0, (1, 1.6)))
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"{_at(fy, fv, 2022):.1f}% foreign-born and "
          f"{tps[2022]:.1f}% under temporary\nprotection in 2022: the stock "
          "lags the inflow")
    _legend(ax, "upper right", size=7.2)
    _foot(p, ax, "Eurostat migr_pop1ctz / migr_pop3ctb stocks and "
          "migr_asytpsm beneficiaries, ÷ the revised population")

    ax = ig.slot("migration.lens", "Net migration, two measures "
                 "(per 1,000, own scale)")
    ry, rv = _yr(ctx, M, "net_migration_registered_per_1000")
    qy, qv = _yr(ctx, M, "net_migration_residual_per_1000")
    ctx.line(ax, qy, qv, p.BLUE, label="Population balance (residual)")
    ctx.line(ax, ry, rv, p.ALERT, label="Register (meldunek)")
    ig.add_recessions(ax, label=False)
    low = min(zip(ry, rv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.30, f"the register lost {abs(low[1]):.1f} per 1,000 "
          f"in {low[0]} and\nthe balance gained "
          f"{max(qv):.1f} in {qy[qv.index(max(qv))]}")
    _legend(ax, "lower left", size=7.4)
    _foot(p, ax, "Eurostat CNMIGRATRT and MIGTRT — the register's rate and "
          "the population-balance residual")
    _finish(ctx, ig)


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Economy — The Union's Fastest Catch-Up, and Its Price "
               "Shock",
         subtitle="Growth, income, prices and jobs from GUS, with the "
                  "Eurostat layer beside each national series.",
         source="Sources: GUS national accounts, prices and labour · "
                "Eurostat harmonised growth, HICP and LFS · World Bank GDP "
                "per person",
         alt="Four panels on the Polish economy, 2006–2026. Real growth is "
             "positive in every year except 2020, which falls 2.0%, and "
             "reaches 6.9% in 2021. GDP per person rises from US$9,069 in "
             "2006 to US$28,420 in 2025. Inflation runs low through the "
             "2010s, turns negative in 2015, and peaks at 14.4% in 2022 "
             "with the harmonised HICP close beside it. The registered "
             "unemployment rate falls from 14.8% in 2006 to about 5%, with "
             "the survey rate roughly two points below it."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — General Government, Not the State Budget",
         subtitle="ESA 2010 accrual, sector S13, calendar years: the EDP "
                  "notification Poland sends to the Commission.",
         source="Sources: Eurostat EDP notification and gov_10a_main · GUS "
                "general-government deficit and debt as the cross-check",
         alt="Four panels on Poland's general government. Revenue holds "
             "near 40% of GDP and rises to 43.6% by 2025; expenditure "
             "reaches 50.9% in 2025. The overall balance is negative in "
             "every year, worst at -7.4% of GDP in 2010 and -7.2% in 2025, "
             "with the primary balance a little above it. Gross debt runs "
             "from 47.1% of GDP in 2006 to 59.6% in 2025, peaking at 56.9% "
             "in 2013 along the way. Interest paid falls from 2.5% of GDP "
             "to 1.1% in 2021 and back to 2.5% in 2025."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Spending — What the State Does, Function by Function",
         subtitle="COFOG general-government expenditure as a share of GDP, "
                  "in the spine's seven groups.",
         source="Sources: Eurostat gov_10a_exp (COFOG), nama_10_gdp "
                "(investment) and P51G (general-government investment)",
         alt="Four panels on public spending. The stacked COFOG total runs "
             "from 44.3% of GDP in 2006 to 49.4% in 2024, with social "
             "protection the largest layer at 15–18% and general public "
             "services next. Social protection is 18.3% of GDP in 2024 "
             "against 31.1% for everything else. The whole-economy "
             "investment rate falls from 22.7% in 2008 to 17.3% in 2025. "
             "Public investment runs between 3.3% and 6.0% of GDP."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — Two Perimeters, One Open Economy",
         subtitle="Goods and services in the national accounts, customs "
                  "goods from GUS, and where the exports go.",
         source="Sources: Eurostat national accounts (P6/P7) and Comext "
                "DS-045409 · GUS external trade (INTRASTAT + EXTRASTAT)",
         alt="Four panels on Polish trade. Exports and imports rise from "
             "about 38% of GDP in 2006 to 62.4% and 60.7% in 2022, with the "
             "balance positive from 2015 and 5.6% of GDP in 2020. Germany "
             "takes about a quarter of goods exports, China about 10%, and "
             "Russia collapses from 12.0% in 2011 to 0.3% in 2025 while "
             "Ukraine rises. On the customs perimeter the goods balance "
             "swings from a -EUR 20bn deficit in 2022 to a +EUR 9.8bn "
             "surplus in 2023."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Markets — The Reference Rate, the Bond and the Zloty",
         subtitle="The NBP's year-end reference rate and the 10-year yield, "
                  "with the zloty against the dollar and inflation beside "
                  "them.",
         source="Sources: NBP reference rate and Table A · Eurostat EMU "
                "convergence criterion · GUS CPI",
         alt="Four panels on Polish markets. The reference rate sits at "
             "0.10% from 2020 until October 2021 and reaches 6.75% at the "
             "end of 2022 against 14.4% inflation, then falls to 4.0%. The "
             "10-year yield runs from 5.2% in 2006 to a 6.05% peak in 2022. "
             "The zloty index rises to 129 in 2008 and falls to 69.6 in "
             "2022, recovering to 82.6 in 2025. The equity panel is pending "
             "because no official WIG20 series could be assembled."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — Household Debt That Fell While the Economy Grew",
         subtitle="Total credit to households from the BIS, the banks' own "
                  "non-performing ratio, and the lending-rate slot the "
                  "publishers will not answer.",
         source="Sources: BIS total credit · EBA Risk Dashboard · World "
                "Bank / IMF Financial Soundness Indicators",
         alt="Four panels on household credit. Household debt rises from "
             "18.3% of GDP in 2006 to 35.9% in 2015 and falls to 22.1% in "
             "2025, the one convergence in this country running backwards. "
             "The lending-rate panel is pending: no official Polish "
             "new-business series exists on a machine feed. Bank "
             "non-performing loans fall from 7.25% in 2014 to 3.59% in "
             "2025, and the World Bank's wider cross-check, which stops in "
             "2020, sits above the banks' own figure."),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="People — Inequality Falling, and a Wage Rising in Zloty",
         subtitle="The Gini and the poverty thresholds on their own "
                  "definitions, and the statutory minimum wage in both "
                  "currencies.",
         source="Sources: Eurostat EU-SILC (ilc_di12, ilc_li02) · GUS "
                "national relative-poverty series · World Bank Gini · NBP "
                "exchange rates",
         alt="Four panels on incomes. The EU-SILC Gini falls from 30.8 in "
             "2014 to 24.9 in 2025 while the World Bank's compilation runs "
             "lower and stops in 2023. Poverty at 60% of median is 19.1% in "
             "2006 and 13.2% in 2025, and the national 50% series falls "
             "from 49.1% before transfers to 13.8% after them in 2024. The "
             "minimum wage rises from US$290 a month in 2006 to US$1,241 in "
             "2025, and in zloty from 899 to 4,666 — it rose every year in "
             "the currency it is set in."),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="Poland in the World — Size, Development, Reputation, "
               "Reserves",
         subtitle="The economy in dollars, the Human Development Index, the "
                  "corruption score and the reserves.",
         source="Sources: World Bank WDI · UNDP Human Development Report · "
                "Transparency International",
         alt="Four panels placing Poland internationally. GDP in current "
             "dollars rises from US$346bn in 2006 to US$1,035bn in 2025 on "
             "a log scale. The Human Development Index rises from 0.831 to "
             "0.906 in 2023. The corruption score runs from 58 in 2012 to "
             "53 in 2024 on the post-2012 method only. Reserves rise from "
             "US$48bn to US$272bn."),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — A Population That Peaked in 2012",
         subtitle="One population series, the revised residence count, and "
                  "the births and deaths that move it.",
         source="Sources: Eurostat demo_gind and demo_find (GUS's revised "
                "post-census population and vital statistics)",
         alt="Four panels on Poland's population. The index falls from 100 "
             "in 2006 to 95.2 in 2026, with the 2021 step that is the "
             "census revision rather than a demographic event. The "
             "fertility rate falls from 1.27 to 1.07, far below the 2.1 "
             "replacement line. Births per 1,000 fall from 9.8 to 6.5 while "
             "deaths rise from 9.7 to a 14.0 peak in 2021. The natural "
             "increase and net migration panel is pending: both official "
             "net-migration series leave the shared scale in 2020."),
    dict(id="10", slug="security", topic="security",
         builder=plate_security,
         title="Security — Two Homicide Counts and a Falling Suicide Rate",
         subtitle="Crime and death from the police, the vital register and "
                  "the WHO, each on its own definition.",
         source="Sources: Polish Police · Eurostat cause-of-death statistics "
                "· UNODC and WHO via the World Bank",
         alt="Four panels on violence and accidents. Police-confirmed "
             "homicide offences fall from 2.14 per 100,000 in 2006 to 1.52 "
             "in 2023 on a log scale, with the UNODC count below them. The "
             "suicide rate falls from 16.7 in 2011 to 12.0 in 2024. "
             "Transport deaths fall from 12.9 to 6.9 per 100,000, while the "
             "WHO's road-only estimate ends in 2019. The lens shows the "
             "police count running about three times the assault-death "
             "count."),
    dict(id="11", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — The Pandemic Wave and the Big Killers",
         subtitle="Registered deaths, the excess over 2015–2019, COVID-19 "
                  "as an underlying cause, and what actually kills Poles.",
         source="Sources: Eurostat demo_gind and hlth_cd_aro (GUS vital "
                "statistics)",
         alt="Four panels on mortality. The crude death rate rises from 9.7 "
             "per 1,000 in 2006 to 12.7 in 2020 and 14.0 in 2021, then "
             "falls to 11.2 in 2024. Excess deaths reach 29.2% above the "
             "2015–2019 average in 2021. COVID-19 kills 243 per 100,000 as "
             "an underlying cause that year. Circulatory disease kills "
             "about 410 per 100,000 and cancer about 270, both far above "
             "the pandemic's toll."),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — The Register That Cannot See the Refugees",
         subtitle="Registration flows, the population-balance residual and "
                  "the temporary-protection stock, never one line.",
         source="Sources: Eurostat migration statistics (migr_imm1ctz, "
                "migr_emi1ctz, migr_pop1ctz, migr_pop3ctb, migr_asytpsm)",
         alt="Four panels on migration. Registered immigration reaches 7.5 "
             "per 1,000 in 2022 while emigration stays near 6, and the net "
             "migration slot is pending because both official series leave "
             "the shared scale in 2020. The foreign-born share is 2.6% and "
             "the temporary-protection stock 2.6% of the population in "
             "2022, against 1.2% foreign citizens. The lens draws the "
             "register's net rate, which loses 20.3 per 1,000 in 2020, "
             "against the population balance's 12.6 in 2022."),
)
