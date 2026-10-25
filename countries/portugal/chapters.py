"""Portugal's page cards, computed from the reviewed publication CSVs."""
MONEY, WORLD, PEOPLE = "money", "world", "people"


def _c(ctx, name, col):
    return ctx.col(f"published/{name}.csv", col)


def headline(ctx):
    return [
        ctx.stat({"en": "GDP", "pt": "PIB"}, _c(ctx, "gdp_estat", "nominal_eurbn"), "money_bn"),
        ctx.stat({"en": "GDP per person, US$", "pt": "PIB por pessoa, US$"},
                 _c(ctx, "gdp_pc_wb", "gdp_per_person_usd"), "count"),
        ctx.stat({"en": "Population", "pt": "População"},
                 [(y, v / 1e6) for y, v in _c(ctx, "demography_ine", "population")], "pop_mn", kind="level"),
        ctx.stat({"en": "Unemployment", "pt": "Desemprego"}, _c(ctx, "unemployment_ine", "rate_serie2021"), "pct"),
        ctx.stat({"en": "Public debt", "pt": "Dívida pública"}, _c(ctx, "debt_estat", "gross_pct_gdp"), "pct_gdp", kind="level"),
        ctx.stat({"en": "Net migration", "pt": "Saldo migratório"}, _c(ctx, "net_migration_ine", "net_nuts2024"), "count"),
        ctx.stat({"en": "Policy rate", "pt": "Taxa diretora"}, _c(ctx, "policy_rate_ecb", "dfr"), "pct2", kind="level"),
    ]


def build(ctx):
    specs = [
        ("01-economy", "economy", MONEY, "The Economy", "A economia", "Growth, prices and work on the current national-accounts vintage.", "Crescimento, preços e emprego na edição atual das contas nacionais.", "gdp_estat", "real_growth", "pct_s"),
        ("02-fiscal", "fiscal", MONEY, "Public Finances", "Finanças públicas", "Revenue, balances, debt and interest on the general-government perimeter.", "Receita, saldos, dívida e juros no perímetro das administrações públicas.", "deficit_estat", "deficit", "pct_gdp_s"),
        ("03-spending", "spending", MONEY, "Public Spending", "Despesa pública", "Functions and investment as shares of the economy.", "Funções e investimento em percentagem da economia.", "spending_by_function_estat", "social_protection", "pct_gdp"),
        ("04-trade", "trade", WORLD, "Trade", "Comércio", "National-accounts trade beside customs goods, never spliced.", "Comércio das contas nacionais ao lado dos bens aduaneiros, sem os unir.", "trade_estat", "exports_eurbn", "money_bn"),
        ("05-markets", "markets", MONEY, "Money & Markets", "Moeda e mercados", "The ECB rate, Portuguese yield, euro and PSI.", "A taxa do BCE, a rendibilidade portuguesa, o euro e o PSI.", "policy_rate_ecb", "dfr", "pct2"),
        ("06-credit", "credit", MONEY, "Household Credit", "Crédito às famílias", "Deleveraging, mortgage pricing and bank repair.", "Desalavancagem, preço do crédito à habitação e recuperação bancária.", "household_debt_bpstat", "housing_pct_gdp", "pct_gdp"),
        ("07-people", "people", PEOPLE, "People", "Pessoas", "Inequality and relative poverty on an explicit survey-year convention.", "Desigualdade e pobreza relativa numa convenção explícita do ano do inquérito.", "poverty_estat", "arop60", "pct"),
        ("08-world", "world", WORLD, "Portugal in the World", "Portugal no mundo", "Comparable international measures from one vintage each.", "Medidas internacionais comparáveis, cada uma numa única edição.", "hdi_undp", "hdi", "dec3"),
        ("09-demography", "demography", PEOPLE, "Demography", "Demografia", "A revised population and migration-led growth.", "Uma população revista e crescimento assente na migração.", "demography_ine", "population", "count"),
        ("10-security", "security", PEOPLE, "Security", "Segurança", "Police records and death certificates remain separate systems.", "Os registos policiais e os certificados de óbito permanecem sistemas distintos.", "crime_ine", "total_nuts2024", "pct"),
        ("11-mortality", "mortality", PEOPLE, "Mortality", "Mortalidade", "Registered deaths against a fixed pre-pandemic baseline.", "Óbitos registados face a uma base fixa anterior à pandemia.", "demography_estat", "deaths", "count"),
        ("12-migration", "migration", PEOPLE, "Migration", "Migração", "Revised flows, stocks and administrative paperwork with the seams visible.", "Fluxos revistos, populações e atos administrativos com as ruturas visíveis.", "net_migration_ine", "net_nuts2024", "count"),
    ]
    out = []
    for ident, topic, family, en, pt, ben, bpt, file, col, fmt in specs:
        pairs = _c(ctx, file, col)
        out.append({
            "id": ident, "topic": topic, "n": ident[:2], "family": family,
            "title": ctx.text(en=en, pt=pt), "blurb": ctx.text(en=ben, pt=bpt),
            "spark": pairs, "stats": [ctx.stat({"en": en, "pt": pt}, pairs, fmt)],
            "alt": {"en": ben, "pt": bpt},
        })
    return out
