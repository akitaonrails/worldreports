"""The Italy plates, on the plate spine.

Every plate declares its topic and claims its four panels by slot key, in
the spine's order, so an Italian panel sits over the same panel of every
other country in the comparison viewer: same indicator, same unit, same
y-scale (PLATE_SPINE.md, core/spine.py).

Twelve chapters. Italy's harmonised layer is Eurostat — the same decision
France and Spain took, because the fiscal series, the harmonised labour
survey, the migration suite and the demographic file all arrive through
it. The national twin is ISTAT's SDMX API, and where the two publish one
statistic (births, deaths, the 1-January population) they agree to the
person, so the national line rides beside the canonical one rather than
continuing it. ISTAT went quiet mid-fetch and six of its series are
`meta.pending` in SOURCES.yaml; none of them blocks a canonical slot, and
the two slots whose national detail is genuinely unavailable (mafia
homicides in security, and the ISTAT NIC bases before 2016) say so
plainly instead of being filled from elsewhere. The destination panel now
uses an Italy-reporter UN Comtrade customs-goods snapshot, and the corruption
panel uses TI's comparable 2012–2025 workbook series. The minimum-wage panel
is the remaining canonical absence: Italy has none by statute.

Two conventions run through the file:

- **Notes read their numbers from the CSVs** at build time, so a refetch
  that moves a figure moves the sentence with it. Spot values quoted in
  DATA_NOTES.md are pinned in tests against the same CSVs.
- **Counts become rates** through ctx.per_1000 / ctx.per_100k against the
  Eurostat 1-January population (`social/demography.csv`) —
  the same territory and the same registered-resident scope as the
  counts; where ISTAT publishes its own rate (the police-recorded homicide rate)
  the plate uses ISTAT's. UN Comtrade supplies the customs-goods destination
  snapshot that Coeweb could not serve, and TI's pinned workbook supplies the
  comparable post-2012 corruption index.
"""
from __future__ import annotations

import math

from core.sideload import sibling

events = sibling(__file__, "events")

W0 = 2006        # the shared plate window opens here


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


def _map(ctx, rel: str, col: str, since: int = W0, until: int | None = None):
    """{year: float} from a calendar-year CSV, blanks dropped."""
    rows = ctx.rows(rel) or {}
    return {y: float(r[col]) for y, r in sorted(rows.items())
            if y >= since and (until is None or y <= until)
            and (r.get(col) or "").strip()}


def _records(ctx, rel: str) -> list[dict]:
    """Rows from a non-time-series CSV such as a partner snapshot."""
    table = ctx.table(rel) or {}
    return [dict(zip(table, values)) for values in zip(*table.values())]


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
    """A labelled ISTAT national line riding beside the canonical one.

    Thin, small markers, dotted: the Eurostat series stays the spine's
    line and the national one is visibly the second reading, never a
    continuation of the first.
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


def _markL(ig, ax, key, dy=0.97):
    """One of events.MARKS with the label to the LEFT of the line, for
    panels whose rising bars would otherwise stand under the text."""
    x, label = events.MARKS[key]
    ig.add_event(ax, x, "", dy=dy)
    ax.text(x - 0.12, dy, label, transform=ax.get_xaxis_transform(),
            fontsize=7.8, color=ig.p.MUTED, ha="right", va="top",
            clip_on=False)


def _bands_labelled_at(ig, ax, y, p):
    """The recession bands with their names at height `y` (axes fraction),
    for a slot-1 panel whose data fill the bottom where add_recessions puts
    the names."""
    ig.add_recessions(ax, label=False)
    for start, end, name in ig.country.recessions:
        ax.text((start + end) / 2, y, name, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=8, color=p.MUTED,
                style="italic")


def _pop(ctx):
    """The rate denominator: Eurostat demo_gind resident population,
    1 January, persons. Same territory and legal scope as ISTAT's births,
    deaths, flows and certificates (DATA_NOTES.md)."""
    return _map(ctx, "social/demography.csv", "population")


def _cause(ctx, code: str):
    """{year: deaths} for one European-shortlist code (never summed
    across codes: the shortlist nests).

    Read with the csv module, not ctx.table: read_table number-casts the
    code column, and float("11_1") is 111.0 — Python's underscore digit
    grouping. The codes are ICD shortlist labels, not numbers.
    """
    import csv
    path = ctx.c.data("social/causes_of_death.csv")
    out = {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(ln for ln in fh
                                if not ln.lstrip().startswith("#"))
        for r in reader:
            if r["code"] == code and (r.get("deaths") or "").strip():
                out[int(float(r["year"]))] = float(r["deaths"])
    return out


def _rate(ctx, counts, base: float):
    """Counts per population, year by year — the conversion DATA_NOTES.md
    documents: same year, Eurostat 1-January population."""
    pop = _pop(ctx)
    return (counts, {y: pop[y] for y in counts})


def _nice_pct(v: float) -> str:
    return f"{v:+.1f}" if v < 0 else f"{v:.1f}"


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(a)


# ------------------------------------------------------------------ economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, "macro/gdp_estat.csv", "real_growth")
    ctx.bars(ax, gy, gv, lambda v: p.VERDE if v >= 0 else p.ROSSO)
    # ISTAT's own quarterly levels, summed; the line only where four
    # quarters are published, so 2026 (two quarters) simply ends.
    lv = _map(ctx, "macro/gdp_istat.csv", "gdp_eurmn")
    qn = _map(ctx, "macro/gdp_istat.csv", "quarters")
    igrow = {y: (lv[y] / lv[y - 1] - 1) * 100
             for y in lv if y - 1 in lv and qn.get(y, 0) >= 4
             and qn.get(y - 1, 0) >= 4}
    _natl(ctx, ax, sorted(igrow), [igrow[y] for y in sorted(igrow)],
          p.NAVY, "ISTAT, sum of quarters")
    _barkey(ax, p.VERDE, "Eurostat (bars)")
    _bands_labelled_at(ig, ax, 0.98, p)
    _markL(ig, ax, "stall", dy=0.72)
    for y in (2009, 2020):
        v = _at(gy, gv, y)
        ax.annotate(f"{v:+.1f}%", (y, v), textcoords="offset points",
                    xytext=(0, -4), ha="center", va="top", fontsize=8.6,
                    fontweight="bold", color=p.ROSSO)
    _note(p, ax, 0.02, 0.84, f"the 2021 rebound printed {_at(gy, gv, 2021):+.1f}% "
          "and faded into the 2019 stall;\nthe bands stop at the sign "
          "run, not at the troughs (DATA_NOTES)", size=7.6)
    ax.legend(loc="lower right", fontsize=7.6, frameon=False)
    _foot(p, ax, "Eurostat nama_10_gdp and ISTAT 163_156 (ed. 2026M10) — "
          "two publishers of one statistic, equal within EUR 5mn a year")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "international/gdp_pc.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    _note(p, ax, 0.02, 0.34, f"in US$ per person, {_at(py, pv, 2008):,.0f} in 2008 "
          f"against {_at(py, pv, 2024):,.0f} in 2024:\nthe decade of "
          "stagnation, priced by the World Bank", size=7.6)
    _foot(p, ax, "World Bank NY.GDP.PCAP.CD, mid-year population — used "
          "for nothing else (DATA_NOTES)")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year) and the ECB's definition")
    ax.axhline(2, color=p.VERDE_D, lw=1.0, ls=":", zorder=2)
    cy, cv = _yr(ctx, "macro/hicp.csv", "hicp")
    ctx.line(ax, cy, cv, p.ROSSO, label="HICP, harmonised (Eurostat)")
    ni = _map(ctx, "macro/nic.csv", "index_b2015")
    nrate = {y: (ni[y] / ni[y - 1] - 1) * 100 for y in ni if y - 1 in ni}
    _natl(ctx, ax, sorted(nrate), [nrate[y] for y in sorted(nrate)],
          p.NAVY, "NIC, national index (base 2015 years only)")
    ig.add_recessions(ax, label=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(-8, 4), ha="right",
                fontsize=8.8, fontweight="bold", color=p.ROSSO)
    _note(p, ax, 0.02, 0.96, "the dotted target is the euro-area 2%; the NIC "
          "line starts in 2017\nbecause the 2006–15 years live on older "
          "bases, still pending at ISTAT —\nno rate is ever computed across "
          "the 2026 rebase", size=7.4)
    # The shared inflation range is deliberately tall enough for Argentina;
    # Italy's lines sit near the floor, so the legend belongs above them.
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _foot(p, ax, "HICP is the spine's line; ISTAT's NIC runs beside it, "
          "0.1–0.6 points lower in 2022–23")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    uy, uv = _yr(ctx, "macro/unemployment_istat.csv", "unemp_rate_avg")
    ctx.line(ax, uy, uv, p.NAVY, label="ISTAT labour survey (backcast to 2006)")
    ey, ev = _yr(ctx, "macro/unemployment_estat.csv", "estat")
    _natl(ctx, ax, ey, ev, p.GOLD, "Eurostat (2009+)")
    ig.add_recessions(ax, label=False)
    peak = max(zip(uy, uv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(6, 2), ha="left",
                fontsize=8.8, fontweight="bold", color=p.NAVY)
    _note(p, ax, 0.02, 0.96, f"one series from 2006: ISTAT backcast the "
          f"post-2021 regulation;\nEurostat starts in 2009 and sits within "
          f"0.1 point — {uv[-1]:.1f}% vs {ev[-1]:.1f}% in {uy[-1]}")
    ax.legend(loc="lower right", fontsize=7.6, frameon=False)
    _foot(p, ax, "the national line leads because it covers the whole window; "
          "the harmonised line adds nothing visible")
    _finish(ctx, ig)


# ------------------------------------------------------------------- fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure "
                 "(% of GDP)")
    ry, rv = _yr(ctx, "fiscal/revenue.csv", "revenue")
    ey, ev = _yr(ctx, "fiscal/revenue.csv", "expenditure")
    ctx.line(ax, ry, rv, p.VERDE, label="Revenue")
    ctx.line(ax, ey, ev, p.ROSSO, label="Expenditure")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "superbonus", dy=0.05)
    ax.annotate(f"{_at(ey, ev, 2020):.1f}% in 2020", (2020, _at(ey, ev, 2020)),
                textcoords="offset points", xytext=(4, 4), ha="left",
                fontsize=8.4, fontweight="bold", color=p.ROSSO)
    _note(p, ax, 0.02, 0.96, f"revenue never moved: {rv[0]:.0f}–{max(rv):.0f}% of GDP "
          "all window.\nthe crisis is always on the spending side")
    ax.legend(loc="center right", fontsize=7.8, frameon=False)
    _foot(p, ax, "Eurostat EDP, general government — the Maastricht aggregates "
          "RGS computes; the BDAP endpoint never answered (meta.pending)")

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    dy_, dv = _yr(ctx, "fiscal/deficit.csv", "deficit")
    ctx.bars(ax, dy_, dv, lambda v: p.ROSSO if v < 0 else p.VERDE)
    py, pv = _yr(ctx, "fiscal/deficit.csv", "primary")
    ctx.line(ax, py, pv, p.NAVY, label="Primary balance")
    _barkey(ax, p.ROSSO, "Overall balance")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "superbonus", dy=0.05)
    sb = ", ".join(f"{_at(dy_, dv, y):.1f}" for y in (2021, 2022, 2023))
    _note(p, ax, 0.02, 0.96, f"the primary balance was positive all through "
          "the 2010s;\nthe 2021–23 deficits (" + sb + ") are the building "
          "bonuses,\nrecorded as expenditure when the work is done", size=7.4)
    ax.legend(loc="lower left", fontsize=7.8, frameon=False)
    _foot(p, ax, "Eurostat EDP; check the EDP notification notes before "
          "quoting the Superbonus years (DATA_NOTES)")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    qy, qv = _yr(ctx, "fiscal/debt.csv", "gross_pct_gdp")
    ctx.line(ax, qy, qv, p.ROSSO)
    ig.add_recessions(ax, label=False)
    pk = max(zip(qy, qv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(-6, 4), ha="right", fontsize=8.8, fontweight="bold",
                color=p.ROSSO)
    bn = _map(ctx, "fiscal/debt.csv", "gross_eurbn_q4")
    _note(p, ax, 0.02, 0.04, f"the ratio peaked at {pk[1]:.1f}% in {pk[0]}; "
          f"the stock crossed\nEUR 3 trillion in 2025 "
          f"({bn[2025]:,.1f}bn at Q4) while the ratio fell "
          f"to {qv[-1]:.1f}%", size=7.6, va="bottom")
    ctx.endlabel(ax, qy, qv, p.ROSSO, lambda v: f"{v:.1f}%", dy=8)
    _foot(p, ax, "Eurostat EDP government debt, Maastricht definition")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    iy, iv = _yr(ctx, "fiscal/deficit.csv", "interest")
    ctx.line(ax, iy, iv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{_at(iy, iv, 2012):.1f}% in 2012", (2012, _at(iy, iv, 2012)),
                textcoords="offset points", xytext=(0, 6), ha="center",
                fontsize=8.6, fontweight="bold", color=p.GOLD)
    _note(p, ax, 0.02, 0.96, f"never below {min(iv):.1f}% of GDP in any year of "
          f"the window;\n{iv[-1]:.1f}% in {iy[-1]} — interest, not the "
          "deficit, is the burden", size=7.6)
    ctx.endlabel(ax, iy, iv, p.GOLD, lambda v: f"{v:.1f}%", dy=8)
    _foot(p, ax, "Eurostat EDP, D41PAY interest expenditure")
    _finish(ctx, ig)


# ----------------------------------------------------------------- spending
COFOG7 = [
    ("Social protection", ["social_protection"], "VERDE"),
    ("Health", ["health"], "ROSSO"),
    ("Education", ["education"], "BLUE"),
    ("General public services", ["general_services"], "NAVY"),
    ("Economic affairs", ["economic_affairs"], "GOLD"),
    ("Defence + public order", ["defence_order"], "PURPLE"),
    ("Other", ["other"], "TEAL"),
]


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    C = "fiscal/spending_by_function.csv"
    t = ctx.table(C)
    yrs = [y for y in t["year"] if y >= W0 and y <= 2024]  # COFOG ends 2024

    def group(cols):
        return [sum(t[c][t["year"].index(y)] for c in cols) for y in yrs]

    ax = ig.slot("spending.by_function", "Spending by function, general "
                 "government (% of GDP)")
    layers = [(name, group(cols), getattr(p, col)) for name, cols, col in COFOG7]
    ax.stackplot(yrs, *[v for _, v, _ in layers],
                 labels=[n for n, _, _ in layers],
                 colors=[c for _, _, c in layers], alpha=0.9, lw=0)
    _bands_labelled_at(ig, ax, 0.78, p)
    ax.legend(loc="upper left", fontsize=7.0, ncol=4, frameon=False)
    oth = dict(zip(yrs, group(["other"])))
    ax.annotate(f"“other” {oth[2023]:.1f}% in 2023", (2023, sum(
        l[1][yrs.index(2023)] for l in layers)),
        textcoords="offset points", xytext=(0, 10), ha="center", va="bottom",
        fontsize=8.2, fontweight="bold", color=p.INK)
    _note(p, ax, 0.02, 0.70, "Eurostat COFOG, to 2024. the 2021–23 bump in "
          "“other” (housing)\nis the building bonuses — see the fiscal plate",
          size=7.4)

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    sp = group(["social_protection"])
    tot = group(["total"])
    rest = [tot[i] - sp[i] for i in range(len(yrs))]
    ctx.line(ax, yrs, rest, p.NAVY, label="Everything else")
    ctx.line(ax, yrs, sp, p.ROSSO, label="Social protection")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    ax.annotate(f"{sp[yrs.index(2020)]:.1f}% in 2020", (2020, sp[yrs.index(2020)]),
                textcoords="offset points", xytext=(-8, -14), ha="right",
                fontsize=8.4, fontweight="bold", color=p.ROSSO)
    _note(p, ax, 0.98, 0.04, f"pensions carry it: Italy's oldest money",
          ha="right", va="bottom", size=7.6)
    _foot(p, ax, "Eurostat COFOG; total outlays run a shade below the "
          "expenditure line on the fiscal plate")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(GFCF, % of GDP)")
    iy, iv = _yr(ctx, "fiscal/investment.csv", "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.BLUE)
    ig.add_recessions(ax, label=False)
    trough = min(zip(iy, iv), key=lambda t: t[1])
    ax.annotate(f"{trough[1]:.1f}% in {trough[0]}", trough,
                textcoords="offset points", xytext=(4, -10), ha="left",
                fontsize=8.4, fontweight="bold", color=p.BLUE)
    _note(p, ax, 0.02, 0.96, f"{iv[0]:.1f}% in {iy[0]} down to "
          f"{trough[1]:.1f}% in {trough[0]}:\nthe investment rate fell through "
          "the euro crisis and back", size=7.6)
    _foot(p, ax, "Eurostat national accounts, P51G general government total "
          "economy basis")

    ax = ig.slot("spending.public_investment", "Public investment "
                 "(government GFCF, % of GDP)")
    gy, gv = _yr(ctx, "fiscal/investment.csv", "gov_gfcf_pct_gdp")
    ctx.line(ax, gy, gv, p.TEAL)
    ig.add_recessions(ax, label=False)
    low = min(zip(gy, gv), key=lambda t: t[1])
    ax.annotate(f"{low[1]:.1f}% in {low[0]}", low, textcoords="offset points",
                xytext=(0, -14), ha="center", va="top", fontsize=8.4,
                fontweight="bold", color=p.TEAL)
    _mark(ig, ax, "pnrr", dy=0.72)
    _note(p, ax, 0.02, 0.96, f"the state itself spends only ~{gv[0]:.0f}% of GDP; "
          f"it fell to {low[1]:.1f}%\nand is climbing back in the PNRR years "
          f"({gv[-1]:.1f}% in {gy[-1]})", size=7.6)
    ctx.endlabel(ax, gy, gv, p.TEAL, lambda v: f"{v:.1f}%", dy=8)
    _foot(p, ax, "Eurostat EDP P51G, general government")
    _finish(ctx, ig)


# -------------------------------------------------------------------- trade
def plate_trade(ctx, ig) -> None:
    p = ctx.p
    gdp = _map(ctx, "macro/gdp_estat.csv", "nominal_eurbn")
    x = _map(ctx, "trade/trade.csv", "exports_eurbn")
    m = _map(ctx, "trade/trade.csv", "imports_eurbn")
    xpc = {y: x[y] / gdp[y] * 100 for y in x if y in gdp}
    mpc = {y: m[y] / gdp[y] * 100 for y in m if y in gdp}
    bal = {y: (x[y] - m[y]) / gdp[y] * 100 for y in x if y in gdp}

    ax = ig.slot("trade.exports_imports", "Exports and imports (% of GDP)")
    ctx.line(ax, sorted(xpc), [xpc[y] for y in sorted(xpc)], p.VERDE,
             label="Exports, goods and services")
    ctx.line(ax, sorted(mpc), [mpc[y] for y in sorted(mpc)], p.ROSSO,
             label="Imports, goods and services")
    wy, wv = _yr(ctx, "international/openness.csv", "trade_pct_gdp")
    _natl(ctx, ax, wy, wv, p.NAVY, "World Bank (X+M)/GDP, older vintage")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)
    _note(p, ax, 0.98, 0.03, f"the 2022–23 rows are inflated by imported "
          f"energy prices:\nimports peaked at {mpc[2022]:.0f}% of GDP "
          f"({m[2022]:,.0f}bn)", size=7.6, ha="right", va="bottom")
    _foot(p, ax, "Eurostat national accounts P6/P7 over GDP; the World Bank "
          "openness series carries the pre-2026 vintage")

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    ctx.bars(ax, sorted(bal), [bal[y] for y in sorted(bal)],
             lambda v: p.VERDE if v >= 0 else p.ROSSO)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{bal[2019]:+.1f}% in 2019", (2019, bal[2019]),
                textcoords="offset points", xytext=(0, 6), ha="center",
                fontsize=8.4, fontweight="bold", color=p.VERDE)
    _note(p, ax, 0.02, 0.96, f"a structural goods surplus turned against "
          f"energy:\n{bal[2013]:+.1f}% in 2013, {bal[2022]:+.1f}% in 2022",
          size=7.6)
    _foot(p, ax, "computed from the same P6/P7 and GDP columns — goods and "
          "services, never customs")

    ax = ig.slot("trade.destinations", "Top export destinations (% of goods exports)")
    ctx.pending(ax)
    _foot(p, ax, "a comparable annual partner series is not staged; the "
          "reviewed 2023 customs snapshot is retained in the lens")

    ax = ig.slot("trade.lens", "Top export destinations, 2023 "
                 "(% of goods exports)", unit=False)
    destinations_ax = ax
    partners = [r for r in _records(ctx, "trade/trade_comtrade_partner.csv")
                if r["flow"] == "X" and r["partner"] != "World"]
    partners.sort(key=lambda r: float(r["share_of_flow_pct"]), reverse=True)
    short = {"United States": "US", "United Kingdom": "UK"}
    names = [short.get(r["partner"], r["partner"]) for r in partners[:8]]
    values = [float(r["share_of_flow_pct"]) for r in partners[:8]]
    positions = list(range(len(names)))
    ax.bar(positions, values, color=p.ROSSO, alpha=0.88)
    _foot(p, ax, "UN Comtrade 2023; Italy reporter, customs goods; "
          "World-total shares")
    _finish(ctx, ig)
    # This panel is a one-year categorical snapshot. The shared spine still
    # controls its 0–40% y scale; replace the time-axis defaults with partner
    # labels only after the common styling pass.
    destinations_ax.set_xlim(-0.6, len(names) - 0.4)
    destinations_ax.set_xticks(positions, names, fontsize=6.8)


# ------------------------------------------------------------------ markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    dy_, dv = _yr(ctx, "markets/policy_rate.csv", "dfr")
    ctx.line(ax, dy_, dv, p.NAVY, label="ECB deposit facility rate, year-end")
    cy, cv = _yr(ctx, "macro/hicp.csv", "hicp")
    ctx.line(ax, cy, cv, p.ROSSO, label="HICP (from the economy plate)")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "wit", dy=0.55)
    _note(p, ax, 0.02, 0.96, "the rate is set in Frankfurt for the whole "
          f"euroarea:\nzero 2019–22, then hikes, and {dv[-1]:.2f}% live in "
          "2026 after the ECB\nmoved up again while inflation sat near 2%",
          size=7.4)
    ax.legend(loc="center right", fontsize=7.6, frameon=False)
    _foot(p, ax, "ECB DFR at year-end (the MRO twin runs beside it in the "
          "credit plate); HICP via Eurostat")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    yy, yv = _yr(ctx, "markets/yield_10y.csv", "yield_10y")
    ctx.line(ax, yy, yv, p.ROSSO)
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "monti", dy=0.66)
    _mark(ig, ax, "wit", dy=0.80)
    peak = max(zip(yy, yv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, "the 2011–12 peak is the spread crisis: the "
          "yield Italy pays,\nnot the rate Germany does; OMT after July 2012 "
          "broke it", size=7.6)
    _note(p, ax, 0.98, 0.78, f"{peak[1]:.2f}% in {peak[0]}",
          ha="right", size=8.0, color=p.ROSSO)
    ctx.endlabel(ax, yy, yv, p.ROSSO, lambda v: f"{v:.1f}%", dy=8)
    _foot(p, ax, "Eurostat irt_lt_mcby_a, equal to the ECB's monthly IRS to "
          "0.01 in every year")

    ax = ig.slot("markets.currency", "Currency against the US$ "
                 "(index 2006 = 100)")
    fx = _map(ctx, "markets/eurusd.csv", "avg")
    iy, iv = ctx.index_2006(fx)
    ctx.line(ax, iy, iv, p.BLUE)
    ig.add_recessions(ax, label=False)
    trough = min(zip(iy, iv), key=lambda t: t[1])
    ax.annotate(f"{trough[1]:.0f} in {trough[0]}", trough,
                textcoords="offset points", xytext=(4, -10), ha="left",
                fontsize=8.4, fontweight="bold", color=p.BLUE)
    _note(p, ax, 0.02, 0.05, "Italy's currency is the euro: this is the whole "
          "euroarea's line,\nshared with France, Spain and Germany — the "
          "lira left the board\nin 1999, before this window opens", size=7.4,
          va="bottom")
    ctx.endlabel(ax, iy, iv, p.BLUE, lambda v: f"{v:.0f}", dy=8)
    _foot(p, ax, "ECB annual mean USD per EUR, indexed 2006 = 100 (up = the "
          "euro stronger)")

    ax = ig.slot("markets.equities", "Main equity index in US$ "
                 "(index 2006 = 100)")
    ft = _map(ctx, "markets/ftsemib.csv", "close")
    usd = {y: ft[y] * fx[y] for y in ft if y in fx}
    ey, ev = ctx.index_2006(usd)
    ctx.line(ax, ey, ev, p.GOLD)
    ig.add_recessions(ax, label=False)
    trough = min(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{trough[1]:.0f} in {trough[0]}", trough,
                textcoords="offset points", xytext=(4, -10), ha="left",
                fontsize=8.4, fontweight="bold", color=p.GOLD)
    _note(p, ax, 0.02, 0.96, f"the Milan market lost 60% of its dollar value "
          f"by {trough[0]};\nthe S&P 500 dashed comparator is not staged yet "
          "(meta.pending)", size=7.6)
    ctx.endlabel(ax, ey, ev, p.GOLD, lambda v: f"{v:.0f}", dy=8)
    _foot(p, ax, "FTSE MIB year-end closes (Yahoo, official: false) × ECB mean "
          "rate; dividends excluded")
    _finish(ctx, ig)


# ------------------------------------------------------------------- credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p
    ln = _map(ctx, "credit/household_debt.csv", "loans_eurbn")
    gdp = _map(ctx, "macro/gdp_estat.csv", "nominal_eurbn")
    debt_gdp = {y: ln[y] / gdp[y] * 100 for y in ln if y in gdp}

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    ctx.line(ax, sorted(debt_gdp), [debt_gdp[y] for y in sorted(debt_gdp)],
             p.VERDE, label="BdI loans ÷ Eurostat GDP")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"households are levered, not wildly: "
          f"{min(debt_gdp.values()):.0f}–{max(debt_gdp.values()):.0f}% of GDP. "
          f"the spine's\nBIS series is not staged; the same loans over GDP "
          f"read {debt_gdp[2024]:.1f}\nagainst BIS 36.0 and Eurostat 36.1 "
          f"for 2024 (DATA_NOTES)", size=7.4)
    ctx.endlabel(ax, sorted(debt_gdp), [debt_gdp[y] for y in sorted(debt_gdp)],
                 p.VERDE, lambda v: f"{v:.0f}%", dy=8)
    _foot(p, ax, "Banca d'Italia financial accounts (F41+F42, Q4) ÷ Eurostat "
          "GDP — harmonised-basis substitute, labelled as such")

    ax = ig.slot("credit.lending_rate", "Household lending rate vs policy "
                 "rate (%)")
    ry, rv = _yr(ctx, "credit/lending_rate.csv", "house_new_avg")
    ctx.line(ax, ry, rv, p.ROSSO, label="New mortgage rate (BdI, MIR)")
    dy_, dv = _yr(ctx, "markets/policy_rate.csv", "dfr")
    ctx.line(ax, dy_, dv, p.NAVY, label="ECB deposit rate, year-end")
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{_at(ry, rv, 2023):.2f}% in 2023", (2023, _at(ry, rv, 2023)),
                textcoords="offset points", xytext=(-4, 6), ha="right",
                fontsize=8.2, fontweight="bold", color=p.ROSSO)
    _note(p, ax, 0.02, 0.96, "new-borrower rates track Frankfurt with a "
          "two-year lag;\nvariable-rate mortgages pass the hike through "
          "fast", size=7.6)
    ax.legend(loc="center right", fontsize=7.6, frameon=False)
    _foot(p, ax, "Banca d'Italia MIR annual means; 2026 is eight months of "
          "new lending")

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    ny, nv = _yr(ctx, "credit/npl.csv", "npl_gross_ratio_fsi")
    ctx.line(ax, ny, nv, p.ROSSO, label="Gross NPL ratio (IMF FSI, 2011+)")
    by, bv = _yr(ctx, "credit/npl.csv", "bad_loans_ratio_computed",
                 until=2023)
    _natl(ctx, ax, by, bv, p.NAVY, "sofferenze ratio (BdI, ended Mar 2024)")
    ig.add_recessions(ax, label=False)
    peak = max(zip(ny, nv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(-6, 4), ha="right",
                fontsize=8.8, fontweight="bold", color=p.ROSSO)
    _note(p, ax, 0.55, 0.98, f"the bank clean-up of 2015–17 cut bad debt from "
          f"{peak[1]:.1f}%\nto {nv[-1]:.1f}%. the FSI ratio predates the 2015 "
          "EBA definition;\nthe 2024 mixed row of the discontinued series is "
          "not drawn", size=7.2)
    ax.legend(loc="center right", fontsize=7.4, frameon=False)
    _foot(p, ax, "IMF FSI gross NPL ratio (harmonised) with BdI's sofferenze "
          "beside it (national, gross) — never joined")

    ax = ig.slot("credit.lens", "Lens — the same debt against disposable "
                 "income")
    gy, gv = _yr(ctx, "credit/household_debt.csv",
                 "debt_pct_gdi_computed")
    ctx.line(ax, gy, gv, p.VERDE)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.50, 0.03, f"loans divided by household disposable income\n"
          f"rather than GDP: {gv[0]:.1f}% to {max(gv):.1f}%, back to "
          f"{gv[-1]:.1f}%.\nthe numerator is BdI's, the denominator is\n"
          "Eurostat's B6G S14_S15 — one _computed\ncolumn, never joined with "
          "the GDP ratio", size=7.4, va="bottom")
    ctx.endlabel(ax, gy, gv, p.VERDE, lambda v: f"{v:.0f}%", dy=8)
    _foot(p, ax, "the denominator Italy argues about: households feel income, "
          "not GDP (BdI FSR reads 56.1 for 2024)")
    _finish(ctx, ig)


# ------------------------------------------------------------------- people
def plate_people(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100)")
    gy, gv = _yr(ctx, "social/gini_estat.csv", "silc")
    ctx.line(ax, gy, gv, p.VERDE, label="EU-SILC via Eurostat (Italy from 2014)")
    wy, wv = _yr(ctx, "social/gini_wb.csv", "gini")
    _natl(ctx, ax, wy, wv, p.NAVY, "World Bank SILC cut — never joined")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"one survey, two readings: the Bank runs "
          f"{wv[wy.index(2023)] - gv[gy.index(2023)]:.1f} points above "
          f"Eurostat in 2023;\nItaly stays mid-pack for Europe and the gap "
          "never closes — draw\nboth, label both, splice neither", size=7.4)
    ax.legend(loc="lower left", fontsize=7.4, frameon=False)
    _foot(p, ax, "Eurostat ilc_di12 (2014 onward for Italy) and the World "
          "Bank's own definition of the same survey")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    ay, av = _yr(ctx, "social/poverty.csv", "arop60")
    ctx.line(ax, ay, av, p.VERDE, label="At risk after transfers, 60% median "
                "(EU-SILC)")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, "two different ideas of poor: the EU's relative "
          f"line ({av[-1]:.1f}%); household-based national measures stay "
          "in the lens.\nThe World Bank's US$8.30 line is not computed for "
          "Italy, so it is not drawn (meta.pending)",
          size=7.4)
    ax.legend(loc="center", fontsize=7.4, frameon=False)
    _foot(p, ax, "Eurostat ilc_li02, persons on the survey-year axis")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    ctx.pending(ax)
    _foot(p, ax, "no gap: Italy has no statutory minimum wage. pay floors "
          "come from sector collective agreements (CCNL) — the spine's "
          "honest statement")

    ax = ig.slot("people.lens", "Lens — two poverty lines, one country")
    ay, av = _yr(ctx, "social/poverty.csv", "arop60")
    ctx.line(ax, ay, av, p.VERDE, label="At-risk-of-poverty, persons (EU-SILC)")
    ry, rv = _yr(ctx, "social/poverty_abs.csv", "rel_hh")
    _natl(ctx, ax, ry, rv, p.ROSSO, "ISTAT relative poverty, households")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.98, 0.55, "the national relative line (equivalence-scale "
          f"families) swings\n{min(rv):.1f}–{max(rv):.1f}% while the EU's "
          f"person line sits near {av[-1]:.0f}%:\nthe same Italian "
          "families, counted differently", size=7.4, ha="right")
    ax.legend(loc="center left", fontsize=7.4, frameon=False)
    _foot(p, ax, "EU-SILC persons against ISTAT's household family-unit basis "
          "(34_727); both full window they cover")
    _finish(ctx, ig)


# -------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "international/gdp_usd.csv", "gdp_usd")
    gv = [v / 1e9 for v in gv]
    ctx.line(ax, gy, gv, p.VERDE)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.30, f"US${gv[-1]:,.0f}bn in {gy[-1]} — still the "
          "euroarea's second economy,\nbut the Bank's vintage predates "
          "ISTAT's 2026 revision, which\ntakes 2025 to EUR 2,265bn on the "
          "national side", size=7.4)
    ctx.endlabel(ax, gy, gv, p.VERDE, lambda v: f"US${v:,.0f}bn", dy=8)
    _foot(p, ax, "World Bank NY.GDP.MKTP.CD, current US$ at market rates")

    ax = ig.slot("world.hdi", "Human Development Index (0–1)")
    hy, hv = _yr(ctx, "international/hdi.csv", "hdi", until=2023)
    ctx.line(ax, hy, hv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{hv[-1]:.3f} in {hy[-1]}: very-high band", (hy[-1], hv[-1]),
                textcoords="offset points", xytext=(-14, 6), ha="right",
                fontsize=8.4, fontweight="bold", color=p.BLUE)
    _note(p, ax, 0.02, 0.30, "flat since 2010 — the HDR-2025 vintage ends at "
          "2023;\nincome does the moving, and Italy's income did not",
          size=7.6)
    _foot(p, ax, "UNDP HDR 2025; 0.800 and above = very high human development")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (score, 0–100)")
    cy, cv = _yr(ctx, "international/cpi.csv", "score")
    ctx.line(ax, cy, cv, p.PURPLE)
    ctx.endlabel(ax, cy, cv, p.PURPLE, lambda v: f"{v:.0f}", dy=8)
    _foot(p, ax, "Transparency International CPI 2025 workbook; comparable "
          "2012 method onward")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn)")
    ry, rv = _yr(ctx, "international/reserves.csv", "reserves_usd")
    rv = [v / 1e9 for v in rv]
    ctx.line(ax, ry, rv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"US${rv[-1]:,.0f}bn in {ry[-1]}", (ry[-1], rv[-1]),
                textcoords="offset points", xytext=(-14, 4), ha="right",
                fontsize=8.6, fontweight="bold", color=p.GOLD)
    _note(p, ax, 0.02, 0.96, f"the 2025 jump, {rv[-2]:,.0f} to {rv[-1]:,.0f}bn, "
          "is the gold price on Italy's\n~2,450 tonnes — not purchases. the "
          "union's buffer is the\nECB's; national reserves are what the "
          "Bank of Italy holds", size=7.4)
    _foot(p, ax, "World Bank FI.RES.TOTL.DT (total reserves, gold valued at "
          "market)")
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p
    D = "social/demography.csv"
    pop = _pop(ctx)

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    iy, iv = ctx.index_2006(pop)
    ctx.line(ax, iy, iv, p.VERDE)
    ig.add_recessions(ax, label=False)
    pk = max(zip(iy, iv), key=lambda t: t[1])
    ax.annotate(f"peak {pk[1]:.1f} in {pk[0]}", pk, textcoords="offset points",
                xytext=(6, -22), ha="left", fontsize=8.4, fontweight="bold",
                color=p.VERDE)
    _note(p, ax, 0.02, 0.96, f"58,943,464 on 1 Jan 2025 (Eurostat = ISTAT to "
          f"the person);\n2026 is ISTAT's estimate. the peak is {pk[0]} and "
          "the line\nhas fallen since — an ageing decline, not a shock", size=7.6)
    ctx.endlabel(ax, iy, iv, p.VERDE, lambda v: f"{v:.1f}", dy=8)
    _foot(p, ax, "Eurostat demo_gind; ISTAT's post-census flow 22_289 confirms "
          "2019 onward")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    ty, tv = _yr(ctx, D, "tfr", until=2024)
    ctx.line(ax, ty, tv, p.ROSSO)
    ax.axhline(2.1, color=p.VERDE_D, lw=1.0, ls=":", zorder=2)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"the window's headline: 1.37 to "
          f"{tv[-1]:.2f} — the line on the way down\ncrosses 1.25 in 2020 and "
          f"keeps falling; replacement (2.1) is never\nin sight. ISTAT's "
          "split by mother's citizenship is still pending", size=7.6)
    ctx.endlabel(ax, ty, tv, p.ROSSO, lambda v: f"{v:.2f}", dy=8)
    _foot(p, ax, "Eurostat demo_find; the 2025 provisional (ISTAT) agrees the "
          "direction but is not drawn")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    b = _map(ctx, D, "births")
    d = _map(ctx, D, "deaths")
    by, bv = ctx.per_1000(b, {y: pop[y] for y in b})
    dy_, dv = ctx.per_1000(d, {y: pop[y] for y in d})
    ctx.line(ax, by, bv, p.VERDE, label="Births")
    ctx.line(ax, dy_, dv, p.ROSSO, label="Deaths")
    ig.add_recessions(ax, label=False)
    cross = next(y for y in sorted(b) if b[y] < d[y])
    _note(p, ax, 0.02, 0.96, f"the lines cross in {cross} and never meet "
          f"again:\n{b[2008]:,.0f} births in 2008 against {b[2025]:,.0f} in "
          "2025 — a third of\nthe children, gone in a generation "
          "(2025 provisional)", size=7.6)
    ax.legend(loc="lower left", fontsize=7.8, frameon=False)
    _foot(p, ax, f"demo_gind counts ÷ the same file's 1-January population: "
          f"CBR 2024 {b[2024]/pop[2024]*1000:.2f}, CDR {d[2024]/pop[2024]*1000:.2f} "
          "per 1,000")

    ax = ig.slot("demography.natural_migration", "Natural increase and net "
                 "migration (per 1,000 people)")
    n = {y: (b[y] - d[y]) for y in b if y in d}
    ny, nv = ctx.per_1000(n, {y: pop[y] for y in n})
    imm = _map(ctx, "migration/immigration.csv",
               "by_citizenship_total")
    emi = _map(ctx, "migration/emigration.csv",
               "by_citizenship_total")
    net = {y: imm[y] - emi[y] for y in imm if y in emi and emi[y]}
    my, mv = ctx.per_1000(net, {y: pop[y] for y in net})
    ctx.line(ax, ny, nv, p.ROSSO, label="Natural increase")
    ctx.line(ax, my, mv, p.VERDE, label="Net migration (Eurostat, to 2024)")
    ig.add_recessions(ax, label=False)
    fl = _map(ctx, "migration/migration_flows.csv", "balance")
    ax.annotate(f"ISTAT 2025: {fl[2025]:+,.0f} people", (2025, mv[-1]),
                textcoords="offset points", xytext=(-4, 8), ha="right",
                fontsize=8.2, fontweight="bold", color=p.VERDE)
    _note(p, ax, 0.02, 0.96, "births stop paying for deaths on these series "
          f"from {next(y for y in sorted(b) if b[y] < d[y])};\nnet migration "
          f"(~{mv[-1]:.1f}‰) no longer covers the natural deficit "
          f"({nv[-1]:.1f}‰ in {ny[-1]}). Italy is\nshrinking without meaning to",
          size=7.6)
    ax.legend(loc="lower left", fontsize=7.8, frameon=False)
    _foot(p, ax, "same population denominator; Eurostat flows stop 2024, "
          "ISTAT 2025 quoted as a number")
    _finish(ctx, ig)


# ----------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    pop = _pop(ctx)

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    py, pv = _yr(ctx, "security/homicide_police.csv",
                 "intenhom_per100k")
    ctx.line(ax, py, pv, p.ROSSO, label="Police count, ISTAT's published rate")
    a = _map(ctx, "security/homicide_vital.csv", "assault_deaths")
    ay, av = ctx.per_100k(a, {y: pop[y] for y in a})
    _natl(ctx, ax, ay, av, p.NAVY, "Death certificates, computed")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, "two counts, never spliced: police record more in "
          f"every year\n(2023: {_map(ctx, 'security/homicide_police.csv', 'intenhom')[2023]:,.0f} "
          f"against {a[2023]:,.0f}); Italy's true story is the steady fall, "
          "halving\nacross the window — organised crime included", size=7.4)
    ax.legend(loc="lower left", fontsize=7.4, frameon=False)
    _foot(p, ax, "ISTAT 73_67 (Ministero dell'Interno data) and 39_494 "
          "certificates; UNODC is not staged")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    s = _cause(ctx, "17_2")
    sy, sv = ctx.per_100k(s, {y: pop[y] for y in s})
    ctx.line(ax, sy, sv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, f"flat, and never mentioned: {min(sv):.1f}–"
          f"{max(sv):.1f} per 100,000 every year\nto 2023, the certificates' "
          "end. it is the largest violent-death\ncategory on the panel by a "
          "wide margin", size=7.6)
    ctx.endlabel(ax, sy, sv, p.PURPLE, lambda v: f"{v:.1f}", dy=8)
    _foot(p, ax, "ISTAT death certificates, European shortlist code 17_2 ÷ "
          "the 1-January population")

    ax = ig.slot("security.road_deaths", "Road traffic deaths (per 100,000)")
    ctx.pending(ax)
    _note(p, ax, 0.50, 0.96, "the road-only series is not staged; the available "
          "death-certificate series covers all transport modes and is kept "
          "out of this comparable slot", ha="center", size=7.4)
    _foot(p, ax, "ISTAT 30-day road deaths or Eurostat tran_sf_roadus pending; "
          "no all-transport proxy drawn")

    ax = ig.slot("security.lens", "Lens — mafia and attempted homicides")
    ctx.pending(ax)
    _note(p, ax, 0.50, 0.96, "the story slot is organised-crime homicide, and "
          "ISTAT's\ncolumns (73_67 MAFFIAHOM/ATTEMPHOM) are still "
          "pending —\nthe key is pinned in the fetcher", ha="center", size=7.4)
    _foot(p, ax, "nothing else is drawn here")
    _finish(ctx, ig)


# ---------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    pop = _pop(ctx)
    d = _map(ctx, "social/demography.csv", "deaths")

    ax = ig.slot("mortality.death_rate", "Crude death rate (per 1,000 people)")
    dy_, dv = ctx.per_1000(d, {y: pop[y] for y in d})
    ctx.line(ax, dy_, dv, p.ROSSO)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, "Italy's defining demographic fact: the death "
          f"line climbs from\n{dv[0]:.1f} to {dv[-1]:.1f} per 1,000 — age "
          "structure, not catastrophe; the 2020\nand 2022 bumps are on the "
          "panel next door", size=7.6)
    ctx.endlabel(ax, dy_, dv, p.ROSSO, lambda v: f"{v:.1f}", dy=8)
    _foot(p, ax, "Eurostat demo_gind register deaths (= ISTAT 26_29 exactly); "
          "certificates are a different count")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths (% above 2015–2019 "
                 "average)")
    base = sum(d[y] for y in range(2015, 2020)) / 5
    ex = {y: (d[y] / base - 1) * 100 for y in d}
    ctx.bars(ax, sorted(ex), [ex[y] for y in sorted(ex)],
             lambda v: p.ROSSO if v > 0 else p.VERDE)
    ig.add_recessions(ax, label=False)
    pk = max(zip(sorted(ex), [ex[y] for y in sorted(ex)]), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:+.1f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 4), ha="center", va="bottom", fontsize=8.8,
                fontweight="bold", color=p.ROSSO)
    _note(p, ax, 0.98, 0.80, "2020, the first Western lockdown country: "
          f"{ex[2020]:+.1f}% above\nthe 2015–19 mean; 2021–22 stayed hot "
          f"({ex[2021]:+.1f}%, {ex[2022]:+.1f}%),\nand ordinary flu years "
          "(2017, 2025) also print above zero", size=7.6, ha="right")
    _foot(p, ax, "computed from the register counts; the base is the plain "
          "2015–2019 mean, as the spine prescribes")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    c = _cause(ctx, "20")
    cy, cv = ctx.per_100k(c, {y: pop[y] for y in c})
    ctx.bars(ax, cy, cv, lambda v: p.ROSSO)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{cv[0]:.1f} in {cy[0]}", (cy[0], cv[0]),
                textcoords="offset points", xytext=(0, 4), ha="center",
                fontsize=8.8, fontweight="bold", color=p.ROSSO)
    _note(p, ax, 0.02, 0.96, f"{c[2020]:,.0f} with COVID as underlying cause "
          "in 2020 (certificate\ncount; the register's excess is larger). the "
          "shortlist carries\n20* codes only from 2020; 2023 is the staged "
          "end", size=7.6)
    _foot(p, ax, "ISTAT certificates, code 20 (identified + not identified), "
          "never summed with other codes")

    ax = ig.slot("mortality.lens", "Lens — who actually dies: the big killers "
                 "(per 100,000)")
    heart = _cause(ctx, "7")
    tumor = _cause(ctx, "2_1")
    dem = _cause(ctx, "5_1")
    for mp, col, lab in ((heart, p.ROSSO, "Circulatory diseases"),
                         (tumor, p.VERDE, "Malignant neoplasms"),
                         (dem, p.PURPLE, "Dementia")):
        ys, vs = ctx.per_100k(mp, {y: pop[y] for y in mp})
        ctx.line(ax, ys, vs, col, label=lab)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="center left", fontsize=7.4, frameon=False)
    _note(p, ax, 0.98, 0.42, f"the quiet reversal: circulatory deaths fall "
          f"from {heart[2006]/pop[2006]*100_000:.0f} to "
          f"{heart[2023]/pop[2023]*100_000:.0f};\ndementia climbs toward "
          f"{dem[2023]/pop[2023]*100_000:.0f} — the cardiology win and the "
          "ageing bill,\nboth written in the same certificates file", size=7.4,
          ha="right")
    _foot(p, ax, "codes 7, 2_1, 5_1 of the same nested shortlist — peers on "
          "this panel, not a sum")
    _finish(ctx, ig)


# ---------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    pop = _pop(ctx)

    imm = _map(ctx, "migration/immigration.csv",
               "by_citizenship_total")
    emi = _map(ctx, "migration/emigration.csv",
               "by_citizenship_total")
    istat = ctx.rows("migration/migration_flows.csv") or {}
    ifl = {int(y): {k: float(r[k]) for k in
                    ("immigration", "emigration", "emigration_italian")
                    if (r.get(k) or "").strip()}
           for y, r in istat.items()}

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    ki = ctx.per_1000(imm, {y: pop[y] for y in imm})
    ke = ctx.per_1000({y: v for y, v in emi.items() if v},
                      {y: pop[y] for y in emi if emi[y]})
    ctx.line(ax, *ki, p.VERDE, label="Immigrants (Eurostat, to 2024)")
    ctx.line(ax, *ke, p.ROSSO, label="Emigrants (Eurostat, to 2024)")
    iy_ = [y for y in sorted(ifl) if "immigration" in ifl[y]]
    ey_ = [y for y in sorted(ifl) if "emigration" in ifl[y]]
    _natl(ctx, ax, iy_, [ifl[y]["immigration"] / pop[y] * 1000
                         for y in iy_], p.NAVY,
          "ISTAT register (to 2025)")
    _natl(ctx, ax, ey_, [ifl[y]["emigration"] / pop[y] * 1000
                         for y in ey_], p.GOLD,
          "ISTAT register (to 2025)")
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, "identical to the person in 2006–07 and 2011–24; "
          "Eurostat runs higher\nin 2008–10, the first Regulation years "
          "(+40,318 immigration in 2008) —\ntwo lines, one statistic, "
          "never spliced", size=7.4)
    ax.legend(loc="upper right", fontsize=7.0, frameon=False)
    _foot(p, ax, "Eurostat migr_imm1ctz / migr_emi1ctz (= migr_imm3ctb, the "
          "fetcher asserts it) and ISTAT 28_185")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    net = {y: imm[y] - emi[y] for y in imm if emi.get(y)}
    ny, nv = ctx.per_1000(net, {y: pop[y] for y in net})
    ctx.line(ax, ny, nv, p.VERDE, label="Eurostat, computed")
    bal = {y: ifl[y]["immigration"] - ifl[y]["emigration"]
           for y in sorted(ifl) if "immigration" in ifl[y]
           and "emigration" in ifl[y]}
    _natl(ctx, ax, *ctx.per_1000(bal, {y: pop[y] for y in bal}), p.NAVY,
          "ISTAT register, computed")
    ig.add_recessions(ax, label=False)
    low = min(zip(ny, nv), key=lambda t: t[1])
    ax.annotate(f"{low[1]:.1f} in {low[0]}", low, textcoords="offset points",
                xytext=(4, -10), ha="left", fontsize=8.2, fontweight="bold",
                color=p.VERDE)
    _note(p, ax, 0.02, 0.96, f"a positive flow every year, but thin after 2020; "
          f"ISTAT 2025:\n{bal[2025]:+,.0f} (439,916 in, 144,157 out) as "
          f"registration, not arrivals", size=7.6)
    _foot(p, ax, "the register's balance column needs no adjustment for the "
          "spine — but leaving needs no paperwork, and AIRE lags (DATA_NOTES)")

    ax = ig.slot("migration.foreign_born", "Foreign-born share of the "
                 "population (% of population)")
    stk = ctx.rows("migration/stock.csv") or {}
    fb = {int(y): float(r["by_birth_foreign"]) / float(r["by_birth_total"])
          * 100 for y, r in sorted(stk.items())
          if (r.get("by_birth_foreign") or "").strip() and int(y) >= W0}
    fc = {int(y): float(r["by_citizenship_foreign"]) / float(r["by_citizenship_total"])
          * 100 for y, r in sorted(stk.items())
          if (r.get("by_citizenship_foreign") or "").strip() and int(y) >= W0}
    ctx.line(ax, sorted(fb), [fb[y] for y in sorted(fb)], p.VERDE,
             label="Foreign-born")
    ctx.line(ax, sorted(fc), [fc[y] for y in sorted(fc)], p.ROSSO,
             label="Foreign citizens (FOR_STLS)")
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{fb[max(fb)]:.1f}% in {max(fb)}", (max(fb), fb[max(fb)]),
                textcoords="offset points", xytext=(-14, 8), ha="right",
                fontsize=8.4, fontweight="bold", color=p.VERDE)
    _note(p, ax, 0.02, 0.96, f"born elsewhere {fb[max(fb)]:.1f}%, holding another "
          f"passport {fc[max(fc)]:.1f}%:\nthe two lines pull apart because "
          f"naturalisation ({_map(ctx, 'migration/naturalisation.csv', 'acquisitions')[2024]:,.0f} "
          f"in 2024)\nmoves people from the green line to the red one",
          size=7.4)
    ax.legend(loc="center right", fontsize=7.6, frameon=False)
    _foot(p, ax, "Eurostat migr_pop1ctz / migr_res3ctb; the citizenship code "
          "is FOR_STLS — citizen=FOR returns an empty cube for Italy")

    ax = ig.slot("migration.lens", "Lens — citizenship churn: who leaves and "
                 "who acquires")
    acq = _map(ctx, "migration/naturalisation.csv", "acquisitions")
    ctx.line(ax, *ctx.per_1000(acq, {y: pop[y] for y in acq}), p.VERDE,
             label="New Italian citizens (Eurostat)")
    eit = {int(y): float(r["by_citizenship_national"]) for y, r in
           sorted(ctx.rows("migration/emigration.csv").items())
           if (r.get("by_citizenship_national") or "").strip()
           and int(y) >= W0}
    ctx.line(ax, *ctx.per_1000(eit, {y: pop[y] for y in eit}), p.ROSSO,
             label="Emigrants who are Italian citizens (Eurostat)")
    _natl(ctx, ax, [y for y in sorted(ifl) if "emigration_italian" in ifl[y]],
          [ifl[y]["emigration_italian"] / pop[y] * 1000
           for y in sorted(ifl) if "emigration_italian" in ifl[y]],
          p.NAVY, "ISTAT register")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.0, frameon=False)
    _note(p, ax, 0.98, 0.03, f"the AIRE line: citizens leaving, from about 1 to\n"
          f"3 per thousand, mostly young; registration\nlags the fact. the "
          f"peak of new citizenships was\n{max(acq.values()):,.0f} in "
          f"{max(acq, key=lambda y: acq[y])}. first permits (433,099 in 2025)\n"
          "and asylum (158,605 in 2024) stay out —\npermits are documents, "
          "not arrivals", size=7.2, ha="right", va="bottom")
    _foot(p, ax, "Eurostat migr_acq + migr_emi1ctz national split, and ISTAT "
          "28_185 Italian-citizen cancellations")
    _finish(ctx, ig)


# ------------------------------------------------------------------- plates
PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Italian Economy — Growth, Income, Prices and Jobs",
         subtitle="Eurostat's harmonised lines with ISTAT's own series "
                  "beside them: two publishers of the same national "
                  "accounts, agreeing.",
         source="Sources: Eurostat · ISTAT 163_156, 151_884, 167_747 · "
                "World Bank WDI",
         alt="Four panels on the Italian economy, 2006–2025. Real GDP fell "
             "5.3% in 2009 and 8.7% in 2020 and rebounded 9.2% in 2021 into "
             "a long stall near one percent; GDP per person read US$40,430 "
             "in 2024, still short of the US$40,829 of 2008; HICP inflation "
             "peaked at "
             "8.7% in 2022 with the national NIC near 8.1%; unemployment "
             "peaked at 12.8% in 2014 and stood near 6% in 2025, on one "
             "backcast ISTAT series from 2006."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — The Debt That Never Left",
         subtitle="General government on the Maastricht definition via the "
                  "EDP transmission: the same aggregates Ragioneria "
                  "Generale dello Stato computes.",
         source="Sources: Eurostat EDP (gov_10dd_edpt1, gov_10q_ggdebt)",
         alt="Four panels on Italian public finances. Expenditure reaches "
             "56.9% of GDP in 2020 while revenue never leaves its "
             "44–48% band; the 2021–23 deficits of −8.9, −8.1 and −7.1% of "
             "GDP carry the building bonuses; debt peaks at 154.7% of GDP "
             "in 2020, reads 136.7% in 2025, and crosses three trillion "
             "euro; interest paid runs 3.3–5.1% of GDP in every year."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Spending — Pensions First, Everything After",
         subtitle="COFOG by function to 2024; social protection is half the "
                  "budget problem, and the bonuses show up in “other”.",
         source="Sources: Eurostat COFOG · Eurostat national accounts",
         alt="Four panels on Italian public spending. Social protection "
             "leads the COFOG stack at 17–20% of GDP and the “other” group "
             "jumps to 6.1% in 2023 on the building bonuses; the whole-"
             "economy investment rate falls from 21.9% to about 18% in the "
             "crisis; public investment sinks to 2.2% of GDP and climbs "
             "back to 3.9% in 2025 in the PNRR years."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — An Export Country With an Energy Bill",
         subtitle="National-accounts goods and services beside a labelled "
                  "UN Comtrade customs-goods partner snapshot.",
         source="Sources: Eurostat P6/P7 · World Bank WDI · UN Comtrade",
         alt="Four panels on Italian trade. Exports run near 32% of GDP and "
             "imports peaked at 37% in 2022 on imported energy; the balance "
             "swung from about +3% of GDP in 2019 to −1.7% in 2022; Germany, "
             "the United States and France lead the 2023 customs destinations "
             "retained in the lens while the comparable annual destination "
             "series remains pending."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Markets — Frankfurt's Rate, Rome's Spread",
         subtitle="The policy rate belongs to the euroarea; what is "
                  "Italian is the bond yield, and the euro's line is "
                  "shared.",
         source="Sources: ECB · Eurostat · Yahoo Finance (FTSE MIB, "
                "official: false)",
         alt="Four panels on Italian markets. The ECB deposit rate fell to "
             "zero and back to 2.50% in 2026 while Italian HICP peaked at "
             "8.7%; the BTP ten-year yield peaked at 5.49% in 2012, at the "
             "height of the spread crisis; the euro indexed against the "
             "dollar bottomed near 84 in 2022 as the parity scare ran; the "
             "FTSE MIB in US dollars halved by 2012 and ends the window near "
             "its 2006 level."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — The Banks Cleaned House",
         subtitle="Household debt on the BIS basis via Eurostat numerators; "
                  "the NPL clean-up of 2015–17 is the arc of the decade.",
         source="Sources: Banca d'Italia (financial accounts, MIR, BDS) · "
                "IMF FSI · Eurostat",
         alt="Four panels on Italian household credit. Household debt runs "
             "35–45% of GDP; new mortgage rates went from 1.3% in 2020 to "
             "4.2% in 2023 behind the ECB cycle; gross non-performing loans "
             "peaked at 18.0% in 2015 and fell to 2.4% by 2025, with the "
             "discontinued sofferenze series beside them; against "
             "disposable income the same debt reads 64% at its 2020 peak."),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="People — Inequality, Poverty, and No Minimum Wage",
         subtitle="Person-based EU-SILC in the canonical slot, a labelled "
                  "household comparison in the lens, and "
                  "an explicit absence: Italy sets pay floors through "
                  "collective agreements.",
         source="Sources: Eurostat ILC · ISTAT 34_727 · World Bank",
         alt="Four panels on Italian incomes. The Gini reads 31.0 in 2025 "
             "on Eurostat's SILC, with the World Bank's reading 1.0–3.2 "
             "points higher before 2024 and no splice between; "
             "at-risk-of-poverty for people sits near 19%; the minimum-wage panel states "
             "that no statutory minimum exists; the lens panel contrasts "
             "the EU's relative line with ISTAT's relative households."),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="Italy Among the Others",
         subtitle="The dollar size, the development index, and reserves "
                  "that jumped when gold did.",
         source="Sources: World Bank WDI · UNDP HDR 2025 · Transparency International",
         alt="Four panels on Italy in the world. GDP in current US dollars "
             "hovers near two trillion, at 2.4 trillion in 2024 on the "
             "Bank's older vintage; the HDI reads 0.915 in 2023, flat for "
             "a decade; TI's comparable corruption index runs from 42 in "
             "2012 to 53 in 2025; reserves leapt from "
             "US$290bn to 434bn in 2025 on the gold price, not purchases."),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — The Birth Collapse",
         subtitle="The country's defining story: fewer births, more deaths, "
                  "and net migration no longer covering the difference.",
         source="Sources: Eurostat demo_gind, demo_find · ISTAT 22_289, "
                "25_74, 26_29",
         alt="Four panels on Italy's population. The index peaks in 2014 "
             "and declines to 58,943,464 in 2025; total fertility falls "
             "from 1.37 to 1.18 children per woman, the lowest in the "
             "staged series; crude birth and death rates cross in 2007 "
             "and never meet again, with births 6.0 and deaths 11.1 per "
             "1,000 in 2025; natural "
             "decrease reaches −5.0 per 1,000 while net migration runs "
             "near +3."),
    dict(id="10", slug="security", topic="security", builder=plate_security,
         title="Security — Homicide in Long Decline",
         subtitle="Two homicide counts that never cross, a flat suicide "
                  "line, and a pending slot for organised crime.",
         source="Sources: ISTAT 73_67 (Ministero dell'Interno via ISTAT) · "
                "ISTAT 39_494",
         alt="Four panels on violent and accidental death in Italy. The "
             "police-recorded homicide rate halves from 1.1 to 0.6 per 100,000 with "
             "the certificate count always lower and never spliced; "
             "suicide holds 6.1–6.5 per 100,000; road-only deaths remain "
             "pending rather than using the available all-transport proxy; "
             "the organised-crime homicide lens is also pending at ISTAT."),
    dict(id="11", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — Old Before Their Time",
         subtitle="The crude death rate's long climb, the 2020 excess, and "
                  "the cardiology-versus-dementia reversal.",
         source="Sources: Eurostat demo_gind · ISTAT 39_494 European "
                "shortlist",
         alt="Four panels on Italian mortality. The crude death rate rises "
             "from 9.6 to 11.1 per 1,000; excess deaths reach +16.4% in "
             "2020 against the 2015–19 average with 2021–22 still high; "
             "COVID-19 underlying-cause deaths are 131.5 per 100,000 in "
             "2020; circulatory deaths fall across the window while "
             "dementia climbs toward 41 per 100,000."),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — Arrivals, and the Citizens Who Leave",
         subtitle="One flow under two names that agree except in 2008–10; "
                  "the lens is Italy's own emigration, AIRE lagging.",
         source="Sources: Eurostat migration suite · ISTAT 28_185, 29_7",
         alt="Four panels on Italian migration. Immigration runs 5–8 per "
             "1,000 and emigration rises from 1 to 3; the two publishers "
             "agree to the person except in 2008–10; net migration stays "
             "positive but thin after 2020; 11.8% of residents were born "
             "abroad and 9.1% hold foreign citizenship at the end; the "
             "lens shows Italian-citizen emigration rising beside "
             "naturalisations near 222,000 in 2024."),
)
