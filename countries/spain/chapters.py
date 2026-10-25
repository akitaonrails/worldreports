"""The spain chapters: the cards, their copy and their headline figures.

Editorial copy lives here. Every number is read from this country's CSVs at
build time by the context, so a figure on a card and the same figure on its
plate cannot disagree.

Twelve chapters, on the shared spine. `kind` says whether a figure is
current: 'flow' for an annual total, 'level' for a stock or a rate read at
a moment.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def headline(ctx) -> list[dict]:
    """The figures the page leads with, above the plates."""
    return [
        ctx.stat({"en": "GDP", "es": "PIB", "pt": "PIB"},
                 ctx.col("macro/gdp.csv", "nominal_eurbn"), "money_bn"),
        ctx.stat({"en": "GDP per person, US$", "es": "PIB por persona, US$",
                  "pt": "PIB por pessoa, US$"},
                 ctx.col("macro/gdp.csv", "gdp_per_capita_usd"), "count"),
        ctx.stat({"en": "Population", "es": "Población", "pt": "População"},
                 [(y, v / 1e6) for y, v in
                  ctx.col("social/population.csv", "population")],
                 "pop_mn", kind="level"),
        ctx.stat({"en": "Unemployment (EPA)", "es": "Paro (EPA)",
                  "pt": "Desemprego (EPA)"},
                 ctx.col("macro/unemployment.csv", "epa"), "pct"),
        ctx.stat({"en": "Public debt (Maastricht)",
                  "es": "Deuda pública (Maastricht)",
                  "pt": "Dívida pública (Maastricht)"},
                 ctx.col("fiscal/debt.csv", "gross_pct_gdp"), "pct_gdp",
                 kind="level"),
        ctx.stat({"en": "Immigration (EMCR)",
                  "es": "Inmigración (EMCR)", "pt": "Imigração (EMCR)"},
                 ctx.col("migration/migration_flows_emcr_ine.csv",
                         "immigration_emcr"), "count"),
        ctx.stat({"en": "Policy rate (ECB, deposit facility)",
                  "es": "Tipo oficial (BCE, facilidad de depósito)",
                  "pt": "Taxa oficial (BCE, facilidade de depósito)"},
                 ctx.col("markets/policy_rate.csv", "dfr"), "pct2",
                 kind="level"),
    ]


def build(ctx) -> list[dict]:
    chapters = [
        {
            "id": "01-economy", "topic": "economy", "n": "01",
            "family": MONEY,
            "title": ctx.text(en="The Economy", es="La economía",
                              pt="A economia"),
            "blurb": ctx.text(
                en="A €1.7 trillion economy that fell twice before COVID — "
                   "2008-09 and the 2011-13 double dip — fell hardest of all "
                   "in 2020, and has outgrown the euro area since; "
                   "unemployment peaked at one worker in four.",
                es="Una economía de 1,7 billones de euros que cayó dos "
                   "veces antes de la COVID — 2008-09 y la doble caída de "
                   "2011-13 —, cayó más que ninguna en 2020 y desde entonces "
                   "crece más que la eurozona; el paro llegó a uno de cada "
                   "cuatro activos.",
                pt="Uma economia de € 1,7 trilhão que caiu duas vezes antes "
                   "da COVID — 2008-09 e o duplo mergulho de 2011-13 —, caiu "
                   "mais que todas em 2020 e desde então cresce mais que a "
                   "zona do euro; o desemprego chegou a um trabalhador em "
                   "cada quatro."),
            "spark": ctx.col("macro/gdp.csv", "real_growth"),
            "stats": [
                ctx.stat({"en": "GDP", "es": "PIB", "pt": "PIB"},
                         ctx.col("macro/gdp.csv", "nominal_eurbn"),
                         "money_bn"),
                ctx.stat({"en": "Real growth", "es": "Crecimiento real",
                          "pt": "Crescimento real"},
                         ctx.col("macro/gdp.csv", "real_growth"), "pct_s"),
                ctx.stat({"en": "Inflation (IPC)", "es": "Inflación (IPC)",
                          "pt": "Inflação (IPC)"},
                         ctx.col("macro/inflation.csv", "ipc"), "pct"),
                ctx.stat({"en": "Unemployment (EPA)", "es": "Paro (EPA)",
                          "pt": "Desemprego (EPA)"},
                         ctx.col("macro/unemployment.csv", "epa"), "pct"),
            ],
        },
        {
            "id": "02-fiscal", "topic": "fiscal", "n": "02",
            "family": MONEY,
            "title": ctx.text(en="The Public Books",
                              es="Las cuentas públicas",
                              pt="As contas públicas"),
            "blurb": ctx.text(
                en="Small surpluses in 2006-07, then a deficit every year "
                   "since; 2012 carries the bank bailout inside it. The "
                   "debt nearly tripled while the interest bill fell back "
                   "from its 2013 peak.",
                es="Pequeños superávits en 2006-07 y déficit todos los años "
                   "desde entonces; 2012 lleva dentro el rescate bancario. "
                   "La deuda casi se triplicó mientras la factura de "
                   "intereses bajaba desde su máximo de 2013.",
                pt="Pequenos superávits em 2006-07 e déficit todos os anos "
                   "desde então; 2012 carrega o resgate bancário. A dívida "
                   "quase triplicou enquanto a fatura de juros recuava do "
                   "pico de 2013."),
            "spark": ctx.col("fiscal/deficit.csv", "deficit"),
            "stats": [
                ctx.stat({"en": "Balance", "es": "Saldo", "pt": "Saldo"},
                         ctx.col("fiscal/deficit.csv", "deficit"),
                         "pct_gdp_s"),
                ctx.stat({"en": "Gross debt", "es": "Deuda bruta",
                          "pt": "Dívida bruta"},
                         ctx.col("fiscal/debt.csv", "gross_pct_gdp"),
                         "pct_gdp", kind="level"),
                ctx.stat({"en": "Interest paid", "es": "Intereses pagados",
                          "pt": "Juros pagos"},
                         ctx.col("fiscal/deficit.csv", "interest"),
                         "pct_gdp"),
            ],
        },
        {
            "id": "03-spending", "topic": "spending", "n": "03",
            "family": MONEY,
            "title": ctx.text(en="Where the Money Goes",
                              es="Adónde va el dinero",
                              pt="Para onde vai o dinheiro"),
            "blurb": ctx.text(
                en="Social protection alone outweighs every other function "
                   "combined — and its 2012-13 peak is unemployment, not "
                   "largesse.",
                es="La protección social por sí sola supera a todas las "
                   "demás funciones juntas — y su pico de 2012-13 es paro, "
                   "no generosidad.",
                pt="A proteção social sozinha supera todas as demais "
                   "funções somadas — e seu pico de 2012-13 é desemprego, "
                   "não generosidade."),
            "spark": ctx.col("fiscal/spending_by_function.csv",
                             "social_protection"),
            "stats": [
                ctx.stat({"en": "Social protection",
                          "es": "Protección social",
                          "pt": "Proteção social"},
                         ctx.col("fiscal/spending_by_function.csv",
                                 "social_protection"), "pct_gdp"),
                ctx.stat({"en": "Health", "es": "Sanidad", "pt": "Saúde"},
                         ctx.col("fiscal/spending_by_function.csv",
                                 "health"), "pct_gdp"),
                ctx.stat({"en": "Education", "es": "Educación",
                          "pt": "Educação"},
                         ctx.col("fiscal/spending_by_function.csv",
                                 "education"), "pct_gdp"),
            ],
        },
        {
            "id": "04-trade", "topic": "trade", "n": "04",
            "family": WORLD,
            "title": ctx.text(en="Foreign Trade", es="Comercio exterior",
                              pt="Comércio exterior"),
            "blurb": ctx.text(
                en="In surplus every year since 2011 — a services surplus, "
                   "tourism mostly, over a goods deficit. France still "
                   "takes one goods export in seven, and food now outsells "
                   "cars.",
                es="En superávit todos los años desde 2011: un superávit de "
                   "servicios, sobre todo turismo, sobre un déficit de "
                   "bienes. Francia aún recibe una de cada siete "
                   "exportaciones de bienes y los alimentos ya venden más "
                   "que los coches.",
                pt="Em superávit todos os anos desde 2011: um superávit de "
                   "serviços, sobretudo turismo, sobre um déficit de bens. "
                   "A França ainda recebe uma em cada sete exportações de "
                   "bens, e os alimentos já vendem mais que os carros."),
            "spark": ctx.col("trade/trade.csv", "exports_eurbn"),
            "stats": [
                ctx.stat({"en": "Exports", "es": "Exportaciones",
                          "pt": "Exportações"},
                         ctx.col("trade/trade.csv", "exports_eurbn"),
                         "money_bn"),
                ctx.stat({"en": "Imports", "es": "Importaciones",
                          "pt": "Importações"},
                         ctx.col("trade/trade.csv", "imports_eurbn"),
                         "money_bn"),
                ctx.stat({"en": "Openness", "es": "Apertura",
                          "pt": "Abertura"},
                         ctx.col("international/openness.csv",
                                 "trade_pct_gdp"), "pct_gdp"),
            ],
        },
        {
            "id": "05-markets", "topic": "markets", "n": "05",
            "family": MONEY,
            "title": ctx.text(en="Money & Markets", es="Dinero y mercados",
                              pt="Moeda e mercados"),
            "blurb": ctx.text(
                en="The policy rate is set in Frankfurt: eight years below "
                   "zero, then the fastest hikes in the euro's history. The "
                   "2012 yield spike is the euro crisis in one number.",
                es="El tipo oficial se decide en Fráncfort: ocho años bajo "
                   "cero y después las subidas más rápidas de la historia "
                   "del euro. El pico del bono en 2012 es la crisis del "
                   "euro en un número.",
                pt="A taxa oficial é decidida em Frankfurt: oito anos "
                   "abaixo de zero e depois as altas mais rápidas da "
                   "história do euro. O pico do juro em 2012 é a crise do "
                   "euro em um número."),
            "spark": ctx.col("markets/policy_rate.csv", "dfr"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Deposit facility, year-end",
                          "es": "Facilidad de depósito, fin de año",
                          "pt": "Facilidade de depósito, fim de ano"},
                         ctx.col("markets/policy_rate.csv", "dfr"),
                         "pct2", kind="level"),
                ctx.stat({"en": "10-year yield", "es": "Bono a 10 años",
                          "pt": "Título de 10 anos"},
                         ctx.col("markets/yield_10y.csv", "yield_10y"),
                         "pct2"),
                ctx.stat({"en": "IBEX 35 close",
                          "es": "Cierre del IBEX 35",
                          "pt": "Fechamento do IBEX 35"},
                         ctx.col("markets/ibex.csv", "close"), "index",
                         kind="level"),
            ],
        },
        {
            "id": "06-people", "topic": "people", "n": "06",
            "family": PEOPLE,
            "title": ctx.text(en="People", es="Las personas",
                              pt="As pessoas"),
            "blurb": ctx.text(
                en="One person in five below the relative poverty line "
                   "through boom and bust, a minimum wage that doubled in "
                   "euros, and the jobs the slump destroyed, rebuilt.",
                es="Una persona de cada cinco bajo el umbral relativo de "
                   "pobreza en la bonanza y en la crisis, un salario mínimo "
                   "que se duplicó en euros y el empleo que destruyó la "
                   "crisis, reconstruido.",
                pt="Uma pessoa em cada cinco abaixo da linha relativa de "
                   "pobreza na bonança e na crise, um salário mínimo que "
                   "dobrou em euros e os empregos que a crise destruiu, "
                   "reconstruídos."),
            "spark": ctx.col("social/poverty.csv", "arop60"),
            "stats": [
                ctx.stat({"en": "Minimum wage, € a month (×12)",
                          "es": "Salario mínimo, € al mes (×12)",
                          "pt": "Salário mínimo, € por mês (×12)"},
                         ctx.col("social/minimum_wage.csv", "eur_month_jul"),
                         "count", kind="level"),
                ctx.stat({"en": "Employment", "es": "Ocupación",
                          "pt": "Emprego"},
                         [(y, v / 1000) for y, v in
                          ctx.col("macro/employment.csv",
                                  "employed_thousands_avg")], "pop_mn"),
                ctx.stat({"en": "At risk of poverty",
                          "es": "Riesgo de pobreza",
                          "pt": "Risco de pobreza"},
                         ctx.col("social/poverty.csv", "arop60"), "pct"),
            ],
        },
        {
            "id": "07-world", "topic": "world", "n": "07",
            "family": WORLD,
            "title": ctx.text(en="Spain in the World",
                              es="España en el mundo",
                              pt="A Espanha no mundo"),
            "blurb": ctx.text(
                en="The comparables layer: GDP in dollars moves with the "
                   "euro as much as with Spain, the corruption score is the "
                   "lowest on TI's current method, and the reserves are "
                   "small because the euro area's buffer sits at the ECB.",
                es="La capa de comparables: el PIB en dólares se mueve con "
                   "el euro tanto como con España, la puntuación de "
                   "corrupción es la peor con el método actual de TI y las "
                   "reservas son pequeñas porque el colchón de la eurozona "
                   "está en el BCE.",
                pt="A camada de comparáveis: o PIB em dólares se move com "
                   "o euro tanto quanto com a Espanha, a pontuação de "
                   "corrupção é a pior no método atual da TI e as reservas "
                   "são pequenas porque o colchão da zona do euro está no "
                   "BCE."),
            "spark": ctx.col("international/hdi.csv", "hdi"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "GDP per person, US$",
                          "es": "PIB por persona, US$",
                          "pt": "PIB por pessoa, US$"},
                         ctx.col("macro/gdp.csv", "gdp_per_capita_usd"),
                         "count"),
                ctx.stat({"en": "HDI", "es": "IDH", "pt": "IDH"},
                         ctx.col("international/hdi.csv", "hdi"), "dec3",
                         kind="level"),
                ctx.stat({"en": "Corruption Perceptions Index",
                          "es": "Índice de Percepción de la Corrupción",
                          "pt": "Índice de Percepção da Corrupção"},
                         ctx.col("international/cpi.csv", "score"), "count",
                         kind="level"),
                ctx.stat({"en": "Reserves incl. gold",
                          "es": "Reservas incl. oro",
                          "pt": "Reservas incl. ouro"},
                         [(y, v / 1e9) for y, v in
                          ctx.col("international/reserves.csv",
                                  "reserves_usd")], "usd_bn", kind="level"),
            ],
        },
        {
            "id": "08-demography", "topic": "demography", "n": "08",
            "family": PEOPLE,
            "title": ctx.text(en="Demography", es="Demografía",
                              pt="Demografia"),
            "blurb": ctx.text(
                en="Deaths overtook births in 2015 and never gave the lead "
                   "back; the population grows on migration alone, and "
                   "fertility is among the lowest ever recorded in Europe.",
                es="Las defunciones superaron a los nacimientos en 2015 y "
                   "nunca devolvieron la delantera; la población crece solo "
                   "por la migración y la fecundidad está entre las más "
                   "bajas jamás registradas en Europa.",
                pt="Os óbitos superaram os nascimentos em 2015 e nunca "
                   "devolveram a liderança; a população cresce só pela "
                   "migração e a fecundidade está entre as mais baixas já "
                   "registradas na Europa."),
            "spark": ctx.col("social/population.csv", "population"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Population, 1 Jan", "es": "Población, 1 ene.",
                          "pt": "População, 1º jan."},
                         [(y, v / 1e6) for y, v in
                          ctx.col("social/population.csv", "population")],
                         "pop_mn", kind="level"),
                ctx.stat({"en": "Fertility rate", "es": "Fecundidad",
                          "pt": "Fecundidade"},
                         ctx.col("social/demography.csv", "tfr"), "dec2"),
                ctx.stat({"en": "Births", "es": "Nacimientos",
                          "pt": "Nascimentos"},
                         ctx.col("social/demography.csv", "births"),
                         "count"),
            ],
        },
        {
            "id": "09-security", "topic": "security", "n": "09",
            "family": PEOPLE,
            "title": ctx.text(en="Security", es="Seguridad",
                              pt="Segurança"),
            "blurb": ctx.text(
                en="One of Europe's lowest homicide rates, on the death "
                   "certificates; suicide is the largest violent death, and "
                   "road deaths fell by more than half. The police count "
                   "is pending — the ministry's portal blocks automated "
                   "access.",
                es="Una de las tasas de homicidio más bajas de Europa, "
                   "según los certificados de defunción; el suicidio es la "
                   "primera muerte violenta y los muertos en carretera se "
                   "redujeron a menos de la mitad. El cómputo policial está "
                   "pendiente: el portal del ministerio bloquea el acceso "
                   "automatizado.",
                pt="Uma das taxas de homicídio mais baixas da Europa, "
                   "segundo as certidões de óbito; o suicídio é a principal "
                   "morte violenta e as mortes no trânsito caíram a menos "
                   "da metade. A contagem policial está pendente: o portal "
                   "do ministério bloqueia o acesso automatizado."),
            "spark": ctx.col("social/homicides.csv", "ecm_deaths"),
            "stats": [
                ctx.stat({"en": "Homicides (death certificates)",
                          "es": "Homicidios (certificados)",
                          "pt": "Homicídios (certidões)"},
                         ctx.col("social/homicides.csv", "ecm_deaths"),
                         "count"),
                ctx.stat({"en": "Suicides", "es": "Suicidios",
                          "pt": "Suicídios"},
                         [(y, v) for y, v in
                          _cause_col(ctx, "Suicidio y lesiones "
                                     "autoinfligidas")], "count"),
                ctx.stat({"en": "Road deaths", "es": "Muertos en la carretera",
                          "pt": "Mortes no trânsito"},
                         [(y, v) for y, v in
                          _cause_col(ctx, "Accidentes de tráfico")], "count"),
            ],
        },
        {
            "id": "10-mortality", "topic": "mortality", "n": "10",
            "family": PEOPLE,
            "title": ctx.text(en="Mortality", es="Mortalidad",
                              pt="Mortalidade"),
            "blurb": ctx.text(
                en="Cancer and the heart trade the lead — cancer only "
                   "pulled ahead in 2024 — and 2020 broke every trend on "
                   "the plate.",
                es="El cáncer y el corazón se turnan al frente — el cáncer "
                   "solo se adelantó en 2024 — y 2020 rompió todas las "
                   "tendencias de la plancha.",
                pt="Câncer e coração trocam a liderança — o câncer só "
                   "passou à frente em 2024 — e 2020 quebrou todas as "
                   "tendências da prancha."),
            "spark": ctx.col("social/demography.csv", "deaths"),
            "stats": [
                ctx.stat({"en": "Deaths", "es": "Defunciones",
                          "pt": "Óbitos"},
                         ctx.col("social/demography.csv", "deaths"),
                         "count"),
                ctx.stat({"en": "COVID-19 deaths 2020–24, certified",
                          "es": "Defunciones COVID-19 2020–24, certificadas",
                          "pt": "Óbitos de COVID-19 2020–24, certificados"},
                         [(y, v) for y, v in
                          _cause_col(ctx, "COVID-19. Virus identificado")],
                         "count", kind="total"),
                ctx.stat({"en": "Tumour deaths",
                          "es": "Defunciones por tumores",
                          "pt": "Óbitos por tumores"},
                         [(y, v) for y, v in _cause_col(ctx, "II.Tumores")],
                         "count"),
            ],
        },
        {
            "id": "11-credit", "topic": "credit", "n": "11",
            "family": MONEY,
            "title": ctx.text(en="Credit", es="Crédito", pt="Crédito"),
            "blurb": ctx.text(
                en="Variable-rate country: the 2022-23 shock hit the "
                   "mortgage stock itself. Households deleveraged from 141% "
                   "of disposable income to 75%.",
                es="El país del tipo variable: el shock de 2022-23 golpeó "
                   "al propio stock hipotecario. Los hogares se "
                   "desapalancaron del 141% de la renta disponible al 75%.",
                pt="O país da taxa variável: o choque de 2022-23 atingiu o "
                   "próprio estoque hipotecário. As famílias se "
                   "desalavancaram de 141% da renda disponível para 75%."),
            "spark": ctx.col("credit/household_debt.csv",
                             "debt_pct_income_avg"),
            "stats": [
                ctx.stat({"en": "Household debt / income",
                          "es": "Deuda de hogares / renta",
                          "pt": "Dívida das famílias / renda"},
                         ctx.col("credit/household_debt.csv",
                                 "debt_pct_income_avg"), "pct"),
                ctx.stat({"en": "Doubtful loans (Dec)",
                          "es": "Créditos dudosos (dic.)",
                          "pt": "Créditos duvidosos (dez.)"},
                         ctx.col("credit/npl.csv", "npl_ratio"), "pct",
                         kind="level"),
                ctx.stat({"en": "Euribor 12m", "es": "Euríbor 12m",
                          "pt": "Euribor 12m"},
                         ctx.col("credit/lending_rates.csv", "euribor_12m"),
                         "pct2"),
            ],
        },
        {
            "id": "12-migration", "topic": "migration", "n": "12",
            "family": PEOPLE,
            "title": ctx.text(en="Migration", es="Migración",
                              pt="Migração"),
            "blurb": ctx.text(
                en="Arrivals at record levels on the new methodology — and "
                   "the 2021 seam where the measurement changed is drawn as "
                   "a seam, never as a trend.",
                es="Llegadas en niveles récord con la nueva metodología — "
                   "y la costura de 2021, donde cambió la medición, se "
                   "dibuja como costura, nunca como tendencia.",
                pt="Chegadas em níveis recorde na nova metodologia — e a "
                   "emenda de 2021, onde a medição mudou, é desenhada como "
                   "emenda, nunca como tendência."),
            "spark": ctx.col("migration/migration_flows_emcr_ine.csv",
                             "immigration_emcr"),
            "stats": [
                ctx.stat({"en": "Immigration (EMCR)",
                          "es": "Inmigración (EMCR)",
                          "pt": "Imigração (EMCR)"},
                         ctx.col("migration/migration_flows_emcr_ine.csv",
                                 "immigration_emcr"), "count"),
                ctx.stat({"en": "Foreign-born residents, 1 Jan",
                          "es": "Residentes nacidos fuera, 1 ene.",
                          "pt": "Residentes nascidos fora, 1º jan."},
                         [(y, v / 1e6) for y, v in
                          _foreign_born(ctx)], "pop_mn", kind="level"),
                ctx.stat({"en": "Naturalisations",
                          "es": "Nacionalizaciones",
                          "pt": "Naturalizações"},
                         ctx.col("migration/naturalisation.csv",
                                 "acquisitions"), "count"),
            ],
        },
    ]
    return chapters


def _cause_col(ctx, cause: str):
    """(year, deaths) pairs for one cause out of the long-format ECM file."""
    t = ctx.c.table("social/causes_of_death.csv")
    if not t:
        return []
    out = [(int(y), float(v)) for y, c, v in zip(t["year"], t["cause"],
                                                 t["deaths"])
           if c == cause and v == v]
    return sorted(out)


def _foreign_born(ctx):
    """Foreign-born residents = the stock total minus those born in Spain."""
    t = ctx.c.table("migration/stock.csv")
    if not t:
        return []
    out = []
    for y, tot, nat in zip(t["year"], t["by_birth_total"],
                           t["by_birth_national"]):
        if tot == tot and nat == nat:
            out.append((int(y), tot - nat))
    return sorted(out)
