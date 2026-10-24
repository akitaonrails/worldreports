"""China's twelve comparison-spine plates.

The reachable layer is international: NBS and the other national machine
channels are blocked or not isolated (DATA_NOTES.md). Every footer says so;
no harmonised line is relabelled as a Chinese national series.
"""
from __future__ import annotations

from core.sideload import sibling

events = sibling(__file__, "events")
W0 = 2006


def _yr(ctx, rel, col, since=W0, until=None):
    table = ctx.table(rel)
    if not table or col not in table:
        return [], []
    years, values = ctx.series(table, col)
    out = [(y, v) for y, v in zip(years, values)
           if y >= since and (until is None or y <= until) and v == v]
    return [y for y, _ in out], [v for _, v in out]


def _rows(ctx, rel):
    table = ctx.table(rel) or {}
    return [dict(zip(table, values)) for values in zip(*table.values())]


def _pop(ctx):
    y, v = _yr(ctx, "demography/population_intl.csv", "population")
    return dict(zip(y, v))


def _foot(p, ax, text):
    ax.text(0.5, -0.07, text, transform=ax.transAxes, ha="center", va="top",
            fontsize=7.0, color=p.FAINT, style="italic")


def _note(p, ax, text, x=0.02, y=0.96):
    ax.text(x, y, text, transform=ax.transAxes, ha="left", va="top",
            fontsize=7.7, color=p.MUTED, style="italic", zorder=7)


def _mark(ig, ax, key, dy=0.94):
    year, label = events.MARKS[key]
    ig.add_event(ax, year, label, dy=dy)


def _pending(ctx, ig, ax, why):
    ctx.pending(ax)
    ax.text(0.5, 0.31, why, transform=ax.transAxes, ha="center", va="top",
            fontsize=7.8, color=ctx.p.MUTED, style="italic")


def _finish(ig):
    for ax in ig.axes_flat:
        if ax.get_visible():
            ig.style_axis(ax)


def plate_economy(ctx, ig):
    p = ctx.p
    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    y, wb = _yr(ctx, "economy/gdp_growth_intl.csv", "wb_real_growth_pct")
    _, imf = _yr(ctx, "economy/gdp_growth_intl.csv", "imf_real_growth_pct")
    ctx.bars(ax, y, wb, lambda n: p.GREEN if n >= 0 else p.RED)
    ctx.line(ax, y, imf, p.BLUE, label="IMF WEO")
    ig.add_recessions(ax)
    _foot(p, ax, "World Bank bars and IMF line; NBS national accounts unavailable (403)")
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    y, v = _yr(ctx, "economy/gdp_pc_usd.csv", "gdp_per_person_usd")
    ctx.line(ax, y, v, p.RED)
    ctx.endlabel(ax, y, v, p.RED, lambda n: f"US${n:,.0f}", dy=8)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "World Bank harmonised reading; current US$ at market exchange rates")

    ax = ig.slot("economy.inflation", "Consumer price inflation (% per year)")
    y, wb = _yr(ctx, "economy/inflation_intl.csv", "wb_cpi_inflation_pct")
    _, imf = _yr(ctx, "economy/inflation_intl.csv", "imf_cpi_inflation_pct")
    ctx.line(ax, y, wb, p.RED, label="World Bank")
    ctx.line(ax, y, imf, p.BLUE, ls="--", label="IMF WEO")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    _foot(p, ax, "Harmonised readings; the NBS CPI remains the national series of record")

    ax = ig.slot("economy.unemployment", "Unemployment (% of labour force)")
    y, v = _yr(ctx, "economy/unemployment_intl.csv", "unemployment_pct")
    ctx.line(ax, y, v, p.NAVY)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "ILO modelled estimate via World Bank; not the NBS surveyed urban rate")
    _finish(ig)


def plate_fiscal(ctx, ig):
    p = ctx.p
    F = "fiscal/finance_intl.csv"
    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure (% of GDP)")
    y, rev = _yr(ctx, F, "revenue_pct_gdp")
    _, exp = _yr(ctx, F, "expenditure_pct_gdp")
    ctx.line(ax, y, rev, p.GREEN, label="Revenue")
    ctx.line(ax, y, exp, p.RED, label="Expenditure")
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _foot(p, ax, "IMF Fiscal Monitor, broad general government; MOF's budget is narrower")
    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    fy, overall = _yr(ctx, F, "overall_balance_pct_gdp")
    _, primary = _yr(ctx, F, "primary_balance_pct_gdp")
    ctx.bars(ax, fy, overall, lambda n: p.GREEN if n >= 0 else p.RED)
    ctx.line(ax, fy, primary, p.BLUE, label="Primary balance")
    ax.legend(loc="lower left", fontsize=7.3, frameon=False)
    _foot(p, ax, "IMF Fiscal Monitor; overall and primary balances from one vintage")
    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    y, v = _yr(ctx, "fiscal/debt_intl_pct_gdp.csv", "gg_gross_debt_pct_gdp")
    ctx.line(ax, y, v, p.RED, label="IMF broad general government")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "covid", 0.88)
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _foot(p, ax, "IMF WEO; MOF on-budget debt excludes LGFVs and must remain separate")
    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    interest = [a - b for a, b in zip(primary, overall)]
    ctx.line(ax, fy, interest, p.PURPLE, label="Interest paid")
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _foot(p, ax, "Derived within one IMF vintage: primary balance minus overall balance")
    _finish(ig)


def plate_spending(ctx, ig):
    p = ctx.p
    ax = ig.slot("spending.by_function", "Spending by function, stacked (% of GDP)")
    _pending(ctx, ig, ax, "China publishes no accessible COFOG mapping in the staged sources")
    ax = ig.slot("spending.social_protection", "Social protection vs everything else (% of GDP)")
    _pending(ctx, ig, ax, "A comparable functional spending series is not staged")
    ax = ig.slot("spending.investment", "Investment rate, whole economy (% of GDP)")
    y, v = _yr(ctx, "economy/gfcf_pct_gdp.csv", "gfcf_pct_gdp")
    ctx.line(ax, y, v, p.RED)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "World Bank GFCF; above the shared 40% reference for much of the window")
    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    _pending(ctx, ig, ax, "Government GFCF is not separately available in the staged sources")
    _finish(ig)


def plate_trade(ctx, ig):
    p = ctx.p
    T = "trade/trade_intl_openness.csv"
    ax = ig.slot("trade.exports_imports", "Exports and imports (% of GDP)")
    y, x = _yr(ctx, T, "exports_pct_gdp")
    _, m = _yr(ctx, T, "imports_pct_gdp")
    ctx.line(ax, y, x, p.GREEN, label="Exports")
    ctx.line(ax, y, m, p.RED, label="Imports")
    ig.add_recessions(ax, label=False)
    _mark(ig, ax, "tariffs", 0.90)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _foot(p, ax, "World Bank goods and services, balance-of-payments basis")
    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    ctx.bars(ax, y, [a-b for a, b in zip(x, m)],
             lambda n: p.GREEN if n >= 0 else p.RED)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "Exports minus imports within one World Bank vintage")

    rows = _rows(ctx, "trade/trade_comtrade_partner.csv")
    exports = [r for r in rows if r["flow"] == "X" and r["partner"] != "World"]
    exports.sort(key=lambda r: float(r["share_of_flow_pct"]), reverse=True)
    ax = ig.slot("trade.destinations", "Top export destinations (% of goods exports)")
    _pending(ctx, ig, ax, "Only a 2023 partner snapshot is staged; the canonical slot requires a time series")

    ax = ig.slot("trade.lens", "Lens — top export destinations, 2023 (% of goods exports)")
    names = [r["partner"] for r in exports[:8]][::-1]
    vals = [float(r["share_of_flow_pct"]) for r in exports[:8]][::-1]
    ax.barh(names, vals, color=p.RED, alpha=0.88)
    for i, value in enumerate(vals):
        ax.text(value + max(vals) * 0.015, i, f"{value:.1f}%",
                va="center", fontsize=7.0, color=p.INK)
    _foot(p, ax, "UN Comtrade snapshot; China reporter, customs goods; Taiwan absent from response")
    _finish(ig)
    # This country lens is categorical, not a time series. `_finish` gives
    # every panel the normal year window, so restore a truthful percentage
    # axis after the shared styling pass.
    ax.set_xlim(0, max(vals) * 1.18)
    ax.set_xticks([0, 5, 10, 15])


def plate_markets(ctx, ig):
    p = ctx.p
    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    _pending(ctx, ig, ax, "LPR begins in 2019; the prior benchmark rate is a separate regime")
    ax = ig.slot("markets.bond_10y", "10-year government bond yield (%, annual average)")
    _pending(ctx, ig, ax, "No official yield series is staged")
    ax = ig.slot("markets.currency", "Renminbi against the US$ (index 2006 = 100, up = stronger)")
    y, fx = _yr(ctx, "markets/fx_cny_per_usd.csv", "cny_per_usd_avg")
    iy, iv = ctx.index_2006({a: 1/b for a, b in zip(y, fx)})
    ctx.line(ax, iy, iv, p.RED)
    _mark(ig, ax, "devaluation", 0.88)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "World Bank official-rate average; PBoC fixing and CFETS close are distinct")
    ax = ig.slot("markets.equities", "SSE Composite in US$ (index 2006 = 100)")
    sy, sv = _yr(ctx, "markets/sse_index.csv", "close")
    fxd = dict(zip(y, fx))
    iy, iv = ctx.index_2006({a: b/fxd[a] for a, b in zip(sy, sv) if a in fxd})
    ctx.line(ax, iy, iv, p.RED, label="SSE Composite")
    py, pv = _yr(ctx, "markets/spx_index.csv", "close")
    py, pv = ctx.index_2006(dict(zip(py, pv)))
    ctx.line(ax, py, pv, p.BLUE, ls="--", label="S&P 500")
    _mark(ig, ax, "stock_crash", 0.86)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _foot(p, ax, "Yahoo price indexes (non-official); SSE converted with annual-average CNY/US$")
    _finish(ig)


def plate_credit(ctx, ig):
    p = ctx.p
    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    y, v = _yr(ctx, "credit/household_credit.csv", "hh_credit_pct_gdp_q4")
    ctx.line(ax, y, v, p.RED, label="Households and NPISH")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _foot(p, ax, "BIS total credit, Q4 stock, adjusted for breaks")
    ax = ig.slot("credit.lending_rate", "Household lending rate vs policy rate (%)")
    _pending(ctx, ig, ax, "Comparable household lending and policy-rate regimes are not staged")
    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    y, v = _yr(ctx, "credit/npl_intl.csv", "npl_pct")
    ctx.line(ax, y, v, p.PURPLE)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "IMF Financial Soundness Indicator via World Bank; bank-wide, not households")
    ax = ig.slot("credit.lens", "Lens — private-sector debt service (% of income)")
    y, v = _yr(ctx, "credit/private_dsr.csv", "private_dsr_pct_q4")
    ctx.line(ax, y, v, p.BLUE, label="Private non-financial sector")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _foot(p, ax, "BIS Q.CN.P; broader than households and never labelled household DSR")
    _finish(ig)


def plate_people(ctx, ig):
    p = ctx.p
    ax = ig.slot("people.gini", "Income inequality, Gini (0–100)")
    y, v = _yr(ctx, "people/gini_intl.csv", "gini")
    ctx.line(ax, y, v, p.RED, label="World Bank survey series")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    _foot(p, ax, "Holes remain holes; the NBS national Gini would ride beside this line")
    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    y, v = _yr(ctx, "people/poverty_intl.csv", "poverty_830_pct")
    ctx.line(ax, y, v, p.RED, label="US$8.30/day, 2021 PPP")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    _foot(p, ax, "World Bank PIP; an international threshold, not China's national poverty line")
    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    _pending(ctx, ig, ax, "No national statutory rate: provinces and municipalities set different floors")
    ax = ig.slot("people.lens", "Lens — poverty at three international lines (%)")
    y, low = _yr(ctx, "people/pov_lines_intl.csv", "poverty_300_pct")
    _, mid = _yr(ctx, "people/pov_lines_intl.csv", "poverty_420_pct")
    _, high = _yr(ctx, "people/poverty_intl.csv", "poverty_830_pct")
    ctx.line(ax, y, low, p.GREEN, label="US$3.00/day")
    ctx.line(ax, y, mid, p.BLUE, label="US$4.20/day")
    ctx.line(ax, y, high, p.RED, label="US$8.30/day")
    ax.legend(loc="upper right", fontsize=7.1, frameon=False)
    _foot(p, ax, "World Bank PIP, 2021 PPP; survey years only")
    _finish(ig)


def plate_world(ctx, ig):
    p = ctx.p
    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    y, v = _yr(ctx, "economy/gdp_usd.csv", "gdp_usd")
    ctx.line(ax, y, [n/1e9 for n in v], p.RED)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "World Bank; current US$ is a size reading, not real growth")
    ax = ig.slot("world.hdi", "Human Development Index (HDI, 0–1)")
    y, v = _yr(ctx, "international/hdi.csv", "hdi")
    ctx.line(ax, y, v, p.BLUE)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "UNDP HDR 2025 vintage; ends in 2023")
    ax = ig.slot("world.cpi", "Corruption Perceptions Index (score, 0–100)")
    y, v = _yr(ctx, "international/corruption_intl.csv", "cpi_score")
    ctx.line(ax, y, v, p.PURPLE)
    _foot(p, ax, "Transparency International; comparable 2012 method only")
    ax = ig.slot("world.reserves", "Official reserves (US$ bn)")
    y, v = _yr(ctx, "markets/reserves_intl.csv", "reserves_usd")
    ctx.line(ax, y, [n/1e9 for n in v], p.RED)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "World Bank / IMF IFS incl. gold; SAFE national reserve assets remain separate")
    _finish(ig)


def plate_demography(ctx, ig):
    p = ctx.p
    pop = _pop(ctx)
    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    y, v = ctx.index_2006(pop)
    ctx.line(ax, y, v, p.RED)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "World Bank / UN WPP mainland-China scope; NBS census series is not spliced")
    ax = ig.slot("demography.fertility", "Total fertility rate (children per woman)")
    y, v = _yr(ctx, "demography/vital_intl.csv", "fertility")
    ctx.line(ax, y, v, p.PURPLE)
    ax.axhline(2.1, color=p.FAINT, ls=":", lw=1)
    ig.add_recessions(ax, label=False)
    ax = ig.slot("demography.birth_death", "Births and deaths (per 1,000 people)")
    y, b = _yr(ctx, "demography/vital_intl.csv", "birth_rate_per_1000")
    _, d = _yr(ctx, "demography/vital_intl.csv", "death_rate_per_1000")
    ctx.line(ax, y, b, p.GREEN, label="Births")
    ctx.line(ax, y, d, p.RED, label="Deaths")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)
    _foot(p, ax, "World Bank published rates; births fell below deaths in 2022")
    ax = ig.slot("demography.natural_migration", "Natural increase and net migration (per 1,000 people)")
    ctx.bars(ax, y, [a-b for a, b in zip(b, d)],
             lambda n: p.GREEN if n >= 0 else p.RED)
    my, mv = _yr(ctx, "demography/vital_intl.csv", "net_migration")
    pts = {a: b/pop[a]*1000 for a, b in zip(my, mv) if a in pop}
    ctx.line(ax, list(pts), list(pts.values()), p.BLUE, label="Net migration")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    _foot(p, ax, "World Bank: published vital rates; net migration count divided by population")
    _finish(ig)


def plate_security(ctx, ig):
    p = ctx.p
    S = "security/security_intl.csv"
    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    y, v = _yr(ctx, S, "homicide_per_100k")
    ctx.line(ax, y, v, p.RED, label="UNODC via World Bank")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    _foot(p, ax, "No accessible comparable national police series; this ends in 2020")
    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    y, v = _yr(ctx, S, "suicide_per_100k")
    ctx.line(ax, y, v, p.PURPLE, label="WHO via World Bank")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    ax = ig.slot("security.road_deaths", "Road traffic deaths (per 100,000)")
    y, v = _yr(ctx, S, "road_deaths_per_100k")
    ctx.line(ax, y, v, p.RED, label="WHO via World Bank")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    ax = ig.slot("security.lens", "Lens — national public-safety series")
    _pending(ctx, ig, ax, "Police and transport series are not published in an accessible comparable form")
    _finish(ig)


def plate_mortality(ctx, ig):
    p = ctx.p
    ax = ig.slot("mortality.death_rate", "Crude death rate (per 1,000 people)")
    y, v = _yr(ctx, "demography/vital_intl.csv", "death_rate_per_1000")
    ctx.line(ax, y, v, p.RED, label="World Bank / UN WPP")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _foot(p, ax, "Published harmonised rate; NBS census rebases must remain a separate series")
    ax = ig.slot("mortality.excess_deaths", "Excess deaths (% above 2015–2019 average)")
    _pending(ctx, ig, ax, "Annual death counts on a consistent national vintage are not staged")
    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause (per 100,000)")
    _pending(ctx, ig, ax, "Official reporting stopped in 2023 and the counts are not comparable")
    ax = ig.slot("mortality.lens", "Lens — causes of death")
    _pending(ctx, ig, ax, "A comparable cause-of-death table is not accessible from the staged sources")
    _finish(ig)


def plate_migration(ctx, ig):
    p = ctx.p
    pop = _pop(ctx)
    ax = ig.slot("migration.flows", "Immigration and emigration (per 1,000 people)")
    _pending(ctx, ig, ax, "Comparable immigration and emigration flows are not staged")
    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    y, v = _yr(ctx, "demography/vital_intl.csv", "net_migration")
    vals = [n/pop[a]*1000 for a, n in zip(y, v) if a in pop]
    years = [a for a in y if a in pop]
    ctx.bars(ax, years, vals, lambda n: p.GREEN if n >= 0 else p.RED)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "World Bank / UN DESA five-year estimates carried annually; not border records")
    ax = ig.slot("migration.foreign_born", "Foreign-born share of population (%)")
    y, v = _yr(ctx, "migration/migrant_stock_intl.csv", "migrant_stock_pct")
    ctx.line(ax, y, v, p.RED, label="International migrant stock")
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    _foot(p, ax, "UN DESA snapshots only: 2010, 2015, 2020 and 2024; never interpolated")
    ax = ig.slot("migration.lens", "Lens — urban population share (%)")
    y, v = _yr(ctx, "migration/urban_share_intl.csv", "urban_share_pct")
    ctx.line(ax, y, v, p.BLUE)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "World Bank / UN WPP; not a hukou or floating-population measure")
    _finish(ig)


BUILDERS = (plate_economy, plate_fiscal, plate_spending, plate_trade,
            plate_markets, plate_credit, plate_people, plate_world,
            plate_demography, plate_security, plate_mortality, plate_migration)
TOPICS = ("economy", "fiscal", "spending", "trade", "markets", "credit",
          "people", "world", "demography", "security", "mortality", "migration")
TITLES = ("The Economy", "Public Finances", "Where the Money Goes", "Trade",
          "Money and Markets", "Credit", "People", "China in the World",
          "Demography", "Security", "Mortality", "Migration")

PLATES = tuple(
    dict(id=f"{i:02d}", slug=topic, topic=topic, builder=builder, title=title,
         subtitle="Harmonised readings while national machine sources remain blocked; never spliced.",
         source="Sources: World Bank · IMF · BIS · UNDP · UN Comtrade · Transparency International",
         alt=f"Four data panels about China: {topic}, 2006–2026.")
    for i, (topic, builder, title) in enumerate(zip(TOPICS, BUILDERS, TITLES), 1)
)
