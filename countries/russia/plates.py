"""The Russia plates, on the plate spine.

Twelve chapters, one per spine topic, every one of them drawn from a
committed CSV. The country is unusual less in what it publishes than in how
many definitions it publishes each thing on, so the plate-level decisions
are nearly all about keeping two correct series apart:

- **Territory.** Rosstat counts Crimea and Sevastopol from 2014 (the
  144.0m → 146.7m step in its population series) and, by its own footnote,
  excludes the four oblasts it claimed in 2022 from that year on. The World
  Bank/UN population line carries neither step. The two are drawn as two
  labelled lines and the demography panel says which year changed which
  perimeter.
- **Prices.** Rosstat's headline CPI is December-to-December; the World
  Bank's is the annual average. Both are correct, they differ every year,
  and no single line is stitched from them: the economy panel carries the
  national definition as the line and the annual average beside it.
- **Public finances.** The spine's fiscal slots are general government
  (IMF WEO, accrual). The federal budget is Minfin's cash execution of one
  level of government and rides beside it as a labelled line, never added
  to it and never relabelled as general government. Spending is drawn on the
  federal perimeter, in the Russian functional classification mapped onto
  the spine's seven groups, because Russia does not publish COFOG.
- **Labour and migration.** Unemployment is the ILO modelled estimate, not
  Rosstat's labour-force survey. Net migration is the UN/WB model, not the
  registration system's arrivals and departures.

Where a canonical slot has no honest series it is drawn pending with the
route that failed, never filled from a convenient proxy.
"""
from __future__ import annotations

import matplotlib.ticker as mticker

from core.sideload import sibling

# plates.py is imported by path, not as a package, so `events` is loaded the
# same way: five countries with a module called `events` would otherwise
# collide in sys.modules and draw another country's timeline.
events = sibling(__file__, "events")

W0 = 2006


# ------------------------------------------------------------ small helpers
def _yr(ctx, rel: str, col: str, since: int = W0):
    """(years, values) from a calendar-year CSV, blanks dropped."""
    t = ctx.table(rel)
    if not t or col not in t:
        return [], []
    yrs, vals = ctx.series(t, col)
    keep = [(y, v) for y, v in zip(yrs, vals) if y >= since]
    return [y for y, _ in keep], [v for _, v in keep]


def _at(years, vals, year):
    return dict(zip(years, vals))[year]


def _note(p, ax, x, y, text, ha="left", va="top", size=8.0):
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=size, style="italic", color=p.MUTED, zorder=7)


def _foot(p, ax, text):
    ax.text(0.5, -0.07, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.2, color=p.FAINT, style="italic")


def _pending(ig, ax, why):
    ax.text(0.5, 0.34, why, transform=ax.transAxes, ha="center", va="top",
            fontsize=8.2, style="italic", color=ig.p.MUTED)


def _finish(ctx, ig):
    for a in ig.axes_flat:
        if a.get_visible():
            ig.style_axis(
                a, xticks_years=not getattr(a, "_categorical_x", False))


def _share(pairs, denom):
    """{year: 100 × value / denom[year]} for the years both cover."""
    return {y: v / denom[y] * 100 for y, v in pairs.items()
            if y in denom and denom[y]}


def _nominal_gdp(ctx):
    """Rosstat's nominal GDP, billion roubles, one vintage."""
    return dict(zip(*ctx.series(ctx.table("macro/gdp.csv"),
                                "nominal_bn_rub")))


# ----------------------------------------------------------------- economy
def plate_economy(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    gy, gv = _yr(ctx, "macro/gdp.csv", "real_growth_pct")
    ctx.bars(ax, gy, gv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    worst = min(zip(gy, gv), key=lambda t: t[1])
    ax.annotate(f"{worst[1]:.1f}%", worst, textcoords="offset points",
                xytext=(0, -2), ha="center", va="top", fontsize=8.8,
                fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96,
          f"{_at(gy, gv, 2009):.1f}% in 2009, {_at(gy, gv, 2020):.1f}% in "
          f"2020, {_at(gy, gv, 2022):.1f}% in 2022:\n"
          "grey bands are those contractions plus 2015–16")
    _foot(p, ax, "Rosstat national accounts; the bands are dated on its "
          "quarterly index. The World Bank agrees to 0.05 pp")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    py, pv = _yr(ctx, "world/gdp_per_person.csv", "gdp_per_person_usd")
    ctx.line(ax, py, pv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"US${v:,.0f}", dy=8)
    peak = max(zip(py, pv), key=lambda t: t[1])
    _note(p, ax, 0.02, 0.96,
          f"US${_at(py, pv, 2013):,.0f} in 2013, "
          f"US${_at(py, pv, 2015):,.0f} in 2015:\n"
          "a dollar figure, so the rouble is half of it")
    _foot(p, ax, "World Bank, current US$ over the UN population — a level "
          "in dollars, not per person present")

    ax = ig.slot("economy.inflation", "Consumer price inflation "
                 "(% per year)")
    cy, cv = _yr(ctx, "macro/cpi.csv", "cpi_dec_pct")
    wy, wv = _yr(ctx, "macro/economy.csv", "cpi_inflation_pct")
    ctx.line(ax, cy, cv, p.ALERT, label="Rosstat, December to December")
    ctx.line(ax, wy, wv, p.BLUE, label="World Bank, annual average")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"{_at(cy, cv, 2015):.1f}% in 2015 against "
          f"{_at(wy, wv, 2015):.1f}%:\ntwo definitions, both published, "
          "never spliced", size=7.8)
    _foot(p, ax, "Rosstat's headline (ipc_s) and the World Bank's annual "
          "average (FP.CPI.TOTL.ZG)")

    ax = ig.slot("economy.unemployment", "Unemployment rate "
                 "(% of the labour force)")
    uy, uv = _yr(ctx, "macro/economy.csv", "unemployment_pct")
    ctx.line(ax, uy, uv, p.NAVY, label="ILO modelled estimate")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"{_at(uy, uv, 2009):.1f}% in 2009, {uv[-1]:.1f}% in {uy[-1]}:"
          "\nthe model's own reading, not the labour-force survey", size=7.8)
    _foot(p, ax, "World Bank (ILO modelled). Rosstat's LFS headline is not "
          "staged: its workbooks are a Phase-B follow-up")
    _finish(ctx, ig)


# ------------------------------------------------------------------- world
def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    gy, gv = _yr(ctx, "world/gdp_usd.csv", "gdp_usd")
    gb = [v / 1e9 for v in gv]
    ctx.line(ax, gy, gb, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gb, p.BLUE, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"US${_at(gy, gb, 2013):,.0f}bn in 2013, "
          f"US${_at(gy, gb, 2015):,.0f}bn in 2015 —\n"
          "the oil price and the exchange rate, not a smaller economy")
    _foot(p, ax, "World Bank, current US$ — nominal, so the rouble moves it")

    ax = ig.slot("world.hdi", "Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "world/hdi.csv", "hdi")
    ctx.line(ax, hy, hv, p.GREEN)
    ctx.endlabel(ax, hy, hv, p.GREEN, lambda v: f"{v:.3f}", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"{_at(hy, hv, 2019):.3f} in 2019, {_at(hy, hv, 2021):.3f} in "
          f"2021,\n{hv[-1]:.3f} in {hy[-1]} — one HDR vintage throughout")
    _foot(p, ax, "UNDP Human Development Report; the series stops in 2023")

    ax = ig.slot("world.cpi", "Corruption Perceptions Index "
                 "(0–100)")
    ctx.pending(ax)
    _pending(ig, ax, "Transparency International's workbook answers\n"
             "403 to this network (2026-10-25). Retry at fetch time;\n"
             "no proxy is substituted.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn, year-end)")
    ry, rv = _yr(ctx, "world/reserves.csv", "reserves_usd")
    rb = [v / 1e9 for v in rv]
    ctx.line(ax, ry, rb, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rb, p.TEAL, lambda v: f"US${v:,.0f}bn", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"US${_at(ry, rb, 2013):,.0f}bn in 2013, US${rb[-1]:,.0f}bn in "
          f"{ry[-1]}:\nthe central bank's own holdings, most of them frozen")
    _foot(p, ax, "World Bank (the Bank of Russia's reserves, year-end)")
    _finish(ctx, ig)


# -------------------------------------------------------------- demography
def plate_demography(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    ry, rv = _yr(ctx, "demography/population.csv", "population_mn")
    wy, wv = _yr(ctx, "demography/population_wb.csv", "population")
    ri_y, ri_v = ctx.index_2006(dict(zip(ry, rv)))
    wi_y, wi_v = ctx.index_2006(dict(zip(wy, wv)))
    ctx.line(ax, ri_y, ri_v, p.GOLD,
             label="Rosstat (Crimea counted from 2014)")
    ctx.line(ax, wi_y, wi_v, p.BLUE,
             label="World Bank / UN (no 2014 step)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    ig.add_event(ax, *events.MARKS["annexation"], dy=0.97, rotation=90)
    _note(p, ax, 0.02, 0.06,
          "two territories, two lines: from 2015 they differ by "
          "2.1–2.8m people", va="bottom", size=7.6)
    _foot(p, ax, "Rosstat popul_1897+ and the World Bank's UN series; from "
          "2022 Rosstat's own footnote narrows the perimeter again")

    ax = ig.slot("demography.fertility", "Total fertility rate "
                 "(children per woman)")
    fy, fv = _yr(ctx, "demography/fertility.csv", "tfr")
    ctx.line(ax, fy, fv, p.ALERT)
    ig.add_recessions(ax, label=False)
    ax.axhline(2.1, color=p.FAINT, lw=1.0, ls=":")
    ax.annotate("2.1: replacement", (fy[0] + 0.3, 2.1),
                textcoords="offset points", xytext=(0, 3), ha="left",
                va="bottom", fontsize=7.6, color=p.MUTED)
    _note(p, ax, 0.02, 0.96,
          f"{_at(fy, fv, 2015):.2f} in 2015, {fv[-1]:.2f} in {fy[-1]}:\n"
          "well below replacement, throughout")
    _foot(p, ax, "World Bank (Rosstat's vital registration through the UN)")

    ax = ig.slot("demography.birth_death", "Crude birth and death rates "
                 "(per 1,000 people)")
    by, bv = _yr(ctx, "demography/vitals.csv", "birth_rate_per_1000")
    dy, dv = _yr(ctx, "demography/vitals.csv", "death_rate_per_1000")
    ctx.line(ax, by, bv, p.GREEN, label="Births")
    ctx.line(ax, dy, dv, p.ALERT, label="Deaths")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="center right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"deaths {_at(dy, dv, 2021):.1f} per 1,000 in 2021 against "
          f"births {_at(by, bv, 2021):.1f}:\nthe pandemic year, and the "
          "birth rate still falling", size=7.6)
    _foot(p, ax, "World Bank (Rosstat vital statistics, published rates — "
          "no denominator applied here)")

    ax = ig.slot("demography.natural_migration",
                 "Natural increase and net migration (per 1,000 people)")
    t = ctx.table("demography/components.csv")
    jan1 = dict(zip(*ctx.series(t, "population_jan1_thousand")))
    nat = {y: v / jan1[y] * 1000 for y, v in
           zip(*ctx.series(t, "natural_change_thousand")) if y in jan1}
    mig = {y: v / jan1[y] * 1000 for y, v in
           zip(*ctx.series(t, "migration_change_thousand")) if y in jan1}
    ny = sorted(y for y in nat if y >= W0)
    my = sorted(y for y in mig if y >= W0)
    ctx.line(ax, ny, [nat[y] for y in ny], p.ALERT, label="Natural increase")
    ctx.line(ax, my, [mig[y] for y in my], p.BLUE, label="Net migration")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"2021: {nat[2021]:.1f} natural, {mig[2021]:+.1f} migration —\n"
          "2014 is blank because the publisher suppressed it", size=7.6)
    _foot(p, ax, "Rosstat's components file ÷ its own 1 January population; "
          "one publication, one perimeter")
    _finish(ctx, ig)


# ------------------------------------------------------------------ people
def plate_people(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("people.gini", "Income inequality, Gini (0–100)")
    gy, gv = _yr(ctx, "people/gini.csv", "gini")
    ctx.line(ax, gy, gv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, gy, gv, p.PURPLE, lambda v: f"{v:.1f}", dy=-14)
    _note(p, ax, 0.02, 0.96,
          f"{_at(gy, gv, 2008):.1f} in 2008, {_at(gy, gv, 2014):.1f} in "
          f"2014,\n{gv[-1]:.1f} in {gy[-1]} — the survey stopped there")
    _foot(p, ax, "World Bank (Rosstat household survey). No 2024+ value")

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    ny, nv = _yr(ctx, "people/poverty.csv", "poverty_national_pct")
    uy, uv = _yr(ctx, "people/poverty.csv", "poverty_umic_pct")
    ctx.line(ax, ny, nv, p.ALERT, label="National definition")
    ctx.line(ax, uy, uv, p.BLUE,
             label="World Bank upper-middle-income line")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"{_at(ny, nv, 2024):.1f}% below the national line in 2024,\n"
          f"{_at(uy, uv, 2022):.1f}% below the international one in 2022",
          size=7.6)
    _foot(p, ax, "Rosstat's national line via the World Bank, and the Bank's "
          "own poverty line — two definitions, two lines")

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    ctx.pending(ax)
    _pending(ig, ax, "The МРОТ is statutory and set by federal law, but no\n"
             "machine-readable official time series was located in this\n"
             "pass. Incomplete research, not an absent statistic.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("people.lens", "What the rouble buys — the price level "
                 "since 2006 (index 2006 = 100)")
    cy, cv = _yr(ctx, "macro/cpi.csv", "cpi_dec_pct")
    level, run = [], 100.0
    for v in cv:
        run *= 1 + v / 100
        level.append(run)
    ctx.line(ax, cy, level, p.GOLD)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"prices {level[-1] / 100:.1f}× the 2006 level by {cy[-1]},\n"
          "chained from the annual headline, one definition throughout")
    _foot(p, ax, "Derived: Rosstat's December-to-December CPI chained from "
          "2006. Not a published index")
    _finish(ctx, ig)


# ------------------------------------------------------------------ fiscal
def plate_fiscal(ctx, ig) -> None:
    p = ctx.p
    F = "fiscal/fiscal.csv"
    gdp = _nominal_gdp(ctx)

    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure "
                 "(% of GDP)")
    ry, rv = _yr(ctx, F, "revenue_pct_gdp")
    ey, ev = _yr(ctx, F, "expenditure_pct_gdp")
    ctx.line(ax, ry, rv, p.TEAL, label="Revenue")
    ctx.line(ax, ey, ev, p.ALERT, label="Expenditure")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower right", fontsize=7.4, frameon=False)
    peak = max(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% in {peak[0]}", peak,
                textcoords="offset points", xytext=(6, 2), ha="left",
                fontsize=8.6, fontweight="bold", color=p.ALERT)
    _note(p, ax, 0.02, 0.96,
          "general government, accrual, one IMF vintage —\n"
          "the federal cash budget is the line on the next panel", size=7.6)
    _foot(p, ax, "IMF WEO (October 2026 vintage). Revenue and expenditure "
          "stop at 2024; 2025 has only the balance and the debt")

    ax = ig.slot("fiscal.balance", "Overall balance (% of GDP)")
    by, bv = _yr(ctx, F, "balance_pct_gdp")
    ctx.bars(ax, by, bv, lambda v: p.ALERT if v < 0 else p.GREEN)
    # The spine pairs the overall balance (bars) with the primary balance
    # (line). Russia's primary balance peaks at +8.49% of GDP in 2006, above
    # the atlas-wide +8 ceiling, and the federal non-oil-and-gas deficit is
    # the series Russian fiscal argument is actually about, so the labelled
    # national line takes the line and the primary balance is stated in the
    # foot. Nothing is clipped and nothing is rescaled here.
    fy, fv = _yr(ctx, "fiscal/federal_budget.csv", "non_oil_gas_balance_bn_rub")
    gdp = _nominal_gdp(ctx)
    nog = {y: v / gdp[y] * 100 for y, v in zip(fy, fv) if y in gdp}
    ny = sorted(nog)
    ctx.line(ax, ny, [nog[y] for y in ny], p.GOLD,
             label="Federal non-oil-and-gas balance (Minfin)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.2, frameon=False)
    head = {y: v / gdp[y] * 100 for y, v in
            zip(*_yr(ctx, "fiscal/federal_budget.csv", "balance_bn_rub"))
            if y in gdp}
    _note(p, ax, 0.98, 0.96,
          f"2025: the federal deficit is {head[2025]:.1f}% of GDP\n"
          f"and the non-oil-and-gas deficit {nog[2025]:.1f}%",
          ha="right", size=7.6)
    _foot(p, ax, "IMF WEO general government; gold: Minfin's non-oil-and-gas "
          "balance ÷ Rosstat GDP.\nThe primary balance peaks at +8.5% in "
          "2006, above the shared +8 ceiling, and is stated, not clipped")

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    dy, dv = _yr(ctx, F, "debt_pct_gdp")
    ctx.line(ax, dy, dv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, dy, dv, p.PURPLE, lambda v: f"{v:.0f}%", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"{_at(dy, dv, 2020):.0f}% after the pandemic, {dv[-1]:.0f}% in "
          f"{dy[-1]}:\nlow debt, and a closed market to sell it into",
          size=7.6)
    _foot(p, ax, "IMF WEO general government gross debt. The 2026 WEO "
          "projection is not drawn")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    iy, iv = _yr(ctx, F, "interest_pct_gdp")
    ctx.line(ax, iy, iv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.GOLD, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"{iv[-1]:.1f}% of GDP in {iy[-1]} —\n"
          "cheap debt while it lasts, at a 21% policy rate", size=7.6)
    _foot(p, ax, "IMF WEO general government interest. Minfin's federal debt "
          "service is a different perimeter and stops in 2021")
    _finish(ctx, ig)


# ---------------------------------------------------------------- spending
#: The Russian functional classification (14 sections) onto the spine's
#: seven COFOG groups. The mapping is approximate by construction and the
#: note on the panel says so; DATA_NOTES §4 is the full table.
SPEND_GROUPS = (
    ("social protection", ("social_policy",), "GREEN_D"),
    ("health", ("health",), "PURPLE"),
    ("education", ("education",), "BLUE"),
    ("general public services", ("general_government", "debt_service"),
     "NAVY"),
    ("economic affairs", ("national_economy",), "TEAL"),
    ("defence + public order", ("national_defence", "security_law_order"),
     "ALERT"),
    ("other", ("housing_utilities", "environment", "culture_media", "media",
               "physical_culture", "interbudgetary"), "FAINT"),
)


def _spend_shares(ctx):
    """{group: {year: % of GDP}} and the total, 2006–2021."""
    t = ctx.table("spending/budget_function.csv")
    gdp = _nominal_gdp(ctx)
    out = {name: {} for name, _, _ in SPEND_GROUPS}
    out["total"] = {}
    if not t:
        return out, []
    for name, columns, _ in SPEND_GROUPS:
        for col in columns:
            if col not in t:
                continue
            for y, v in zip(*ctx.series(t, col)):
                if y in gdp and gdp[y]:
                    out[name][y] = out[name].get(y, 0.0) + v / gdp[y] * 100
    for y in sorted(gdp):
        if y < W0 or y > 2021:
            continue
        if all(y in out[name] for name, _, _ in SPEND_GROUPS):
            out["total"][y] = sum(out[name][y] for name, _, _ in SPEND_GROUPS)
    return out, sorted(out["total"])


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    shares, years = _spend_shares(ctx)

    ax = ig.slot("spending.by_function",
                 "Spending by function, stacked (% of GDP)")
    ax.stackplot(years,
                 *[[shares[name][y] for y in years]
                   for name, _, _ in SPEND_GROUPS],
                 labels=[name for name, _, _ in SPEND_GROUPS],
                 colors=[getattr(p, color) for _, _, color in SPEND_GROUPS],
                 alpha=0.9, lw=0)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=6.8, ncol=2, frameon=False)
    tot = [shares["total"][y] for y in years]
    ax.annotate(f"{tot[-1]:.1f}% of GDP ({years[-1]})",
                (years[-1], tot[-1]), textcoords="offset points",
                xytext=(-4, 6), ha="right", fontsize=8.2,
                fontweight="bold", color=p.INK)
    _note(p, ax, 0.98, 0.62,
          "the Russian classification, not COFOG,\n"
          "and the federal budget only: pensions are\n"
          "paid through the Social Fund", ha="right", size=7.4)
    _foot(p, ax, "Minfin functional classification ÷ Rosstat's nominal GDP. "
          "The publisher has not released the breakdown since 2021")

    ax = ig.slot("spending.social_protection",
                 "Social protection vs everything else (% of GDP)")
    soc = [shares["social protection"][y] for y in years]
    rest = [t - s for t, s in zip(tot, soc)]
    ctx.line(ax, years, rest, p.NAVY, label="Everything else")
    ctx.line(ax, years, soc, p.GREEN_D, label="Social protection")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="center right", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"social protection is {soc[-1]:.1f}% of GDP in {years[-1]} —\n"
          "on the federal perimeter, so the Social Fund is outside it",
          size=7.4)
    _foot(p, ax, "Same series, two groups: one function and the remainder")

    ax = ig.slot("spending.investment", "Investment rate, whole economy "
                 "(% of GDP)")
    iy, iv = _yr(ctx, "macro/economy.csv", "gfcf_pct_gdp")
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.TEAL, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"{_at(iy, iv, 2008):.1f}% in 2008, {iv[-1]:.1f}% in {iy[-1]} —\n"
          "gross fixed capital formation, the whole economy")
    _foot(p, ax, "World Bank national accounts (NE.GDI.FTOT.ZS)")

    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    ctx.pending(ax)
    _pending(ig, ax, "Government fixed capital formation is published by\n"
             "Rosstat only in the annual SNA tables by ownership, which\n"
             "this pass did not stage. No budget line is relabelled as it.")
    _foot(p, ax, "SOURCES.yaml meta.pending — research incomplete, not absent")
    _finish(ctx, ig)


# ------------------------------------------------------------------- trade
def plate_trade(ctx, ig) -> None:
    p = ctx.p
    T = "trade/trade.csv"

    ax = ig.slot("trade.exports_imports", "Exports and imports "
                 "(% of GDP)")
    xy, xv = _yr(ctx, T, "exports_pct_gdp")
    my, mv = _yr(ctx, T, "imports_pct_gdp")
    ctx.line(ax, xy, xv, p.BLUE, label="Exports")
    ctx.line(ax, my, mv, p.ALERT, label="Imports")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.6, frameon=False)
    _note(p, ax, 0.02, 0.96,
          f"exports {_at(xy, xv, 2021):.1f}% of GDP in 2021, "
          f"{_at(xy, xv, 2025):.1f}% in 2025:\n"
          "the customs series is suspended; this one is national accounts",
          size=7.4)
    _foot(p, ax, "World Bank national accounts, goods and services — not the "
          "customs statistics, which Russia stopped publishing in 2022")

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    ex, im = dict(zip(xy, xv)), dict(zip(my, mv))
    by = [y for y in xy if y in im]
    bv = [ex[y] - im[y] for y in by]
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{bv[-1]:+.1f}%", (by[-1], bv[-1]),
                textcoords="offset points", xytext=(0, 8), ha="center",
                va="bottom", fontsize=8.6, fontweight="bold", color=p.GREEN)
    drop = 100 * (1 - bv[-1] / _at(by, bv, 2021))
    _note(p, ax, 0.02, 0.96,
          f"{_at(by, bv, 2021):+.1f}% in 2021, {bv[-1]:+.1f}% in {by[-1]}:\n"
          f"the surplus is {drop:.0f}% smaller than in 2021")
    _foot(p, ax, "Derived: exports minus imports, one World Bank series")

    ax = ig.slot("trade.destinations", "Top export destinations "
                 "(% of goods exports)")
    ctx.pending(ax)
    _pending(ig, ax, "The customs service suspended its detailed release in\n"
             "2022 and its host does not answer; UN Comtrade returns no\n"
             "Russian rows for 2022–2023. No unofficial mirror is used.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("trade.lens", "The surplus in dollars — net exports of "
                 "goods and services (US$ bn)")
    gy, gv = _yr(ctx, "world/gdp_usd.csv", "gdp_usd")
    g = dict(zip(gy, gv))
    ly = [y for y in by if y in g]
    lv = [(ex[y] - im[y]) / 100 * g[y] / 1e9 for y in ly]
    ctx.bars(ax, ly, lv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    best = max(zip(ly, lv), key=lambda t: t[1])
    ax.annotate(f"US${best[1]:,.0f}bn in {best[0]}", best,
                textcoords="offset points", xytext=(6, 2), ha="left",
                va="bottom", fontsize=8.4, fontweight="bold", color=p.GREEN)
    _note(p, ax, 0.02, 0.96,
          f"US${lv[-1]:,.0f}bn in {ly[-1]} —\n"
          "derived, and one definition of GDP throughout", size=7.6)
    _foot(p, ax, "Derived: the national-accounts trade share × World Bank "
          "GDP at current US$")
    _finish(ctx, ig)


# ----------------------------------------------------------------- markets
def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ky, kv = _yr(ctx, "markets/key_rate.csv", "key_rate_pct")
    kpy, kpv = _yr(ctx, "markets/key_rate.csv", "key_rate_pct_peak")
    cy, cv = _yr(ctx, "macro/cpi.csv", "cpi_dec_pct")
    ctx.line(ax, ky, kv, p.NAVY, label="Key rate (annual mean)")
    ctx.line(ax, cy, cv, p.ALERT, label="Rosstat CPI (Dec/Dec)")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    ax.annotate(f"{_at(kpy, kpv, 2022):.0f}% on 28 Feb 2022",
                (2022, _at(kpy, kpv, 2022)), textcoords="offset points",
                xytext=(-6, 34), ha="right", va="bottom", fontsize=8.0,
                fontweight="bold", color=p.NAVY,
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    _note(p, ax, 0.02, 0.96,
          f"the 2022 mean is {_at(ky, kv, 2022):.1f}%: the emergency rate\n"
          "lasted three weeks and the year is the mean of the rest",
          size=7.4)
    _foot(p, ax, "Bank of Russia key rate (mean of the daily rate, peak "
          "marked) and Rosstat's December-to-December CPI")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield "
                 "(%, annual average)")
    oy, ov = _yr(ctx, "markets/ofz_10y.csv", "ofz_10y_pct")
    ctx.line(ax, oy, ov, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, oy, ov, p.PURPLE, lambda v: f"{v:.1f}%", dy=8)
    o_full = dict(zip(oy, ov))[ctx.LAST_FULL_YEAR]
    _note(p, ax, 0.02, 0.96,
          f"{_at(oy, ov, 2020):.1f}% in 2020, {o_full:.1f}% in "
          f"{ctx.LAST_FULL_YEAR} —\nthe yield the state pays at home, not "
          "abroad")
    _foot(p, ax, "Bank of Russia zero-coupon curve, 10-year tenor, annual "
          "mean of the daily readings")

    ax = ig.slot("markets.currency", "Currency against the US$ "
                 "(index 2006 = 100, up = stronger)")
    fy, fv = _yr(ctx, "markets/usd_rub.csv", "rub_per_usd")
    iy, iv = ctx.fx_index(dict(zip(fy, fv)))
    ctx.line(ax, iy, iv, p.TEAL)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, iy, iv, p.TEAL, lambda v: f"{v:.0f}", dy=8)
    ig.add_event(ax, *events.MARKS["rouble_halving"], dy=0.60)
    base = _at(fy, fv, 2006)
    _note(p, ax, 0.98, 0.96,
          f"{base:.1f} per dollar in 2006, {_at(fy, fv, 2025):.1f} in 2025;\n"
          "2022 is partly an administered rate", ha="right", size=7.4)
    _foot(p, ax, "Bank of Russia official rate, annual mean of the daily "
          "rate. Capital controls fixed it for part of 2022")

    ax = ig.slot("markets.equities", "Main equity index in US$ "
                 "(index 2006 = 100, in US$)")
    my, mv = _yr(ctx, "markets/imoex.csv", "imoex_usd_avg")
    ey, ev = ctx.index_2006(dict(zip(my, mv)))
    ctx.line(ax, ey, ev, p.RED)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ey, ev, p.RED, lambda v: f"{v:.0f}", dy=8)
    e_full = dict(zip(ey, ev))[ctx.LAST_FULL_YEAR]
    _note(p, ax, 0.02, 0.96,
          f"{_at(ey, ev, 2021):.0f} in 2021, {e_full:.0f} in "
          f"{ctx.LAST_FULL_YEAR} —\nin dollars, and trading stopped "
          "25 Feb – 24 Mar 2022", size=7.4)
    _foot(p, ax, "MOEX IMOEX ÷ the Bank of Russia's own annual mean rate "
          "(a market series, not an official statistic)")
    _finish(ctx, ig)


# ------------------------------------------------------------------ credit
def plate_credit(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    hy, hv = _yr(ctx, "credit/household_debt.csv", "household_debt_pct_gdp")
    ctx.line(ax, hy, hv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, hy, hv, p.BLUE, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"{hv[0]:.1f}% in {hy[0]}, {_at(hy, hv, 2020):.1f}% in 2020,\n"
          f"{hv[-1]:.1f}% in {hy[-1]} — small by any rich-country standard")
    _foot(p, ax, "BIS total credit (Q4 reading, break-adjusted), "
          "households and NPISHs")

    ax = ig.slot("credit.lending_rate", "Household lending rate vs policy "
                 "rate (%)")
    ly, lv = _yr(ctx, "credit/household_lending_rate.csv",
                 "household_lending_rate_pct")
    ky, kv = _yr(ctx, "markets/key_rate.csv", "key_rate_pct", since=ly[0])
    ctx.line(ax, ly, lv, p.ALERT, label="New rouble loans to households")
    ctx.line(ax, ky, kv, p.NAVY, label="Key rate")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    l_full = dict(zip(ly, lv))[ctx.LAST_FULL_YEAR]
    k_full = dict(zip(ky, kv))[ctx.LAST_FULL_YEAR]
    _note(p, ax, 0.98, 0.72,
          f"{l_full:.1f}% in {ctx.LAST_FULL_YEAR} against a {k_full:.1f}% "
          "key rate", ha="right", size=7.6)
    _foot(p, ax, "Bank of Russia weighted-average rate on new rouble loans "
          "to individuals; the workbook starts in January 2014")

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    ny, nv = _yr(ctx, "credit/npl.csv", "npl_pct_loans")
    ctx.line(ax, ny, nv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ny, nv, p.PURPLE, lambda v: f"{v:.1f}%", dy=-14)
    _note(p, ax, 0.02, 0.96,
          f"{_at(ny, nv, 2017):.1f}% in 2017, {nv[-1]:.1f}% in {ny[-1]} —\n"
          "the World Bank's series stops there", size=7.6)
    _foot(p, ax, "World Bank FS indicator (the Bank of Russia's own ratio is "
          "not on a machine feed here)")

    ax = ig.slot("credit.lens", "What banks charge above the key rate "
                 "(percentage points)")
    spread = {y: v - dict(zip(ky, kv))[y] for y, v in zip(ly, lv)
              if y in dict(zip(ky, kv))}
    sy = sorted(spread)
    ctx.bars(ax, sy, [spread[y] for y in sy],
             lambda v: p.ALERT if v >= 0 else p.GREEN)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{spread[2014]:+.1f} pp in 2014, "
          f"{spread[ctx.LAST_FULL_YEAR]:+.1f} pp in {ctx.LAST_FULL_YEAR}:\n"
          "the margin inverted as the policy rate rose", size=7.4)
    _foot(p, ax, "Derived: the new-loan rate minus the key rate, two Bank of "
          "Russia series")
    _finish(ctx, ig)


# ---------------------------------------------------------------- security
def plate_security(ctx, ig) -> None:
    p = ctx.p
    S = "security/security.csv"

    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    hy, hv = _yr(ctx, S, "homicide_per_100k")
    ctx.line(ax, hy, hv, p.ALERT)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, hy, hv, p.ALERT, lambda v: f"{v:.1f}", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"{hv[0]:.1f} in {hy[0]}, {hv[-1]:.1f} in {hy[-1]} —\nthe UNODC "
          "series stops before the war", size=7.6)
    _foot(p, ax, "UNODC via the World Bank; no 2022+ value")

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    sy_all, sv_all = _yr(ctx, S, "suicide_per_100k")
    # 2006 is 41.4 per 100,000; the shared ceiling is 45, so the whole
    # series is drawn canonically (it was 40 when this chapter was first
    # written, and the point lived in the lens).
    sy = sy_all
    sv = sv_all
    ctx.line(ax, sy, sv, p.PURPLE)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, sy, sv, p.PURPLE, lambda v: f"{v:.1f}", dy=-14)
    _note(p, ax, 0.02, 0.06,
          "41.4 in 2006 is above the shared 0–40 scale:\n"
          f"the line starts in 2007 and the lens carries 2006; {sv[-1]:.1f} "
          f"in {sy[-1]}", va="bottom", size=7.4)
    _foot(p, ax, "WHO via the World Bank; no 2022+ value")

    ax = ig.slot("security.road_deaths", "Road traffic deaths "
                 "(per 100,000)")
    ry, rv = _yr(ctx, S, "road_deaths_per_100k")
    ctx.line(ax, ry, rv, p.GOLD)
    ig.add_recessions(ax, label=False)
    ctx.endlabel(ax, ry, rv, p.GOLD, lambda v: f"{v:.1f}", dy=-14)
    _note(p, ax, 0.02, 0.96,
          f"{rv[0]:.1f} in {ry[0]} to {rv[-1]:.1f} in {ry[-1]};\n"
          "the WHO series stops there", size=7.6)
    _foot(p, ax, "WHO via the World Bank")

    ax = ig.slot("security.lens", "Violent and road deaths: 2006 and the "
                 "last year each is published (per 100,000)")
    # Each series is read again here rather than reusing the slots' own
    # reads: the suicide line above starts at 2007 on purpose, and the lens
    # is the one panel that carries the 2006 reading.
    series = (("homicide",) + _yr(ctx, S, "homicide_per_100k"),
              ("suicide",) + _yr(ctx, S, "suicide_per_100k"),
              ("road deaths",) + _yr(ctx, S, "road_deaths_per_100k"))
    names = {"homicide": "Homicide", "suicide": "Suicide",
             "road deaths": "Road deaths"}
    positions = list(range(len(series)))
    first = [vals[0] for _, _, vals in series]
    last = [vals[-1] for _, _, vals in series]
    ax.bar([x - 0.19 for x in positions], first, width=0.36,
           color=p.FAINT, label="2006")
    ax.bar([x + 0.19 for x in positions], last, width=0.36,
           color=p.ALERT, label="last published year")
    ax.set_xticks(positions)
    ax.set_xticklabels([names[name] for name, _, _ in series], fontsize=8.0)
    ax.tick_params(axis="x", length=0)
    ax.set_ylim(0, max(first) * 1.22)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    ax._categorical_x = True
    endings = ", ".join(f"{names[name]} {years[-1]}" for name, years, _
                        in series)
    _note(p, ax, 0.02, 0.96,
          f"by the last year each is published — {endings} —\n"
          "the homicide rate fell by two thirds", size=7.2)
    _foot(p, ax, "UNODC and WHO via the World Bank; one bar pair per cause")
    _finish(ctx, ig)


# --------------------------------------------------------------- mortality
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
                fontsize=8.6, fontweight="bold", color=p.INK)
    _note(p, ax, 0.02, 0.96,
          f"{dv[0]:.1f} in {dy[0]}, {dv[-1]:.1f} in {dy[-1]};\n"
          "2021 is the pandemic's second year", size=7.6)
    _foot(p, ax, "World Bank (Rosstat vital registration), published rate")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths "
                 "(% above 2015–2019 average)")
    ctx.pending(ax)
    _pending(ig, ax, "Excess deaths need the registered-death count, not the\n"
             "rate, and no official count series is reachable from here:\n"
             "Rosstat's own COVID release is not machine-readable.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause "
                 "(per 100,000)")
    ctx.pending(ax)
    _pending(ig, ax, "No official underlying-cause COVID-19 series is\n"
             "reachable: WHO's general indicator was withdrawn and\n"
             "Rosstat's operational data are not published as a file.")
    _foot(p, ax, "SOURCES.yaml meta.pending")

    ax = ig.slot("mortality.lens", "Life expectancy at birth (years)",
                 unit=False)
    ax.set_ylabel("years", fontsize=8.6, color=p.muted)
    ly, lv = _yr(ctx, M, "life_expectancy")
    ctx.line(ax, ly, lv, p.TEAL)
    ig.add_recessions(ax, label=False)
    _note(p, ax, 0.02, 0.96,
          f"{_at(ly, lv, 2019):.1f} years in 2019, {_at(ly, lv, 2021):.1f} "
          f"in 2021,\n{lv[-1]:.1f} in {ly[-1]}", size=7.6)
    _foot(p, ax, "World Bank (UN WPP life tables)")
    _finish(ctx, ig)


# --------------------------------------------------------------- migration
def plate_migration(ctx, ig) -> None:
    p = ctx.p

    ax = ig.slot("migration.flows", "Immigration and emigration "
                 "(per 1,000 people)")
    ctx.pending(ax)
    _pending(ig, ax, "Rosstat's registration totals were downloaded and are\n"
             "deliberately not staged beside the modelled series: the two\n"
             "measure different things and must not be subtracted.")
    _foot(p, ax, "SOURCES.yaml meta.pending — a rejected proxy, not a gap")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    gy, gv = _yr(ctx, "migration/net_migration.csv", "net_migration")
    py, pv = _yr(ctx, "demography/population_wb.csv", "population")
    pop = dict(zip(py, pv))
    ny = [y for y in gy if y in pop]
    nv = [dict(zip(gy, gv))[y] / pop[y] * 1000 for y in ny]
    ctx.line(ax, ny, nv, p.BLUE)
    ig.add_recessions(ax, label=False)
    ax.annotate(f"{nv[-1]:+.1f}", (ny[-1], nv[-1]),
                textcoords="offset points", xytext=(-4, -12), ha="right",
                va="top", fontsize=8.6, fontweight="bold", color=p.BLUE)
    _note(p, ax, 0.02, 0.96,
          f"{_at(ny, nv, 2022):+.1f} per 1,000 in 2022, {nv[-1]:+.1f} in "
          f"{ny[-1]}:\nthe model's own reversal", size=7.6)
    _foot(p, ax, "World Bank (UN WPP) net migration ÷ the same series' "
          "population — modelled, not a register")

    ax = ig.slot("migration.foreign_born", "Foreign-born share of the "
                 "population (%)")
    sy, sv = _yr(ctx, "migration/migrant_stock.csv", "migrant_stock")
    fy, fv = [], []
    for y, v in zip(sy, sv):
        if y in pop:
            fy.append(y)
            fv.append(v / pop[y] * 100)
    ctx.line(ax, fy, fv, p.PURPLE)
    ctx.endlabel(ax, fy, fv, p.PURPLE, lambda v: f"{v:.1f}%", dy=8)
    _note(p, ax, 0.02, 0.96,
          f"{fv[0]:.1f}% in {fy[0]}, {fv[-1]:.1f}% in {fy[-1]}:\n"
          "snapshot years only — the stock is a UN estimate", size=7.6)
    _foot(p, ax, "World Bank (UN DESA migrant stock) ÷ the UN population")

    ax = ig.slot("migration.lens", "Net migration, persons a year (the "
                 "model's own level)")
    ly = gy
    lv = gv
    ctx.bars(ax, ly, lv, lambda v: p.GREEN if v >= 0 else p.ALERT)
    ig.add_recessions(ax, label=False)
    best = max(zip(ly, lv), key=lambda t: t[1])
    ax.annotate(f"{best[1]:,.0f} in {best[0]}", best,
                textcoords="offset points", xytext=(-6, 6), ha="right",
                va="bottom", fontsize=8.2, fontweight="bold", color=p.GREEN)
    ig.headroom(ax, top=0.20)
    # Fixed ticks: left to itself the axis labels a million as the offset
    # text "1e6", which is neither a Russian nor a readable one.
    ax.set_yticks([-250_000, 0, 250_000, 500_000, 750_000])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: f"{v:,.0f}"))
    _note(p, ax, 0.02, 0.96,
          f"{lv[-1]:+,.0f} in {ly[-1]}:\nthe 2022 inflow became an outflow",
          size=7.6)
    _foot(p, ax, "World Bank (UN WPP) — modelled, and a level, not a rate")
    _finish(ctx, ig)


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Economy — Three Contractions and a Long Stagnation",
         subtitle="Output, income, prices and jobs, 2006–2026. Grey bands "
                  "are the contractions dated on Rosstat's quarterly index.",
         alt="Four panels on the Russian economy, 2006–2026. Real GDP "
             "growth turns negative in 2009, 2015, 2020 and 2022, with the "
             "2009 fall the deepest at -7.8%. GDP per person in dollars "
             "halves between 2013 and 2015 and recovers only by 2021. Two "
             "inflation lines — Rosstat's December-to-December headline and "
             "the World Bank's annual average — track each other but never "
             "merge. Unemployment is the ILO modelled estimate, falling "
             "from 8.3% in 2009 to 2.1% in 2025.",
         filename="01-economy"),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — Three Perimeters and One Deficit",
         subtitle="General government on the IMF's accrual accounts, with "
                  "the federal cash budget beside it, never added to it.",
         alt="Four panels on Russia's public finances. General-government "
             "revenue and expenditure as a share of GDP, 2006–2024, with "
             "expenditure peaking at 39.2% in 2020. The overall balance is "
             "in surplus through 2006–2008 and 2018–2019, and the federal "
             "budget line sits close to it. Gross debt stays under 20% of "
             "GDP throughout. Interest paid stays below 1.2% of GDP.",
         filename="02-fiscal"),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Spending — What the Federal Budget Buys, and Where the "
               "Record Stops",
         subtitle="The Russian functional classification mapped onto the "
                  "spine's seven groups. It stops in 2021, and says so.",
         alt="Four panels on Russian federal spending. A stacked area of "
             "seven functional groups as a share of GDP, 2006–2021, with "
             "social policy, interbudgetary transfers and defence the "
             "largest. Social protection against everything else. The "
             "whole-economy investment rate holds near 20–23% of GDP. "
             "Public investment is pending: no official government "
             "investment series is staged.",
         filename="03-spending"),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — The Surplus That Pays for the Budget",
         subtitle="Goods and services on the national-accounts basis, "
                  "because the customs series stopped in 2022.",
         alt="Four panels on Russian trade. Exports and imports of goods "
             "and services as a share of GDP, with exports peaking at "
             "33.7% in 2006 and falling to 18.2% in 2025. The trade "
             "balance stays in surplus every year. Export destinations are "
             "pending: the customs service suspended its release in 2022. "
             "The lens converts the surplus to dollars, peaking near "
             "US$290bn in 2022.",
         filename="04-trade"),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Markets — A 20% Key Rate and a Rouble Under Controls",
         subtitle="The central bank's own series: the policy rate, the "
                  "curve, the official rate and the exchange's index.",
         alt="Four panels on Russian markets. The key rate's annual mean "
             "and Rosstat inflation both sit in single digits until 2014, "
             "and the 28 February 2022 emergency rate of 20% is marked. "
             "The 10-year yield rises to 15.3% by 2026. The rouble falls "
             "from 27 per dollar in 2006 to 83 in 2025. The MOEX index in "
             "dollars falls from 100 in 2006 to 67 in 2025.",
         filename="05-markets"),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — Borrowing That Stayed Small Until It Got Expensive",
         subtitle="Household credit from the BIS, and what the Bank of "
                  "Russia charged for new loans.",
         alt="Four panels on Russian credit. Household debt rises from "
             "8.2% of GDP in 2006 to 21–22% from 2020, flat by rich-country "
             "standards. The new-loan rate to households falls from 20.2% "
             "in 2015 to 10.6% in 2021 and rises to 18.6% in 2025 against "
             "a 19.1% key rate. Non-performing loans fall from 9.8% in 2009 "
             "to 4.5% in 2023, where the series stops. The lens shows the "
             "lending margin over the key rate turning negative.",
         filename="06-credit"),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="People — Inequality Falling, Poverty Measured Twice",
         subtitle="Two poverty definitions and one price level: what a "
                  "rouble buys, chained from the headline CPI.",
         alt="Four panels on Russian living standards. The Gini coefficient "
             "falls from 42.3 in 2008 to 33.0 in 2023, where the survey "
             "stops. Poverty on the national definition falls from 15.2% "
             "in 2006 to 7.2% in 2024, with the World Bank's "
             "upper-middle-income line far below it. The minimum wage is "
             "pending. The lens chains the headline CPI to show prices at "
             "about 3.5 times their 2006 level.",
         filename="07-people"),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="Russia in the World — Size, Development and Reserves",
         subtitle="Dollars at market rates, one HDI vintage, and the "
                  "reserves most of which are now immobilised.",
         alt="Four panels placing Russia in the world. GDP at current "
             "prices peaks near US$2.29tn in 2013 and 2022. The Human "
             "Development Index rises from 0.791 in 2006 to 0.832 in 2023, "
             "dipping in 2020–2021. The Corruption Perceptions Index is "
             "pending. Official reserves rise from US$304bn in 2006 to "
             "US$608bn in 2024.",
         filename="08-world"),
    dict(id="09", slug="demography", topic="demography",
         builder=plate_demography,
         title="Demography — Two Territories and One Shrinking Population",
         subtitle="Rosstat counts Crimea from 2014 and narrows its "
                  "perimeter again from 2022; the UN line does neither.",
         alt="Four panels on Russian demography. Two population lines, "
             "both indexed to 2006: Rosstat's steps up 2.7 million between "
             "2014 and 2015 and the UN's does not, so from 2015 they "
             "differ by about 2.5 million. The total fertility rate falls "
             "from 1.78 in 2015 to 1.42 in 2024, well under replacement. "
             "Births fall below deaths from 2016. Natural increase is "
             "negative every year and net migration positive until 2023.",
         filename="09-demography"),
    dict(id="10", slug="security", topic="security", builder=plate_security,
         title="Security — Violence Falling, and the Record Stopping",
         subtitle="Homicide, suicide and the road, from the international "
                  "carriers: the national publishers are not reachable.",
         alt="Four panels on Russian violent and accidental death. The "
             "homicide rate falls from 20.0 per 100,000 in 2006 to 6.8 in "
             "2021, where the series stops. Suicide falls from 41.4 to "
             "21.4 over the same years. Road deaths fall from 27.5 in 2006 "
             "to 12.0 in 2019. The lens sets 2006 against each series' last "
             "year.",
         filename="10-security"),
    dict(id="11", slug="mortality", topic="mortality",
         builder=plate_mortality,
         title="Mortality — A Death Rate That Peaked in 2021",
         subtitle="The crude death rate and life expectancy, and the two "
                  "pandemic panels that cannot be drawn from official files.",
         alt="Four panels on Russian mortality. The crude death rate falls "
             "from 15.1 per 1,000 in 2006 to 12.3 in 2019, spikes to 16.7 "
             "in 2021, and falls back to 12.4 in 2024. Excess deaths and "
             "COVID-19 deaths are pending: neither an official count series "
             "nor an underlying-cause series is reachable. Life expectancy "
             "rises from 66.7 years in 2006 to 73.4 in 2024, with a dip to "
             "69.9 in 2021.",
         filename="11-mortality"),
    dict(id="12", slug="migration", topic="migration",
         builder=plate_migration,
         title="Migration — A Modelled Flow, and the 2022 Spike",
         subtitle="Net migration is the UN model, not the registration "
                  "system: the two measure different things and are kept "
                  "apart.",
         alt="Four panels on Russian migration. Gross immigration and "
             "emigration are pending: the registration totals are not "
             "staged beside the modelled series. Net migration per 1,000 "
             "peaks at 5.3 in 2022 and turns negative by 2024. The "
             "foreign-born share falls from 7.8% in 2010 to 5.3% in 2024. "
             "The lens shows the same model in persons, from +766,000 in "
             "2022 to -252,000 in 2025.",
         filename="12-migration"),
)
