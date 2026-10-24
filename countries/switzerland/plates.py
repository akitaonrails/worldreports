"""Switzerland's twelve data plates on the shared comparison spine."""
from __future__ import annotations

from collections import defaultdict

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


def _yr_where(ctx, rel, col, field, value, since=W0):
    """Return an annual series for one explicit published perimeter."""
    out = sorted((int(row["year"]), float(row[col]))
                 for row in _rows(ctx, rel)
                 if int(row["year"]) >= since and row.get(field) == value
                 and row.get(col) == row.get(col))
    return [year for year, _ in out], [number for _, number in out]


def _annual_monthly(ctx, rel, col, how="mean"):
    grouped = defaultdict(list)
    for row in _rows(ctx, rel):
        value = row.get(col)
        if value != value:
            continue
        grouped[int(str(row["month"])[:4])].append((str(row["month"]), value))
    out = []
    for year, values in sorted(grouped.items()):
        if year < W0:
            continue
        values.sort()
        value = (values[-1][1] if how == "last"
                 else sum(v for _, v in values) / len(values))
        out.append((year, value))
    return [y for y, _ in out], [v for _, v in out]


def _at(years, values, year):
    return dict(zip(years, values))[year]


def _pop(ctx):
    rows = ctx.rows("demography/balance_bfs.csv") or {}
    return {y: (float(r["pop_1jan"]) + float(r["pop_31dec"])) / 2
            for y, r in rows.items() if y >= W0}


def _cause(ctx, name):
    out = {}
    for row in _rows(ctx, "mortality/causes_of_death_bfs.csv"):
        if (int(row["year"]) >= W0 and row["cause"] == name
                and row["deaths_total"] == row["deaths_total"]):
            out[int(row["year"])] = float(row["deaths_total"])
    return out


def _note(p, ax, text, x=0.02, y=0.96, ha="left", size=7.6):
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va="top",
            fontsize=size, style="italic", color=p.MUTED, zorder=7)


def _foot(p, ax, text):
    ax.text(0.5, -0.07, text, transform=ax.transAxes, ha="center",
            va="top", fontsize=7.0, color=p.FAINT, style="italic")


def _mark(ig, ax, key, dy=0.96):
    year, label = events.MARKS[key]
    ig.add_event(ax, year, label, dy=dy)


def _finish(ig):
    for ax in ig.axes_flat:
        if ax.get_visible():
            ig.style_axis(ax)


def plate_economy(ctx, ig):
    p = ctx.p
    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    y, v = _yr(ctx, "macro/gdp_bfs.csv", "gdp_real_growth_pct")
    ctx.bars(ax, y, v, lambda n: p.GREEN if n >= 0 else p.RED)
    ey, ev = _yr(ctx, "macro/gdp_estat.csv", "real_growth_pct")
    ctx.line(ax, ey, ev, p.BLUE, label="Eurostat, previous GDP vintage")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower right", fontsize=7.2, frameon=False)
    _foot(p, ax, "BFS current vintage; Eurostat diverges from 2023")

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    y, v = _yr(ctx, "international/gdp_pc_wb.csv", "gdp_per_person_usd")
    ctx.line(ax, y, v, p.RED)
    ctx.endlabel(ax, y, v, p.RED, lambda n: f"US${n:,.0f}", dy=8)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "World Bank NY.GDP.PCAP.CD")

    ax = ig.slot("economy.inflation", "Consumer price inflation (% per year)")
    y, v = _yr(ctx, "macro/cpi_bfs.csv", "cpi_inflation_pct")
    ctx.line(ax, y, v, p.RED, label="Swiss CPI (BFS)")
    hy, hv = _yr(ctx, "macro/hicp_estat.csv", "hicp_pct")
    ctx.line(ax, hy, hv, p.BLUE, ls="--", label="HICP (Eurostat)")
    ax.axhspan(0, 2, color=p.GREEN, alpha=0.08, zorder=0)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    _foot(p, ax, "SNB price stability: inflation below 2%")

    ax = ig.slot("economy.unemployment", "Unemployment (% of labour force)")
    y, v = _yr(ctx, "macro/unemployment_rate_bfs.csv", "ilo_rate_annual_pct")
    ctx.line(ax, y, v, p.SLATE, label="BFS ILO annual rate")
    ey, ev = _yr(ctx, "macro/unemployment_estat.csv", "ilo_rate_pct")
    ctx.line(ax, ey, ev, p.FAINT, ls="--", label="Eurostat LFS")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)
    _finish(ig)


def plate_fiscal(ctx, ig):
    p = ctx.p
    E = "fiscal/general_government_estat.csv"
    ax = ig.slot("fiscal.revenue_expenditure", "Revenue and expenditure (% of GDP)")
    y, r = _yr(ctx, E, "revenue_pct_gdp")
    _, x = _yr(ctx, E, "expenditure_pct_gdp")
    ctx.line(ax, y, r, p.GREEN, label="Revenue, Eurostat")
    ctx.line(ax, y, x, p.RED, label="Expenditure, Eurostat")
    ey, er = _yr_where(ctx, "fiscal/general_government_efv.csv",
                       "revenue_pct_gdp", "sector", "general_government")
    _, ex = _yr_where(ctx, "fiscal/general_government_efv.csv",
                      "expenditure_pct_gdp", "sector", "general_government")
    ctx.line(ax, ey, er, p.GREEN_D, ls="--", label="Revenue, EFV")
    ctx.line(ax, ey, ex, p.RED_D, ls="--", label="Expenditure, EFV")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=6.8, ncol=2, frameon=False)

    ax = ig.slot("fiscal.balance", "Overall and primary balance (% of GDP)")
    y, b = _yr(ctx, E, "balance_pct_gdp")
    _, interest = _yr(ctx, E, "interest_pct_gdp")
    ctx.bars(ax, y, b, lambda n: p.GREEN if n >= 0 else p.RED)
    ctx.line(ax, y, [a + i for a, i in zip(b, interest)], p.SLATE,
             label="Primary balance")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower right", fontsize=7.5, frameon=False)

    ax = ig.slot("fiscal.debt", "Gross debt (% of GDP)")
    y, d = _yr(ctx, "international/gg_debt_imf.csv", "gross_debt_pct_gdp")
    py, pv = _yr(ctx, "international/gg_debt_imf.csv", "gross_debt_pct_gdp_proj")
    ctx.line(ax, y + py, d + pv, p.RED, label="IMF total liabilities")
    my, mv = _yr_where(ctx, "fiscal/general_government_efv.csv",
                       "maastricht_debt_pct_gdp", "sector", "general_government")
    ctx.line(ax, my, mv, p.BLUE, ls="--", label="EFV Maastricht debt")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)

    ax = ig.slot("fiscal.interest", "Interest paid (% of GDP)")
    y, v = _yr(ctx, E, "interest_pct_gdp")
    ctx.line(ax, y, v, p.PURPLE)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "Eurostat D41PAY; calendar years")
    _finish(ig)


def plate_spending(ctx, ig):
    p = ctx.p
    S = "fiscal/spending_by_function_estat.csv"
    cols = [("Social protection", "social_protection", p.RED),
            ("Health", "health", p.TEAL), ("Education", "education", p.GOLD),
            ("General services", "general_services", p.PURPLE),
            ("Economic affairs", "economic_affairs", p.BLUE),
            ("Defence and order", "defence_order", p.SLATE),
            ("Other", "other", p.FAINT)]
    years, _ = _yr(ctx, S, "total")
    layers = [_yr(ctx, S, col)[1] for _, col, _ in cols]
    ax = ig.slot("spending.by_function", "Spending by function, stacked (% of GDP)")
    ax.stackplot(years, *layers, labels=[n for n, _, _ in cols],
                 colors=[c for _, _, c in cols], alpha=0.9, lw=0)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=6.7, ncol=3, frameon=False)

    ax = ig.slot("spending.social_protection", "Social protection vs everything else (% of GDP)")
    y, social = _yr(ctx, S, "social_protection")
    _, total = _yr(ctx, S, "total")
    ctx.line(ax, y, social, p.RED, label="Social protection")
    ctx.line(ax, y, [t - s for t, s in zip(total, social)], p.SLATE,
             label="Everything else")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.4, frameon=False)
    _foot(p, ax, "Compulsory health insurance and occupational pensions sit outside government")

    ax = ig.slot("spending.investment", "Investment rate, whole economy (% of GDP)")
    gy, gfcf = _yr(ctx, "macro/gdp_bfs.csv", "gfcf_chf_mn")
    _, gdp = _yr(ctx, "macro/gdp_bfs.csv", "gdp_nominal_chf_mn")
    ctx.line(ax, gy, [a / b * 100 for a, b in zip(gfcf, gdp)], p.GREEN)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "BFS GFCF divided by BFS GDP, one vintage")

    ax = ig.slot("spending.public_investment", "Public investment (% of GDP)")
    y, v = _yr(ctx, "fiscal/public_investment_estat.csv", "public_investment_pct_gdp")
    ctx.line(ax, y, v, p.BLUE)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "Eurostat general-government GFCF, P51G")
    _finish(ig)


def _partner_rows(ctx):
    return _rows(ctx, "trade/goods_by_partner_bazg.csv")


def plate_trade(ctx, ig):
    p = ctx.p
    G = "macro/gdp_bfs.csv"
    gy, gdp = _yr(ctx, G, "gdp_nominal_chf_mn")
    _, exports = _yr(ctx, G, "exports_chf_mn")
    _, imports = _yr(ctx, G, "imports_chf_mn")
    ax = ig.slot("trade.exports_imports", "Exports and imports (% of GDP)")
    ctx.line(ax, gy, [v / d * 100 for v, d in zip(exports, gdp)], p.GREEN, label="Exports")
    ctx.line(ax, gy, [v / d * 100 for v, d in zip(imports, gdp)], p.RED, label="Imports")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    _foot(p, ax, "BFS national accounts, including non-monetary gold")

    ax = ig.slot("trade.balance", "Trade balance (% of GDP)")
    vals = [(a - b) / d * 100 for a, b, d in zip(exports, imports, gdp)]
    ctx.bars(ax, gy, vals, lambda n: p.GREEN if n >= 0 else p.RED)
    ig.add_recessions(ax, label=False)

    rows = _partner_rows(ctx)
    totals = {int(r["year"]): float(r["exports_chf_mn"]) for r in rows
              if r["partner_code"] == "TOTAL1" and int(r["year"]) >= W0}
    partners = [("USA", "United States"), ("Germany", "Germany"),
                ("China", "China"), ("France", "France"),
                ("Italy", "Italy")]
    ax = ig.slot("trade.destinations", "Top export destinations (% of goods exports)")
    for i, (name, label) in enumerate(partners):
        pts = sorted((int(r["year"]), float(r["exports_chf_mn"]) / totals[int(r["year"])] * 100)
                     for r in rows if r["partner"] == name and int(r["year"]) in totals)
        if pts:
            ctx.line(ax, [x for x, _ in pts], [v for _, v in pts], p.cycle(i), label=label)
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper right", fontsize=7.0, ncol=2, frameon=False)
    _foot(p, ax, "BAZG Swiss–Liechtenstein customs area; Total 1 denominator")

    ax = ig.slot("trade.lens", "Lens — gold changes the trade total (CHF bn)")
    for code, label, color in (("TOTAL1", "Total 1, excl. gold etc.", p.SLATE),
                               ("TOTAL2", "Total 2, incl. gold", p.RED),
                               ("GOLD_SITC971", "Non-monetary gold", p.GOLD)):
        pts = sorted((int(r["year"]), float(r["exports_chf_mn"]) / 1000)
                     for r in rows if r["partner_code"] == code and int(r["year"]) >= W0)
        ctx.line(ax, [x for x, _ in pts], [v for _, v in pts], color, label=label)
    _mark(ig, ax, "gold_trade")
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    _finish(ig)


def plate_markets(ctx, ig):
    p = ctx.p
    ax = ig.slot("markets.policy_rate", "Policy rate vs inflation (%)")
    py, pv = _annual_monthly(ctx, "markets/policy_rate_snb.csv", "policy_rate", "last")
    ly, lo = _annual_monthly(ctx, "markets/policy_rate_snb.csv", "libor_target_lower", "last")
    _, hi = _annual_monthly(ctx, "markets/policy_rate_snb.csv", "libor_target_upper", "last")
    if ly:
        ax.fill_between(ly, lo, hi, color=p.BLUE, alpha=0.18, label="Libor target range")
    ctx.line(ax, py, pv, p.RED, label="SNB policy rate, year-end")
    iy, iv = _yr(ctx, "macro/cpi_bfs.csv", "cpi_inflation_pct")
    ctx.line(ax, iy, iv, p.FAINT, ls="--", label="CPI inflation")
    _mark(ig, ax, "policy_rate")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.0, frameon=False)

    ax = ig.slot("markets.bond_10y", "10-year government bond yield (%, annual average)")
    y, v = _annual_monthly(ctx, "markets/yields_snb.csv", "yield_10y")
    ctx.line(ax, y, v, p.PURPLE)
    ig.add_recessions(ax, label=False)

    ax = ig.slot("markets.currency", "Franc against the US$ (index 2006 = 100, up = stronger)")
    y, fx = _annual_monthly(ctx, "markets/fx_snb.csv", "usd_chf_avg")
    iy, iv = ctx.index_2006({a: 1 / b for a, b in zip(y, fx)})
    ctx.line(ax, iy, iv, p.RED)
    _mark(ig, ax, "franc_floor", dy=0.98)
    _mark(ig, ax, "franc_unpeg", dy=0.78)
    ig.add_recessions(ax, label=False)

    ax = ig.slot("markets.equities", "SMI in US$ (index 2006 = 100)")
    sy, sv = _yr(ctx, "markets/smi_yahoo.csv", "close")
    eoy_y, eoy_fx = _annual_monthly(ctx, "markets/fx_snb.csv", "usd_chf_eom", "last")
    eoy = dict(zip(eoy_y, eoy_fx))
    series = {y: v / eoy[y] for y, v in zip(sy, sv) if y in eoy}
    y, v = ctx.index_2006(series)
    ctx.line(ax, y, v, p.RED, label="SMI, year-end in US$")
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "Yahoo SMI close (not official) × SNB year-end USD/CHF")
    _finish(ig)


def plate_credit(ctx, ig):
    p = ctx.p
    ax = ig.slot("credit.household_debt", "Household debt (% of GDP)")
    y, v = _yr(ctx, "credit/household_credit_bis.csv", "household_credit_pct_gdp_q4")
    ctx.line(ax, y, v, p.RED, label="BIS, Q4")
    ey, ev = _yr(ctx, "credit/household_debt_estat.csv", "loans_pct_gdp")
    ctx.line(ax, ey, ev, p.BLUE, ls="--", label="Eurostat financial accounts")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="lower left", fontsize=7.2, frameon=False)

    ax = ig.slot("credit.lending_rate", "Mortgage rate vs policy rate (%)")
    my, mv = _annual_monthly(ctx, "markets/mortgage_rates_snb.csv", "new_fixed_mortgage")
    py, pv = _annual_monthly(ctx, "markets/policy_rate_snb.csv", "policy_rate", "last")
    ctx.line(ax, my, mv, p.BLUE, label="New fixed mortgage, annual average")
    ctx.line(ax, py, pv, p.RED, label="SNB policy rate, year-end")
    ig.add_recessions(ax, label=False)
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)

    ax = ig.slot("credit.npl", "Non-performing loans (% of loans)")
    y, v = _yr(ctx, "credit/npl_wb.csv", "npl_pct")
    ctx.line(ax, y, v, p.PURPLE)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "IMF FSI via World Bank; all bank loans")

    ax = ig.slot("credit.lens", "Lens — payment arrears (% of people)")
    y, any_arrears = _yr(ctx, "social/arrears_bfs.csv", "any_kind_pct")
    _, housing = _yr(ctx, "social/arrears_bfs.csv", "rent_or_mortgage_pct")
    ctx.line(ax, y, any_arrears, p.RED, label="Any payment arrears")
    ctx.line(ax, y, housing, p.BLUE, label="Rent or mortgage arrears")
    ax.legend(loc="center right", fontsize=7.3, frameon=False)
    _foot(p, ax, "BFS SILC survey; people, not delinquent loans")
    _finish(ig)


def plate_people(ctx, ig):
    p = ctx.p
    ax = ig.slot("people.gini", "Income inequality, Gini (0–100)")
    y, v = _yr(ctx, "social/gini_estat.csv", "gini")
    ctx.line(ax, y, v, p.RED, label="Eurostat disposable income")
    by, bv = _yr(ctx, "social/gini_bfs.csv", "gini_disposable")
    ctx.line(ax, by, [x * 100 for x in bv], p.BLUE, ls="--", label="BFS HABE")
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    ig.add_recessions(ax, label=False)

    ax = ig.slot("people.poverty", "Poverty rate (% of people)")
    y, v = _yr(ctx, "social/poverty_bfs.csv", "poverty_rate_pct")
    ctx.line(ax, y, v, p.RED, label="BFS national poverty line")
    ey, ev = _yr(ctx, "social/poverty_estat.csv", "arop60_pct")
    ctx.line(ax, ey, ev, p.BLUE, label="At risk, below 60% median")
    wy, wv = _yr(ctx, "social/poverty_wb.csv", "poverty_8_30_pct")
    ctx.line(ax, wy, wv, p.FAINT, ls="--", label="US$8.30/day, 2021 PPP")
    ax.legend(loc="upper left", fontsize=6.9, frameon=False)
    ig.add_recessions(ax, label=False)

    ax = ig.slot("people.minimum_wage", "Minimum wage (US$ per month)")
    ctx.pending(ax)
    _foot(p, ax, "No statutory national minimum wage; several cantons set their own")

    ax = ig.slot("people.lens", "Lens — real wages and redistribution")
    rows = [r for r in _rows(ctx, "macro/wages_bfs.csv")
            if r["real_pct"] == r["real_pct"]]
    rows.sort(key=lambda r: int(r["year"]))
    ctx.bars(ax, [int(r["year"]) for r in rows], [float(r["real_pct"]) for r in rows],
             lambda n: p.GREEN if n >= 0 else p.RED)
    _foot(p, ax, "BFS real wage change; changing published index bases are not spliced")
    _finish(ig)


def plate_world(ctx, ig):
    p = ctx.p
    ax = ig.slot("world.gdp", "GDP at current prices (US$ bn)")
    y, v = _yr(ctx, "international/gdp_usd_wb.csv", "gdp_usd")
    ctx.line(ax, y, [n / 1e9 for n in v], p.RED)
    ig.add_recessions(ax, label=False)

    ax = ig.slot("world.hdi", "Human Development Index (HDI, 0–1)")
    y, v = _yr(ctx, "international/hdi_undp.csv", "hdi")
    ctx.line(ax, y, v, p.BLUE)
    ig.add_recessions(ax, label=False)

    ax = ig.slot("world.cpi", "Corruption Perceptions Index (score, 0–100)")
    y, v = _yr(ctx, "international/cpi.csv", "score")
    ctx.line(ax, y, v, p.PURPLE)
    _foot(p, ax, "Transparency International; methodology seam at 2012")

    ax = ig.slot("world.reserves", "Official reserves (US$ bn)")
    y, v = _annual_monthly(ctx, "international/reserves_snb.csv", "reserves_usd_mn", "last")
    ctx.line(ax, y, [n / 1000 for n in v], p.RED, label="SNB, December")
    wy, wv = _yr(ctx, "international/reserves_wb.csv", "reserves_usd")
    ctx.line(ax, wy, [n / 1e9 for n in wv], p.FAINT, ls="--", label="World Bank / IMF IFS")
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    ig.add_recessions(ax, label=False)
    _finish(ig)


def plate_demography(ctx, ig):
    p = ctx.p
    pop = _pop(ctx)
    ax = ig.slot("demography.population", "Population (index 2006 = 100)")
    y, v = ctx.index_2006(pop)
    ctx.line(ax, y, v, p.RED)
    ig.add_recessions(ax, label=False)

    ax = ig.slot("demography.fertility", "Total fertility rate (children per woman)")
    y, v = _yr(ctx, "demography/fertility_bfs.csv", "tfr")
    ctx.line(ax, y, v, p.PURPLE)
    ax.axhline(2.1, color=p.FAINT, ls=":", lw=1)
    ig.add_recessions(ax, label=False)

    rows = ctx.rows("demography/balance_bfs.csv") or {}
    births = {y: float(r["births"]) for y, r in rows.items() if y >= W0}
    deaths = {y: float(r["deaths"]) for y, r in rows.items() if y >= W0}
    ax = ig.slot("demography.birth_death", "Births and deaths (per 1,000 people)")
    by, bv = ctx.per_1000(births, pop)
    dy, dv = ctx.per_1000(deaths, pop)
    ctx.line(ax, by, bv, p.GREEN, label="Births")
    ctx.line(ax, dy, dv, p.RED, label="Deaths")
    ax.legend(loc="upper right", fontsize=7.5, frameon=False)
    ig.add_recessions(ax, label=False)

    natural = {y: births[y] - deaths[y] for y in births if y in deaths}
    net = {y: float(r["net_migration_incl_type_change"]) for y, r in rows.items() if y >= W0}
    ax = ig.slot("demography.natural_migration", "Natural increase and net migration (per 1,000 people)")
    y, v = ctx.per_1000(natural, pop)
    ctx.bars(ax, y, v, lambda n: p.GREEN if n >= 0 else p.RED)
    y, v = ctx.per_1000(net, pop)
    ctx.line(ax, y, v, p.BLUE, label="Net migration, incl. type changes")
    ax.legend(loc="upper left", fontsize=7.2, frameon=False)
    ig.add_recessions(ax, label=False)
    _finish(ig)


def plate_security(ctx, ig):
    p = ctx.p
    pop = _pop(ctx)
    ax = ig.slot("security.homicide", "Homicide rate (per 100,000)")
    y, v = _yr(ctx, "security/homicide_police_bfs.csv", "homicide_completed_per_100k")
    ctx.line(ax, y, v, p.RED, label="BFS, police-recorded completed homicides")
    wy, wv = _yr(ctx, "security/homicide_wb.csv", "homicide_per_100k")
    ctx.line(ax, wy, wv, p.FAINT, ls="--", label="UNODC via World Bank")
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    ig.add_recessions(ax, label=False)

    suicide = _cause(ctx, "Suizid")
    ax = ig.slot("security.suicide", "Suicide rate (per 100,000)")
    y, v = ctx.per_100k(suicide, pop)
    ctx.line(ax, y, v, p.PURPLE)
    _mark(ig, ax, "suicide_coding")
    ig.add_recessions(ax, label=False)

    road = _cause(ctx, "Strassenverkehrsunfälle")
    ax = ig.slot("security.road_deaths", "Road traffic deaths (per 100,000)")
    y, v = ctx.per_100k(road, pop)
    ctx.line(ax, y, v, p.RED, label="BFS resident deaths")
    wy, wv = _yr(ctx, "security/road_deaths_wb.csv", "road_deaths_per_100k")
    ctx.line(ax, wy, wv, p.FAINT, ls="--", label="WHO via World Bank")
    ax.legend(loc="upper right", fontsize=7.2, frameon=False)
    ig.add_recessions(ax, label=False)

    ax = ig.slot("security.lens", "Lens — firearms and assisted suicide (deaths)")
    fy, fv = _yr(ctx, "security/firearm_deaths_bfs.csv", "firearm_deaths")
    _, fs = _yr(ctx, "security/firearm_deaths_bfs.csv", "firearm_suicides")
    ay, av = _yr(ctx, "mortality/assisted_suicide_bfs.csv", "assisted_suicides")
    ctx.line(ax, fy, fv, p.SLATE, label="All firearm deaths")
    ctx.line(ax, fy, fs, p.RED, label="Firearm suicides")
    ctx.line(ax, ay, av, p.GOLD, label="Assisted suicide")
    ax.legend(loc="upper left", fontsize=7.0, frameon=False)
    _finish(ig)


def plate_mortality(ctx, ig):
    p = ctx.p
    pop = _pop(ctx)
    all_deaths = _cause(ctx, "Alle Todesursachen")
    ax = ig.slot("mortality.death_rate", "Crude death rate (per 1,000 people)")
    y, v = ctx.per_1000(all_deaths, pop)
    ctx.line(ax, y, v, p.RED)
    ig.add_recessions(ax, label=False)

    base = sum(all_deaths[y] for y in range(2015, 2020)) / 5
    ax = ig.slot("mortality.excess_deaths", "Excess deaths (% above 2015–2019 average)")
    y = sorted(k for k in all_deaths if k >= 2015)
    v = [(all_deaths[k] / base - 1) * 100 for k in y]
    ctx.bars(ax, y, v, lambda n: p.RED if n > 0 else p.GREEN)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, f"Fixed 2015–2019 mean: {base:,.1f} deaths")

    covid = _cause(ctx, "COVID-19")
    ax = ig.slot("mortality.covid", "COVID-19 deaths, underlying cause (per 100,000)")
    y, v = ctx.per_100k(covid, pop)
    ctx.bars(ax, y, v, lambda n: p.RED)
    ig.add_recessions(ax, label=False)

    ax = ig.slot("mortality.lens", "Lens — cancers, dementia and assisted suicide (per 100,000)")
    for i, (cause, label) in enumerate((("Bösartige Tumoren", "Malignant tumours"),
                                        ("Demenz", "Dementia"))):
        y, v = ctx.per_100k(_cause(ctx, cause), pop)
        ctx.line(ax, y, v, p.cycle(i), label=label)
    ay, av = _yr(ctx, "mortality/assisted_suicide_bfs.csv", "assisted_suicides")
    y, v = ctx.per_100k(dict(zip(ay, av)), pop)
    ctx.line(ax, y, v, p.GOLD, label="Assisted suicide")
    ax.legend(loc="center right", fontsize=7.0, frameon=False)
    _finish(ig)


def plate_migration(ctx, ig):
    p = ctx.p
    pop = _pop(ctx)
    rows = ctx.rows("migration/flows_bfs.csv") or {}
    imm = {y: float(r["immigration_total"]) for y, r in rows.items() if y >= W0}
    emi = {y: float(r["emigration_total"]) for y, r in rows.items() if y >= W0}
    net = {y: float(r["net_total"]) for y, r in rows.items() if y >= W0}
    ax = ig.slot("migration.flows", "Immigration and emigration (per 1,000 people)")
    y, v = ctx.per_1000(imm, pop)
    ctx.line(ax, y, v, p.RED, label="Immigration incl. type changes")
    y, v = ctx.per_1000(emi, pop)
    ctx.line(ax, y, v, p.BLUE, label="Emigration")
    ax.legend(loc="upper left", fontsize=7.0, frameon=False)
    _mark(ig, ax, "s_status")
    ig.add_recessions(ax, label=False)

    ax = ig.slot("migration.net", "Net migration (per 1,000 people)")
    y, v = ctx.per_1000(net, pop)
    ctx.bars(ax, y, v, lambda n: p.GREEN if n >= 0 else p.RED)
    ig.add_recessions(ax, label=False)
    _foot(p, ax, "BFS immigration minus emigration, including population-type changes")

    stock = ctx.rows("migration/stock_estat.csv") or {}
    born = {y: (float(r["pop_bybirth_foreign_born"]) / float(r["pop_bybirth_total"]) * 100)
            for y, r in stock.items() if y >= W0 and r.get("pop_bybirth_foreign_born") not in (None, "")}
    foreign = {y: float(r["pop_foreign"]) / float(r["pop_total"]) * 100
               for y, r in stock.items() if y >= W0}
    ax = ig.slot("migration.foreign_born", "Foreign-born share of population (%)")
    ctx.line(ax, *zip(*sorted(born.items())), p.RED, label="Foreign-born")
    ctx.line(ax, *zip(*sorted(foreign.items())), p.BLUE, ls="--", label="Foreign citizens")
    ax.legend(loc="upper left", fontsize=7.3, frameon=False)
    ig.add_recessions(ax, label=False)

    ax = ig.slot("migration.lens", "Lens — asylum, S status and citizenship (thousands)")
    ay, av = _yr(ctx, "migration/asylum_estat.csv", "applicants")
    ctx.line(ax, ay, [n / 1000 for n in av], p.RED, label="Asylum applicants, flow")
    cy, cv = _yr(ctx, "migration/citizenship_estat.csv", "acquisitions")
    ctx.line(ax, cy, [n / 1000 for n in cv], p.GREEN, label="Citizenship acquisitions, flow")
    permit_rows = [r for r in _rows(ctx, "migration/stock_by_permit_bfs.csv")
                   if r["population_type"] == "permanent" and r["permit"] == "Schutzbedürftiger (S)"]
    if permit_rows:
        ctx.line(ax, [int(r["year"]) for r in permit_rows],
                 [float(r["persons"]) / 1000 for r in permit_rows], p.GOLD,
                 label="S permit holders, year-end stock")
    ax.legend(loc="upper left", fontsize=6.9, frameon=False)
    _finish(ig)


BUILDERS = (plate_economy, plate_fiscal, plate_spending, plate_trade,
            plate_markets, plate_credit, plate_people, plate_world,
            plate_demography, plate_security, plate_mortality, plate_migration)
TOPICS = ("economy", "fiscal", "spending", "trade", "markets", "credit",
          "people", "world", "demography", "security", "mortality", "migration")
TITLES = ("The Economy", "Public Finances", "Where the Money Goes", "Trade",
          "Money and Markets", "Credit", "People", "Switzerland in the World",
          "Demography", "Security", "Mortality", "Migration")

PLATES = tuple(
    dict(id=f"{i:02d}", slug=topic, topic=topic, builder=builder,
         title=title,
         subtitle="Official Swiss series and harmonised comparisons, with definitions kept separate.",
         source="Sources: BFS · SNB · EFV · BAZG · Eurostat · World Bank",
         alt=f"Four panels on Switzerland: {topic}, 2006–2026.")
    for i, (topic, builder, title) in enumerate(zip(TOPICS, BUILDERS, TITLES), 1)
)
