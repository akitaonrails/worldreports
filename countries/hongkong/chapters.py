"""The Hong Kong chapters: the cards, their copy and the headline figures.

Editorial copy lives here. Every number is read from this country's CSVs at
build time by the context, so a figure on a card and the same figure on its
plate cannot disagree; nothing below is typed in.

Twelve chapters on the shared spine. Six rest on Hong Kong's own publishers —
C&SD, the HKMA and the Department of Health — and several carry the harmonised
international reading beside them on a plate. Three chapters say plainly that
a canonical panel is pending: the Gini, the poverty rate and the statutory
minimum wage are published in reports and Gazette notices with no machine-
readable official series; the ten-year yield has no continuous benchmark;
gross migration, the foreign-born share, suicide and road deaths are not
published as series at all. Trade slot 1, net migration and the demography
components panel wait on the atlas's shared scales, and say so.

`kind` says whether a figure is current: 'flow' for an annual total, 'level'
for a stock or a rate read at a moment.
"""
from __future__ import annotations

EN, PT, ZH = "en", "pt", "zh-Hant"
MONEY, WORLD, PEOPLE = "money", "world", "people"


def T(ctx, en, pt, zh):
    """One piece of copy in the three languages this page publishes."""
    return ctx.text(**{EN: en, PT: pt, ZH: zh})


def S(en, pt, zh):
    """A figure's label, in the three languages."""
    return {EN: en, PT: pt, ZH: zh}


def _gce_total(ctx):
    """Government consumption as a share of GDP, from the total row only.

    `spending/gce_function.csv` is tidy — nine functions per year — so the
    rows are filtered on the publisher's own total code rather than on
    position, which would silently take whichever function came last.
    """
    t = ctx.c.table("spending/gce_function.csv")
    gdp = dict(ctx.col("macro/gdp.csv", "nominal_hkd_mn"))
    out = {}
    for y, fn, v in zip(t["year"], t["function"], t["spending_hkd_mn"]):
        if fn == "GCE" and v == v and gdp.get(y):
            out[y] = v / gdp[y] * 100
    return sorted(out.items())


def _q4(ctx, path, col):
    """(year, value) at each year-end, from a quarterly file.

    The HKMA's table is ordered Q4, Q2, Q1, Q3 within a year, so reading a
    column by position would publish the third quarter as the year-end.
    """
    t = ctx.c.table(path)
    return sorted((y, v) for y, q, v in zip(t["year"], t["quarter"], t[col])
                  if q == "Q4" and v == v)


def headline(ctx) -> list[dict]:
    """The figures the page leads with, above the plates."""
    return [
        ctx.stat(S("GDP", "PIB", "本地生產總值"),
                 ctx.col("world/gdp_usd.csv", "gdp_usd_bn"), "usd_bn"),
        ctx.stat(S("GDP per person, US$", "PIB por pessoa, US$",
                   "人均本地生產總值（美元）"),
                 ctx.col("world/gdp_usd.csv", "gdp_per_person_usd"), "count"),
        ctx.stat(S("Population", "População", "人口"),
                 [(y, v / 1e6) for y, v in
                  ctx.col("demography/population.csv", "population")],
                 "pop_mn", kind="level"),
        ctx.stat(S("Budget balance, financial year",
                   "Saldo orçamental, ano fiscal",
                   "財政年度預算盈餘"),
                 [(y, v / 1e3) for y, v in
                  ctx.col("fiscal/govt.csv", "balance_hkd_mn")],
                 "money_bn"),
        ctx.stat(S("Base Rate", "Taxa básica", "基準利率"),
                 ctx.col("markets/base_rate.csv", "base_rate_pct"), "pct2",
                 kind="level"),
        ctx.stat(S("Consumer price inflation", "Inflação dos preços",
                   "消費物價通脹"),
                 ctx.col("macro/cpi.csv", "cpi_yoy_pct"), "pct"),
        ctx.stat(S("Human Development Index",
                   "Índice de Desenvolvimento Humano", "人類發展指數"),
                 ctx.col("world/hdi.csv", "hdi"), "dec3", kind="level"),
        ctx.stat(S("Official reserves", "Reservas oficiais", "官方儲備"),
                 [(y, v / 1e3) for y, v in
                  ctx.col("world/reserves.csv", "reserves_usd_mn")],
                 "usd_bn", kind="level"),
    ]


def build(ctx) -> list[dict]:
    gce_total = _gce_total(ctx)
    return [
        {
            "id": "01-economy", "topic": "economy", "n": "01",
            "family": MONEY,
            "title": T(ctx, "The Economy", "A economia", "經濟"),
            "blurb": T(
                ctx,
                "Four downturns in twenty years and a price level that barely "
                "moved: the peg imports American interest rates, so Hong "
                "Kong's cycles arrive from outside.",
                "Quatro quedas em vinte anos e um nível de preços que quase "
                "não se moveu: a paridade importa as taxas americanas, por "
                "isso os ciclos de Hong Kong chegam de fora.",
                "二十年間四次下滑，而物價幾乎不動：聯繫匯率把美國利率輸入，"
                "香港的周期因此來自外面。"),
            "spark": ctx.col("macro/gdp.csv", "real_growth_pct"),
            "stats": [
                ctx.stat(S("Real growth", "Crescimento real", "實質增長"),
                         ctx.col("macro/gdp.csv", "real_growth_pct"),
                         "pct_s"),
                ctx.stat(S("GDP per person, US$", "PIB por pessoa, US$",
                           "人均本地生產總值（美元）"),
                         ctx.col("world/gdp_usd.csv", "gdp_per_person_usd"),
                         "count"),
                ctx.stat(S("Unemployment", "Desemprego", "失業率"),
                         ctx.col("macro/labour.csv",
                                 "unemployment_rate_pct"), "pct"),
            ],
        },
        {
            "id": "02-fiscal", "topic": "fiscal", "n": "02",
            "family": MONEY,
            "title": T(ctx, "The Public Books", "As contas públicas",
                       "公共財政"),
            "blurb": T(
                ctx,
                "Two perimeters that disagree, both correctly: the "
                "government's cash account and the IMF's consolidated general "
                "government are drawn side by side, never joined.",
                "Dois perímetros que discordam, ambos com razão: a conta de "
                "caixa do governo e o governo geral consolidado do FMI são "
                "desenhados lado a lado, nunca juntados.",
                "兩套範圍各說各話，而兩者都對：政府的現金帳目與國際貨幣基金"
                "組織合併後的一般政府並列而畫，從不合併。"),
            "spark": ctx.col("fiscal/govt.csv", "balance_hkd_mn"),
            "stats": [
                ctx.stat(S("Cash balance", "Saldo de caixa", "現金盈餘"),
                         [(y, v / 1e3) for y, v in
                          ctx.col("fiscal/govt.csv", "balance_hkd_mn")],
                         "money_bn"),
                ctx.stat(S("Gross debt, general government",
                           "Dívida bruta, governo geral", "一般政府債務總額"),
                         ctx.col("fiscal/gg_imf.csv", "gross_debt_pct_gdp"),
                         "pct_gdp"),
                ctx.stat(S("Interest paid", "Juros pagos", "利息支出"),
                         ctx.col("fiscal/gg_imf.csv", "interest_pct_gdp"),
                         "pct2"),
            ],
        },
        {
            "id": "03-spending", "topic": "spending", "n": "03",
            "family": MONEY,
            "title": T(ctx, "Where the Money Goes", "Para onde vai o dinheiro",
                       "錢往何處去"),
            "blurb": T(
                ctx,
                "Health and public order take half of what the government "
                "consumes. Social protection reads near zero because the "
                "pensions and allowances are transfers, and transfers are "
                "outside this table.",
                "Saúde e ordem pública levam metade do que o governo consome. "
                "A proteção social lê perto de zero porque as pensões e os "
                "subsídios são transferências, e as transferências estão fora "
                "desta tabela.",
                "衞生與公共秩序合共佔政府消費的一半。社會保障讀來接近零，因為"
                "退休金與津貼都是現金轉移，而轉移不在此表之內。"),
            "spark": list(gce_total),
            "stats": [
                ctx.stat(S("Government consumption", "Consumo do governo",
                           "政府消費"), gce_total, "pct_gdp"),
                ctx.stat(S("Whole-economy investment",
                           "Investimento da economia", "整體經濟投資"),
                         ctx.col("spending/investment.csv", "gfcf_pct_gdp"),
                         "pct_gdp"),
                ctx.stat(S("Public investment", "Investimento público",
                           "公共投資"),
                         ctx.col("spending/investment.csv",
                                 "public_gfcf_pct_gdp"), "pct_gdp"),
            ],
        },
        {
            "id": "04-trade", "topic": "trade", "n": "04",
            "family": MONEY,
            "title": T(ctx, "Trade", "Comércio", "貿易"),
            "blurb": T(
                ctx,
                "An entrepot re-exports what it imports, so exports and "
                "imports each run near twice the economy. The Mainland takes "
                "six of every ten dollars of goods; the United States took one "
                "in seven in 2006 and one in sixteen now.",
                "Um entreposto reexporta o que importa, por isso as "
                "exportações e as importações andam perto do dobro da "
                "economia. A China continental leva seis de cada dez dólares "
                "em bens; os Estados Unidos levavam um em sete em 2006 e um em "
                "dezasseis hoje.",
                "轉口港進口什麼就轉口什麼，所以出口與進口各約等於經濟規模的兩倍。"
                "中國內地拿走每十元貨物出口中的六元；美國在2006年拿走七分之一，"
                "如今是十六分之一。"),
            "spark": ctx.col("trade/trade_gdp.csv", "exports_gnfs_pct_gdp"),
            "stats": [
                ctx.stat(S("Exports, goods and services",
                           "Exportações, bens e serviços", "出口，貨物與服務"),
                         ctx.col("trade/trade_gdp.csv",
                                 "exports_gnfs_pct_gdp"), "pct_gdp"),
                ctx.stat(S("Trade balance", "Saldo comercial", "貿易差額"),
                         ctx.col("trade/trade_gdp.csv", "balance_pct_gdp"),
                         "pct_gdp_s"),
                ctx.stat(S("Merchandise exports, customs basis",
                           "Exportações de mercadorias, alfândega",
                           "商品出口，海關基準"),
                         [(y, v / 1e3) for y, v in
                          ctx.col("trade/merchandise.csv", "exports_hkd_mn")],
                         "money_bn"),
            ],
        },
        {
            "id": "05-markets", "topic": "markets", "n": "05",
            "family": MONEY,
            "title": T(ctx, "Money and Markets", "Moeda e mercados",
                       "貨幣與市場"),
            "blurb": T(
                ctx,
                "The Base Rate is the Fed's upper bound plus 50 basis points "
                "and the spot rate is held between 7.75 and 7.85: Hong Kong "
                "has no independent monetary policy to chart, so the plate "
                "charts the consequence instead.",
                "A taxa básica é o limite superior da Fed mais 50 pontos base "
                "e a taxa à vista é mantida entre 7,75 e 7,85: Hong Kong não "
                "tem política monetária própria para desenhar, por isso a "
                "prancha desenha a consequência.",
                "基準利率是聯儲局目標上限加50基點，現貨匯率守在7.75至7.85"
                "之間：香港沒有獨立的貨幣政策可畫，圖板畫的是後果。"),
            "spark": ctx.col("markets/base_rate.csv", "base_rate_pct"),
            "stats": [
                ctx.stat(S("Base Rate", "Taxa básica", "基準利率"),
                         ctx.col("markets/base_rate.csv", "base_rate_pct"),
                         "pct2", kind="level"),
                ctx.stat(S("HKD per US$", "HKD por US$", "港元兌美元"),
                         ctx.col("markets/fx.csv", "hkd_per_usd"), "dec2",
                         kind="level"),
                ctx.stat(S("Hang Seng Index, year-end",
                           "Hang Seng, fim de ano", "恒生指數，年底"),
                         ctx.col("markets/equity.csv", "hsi_close"), "count",
                         kind="level"),
            ],
        },
        {
            "id": "06-credit", "topic": "credit", "n": "06",
            "family": MONEY,
            "title": T(ctx, "Credit", "Crédito", "信貸"),
            "blurb": T(
                ctx,
                "Household debt rose 45 points of GDP in sixteen years and has "
                "turned; classified loans are still under 2%. A savings "
                "account paid a hundredth of a percentage point for a decade.",
                "A dívida das famílias subiu 45 pontos do PIB em dezasseis "
                "anos e já virou; os créditos classificados continuam abaixo "
                "de 2%. Uma conta poupança pagou um centésimo de ponto durante "
                "uma década.",
                "住戶債務十六年間升了45個百分點，現已回落；特定分類貸款仍在2%"
                "以下。儲蓄存款利率曾連續十年只有百分之一厘。"),
            "spark": ctx.col("credit/household_debt.csv",
                             "household_debt_pct_gdp"),
            "stats": [
                ctx.stat(S("Household debt", "Dívida das famílias", "住戶債務"),
                         ctx.col("credit/household_debt.csv",
                                 "household_debt_pct_gdp"), "pct_gdp"),
                ctx.stat(S("Classified loans", "Créditos classificados",
                           "特定分類貸款"),
                         _q4(ctx, "credit/classified_loans.csv",
                             "classified_loans_pct"), "pct2"),
                ctx.stat(S("Best lending rate", "Taxa preferencial",
                           "最優惠利率"),
                         ctx.col("markets/lending_rate.csv",
                                 "best_lending_rate_pct"), "pct2",
                         kind="level"),
            ],
        },
        {
            "id": "07-people", "topic": "people", "n": "07",
            "family": PEOPLE,
            "title": T(ctx, "People", "Pessoas", "人民"),
            "blurb": T(
                ctx,
                "Hong Kong publishes a Gini, a poverty rate and a minimum "
                "wage — in a census report, a poverty report and a Gazette "
                "notice. None has a machine-readable official series, so the "
                "three panels say so and the lens carries the median household "
                "income that does.",
                "Hong Kong publica um Gini, uma taxa de pobreza e um salário "
                "mínimo — num relatório censitário, num relatório de pobreza e "
                "num aviso da Gazette. Nenhum tem série oficial legível por "
                "máquina, por isso os três painéis dizem-no e a lente leva a "
                "mediana dos agregados, que tem.",
                "香港有堅尼系數、貧窮率和最低工資——分別在普查報告、貧窮報告和"
                "憲報公告裡。三者都沒有機器可讀的官方系列，所以三格如實說明，"
                "透鏡格則載有確實存在的住戶收入中位數。"),
            "spark": ctx.col("people/income.csv",
                             "median_household_income_real_2024_hkd"),
            "stats": [
                ctx.stat(S("Median household income",
                           "Rendimento mediano do agregado", "住戶收入中位數"),
                         ctx.col("people/income.csv",
                                 "median_household_income_hkd"), "money"),
                ctx.stat(S("In 2024 prices", "A preços de 2024",
                           "以2024年價格計"),
                         ctx.col("people/income.csv",
                                 "median_household_income_real_2024_hkd"),
                         "money"),
                ctx.stat(S("Real change since 2006", "Variação real desde 2006",
                           "自2006年的實質變動"),
                         [(y, v / 25148 * 100) for y, v in
                          ctx.col("people/income.csv",
                                  "median_household_income_real_2024_hkd")],
                         "index"),
            ],
        },
        {
            "id": "08-world", "topic": "world", "n": "08",
            "family": WORLD,
            "title": T(ctx, "Hong Kong in the World", "Hong Kong no mundo",
                       "香港在世界"),
            "blurb": T(
                ctx,
                "An economy of seven and a half million people with reserves "
                "larger than its annual output. Every international body "
                "reports it as HKG, never inside CHN.",
                "Uma economia de sete milhões e meio de pessoas, com reservas "
                "maiores do que a produção de um ano. Todos os organismos "
                "internacionais a reportam como HKG, nunca dentro de CHN.",
                "七百五十萬人的經濟體，外匯儲備更勝一年的產出。所有國際機構都以"
                " HKG 單獨列報，從不歸入 CHN。"),
            "spark": ctx.col("world/gdp_usd.csv", "gdp_usd_bn"),
            "stats": [
                ctx.stat(S("GDP", "PIB", "本地生產總值"),
                         ctx.col("world/gdp_usd.csv", "gdp_usd_bn"), "usd_bn"),
                ctx.stat(S("Human Development Index", "IDH", "人類發展指數"),
                         ctx.col("world/hdi.csv", "hdi"), "dec3",
                         kind="level"),
                ctx.stat(S("Official reserves", "Reservas oficiais",
                           "官方儲備"),
                         [(y, v / 1e3) for y, v in
                          ctx.col("world/reserves.csv", "reserves_usd_mn")],
                         "usd_bn", kind="level"),
            ],
        },
        {
            "id": "09-demography", "topic": "demography", "n": "09",
            "family": PEOPLE,
            "title": T(ctx, "Demography", "Demografia", "人口"),
            "blurb": T(
                ctx,
                "Deaths have exceeded births since 2020 and the fertility rate "
                "is a third of replacement. What keeps the count near seven "
                "and a half million is movement across the border, and that is "
                "a policy, not a trend.",
                "As mortes superam os nascimentos desde 2020 e a fecundidade é "
                "um terço da substituição. O que mantém a contagem perto de "
                "sete milhões e meio é o movimento através da fronteira, e "
                "isso é política, não tendência.",
                "自2020年起死亡多於出生，生育率只有替代水平的三分之一。把人口守在"
                "七百五十萬上下的是跨境流動，而那是政策，不是趨勢。"),
            "spark": ctx.col("demography/population.csv", "population"),
            "stats": [
                ctx.stat(S("Population", "População", "人口"),
                         [(y, v / 1e6) for y, v in
                          ctx.col("demography/population.csv", "population")],
                         "pop_mn", kind="level"),
                ctx.stat(S("Fertility rate", "Fecundidade", "總和生育率"),
                         ctx.col("demography/fertility.csv", "tfr"), "dec2"),
                ctx.stat(S("Crude death rate", "Taxa bruta de mortalidade",
                           "粗死亡率"),
                         ctx.col("demography/vital.csv",
                                 "death_rate_per_1000"), "dec2"),
            ],
        },
        {
            "id": "10-security", "topic": "security", "n": "10",
            "family": PEOPLE,
            "title": T(ctx, "Security", "Segurança", "治安"),
            "blurb": T(
                ctx,
                "Reported offences restart in 2021, when the police re-based "
                "their classification, and 2025 carries a single quarter that "
                "no other quarter resembles.",
                "Os crimes registados recomeçam em 2021, quando a polícia refez "
                "a classificação, e 2025 traz um trimestre que não se parece "
                "com nenhum outro.",
                "舉報罪案自2021年重新開始，那年警方重訂分類；2025年有一季與其他"
                "任何一季都不相似。"),
            "spark": ctx.col("security/crime.csv", "total_cases"),
            "stats": [
                ctx.stat(S("Homicide rate", "Taxa de homicídio", "兇殺率"),
                         ctx.col("security/crime.csv",
                                 "homicide_rate_per_100k"), "per100k2"),
                ctx.stat(S("Reported offences", "Crimes registados",
                           "舉報罪案"),
                         ctx.col("security/crime.csv", "total_cases"),
                         "count"),
                ctx.stat(S("Violent offences", "Crimes violentos", "暴力罪案"),
                         ctx.col("security/crime.csv",
                                 "violent_crime_cases"), "count"),
            ],
        },
        {
            "id": "11-mortality", "topic": "mortality", "n": "11",
            "family": PEOPLE,
            "title": T(ctx, "Mortality", "Mortalidade", "死亡"),
            "blurb": T(
                ctx,
                "The fifth wave killed 9,291 people in 2022 with COVID-19 as "
                "the underlying cause — 126 per 100,000 — and took two and a "
                "half years off male life expectancy in a single year.",
                "A quinta vaga matou 9.291 pessoas em 2022 com a COVID-19 como "
                "causa básica — 126 por 100 mil — e tirou dois anos e meio à "
                "esperança de vida masculina num só ano.",
                "第五波在2022年奪去9,291人，根本死因為2019冠狀病毒病——每十萬人"
                "126宗——男性預期壽命一年之內少了兩年半。"),
            "spark": ctx.col("mortality/deaths.csv",
                             "excess_deaths_pct_vs_2015_2019"),
            "stats": [
                ctx.stat(S("Crude death rate", "Taxa bruta de mortalidade",
                           "粗死亡率"),
                         ctx.col("mortality/deaths.csv",
                                 "crude_death_rate_per_1000"), "dec2"),
                ctx.stat(S("Excess deaths", "Excesso de mortes", "超額死亡"),
                         ctx.col("mortality/deaths.csv",
                                 "excess_deaths_pct_vs_2015_2019"), "pct_s"),
                ctx.stat(S("Life expectancy, women",
                           "Esperança de vida, mulheres", "預期壽命，女性"),
                         ctx.col("demography/vital.csv",
                                 "life_expectancy_female"), "years",
                         kind="level"),
            ],
        },
        {
            "id": "12-migration", "topic": "migration", "n": "12",
            "family": PEOPLE,
            "title": T(ctx, "Migration", "Migração", "遷移"),
            "blurb": T(
                ctx,
                "There is no gross immigration series: what C&SD publishes is "
                "the residual after births and deaths, split into one-way "
                "permit holders from the Mainland and everyone else. In 2020 "
                "the second group left 96,000 people behind.",
                "Não há série de imigração bruta: o que o C&SD publica é o "
                "resíduo depois dos nascimentos e óbitos, dividido entre "
                "titulares de autorização de sentido único vindos do "
                "continente e todos os outros. Em 2020 o segundo grupo deixou "
                "96.000 pessoas atrás.",
                "沒有總流入的系列：政府統計處公布的是出生與死亡之後的餘額，再分為"
                "內地單程通行證持有人與其他所有人。2020年第二組淨走了九萬六千人。"),
            "spark": ctx.col("migration/net_movement.csv",
                             "net_movement_per_1000"),
            "stats": [
                ctx.stat(S("Net movement, per 1,000",
                           "Movimento líquido, por 1.000", "淨遷移，每千人"),
                         ctx.col("migration/net_movement.csv",
                                 "net_movement_per_1000"), "dec2"),
                ctx.stat(S("One-way permit holders",
                           "Titulares de sentido único", "單程通行證持有人"),
                         [(y, v * 1000) for y, v in
                          ctx.col("migration/net_movement.csv",
                                  "one_way_permit_k")], "count"),
                ctx.stat(S("Everyone else", "Todos os outros", "其他所有人"),
                         [(y, v * 1000) for y, v in
                          ctx.col("migration/net_movement.csv", "others_k")],
                         "count"),
            ],
        },
    ]
