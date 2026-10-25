"""The Venezuela cards: their copy, their figures and their sparklines.

Editorial copy lives here, and the numbers inside it are read from the
committed CSVs at build time rather than typed: a refetch that moves the
collapse moves the sentence with it. The plates say what kind of number each
series is; the cards say what this country's window came to.

Eleven chapters on the shared spine. Three are drawn largely pending — the
functional budget, the markets, migration — and their copy says so instead of
sounding as if a chart were there. Nothing on this page is a national
outturn that this repository invented: where the state stopped publishing,
the card names the harmonised series that stands in its place.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def _d(pairs) -> dict:
    return dict(pairs)


def _v(pairs, year):
    return _d(pairs).get(year)


def headline(ctx) -> list[dict]:
    """The figures the page leads with, in the atlas's fixed order.

    GDP, then GDP per person, then population — the same three readings, in
    the same places, as every other country. The three that follow are this
    country's own: the inflation that left the comparable scale, the growth
    the Fund estimates, and the number of Venezuelans with a protection
    status abroad.
    """
    gdp = [(y, v) for y, v in ctx.col("world/gdp_usd.csv", "gdp_usd_bn_wb")]
    return [
        ctx.stat({"en": "GDP", "es": "PIB", "pt": "PIB"}, gdp, "usd_bn"),
        ctx.stat({"en": "GDP per person, US$", "es": "PIB por persona, US$",
                  "pt": "PIB por pessoa, US$"},
                 ctx.col("world/gdp_per_person.csv", "gdp_per_person_usd"),
                 "count"),
        ctx.stat({"en": "Population", "es": "Población", "pt": "População"},
                 [(y, v / 1e6) for y, v in
                  ctx.col("demography/population.csv", "population")],
                 "pop_mn", kind="level"),
        ctx.stat({"en": "Inflation, IMF staff estimate",
                  "es": "Inflación, estimación del FMI",
                  "pt": "Inflação, estimativa do FMI"},
                 ctx.col("macro/economy.csv", "cpi_inflation_pct_imf"), "pct"),
        ctx.stat({"en": "Real GDP growth, IMF staff estimate",
                  "es": "Crecimiento real del PIB, estimación del FMI",
                  "pt": "Crescimento real do PIB, estimativa do FMI"},
                 ctx.col("macro/economy.csv", "gdp_growth_pct_imf"), "pct_s"),
        ctx.stat({"en": "Venezuelans with a protection status abroad",
                  "es": "Venezolanos con estatus de protección en el exterior",
                  "pt": "Venezuelanos com status de proteção no exterior"},
                 ctx.col("migration/displacement.csv",
                         "refugees_and_asylum_seekers"), "count",
                 kind="level"),
    ]


def build(ctx) -> list[dict]:
    T = ctx.text
    eco = ctx.col("macro/economy.csv", "gdp_growth_pct_wb")
    imf = ctx.col("macro/economy.csv", "gdp_growth_pct_imf")
    pc = ctx.col("world/gdp_per_person.csv", "gdp_per_person_usd")
    cpi = ctx.col("macro/economy.csv", "cpi_inflation_pct_imf")
    fiscal = ctx.col("fiscal/fiscal.csv", "balance_pct_gdp")
    rev = ctx.col("fiscal/fiscal.csv", "revenue_pct_gdp")
    exp = ctx.col("fiscal/fiscal.csv", "expenditure_pct_gdp")
    gfcf = ctx.col("spending/spending.csv", "gfcf_pct_gdp")
    xp = ctx.col("trade/trade.csv", "exports_pct_gdp")
    im = ctx.col("trade/trade.csv", "imports_pct_gdp")
    _im = _d(im)
    balance = [(y, a - _im[y]) for y, a in xp if y in _im]
    fx = ctx.col("markets/fx_official.csv", "fx_index_2006_100")
    gini = ctx.col("people/gini.csv", "gini")
    gdp = ctx.col("world/gdp_usd.csv", "gdp_usd_bn_wb")
    gdp_imf = ctx.col("world/gdp_usd.csv", "gdp_usd_bn_imf")
    hdi = ctx.col("world/hdi.csv", "hdi")
    reserves = ctx.col("world/reserves.csv", "reserves_usd_bn")
    pop = ctx.col("demography/population.csv", "population")
    fert = ctx.col("demography/vital.csv", "fertility_rate")
    birth = ctx.col("demography/vital.csv", "birth_rate_per_1000")
    death = ctx.col("demography/vital.csv", "death_rate_per_1000")
    life = ctx.col("demography/vital.csv", "life_expectancy")
    hom = ctx.col("security/security.csv", "homicide_per_100k")
    sui = ctx.col("security/security.csv", "suicide_per_100k")
    net = ctx.col("migration/migration.csv", "net_migration_per_1000")
    caseload = ctx.col("migration/displacement.csv",
                       "refugees_and_asylum_seekers")
    stock_share = _stock_share(ctx)

    peak_gni = max(gini, key=lambda p: p[1]) if gini else (0, 0)
    low_gni = min(gini, key=lambda p: p[1]) if gini else (0, 0)
    worst_net = min(net, key=lambda p: p[1]) if net else (0, 0)
    peak_case = max(caseload, key=lambda p: p[1]) if caseload else (0, 0)
    peak_hom = max((p for p in hom if p[1] == p[1]), key=lambda p: p[1]) \
        if hom else (0, 0)
    peak_cpi = max(cpi, key=lambda p: p[1]) if cpi else (0, 0)
    peak_gdp = max(gdp, key=lambda p: p[1]) if gdp else (0, 0)

    chapters = [
        {
            "id": "01-economy", "topic": "economy", "n": "01",
            "family": MONEY,
            "title": T(en="The Economy", es="La economía",
                       pt="A economia"),
            "blurb": T(
                en=f"Two staff estimates of the same collapse: the World "
                   f"Bank's bars fall {abs(_v(eco, 2020) or 0):.1f}% in 2020, "
                   f"the Fund's line {abs(_v(imf, 2020) or 0):.1f}%, and "
                   f"income per person ends the window at a quarter of its "
                   f"2010 level. The inflation that followed is on the people "
                   f"plate, because 65,374% cannot share a linear axis.",
                es=f"Dos estimaciones técnicas del mismo derrumbe: las barras "
                   f"del Banco Mundial caen {abs(_v(eco, 2020) or 0):.1f}% en "
                   f"2020, la línea del Fondo {abs(_v(imf, 2020) or 0):.1f}%, "
                   f"y el ingreso por persona termina la ventana en un cuarto "
                   f"de su nivel de 2010. La inflación que vino después está "
                   f"en la plancha de personas, porque 65.374% no cabe en un "
                   f"eje lineal.",
                pt=f"Duas estimativas técnicas do mesmo colapso: as barras do "
                   f"Banco Mundial caem {abs(_v(eco, 2020) or 0):.1f}% em "
                   f"2020, a linha do Fundo {abs(_v(imf, 2020) or 0):.1f}%, e "
                   f"a renda por pessoa termina a janela num quarto do seu "
                   f"nível de 2010. A inflação que veio depois está na prancha "
                   f"de pessoas, porque 65.374% não cabe num eixo linear."),
            "spark": imf,
            "stats": [
                ctx.stat({"en": "GDP per person, US$",
                          "es": "PIB por persona, US$",
                          "pt": "PIB por pessoa, US$"}, pc, "count"),
                ctx.stat({"en": "Real growth, IMF estimate",
                          "es": "Crecimiento real, estimación del FMI",
                          "pt": "Crescimento real, estimativa do FMI"},
                         imf, "pct_s"),
                ctx.stat({"en": "Unemployment, ILO model",
                          "es": "Desempleo, modelo de la OIT",
                          "pt": "Desemprego, modelo da OIT"},
                         ctx.col("macro/economy.csv", "unemployment_pct_ilo"),
                         "pct"),
            ],
        },
        {
            "id": "02-fiscal", "topic": "fiscal", "n": "02", "family": MONEY,
            "title": T(en="Public Finances", es="Finanzas públicas",
                       pt="Finanças públicas"),
            "blurb": T(
                en=f"The Fund's general-government estimate, because the "
                   f"national books stop in 2009: revenue of "
                   f"{_v(rev, 2018):.1f}% of GDP in 2018 against spending of "
                   f"{_v(exp, 2018):.1f}%, a deficit of "
                   f"{_v(fiscal, 2018):.1f} points. No debt stock is drawn — "
                   f"the vintage carries no Venezuelan observation, and a hole "
                   f"is not a zero.",
                es=f"La estimación del Fondo para el gobierno general, porque "
                   f"las cuentas nacionales se detienen en 2009: ingresos de "
                   f"{_v(rev, 2018):.1f}% del PIB en 2018 frente a gastos de "
                   f"{_v(exp, 2018):.1f}%, un déficit de "
                   f"{_v(fiscal, 2018):.1f} puntos. No se dibuja stock de "
                   f"deuda: la edición no trae ninguna observación venezolana, "
                   f"y un hueco no es un cero.",
                pt=f"A estimativa do Fundo para o governo geral, porque as "
                   f"contas nacionais param em 2009: receitas de "
                   f"{_v(rev, 2018):.1f}% do PIB em 2018 contra despesas de "
                   f"{_v(exp, 2018):.1f}%, um déficit de "
                   f"{_v(fiscal, 2018):.1f} pontos. Nenhum estoque de dívida é "
                   f"desenhado: a edição não traz observação venezuelana, e um "
                   f"buraco não é um zero."),
            "spark": fiscal,
            "stats": [
                ctx.stat({"en": "Overall balance",
                          "es": "Balance global", "pt": "Saldo total"},
                         fiscal, "pct_gdp_s"),
                ctx.stat({"en": "Revenue", "es": "Ingresos",
                          "pt": "Receitas"}, rev, "pct_gdp"),
                ctx.stat({"en": "Expenditure", "es": "Gastos",
                          "pt": "Despesas"}, exp, "pct_gdp"),
            ],
        },
        {
            "id": "03-spending", "topic": "spending", "n": "03", "family": MONEY,
            "title": T(en="What the Budget Does Not Say",
                       es="Lo que el presupuesto no dice",
                       pt="O que o orçamento não diz"),
            "blurb": T(
                en=f"Three of four panels are pending, and that is the "
                   f"finding: Venezuela reports no COFOG to the IMF and the "
                   f"finance ministry's functional budget stops in 2009, in "
                   f"bolívares of three different currencies. What can be "
                   f"drawn is the whole-economy investment rate — "
                   f"{_v(gfcf, 2013):.1f}% of GDP in 2013, "
                   f"{_v(gfcf, 2024):.1f}% in 2024.",
                es=f"Tres de cuatro paneles están pendientes, y ese es el "
                   f"hallazgo: Venezuela no reporta COFOG al FMI y el "
                   f"presupuesto funcional del ministerio se detiene en 2009, "
                   f"en bolívares de tres monedas distintas. Lo que sí se "
                   f"puede dibujar es la tasa de inversión de toda la economía: "
                   f"{_v(gfcf, 2013):.1f}% del PIB en 2013, "
                   f"{_v(gfcf, 2024):.1f}% en 2024.",
                pt=f"Três de quatro painéis estão pendentes, e essa é a "
                   f"descoberta: a Venezuela não reporta COFOG ao FMI e o "
                   f"orçamento funcional do ministério para em 2009, em "
                   f"bolívares de três moedas diferentes. O que se pode "
                   f"desenhar é a taxa de investimento de toda a economia: "
                   f"{_v(gfcf, 2013):.1f}% do PIB em 2013, "
                   f"{_v(gfcf, 2024):.1f}% em 2024."),
            "spark": gfcf,
            "stats": [
                ctx.stat({"en": "Investment rate, whole economy",
                          "es": "Tasa de inversión, toda la economía",
                          "pt": "Taxa de investimento, toda a economia"},
                         gfcf, "pct_gdp"),
            ],
        },
        {
            "id": "04-trade", "topic": "trade", "n": "04", "family": WORLD,
            "title": T(en="Trade", es="Comercio", pt="Comércio"),
            "blurb": T(
                en=f"The oil surplus of an economy that had stopped importing: "
                   f"exports were {_v(xp, 2019):.1f}% of GDP in 2019 against "
                   f"imports of {_v(im, 2019):.1f}%, a balance of "
                   f"{_v(dict(balance), 2019):+.1f} points. The destinations "
                   f"panel is a hole — the customs service does not answer and "
                   f"Venezuela's own Comtrade reporting stops in 2013.",
                es=f"El superávit petrolero de una economía que había dejado de "
                   f"importar: las exportaciones fueron {_v(xp, 2019):.1f}% "
                   f"del PIB en 2019 frente a importaciones de "
                   f"{_v(im, 2019):.1f}%, un saldo de "
                   f"{_v(dict(balance), 2019):+.1f} puntos. El panel de "
                   f"destinos es un hueco: la aduana no responde y el reporte "
                   f"propio de Venezuela al Comtrade termina en 2013.",
                pt=f"O superávit petroleiro de uma economia que havia parado de "
                   f"importar: as exportações foram {_v(xp, 2019):.1f}% do PIB "
                   f"em 2019 contra importações de {_v(im, 2019):.1f}%, um "
                   f"saldo de {_v(dict(balance), 2019):+.1f} pontos. O painel "
                   f"de destinos é um buraco: a alfândega não responde e o "
                   f"próprio reporte da Venezuela ao Comtrade para em 2013."),
            "spark": balance,
            "stats": [
                ctx.stat({"en": "Trade balance", "es": "Balance comercial",
                          "pt": "Saldo comercial"},
                         balance, "pct_gdp_s"),
                ctx.stat({"en": "Exports", "es": "Exportaciones",
                          "pt": "Exportações"}, xp, "pct_gdp"),
                ctx.stat({"en": "Imports", "es": "Importaciones",
                          "pt": "Importações"}, im, "pct_gdp"),
            ],
        },
        {
            "id": "05-markets", "topic": "markets", "n": "05", "family": MONEY,
            "title": T(en="Markets", es="Mercados", pt="Mercados"),
            "blurb": T(
                en=f"The Central Bank publishes the policy rate, the reserves "
                   f"and the exchange rate, and its site does not answer over "
                   f"TLS from this network. What is left is the official rate "
                   f"to 2017, as an index: 100 in 2006, {_v(fx, 2017):.1f} in "
                   f"2017. The policy rate, the bond and the equity index stay "
                   f"pending rather than drawn from a substitute.",
                es=f"El Banco Central publica la tasa de política, las reservas "
                   f"y el tipo de cambio, y su sitio no responde por TLS desde "
                   f"esta red. Queda el tipo oficial hasta 2017, como índice: "
                   f"100 en 2006, {_v(fx, 2017):.1f} en 2017. La tasa de "
                   f"política, el bono y el índice bursátil siguen pendientes "
                   f"en vez de dibujarse con un sustituto.",
                pt=f"O Banco Central publica a taxa de política, as reservas e "
                   f"o câmbio, e o seu site não responde por TLS a partir "
                   f"desta rede. O que resta é o câmbio oficial até 2017, como "
                   f"índice: 100 em 2006, {_v(fx, 2017):.1f} em 2017. A taxa "
                   f"de política, o título e o índice de ações seguem "
                   f"pendentes em vez de desenhados a partir de um substituto."),
            "spark": fx,
            "stats": [
                ctx.stat({"en": "Currency index, 2006 = 100",
                          "es": "Índice de la moneda, 2006 = 100",
                          "pt": "Índice da moeda, 2006 = 100"},
                         fx, "dec2", kind="level"),
            ],
        },
        {
            "id": "06-people", "topic": "people", "n": "06", "family": PEOPLE,
            "title": T(en="People & Prices", es="Personas y precios",
                       pt="Pessoas e preços"),
            "blurb": T(
                en=f"The one national series that runs the whole window is the "
                   f"INE's Gini, and it barely moves: {peak_gni[1]:.1f} at its "
                   f"highest, {low_gni[1]:.1f} at its lowest in "
                   f"{low_gni[0]}. That flatness is the publisher's claim, not "
                   f"this atlas's finding. Beside it, the prices lens: the "
                   f"Fund's estimate reaches {peak_cpi[1]:,.0f}% in "
                   f"{peak_cpi[0]}, on a log axis, with the BCV's own INPC as "
                   f"a separate short line.",
                es=f"La única serie nacional que recorre toda la ventana es el "
                   f"Gini del INE, y apenas se mueve: {peak_gni[1]:.1f} en su "
                   f"máximo, {low_gni[1]:.1f} en su mínimo en {low_gni[0]}. Esa "
                   f"planitud es la afirmación del editor, no un hallazgo de "
                   f"este atlas. Al lado, la lente de precios: la estimación "
                   f"del Fondo llega a {peak_cpi[1]:,.0f}% en {peak_cpi[0]}, en "
                   f"eje logarítmico, con el INPC del BCV como línea corta "
                   f"aparte.",
                pt=f"A única série nacional que atravessa toda a janela é o "
                   f"Gini do INE, e ele quase não se move: {peak_gni[1]:.1f} no "
                   f"máximo, {low_gni[1]:.1f} no mínimo em {low_gni[0]}. Essa "
                   f"planura é a afirmação do editor, não uma descoberta deste "
                   f"atlas. Ao lado, a lente de preços: a estimativa do Fundo "
                   f"chega a {peak_cpi[1]:,.0f}% em {peak_cpi[0]}, em eixo "
                   f"logarítmico, com o INPC do BCV como linha curta separada."),
            "spark": gini,
            "stats": [
                ctx.stat({"en": "Gini, INE survey", "es": "Gini, encuesta del INE",
                          "pt": "Gini, pesquisa do INE"}, gini, "dec2"),
                ctx.stat({"en": "Inflation, IMF estimate",
                          "es": "Inflación, estimación del FMI",
                          "pt": "Inflação, estimativa do FMI"}, cpi, "pct"),
            ],
        },
        {
            "id": "07-world", "topic": "world", "n": "07", "family": WORLD,
            "title": T(en="Venezuela in the World", es="Venezuela en el mundo",
                       pt="Venezuela no mundo"),
            "blurb": T(
                en=f"Dollar GDP on a log axis, from US${peak_gdp[1]:,.0f}bn in "
                   f"{peak_gdp[0]} to US${gdp[-1][1]:,.0f}bn in {gdp[-1][0]} — "
                   f"and the Fund's line beside it, "
                   f"US${gdp_imf[-1][1]:,.0f}bn, because the two convert the "
                   f"same bolívar GDP at different official rates. Development "
                   f"fell with it: the HDI is {hdi[-1][1]:.3f} in {hdi[-1][0]}, "
                   f"from {max(hdi, key=lambda p: p[1])[1]:.3f} in 2013.",
                es=f"PIB en dólares en eje logarítmico, de US${peak_gdp[1]:,.0f} "
                   f"mil millones en {peak_gdp[0]} a US${gdp[-1][1]:,.0f} mil "
                   f"millones en {gdp[-1][0]} — y la línea del Fondo al lado, "
                   f"US${gdp_imf[-1][1]:,.0f} mil millones, porque ambos "
                   f"convierten el mismo PIB en bolívares a tipos oficiales "
                   f"distintos. El desarrollo cayó con él: el IDH es "
                   f"{hdi[-1][1]:.3f} en {hdi[-1][0]}, desde "
                   f"{max(hdi, key=lambda p: p[1])[1]:.3f} en 2013.",
                pt=f"PIB em dólares em eixo logarítmico, de US${peak_gdp[1]:,.0f} "
                   f"bilhões em {peak_gdp[0]} para US${gdp[-1][1]:,.0f} bilhões "
                   f"em {gdp[-1][0]} — e a linha do Fundo ao lado, "
                   f"US${gdp_imf[-1][1]:,.0f} bilhões, porque os dois convertem "
                   f"o mesmo PIB em bolívares a câmbios oficiais diferentes. O "
                   f"desenvolvimento caiu junto: o IDH é {hdi[-1][1]:.3f} em "
                   f"{hdi[-1][0]}, de {max(hdi, key=lambda p: p[1])[1]:.3f} em "
                   f"2013."),
            "spark": gdp,
            "stats": [
                ctx.stat({"en": "GDP, US$ bn", "es": "PIB, US$ mil millones",
                          "pt": "PIB, US$ bilhões"}, gdp, "usd_bn"),
                ctx.stat({"en": "Human Development Index",
                          "es": "Índice de Desarrollo Humano",
                          "pt": "Índice de Desenvolvimento Humano"},
                         hdi, "dec3"),
                ctx.stat({"en": "Reserves, US$ bn",
                          "es": "Reservas, US$ mil millones",
                          "pt": "Reservas, US$ bilhões"}, reserves, "usd_bn"),
            ],
        },
        {
            "id": "08-demography", "topic": "demography", "n": "08",
            "family": PEOPLE,
            "title": T(en="Demography", es="Demografía", pt="Demografia"),
            "blurb": T(
                en=f"The UN model peaks at "
                   f"{max(pop, key=lambda p: p[1])[1] / 1e6:.1f}m in "
                   f"{max(pop, key=lambda p: p[1])[0]} and settles at "
                   f"{pop[-1][1] / 1e6:.1f}m in {pop[-1][0]}; no census has "
                   f"been taken since 2011, so the fall is modelled emigration, "
                   f"not a count. Births nearly halve while deaths creep up, "
                   f"and fertility sits below replacement from the first year "
                   f"of the window.",
                es=f"El modelo de la ONU alcanza "
                   f"{max(pop, key=lambda p: p[1])[1] / 1e6:.1f} millones en "
                   f"{max(pop, key=lambda p: p[1])[0]} y se asienta en "
                   f"{pop[-1][1] / 1e6:.1f} millones en {pop[-1][0]}; no hay "
                   f"censo desde 2011, así que la caída es emigración modelada, "
                   f"no un conteo. Los nacimientos casi se reducen a la mitad "
                   f"mientras las muertes suben, y la fecundidad está por debajo "
                   f"del reemplazo desde el primer año de la ventana.",
                pt=f"O modelo da ONU atinge "
                   f"{max(pop, key=lambda p: p[1])[1] / 1e6:.1f} milhões em "
                   f"{max(pop, key=lambda p: p[1])[0]} e assenta em "
                   f"{pop[-1][1] / 1e6:.1f} milhões em {pop[-1][0]}; não há "
                   f"censo desde 2011, então a queda é emigração modelada, não "
                   f"uma contagem. Os nascimentos quase caem pela metade "
                   f"enquanto as mortes sobem, e a fecundidade fica abaixo da "
                   f"reposição desde o primeiro ano da janela."),
            "spark": [(y, v / 1e6) for y, v in pop],
            "stats": [
                ctx.stat({"en": "Population", "es": "Población",
                          "pt": "População"},
                         [(y, v / 1e6) for y, v in pop], "pop_mn",
                         kind="level"),
                ctx.stat({"en": "Fertility, children per woman",
                          "es": "Fecundidad, hijos por mujer",
                          "pt": "Fecundidade, filhos por mulher"}, fert,
                         "dec2"),
                ctx.stat({"en": "Natural increase, per 1,000",
                          "es": "Crecimiento natural, por 1.000",
                          "pt": "Crescimento natural, por 1.000"},
                         [(y, a - b) for (y, a), (yy, b)
                          in zip(birth, death) if y == yy], "dec2"),
            ],
        },
        {
            "id": "09-security", "topic": "security", "n": "09",
            "family": PEOPLE,
            "title": T(en="Security", es="Seguridad", pt="Segurança"),
            "blurb": T(
                en=f"UNODC puts the homicide peak at {peak_hom[1]:.1f} per "
                   f"100,000 in {peak_hom[0]} and the last reading at "
                   f"{hom[-1][1]:.1f} in {hom[-1][0]} — an estimate, not a "
                   f"police count, with no observation at all for 2013 and "
                   f"2018. The suicide spike of 2016 is a change of WHO "
                   f"estimate vintage; road deaths rise as traffic thins.",
                es=f"La UNODC sitúa el pico de homicidios en {peak_hom[1]:.1f} "
                   f"por 100 000 en {peak_hom[0]} y la última lectura en "
                   f"{hom[-1][1]:.1f} en {hom[-1][0]} — una estimación, no un "
                   f"registro policial, y sin ninguna observación para 2013 ni "
                   f"2018. El salto del suicidio en 2016 es un cambio de "
                   f"edición de la estimación de la OMS; las muertes de "
                   f"tránsito suben mientras el tráfico se adelgaza.",
                pt=f"A UNODC situa o pico de homicídios em {peak_hom[1]:.1f} por "
                   f"100 000 em {peak_hom[0]} e a última leitura em "
                   f"{hom[-1][1]:.1f} em {hom[-1][0]} — uma estimativa, não um "
                   f"registro policial, e sem nenhuma observação para 2013 e "
                   f"2018. O salto do suicídio em 2016 é uma mudança de edição "
                   f"da estimativa da OMS; as mortes no trânsito sobem enquanto "
                   f"o tráfego diminui."),
            "spark": hom,
            "stats": [
                ctx.stat({"en": "Homicide, per 100,000",
                          "es": "Homicidios, por 100.000",
                          "pt": "Homicídios, por 100.000"}, hom, "per100k"),
                ctx.stat({"en": "Suicide, per 100,000",
                          "es": "Suicidios, por 100.000",
                          "pt": "Suicídios, por 100.000"}, sui, "per100k"),
            ],
        },
        {
            "id": "10-mortality", "topic": "mortality", "n": "10",
            "family": PEOPLE,
            "title": T(en="Mortality", es="Mortalidad", pt="Mortalidade"),
            "blurb": T(
                en=f"The published death rate is the UN model, not the civil "
                   f"register: {death[0][1]:.1f} per 1,000 in {death[0][0]}, "
                   f"{death[-1][1]:.1f} in {death[-1][0]}. Life expectancy ends "
                   f"at {life[-1][1]:.1f} years, half a year below where it "
                   f"started. Excess deaths and COVID-19 stay pending: both "
                   f"need registered death counts, which are legacy .xls files "
                   f"that are not staged.",
                es=f"La tasa de mortalidad publicada es el modelo de la ONU, no "
                   f"el registro civil: {death[0][1]:.1f} por 1 000 en "
                   f"{death[0][0]}, {death[-1][1]:.1f} en {death[-1][0]}. La "
                   f"esperanza de vida termina en {life[-1][1]:.1f} años, medio "
                   f"año por debajo de donde empezó. La mortalidad excedente y "
                   f"la COVID-19 siguen pendientes: ambas necesitan conteos de "
                   f"defunciones registradas, que son archivos .xls heredados "
                   f"que no están preparados.",
                pt=f"A taxa de mortalidade publicada é o modelo da ONU, não o "
                   f"registro civil: {death[0][1]:.1f} por 1 000 em "
                   f"{death[0][0]}, {death[-1][1]:.1f} em {death[-1][0]}. A "
                   f"expectativa de vida termina em {life[-1][1]:.1f} anos, meio "
                   f"ano abaixo de onde começou. Excesso de mortes e COVID-19 "
                   f"seguem pendentes: ambos exigem contagens de óbitos "
                   f"registrados, que são arquivos .xls legados não preparados."),
            "spark": life,
            "stats": [
                ctx.stat({"en": "Deaths per 1,000", "es": "Muertes por 1.000",
                          "pt": "Mortes por 1.000"}, death, "dec2"),
                ctx.stat({"en": "Life expectancy, years",
                          "es": "Esperanza de vida, años",
                          "pt": "Expectativa de vida, anos"}, life, "years"),
            ],
        },
        {
            "id": "11-migration", "topic": "migration", "n": "11",
            "family": PEOPLE,
            "title": T(en="Migration", es="Migración", pt="Migração"),
            "blurb": T(
                en=f"Net migration leaves the comparable range in 2017 and "
                   f"reaches {worst_net[1]:.1f} per 1,000 in {worst_net[0]}, "
                   f"so that slot stays pending and the whole series is drawn "
                   f"in a lens on its own axis. UNHCR's caseload abroad peaks "
                   f"at {peak_case[1] / 1e6:.2f} million in {peak_case[0]}: a "
                   f"second publisher, a different measure, drawn on a second "
                   f"axis and never divided by Venezuela's population.",
                es=f"La migración neta sale del rango comparable en 2017 y "
                   f"llega a {worst_net[1]:.1f} por 1 000 en {worst_net[0]}, "
                   f"así que esa posición sigue pendiente y toda la serie se "
                   f"dibuja en una lente con eje propio. El stock de ACNUR en "
                   f"el exterior alcanza {peak_case[1] / 1e6:.2f} millones en "
                   f"{peak_case[0]}: otro editor, otra medida, dibujada en un "
                   f"segundo eje y nunca dividida por la población venezolana.",
                pt=f"A migração líquida sai da faixa comparável em 2017 e chega "
                   f"a {worst_net[1]:.1f} por 1 000 em {worst_net[0]}, então "
                   f"essa posição segue pendente e toda a série é desenhada "
                   f"numa lente com eixo próprio. O estoque do ACNUR no exterior "
                   f"atinge {peak_case[1] / 1e6:.2f} milhões em {peak_case[0]}: "
                   f"outro editor, outra medida, desenhada num segundo eixo e "
                   f"nunca dividida pela população venezuelana."),
            "spark": net,
            "stats": [
                # The card names the wave's own year rather than the
                # mild latest reading: the stat prints its year beside it.
                ctx.stat({"en": "Net migration, per 1,000",
                          "es": "Migración neta, por 1.000",
                          "pt": "Migração líquida, por 1.000"}, net, "dec2",
                         year=worst_net[0]),
                ctx.stat({"en": "Protection status abroad",
                          "es": "Estatus de protección en el exterior",
                          "pt": "Status de proteção no exterior"},
                         caseload, "count", kind="level"),
                ctx.stat({"en": "Foreign-born share",
                          "es": "Población nacida en el exterior",
                          "pt": "Parcela nascida no exterior"},
                         stock_share, "pct", kind="level"),
            ],
        },
    ]

    # The alt text is per locale and is written here rather than assembled
    # from the card's own figures: a screen-reader user gets the shape of the
    # plate, which is what the figure says and not what its three numbers say.
    ALT = {
        "01-economy": T(
            en="Four panels: real GDP growth as World Bank bars with the IMF's "
               "staff estimate as a line, both troughing in 2020; GDP per "
               "person on a log axis; a pending inflation slot with its reason; "
               "and unemployment on the ILO model beside the Fund's series.",
            es="Cuatro paneles: el crecimiento real del PIB en barras del Banco "
               "Mundial con la estimación del FMI como línea, ambos con su "
               "mínimo en 2020; el PIB por persona en eje logarítmico; una "
               "posición de inflación pendiente con su razón; y el desempleo "
               "del modelo de la OIT junto a la serie del Fondo.",
            pt="Quatro painéis: o crescimento real do PIB em barras do Banco "
               "Mundial com a estimativa do FMI como linha, ambos com mínimo em "
               "2020; o PIB por pessoa em eixo logarítmico; uma posição de "
               "inflação pendente com a sua razão; e o desemprego do modelo da "
               "OIT ao lado da série do Fundo."),
        "02-fiscal": T(
            en="Four panels on the Fund's general-government estimate: revenue "
               "and expenditure as shares of GDP; the overall balance as bars "
               "with the primary balance as a line; a pending debt slot; and "
               "interest paid.",
            es="Cuatro paneles sobre la estimación del Fondo para el gobierno "
               "general: ingresos y gastos como proporción del PIB; el balance "
               "global en barras con el balance primario como línea; una "
               "posición de deuda pendiente; y los intereses pagados.",
            pt="Quatro painéis sobre a estimativa do Fundo para o governo "
               "geral: receitas e despesas como parcela do PIB; o saldo total "
               "em barras com o saldo primário como linha; uma posição de "
               "dívida pendente; e os juros pagos."),
        "03-spending": T(
            en="Four panels: three pending for the functional breakdown, the "
               "social-protection split and public investment, each with the "
               "route that failed; and whole-economy investment falling from a "
               "quarter of GDP to under 4%.",
            es="Cuatro paneles: tres pendientes por la desagregación funcional, "
               "la separación de protección social y la inversión pública, cada "
               "uno con la ruta que falló; y la inversión de toda la economía "
               "cayendo de un cuarto del PIB a menos del 4%.",
            pt="Quatro painéis: três pendentes pela desagregação funcional, a "
               "separação da proteção social e o investimento público, cada um "
               "com a rota que falhou; e o investimento de toda a economia "
               "caindo de um quarto do PIB para menos de 4%."),
        "04-trade": T(
            en="Four panels: exports and imports as shares of GDP from 2012; "
               "the trade balance as bars, reaching its surplus in 2019; a "
               "pending destinations slot; and a lens deriving the same two "
               "flows in US$ billion.",
            es="Cuatro paneles: exportaciones e importaciones como proporción del PIB "
               "desde 2012; el balance comercial en barras, con su superávit en "
               "2019; una posición de destinos pendiente; y una lente que deriva "
               "los mismos dos flujos en miles de millones de dólares.",
            pt="Quatro painéis: exportações e importações como parcela do PIB "
               "desde 2012; o saldo comercial em barras, com seu superávit em "
               "2019; uma posição de destinos pendente; e uma lente que deriva "
               "os mesmos dois fluxos em bilhões de dólares."),
        "05-markets": T(
            en="Four panels: pending policy rate, bond yield and equity index, "
               "each with its reason; and the official exchange rate as an "
               "index on a log axis from 100 in 2006 to 21.5 in 2017, marked "
               "with the 2018 redenomination.",
            es="Cuatro paneles: tasa de política, rendimiento de bonos e índice "
               "bursátil pendientes, cada uno con su razón; y el tipo de cambio "
               "oficial como índice en eje logarítmico de 100 en 2006 a 21,5 en "
               "2017, marcado con la redenominación de 2018.",
            pt="Quatro painéis: taxa de política, rendimento de títulos e índice "
               "de ações pendentes, cada um com a sua razão; e o câmbio oficial "
               "como índice em eixo logarítmico de 100 em 2006 para 21,5 em "
               "2017, marcado com a redenominação de 2018."),
        "06-people": T(
            en="Four panels: the INE's Gini as a nearly flat line; pending "
               "poverty and minimum-wage slots; and a prices lens on a log axis "
               "where the Fund's staff estimate rises to 65,374% in 2018, with "
               "the BCV's own INPC drawn as a separate short line.",
            es="Cuatro paneles: el Gini del INE como una línea casi plana; "
               "posiciones pendientes de pobreza y salario mínimo; y una lente "
               "de precios en eje logarítmico donde la estimación del Fondo "
               "sube a 65.374% en 2018, con el INPC del BCV dibujado como "
               "línea corta aparte.",
            pt="Quatro painéis: o Gini do INE como uma linha quase plana; "
               "posições pendentes de pobreza e salário mínimo; e uma lente de "
               "preços em eixo logarítmico onde a estimativa do Fundo sobe a "
               "65.374% em 2018, com o INPC do BCV desenhado como linha curta "
               "separada."),
        "07-world": T(
            en="Four panels: GDP in current dollars on a log axis, the World "
               "Bank's line and the IMF's; the Human Development Index; a "
               "pending corruption index; and reserves on a log axis, ending in "
               "2017.",
            es="Cuatro paneles: el PIB en dólares corrientes en eje "
               "logarítmico, la línea del Banco Mundial y la del FMI; el Índice "
               "de Desarrollo Humano; un índice de corrupción pendiente; y las "
               "reservas en eje logarítmico, que terminan en 2017.",
            pt="Quatro painéis: o PIB em dólares correntes em eixo logarítmico, "
               "a linha do Banco Mundial e a do FMI; o Índice de "
               "Desenvolvimento Humano; um índice de corrupção pendente; e as "
               "reservas em eixo logarítmico, que terminam em 2017."),
        "08-demography": T(
            en="Four panels: the population index peaking in 2016 and settling "
               "below it; fertility against the replacement line; crude birth "
               "and death rates converging; and natural increase as bars, with "
               "net migration left to the migration plate.",
            es="Cuatro paneles: el índice de población con su pico en 2016 y "
               "asentándose por debajo; la fecundidad frente a la línea de "
               "reemplazo; las tasas brutas de natalidad y mortalidad "
               "convergiendo; y el crecimiento natural en barras, con la "
               "migración neta en la plancha de migración.",
            pt="Quatro painéis: o índice de população com pico em 2016 e "
               "assentando abaixo dele; a fecundidade contra a linha de "
               "reposição; as taxas brutas de natalidade e mortalidade "
               "convergindo; e o crescimento natural em barras, com a migração "
               "líquida na prancha de migração."),
        "09-security": T(
            en="Three panels: the homicide rate on a log axis with the 2013 and "
               "2018 holes left open; the suicide rate with its 2016 estimate "
               "spike; and road deaths rising to 2019.",
            es="Tres paneles: la tasa de homicidios en eje logarítmico con los "
               "huecos de 2013 y 2018 abiertos; la tasa de suicidios con su "
               "salto de edición en 2016; y las muertes de tránsito subiendo "
               "hasta 2019.",
            pt="Três painéis: a taxa de homicídios em eixo logarítmico com os "
               "buracos de 2013 e 2018 abertos; a taxa de suicídios com seu "
               "salto de edição em 2016; e as mortes no trânsito subindo até "
               "2019."),
        "10-mortality": T(
            en="Four panels: the modelled crude death rate rising; pending "
               "excess-death and COVID-19 slots with their routes; and life "
               "expectancy as a lens, dipping in 2021.",
            es="Cuatro paneles: la tasa bruta de mortalidad modelada subiendo; "
               "posiciones pendientes de mortalidad excedente y COVID-19 con "
               "sus rutas; y la esperanza de vida como lente, con una caída en "
               "2021.",
            pt="Quatro painéis: a taxa bruta de mortalidade modelada subindo; "
               "posições pendentes de excesso de mortes e COVID-19 com as suas "
               "rotas; e a expectativa de vida como lente, com queda em 2021."),
        "11-migration": T(
            en="Four panels: pending immigration and emigration flows; a "
               "pending net-migration slot; the foreign-born share in snapshot "
               "years; and a lens with net migration as bars and UNHCR's "
               "caseload abroad as a line on a second axis.",
            es="Cuatro paneles: flujos de inmigración y emigración pendientes; "
               "una posición de migración neta pendiente; la parcela nacida en "
               "el exterior en años de corte; y una lente con la migración neta "
               "en barras y el stock de ACNUR como línea en un segundo eje.",
            pt="Quatro painéis: fluxos de imigração e emigração pendentes; uma "
               "posição de migração líquida pendente; a parcela nascida no "
               "exterior em anos de corte; e uma lente com a migração líquida "
               "em barras e o estoque do ACNUR como linha num segundo eixo."),
    }
    for ch in chapters:
        ch["alt"] = ALT[ch["id"]]

    # The copy carries numbers read from the CSVs, so it is localised with
    # the same number rules the page uses: a Spanish reader gets 29,8% and
    # not 29.8%, and a Portuguese one 1.598.166. Years and unit labels are
    # untouched — `localize_prose` only rewrites decimals and thousands.
    from core.sitebuild import localize_prose
    for ch in chapters:
        for key in ("title", "blurb", "alt"):
            ch[key] = {loc: localize_prose(text, ctx.c.number_style(loc))
                       for loc, text in ch[key].items()}
    return chapters


def _stock_share(ctx):
    """Foreign-born stock over the same year's population, %.

    Snapshot years only (2010, 2015, 2020, 2024): the UN DESA stock is not
    published annually and is never interpolated, so the card reports the
    latest of those four, not a 2025 value that does not exist.
    """
    stock = dict(ctx.col("migration/migration.csv", "migrant_stock"))
    pop = dict(ctx.col("demography/population.csv", "population"))
    return [(y, stock[y] / pop[y] * 100) for y in sorted(stock)
            if y in pop and pop[y]]
