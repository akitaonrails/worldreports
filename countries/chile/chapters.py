"""Chile's twelve page cards, computed from the committed CSVs.

Every figure on a card is read from the same file its plate draws, at build
time, so a card and its plate cannot disagree. The copy names the
institution behind each series and, where Phase A could not reach the
national publisher, says so on the card itself rather than in a footnote.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def _scaled(ctx, path, column, divisor):
    return [(y, v / divisor) for y, v in ctx.col(path, column)]


def _fx_index(ctx, year=2025):
    pairs = ctx.col("macro/fx.csv", "clp_per_usd")
    base = dict(pairs)[2006]
    return [(y, base / v * 100) for y, v in pairs]


def _share(ctx, partner=None):
    """The 2024 destination shares, as (partner, share) pairs."""
    t = ctx.c.table("trade/partners_2024.csv") or {}
    return list(zip(t.get("partner", []), t.get("share_pct", [])))


def headline(ctx):
    T = ctx.text
    return [
        ctx.stat(T(es="PIB", en="GDP", pt="PIB"),
                 ctx.col("world/world.csv", "gdp_usd_bn"),
                 "usd_bn", kind="level"),
        ctx.stat(T(es="PIB por persona, US$", en="GDP per person, US$",
                   pt="PIB por pessoa, US$"),
                 ctx.col("world/world.csv", "gdp_per_person_usd"),
                 "count", kind="level"),
        ctx.stat(T(es="Población", en="Population", pt="População"),
                 _scaled(ctx, "demography/demography.csv", "population", 1e6),
                 "pop_mn", kind="level"),
        ctx.stat(T(es="Inflación", en="Inflation", pt="Inflação"),
                 ctx.col("macro/economy.csv", "inflation_pct"), "pct"),
        ctx.stat(T(es="Crecimiento real del PIB", en="Real GDP growth",
                   pt="Crescimento real do PIB"),
                 ctx.col("macro/economy.csv", "real_growth_pct"), "pct_s"),
        ctx.stat(T(es="Desempleo", en="Unemployment", pt="Desemprego"),
                 ctx.col("macro/economy.csv", "unemployment_pct"), "pct"),
        ctx.stat(T(es="Deuda pública bruta", en="Gross public debt",
                   pt="Dívida pública bruta"),
                 ctx.col("fiscal/fiscal.csv", "debt_pct_gdp"), "pct_gdp",
                 kind="level"),
        ctx.stat(T(es="Homicidios por 100 mil", en="Homicides per 100,000",
                   pt="Homicídios por 100 mil"),
                 ctx.col("security/security.csv", "homicide_per_100k"),
                 "per100k2", kind="level"),
    ]


def build(ctx):
    T = ctx.text
    E = "macro/economy.csv"
    F = "fiscal/fiscal.csv"
    S = "spending/cofog.csv"
    TR = "trade/trade.csv"
    W = "world/world.csv"
    D = "demography/demography.csv"
    M = "mortality/mortality.csv"
    G = "security/security.csv"
    MI = "migration/migration.csv"

    partners = _share(ctx)
    top = max(partners, key=lambda p: p[1]) if partners else ("China", 0.0)
    fx = _fx_index(ctx)
    fx25 = dict(fx)[2025]

    specs = [
        ("01-economy", "economy", MONEY, "macro/economy.csv",
         "real_growth_pct",
         T(es="La economía", en="The Economy", pt="A economia"),
         T(es="Crecimiento, ingreso, precios y empleo en las series del Banco "
              "Mundial que republican las cuentas, el IPC del INE y el "
              "desempleo modelado por la OIT.",
           en="Growth, income, prices and jobs from the World Bank series "
              "that republish Chile's accounts, the INE's CPI and the "
              "ILO-modelled unemployment rate.",
           pt="Crescimento, renda, preços e emprego nas séries do Banco "
              "Mundial que republicam as contas chilenas, o IPC do INE e o "
              "desemprego modelado pela OIT."),
         T(es=f"Cuatro paneles para 2006–2025. El PIB real cayó 6,1% en 2020 "
              f"y rebotó 11,3% en 2021; la inflación llegó a 11,6% en 2022, "
              f"la más alta de la ventana, y el desempleo modelado marcó "
              f"11,3% en 2009. El PIB por persona pasó de US$ 9.319 a "
              f"US$ 17.995 en dólares corrientes: un nivel nominal, no un "
              f"ingreso disponible.",
           en=f"Four panels for 2006–2025. Real GDP fell 6.1% in 2020 and "
              f"rebounded 11.3% in 2021; inflation reached 11.6% in 2022, "
              f"the highest of the window, and modelled unemployment peaked "
              f"at 11.3% in 2009. GDP per person went from US$9,319 to "
              f"US$17,995 in current dollars — a nominal level, not "
              f"disposable income.",
           pt=f"Quatro painéis para 2006–2025. O PIB real caiu 6,1% em 2020 e "
              f"rebateu 11,3% em 2021; a inflação chegou a 11,6% em 2022, a "
              f"mais alta da janela, e o desemprego modelado marcou 11,3% em "
              f"2009. O PIB por pessoa passou de US$ 9.319 a US$ 17.995 em "
              f"dólares correntes: um nível nominal, não renda disponível."),
         [E, "world/world.csv"]),

        ("02-fiscal", "fiscal", MONEY, "fiscal/fiscal.csv", "debt_pct_gdp",
         T(es="Finanzas públicas", en="Public Finances",
           pt="Finanças públicas"),
         T(es="Gobierno general, años calendario, en una sola edición del FMI: "
              "ingresos y gastos del Fiscal Monitor, balance y deuda del WEO.",
           en="General government, calendar years, from one IMF vintage: "
              "revenue and spending from the Fiscal Monitor, the balance and "
              "debt from the WEO.",
           pt="Governo geral, anos-calendário, numa única edição do FMI: "
              "receitas e despesas do Fiscal Monitor, saldo e dívida do WEO."),
         T(es=f"El superávit del cobre (+7,5% del PIB en 2006) se gastó: el "
              f"balance llegó a -7,5% en 2021 y la deuda bruta subió de 5% "
              f"del PIB en 2006 a 41,5% en 2025. Los intereses pagados "
              f"quedan pendientes: no hay indicador de gobierno general en "
              f"una ruta oficial accesible.",
           en=f"The copper surplus (+7.5% of GDP in 2006) was spent: the "
              f"balance reached -7.5% in 2021 and gross debt rose from 5% of "
              f"GDP in 2006 to 41.5% in 2025. Interest paid stays pending: "
              f"no general-government indicator sits on an accessible "
              f"official route.",
           pt=f"O superávit do cobre (+7,5% do PIB em 2006) foi gasto: o "
              f"saldo chegou a -7,5% em 2021 e a dívida bruta subiu de 5% do "
              f"PIB em 2006 para 41,5% em 2025. Os juros pagos seguem "
              f"pendentes: não há indicador de governo geral numa rota "
              f"oficial acessível."),
         [F]),

        ("03-spending", "spending", MONEY, "spending/cofog.csv", "total",
         T(es="Gasto público", en="Spending", pt="Gasto público"),
         T(es="La clasificación funcional (COFOG) que Chile reporta a la OCDE "
              "desde 2018, junto a la inversión de toda la economía y la del "
              "gobierno, cuya serie se detuvo en 2012.",
           en="The functional classification (COFOG) Chile reports to the "
              "OECD from 2018, beside the whole economy's investment rate "
              "and the government's own, whose series stopped in 2012.",
           pt="A classificação funcional (COFOG) que o Chile reporta à OCDE "
              "desde 2018, ao lado do investimento de toda a economia e do "
              "governo, cuja série parou em 2012."),
         T(es=f"El gasto total llegó a 34,1% del PIB en 2021, cuando la "
              f"protección social sola tomó 15,5% (6,9% en 2018). La "
              f"inversión de toda la economía se movió entre 21,1% y 26,9% "
              f"del PIB; la inversión pública solo existe para 2007–2012, "
              f"con 2,4% a 2,9%.",
           en=f"Total spending reached 34.1% of GDP in 2021, when social "
              f"protection alone took 15.5% (6.9% in 2018). Whole-economy "
              f"investment ran between 21.1% and 26.9% of GDP; public "
              f"investment exists only for 2007–2012, at 2.4% to 2.9%.",
           pt=f"O gasto total chegou a 34,1% do PIB em 2021, quando a "
              f"proteção social sozinha tomou 15,5% (6,9% em 2018). O "
              f"investimento de toda a economia ficou entre 21,1% e 26,9% do "
              f"PIB; o investimento público só existe para 2007–2012, com "
              f"2,4% a 2,9%."),
         [S, "spending/public_investment.csv", E]),

        ("04-trade", "trade", WORLD, "trade/trade.csv", "trade_balance_pct_gdp",
         T(es="Comercio", en="Trade", pt="Comércio"),
         T(es="Exportaciones e importaciones de bienes y servicios en las "
              "cuentas nacionales, más el retrato aduanero de 2024 por "
              "destino.",
           en="Goods and services exports and imports on the national-accounts "
              "basis, plus the 2024 customs snapshot by destination.",
           pt="Exportações e importações de bens e serviços nas contas "
              "nacionais, mais o retrato aduaneiro de 2024 por destino."),
         T(es=f"Las exportaciones cayeron de 45,1% del PIB en 2007 a 34,6% en "
              f"2025 y el balance pasó de +14,0% a -4,0% en 2022. En 2024 "
              f"China recibió {top[1]:.1f}% de los bienes exportados, "
              f"Estados Unidos 15,9% y Japón 8,4%: un año, no una serie.",
           en=f"Exports fell from 45.1% of GDP in 2007 to 34.6% in 2025 and "
              f"the balance went from +14.0% to -4.0% in 2022. In 2024 China "
              f"took {top[1]:.1f}% of goods exported, the United States "
              f"15.9% and Japan 8.4% — one year, not a series.",
           pt=f"As exportações caíram de 45,1% do PIB em 2007 para 34,6% em "
              f"2025 e o saldo passou de +14,0% para -4,0% em 2022. Em 2024 "
              f"a China recebeu {top[1]:.1f}% dos bens exportados, os "
              f"Estados Unidos 15,9% e o Japão 8,4%: um ano, não uma série."),
         [TR, "trade/partners_2024.csv"]),

        ("05-markets", "markets", MONEY, "markets/policy_rate.csv",
         "policy_rate_pct",
         T(es="Mercados", en="Markets", pt="Mercados"),
         T(es="La tasa de política del Banco Central y el peso frente al "
              "dólar; el rendimiento a diez años y el IPSA quedan "
              "pendientes por rutas cerradas.",
           en="The Banco Central's policy rate and the peso against the "
              "dollar; the 10-year yield and the IPSA stay pending behind "
              "closed routes.",
           pt="A taxa de política do Banco Central e o peso frente ao dólar; "
              "o rendimento de dez anos e o IPSA seguem pendentes por rotas "
              "fechadas."),
         T(es=f"La tasa promedió 5,0% en 2006, 0,8% en 2020 y 10,5% en 2023; "
              f"el peso pasó de 530 a 951 por dólar y conserva {fx25:.0f} de "
              f"su valor de 2006 en el índice. Los dos paneles pendientes no "
              f"se sustituyen por un proxy.",
           en=f"The rate averaged 5.0% in 2006, 0.8% in 2020 and 10.5% in "
              f"2023; the peso went from 530 to 951 per dollar and keeps "
              f"{fx25:.0f} of its 2006 value on the index. The two pending "
              f"panels are not replaced by a proxy.",
           pt=f"A taxa ficou em média em 5,0% em 2006, 0,8% em 2020 e 10,5% "
              f"em 2023; o peso passou de 530 para 951 por dólar e conserva "
              f"{fx25:.0f} do seu valor de 2006 no índice. Os dois painéis "
              f"pendentes não são substituídos por um proxy."),
         ["markets/policy_rate.csv", "macro/fx.csv", E]),

        ("06-credit", "credit", MONEY, "credit/household_credit.csv",
         "hh_debt_pct_gdp_q4",
         T(es="Crédito", en="Credit", pt="Crédito"),
         T(es="Deuda de los hogares con todas las fuentes, saldo de fin de "
              "año, en la serie de crédito total del BIS.",
           en="Household debt from all sources, the year-end stock, on the "
              "BIS total-credit series.",
           pt="Dívida das famílias com todas as fontes, estoque de fim de "
              "ano, na série de crédito total do BIS."),
         T(es=f"La deuda de los hogares subió de 26,4% del PIB a fines de "
              f"2006 a un máximo de 48,3% en 2020 y bajó a 43,8% en 2025. La "
              f"tasa de interés de los créditos y la morosidad quedan "
              f"pendientes: las estadísticas de la CMF son HTML o están tras "
              f"un 403.",
           en=f"Household debt rose from 26.4% of GDP at the end of 2006 to a "
              f"peak of 48.3% in 2020 and fell to 43.8% in 2025. The lending "
              f"rate and the arrears ratio stay pending: the CMF's "
              f"statistics are HTML or behind a 403.",
           pt=f"A dívida das famílias subiu de 26,4% do PIB no fim de 2006 "
              f"para um pico de 48,3% em 2020 e caiu para 43,8% em 2025. A "
              f"taxa de juros dos créditos e a inadimplência seguem "
              f"pendentes: as estatísticas da CMF são HTML ou estão atrás de "
              f"um 403."),
         ["credit/household_credit.csv"]),

        ("07-people", "people", PEOPLE, "people/gini.csv", "gini",
         T(es="Personas", en="People", pt="Pessoas"),
         T(es="La encuesta CASEN, que no es anual: el Gini de ingresos y las "
              "dos líneas de pobreza se dibujan como observaciones, sin "
              "interpolar.",
           en="The CASEN survey, which is not annual: the income Gini and "
              "both poverty lines are drawn as observations, never "
              "interpolated.",
           pt="A pesquisa CASEN, que não é anual: o Gini de renda e as duas "
              "linhas de pobreza são desenhados como observações, sem "
              "interpolação."),
         T(es=f"El Gini bajó de 47,7 en 2006 a 43,0 en 2024, con un repunte a "
              f"47,0 en 2020. La pobreza por línea nacional cayó de 28,7% a "
              f"6,5% (2022) y la línea de US$ 8,30 diarios marca 4,5% en "
              f"2024: son preguntas distintas. El salario mínimo queda "
              f"pendiente y la ruta siguiente es la ley en bcn.cl.",
           en=f"The Gini fell from 47.7 in 2006 to 43.0 in 2024, with a rise "
              f"to 47.0 in 2020. Poverty on the national line fell from 28.7% "
              f"to 6.5% (2022) and the US$8.30-a-day line reads 4.5% in "
              f"2024 — different questions. The minimum wage stays pending, "
              f"and the next route is the statutes on bcn.cl.",
           pt=f"O Gini caiu de 47,7 em 2006 para 43,0 em 2024, com repique a "
              f"47,0 em 2020. A pobreza pela linha nacional caiu de 28,7% "
              f"para 6,5% (2022) e a linha de US$ 8,30 por dia marca 4,5% em "
              f"2024: são perguntas distintas. O salário mínimo segue "
              f"pendente, e a próxima rota é a lei em bcn.cl."),
         ["people/gini.csv", "people/poverty.csv"]),

        ("08-world", "world", WORLD, "world/world.csv", "gdp_usd_bn",
         T(es="Chile en el mundo", en="Chile in the World",
           pt="O Chile no mundo"),
         T(es="Tamaño en dólares corrientes, desarrollo humano, percepción de "
              "corrupción y reservas, en definiciones internacionales.",
           en="Size in current dollars, human development, corruption "
              "perceptions and reserves, on international definitions.",
           pt="Tamanho em dólares correntes, desenvolvimento humano, perceção "
              "da corrupção e reservas, em definições internacionais."),
         T(es="El PIB nominal pasó de US$ 153,8 mil millones en 2006 a "
              "US$ 357,4 mil millones en 2025; el IDH de 0,804 a 0,878 "
              "(2023); el índice de percepción de corrupción cayó de 72 a 63 "
              "y las reservas subieron de US$ 19,4 a 49,4 mil millones.",
           en="Nominal GDP went from US$153.8bn in 2006 to US$357.4bn in "
              "2025; the HDI from 0.804 to 0.878 (2023); the corruption "
              "perceptions score fell from 72 to 63 and reserves rose from "
              "US$19.4bn to US$49.4bn.",
           pt="O PIB nominal passou de US$ 153,8 bilhões em 2006 para "
              "US$ 357,4 bilhões em 2025; o IDH de 0,804 para 0,878 (2023); "
              "o índice de perceção da corrupção caiu de 72 para 63 e as "
              "reservas subiram de US$ 19,4 para 49,4 bilhões."),
         [W]),

        ("09-demography", "demography", PEOPLE, "demography/demography.csv",
         "population",
         T(es="Demografía", en="Demography", pt="Demografia"),
         T(es="Población, fecundidad, nacimientos y muertes, y los dos "
              "componentes del crecimiento, en las series de la ONU y del INE "
              "que republica el Banco Mundial.",
           en="Population, fertility, births and deaths, and the two "
              "components of growth, on the UN and INE series the World Bank "
              "republishes.",
           pt="População, fecundidade, nascimentos e mortes, e os dois "
              "componentes do crescimento, nas séries da ONU e do INE que o "
              "Banco Mundial republica."),
         T(es=f"La población creció 20% en la ventana, a 19,9 millones en "
              f"2025. La fecundidad cayó de 1,80 a 1,14 hijos por mujer y "
              f"quedó bajo el reemplazo todo el período; los nacimientos "
              f"bajaron de 14,0 a 8,7 por mil mientras las muertes subían de "
              f"5,8 (2010) a 7,7 (2021). El crecimiento natural cayó a 2,1 "
              f"por mil y la migración neta marcó 12,6 en 2018.",
           en=f"Population grew 20% over the window, to 19.9 million in "
              f"2025. Fertility fell from 1.80 to 1.14 children per woman and "
              f"stayed below replacement throughout; births fell from 14.0 to "
              f"8.7 per 1,000 while deaths rose from 5.8 (2010) to 7.7 "
              f"(2021). Natural increase fell to 2.1 per 1,000 and net "
              f"migration peaked at 12.6 in 2018.",
           pt=f"A população cresceu 20% na janela, para 19,9 milhões em 2025. "
              f"A fecundidade caiu de 1,80 para 1,14 filhos por mulher e "
              f"ficou abaixo da reposição em todo o período; os nascimentos "
              f"caíram de 14,0 para 8,7 por mil enquanto as mortes subiam de "
              f"5,8 (2010) para 7,7 (2021). O crescimento natural caiu para "
              f"2,1 por mil e a migração líquida marcou 12,6 em 2018."),
         [D, MI]),

        ("10-security", "security", PEOPLE, "security/security.csv",
         "homicide_per_100k",
         T(es="Seguridad", en="Security", pt="Segurança"),
         T(es="Homicidios, suicidios y muertes en el tránsito: las series de "
              "UNODC y la OMS que lleva el Banco Mundial, todas por 100 mil "
              "habitantes.",
           en="Homicide, suicide and road deaths: the UNODC and WHO series "
              "the World Bank carries, all per 100,000 people.",
           pt="Homicídios, suicídios e mortes no trânsito: as séries da UNODC "
              "e da OMS que o Banco Mundial leva, todas por 100 mil "
              "habitantes."),
         T(es="La tasa de homicidios tocó 2,3 en 2015 y subió a 4,8 en 2019 y "
              "6,8 en 2022, antes de 6,4 en 2023, donde termina UNODC. El "
              "suicidio bajó de 12,8 (2009) a 7,7 (2021) y las muertes en el "
              "tránsito de 18,7 (2006) a 14,9 (2019). El conteo de "
              "Carabineros y la Fiscalía es otra base y está pendiente.",
           en="The homicide rate bottomed at 2.3 in 2015 and rose to 4.8 in "
              "2019 and 6.8 in 2022, before 6.4 in 2023 where UNODC stops. "
              "Suicide fell from 12.8 (2009) to 7.7 (2021) and road deaths "
              "from 18.7 (2006) to 14.9 (2019). The Carabineros and Fiscalía "
              "count is another basis and is pending.",
           pt="A taxa de homicídios tocou 2,3 em 2015 e subiu para 4,8 em "
              "2019 e 6,8 em 2022, antes de 6,4 em 2023, onde a UNODC "
              "termina. O suicídio caiu de 12,8 (2009) para 7,7 (2021) e as "
              "mortes no trânsito de 18,7 (2006) para 14,9 (2019). A "
              "contagem dos Carabineros e da Fiscalía é outra base e está "
              "pendente."),
         [G]),

        ("11-mortality", "mortality", PEOPLE, "mortality/mortality.csv",
         "crude_death_rate_national",
         T(es="Mortalidad", en="Mortality", pt="Mortalidade"),
         T(es="La única serie oficial de esta capa: las muertes registradas "
              "por el DEIS/MINSAL, con la tasa del Banco Mundial sobre la "
              "población de la ONU al lado y nunca unida a ella.",
           en="The one official series in this layer: deaths registered by "
              "DEIS/MINSAL, with the World Bank's rate on the UN population "
              "beside it and never joined to it.",
           pt="A única série oficial desta camada: as mortes registadas pelo "
              "DEIS/MINSAL, com a taxa do Banco Mundial sobre a população da "
              "ONU ao lado e nunca unida a ela."),
         T(es="La tasa nacional fue 5,72 por mil en 2019 y 6,98 en 2021; las "
              "muertes registradas corrieron 29,9% sobre el promedio "
              "2015–2019 en 2021 y 21,5% en 2025. El cuarto panel cuenta "
              "137.267 muertes en 2021 contra una base de 105.681. Las "
              "muertes por COVID como causa quedan pendientes.",
           en="The national rate was 5.72 per 1,000 in 2019 and 6.98 in "
              "2021; registered deaths ran 29.9% above the 2015–2019 average "
              "in 2021 and 21.5% in 2025. The fourth panel counts 137,267 "
              "deaths in 2021 against a baseline of 105,681. COVID-19 as an "
              "underlying cause stays pending.",
           pt="A taxa nacional foi 5,72 por mil em 2019 e 6,98 em 2021; as "
              "mortes registadas correram 29,9% acima da média 2015–2019 em "
              "2021 e 21,5% em 2025. O quarto painel conta 137.267 mortes em "
              "2021 contra uma base de 105.681. As mortes por COVID como "
              "causa seguem pendentes."),
         [M]),

        ("12-migration", "migration", PEOPLE, "migration/migration.csv",
         "net_migration_per_1000",
         T(es="Migración", en="Migration", pt="Migração"),
         T(es="La estimación de migración neta de la ONU y el stock de "
              "nacidos en el exterior, con las personas por año en la lente. "
              "Los flujos brutos del registro están pendientes.",
           en="The UN's net-migration estimate and the foreign-born stock, "
              "with persons per year in the lens. The register's gross flows "
              "are pending.",
           pt="A estimativa de migração líquida da ONU e o estoque de "
              "nascidos no exterior, com as pessoas por ano na lente. Os "
              "fluxos brutos do registro estão pendentes."),
         T(es="La migración neta subió de 1,1 por mil en 2006 a 12,6 en 2018 "
              "y 2,6 en 2025; la proporción de nacidos en el exterior pasó "
              "de 2,1% (2010) a 7,8% (2024) en el stock quinquenal. La lente "
              "muestra 237.807 personas en 2018 y 26.042 en 2020. La "
              "inmigración y emigración brutas del registro siguen "
              "pendientes.",
           en="Net migration rose from 1.1 per 1,000 in 2006 to 12.6 in 2018 "
              "and 2.6 in 2025; the foreign-born share went from 2.1% (2010) "
              "to 7.8% (2024) on the five-year stock. The lens shows 237,807 "
              "people in 2018 and 26,042 in 2020. Gross immigration and "
              "emigration from the register remain pending.",
           pt="A migração líquida subiu de 1,1 por mil em 2006 para 12,6 em "
              "2018 e 2,6 em 2025; a proporção de nascidos no exterior "
              "passou de 2,1% (2010) para 7,8% (2024) no estoque "
              "quinquenal. A lente mostra 237.807 pessoas em 2018 e 26.042 "
              "em 2020. A imigração e a emigração brutas do registro seguem "
              "pendentes."),
         [MI, D]),
    ]

    out = []
    for (ident, topic, family, path, column, title, blurb, alt,
         sources) in specs:
        pairs = ctx.col(path, column)
        last = ctx.last(pairs)
        out.append({
            "id": ident, "topic": topic, "n": ident[:2], "family": family,
            "title": title, "blurb": blurb, "alt": alt,
            "spark": pairs,
            "stats": _stats(ctx, ident, last, partners, fx25),
            "sources": sources,
        })
    return out


def _stats(ctx, ident, last, partners, fx25):
    """Three or four readings per card, each read from a CSV."""
    T = ctx.text
    E = "macro/economy.csv"
    F = "fiscal/fiscal.csv"
    S = "spending/cofog.csv"
    TR = "trade/trade.csv"
    W = "world/world.csv"
    D = "demography/demography.csv"
    M = "mortality/mortality.csv"
    G = "security/security.csv"
    MI = "migration/migration.csv"
    P = "people/poverty.csv"
    GINI = "people/gini.csv"

    def s(label, path, column, spec, year=None, kind="flow"):
        return ctx.stat(T(**label), ctx.col(path, column), spec, year=year,
                        kind=kind)

    if ident == "01-economy":
        return [
            s({"es": "Crecimiento real", "en": "Real growth",
               "pt": "Crescimento real"}, E, "real_growth_pct", "pct_s"),
            s({"es": "Inflación", "en": "Inflation", "pt": "Inflação"},
              E, "inflation_pct", "pct"),
            s({"es": "Desempleo", "en": "Unemployment",
               "pt": "Desemprego"}, E, "unemployment_pct", "pct"),
            s({"es": "PIB por persona", "en": "GDP per person",
               "pt": "PIB por pessoa"}, W, "gdp_per_person_usd", "count",
              kind="level"),
        ]
    if ident == "02-fiscal":
        return [
            s({"es": "Ingresos", "en": "Revenue", "pt": "Receitas"},
              F, "revenue_pct_gdp", "pct_gdp"),
            s({"es": "Gastos", "en": "Spending", "pt": "Despesas"},
              F, "expenditure_pct_gdp", "pct_gdp"),
            s({"es": "Balance global", "en": "Overall balance",
               "pt": "Saldo global"}, F, "balance_pct_gdp", "pct_s"),
            s({"es": "Deuda bruta", "en": "Gross debt",
               "pt": "Dívida bruta"}, F, "debt_pct_gdp", "pct_gdp",
              kind="level"),
        ]
    if ident == "03-spending":
        return [
            s({"es": "Gasto total", "en": "Total spending",
               "pt": "Gasto total"}, S, "total", "pct_gdp"),
            s({"es": "Protección social", "en": "Social protection",
               "pt": "Proteção social"}, S, "social_protection", "pct_gdp"),
            s({"es": "Inversión de la economía", "en": "Whole-economy investment",
               "pt": "Investimento da economia"}, E, "gfcf_pct_gdp",
              "pct_gdp"),
            s({"es": "Inversión pública", "en": "Public investment",
               "pt": "Investimento público"},
              "spending/public_investment.csv", "gov_gfcf_pct_gdp",
              "pct_gdp", year=2012),
        ]
    if ident == "04-trade":
        top = max(partners, key=lambda p: p[1]) if partners else ("China", 0.0)
        return [
            s({"es": "Exportaciones", "en": "Exports", "pt": "Exportações"},
              TR, "exports_pct_gdp", "pct_gdp"),
            s({"es": "Importaciones", "en": "Imports", "pt": "Importações"},
              TR, "imports_pct_gdp", "pct_gdp"),
            s({"es": "Balance comercial", "en": "Trade balance",
               "pt": "Saldo comercial"}, TR, "trade_balance_pct_gdp",
              "pct_s"),
            ctx.stat(
                T(es=f"Mayor destino de los bienes ({top[1]:.1f}%)",
                  en=f"Top goods destination ({top[1]:.1f}%)",
                  pt=f"Maior destino dos bens ({top[1]:.1f}%)"),
                [(2024, top[1])], "pct", year=2024, kind="level"),
        ]
    if ident == "05-markets":
        return [
            s({"es": "Tasa de política", "en": "Policy rate",
               "pt": "Taxa de política"},
              "markets/policy_rate.csv", "policy_rate_pct", "pct"),
            s({"es": "Inflación", "en": "Inflation", "pt": "Inflação"},
              E, "inflation_pct", "pct"),
            ctx.stat(
                T(es="Peso frente al dólar (2006 = 100)",
                  en="Peso against the dollar (2006 = 100)",
                  pt="Peso frente ao dólar (2006 = 100)"),
                [(2025, fx25)], "index", year=2025, kind="level"),
        ]
    if ident == "06-credit":
        return [
            s({"es": "Deuda de los hogares", "en": "Household debt",
               "pt": "Dívida das famílias"},
              "credit/household_credit.csv", "hh_debt_pct_gdp_q4", "pct_gdp",
              kind="level"),
            s({"es": "Máximo, 2020", "en": "Peak, 2020", "pt": "Pico, 2020"},
              "credit/household_credit.csv", "hh_debt_pct_gdp_q4", "pct_gdp",
              year=2020, kind="level"),
        ]
    if ident == "07-people":
        return [
            s({"es": "Gini", "en": "Gini", "pt": "Gini"}, GINI, "gini",
              "dec2", kind="level"),
            s({"es": "Pobreza nacional", "en": "National poverty",
               "pt": "Pobreza nacional"}, P, "poverty_national_pct", "pct"),
            s({"es": "Pobreza US$ 8,30 al día", "en": "Poverty at US$8.30 a day",
               "pt": "Pobreza a US$ 8,30 por dia"}, P, "poverty_830_pct",
              "pct"),
        ]
    if ident == "08-world":
        return [
            s({"es": "PIB nominal", "en": "Nominal GDP", "pt": "PIB nominal"},
              W, "gdp_usd_bn", "usd_bn", kind="level"),
            s({"es": "IDH", "en": "HDI", "pt": "IDH"}, W, "hdi", "dec3",
              kind="level"),
            s({"es": "Percepción de corrupción", "en": "Corruption perceptions",
               "pt": "Perceção da corrupção"}, W, "cpi_score", "score100",
              kind="level"),
            s({"es": "Reservas", "en": "Reserves", "pt": "Reservas"}, W,
              "reserves_usd_bn", "usd_bn", kind="level"),
        ]
    if ident == "09-demography":
        return [
            s({"es": "Población", "en": "Population", "pt": "População"},
              D, "population", "pop_mn", kind="level"),
            s({"es": "Fecundidad", "en": "Fertility", "pt": "Fecundidade"},
              D, "fertility", "dec2"),
            s({"es": "Nacimientos por mil", "en": "Births per 1,000",
               "pt": "Nascimentos por mil"}, D, "birth_rate_per_1000",
              "dec2"),
            s({"es": "Migración neta por mil", "en": "Net migration per 1,000",
               "pt": "Migração líquida por mil"}, MI,
              "net_migration_per_1000", "dec2"),
        ]
    if ident == "10-security":
        return [
            s({"es": "Homicidios", "en": "Homicide", "pt": "Homicídios"},
              G, "homicide_per_100k", "per100k2", kind="level"),
            s({"es": "Suicidios", "en": "Suicide", "pt": "Suicídios"},
              G, "suicide_per_100k", "per100k2", kind="level"),
            s({"es": "Muertes en el tránsito", "en": "Road deaths",
               "pt": "Mortes no trânsito"}, G, "road_deaths_per_100k",
              "per100k2", kind="level"),
        ]
    if ident == "11-mortality":
        return [
            s({"es": "Tasa de mortalidad nacional", "en": "National death rate",
               "pt": "Taxa de mortalidade nacional"}, M,
              "crude_death_rate_national", "dec2"),
            s({"es": "Exceso sobre 2015–2019", "en": "Excess over 2015–2019",
               "pt": "Excesso sobre 2015–2019"}, M,
              "excess_deaths_pct_vs_2015_2019", "pct_s", kind="level"),
            s({"es": "Muertes registradas", "en": "Registered deaths",
               "pt": "Mortes registadas"}, M, "deaths", "count"),
        ]
    if ident == "12-migration":
        return [
            s({"es": "Migración neta por mil", "en": "Net migration per 1,000",
               "pt": "Migração líquida por mil"}, MI,
              "net_migration_per_1000", "dec2"),
            s({"es": "Nacidos en el exterior", "en": "Foreign-born share",
               "pt": "Nascidos no exterior"}, MI, "foreign_born_share_pct",
              "pct", kind="level"),
            s({"es": "Migración neta, personas", "en": "Net migration, persons",
               "pt": "Migração líquida, pessoas"}, MI, "net_migration",
              "count"),
        ]
    return []
