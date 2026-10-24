"""Portugal's twelve data plates on the shared comparison spine.

All plotted inputs are reviewed copies under data/published.  National and
harmonised definitions are labelled separately and never spliced.  Rates use
the revised INE resident population for the same calendar year unless the
publisher supplies the rate directly.
"""
from __future__ import annotations

from core.sideload import sibling

events = sibling(__file__, "events")


def _yr(ctx, name, col, since=2006):
    t = ctx.table(f"published/{name}.csv")
    if not t or col not in t:
        return [], []
    ys, vs = ctx.series(t, col)
    keep = [(int(y), float(v)) for y, v in zip(ys, vs)
            if y >= since and v == v]
    return [y for y, _ in keep], [v for _, v in keep]


def _d(ctx, name, col):
    return dict(zip(*_yr(ctx, name, col)))


def _note(ctx, ax, text, x=0.02, y=0.96, ha="left"):
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va="top",
            fontsize=7.5, color=ctx.p.MUTED, style="italic")


def _foot(ctx, ax, text):
    ax.text(0.5, -0.095, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.0, color=ctx.p.FAINT, style="italic")


def _finish(ctx, ig):
    for ax in ig.axes_flat:
        ig.style_axis(ax)


def _pop(ctx):
    return _d(ctx, "demography_ine", "population")


def _cause(ctx, code):
    table = ctx.table("published/causes_of_death_ine.csv")
    out = {}
    for year, got_code, old, new in zip(
            table["year"], table["cause_code"],
            table["deaths_nuts2013"], table["deaths_nuts2024"]):
        if int(got_code) != int(code):
            continue
        value = new if new == new else old
        if value == value:
            out[int(year)] = float(value)
    return out


def _bands(ig, ax, label=False):
    ig.add_recessions(ax, label=False)


def plate_economy(ctx, ig):
    p = ctx.p
    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    y, v = _yr(ctx, "gdp_estat", "real_growth")
    ctx.bars(ax, y, v, lambda n: p.VERDE if n >= 0 else p.RED)
    _bands(ig, ax, True)
    _foot(ctx, ax, "Eurostat national accounts; current vintage")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    y, v = _yr(ctx, "gdp_pc_wb", "gdp_per_person_usd")
    ctx.line(ax, y, v, p.BLUE)
    _bands(ig, ax)
    ctx.endlabel(ax, y, v, p.BLUE, lambda n: f"US${n:,.0f}", dy=8)

    ax = ig.slot("economy.inflation", "Consumer prices (% per year)")
    iy, iv = _yr(ctx, "ipc_ine", "ipc_avg_rate")
    hy, hv = _yr(ctx, "hicp_estat", "hicp")
    ax.axhline(2, color=p.FAINT, ls=":", lw=1)
    ctx.line(ax, iy, iv, p.RED, label="INE CPI")
    ctx.line(ax, hy, hv, p.NAVY, label="Eurostat HICP")
    _bands(ig, ax)
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)

    ax = ig.slot("economy.unemployment", "Unemployment (% of labour force)")
    ny, nv = _yr(ctx, "unemployment_ine", "rate_serie2021")
    ey, ev = _yr(ctx, "unemployment_estat", "estat")
    ctx.line(ax, ny, nv, p.RED, label="INE, 2021 series")
    ctx.line(ax, ey, ev, p.NAVY, ls="--", label="Eurostat LFS")
    _bands(ig, ax)
    ax.legend(loc="upper right", fontsize=7.3, frameon=False)
    _finish(ctx, ig)


def plate_fiscal(ctx, ig):
    p = ctx.p
    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure (% of GDP)")
    ry, rv = _yr(ctx, "revenue_estat", "revenue")
    ey, ev = _yr(ctx, "revenue_estat", "expenditure")
    ctx.line(ax, ry, rv, p.VERDE, label="Revenue")
    ctx.line(ax, ey, ev, p.RED, label="Expenditure")
    _bands(ig, ax, True)
    ax.legend(loc="lower right", fontsize=7.5, frameon=False)

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    by, bv = _yr(ctx, "deficit_estat", "deficit")
    py, pv = _yr(ctx, "deficit_estat", "primary")
    ctx.bars(ax, by, bv, lambda n: p.VERDE if n >= 0 else p.RED)
    ctx.line(ax, py, pv, p.NAVY, label="Primary balance")
    _bands(ig, ax)
    ax.legend(loc="lower right", fontsize=7.5, frameon=False)

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    y, v = _yr(ctx, "debt_estat", "gross_pct_gdp")
    ctx.line(ax, y, v, p.RED)
    _bands(ig, ax)
    _foot(ctx, ax, "Maastricht general-government gross debt")

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    y, v = _yr(ctx, "deficit_estat", "interest")
    ctx.line(ax, y, v, p.BRONZE)
    _bands(ig, ax)
    ctx.endlabel(ax, y, v, p.BRONZE, lambda n: f"{n:.1f}%", dy=8)
    _finish(ctx, ig)


def plate_spending(ctx, ig):
    p = ctx.p
    cols = [("Social protection", "social_protection", p.RED),
            ("Health", "health", p.TEAL),
            ("General services", "general_services", p.PURPLE),
            ("Education", "education", p.BRONZE),
            ("Economic affairs", "economic_affairs", p.BLUE),
            ("Defence and public order", "defence_order", p.NAVY),
            ("Other", "other", p.FAINT)]
    series = [(label, *_yr(ctx, "spending_by_function_estat", col), color)
              for label, col, color in cols]
    ax = ig.slot("spending.by_function", "Spending by function (% of GDP)")
    ys = series[0][1]
    ax.stackplot(ys, *[s[2] for s in series], labels=[s[0] for s in series],
                 colors=[s[3] for s in series], alpha=.9)
    _bands(ig, ax, True)
    ax.legend(loc="upper left", fontsize=6.5, ncol=2, frameon=False)

    ax = ig.slot("spending.social_protection", "Social protection vs other spending (% of GDP)")
    sy, sv = _yr(ctx, "spending_by_function_estat", "social_protection")
    ty, tv = _yr(ctx, "spending_by_function_estat", "total")
    total = dict(zip(ty, tv))
    ctx.line(ax, sy, sv, p.RED, label="Social protection")
    ctx.line(ax, sy, [total[y] - v for y, v in zip(sy, sv)], p.NAVY,
             label="All other functions")
    _bands(ig, ax)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)

    ax = ig.slot("spending.investment", "Investment (% of GDP)")
    gy, gv = _yr(ctx, "investment_estat", "gfcf_pct_gdp")
    ctx.line(ax, gy, gv, p.BLUE)
    _bands(ig, ax)
    _foot(ctx, ax, "Whole-economy gross fixed capital formation")

    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    y, v = _yr(ctx, "investment_estat", "gov_gfcf_pct_gdp")
    ctx.line(ax, y, v, p.VERDE)
    _bands(ig, ax)
    _finish(ctx, ig)


def plate_trade(ctx, ig):
    p = ctx.p
    gdp = _d(ctx, "gdp_estat", "nominal_eurbn")
    ex = _d(ctx, "trade_estat", "exports_eurbn")
    im = _d(ctx, "trade_estat", "imports_eurbn")
    years = sorted(set(gdp) & set(ex) & set(im))
    ax = ig.slot("trade.exports_imports", "Exports and imports (% of GDP)")
    ctx.line(ax, years, [ex[y] / gdp[y] * 100 for y in years], p.VERDE,
             label="Exports")
    ctx.line(ax, years, [im[y] / gdp[y] * 100 for y in years], p.RED,
             label="Imports")
    _bands(ig, ax, True)
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    bal = [(ex[y] - im[y]) / gdp[y] * 100 for y in years]
    ctx.bars(ax, years, bal, lambda n: p.VERDE if n >= 0 else p.RED)
    _bands(ig, ax)

    ax = ig.slot("trade.destinations", "Goods export destinations (% of goods exports)")
    t = ctx.table("published/goods_trade_ine.csv")
    ty = [int(y) for y in t["year"] if int(y) <= ctx.c.last_full_year]
    world = dict(zip(map(int, t["year"]), t["exports_mundo_eur"]))
    for label, col, color in [("Spain", "exports_es_eur", p.RED),
                              ("France", "exports_fr_eur", p.BLUE),
                              ("Germany", "exports_de_eur", p.NAVY),
                              ("United States", "exports_us_eur", p.BRONZE)]:
        vals = dict(zip(map(int, t["year"]), t[col]))
        yy = [y for y in ty if vals.get(y) == vals.get(y) and world.get(y)]
        ctx.line(ax, yy, [vals[y] / world[y] * 100 for y in yy], color,
                 label=label)
    _bands(ig, ax)
    ax.legend(loc="upper right", fontsize=7.0, frameon=False)

    ax = ig.slot("trade.lens", "Goods share of all exports (%)")
    goods = dict(zip(map(int, t["year"]), t["exports_mundo_eur"]))
    yy = [y for y in years if y in goods and goods[y] == goods[y]]
    ctx.line(ax, yy, [goods[y] / 1e9 / ex[y] * 100 for y in yy], p.PURPLE)
    _bands(ig, ax)
    _foot(ctx, ax, "Customs goods divided by national-accounts goods and services")
    _finish(ctx, ig)


def plate_markets(ctx, ig):
    p = ctx.p
    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    y, v = _yr(ctx, "policy_rate_ecb", "dfr")
    iy, iv = _yr(ctx, "ipc_ine", "ipc_avg_rate")
    ctx.line(ax, y, v, p.NAVY, label="ECB deposit facility")
    ctx.line(ax, iy, iv, p.RED, label="INE CPI")
    _bands(ig, ax, True)
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)

    ax = ig.slot("markets.bond_10y", "10-year government bond yield (%)")
    y, v = _yr(ctx, "yield_10y_bpstat", "yield_pt_avg")
    ctx.line(ax, y, v, p.RED)
    _bands(ig, ax)

    ax = ig.slot("markets.currency", "Euro against US$ (index 2006 = 100, up = stronger)")
    y, v = _yr(ctx, "eurusd_ecb", "avg")
    base = v[0]
    ctx.line(ax, y, [n / base * 100 for n in v], p.BLUE)
    _bands(ig, ax)

    ax = ig.slot("markets.equities", "Main equity index in US$ (index 2006 = 100)")
    ctx.pending(ax)
    _foot(ctx, ax, "the reviewed Yahoo Finance history begins in 2013; a "
          "2013-base index is not overlaid on the canonical 2006-base slot")
    _finish(ctx, ig)


def plate_credit(ctx, ig):
    p = ctx.p
    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    y, h = _yr(ctx, "household_debt_bpstat", "housing_pct_gdp")
    _, c = _yr(ctx, "household_debt_bpstat", "consumption_other_pct_gdp")
    ctx.line(ax, y, [a + b for a, b in zip(h, c)], p.RED)
    _bands(ig, ax, True)

    ax = ig.slot("credit.lending_rate", "Mortgage lending rate (%)")
    y, v = _yr(ctx, "mortgage_rate_bpstat", "mortgage_new_avg")
    ctx.line(ax, y, v, p.NAVY)
    _bands(ig, ax)

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    y, v = _yr(ctx, "npl_bpstat", "npl_ratio")
    ctx.line(ax, y, v, p.RED)
    _bands(ig, ax)

    ax = ig.slot("credit.lens", "Housing debt (% of GDP)")
    y, v = _yr(ctx, "household_debt_bpstat", "housing_pct_gdp")
    ctx.line(ax, y, v, p.BRONZE)
    _bands(ig, ax)
    _finish(ctx, ig)


def plate_people(ctx, ig):
    p = ctx.p
    ax = ig.slot("people.gini", "Gini coefficient (0–100)")
    y, v = _yr(ctx, "gini_estat", "silc")
    ctx.line(ax, y, v, p.RED, label="Eurostat, survey year")
    wy, wv = _yr(ctx, "gini_wb", "gini")
    ctx.line(ax, wy, wv, p.NAVY, ls="--", label="World Bank")
    _bands(ig, ax, True)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)

    ax = ig.slot("people.poverty", "At risk of poverty (% of people)")
    y, v = _yr(ctx, "poverty_estat", "arop60")
    ctx.line(ax, y, v, p.RED)
    _bands(ig, ax)
    _foot(ctx, ax, "EU-SILC, below 60% of national median income")

    ax = ig.slot("people.minimum_wage",
                 "Minimum wage (US$ per month, 12-month basis)")
    wages = _d(ctx, "minimum_wage_estat", "eur_month_jul")
    fx = _d(ctx, "eurusd_ecb", "avg")
    years = [year for year in sorted(wages) if year in fx]
    values = [wages[year] * fx[year] for year in years]
    ctx.line(ax, years, values, p.RED)
    ctx.endlabel(ax, years, values, p.RED, lambda n: f"US${n:,.0f}", dy=8)
    _bands(ig, ax)
    _foot(ctx, ax, "Eurostat earn_mw_cur; 12-month basis, converted at the "
          "ECB annual-average US$/EUR rate")

    ax = ig.slot("people.lens", "Tax burden (% of GDP)")
    y, v = _yr(ctx, "tax_burden_estat", "estat")
    ctx.line(ax, y, v, p.VERDE)
    _bands(ig, ax)
    _finish(ctx, ig)


def plate_world(ctx, ig):
    p = ctx.p
    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    y, v = _yr(ctx, "gdp_usd_wb", "gdp_usd")
    v = [n / 1e9 for n in v]
    ctx.line(ax, y, v, p.VERDE)
    _bands(ig, ax, True)

    ax = ig.slot("world.hdi", "Human Development Index (0–1)")
    y, v = _yr(ctx, "hdi_undp", "hdi")
    ctx.line(ax, y, v, p.BLUE)
    _bands(ig, ax)

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (0–100)")
    y, v = _yr(ctx, "cpi_ti", "score")
    ctx.line(ax, y, v, p.PURPLE)
    ctx.endlabel(ax, y, v, p.PURPLE, lambda n: f"{n:.0f}", dy=8)
    _foot(ctx, ax, "Transparency International CPI 2025 workbook; comparable "
          "2012 method onward")

    ax = ig.slot("world.reserves", "International reserves (US$ bn)")
    y, v = _yr(ctx, "reserves_wb", "reserves_usd")
    ctx.line(ax, y, [n / 1e9 for n in v], p.BRONZE)
    _bands(ig, ax)
    _finish(ctx, ig)


def plate_demography(ctx, ig):
    p = ctx.p
    pop = _pop(ctx)
    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    y = sorted(pop)
    base = pop[y[0]]
    ctx.line(ax, y, [pop[n] / base * 100 for n in y], p.VERDE)
    _bands(ig, ax, True)

    ax = ig.slot("demography.fertility", "Total fertility rate (children per woman)")
    y, v = _yr(ctx, "demography_ine", "tfr")
    ctx.line(ax, y, v, p.PURPLE)
    _bands(ig, ax)

    ax = ig.slot("demography.birth_death", "Births and deaths (per 1,000 people)")
    births = _d(ctx, "demography_ine", "births_nuts2024")
    deaths = _d(ctx, "demography_ine", "deaths_nuts2013")
    by, bv = ctx.per_1000(births, pop)
    dy, dv = ctx.per_1000(deaths, pop)
    ctx.line(ax, by, bv, p.VERDE, label="Births")
    ctx.line(ax, dy, dv, p.RED, label="Deaths")
    _bands(ig, ax)
    ax.legend(loc="upper right", fontsize=7.4, frameon=False)

    ax = ig.slot("demography.natural_migration", "Natural increase and net migration (per 1,000 people)")
    natural = {y: births[y] - deaths[y] for y in births if y in deaths}
    ny, nv = ctx.per_1000(natural, pop)
    ctx.bars(ax, ny, nv, lambda n: p.VERDE if n >= 0 else p.RED)
    net = _d(ctx, "net_migration_ine", "net_nuts2024")
    my, mv = ctx.per_1000(net, pop)
    ctx.line(ax, my, mv, p.NAVY, label="INE published net migration")
    _bands(ig, ax)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    _finish(ctx, ig)


def plate_security(ctx, ig):
    p = ctx.p
    pop = _pop(ctx)
    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    police = _d(ctx, "homicide_estat", "police_recorded")
    cert = _cause(ctx, "64")
    py, pv = ctx.per_100k(police, pop)
    cy, cv = ctx.per_100k(cert, pop)
    ctx.line(ax, py, pv, p.NAVY, label="Police-recorded offences")
    ctx.line(ax, cy, cv, p.RED, label="Death certificates")
    _bands(ig, ax, True)
    ax.legend(loc="upper right", fontsize=7.0, frameon=False)

    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    y, v = ctx.per_100k(_cause(ctx, "63"), pop)
    ctx.line(ax, y, v, p.PURPLE)
    _bands(ig, ax)

    ax = ig.slot("security.road_deaths", "Road deaths (per 100,000)")
    y, v = ctx.per_100k(_cause(ctx, "60"), pop)
    ctx.line(ax, y, v, p.BRONZE)
    _bands(ig, ax)

    ax = ig.slot("security.lens", "Recorded crime rate (per 1,000 people)")
    y, v = _yr(ctx, "crime_ine", "total_nuts2024")
    ctx.line(ax, y, v, p.VERDE)
    _bands(ig, ax)
    _finish(ctx, ig)


def plate_mortality(ctx, ig):
    p = ctx.p
    pop = _pop(ctx)
    deaths = _d(ctx, "demography_estat", "deaths")
    ax = ig.slot("mortality.death_rate", "Crude death rate (per 1,000 people)")
    y, v = ctx.per_1000(deaths, pop)
    ctx.line(ax, y, v, p.RED)
    _bands(ig, ax, True)

    ax = ig.slot("mortality.excess_deaths", "Excess deaths (% above 2015–2019 average)")
    base = sum(deaths[y] for y in range(2015, 2020)) / 5
    yy = [y for y in sorted(deaths) if y >= 2015]
    vv = [(deaths[y] / base - 1) * 100 for y in yy]
    ctx.bars(ax, yy, vv, lambda n: p.RED if n > 0 else p.VERDE)
    _bands(ig, ax)

    ax = ig.slot("mortality.covid", "COVID-19 deaths (per 100,000)")
    ctx.pending(ax)
    _foot(ctx, ax, "Exact U07.1/U07.2 series not staged — pending")

    ax = ig.slot("mortality.lens", "Neoplasms and circulatory deaths (per 100,000)")
    for code, label, color in [("06", "Neoplasms", p.RED),
                               ("33", "Circulatory diseases", p.NAVY)]:
        y, v = ctx.per_100k(_cause(ctx, code), pop)
        ctx.line(ax, y, v, color, label=label)
    _bands(ig, ax)
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    _finish(ctx, ig)


def plate_migration(ctx, ig):
    p = ctx.p
    pop = _pop(ctx)
    imm = _d(ctx, "immigration_ine", "immigrants")
    emi = _d(ctx, "emigration_ine", "emigrants")
    ax = ig.slot("migration.flows", "Immigration and emigration (per 1,000 people)")
    iy, iv = ctx.per_1000(imm, pop)
    ey, ev = ctx.per_1000(emi, pop)
    ctx.line(ax, iy, iv, p.VERDE, label="INE immigration")
    ctx.line(ax, ey, ev, p.RED, label="INE emigration")
    _bands(ig, ax, True)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    _foot(ctx, ax, "INE method break from 2021; the line is not comparable across the seam")

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    net = _d(ctx, "net_migration_ine", "net_nuts2024")
    y, v = ctx.per_1000(net, pop)
    ctx.bars(ax, y, v, lambda n: p.VERDE if n >= 0 else p.RED)
    _bands(ig, ax)
    _foot(ctx, ax, "INE published balance, including statistical adjustment")

    ax = ig.slot("migration.foreign_born", "Foreign-born and foreign-citizen share (%)")
    stock = ctx.table("published/stock_estat.csv")
    sy, born, citizen = [], [], []
    for year, bt, bn, ct, cn in zip(
            stock["year"], stock["by_birth_total"],
            stock["by_birth_national"], stock["by_citizenship_total"],
            stock["by_citizenship_national"]):
        if all(x == x for x in (bt, bn, ct, cn)):
            sy.append(int(year))
            born.append((bt - bn) / bt * 100)
            citizen.append((ct - cn) / ct * 100)
    ctx.line(ax, sy, born, p.NAVY, label="Foreign-born")
    ctx.line(ax, sy, citizen, p.BRONZE, label="Foreign citizen")
    _bands(ig, ax)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)

    ax = ig.slot("migration.lens", "First residence permits (thousands)")
    y, v = _yr(ctx, "permits_estat", "first_permits")
    ctx.line(ax, y, [n / 1000 for n in v], p.PURPLE)
    _bands(ig, ax)
    _foot(ctx, ax, "Administrative events, not arrivals; 2025 backlog clearance")
    _finish(ctx, ig)


PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="The Economy — Growth, Prices and Work", subtitle="Current national accounts beside the national and harmonised price and labour series.", source="Sources: Eurostat · INE · World Bank", alt="Four panels on Portugal's economy: real growth, GDP per person, inflation and unemployment."),
    dict(id="02", slug="fiscal", topic="fiscal", builder=plate_fiscal,
         title="Public Finances — Revenue, Balance, Debt and Interest", subtitle="General-government national accounts on one perimeter.", source="Source: Eurostat government finance statistics", alt="Four panels on Portugal's general-government revenue, expenditure, balances, debt and interest."),
    dict(id="03", slug="spending", topic="spending", builder=plate_spending,
         title="Public Spending — Functions and Investment", subtitle="COFOG functions and investment, all as shares of GDP.", source="Source: Eurostat government finance statistics", alt="Four panels on Portuguese spending by function, social protection, investment and public investment."),
    dict(id="04", slug="trade", topic="trade", builder=plate_trade,
         title="Trade — Openness, Partners and the Services Economy", subtitle="National-accounts trade beside customs goods, kept as distinct definitions.", source="Sources: Eurostat national accounts · INE international trade", alt="Four panels on Portuguese exports, imports, the trade balance, goods destinations and the goods share of exports."),
    dict(id="05", slug="markets", topic="markets", builder=plate_markets,
         title="Markets — Frankfurt's Rate, Portuguese Yields and the PSI", subtitle="The ECB rate, Portuguese benchmark yield and euro; the 2006-base equity slot remains pending.", source="Sources: ECB · Banco de Portugal · INE · Yahoo Finance", alt="Four panels on Portuguese markets. Interest rates, the euro and yields are drawn; the comparable 2006-base equity index remains pending because the reviewed PSI history begins in 2013."),
    dict(id="06", slug="credit", topic="credit", builder=plate_credit,
         title="Credit — Household Deleveraging and Bank Repair", subtitle="Household debt, mortgage pricing and non-performing loans.", source="Source: Banco de Portugal BPstat", alt="Four panels on household debt, mortgage rates, non-performing loans and housing debt."),
    dict(id="07", slug="people", topic="people", builder=plate_people,
         title="People — Inequality, Poverty and the Tax Burden", subtitle="EU-SILC measures, with their year convention kept explicit.", source="Sources: Eurostat EU-SILC · World Bank · Eurostat earn_mw_cur · ECB", alt="Four panels on inequality, relative poverty, Portugal's twelve-month-equivalent statutory minimum wage in US dollars, and the tax burden."),
    dict(id="08", slug="world", topic="world", builder=plate_world,
         title="Portugal in the World — Size, Development and Reserves", subtitle="Comparable international measures from one vintage each.", source="Sources: World Bank · UNDP · Transparency International", alt="Four panels on GDP, human development, Transparency International's comparable 2012–2025 corruption index, and international reserves."),
    dict(id="09", slug="demography", topic="demography", builder=plate_demography,
         title="Demography — A Revised Population and Migration-Led Growth", subtitle="The 2026 population revision is kept on the same denominator as the rates.", source="Sources: INE · Eurostat", alt="Four panels on population, fertility, births and deaths, and natural increase beside net migration."),
    dict(id="10", slug="security", topic="security", builder=plate_security,
         title="Security — Police Records and Death Certificates", subtitle="Different systems remain different lines, converted on the revised population.", source="Sources: Eurostat · INE/DGPJ", alt="Four panels on homicide, suicide, road deaths and recorded crime rates."),
    dict(id="11", slug="mortality", topic="mortality", builder=plate_mortality,
         title="Mortality — The Pandemic and the Two Largest Causes", subtitle="Registered deaths and a fixed pre-pandemic baseline.", source="Sources: INE · Eurostat", alt="Four panels on crude mortality, excess deaths, pending exact COVID deaths and major certified causes."),
    dict(id="12", slug="migration", topic="migration", builder=plate_migration,
         title="Migration — Revised Flows, Stocks and Paperwork", subtitle="The 2021 methodology seam is marked and administrative events are not called arrivals.", source="Sources: INE · Eurostat migration suite", alt="Four panels on migration flows, the published net balance, foreign-born and foreign-citizen stocks, and first permits."),
)
