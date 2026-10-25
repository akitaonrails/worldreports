"""Japan's page cards, computed from the reviewed publication CSVs."""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def _c(ctx, name, col):
    return ctx.col(f"published/{name}.csv", col)


def _scaled(ctx, name, col, divisor):
    return [(year, value / divisor) for year, value in _c(ctx, name, col)]


def headline(ctx):
    T = ctx.text
    return [
        ctx.stat(T(ja="GDP", en="GDP", pt="PIB"),
                 _c(ctx, "gdp_esri", "gdp_nominal_cy_bn"), "money_bn"),
        ctx.stat(T(ja="1人当たりGDP", en="GDP per person, US$",
                   pt="PIB por pessoa, US$"),
                 _c(ctx, "gdp_pc_wb", "gdp_per_person_usd"), "count"),
        ctx.stat(T(ja="人口", en="Population", pt="População"),
                 _scaled(ctx, "population_stat", "population_k", 1_000),
                 "pop_mn", kind="level"),
        ctx.stat(T(ja="失業率", en="Unemployment", pt="Desemprego"),
                 _c(ctx, "labour_stat", "unemployment_rate_pct"), "pct"),
        ctx.stat(T(ja="政府総債務", en="Gross public debt", pt="Dívida pública bruta"),
                 _c(ctx, "gg_fiscal_imf", "gross_debt_pct_gdp"),
                 "pct_gdp", kind="level"),
        ctx.stat(T(ja="在留外国人数", en="Foreign residents", pt="Residentes estrangeiros"),
                 _c(ctx, "foreign_residents_isa", "foreign_residents"),
                 "count", kind="level"),
        ctx.stat(T(ja="無担保コール翌日物", en="Overnight call rate", pt="Taxa overnight"),
                 _c(ctx, "rates_boj", "call_rate_dec"), "pct2", kind="level"),
    ]


def build(ctx):
    T = ctx.text
    specs = [
        ("01-economy", "economy", MONEY,
         T(ja="日本経済", en="The Japanese Economy", pt="A Economia Japonesa"),
         T(ja="内閣府と総務省の統計から、成長、所得、物価、雇用の変化を一望します（GDP / GNI / CPI / LFS）。",
           en="Growth, income, prices and jobs from Cabinet Office and Statistics Bureau series.",
           pt="Crescimento, renda, preços e emprego nas séries do Gabinete do Governo e do Escritório de Estatística."),
         "gdp_esri", "gdp_nominal_cy_bn", "money_bn"),
        ("02-fiscal", "fiscal", MONEY,
         T(ja="財政", en="Public Finances", pt="Finanças Públicas"),
         T(ja="一般政府の収支を追いながら、範囲と評価方法が異なる三つの債務指標を明確に分けて示します（収支 / 純債務 / 総債務 / 償還額）。",
           en="General-government balances and three differently defined debt series, kept separate.",
           pt="Saldos do governo geral e três séries de dívida com definições diferentes, mantidas separadas."),
         "gg_fiscal_imf", "gross_debt_pct_gdp", "pct_gdp"),
        ("03-spending", "spending", MONEY,
         T(ja="歳出の行方", en="Where the Money Goes", pt="Para Onde Vai o Dinheiro"),
         T(ja="政府支出の内訳を目的別に読み解き、経済全体の投資率と政府投資を比較します（社会保障 / 保健 / 教育 / 公共投資）。",
           en="Government spending by function beside whole-economy and public investment.",
           pt="Despesa pública por função ao lado do investimento da economia e do setor público."),
         "cofog_esri", "social_protection_bn", "money_bn"),
        ("04-trade", "trade", WORLD,
         T(ja="貿易", en="Trade", pt="Comércio"),
         T(ja="国民経済計算の財・サービス貿易、税関統計の相手国、国際収支を、それぞれの範囲を保って並べます（輸出 / 輸入 / 相手国 / 経常収支）。",
           en="National-accounts goods and services, customs destinations and the balance of payments.",
           pt="Bens e serviços das contas nacionais, destinos aduaneiros e balanço de pagamentos."),
         "trade_customs", "exports_jpy_bn", "money_bn"),
        ("05-markets", "markets", MONEY,
         T(ja="金融と市場", en="Money & Markets", pt="Moeda e Mercados"),
         T(ja="日銀の政策転換から国債利回り、円相場、ドル換算した株価まで、金融環境の変化をたどります（政策金利 / 国債 / 為替 / 株価）。",
           en="The BOJ regime shift, bond yields, the yen and equities measured in US dollars.",
           pt="A mudança de regime do BOJ, rendimentos, o iene e ações medidas em dólares."),
         "rates_boj", "call_rate_avg", "pct2"),
        ("06-credit", "credit", MONEY,
         T(ja="家計信用", en="Household Credit", pt="Crédito às Famílias"),
         T(ja="資金循環統計で家計借入の規模を捉え、未収集の国際比較指標についても不足を明記します（住宅ローン / 消費者信用 / 延滞 / 不良債権）。",
           en="Household borrowing in the flow of funds, with unavailable comparison measures stated plainly.",
           pt="Endividamento familiar nas contas financeiras, com medidas comparáveis ausentes declaradas claramente."),
         "household_debt_boj", "household_loans_bn", "money_bn"),
        ("07-people", "people", PEOPLE,
         T(ja="暮らしと格差", en="People", pt="Pessoas"),
         T(ja="所得格差と相対的貧困に加え、高齢化のなかで変わる就業と労働参加を見渡します（格差 / 貧困 / 就業 / 労働参加）。",
           en="Income inequality, relative poverty and an ageing labour force.",
           pt="Desigualdade de renda, pobreza relativa e uma força de trabalho envelhecida."),
         "gini_oecd", "gini_meth2012", "dec3"),
        ("08-world", "world", WORLD,
         T(ja="世界の中の日本", en="Japan in the World", pt="O Japão no Mundo"),
         T(ja="ドル換算の経済規模、人間開発、外貨準備を、国際比較に適した共通の定義で示します（GDP / HDI / 外貨準備 / 世界順位）。",
           en="Dollar-measured size, human development and reserves on international definitions.",
           pt="Tamanho em dólares, desenvolvimento humano e reservas em definições internacionais."),
         "gdp_usd_wb", "gdp_usd", "usd"),
        ("09-demography", "demography", PEOPLE,
         T(ja="人口", en="Demography", pt="Demografia"),
         T(ja="人口減少、出生率の低下、自然減の拡大を、2025年国勢調査による基準変更とともに示します（人口 / 出生 / 死亡 / 自然増減）。",
           en="Population decline, fertility and natural decrease, with the 2025 census break visible.",
           pt="Declínio populacional, fecundidade e redução natural, com a ruptura do censo de 2025 visível."),
         "population_stat", "population_k", "count"),
        ("10-security", "security", PEOPLE,
         T(ja="安全", en="Security", pt="Segurança"),
         T(ja="死亡票に基づく他殺と自殺を示し、道路交通死は保留、警察が把握した事件数は別の概念として扱います（他殺 / 自殺 / 道路交通死 / 認知件数）。",
           en="Registered homicide and suicide, with road-only deaths pending and police cases kept conceptually separate.",
           pt="Homicídios e suicídios registrados, com mortes rodoviárias pendentes e casos policiais mantidos conceitualmente separados."),
         "homicide_deaths_mhlw", "homicide_deaths", "count"),
        ("11-mortality", "mortality", PEOPLE,
         T(ja="死亡", en="Mortality", pt="Mortalidade"),
         T(ja="粗死亡率と超過死亡を軸に、二つのCOVID分類の切れ目と老衰死の増加をたどります（死亡率 / 超過死亡 / COVID / 老衰）。",
           en="Crude mortality, excess deaths, two COVID classifications and deaths certified as senility.",
           pt="Mortalidade bruta, excesso de mortes, duas classificações de COVID e óbitos certificados como senilidade."),
         "vital_mhlw", "death_rate", "dec2"),
        ("12-migration", "migration", PEOPLE,
         T(ja="移住", en="Migration", pt="Migração"),
         T(ja="制度変更を挟む二つの外国人登録系列を分け、日本に全国系列がない移住フローも率直に示します（在留外国人 / 新規入国 / 難民 / 移住フロー）。",
           en="Two foreign-resident registers and the migration-flow statistics Japan does not keep.",
           pt="Dois registros de residentes estrangeiros e as estatísticas de fluxo migratório que o Japão não mantém."),
         "foreign_residents_isa", "foreign_residents", "count"),
    ]
    out = []
    for ident, topic, family, title, blurb, file, col, fmt in specs:
        pairs = _c(ctx, file, col)
        if fmt == "usd":
            pairs = [(year, value / 1_000_000_000) for year, value in pairs]
            fmt = "usd_bn"
        out.append({
            "id": ident, "topic": topic, "n": ident[:2], "family": family,
            "title": title, "blurb": blurb, "alt": blurb,
            "spark": pairs,
            "stats": [ctx.stat(title, pairs, fmt)],
        })
    return out
