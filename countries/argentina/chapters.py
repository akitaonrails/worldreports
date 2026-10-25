"""The Argentina chapters: the cards, their copy and the headline figures.

One chapter per plate, each declaring the spine topic it answers (see
PLATE_SPINE.md). The ids of the nine original chapters are kept, so links
to them still work, even where the name and the topic now differ: the
chapter called "living" answers the topic `people`, the one called "people"
answers `demography`, and "state" answers `fiscal`. The three chapters the
spine added — spending, world, mortality — take new ids.

`alt` is written prose about what the plate shows, in all three languages,
because it is the only thing a reader using a screen reader gets instead
of the figure. Every number on a card is read from the CSVs at build time.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def headline(ctx) -> list[dict]:
    """The figures the page leads with, read from the CSVs."""
    return [
        ctx.stat(
            {"es": 'PIB, {year}', "en": 'GDP, {year}', "pt": 'PIB, {year}'},
            ctx.col("macro/gdp.csv", "usd_bn"), "usd_bn1", kind="level"),
        ctx.stat(
            {"es": 'PIB por persona, US$', "en": 'GDP per person, US$',
             "pt": 'PIB por pessoa, US$'},
            ctx.col("macro/world.csv", "gdp_per_person_usd"), "count"),
        ctx.stat(
            {"es": 'Población', "en": 'Population', "pt": 'População'},
            ctx.col("macro/gdp.csv", "population_mn"), "pop_mn",
            kind="level"),
        ctx.stat(
            {"es": 'Inflación, {year}', "en": 'Inflation, {year}',
             "pt": 'Inflação, {year}'},
            ctx.col('macro/ipc.csv', 'official'), 'pct'),
        ctx.stat(
            {"es": 'Pobreza, primer semestre {year}',
             "en": 'Poverty, first half {year}',
             "pt": 'Pobreza, primeiro semestre {year}'},
            ctx.col('social/poverty.csv', 's1'), 'pct', kind='level'),
        ctx.stat(
            {"es": 'Crédito privado, {year}', "en": 'Private credit, {year}',
             "pt": 'Crédito privado, {year}'},
            ctx.col('macro/credit.csv', 'private_pct_gdp'), 'pct_gdp',
            kind='level'),
        ctx.stat(
            {"es": 'Nacimientos, {year}', "en": 'Births, {year}',
             "pt": 'Nascimentos, {year}'},
            ctx.col('social/vitals.csv', 'births'), 'count'),
        ctx.stat(
            {"es": 'Muertes por COVID-19 registradas',
             "en": 'COVID-19 deaths recorded',
             "pt": 'Mortes por COVID-19 registradas'},
            ctx.col('social/causes.csv', 'covid'), 'count', kind='total'),
    ]


def _per(ctx, count_path, count_col, base):
    """A count over INDEC's population, as the plates compute it."""
    pop = dict(ctx.col("macro/gdp.csv", "population_mn"))
    return [(y, v / (pop[y] * 1e6) * base)
            for y, v in ctx.col(count_path, count_col) if y in pop]


def build(ctx) -> list[dict]:
    gg = "fiscal/general_government.csv"
    return [
        {
            "id": '01-output', "topic": "economy", "n": '01', "family": MONEY,
            "title": ctx.text(es='Veinte años de producto argentino',
                              en='Twenty years of Argentine output',
                              pt='Vinte anos de produto argentino'),
            "blurb": ctx.text(
                es='Crecimiento, ingreso por habitante, inflación y desempleo: una economía que cayó en nueve de veinte años.',
                en='Growth, income per head, inflation and unemployment: an economy that shrank in nine years of twenty.',
                pt='Crescimento, renda por habitante, inflação e desemprego: uma economia que encolheu em nove de vinte anos.'),
            "spark": ctx.col("macro/gdp.csv", "real_growth"),
            "stats": [
                ctx.stat({"en": "Real growth", "es": "Crecimiento real",
                          "pt": "Crescimento real"},
                         ctx.col("macro/gdp.csv", "real_growth"), "pct_s"),
                ctx.stat({"en": "Inflation", "es": "Inflación",
                          "pt": "Inflação"},
                         ctx.col("macro/ipc.csv", "official"), "pct"),
                ctx.stat({"en": "Unemployment", "es": "Desempleo",
                          "pt": "Desemprego"},
                         ctx.col("macro/unemployment.csv", "value"), "pct"),
            ],
            "alt": ctx.text(
                es='Cuatro paneles sobre la economía argentina, 2006 a 2026. El crecimiento real del PIB oscila entre -9,9% en 2020 y +10,4% en 2021, y el producto cayó en nueve de los veinte años. El PIB por habitante en dólares corrientes, en escala logarítmica, llega a US$14.898 en 2025 tras un piso de US$8.536 en 2020. La inflación corre entre 18% y 39% anual según el índice provincial de San Luis mientras el índice nacional estuvo intervenido, luego entre 25% y 211% con el índice restaurado del INDEC, con máximo en 2023, y 31,5% en 2025. El desempleo urbano baja de 10,1% a 6,1% en 2023, tras un máximo de 11,5% en 2020.',
                en='Four panels on the Argentine economy, 2006 to 2026. Real GDP growth swings between -9.9% in 2020 and +10.4% in 2021, and output fell in nine of the twenty years. GDP per person in current dollars, on a log scale, reaches US$14,898 in 2025 after a trough of US$8,536 in 2020. Inflation runs at 18% to 39% a year on the San Luis provincial index while the national index was intervened, then 25% to 211% on INDEC\'s restored index, peaking in 2023, and 31.5% in 2025. Urban unemployment falls from 10.1% to 6.1% in 2023, after peaking at 11.5% in 2020.',
                pt='Quatro painéis sobre a economia argentina, 2006 a 2026. O crescimento real do PIB oscila entre -9,9% em 2020 e +10,4% em 2021, e o produto caiu em nove dos vinte anos. O PIB per capita em dólares correntes, em escala logarítmica, chega a US$14.898 em 2025 após um piso de US$8.536 em 2020. A inflação fica entre 18% e 39% ao ano pelo índice provincial de San Luis enquanto o índice nacional esteve sob intervenção, depois entre 25% e 211% pelo índice restaurado do INDEC, com pico em 2023, e 31,5% em 2025. O desemprego urbano cai de 10,1% para 6,1% em 2023, após o pico de 11,5% em 2020.'),
        },
        {
            "id": '02-prices', "topic": "prices", "n": '02', "family": MONEY,
            "title": ctx.text(es='Los precios, el peso y los dos dólares',
                              en='Prices, the peso and the two dollars',
                              pt='Os preços, o peso e os dois dólares'),
            "blurb": ctx.text(
                es='Inflación, el dólar oficial y el paralelo, la brecha y las reservas: la lente propia de la Argentina.',
                en='Inflation, the official and parallel dollar, the gap and reserves: Argentina\'s own lens.',
                pt='Inflação, o dólar oficial e o paralelo, o spread e as reservas: a lente própria da Argentina.'),
            "spark": ctx.col("macro/ipc.csv", "official"),
            "stats": [
                ctx.stat({"en": "Official dollar, year end",
                          "es": "Dólar oficial, fin de año",
                          "pt": "Dólar oficial, fim de ano"},
                         ctx.col("macro/dollar.csv", "official_eop"),
                         "count", kind="level"),
                ctx.stat({"en": "Gross reserves", "es": "Reservas brutas",
                          "pt": "Reservas brutas"},
                         ctx.col("macro/reserves.csv", "eop_usbi"),
                         "usd_bn1", kind="level"),
            ],
            "alt": ctx.text(
                es='Cuatro paneles sobre los precios en la Argentina. La inflación anual aparece en dos colores porque entre 2007 y 2016 no existe un índice nacional utilizable: el IPC provincial de San Luis lo reemplaza, entre 18% y 39% anual. El índice nacional llega a 211% en 2023 y baja a 31,5% en 2025. El peso pasa de 3,06 por dólar a fin de 2006 a 1.447 a fin de 2025, junto al dólar paralelo. La brecha entre ambos llega a 104% en 2021, durante el segundo cepo. Las reservas brutas caen a US$21.900 millones en 2023 desde US$57.000 millones en 2018.',
                en='Four panels on Argentine prices. Annual inflation is drawn in two colours because no usable national index exists for 2007 to 2016: the provincial San Luis index stands in at 18% to 39% a year. The national index peaks at 211% in 2023 and falls to 31.5% in 2025. The peso goes from 3.06 to the dollar at the end of 2006 to 1,447 at the end of 2025, drawn against the parallel blue rate. The gap between the two reaches 104% in 2021, under the second cepo. Gross reserves fall to US$21.9 billion in 2023 from US$57 billion in 2018.',
                pt='Quatro painéis sobre os preços na Argentina. A inflação anual aparece em duas cores porque entre 2007 e 2016 não existe índice nacional utilizável: o IPC provincial de San Luis o substitui, entre 18% e 39% ao ano. O índice nacional chega a 211% em 2023 e cai para 31,5% em 2025. O peso vai de 3,06 por dólar no fim de 2006 para 1.447 no fim de 2025, ao lado do dólar paralelo. O spread entre os dois chega a 104% em 2021, durante o segundo cepo. As reservas brutas caem para US$21,9 bilhões em 2023, de US$57 bilhões em 2018.'),
        },
        {
            "id": '03-living', "topic": "people", "n": '03', "family": PEOPLE,
            "title": ctx.text(es='Trabajo, salarios y quién es pobre',
                              en='Work, wages and who is poor',
                              pt='Trabalho, salários e quem é pobre'),
            "blurb": ctx.text(
                es='Desigualdad, pobreza y salario mínimo, medidos en las ciudades: la EPH releva 31 aglomerados urbanos.',
                en='Inequality, poverty and the minimum wage, measured in the cities: the EPH surveys 31 urban areas.',
                pt='Desigualdade, pobreza e salário mínimo, medidos nas cidades: a EPH pesquisa 31 aglomerados urbanos.'),
            "spark": ctx.col("social/poverty.csv", "s1"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Gini (0–1)", "es": "Gini (0–1)",
                          "pt": "Gini (0–1)"},
                         ctx.col("social/gini.csv", "indec"), "dec3"),
                ctx.stat({"en": "Poverty, first half",
                          "es": "Pobreza, primer semestre",
                          "pt": "Pobreza, primeiro semestre"},
                         ctx.col("social/poverty.csv", "s1"), "pct",
                         kind="level"),
            ],
            "alt": ctx.text(
                es='Cuatro paneles sobre el nivel de vida en la Argentina, todos de la encuesta urbana de hogares. El coeficiente de Gini, por 100, baja de 48,1 en 2006 a 41,5 en 2015 y es 42,9 en 2025. La pobreza según la canasta nacional promedia 45,5% en 2024, frente a 15,2% bajo la línea de US$8,30 diarios del Banco Mundial; la serie oficial fue retirada para 2007 a 2015. El salario mínimo al tipo de cambio oficial llega a US$603 en 2015 y es de US$269 en 2025. Por semestre, la pobreza llega a 52,9% en el primero de 2024, tras la devaluación de diciembre de 2023, y a 38,1% en el segundo.',
                en='Four panels on Argentine living standards, all from the urban household survey. The Gini coefficient, times 100, falls from 48.1 in 2006 to 41.5 in 2015 and is 42.9 in 2025. Poverty on the national basket averages 45.5% in 2024 against 15.2% below the World Bank\'s US$8.30 a day line; the official series was withdrawn for 2007 to 2015. The minimum wage at the official rate peaks at US$603 in 2015 and is US$269 in 2025. Half by half, poverty reaches 52.9% in the first half of 2024, after the December 2023 devaluation, and 38.1% in the second.',
                pt='Quatro painéis sobre o padrão de vida na Argentina, todos da pesquisa urbana de domicílios. O coeficiente de Gini, vezes 100, cai de 48,1 em 2006 para 41,5 em 2015 e é 42,9 em 2025. A pobreza pela cesta nacional tem média de 45,5% em 2024, contra 15,2% abaixo da linha de US$8,30 por dia do Banco Mundial; a série oficial foi retirada para 2007 a 2015. O salário mínimo ao câmbio oficial chega a US$603 em 2015 e é de US$269 em 2025. Semestre a semestre, a pobreza chega a 52,9% no primeiro de 2024, após a desvalorização de dezembro de 2023, e a 38,1% no segundo.'),
        },
        {
            "id": '04-state', "topic": "fiscal", "n": '04', "family": MONEY,
            "title": ctx.text(es='Lo que el Estado recauda y lo que gasta',
                              en='What the state takes and what it spends',
                              pt='O que o Estado arrecada e o que gasta'),
            "blurb": ctx.text(
                es='Gobierno general: ingresos, resultado, deuda e intereses, con el resultado primario nacional al lado.',
                en='General government revenue, balance, debt and interest, with the national primary result beside them.',
                pt='Governo geral: receita, resultado, dívida e juros, com o resultado primário nacional ao lado.'),
            "spark": ctx.col(gg, "primary_balance_pct_gdp"),
            "stats": [
                ctx.stat({"en": "Primary balance", "es": "Resultado primario",
                          "pt": "Resultado primário"},
                         ctx.col(gg, "primary_balance_pct_gdp"),
                         "pct_gdp_s"),
                ctx.stat({"en": "Gross debt", "es": "Deuda bruta",
                          "pt": "Dívida bruta"},
                         ctx.col(gg, "gross_debt_pct_gdp"), "pct_gdp",
                         kind="level"),
            ],
            "alt": ctx.text(
                es='Cuatro paneles sobre las cuentas públicas argentinas. Los ingresos del gobierno general suben de 28% a 35% del PIB hasta 2015, mientras el gasto pasa de 27% a 41,5% en 2016 y 42,5% en 2020; ambos bajan a cerca de 31% en 2024-25. El resultado total es deficitario todos los años entre 2009 y 2023, con -8,7% del PIB en 2020, y el primario pasa a un superávit de 2,2% en 2024; al lado se dibuja el resultado primario del sector público nacional en tres metodologías sin unir. La deuda bruta va de 39% del PIB en 2011 a 153% en 2023 y 80% en 2025. Los intereses netos llegan a 4,0% del PIB en 2019.',
                en='Four panels on Argentine public finances. General government revenue rises from 28% to 35% of GDP by 2015 while spending rises from 27% to 41.5% in 2016 and 42.5% in 2020, and both fall to about 31% in 2024-25. The overall balance is in deficit every year from 2009 to 2023, reaching -8.7% of GDP in 2020, and the primary balance turns to a surplus of 2.2% in 2024; the national public sector\'s own primary result is drawn beside it in three unjoined methodologies. Gross debt runs from 39% of GDP in 2011 to 153% in 2023, then 80% in 2025. Net interest peaks at 4.0% of GDP in 2019.',
                pt='Quatro painéis sobre as contas públicas argentinas. A receita do governo geral sobe de 28% para 35% do PIB até 2015, enquanto a despesa passa de 27% para 41,5% em 2016 e 42,5% em 2020; ambas caem para cerca de 31% em 2024-25. O resultado total é deficitário todos os anos de 2009 a 2023, com -8,7% do PIB em 2020, e o primário vira superávit de 2,2% em 2024; ao lado, o resultado primário do setor público nacional em três metodologias não unidas. A dívida bruta vai de 39% do PIB em 2011 a 153% em 2023 e 80% em 2025. Os juros líquidos chegam a 4,0% do PIB em 2019.'),
        },
        {
            "id": '05-trade', "topic": "trade", "n": '05', "family": WORLD,
            "title": ctx.text(es='Lo que la Argentina le vende al mundo',
                              en='What Argentina sells to the world',
                              pt='O que a Argentina vende ao mundo'),
            "blurb": ctx.text(
                es='Exportaciones e importaciones como parte del PIB, la balanza, los destinos y qué se vende.',
                en='Exports and imports as a share of GDP, the balance, the destinations and what is sold.',
                pt='Exportações e importações como parcela do PIB, a balança, os destinos e o que se vende.'),
            "spark": ctx.col("trade/trade_gns.csv", "exports_pct_gdp"),
            "stats": [
                ctx.stat({"en": "Exports, goods and services",
                          "es": "Exportaciones, bienes y servicios",
                          "pt": "Exportações, bens e serviços"},
                         ctx.col("trade/trade_gns.csv", "exports_pct_gdp"),
                         "pct_gdp"),
                ctx.stat({"en": "Goods exports", "es": "Exportaciones de bienes",
                          "pt": "Exportações de bens"},
                         ctx.col("trade/trade.csv", "exports"), "usd_bn1"),
            ],
            "alt": ctx.text(
                es='Cuatro paneles sobre el comercio exterior argentino. Las exportaciones de bienes y servicios bajan de 23% del PIB en 2006 a 10,7% en 2015 y son 15,6% en 2025; las importaciones pasan de 17% a 15%. La balanza es negativa en 2013, de 2015 a 2018 y en 2023. Brasil compra entre 14,3% y 21,2% de las exportaciones de bienes; China, Estados Unidos y Chile, entre 4% y 11% cada uno. Las exportaciones por rubro se apilan en dólares: productos primarios, manufacturas de origen agropecuario e industrial y combustibles, cuya participación baja a 3,5% en 2016 y sube a 12,7% en 2025.',
                en='Four panels on Argentine trade. Exports of goods and services fall from 23% of GDP in 2006 to 10.7% in 2015 and are 15.6% in 2025; imports move from 17% to 15%. The balance is negative in 2013, 2015 to 2018 and 2023. Brazil takes 14.3% to 21.2% of goods exports, China, the United States and Chile 4% to 11% each. Exports by category are stacked in dollars: primary products, agricultural and industrial manufactures, and fuel, whose share falls to 3.5% in 2016 and rises to 12.7% in 2025.',
                pt='Quatro painéis sobre o comércio exterior argentino. As exportações de bens e serviços caem de 23% do PIB em 2006 para 10,7% em 2015 e são 15,6% em 2025; as importações vão de 17% para 15%. A balança é negativa em 2013, de 2015 a 2018 e em 2023. O Brasil compra de 14,3% a 21,2% das exportações de bens; China, Estados Unidos e Chile, de 4% a 11% cada um. As exportações por categoria são empilhadas em dólares: produtos primários, manufaturas de origem agropecuária e industrial e combustíveis, cuja participação cai para 3,5% em 2016 e sobe para 12,7% em 2025.'),
        },
        {
            "id": '06-credit', "topic": "credit", "n": '06', "family": MONEY,
            "title": ctx.text(es='Un sistema financiero que casi no presta',
                              en='A banking system that barely lends',
                              pt='Um sistema financeiro que quase não empresta'),
            "blurb": ctx.text(
                es='Deuda de los hogares, el precio del dinero y la cartera que no se paga.',
                en='Household debt, what money costs and the loans that go bad.',
                pt='Dívida das famílias, o preço do dinheiro e os empréstimos que não são pagos.'),
            "spark": ctx.col("macro/household_credit.csv", "bis_q4_pct_gdp"),
            "stats": [
                ctx.stat({"en": "Household debt (BIS)",
                          "es": "Deuda de los hogares (BIS)",
                          "pt": "Dívida das famílias (BIS)"},
                         ctx.col("macro/household_credit.csv",
                                 "bis_q4_pct_gdp"), "pct_gdp", kind="level"),
                ctx.stat({"en": "Non-performing loans",
                          "es": "Cartera irregular", "pt": "Inadimplência"},
                         ctx.col("macro/credit_quality.csv",
                                 "npl_private_pct"), "pct2", kind="level"),
            ],
            "alt": ctx.text(
                es='Cuatro paneles sobre el crédito en la Argentina. La deuda de los hogares con todos los prestamistas nunca supera el 6,9% del PIB; el crédito hipotecario cae de 1,56% del PIB en 2007 a 0,28% en 2024. La tasa nominal de los préstamos personales va de 29% a 102% anual, frente a una tasa de política que solo existe entre 2016 y mediados de 2025. La cartera irregular privada salta de 1,54% en 2024 a 5,54% en 2025. Las tasas reales de los plazos fijos son negativas todos los años entre 2017 y 2024, con -37,1% en 2023, y el costo real de endeudarse supera el 30% en 2025.',
                en='Four panels on Argentine credit. Household debt, all lenders, never exceeds 6.9% of GDP; mortgage lending falls from 1.56% of GDP in 2007 to 0.28% in 2024. The nominal personal-loan rate runs between 29% and 102% a year against a policy rate that exists only from 2016 to mid-2025. Non-performing private loans jump from 1.54% in 2024 to 5.54% in 2025. Real deposit rates are negative every year from 2017 to 2024, reaching -37.1% in 2023, and real borrowing costs pass 30% in 2025.',
                pt='Quatro painéis sobre o crédito na Argentina. A dívida das famílias com todos os credores nunca passa de 6,9% do PIB; o crédito imobiliário cai de 1,56% do PIB em 2007 para 0,28% em 2024. A taxa nominal do crédito pessoal vai de 29% a 102% ao ano, contra uma taxa básica que só existe de 2016 a meados de 2025. A inadimplência privada salta de 1,54% em 2024 para 5,54% em 2025. Os juros reais dos depósitos a prazo são negativos todos os anos de 2017 a 2024, com -37,1% em 2023, e o custo real de tomar emprestado passa de 30% em 2025.'),
        },
        {
            "id": '07-markets', "topic": "markets", "n": '07', "family": MONEY,
            "title": ctx.text(es='Lo que el mercado le cobró a la Argentina',
                              en='What the market charged Argentina',
                              pt='O que o mercado cobrou da Argentina'),
            "blurb": ctx.text(
                es='La tasa de política, el costo de la deuda en dólares, el peso y el Merval en dólares.',
                en='The policy rate, the price of dollar debt, the peso and the Merval in dollars.',
                pt='A taxa básica, o custo da dívida em dólares, o peso e o Merval em dólares.'),
            "spark": ctx.col("markets/country_risk.csv", "avg_bp"),
            "stats": [
                ctx.stat({"en": "Country risk, EMBI+ (bp)",
                          "es": "Riesgo país, EMBI+ (pb)",
                          "pt": "Risco-país, EMBI+ (pb)"},
                         ctx.col("markets/country_risk.csv", "eop_bp"),
                         "count", kind="level"),
            ],
            "alt": ctx.text(
                es='Cuatro paneles sobre los mercados argentinos. La tasa de política del BCRA, que solo existe entre diciembre de 2015 y julio de 2025, promedia entre 26% y 100% anual frente a una inflación de 25% a 211%, con la tasa BADLAR de depósitos dibujada en todo el período como aproximación. El rendimiento de la deuda en dólares, el Tesoro de EE. UU. a 10 años más el spread EMBI+, llega a 26% en promedio en 2023. El peso oficial, como índice 2006 = 100, cae a 0,25 en 2025: compra la cuatrocientosava parte de los dólares de entonces. El Merval en dólares termina 2025 en unas tres veces su nivel de 2006; el S&P 500, en casi cinco.',
                en='Four panels on Argentine markets. The BCRA\'s policy rate, which exists only from December 2015 to July 2025, averages 26% to 100% a year against inflation of 25% to 211%, with the BADLAR deposit rate drawn across the whole window as a proxy. The yield on Argentine dollar debt, the US 10-year Treasury plus the EMBI+ spread, reaches 26% on average in 2023. The official peso, as an index of 2006 = 100, falls to 0.25 in 2025, a currency that buys a four-hundredth of the dollars it did. The Merval in dollars ends 2025 about three times its 2006 level, the S&P 500 nearly five times.',
                pt='Quatro painéis sobre os mercados argentinos. A taxa básica do BCRA, que só existe de dezembro de 2015 a julho de 2025, tem média de 26% a 100% ao ano contra inflação de 25% a 211%, com a taxa BADLAR de depósitos desenhada em todo o período como aproximação. O rendimento da dívida em dólares, o Tesouro dos EUA de 10 anos mais o spread EMBI+, chega a 26% em média em 2023. O peso oficial, como índice 2006 = 100, cai para 0,25 em 2025: compra um quatrocentos avos dos dólares de então. O Merval em dólares termina 2025 em cerca de três vezes o nível de 2006; o S&P 500, em quase cinco.'),
        },
        {
            "id": '08-people', "topic": "demography", "n": '08',
            "family": PEOPLE,
            "title": ctx.text(es='Menos nacimientos, una población que todavía crece',
                              en='Fewer births, a population still growing',
                              pt='Menos nascimentos, uma população que ainda cresce'),
            "blurb": ctx.text(
                es='Población, fecundidad y tasas de natalidad y mortalidad cada 1.000 habitantes.',
                en='Population, fertility, and birth and death rates per 1,000 people.',
                pt='População, fecundidade e taxas de natalidade e mortalidade por 1.000 habitantes.'),
            "spark": _per(ctx, "social/vitals.csv", "births", 1000),
            "stats": [
                ctx.stat({"en": "Population", "es": "Población",
                          "pt": "População"},
                         ctx.col("macro/gdp.csv", "population_mn"), "pop_mn",
                         kind="level"),
                ctx.stat({"en": "Fertility", "es": "Fecundidad",
                          "pt": "Fecundidade"},
                         ctx.col("social/demography_intl.csv", "fertility"),
                         "dec2", kind="level"),
            ],
            "alt": ctx.text(
                es='Cuatro paneles sobre la demografía argentina. La población crece de 39,1 millones en 2006 a 46,4 millones en 2025, 18,6% más. La fecundidad baja de 2,40 hijos por mujer a 1,50 en 2024, muy por debajo del umbral de reemplazo de 2,1. La tasa bruta de natalidad cae de 18 por 1.000 a 8,9 en 2024, mientras la de mortalidad sube de 7,5 a 8,1, con un pico de 9,5 en 2021 por el COVID-19. El crecimiento vegetativo cae de 451.473 nacimientos más que defunciones en 2014 a 36.730 en 2024; la migración neta es casi nula.',
                en='Four panels on Argentine demography. The population grows from 39.1 million in 2006 to 46.4 million in 2025, 18.6% more. Fertility falls from 2.40 children per woman to 1.50 in 2024, well under the 2.1 replacement line. The crude birth rate falls from 18 per 1,000 to 8.9 in 2024 while the death rate rises from 7.5 to 8.1, with a COVID-19 peak of 9.5 in 2021. Natural increase falls from 451,473 more births than deaths in 2014 to 36,730 in 2024; net migration is close to zero.',
                pt='Quatro painéis sobre a demografia argentina. A população cresce de 39,1 milhões em 2006 para 46,4 milhões em 2025, 18,6% a mais. A fecundidade cai de 2,40 filhos por mulher para 1,50 em 2024, bem abaixo da linha de reposição de 2,1. A taxa bruta de natalidade cai de 18 por 1.000 para 8,9 em 2024, enquanto a de mortalidade sobe de 7,5 para 8,1, com pico de 9,5 em 2021 pela COVID-19. O crescimento vegetativo cai de 451.473 nascimentos a mais que óbitos em 2014 para 36.730 em 2024; a migração líquida é quase nula.'),
        },
        {
            "id": '09-violence', "topic": "security", "n": '09',
            "family": PEOPLE,
            "title": ctx.text(es='Homicidio, suicidio, las rutas y el femicidio',
                              en='Homicide, suicide, the roads and femicide',
                              pt='Homicídio, suicídio, as estradas e o feminicídio'),
            "blurb": ctx.text(
                es='Muertes violentas y siniestros, cada 100.000 habitantes; el femicidio, cada 100.000 mujeres.',
                en='Violent and accidental deaths per 100,000 people; femicide per 100,000 women.',
                pt='Mortes violentas e acidentes, por 100.000 habitantes; o feminicídio, por 100.000 mulheres.'),
            "spark": ctx.col("social/homicides.csv", "rate"),
            "stats": [
                ctx.stat({"en": "Homicide rate", "es": "Tasa de homicidios",
                          "pt": "Taxa de homicídios"},
                         ctx.col("social/homicides.csv", "rate"),
                         "per100k2"),
                ctx.stat({"en": "Femicide, per 100k women",
                          "es": "Femicidio, cada 100 mil mujeres",
                          "pt": "Feminicídio, por 100 mil mulheres"},
                         ctx.col("social/femicides.csv",
                                 "rate_per_100k_women"), "dec2"),
            ],
            "alt": ctx.text(
                es='Cuatro paneles sobre la violencia letal en la Argentina, cada 100.000 habitantes. La tasa de homicidios llega a 7,62 en 2014 y baja a 3,61 en 2025, en escala logarítmica junto a la serie de la UNODC. Los suicidios registrados van de 6,3 a 8,0 cada 100.000, por debajo de la estimación estandarizada por edad de la OMS. Las muertes registradas en transporte terrestre bajan de 13,1 en 2013 a 5,2 en 2020, muy por debajo de la estimación vial de la OMS, de 13 a 15. La tasa de femicidio directo cada 100.000 mujeres ronda 1,0 a 1,14 hasta 2023 y baja a 0,85 en 2025, con un cambio de método marcado en 2017.',
                en='Four panels on lethal violence in Argentina, per 100,000 people. The homicide rate peaks at 7.62 in 2014 and falls to 3.61 in 2025, on a log scale beside UNODC\'s series. Registered suicides run at 6.3 to 8.0 per 100,000, below WHO\'s age-standardised estimate. Registered land-transport deaths fall from 13.1 in 2013 to 5.2 in 2020, well under WHO\'s road estimate of 13 to 15. The direct femicide rate per 100,000 women is near 1.0 to 1.14 until 2023 and falls to 0.85 in 2025, with a method change marked at 2017.',
                pt='Quatro painéis sobre a violência letal na Argentina, por 100.000 habitantes. A taxa de homicídios chega a 7,62 em 2014 e cai para 3,61 em 2025, em escala logarítmica ao lado da série do UNODC. Os suicídios registrados vão de 6,3 a 8,0 por 100.000, abaixo da estimativa padronizada por idade da OMS. As mortes registradas no transporte terrestre caem de 13,1 em 2013 para 5,2 em 2020, bem abaixo da estimativa viária da OMS, de 13 a 15. A taxa de feminicídio direto por 100.000 mulheres fica perto de 1,0 a 1,14 até 2023 e cai para 0,85 em 2025, com uma mudança de método marcada em 2017.'),
        },
        {
            "id": '10-spending', "topic": "spending", "n": '10',
            "family": MONEY,
            "title": ctx.text(es='Adónde va el presupuesto nacional',
                              en='Where the national budget goes',
                              pt='Para onde vai o orçamento nacional'),
            "blurb": ctx.text(
                es='Gasto nacional por finalidad, protección social e inversión, pública y de toda la economía.',
                en='National spending by function, social protection, and investment, public and whole-economy.',
                pt='Gasto nacional por função, proteção social e investimento, público e de toda a economia.'),
            "spark": ctx.col("fiscal/spending_by_function.csv", "total"),
            "stats": [
                ctx.stat({"en": "National spending", "es": "Gasto nacional",
                          "pt": "Gasto nacional"},
                         ctx.col("fiscal/spending_by_function.csv", "total"),
                         "pct_gdp"),
                ctx.stat({"en": "Investment rate", "es": "Tasa de inversión",
                          "pt": "Taxa de investimento"},
                         ctx.col("macro/economy_intl.csv", "gfcf_pct_gdp"),
                         "pct_gdp"),
            ],
            "alt": ctx.text(
                es='Cuatro paneles sobre el gasto en la Argentina. El gasto del gobierno nacional por finalidad, agrupado como la COFOG, sube de 14,5% del PIB en 2006 a 27,5% en 2020 y es 22,3% en 2023, cuando termina la serie. La protección social, jubilaciones y transferencias, pasa de 5,2% a 12,8% del PIB en 2020. La inversión de toda la economía va de 14,2% a 19,5% del PIB. La inversión directa del sector público nacional llega a 1,24% del PIB en 2009 y cae a 0,27% en 2025, en tres metodologías dibujadas por separado.',
                en='Four panels on Argentine spending. National government spending by function, grouped like COFOG, rises from 14.5% of GDP in 2006 to 27.5% in 2020 and is 22.3% in 2023, when the series ends. Social protection, pensions and transfers, goes from 5.2% to 12.8% of GDP in 2020. Whole-economy investment runs between 14.2% and 19.5% of GDP. Direct investment by the national public sector peaks at 1.24% of GDP in 2009 and falls to 0.27% in 2025, in three methodologies drawn apart.',
                pt='Quatro painéis sobre o gasto na Argentina. O gasto do governo nacional por função, agrupado como a COFOG, sobe de 14,5% do PIB em 2006 para 27,5% em 2020 e é 22,3% em 2023, quando a série termina. A proteção social, aposentadorias e transferências, vai de 5,2% para 12,8% do PIB em 2020. O investimento de toda a economia fica entre 14,2% e 19,5% do PIB. O investimento direto do setor público nacional chega a 1,24% do PIB em 2009 e cai para 0,27% em 2025, em três metodologias desenhadas separadamente.'),
        },
        {
            "id": '11-world', "topic": "world", "n": '11', "family": WORLD,
            "title": ctx.text(es='La Argentina entre los demás',
                              en='Argentina among the others',
                              pt='A Argentina entre os outros'),
            "blurb": ctx.text(
                es='PIB en dólares, desarrollo humano, percepción de la corrupción y reservas.',
                en='Dollar GDP, human development, corruption perceptions and reserves.',
                pt='PIB em dólares, desenvolvimento humano, percepção da corrupção e reservas.'),
            "spark": ctx.col("macro/world.csv", "gdp_usd_bn"),
            "stats": [
                ctx.stat({"en": "HDI", "es": "IDH", "pt": "IDH"},
                         ctx.col("social/hdi.csv", "undp"), "dec3",
                         kind="level"),
                ctx.stat({"en": "Corruption score", "es": "Puntaje de corrupción",
                          "pt": "Nota de corrupção"},
                         ctx.col("social/corruption.csv", "score"),
                         "score100", kind="level"),
            ],
            "alt": ctx.text(
                es='Cuatro paneles que ubican a la Argentina entre los demás países. El PIB a precios corrientes sube de US$233.000 millones en 2006 a US$683.000 millones en 2025, en escala logarítmica. El Índice de Desarrollo Humano sube de 0,822 a 0,865 en 2023, siempre en la franja muy alta. El puntaje de corrupción de Transparencia Internacional llega a 45 en 2019 y es 36 en 2025, puesto 104. Las reservas totales caen a un mínimo de US$23.100 millones en 2023, junto a la cifra bruta del BCRA.',
                en='Four panels placing Argentina among other countries. GDP at current prices rises from US$233 billion in 2006 to US$683 billion in 2025, on a log scale. The Human Development Index rises from 0.822 to 0.865 in 2023, in the very high band throughout. Transparency International\'s corruption score peaks at 45 in 2019 and is 36 in 2025, rank 104. Total reserves fall to a low of US$23.1 billion in 2023, drawn beside the BCRA\'s gross figure.',
                pt='Quatro painéis que situam a Argentina entre os outros países. O PIB a preços correntes sobe de US$233 bilhões em 2006 para US$683 bilhões em 2025, em escala logarítmica. O Índice de Desenvolvimento Humano sobe de 0,822 para 0,865 em 2023, sempre na faixa muito alta. A nota de corrupção da Transparência Internacional chega a 45 em 2019 e é 36 em 2025, posição 104. As reservas totais caem a um mínimo de US$23,1 bilhões em 2023, ao lado do número bruto do BCRA.'),
        },
        {
            "id": '12-mortality', "topic": "mortality", "n": '12',
            "family": PEOPLE,
            "title": ctx.text(es='Un año malo de muertes',
                              en='One bad year of deaths',
                              pt='Um ano ruim de mortes'),
            "blurb": ctx.text(
                es='Mortalidad, exceso de muertes, COVID-19 y neumonía, cada 1.000 y cada 100.000 habitantes.',
                en='The death rate, excess deaths, COVID-19 and pneumonia, per 1,000 and per 100,000 people.',
                pt='Mortalidade, excesso de mortes, COVID-19 e pneumonia, por 1.000 e por 100.000 habitantes.'),
            "spark": _per(ctx, "social/causes.csv", "deaths_total", 1000),
            "stats": [
                ctx.stat({"en": "COVID-19, per 100k, peak year",
                          "es": "COVID-19, cada 100 mil, año pico",
                          "pt": "COVID-19, por 100 mil, ano de pico"},
                         _per(ctx, "social/causes.csv", "covid", 1e5),
                         "per100k", year=2021),
            ],
            "alt": ctx.text(
                es='Cuatro paneles sobre la mortalidad en la Argentina. La tasa bruta de mortalidad ronda 7,5 cada 1.000 habitantes y llega a 9,5 en 2021, con 436.799 muertes. Frente al promedio 2015-2019, de 341.328, hubo 10,2% más muertes en 2020 y 28,0% más en 2021. Las muertes por COVID-19 son 117 cada 100.000 en 2020 y 185 en 2021, 164.785 en total, confirmadas y probables juntas. La neumonía mata entre 40 y 87 personas cada 100.000 por año; la gripe casi no aparece, porque una gripe fatal se certifica como neumonía.',
                en='Four panels on Argentine mortality. The crude death rate runs near 7.5 per 1,000 people and peaks at 9.5 in 2021, 436,799 deaths. Against the 2015-2019 average of 341,328, deaths were 10.2% higher in 2020 and 28.0% higher in 2021. COVID-19 deaths are 117 per 100,000 in 2020 and 185 in 2021, 164,785 in all, confirmed and probable together. Pneumonia kills 40 to 87 per 100,000 a year; influenza barely appears, because a fatal flu is certified as pneumonia.',
                pt='Quatro painéis sobre a mortalidade na Argentina. A taxa bruta de mortalidade fica perto de 7,5 por 1.000 habitantes e chega a 9,5 em 2021, com 436.799 mortes. Contra a média de 2015-2019, de 341.328, houve 10,2% mais mortes em 2020 e 28,0% mais em 2021. As mortes por COVID-19 são 117 por 100.000 em 2020 e 185 em 2021, 164.785 no total, confirmadas e prováveis juntas. A pneumonia mata de 40 a 87 pessoas por 100.000 ao ano; a gripe quase não aparece, porque uma gripe fatal é certificada como pneumonia.'),
        },
        {
            "id": "13-migration", "topic": "migration", "n": "13", "family": PEOPLE,
            "title": ctx.text(es="Migración, sin confundir viajes con personas",
                              en="Migration, without confusing trips with people",
                              pt="Migração, sem confundir viagens com pessoas"),
            "blurb": ctx.text(es="Migración neta modelada, población nacida en otro país y principales orígenes; los flujos brutos siguen pendientes.",
                              en="Modelled net migration, the foreign-born census stock and leading origins; gross resident flows remain pending.",
                              pt="Migração líquida modelada, população nascida no exterior e principais origens; os fluxos brutos seguem pendentes."),
            "spark": ctx.col("migration/foreign_born_census.csv", "foreign_born_pct"),
            "spark_level": True,
            "stats": [ctx.stat({"es": "Nacidos en otro país", "en": "Foreign-born", "pt": "Nascidos no exterior"},
                               ctx.col("migration/foreign_born_census.csv", "foreign_born_pct"), "pct", kind="level")],
            "alt": ctx.text(es="Los flujos brutos de residentes están pendientes porque los movimientos de frontera cuentan viajes y las residencias cuentan decisiones. La migración neta modelada de la ONU se muestra cada mil habitantes. Los censos del INDEC muestran 4,5% de nacidos en otro país en 2010 y 4,2% en 2022, con Paraguay, Bolivia y Venezuela como los orígenes mostrados.",
                            en="Gross resident flows remain pending because border movements count trips and residence grants count decisions. UN modelled net migration is shown per 1,000. INDEC censuses show 4.5% foreign-born in 2010 and 4.2% in 2022, with Paraguay, Bolivia and Venezuela as the origins shown.",
                            pt="Os fluxos brutos de residentes seguem pendentes porque movimentos de fronteira contam viagens e residências contam decisões. A migração líquida modelada da ONU aparece por mil habitantes. Os censos do INDEC mostram 4,5% de nascidos no exterior em 2010 e 4,2% em 2022, com Paraguai, Bolívia e Venezuela como as origens mostradas."),
        },
    ]
