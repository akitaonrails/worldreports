"""The japan plates, on the plate spine.

Every plate declares its topic and claims its four panels by slot key, in
the spine's order, so a Japanese panel sits over the same panel of every
other country in the comparison viewer: same indicator, same unit, same
y-scale (PLATE_SPINE.md, core/spine.py).

Three conventions run through the file:

- **Fiscal years** (April–March, keyed on the starting year, `FY_SHIFT`
  drawn at the 1 October midpoint) appear only where ESRI's national
  accounts and MOF's accounts are fiscal-year documents; those panels say
  so in their labels, and the calendar recession bands above sit where
  they happened relative to both kinds of year. Where a slot has a
  calendar-year canonical line (the IMF's), it is the line and the FY
  national perimeter rides beside it, labelled.
- **Per-100k rates use the Japanese-national population** — MHLW's counts
  are Japanese nationals in Japan, and their published rates divide by
  that population (DATA_NOTES.md). `japanese_k` for 2006–2024, the 2025
  census for 2025. The panel names the denominator.
- **Notes read their numbers from the CSVs** at build time, so a refetch
  that moves a figure moves the sentence with it.

Definitional seams are drawn as seams — separate labelled segments, never
spliced: the 2011→2012 foreigner-registration/residence-card step, the
2017 ICD aspiration-pneumonia split, the 2020–22 and 2023+ COVID codes,
the OECD poverty methods, and the three different government debts.
"""
from __future__ import annotations

from core.sideload import sibling

events = sibling(__file__, "events")

W0 = 2006        # the shared plate window opens here
FY_SHIFT = 0.75  # an April-March fiscal year, drawn at its 1 October midpoint


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
    """(x, values) from a fiscal-year CSV, drawn at the midpoint.

    The ESRI and MOF files are keyed by `fiscal_year`, the STARTING year
    of an April–March year, which ctx.series cannot see; ctx.rows takes
    the key and skips the '#' provenance header.
    """
    rows = ctx.rows(rel, key="fiscal_year") or {}
    out = [(y + FY_SHIFT, float(r[col])) for y, r in sorted(rows.items())
           if y >= since and (r.get(col) or "").strip()]
    return [y for y, _ in out], [v for _, v in out]


def _fy_gdp(ctx, col="gdp_nominal_fy_bn"):
    """The fiscal-year GDP column of the calendar-keyed ESRI file, drawn
    at the fiscal year's midpoint: row 2024 holds FY2024 (Apr-2024 –
    Mar-2025)."""
    rows = ctx.rows("published/gdp_esri.csv", key="year") or {}
    out = [(y + FY_SHIFT, float(r[col])) for y, r in sorted(rows.items())
           if y >= W0 and (r.get(col) or "").strip()]
    return [y for y, _ in out], [v for _, v in out]


def _at(years, vals, year):
    return dict(zip(years, vals))[year]


def _jp_pop(ctx):
    """The Japanese-national population, persons, keyed by year.

    The estimates' Japanese count on 1 October (2006–2024); 2025 exists
    only as the census, which is a change of base the notes flag.
    """
    pop = {y: v * 1000 for y, v in
           zip(*_yr(ctx, "published/population_stat.csv",
                    "japanese_k", since=W0))}
    cen = ctx.rows("published/census_stat.csv", key="census_year") or {}
    for y, r in cen.items():
        pop[y] = float(r["japanese"])
    return pop


def _total_pop(ctx):
    """Total resident population, persons (estimates; 2025 is the census)."""
    pop = {y: v * 1000 for y, v in
           zip(*_yr(ctx, "published/population_stat.csv",
                    "population_k", since=W0))}
    cen = ctx.rows("published/census_stat.csv", key="census_year") or {}
    for y, r in cen.items():
        pop[y] = float(r["population"])
    return pop


def _cpi_annual(ctx, col="cpi2020_all"):
    """Annual-average CPI inflation, % — the mean-index ratio, which is
    how the Statistics Bureau's own annual comparison works. One base
    only: the 2020 base, which the 2025 base agrees with to the 2025
    publication (DATA_NOTES)."""
    t = ctx.table("published/cpi_stat.csv")
    idx = {}
    for m, v in zip(t["month"], t[col]):
        if not (m or "").strip():
            continue
        y = int(m[:4])
        v = float(v)
        if v == v:
            idx.setdefault(y, []).append(v)
    means = {y: sum(v) / len(v) for y, v in idx.items() if len(v) >= 12}
    yrs = sorted(means)
    return ([y for y in yrs if y - 1 in means and y >= W0],
            [(means[y] / means[y - 1] - 1) * 100
             for y in yrs if y - 1 in means and y >= W0])


def _nikkei_usd(ctx):
    """Annual mean of the Nikkei monthly closes, converted to US$ at the
    BoJ annual-average USD/JPY (2026 partial months ride in, dashed)."""
    t = ctx.table("published/nikkei_yahoo.csv")
    closes = {}
    for m, v in zip(t["month"], t["close"]):
        if not (m or "").strip():
            continue
        v = float(v)
        if v == v:
            closes.setdefault(int(m[:4]), []).append(v)
    fx = dict(zip(*_yr(ctx, "published/usdjpy_boj.csv", "usdjpy_avg")))
    yrs = [y for y in sorted(closes) if y >= W0 and y in fx]
    return yrs, [sum(closes[y]) / len(closes[y]) / fx[y] for y in yrs]


def _note(p, ax, x, y, text, color=None, ha="left", va="top", size=8.0):
    """Narrative belongs in the chapter copy, not over comparable data."""
    return None


def _foot(p, ax, text):
    """Plate-level provenance is carried by the source line and manifest."""
    return None


def _mark(ig, ax, key, dy=0.97):
    """Events remain in events.py and the prose; the spine stays uncluttered."""
    return None


def _bands_labelled_at(ig, ax, y, p):
    """Draw recession intervals without labels competing for the data area."""
    ig.add_recessions(ax, label=False)


def _fy_note(p, ax, size=7.6):
    """Fiscal-year scope is stated in panel titles and the reading notes."""
    return None


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            # Point annotations collide with the fixed comparison frame in
            # at least one of three languages. The exact values remain in
            # the committed CSVs, card stats and accessible page copy; the
            # plate keeps only the comparable marks and axes. Legends stay:
            # a stacked layer or a second series nobody can name is not
            # comparable, it is unreadable (issue #3).
            for text in list(a.texts):
                # Keep only the spine's own status markers. Data-point labels,
                # event captions and end labels all fail in at least one
                # locale on the fixed 2×2 comparison frame.
                if text.get_gid() == "spine-extended" or \
                        text.get_text().startswith("data pending"):
                    continue
                text.remove()
            ig.style_axis(a)


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p
    G = "published/gdp_esri.csv"

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yoy_pct(ctx, G, "gdp_real_cy_bn")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.RED)
    ig.add_recessions(ax, label=False)
    for y in (2009, 2020):
        v = _at(gy, gv, y)
        ax.annotate(f"{v:.1f}%", (y, v), textcoords="offset points",
                    xytext=(0, -4), ha="center", va="top", fontsize=8.6,
                    fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.96, f"the 2024 H1 dip is two negative quarters "
          f"inside revision noise:\nthe year still grew {_at(gy, gv, 2024):.1f}% "
          "— the band is kept, and a test pins it (DATA_NOTES)")
    _foot(p, ax, "Cabinet Office (ESRI), chained 2020 yen, calendar years")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "published/gdp_pc_wb.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    _note(p, ax, 0.02, 0.30, f"US$ per person, 2012 to 2024: {_at(py, pv, 2012):,.0f} to "
          f"{_at(py, pv, 2024):,.0f} — the yen,\nnot the economy: in yen the "
          "figure keeps rising")
    _foot(p, ax, "World Bank, current US$ at market exchange rates")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year) and the 2% target")
    ax.axhline(2, color=p.GREEN_D, lw=1.0, ls=":", zorder=2)
    cy, cv = _cpi_annual(ctx)
    ctx.line(ax, cy, cv, p.RED, label="CPI, annual average, 2020 base")
    ig.add_recessions(ax, label=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(-8, 4), ha="right",
                fontsize=8.8, fontweight="bold", color=p.RED)
    _mark(ig, ax, "tax14", dy=0.62)
    _mark(ig, ax, "tax19", dy=0.62)
    _note(p, ax, 0.02, 0.96, "the BOJ's 2% target, set in January 2013: "
          "reached from 2022,\non import prices — the yen's slide, not "
          "domestic demand")
    _foot(p, ax, "Statistics Bureau; published rates on the 2020 base — the "
          "2025 base agrees month for month through 2025")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    L = "published/labour_stat.csv"
    uy, uv = _yr(ctx, L, "unemployment_rate_pct")
    ctx.line(ax, uy, uv, p.NAVY, label="labour force survey (ILO-compatible)")
    ig.add_recessions(ax, label=False)
    peak = max(zip(uy, uv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(0, 6), ha="center",
                fontsize=8.8, fontweight="bold", color=p.NAVY)
    low = min(zip(uy, uv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, f"the G7's low: a trough of {low[1]:.1f}% in "
          f"{low[0]}; {uv[-1]:.1f}% in {uy[-1]} —\nunderemployment, not "
          "joblessness, is the Japanese question")
    _foot(p, ax, "Statistics Bureau labour force survey; 2011 partly a "
          "supplementary estimate after the earthquake")
    _finish(ctx, ig)


def _div_years(ys, vs, gy, gv):
    """a ÷ b × 100 over the years both sides have (a line of values over
    the calendar-year nominal GDP, or any two columns aligned by year)."""
    bd = dict(zip(gy, gv))
    out = [(y, v / bd[y] * 100) for y, v in zip(ys, vs) if y in bd and y >= W0]
    return [y for y, _ in out], [v for _, v in out]


def _yoy_pct(ctx, rel, col):
    """Real year-on-year % from a level column (annual accounts)."""
    ys, vs = _yr(ctx, rel, col)
    d = dict(zip(ys, vs))
    out = [(y, (d[y] / d[y - 1] - 1) * 100) for y in ys if y - 1 in d]
    return [y for y, _ in out], [v for _, v in out]


# ------------------------------------------------------------------ fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p
    GG = "published/gg_accounts_esri.csv"
    IMF = "published/gg_fiscal_imf.csv"
    GDPF = "published/gdp_esri.csv"

    ax = ig.slot("fiscal.revenue_expenditure",
                 "Revenue and expenditure (% of GDP)")
    ey, ev = _fy(ctx, GG, "gg_expense_bn")
    ry, rv = _fy(ctx, GG, "gg_revenue_bn")
    fy_gdp = _fy_gdp(ctx)
    ey, epct = _div_years(ey, ev, *fy_gdp)
    ry, rpct = _div_years(ry, rv, *fy_gdp)
    ctx.line(ax, ey, epct, p.RED, dashed_partial=False,
             label="General government, expenditure (fiscal years)")
    ctx.line(ax, ry, rpct, p.NAVY, dashed_partial=False,
             label="General government, revenue (fiscal years)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower right", fontsize=7.4, ncol=2, frameon=False)
    _fy_note(p, ax)
    _note(p, ax, 0.02, 0.97, "the spine's calendar-year line is pending: "
          "the IMF answers\nempty for Japan's general government and the "
          "OECD line is a fetch;\nESRI publishes its accounts by fiscal "
          "year only (DATA_NOTES)", size=7.4)
    _foot(p, ax, "Cabinet Office (ESRI), System of National Accounts, "
          "general government")

    ax = ig.slot("fiscal.balance", "Overall balance (bars) and primary "
                 "balance (% of GDP)")
    by, bv = _yr(ctx, IMF, "net_lending_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.RED)
    fy_b = _fy(ctx, GG, "gg_net_lending_bn")
    ly, lv = _div_years(*fy_b, *_fy_gdp(ctx))
    ctx.line(ax, ly, lv, p.NAVY, lw=1.8, ms=3.2, dashed_partial=False,
             label="ESRI, general government, fiscal years")
    ig.add_recessions(ax, label=False)
    gw = min(zip(by, bv), key=lambda t: t[1])
    ax.annotate(f"{gw[1]:.1f}%", gw, textcoords="offset points",
                xytext=(-8, -2), ha="right", va="top", fontsize=8.6,
                fontweight="bold", color=p.RED)
    ax.legend(loc="lower left", fontsize=7.6, frameon=False)
    imf20 = _at(by, bv, 2020) if 2020 in by else bv[0]
    fy20 = _at(ly, lv, 2020 + FY_SHIFT) if 2020 + FY_SHIFT in ly else lv[-1]
    _note(p, ax, 0.98, 0.97, f"IMF calendar years, ESRI fiscal years: the "
          f"pandemic deficit reads\n{imf20:.1f}% for CY2020 and {fy20:.1f}% "
          "for FY2020 (which ended in Mar-2021)\n— one event, two accounting "
          "years. The primary balance is a\npending fetch (IMF GGXONLB).",
          ha="right", size=7.4)

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP) — and the three "
                 "figures quoted instead")
    dy, dv = _yr(ctx, IMF, "gross_debt_pct_gdp")
    fof_d = _yr(ctx, "published/gg_liabilities_boj.csv",
                "gg_liabilities_bn")
    cy, cv = _yr(ctx, "published/central_debt_mof.csv", "total_bn")
    gdp_cy = _yr(ctx, GDPF, "gdp_nominal_cy_bn")
    fy_, fv = _div_years(*fof_d, *gdp_cy)
    mz, mv = _div_years(cy, cv, *gdp_cy)
    ctx.line(ax, dy, dv, p.RED, label="IMF, general government (the spine "
             "line)")
    ctx.line(ax, fy_, fv, p.GOLD, lw=1.8, ms=3.2,
             label="BoJ flow of funds, all liabilities, market value")
    ctx.line(ax, mz, mv, p.NAVY, lw=1.8, ms=3.2,
             label="MOF, central government debt, face value")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.RED, lambda v: f"{v:.0f}%", dy=7)
    ax.legend(loc="upper left", fontsize=7.0, frameon=False)
    _note(p, ax, 0.98, 0.62, f"three debts, never spliced: {fv[-1]:.0f} / "
          f"{dv[-1]:.0f} / {mv[-1]:.0f}% at their\n2025 readings. The flow of "
          "funds figure is liabilities\n(L900−L700): the ¥948.6tn headline is "
          "financial assets.", ha="right", va="bottom", size=7.4)

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    iy, iv = _fy(ctx, GG, "gg_interest_bn")
    iy, ipct = _div_years(iy, iv, *fy_gdp)
    ctx.line(ax, iy, ipct, p.PURPLE, dashed_partial=False,
             label="General government, interest (fiscal years)")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, ipct, p.PURPLE, lambda v: f"{v:.1f}%", dy=8)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    low = min(zip(iy, ipct), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.97, "the cheap-money paradox: debt above 200% of GDP, "
          f"interest under\n{max(ipct):.0f}% — a {low[1]:.1f}% trough in "
          f"{low[0]}, and 26 years of rates near zero.\nCalendar-year "
          "interest is a pending fetch (OECD).", size=7.6)
    _fy_note(p, ax, size=7.2)
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
COFOG7 = [
    ("Social protection", ["social_protection_bn"], "RED"),
    ("Health", ["health_bn"], "TEAL"),
    ("Education", ["education_bn"], "GOLD"),
    ("General public services", ["general_public_services_bn"], "PURPLE"),
    ("Economic affairs", ["economic_affairs_bn"], "BLUE"),
    ("Defence and public order", ["defence_bn", "public_order_bn"], "NAVY"),
    ("Other", ["environment_bn", "housing_community_bn",
               "recreation_culture_bn"], "FAINT"),
]


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    C = "published/cofog_esri.csv"
    rows = ctx.rows(C, key="fiscal_year") or {}
    yrs = [y for y in sorted(rows) if y >= W0 and rows[y]["total_expenditure_bn"]]

    ax = ig.slot("spending.by_function", "Spending by function, general "
                 "government (% of GDP)")
    gdp_fy = ctx.rows("published/gdp_esri.csv", key="year") or {}
    # gdp_from_esri keys on calendar years; the FY GDP column rides on the
    # row whose year equals the fiscal year's starting year.
    def gdp_of(y):
        return float(gdp_fy[y]["gdp_nominal_fy_bn"])
    xs = [y + FY_SHIFT for y in yrs]
    layers = [(name, [sum(float(rows[y][c]) for c in cols) / gdp_of(y) * 100
                      for y in yrs], getattr(p, col))
              for name, cols, col in COFOG7]
    ax.stackplot(xs, *[v for _, v, _ in layers],
                 labels=[n for n, _, _ in layers],
                 colors=[c for _, _, c in layers], alpha=0.9, lw=0)
    _bands_labelled_at(ig, ax, 0.84, p)
    # The stack fills the lower right; the only clear ground is upper left,
    # under the title (the spine scale runs to 65, the stack peaks at ~46).
    ax.legend(loc="upper left", fontsize=6.9, ncol=2, frameon=False,
              bbox_to_anchor=(0.0, 0.98))
    tot = [sum(v) for v in zip(*[v for _, v, _ in layers])]
    i24 = yrs.index(2024)
    ax.annotate(f"{tot[i24]:.1f}%", (xs[i24], tot[i24]),
                textcoords="offset points", xytext=(0, 7), ha="center",
                fontsize=8.6, fontweight="bold", color=p.INK)
    _fy_note(p, ax, size=7.2)
    spf = [float(rows[y]["social_protection_bn"]) / gdp_of(y) * 100
           for y in yrs]
    _note(p, ax, 0.02, 0.80, f"a welfare state built quietly: {tot[0]:.1f}% of "
          f"GDP in {yrs[0]}, {tot[-1]:.1f}% in {yrs[-1]} —\nand social "
          f"protection alone, {spf[0]:.1f}% to {spf[-1]:.1f}% of GDP",
          size=7.4)

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    sp = [float(rows[y]["social_protection_bn"]) / gdp_of(y) * 100 for y in yrs]
    rest = [t - s for t, s in zip(tot, sp)]
    ctx.line(ax, xs, rest, p.NAVY, dashed_partial=False, label="Everything else")
    ctx.line(ax, xs, sp, p.RED, dashed_partial=False, label="Social protection")
    ig.add_recessions(ax, label=False)
    cash = [float(rows[y]["social_benefits_cash_social_protection_bn"])
            / gdp_of(y) * 100 for y in yrs]
    ax.plot([], [], color=p.GOLD, lw=1.6, ls=":",
            label="of which cash benefits")
    ax.legend(loc="lower left", fontsize=7.8, frameon=False)
    ctx.line(ax, xs, cash, p.GOLD, lw=1.4, ms=0, ls=(0, (1, 1.4)),
             dashed_partial=False)
    i24 = yrs.index(2024)
    ax.annotate(f"{sp[i24]:.1f}%: pensions and care for the largest "
                "ageing cohort", (xs[i24], sp[i24]),
                textcoords="offset points", xytext=(-10, 6), ha="right",
                fontsize=8.0, fontweight="bold", color=p.RED)
    _fy_note(p, ax, size=7.2)

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(GFCF, % of GDP)")
    G = "published/gdp_esri.csv"
    gy, gdp = _yr(ctx, G, "gdp_nominal_cy_bn")
    res = _yr(ctx, G, "private_residential_investment_nominal_cy_bn")
    nonres = _yr(ctx, G, "private_nonresidential_investment_nominal_cy_bn")
    pub = _yr(ctx, G, "public_investment_nominal_cy_bn")
    bd = dict(zip(gy, gdp))
    iy = [y for y in gy if W0 <= y <= min(max(res[0]), max(nonres[0]), max(pub[0]))]
    iv = [(dict(zip(*res))[y] + dict(zip(*nonres))[y] + dict(zip(*pub))[y])
          / bd[y] * 100 for y in iy]
    ctx.line(ax, iy, iv, p.BLUE)
    ig.add_recessions(ax, label=False)
    pk = max(zip(iy, iv), key=lambda t: t[1])
    lo = min(zip(iy, iv), key=lambda t: t[1])
    ax.annotate(f"{lo[1]:.1f}% in {lo[0]}: after the balance-sheet "
                "recession", lo, textcoords="offset points", xytext=(0, -12),
                ha="center", va="top", fontsize=8.0, fontweight="bold",
                color=p.BLUE)
    _note(p, ax, 0.02, 0.96, f"households, companies and government, from "
          f"the national accounts:\n{pk[1]:.1f}% at the {pk[0]} peak, "
          f"{iv[-1]:.1f}% in {iy[-1]} — the 1990s collapse precedes "
          "this window")
    _foot(p, ax, "ESRI national accounts: residential + non-residential + "
          "public investment ÷ nominal GDP")

    ax = ig.slot("spending.public_investment", "Public investment "
                 "(government GFCF, % of GDP)")
    py, pv = _div_years(*pub, gy, gdp)
    ctx.line(ax, py, pv, p.TEAL)
    ig.add_recessions(ax, label=False)
    pk = max(zip(py, pv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}: the stimulus years", pk,
                textcoords="offset points", xytext=(0, 7), ha="center",
                fontsize=8.2, fontweight="bold", color=p.TEAL)
    ctx.endlabel(ax, py, pv, p.TEAL, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96, "public gross fixed capital formation — public "
          "corporations included, so a\nlittle above the strict "
          "general-government line the spine prefers")
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
CUSTOMS_PARTNERS = [
    ("china", "China", "RED"),
    ("usa", "United States", "NAVY"),
    ("asean", "ASEAN", "TEAL"),
    ("korea", "Korea", "GOLD"),
    ("eu", "European Union", "PURPLE"),
]


def plate_trade(ctx, ig) -> None:
    p = ctx.p
    G = "published/gdp_esri.csv"

    ax = ig.slot("trade.exports_imports", "Exports and imports of goods "
                 "and services (% of GDP)")
    gy, gdp = _yr(ctx, G, "gdp_nominal_cy_bn")
    xy, xv = _div_years(*_yr(ctx, G, "exports_nominal_cy_bn"), gy, gdp)
    my, mv = _div_years(*_yr(ctx, G, "imports_nominal_cy_bn"), gy, gdp)
    ctx.line(ax, xy, xv, p.GREEN, label="Exports")
    ctx.line(ax, my, mv, p.RED, label="Imports")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=8.0, frameon=False)
    _note(p, ax, 0.02, 0.96, f"{xv[-1] + mv[-1]:.0f}% of GDP crosses the "
          f"border each way combined ({xy[-1]}),\nup from {xv[0] + mv[0]:.0f}% "
          "in " + str(xy[0]) + " — energy imports and global supply chains")
    _foot(p, ax, "ESRI national accounts, goods and services; the World Bank's "
          "openness agrees to 0.2 points")

    ax = ig.slot("trade.balance", "Trade balance, goods and services "
                 "(% of GDP)")
    bd = dict(zip(xy, xv))
    im = dict(zip(my, mv))
    byr = sorted(set(bd) & set(im))
    bal = [bd[y] - im[y] for y in byr]
    ctx.bars(ax, byr, bal, lambda v: p.GREEN if v >= 0 else p.RED)
    ig.add_recessions(ax, label=False)
    neg = [y for y, b in zip(byr, bal) if b < 0]
    _note(p, ax, 0.02, 0.96, f"in deficit in {len(neg)} of the {len(bal)} "
          f"years: {min(neg)}–{max(neg)} mostly\nwithout interruption — after "
          "2011, energy imports plus the cheap yen")
    _foot(p, ax, "ESRI national accounts, goods and services")

    PT = "published/trade_partners_customs.csv"
    total_x = dict(zip(*_yr(ctx, "published/trade_customs.csv",
                            "exports_jpy_bn")))

    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    shares = {}
    for code, name, col in CUSTOMS_PARTNERS:
        cy, cv = _yr(ctx, PT, f"exports_{code}_jpy_bn")
        sy, sv = _div_years(cy, cv, *zip(*[(y, total_x[y]) for y in cy
                                           if y in total_x]))
        shares[code] = dict(zip(sy, sv))
        ctx.line(ax, sy, sv, getattr(p, col),
                 lw=2.2 if code in ("china", "usa") else 1.7, ms=3.4,
                 label=name)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)
    ch = shares["china"]
    last = max(ch)
    ax.annotate(f"{ch[last]:.0f}%", (last, ch[last]), textcoords="offset points",
                xytext=(0, 7), ha="center", fontsize=8.4, fontweight="bold",
                color=p.RED)
    _note(p, ax, 0.02, 0.04, "goods only (customs), not the services line "
          "above; the EU line\nis EU28 to 2019 and EU27 from 2020 — the "
          "2019 to 2020 step is Brexit\nplus COVID, and is not spliced",
          va="bottom", size=7.4)

    ax = ig.slot("trade.lens", "Lens — the balance of payments: what Japan "
                 "earns abroad pays for what it buys")
    CA = "published/current_account_boj.csv"
    gdpd = dict(zip(gy, gdp))
    def ca_pct(col):
        ys, vs = _yr(ctx, CA, col)
        return _div_years(ys, vs, gy, gdp)
    gys, gvs = ca_pct("goods_bn")
    pys, pvs = ca_pct("primary_income_bn")
    ax.axhline(0, color=p.MUTED, lw=0.9, zorder=2)
    ctx.line(ax, gys, gvs, p.RED, label="goods balance")
    ctx.line(ax, pys, pvs, p.GREEN, label="primary income — profits, "
             "dividends and interest from abroad")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, pys, pvs, p.GREEN, lambda v: f"{v:+.1f}%", dy=8)
    ax.legend(loc="lower left", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.97, f"a goods deficit of {gvs[-1]:.1f}% of GDP paid "
          f"for by a {pvs[-1]:.1f}%\nprimary-income surplus: Japan is now an "
          "asset-income economy\nmore than an export economy — the surplus on "
          "the whole current\naccount (tests pin it) is the sum of these lines "
          "plus services\nand secondary income", size=7.6)
    _finish(ctx, ig)


# ---------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p
    R = "published/rates_boj.csv"

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ax.axvspan(2016.7, 2024.25, color=p.INDIGO, alpha=0.08, zorder=0)
    ay, av = _yr(ctx, R, "call_rate_avg")
    cy, cv = _cpi_annual(ctx)
    ctx.line(ax, cy, cv, p.RED, lw=1.6, ms=3.0, label="CPI inflation, "
             "annual average")
    ctx.line(ax, ay, av, p.NAVY, label="uncollateralised overnight call rate, "
             "annual average")
    _bands_labelled_at(ig, ax, 0.84, p)
    ctx.endlabel(ax, ay, av, p.NAVY, lambda v: f"{v:.2f}%", dy=8)
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)
    _mark(ig, ax, "neg", dy=0.66)
    _mark(ig, ax, "ycc_end", dy=0.40)
    _mark(ig, ax, "hike", dy=0.40)
    _note(p, ax, 0.02, 0.97, "the shaded band is yield-curve control, "
          "Sep-2016 to Mar-2024 —\nminus a fifth of a point for eight years. "
          "The decided target is\nhand-curation pending; the realised call "
          "rate is drawn, so the\nregime break off −0.1% in March 2024 shows "
          "through.", size=7.4)

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                   "(%, annual average)")
    j1, v1 = _yr(ctx, "published/jgb_mof.csv", "jgb_10y_avg")
    j2, v2 = _yr(ctx, "published/jgb_mof.csv", "jgb_2y_avg")
    ctx.line(ax, j2, v2, p.BLUE, lw=1.6, ms=3.0, label="2-year")
    ctx.line(ax, j1, v1, p.NAVY, label="10-year")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, j1, v1, p.NAVY, lambda v: f"{v:.2f}%", dy=8)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    lo = min(zip(j1, v1), key=lambda t: t[1])
    pk = max(zip(j1, v1), key=lambda t: t[1])
    _mark(ig, ax, "ycc", dy=0.30)
    _note(p, ax, 0.02, 0.97, f"a {lo[1]:.2f}% low in {lo[0]}, and {pk[1]:.2f}% "
          f"in {pk[0]} — the last bar\nis ten months of 2026, dashed: the "
          "highest 10-year yield\nsince 1999. The curve inverted as the BOJ "
          "normalised.", size=7.4)
    _foot(p, ax, "Ministry of Finance; the OECD MEI series agrees to 0.04 "
          "points")

    ax = ig.slot("markets.currency", "The yen against the US$ "
                 "(index 2006 = 100, up = stronger)")
    H = "published/usdjpy_boj.csv"
    hy, hv = _yr(ctx, H, "usdjpy_avg")
    ix_y, ix_v = ctx.fx_index(dict(zip(hy, hv)))
    ctx.line(ax, ix_y, ix_v, p.RED)
    _bands_labelled_at(ig, ax, 0.86, p)
    _mark(ig, ax, "fx_slide", dy=0.60)
    ctx.endlabel(ax, ix_y, ix_v, p.RED, lambda v: f"{v:.0f}", dy=-14, ha="left")
    pk = max(zip(ix_y, ix_v), key=lambda t: t[1])
    ax.annotate(f"{pk[0]}: the interval's strongest yen", pk,
                textcoords="offset points", xytext=(0, 6), ha="center",
                fontsize=8.0, fontweight="bold", color=p.NAVY)
    _note(p, ax, 0.02, 0.30, f"2022 to 2024: the slide to near {hv[-2]:.0f} yen "
          f"to the dollar\n({ix_v[-3]:.0f} on this scale) — the depreciation "
          "that put food and\nenergy inflation on Japanese tables", size=7.4)

    ax = ig.slot("markets.equities", "The Nikkei 225 in US$ "
                 "(index 2006 = 100)")
    ny, nv = _nikkei_usd(ctx)
    niy, niv = ctx.index_2006(dict(zip(ny, nv)))
    ctx.line(ax, niy, niv, p.RED)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, niy, niv, p.RED, lambda v: f"{v:.0f}", dy=8)
    _mark(ig, ax, "crisis", dy=0.30)
    _note(p, ax, 0.02, 0.97, "the S&P 500 comparison line is a spine fetch, "
          "pending with it.\nThe dollar-measured jump after 2012 is Abenomics "
          "and the yen: in yen\nthe index only passes its 1989 high in 2024, "
          "which is the whole story\nof this panel.", size=7.4)
    _foot(p, ax, "Yahoo Finance (not an official statistic), annual mean of "
          "monthly closes ÷ the BoJ average USD/JPY")
    _finish(ctx, ig)


# ------------------------------------------------------------------ credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p
    F = "published/household_debt_boj.csv"

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP, "
                 "year-end)")
    gy, gdp = _yr(ctx, "published/gdp_esri.csv", "gdp_nominal_cy_bn")
    ly, lv = _div_years(*_yr(ctx, F, "household_loans_bn"), gy, gdp)
    ctx.line(ax, ly, lv, p.RED)
    ig.add_recessions(ax, label=False)
    pk = max(zip(ly, lv), key=lambda t: t[1])
    lo = min(zip(ly, lv), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}% in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 7), ha="center", fontsize=8.6, fontweight="bold",
                color=p.RED)
    ctx.endlabel(ax, ly, lv, p.RED, lambda v: f"{v:.0f}%", dy=-14, ha="left")
    _note(p, ax, 0.02, 0.96, "the national line — flow-of-funds loans ÷ GDP, "
          "not the BIS total-credit\nline the spine prefers, which is a "
          f"fetch (BIS read 61.8% at 2024 Q4\nagainst {lv[-1]:.1f}% here; "
          "BIS counts household-like NPISHs too). The\n1990s bust is before "
          "this window; debt-to-GDP starts at " + f"{ly[0]}: {lv[0]:.0f}%",
          size=7.4)
    _foot(p, ax, "BoJ flow of funds, household-sector loans at year-end ÷ "
          "ESRI nominal GDP")

    ax = ig.slot("credit.lending_rate", "Household lending rate vs the "
                 "policy rate (%)")
    ctx.pending(ax)
    _note(p, ax, 0.5, 0.55, "pending: the BoJ's new-loan and housing-loan "
          "rates are a spine\nfetch; the call rate beside them would be a "
          "second −0.1% line", ha="center", va="center", size=7.6)

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    ctx.pending(ax)
    _note(p, ax, 0.5, 0.55, "pending: Japan's banks disclose under the "
          "Resolution and Repair\nAct (FSA) rather than a central-bank "
          "series; neither the FSA ratio\nnor the IMF FSI line is staged yet",
          ha="center", va="center", size=7.6)

    ax = ig.slot("credit.lens", "Lens — the household's balance sheet: what "
                 "the debt is (¥tn, year-end)")
    hy, hv0 = _yr(ctx, F, "household_loans_bn")
    hsy, hsv = _yr(ctx, F, "housing_loans_bn")
    cys, csv_ = _yr(ctx, F, "consumer_credit_bn")
    hv = [v / 1000 for v in hv0]
    ax.axhline(0, color=p.MUTED, lw=0.9, zorder=2)
    ctx.line(ax, hy, hv, p.RED, label="all household loans")
    ctx.line(ax, hsy, [v / 1000 for v in hsv], p.NAVY, lw=1.6, ms=3.0,
             label="housing loans")
    ctx.line(ax, cys, [v / 1000 for v in csv_], p.TEAL, lw=1.6, ms=3.0,
             label="consumer credit")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, hy, hv, p.RED, lambda v: f"¥{v:,.0f}tn", dy=8)
    _note(p, ax, 0.02, 0.96, f"a stock, not a flow: ¥{hv[-1]:,.1f}tn at the "
          f"{hy[-1]} reading, and\nhousing is {hsv[-1] / hv0[-1] * 100:.0f}% "
          "of it. Mortgages refinance at fixed\nrates far less often than "
          "America's: the rate rises reach\npayments slowly.", size=7.4)
    _finish(ctx, ig)


# ------------------------------------------------------------------ people
def plate_people(ctx, ig) -> None:
    p = ctx.p
    O = "published/gini_oecd.csv"

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100, higher "
                 "= more unequal)")
    y1, v1 = _yr(ctx, O, "gini_meth2011")
    y2, v2 = _yr(ctx, O, "gini_meth2012")
    wy, wv = _yr(ctx, "published/gini_wb.csv", "gini")
    ctx.line(ax, y1, [v * 100 for v in v1], p.NAVY, dashed_partial=False,
             label="OECD, 2011 method (to 2018)")
    ctx.line(ax, y2, [v * 100 for v in v2], p.RED, dashed_partial=False,
             label="OECD, 2012 method (from 2018)")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.6, ms=3.0, label="World Bank")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.96, "one survey, two income definitions: 2018 exists "
          "on both, and the\nlines never cross the seam — the OECD "
          "redrew Japan's disposable-income\nconcept, it is not a jump in "
          "inequality", size=7.4)
    _foot(p, ax, "OECD Income Distribution Database (the MHLW survey), and "
          "the World Bank")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    P = "published/poverty_mhlw.csv"
    p1, v1 = _yr(ctx, P, "poverty_rate_old")
    p2, v2 = _yr(ctx, P, "poverty_rate_new")
    ctx.line(ax, p1, v1, p.NAVY, marker="o", ms=6, dashed_partial=False,
             label="national relative poverty, old definition (to 2018)")
    ctx.line(ax, p2, v2, p.RED, marker="o", ms=6, dashed_partial=False,
             label="new definition (from 2018)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.96, "below half the median equivalised disposable "
          "income — triennial,\nso the gaps are real gaps, not interpolation; "
          "the World Bank's\nUS$8.30 line for Japan is a pending fetch",
          size=7.4)
    _foot(p, ax, "MHLW National Survey on Income and Living Conditions, via "
          "the OECD")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    ctx.pending(ax)
    _note(p, ax, 0.5, 0.55, "Pending: Japan has a statutory minimum wage set by prefecture; the MHLW national weighted average was ¥1,055 per hour in FY2024, and the monthly conversion is not yet staged.",
          ha="center", va="center", size=7.6)

    ax = ig.slot("people.lens", "Lens — an ageing labour force keeps working "
                 "(% of those 15 and over)")
    L = "published/labour_stat.csv"
    ry, rv = _yr(ctx, L, "participation_rate_pct")
    ey, ev = _yr(ctx, L, "employment_rate_pct")
    ctx.line(ax, ry, rv, p.NAVY, label="participation rate")
    ctx.line(ax, ey, ev, p.GREEN, label="employment rate")
    ax.set_ylabel("% of ages 15 and over", fontsize=8.6, color=p.MUTED)
    ig.add_recessions(ax, label=False)
    # The employment dip owns the lower left; the upper left is clear.
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.96, f"participation, {rv[0]:.1f}% to {rv[-1]:.1f}% "
          f"({ry[-1]}), while the 15+ population\nfalls: the workforce is "
          "older and thinner each year, and women\nand older workers are "
          f"what grew. Child poverty: {_at(*_yr(ctx, P, 'child_poverty_new'), 2024):.1f}% "
          "in 2024", size=7.4)
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "published/gdp_usd_wb.csv", "gdp_usd")
    gv = [v / 1e9 for v in gv]
    ctx.line(ax, gy, gv, p.RED)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.RED, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, f"US$ at market rates: {gv[0]:,.0f}bn in {gy[0]}, "
          f"{gv[-1]:,.0f}bn in {gy[-1]} —\nnominal yen barely moved; the whole "
          "arc is the exchange rate.\nIn dollar terms Japan was overtaken by "
          "Germany in 2023 — in\nyen, nothing of the sort happened")
    _foot(p, ax, "World Bank; ESRI ÷ the BoJ average USD/JPY agrees within "
          "0.4%")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "published/hdi_undp.csv", "hdi")
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
    cy, cv = _yr(ctx, "published/cpi_ti.csv", "cpi_score")
    ctx.line(ax, cy, cv, p.PURPLE)
    ctx.endlabel(ax, cy, cv, p.PURPLE, lambda v: f"{v:.0f}", dy=8)
    _foot(p, ax, "Transparency International; comparable 2012 method only")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn, year-end)")
    ry, rv = _yr(ctx, "published/reserves_mof.csv",
                 "reserves_total_musd")
    rv = [v / 1000 for v in rv]
    ctx.line(ax, ry, rv, p.GREEN_D)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.GREEN_D, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, "one of the world's largest stacks, defended only "
          "obliquely:\nintervention deposits are signed by MOF and run through "
          "the BoJ.\nThe World Bank agrees to within US$50mn at Dec-2024")
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p
    D = "published/vital_mhlw.csv"
    P = "published/population_stat.csv"

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    pop = _total_pop(ctx)
    est = {y: v for y, v in pop.items() if y <= 2024}
    iy, iv = ctx.index_2006(est)
    ctx.line(ax, iy, iv, p.BLUE)
    cens = {y: v for y, v in pop.items() if y >= 2025}
    cx = sorted(cens)
    ax.scatter(cx, [cens[y] / est[2006] * 100 for y in cx], s=26,
               color=p.NAVY, zorder=6, marker="D",
               label="2025 census — a change of base, not joined")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.2, frameon=False)
    last = max(est)
    ctx.endlabel(ax, iy, iv, p.BLUE, lambda v: f"{est[last] / 1e6:.1f}M",
                 dy=-14, ha="left")
    _mark(ig, ax, "census25", dy=0.30)
    _note(p, ax, 0.02, 0.96, "the G7's first shrinkage: 128.0m in 2010, "
          f"{est[last] / 1e6:.1f}m in {last}, and\nthe census counts "
          f"{cens[cx[-1]] / 1e6:.1f}m on a new base; IPSS's medium variant "
          "sees\nabout 87m by 2070 (its projections are a note, not a line)",
          size=7.6)
    _foot(p, ax, "Statistics Bureau estimates (1 October); the 2025 census "
          "stands alone")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    ty, tv = _yr(ctx, D, "tfr")
    ax.axhline(2.1, color=p.FAINT, lw=1.0, ls=":")
    ctx.line(ax, ty, tv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ty, tv, p.PURPLE, lambda v: f"{v:.2f}", dy=-14)
    _note(p, ax, 0.98, 0.74, "2.1 = replacement", ha="right", size=7.8)
    _note(p, ax, 0.02, 0.18, f"below 1.5 since 1993, and {tv[-1]:.2f} in "
          f"{ty[-1]}: the world has never\nseen a large economy age this far "
          "without a fertility recovery", va="bottom", size=7.8)
    _foot(p, ax, "MHLW vital statistics (Japanese nationals), published rate")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    by, bv = _yr(ctx, D, "birth_rate")
    dy_, dv = _yr(ctx, D, "death_rate")
    ctx.line(ax, by, bv, p.GREEN, label="Births (Japanese nationals)")
    ctx.line(ax, dy_, dv, p.RED_D, label="Deaths (Japanese nationals)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=8.0, frameon=False)
    ny_, nv_ = _yr(ctx, D, "natural_change_rate")
    first_neg = next((y for y in ny_ if _at(ny_, nv_, y) < 0), None)
    _note(p, ax, 0.02, 0.96, f"the published rates, on the Japanese-national "
          f"population; deaths\noutnumber births in every year of this window "
          f"— {bv[-1]:.1f} births against\n{dv[-1]:.1f} deaths per 1,000 in "
          f"{by[-1]} — and natural change turns negative\nin {first_neg} "
          f"({nv_[ny_.index(first_neg)]:.1f} per 1,000)", size=7.6)
    _foot(p, ax, "MHLW vital statistics; counts of Japanese nationals only "
          "(DATA_NOTES)")

    ax = ig.slot("demography.natural_migration", "Natural increase and net "
                 "migration (per 1,000 people)")
    ny, nv = _yr(ctx, D, "natural_change_rate")
    ctx.bars(ax, ny, nv, lambda v: p.GREEN)
    ig.add_recessions(ax, label=False)
    ax.axhline(0, color=p.MUTED, lw=0.9, zorder=2)
    pk = max(zip(ny, nv), key=lambda t: t[1])
    lo = min(zip(ny, nv), key=lambda t: t[1])
    ax.annotate(f"{lo[1]:.1f}", (lo[0], lo[1]), textcoords="offset points",
                xytext=(0, -4), ha="center", va="top", fontsize=8.6,
                fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.96, "natural change alone — the published rate, "
          "Japanese nationals.\nA migration line is not overlaid because "
          "the UN model has a different scope;\nit is shown separately on "
          "the migration plate.", size=7.4)
    _finish(ctx, ig)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    C = "published/causes_mhlw.csv"
    jpp = _jp_pop(ctx)

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000, log "
                 "scale)")
    hy, hv = _yr(ctx, "published/homicide_deaths_mhlw.csv",
                 "homicide_deaths")
    ry, rv = ctx.per_100k(dict(zip(hy, hv)), jpp)
    ctx.line(ax, ry, rv, p.RED, split_year=max(ry),
             label="MHLW deaths ÷ Japanese-national population")
    wy, wv = _yr(ctx, "published/homicide_rate_wb.csv",
                 "homicides_per_100k")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.6, ms=3.0, split_year=max(wy),
             label="UNODC via the World Bank (all residents)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    lo = min(zip(ry, rv), key=lambda t: t[1])
    ax.annotate(f"{lo[1]:.2f} in {lo[0]}", lo, textcoords="offset points",
                xytext=(0, -12), ha="center", va="top", fontsize=8.2,
                fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.96, "one of the lowest homicide rates measured "
          "anywhere, and still\nfalling; the log axis keeps it honest "
          "against countries an order\nor two up. The police count is the "
          "lens below, not this line", size=7.4)

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    t = ctx.table(C)
    ys, vs = ctx.series(t, "suicide_20200")
    sy, sv = ctx.per_100k(dict(zip(ys, vs)), jpp)
    ctx.line(ax, sy, sv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    pk = max(zip(sy, sv), key=lambda t_: t_[1])
    ax.annotate(f"{pk[1]:.1f} in {pk[0]}", pk, textcoords="offset points",
                xytext=(0, 6), ha="center", fontsize=8.4, fontweight="bold",
                color=p.PURPLE)
    ctx.endlabel(ax, sy, sv, p.PURPLE, lambda v: f"{v:.1f}", dy=-14, ha="left")
    _note(p, ax, 0.02, 0.96, f"death registrations (ICD X04–X06, Y87.0) ÷ the "
          f"Japanese-national\npopulation: {sv[0]:.1f} per 100,000 in {sy[0]}, "
          f"a {pk[1]:.1f} peak in {pk[0]},\nthen a decade of falls — the one "
          "large Japanese mortality trend\nthat reversed", size=7.4)
    _foot(p, ax, "MHLW causes of death; the NPA's suicide survey counts "
          "all residents")

    ax = ig.slot("security.road_deaths", "Road traffic deaths "
                 "(per 100,000)")
    ctx.pending(ax)
    _foot(p, ax, "MHLW code 20100 covers all accidents, including the 2011 disaster; a verified road-only series is not staged")

    ax = ig.slot("security.lens", "Lens — two counts of the same crime, "
                 "4.6× apart (deaths and cases per year)")
    ay, av = _yr(ctx, "published/homicide_police_npa.csv",
                 "satsujin_recorded_incl_attempts")
    dy0, dv0 = _yr(ctx, "published/homicide_deaths_mhlw.csv",
                   "homicide_deaths")
    ctx.bars(ax, ay, av, lambda v: p.RED)
    ctx.line(ax, dy0, dv0, p.NAVY, marker="o", ms=4, label="MHLW homicide "
             "deaths (registered)")
    ig.add_recessions(ax, label=False)
    ax.set_ylabel("deaths / recorded cases", fontsize=8.6, color=p.MUTED)
    ctx.endlabel(ax, ay, av, p.RED, lambda v: f"{v:,.0f}", dy=8)
    # The bar tops own the upper left; the bars fall away to the right.
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96, f"the police agency's homicide record includes "
          f"attempts and preparation: "
          f"{av[-1]:,.0f} recorded\nagainst {dv0[-1]:,.0f} registered deaths in "
          f"{dy0[-1]} — {av[-1] / dv0[-1]:.1f}×. It is a\npolice-administration "
          "count, not a crime rate", size=7.4)
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    D = "published/vital_mhlw.csv"
    C = "published/causes_mhlw.csv"
    jpp = _jp_pop(ctx)

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000 people)")
    cy, cv = _yr(ctx, D, "death_rate")
    ctx.line(ax, cy, cv, p.RED_D)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, cy, cv, p.RED_D, lambda v: f"{v:.1f}", dy=8)
    _note(p, ax, 0.02, 0.96, "the published rate, Japanese nationals: "
          f"{cv[0]:.1f} per 1,000 in {cy[0]},\n{cv[-1]:.1f} in {cy[-1]} — the "
          "baby boom generation now passes\nthrough the highest-death ages")
    _foot(p, ax, "MHLW vital statistics; counts agree with the Statistics "
          "Bureau's within ±2.5%")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above the 2015–2019 average)")
    dy, dv = _yr(ctx, "published/causes_mhlw.csv", "all_causes_revised")
    d = dict(zip(dy, dv))
    base = sum(d[y] for y in range(2015, 2020)) / 5
    ex_y = [y for y in dy if y >= 2015]
    ex_v = [(d[y] / base - 1) * 100 for y in ex_y]
    ctx.bars(ax, ex_y, ex_v, lambda v: p.RED if v > 0 else p.GREEN)
    ig.add_recessions(ax, label=False)
    pk = max(zip(ex_y, ex_v), key=lambda t: t[1])
    ax.annotate(f"+{pk[1]:.1f}%", pk, textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=8.6, fontweight="bold",
                color=p.RED)
    lo = min(zip(ex_y, ex_v), key=lambda t: t[1])
    ax.annotate(f"{lo[1]:.1f}%", lo, textcoords="offset points",
                xytext=(0, -4), ha="center", va="top", fontsize=8.0,
                fontweight="bold", color=p.GREEN)
    _note(p, ax, 0.02, 0.97, f"counts against {base / 1e3:,.0f} thousand a "
          "year, the 2015–2019 mean; the\n2020–22 flu seasons were light, and "
          "Japan's 2022 wave\nlifts 2022 alone. Not adjusted for a population "
          "shrinking\nand ageing — deaths in raw numbers are falling",
          size=7.4)

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                  "(per 100,000)")
    ys, v200 = ctx.series(ctx.table(C), "special_purpose_codes_22200")
    _, v201 = ctx.series(ctx.table(C), "covid19_22201")
    y200, r200 = ctx.per_100k(dict(zip(ys, v200)), jpp)
    y201, r201 = ctx.per_100k(dict(zip(ys, v201)), jpp)
    ctx.bars(ax, y200, r200, lambda v: p.PURPLE)
    ctx.bars(ax, y201, r201, lambda v: p.INDIGO)
    ax.plot([], [], color=p.PURPLE, lw=5, label="code 22200, 2020–22")
    ax.plot([], [], color=p.INDIGO, lw=5,
            label="code 22201, from 2023 — a different tabulation")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    pk = max(zip(y200 + y201, r200 + r201), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}", pk, textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=8.6, fontweight="bold",
                color=p.PURPLE)
    _note(p, ax, 0.02, 0.97, f"the worst Japanese year was {pk[0]}, the year "
          "of Omicron —\nnot 2020: borders held until mid-2020 and reopened "
          "into\na late, large wave. The two codes are never added", size=7.4)

    ax = ig.slot("mortality.lens", "Lens — certified "
                 "\"death from old age\" becomes a leading cause "
                 "(per 100,000)")
    ys, sv = ctx.series(ctx.table(C), "senility_18100")
    sy, sr = ctx.per_100k(dict(zip(ys, sv)), jpp)
    ys2, cv2 = ctx.series(ctx.table(C), "malignant_neoplasms_02100")
    cy2, cr = ctx.per_100k(dict(zip(ys2, cv2)), jpp)
    ctx.line(ax, sy, sr, p.GOLD, label="senility (R54)")
    ctx.line(ax, cy2, cr, p.FAINT, lw=1.6, ms=3.0, dashed_partial=False,
             label="all cancers (for scale)")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, sy, sr, p.GOLD, lambda v: f"{v:.0f}", dy=8)
    # The rising senility line owns the centre right; the lower right below
    # it is the only corner clear in every locale.
    ax.legend(loc="lower right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.97, "a certificate, not a disease: \"death from "
          "old age\" rises with the share\nof deaths at very old ages — a "
          "doctor writing it skips the mechanism\nwork. It makes Japan's cause "
          "rankings incomparable, and aspiration\npneumonia split out of "
          "pneumonia in 2017 for the same coding\nreason; neither line is "
          "spliced", size=7.4)
    _finish(ctx, ig)


# --------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p
    R = "published/foreign_residents_isa.csv"

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    ctx.pending(ax)
    _note(p, ax, 0.5, 0.55, "pending — and partly unavailable: Japan keeps no "
          "emigration\nregister, and ISA's entrant counts are travel events "
          "with tourists,\nnot people moving. The Statistics Bureau's "
          "net-mover columns\n(residents of three months or more) are the "
          "national answer "
          "and a spine fetch", ha="center", va="center", size=7.6)

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    my, mv = _yr(ctx, "published/net_migration_wb.csv", "net_migration")
    pop = _total_pop(ctx)
    points = [(y, v / pop[y] * 1000) for y, v in zip(my, mv) if y in pop]
    ctx.bars(ax, [y for y, _ in points], [v for _, v in points],
             lambda v: p.GREEN if v >= 0 else p.RED)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96, "UN WPP modelled net migration via the World "
          "Bank — not Japan's resident-movement register", size=7.6)

    ax = ig.slot("migration.foreign_born", "Foreign citizens as a share of "
                 "the population (%) — no country-of-birth data exist")
    fk, fv = _yr(ctx, "published/population_stat.csv", "foreign_k")
    pop = _total_pop(ctx)
    sy, sv = ([], [])
    for y, v in zip(fk, fv):
        if y in pop:
            sy.append(y)
            sv.append(v * 1000 / pop[y] * 100)
    cen = ctx.rows("published/census_stat.csv", key="census_year") or {}
    ctx.line(ax, sy, sv, p.TEAL, marker="o", ms=4.5,
             label="foreign citizens (estimates, 1 October)")
    if 2025 in cen:
        v25 = float(cen[2025]["foreign"]) / pop[2025] * 100
        ax.scatter([2025], [v25], s=30, color=p.NAVY, marker="D", zorder=6,
                   label="2025 census — a different count of the same idea")
        ax.annotate(f"{v25:.1f}%", (2025, v25), textcoords="offset points",
                    xytext=(-4, 8), ha="right", fontsize=8.2,
                    fontweight="bold", color=p.NAVY)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    _note(p, ax, 0.02, 0.96, "Japan's census asks citizenship, never "
          "country of birth: the\nspine's foreign-born share genuinely does "
          "not exist here, and a\ncitizen share of ~3% is one of the G7's "
          "lowest — it is the true\nstatement, not a gap", size=7.4)
    _foot(p, ax, "Statistics Bureau estimates and the 2025 census; ISA's "
          "registry reads 4.13m at end-2025 (the lens)")

    ax = ig.slot("migration.lens", "Lens — the foreign-resident stock, "
                 "two registers (persons at 31 December)")
    reg_y, reg_v = _yr(ctx, R, "registered_foreigners", until=2011)
    res_y, res_v = _yr(ctx, R, "foreign_residents", since=2012)
    ctx.line(ax, reg_y, [v / 1e6 for v in reg_v], p.NAVY,
             dashed_partial=False,
             label="foreigner-registration register (to end-2011)")
    ctx.line(ax, res_y, [v / 1e6 for v in res_v], p.TEAL,
             label="residence-card foreigners (from end-2012)")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "residence", dy=0.90)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    ctx.endlabel(ax, res_y, [v / 1e6 for v in res_v], p.TEAL,
                 lambda v: f"{v:.1f}M", dy=8)
    _note(p, ax, 0.02, 0.04, f"a stock, not a flow. The {reg_y[-1]} to {res_y[0]} "
          f"step ({reg_v[-1] / 1e6:.2f}m down to {res_v[0] / 1e6:.2f}m)\nis a "
          "change of register, not a fall; the doubling after 2019 is "
          "work-visa\nregimes opened by the Abe and Kishida governments. "
          "Asylum recognition\nis not drawn: UNHCR's 2024 figure folds "
          "refugees and complementary\nprotection together until the ISA "
          "release splits them (DATA_NOTES)", va="bottom", size=7.4)
    _finish(ctx, ig)


# The plates, in the order the page lists them; the ids are the spine's
# chapter numbers.
_SRC = ("Cabinet Office (ESRI) · Statistics Bureau (e-Stat) · Bank of Japan · "
        "Ministry of Finance · MHLW")
PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Japanese Economy — Two Lost Decades That Ended in Prices",
         subtitle="Growth, income, prices and jobs from the Cabinet Office's "
                  "chained accounts and the Statistics Bureau's surveys.",
         source="Sources: " + _SRC + " · World Bank",
         alt="Four panels on the Japanese economy, 2006–2025. Real GDP fell "
             "about 5% in 2009 and 4% in 2020; GDP per person in US dollars "
             "round-tripped from near 50,000 to about 34,000 in 2021 and back "
             "with the yen; consumer price inflation, pinned near zero for a "
             "decade, ran above the BOJ's 2% target from 2022; unemployment "
             "stayed between 2.4% and 5.5% throughout."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — The Deepest Debt in the Rich World, and "
                "the Cheapest Money That Carried It",
         subtitle="General government on ESRI's fiscal-year books, the IMF's "
                  "calendar-year line, and the two debts Japan argues about "
                  "beside them.",
         source="Sources: ESRI System of National Accounts · IMF WEO · BoJ "
                "flow of funds · Ministry of Finance",
         alt="Four panels on Japanese public finances. General-government "
             "expenditure runs near 40% of GDP against revenue near 30%; the "
             "IMF's calendar-year balance reached about −10% of GDP in 2020; "
             "gross debt runs between 170% and 230% of GDP — the IMF's "
             "general-government line above 200%, the flow of funds higher, "
             "MOF's central line lower — with the panel naming all three; "
             "interest paid never exceeds 3% of GDP."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Where the Money Goes — A Quiet Welfare State for an Old "
                "Country",
         subtitle="COFOG by function on ESRI's fiscal-year accounts, and the "
                  "economy's and the state's investment rates.",
         source="Sources: ESRI System of National Accounts (COFOG divisions)",
         alt="Four panels on spending. General-government outlays by function "
             "grow from about 32% to 42% of GDP, social protection the "
             "largest group and education the slowest; whole-economy "
             "investment runs 21–26% of GDP; public investment peaks above "
             "6% in the mid-1990s aftermath years inside the window and "
             "falls to about 4%."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — An Export Champion That Became an Asset Manager",
         subtitle="Goods and services on the national accounts, destinations "
                  "on the customs books, and the balance of payments as the "
                  "lens.",
         source="Sources: ESRI national accounts · Japan Customs · Bank of "
                "Japan balance of payments",
         alt="Four panels on Japanese trade. Exports plus imports rise from "
             "about 28% to 46% of GDP; the goods-and-services balance is in "
             "deficit through most of the window, deepest in 2011–22; China "
             "and the United States each take roughly a fifth to a quarter "
             "of goods exports; the lens shows a goods deficit of about 1% "
             "of GDP paid for by a primary-income surplus of about 6%."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Markets — The Regime Break of 2024, After Eight Years of "
                "Minus a Fifth of a Point",
         subtitle="The call rate under yield-curve control and after it, the "
                  "JGB curve, the yen's slide, and the Nikkei in US dollars.",
         source="Sources: Bank of Japan · Ministry of Finance (JGB) · Yahoo "
                "Finance (not an official statistic)",
         alt="Four panels on Japanese markets. The call rate sat at zero or "
             "below from 2016 to March 2024 and rises through 2026 as "
             "inflation runs above target; the 10-year yield stayed near "
             "zero until 2024 and runs above 2% by 2026; the yen index falls "
             "from about 105 to the 60s between 2012 and 2024; the Nikkei in "
             "US dollars roughly triples from its 2012 low."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — Household Debt That Grew While Wages Didn't",
         subtitle="Household loans from the BoJ flow of funds on the national "
                  "line; the BIS line, lending rates and NPLs are spine "
                  "fetches still pending.",
         source="Sources: Bank of Japan flow of funds · ESRI national "
                "accounts · BIS cross-check per DATA_NOTES",
         alt="Four panels on credit. Household debt runs near 60% of GDP on "
             "the national line; two panels are pending fetches with their "
             "reasons stated; the lens shows household loans of about ¥390tn "
             "with housing the largest part."),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="People — Inequality the Quiet, and Work the Older",
         subtitle="Income distribution from the OECD's database of the MHLW "
                  "survey, poverty on its two definitions, and the labour "
                  "force survey as the lens.",
         source="Sources: OECD Income Distribution Database · MHLW · "
                "Statistics Bureau labour force survey · World Bank",
         alt="Four panels on people. The Gini runs in the low 30s across two "
             "OECD method segments; relative poverty reads 15–16% and child "
             "poverty near 11–13% on triennial points; the minimum-wage panel "
             "states its pending fetch; participation and employment rates "
             "rise as the 15+ population shrinks."),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="Japan Among the Others — A Dollar Mirror",
         subtitle="Size, development, corruption and reserves as the world "
                  "measures them.",
         source="Sources: World Bank · UNDP · Ministry of Finance · "
                "Transparency International",
         alt="Four panels on Japan among other countries. GDP in US dollars "
             "falls from about $5.2tn to below $4.2tn and recovers, a "
             "currency move more than an economy move; the HDI runs near "
             "0.92; the Corruption Perceptions Index reads 71 in 2025; "
             "reserves stand above $1.3tn."),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — The Country the Projection Isn't Kind To",
         subtitle="Estimates and the 2025 census, published fertility and "
                  "mortality rates, and natural change alone where "
                  "international flows end.",
         source="Sources: Statistics Bureau (estimates and census) · MHLW "
                "vital statistics · IPSS projections (noted, not drawn)",
         alt="Four panels on demography. Population peaks in 2008 and falls "
             "to 123.8m on the estimates and 123.0m on the census base; "
             "fertility runs 1.26–1.45 and reads 1.14 in 2025; deaths overtake "
             "births inside the window; natural change turns negative from "
             "2015; the differently scoped UN model is kept on the migration "
             "plate."),
    dict(id="10", slug="security", topic="security", builder=plate_security,
         title="Security — The Low-Crime Country, Counted Twice",
         subtitle="Homicide and suicide from MHLW registrations, with the "
                  "road-only slot visibly pending and the police count as the lens.",
         source="Sources: MHLW causes of death · World Bank/UNODC · National "
                "Police Agency",
         alt="Four panels on security. Homicide falls to about 0.19 per "
             "100,000 on the MHLW deaths and near 0.23 on UNODC; suicide "
             "runs 23.7 per 100,000 in 2006, peaks inside the window in "
             "2011, and falls to 16.3 by 2024; road-only deaths remain "
             "pending because the staged accident category is broader; the lens shows police-recorded homicide at about "
             "4.6× registered homicide deaths."),
    dict(id="11", slug="mortality", topic="mortality", builder=plate_mortality,
         title="Mortality — An Ageing Pyramid Writing Its Own Statistics",
         subtitle="Crude death rates, excess deaths, the two COVID codes, "
                  "and senility certification as the lens.",
         source="Sources: MHLW vital statistics and causes of death "
                "(revised tabulation)",
         alt="Four panels on mortality. The crude death rate rises from 8.8 "
             "to 13.3 per 1,000; excess deaths against the 2015–19 mean dip "
             "negative in 2020–21 and peak in 2022 and 2023; COVID deaths "
             "per 100,000 peak in 2022 and 2023–24 on two separate codes; "
             "senility certification rises to over 175 per 100,000, beside "
             "all cancers for scale."),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — The Register Is the Story",
         subtitle="What Japan counts: citizens abroad and residents at home "
                  "by register; flows it does not keep, stated plainly.",
         source="Sources: Immigration Services Agency · Statistics Bureau "
                "estimates and census · Ministry of Justice · World Bank/UN "
                "WPP · UNHCR (noted, not drawn)",
         alt="Four panels on migration. One panel states plainly why gross "
             "immigration and emigration flows cannot be drawn; modelled UN "
             "net migration is shown separately from national registers; the "
             "foreign-citizen share rises to about 3.1% and the "
             "2025 census point sits beside it; the lens draws the two "
             "foreign-resident registers as separate segments, from 2.08m to "
             "4.13m, the 2012 seam marked."),
)
