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
    return [
        {
            "id": '01-economy', "n": '01', "family": MONEY,
            "title": ctx.text(en='The American economy, 2006-2026',
                              pt='A economia americana, 2006-2026'),
            "blurb": ctx.text(en='Output, prices and work, from the agencies that measure them',
                              pt='Produto, preços e trabalho, segundo os órgãos que os medem'),
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
            "id": '02-fiscal', "n": '02', "family": MONEY,
            "title": ctx.text(en='What Washington takes in and what it owes',
                              pt='O que Washington arrecada e o que deve'),
            "blurb": ctx.text(en='Federal receipts, outlays and debt, by fiscal year ending 30 September',
                              pt='Receitas, gastos e dívida federais, por ano fiscal encerrado em 30 de setembro'),
            "table": {
                "csv": 'fiscal/budget.csv', "key": 'fiscal_year',
                "columns": [
                    ('fiscal_year', ctx.text(en='Fiscal year', pt='Ano fiscal')),
                    ('receipts_pct_gdp', ctx.text(en='Receipts, % GDP', pt='Receitas, % PIB')),
                    ('outlays_pct_gdp', ctx.text(en='Outlays, % GDP', pt='Gastos, % PIB')),
                    ('deficit_pct_gdp', ctx.text(en='Deficit, % GDP', pt='Déficit, % PIB')),
                    ('source', ctx.text(en='Source', pt='Fonte')),
                ],
                "facts": ('deficit_pct_gdp',),
            },
        },
        {
            "id": '03-spending', "n": '03', "family": MONEY,
            "title": ctx.text(en='Where the money goes',
                              pt='Para onde vai o dinheiro'),
            "blurb": ctx.text(en='Federal outlays by function, in dollars and as a share of the budget',
                              pt='Gastos federais por função, em dólares e como parcela do orçamento'),
            "table": {
                "csv": 'fiscal/spending.csv', "key": 'fiscal_year',
                "columns": [
                    ('fiscal_year', ctx.text(en='Fiscal year', pt='Ano fiscal')),
                    ('social_security_usdbn', ctx.text(en='Social Security, US$ bn', pt='Previdência, US$ bi')),
                    ('medicare_usdbn', ctx.text(en='Medicare, US$ bn', pt='Medicare, US$ bi')),
                    ('defense_usdbn', ctx.text(en='Defense, US$ bn', pt='Defesa, US$ bi')),
                    ('net_interest_usdbn', ctx.text(en='Net interest, US$ bn', pt='Juros líquidos, US$ bi')),
                    ('total_usdbn', ctx.text(en='Total outlays, US$ bn', pt='Gastos totais, US$ bi')),
                ],
                "facts": ('net_interest_usdbn', 'defense_usdbn'),
            },
        },
        {
            "id": '04-trade', "n": '04', "family": WORLD,
            "title": ctx.text(en='What America buys and sells',
                              pt='O que os Estados Unidos compram e vendem'),
            "blurb": ctx.text(en='Trade in goods and services, and who the goods come from',
                              pt='Comércio de bens e serviços, e de onde vêm os bens'),
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
            "id": '05-markets', "n": '05', "family": MONEY,
            "title": ctx.text(en='Money and markets',
                              pt='Dinheiro e mercados'),
            "blurb": ctx.text(en='The policy rate, the yield curve, the dollar and the stock market',
                              pt='A taxa básica, a curva de juros, o dólar e a bolsa'),
            "table": {
                "csv": 'markets/sp500.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('close', ctx.text(en='Year-end close', pt='Fechamento do ano')),
                    ('change_pct', ctx.text(en='Change, %', pt='Variação, %')),
                    ('drawdown_pct', ctx.text(en='Largest fall in year, %', pt='Maior queda no ano, %')),
                ],
                "facts": ('close', 'drawdown_pct'),
            },
        },
        {
            "id": '06-people', "n": '06', "family": PEOPLE,
            "title": ctx.text(en='Households',
                              pt='Famílias'),
            "blurb": ctx.text(en='What a typical household earns, who is counted as poor, and the wage floor',
                              pt='O que uma família típica ganha, quem é contado como pobre e o piso salarial'),
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
            "id": '07-world', "n": '07', "family": WORLD,
            "title": ctx.text(en='The United States in the world',
                              pt='Os Estados Unidos no mundo'),
            "blurb": ctx.text(en='Share of world output, what health costs, and how long people live',
                              pt='Parcela do produto mundial, quanto custa a saúde e quanto se vive'),
            "table": {
                "csv": 'international/worldbank.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('us_share_world_gdp', ctx.text(en='US share of world GDP, %', pt='Parcela americana do PIB mundial, %')),
                    ('health_spending_pct_gdp', ctx.text(en='Health spending, % GDP', pt='Gasto com saúde, % PIB')),
                    ('life_expectancy', ctx.text(en='Life expectancy, years', pt='Expectativa de vida, anos')),
                ],
                "facts": ('us_share_world_gdp', 'life_expectancy'),
            },
        },
        {
            "id": '08-demographics', "n": '08', "family": PEOPLE,
            "title": ctx.text(en='How many Americans',
                              pt='Quantos americanos'),
            "blurb": ctx.text(en='Population, what changes it, and where the Census Bureau expects it to go',
                              pt='População, o que a altera e para onde o Census Bureau projeta que ela vai'),
            "table": {
                "csv": 'social/population.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('population', ctx.text(en='Population', pt='População')),
                    ('births', ctx.text(en='Births', pt='Nascimentos')),
                    ('deaths', ctx.text(en='Deaths', pt='Mortes')),
                    ('net_migration', ctx.text(en='Net migration', pt='Migração líquida')),
                ],
                "facts": ('population', 'net_migration'),
            },
        },
        {
            "id": '09-mortality', "n": '09', "family": PEOPLE,
            "title": ctx.text(en='Deaths',
                              pt='Mortes'),
            "blurb": ctx.text(en='All causes, COVID-19 and the respiratory diseases — on two definitions',
                              pt='Todas as causas, COVID-19 e as doenças respiratórias — em duas definições'),
            "table": {
                "csv": 'social/mortality.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('total_deaths', ctx.text(en='All deaths', pt='Todas as mortes')),
                    ('covid_involved', ctx.text(en='Involving COVID-19', pt='Envolvendo COVID-19')),
                    ('influenza_underlying', ctx.text(en='Influenza, underlying cause', pt='Gripe, causa básica')),
                    ('influenza_involved', ctx.text(en='Involving influenza', pt='Envolvendo gripe')),
                ],
                "facts": ('total_deaths', 'covid_involved'),
            },
        },
        {
            "id": '10-violence', "n": '10', "family": PEOPLE,
            "title": ctx.text(en='Violent and accidental death',
                              pt='Mortes violentas e acidentais'),
            "blurb": ctx.text(en='Homicide, firearms, suicide and overdose',
                              pt='Homicídio, armas de fogo, suicídio e overdose'),
            "table": {
                "csv": 'social/violence.csv', "key": 'year',
                "columns": [
                    ('year', ctx.text(en='Year', pt='Ano')),
                    ('homicides', ctx.text(en='Homicides', pt='Homicídios')),
                    ('firearm_deaths', ctx.text(en='Firearm deaths', pt='Mortes por arma de fogo')),
                    ('suicides', ctx.text(en='Suicides', pt='Suicídios')),
                    ('overdoses', ctx.text(en='Overdoses', pt='Overdoses')),
                ],
                "facts": ('firearm_deaths', 'overdoses'),
            },
        },
        {
            "id": '11-credit', "n": '11', "family": MONEY,
            "title": ctx.text(en='What households owe',
                              pt='O que as famílias devem'),
            "blurb": ctx.text(en='Household debt, the credit available to draw on, and what it costs',
                              pt='Dívida das famílias, o crédito disponível e quanto ele custa'),
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
    ]
