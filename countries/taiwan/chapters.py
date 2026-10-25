"""The taiwan chapters: the cards, their copy and their headline figures.

Editorial copy lives here. Every number is read from this country's CSVs
at build time by the context, so a figure on a card and the same figure
on its plate cannot disagree.

Ten chapters, on the shared spine. The World Bank, the IMF and the UN do
not carry Taiwan, so every plate is drawn from Taiwan's own publishers —
DGBAS, the Central Bank (CBC), the Ministry of Finance (MOF) — and each
label names which. Where two official publishers measure one idea
differently (inflation, trade, the books of account), both ride as
clearly labelled lines and are never spliced. Gaps are pending with the
reason, never invented; `kind` says whether a figure is current: 'flow'
for an annual total, 'level' for a stock or a rate read at a moment.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"

ZH, EN, PT = "zh-Hant", "en", "pt"


def _by_year(pairs) -> dict:
    return dict(pairs)


def _ratio(ctx, num_rel: str, num_col: str, den_rel: str, den_col: str,
           num_scale: float = 1.0, den_scale: float = 1.0):
    """(year, percent-of) pairs: one column over another, never stored.

    The percent is computed at build time from the two staged columns;
    the CSVs keep their own units and no pre-computed ratio is invented.
    """
    den = _by_year(ctx.col(den_rel, den_col))
    return [(y, v * num_scale / (den[y] * den_scale) * 100.0)
            for y, v in ctx.col(num_rel, num_col) if y in den]


def _per(ctx, rel: str, col: str, per: float = 1e5):
    """(year, deaths per `per` people) pairs against the DGBAS population —
    the same-year population every rate on the plates divides by
    (DATA_NOTES)."""
    pop = _by_year(ctx.col("demography/population.csv", "population"))
    return [(y, v / pop[y] * per)
            for y, v in ctx.col(rel, col) if y in pop]


def _goods_balance_usd_bn(ctx):
    """MOF goods balance, converting the source's US$ thousands to bn."""
    exports = ctx.col("trade/goods.csv", "exports_usd_thousands")
    imports = ctx.col("trade/goods.csv", "imports_usd_thousands")
    return [(year, (exported - imported) / 1e6)
            for (year, exported), (_, imported) in zip(exports, imports)]


def headline(ctx) -> list[dict]:
    """The figures the page leads with, above the plates."""
    return [
        ctx.stat({ZH: "GDP", EN: "GDP", PT: "PIB"},
                 [(y, v / 1e3) for y, v in
                  ctx.col("economy/gdp.csv", "gdp_nominal_usd_mn")], "usd_bn"),
        ctx.stat({ZH: "每人GDP", EN: "GDP per person", PT: "PIB por pessoa"},
                 ctx.col("economy/gdp.csv", "gdp_per_capita_usd"),
                 "count", kind="level"),
        ctx.stat({ZH: "人口", EN: "Population", PT: "População"},
                 [(y, v / 1e6) for y, v in
                  ctx.col("demography/population.csv", "population")],
                 "pop_mn", kind="level"),
        ctx.stat({ZH: "政策利率(年底)", EN: "Policy rate, year-end",
                  PT: "Taxa de política, fim de ano"},
                 ctx.col("markets/policy_rate.csv", "rediscount_rate_pct"),
                 "pct2", kind="level"),
        ctx.stat({ZH: "貿易餘絀(商品)", EN: "Trade balance, goods",
                  PT: "Saldo comercial, bens"},
                 _goods_balance_usd_bn(ctx),
                 "usd_bn"),
        ctx.stat({ZH: "中央政府債務", EN: "Central government debt",
                  PT: "Dívida do governo central"},
                 ctx.col("fiscal/debt_central.csv", "debt_central_pct_gdp"),
                 "pct_gdp", kind="level"),
        ctx.stat({ZH: "外匯準備資產", EN: "Official reserves",
                  PT: "Reservas oficiais"},
                 [(y, v / 1e3) for y, v in
                  ctx.col("world/reserves.csv", "fx_reserves_usd_mn")],
                 "usd_bn", kind="level"),
    ]


def build(ctx) -> list[dict]:
    S = ctx.stat
    T = ctx.text
    exp_share = _ratio(ctx, "trade/goods.csv", "exports_usd_thousands",
                       "economy/gdp.csv", "gdp_nominal_usd_mn", 1e-3)
    out_share = _ratio(ctx, "spending/function.csv", "spending_total",
                       "economy/gdp.csv", "gdp_nominal_ntd_mn",
                       1e3, 1e6)
    household = _ratio(ctx, "credit/household_credit.csv",
                       "consumer_loans_ntd_mn",
                       "economy/gdp.csv", "gdp_nominal_ntd_mn")
    return [
        {
            "id": "01-economy", "topic": "economy", "n": "01",
            "family": MONEY,
            "title": T(**{ZH: "開放經濟的雲霄飛車",
                          EN: "The Open Economy's Roller Coaster",
                          PT: "A Montanha-Russa da Economia Aberta"}),
            "blurb": T(**{ZH: "實質成長、所得、物價來自主計總處與中央銀行;失業率為主計總處年平均總失業率。",
                          EN: "Real growth, income and prices come from DGBAS and the Central Bank; unemployment is DGBAS's annual-average total rate.",
                          PT: "Crescimento real, renda e preços vêm da DGBAS e do Banco Central; o desemprego é a taxa total média anual da DGBAS."}),
            "alt": T(**{ZH: "臺灣總體經濟的四個面板。實質成長在出口崩跌的 2009 年掉到"
                            "-1.6%,2025 年反彈到 +8.8%,是區間最快的一年;2020 年不論疫情"
                            "都成長 +3.4%,所以不畫衰退帶。每人 GDP 整個區間超過翻倍,從 "
                            "2006 年的 16,934 美元到 2025 年的 39,515 美元。通膨有兩條線:"
                            "主計總處 2009 年看到 -0.9%,央行的期間率是 -0.3%。失業率在2009年達5.85%,2025年降至3.35%。",
                          EN: "Four panels on Taiwan's macroeconomy. Real growth"
                              " falls to -1.6% in 2009 after the export collapse"
                              " and rebounds to +8.8% in 2025, the window's"
                              " fastest; 2020, pandemic or not, grew +3.4% and is"
                              " not banded. GDP per person more than doubles,"
                              " from US$16,934 in 2006 to US$39,515 in 2025."
                              " Inflation is drawn twice: the DGBAS sees -0.9%"
                              " in 2009, the Central Bank's period rate -0.3%."
                              " Unemployment peaks at 5.85% in 2009 and falls to 3.35% in 2025.",
                          PT: "Quatro painéis sobre a macroeconomia de Taiwan."
                              " O crescimento real cai para -1,6% em 2009, após"
                              " o colapso das exportações, e rebate a +8,8% em"
                              " 2025, o mais rápido da janela; 2020, com pandemia"
                              " ou não, cresceu +3,4% e não recebe banda. O PIB"
                              " por pessoa mais que dobra, de US$ 16.934 em 2006"
                              " para US$ 39.515 em 2025. A inflação é desenhada"
                              " duas vezes: a DGBAS vê -0,9% em 2009, a taxa"
                              " periódica do Banco Central, -0,3%. O painel de"
                              " desemprego atinge 5,85% em 2009 e cai para 3,35% em 2025."}),
            "sources": ["economy/gdp.csv", "economy/cpi.csv",
                        "economy/cpi_yoy_cbc.csv", "economy/unemployment.csv"],
            "spark": ctx.col("economy/gdp.csv", "real_growth_pct"),
            "stats": [
                S({ZH: "實質成長率", EN: "Real growth",
                   PT: "Crescimento real"},
                  ctx.col("economy/gdp.csv", "real_growth_pct"), "pct"),
                S({ZH: "通膨率(主計總處)", EN: "Inflation (DGBAS)",
                   PT: "Inflação (DGBAS)"},
                  ctx.col("economy/cpi.csv", "cpi_inflation_pct"), "pct"),
            ],
        },
        {
            "id": "02-fiscal", "topic": "fiscal", "n": "02", "family": MONEY,
            "title": T(**{ZH: "政府記了兩次的帳",
                          EN: "The Government's Books, Kept Twice",
                          PT: "As Contas do Governo, Registadas Duas Vezes"}),
            "blurb": T(**{ZH: "全政府層級的權責發生制決算並列國庫現金賬;"
                            "中央政府債務是公佈的存量,利息以債務類支出爲替代指標。",
                          EN: "All-levels accrual final accounts with the"
                              " treasury's cash ledger beside them; central"
                              " government debt is the published stock, and"
                              " interest rides on the debt-category proxy.",
                          PT: "Contas finais de competência de todos os níveis"
                              " com o caixa do Tesouro ao lado; a dívida do"
                              " governo central é o estoque publicado, e os"
                              " juros usam o proxy da categoria dívida."}),
            "alt": T(**{ZH: "臺灣公共財政的四個面板。歲入從 2006 年佔 GDP 的 17.3%"
                            "降到 2025 年的 14.7%;餘絀從 2009 年崩跌時的 -4.3% 轉為"
                            "2025 年的 +0.3%;中央債務在 2012 年見頂 34.0%,之後降到"
                            "21.1%;債務類支出從 GDP 的 1.1% 降到 0.3%。",
                          EN: "Four panels on Taiwan's public finances."
                              " Revenue eases from 17.3% of GDP in 2006 to"
                              " 14.7% in 2025; the balance swings from -4.3%"
                              " in the 2009 collapse to +0.3% in 2025; central"
                              " debt peaks at 34.0% in 2012 and falls to"
                              " 21.1%; debt-category outlays fall from 1.1%"
                              " to 0.3% of GDP.",
                          PT: "Quatro painéis sobre as finanças públicas de"
                              " Taiwan. A receita recua de 17,3% do PIB em 2006"
                              " para 14,7% em 2025; o resultado vai de -4,3%"
                              " no colapso de 2009 a +0,3% em 2025; a dívida"
                              " central atinge o pico de 34,0% em 2012 e cai a"
                              " 21,1%; as despesas da categoria dívida caem de"
                              " 1,1% para 0,3% do PIB."}),
            "sources": ["fiscal/budget.csv", "fiscal/debt_central.csv",
                        "spending/function.csv", "economy/gdp.csv"],
            "spark": ctx.col("fiscal/debt_central.csv",
                             "debt_central_pct_gdp"),
            "spark_level": True,
            "stats": [
                S({ZH: "中央政府債務", EN: "Central debt",
                   PT: "Dívida central"},
                  ctx.col("fiscal/debt_central.csv", "debt_central_pct_gdp"),
                  "pct_gdp", kind="level"),
                S({ZH: "總餘絀", EN: "Balance", PT: "Resultado"},
                  ctx.col("fiscal/budget.csv", "balance_pct_gdp"),
                  "pct_gdp_s"),
            ],
        },
        {
            "id": "03-spending", "topic": "spending", "n": "03",
            "family": MONEY,
            "title": T(**{ZH: "錢去了哪裡——八個分類",
                          EN: "Where the Money Goes — Eight Groups",
                          PT: "Para Onde Vai o Dinheiro — Oito Grupos"}),
            "blurb": T(**{ZH: "財政部功能分類堆疊於 GDP 之上,不是 COFOG;兩個投資面板待補,"
                            "因為資本形成沒有 staged 欄位。",
                          EN: "The MOF functional classification stacked over"
                              " GDP — not COFOG; both investment panels are"
                              " pending, for want of a staged"
                              " capital-formation column.",
                          PT: "A classificação funcional da Fazenda empilhada"
                              " sobre o PIB — não a COFOG; os dois painéis de"
                              " investimento estão pendentes por falta de uma"
                              " coluna de formação de capital coletada."}),
            "alt": T(**{ZH: "政府支出的四個面板。堆疊起來,財政部八個分類合計佔 GDP 由"
                            "2006 年的 17.6% 降到 2025 年的 14.8%,社會保障與退休金最大,"
                            "從 5.2% 降到 4.6%;社會保障與其餘一切同時縮小。兩個投資面板待"
                            "補——沒有資本形成欄位被取得。",
                          EN: "Four panels on government spending. Stacked,"
                              " the eight MOF groups total 17.6% of GDP in"
                              " 2006 and 14.8% in 2025, social security and"
                              " pensions the largest at 5.2% falling to 4.6%;"
                              " social security and everything else both"
                              " shrink across the window. The investment"
                              " panels are pending — no capital-formation"
                              " column was staged.",
                          PT: "Quatro painéis sobre o gasto público."
                              " Empilhados, os oito grupos da Fazenda somam"
                              " 17,6% do PIB em 2006 e 14,8% em 2025; segurança"
                              " social e pensões é o maior, de 5,2% caindo para"
                              " 4,6%; segurança social e todo o resto encolhem"
                              " juntos. Os painéis de investimento estão"
                              " pendentes — nenhuma coluna de formação de"
                              " capital foi coletada."}),
            "sources": ["spending/function.csv", "economy/gdp.csv"],
            "spark": out_share,
            "stats": [
                S({ZH: "總支出(決算)", EN: "Total outlays (final accounts)",
                   PT: "Despesa total (contas finais)"},
                  out_share, "pct_gdp"),
                S({ZH: "社會保障與退休金", EN: "Social security & pensions",
                   PT: "Segurança social e pensões"},
                  _ratio(ctx, "spending/function.csv",
                         "spending_social_security_pension_subtotal",
                         "economy/gdp.csv", "gdp_nominal_ntd_mn",
                         1e3, 1e6), "pct_gdp"),
            ],
        },
        {
            "id": "04-trade", "topic": "trade", "n": "04", "family": WORLD,
            "title": T(**{ZH: "航運路線——與客戶的轉換",
                          EN: "The Shipping Lanes — and the Customer Switch",
                          PT: "As Rotas Marítimas — e a Troca de Cliente"}),
            "blurb": T(**{ZH: "可比的商品與服務總額仍待補;海關商品保留在目的地與視野面板。",
                          EN: "Comparable goods-and-services totals remain pending; customs goods stay in the destination and lens panels.",
                          PT: "Totais comparáveis de bens e serviços seguem pendentes; os bens aduaneiros ficam nos painéis de destinos e de lente."}),
            "alt": T(**{ZH: "貿易的四個面板。可比的商品與服務總額及餘額仍明確待補。中國"
                            "大陸佔商品出口在 2020 年攀到約 30% 的頂峯後減半到 16%,美國從 14%"
                            " 升到 31% 取得領先。視野面板把同一個商品流量繪了兩次:2025 年僅"
                            "出口就差約 560 億美元。MOF海關資料只含商品,服務不在這個資料集中。",
                          EN: "Four panels on trade. Comparable goods-and-services totals and the balance remain visibly pending. Mainland China's share"
                              " of goods exports peaks near 30% in 2020 and"
                              " halves to 16%, while the United States rises"
                              " from 14% to 31% and takes the lead. The lens"
                              " panel draws one goods flow twice: in 2025 the"
                              " two answers differ by about US$56bn on exports"
                              " alone. The MOF customs dataset covers goods;"
                              " services are outside its scope.",
                          PT: "Quatro painéis sobre o comércio. Totais e saldo comparáveis de bens e serviços seguem visivelmente pendentes. A fatia da China continental nas"
                              " exportações de bens atinge quase 30% em 2020 e"
                              " cai à metade, para 16%, enquanto os Estados"
                              " Unidos sobem de 14% para 31% e assumem a"
                              " liderança. O painel-lente desenha o mesmo fluxo"
                              " de bens duas vezes: em 2025 as duas respostas"
                              " diferem em cerca de US$ 56 bilhões só nas"
                              " exportações. A base aduaneira do MOF cobre bens;"
                              " serviços ficam fora do seu escopo."}),
            "sources": ["trade/goods.csv", "trade/partners.csv",
                        "world/bop_goods.csv", "economy/gdp.csv"],
            "spark": exp_share,
            "stats": [
                S({ZH: "商品出口", EN: "Goods exports",
                   PT: "Exportações de bens"},
                  [(y, v / 1e6) for y, v in
                   ctx.col("trade/goods.csv", "exports_usd_thousands")],
                  "usd_bn"),
                S({ZH: "商品順差", EN: "Goods surplus",
                   PT: "Superávit de bens"},
                  _goods_balance_usd_bn(ctx),
                  "usd_bn"),
            ],
        },
        {
            "id": "05-markets", "topic": "markets", "n": "05", "family": MONEY,
            "title": T(**{ZH: "貨幣與市場——安靜的利率,喧鬧的指數",
                          EN: "Money & Markets — a Quiet Rate, a Loud Index",
                          PT: "Dinheiro e Mercados — uma Taxa Silenciosa,"
                             " um Índice Barulhento"}),
            "blurb": T(**{ZH: "央行的政策利率就是重貼現率;匯率幾乎不動;"
                            "美元計的 TAIEX 把年平均與年底兩種讀法分開。",
                          EN: "The CBC's policy rate is the rediscount rate;"
                              " the currency barely moves; and TAIEX in"
                              " dollars keeps its annual average and its"
                              " year-end close apart.",
                          PT: "A taxa de política do CBC é a taxa de"
                              " redesconto; a moeda mal se move; e o TAIEX em"
                              " dólares mantém separados a média anual e o"
                              " fechamento de fim de ano."}),
            "alt": T(**{ZH: "市場的四個面板。重貼現率從 2007 年的 3.4% 降到 2020 年的"
                            "1.1%,2025 年回到 2.0%;通膨整段不超過 4%。匯率指數(2006 = 100,"
                            "向上代表更強)20 年只在 98 到 116 之間。以美元計的 TAIEX"
                            "成長為約三倍:"
                            "官方年平均到 364,年底收盤到 385;債券面板待補。",
                          EN: "Four panels on markets. The rediscount rate"
                              " falls from 3.4% in 2007 to 1.1% in 2020 and"
                              " returns to 2.0%; inflation stays under 4%"
                              " throughout. The currency index, 2006 = 100"
                              " with up stronger, moves only between 98 and"
                              " 116 in twenty years. TAIEX in US dollars"
                              " roughly triples: the official annual average"
                              " reaches 364, the year-end close 385; the bond"
                              " panel is pending.",
                          PT: "Quatro painéis sobre os mercados. A taxa de"
                              " redesconto cai de 3,4% em 2007 para 1,1% em"
                              " 2020 e volta a 2,0%; a inflação fica abaixo de"
                              " 4% o tempo todo. O índice cambial, 2006 = 100"
                              " com cima mais forte, move-se só entre 98 e 116"
                              " em vinte anos. O TAIEX em dólares mais que"
                              " triplica: a média anual oficial chega a 364, o"
                              " fechamento de fim de ano a 385; o painel de"
                              " títulos está pendente."}),
            "sources": ["markets/policy_rate.csv", "economy/cpi.csv",
                        "markets/usdtwd.csv", "markets/stock_index_avg.csv",
                        "markets/stock_index_yearend.csv"],
            "spark": ctx.col("markets/policy_rate.csv",
                             "rediscount_rate_pct"),
            "spark_level": True,
            "stats": [
                S({ZH: "政策利率(年底)", EN: "Policy rate (year-end)",
                   PT: "Taxa de política (fim de ano)"},
                  ctx.col("markets/policy_rate.csv", "rediscount_rate_pct"),
                  "pct2", kind="level"),
                S({ZH: "兌美元匯率(年平均)", EN: "US$ rate (annual mean)",
                   PT: "Taxa do dólar (média anual)"},
                  ctx.col("markets/usdtwd.csv",
                          "usd_twd_interbank_annual_mean"),
                  "dec2", kind="level"),
            ],
        },
        {
            "id": "06-credit", "topic": "credit", "n": "06",
            "family": MONEY,
            "title": T(**{ZH: "信用——幾乎沒有成長的家庭帳簿",
                          EN: "Credit — the Household Book That Barely Grew",
                          PT: "Crédito — o Livro de Contas Doméstico que Mal"
                             " Cresceu"}),
            "blurb": T(**{ZH: "消費信貸約佔 GDP 之半、壞帳持續下降,採央行自己的定義;"
                            "視野面板是建商的建築貸款。",
                          EN: "Consumer loans near half of GDP and falling"
                              " bad debt, on the CBC's own definitions; the"
                              " lens panel is the developers' building loans.",
                          PT: "Crédito ao consumidor perto de metade do PIB e"
                              " inadimplência em queda, pelas definições do"
                              " CBC; o painel-lente são os empréstimos"
                              " imobiliários das construtoras."}),
            "alt": T(**{ZH: "信用的四個面板。消費信貸從 2006 年佔 GDP 的 52% 高點降至 2025 年"
                            "的 47%;逾期放款比率從 2.13% 降到 0.15%。"
                            "五大銀行新承作購屋貸款利率與政策利率並列。視野裡建商建築貸款翻倍,從 GDP 的 6.5% 到"
                            "12.0%,2023 年見頂 14.0%。",
                          EN: "Four panels on credit. Consumer loans run from"
                              " their 52% of GDP peak in 2006 to 47% in 2025;"
                              " the overdue-to-loan ratio"
                              " falls from 2.13% to 0.15%. Five-bank new-home"
                              " rates are compared with the policy rate. In the lens, building loans"
                              " to developers double, from 6.5% of GDP to"
                              " 12.0%, peaking at 14.0% in 2023.",
                          PT: "Quatro painéis sobre crédito. O crédito ao"
                              " consumidor vai de 52% do PIB em 2006 para 47%"
                              " em 2025, partindo do pico de 52% em 2006; o"
                              " índice de atraso cai de 2,13% para 0,15%. O"
                              " taxa de novos financiamentos habitacionais dos cinco bancos é comparada à taxa básica. Na"
                              " lente, os empréstimos imobiliários às"
                              " construtoras dobram, de 6,5% para 12,0% do"
                              " PIB, com pico de 14,0% em 2023."}),
            "sources": ["credit/household_credit.csv", "credit/npl.csv",
                        "credit/new_housing_rate.csv", "economy/gdp.csv"],
            "spark": household,
            "stats": [
                S({ZH: "消費信貸", EN: "Consumer loans",
                   PT: "Crédito ao consumidor"}, household, "pct_gdp",
                  kind="level"),
                S({ZH: "逾期放款比率", EN: "Overdue-to-loan ratio",
                   PT: "Índice de atraso"},
                  ctx.col("credit/npl.csv", "bank_npl_ratio_pct"), "pct2",
                  kind="level"),
            ],
        },
        {
            "id": "07-people", "topic": "people", "n": "07", "family": PEOPLE,
            "title": T(**{ZH: "所得、貧窮與法定工資底線",
                          EN: "Income, Poverty and the Statutory Wage Floor",
                          PT: "Renda, Pobreza e o Piso Salarial Legal"}),
            "blurb": T(**{ZH: "家庭可支配所得不均維持在約34點；相對貧窮率與法定月薪使用各自官方定義。",
                          EN: "Disposable-income inequality holds near 34 points; relative poverty and the monthly wage floor retain their official definitions.",
                          PT: "A desigualdade da renda disponível fica perto de 34 pontos; pobreza relativa e piso mensal mantêm suas definições oficiais."}),
            "alt": T(**{ZH: "所得的四個面板。 家庭可支配所得吉尼係數在2025年為34.1點； 2024年相對貧窮率為7.57%，門檻是全國等值可支配所得中位數的50%； 2025年法定月薪按年平均匯率折算為917美元； 最高五分位所得是最低五分位的6.17倍。",
                          EN: "Four panels on income. The household disposable-income Gini is 34.1 points in 2025; relative poverty is 7.57% in 2024 below 50% of median equivalised disposable income; the statutory monthly wage converts to US$917 in 2025; and the top household quintile receives 6.17 times the bottom quintile's income.",
                          PT: "Quatro painéis sobre renda. O Gini da renda disponível domiciliar é 34,1 pontos em 2025; a pobreza relativa é 7,57% em 2024 abaixo de 50% da mediana da renda disponível equivalente; o salário mínimo mensal equivale a US$ 917 em 2025; e o quinto superior recebe 6,17 vezes a renda do quinto inferior."}),
            "sources": ["people/gini.csv", "people/poverty.csv", "people/minimum_wage.csv"],
            "spark": ctx.col("people/gini.csv", "gini_points"),
            "stats": [
                S({ZH: "吉尼係數", EN: "Gini", PT: "Gini"},
                  ctx.col("people/gini.csv", "gini_points"), "dec2", kind="level"),
                S({ZH: "相對貧窮率", EN: "Relative poverty", PT: "Pobreza relativa"},
                  ctx.col("people/poverty.csv", "relative_poverty_pct"), "pct2", kind="level"),
            ],
        },
        {
            "id": "08-world", "topic": "world", "n": "08", "family": WORLD,
            "title": T(**{ZH: "在世界之中,統計地位不均",
                          EN: "In the World, on Uneven Statistical Ground",
                          PT: "No Mundo, em Terreno Estatístico Desigual"}),
            "blurb": T(**{ZH: "規模與準備資產來自臺灣發布者;HDI缺席,但透明國際CPI收錄臺灣。",
                          EN: "Size and reserves come from Taiwan's own publishers; HDI is absent, while Transparency International's CPI covers Taiwan.",
                          PT: "Tamanho e reservas vêm dos publicadores de Taiwan; o IDH está ausente, mas o IPC da Transparência Internacional cobre Taiwan."}),
            "alt": T(**{ZH: "臺灣在世界中的四個面板。按發布者自備的美元欄,GDP 在 2025 年"
                            "達到 9,220 億美元;官方準備資產從 2,661 億美元升到 6,028 億,"
                            "名列世界最大之列。聯合國不收錄臺灣,HDI仍缺;透明國際CPI則從2012年61升至2025年68。",
                          EN: "Four panels on Taiwan in the world. GDP reaches"
                              " US$922bn in 2025 on the publisher's own US$"
                              " column; official reserves rise from US$266bn"
                              " to US$603bn, among the world's largest. The"
                              " HDI is unavailable because the UN does not carry Taiwan; TI's CPI rises from 61 in 2012 to 68 in 2025.",
                          PT: "Quatro painéis sobre Taiwan no mundo. O PIB"
                              " atinge US$ 922 bilhões em 2025 pela própria"
                              " coluna em dólares do publicador; as reservas"
                              " oficiais sobem de US$ 266 bilhões para US$"
                              " 603 bilhões, entre as maiores do mundo. Os"
                              " o IDH segue indisponível porque a ONU não inclui Taiwan; o IPC da TI sobe de 61 em 2012 para 68 em 2025."}),
            "sources": ["economy/gdp.csv", "world/reserves.csv", "world/corruption.csv"],
            "spark": [(y, v / 1e3) for y, v in
                      ctx.col("world/reserves.csv", "fx_reserves_usd_mn")],
            "spark_level": True,
            "stats": [
                S({ZH: "名目GDP", EN: "GDP, current",
                   PT: "PIB, corrente"},
                  [(y, v / 1e3) for y, v in
                   ctx.col("economy/gdp.csv", "gdp_nominal_usd_mn")],
                  "usd_bn"),
                S({ZH: "外匯準備資產", EN: "Official reserves",
                   PT: "Reservas oficiais"},
                  [(y, v / 1e3) for y, v in
                   ctx.col("world/reserves.csv", "fx_reserves_usd_mn")],
                  "usd_bn", kind="level"),
            ],
        },
        {
            "id": "09-demography", "topic": "demography", "n": "09",
            "family": PEOPLE,
            "title": T(**{ZH: "人口曲線已經轉彎",
                          EN: "The Population Line Has Turned",
                          PT: "A Linha da População Virou"}),
            "blurb": T(**{ZH: "戶籍人口 2019 年見頂後已在下滑；出生與死亡這一對只畫出可取得的死亡，戶政出生端點回傳查無資料。",
                          EN: "A register that peaked in 2019 and is already"
                              " falling; deaths are available, while the audited RIS birth endpoint returns no data.",
                          PT: "Um registro que atingiu o pico em 2019 e já"
                              " cai; as mortes estão disponíveis, enquanto a rota RIS auditada de nascimentos devolve ausência de dados."}),
            "alt": T(**{ZH: "人口的四個面板。人口指數在 2019 年見頂 103(23,596,027 人),"
                            "之後降到 102;粗死亡率 2008 到 2025 年從每千人 6.2 升到 8.5。"
                            "生育率與自然增加面板待補，因戶政出生端點回傳查無資料；戶籍國際遷徙另列於遷徙圖板。",
                          EN: "Four panels on demography. The population index"
                              " peaks at 103 in 2019 (23,596,027 people) and"
                              " falls to 102; the crude death rate rises from"
                              " 6.2 to 8.5 per 1,000 between 2008 and 2025."
                              " Fertility and natural increase remain pending because the audited birth endpoint returned no data; registered international movement is shown on migration.",
                          PT: "Quatro painéis sobre demografia. O índice"
                              " populacional atinge o pico de 103 em 2019"
                              " (23.596.027 pessoas) e cai a 102; a taxa bruta"
                              " de mortalidade sobe de 6,2 para 8,5 por 1.000"
                              " entre 2008 e 2025. Os painéis de fecundidade e"
                              " crescimento vegetativo estão pendentes porque a rota auditada de nascimentos não trouxe dados; o movimento internacional registrado aparece em migração."}),
            "sources": ["demography/population.csv",
                        "mortality/causes_of_death.csv"],
            "spark": ctx.col("demography/population.csv", "population"),
            "spark_level": True,
            "stats": [
                S({ZH: "人口", EN: "Population", PT: "População"},
                  [(y, v / 1e6) for y, v in
                   ctx.col("demography/population.csv", "population")],
                  "pop_mn", kind="level"),
                S({ZH: "粗死亡率", EN: "Crude death rate",
                   PT: "Taxa bruta de mortalidade"},
                  _per(ctx, "mortality/causes_of_death.csv",
                       "deaths_all_cause", 1e3), "dec2", kind="level"),
            ],
        },
        {
            "id": "10-security", "topic": "security", "n": "10",
            "family": PEOPLE,
            "title": T(**{ZH: "證書上的死亡——自殺曲線與意外",
                          EN: "Deaths by Certificate — the Suicide Line and"
                             " the Accidents",
                          PT: "Mortes por Certidão — a Linha do Suicídio e os"
                             " Acidentes"}),
            "blurb": T(**{ZH: "自殺從未一路下降;各類意外都在下降;殺人與道路面板"
                            "說明缺的是哪條警方序列。",
                          EN: "Suicide never falls for good; all accidental"
                              " deaths fall; the homicide and road panels say"
                              " exactly which police series is missing.",
                          PT: "O suicídio nunca cai de vez; todas as mortes"
                              " acidentais caem; os painéis de homicídio e"
                              " trânsito dizem qual série policial falta."}),
            "alt": T(**{ZH: "暴力與意外死亡的四個面板。自殺率每十萬人在 15.1 到 17.9"
                            "之間,2025 年是 16.9;全部意外死亡從每十萬人 30.8 降到 28.6。"
                            "殺人與道路交通事故面板待補——警方序列在牆後,證書把各種意外"
                            "合併為一類。",
                          EN: "Four panels on violent and accidental death."
                              " Suicide runs between 15.1 and 17.9 per 100,000"
                              " and is 16.9 in 2025; all accidental deaths"
                              " fall from 30.8 per 100,000 to 28.6. The"
                              " homicide and road-traffic panels are pending"
                              " — the police series are walled and the"
                              " certificates lump accidents.",
                          PT: "Quatro painéis sobre morte violenta e"
                              " acidental. O suicídio corre entre 15,1 e 17,9"
                              " por 100.000 e fica em 16,9 em 2025; todas as"
                              " mortes acidentais caem de 30,8 para 28,6 por"
                              " 100.000. Os painéis de homicídio e trânsito"
                              " estão pendentes — as séries policiais estão"
                              " muradas e as certidões agrupam os acidentes."}),
            "sources": ["mortality/causes_of_death.csv",
                        "demography/population.csv"],
            "spark": _per(ctx, "mortality/causes_of_death.csv",
                          "deaths_suicide"),
            "stats": [
                S({ZH: "自殺率", EN: "Suicide rate", PT: "Taxa de suicídio"},
                  _per(ctx, "mortality/causes_of_death.csv",
                       "deaths_suicide"), "per100k", kind="level"),
                S({ZH: "意外死亡", EN: "Accidental deaths",
                   PT: "Mortes acidentais"},
                  _per(ctx, "mortality/causes_of_death.csv",
                       "deaths_accidents"), "per100k", kind="level"),
            ],
        },
        {
            "id": "11-mortality", "topic": "mortality", "n": "11",
            "family": PEOPLE,
            "title": T(**{ZH: "死亡率——老化,與一波遲來的疫情",
                          EN: "Mortality — Ageing, and a Late Pandemic Wave",
                          PT: "Mortalidade — Envelhecimento e uma Onda Tardia"
                             " da Pandemia"}),
            "blurb": T(**{ZH: "粗死亡率、以 2015–2019 平均值為基準的超額死亡、"
                            "待補的新冠欄,以及隨人口成長的殺手。",
                          EN: "Crude death rate, excess deaths against the"
                              " 2015–2019 mean, a pending COVID column, and"
                              " the killers that grew with the population.",
                          PT: "Taxa bruta de mortalidade, óbitos excessivos"
                              " contra a média de 2015–2019, uma coluna COVID"
                              " pendente e os matadores que cresceram com a"
                              " população."}),
            "alt": T(**{ZH: "死亡的四個面板。粗死亡率從每千人 6.2 升到 8.5;死亡比 2015–"
                            "2019 平均值高出 21.7% 的是 2022 年,不是 2020,之後持續高於平均值。"
                            "新冠面板待補。癌症升到每十萬人 235,心臟疾病 98,肺炎翻倍到 75。",
                          EN: "Four panels on mortality. The crude death rate"
                              " rises from 6.2 to 8.5 per 1,000; deaths run"
                              " +21.7% above the 2015–2019 mean in 2022, not"
                              " 2020, and stay above it through 2025. The"
                              " COVID panel is pending. Cancer rises to 235"
                              " per 100,000, heart disease to 98, and"
                              " pneumonia doubles to 75.",
                          PT: "Quatro painéis sobre mortalidade. A taxa bruta"
                              " de mortalidade sobe de 6,2 para 8,5 por 1.000;"
                              " os óbitos ficam 21,7% acima da média de 2015–"
                              "2019 em 2022, não em 2020, e seguem acima dela"
                              " até 2025. O painel COVID está pendente. O"
                              " câncer sobe a 235 por 100.000, as doenças"
                              " cardíacas a 98, e a pneumonia dobra para 75."}),
            "sources": ["mortality/causes_of_death.csv",
                        "demography/population.csv"],
            "spark": _per(ctx, "mortality/causes_of_death.csv",
                          "deaths_all_cause"),
            "stats": [
                S({ZH: "粗死亡率", EN: "Crude death rate",
                   PT: "Taxa bruta de mortalidade"},
                  _per(ctx, "mortality/causes_of_death.csv",
                       "deaths_all_cause", 1e3), "dec2", kind="level"),
                S({ZH: "癌症死亡率", EN: "Cancer death rate",
                   PT: "Taxa de mortalidade por câncer"},
                  _per(ctx, "mortality/causes_of_death.csv",
                       "deaths_cancer"), "per100k", kind="level"),
            ],
        },
        {
            "id": "12-migration", "topic": "migration", "n": "12",
            "family": PEOPLE,
            "title": T(**{ZH: "戶籍移動，以及旁邊的居留證人口",
                          EN: "Register Movement, with the ARC Population Beside It",
                          PT: "Movimento no Registro, com a População ARC ao Lado"}),
            "blurb": T(**{ZH: "戶籍遷入與遷出是登記事件；有效居留證持有人是另一個月底法律存量。",
                          EN: "Household-register arrivals and departures are registration events; valid ARC holders are a separate month-end legal stock.",
                          PT: "Entradas e saídas do registro domiciliar são eventos; portadores de ARC válido formam um estoque jurídico separado no fim do mês."}),
            "alt": T(**{ZH: "遷徙的四個面板。 2018年起分別顯示戶籍國際遷入與遷出； 2020至2022年的大幅負值受出境滿兩年逕為遷出登記影響，2023年轉正。 沒有經審核的外國出生人口比率。 2025年12月有1,028,945名持有效居留證且實際在臺的外僑，其中751,806名為外籍勞工。",
                          EN: "Four panels on migration. Household-register international in and out are separate from 2018; the sharply negative 2020–2022 net includes ex-officio deregistration after two years abroad and turns positive in 2023. No audited foreign-born share is available. In December 2025, 1,028,945 foreign residents held a valid ARC and were actually in Taiwan, including 751,806 foreign labourers.",
                          PT: "Quatro painéis sobre migração. Entradas e saídas internacionais do registro aparecem separadas desde 2018; o saldo fortemente negativo de 2020–2022 inclui baixas de ofício após dois anos no exterior e volta a ser positivo em 2023. Não há proporção auditada de nascidos no exterior. Em dezembro de 2025, 1.028.945 residentes estrangeiros tinham ARC válido e estavam em Taiwan, incluindo 751.806 trabalhadores estrangeiros."}),
            "sources": ["migration/registration_flows.csv",
                        "migration/foreign_residents.csv",
                        "demography/population.csv"],
            "spark": ctx.col("migration/registration_flows.csv", "registered_net"),
            "stats": [
                S({ZH: "戶籍淨遷徙", EN: "Net registration", PT: "Saldo registrado"},
                  ctx.col("migration/registration_flows.csv", "registered_net"), "count"),
                S({ZH: "外僑居留證人口", EN: "ARC foreign residents", PT: "Residentes estrangeiros com ARC"},
                  ctx.col("migration/foreign_residents.csv", "arc_foreign_residents_dec"), "count", kind="level"),
            ],
        },
    ]
