"""The Argentina chapters: the cards, their copy and the headline figures.

The title, blurb and alt text of each plate are the strings the standalone
site served, in all three languages. `alt` is written prose about what the
plate shows, which is why it is kept rather than generated: it is the only
thing a reader using a screen reader gets instead of the figure.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def headline(ctx) -> list[dict]:
    """The figures the page leads with.

    Computed from the CSVs rather than typed into the page, so rebuilding
    after a fetch moves the numbers instead of leaving the page quietly
    describing last year. The labels carry {year}; the page fills it from
    each figure's own year.
    """
    return [
        ctx.stat(
            {"es": 'PIB, {year}', "en": 'GDP, {year}', "pt": 'PIB, {year}'},
            ctx.col("macro/gdp.csv", "usd_bn"), "usd_bn1", kind="level"),
        ctx.stat(
            {"es": 'Inflación, {year}', "en": 'Inflation, {year}', "pt": 'Inflação, {year}'},
            ctx.col('macro/ipc.csv', 'official'), 'pct', kind='level'),
        ctx.stat(
            {"es": 'Pobreza, primer semestre {year}', "en": 'Poverty, first half {year}', "pt": 'Pobreza, primeiro semestre {year}'},
            ctx.col('social/poverty.csv', 's1'), 'pct', kind='level'),
        ctx.stat(
            {"es": 'Crédito privado, {year}', "en": 'Private credit, {year}', "pt": 'Crédito privado, {year}'},
            ctx.col('macro/credit.csv', 'private_pct_gdp'), 'pct_gdp', kind='level'),
        ctx.stat(
            {"es": 'Nacimientos, {year}', "en": 'Births, {year}', "pt": 'Nascimentos, {year}'},
            ctx.col('social/vitals.csv', 'births'), 'count', kind='level'),
        ctx.stat(
            {"es": 'Muertes por COVID-19 registradas', "en": 'COVID-19 deaths recorded', "pt": 'Mortes por COVID-19 registradas'},
            ctx.col('social/causes.csv', 'covid'), 'count', kind='total'),
    ]


def build(ctx) -> list[dict]:
    return [
        {
            "id": '01-output', "topic": "economy", "n": '01', "family": MONEY,
            "title": ctx.text(es='Veinte años de producto argentino',
                             en='Twenty years of Argentine output',
                             pt='Vinte anos de produto argentino'),
            "blurb": ctx.text(es='PIB en dólares, crecimiento real e ingreso por habitante, 2006-2026',
                             en='Dollar GDP, real growth, income per head, 2006-2026',
                             pt='PIB em dólares, crescimento real e renda por habitante, 2006-2026'),
            "alt": ctx.text(es='Cuatro paneles sobre el producto argentino entre 2006 y 2026. El PIB en dólares sube de US$233.000 millones a un máximo de US$656.000 millones en 2023 y termina cerca de US$683.000 millones, pero se mueve tanto con el tipo de cambio como con el producto. El crecimiento real alterna con fuerza: -5,9% en 2009, -9,9% en 2020, +10,4% en 2021, con un promedio cercano al 1% anual. El PIB per cápita alcanza US$14.901 en 2015 y es de US$14.730 en 2025. Un índice de producto real con base 100 en 2006 termina el período apenas por encima de donde empezó.',
                             en='Four panels on Argentine output from 2006 to 2026. Dollar GDP rises from US$233 billion to a peak of US$656 billion in 2023 and ends near US$683 billion, but moves with the exchange rate as much as with output. Real growth alternates sharply: -5.9% in 2009, -9.9% in 2020, +10.4% in 2021, averaging close to 1% a year. GDP per capita peaks at US$14,901 in 2015 and is US$14,730 in 2025. An index of real output set to 100 in 2006 ends the window only modestly above where it began.',
                             pt='Quatro painéis sobre o produto argentino entre 2006 e 2026. O PIB em dólares sobe de US$233 bilhões para um pico de US$656 bilhões em 2023 e termina perto de US$683 bilhões, mas se move tanto com o câmbio quanto com o produto. O crescimento real alterna com força: -5,9% em 2009, -9,9% em 2020, +10,4% em 2021, com média próxima de 1% ao ano. O PIB per capita chega a US$14.901 em 2015 e é de US$14.730 em 2025. Um índice de produto real com base 100 em 2006 termina o período apenas um pouco acima de onde começou.'),
        },
        {
            "id": '02-prices', "topic": "prices", "n": '02', "family": MONEY,
            "title": ctx.text(es='Los precios, el peso y los dos dólares',
                             en='Prices, the peso and the two dollars',
                             pt='Os preços, o peso e os dois dólares'),
            "blurb": ctx.text(es='Inflación, tipo de cambio y reservas, 2006-2026',
                             en='Inflation, the exchange rate and reserves, 2006-2026',
                             pt='Inflação, câmbio e reservas, 2006-2026'),
            "alt": ctx.text(es='Cuatro paneles sobre los precios en la Argentina. La inflación anual aparece en dos colores porque entre 2007 y 2016, la década de la intervención del INDEC, no existe un índice nacional utilizable: en su lugar se usa el IPC provincial de San Luis, entre 18% y 39% anual. El índice nacional vuelve en 2017, llega a 211% en 2023 y baja a 31,5% en 2025 y 21,3% en 2026. El peso pasa de unos 3 por dólar a alrededor de 1.500, en escala logarítmica y junto al dólar paralelo. La brecha entre ambos llega a casi 100% durante el segundo cepo. Las reservas del banco central oscilan entre US$56.000 millones y US$21.900 millones en 2023, y se recuperan hasta US$49.700 millones.',
                             en='Four panels on Argentine prices. Annual inflation is shown in two colours because no usable official national index exists between 2007 and 2016, the decade INDEC was intervened: the provincial San Luis index stands in, running 18% to 39% a year. The national index resumes in 2017 and peaks at 211% in 2023 before falling to 31.5% in 2025 and 21.3% in 2026. The peso goes from about 3 to the dollar to roughly 1,500, drawn on a log scale against the parallel rate. The gap between the two reaches nearly 100% during the second currency control period. Central bank reserves swing between US$56 billion and US$21.9 billion in 2023, recovering to US$49.7 billion.',
                             pt='Quatro painéis sobre os preços na Argentina. A inflação anual aparece em duas cores porque entre 2007 e 2016, a década da intervenção no INDEC, não existe índice nacional utilizável: em seu lugar entra o IPC provincial de San Luis, entre 18% e 39% ao ano. O índice nacional volta em 2017, chega a 211% em 2023 e cai para 31,5% em 2025 e 21,3% em 2026. O peso vai de cerca de 3 por dólar para aproximadamente 1.500, em escala logarítmica e ao lado do dólar paralelo. O spread entre os dois chega a quase 100% durante o segundo cepo. As reservas do banco central oscilam entre US$56 bilhões e US$21,9 bilhões em 2023, recuperando-se até US$49,7 bilhões.'),
        },
        {
            "id": '03-living', "topic": "people", "n": '03', "family": PEOPLE,
            "title": ctx.text(es='Trabajo, salarios y quién es pobre',
                             en='Work, wages and who is poor',
                             pt='Trabalho, salários e quem é pobre'),
            "blurb": ctx.text(es='Desempleo, salario mínimo, pobreza y desigualdad',
                             en='Unemployment, the minimum wage, poverty and inequality',
                             pt='Desemprego, salário mínimo, pobreza e desigualdade'),
            "alt": ctx.text(es='Cuatro paneles sobre el nivel de vida en la Argentina. El desempleo baja de 10,1% en 2006 a 6,1% en 2023 y vuelve a alrededor de 7%. El salario mínimo en dólares supera los US$600 entre 2013 y 2015 y es de US$269 en 2025, por debajo del nivel de 2006. La pobreza se dibuja con dos líneas, una por semestre, con la década intervenida en blanco: llega a 52,9% en el primer semestre de 2024, el posterior a la devaluación de diciembre de 2023, y a 38,1% en el segundo. El coeficiente de Gini se mueve en una franja estrecha entre 0,42 y 0,44.',
                             en='Four panels on Argentine living standards. Unemployment falls from 10.1% in 2006 to 6.1% in 2023, rising to about 7% after. The minimum wage in dollars peaks above US$600 around 2013-15 and is US$269 in 2025, lower than in 2006. Poverty is drawn as two lines, one per half year, with the intervened decade left blank: it reaches 52.9% in the first half of 2024 — the half after the December 2023 devaluation — and 38.1% in the second. The Gini coefficient moves in a narrow band around 0.42-0.44.',
                             pt='Quatro painéis sobre o padrão de vida na Argentina. O desemprego cai de 10,1% em 2006 para 6,1% em 2023 e volta a cerca de 7%. O salário mínimo em dólares passa de US$600 entre 2013 e 2015 e é de US$269 em 2025, abaixo do nível de 2006. A pobreza é desenhada em duas linhas, uma por semestre, com a década intervinda em branco: chega a 52,9% no primeiro semestre de 2024, o seguinte à desvalorização de dezembro de 2023, e a 38,1% no segundo. O coeficiente de Gini se move numa faixa estreita entre 0,42 e 0,44.'),
        },
        {
            "id": '04-state', "topic": "fiscal", "n": '04', "family": MONEY,
            "title": ctx.text(es='Lo que el Estado recauda y lo que gasta',
                             en='What the state takes and what it spends',
                             pt='O que o Estado arrecada e o que gasta'),
            "blurb": ctx.text(es='Resultado primario, recursos tributarios y gasto por finalidad',
                             en='Primary balance, tax revenue and spending by function',
                             pt='Resultado primário, receita tributária e gasto por finalidade'),
            "alt": ctx.text(es='Cuatro paneles sobre las cuentas públicas argentinas. El resultado primario se dibuja en tres tramos separados porque tres metodologías incompatibles cubren el período; el último llega a -6,4% del PIB en 2020 y se da vuelta a un superávit de +1,78% en 2024, el primero desde 2010. Los recursos tributarios se ubican entre 21% y 26% del PIB, con los derechos de exportación y el impuesto a las ganancias mostrados como componentes. El gasto primario por finalidad se apila y lo domina la previsión social, entre 7,6% y 9,7% del PIB; la serie consolidada termina en 2023. El último panel enfrenta la previsión social con los servicios de la deuda, que llegan a 4,35% del PIB en 2019.',
                             en='Four panels on Argentine public finances. The primary balance is drawn as three separate segments because three incompatible methodologies cover the window; the last reaches -6.4% of GDP in 2020 and turns to a surplus of +1.78% in 2024, the first since 2010. Tax revenue runs between 21% and 26% of GDP, with export duties and income tax shown as components. Primary spending by function is stacked, dominated by pensions at 7.6% to 9.7% of GDP; the consolidated series ends in 2023. The last panel sets pensions against debt service, which peaks at 4.35% of GDP in 2019.',
                             pt='Quatro painéis sobre as contas públicas argentinas. O resultado primário é desenhado em três trechos separados porque três metodologias incompatíveis cobrem o período; o último chega a -6,4% do PIB em 2020 e vira um superávit de +1,78% em 2024, o primeiro desde 2010. A receita tributária fica entre 21% e 26% do PIB, com os direitos de exportação e o imposto de renda mostrados como componentes. O gasto primário por finalidade é empilhado e dominado pela previdência, entre 7,6% e 9,7% do PIB; a série consolidada termina em 2023. O último painel confronta a previdência com o serviço da dívida, que chega a 4,35% do PIB em 2019.'),
        },
        {
            "id": '05-trade', "topic": "trade", "n": '05', "family": WORLD,
            "title": ctx.text(es='Lo que la Argentina le vende al mundo',
                             en='What Argentina sells to the world',
                             pt='O que a Argentina vende ao mundo'),
            "blurb": ctx.text(es='Exportaciones, importaciones y composición de las ventas, 2006-2026',
                             en='Exports, imports and the composition of sales, 2006-2026',
                             pt='Exportações, importações e composição das vendas, 2006-2026'),
            "alt": ctx.text(es='Cuatro paneles sobre el comercio exterior argentino. Las exportaciones y las importaciones llegan a máximos cercanos a US$88.000 y US$81.000 millones en 2022; el saldo comercial pasa de un déficit de US$8.300 millones en 2017 a un superávit de US$18.900 millones en 2024. Las exportaciones por rubro se apilan: productos primarios, manufacturas de origen agropecuario, manufacturas de origen industrial y combustibles. Las manufacturas industriales se calculan como residuo porque la fuente sirve vacía la serie propia de ese rubro. Los combustibles y la energía ganan participación en los años más recientes.',
                             en="Four panels on Argentine trade. Exports and imports both peak near US$88 billion and US$81 billion in 2022; the trade balance swings from a deficit of US$8.3 billion in 2017 to a surplus of US$18.9 billion in 2024. Exports by category are stacked: primary products, agricultural manufactures, industrial manufactures and fuel. Industrial manufactures are computed as the residual because that category's own series is served empty by the source. Fuel and energy rise as a share of exports in the most recent years.",
                             pt='Quatro painéis sobre o comércio exterior argentino. Exportações e importações atingem picos próximos de US$88 bilhões e US$81 bilhões em 2022; o saldo comercial vai de um déficit de US$8,3 bilhões em 2017 a um superávit de US$18,9 bilhões em 2024. As exportações por categoria são empilhadas: produtos primários, manufaturas de origem agropecuária, manufaturas de origem industrial e combustíveis. As manufaturas industriais são calculadas como resíduo porque a fonte serve vazia a série própria dessa categoria. Combustíveis e energia ganham participação nos anos mais recentes.'),
        },
        {
            "id": '06-credit', "topic": "credit", "n": '06', "family": MONEY,
            "title": ctx.text(es='Un sistema financiero que casi no presta',
                             en='A banking system that barely lends',
                             pt='Um sistema financeiro que quase não empresta'),
            "blurb": ctx.text(es='Crédito, deuda de las familias y el precio del dinero, 2006-2026',
                             en='Credit, household debt and what money costs, 2006-2026',
                             pt='Crédito, dívida das famílias e o preço do dinheiro, 2006-2026'),
            "alt": ctx.text(es='Cuatro paneles sobre el crédito en la Argentina. El crédito al sector privado se mantiene entre 9% y 15% del PIB a lo largo de veinte años, contra 50-70% en Chile o Brasil; las familias explican aproximadamente la mitad. El crédito hipotecario se derrumba de 1,56% del PIB en 2008 a 0,28% en 2024 y apenas se recupera a 0,74% en 2025. Las tasas reales muestran que ahorrar fue castigado todos los años entre 2017 y 2024, con una tasa real de plazo fijo de -37% en 2023, y que desde 2025 la tasa pasa a ser positiva mientras el costo real de endeudarse supera el 30%. La irregularidad de la cartera salta de 1,54% en 2024 a 5,54% en 2025, el peor registro desde 2006.',
                             en='Four panels on Argentine credit. Credit to the private sector stays between 9% and 15% of GDP across twenty years, against 50-70% in Chile or Brazil; households account for roughly half of it. Mortgage lending collapses from 1.56% of GDP in 2008 to 0.28% in 2024, recovering only to 0.74% in 2025. Real interest rates show saving punished every year from 2017 to 2024, the real deposit rate reaching -37% in 2023, then turning positive in 2025 while real borrowing costs rise above 30%. Non-performing loans jump from 1.54% in 2024 to 5.54% in 2025, the worst reading since 2006.',
                             pt='Quatro painéis sobre o crédito na Argentina. O crédito ao setor privado fica entre 9% e 15% do PIB ao longo de vinte anos, contra 50-70% no Chile ou no Brasil; as famílias respondem por cerca de metade. O crédito imobiliário despenca de 1,56% do PIB em 2008 para 0,28% em 2024 e mal se recupera para 0,74% em 2025. As taxas reais mostram que poupar foi punido todos os anos entre 2017 e 2024, com taxa real de depósito de -37% em 2023, e que a partir de 2025 ela fica positiva enquanto o custo real de tomar emprestado passa de 30%. A inadimplência da carteira salta de 1,54% em 2024 para 5,54% em 2025, o pior registro desde 2006.'),
        },
        {
            "id": '07-markets', "topic": "markets", "n": '07', "family": MONEY,
            "title": ctx.text(es='Lo que el mercado le cobró a la Argentina',
                             en='What the market charged Argentina',
                             pt='O que o mercado cobrou da Argentina'),
            "blurb": ctx.text(es='El Merval en dólares, el riesgo país y las reservas',
                             en='The Merval in dollars, country risk and reserves',
                             pt='O Merval em dólares, o risco-país e as reservas'),
            "alt": ctx.text(es='Cuatro paneles sobre los mercados argentinos. El Merval convertido a dólares se compara con el S&P 500 con base 100 en 2006 y en escala logarítmica; le gana al índice estadounidense en algunos tramos y devuelve todo en otros. El riesgo país, el spread EMBI+, ronda los 400 puntos básicos en 2017 y supera los 2.200 en 2022, hasta bajar a unos 570 en 2025. El último panel enfrenta las reservas con el riesgo país en ejes gemelos: se mueven en sentido contrario casi todo el período.',
                             en='Four panels on Argentine markets. The Merval converted to dollars is indexed against the S&P 500 at 2006 equals 100 on a log scale; it outruns the American index in some periods and gives it all back in others. Country risk, the EMBI+ spread, sits near 400 basis points in 2017 and above 2,200 in 2022, falling to about 570 by 2025. The last panel sets reserves against country risk on twin axes: they move against each other almost throughout.',
                             pt='Quatro painéis sobre os mercados argentinos. O Merval convertido em dólares é comparado ao S&P 500 com base 100 em 2006 e escala logarítmica; supera o índice americano em alguns trechos e devolve tudo em outros. O risco-país, o spread EMBI+, fica perto de 400 pontos-base em 2017 e passa de 2.200 em 2022, caindo para cerca de 570 em 2025. O último painel confronta reservas e risco-país em eixos gêmeos: movem-se em sentidos opostos quase todo o período.'),
        },
        {
            "id": '08-people', "topic": "demography", "n": '08', "family": PEOPLE,
            "title": ctx.text(es='Menos nacimientos, y un año malo de muertes',
                             en='Fewer births, and one bad year of deaths',
                             pt='Menos nascimentos, e um ano ruim de mortes'),
            "blurb": ctx.text(es='Estadísticas vitales y causas de muerte, 2006-2024',
                             en='Vital statistics and causes of death, 2006-2024',
                             pt='Estatísticas vitais e causas de morte, 2006-2024'),
            "alt": ctx.text(es='Cuatro paneles sobre la demografía argentina. Los nacimientos caen de 777.012 en 2014 a 413.135 en 2024, 46,8% menos en diez años, mientras las defunciones suben; las dos líneas convergen sin cruzarse. El crecimiento vegetativo se desploma de 451.000 por año a 36.700. Las muertes por COVID-19 son 53.222 en 2020 y 84.695 en 2021, frente a entre 15.000 y 40.000 muertes anuales por neumonía; la gripe queda fuera porque la Argentina codifica apenas entre 9 y 358 muertes por gripe al año. Las defunciones totales llegan a su máximo de 436.799 en 2021, con el COVID-19 apilado como parte del total; el registro contabiliza 164.785 muertes por COVID-19 en total, confirmadas y probables juntas.',
                             en='Four panels on Argentine demography. Births fall from 777,012 in 2014 to 413,135 in 2024, down 46.8% in ten years, while deaths rise; the two lines converge without crossing. Natural increase collapses from 451,000 a year to 36,700. COVID-19 deaths are 53,222 in 2020 and 84,695 in 2021, against 15,000 to 40,000 pneumonia deaths a year; influenza is excluded because Argentina codes only 9 to 358 influenza deaths a year. Total deaths peak at 436,799 in 2021, with COVID-19 shown as a stacked share; the registry records 164,785 COVID-19 deaths in all, confirmed and probable together.',
                             pt='Quatro painéis sobre a demografia argentina. Os nascimentos caem de 777.012 em 2014 para 413.135 em 2024, 46,8% a menos em dez anos, enquanto os óbitos sobem; as duas linhas convergem sem se cruzar. O crescimento vegetativo despenca de 451.000 por ano para 36.700. As mortes por COVID-19 são 53.222 em 2020 e 84.695 em 2021, frente a entre 15.000 e 40.000 mortes anuais por pneumonia; a gripe fica de fora porque a Argentina codifica apenas de 9 a 358 mortes por gripe ao ano. Os óbitos totais atingem o pico de 436.799 em 2021, com a COVID-19 empilhada como parcela do total; o registro contabiliza 164.785 mortes por COVID-19 no total, confirmadas e prováveis juntas.'),
        },
        {
            "id": '09-violence', "topic": "security", "n": '09', "family": PEOPLE,
            "title": ctx.text(es='Homicidio y femicidio',
                             en='Homicide and femicide',
                             pt='Homicídio e feminicídio'),
            "blurb": ctx.text(es='Dos registros, dos formas distintas de estar completo',
                             en='Two registries, two different kinds of completeness',
                             pt='Dois registros, dois tipos diferentes de completude'),
            "alt": ctx.text(es='Cuatro paneles sobre la violencia letal en la Argentina. La tasa de homicidios dolosos llega a 7,62 cada 100.000 habitantes en 2014 y baja a 3,61 en 2025, prácticamente a la mitad, y está entre las más bajas de Sudamérica; la cantidad de víctimas cae de 3.253 a 1.676. La tasa de femicidios cada 100.000 mujeres se mantiene cerca de 1,0 entre 2014 y 2023 y después baja a 0,95 en 2024 y 0,85 en 2025; una marca en 2017 advierte que el registro cambió de metodología y que los valores de uno y otro lado no son estrictamente comparables. El último panel muestra las víctimas contadas solo para los tres años en que los informes las declaran —2023, 2024 y 2025— con las víctimas vinculadas apiladas sobre las directas como personas adicionales, no como parte del mismo total.',
                             en='Four panels on lethal violence in Argentina. The intentional homicide rate peaks at 7.62 per 100,000 in 2014 and falls to 3.61 by 2025, roughly halving, among the lowest rates in South America; the victim count falls from 3,253 to 1,676. The femicide rate per 100,000 women is flat near 1.0 from 2014 to 2023, then falls to 0.95 in 2024 and 0.85 in 2025; a marker at 2017 notes that the registry changed its method there and readings either side are not strictly comparable. The final panel shows counted victims for only the three years the reports state them — 2023, 2024 and 2025 — with linked victims stacked above direct victims as further people killed rather than as part of the same count.',
                             pt='Quatro painéis sobre a violência letal na Argentina. A taxa de homicídios dolosos chega a 7,62 por 100.000 habitantes em 2014 e cai para 3,61 em 2025, praticamente pela metade, e está entre as mais baixas da América do Sul; o número de vítimas cai de 3.253 para 1.676. A taxa de feminicídios por 100.000 mulheres fica perto de 1,0 entre 2014 e 2023 e depois cai para 0,95 em 2024 e 0,85 em 2025; uma marca em 2017 avisa que o registro mudou de metodologia e que os valores de um lado e do outro não são estritamente comparáveis. O último painel mostra as vítimas contadas apenas nos três anos em que os relatórios as declaram — 2023, 2024 e 2025 — com as vítimas vinculadas empilhadas sobre as diretas como pessoas adicionais, não como parte do mesmo total.'),
        },
    ]
