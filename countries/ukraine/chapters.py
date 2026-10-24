"""Ukraine's four page cards, computed from reviewed publication CSVs."""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def _scaled(ctx, path, column, divisor):
    return [(y, v / divisor) for y, v in ctx.col(path, column)]


def headline(ctx):
    T = ctx.text
    return [
        ctx.stat(T(uk="Темп зростання ВВП", en="Real GDP growth",
                   pt="Crescimento real do PIB"),
                 ctx.col("macro/gdp_growth_imf.csv", "gdp_growth_pct"),
                 "pct_s"),
        ctx.stat(T(uk="ВВП на особу, доларів", en="GDP per person, US$",
                   pt="PIB por pessoa, US$"),
                 ctx.col("world/gdp_per_person.csv", "gdp_per_person_usd"),
                 "count"),
        ctx.stat(T(uk="Інфляція", en="Inflation", pt="Inflação"),
                 ctx.col("macro/economy.csv", "cpi_inflation_pct"), "pct"),
        ctx.stat(T(uk="ВВП, млрд доларів", en="GDP, US$ bn",
                   pt="PIB, US$ bi"),
                 _scaled(ctx, "world/gdp_usd.csv", "gdp_usd", 1e9),
                 "usd_bn", kind="level"),
        ctx.stat(T(uk="Населення, млн", en="Population, million",
                   pt="População, milhões"),
                 _scaled(ctx, "demography/population.csv", "population", 1e6),
                 "pop_mn", kind="level"),
        ctx.stat(T(uk="Резерви, млрд доларів", en="Reserves, US$ bn",
                   pt="Reservas, US$ bi"),
                 _scaled(ctx, "world/reserves.csv", "reserves_usd", 1e9),
                 "usd_bn", kind="level"),
    ]


def build(ctx):
    T = ctx.text
    specs = [
        ("01-economy", "economy", MONEY,
         T(uk="Економіка", en="The Economy", pt="A Economia"),
         T(uk="Зростання, дохід, ціни й зайнятість у порівнянних рядах Світового банку та МВФ.",
           en="Growth, income, prices and jobs in comparable World Bank and IMF series.",
           pt="Crescimento, renda, preços e emprego em séries comparáveis do Banco Mundial e do FMI."),
         T(uk="Чотири панелі за 2006–2025 роки. ВВП скоротився на 28,8% у 2022 році — найглибше падіння за весь період; інфляція сягнула 48,7% у 2015 році; безробіття обірвалося на 2021 році.",
           en="Four panels for 2006–2025. GDP fell 28.8% in 2022 — the deepest drop of the window; inflation reached 48.7% in 2015; the unemployment series stops in 2021.",
           pt="Quatro painéis para 2006–2025. O PIB caiu 28,8% em 2022 — a maior queda do período; a inflação chegou a 48,7% em 2015; a série de desemprego termina em 2021."),
         "macro/economy.csv", "cpi_inflation_pct", "pct",
         ["macro/economy.csv", "macro/gdp_growth_imf.csv",
          "world/gdp_per_person.csv"]),
        ("02-world", "world", WORLD,
         T(uk="Україна у світі", en="Ukraine in the World",
           pt="Ucrânia no Mundo"),
         T(uk="Розмір економіки й резерви в доларах та індекс людського розвитку — за міжнародними визначеннями.",
           en="Economic size and reserves in US dollars and human development on international definitions.",
           pt="Tamanho econômico e reservas em dólares e desenvolvimento humano em definições internacionais."),
         T(uk="Чотири панелі. Номінальний ВВП у доларах упав до 162 млрд у 2022 році й відновився до 214 млрд у 2025-му; резерви зросли до 57 млрд; індекс людського розвитку за 2023 рік — 0,779; індекс сприйняття корупції лишається відсутнім.",
           en="Four panels. Nominal GDP in dollars fell to US$162bn in 2022 and recovered to US$214bn in 2025; reserves rose to US$57bn; the 2023 HDI is 0.779; the corruption index remains unavailable.",
           pt="Quatro painéis. O PIB nominal em dólares caiu para US$162 bi em 2022 e recuperou-se para US$214 bi em 2025; as reservas subiram para US$57 bi; o IDH de 2023 é 0,779; o índice de corrupção segue indisponível."),
         "world/gdp_usd.csv", "gdp_usd", "usd_bn",
         ["world/gdp_usd.csv", "world/hdi.csv", "world/reserves.csv"]),
        ("03-demography", "demography", PEOPLE,
         T(uk="Демографія", en="Demography", pt="Demografia"),
         T(uk="Національний реєстр і міжнародна оцінка — дві різні території, дві окремі лінії.",
           en="The national register and the international estimate — two different perimeters, two separate lines.",
           pt="O registro nacional e a estimativa internacional — dois perímetros diferentes, duas linhas separadas."),
         T(uk="Чотири панелі. Реєстр Укрстату падає з 46,9 млн у 2006 році до 41,2 млн у 2022-му, і стрибок 2015 року — це виключення окупованих територій, а не демографічна подія; оцінка ООН включає Крим і сягає 39,0 млн у 2025 році; народжуваність, смертність і міграція лишаються відсутніми.",
           en="Four panels. The Ukrstat register falls from 46.9m in 2006 to 41.2m in 2022, and the 2015 step is the exclusion of the occupied territories, not a demographic event; the UN estimate includes Crimea and reaches 39.0m in 2025; births, deaths and migration remain unavailable.",
           pt="Quatro painéis. O registro do Ukrstat cai de 46,9 milhões em 2006 para 41,2 milhões em 2022, e o degrau de 2015 é a exclusão dos territórios ocupados, não um evento demográfico; a estimativa da ONU inclui a Crimeia e chega a 39,0 milhões em 2025; natalidade, mortalidade e migração seguem indisponíveis."),
         "demography/population_ukrstat.csv", "population", "pop_mn",
         ["demography/population.csv", "demography/population_ukrstat.csv"]),
        ("04-people", "people", PEOPLE,
         T(uk="Люди й ціни", en="People & Prices", pt="Pessoas e Preços"),
         T(uk="Нерівність до війни та купівельна спроможність гривні — два різні питання.",
           en="Inequality before the war and what the hryvnia buys — two different questions.",
           pt="Desigualdade antes da guerra e o que a hryvnia compra — duas questões diferentes."),
         T(uk="Чотири панелі. Джині коливається від 29,8 у 2006 році до 25,6 у 2020-му, і обстеження домогосподарств на цьому спинилося; рівень цін, нанизаний з річної інфляції, зріс у 10,1 раза за 2006–2025 роки; бідність і мінімальна зарплата лишаються відсутніми.",
           en="Four panels. The Gini moves from 29.8 in 2006 to 25.6 in 2020, where the household survey stops; the price level chained from annual inflation rose 10.1 times over 2006–2025; poverty and the minimum wage remain unavailable.",
           pt="Quatro painéis. O Gini vai de 29,8 em 2006 a 25,6 em 2020, onde o inquérito domiciliar para; o nível de preços encadeado pela inflação anual subiu 10,1 vezes entre 2006 e 2025; pobreza e salário mínimo seguem indisponíveis."),
         "people/gini.csv", "gini", "dec2",
         ["people/gini.csv", "macro/economy.csv"]),
    ]
    out = []
    for ident, topic, family, title, blurb, alt, path, column, fmt, sources in specs:
        pairs = ctx.col(path, column)
        out.append({"id": ident, "topic": topic, "n": ident[:2], "family": family,
                    "title": title, "blurb": blurb, "alt": alt, "spark": pairs,
                    "stats": [ctx.stat(title, pairs, fmt)],
                    "sources": sources})
    return out
