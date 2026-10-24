"""The United Kingdom plates, on the plate spine.

Every plate declares its topic and claims its four panels by slot key, in
the spine's order, so a British panel sits over the same panel of every
other country in the comparison viewer: same indicator, same unit, same
y-scale (PLATE_SPINE.md, core/spine.py). The UK is born on the spine: no
chapter here predates it.

Twelve chapters, and the harmonised layer is a different shape from every
other country's. Brexit closed the Eurostat slices: the fiscal, LFS and
EU-SILC cubes come back well-formed and empty, HICP and the whole migration
suite are frozen at 2019, and only demography and the Maastricht yield still
run. So the national series are the ONS, the Bank of England, the Treasury,
the Home Office, HMRC and DWP, and the harmonised comparisons come from the
IMF (fiscal) and the World Bank (everything else). Where a slot has no
harmonised twin in the lane, the panel says so; where a series genuinely
does not exist for the UK, the panel says that instead (core.ctx.pending).

Three conventions run through the file:

- **Financial years** (April to March, `fiscal_year` = the starting year)
  are drawn at their midpoint, 1 October, a quarter of a year right of the
  calendar year they start in (`FY_SHIFT`). PESA, HBAI, the ONS Gini and the
  Homicide Index all run on them; the PSF files carry both keys and the
  plates use the one they name.
- **Breaks are drawn as seams.** The migration chapter draws the Eurostat
  IPS-era segment and the ONS administrative-era segment as two labelled
  lines over the 2012–2019 overlap, never joined; the certificate-based
  homicide line starts in 2007 because of the Y33.9→U50.9 coding change;
  the settlement line marks the component that ends in May 2019.
- **Notes read their numbers from the CSVs** at build time, so a refetch
  that moves a figure moves the sentence with it.

Scope is stated on every panel that needs it: the UK for the economy, the
finances, trade, markets, credit, people and migration; Great Britain for
the Treasury's functional spending; England & Wales for births, deaths and
both homicide series, because no UK-wide police or cause-of-death series
exists (DATA_NOTES.md).
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


def _fy(ctx, rel: str, col: str, since: int = W0):
    """(x, values) from an April-March financial-year CSV, drawn at its
    midpoint. The files are keyed `fiscal_year` — the STARTING year — which
    ctx.series cannot see; ctx.rows takes the key and skips the '#' header.
    """
    rows = ctx.rows(rel, key="fiscal_year") or {}
    out = [(y + FY_SHIFT, float(r[col])) for y, r in sorted(rows.items())
           if y >= since and (r.get(col) or "").strip()]
    return [y for y, _ in out], [v for _, v in out]


def _at(years, vals, year):
    return dict(zip(years, vals))[year]


def _nominal_gdp(ctx) -> dict[int, float]:
    """Calendar-year nominal GDP, £ million — the denominator the ONS's own
    calendar-year percentages are computed on."""
    return dict(zip(*_yr(ctx, "macro/gdp.csv", "gdp_nominal_gbp_mn")))


def _fy_gdp_bn(ctx) -> dict[int, float]:
    """Financial-year nominal GDP, £ billion.

    PESA quotes spending in £ billion on April-March years and the ONS
    publishes that GDP only as a ratio, so the level is recovered from the
    two ratios the PSF files carry: receipts ÷ receipts-as-%-of-GDP and TME
    ÷ TME-as-%-of-GDP. The two agree to well under a point of a percent,
    which is asserted here rather than assumed, and the panel averages them.
    """
    rows = ctx.rows("fiscal/revenue_spending.csv") or {}
    out = {}
    for y, r in sorted(rows.items()):
        try:
            # level_mn / (share / 100) / 1,000 = GDP in £bn
            a = (float(r["receipts_fiscal_gbp_mn"])
                 / float(r["receipts_fiscal_pct_gdp"])) / 10
            b = (float(r["tme_fiscal_gbp_mn"])
                 / float(r["tme_fiscal_pct_gdp"])) / 10
        except (KeyError, TypeError, ValueError):
            continue
        if abs(a - b) / b > 0.005:
            raise AssertionError(
                f"FY{y}: the two implied GDP levels disagree by "
                f"{abs(a - b) / b:.2%}; a denominator this important is not "
                f"guessed at")
        out[y] = (a + b) / 2
    return out


def _note(p, ax, x, y, text, color=None, ha="left", va="top", size=8.0):
    """A short italic note in axes fractions, placed where the reference
    scale is known to leave room."""
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=size, style="italic", color=color or p.MUTED, zorder=7)


def _foot(p, ax, text):
    """The provenance line under a panel."""
    ax.text(0.5, -0.07, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.2, color=p.FAINT, style="italic")


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

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    ry, rv = _yr(ctx, "macro/gdp.csv", "gdp_real_cvm_gbp_mn",
                 since=W0 - 1)
    gy = [y for y in ry if y - 1 in dict(zip(ry, rv)) and y >= W0]
    gv = [(_at(ry, rv, y) / _at(ry, rv, y - 1) - 1) * 100 for y in gy]
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.RED)
    _bands_labelled_at(ig, ax, 0.86, p)
    for y in (2009, 2020):
        v = _at(gy, gv, y)
        ax.annotate(f"{v:.1f}%", (y, v), textcoords="offset points",
                    xytext=(0, -4), ha="center", va="top", fontsize=8.6,
                    fontweight="bold", color=p.RED)
    _foot(p, ax, "ONS national accounts: annual growth computed from the "
          "chained-volume levels")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "international/gdp_pc.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    low = min(zip(py, pv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.30, f"the 2008–09 dollar fall combines a real recession with\n"
          f"sterling depreciation; {low[0]} ({low[1]:,.0f}) is its trough. "
          "The\n2016 and 2022 falls are dominated by the exchange rate", size=7.8)
    _foot(p, ax, "World Bank NY.GDP.PCAP.CD, current US$ at market rates")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year) and the 2% target")
    ax.axhspan(1, 3, color=p.GREEN, alpha=0.07, zorder=0)
    ax.axhline(2, color=p.GREEN_D, lw=1.0, ls=":", zorder=2)
    hy, hv = _yr(ctx, "macro/prices.csv", "cpih_annual_rate_pct")
    cy, cv = _yr(ctx, "macro/prices.csv", "cpi_annual_rate_pct")
    ctx.line(ax, hy, hv, p.NAVY, label="CPIH, including owner-occupiers' "
             "housing costs")
    ctx.line(ax, cy, cv, p.RED, lw=1.8, ms=3.2, label="CPI, the target measure")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, ncol=2, frameon=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(-8, 4), ha="right",
                fontsize=8.8, fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.58, "Bank of England target: 2% on the CPI. The gap "
          "between\nthe two lines is mostly housing costs, which the CPI "
          "leaves out")
    _foot(p, ax, "ONS CPIH and CPI; Eurostat's HICP for the UK stops at 2019")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    uy, uv = _yr(ctx, "macro/labour.csv", "unemployment_rate_pct")
    ctx.line(ax, uy, uv, p.NAVY, label="Labour Force Survey")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "lfs_break", dy=0.30)
    hi = max(zip(uy, uv), key=lambda t: t[1])
    lo = min(zip(uy, uv), key=lambda t: t[1])
    ax.annotate(f"{hi[1]:.1f}% in {hi[0]}", hi, textcoords="offset points",
                xytext=(6, 4), ha="left", fontsize=8.8, fontweight="bold",
                color=p.NAVY)
    ax.annotate(f"{lo[1]:.1f}%", lo, textcoords="offset points",
                xytext=(-2, -12), ha="right", va="top", fontsize=8.4,
                fontweight="bold", color=p.NAVY)
    _note(p, ax, 0.02, 0.96, "the LFS response rate collapsed in 2023-24 and "
          "the ONS\nreweighted the outputs: the 2023-onwards line is a "
          "different\nsurvey, and Eurostat has no UK series to check it "
          "against")
    _foot(p, ax, "ONS Labour Force Survey (ILO definition)")
    _finish(ctx, ig)


# The plates, in the order the page lists them; the ids are the spine's
# chapter numbers, and they match Canada's numbering so the two countries
# line up panel for panel in the comparison viewer.
PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The United Kingdom Economy — Growth, Income, Prices and Jobs",
         subtitle="Two contractions the year can see, and an unemployment "
                  "line that changed survey in 2023.",
         source="Sources: ONS national accounts, CPIH and CPI, Labour Force "
                "Survey · World Bank WDI",
         alt="Four panels on the United Kingdom economy, 2006–2025. Real GDP "
             "fell 4.5% in 2009 and 10.1% in 2020; growth in 2023 was 0.4% "
             "inside a two-quarter technical recession. GDP per person in US "
             "dollars is 57,602 in 2025; its 2008–09 fall combines the real "
             "recession and sterling depreciation, while exchange rates "
             "dominate the 2016 and 2022 falls. Consumer price inflation "
             "peaked at 9.1% on the CPI in 2022 and 7.9% on CPIH, against a "
             "2% target. Unemployment peaked at 8.1% in 2011 and reached a "
             "low of 3.8% in 2019 and 2022 before the survey was reweighted."),
)


# ------------------------------------------------------------------ fiscal
def plate_fiscal(ctx, ig) -> None:
    """IMF general-government flows, with the UK's ONS/PESA public-sector
    measures shown only as separately labelled comparisons.  The perimeters,
    netting and time bases differ and the lines are never spliced."""
    p = ctx.p
    IMF = "international/fiscal_imf.csv"

    ax = ig.slot("fiscal.revenue_expenditure",
                 "Revenue and expenditure (% of GDP)")
    ry, rv = _yr(ctx, IMF, "revenue_pct_gdp")
    ey, ev = _yr(ctx, IMF, "expenditure_pct_gdp")
    ctx.line(ax, ey, ev, p.RED, label="General-government expenditure")
    ctx.line(ax, ry, rv, p.NAVY, label="General-government revenue")
    _bands_labelled_at(ig, ax, 0.88, p)
    pk = max(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{pk[1]:.1f}%", pk, textcoords="offset points",
                xytext=(8, 0), ha="left", va="center", fontsize=8.6,
                fontweight="bold", color=p.RED)
    ax.legend(loc="lower right", fontsize=7.8, ncol=2, frameon=False)
    _note(p, ax, 0.02, 0.74, f"calendar years, general government: the "
          f"{pk[0]} spike is the\npandemic; spending is "
          f"{ev[-1]:.1f}% of GDP in {ey[-1]}, below its 2010 level",
          size=7.8)
    _foot(p, ax, "IMF Fiscal Monitor, general government")

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    by, bal = _yr(ctx, IMF, "overall_balance_pct_gdp")
    ctx.bars(ax, by, bal, lambda v: p.GREEN if v >= 0 else p.RED)
    iy, ival = _yr(ctx, IMF, "primary_balance_pct_gdp")
    ctx.line(ax, iy, ival, p.BLUE, lw=1.8, ms=3.2,
             label="Primary balance")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.8, frameon=False)
    gw = min(zip(by, bal), key=lambda t: t[1])
    ax.annotate(f"{gw[1]:.1f}%", gw, textcoords="offset points",
                xytext=(9, -2), ha="left", va="top", fontsize=8.6,
                fontweight="bold", color=p.RED)
    _foot(p, ax, "IMF Fiscal Monitor; calendar years")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    gy, gv = _yr(ctx, IMF, "gross_debt_pct_gdp")
    gpy, gpval = _yr(ctx, IMF, "gross_debt_pct_gdp_proj")
    ctx.line(ax, gy + gpy, gv + gpval, p.RED,
             label="IMF general government, gross (WEO)")
    dy, dval = _yr(ctx, "fiscal/psnd.csv", "psnd_ex_dec_pct_gdp")
    ctx.line(ax, dy, dval, p.NAVY, lw=1.8, ms=3.2,
             label="ONS PSND, public sector net debt, end-December")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.6, ncol=2, frameon=False)
    gap = _at(gy + gpy, gv + gpval, 2024) - _at(dy, dval, 2024)
    _foot(p, ax, f"IMF general-government gross vs ONS whole-public-sector "
          f"net debt ({gap:.1f} point gap in 2024); 2026 IMF projection")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    gx, gi = _yr(ctx, "fiscal/gfs_operations.csv",
                 "interest_payable_pct_gdp")
    ctx.line(ax, gx, gi, p.PURPLE,
             label="IMF general government, interest payable")
    iy2, i2 = _fy(ctx, "fiscal/spending_by_function.csv",
                  "sub_public_sector_debt_interest_bn")
    fy_gdp = _fy_gdp_bn(ctx)
    ix = [x for x in iy2 if int(x - FY_SHIFT) in fy_gdp]
    iv = [_at(iy2, i2, x) / fy_gdp[int(x - FY_SHIFT)] * 100 for x in ix]
    ctx.line(ax, ix, iv, p.FAINT, ls="--", lw=1.6, ms=3.0,
             label="PESA public-sector debt interest")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _foot(p, ax, "IMF GFS S13 G24_T; PESA Table 4.2 shown separately")
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
#: PESA's national functions, mapped onto the spine's seven COFOG groups.
#: PESA publishes national, not COFOG, classification: the mapping is
#: stated on the panel and in DATA_NOTES, and it is clean for six of the
#: seven groups.
SPEND7 = [
    ("Social protection", ["social_protection_bn"], "RED"),
    ("Health", ["health_bn"], "TEAL"),
    ("Education", ["education_bn"], "GOLD"),
    ("General public services", ["general_public_services_bn"], "PURPLE"),
    ("Economic affairs", ["economic_affairs_bn"], "BLUE"),
    ("Defence and public order", ["defence_bn", "public_order_and_safety_bn"],
     "NAVY"),
    ("Other", ["environment_protection_bn",
               "housing_and_community_amenities_bn",
               "recreation_culture_and_religion_bn"], "FAINT"),
]


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    S = "fiscal/spending_by_function.csv"
    rows = ctx.rows(S, key="fiscal_year") or {}
    years = sorted(y for y in rows if y >= W0)
    xs = [y + FY_SHIFT for y in years]
    fy_gdp = _fy_gdp_bn(ctx)

    def group(cols):
        return [sum(float(rows[y][c]) for c in cols) / fy_gdp[y] * 100
                for y in years]

    ax = ig.slot("spending.by_function", "Spending by function, UK public "
                 "sectors (% of GDP)")
    layers = [(name, group(cols), getattr(p, col))
              for name, cols, col in SPEND7]
    ax.stackplot(xs, *[v for _, v, _ in layers],
                 labels=[n for n, _, _ in layers],
                 colors=[c for _, _, c in layers], alpha=0.9, lw=0)
    _bands_labelled_at(ig, ax, 0.86, p)
    ax.legend(loc="lower left", fontsize=7.0, ncol=3, frameon=False)
    tot = {y: sum(v) for y, v in zip(years, zip(*[v for _, v, _ in layers]))}
    ax.annotate(f"{tot[2024]:.1f}%", (2024 + FY_SHIFT, tot[2024]),
                textcoords="offset points", xytext=(10, -2), ha="left",
                va="center", fontsize=8.6, fontweight="bold", color=p.INK)

    ax = ig.slot("spending.social_protection", "Social protection vs "
                 "everything else (% of GDP)")
    sp = group(["social_protection_bn"])
    rest = [t - s for t, s in zip((tot[y] for y in years), sp)]
    ctx.line(ax, xs, rest, p.NAVY, label="Everything else")
    ctx.line(ax, xs, sp, p.RED, label="Social protection")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    pk = max(zip(years, sp), key=lambda t: t[1])
    ax.annotate(f"{sp[years.index(pk[0])]:.1f}%", (pk[0] + FY_SHIFT,
                sp[years.index(pk[0])]), textcoords="offset points",
                xytext=(-8, 6), ha="right", fontsize=8.4, fontweight="bold",
                color=p.RED)
    _note(p, ax, 0.02, 0.16, f"the biggest single group, and it grows: "
          f"{sp[0]:.1f}% of GDP in\n{years[0]}-11 to {sp[-1]:.1f}% in "
          f"{years[-1]}-{(years[-1] + 1) % 100:02d}, mostly pensions and "
          "benefits uprating", va="bottom", size=7.8)

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(GFCF, % of GDP)")
    iy, iv = _yr(ctx, "international/gfcf.csv", "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.BLUE, lambda v: f"{v:.1f}%", dy=8)
    lo = min(zip(iy, iv), key=lambda t: t[1])
    ax.annotate(f"{lo[1]:.1f}% in {lo[0]}", lo, textcoords="offset points",
                xytext=(8, -12), ha="left", va="top", fontsize=8.2,
                fontweight="bold", color=p.BLUE)
    _note(p, ax, 0.02, 0.96, "the World Bank's harmonised reading of the ONS "
          "national\naccounts: the UK invests a smaller share of its income "
          "than\nevery other G7 economy in the years after 2010")
    _foot(p, ax, "World Bank NE.GDI.FTOT.ZS; the ONS GFCF line itself is not "
          "staged")

    ax = ig.slot("spending.public_investment", "Public investment "
                 "(government GFCF, % of GDP)")
    ctx.pending(ax)
    _note(p, ax, 0.02, 0.86, "no series in the lane: PESA publishes "
          "functional\nspending, not a general-government GFCF, and "
          "Eurostat's\nP51G slice for the UK closed with Brexit "
          "(DATA_NOTES)", size=7.6)
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
PARTNERS = [("United States", "RED"), ("Germany", "NAVY"),
            ("Ireland", "GREEN"), ("France", "BLUE"), ("Netherlands", "PURPLE"),
            ("China", "GOLD")]


def plate_trade(ctx, ig) -> None:
    p = ctx.p
    T = "trade/totals.csv"
    gdp = _nominal_gdp(ctx)

    ax = ig.slot("trade.exports_imports", "Exports and imports of goods "
                 "and services (% of GDP)")
    xy, xv = _yr(ctx, T, "exports_gs_gbp_mn")
    my, mv = _yr(ctx, T, "imports_gs_gbp_mn")
    ctx.line(ax, xy, [v / gdp[y] * 100 for y, v in zip(xy, xv)], p.GREEN,
             label="Exports")
    ctx.line(ax, my, [v / gdp[y] * 100 for y, v in zip(my, mv)], p.RED,
             label="Imports")
    _bands_labelled_at(ig, ax, 0.90, p)
    ax.legend(loc="lower right", fontsize=8.0, frameon=False)
    _note(p, ax, 0.02, 0.74, "balance-of-payments basis, £ divided by nominal "
          "GDP;\nthe World Bank's harmonised openness ratio lands within "
          "1.3\npoints of the sum of these two lines in every year")

    ax = ig.slot("trade.balance", "Trade balance, goods and services "
                 "(% of GDP)")
    bal = [(x - m) / gdp[y] * 100 for y, (x, m) in
           zip(xy, zip(xv, mv))]
    ctx.bars(ax, xy, bal, lambda v: p.GREEN if v >= 0 else p.RED)
    ig.add_recessions(ax, label=False)
    widest = min(zip(xy, bal), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96, f"a deficit in all {len(bal)} years; the "
          f"widest was {widest[1]:.1f}% of GDP\nin {widest[0]}, while the "
          "2022 terms-of-trade shock is visible\nin both gross flows")
    _foot(p, ax, "ONS balance of payments (IKBH, IKBI) ÷ nominal GDP")

    PT = "trade/goods_by_partner.csv"
    table = ctx.table(PT) or {}
    rows = [dict(zip(table, values)) for values in zip(*table.values())]
    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    years = sorted({int(r["year"]) for r in rows})
    last = max(y for y in years if all(int(r["months"]) == 12
                                      for r in _partner_rows(rows, y)))
    ranked = sorted(PARTNERS,
                    key=lambda pr: -_share(rows, last, pr[0]))
    for name, colour in ranked[:6]:
        sy = [y for y in years if y <= last]
        sv = [_share(rows, y, name) for y in sy]
        ctx.line(ax, sy, sv, getattr(p, colour),
                 lw=2.2 if name == "United States" else 1.7, ms=3.4,
                 label=name)
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "customs_break", dy=0.72)
    ax.legend(loc="upper right", fontsize=7.2, ncol=2, frameon=False)
    _note(p, ax, 0.02, 0.96, f"customs-value goods, HMRC; each share uses all "
          f"UK goods\nexports in {last}, including unallocated special buckets.\n"
          f"The EU-intrastat series ends in 2020 and 2021 begins "
          "customs\ndeclarations: a source break, not a trade collapse",
          size=7.4)

    ax = ig.slot("trade.lens", "Lens — the current account "
                 "(% of GDP)")
    cy, cv = _yr(ctx, T, "current_account_gbp_mn")
    cv = [v / gdp[y] * 100 for y, v in zip(cy, cv)]
    ctx.bars(ax, cy, cv, lambda v: p.GREEN if v >= 0 else p.RED_D)
    ax.axhline(0, color=p.MUTED, lw=0.9)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "ONS balance of payments, current account")
    _finish(ctx, ig)


def _partner_rows(rows, year):
    return [r for r in rows if int(r["year"]) == year]


def _share(rows, year, name):
    hit = next((r for r in _partner_rows(rows, year)
                if r["country"] == name), None)
    return float(hit["export_share"]) if hit else 0.0


PLATES += (
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — Revenue, Borrowing, Debt and Interest",
         subtitle="The ONS public-sector accounts beside the IMF's general-government reading.",
         source="Sources: IMF Fiscal Monitor, WEO and GFS · ONS Public Sector Finances · HM Treasury PESA",
         alt="Four panels on United Kingdom public finances: receipts and spending, borrowing, debt and debt interest, all as shares of GDP."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Where the Money Goes — Functions and Investment",
         subtitle="Treasury functions in financial years, and the whole economy's investment rate.",
         source="Sources: HM Treasury PESA · ONS Public Sector Finances · World Bank WDI",
         alt="Four panels on United Kingdom spending: seven functional groups, social protection, whole-economy investment and the unavailable public-investment series."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — the Balance, the Partners and the Current Account",
         subtitle="National-accounts trade beside customs-value goods, with the 2021 collection break shown.",
         source="Sources: ONS balance of payments · HMRC UK Trade Info",
         alt="Four panels on United Kingdom trade: exports and imports, the trade balance, leading goods destinations as shares of all UK goods exports, and a current-account balance that remained in deficit throughout, including minus 0.84% of GDP in 2021."),
)


# ---------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p
    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ry, rv = _yr(ctx, "markets/bank_rate.csv", "bank_rate_avg")
    cy, cv = _yr(ctx, "macro/prices.csv", "cpi_annual_rate_pct")
    ctx.line(ax, cy, cv, p.RED, label="CPI inflation")
    ctx.line(ax, ry, rv, p.NAVY, label="Bank Rate, annual average")
    _bands_labelled_at(ig, ax, 0.82, p)
    ax.legend(loc="upper left", fontsize=8, frameon=False)

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    gy, gv = _yr(ctx, "markets/gilt_yield.csv", "gilt_10y_avg")
    ctx.line(ax, gy, gv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.PURPLE, lambda v: f"{v:.1f}%", dy=8)

    ax = ig.slot("markets.currency", "Sterling against the US$ "
                 "(index 2006 = 100, up = stronger)")
    fy, fv = _yr(ctx, "markets/sterling.csv", "usd_per_gbp_avg")
    ix_y, ix_v = ctx.index_2006(dict(zip(fy, fv)))
    ctx.line(ax, ix_y, ix_v, p.NAVY)
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "referendum", dy=0.20)

    ax = ig.slot("markets.equities", "FTSE 100 in US$ "
                 "(index 2006 = 100)")
    ft_y, ft_v = _yr(ctx, "markets/ftse.csv", "close")
    eoy_y, eoy_v = _yr(ctx, "markets/sterling.csv", "usd_per_gbp_eoy")
    fx = dict(zip(eoy_y, eoy_v))
    ft_usd = {y: v * fx[y] for y, v in zip(ft_y, ft_v) if y in fx}
    sp_y, sp_v = _yr(ctx, "markets/sp500.csv", "close")
    a_y, a_v = ctx.index_2006(ft_usd)
    assert abs(_at(a_y, a_v, 2024) - 84.11) < 0.02
    assert abs(_at(a_y, a_v, 2025) - 109.73) < 0.02
    b_y, b_v = ctx.index_2006(dict(zip(sp_y, sp_v)))
    ctx.line(ax, a_y, a_v, p.RED, label="FTSE 100, converted to US$")
    ctx.line(ax, b_y, b_v, p.FAINT, ls="--", label="S&P 500, US$")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    _finish(ctx, ig)


# ----------------------------------------------------------------- credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p
    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    dy, dv = _yr(ctx, "credit/household_credit.csv",
                 "household_credit_pct_gdp_q4")
    ctx.line(ax, dy, dv, p.NAVY)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.NAVY, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.90, "BIS total credit to households and NPISHs; Q4 stock.\n"
          "2026 is omitted because only Q1 is available.")

    ax = ig.slot("credit.lending_rate", "Mortgage rates vs the policy rate (%)")
    my, mv = _yr(ctx, "credit/mortgage_rate.csv", "mortgage_2y_60ltv_avg")
    ry, rv = _yr(ctx, "markets/bank_rate.csv", "bank_rate_avg")
    ctx.line(ax, my, mv, p.RED, label="Two-year mortgage, 60% LTV")
    ctx.line(ax, ry, rv, p.NAVY, label="Bank Rate")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=8, frameon=False)

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    ny, nv = _yr(ctx, "credit/npl.csv", "npl_pct")
    ctx.line(ax, ny, nv, p.RED)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ny, nv, p.RED, lambda v: f"{v:.2f}%", dy=8)
    _note(p, ax, 0.02, 0.90, "Bank non-performing loans; IMF Financial Soundness\n"
          "Indicator distributed by the World Bank.")

    ax = ig.slot("credit.lens", "Lens — household debt "
                 "(% of disposable income)")
    hy, hv = _yr(ctx, "credit/household_debt.csv", "hh_debt_to_income_pct_q4")
    ctx.line(ax, hy, hv, p.GOLD)
    ig.add_recessions(ax, label=False)
    _finish(ctx, ig)


PLATES += (
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Money & Markets — Rates, Sterling and the FTSE",
         subtitle="Bank Rate and gilts beside sterling and London equities in US dollars.",
         source="Sources: Bank of England · ONS · Yahoo Finance",
         alt="Four panels on UK markets show Bank Rate against inflation, the ten-year gilt yield, sterling against the dollar, and the FTSE 100 converted to US dollars against the S&P 500."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Household Credit — Mortgage Rates and Debt",
         subtitle="Household leverage on two denominators, with mortgage rates and bank bad loans.",
         source="Sources: BIS · World Bank/IMF FSI · Bank of England · ONS",
         alt="Four panels on UK credit show household credit as a share of GDP, mortgage rates against Bank Rate, bank non-performing loans, and household debt as a share of disposable income."),
)


# ----------------------------------------------------------------- people
def plate_people(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("people.gini", "Income inequality, Gini "
                 "(0–100, higher = more unequal)")
    oy, ov = _fy(ctx, "social/gini.csv", "gini_pct")
    wy, wv = _yr(ctx, "international/gini.csv", "gini")
    ctx.line(ax, oy, ov, p.PURPLE,
             label="ONS, disposable income (financial year)")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.7, ms=3.2,
             label="World Bank (calendar year)")
    _bands_labelled_at(ig, ax, 0.10, p)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.96, "two definitions from the same survey family, not two\n"
          "measurements of one number; the World Bank series ends in 2021",
          size=7.7)
    _foot(p, ax, "ONS FYE series is drawn at the financial-year midpoint; "
          "World Bank is calendar-year")

    ax = ig.slot("people.poverty", "Relative low income "
                 "(% of people)")
    by, bv = _fy(ctx, "social/poverty.csv",
                 "relative_low_income_bhc_pct")
    ay, av = _fy(ctx, "social/poverty.csv",
                 "relative_low_income_ahc_pct")
    wy, wv = _yr(ctx, "international/poverty.csv",
                 "poverty_at_8_30_2021_ppp_pct")
    ctx.line(ax, by, bv, p.BLUE, label="Before housing costs")
    ctx.line(ax, ay, av, p.RED, label="After housing costs")
    ctx.line(ax, wy, wv, p.FAINT, lw=1.7, ms=3.2,
             label="Below US$8.30/day (World Bank)")
    ig.add_recessions(ax, label=False)
    ig.add_event(ax, *events.MARKS["hbai_seam"], dy=0.54, fontsize=7.0)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.66, "the DWP lines are relative to that year's median; the\n"
          "World Bank line is an absolute international threshold",
          va="bottom", size=7.7)
    _foot(p, ax, "DWP HBAI, UK (financial-year midpoint); World Bank "
          "SI.POV.UMIC (calendar year)")

    ax = ig.slot("people.minimum_wage", "Minimum wage "
                 "(US$ per month)")
    my, mv = _yr(ctx, "social/minimum_wage.csv", "adult_rate_usd_month")
    ctx.line(ax, my, mv, p.GREEN_D, label="Statutory adult rate")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, my, mv, p.GREEN_D, lambda v: f"US${v:,.0f}", dy=-24)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    _note(p, ax, 0.98, 0.05, "calendar-year average of the adult hourly floor;\n"
          "40 hours/week × 52 ÷ 12, at annual-average USD/GBP",
          ha="right", va="bottom", size=7.6)
    _foot(p, ax, "Low Pay Commission statutory-rate history; Bank of England "
          "exchange rate (2026 year-to-date)")

    ax = ig.slot("people.lens", "Lens — top 1% share of household income "
                 "(%)")
    ty, tv = _fy(ctx, "social/gini.csv", "top1_share_pct")
    ctx.line(ax, ty, tv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ax.set_ylabel("% of household income", fontsize=8.6, color=p.MUTED)
    ax.set_ylim(0, 12)
    _note(p, ax, 0.02, 0.96, f"equivalised disposable household income, adjusted\n"
          f"for top-earner under-coverage; {tv[-1]:.1f}% in FY{int(ty[-1] - FY_SHIFT)}-"
          f"{(int(ty[-1] - FY_SHIFT) + 1) % 100:02d}",
          size=7.7)
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "international/gdp_usd.csv", "gdp_usd")
    gv = [v / 1e9 for v in gv]
    ctx.line(ax, gy, gv, p.NAVY)
    _bands_labelled_at(ig, ax, 0.10, p)
    ctx.endlabel(ax, gy, gv, p.NAVY, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, "current dollars at market exchange rates: sterling's\n"
          "moves are part of this line, not changes in real output", size=7.7)

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "international/hdi.csv", "hdi")
    ctx.line(ax, hy, hv, p.GREEN_D, split_year=max(hy))
    ax.axhline(0.8, color=p.FAINT, lw=0.9, ls=":")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, hy, hv, p.GREEN_D, lambda v: f"{v:.3f}", dy=8)
    _note(p, ax, 0.98, 0.62, "0.800 and above = very high development",
          ha="right", size=7.7)
    _foot(p, ax, "one HDR 2025 vintage throughout; UNDP recomputes the "
          "back-series")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index "
                 "(0–100, higher = cleaner)")
    oy, ov = _yr(ctx, "international/cpi.csv", "cpi_pre2012_0_10")
    ny, nv = _yr(ctx, "international/cpi.csv", "cpi_2012_method_0_100")
    # Keep the publisher's old 0-10 values untouched in the CSV. Multiplying
    # only for screen position lets both scales share the panel while the gap,
    # event rule and label make clear that this is not one comparable series.
    ctx.line(ax, oy, [v * 10 for v in ov], p.FAINT, lw=1.7, ms=3.2,
             label="2006–11 old method (0–10, positioned ×10)")
    ctx.line(ax, ny, nv, p.PURPLE, label="2012 method (0–100)")
    ig.add_recessions(ax, label=False)
    ig.add_event(ax, 2011.5, "method and scale change", dy=0.94)
    ax.legend(loc="lower left", fontsize=7.3, frameon=False)
    ctx.endlabel(ax, ny, nv, p.PURPLE, lambda v: f"{v:.0f}", dy=8)
    _note(p, ax, 0.98, 0.96, "only scores from 2012 onward are comparable over time",
          ha="right", size=7.5)
    _foot(p, ax, "Transparency International CPI; official annual archives "
          "and CPI 2025 results workbook")

    ax = ig.slot("world.reserves", "Official reserves including gold "
                 "(US$ bn)")
    ry, rv = _yr(ctx, "international/reserves.csv", "reserves_usd")
    rv = [v / 1e9 for v in rv]
    ctx.line(ax, ry, rv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.GOLD, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96, "small beside the largest reserve holders by design:\n"
          "sterling floats, so there is no exchange-rate peg to defend",
          size=7.7)
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def _ons_december_net_migration(ctx):
    """Calendar-year ONS net migration: only rolling years ending December.

    The source also carries March, June and September rolling years. Treating
    those as annual calendar observations would put four incompatible periods
    on one year, so this deliberately selects YE December before conversion.
    """
    table = ctx.table("migration/flows.csv") or {}
    out = []
    for period, flow, value in zip(table.get("period_end", []),
                                   table.get("flow", []),
                                   table.get("all_nationalities", [])):
        if isinstance(period, str) and period.endswith("-12") and flow == "net":
            out.append((int(period[:4]), float(value)))
    return dict(out)


def plate_demography(ctx, ig) -> None:
    p = ctx.p
    pop = dict(zip(*_yr(ctx, "demography/population.csv", "population_uk")))

    ax = ig.slot("demography.population", "Population "
                 "(index 2006 = 100)")
    iy, iv = ctx.index_2006(pop)
    ctx.line(ax, iy, iv, p.BLUE)
    _bands_labelled_at(ig, ax, 0.10, p)
    last = max(pop)
    ctx.endlabel(ax, iy, iv, p.BLUE,
                 lambda v: f"{pop[last] / 1e6:.1f}mn", dy=8)
    _note(p, ax, 0.02, 0.96, f"ONS mid-year residents: {pop[W0] / 1e6:.1f}mn in "
          f"{W0} and {pop[last] / 1e6:.1f}mn in {last};\none census-rebased "
          "vintage throughout", size=7.7)

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    ty, tv = _yr(ctx, "demography/fertility.csv", "tfr")
    ax.axhline(2.1, color=p.FAINT, lw=1.0, ls=":")
    ctx.line(ax, ty, tv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ty, tv, p.PURPLE, lambda v: f"{v:.2f}", dy=8)
    _note(p, ax, 0.98, 0.96, "2.1 = replacement level", ha="right",
          size=7.7)
    _note(p, ax, 0.02, 0.18, f"World Bank modelled series through {ty[-1]}; "
          "the Eurostat UK\nseries stops in 2018 and is not spliced onto it",
          va="bottom", size=7.7)
    _foot(p, ax, "World Bank SP.DYN.TFRT.IN; children per woman")

    ax = ig.slot("demography.birth_death", "Births and deaths "
                 "(per 1,000 people, UK)")
    births = dict(zip(*_yr(ctx, "demography/demography.csv", "births")))
    deaths = dict(zip(*_yr(ctx, "demography/demography.csv", "deaths")))
    by, bv = ctx.per_1000(births, pop)
    dy, dv = ctx.per_1000(deaths, pop)
    ctx.line(ax, by, bv, p.GREEN, label="Births")
    ctx.line(ax, dy, dv, p.RED_D, label="Deaths")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=8.0, frameon=False)
    _note(p, ax, 0.02, 0.96, "Eurostat UK counts divided by the ONS mid-year UK\n"
          "population of the same year; never mixed with the\n"
          "England & Wales registration series", size=7.5)

    ax = ig.slot("demography.natural_migration", "Natural increase and "
                 "net migration (per 1,000 people)")
    natural = {y: births[y] - deaths[y] for y in births
               if y in deaths and y in pop}
    ny, nv = ctx.per_1000(natural, pop)
    ctx.bars(ax, ny, nv, lambda v: p.GREEN if v >= 0 else p.RED_D)
    net = _ons_december_net_migration(ctx)
    ei_y, ei_v = _yr(ctx, "migration/flows_estat.csv",
                     "immigration_by_citizenship_total")
    ee_y, ee_v = _yr(ctx, "migration/flows_estat.csv",
                     "emigration_by_citizenship_total")
    estat_imm, estat_emi = dict(zip(ei_y, ei_v)), dict(zip(ee_y, ee_v))
    estat = {y: estat_imm[y] - estat_emi[y] for y in estat_imm
             if y in estat_emi}
    before = {y: v for y, v in net.items() if y <= 2020}
    after = {y: v for y, v in net.items() if y >= 2021}
    ctx.line(ax, *ctx.per_1000(estat, pop), p.FAINT, lw=1.7, ms=3.2,
             label="Eurostat IPS-era segment (to 2019)")
    ctx.line(ax, *ctx.per_1000(before, pop), p.NAVY,
             label="ONS new approach, to March 2021")
    ctx.line(ax, *ctx.per_1000(after, pop), p.NAVY, ls=(0, (2, 2)),
             label="ONS fully administrative, from June 2021")
    ax.plot([], [], color=p.GREEN, lw=6, label="Natural increase")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "ltim_admin", dy=0.94)
    ax.legend(loc="upper left", fontsize=6.9, frameon=False)
    _note(p, ax, 0.98, 0.05, "Eurostat calendar-year and ONS YE-December estimates\n"
          "overlap but are labelled separately and never spliced",
          ha="right", va="bottom",
          size=7.4)
    _finish(ctx, ig)


PLATES += (
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="People — Inequality, Poverty and the Income Floor",
         subtitle="Household inequality, two poverty concepts and the statutory adult wage floor.",
         source="Sources: ONS · DWP HBAI · Low Pay Commission · World Bank WDI",
         alt="Four panels on people in the United Kingdom: two definitions of the Gini index; relative low income before and after housing costs beside the World Bank absolute poverty threshold; the statutory adult minimum wage converted to a monthly US-dollar equivalent; and the top one percent income share."),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="The United Kingdom in the World — Size and Development",
         subtitle="Current-dollar output, human development, corruption perceptions and reserves.",
         source="Sources: World Bank WDI · UNDP Human Development Report · Transparency International",
         alt="Four panels place the United Kingdom in the world through current-dollar GDP, human development, two separately labelled corruption-index method segments, and official reserves including gold."),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — Growth, Fertility and the Two Balances",
         subtitle="UK population and vital counts, with the June 2021 migration-method seam kept visible.",
         source="Sources: ONS · Eurostat · World Bank WDI",
         alt="Four panels on United Kingdom demography: population indexed to 2006, World Bank fertility, Eurostat birth and death rates, and natural increase beside separately labelled Eurostat and ONS net-migration segments."),
)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    pop_t = ctx.table("demography/population.csv") or {}
    ew_pop = {
        y: e + w for y, e, w in zip(pop_t.get("year", []),
                                    pop_t.get("population_england", []),
                                    pop_t.get("population_wales", []))
    }

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000, "
                 "England & Wales; log scale)")
    police = ctx.rows("security/homicide_police.csv",
                      key="fiscal_year") or {}
    police_rate = {
        y + FY_SHIFT: float(r["offences_currently_recorded"])
        / ew_pop[y] * 100_000
        for y, r in police.items()
        if y >= W0 and y in ew_pop and r.get("offences_currently_recorded")
    }
    cert_y, cert_v = _yr(ctx, "security/homicide_deaths.csv",
                         "homicide_ons_definition", since=2007)
    cert = {y: v / ew_pop[y] * 100_000 for y, v in zip(cert_y, cert_v)
            if y in ew_pop}
    ctx.line(ax, *zip(*sorted(police_rate.items())), p.RED,
             label="Home Office Homicide Index — police-recorded (year ending March)")
    ctx.line(ax, *zip(*sorted(cert.items())), p.PURPLE,
             label="Death certificate, ONS definition (calendar year)")
    ig.add_recessions(ax, inside=True, label=False)
    ax.legend(loc="upper right", fontsize=7.5, frameon=False)
    _note(p, ax, 0.02, 0.08, "two publishers and two reference periods; the lines\n"
          "are separately rated and never joined", va="bottom", size=7.5)
    _foot(p, ax, "same-year ONS England & Wales population; certificate "
          "line starts in 2007 after the Y33.9-to-U50.9 coding break")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000, UK)")
    sy, sv = _yr(ctx, "international/suicide.csv", "suicide_per_100k")
    ctx.line(ax, sy, sv, p.PURPLE, split_year=max(sy),
             label="WHO age-standardised estimate")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, sy, sv, p.PURPLE, lambda v: f"{v:.1f}", dy=8)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.96, f"publisher-supplied UK rate; the series ends in {sy[-1]}",
          size=7.7)
    _foot(p, ax, "WHO Global Health Observatory via World Bank "
          "SH.STA.SUIC.P5; rate is not recomputed")

    ax = ig.slot("security.road_deaths", "Road traffic deaths "
                 "(per 100,000, UK)")
    ry, rv = _yr(ctx, "international/road_deaths.csv",
                 "road_deaths_per_100k")
    ctx.line(ax, ry, rv, p.GOLD, split_year=max(ry),
             label="WHO estimate")
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.GOLD, lambda v: f"{v:.1f}", dy=8)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.96, f"publisher-supplied UK rate; the series ends in {ry[-1]}",
          size=7.7)
    _foot(p, ax, "WHO Global Health Observatory via World Bank "
          "SH.STA.TRAF.P5; rate is not recomputed")

    ax = ig.slot("security.lens", "Lens — police-recorded homicide revisions "
                 "(England & Wales)")
    py, initial = _fy(ctx, "security/homicide_police.csv",
                      "offences_initially_recorded")
    _, current = _fy(ctx, "security/homicide_police.csv",
                     "offences_currently_recorded")
    ctx.line(ax, py, initial, p.FAINT, lw=1.7, ms=3.2,
             label="Initially recorded")
    ctx.line(ax, py, current, p.RED_D, label="Currently recorded")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    ax.set_ylabel("offences", fontsize=8.6, color=p.MUTED)
    _foot(p, ax, "initially vs currently recorded; later reclassification "
          "changes history; financial-year midpoint")
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
def _cause(ctx, chapter: str) -> dict[int, float]:
    table = ctx.table("mortality/causes_of_death.csv") or {}
    out = {}
    for year, key, deaths in zip(table.get("year", []),
                                 table.get("chapter", []),
                                 table.get("deaths", [])):
        if key == chapter and year >= W0:
            out[year] = float(deaths)
    return out


def _cause_segments(ctx, ax, counts, pop, color, label):
    # Five unjoined production regimes. The year at each boundary belongs
    # to the NEW regime: 2011's ICD update, IRIS from 2014, MUSE from 2020,
    # and the updated MUSE implementation from 2022. A single 2015–2025
    # segment would silently erase two software changes.
    regimes = (
        (W0, 2010, "-"),
        (2011, 2013, (0, (5, 2))),
        (2014, 2019, "-"),
        (2020, 2021, (0, (3, 2))),
        (2022, 2026, (0, (1, 1.5))),
    )
    for index, (start, end, ls) in enumerate(regimes):
        part = {y: v for y, v in counts.items()
                if start <= y <= end and y in pop}
        if not part:
            continue
        ctx.line(ax, *ctx.per_100k(part, pop), color,
                 label=label if index == 0 else "_nolegend_", ls=ls,
                 dashed_partial=False, split_year=max(part) + 1)


def plate_mortality(ctx, ig) -> None:
    p = ctx.p
    pop_t = ctx.table("demography/population.csv") or {}
    ew_pop = {
        y: e + w for y, e, w in zip(pop_t.get("year", []),
                                    pop_t.get("population_england", []),
                                    pop_t.get("population_wales", []))
    }
    vy, deaths_v = _yr(ctx, "demography/vital.csv", "deaths")
    deaths = dict(zip(vy, deaths_v))

    ax = ig.slot("mortality.death_rate", "Crude death rate "
                 "(per 1,000, England & Wales)")
    dy, dv = _yr(ctx, "demography/vital.csv",
                 "crude_death_rate_per_1000")
    ctx.line(ax, dy, dv, p.RED_D)
    ig.add_recessions(ax, inside=True, label=False)
    ctx.endlabel(ax, dy, dv, p.RED_D, lambda v: f"{v:.1f}", dy=8)
    _note(p, ax, 0.02, 0.96, "the ONS published crude rate, not a rate rebuilt\n"
          "from a differently scoped population series", size=7.7)
    _foot(p, ax, "ONS deaths registered, England & Wales, calendar year")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above the 2015–2019 average)")
    base = sum(deaths[y] for y in range(2015, 2020)) / 5
    excess = {y: (deaths[y] / base - 1) * 100 for y in deaths if y >= 2015}
    ex_y = sorted(excess)
    ex_v = [excess[y] for y in ex_y]
    ctx.bars(ax, ex_y, ex_v, lambda v: p.RED if v > 0 else p.GREEN)
    ig.add_recessions(ax, label=False)
    peak = max(zip(ex_y, ex_v), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:+.1f}%", peak, textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=8.5,
                fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.96, f"fixed baseline: {base:,.0f} registered deaths, the 2015–19 mean;\n"
          "not adjusted for population growth or ageing", size=7.7)
    _foot(p, ax, "computed from the same ONS vital-deaths series as slot 1")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    ctx.pending(ax)
    _note(p, ax, 0.02, 0.86, "exact U07.1/U07.2 deaths are not staged; ICD-10 chapter 22\n"
          "also contains other special-purpose codes and is not a proxy",
          size=7.7)
    _foot(p, ax, "deliberately pending — never substituted with chapter 22")

    ax = ig.slot("mortality.lens", "Lens — neoplasms and circulatory "
                 "diseases (per 100,000)")
    _cause_segments(ctx, ax, _cause(ctx, "ch2"), ew_pop, p.NAVY,
                    "Neoplasms")
    _cause_segments(ctx, ax, _cause(ctx, "ch9"), ew_pop, p.RED,
                    "Circulatory diseases")
    ig.add_recessions(ax, label=False)
    for key, dy in (("icd2011", 0.96), ("iris", 0.86),
                    ("muse", 0.72), ("muse_update", 0.86)):
        _mark(ig, ax, key, dy=dy)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    _note(p, ax, 0.02, 0.08, "underlying-cause chapter totals exclude neonatal deaths;\n"
          "five unjoined coding/software regimes; boundary year is new regime",
          va="bottom", size=7.5)
    _foot(p, ax, "ONS Series DR / 21st Century Mortality; England & Wales")
    _finish(ctx, ig)


# ---------------------------------------------------------------- migration
def _ons_december_flows(ctx):
    table = ctx.table("migration/flows.csv") or {}
    out = {"immigration": {}, "emigration": {}, "net": {}}
    for period, flow, value in zip(table.get("period_end", []),
                                   table.get("flow", []),
                                   table.get("all_nationalities", [])):
        if (isinstance(period, str) and period.endswith("-12")
                and flow in out and value == value):
            out[flow][int(period[:4])] = float(value)
    return out


def _ons_method_parts(series):
    return ({y: v for y, v in series.items() if y <= 2020},
            {y: v for y, v in series.items() if y >= 2021})


def plate_migration(ctx, ig) -> None:
    p = ctx.p
    pop = dict(zip(*_yr(ctx, "demography/population.csv", "population_uk")))
    ons = _ons_december_flows(ctx)
    ei_y, ei_v = _yr(ctx, "migration/flows_estat.csv",
                     "immigration_by_citizenship_total")
    ee_y, ee_v = _yr(ctx, "migration/flows_estat.csv",
                     "emigration_by_citizenship_total")
    estat_i, estat_e = dict(zip(ei_y, ei_v)), dict(zip(ee_y, ee_v))

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people, UK)")
    ctx.line(ax, *ctx.per_1000(estat_i, pop), p.FAINT, lw=1.6, ms=3.0,
             label="Eurostat immigration, IPS-era")
    ctx.line(ax, *ctx.per_1000(estat_e, pop), p.FAINT, lw=1.6, ms=3.0,
             ls=(0, (2, 2)), label="Eurostat emigration, IPS-era")
    for flow, color, noun in (("immigration", p.NAVY, "Immigration"),
                              ("emigration", p.RED, "Emigration")):
        before, after = _ons_method_parts(ons[flow])
        ctx.line(ax, *ctx.per_1000(before, pop), color,
                 label=f"ONS {noun}, pre-June 2021")
        ctx.line(ax, *ctx.per_1000(after, pop), color, ls=(0, (2, 2)),
                 label=f"ONS {noun}, from June 2021")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "ltim_admin", dy=0.96)
    ax.legend(loc="upper left", fontsize=6.6, ncol=2, frameon=False)
    _note(p, ax, 0.98, 0.66, "Eurostat calendar years and ONS YE-December overlap;\n"
          "the labelled systems are never joined", ha="right", va="bottom",
          size=7.3)

    ax = ig.slot("migration.net", "Net migration "
                 "(per 1,000 people, UK)")
    estat_net = {y: estat_i[y] - estat_e[y] for y in estat_i if y in estat_e}
    ctx.line(ax, *ctx.per_1000(estat_net, pop), p.FAINT, lw=1.7, ms=3.2,
             label="Eurostat, immigration minus emigration")
    before, after = _ons_method_parts(ons["net"])
    ctx.line(ax, *ctx.per_1000(before, pop), p.BLUE,
             label="ONS published net, pre-June 2021")
    ctx.line(ax, *ctx.per_1000(after, pop), p.BLUE, ls=(0, (2, 2)),
             label="ONS published net, from June 2021")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "ltim_admin", dy=0.96)
    ax.legend(loc="upper left", fontsize=7.1, frameon=False)
    _note(p, ax, 0.98, 0.06, "the ONS row is the publisher's net estimate — never\n"
          "rounded immigration minus rounded emigration", ha="right",
          va="bottom", size=7.4)

    ax = ig.slot("migration.foreign_born", "Foreign-born and foreign-citizen "
                 "shares (%)")
    stocks = ctx.rows("migration/stocks.csv") or {}
    born, citizen = {}, {}
    for y, r in stocks.items():
        try:
            bt, bn = float(r["stock_by_birth_total"]), float(r["stock_by_birth_national"])
            born[y] = (bt - bn) / bt * 100
        except (KeyError, TypeError, ValueError):
            pass
        try:
            ct, cn = float(r["stock_by_citizenship_total"]), float(r["stock_by_citizenship_national"])
            citizen[y] = (ct - cn) / ct * 100
        except (KeyError, TypeError, ValueError):
            pass
    ctx.line(ax, *zip(*sorted(born.items())), p.PURPLE,
             label="Foreign-born")
    ctx.line(ax, *zip(*sorted(citizen.items())), p.GOLD,
             label="Foreign citizen")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    _foot(p, ax, "each share uses its own Eurostat classification total, "
          "not ONS population; 1 January stocks frozen after 2019")

    ax = ig.slot("migration.lens", "Lens — asylum applications and casework "
                 "(thousands of people)")
    ay, applications = _yr(ctx, "migration/asylum.csv", "applications_persons")
    _, decisions = _yr(ctx, "migration/asylum.csv", "initial_decisions_persons")
    _, initial_grants = _yr(ctx, "migration/asylum.csv",
                            "initial_grants_persons")
    by, backlog = _yr(ctx, "migration/asylum.csv",
                      "awaiting_initial_decision_31dec_persons")
    ctx.line(ax, ay, [v / 1_000 for v in applications], p.NAVY,
             label="Asylum applications (flow)")
    ctx.line(ax, ay, [v / 1_000 for v in decisions], p.GREEN_D,
             label="Initial decisions (flow)")
    ctx.line(ax, ay, [v / 1_000 for v in initial_grants], p.GOLD,
             label="Initial grants (flow)")
    ctx.line(ax, by, [v / 1_000 for v in backlog], p.RED,
             label="Awaiting initial decision, 31 Dec (stock)")
    ig.add_recessions(ax, label=False)
    ax.set_ylabel("thousand people", fontsize=8.3, color=p.MUTED)
    ax.legend(loc="upper left", fontsize=7.0, ncol=2, frameon=False)
    _foot(p, ax, "applications, initial decisions and grants are annual "
          "flows; awaiting-decision backlog is a 31 December stock")
    _finish(ctx, ig)


PLATES += (
    dict(id="10", slug="security", topic="security", builder=plate_security,
         title="Security — Homicide, Suicide and Road Deaths",
         subtitle="England & Wales homicide systems beside comparable WHO rates for the UK.",
         source="Sources: Home Office Homicide Index · ONS · WHO / World Bank WDI",
         alt="Four panels on security: separately labelled police-recorded and death-certificate homicide rates for England and Wales; WHO suicide and road-death rates for the UK; and revisions to the police-recorded homicide count."),
    dict(id="11", slug="mortality", topic="mortality", builder=plate_mortality,
         title="Mortality — Registered Deaths and the Classification Seam",
         subtitle="England & Wales registrations, with exact COVID deaths left pending rather than proxied.",
         source="Sources: ONS vital statistics · ONS Series DR · 21st Century Mortality",
         alt="Four panels on mortality in England and Wales: the published crude death rate, deaths relative to the fixed 2015 to 2019 mean, a visibly pending exact COVID-death slot, and neoplasm and circulatory-disease rates split into the five regimes created by the 2011, 2014, 2020 and 2022 coding and software changes."),
    dict(id="12", slug="migration", topic="migration", builder=plate_migration,
         title="Migration — Two Systems, Stocks and Paperwork",
         subtitle="Eurostat's IPS-era record and the ONS administrative estimates overlap but never join.",
         source="Sources: Eurostat · ONS long-term international migration · Home Office",
         alt="Four panels on UK migration: separately labelled Eurostat and ONS immigration and emigration, published net migration, Eurostat foreign-born and foreign-citizen shares using their own totals, and Home Office asylum applications, initial decisions and grants as flows beside the year-end backlog stock."),
)
