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
    return dict(zip(*_yr(ctx, "macro/gdp_from_ons.csv", "gdp_nominal_gbp_mn")))


def _fy_gdp_bn(ctx) -> dict[int, float]:
    """Financial-year nominal GDP, £ billion.

    PESA quotes spending in £ billion on April-March years and the ONS
    publishes that GDP only as a ratio, so the level is recovered from the
    two ratios the PSF files carry: receipts ÷ receipts-as-%-of-GDP and TME
    ÷ TME-as-%-of-GDP. The two agree to well under a point of a percent,
    which is asserted here rather than assumed, and the panel averages them.
    """
    rows = ctx.rows("fiscal/revenue_spending_from_ons.csv") or {}
    out = {}
    for y, r in sorted(rows.items()):
        try:
            a = (float(r["receipts_fiscal_gbp_mn"])
                 / float(r["receipts_fiscal_pct_gdp"])) / 1e3
            b = (float(r["tme_fiscal_gbp_mn"])
                 / float(r["tme_fiscal_pct_gdp"])) / 1e3
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
    ry, rv = _yr(ctx, "macro/gdp_from_ons.csv", "gdp_real_cvm_gbp_mn",
                 since=W0 - 1)
    gy = [y for y in ry if y - 1 in dict(zip(ry, rv)) and y >= W0]
    gv = [(g := _at(ry, rv, y) / _at(ry, rv, y - 1) - 1) * 100 for y in gy]
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.RED)
    _bands_labelled_at(ig, ax, 0.86, p)
    for y in (2009, 2020):
        v = _at(gy, gv, y)
        ax.annotate(f"{v:.1f}%", (y, v), textcoords="offset points",
                    xytext=(0, -4), ha="center", va="top", fontsize=8.6,
                    fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.72, f"the annual figure understates all three "
          f"downturns: 2008 grew\n{_at(gy, gv, 2008):.1f}% before it fell, and "
          f"the two-quarter recession of\n2023-24 costs "
          f"{abs(_at(gy, gv, 2024) - _at(gy, gv, 2023)):.1f} points of growth",
          size=7.8)
    _foot(p, ax, "ONS national accounts: annual growth computed from the "
          "chained-volume levels")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "international/gdp_pc_from_wb.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    low = min(zip(py, pv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.30, f"three falls in US dollars, none of them in "
          f"output:\n{low[0]} ({low[1]:,.0f}) is the oil-and-sterling year, "
          "2016 and\n2022 are sterling's own", size=7.8)
    _foot(p, ax, "World Bank NY.GDP.PCAP.CD, current US$ at market rates")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year) and the 2% target")
    ax.axhspan(1, 3, color=p.GREEN, alpha=0.07, zorder=0)
    ax.axhline(2, color=p.GREEN_D, lw=1.0, ls=":", zorder=2)
    hy, hv = _yr(ctx, "macro/prices_from_ons.csv", "cpih_annual_rate_pct")
    cy, cv = _yr(ctx, "macro/prices_from_ons.csv", "cpi_annual_rate_pct")
    ctx.line(ax, hy, hv, p.NAVY, label="CPIH, including owner-occupiers' "
             "housing costs")
    ctx.line(ax, cy, cv, p.RED, lw=1.8, ms=3.2, label="CPI, the target measure")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "mini_budget", dy=0.44)
    ax.legend(loc="lower left", fontsize=7.4, ncol=2, frameon=False)
    peak = max(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(-8, 4), ha="right",
                fontsize=8.8, fontweight="bold", color=p.RED)
    _note(p, ax, 0.02, 0.96, "Bank of England target: 2% on the CPI. The gap "
          "between\nthe two lines is mostly housing costs, which the CPI "
          "leaves out")
    _foot(p, ax, "ONS CPIH and CPI; Eurostat's HICP for the UK stops at 2019")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    uy, uv = _yr(ctx, "macro/labour_from_ons.csv", "unemployment_rate_pct")
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
             "dollars is about 54,000 in 2025 after falls in 2008, 2016 and "
             "2022 that came from the exchange rate. Consumer price inflation "
             "peaked at 9.1% on the CPI in 2022 and 7.9% on CPIH, against a "
             "2% target. Unemployment peaked at 8.1% in 2011 and reached a "
             "low of 3.8% in 2023 before the survey was reweighted."),
)
