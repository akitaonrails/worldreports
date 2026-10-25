"""The Russia chapters: the cards, their copy and their headline figures.

Editorial copy lives here. Every number on a card is read from this
country's CSVs at build time, so a figure on a card and the same figure on
its plate cannot disagree.

Twelve chapters, one per spine topic. The headline strip leads with the
three readings every country carries — GDP, GDP per person, population —
and then the four numbers Russia's own argument is about: the key rate, the
December-to-December CPI, the federal balance and the national poverty
line.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def _nominal_gdp(ctx):
    """Rosstat's nominal GDP in billion roubles, one vintage."""
    return dict(ctx.col("macro/gdp.csv", "nominal_bn_rub"))


def _federal_balance(ctx):
    """The federal balance as % of GDP — Minfin's roubles over Rosstat's GDP.

    The same derivation the fiscal plate draws, and the same perimeter
    caveat: it is the federal budget, not general government.
    """
    gdp = _nominal_gdp(ctx)
    return [(y, v / gdp[y] * 100) for y, v in
            ctx.col("fiscal/federal_budget.csv", "balance_bn_rub")
            if y in gdp and gdp[y]]


def _price_level(ctx):
    """The December-to-December CPI chained from 2006 = 100."""
    run, out = 100.0, []
    for y, v in ctx.col("macro/cpi.csv", "cpi_dec_pct"):
        run *= 1 + v / 100
        out.append((y, run / 100))
    return out


def _trade_balance(ctx):
    ex = dict(ctx.col("trade/trade.csv", "exports_pct_gdp"))
    im = dict(ctx.col("trade/trade.csv", "imports_pct_gdp"))
    return [(y, ex[y] - im[y]) for y in sorted(ex) if y in im]


def headline(ctx) -> list[dict]:
    """The figures the page leads with, above the plates.

    The order is fixed by the atlas: GDP, GDP per person, population, then
    this country's own readings (tests/test_site.py enforces the first
    three).
    """
    return [
        ctx.stat({"en": "GDP", "ru": "ВВП", "pt": "PIB"},
                 [(y, v / 1e9) for y, v in
                  ctx.col("world/gdp_usd.csv", "gdp_usd")], "usd_bn"),
        ctx.stat({"en": "GDP per person, US$", "ru": "ВВП на человека, долл.",
                  "pt": "PIB por pessoa, US$"},
                 ctx.col("world/gdp_per_person.csv", "gdp_per_person_usd"),
                 "count"),
        ctx.stat({"en": "Population", "ru": "Население",
                  "pt": "População"},
                 ctx.col("demography/population.csv", "population_mn"),
                 "pop_mn", kind="level"),
        ctx.stat({"en": "Key rate, annual mean", "ru": "Ключевая ставка, "
                  "среднее за год", "pt": "Taxa básica, média do ano"},
                 ctx.col("markets/key_rate.csv", "key_rate_pct"), "pct"),
        ctx.stat({"en": "Inflation, December to December",
                  "ru": "Инфляция, декабрь к декабрю",
                  "pt": "Inflação, dezembro a dezembro"},
                 ctx.col("macro/cpi.csv", "cpi_dec_pct"), "pct"),
        ctx.stat({"en": "Federal balance", "ru": "Баланс федерального "
                  "бюджета", "pt": "Saldo federal"},
                 _federal_balance(ctx), "pct_gdp_s"),
        ctx.stat({"en": "Poverty, national line",
                  "ru": "Бедность, национальная черта",
                  "pt": "Pobreza, linha nacional"},
                 ctx.col("people/poverty.csv", "poverty_national_pct"), "pct"),
        ctx.stat({"en": "Reserves", "ru": "Резервы", "pt": "Reservas"},
                 [(y, v / 1e9) for y, v in
                  ctx.col("world/reserves.csv", "reserves_usd")],
                 "usd_bn", kind="level"),
    ]


def build(ctx) -> list[dict]:
    chapters = [
        {
            "id": "01-economy", "topic": "economy", "n": "01",
            "family": MONEY,
            "title": ctx.text(en="The Economy",
                              ru="Экономика",
                              pt="A Economia"),
            "blurb": ctx.text(
                en="Three contractions and a long stagnation: output fell "
                   "7.8% in 2009, 2.0% in 2015 and 1.4% in 2022, and the "
                   "dollar value of a Russian income halved between 2013 "
                   "and 2015 without anyone's rouble pay falling.",
                ru="Три спада и долгая стагнация: выпуск упал на 7,8% в "
                   "2009, на 2,0% в 2015 и на 1,4% в 2022 году, а долларовая "
                   "величина российского дохода упала вдвое между 2013 и "
                   "2015 годами, хотя рублёвая зарплата не уменьшалась.",
                pt="Três contrações e uma longa estagnação: o produto caiu "
                   "7,8% em 2009, 2,0% em 2015 e 1,4% em 2022, e o valor em "
                   "dólares da renda russa caiu pela metade entre 2013 e "
                   "2015 sem que o salário em rublos caísse."),
            "alt": {
                "en": "Four panels on the Russian economy. Real GDP growth "
                      "is negative in 2009, 2015, 2020 and 2022. GDP per "
                      "person in dollars halves between 2013 and 2015. Two "
                      "inflation lines, Rosstat's December-to-December and "
                      "the World Bank's annual average, never merge. "
                      "Unemployment is the ILO modelled estimate.",
                "ru": "Четыре панели об экономике России. Реальный рост ВВП "
                      "отрицателен в 2009, 2015, 2020 и 2022 годах. ВВП на "
                      "человека в долларах падает вдвое между 2013 и 2015 "
                      "годами. Две линии инфляции — ИПЦ Росстата «декабрь к "
                      "декабрю» и среднегодовой Всемирного банка — не "
                      "сливаются. Безработица — модельная оценка МОТ.",
                "pt": "Quatro painéis sobre a economia russa. O crescimento "
                      "real do PIB é negativo em 2009, 2015, 2020 e 2022. O "
                      "PIB por pessoa em dólares cai pela metade entre 2013 "
                      "e 2015. Duas linhas de inflação, a do Rosstat de "
                      "dezembro a dezembro e a média anual do Banco "
                      "Mundial, nunca se juntam. O desemprego é a "
                      "estimativa modelada da OIT.",
            },
            "spark": ctx.col("macro/gdp.csv", "real_growth_pct"),
            "stats": [
                ctx.stat({"en": "GDP per person, US$",
                          "ru": "ВВП на человека, долл.",
                          "pt": "PIB por pessoa, US$"},
                         ctx.col("world/gdp_per_person.csv",
                                 "gdp_per_person_usd"), "count"),
                ctx.stat({"en": "Real growth", "ru": "Реальный рост",
                          "pt": "Crescimento real"},
                         ctx.col("macro/gdp.csv", "real_growth_pct"),
                         "pct_s"),
                ctx.stat({"en": "CPI inflation", "ru": "Инфляция (ИПЦ)",
                          "pt": "Inflação (IPC)"},
                         ctx.col("macro/cpi.csv", "cpi_dec_pct"), "pct"),
            ],
        },
        {
            "id": "02-fiscal", "topic": "fiscal", "n": "02", "family": MONEY,
            "title": ctx.text(en="Public Finances",
                              ru="Государственные финансы",
                              pt="Finanças Públicas"),
            "blurb": ctx.text(
                en="Three perimeters, never added together: general "
                   "government on the IMF's accrual accounts, the federal "
                   "cash budget, and the non-oil-and-gas deficit the "
                   "Ministry leads with — 6.6% of GDP in 2025, against a "
                   "headline federal deficit of 2.6%.",
                ru="Три периметра, которые никогда не складываются: общее "
                   "госуправление по методу начисления МВФ, федеральный "
                   "кассовый бюджет и дефицит без нефти и газа, с которого "
                   "начинает Минфин, — 6,6% ВВП в 2025 году против "
                   "официального федерального дефицита 2,6%.",
                pt="Três perímetros que nunca se somam: a administração "
                   "pública geral nas contas de competência do FMI, o "
                   "orçamento federal de caixa e o déficit sem petróleo e "
                   "gás que o Ministério destaca — 6,6% do PIB em 2025 "
                   "contra um déficit federal de 2,6%."),
            "alt": {
                "en": "Four panels on Russia's public finances. Revenue and "
                      "expenditure as a share of GDP, expenditure peaking "
                      "in 2020. The overall balance is in surplus in "
                      "2006–2008 and 2018–2019; the gold line is the "
                      "federal non-oil-and-gas deficit, far below it. Gross "
                      "debt stays under 20% of GDP and interest under 1.2%.",
                "ru": "Четыре панели о государственных финансах России. "
                      "Доходы и расходы в доле ВВП, расходы достигают пика "
                      "в 2020 году. Общий баланс был профицитным в "
                      "2006–2008 и 2018–2019 годах; золотая линия — "
                      "федеральный дефицит без нефти и газа, намного ниже. "
                      "Валовой долг остаётся ниже 20% ВВП, проценты — ниже "
                      "1,2%.",
                "pt": "Quatro painéis sobre as finanças públicas russas. "
                      "Receita e despesa como fração do PIB, com a despesa "
                      "no pico em 2020. O saldo total é superavitário em "
                      "2006–2008 e 2018–2019; a linha dourada é o déficit "
                      "federal sem petróleo e gás, bem abaixo. A dívida "
                      "bruta fica abaixo de 20% do PIB e os juros abaixo "
                      "de 1,2%.",
            },
            "spark": ctx.col("fiscal/fiscal.csv", "balance_pct_gdp"),
            "stats": [
                ctx.stat({"en": "Overall balance", "ru": "Общий баланс",
                          "pt": "Saldo total"},
                         ctx.col("fiscal/fiscal.csv", "balance_pct_gdp"),
                         "pct_gdp_s"),
                ctx.stat({"en": "Gross debt", "ru": "Валовой долг",
                          "pt": "Dívida bruta"},
                         ctx.col("fiscal/fiscal.csv", "debt_pct_gdp"),
                         "pct_gdp", kind="level"),
                ctx.stat({"en": "Federal balance", "ru": "Баланс "
                          "федерального бюджета", "pt": "Saldo federal"},
                         _federal_balance(ctx), "pct_gdp_s"),
            ],
        },
        {
            "id": "03-spending", "topic": "spending", "n": "03",
            "family": MONEY,
            "title": ctx.text(en="Spending",
                              ru="Расходы",
                              pt="Despesas"),
            "blurb": ctx.text(
                en="The federal budget spends about 18% of GDP, and social "
                   "policy is its largest single function. Pensions are paid "
                   "through the Social Fund outside this perimeter, and the "
                   "functional breakdown itself has not been published "
                   "since 2021.",
                ru="Федеральный бюджет расходует около 18% ВВП, и социальная "
                   "политика — его крупнейшая функция. Пенсии платятся "
                   "через Социальный фонд вне этого периметра, а сама "
                   "функциональная разбивка не публикуется с 2021 года.",
                pt="O orçamento federal gasta cerca de 18% do PIB, e a "
                   "política social é a sua maior função isolada. As "
                   "pensões são pagas pelo Fundo Social fora deste "
                   "perímetro, e a própria abertura funcional não é "
                   "publicada desde 2021."),
            "alt": {
                "en": "Four panels on Russian federal spending. A stacked "
                      "area of seven functional groups as a share of GDP, "
                      "2006–2021, and social protection against everything "
                      "else. Whole-economy investment holds near 20–23% of "
                      "GDP. Public investment is pending: no official "
                      "government investment series is staged.",
                "ru": "Четыре панели о федеральных расходах России. "
                      "Накопленная площадь семи функциональных групп в доле "
                      "ВВП, 2006–2021, и социальная политика против всего "
                      "остального. Инвестиции всей экономики держатся "
                      "около 20–23% ВВП. Государственные инвестиции "
                      "отсутствуют: официальный ряд не собран.",
                "pt": "Quatro painéis sobre a despesa federal russa. Uma "
                      "área empilhada de sete grupos funcionais como fração "
                      "do PIB, 2006–2021, e a proteção social contra todo o "
                      "resto. O investimento da economia inteira fica perto "
                      "de 20–23% do PIB. O investimento público está "
                      "pendente: nenhuma série oficial foi coletada.",
            },
            "spark": ctx.col("macro/economy.csv", "gfcf_pct_gdp"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Investment rate", "ru": "Норма инвестиций",
                          "pt": "Taxa de investimento"},
                         ctx.col("macro/economy.csv", "gfcf_pct_gdp"),
                         "pct_gdp", kind="level"),
                ctx.stat({"en": "Federal spending", "ru": "Федеральные "
                          "расходы", "pt": "Despesa federal"},
                         _federal_spending(ctx), "pct_gdp", year=2021),
                ctx.stat({"en": "Social policy", "ru": "Социальная "
                          "политика", "pt": "Política social"},
                         _social_policy(ctx), "pct_gdp", year=2021),
            ],
        },
        {
            "id": "04-trade", "topic": "trade", "n": "04", "family": MONEY,
            "title": ctx.text(en="Trade",
                              ru="Торговля",
                              pt="Comércio"),
            "blurb": ctx.text(
                en="A surplus every year of the window, and a shrinking one: "
                   "exports fell from 33.7% of GDP in 2006 to 18.2% in 2025. "
                   "The customs service suspended its detailed release in "
                   "2022, so the partner cut is not on the page.",
                ru="Профицит в каждом году окна, и он сжимается: экспорт "
                   "упал с 33,7% ВВП в 2006 году до 18,2% в 2025-м. "
                   "Таможенная служба приостановила подробный выпуск в 2022 "
                   "году, поэтому разбивки по партнёрам здесь нет.",
                pt="Superávit em todos os anos da janela, e encolhendo: as "
                   "exportações caíram de 33,7% do PIB em 2006 para 18,2% "
                   "em 2025. O serviço aduaneiro suspendeu a divulgação "
                   "detalhada em 2022, então o recorte por parceiro não "
                   "está na página."),
            "alt": {
                "en": "Four panels on Russian trade. Exports and imports of "
                      "goods and services as a share of GDP, exports "
                      "falling from 33.7% in 2006 to 18.2% in 2025. The "
                      "balance is in surplus every year. Export "
                      "destinations are pending; the lens converts the "
                      "surplus to dollars, peaking near US$290bn in 2022.",
                "ru": "Четыре панели о торговле России. Экспорт и импорт "
                      "товаров и услуг в доле ВВП, экспорт падает с 33,7% в "
                      "2006 до 18,2% в 2025. Баланс профицитен каждый год. "
                      "Направления экспорта отсутствуют; правая панель "
                      "переводит профицит в доллары — пик около 290 млрд "
                      "долл. в 2022.",
                "pt": "Quatro painéis sobre o comércio russo. Exportações e "
                      "importações de bens e serviços como fração do PIB, "
                      "com as exportações caindo de 33,7% em 2006 para "
                      "18,2% em 2025. O saldo é superavitário todo ano. Os "
                      "destinos das exportações estão pendentes; o painel "
                      "da direita converte o superávit em dólares, com pico "
                      "perto de US$ 290 bi em 2022.",
            },
            "spark": ctx.col("trade/trade.csv", "exports_pct_gdp"),
            "stats": [
                ctx.stat({"en": "Exports", "ru": "Экспорт",
                          "pt": "Exportações"},
                         ctx.col("trade/trade.csv", "exports_pct_gdp"),
                         "pct_gdp"),
                ctx.stat({"en": "Imports", "ru": "Импорт",
                          "pt": "Importações"},
                         ctx.col("trade/trade.csv", "imports_pct_gdp"),
                         "pct_gdp"),
                ctx.stat({"en": "Trade balance", "ru": "Торговый баланс",
                          "pt": "Balança comercial"},
                         _trade_balance(ctx), "pct_gdp_s"),
            ],
        },
        {
            "id": "05-markets", "topic": "markets", "n": "05",
            "family": MONEY,
            "title": ctx.text(en="Markets",
                              ru="Рынки",
                              pt="Mercados"),
            "blurb": ctx.text(
                en="The key rate went from 9.50% to 20.00% on 28 February "
                   "2022 and back within three weeks, then to 21% in 2024. "
                   "The official rouble rate was an administered price for "
                   "part of 2022, and the exchange's dollar index has never "
                   "recovered its 2006 level.",
                ru="Ключевая ставка выросла с 9,50% до 20,00% 28 февраля "
                   "2022 года и вернулась назад за три недели, а в 2024 "
                   "году дошла до 21%. Официальный курс рубля часть 2022 "
                   "года был административным, и долларовый индекс биржи "
                   "так и не вернулся к уровню 2006 года.",
                pt="A taxa básica foi de 9,50% para 20,00% em 28 de "
                   "fevereiro de 2022 e voltou em três semanas, depois "
                   "chegou a 21% em 2024. A taxa oficial do rublo foi um "
                   "preço administrado em parte de 2022, e o índice da "
                   "bolsa em dólares nunca recuperou o nível de 2006."),
            "alt": {
                "en": "Four panels on Russian markets. The key rate and "
                      "inflation, with the 20% emergency rate of 28 "
                      "February 2022 marked. The 10-year yield rises to "
                      "15.3% by 2026. The rouble falls from 27 per dollar "
                      "in 2006 to 83 in 2025. The MOEX index in dollars "
                      "falls from 100 in 2006 to 67 in 2025.",
                "ru": "Четыре панели о рынках России. Ключевая ставка и "
                      "инфляция, с отмеченной ставкой 20% от 28 февраля "
                      "2022 года. Доходность 10-летних бумаг растёт до "
                      "15,3% к 2026 году. Рубль падает с 27 за доллар в "
                      "2006 до 83 в 2025. Индекс MOEX в долларах падает со "
                      "100 в 2006 до 67 в 2025.",
                "pt": "Quatro painéis sobre os mercados russos. A taxa "
                      "básica e a inflação, com a taxa de emergência de 20% "
                      "de 28 de fevereiro de 2022 marcada. O rendimento de "
                      "10 anos sobe a 15,3% até 2026. O rublo cai de 27 por "
                      "dólar em 2006 para 83 em 2025. O índice MOEX em "
                      "dólares cai de 100 em 2006 para 67 em 2025.",
            },
            "spark": ctx.col("markets/key_rate.csv", "key_rate_pct"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Key rate, annual mean",
                          "ru": "Ключевая ставка, среднее за год",
                          "pt": "Taxa básica, média do ano"},
                         ctx.col("markets/key_rate.csv", "key_rate_pct"),
                         "pct"),
                ctx.stat({"en": "10-year yield", "ru": "Доходность "
                          "10-летних бумаг", "pt": "Juro de 10 anos"},
                         ctx.col("markets/ofz_10y.csv", "ofz_10y_pct"),
                         "pct2"),
                ctx.stat({"en": "Roubles per US$", "ru": "Рублей за доллар",
                          "pt": "Rublos por US$"},
                         ctx.col("markets/usd_rub.csv", "rub_per_usd"),
                         "dec2"),
            ],
        },
        {
            "id": "06-credit", "topic": "credit", "n": "06", "family": MONEY,
            "title": ctx.text(en="Credit",
                              ru="Кредит",
                              pt="Crédito"),
            "blurb": ctx.text(
                en="Household debt is small for a country at this income — "
                   "21% of GDP — but it became expensive: new rouble loans "
                   "cost 18.6% in 2025 against a 19.1% key rate, and the "
                   "margin over the policy rate inverted.",
                ru="Долг домохозяйств невелик для страны с таким доходом — "
                   "21% ВВП, — но подорожал: новые рублёвые кредиты стоили "
                   "18,6% в 2025 году против ключевой ставки 19,1%, и "
                   "маржа над ставкой перевернулась.",
                pt="A dívida das famílias é pequena para um país nessa "
                   "faixa de renda — 21% do PIB — mas ficou cara: novos "
                   "empréstimos em rublos custavam 18,6% em 2025 contra "
                   "19,1% da taxa básica, e a margem sobre a taxa básica se "
                   "inverteu."),
            "alt": {
                "en": "Four panels on Russian credit. Household debt rises "
                      "from 8.2% of GDP in 2006 to 21–22% from 2020. The "
                      "new-loan rate falls to 10.6% in 2021 and rises to "
                      "18.6% in 2025. Non-performing loans fall to 4.5% in "
                      "2023, where the series stops. The margin over the "
                      "key rate turns negative.",
                "ru": "Четыре панели о кредите в России. Долг домохозяйств "
                      "растёт с 8,2% ВВП в 2006 до 21–22% с 2020 года. "
                      "Ставка по новым кредитам падает до 10,6% в 2021 и "
                      "растёт до 18,6% в 2025. Проблемные кредиты падают до "
                      "4,5% в 2023, где ряд обрывается. Маржа над ключевой "
                      "ставкой становится отрицательной.",
                "pt": "Quatro painéis sobre o crédito russo. A dívida das "
                      "famílias sobe de 8,2% do PIB em 2006 para 21–22% "
                      "desde 2020. A taxa dos novos empréstimos cai a 10,6% "
                      "em 2021 e sobe a 18,6% em 2025. A inadimplência cai "
                      "a 4,5% em 2023, onde a série para. A margem sobre a "
                      "taxa básica fica negativa.",
            },
            "spark": ctx.col("credit/household_debt.csv",
                             "household_debt_pct_gdp"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Household debt", "ru": "Долг домохозяйств",
                          "pt": "Dívida das famílias"},
                         ctx.col("credit/household_debt.csv",
                                 "household_debt_pct_gdp"), "pct_gdp",
                         kind="level"),
                ctx.stat({"en": "New loan rate", "ru": "Ставка по новым "
                          "кредитам", "pt": "Juro de novos empréstimos"},
                         ctx.col("credit/household_lending_rate.csv",
                                 "household_lending_rate_pct"), "pct2"),
                ctx.stat({"en": "Non-performing loans", "ru": "Проблемные "
                          "кредиты", "pt": "Inadimplência"},
                         ctx.col("credit/npl.csv", "npl_pct_loans"), "pct"),
            ],
        },
        {
            "id": "07-people", "topic": "people", "n": "07", "family": PEOPLE,
            "title": ctx.text(en="People",
                              ru="Люди",
                              pt="Pessoas"),
            "blurb": ctx.text(
                en="Inequality fell for fifteen years — the Gini from 42.3 to "
                   "33.0 — and poverty on the national line from 15.2% to "
                   "7.2%. Prices, meanwhile, are 4.5 times their 2006 level, "
                   "which is what a rouble's worth means across this window.",
                ru="Неравенство падало пятнадцать лет — Джини с 42,3 до "
                   "33,0, — а бедность по национальной черте — с 15,2% до "
                   "7,2%. Цены за это время выросли в 4,5 раза к уровню "
                   "2006 года — вот что значит рубль на этом окне.",
                pt="A desigualdade caiu por quinze anos — o Gini de 42,3 "
                   "para 33,0 — e a pobreza na linha nacional de 15,2% para "
                   "7,2%. Os preços, entretanto, estão 4,5 vezes o nível de "
                   "2006, que é o que vale um rublo nesta janela."),
            "alt": {
                "en": "Four panels on Russian living standards. The Gini "
                      "falls from 42.3 in 2007 to 33.0 in 2023. Poverty on "
                      "the national line falls to 7.2% in 2024, with the "
                      "World Bank's upper-middle-income line far below. The "
                      "minimum wage is pending. The lens chains the CPI to "
                      "about 4.5 times the 2006 level.",
                "ru": "Четыре панели об уровне жизни в России. Джини падает "
                      "с 42,3 в 2007 до 33,0 в 2023. Бедность по "
                      "национальной черте падает до 7,2% в 2024, а черта "
                      "Всемирного банка для стран с доходом выше среднего "
                      "намного ниже. Минимальная оплата труда отсутствует. "
                      "Правая панель сцепляет ИПЦ до 4,5 раза к уровню "
                      "2006 года.",
                "pt": "Quatro painéis sobre o padrão de vida russo. O Gini "
                      "cai de 42,3 em 2007 para 33,0 em 2023. A pobreza na "
                      "linha nacional cai para 7,2% em 2024, com a linha do "
                      "Banco Mundial para renda média-alta bem abaixo. O "
                      "salário mínimo está pendente. O painel da direita "
                      "encadeia o IPC até 4,5 vezes o nível de 2006.",
            },
            "spark": ctx.col("people/gini.csv", "gini"),
            "stats": [
                ctx.stat({"en": "Gini", "ru": "Джини", "pt": "Gini"},
                         ctx.col("people/gini.csv", "gini"), "count"),
                ctx.stat({"en": "Poverty, national line",
                          "ru": "Бедность, национальная черта",
                          "pt": "Pobreza, linha nacional"},
                         ctx.col("people/poverty.csv", "poverty_national_pct"),
                         "pct"),
                ctx.stat({"en": "Price level since 2006, ×",
                          "ru": "Уровень цен с 2006 года, ×",
                          "pt": "Nível de preços desde 2006, ×"},
                         _price_level(ctx), "dec2"),
            ],
        },
        {
            "id": "08-world", "topic": "world", "n": "08", "family": WORLD,
            "title": ctx.text(en="Russia in the World",
                              ru="Россия в мире",
                              pt="A Rússia no Mundo"),
            "blurb": ctx.text(
                en="A US$2.6tn economy in 2025 in current dollars, an HDI of "
                   "0.832, and US$608bn of reserves — most of them "
                   "immobilised abroad since 2022. The Corruption "
                   "Perceptions Index has no reachable official file.",
                ru="Экономика в 2,6 трлн долл. в 2025 году в текущих "
                   "долларах, ИРЧП 0,832 и 608 млрд долл. резервов, большая "
                   "часть которых с 2022 года заморожена за рубежом. "
                   "Доступного официального файла индекса восприятия "
                   "коррупции нет.",
                pt="Uma economia de US$ 2,6 tri em 2025 em dólares "
                   "correntes, um IDH de 0,832 e US$ 608 bi de reservas — a "
                   "maioria imobilizada no exterior desde 2022. O Índice de "
                   "Percepção da Corrupção não tem arquivo oficial "
                   "alcançável."),
            "alt": {
                "en": "Four panels placing Russia in the world. GDP at "
                      "current prices peaks near US$2.29tn in 2013 and 2022. "
                      "The HDI rises from 0.791 in 2006 to 0.832 in 2023, "
                      "dipping in 2020–2021. The Corruption Perceptions "
                      "Index is pending. Reserves rise to US$608bn in 2024.",
                "ru": "Четыре панели о месте России в мире. ВВП в текущих "
                      "ценах достигает пика около 2,29 трлн долл. в 2013 и "
                      "2022 годах. ИРЧП растёт с 0,791 в 2006 до 0,832 в "
                      "2023, с провалом в 2020–2021. Индекс восприятия "
                      "коррупции отсутствует. Резервы растут до 608 млрд "
                      "долл. в 2024.",
                "pt": "Quatro painéis que situam a Rússia no mundo. O PIB a "
                      "preços correntes tem pico perto de US$ 2,29 tri em "
                      "2013 e 2022. O IDH sobe de 0,791 em 2006 para 0,832 "
                      "em 2023, com queda em 2020–2021. O Índice de "
                      "Percepção da Corrupção está pendente. As reservas "
                      "sobem a US$ 608 bi em 2024.",
            },
            "spark": ctx.col("world/gdp_usd.csv", "gdp_usd"),
            "stats": [
                ctx.stat({"en": "GDP, current US$", "ru": "ВВП, текущие "
                          "доллары", "pt": "PIB, US$ correntes"},
                         [(y, v / 1e9) for y, v in
                          ctx.col("world/gdp_usd.csv", "gdp_usd")],
                         "usd_bn"),
                ctx.stat({"en": "HDI", "ru": "ИРЧП", "pt": "IDH"},
                         ctx.col("world/hdi.csv", "hdi"), "dec3"),
                ctx.stat({"en": "Reserves", "ru": "Резервы",
                          "pt": "Reservas"},
                         [(y, v / 1e9) for y, v in
                          ctx.col("world/reserves.csv", "reserves_usd")],
                         "usd_bn", kind="level"),
            ],
        },
        {
            "id": "09-demography", "topic": "demography", "n": "09",
            "family": PEOPLE,
            "title": ctx.text(en="Demography",
                              ru="Демография",
                              pt="Demografia"),
            "blurb": ctx.text(
                en="146.1m people on Rosstat's perimeter, a fertility rate of "
                   "1.42 and deaths above births every year since 2016. The "
                   "2014 step in the population line is territory — Crimea "
                   "and Sevastopol — and the UN series does not carry it.",
                ru="146,1 млн человек в периметре Росстата, коэффициент "
                   "рождаемости 1,42 и смертность выше рождаемости каждый "
                   "год с 2016-го. Скачок 2014 года в ряду населения — это "
                   "территория: Крым и Севастополь, — и в ряду ООН его нет.",
                pt="146,1 milhões de pessoas no perímetro do Rosstat, "
                   "fecundidade de 1,42 e mortes acima dos nascimentos todos "
                   "os anos desde 2016. O degrau de 2014 na linha "
                   "populacional é território — Crimeia e Sebastopol — e a "
                   "série da ONU não o carrega."),
            "alt": {
                "en": "Four panels on Russian demography. Two population "
                      "lines indexed to 2006: Rosstat's steps up 2.7 million "
                      "between 2014 and 2015 and the UN's does not. "
                      "Fertility falls from 1.78 in 2015 to 1.42 in 2024. "
                      "Births fall below deaths from 2016. Natural increase "
                      "is negative every year.",
                "ru": "Четыре панели о демографии России. Две линии "
                      "населения с индексом 2006 = 100: у Росстата скачок на "
                      "2,7 млн между 2014 и 2015 годами, у ООН его нет. "
                      "Рождаемость падает с 1,78 в 2015 до 1,42 в 2024. С "
                      "2016 года смертей больше, чем рождений. Естественный "
                      "прирост отрицателен каждый год.",
                "pt": "Quatro painéis sobre a demografia russa. Duas linhas "
                      "populacionais indexadas a 2006: a do Rosstat dá um "
                      "degrau de 2,7 milhões entre 2014 e 2015 e a da ONU "
                      "não. A fecundidade cai de 1,78 em 2015 para 1,42 em "
                      "2024. Desde 2016 as mortes superam os nascimentos. O "
                      "crescimento natural é negativo todo ano.",
            },
            "spark": ctx.col("demography/population.csv", "population_mn"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Population", "ru": "Население",
                          "pt": "População"},
                         ctx.col("demography/population.csv",
                                 "population_mn"), "pop_mn", kind="level"),
                ctx.stat({"en": "Fertility rate", "ru": "Коэффициент "
                          "рождаемости", "pt": "Taxa de fecundidade"},
                         ctx.col("demography/fertility.csv", "tfr"), "dec2"),
                ctx.stat({"en": "Births per 1,000", "ru": "Рождений на 1 000",
                          "pt": "Nascimentos por 1.000"},
                         ctx.col("demography/vitals.csv",
                                 "birth_rate_per_1000"), "dec2"),
            ],
        },
        {
            "id": "10-security", "topic": "security", "n": "10",
            "family": PEOPLE,
            "title": ctx.text(en="Security",
                              ru="Безопасность",
                              pt="Segurança"),
            "blurb": ctx.text(
                en="Violence fell by two thirds in fifteen years: the "
                   "homicide rate from 20.0 to 6.8 per 100,000, suicide from "
                   "41.4 to 21.4. Every one of these series stops before "
                   "the war, and the national publishers do not answer.",
                ru="Насилие упало на две трети за пятнадцать лет: "
                   "коэффициент убийств с 20,0 до 6,8 на 100 000, "
                   "самоубийств — с 41,4 до 21,4. Каждый из этих рядов "
                   "обрывается до войны, а национальные публикаторы не "
                   "отвечают.",
                pt="A violência caiu dois terços em quinze anos: a taxa de "
                   "homicídios de 20,0 para 6,8 por 100.000, a de suicídios "
                   "de 41,4 para 21,4. Todas essas séries param antes da "
                   "guerra, e os publicadores nacionais não respondem."),
            "alt": {
                "en": "Four panels on Russian violent and accidental death. "
                      "The homicide rate falls from 20.0 per 100,000 in 2006 "
                      "to 6.8 in 2021. Suicide falls from 41.4 to 21.4. "
                      "Road deaths fall from 27.5 in 2006 to 12.0 in 2019. "
                      "The lens sets 2006 against each series' last year.",
                "ru": "Четыре панели о насильственной и дорожной смерти в "
                      "России. Коэффициент убийств падает с 20,0 на 100 000 в "
                      "2006 до 6,8 в 2021. Самоубийства — с 41,4 до 21,4. "
                      "Смерти в ДТП — с 27,5 в 2006 до 12,0 в 2019. Правая "
                      "панель сопоставляет 2006 год с последним годом "
                      "каждого ряда.",
                "pt": "Quatro painéis sobre a morte violenta e no trânsito "
                      "na Rússia. A taxa de homicídios cai de 20,0 por "
                      "100.000 em 2006 para 6,8 em 2021. A de suicídios cai "
                      "de 41,4 para 21,4. As mortes no trânsito caem de "
                      "27,5 em 2006 para 12,0 em 2019. O painel da direita "
                      "compara 2006 com o último ano de cada série.",
            },
            "spark": ctx.col("security/security.csv", "homicide_per_100k"),
            "stats": [
                ctx.stat({"en": "Homicide", "ru": "Убийства",
                          "pt": "Homicídios"},
                         ctx.col("security/security.csv",
                                 "homicide_per_100k"), "per100k"),
                ctx.stat({"en": "Suicide", "ru": "Самоубийства",
                          "pt": "Suicídios"},
                         ctx.col("security/security.csv",
                                 "suicide_per_100k"), "per100k"),
                ctx.stat({"en": "Road deaths", "ru": "Дорожные смерти",
                          "pt": "Mortes no trânsito"},
                         ctx.col("security/security.csv",
                                 "road_deaths_per_100k"), "per100k"),
            ],
        },
        {
            "id": "11-mortality", "topic": "mortality", "n": "11",
            "family": PEOPLE,
            "title": ctx.text(en="Mortality",
                              ru="Смертность",
                              pt="Mortalidade"),
            "blurb": ctx.text(
                en="The death rate fell from 15.1 to 12.3 per 1,000 before "
                   "the pandemic, peaked at 16.7 in 2021, and is back at "
                   "12.4. Life expectancy lost three years in 2021 and has "
                   "recovered. Neither excess deaths nor COVID-19 deaths can "
                   "be drawn: no official count series is reachable.",
                ru="Коэффициент смертности упал с 15,1 до 12,3 на 1 000 до "
                   "пандемии, достиг пика 16,7 в 2021 году и вернулся к "
                   "12,4. Ожидаемая продолжительность жизни потеряла три "
                   "года в 2021-м и восстановилась. Ни избыточную "
                   "смертность, ни смерти от COVID-19 нарисовать нельзя: "
                   "официального ряда счёта нет.",
                pt="A taxa de mortalidade caiu de 15,1 para 12,3 por 1.000 "
                   "antes da pandemia, teve pico de 16,7 em 2021 e voltou a "
                   "12,4. A expectativa de vida perdeu três anos em 2021 e "
                   "se recuperou. Nem o excesso de mortes nem as mortes por "
                   "COVID-19 podem ser desenhados: não há série oficial de "
                   "contagem alcançável."),
            "alt": {
                "en": "Four panels on Russian mortality. The crude death "
                      "rate falls from 15.1 per 1,000 in 2006 to 12.3 in "
                      "2019, spikes to 16.7 in 2021 and falls back to 12.4 "
                      "in 2024. Excess deaths and COVID-19 deaths are "
                      "pending. Life expectancy rises to 73.4 years in "
                      "2024, after a dip to 69.9 in 2021.",
                "ru": "Четыре панели о смертности в России. Общий "
                      "коэффициент смертности падает с 15,1 на 1 000 в 2006 "
                      "до 12,3 в 2019, подскакивает до 16,7 в 2021 и "
                      "возвращается к 12,4 в 2024. Избыточная смертность и "
                      "смерти от COVID-19 отсутствуют. Ожидаемая "
                      "продолжительность жизни растёт до 73,4 года в 2024 "
                      "после провала до 69,9 в 2021.",
                "pt": "Quatro painéis sobre a mortalidade russa. A taxa "
                      "bruta de mortalidade cai de 15,1 por 1.000 em 2006 "
                      "para 12,3 em 2019, sobe a 16,7 em 2021 e volta a "
                      "12,4 em 2024. O excesso de mortes e as mortes por "
                      "COVID-19 estão pendentes. A expectativa de vida sobe "
                      "a 73,4 anos em 2024, após cair a 69,9 em 2021.",
            },
            "spark": ctx.col("mortality/mortality.csv",
                             "death_rate_per_1000"),
            "stats": [
                ctx.stat({"en": "Crude death rate", "ru": "Общий "
                          "коэффициент смертности",
                          "pt": "Taxa bruta de mortalidade"},
                         ctx.col("mortality/mortality.csv",
                                 "death_rate_per_1000"), "dec2"),
                ctx.stat({"en": "Life expectancy", "ru": "Ожидаемая "
                          "продолжительность жизни",
                          "pt": "Expectativa de vida"},
                         ctx.col("mortality/mortality.csv",
                                 "life_expectancy"), "dec2", kind="level"),
            ],
        },
        {
            "id": "12-migration", "topic": "migration", "n": "12",
            "family": PEOPLE,
            "title": ctx.text(en="Migration",
                              ru="Миграция",
                              pt="Migração"),
            "blurb": ctx.text(
                en="The UN model has net migration at +5.3 per 1,000 in 2022 "
                   "and -1.8 in 2025, and the foreign-born share falling from "
                   "7.8% to 5.3%. Rosstat's own registration totals measure "
                   "something else and are deliberately not drawn beside "
                   "them.",
                ru="В модели ООН миграционный прирост составил +5,3 на 1 000 "
                   "в 2022 году и -1,8 в 2025-м, а доля родившихся за "
                   "рубежом упала с 7,8% до 5,3%. Собственные "
                   "регистрационные итоги Росстата измеряют другое и "
                   "намеренно не нарисованы рядом.",
                pt="No modelo da ONU a migração líquida é +5,3 por 1.000 em "
                   "2022 e -1,8 em 2025, e a proporção de nascidos no "
                   "exterior cai de 7,8% para 5,3%. Os totais de registro do "
                   "próprio Rosstat medem outra coisa e deliberadamente não "
                   "são desenhados ao lado deles."),
            "alt": {
                "en": "Four panels on Russian migration. Gross immigration "
                      "and emigration are pending. Net migration per 1,000 "
                      "peaks at 5.3 in 2022 and turns negative by 2024. The "
                      "foreign-born share falls from 7.8% in 2010 to 5.3% in "
                      "2024. The lens shows the same model in persons.",
                "ru": "Четыре панели о миграции в России. Иммиграция и "
                      "эмиграция отсутствуют. Миграционный прирост на 1 000 "
                      "достигает пика 5,3 в 2022 и становится отрицательным "
                      "к 2024. Доля родившихся за рубежом падает с 7,8% в "
                      "2010 до 5,3% в 2024. Правая панель показывает ту же "
                      "модель в человеках.",
                "pt": "Quatro painéis sobre a migração russa. Imigração e "
                      "emigração estão pendentes. A migração líquida por "
                      "1.000 tem pico de 5,3 em 2022 e fica negativa em "
                      "2024. A proporção de nascidos no exterior cai de 7,8% "
                      "em 2010 para 5,3% em 2024. O painel da direita mostra "
                      "o mesmo modelo em pessoas.",
            },
            "spark": ctx.col("migration/net_migration.csv", "net_migration"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Net migration per 1,000",
                          "ru": "Миграционный прирост на 1 000",
                          "pt": "Migração líquida por 1.000"},
                         _net_per_1000(ctx), "dec2"),
                ctx.stat({"en": "Foreign-born share", "ru": "Доля родившихся "
                          "за рубежом", "pt": "Nascidos no exterior"},
                         _migrant_share(ctx), "pct", kind="level"),
                ctx.stat({"en": "Net migration, 2022",
                          "ru": "Миграционный прирост, 2022",
                          "pt": "Migração líquida, 2022"},
                         ctx.col("migration/net_migration.csv",
                                 "net_migration"), "count", year=2022),
            ],
        },
    ]
    return chapters


def _federal_spending(ctx):
    """Federal expenditure as % of GDP — Minfin's roubles over Rosstat's."""
    gdp = _nominal_gdp(ctx)
    return [(y, v / gdp[y] * 100) for y, v in
            ctx.col("fiscal/federal_budget.csv", "expenditure_bn_rub")
            if y in gdp and gdp[y]]


def _social_policy(ctx):
    """The Russian functional section 'Социальная политика' as % of GDP."""
    gdp = _nominal_gdp(ctx)
    return [(y, v / gdp[y] * 100) for y, v in
            ctx.col("spending/budget_function.csv", "social_policy")
            if y in gdp and gdp[y]]


def _net_per_1000(ctx):
    """The UN/WB modelled net migration per 1,000 of its own population."""
    pop = dict(ctx.col("demography/population_wb.csv", "population"))
    return [(y, v / pop[y] * 1000) for y, v in
            ctx.col("migration/net_migration.csv", "net_migration")
            if y in pop and pop[y]]


def _migrant_share(ctx):
    """UN DESA's migrant stock over the UN population, in per cent."""
    pop = dict(ctx.col("demography/population_wb.csv", "population"))
    return [(y, v / pop[y] * 100) for y, v in
            ctx.col("migration/migrant_stock.csv", "migrant_stock")
            if y in pop and pop[y]]
