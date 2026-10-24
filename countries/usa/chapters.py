"""The USA chapters: the cards, their copy, and each plate's data table.

The titles and blurbs are the same strings the plates build their figures
with, and the Portuguese is the same catalog entry the plates are translated
through, so a card and its plate cannot disagree about what the plate is
called.

`table` names the CSV behind a plate and the columns worth tabulating. The
page renders it as a real table under the figure, which is the only way a
reader who cannot see the chart gets the numbers, and `facts` names the
columns the generated alt text quotes.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def headline(ctx) -> list[dict]:
    """The figures the page leads with, above the plates.

    Six readings that frame everything below, computed from this country's
    CSVs at build time rather than typed in, so a refetch moves them
    instead of leaving the page quietly describing last year.

    `kind` is the load-bearing argument. An annual total or average is a
    flow: it stops at the last complete year, because the running year's
    partial figure is not comparable with the ones before it. A stock or a
    population estimate is a level, read at a moment and genuinely
    current. The year is printed under each figure by the page, from the
    row it was actually read from, so the labels do not repeat it.
    """
    return [
        ctx.stat({"en": 'GDP', "pt": 'PIB'},
                 ctx.col("macro/gdp.csv", "nominal_usdbn"), "money_bn"),
        ctx.stat({"en": 'GDP per person, US$', "pt": 'PIB por pessoa, US$'},
                 ctx.col("macro/gdp.csv", "gdp_per_capita_usd"), "count"),
        ctx.stat({"en": 'Population', "pt": 'População'},
                 ctx.col("macro/gdp.csv", "population_mn"), "pop_mn", kind="level"),
        ctx.stat({"en": 'Inflation (CPI)', "pt": 'Inflação (CPI)'},
                 ctx.col("macro/cpi.csv", "value"), "pct"),
        ctx.stat({"en": 'Unemployment', "pt": 'Desemprego'},
                 ctx.col("macro/unemployment.csv", "value"), "pct"),
        # Keyed on the fiscal year, not the calendar year: the American
        # budget tables are published that way and the column is named so.
        ctx.stat({"en": 'Gross federal debt', "pt": 'Dívida federal bruta'},
                 ctx.col("fiscal/debt.csv", "gross_pct_gdp", key="fiscal_year"),
                 "pct_gdp", kind="level"),
    ]


def build(ctx) -> list[dict]:
    """The chapters in page order, each on its spine topic (PLATE_SPINE.md).

    Ids and slugs are the ones the pages have always linked to; the titles
    and blurbs are the plates' own, through the same catalog entries.
    """
    pop = "social/population_july1.csv"
    return [
        {
            "id": '01-economy', "topic": "economy", "n": '01', "family": MONEY,
            "title": ctx.text(en='The American economy',
                              pt='A economia americana'),
            "blurb": ctx.text(en='Growth, income per person, prices and jobs',
                              pt='Crescimento, renda por pessoa, preços e emprego'),
            "spark": ctx.col("macro/gdp.csv", "real_growth"),
            "stats": [
                ctx.stat({"en": "Real growth", "pt": "Crescimento real"},
                         ctx.col("macro/gdp.csv", "real_growth"), "pct_s"),
                ctx.stat({"en": "Inflation (CPI)", "pt": "Inflação (CPI)"},
                         ctx.col("macro/cpi.csv", "value"), "pct"),
            ],
            "table": {
                "csv": 'macro/gdp.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('nominal_usdbn', ctx.text(en='GDP, US$ bn', pt='PIB, US$ bi')),
                    ('real_growth', ctx.text(en='Real growth, %', pt='Crescimento real, %')),
                    ('gdp_per_capita_usd', ctx.text(en='GDP per person, US$', pt='PIB por pessoa, US$')),
                ],
                "facts": ('real_growth', 'nominal_usdbn'),
            },
        },
        {
            "id": '02-fiscal', "topic": "fiscal", "n": '02', "family": MONEY,
            "title": ctx.text(en='What government takes in, spends and owes',
                              pt='O que o governo arrecada, gasta e deve'),
            "blurb": ctx.text(en='General government by calendar year, with the federal budget beside it',
                              pt='Governo geral por ano-calendário, com o orçamento federal ao lado'),
            "spark": ctx.col("fiscal/general_government.csv", "gross_debt_pct_gdp"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Balance", "pt": "Resultado"},
                         ctx.col("fiscal/general_government.csv", "balance_pct_gdp"),
                         "pct_gdp_s"),
                ctx.stat({"en": "Gross debt", "pt": "Dívida bruta"},
                         ctx.col("fiscal/general_government.csv", "gross_debt_pct_gdp"),
                         "pct_gdp", kind="level"),
            ],
            "table": {
                "csv": 'fiscal/general_government.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('revenue_pct_gdp', ctx.text(en='Revenue, % GDP', pt='Receita, % PIB')),
                    ('expenditure_pct_gdp', ctx.text(en='Expenditure, % GDP', pt='Despesa, % PIB')),
                    ('balance_pct_gdp', ctx.text(en='Balance, % GDP', pt='Resultado, % PIB')),
                    ('gross_debt_pct_gdp', ctx.text(en='Gross debt, % GDP', pt='Dívida bruta, % PIB')),
                ],
                "facts": ('balance_pct_gdp', 'gross_debt_pct_gdp'),
            },
        },
        {
            "id": '03-spending', "topic": "spending", "n": '03', "family": MONEY,
            "title": ctx.text(en='Where the money goes',
                              pt='Para onde vai o dinheiro'),
            "blurb": ctx.text(en='General-government spending by function, and what is invested',
                              pt='Gasto do governo geral por função, e o que se investe'),
            "spark": ctx.col("fiscal/cofog.csv", "total"),
            "stats": [
                ctx.stat({"en": "Spending", "pt": "Gasto"},
                         ctx.col("fiscal/cofog.csv", "total"), "pct_gdp"),
                ctx.stat({"en": "Health", "pt": "Saúde"},
                         ctx.col("fiscal/cofog.csv", "health"), "pct_gdp"),
            ],
            "table": {
                "csv": 'fiscal/cofog.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('total', ctx.text(en='Total, % GDP', pt='Total, % PIB')),
                    ('social_protection', ctx.text(en='Social protection, % GDP', pt='Proteção social, % PIB')),
                    ('health', ctx.text(en='Health, % GDP', pt='Saúde, % PIB')),
                    ('education', ctx.text(en='Education, % GDP', pt='Educação, % PIB')),
                    ('defence', ctx.text(en='Defence, % GDP', pt='Defesa, % PIB')),
                ],
                "facts": ('total', 'health'),
            },
        },
        {
            "id": '04-trade', "topic": "trade", "n": '04', "family": WORLD,
            "title": ctx.text(en='What America buys and sells',
                              pt='O que os Estados Unidos compram e vendem'),
            "blurb": ctx.text(en='Trade as a share of GDP, who buys American goods and who sells to America',
                              pt='Comércio como parcela do PIB, quem compra bens americanos e quem vende aos EUA'),
            "spark": ctx.col("trade/trade.csv", "balance"),
            "stats": [
                ctx.stat({"en": "Goods balance", "pt": "Saldo de bens"},
                         ctx.col("trade/trade.csv", "goods_balance"), "usd_bn_s"),
                ctx.stat({"en": "Services balance", "pt": "Saldo de serviços"},
                         ctx.col("trade/trade.csv", "services_balance"), "usd_bn_s"),
            ],
            "table": {
                "csv": 'trade/trade.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('exports', ctx.text(en='Exports, US$ bn', pt='Exportações, US$ bi')),
                    ('imports', ctx.text(en='Imports, US$ bn', pt='Importações, US$ bi')),
                    ('goods_balance', ctx.text(en='Goods balance, US$ bn', pt='Saldo de bens, US$ bi')),
                    ('services_balance', ctx.text(en='Services balance, US$ bn', pt='Saldo de serviços, US$ bi')),
                ],
                "facts": ('goods_balance', 'services_balance'),
            },
        },
        {
            "id": '05-markets', "topic": "markets", "n": '05', "family": MONEY,
            "title": ctx.text(en='Money and markets',
                              pt='Dinheiro e mercados'),
            "blurb": ctx.text(en='The policy rate, the long rate, the dollar and the stock market',
                              pt='A taxa básica, os juros longos, o dólar e a bolsa'),
            "spark": ctx.col("macro/treasury.csv", "ten_year_avg"),
            "stats": [
                ctx.stat({"en": "10-year yield", "pt": "Juro de 10 anos"},
                         ctx.col("macro/treasury.csv", "ten_year_avg"), "pct2"),
                ctx.stat({"en": "Policy rate, top of range", "pt": "Taxa básica, teto da faixa"},
                         ctx.col("macro/fed_funds.csv", "target_hi"), "pct2",
                         kind="level"),
            ],
            "table": {
                "csv": 'markets/sp500.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('average', ctx.text(en='Yearly average', pt='Média do ano')),
                    ('close', ctx.text(en='Year-end close', pt='Fechamento do ano')),
                    ('change_pct', ctx.text(en='Change, %', pt='Variação, %')),
                    ('drawdown_pct', ctx.text(en='Largest fall in year, %', pt='Maior queda no ano, %')),
                ],
                "facts": ('close', 'drawdown_pct'),
            },
        },
        {
            "id": '06-people', "topic": "people", "n": '06', "family": PEOPLE,
            "title": ctx.text(en='Households',
                              pt='Famílias'),
            "blurb": ctx.text(en='Inequality, poverty on three measures, the wage floor and the children',
                              pt='Desigualdade, pobreza em três medidas, o piso salarial e as crianças'),
            "spark": ctx.col("social/poverty.csv", "spm_all"),
            "stats": [
                ctx.stat({"en": "Poverty, supplemental", "pt": "Pobreza, suplementar"},
                         ctx.col("social/poverty.csv", "spm_all"), "pct"),
                ctx.stat({"en": "Median household income, US$", "pt": "Renda mediana dos domicílios, US$"},
                         ctx.col("social/income.csv", "median_household_income"), "count"),
            ],
            "table": {
                "csv": 'social/poverty.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('opm_all', ctx.text(en='Official, all, %', pt='Oficial, todos, %')),
                    ('spm_all', ctx.text(en='Supplemental, all, %', pt='Suplementar, todos, %')),
                    ('opm_under18', ctx.text(en='Official, under 18, %', pt='Oficial, menores de 18, %')),
                    ('spm_under18', ctx.text(en='Supplemental, under 18, %', pt='Suplementar, menores de 18, %')),
                ],
                "facts": ('spm_under18', 'opm_under18'),
            },
        },
        {
            "id": '07-world', "topic": "world", "n": '07', "family": WORLD,
            "title": ctx.text(en='The United States in the world',
                              pt='Os Estados Unidos no mundo'),
            "blurb": ctx.text(en='The size of the economy, human development, corruption and reserves',
                              pt='O tamanho da economia, desenvolvimento humano, corrupção e reservas'),
            "spark": ctx.col("international/corruption.csv", "score"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Share of world GDP", "pt": "Parcela do PIB mundial"},
                         ctx.col("international/worldbank.csv", "us_share_world_gdp"), "pct"),
                ctx.stat({"en": "Corruption Perceptions Index", "pt": "Índice de Percepção da Corrupção"},
                         ctx.col("international/corruption.csv", "score"), "score100",
                         kind="level"),
            ],
            "table": {
                "csv": 'international/corruption.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('score', ctx.text(en='CPI score, 2012 method', pt='Pontuação no IPC, método de 2012')),
                    ('score_pre2012', ctx.text(en='Old method, 0-10', pt='Método antigo, 0-10')),
                ],
                "facts": ('score',),
            },
        },
        {
            "id": '08-demographics', "topic": "demography", "n": '08', "family": PEOPLE,
            "title": ctx.text(en='How many Americans',
                              pt='Quantos americanos'),
            "blurb": ctx.text(en='Population, fertility, births and deaths, and what changes the total',
                              pt='População, fecundidade, nascimentos e mortes, e o que muda o total'),
            "spark": ctx.col(pop, "population"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Net migration, per 1,000", "pt": "Migração líquida, por mil"},
                         ctx.col("social/components.csv", "net_migration_rate"), "dec2"),
                ctx.stat({"en": "Fertility rate", "pt": "Taxa de fecundidade"},
                         ctx.col("international/worldbank.csv", "fertility"), "dec2"),
            ],
            "table": {
                "csv": 'social/components.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('birth_rate', ctx.text(en='Births per 1,000', pt='Nascimentos por mil')),
                    ('death_rate', ctx.text(en='Deaths per 1,000', pt='Mortes por mil')),
                    ('natural_rate', ctx.text(en='Natural increase per 1,000', pt='Crescimento natural por mil')),
                    ('net_migration_rate', ctx.text(en='Net migration per 1,000', pt='Migração líquida por mil')),
                ],
                "facts": ('net_migration_rate', 'natural_rate'),
            },
        },
        {
            "id": '09-mortality', "topic": "mortality", "n": '09', "family": PEOPLE,
            "title": ctx.text(en='Deaths',
                              pt='Mortes'),
            "blurb": ctx.text(en='How many die, how many more than usual, COVID-19, and how long people live',
                              pt='Quantos morrem, quantos a mais que o normal, a COVID-19 e quanto se vive'),
            "spark": ctx.col("social/demography_wdi.csv", "death_rate_per_1000"),
            "stats": [
                ctx.stat({"en": "Deaths per 1,000", "pt": "Mortes por mil"},
                         ctx.col("social/demography_wdi.csv", "death_rate_per_1000"), "dec2"),
                ctx.stat({"en": "Life expectancy, years", "pt": "Expectativa de vida, anos"},
                         ctx.col("international/worldbank.csv", "life_expectancy"), "years"),
            ],
            "table": {
                "csv": 'social/mortality.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('total_deaths', ctx.text(en='All deaths', pt='Todas as mortes')),
                    ('covid_underlying', ctx.text(en='COVID-19, underlying cause', pt='COVID-19, causa básica')),
                    ('covid_involved', ctx.text(en='Involving COVID-19', pt='Envolvendo COVID-19')),
                ],
                "facts": ('total_deaths', 'covid_involved'),
            },
        },
        {
            "id": '10-violence', "topic": "security", "n": '10', "family": PEOPLE,
            "title": ctx.text(en='Violent and accidental death',
                              pt='Mortes violentas e acidentais'),
            "blurb": ctx.text(en='Homicide, suicide, the roads, overdoses and firearms, per 100,000 people',
                              pt='Homicídio, suicídio, trânsito, overdoses e armas de fogo, por 100 mil habitantes'),
            "spark": ctx.col("social/violence.csv", "homicide_rate"),
            "stats": [
                ctx.stat({"en": "Homicides per 100,000", "pt": "Homicídios por 100 mil"},
                         ctx.col("social/violence.csv", "homicide_rate"), "per100k"),
                ctx.stat({"en": "Suicides per 100,000", "pt": "Suicídios por 100 mil"},
                         ctx.col("social/death_rates.csv", "suicide_rate"), "per100k"),
            ],
            "table": {
                "csv": 'social/violence.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('homicides', ctx.text(en='Homicides', pt='Homicídios')),
                    ('homicide_rate', ctx.text(en='Homicides per 100,000', pt='Homicídios por 100 mil')),
                    ('firearm_deaths', ctx.text(en='Firearm deaths', pt='Mortes por arma de fogo')),
                    ('suicides', ctx.text(en='Suicides', pt='Suicídios')),
                    ('overdoses', ctx.text(en='Overdoses', pt='Overdoses')),
                ],
                "facts": ('homicide_rate', 'overdoses'),
            },
        },
        {
            "id": '11-credit', "topic": "credit", "n": '11', "family": MONEY,
            "title": ctx.text(en='What households owe',
                              pt='O que as famílias devem'),
            "blurb": ctx.text(en='Household debt, what it costs, who falls behind, and what it is made of',
                              pt='Dívida das famílias, quanto custa, quem atrasa e do que ela é feita'),
            "spark": ctx.col("credit/household_credit.csv", "hh_credit_pct_gdp_q4"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Household debt", "pt": "Dívida das famílias"},
                         ctx.col("credit/household_credit.csv", "hh_credit_pct_gdp_q4"),
                         "pct_gdp", kind="level"),
                ctx.stat({"en": "90+ days delinquent", "pt": "Atraso de 90+ dias"},
                         ctx.col("credit/delinquency.csv", "all"), "pct"),
            ],
            "table": {
                "csv": 'credit/household_debt.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('mortgage', ctx.text(en='Mortgage, US$ tn', pt='Hipoteca, US$ tri')),
                    ('credit_card', ctx.text(en='Credit card, US$ tn', pt='Cartão de crédito, US$ tri')),
                    ('student', ctx.text(en='Student, US$ tn', pt='Estudantil, US$ tri')),
                    ('total', ctx.text(en='Total, US$ tn', pt='Total, US$ tri')),
                ],
                "facts": ('total', 'credit_card'),
            },
        },
        {
            "id": "12-migration", "topic": "migration", "n": "12", "family": PEOPLE,
            "title": ctx.text(en="Migration, without mixing unlike measures", pt="Migração, sem misturar medidas diferentes"),
            "blurb": ctx.text(en="Census net migration and ACS birthplace and citizenship stocks; gross PEP components remain unpublished.", pt="Migração líquida do Census e estoques do ACS por nascimento e cidadania; os componentes brutos do PEP seguem inéditos."),
            "spark": ctx.col("migration/stock_acs.csv", "foreign_born"),
            "spark_level": True,
            "stats": [ctx.stat({"en": "Foreign-born residents", "pt": "Residentes nascidos no exterior"}, ctx.col("migration/stock_acs.csv", "foreign_born"), "count", kind="level")],
            "table": {"csv": "migration/stock_acs.csv", "key": "year",
                      "columns": [("year", ctx.text(en="Year", pt="Ano")),
                                  ("foreign_born", ctx.text(en="Foreign-born", pt="Nascidos no exterior")),
                                  ("naturalized", ctx.text(en="Naturalized citizens", pt="Cidadãos naturalizados")),
                                  ("noncitizen", ctx.text(en="Noncitizens", pt="Não cidadãos"))],
                      "facts": ("foreign_born", "noncitizen")},
        },
    ]
