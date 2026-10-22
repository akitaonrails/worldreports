"""The South Korea chapters: the cards, their copy and their provenance.

The title, blurb and alt text of each plate are the strings the standalone
site published, in all three languages. `alt` is written prose about what
the plate shows rather than a generated summary, which is why it is kept
verbatim: it is the only thing a reader using a screen reader gets.

`sources` lists the CSVs a plate draws, so the page can link a figure to
its own provenance rather than to the whole manifest.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def headline(ctx) -> list[dict]:
    """The figures the page carries above the plates.

    The year is whatever the latest filled row turns out to be: stating a
    figure without its year is how a dashboard goes quietly stale.
    """
    return [
        ctx.stat(
            {"ko": '국내총생산', "en": 'GDP', "pt": 'PIB'},
            ctx.col('macro/gdp.csv', 'nominal_krw_tn'), 'money_tn', kind="level"),
        ctx.stat(
            {"ko": '1인당 GDP', "en": 'GDP per person', "pt": 'PIB por pessoa'},
            ctx.col('macro/gdp.csv', 'gdp_per_capita_usd'), 'count', kind="level"),
        ctx.stat(
            {"ko": '인구', "en": 'Population', "pt": 'População'},
            ctx.col('macro/gdp.csv', 'population_mn'), 'pop_mn', kind="level"),
        ctx.stat(
            {"ko": '합계출산율', "en": 'Births per woman', "pt": 'Filhos por mulher'},
            ctx.col('social/population.csv', 'tfr'), 'dec2', kind="level"),
        ctx.stat(
            {"ko": '수출', "en": 'Exports', "pt": 'Exportações'},
            ctx.col('trade/trade.csv', 'exports'), 'usd_bn', kind="level"),
        ctx.stat(
            {"ko": '국가채무(D2)', "en": 'Public debt (D2)', "pt": 'Dívida pública (D2)'},
            ctx.col('fiscal/debt.csv', 'd2'), 'pct_gdp', kind="level"),
        ctx.stat(
            {"ko": '가계부채', "en": 'Household debt', "pt": 'Dívida das famílias'},
            ctx.col('macro/household_credit.csv', 'credit_pct_gdp'), 'pct_gdp', kind="level"),
        ctx.stat(
            {"ko": '65세 이상 빈곤율', "en": 'Poverty at 65+', "pt": 'Pobreza aos 65+'},
            ctx.col('social/poverty.csv', 'elderly_65'), 'pct', kind="level"),
        ctx.stat(
            {"ko": '자살률', "en": 'Suicide rate', "pt": 'Taxa de suicídio'},
            ctx.col('social/mortality.csv', 'suicide'), 'per100k', kind="level"),
        ctx.stat(
            {"ko": '순대외금융자산', "en": 'Net foreign assets', "pt": 'Ativos externos líquidos'},
            ctx.col('macro/external.csv', 'net_usbi'), 'usd_bn', kind="level"),
    ]


def build(ctx) -> list[dict]:
    return [
        {
            "id": '01_economy', "n": '01', "family": MONEY,
            "title": ctx.text(ko='한국 경제',
                             en='The Korean Economy',
                             pt='A Economia Coreana'),
            "blurb": ctx.text(ko='명목 규모, 실질 성장, 1인당 소득, 물가 — 나머지 모든 그래프를 재는 네 가지 숫자.',
                             en='Nominal size, real growth, income per person and inflation — the four numbers every other plate is measured against.',
                             pt='Tamanho nominal, crescimento real, renda por pessoa e inflação — os quatro números contra os quais todos os outros painéis são medidos.'),
            "alt": ctx.text(ko='2006년부터 2026년까지 한국 경제를 다룬 네 개 패널. 명목 GDP는 1,046조 원에서 2,677조 원으로 늘어난다. 실질 성장률은 이 기간 유일한 역성장인 2020년을 빼면 매년 양(+)이며, 2025년에는 1% 안팎까지 둔화된다. 1인당 GDP는 약 22,700달러에서 약 36,400달러로 오르되 2009년과 2022년에는 환율 때문에 내려간다. 물가상승률은 2010년대 대부분 2% 목표 근처이거나 그 아래였다가 2022년 5%를 넘고 다시 2% 수준으로 돌아온다.',
                             en='Four panels on the Korean economy from 2006 to 2026. Nominal GDP rises from ₩1,046 trillion to ₩2,677 trillion. Real growth is positive every year except 2020, the only contraction in the window, and slows to about 1 per cent by 2025. GDP per person rises from about US$22,700 to about US$36,400, with dips in 2009 and 2022 caused by the exchange rate. Inflation sits near or below the 2 per cent target for most of the 2010s, spikes above 5 per cent in 2022, and returns to about 2 per cent.',
                             pt='Quatro painéis sobre a economia coreana de 2006 a 2026. O PIB nominal sobe de ₩1.046 trilhões para ₩2.677 trilhões. O crescimento real é positivo em todos os anos menos 2020, a única retração do período, e desacelera para cerca de 1 por cento até 2025. O PIB por pessoa sobe de cerca de US$22.700 para cerca de US$36.400, com quedas em 2009 e 2022 causadas pelo câmbio. A inflação fica perto ou abaixo da meta de 2 por cento na maior parte dos anos 2010, passa de 5 por cento em 2022 e volta para cerca de 2 por cento.'),
            "sources": ['macro/gdp.csv', 'macro/cpi.csv'],
        },
        {
            "id": '02_fiscal', "n": '02', "family": MONEY,
            "title": ctx.text(ko='조세, 재정수지, 국가채무',
                             en='Taxes, Fiscal Balance & Public Debt',
                             pt='Impostos, Resultado Fiscal e Dívida Pública'),
            "blurb": ctx.text(ko='국가가 경제의 얼마를 거두는지, 거둔 것보다 많이 쓰는지, 그 결과가 채무에 어떻게 쌓이는지.',
                             en='How much of the economy the state collects, whether it spends more than it raises, and what that does to debt.',
                             pt='Quanto da economia o Estado arrecada, se gasta mais do que arrecada, e o que isso faz com a dívida.'),
            "alt": ctx.text(ko='한국 재정을 다룬 네 개 패널. 조세부담률은 GDP의 약 17%에서 2022년 22%까지 올랐다가 다시 내려온다. 2019년까지는 총수입이 총지출보다 많았고, 2020년부터는 반대다. 일반정부 재정수지는 2019년까지 흑자, 2020년부터 적자이며 그해가 가장 깊다. 국가채무는 두 공식 정의로 함께 그린다. 중앙·지방정부 채무 D1은 GDP의 27%에서 약 49%로, 이를 포함하는 일반정부 부채 D2는 2011년 32%에서 약 50%로 오른다.',
                             en='Four panels on Korean public finances. The tax burden rises from about 17 to 22 per cent of GDP by 2022 before falling back. Revenue exceeded spending every year until 2019; since 2020 spending has been higher. The general government balance is in surplus through 2019 and in deficit from 2020, deepest in that year. Public debt is shown on both official definitions: central and local government debt, D1, rises from 27 to about 49 per cent of GDP, and general government debt, D2, which contains it, from 32 per cent in 2011 to about 50 per cent.',
                             pt='Quatro painéis sobre as contas públicas coreanas. A carga tributária sobe de cerca de 17 para 22 por cento do PIB até 2022 e depois recua. A receita superou a despesa todos os anos até 2019; desde 2020 a despesa é maior. O resultado do governo geral é superavitário até 2019 e deficitário a partir de 2020, com o pior ano sendo 2020. A dívida pública aparece nas duas definições oficiais: a dívida do governo central e local, D1, sobe de 27 para cerca de 49 por cento do PIB, e a dívida do governo geral, D2, que a contém, de 32 por cento em 2011 para cerca de 50 por cento.'),
            "sources": ['fiscal/tax_burden.csv', 'fiscal/government.csv', 'fiscal/debt.csv'],
        },
        {
            "id": '03_spending', "n": '03', "family": MONEY,
            "title": ctx.text(ko='돈이 가는 곳',
                             en='Where the Money Goes',
                             pt='Para Onde Vai o Dinheiro'),
            "blurb": ctx.text(ko='분야별 일반정부 지출과, 같은 예산이 치르는 투자.',
                             en='General government outlays by area, against the investment the same budget pays for.',
                             pt='Gastos do governo geral por área, ao lado do investimento que o mesmo orçamento paga.'),
            "alt": ctx.text(ko='정부 지출을 다룬 네 개 패널. 누적 영역 그래프는 GDP 대비 기능별 지출이 약 27%에서 약 35%로 늘어나는 모습을 보여주며, 사회보호가 4.2%에서 9.2%로 어느 기능보다 크게 늘었다. 두 번째 패널은 사회보호와 나머지 모든 기능의 합계를 비교하는데, 후자는 거의 평평하다. 경제 전체의 투자율은 내내 GDP의 30% 안팎이다. 연구개발비는 GDP의 2.6%에서 4.9%로 올라 세계 2위다.',
                             en='Four panels on Korean government spending. A stacked area shows outlays by function as a share of GDP, rising from about 27 to about 35 per cent, with social protection growing from 4.2 to 9.2 per cent — the largest single increase of any function. A second panel puts social protection against all other functions combined, which are roughly flat. Whole-economy investment stays near 30 per cent of GDP throughout. Research and development spending rises from 2.6 to 4.9 per cent of GDP, the second highest in the world.',
                             pt='Quatro painéis sobre o gasto público coreano. Uma área empilhada mostra o gasto por função como proporção do PIB, subindo de cerca de 27 para cerca de 35 por cento, com a proteção social crescendo de 4,2 para 9,2 por cento — o maior aumento de qualquer função. Um segundo painel põe a proteção social contra todas as outras funções somadas, que ficam praticamente estáveis. O investimento de toda a economia fica perto de 30 por cento do PIB o tempo todo. O gasto com pesquisa e desenvolvimento sobe de 2,6 para 4,9 por cento do PIB, o segundo maior do mundo.'),
            "sources": ['fiscal/spending_by_function.csv', 'fiscal/investment.csv', 'fiscal/rnd.csv'],
        },
        {
            "id": '04_trade', "n": '04', "family": WORLD,
            "title": ctx.text(ko='대외무역',
                             en='Foreign Trade',
                             pt='Comércio Exterior'),
            "blurb": ctx.text(ko='자기 경제만 한 규모를 수출하는 제조업 국가 — 반도체, 자동차, 선박과 대부분 에너지인 수입.',
                             en='A manufacturing exporter the size of its own economy: semiconductors, cars and ships against an import bill that is mostly energy.',
                             pt='Um exportador industrial do tamanho da própria economia: semicondutores, automóveis e navios contra uma conta de importação que é quase toda energia.'),
            "alt": ctx.text(ko='무역을 다룬 네 개 패널. 수출과 수입 모두 2006년부터 2026년 사이 대략 두 배가 되며, 2026년 1~9월 누계 수출은 8,147억 달러다. 무역수지는 2008년, 2022년, 2023년을 빼면 매년 흑자이고, 2022년 적자는 에너지 수입 때문이다. 다섯 개 기준연도의 품목별 수출을 보면 반도체는 256억 달러에서 1,428억 달러로 늘고, 통신기기는 2015년 정점 이후 무너졌으며, 선박은 2010년 고점에서 내려왔다. 수출 상대국에서는 중국 비중이 2018년 약 27% 정점에서 19% 아래로 떨어지고 미국이 그 자리를 메우며, 베트남이 일본을 앞지른다.',
                             en='Four panels on Korean trade. Exports and imports both roughly double between 2006 and 2026, with exports reaching a cumulative US$815 billion in the first nine months of 2026. The trade balance is in surplus every year except 2008, 2022 and 2023; the 2022 deficit was driven by the energy import bill. Exports by product at five snapshot years show semiconductors growing from US$26 billion to US$143 billion while telecom equipment collapses from a 2015 peak and shipbuilding falls from its 2010 high. Export destinations show China falling from a 2018 peak of about 27 per cent to under 19 per cent while the United States rises to meet it, and Vietnam overtaking Japan.',
                             pt='Quatro painéis sobre o comércio coreano. Exportações e importações praticamente dobram entre 2006 e 2026, com as exportações acumulando US$815 bilhões nos nove primeiros meses de 2026. O saldo comercial é superavitário em todos os anos menos 2008, 2022 e 2023; o déficit de 2022 veio da conta de energia. As exportações por produto em cinco anos de referência mostram os semicondutores crescendo de US$26 bilhões para US$143 bilhões enquanto os equipamentos de telecom despencam depois do pico de 2015 e a construção naval recua do auge de 2010. Entre os destinos, a China cai de um pico de cerca de 27 por cento em 2018 para menos de 19 por cento enquanto os Estados Unidos sobem para alcançá-la, e o Vietnã ultrapassa o Japão.'),
            "sources": ['trade/trade.csv', 'trade/exports_products.csv', 'trade/destinations.csv'],
        },
        {
            "id": '05_markets', "n": '05', "family": MONEY,
            "title": ctx.text(ko='돈과 시장',
                             en='Money & Markets',
                             pt='Dinheiro e Mercados'),
            "blurb": ctx.text(ko='원화로 본 한국 주식, 달러로 본 한국 주식, 그리고 S&P 500 — 환율이 이야기의 절반이다.',
                             en='Korean equities in won, in dollars, and next to the S&P 500: the currency is half of the story.',
                             pt='As ações coreanas em wons, em dólares, e ao lado do S&P 500: o câmbio é metade da história.'),
            "alt": ctx.text(ko='한국 금융시장을 다룬 네 개 패널. 2005년에 코스피에 넣은 100원은 2026년에 약 400원이 되고, 달러로 본 S&P 500은 약 620원에 해당한다. S&P 500을 원화로 환산하면 격차는 더 벌어지는데, 같은 기간 원화 가치가 달러 대비 떨어졌기 때문이다. 원달러 환율은 2006년 말 약 930원에서 2024년 말 1,470원 위까지 올랐다. 기준금리와 물가는 함께 움직이며, 물가상승률이 5%를 넘자 기준금리는 2020년 0.5%에서 2023년 3.5%까지 올랐다.',
                             en='Four panels on Korean markets. ₩100 invested in the KOSPI in 2005 is worth about ₩400 by 2026, against about ₩620 for the S&P 500 in dollars. Converting the S&P into won widens the gap further, because the won lost value against the dollar over the same period. The won weakened from about 930 per dollar at the end of 2006 to a peak above 1,470 at the end of 2024. The policy rate and inflation move together, with the rate rising from 0.5 per cent in 2020 to 3.5 per cent in 2023 as inflation peaked above 5 per cent.',
                             pt='Quatro painéis sobre os mercados coreanos. ₩100 investidos no KOSPI em 2005 valem cerca de ₩400 em 2026, contra cerca de ₩620 do S&P 500 em dólares. Converter o S&P para wons amplia ainda mais a diferença, porque o won perdeu valor frente ao dólar no mesmo período. O won enfraqueceu de cerca de 930 por dólar no fim de 2006 para um pico acima de 1.470 no fim de 2024. A taxa básica e a inflação andam juntas: a taxa subiu de 0,5 por cento em 2020 para 3,5 por cento em 2023, quando a inflação passou de 5 por cento.'),
            "sources": ['markets/kospi.csv', 'markets/sp500.csv', 'macro/won.csv', 'macro/base_rate.csv'],
        },
        {
            "id": '06_people', "n": '06', "family": PEOPLE,
            "title": ctx.text(ko='사람',
                             en='People',
                             pt='Pessoas'),
            "blurb": ctx.text(ko='부유한 나라의 가난한 노년 — 높은 인간개발지수와 낮은 실업률 옆의 OECD 최악 노인빈곤.',
                             en="A rich country with a poor old age: high human development and low unemployment next to the OECD's worst elderly poverty.",
                             pt='Um país rico com uma velhice pobre: desenvolvimento humano alto e desemprego baixo ao lado da pior pobreza na terceira idade da OCDE.'),
            "alt": ctx.text(ko='생활 수준을 다룬 여섯 개 패널. 인간개발지수는 0.871에서 0.937로 올라 매우 높은 수준 기준인 0.900을 크게 넘는다. 지니계수는 서로 다른 두 조사에서 나온 값이라 이어 붙이지 않고 따로 그린다. 현행 조사 기준으로는 2011년 0.387에서 2024년 0.325로 낮아졌다. 실업률은 내내 2.8%에서 4% 사이다. 최저임금은 시간당 3,100원에서 10,320원으로, 실질 기준으로도 대략 두 배가 됐다. 전체 인구의 상대적 빈곤율은 18.5%에서 약 15%로 내려간다. 65세 이상 빈곤율은 처분가능소득 기준으로 46.5%에서 35.9%로 낮아졌고, 같은 해 시장소득 기준은 54.9%다. 두 선 사이의 간격이 이전소득 제도의 크기다.',
                             en='Six panels on living standards in Korea. The Human Development Index rises from 0.871 to 0.937, well above the 0.900 very-high threshold. Two Gini coefficients are drawn separately because they come from two different surveys and must not be joined; the current survey shows inequality falling from 0.387 in 2011 to 0.325 in 2024. Unemployment stays between 2.8 and 4 per cent throughout. The minimum wage rises from ₩3,100 to ₩10,320 an hour, roughly doubling in real terms. Relative poverty for the whole population falls from 18.5 to about 15 per cent. Poverty among people aged 65 and over falls from 46.5 to 35.9 per cent after transfers, against 54.9 per cent before them — the gap between the two lines is the size of the transfer system.',
                             pt='Seis painéis sobre o padrão de vida na Coreia. O Índice de Desenvolvimento Humano sobe de 0,871 para 0,937, bem acima do limiar de 0,900. Dois coeficientes de Gini são desenhados separadamente porque vêm de duas pesquisas diferentes e não podem ser unidos; na pesquisa atual a desigualdade cai de 0,387 em 2011 para 0,325 em 2024. O desemprego fica entre 2,8 e 4 por cento o tempo todo. O salário mínimo sobe de ₩3.100 para ₩10.320 por hora, aproximadamente dobrando em termos reais. A pobreza relativa de toda a população cai de 18,5 para cerca de 15 por cento. A pobreza entre pessoas de 65 anos ou mais cai de 46,5 para 35,9 por cento depois das transferências, contra 54,9 por cento antes delas — a distância entre as duas linhas é o tamanho do sistema de transferências.'),
            "sources": ['social/hdi.csv', 'social/gini.csv', 'macro/unemployment.csv', 'macro/minimum_wage.csv', 'social/poverty.csv'],
        },
        {
            "id": '07_world', "n": '07', "family": WORLD,
            "title": ctx.text(ko='세계 속의 한국',
                             en='Korea in the World',
                             pt='A Coreia no Mundo'),
            "blurb": ctx.text(ko='경제의 얼마가 무역에 걸려 있는지, 세계가 한국의 청렴도를 어떻게 보는지, 이 나라가 해외에 무엇을 갖고 있는지.',
                             en='How much of the economy rides on trade, how the outside world scores Korea for integrity, and what the country owns abroad.',
                             pt='Quanto da economia depende do comércio, como o mundo avalia a integridade da Coreia, e o que o país possui no exterior.'),
            "alt": ctx.text(ko='한국의 국제적 위치를 다룬 네 개 패널. 무역은 이 기간 GDP의 65%에서 102% 사이로, 세계 평균보다 훨씬 높다. 부패인식지수 점수는 2012년 56점에서 2024년 64점으로 정점을 찍고 2025년 63점이다. 외환보유액은 2,390억 달러에서 약 4,410억 달러로 늘었다. 국제투자대조표는 2014년에 0을 지난다. 한국은 순대외채무국에서 벗어나 2024년 약 1조 864억 달러의 순대외금융자산을 갖게 된다.',
                             en="Four panels placing Korea internationally. Trade is worth between 65 and 102 per cent of GDP across the window, far above the world average. Korea's Corruption Perceptions Index score rises from 56 in 2012 to a peak of 64 in 2024 and 63 in 2025. Foreign exchange reserves grow from US$239 billion to about US$441 billion. The international investment position crosses zero in 2014: Korea stops being a net debtor to the rest of the world and reaches net foreign assets of about US$1,086 billion in 2024.",
                             pt='Quatro painéis situando a Coreia internacionalmente. O comércio equivale a entre 65 e 102 por cento do PIB ao longo do período, bem acima da média mundial. A pontuação da Coreia no Índice de Percepção da Corrupção sobe de 56 em 2012 para um pico de 64 em 2024 e 63 em 2025. As reservas internacionais crescem de US$239 bilhões para cerca de US$441 bilhões. A posição de investimento internacional cruza o zero em 2014: a Coreia deixa de ser devedora líquida do resto do mundo e chega a ativos externos líquidos de cerca de US$1.086 bilhões em 2024.'),
            "sources": ['intl/openness.csv', 'intl/cpi.csv', 'macro/reserves.csv', 'macro/external.csv'],
        },
        {
            "id": '08_demography', "n": '08', "family": PEOPLE,
            "title": ctx.text(ko='인구 전환',
                             en="Korea's Demographic Transition",
                             pt='A Transição Demográfica Coreana'),
            "blurb": ctx.text(ko='평시에 기록된 가장 낮은 출산율, 그리고 2020년에 정점을 지난 인구.',
                             en='The lowest fertility rate ever recorded in peacetime, and a population that peaked in 2020.',
                             pt='A menor taxa de fecundidade já registrada em tempos de paz, e uma população que atingiu o pico em 2020.'),
            "alt": ctx.text(ko='인구를 다룬 네 개 패널. 인구는 2020년 5,184만 명으로 정점을 찍었고, 2024년 공식 장래인구추계는 2072년 3,622만 명까지 줄어든다고 본다. 합계출산율은 2000년 1.48에서 2023년 0.721까지 떨어졌다가 0.799로 조금 올랐는데, 인구 유지 수준 2.1에 한참 못 미친다. 출생아 수와 사망자 수는 2020년에 교차했고 이후 격차가 매년 벌어졌다. 65세 이상 인구 비중은 2025년 20%를 넘어 초고령사회가 되었고, 약 48%까지 오를 것으로 전망된다.',
                             en='Four panels on Korean demography. The population peaked at 51.8 million in 2020 and the official 2024 projection has it falling to 36.2 million by 2072. The total fertility rate falls from 1.48 in 2000 to a trough of 0.721 in 2023, recovering slightly to 0.799 — far below the replacement level of 2.1. Births and deaths cross in 2020 and the gap has widened every year since. The share of the population aged 65 and over passes 20 per cent in 2025, making Korea a super-aged society, and is projected to reach about 48 per cent.',
                             pt='Quatro painéis sobre a demografia coreana. A população atingiu o pico de 51,8 milhões em 2020 e a projeção oficial de 2024 a leva a 36,2 milhões até 2072. A taxa de fecundidade total cai de 1,48 em 2000 para um mínimo de 0,721 em 2023, recuperando-se levemente para 0,799 — muito abaixo do nível de reposição de 2,1. Nascimentos e óbitos se cruzam em 2020 e a diferença aumentou todos os anos desde então. A parcela da população com 65 anos ou mais passa de 20 por cento em 2025, tornando a Coreia uma sociedade superenvelhecida, e deve chegar a cerca de 48 por cento.'),
            "sources": ['social/population.csv', 'social/vital.csv'],
        },
        {
            "id": '09_safety', "n": '09', "family": PEOPLE,
            "title": ctx.text(ko='건강과 안전',
                             en='Health & Safety',
                             pt='Saúde e Segurança'),
            "blurb": ctx.text(ko='타인으로부터는 세계에서 가장 안전하고, 자기 자신으로부터는 OECD에서 가장 위험한 나라.',
                             en='One of the safest countries in the world from other people, and the most dangerous in the OECD from oneself.',
                             pt='Um dos países mais seguros do mundo em relação aos outros, e o mais perigoso da OCDE em relação a si mesmo.'),
            "alt": ctx.text(ko='사망 원인을 다룬 네 개 패널. 자살과 살인을 같은 축에 그린다. 자살률은 2011년 10만 명당 31.7명으로 정점을 찍었고 2025년 27.8명으로 OECD 최고인 반면, 살인은 약 0.5명으로 그래프 바닥을 벗어나지 않는다. 사망신고서 기준 코로나19 사망률은 2022년 10만 명당 61명으로 정점을 찍고 2025년 2.2명까지 내려왔으며, 폐렴은 팬데믹 이전부터 이미 오르고 있다가 60.8명에 이른다. 전염병이 아니라 인구 고령화 때문이다. 도로교통사고 사망률은 10만 명당 13.1명에서 4.9명으로 줄었다. 산업재해 사망은 비율과 숫자가 엇갈린다. 근로자 1만 명당 사고사망만인율은 절반 넘게 줄었지만 사망자 수는 줄지 않았는데, 근로자가 늘었고 집계에 업무상 질병이 포함되기 때문이다.',
                             en='Four panels on causes of death in Korea. Suicide and homicide are drawn on the same axis: suicide peaks at 31.7 per 100,000 in 2011 and stands at 27.8 in 2025, the highest in the OECD, while homicide never leaves the floor of the chart at about 0.5. COVID-19 deaths, counted from death certificates, peak at 61 per 100,000 in 2022 and fall to 2.2 by 2025, against pneumonia which was already climbing before the pandemic and reaches 60.8 — an ageing population rather than an epidemic. Road deaths fall from 13.1 to 4.9 per 100,000. Workplace deaths show a rate and a count disagreeing: the fatal accident rate per 10,000 workers more than halves while the number of deaths does not fall, because the workforce grew and because the count now includes occupational disease.',
                             pt='Quatro painéis sobre causas de morte na Coreia. Suicídio e homicídio aparecem no mesmo eixo: o suicídio atinge 31,7 por 100 mil em 2011 e está em 27,8 em 2025, o mais alto da OCDE, enquanto o homicídio nunca sai do piso do gráfico, em cerca de 0,5. As mortes por COVID-19, contadas a partir de atestados de óbito, atingem 61 por 100 mil em 2022 e caem para 2,2 até 2025, contra a pneumonia, que já subia antes da pandemia e chega a 60,8 — envelhecimento da população, não epidemia. As mortes no trânsito caem de 13,1 para 4,9 por 100 mil. As mortes no trabalho mostram uma taxa e um número discordando: a taxa de acidentes fatais por 10 mil trabalhadores cai mais da metade enquanto o número de mortes não cai, porque a força de trabalho cresceu e porque a contagem agora inclui doença ocupacional.'),
            "sources": ['social/mortality.csv', 'social/covid.csv', 'social/homicide.csv', 'social/road.csv', 'social/workplace.csv'],
        },
        {
            "id": '10_credit', "n": '10', "family": MONEY,
            "title": ctx.text(ko='가계부채와 신용의 가격',
                             en='Household Debt & the Price of Credit',
                             pt='Dívida das Famílias e o Preço do Crédito'),
            "blurb": ctx.text(ko='한국의 가계는 이 나라가 1년간 생산하는 것과 맞먹는 빚을 지고 있다. 그 대가로 무엇을 지불하고, 얼마가 연체되는가.',
                             en='Korean households owe almost as much as the whole economy produces in a year. What they pay for it, and how much of it goes unpaid.',
                             pt='As famílias coreanas devem quase tanto quanto a economia inteira produz em um ano. Quanto pagam por isso, e quanto fica em atraso.'),
            "alt": ctx.text(ko='가계신용을 다룬 네 개 패널. 잔액은 607조 원에서 1,979조 원으로 늘었고, 판매신용이 아니라 거의 전부가 대출이다. GDP 대비로는 2021년 84%로 정점을 찍고 약 74%까지 내려왔다. 은행 신규취급 대출금리는 2010년대 내내 내려가 2020년 무렵 바닥을 친 뒤 2년 만에 대략 두 배가 됐고, 일반신용대출은 6.7%에 이르렀다. 연체율은 내내 낮다. 가계 연체율은 2012년 1.1% 근처에서 정점을 찍고 0.2% 아래까지 떨어졌다가 2022년부터 다시 오른다.',
                             en='Four panels on Korean household credit. The stock rises from ₩607 trillion to ₩1,979 trillion, almost entirely in loans rather than card and instalment credit. As a share of GDP it peaks at 84 per cent in 2021 and falls back to about 74 per cent. New bank lending rates fall through the 2010s to a trough around 2020 and then roughly double in two years, with unsecured loans reaching 6.7 per cent. Loan delinquency is low throughout: household arrears peak near 1.1 per cent in 2012, fall below 0.2 per cent, and rise again from 2022.',
                             pt='Quatro painéis sobre o crédito às famílias na Coreia. O estoque sobe de ₩607 trilhões para ₩1.979 trilhões, quase todo em empréstimos e não em crédito de cartão e parcelado. Como proporção do PIB, atinge o pico de 84 por cento em 2021 e recua para cerca de 74 por cento. As taxas de novos empréstimos bancários caem ao longo dos anos 2010 até um mínimo por volta de 2020 e então praticamente dobram em dois anos, com o crédito sem garantia chegando a 6,7 por cento. A inadimplência é baixa o tempo todo: o atraso das famílias atinge cerca de 1,1 por cento em 2012, cai abaixo de 0,2 por cento, e volta a subir a partir de 2022.'),
            "sources": ['macro/household_credit.csv', 'macro/credit_terms.csv'],
        },
    ]
