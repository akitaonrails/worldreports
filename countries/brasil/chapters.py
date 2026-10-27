"""The brasil chapters: the cards, their copy and their headline figures.

Editorial copy lives here. Every number is read from this country's CSVs at
build time by the context, so a figure on a card and the same figure on its
plate cannot disagree.

`spec` names how a figure is written, not what it means — see
core.sitebuild.NUMFMT and AFFIX. `kind` says whether it is current:
'flow' for an annual total that is only comparable once the year is
complete, 'level' for a stock or a rate read at a moment, 'projection' for
an official forward estimate.
"""
from __future__ import annotations

from core.sideload import sibling

MONEY, WORLD, PEOPLE = "money", "world", "people"


def per_100k(ctx, count_col, pop_mn_col):
    """(year, rate) pairs: a count over the same year's population in
    millions, ×100,000 — the same conversion the plates draw."""
    pop = dict(pop_mn_col)
    return [(y, v / (pop[y] * 1e6) * 1e5) for y, v in count_col if y in pop]


def trillions(pairs):
    """Convert a series stored in billions of reais to trillions."""
    return [(year, value / 1_000) for year, value in pairs]


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
        ctx.stat({"pt": 'PIB', "en": 'GDP'},
                 trillions(ctx.col("macro/gdp.csv", "nominal_rbi")),
                 "money_tn1"),
        ctx.stat({"pt": 'PIB por pessoa, US$', "en": 'GDP per person, US$'},
                 ctx.col("macro/gdp.csv", "gdp_per_capita_usd"), "count"),
        ctx.stat({"pt": 'População', "en": 'Population'},
                 ctx.col("macro/gdp.csv", "population_mn"), "pop_mn", kind="level"),
        ctx.stat({"pt": 'IPCA', "en": 'Inflation (IPCA)'},
                 ctx.col("macro/ipca.csv", "value"), "pct"),
        ctx.stat({"pt": 'Desemprego', "en": 'Unemployment'},
                 ctx.col("macro/unemployment.csv", "value"), "pct"),
        ctx.stat({"pt": 'Dívida bruta', "en": 'Gross public debt'},
                 ctx.col("fiscal/debt.csv", "gross"), "pct_gdp", kind="level"),
    ]


def build(ctx) -> list[dict]:
    stories = sibling(__file__, "stories")
    chapters = [
        {
            "id": "01_economy", "topic": "economy", "n": "01", "family": MONEY,
            "title": ctx.text(en="The Brazilian Economy", pt="A Economia Brasileira"),
            "blurb": ctx.text(en="Real growth, income per person in dollars, inflation "
                "against the target and unemployment at a series low.", pt="Crescimento real, renda por pessoa em dólares, inflação "
                "contra a meta e desemprego na mínima da série."),
            "spark": ctx.col("macro/gdp.csv", "nominal_rbi"),
            "stats": [
                ctx.stat({"en": "GDP", "pt": "PIB"},
                     trillions(ctx.col("macro/gdp.csv", "nominal_rbi")),
                     "money_tn1"),
                ctx.stat({"en": "Real growth", "pt": "Crescimento real"},
                     ctx.col("macro/gdp.csv", "real_growth"), "pct_s"),
                ctx.stat({"en": "Inflation", "pt": "Inflação"},
                     ctx.col("macro/ipca.csv", "value"), "pct"),
            ],
            "stories": stories.economy_stories(ctx),
        },
        {
            "id": "02_fiscal", "topic": "fiscal", "n": "02", "family": MONEY,
            "title": ctx.text(en="Balance, Debt & Interest", pt="Resultado, Dívida e Juros"),
            "blurb": ctx.text(en="General government on the IMF's basis, beside the "
                "measures Brazil argues in: the primary result, DBGG gross debt and the "
                "interest bill.", pt="O governo geral pelo critério do FMI, ao lado das "
                "medidas do debate brasileiro: resultado primário, dívida bruta DBGG e a "
                "conta de juros."),
            "spark": ctx.col("fiscal/general_government.csv", "gross_debt_pct_gdp"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Gross debt (IMF)", "pt": "Dívida bruta (FMI)"},
                     ctx.col("fiscal/general_government.csv", "gross_debt_pct_gdp"),
                     "pct_gdp", kind="level"),
                ctx.stat({"en": "Overall balance", "pt": "Resultado nominal"},
                     ctx.col("fiscal/general_government.csv", "balance_pct_gdp"),
                     "pct_gdp_s"),
                ctx.stat({"en": "Interest (NFSP)", "pt": "Juros (NFSP)"},
                     ctx.col("fiscal/nfsp.csv", "interest"), "pct_gdp"),
            ],
            "stories": stories.fiscal_stories(ctx),
        },
        {
            "id": "03_spending", "topic": "spending", "n": "03", "family": MONEY,
            "title": ctx.text(en="Where the Money Goes", pt="Para Onde Vai o Dinheiro"),
            "blurb": ctx.text(en="Spending by function — social protection against "
                "everything else — and how little the economy invests.", pt="Gasto por função — a proteção social contra todo o "
                "resto — e quão pouco a economia investe."),
            "spark": ctx.col("fiscal/spending_by_function_rbi.csv", "previdencia"),
            "stats": [
                ctx.stat({"en": "Pensions", "pt": "Previdência"},
                     ctx.col("fiscal/spending_by_function_rbi.csv", "previdencia"), "money_bn"),
                ctx.stat({"en": "Health", "pt": "Saúde"},
                     ctx.col("fiscal/spending_by_function_rbi.csv", "saude"), "money_bn"),
                ctx.stat({"en": "Investment", "pt": "Investimento"},
                     ctx.col("fiscal/spending_by_function_rbi.csv", "investimento_gnd4"), "money_bn"),
            ],
            "stories": stories.spending_stories(ctx),
        },
        {
            "id": "06_trade", "topic": "trade", "n": "06", "family": WORLD,
            "title": ctx.text(en="Foreign Trade", pt="Comércio Exterior"),
            "blurb": ctx.text(en="A commodity-heavy export machine, a diversified import "
                "bill, and China replacing everyone else.", pt="Uma pauta de exportação pesada em commodities, uma conta de "
                "importação diversificada, e a China substituindo todo mundo."),
            "spark": ctx.col("trade/trade.csv", "balance"),
            "stats": [
                ctx.stat({"en": "Exports", "pt": "Exportações"},
                     ctx.col("trade/trade.csv", "exports"), "usd_bn"),
                ctx.stat({"en": "Imports", "pt": "Importações"},
                     ctx.col("trade/trade.csv", "imports"), "usd_bn"),
                ctx.stat({"en": "Balance", "pt": "Saldo"},
                     ctx.col("trade/trade.csv", "balance"), "usd_bn_s"),
            ],
            "stories": stories.trade_stories(ctx),
        },
        {
            "id": "04_markets", "topic": "markets", "n": "04", "family": MONEY,
            "title": ctx.text(en="Money & Markets", pt="Moeda e Mercados"),
            "blurb": ctx.text(en="Brazilian equities in reais, in dollars, and beside the "
                "S&P 500 — the currency is half the story.", pt="A bolsa brasileira em reais, em dólares e ao lado do "
                "S&P 500 — o câmbio é metade da história."),
            "spark": ctx.col("macro/dollar.csv", "eop"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "USD/BRL", "pt": "Dólar"},
                     ctx.col("macro/dollar.csv", "eop"), "money2", kind="level"),
                ctx.stat({"en": "Selic", "pt": "Selic"},
                     ctx.col("macro/selic.csv", "value"), "pct2", kind="level"),
                ctx.stat({"en": "Ibovespa", "pt": "Ibovespa"},
                     ctx.col("markets/ibov.csv", "close"), "count", kind="level"),
            ],
            "stories": stories.markets_stories(ctx),
        },
        {
            "id": "08_people", "topic": "people", "n": "08", "family": PEOPLE,
            "title": ctx.text(en="Inequality, Poverty & Wages", pt="Desigualdade, Pobreza e Salários"),
            "blurb": ctx.text(en="Inequality, how far poverty actually fell, and a "
                "minimum wage that gained far more in reais than in dollars.", pt="A desigualdade, quanto a pobreza realmente caiu e "
                "um salário mínimo que ganhou muito mais em reais do que em dólares."),
            "spark": ctx.col("social/poverty.csv", "poverty_pct"),
            "stats": [
                ctx.stat({"en": "Gini (IBGE)", "pt": "Gini (IBGE)"},
                     ctx.col("social/gini.csv", "ibge"), "dec3"),
                ctx.stat({"en": "Poverty, US$8.30 a day", "pt": "Pobreza, US$ 8,30 por dia"},
                     ctx.col("social/poverty.csv", "poverty_pct"), "pct"),
                ctx.stat({"en": "Minimum wage, R$ a month", "pt": "Salário mínimo, R$ por mês"},
                     ctx.col("macro/minimum_wage.csv", "value"), "count",
                     kind="level"),
            ],
            "stories": stories.people_stories(ctx),
        },
        {
            "id": "07_world", "topic": "world", "n": "07", "family": WORLD,
            "title": ctx.text(en="Brazil in the World", pt="O Brasil no Mundo"),
            "blurb": ctx.text(en="The economy in dollars, how the UNDP and Transparency "
                "International score Brazil, and the reserves behind the real.", pt="A economia em dólares, como o PNUD e a Transparência "
                "Internacional avaliam o Brasil, e as reservas por trás do real."),
            "spark": ctx.col("macro/reserves.csv", "eop_usbi"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Reserves", "pt": "Reservas"},
                     ctx.col("macro/reserves.csv", "eop_usbi"), "usd_bn", kind="level"),
                ctx.stat({"en": "Corruption index", "pt": "Índice de corrupção"},
                     ctx.col("international/cpi.csv", "score"), "score100"),
                ctx.stat({"en": "HDI", "pt": "IDH"},
                     ctx.col("social/hdi.csv", "value"), "dec3"),
            ],
            "stories": stories.world_stories(ctx),
        },
        {
            "id": "09_demographics", "topic": "demography", "n": "09", "family": PEOPLE,
            "title": ctx.text(en="The Demographic Transition", pt="A Transição Demográfica"),
            "blurb": ctx.text(en="Fertility down a third since 2000. The population peaks in "
                "2041 and shrinks from 2042.", pt="Fecundidade um terço menor desde 2000. A população atinge o "
                "pico em 2041 e encolhe a partir de 2042."),
            "spark": [p for p in ctx.col("social/population.csv", "tfr") if p[0] <= 2040],
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Fertility rate", "pt": "Taxa de fecundidade"},
                     ctx.col("social/population.csv", "tfr"), "dec2", year=2024),
                ctx.stat({"en": "Births", "pt": "Nascimentos"},
                     ctx.col("social/population.csv", "births"), "count", year=2024),
                ctx.stat({"en": "Population", "pt": "População"},
                     ctx.col("social/population.csv", "pop_mn"), "pop_mn",
                     year=2026, kind="projection"),
            ],
            "stories": stories.demography_stories(ctx),
        },
        {
            "id": "10_security", "topic": "security", "n": "10", "family": PEOPLE,
            "title": ctx.text(en="Violence", pt="Violência"),
            "blurb": ctx.text(en="Homicides falling while recorded deaths resulting from police intervention rise — two "
                "measurement systems, deliberately not spliced.", pt="Homicídios caindo enquanto os óbitos registrados decorrentes de intervenção policial aumentam — "
                "dois sistemas de medição, deliberadamente não emendados."),
            "spark": ctx.col("social/homicides.csv", "rate"),
            "stats": [
                ctx.stat({"en": "Homicide rate", "pt": "Taxa de homicídios"},
                     ctx.col("social/homicides.csv", "rate"), "per100k"),
                ctx.stat({"en": "Deaths following police intervention", "pt": "Mortes decorrentes de intervenção policial"},
                     per_100k(ctx, ctx.col("social/violence_fbsp.csv", "police_killings"),
                              ctx.col("social/population.csv", "pop_mn")), "per100k"),
                ctx.stat({"en": "Femicides", "pt": "Feminicídios"},
                     ctx.col("social/violence_fbsp.csv", "femicides"), "count"),
            ],
            "stories": stories.security_stories(ctx),
        },
        {
            "id": "11_epidemics", "topic": "mortality", "n": "11", "family": PEOPLE,
            "title": ctx.text(en="Mortality & Epidemics", pt="Mortalidade e Epidemias"),
            "blurb": ctx.text(en="COVID killed 425,218 in 2021 alone. Dengue set its record "
                "in 2024, and influenza in 2025.", pt="A COVID matou 425.218 só em 2021. A dengue bateu recorde "
                "em 2024, e a influenza em 2025."),
            # the COVID column is the striking one but it is two orders of
            # magnitude above the others and nearly flat since 2023; dengue
            # carries the shape a sparkline can actually show
            "spark": ctx.col("social/epidemic_deaths.csv", "dengue"),
            "stats": [
                ctx.stat({"en": "Registered deaths", "pt": "Óbitos registrados"},
                     ctx.col("social/deaths.csv", "registered"), "count"),
                ctx.stat({"en": "COVID-19 deaths", "pt": "Óbitos por COVID-19"},
                     ctx.col("social/epidemic_deaths.csv", "covid"), "count"),
                ctx.stat({"en": "Dengue deaths", "pt": "Óbitos por dengue"},
                     ctx.col("social/epidemic_deaths.csv", "dengue"), "count"),
            ],
            "stories": stories.mortality_stories(ctx),
        },
        {
            "id": "05_credit", "topic": "credit", "n": "05", "family": MONEY,
            "title": ctx.text(en="Credit & Household Debt", pt="Crédito e Endividamento"),
            "blurb": ctx.text(en="Households owe half a year's income and pay 38% a year to "
                "borrow. Debt service and arrears are at series highs.", pt="As famílias devem meio ano de renda e pagam 38% ao ano para "
                "tomar emprestado. Serviço da dívida e inadimplência no topo "
                "da série."),
            "spark": ctx.col("macro/household_debt.csv", "debt_income"),
            "spark_level": True,
            "stats": [
                # all three are point-in-time readings, not annual totals,
                # so the August 2026 value is genuinely the current one
                ctx.stat({"en": "Household debt", "pt": "Endividamento das famílias"},
                     ctx.col("macro/household_debt.csv", "debt_income"), "pct",
                     kind="level"),
                ctx.stat({"en": "Rate paid by households", "pt": "Juros pagos pelas famílias"},
                     ctx.col("macro/credit.csv", "rate_pf"), "pct", kind="level"),
                ctx.stat({"en": "Credit / GDP", "pt": "Crédito / PIB"},
                     ctx.col("macro/credit.csv", "credit_gdp"), "pct_gdp",
                     kind="level"),
            ],
            "stories": stories.credit_stories(ctx),
        },
        {
            "id": "12_migration", "topic": "migration", "n": "12", "family": PEOPLE,
            "title": ctx.text(en="Migration, on compatible definitions", pt="Migração, em definições compatíveis"),
            "blurb": ctx.text(en="Modelled net migration and census stocks; unresolved gross components stay visibly pending.", pt="Migração líquida modelada e estoques censitários; componentes brutos incompatíveis ficam visivelmente pendentes."),
            "spark": ctx.col("migration/stock_census.csv", "foreign_born_pct"),
            "spark_level": True,
            "stats": [ctx.stat({"en": "Foreign-born", "pt": "Nascidos no exterior"}, ctx.col("migration/stock_census.csv", "foreign_born_pct"), "pct", kind="level")],
            "stories": stories.migration_stories(ctx),
        },
    ]

    # Plate numbers are assigned by family — money 01-05, world 06-07,
    # people 08-11 — so sorting by id is what groups the index page. The
    # editorial blocks above stay in the order they were written, because
    # moving them would make every future diff look like a rewrite.
    chapters.sort(key=lambda c: c["id"])

    return chapters
