"""Paraguay's twelve page cards, computed from reviewed publication CSVs.

Every figure here is read out of `data/` at build time, so a refetch that
moves a number moves the card with it. The headline strip leads with the
three readings every country carries — GDP, GDP per person, population —
and then Paraguay's own: growth, inflation, poverty and the debt.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def _per_million(ctx, rel, col):
    """A count in millions, stopped at the last complete year.

    INE's projection runs to 2050; a headline reading or a card sparkline
    that ran with it would present 2050 as the population today.
    """
    return [(y, v / 1e6) for y, v in ctx.col(rel, col)
            if y <= ctx.LAST_FULL_YEAR]


def _fx_index(ctx):
    pairs = ctx.col("markets/fx.csv", "pyg_per_usd")
    if not pairs:
        return []
    base = dict(pairs)[2006]
    return [(y, base / v * 100) for y, v in pairs]


def _migrant_share(ctx):
    """UN DESA's migrant stock over the UN's population, both UN series."""
    pop = dict(ctx.col("demography/population_un_wpp.csv", "population"))
    return [(y, v / pop[y] * 100)
            for y, v in ctx.col("migration/migration.csv", "migrant_stock")
            if y in pop]


def headline(ctx):
    T = ctx.text
    return [
        ctx.stat(T(es="PIB", en="GDP", pt="PIB"),
                 ctx.col("world/gdp_usd.csv", "gdp_usd_bn"),
                 "usd_bn", kind="level"),
        ctx.stat(T(es="PIB por persona, US$", en="GDP per person, US$",
                   pt="PIB por pessoa, US$"),
                 ctx.col("macro/economy.csv", "gdp_per_person_usd"),
                 "count", kind="level"),
        ctx.stat(T(es="Población", en="Population", pt="População"),
                 _per_million(ctx, "demography/population.csv", "population"),
                 "pop_mn", kind="level"),
        ctx.stat(T(es="Crecimiento real", en="Real GDP growth",
                   pt="Crescimento real do PIB"),
                 ctx.col("macro/economy.csv", "gdp_growth_pct"), "pct_s"),
        ctx.stat(T(es="Inflación", en="Inflation", pt="Inflação"),
                 ctx.col("macro/economy.csv", "cpi_inflation_pct"), "pct"),
        ctx.stat(T(es="Pobreza", en="Poverty", pt="Pobreza"),
                 ctx.col("people/income.csv", "poverty_rate_pct"), "pct"),
        ctx.stat(T(es="Deuda pública bruta", en="Gross public debt",
                   pt="Dívida pública bruta"),
                 ctx.col("fiscal/fiscal.csv", "debt_pct_gdp"),
                 "pct_gdp", kind="level"),
    ]


#: What each card's figure shows, written for a reader who cannot see it.
#: Hand-written rather than assembled from the table's facts: the demography
#: table runs to 2050 and the poverty table back to 2002, and a generated
#: sentence would report those as the plate's own range.
CH_ALT = {
    "01-economy": {
        "es": "Cuatro paneles sobre la economía paraguaya: crecimiento real con las recesiones de 2009, 2012 y 2019-20 marcadas; PIB por persona en dólares corrientes; inflación; y desempleo, el modelo de la OIT junto a la EPHC del INE desde 2017.",
        "en": "Four panels on Paraguay's economy: real growth with the 2009, 2012 and 2019-20 downturns banded; GDP per person in current dollars; consumer price inflation; and unemployment, the ILO model beside INE's survey from 2017.",
        "pt": "Quatro painéis sobre a economia paraguaia: crescimento real com as recessões de 2009, 2012 e 2019-20 marcadas; PIB por pessoa em dólares correntes; inflação; e desemprego, o modelo da OIT ao lado da EPHC do INE desde 2017.",
    },
    "02-fiscal": {
        "es": "Cuatro paneles sobre las finanzas públicas: ingresos y gastos del gobierno general sobre base devengada y de la administración central sobre base de caja, unos cuatro puntos de PIB aparte; resultado global y primario; deuda bruta; e intereses pagados.",
        "en": "Four panels on Paraguay's public finances: revenue and spending for general government on an accrual basis and for central administration on cash, about four points of GDP apart; the overall and primary balance; gross debt; and interest paid.",
        "pt": "Quatro painéis sobre as finanças públicas: receitas e despesas do governo geral por competência e da administração central por caixa, cerca de quatro pontos do PIB de diferença; resultado global e primário; dívida bruta; e juros pagos.",
    },
    "03-spending": {
        "es": "Cuatro paneles sobre el gasto: dos paneles funcionales visiblemente pendientes con las rutas que fallaron, la tasa de inversión de toda la economía y la inversión fija del gobierno central.",
        "en": "Four panels on spending: two functional panels visibly pending with the routes that failed, the whole-economy investment rate, and the central government's own fixed investment.",
        "pt": "Quatro painéis sobre o gasto: dois painéis funcionais visivelmente pendentes com as rotas que falharam, a taxa de investimento da economia inteira e o investimento fixo do governo central.",
    },
    "04-trade": {
        "es": "Cuatro paneles sobre el comercio: exportaciones e importaciones de bienes y servicios sobre PIB; su balance; los destinos de las exportaciones de aduana desde 2006; y las regalías de Itaipú y Yacyretá como ingreso fiscal de los tratados.",
        "en": "Four panels on Paraguay's trade: exports and imports of goods and services as a share of GDP; their balance; the destinations of customs goods exports since 2006; and Itaipú-Yacyretá royalties as treaty revenue.",
        "pt": "Quatro painéis sobre o comércio: exportações e importações de bens e serviços sobre o PIB; o saldo; os destinos das exportações de alfândega desde 2006; e os royalties de Itaipú e Yacyretá como receita fiscal dos tratados.",
    },
    "05-markets": {
        "es": "Cuatro paneles sobre mercados: tres visiblemente pendientes (tasa de política, rendimiento a diez años e índice bursátil) y el guaraní frente al dólar indexado a 2006.",
        "en": "Four panels on markets: three visibly pending panels for the policy rate, the ten-year yield and an equity index, and the guaraní against the dollar indexed to 2006.",
        "pt": "Quatro painéis sobre mercados: três visivelmente pendentes (taxa de política, rendimento de dez anos e índice acionário) e o guaraní frente ao dólar indexado a 2006.",
    },
    "06-credit": {
        "es": "Cuatro paneles sobre crédito: deuda de los hogares y tasa de préstamo a hogares pendientes, el ratio de morosidad y el crédito al sector privado, rotulado como no deuda de los hogares.",
        "en": "Four panels on credit: household debt and the household lending rate visibly pending, the non-performing loan ratio, and private-sector credit labelled as not household debt.",
        "pt": "Quatro painéis sobre crédito: dívida das famílias e taxa de empréstimo às famílias pendentes, o índice de inadimplência e o crédito ao setor privado rotulado como não dívida das famílias.",
    },
    "07-people": {
        "es": "Cuatro paneles sobre personas: el Gini; la pobreza nacional con su ruptura de encuesta de 2017 marcada; el salario mínimo legal en dólares; y su valor en guaraníes frente al IPC.",
        "en": "Four panels on people: the Gini coefficient; the national poverty rate with its 2017 survey break marked; the statutory minimum wage in dollars per month; and its value in guaraníes against the CPI.",
        "pt": "Quatro painéis sobre pessoas: o Gini; a pobreza nacional com a ruptura de pesquisa de 2017 marcada; o salário mínimo legal em dólares; e o seu valor em guaranis frente ao IPC.",
    },
    "08-world": {
        "es": "Cuatro paneles que sitúan al Paraguay en el mundo: PIB nominal en dólares, IDH, un índice de corrupción pendiente con su razón, y reservas oficiales.",
        "en": "Four panels placing Paraguay in the world: nominal GDP in dollars, the Human Development Index, a pending corruption index with its reason, and official reserves.",
        "pt": "Quatro painéis que situam o Paraguai no mundo: PIB nominal em dólares, IDH, um índice de corrupção pendente com a sua razão, e reservas oficiais.",
    },
    "09-demography": {
        "es": "Cuatro paneles sobre demografía: el índice de población en dos perímetros nueve por ciento aparte; la fecundidad, que cae bajo el reemplazo en 2022; las tasas brutas de natalidad y mortalidad; y el crecimiento natural frente a la migración neta.",
        "en": "Four panels on demography: the population index on two perimeters nine per cent apart; the fertility rate falling below replacement in 2022; crude birth and death rates; and natural increase against net migration.",
        "pt": "Quatro painéis sobre demografia: o índice de população em dois perímetros nove por cento de distância; a fecundidade, que cai abaixo da reposição em 2022; as taxas brutas de natalidade e mortalidade; e o crescimento natural frente à migração líquida.",
    },
    "10-security": {
        "es": "Cuatro paneles sobre seguridad: homicidios en escala logarítmica, suicidios, muertes en el tránsito, y las tres tasas juntas en un mismo eje.",
        "en": "Four panels on security: the homicide rate on a log scale, the suicide rate, road traffic deaths, and the three rates drawn together on one axis.",
        "pt": "Quatro painéis sobre segurança: homicídios em escala logarítmica, suicídios, mortes no trânsito, e as três taxas juntas em um mesmo eixo.",
    },
    "11-mortality": {
        "es": "Cuatro paneles sobre mortalidad: la tasa bruta de mortalidad con su pico de 2021, dos paneles pendientes (muertes en exceso y COVID-19) con sus razones, y la esperanza de vida.",
        "en": "Four panels on mortality: the crude death rate with its 2021 spike, two visibly pending panels for excess and COVID-19 deaths with their reasons, and life expectancy.",
        "pt": "Quatro painéis sobre mortalidade: a taxa bruta de mortalidade com o pico de 2021, dois painéis pendentes (excesso de mortes e COVID-19) com as suas razões, e a esperança de vida.",
    },
    "12-migration": {
        "es": "Cuatro paneles sobre migración: flujos brutos pendientes; migración neta del INE y de la ONU, cada una sobre su propia población; la proporción de nacidos en el exterior en cuatro cortes; y la migración neta en personas.",
        "en": "Four panels on migration: gross flows visibly pending; net migration from INE and from the UN, each on its own population; the foreign-born share in four snapshots; and net migration in persons.",
        "pt": "Quatro painéis sobre migração: fluxos brutos pendentes; migração líquida do INE e da ONU, cada uma sobre a sua própria população; a parcela de nascidos no exterior em quatro cortes; e a migração líquida em pessoas.",
    },
}


def build(ctx):
    T, S = ctx.text, ctx.stat
    specs = [
        ("01-economy", "economy", MONEY,
         T(es="La economía", en="The Economy", pt="A economia"),
         T(es="Crecimiento, ingreso, precios y empleo en series comparables "
              "del Banco Mundial y el FMI, con el IPC del BCP tal como lo "
              "registra el Fondo.",
           en="Growth, income, prices and jobs in comparable World Bank and "
              "IMF series, with the BCP's CPI as the Fund records it.",
           pt="Crescimento, renda, preços e emprego em séries comparáveis do "
              "Banco Mundial e do FMI, com o IPC do BCP como o Fundo o "
              "registra."),
         "macro/economy.csv", "gdp_growth_pct", False,
         [S(T(es="Crecimiento real", en="Real GDP growth",
              pt="Crescimento real"),
            ctx.col("macro/economy.csv", "gdp_growth_pct"), "pct_s"),
          S(T(es="Inflación", en="Inflation", pt="Inflação"),
            ctx.col("macro/economy.csv", "cpi_inflation_pct"), "pct")],
         {"csv": "macro/economy.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("gdp_growth_pct", T(es="PIB real, %", en="Real GDP, %",
                                   pt="PIB real, %")),
              ("gdp_per_person_usd", T(es="PIB por persona, US$",
                                       en="GDP per person, US$",
                                       pt="PIB por pessoa, US$")),
              ("cpi_inflation_pct", T(es="IPC, % interanual",
                                      en="CPI, % year on year",
                                      pt="IPC, % em 12 meses")),
              ("unemployment_pct", T(es="Desempleo OIT, %",
                                     en="Unemployment, ILO %",
                                     pt="Desemprego OIT, %"))],
          "facts": ("gdp_growth_pct", "cpi_inflation_pct")}),
        ("02-fiscal", "fiscal", MONEY,
         T(es="Finanzas públicas", en="Public Finances",
           pt="Finanças públicas"),
         T(es="El gobierno general del FMI sobre base devengada y la "
              "administración central del MEF sobre base de caja: dos "
              "perímetros, cuatro puntos de PIB.",
           en="The IMF's general government on an accrual basis and the "
              "MEF's central administration on the Treasury's cash books: "
              "two perimeters, four points of GDP.",
           pt="O governo geral do FMI por competência e a administração "
              "central do MEF por caixa: dois perímetros, quatro pontos "
              "do PIB."),
         "fiscal/fiscal.csv", "debt_pct_gdp", True,
         [S(T(es="Resultado global", en="Overall balance",
              pt="Resultado global"),
            ctx.col("fiscal/fiscal.csv", "balance_pct_gdp"), "pct_gdp_s"),
          S(T(es="Deuda bruta", en="Gross debt", pt="Dívida bruta"),
            ctx.col("fiscal/fiscal.csv", "debt_pct_gdp"), "pct_gdp",
            kind="level")],
         {"csv": "fiscal/fiscal.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("revenue_pct_gdp", T(es="Ingresos, % PIB",
                                    en="Revenue, % GDP",
                                    pt="Receitas, % PIB")),
              ("expenditure_pct_gdp", T(es="Gastos, % PIB",
                                        en="Expenditure, % GDP",
                                        pt="Despesas, % PIB")),
              ("balance_pct_gdp", T(es="Resultado, % PIB",
                                    en="Balance, % GDP",
                                    pt="Resultado, % PIB")),
              ("debt_pct_gdp", T(es="Deuda bruta, % PIB",
                                 en="Gross debt, % GDP",
                                 pt="Dívida bruta, % PIB"))],
          "facts": ("balance_pct_gdp", "debt_pct_gdp")}),
        ("03-spending", "spending", MONEY,
         T(es="Gasto e inversión", en="Spending and Investment",
           pt="Gasto e investimento"),
         T(es="La clasificación funcional no se publica como serie; los dos "
              "paneles de inversión sí se dibujan.",
           en="The functional classification is not published as a series; "
              "the two investment panels are drawn.",
           pt="A classificação funcional não é publicada como série; os "
              "dois painéis de investimento são desenhados."),
         "spending/spending.csv", "gfcf_pct_gdp", True,
         [S(T(es="Inversión, % PIB", en="Investment rate",
              pt="Taxa de investimento"),
            ctx.col("spending/spending.csv", "gfcf_pct_gdp"), "pct_gdp",
            kind="level"),
          S(T(es="Inversión pública, % PIB", en="Public investment",
              pt="Investimento público"),
            ctx.col("spending/spending.csv", "public_investment_pct_gdp"),
            "pct_gdp", kind="level")],
         {"csv": "spending/spending.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("gfcf_pct_gdp", T(es="FBKF, % PIB", en="GFCF, % GDP",
                                 pt="FBCF, % PIB")),
              ("public_investment_pct_gdp",
               T(es="Activos fijos del gobierno central, % PIB",
                 en="Central-government fixed assets, % GDP",
                 pt="Ativos fixos do governo central, % PIB"))],
          "facts": ("gfcf_pct_gdp", "public_investment_pct_gdp")}),
        ("04-trade", "trade", WORLD,
         T(es="Comercio", en="Trade", pt="Comércio"),
         T(es="Bienes y servicios en cuentas nacionales, bienes de aduana "
              "por destino, y los ingresos de los tratados aparte.",
           en="Goods and services in the national accounts, customs goods "
              "by destination, and the treaties' revenue kept separate.",
           pt="Bens e serviços nas contas nacionais, bens de alfândega por "
              "destino, e as receitas dos tratados à parte."),
         "trade/trade.csv", "exports_pct_gdp", True,
         [S(T(es="Exportaciones, % PIB", en="Exports, % of GDP",
              pt="Exportações, % do PIB"),
            ctx.col("trade/trade.csv", "exports_pct_gdp"), "pct_gdp",
            kind="level"),
          S(T(es="Balance comercial, % PIB", en="Trade balance, % of GDP",
              pt="Saldo comercial, % do PIB"),
            ctx.col("trade/trade.csv", "balance_pct_gdp"), "pct_gdp_s")],
         {"csv": "trade/trade.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("exports_pct_gdp", T(es="Exportaciones, % PIB",
                                    en="Exports, % GDP",
                                    pt="Exportações, % PIB")),
              ("imports_pct_gdp", T(es="Importaciones, % PIB",
                                    en="Imports, % GDP",
                                    pt="Importações, % PIB")),
              ("balance_pct_gdp", T(es="Balance, % PIB",
                                    en="Balance, % GDP",
                                    pt="Saldo, % PIB"))],
          "facts": ("exports_pct_gdp", "balance_pct_gdp")}),
        ("05-markets", "markets", MONEY,
         T(es="Mercados", en="Markets", pt="Mercados"),
         T(es="El camino del guaraní en veinte años es comparable; la tasa "
              "de política, la curva y un índice no se pueden preparar.",
           en="The guaraní's twenty-year path is comparable; the policy "
              "rate, the yield curve and an index cannot be staged.",
           pt="O caminho do guaraní em vinte anos é comparável; a taxa de "
              "política, a curva e um índice não podem ser preparados."),
         "markets/fx.csv", "pyg_per_usd", True,
         [S(T(es="Guaraní por dólar", en="Guaraníes per dollar",
              pt="Guaranis por dólar"),
            _fx_index(ctx), "index", kind="level")],
         {"csv": "markets/fx.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("pyg_per_usd", T(es="Guaraníes por US$, promedio anual",
                                en="Guaraníes per US$, annual average",
                                pt="Guaranis por US$, média anual"))],
          "facts": ("pyg_per_usd",)}),
        ("06-credit", "credit", MONEY,
         T(es="Crédito", en="Credit", pt="Crédito"),
         T(es="Los préstamos morosos y el crédito al sector privado se "
              "dibujan; la deuda de los hogares y la tasa de préstamo no se "
              "publican.",
           en="Non-performing loans and private-sector credit are drawn; "
              "household debt and the lending rate are not published.",
           pt="A inadimplência e o crédito ao setor privado são desenhados; "
              "a dívida das famílias e a taxa de empréstimo não são "
              "publicadas."),
         "credit/credit.csv", "private_credit_pct_gdp", True,
         [S(T(es="Morosidad", en="Non-performing loans", pt="Inadimplência"),
            ctx.col("credit/credit.csv", "npl_ratio"), "pct", kind="level"),
          S(T(es="Crédito privado, % PIB", en="Private credit, % of GDP",
              pt="Crédito privado, % do PIB"),
            ctx.col("credit/credit.csv", "private_credit_pct_gdp"),
            "pct_gdp", kind="level")],
         {"csv": "credit/credit.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("npl_ratio", T(es="Morosidad, % de préstamos",
                              en="NPL, % of loans",
                              pt="Inadimplência, % dos empréstimos")),
              ("private_credit_pct_gdp",
               T(es="Crédito privado, % PIB", en="Private credit, % GDP",
                 pt="Crédito privado, % PIB"))],
          "facts": ("npl_ratio", "private_credit_pct_gdp")}),
        ("07-people", "people", PEOPLE,
         T(es="Personas", en="People", pt="Pessoas"),
         T(es="Desigualdad y pobreza de la encuesta del INE, el salario "
              "mínimo legal en dólares y lo que vale en guaraníes.",
           en="Inequality and poverty from INE's survey, the statutory "
              "minimum in dollars, and what it is worth in guaraníes.",
           pt="Desigualdade e pobreza da pesquisa do INE, o salário mínimo "
              "legal em dólares e o que ele vale em guaranis."),
         "people/income.csv", "poverty_rate_pct", True,
         [S(T(es="Pobreza", en="Poverty", pt="Pobreza"),
            ctx.col("people/income.csv", "poverty_rate_pct"), "pct"),
          S(T(es="Gini", en="Gini", pt="Gini"),
            ctx.col("people/income.csv", "gini"), "dec2", kind="level")],
         {"csv": "people/income.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("gini", T(es="Gini", en="Gini", pt="Gini")),
              ("poverty_rate_pct", T(es="Pobreza, % de personas",
                                     en="Poverty, % of people",
                                     pt="Pobreza, % das pessoas")),
              ("minimum_wage_usd_month",
               T(es="Salario mínimo, US$ por mes",
                 en="Minimum wage, US$ per month",
                 pt="Salário mínimo, US$ por mês"))],
          "facts": ("gini", "poverty_rate_pct")}),
        ("08-world", "world", WORLD,
         T(es="Paraguay en el mundo", en="Paraguay in the World",
           pt="Paraguai no mundo"),
         T(es="Tamaño nominal, desarrollo humano y reservas; el índice de "
              "corrupción está bloqueado en el editor.",
           en="Nominal size, human development and reserves; the corruption "
              "index is blocked at the publisher.",
           pt="Tamanho nominal, desenvolvimento humano e reservas; o índice "
              "de corrupção está bloqueado no editor."),
         "world/gdp_usd.csv", "gdp_usd_bn", False,
         [S(T(es="PIB, US$ miles de millones", en="GDP, US$ bn",
              pt="PIB, US$ bilhões"),
            ctx.col("world/gdp_usd.csv", "gdp_usd_bn"), "usd_bn",
            kind="level"),
          S(T(es="IDH", en="HDI", pt="IDH"),
            ctx.col("world/hdi.csv", "hdi"), "dec3", kind="level")],
         {"csv": "world/gdp_usd.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("gdp_usd_bn", T(es="PIB, US$ miles de millones",
                               en="GDP, US$ bn", pt="PIB, US$ bilhões")),
              ("reserves_usd_bn", T(es="Reservas, US$ miles de millones",
                                    en="Reserves, US$ bn",
                                    pt="Reservas, US$ bilhões"))],
          "facts": ("gdp_usd_bn",)}),
        ("09-demography", "demography", PEOPLE,
         T(es="Demografía", en="Demography", pt="Demografia"),
         T(es="La revisión 2024 del INE está anclada en el censo de 2022; la "
              "serie de la ONU que publica el Banco Mundial no.",
           en="INE's revision 2024 is anchored on the 2022 census; the UN "
              "series the World Bank carries is not.",
           pt="A revisão 2024 do INE está ancorada no censo de 2022; a série "
              "da ONU que o Banco Mundial publica não."),
         "demography/population.csv", "population", False,
         [S(T(es="Población", en="Population", pt="População"),
            _per_million(ctx, "demography/population.csv", "population"),
            "pop_mn", kind="level"),
          S(T(es="Fecundidad", en="Fertility rate", pt="Fecundidade"),
            ctx.col("demography/population.csv", "fertility_rate"), "dec2",
            kind="level")],
         {"csv": "demography/population.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("population", T(es="Población (INE)", en="Population (INE)",
                               pt="População (INE)")),
              ("fertility_rate", T(es="Hijos por mujer",
                                   en="Children per woman",
                                   pt="Filhos por mulher")),
              ("death_rate_per_1000", T(es="Mortalidad, por 1.000",
                                        en="Deaths, per 1,000",
                                        pt="Mortalidade, por 1.000"))],
          "facts": ("population", "fertility_rate")}),
        ("10-security", "security", PEOPLE,
         T(es="Seguridad", en="Security", pt="Segurança"),
         T(es="Homicidios, suicidios y muertes en el tránsito en la serie "
              "armonizada, y luego los tres juntos.",
           en="Homicide, suicide and road deaths on the harmonised series, "
              "then the three beside each other.",
           pt="Homicídios, suicídios e mortes no trânsito na série "
              "harmonizada, e depois os três juntos."),
         "security/security.csv", "homicide_per_100k", True,
         [S(T(es="Homicidios, por 100.000", en="Homicide, per 100,000",
              pt="Homicídios, por 100.000"),
            ctx.col("security/security.csv", "homicide_per_100k"),
            "per100k", kind="level"),
          S(T(es="Muertes en el tránsito, por 100.000",
              en="Road deaths, per 100,000",
              pt="Mortes no trânsito, por 100.000"),
            ctx.col("security/security.csv", "road_deaths_per_100k"),
            "per100k")],
         {"csv": "security/security.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("homicide_per_100k", T(es="Homicidios, por 100.000",
                                      en="Homicide, per 100,000",
                                      pt="Homicídios, por 100.000")),
              ("suicide_per_100k", T(es="Suicidios, por 100.000",
                                     en="Suicide, per 100,000",
                                     pt="Suicídios, por 100.000")),
              ("road_deaths_per_100k",
               T(es="Tránsito, por 100.000", en="Road, per 100,000",
                 pt="Trânsito, por 100.000"))],
          "facts": ("homicide_per_100k", "road_deaths_per_100k")}),
        ("11-mortality", "mortality", PEOPLE,
         T(es="Mortalidad", en="Mortality", pt="Mortalidade"),
         T(es="La tasa de mortalidad y la esperanza de vida de la proyección "
              "del INE; las muertes en exceso y por COVID-19 siguen "
              "pendientes.",
           en="The death rate and life expectancy from INE's projection; "
              "excess and COVID-19 deaths stay pending.",
           pt="A taxa de mortalidade e a esperança de vida da projeção do "
              "INE; o excesso de mortes e a COVID-19 seguem pendentes."),
         "mortality/mortality.csv", "life_expectancy", True,
         [S(T(es="Esperanza de vida", en="Life expectancy",
              pt="Esperança de vida"),
            ctx.col("mortality/mortality.csv", "life_expectancy"), "years",
            kind="level"),
          S(T(es="Mortalidad, por 1.000", en="Death rate, per 1,000",
              pt="Mortalidade, por 1.000"),
            ctx.col("mortality/mortality.csv", "death_rate_per_1000"),
            "dec2", kind="level")],
         {"csv": "mortality/mortality.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("deaths", T(es="Defunciones (proyección)",
                            en="Deaths (projection)",
                            pt="Óbitos (projeção)")),
              ("death_rate_per_1000", T(es="Tasa bruta, por 1.000",
                                        en="Crude rate, per 1,000",
                                        pt="Taxa bruta, por 1.000")),
              ("life_expectancy", T(es="Esperanza de vida, años",
                                    en="Life expectancy, years",
                                    pt="Esperança de vida, anos"))],
          "facts": ("death_rate_per_1000", "life_expectancy")}),
        ("12-migration", "migration", WORLD,
         T(es="Migración", en="Migration", pt="Migração"),
         T(es="La migración neta con el denominador de cada editor, el stock "
              "de nacidos en el exterior y la salida en personas.",
           en="Net migration on each publisher's own denominator, the "
              "foreign-born stock, and the outflow in persons.",
           pt="A migração líquida com o denominador de cada editor, o "
              "estoque de nascidos no exterior e a saída em pessoas."),
         "migration/migration.csv", "net_migration_rate_per_1000", True,
         [S(T(es="Migración neta, por 1.000", en="Net migration, per 1,000",
              pt="Migração líquida, por 1.000"),
            ctx.col("migration/migration.csv",
                    "net_migration_rate_per_1000"), "dec2", kind="level"),
          S(T(es="Nacidos en el exterior, % de la población",
              en="Foreign-born, % of population",
              pt="Nascidos no exterior, % da população"),
            _migrant_share(ctx), "pct", kind="level")],
         {"csv": "migration/migration.csv", "key": "year",
          "columns": [
              ("year", T(es="Año", en="Year", pt="Ano")),
              ("net_migration_rate_per_1000",
               T(es="Migración neta INE, por 1.000",
                 en="INE net migration, per 1,000",
                 pt="Migração líquida INE, por 1.000")),
              ("net_migration_persons",
               T(es="Migración neta ONU, personas",
                 en="UN net migration, persons",
                 pt="Migração líquida ONU, pessoas")),
              ("migrant_stock", T(es="Stock de migrantes (ONU)",
                                  en="Migrant stock (UN)",
                                  pt="Estoque de migrantes (ONU)"))],
          "facts": ("net_migration_rate_per_1000",)}),
    ]
    out = []
    for (ident, topic, family, title, blurb, path, column, level,
         stats, table) in specs:
        out.append({
            "id": ident, "topic": topic, "n": ident[:2], "family": family,
            "title": title, "blurb": blurb, "alt": CH_ALT[ident],
            "spark": ctx.col(path, column),
            "spark_level": level,
            "stats": stats,
            "table": table,
        })
    return out
