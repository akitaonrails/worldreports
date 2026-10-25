"""Singapore's twelve page cards, computed from the reviewed CSVs.

Editorial copy lives here, in the two languages Singapore publishes; every
figure on a card is read out of `countries/singapore/data` at build time, so
a card and its plate cannot disagree.

Two things the copy has to keep straight, because the plates do:

  * the population a rate is divided by — resident for every vital rate,
    everyone present for crime, suicide and GDP per person;
  * the year basis — the public finances of the budget are on 1 April to
    31 March and are labelled by the starting year, the general-government
    line is on calendar years, and the plates never mix them.

The cards state gaps as gaps. A card whose plate is half pending says which
half and why, in the same words as the panel and as ui.json.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


# --------------------------------------------------------------- headline
def headline(ctx) -> list[dict]:
    """The strip above the plates: GDP, GDP per person, population, then
    this country's own readings, in that order."""
    T = ctx.text
    return [
        ctx.stat(T(en="GDP", pt="PIB"),
                 [(y, v / 1e9) for y, v in
                  ctx.col("world/world.csv", "gdp_usd")], "usd_bn"),
        ctx.stat(T(en="GDP per person, US$", pt="PIB por pessoa, US$"),
                 ctx.col("world/world.csv", "gdp_per_person_usd"), "count"),
        ctx.stat(T(en="Population", pt="População"),
                 [(y, v / 1e6) for y, v in
                  ctx.col("demography/demography.csv", "population_total")],
                 "pop_mn", kind="level"),
        ctx.stat(T(en="Real GDP growth", pt="Crescimento real do PIB"),
                 ctx.col("macro/economy.csv", "real_growth_pct"), "pct_s"),
        ctx.stat(T(en="Inflation", pt="Inflação"),
                 ctx.col("macro/economy.csv", "inflation_pct"), "pct"),
        ctx.stat(T(en="Gross debt (general govt)", pt="Dívida bruta (governo geral)"),
                 ctx.col("fiscal/imf_general_government.csv", "debt_pct_gdp"),
                 "pct_gdp", kind="level"),
        ctx.stat(T(en="Reserves, US$ bn", pt="Reservas, US$ bi"),
                 [(y, v / 1e9) for y, v in
                  ctx.col("world/world.csv", "reserves_usd")],
                 "usd_bn", kind="level"),
    ]


# ------------------------------------------------------------------ cards
def build(ctx) -> list[dict]:
    T = ctx.text
    E = "macro/economy.csv"
    I = "fiscal/imf_general_government.csv"
    D = "demography/demography.csv"
    S = "security/security.csv"
    M = "mortality/mortality.csv"

    return [
        {
            "id": "01-economy", "topic": "economy", "n": "01",
            "family": MONEY,
            "title": T(en="The Economy", pt="A Economia"),
            "blurb": T(
                en="A small, open, managed economy: growth broke only in "
                   "2020, prices have not run above 7% in twenty years, and "
                   "the central bank works through the exchange rate.",
                pt="Uma economia pequena, aberta e administrada: o "
                   "crescimento só quebrou em 2020, os preços não passaram "
                   "de 7% em vinte anos, e o banco central atua pelo câmbio."),
            "spark": ctx.col(E, "real_growth_pct"),
            "stats": [
                ctx.stat(T(en="GDP per person, US$", pt="PIB por pessoa, US$"),
                         ctx.col("world/world.csv", "gdp_per_person_usd"),
                         "count"),
                ctx.stat(T(en="Real growth", pt="Crescimento real"),
                         ctx.col(E, "real_growth_pct"), "pct_s"),
                ctx.stat(T(en="CPI inflation", pt="Inflação (IPC)"),
                         ctx.col(E, "inflation_pct"), "pct"),
            ],
        },
        {
            "id": "02-fiscal", "topic": "fiscal", "n": "02", "family": MONEY,
            "title": T(en="Public Finances", pt="Finanças Públicas"),
            "blurb": T(
                en="The general government runs a surplus and carries gross "
                   "debt of 166% of GDP — issued to hold CPF liabilities "
                   "and build reserves, and published with no asset offset.",
                pt="O governo geral tem superávit e carrega dívida bruta de "
                   "166% do PIB — emitida para sustentar passivos do CPF e "
                   "formar reservas, publicada sem compensação de ativos."),
            "spark": ctx.col(I, "debt_pct_gdp"),
            "stats": [
                ctx.stat(T(en="Overall balance", pt="Saldo total"),
                         ctx.col(I, "balance_pct_gdp"), "pct_gdp_s"),
                ctx.stat(T(en="Gross debt (general govt)",
                           pt="Dívida bruta (governo geral)"),
                         ctx.col(I, "debt_pct_gdp"), "pct_gdp",
                         kind="level"),
                ctx.stat(T(en="Expenditure (general govt)",
                           pt="Despesa (governo geral)"),
                         ctx.col(I, "expenditure_pct_gdp"), "pct_gdp"),
            ],
        },
        {
            "id": "03-spending", "topic": "spending", "n": "03",
            "family": MONEY,
            "title": T(en="Spending", pt="Despesas"),
            "blurb": T(
                en="The whole-economy investment rate is comparable. The "
                   "functional split is not: Singapore is not an OECD "
                   "member and table 11 carries no COFOG for it.",
                pt="A taxa de investimento da economia é comparável. A "
                   "divisão por função não é: Singapura não é membro da "
                   "OCDE e a tabela 11 não traz COFOG para o país."),
            "spark": ctx.col("macro/economy.csv", "gfcf_pct_gdp_wb"),
            "stats": [
                ctx.stat(T(en="Investment rate, whole economy",
                           pt="Taxa de investimento da economia"),
                         ctx.col("macro/economy.csv", "gfcf_pct_gdp_wb"),
                         "pct_gdp"),
            ],
        },
        {
            "id": "04-trade", "topic": "trade", "n": "04", "family": WORLD,
            "title": T(en="Trade", pt="Comércio"),
            "blurb": T(
                en="A port that refines and re-exports: goods and services "
                   "exports run at 178% of GDP, imports at 142%, and the "
                   "balance is in surplus every year of the window.",
                pt="Um porto que refina e reexporta: as exportações de bens "
                   "e serviços somam 178% do PIB, as importações 142%, e o "
                   "saldo é superavitário em todos os anos do período."),
            "spark": ctx.col("trade/trade.csv", "balance_pct_gdp"),
            "stats": [
                ctx.stat(T(en="Exports, goods and services",
                           pt="Exportações, bens e serviços"),
                         ctx.col("trade/trade.csv", "exports_pct_gdp"),
                         "pct_gdp"),
                ctx.stat(T(en="Imports, goods and services",
                           pt="Importações, bens e serviços"),
                         ctx.col("trade/trade.csv", "imports_pct_gdp"),
                         "pct_gdp"),
                ctx.stat(T(en="Trade balance", pt="Saldo comercial"),
                         ctx.col("trade/trade.csv", "balance_pct_gdp"),
                         "pct_gdp_s"),
            ],
        },
        {
            "id": "05-markets", "topic": "markets", "n": "05",
            "family": MONEY,
            "title": T(en="Markets", pt="Mercados"),
            "blurb": T(
                en="There is no policy rate to plot: MAS sets the slope, "
                   "width and level of the Singapore dollar's trade-weighted "
                   "band. The bond yield and the currency are market series.",
                pt="Não há taxa básica a traçar: o MAS define a inclinação, "
                   "a largura e o nível da banda cambial ponderada pelo "
                   "comércio. O juro do título e o câmbio são séries de "
                   "mercado."),
            "spark": ctx.col("markets/markets.csv", "govt_bond_10y_pct"),
            "stats": [
                ctx.stat(T(en="10-year bond yield", pt="Juro do título de 10 anos"),
                         ctx.col("markets/markets.csv", "govt_bond_10y_pct"),
                         "pct2"),
                ctx.stat(T(en="S$ per US$", pt="S$ por US$"),
                         ctx.col("markets/markets.csv", "sgd_per_usd"),
                         "dec2"),
                ctx.stat(T(en="SORA overnight benchmark",
                           pt="SORA, referência de um dia"),
                         ctx.col("markets/markets.csv", "sora_pct"), "pct2",
                         kind="level"),
            ],
        },
        {
            "id": "06-credit", "topic": "credit", "n": "06",
            "family": MONEY,
            "title": T(en="Credit", pt="Crédito"),
            "blurb": T(
                en="Household debt is 52% of GDP on the national balance "
                   "sheet and 44% on the BIS aggregate, against net worth "
                   "of S$3.3 trillion. The MAS lending and NPL series are "
                   "blocked.",
                pt="A dívida das famílias é 52% do PIB no balanço nacional "
                   "e 44% no agregado do BIS, contra um patrimônio líquido "
                   "de S$ 3,3 trilhões. As séries de crédito e "
                   "inadimplência do MAS estão bloqueadas."),
            "spark": ctx.col("credit/household.csv", "liabilities_pct_gdp"),
            "stats": [
                ctx.stat(T(en="Household debt (national)",
                           pt="Dívida das famílias (nacional)"),
                         ctx.col("credit/household.csv",
                                 "liabilities_pct_gdp"), "pct_gdp",
                         kind="level"),
                ctx.stat(T(en="Household debt (BIS)",
                           pt="Dívida das famílias (BIS)"),
                         ctx.col("credit/household.csv",
                                 "credit_pct_gdp_bis"), "pct_gdp",
                         kind="level"),
                ctx.stat(T(en="Household net worth",
                           pt="Patrimônio líquido das famílias"),
                         [(y, v / 1e3) for y, v in
                          ctx.col("credit/household.csv",
                                  "net_worth_sgd_mn")],
                         "money_bn", kind="level"),
            ],
        },
        {
            "id": "07-people", "topic": "people", "n": "07",
            "family": PEOPLE,
            "title": T(en="People and Incomes", pt="Pessoas e Rendas"),
            "blurb": T(
                en="One survey prints six coefficients; the two drawn are "
                   "before and after taxes and transfers, on employment "
                   "income of resident employed households. Poverty and the "
                   "minimum wage have no national definition.",
                pt="Um só inquérito imprime seis coeficientes; os dois "
                   "traçados são antes e depois de impostos e "
                   "transferências, sobre a renda do trabalho de famílias "
                   "residentes ocupadas. Pobreza e salário mínimo não têm "
                   "definição nacional."),
            "spark": ctx.col("people/income.csv", "gini_after_taxes_transfers"),
            "stats": [
                ctx.stat(T(en="Gini after taxes and transfers",
                           pt="Gini após impostos e transferências"),
                         [(y, v * 100) for y, v in
                          ctx.col("people/income.csv",
                                  "gini_after_taxes_transfers")], "dec2"),
                ctx.stat(T(en="Gini before taxes and transfers",
                           pt="Gini antes de impostos e transferências"),
                         [(y, v * 100) for y, v in
                          ctx.col("people/income.csv",
                                  "gini_before_taxes_transfers")], "dec2"),
                ctx.stat(T(en="Median income per household member, S$",
                           pt="Renda mediana por membro da família, S$"),
                         ctx.col("people/income.csv",
                                 "median_income_per_member_sgd"), "count"),
            ],
        },
        {
            "id": "08-world", "topic": "world", "n": "08", "family": WORLD,
            "title": T(en="Singapore in the World", pt="Singapura no Mundo"),
            "blurb": T(
                en="A city of six million with the GDP of a mid-sized "
                   "country, a 2023 HDI of 0.946, and reserves that back a "
                   "managed currency. The corruption index is not "
                   "reachable.",
                pt="Uma cidade de seis milhões com o PIB de um país médio, "
                   "IDH de 0,946 em 2023, e reservas que sustentam uma "
                   "moeda administrada. O índice de corrupção não está "
                   "acessível."),
            "spark": ctx.col("world/world.csv", "gdp_usd"),
            "stats": [
                ctx.stat(T(en="GDP, US$ bn", pt="PIB, US$ bi"),
                         [(y, v / 1e9) for y, v in
                          ctx.col("world/world.csv", "gdp_usd")], "usd_bn"),
                ctx.stat(T(en="Human Development Index", pt="Índice de Desenvolvimento Humano"),
                         ctx.col("world/world.csv", "hdi"), "dec3"),
                ctx.stat(T(en="Official reserves, US$ bn",
                           pt="Reservas oficiais, US$ bi"),
                         [(y, v / 1e9) for y, v in
                          ctx.col("world/world.csv", "reserves_usd")],
                         "usd_bn", kind="level"),
            ],
        },
        {
            "id": "09-demography", "topic": "demography", "n": "09",
            "family": PEOPLE,
            "title": T(en="Demography", pt="Demografia"),
            "blurb": T(
                en="Citizens, residents and everyone present are three "
                   "populations, and the third grew twice as fast. Fertility "
                   "is 0.87 — the lowest in the atlas.",
                pt="Cidadãos, residentes e todos os presentes são três "
                   "populações, e a terceira cresceu duas vezes mais rápido. "
                   "A fecundidade é 0,87 — a mais baixa do atlas."),
            "spark": ctx.col(D, "tfr"),
            "stats": [
                ctx.stat(T(en="Total population", pt="População total"),
                         [(y, v / 1e6) for y, v in
                          ctx.col(D, "population_total")], "pop_mn",
                         kind="level"),
                ctx.stat(T(en="Residents", pt="Residentes"),
                         [(y, v / 1e6) for y, v in
                          ctx.col(D, "population_resident")], "pop_mn",
                         kind="level"),
                ctx.stat(T(en="Total fertility rate",
                           pt="Taxa de fecundidade total"),
                         ctx.col(D, "tfr"), "dec2"),
            ],
        },
        {
            "id": "10-security", "topic": "security", "n": "10",
            "family": PEOPLE,
            "title": T(en="Security", pt="Segurança"),
            "blurb": T(
                en="Murder is a Penal Code category and there were seven in "
                   "2025; the suicide line's 2025 fall is coroner's cases "
                   "still being assigned, not a decline.",
                pt="Homicídio é uma categoria do Código Penal e houve sete "
                   "em 2025; a queda de 2025 na linha de suicídios são "
                   "casos do legista ainda em atribuição, não um declínio."),
            "spark": ctx.col(S, "suicide_per_100k"),
            "stats": [
                ctx.stat(T(en="Suicide rate, preliminary year",
                           pt="Taxa de suicídio, ano preliminar"),
                         ctx.col(S, "suicide_per_100k"), "per100k",
                         kind="level"),
                ctx.stat(T(en="Road deaths", pt="Mortes no trânsito"),
                         ctx.col(S, "road_death_per_100k"), "per100k"),
                ctx.stat(T(en="Murder rate", pt="Taxa de homicídios"),
                         ctx.col(S, "murder_per_100k"), "per100k2",
                         kind="level"),
            ],
        },
        {
            "id": "11-mortality", "topic": "mortality", "n": "11",
            "family": PEOPLE,
            "title": T(en="Mortality", pt="Mortalidade"),
            "blurb": T(
                en="Deaths per resident rose with an ageing population, not "
                   "with a shock: the crude rate went from 4.4 to 6.0 per "
                   "1,000. Excess deaths over 2015–2019 peak at 30%.",
                pt="As mortes por residente subiram com o envelhecimento, "
                   "não com um choque: a taxa bruta foi de 4,4 para 6,0 por "
                   "1.000. O excesso sobre 2015–2019 chega a 30%."),
            "spark": ctx.col(M, "crude_death_rate_per_1000"),
            "stats": [
                ctx.stat(T(en="Crude death rate, per 1,000 residents",
                           pt="Taxa bruta de mortalidade, por 1.000 residentes"),
                         ctx.col(M, "crude_death_rate_per_1000"), "dec2"),
                ctx.stat(T(en="Deaths in the year", pt="Mortes no ano"),
                         ctx.col(M, "deaths_total_by_cause"), "count"),
                ctx.stat(T(en="Life expectancy", pt="Expectativa de vida"),
                         ctx.col(M, "life_expectancy"), "dec2", kind="level"),
            ],
        },
        {
            "id": "12-migration", "topic": "migration", "n": "12",
            "family": PEOPLE,
            "title": T(en="Migration", pt="Migração"),
            "blurb": T(
                en="Singapore publishes who is here and on what pass, not "
                   "how many arrived: 40% of the population are not "
                   "citizens. The UN's net estimate is drawn in a lens.",
                pt="Singapura publica quem está aqui e com que passe, não "
                   "quantos chegaram: 40% da população não é de cidadãos. A "
                   "estimativa líquida da ONU aparece numa lente."),
            "spark": ctx.col("migration/migration.csv", "nonresident_population"),
            "stats": [
                ctx.stat(T(en="Foreign citizens", pt="Estrangeiros"),
                         [(y, (dict(ctx.col(D, "population_total"))[y]
                               - dict(ctx.col(D, "population_citizen"))[y])
                           / dict(ctx.col(D, "population_total"))[y] * 100)
                          for y, _ in ctx.col(D, "population_total")],
                         "pct", kind="level"),
                ctx.stat(T(en="Non-residents", pt="Não residentes"),
                         [(y, v / 1e6) for y, v in
                          ctx.col("migration/migration.csv",
                                  "nonresident_population")], "pop_mn",
                         kind="level"),
                ctx.stat(T(en="Net migration, per 1,000 people",
                           pt="Migração líquida, por 1.000 pessoas"),
                         [(y, v / dict(ctx.col(D, "population_total"))[y] * 1000)
                          for y, v in
                          ctx.col("migration/migration.csv",
                                  "net_migration_wb")
                          if y in dict(ctx.col(D, "population_total"))],
                         "dec2"),
            ],
        },
    ]
