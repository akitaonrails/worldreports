"""Vietnam's twelve data plates, born on the shared plate spine.

National series are labelled NSO/SBV. International series remain separate
comparators because several national concepts have different populations,
methods or accounting perimeters. Reviewed publication CSVs have stable names;
fetch sidecars are never read here.
"""
from __future__ import annotations

from core.sideload import sibling

events = sibling(__file__, "events")
W0 = 2006


def _yr(ctx, rel, col, since=W0, until=None):
    t = ctx.table(rel)
    if not t or col not in t:
        return [], []
    y, v = ctx.series(t, col)
    pairs = [(int(a), float(b)) for a, b in zip(y, v)
             if a >= since and (until is None or a <= until)]
    return [a for a, _ in pairs], [b for _, b in pairs]


def _finish(ig):
    for ax in ig.axes_flat:
        if ax.get_visible():
            ig.style_axis(ax)


def _foot(p, ax, text):
    ax.text(.5, -.07, text, transform=ax.transAxes, ha="center", va="top",
            fontsize=7.0, color=p.FAINT, style="italic")


def _mark(ig, ax, key, dy=.96):
    x, label = events.MARKS[key]
    ig.add_event(ax, x, label, dy=dy)


def _line(ctx, ax, rel, col, color, label=None, **kw):
    y, v = _yr(ctx, rel, col)
    if y:
        ctx.line(ax, y, v, color, label=label, **kw)
    return y, v


def _rows(ctx, rel):
    return ctx.rows(rel) or {}


def plate_economy(ctx, ig):
    p = ctx.p
    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    y, v = _yr(ctx, "macro/gdp.csv", "real_growth_pct")
    ctx.bars(ax, y, v, lambda n: p.JADE if n >= 0 else p.RED)
    ax.axhline(0, color=p.FAINT, lw=.8)
    _foot(p, ax, "NSO national accounts; annual growth is within-scale")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    a, b = _yr(ctx, "international/gdp_usd_wb.csv", "gdp_per_person_usd_old_scale", until=2009)
    c, d = _yr(ctx, "international/gdp_usd_wb.csv", "gdp_per_person_usd", since=2010)
    ctx.line(ax, a, b, p.FAINT, label="World Bank, old GDP scale")
    ctx.line(ax, c, d, p.BLUE, label="World Bank, revalued GDP scale")
    _mark(ig, ax, "gdp_scale", dy=.56)
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)

    ax = ig.slot("economy.inflation", "Consumer price inflation (% per year)")
    y, idx = _yr(ctx, "macro/cpi.csv", "cpi")
    inf = [n - 100 for n in idx]
    ctx.line(ax, y, inf, p.RED)
    _mark(ig, ax, "inflation_2008", dy=.88)
    _foot(p, ax, "NSO annual-average CPI; previous year = 100")

    ax = ig.slot("economy.unemployment", "Unemployment (% of labour force)")
    _line(ctx, ax, "social/labour.csv", "unemployment_national_pct", p.NAVY,
          "NSO, working age")
    _line(ctx, ax, "social/unemployment_adb.csv", "unemployment_rate_pct", p.GOLD,
          "ADB, age 15+", ls="--")
    ax.legend(loc="upper right", fontsize=7.5, frameon=False)
    _finish(ig)


def plate_fiscal(ctx, ig):
    p = ctx.p
    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure (% of GDP)")
    _line(ctx, ax, "fiscal/gg_finance.csv", "revenue_pct_gdp", p.JADE,
          "General-government revenue")
    _line(ctx, ax, "fiscal/gg_finance.csv", "expenditure_pct_gdp", p.RED,
          "General-government expenditure")
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)
    _foot(p, ax, "ADB GFSM 2014; general government, through 2022")

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    y, overall = _yr(ctx, "fiscal/gg_finance.csv", "net_lending_pct_gdp")
    ctx.bars(ax, y, overall, lambda n: p.JADE if n >= 0 else p.RED)
    _line(ctx, ax, "fiscal/gg_finance.csv", "primary_balance_pct_gdp", p.NAVY,
          "Primary balance")
    ax.legend(loc="lower left", fontsize=7.4, frameon=False)

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    _line(ctx, ax, "fiscal/debt_balance.csv", "gross_debt_pct_gdp", p.RED,
          "IMF general government")
    _line(ctx, ax, "fiscal/debt_balance.csv", "gross_debt_pct_gdp_proj", p.RED,
          "IMF projection", ls="--")
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    rows = _rows(ctx, "fiscal/gg_finance.csv")
    pts = [(y, float(r["interest_bn_vnd"]) / float(r["expenditure_bn_vnd"])
            * float(r["expenditure_pct_gdp"])) for y, r in rows.items()
           if r.get("interest_bn_vnd") and r.get("expenditure_bn_vnd")
           and r.get("expenditure_pct_gdp") and y >= W0]
    ctx.line(ax, *zip(*pts), p.PURPLE)
    _foot(p, ax, "ADB interest expense divided by the same GG GDP denominator")
    _finish(ig)


def plate_spending(ctx, ig):
    p = ctx.p
    rows = _rows(ctx, "spending/budget_spending.csv")
    years = sorted(y for y, r in rows.items() if y >= 2018 and r.get("exp_total_pct_gdp"))
    groups = [
        ("Education", "exp_education_training_pct_gdp", p.GOLD),
        ("Health", "exp_health_population_vnd_bn", p.JADE),
        ("Social protection", "exp_social_security_vnd_bn", p.RED),
        ("Economic affairs", "exp_economic_environment_vnd_bn", p.BLUE),
        ("Administration", "exp_administration_party_vnd_bn", p.PURPLE),
    ]
    totals = {y: float(rows[y]["exp_total_vnd_bn"]) for y in years}
    vals = []
    for _, col, _ in groups:
        vals.append([float(rows[y].get(col) or 0) / totals[y]
                     * float(rows[y]["exp_total_pct_gdp"]) for y in years])
    ax = ig.slot("spending.by_function", "Budget spending by function (% of GDP)")
    ax.stackplot(years, *vals, labels=[x[0] for x in groups],
                 colors=[x[2] for x in groups], alpha=.9)
    ax.legend(loc="upper left", fontsize=6.8, ncol=2, frameon=False)
    _foot(p, ax, "NSO national budget heads; defence and public order unavailable")

    ax = ig.slot("spending.social_protection", "Social protection vs everything else (% of GDP)")
    social = vals[2]
    total = [float(rows[y]["exp_total_pct_gdp"]) for y in years]
    ctx.line(ax, years, social, p.RED, label="Social-security budget head")
    ctx.line(ax, years, [t-s for t, s in zip(total, social)], p.NAVY,
             label="Other published heads")
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)

    ax = ig.slot("spending.investment", "Investment rate, whole economy (% of GDP)")
    _line(ctx, ax, "macro/gdp.csv", "fixed_assets_pct_gdp", p.BLUE)
    _foot(p, ax, "NSO fixed assets as a share of GDP")

    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    rows2 = _rows(ctx, "fiscal/gg_finance.csv")
    pts = [(y, float(r["net_investment_nonfinancial_assets_bn_vnd"])
            / float(r["expenditure_bn_vnd"]) * float(r["expenditure_pct_gdp"]))
           for y, r in rows2.items() if y >= W0
           and r.get("net_investment_nonfinancial_assets_bn_vnd")
           and r.get("expenditure_bn_vnd") and r.get("expenditure_pct_gdp")]
    ctx.line(ax, *zip(*pts), p.JADE)
    _foot(p, ax, "ADB general-government net investment, through 2022")
    _finish(ig)


def plate_trade(ctx, ig):
    p = ctx.p
    ax = ig.slot("trade.exports_imports", "Exports and imports (% of GDP)")
    _line(ctx, ax, "macro/gdp.csv", "exports_gs_pct_gdp", p.JADE, "Exports")
    _line(ctx, ax, "macro/gdp.csv", "imports_gs_pct_gdp", p.RED, "Imports")
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    ey, ev = _yr(ctx, "macro/gdp.csv", "exports_gs_pct_gdp")
    iy, iv = _yr(ctx, "macro/gdp.csv", "imports_gs_pct_gdp")
    imp = dict(zip(iy, iv)); yy = [y for y in ey if y in imp]
    ctx.bars(ax, yy, [v - imp[y] for y, v in zip(ey, ev) if y in imp],
             lambda n: p.JADE if n >= 0 else p.RED)

    ax = ig.slot("trade.destinations", "Top export destinations (% of goods exports)")
    rr = ctx.rows("trade/exports_by_partner.csv", key="year") or {}
    # rows() cannot retain repeated years; read columns directly instead.
    t = ctx.table("trade/exports_by_partner.csv")
    records = list(zip(t["year"], t["partner"], t["partner_iso3"], t["kind"], t["exports_usd_mn"]))
    totals = {int(y): float(v) for y, _, _, kind, v in records if kind == "total" and v == v}
    latest = max(y for y in totals if y <= ctx.LAST_FULL_YEAR)
    candidates = {}
    for y, name, iso, kind, value in records:
        y = int(y)
        if kind == "country" and value == value and y >= W0 and y in totals:
            candidates.setdefault(iso or name, {})[y] = float(value) / totals[y] * 100
    top = sorted(candidates, key=lambda k: candidates[k].get(latest, 0), reverse=True)[:5]
    for i, name in enumerate(top):
        pts = sorted(candidates[name].items())
        ctx.line(ax, *zip(*pts), p.cycle(i), label=name)
    ax.legend(loc="upper left", fontsize=7.0, ncol=2, frameon=False)

    ax = ig.slot("trade.lens", "Lens — merchandise balance with the US and China (US$ bn)")
    ex = ctx.table("trade/exports_by_partner.csv"); im = ctx.table("trade/imports_by_partner.csv")
    def country(table, code, col):
        return {int(y): float(v) for y, iso, kind, v in zip(table["year"], table["partner_iso3"], table["kind"], table[col]) if iso == code and kind == "country" and v == v and int(y) >= W0}
    for i, code in enumerate(("USA", "CHN")):
        a, b = country(ex, code, "exports_usd_mn"), country(im, code, "imports_usd_mn")
        pts = sorted((y, (a[y]-b[y])/1000) for y in a if y in b)
        ctx.line(ax, *zip(*pts), p.cycle(i), label=code)
    ax.axhline(0, color=p.FAINT, lw=.8); ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    _finish(ig)


def plate_markets(ctx, ig):
    p = ctx.p
    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    ctx.pending(ax)
    _foot(p, ax, "No verified SBV policy-rate history is staged; commercial lending rates remain on the credit plate")

    ax = ig.slot("markets.bond_10y", "10-year government bond yield")
    ctx.pending(ax)
    _foot(p, ax, "AsianBondsOnline history not staged")

    ax = ig.slot("markets.currency", "VND against US$ (index 2006 = 100, up = stronger)")
    y, rate = _yr(ctx, "markets/usdvnd.csv", "usdvnd_avg")
    if y:
        base = rate[0]; ctx.line(ax, y, [base/n*100 for n in rate], p.GOLD)
    _foot(p, ax, "World Bank annual average; inverted so up means stronger")

    ax = ig.slot("markets.equities", "VN-Index in US$ (index 2006 = 100)")
    sy, sv = _yr(ctx, "markets/vnindex.csv", "close")
    fx = dict(zip(*_yr(ctx, "markets/usdvnd.csv", "usdvnd_end_period")))
    usd = {y: v/fx[y] for y, v in zip(sy, sv) if y in fx}
    if usd:
        base = usd[min(usd)]; pts = sorted((y, v/base*100) for y, v in usd.items())
        ctx.line(ax, *zip(*pts), p.RED)
    _foot(p, ax, "CafeF year-end close converted at ADB end-period VND/US$")
    _finish(ig)


def plate_credit(ctx, ig):
    p = ctx.p
    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    ctx.pending(ax)
    _foot(p, ax, "Economy-wide private credit is not household debt; no verified household series is staged")

    ax = ig.slot("credit.lending_rate", "Average lending rate (%)")
    _line(ctx, ax, "markets/rates_fx.csv", "lending_vnd_short", p.GOLD,
          "Short-term VND lending")
    _line(ctx, ax, "markets/rates_fx.csv", "lending_vnd_medium_long", p.RED,
          "Medium/long-term VND lending")
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    _line(ctx, ax, "credit/credit_adb.csv", "npl_ratio_pct", p.RED)
    _foot(p, ax, "ADB/IMF Financial Soundness Indicator")

    ax = ig.slot("credit.lens", "Lens — credit growth and money (% / % of GDP)")
    _line(ctx, ax, "credit/private_credit.csv", "private_credit_pct_gdp", p.NAVY,
          "Economy-wide private credit / GDP")
    _line(ctx, ax, "credit/credit_adb.csv", "m2_growth_pct", p.JADE, "M2 growth")
    _line(ctx, ax, "credit/credit_adb.csv", "m2_pct_gdp", p.PURPLE, "M2 / GDP")
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)
    _finish(ig)


def plate_people(ctx, ig):
    p = ctx.p
    ax = ig.slot("people.gini", "Income inequality, Gini (0–100)")
    a, b = _yr(ctx, "social/gini.csv", "gini_national_2002_2019", until=2019)
    c, d = _yr(ctx, "social/gini.csv", "gini_national_2020_on", since=2020)
    ctx.line(ax, a, [n*100 for n in b], p.NAVY, label="NSO VHLSS, old segment")
    ctx.line(ax, c, [n*100 for n in d], p.NAVY, ls="--", label="NSO VHLSS, 2020-on")
    _line(ctx, ax, "social/inequality_wb.csv", "gini", p.GOLD,
          "World Bank consumption Gini")
    _mark(ig, ax, "gini_break"); ax.legend(loc="lower left", fontsize=6.8, frameon=False)

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    _line(ctx, ax, "social/inequality_wb.csv", "poverty_national_line_pct", p.GOLD,
          "World Bank people, national line", ls="--")
    ax.legend(loc="upper right", fontsize=6.9, frameon=False)

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    ctx.pending(ax); _foot(p, ax, "Four regional statutory rates; reviewed history not staged")

    ax = ig.slot("people.lens", "Lens — richest-to-poorest income ratio")
    t = ctx.table("social/income_quintiles.csv")
    pts = [(int(y), float(q5)/float(q1)) for y, level, q1, q5 in zip(t["year"], t["breakdown"], t["q1"], t["q5"]) if level == "national" and int(y) >= W0 and q1 == q1 and q5 == q5]
    ctx.line(ax, *zip(*pts), p.PURPLE)
    _foot(p, ax, "NSO monthly income per person: quintile 5 divided by quintile 1")
    _finish(ig)


def plate_world(ctx, ig):
    p = ctx.p
    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    _line(ctx, ax, "international/gdp_usd_imf.csv", "gdp_usd_bn", p.RED, "IMF back-cast")
    _line(ctx, ax, "international/gdp_usd_imf.csv", "gdp_usd_bn_proj", p.RED, "IMF projection", ls="--")
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)

    ax = ig.slot("world.hdi", "Human Development Index (0–1)")
    _line(ctx, ax, "international/hdi_undp.csv", "hdi", p.NAVY, "UNDP")
    _line(ctx, ax, "international/hdi_gso.csv", "hdi_nso", p.GOLD, "NSO national HDI")
    ax.legend(loc="lower right", fontsize=7.4, frameon=False)

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (0–100)")
    _line(ctx, ax, "international/cpi_ti.csv", "cpi_score", p.PURPLE,
          "Transparency International")
    _foot(p, ax, "Comparable 2012-method CPI series; higher = perceived cleaner")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn)")
    y, v = _yr(ctx, "international/reserves.csv", "reserves_usd")
    ctx.line(ax, y, [n/1e9 for n in v], p.JADE)
    _finish(ig)


def plate_demography(ctx, ig):
    p = ctx.p
    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    y, v = _yr(ctx, "demography/population.csv", "population_total_thousand")
    base = v[0]; ctx.line(ax, y, [n/base*100 for n in v], p.RED)

    ax = ig.slot("demography.fertility", "Total fertility rate (children per woman)")
    _line(ctx, ax, "demography/vital_rates.csv", "tfr_total", p.RED, "NSO")
    _line(ctx, ax, "demography/population_wb.csv", "tfr", p.GOLD, "World Bank", ls="--")
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)

    ax = ig.slot("demography.birth_death", "Crude birth and death rates (per 1,000)")
    _line(ctx, ax, "demography/vital_rates.csv", "cbr_total_per_mille", p.JADE, "Births")
    _line(ctx, ax, "demography/vital_rates.csv", "cdr_total_per_mille", p.RED, "Deaths")
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)

    ax = ig.slot("demography.natural_migration", "Natural increase and net migration (per 1,000)")
    _line(ctx, ax, "demography/vital_rates.csv", "natural_increase_total_per_mille", p.JADE, "Natural increase")
    pop = {y: v*1000 for y, v in zip(*_yr(ctx, "demography/population.csv", "population_total_thousand"))}
    ny, nv = _yr(ctx, "migration/net_migration.csv", "net_migration")
    pts = [(y, n/pop[y]*1000) for y, n in zip(ny, nv) if y in pop and y != 2006]
    ctx.line(ax, *zip(*pts), p.PURPLE, label="UN modelled net migration")
    ax.legend(loc="upper right", fontsize=7.1, frameon=False)
    _finish(ig)


def plate_security(ctx, ig):
    p = ctx.p
    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    _line(ctx, ax, "security/homicide_who.csv", "homicide_per_100k", p.RED, "WHO model")
    _line(ctx, ax, "security/homicide_wb.csv", "homicide_per_100k", p.FAINT, "UNODC via World Bank", ls="--")
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    t = ctx.table("mortality/causes.csv")
    pts = [(int(y), float(r)) for y, code, r in zip(t["year"], t["cause_code"], t["rate_per_100k"]) if code == 1610 and int(y) >= W0 and r == r]
    ctx.line(ax, *zip(*pts), p.PURPLE); _foot(p, ax, "WHO GHE modelled self-harm")

    ax = ig.slot("security.road_deaths", "Road traffic deaths (per 100,000)")
    _line(ctx, ax, "security/road_deaths.csv", "road_deaths_per_100k", p.GOLD, "WHO model")
    pop = {y: v*1000 for y, v in zip(*_yr(ctx, "demography/population.csv", "population_total_thousand"))}
    a, b = _yr(ctx, "security/traffic_fire.csv", "traffic_deaths_to2021", until=2021)
    c, d = _yr(ctx, "security/traffic_fire.csv", "traffic_deaths_from2022", since=2022)
    ctx.line(ax, *zip(*[(y, n/pop[y]*1e5) for y,n in zip(a,b) if y in pop]), p.NAVY, label="Police, old series")
    ctx.line(ax, *zip(*[(y, n/pop[y]*1e5) for y,n in zip(c,d) if y in pop]), p.NAVY, ls="--", label="Police, 2022-on")
    _mark(ig, ax, "traffic_break"); ax.legend(loc="lower left", fontsize=6.8, frameon=False)

    ax = ig.slot("security.lens", "Lens — justice-system cases (thousands)")
    y, v = _yr(ctx, "security/justice.csv", "cases_prosecuted")
    ctx.line(ax, y, [n/1000 for n in v], p.RED, label="Prosecuted")
    y, v = _yr(ctx, "security/justice.csv", "cases_tried")
    ctx.line(ax, y, [n/1000 for n in v], p.NAVY, label="Tried")
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _finish(ig)


def plate_mortality(ctx, ig):
    p = ctx.p
    ax = ig.slot("mortality.death_rate", "Crude death rate (per 1,000)")
    _line(ctx, ax, "demography/vital_rates.csv", "cdr_total_per_mille", p.RED, "NSO survey")

    ax = ig.slot("mortality.excess_deaths", "Excess deaths vs 2015–2019 mean (%)")
    ctx.pending(ax)
    _foot(p, ax, "The death register begins in 2018, so the canonical 2015–2019 baseline cannot be computed")

    ax = ig.slot("mortality.covid", "COVID-19 deaths, modelled (per 100,000)")
    t = ctx.table("mortality/causes.csv")
    pts = [(int(y), float(r)) for y, code, r in zip(t["year"], t["cause_code"], t["rate_per_100k"]) if code == 395 and int(y)>=W0 and r == r]
    ctx.line(ax, *zip(*pts), p.RED); _mark(ig, ax, "covid")
    _foot(p, ax, "WHO GHE model; Vietnam has no ICD-coded national register")

    ax = ig.slot("mortality.lens", "Lens — modelled major causes (per 100,000)")
    for i, (code, label) in enumerate(((610,"Malignant neoplasms"),(1100,"Cardiovascular diseases"))):
        pts = [(int(y), float(r)) for y,c,r in zip(t["year"],t["cause_code"],t["rate_per_100k"]) if c==code and int(y)>=W0 and r==r]
        ctx.line(ax, *zip(*pts), p.cycle(i), label=label)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    _finish(ig)


def plate_migration(ctx, ig):
    p = ctx.p
    ax = ig.slot("migration.flows", "International immigration and emigration")
    ctx.pending(ax); _foot(p, ax, "No national international-flow series")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    pop = {y: v*1000 for y,v in zip(*_yr(ctx,"demography/population.csv","population_total_thousand"))}
    y, v = _yr(ctx, "migration/net_migration.csv", "net_migration")
    pts = [(yy, n/pop[yy]*1000) for yy,n in zip(y,v) if yy in pop and yy != 2006]
    ctx.line(ax, *zip(*pts), p.PURPLE); _foot(p, ax, "UN/WB model; 2006 artefact omitted")

    ax = ig.slot("migration.foreign_born", "Immigrant stock (% of population)")
    y, v = _yr(ctx, "migration/migrant_stock.csv", "immigrants_in_vietnam")
    pts = [(yy, n/pop[yy]*100) for yy,n in zip(y,v) if yy in pop]
    if pts: ctx.line(ax, *zip(*pts), p.BLUE)
    _foot(p, ax, "UN DESA citizenship-plus-refugees stock; not country of birth")

    ax = ig.slot("migration.lens", "Lens — Vietnamese emigrants abroad (millions)")
    y, v = _yr(ctx, "migration/migrant_stock.csv", "emigrants_world")
    ctx.line(ax, y, [n/1e6 for n in v], p.RED, label="Emigrant stock")
    y, v = _yr(ctx, "migration/remittances_proxy.csv", "secondary_income_credit_mn_usd")
    ctx.line(ax, y, [n/10000 for n in v], p.GOLD, label="Secondary-income credits / 10")
    ax.legend(loc="upper left", fontsize=7.0, frameon=False)
    _foot(p, ax, "stock beside a labelled remittance superset; never treated as flows")
    _finish(ig)


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy, title="Vietnam's Economy", subtitle="Growth, income, prices and work across the GDP revaluation.", source="Sources: NSO · World Bank · ADB", alt="Four panels on Vietnam's economy."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal, title="Public Finances", subtitle="General-government accounts remain separate from the state budget.", source="Sources: ADB · IMF · NSO", alt="Four panels on Vietnam's public finances."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending, title="Public Spending and Investment", subtitle="National budget heads beside the whole economy's investment rate.", source="Sources: NSO · ADB", alt="Four panels on spending and investment in Vietnam."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade, title="Trade", subtitle="An export economy whose partner balances point in opposite directions.", source="Source: NSO", alt="Four panels on Vietnam's trade."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets, title="Markets", subtitle="The policy history stays pending; the đồng and VN-Index remain comparable.", source="Sources: NSO/SBV · World Bank · CafeF", alt="Four panels on Vietnam's markets, with policy rates visibly pending."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit, title="Credit and Money", subtitle="Household debt stays pending; economy-wide credit remains in the country lens.", source="Sources: NSO/SBV · ADB · World Bank", alt="Four panels on credit and money in Vietnam, separating household debt from economy-wide credit."),
    dict(id="07", slug="people", topic="people", builder=plate_people, title="People and Incomes", subtitle="Survey seams and changing poverty standards stay separate.", source="Sources: NSO · World Bank", alt="Four panels on inequality, poverty and income in Vietnam."),
    dict(id="08", slug="world", topic="world", builder=plate_world, title="Vietnam in the World", subtitle="International comparables beside Vietnam's national HDI.", source="Sources: IMF · UNDP · NSO · World Bank · Transparency International", alt="Four panels placing Vietnam in international context, including the comparable 2012-method Corruption Perceptions Index."),
    dict(id="09", slug="demography", topic="demography", builder=plate_demography, title="Demography", subtitle="Population growth slows as fertility falls below replacement.", source="Sources: NSO · World Bank · UN", alt="Four panels on Vietnam's demography."),
    dict(id="10", slug="security", topic="security", builder=plate_security, title="Security and Road Safety", subtitle="Modelled violence rates beside police and justice-system counts.", source="Sources: WHO · World Bank/UNODC · NSO", alt="Four panels on security and road deaths in Vietnam."),
    dict(id="11", slug="mortality", topic="mortality", builder=plate_mortality, title="Mortality", subtitle="The short register cannot supply the shared 2015–2019 excess baseline; WHO causes remain separate.", source="Sources: NSO · WHO GHE", alt="Four panels on mortality in Vietnam, with comparable excess deaths pending."),
    dict(id="12", slug="migration", topic="migration", builder=plate_migration, title="Migration", subtitle="Stocks and modelled net migration, without invented international flows.", source="Sources: UN DESA · World Bank/WPP · ADB", alt="Four panels on migration related measures for Vietnam."),
)
