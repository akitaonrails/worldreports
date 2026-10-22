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

MONEY, WORLD, PEOPLE = "money", "world", "people"


def build(ctx) -> list[dict]:
    chapters = [
        {
            "id": "01_economy", "n": "01", "family": MONEY,
            "title": ctx.text(en="The Brazilian Economy", pt="A Economia Brasileira"),
            "blurb": ctx.text(en="Nominal size, real growth, income per person and inflation "
                "— the four numbers the rest depend on.", pt="Tamanho nominal, crescimento real, renda por pessoa e "
                "inflação — os quatro números dos quais o resto depende."),
            "spark": ctx.col("macro/gdp.csv", "nominal_rbi"),
            "stats": [
                ctx.stat({"en": "GDP", "pt": "PIB"},
                     ctx.col("macro/gdp.csv", "nominal_rbi"), "money_bn"),
                ctx.stat({"en": "Real growth", "pt": "Crescimento real"},
                     ctx.col("macro/gdp.csv", "real_growth"), "pct_s"),
                ctx.stat({"en": "Inflation", "pt": "Inflação"},
                     ctx.col("macro/ipca.csv", "value"), "pct"),
            ],
        },
        {
            "id": "02_fiscal", "n": "02", "family": MONEY,
            "title": ctx.text(en="Taxes, Balance & Debt", pt="Impostos, Resultado e Dívida"),
            "blurb": ctx.text(en="What the state collects, whether it spends more than it "
                "raises, and what that does to the debt stock.", pt="O que o Estado arrecada, se gasta mais do que arrecada, e o "
                "que isso faz com o estoque da dívida."),
            "spark": ctx.col("fiscal/debt.csv", "gross"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Gross debt", "pt": "Dívida bruta"},
                     ctx.col("fiscal/debt.csv", "gross"), "pct_gdp", kind="level"),
                ctx.stat({"en": "Tax burden", "pt": "Carga tributária"},
                     ctx.col("fiscal/tax_burden.csv", "value"), "pct_gdp"),
                ctx.stat({"en": "Primary result", "pt": "Resultado primário"},
                     ctx.col("fiscal/primary_result.csv", "value"), "pct_gdp_s"),
            ],
        },
        {
            "id": "03_spending", "n": "03", "family": MONEY,
            "title": ctx.text(en="Where the Money Goes", pt="Para Onde Vai o Dinheiro"),
            "blurb": ctx.text(en="Federal spending by function — pensions against everything "
                "else the budget has to carry.", pt="Gasto federal por função — a Previdência contra tudo mais "
                "que o Orçamento precisa carregar."),
            "spark": ctx.col("fiscal/spending_by_function_rbi.csv", "previdencia"),
            "stats": [
                ctx.stat({"en": "Pensions", "pt": "Previdência"},
                     ctx.col("fiscal/spending_by_function_rbi.csv", "previdencia"), "money_bn"),
                ctx.stat({"en": "Health", "pt": "Saúde"},
                     ctx.col("fiscal/spending_by_function_rbi.csv", "saude"), "money_bn"),
                ctx.stat({"en": "Investment", "pt": "Investimento"},
                     ctx.col("fiscal/spending_by_function_rbi.csv", "investimento_gnd4"), "money_bn"),
            ],
        },
        {
            "id": "06_trade", "n": "06", "family": WORLD,
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
        },
        {
            "id": "04_markets", "n": "04", "family": MONEY,
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
        },
        {
            "id": "08_people", "n": "08", "family": PEOPLE,
            "title": ctx.text(en="Development, Jobs & Poverty", pt="Desenvolvimento, Trabalho e Pobreza"),
            "blurb": ctx.text(en="Human development, inequality, unemployment, the minimum "
                "wage and how far poverty actually fell.", pt="Desenvolvimento humano, desigualdade, desemprego, o salário "
                "mínimo e quanto a pobreza realmente caiu."),
            "spark": ctx.col("macro/unemployment.csv", "value"),
            "stats": [
                ctx.stat({"en": "Unemployment", "pt": "Desemprego"},
                     ctx.col("macro/unemployment.csv", "value"), "pct"),
                ctx.stat({"en": "HDI", "pt": "IDH"},
                     ctx.col("social/hdi.csv", "value"), "dec3"),
                ctx.stat({"en": "Poverty", "pt": "Pobreza"},
                     ctx.col("social/poverty.csv", "poverty_pct"), "pct"),
            ],
        },
        {
            "id": "07_world", "n": "07", "family": WORLD,
            "title": ctx.text(en="Brazil in the World", pt="O Brasil no Mundo"),
            "blurb": ctx.text(en="How the outside world scores Brazil, how closed its economy "
                "is, and the reserves behind it.", pt="Como o mundo avalia o Brasil, quão fechada é sua economia, "
                "e as reservas por trás disso."),
            "spark": ctx.col("macro/reserves.csv", "eop_usbi"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Reserves", "pt": "Reservas"},
                     ctx.col("macro/reserves.csv", "eop_usbi"), "usd_bn", kind="level"),
                ctx.stat({"en": "Corruption index", "pt": "Índice de corrupção"},
                     ctx.col("international/cpi.csv", "score"), "score100"),
                ctx.stat({"en": "Competitiveness", "pt": "Competitividade"},
                     ctx.col("international/wef.csv", "rank"), "rank"),
            ],
        },
        {
            "id": "09_demographics", "n": "09", "family": PEOPLE,
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
        },
        {
            "id": "10_security", "n": "10", "family": PEOPLE,
            "title": ctx.text(en="Violence", pt="Violência"),
            "blurb": ctx.text(en="Homicides falling while police lethality climbs — two "
                "measurement systems, deliberately not spliced.", pt="Homicídios caindo enquanto a letalidade policial sobe — "
                "dois sistemas de medição, deliberadamente não emendados."),
            "spark": ctx.col("social/homicides.csv", "rate"),
            "stats": [
                ctx.stat({"en": "Homicide rate", "pt": "Taxa de homicídios"},
                     ctx.col("social/homicides.csv", "rate"), "per100k"),
                ctx.stat({"en": "Police killings", "pt": "Mortes por intervenção policial"},
                     ctx.col("social/violence_fbsp.csv", "police_killings"), "count"),
                ctx.stat({"en": "Femicides", "pt": "Feminicídios"},
                     ctx.col("social/violence_fbsp.csv", "femicides"), "count"),
            ],
        },
        {
            "id": "11_epidemics", "n": "11", "family": PEOPLE,
            "title": ctx.text(en="Epidemics", pt="Epidemias"),
            "blurb": ctx.text(en="COVID killed 425,218 in 2021 alone. Dengue set its record "
                "in 2024, and influenza in 2025.", pt="A COVID matou 425.218 só em 2021. A dengue bateu recorde "
                "em 2024, e a influenza em 2025."),
            # the COVID column is the striking one but it is two orders of
            # magnitude above the others and nearly flat since 2023; dengue
            # carries the shape a sparkline can actually show
            "spark": ctx.col("social/epidemic_deaths.csv", "dengue"),
            "stats": [
                ctx.stat({"en": "COVID-19 deaths", "pt": "Óbitos por COVID-19"},
                     ctx.col("social/epidemic_deaths.csv", "covid"), "count"),
                ctx.stat({"en": "Influenza deaths", "pt": "Óbitos por influenza"},
                     ctx.col("social/epidemic_deaths.csv", "influenza"), "count"),
                ctx.stat({"en": "Dengue deaths", "pt": "Óbitos por dengue"},
                     ctx.col("social/epidemic_deaths.csv", "dengue"), "count"),
            ],
        },
        {
            "id": "05_credit", "n": "05", "family": MONEY,
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
        },
    ]

    # Plate numbers are assigned by family — money 01-05, world 06-07,
    # people 08-11 — so sorting by id is what groups the index page. The
    # editorial blocks above stay in the order they were written, because
    # moving them would make every future diff look like a rewrite.
    chapters.sort(key=lambda c: c["id"])

    return chapters
