"""Poland's twelve page cards, computed from the reviewed CSVs at build time.

Every figure the copy prints is read here rather than typed, so a refetch
that moves a number moves the sentence with it. Numbers are written in each
locale's own style (Polish and Portuguese take the decimal comma), because
a card that says 14.4% beside a plate that says 14,4% is the same page
telling two stories.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def _num(v, loc: str, dec: int = 1, sign: bool = False):
    text = f"{v:+,.{dec}f}" if sign else f"{v:,.{dec}f}"
    return text.replace(",", "\u00a0").replace(".", ",") \
        if loc in ("pl", "pt") else text


def _pairs(ctx, path, column):
    return ctx.col(path, column)


def _scaled(ctx, path, column, divisor):
    return [(y, v / divisor) for y, v in ctx.col(path, column)]


def _dict(ctx, path, column):
    return dict(ctx.col(path, column))


def _at(ctx, path, column, year):
    return _dict(ctx, path, column)[year]


def headline(ctx):
    T = ctx.text
    return [
        ctx.stat(T(pl="PKB", en="GDP", pt="PIB"),
                 _dict(ctx, "macro/gdp_per_person.csv", "gdp_usd_bn").items(),
                 "usd_bn"),
        ctx.stat(T(pl="PKB na osobę", en="GDP per person",
                   pt="PIB por pessoa"),
                 _pairs(ctx, "macro/gdp_per_person.csv",
                        "gdp_per_capita_usd"), "count"),
        ctx.stat(T(pl="Ludność", en="Population", pt="População"),
                 _scaled(ctx, "demography/demography.csv", "population_jan",
                         1e6),
                 "pop_mn", kind="level"),
        ctx.stat(T(pl="Inflacja", en="Inflation", pt="Inflação"),
                 _pairs(ctx, "macro/economy.csv", "cpi_pct"), "pct"),
        ctx.stat(T(pl="Bezrobocie rejestrowane", en="Registered "
                   "unemployment", pt="Desemprego registrado"),
                 _pairs(ctx, "macro/economy.csv",
                        "unemployment_registered_pct"), "pct"),
        ctx.stat(T(pl="Dług publiczny", en="Gross debt", pt="Dívida bruta"),
                 _pairs(ctx, "fiscal/fiscal.csv", "debt_pct_gdp"),
                 "pct_gdp"),
        ctx.stat(T(pl="Zadłużenie gospodarstw domowych",
                   en="Household debt", pt="Dívida das famílias"),
                 _pairs(ctx, "credit/credit.csv", "household_debt_pct_gdp"),
                 "pct_gdp", kind="level"),
    ]


def build(ctx):
    T = ctx.text
    E = "macro/economy.csv"
    F = "fiscal/fiscal.csv"
    S = "spending/spending.csv"
    TR = "trade/trade.csv"
    M = "markets/markets.csv"
    C = "credit/credit.csv"
    P = "people/people.csv"
    W = "world/world.csv"
    D = "demography/demography.csv"
    SEC = "security/security.csv"
    MO = "mortality/mortality.csv"
    MI = "migration/migration.csv"

    growth20 = _at(ctx, E, "gdp_growth_pct", 2020)
    growth09 = _at(ctx, E, "gdp_growth_pct", 2009)
    cpi22 = _at(ctx, E, "cpi_pct", 2022)
    cpi15 = _at(ctx, E, "cpi_pct", 2015)
    pct06 = _at(ctx, "macro/gdp_per_person.csv", "gdp_per_capita_usd", 2006)
    exp25 = _at(ctx, F, "expenditure_pct_gdp", 2025)
    rev25 = _at(ctx, F, "revenue_pct_gdp", 2025)
    bal25 = _at(ctx, F, "deficit_pct_gdp", 2025)
    debt25 = _at(ctx, F, "debt_pct_gdp", 2025)
    soc24 = _at(ctx, S, "social_protection_pct_gdp", 2024)
    tot24 = _at(ctx, S, "total_pct_gdp", 2024)
    exp22 = _at(ctx, TR, "exports_pct_gdp", 2022)
    imp22 = _at(ctx, TR, "imports_pct_gdp", 2022)
    de = _dict(ctx, TR, "share_germany_pct")
    ru = _dict(ctx, TR, "share_russia_pct")
    gbal22 = _at(ctx, TR, "goods_balance_mln_eur", 2022) / 1000
    gbal23 = _at(ctx, TR, "goods_balance_mln_eur", 2023) / 1000
    rate20 = _at(ctx, M, "nbp_reference_rate_year_end_pct", 2020)
    rate22 = _at(ctx, M, "nbp_reference_rate_year_end_pct", 2022)
    fx08 = _at(ctx, M, "pln_index_usd_2006", 2008)
    fx22 = _at(ctx, M, "pln_index_usd_2006", 2022)
    hd06 = _at(ctx, C, "household_debt_pct_gdp", 2006)
    hd15 = _at(ctx, C, "household_debt_pct_gdp", 2015)
    hd25 = _at(ctx, C, "household_debt_pct_gdp", 2025)
    npl14 = _at(ctx, C, "npl_ratio_pct_q4", 2014)
    npl25 = _at(ctx, C, "npl_ratio_pct_q4", 2025)
    gini14 = _at(ctx, P, "gini_eurostat", 2014)
    gini25 = _at(ctx, P, "gini_eurostat", 2025)
    pov_before = _at(ctx, P, "relative_poverty_before_transfers_pct", 2024)
    pov_after = _at(ctx, P, "relative_poverty_after_transfers_pct", 2024)
    wage06 = _at(ctx, P, "minimum_wage_pln_month", 2006)
    wage25 = _at(ctx, P, "minimum_wage_pln_month", 2025)
    gdp25 = _at(ctx, "macro/gdp_per_person.csv", "gdp_usd_bn", 2025)
    hdi23 = _at(ctx, W, "hdi", 2023)
    pop06 = _at(ctx, D, "population_jan", 2006) / 1e6
    pop26 = _at(ctx, D, "population_jan", 2026) / 1e6
    tfr10 = _at(ctx, D, "tfr", 2010)
    tfr25 = _at(ctx, D, "tfr", 2025)
    hom06 = _at(ctx, SEC, "homicides_police_per_100k", 2006)
    hom23 = _at(ctx, SEC, "homicides_police_per_100k", 2023)
    road11 = _at(ctx, SEC, "transport_deaths_per_100k", 2011)
    road24 = _at(ctx, SEC, "transport_deaths_per_100k", 2024)
    dr21 = _at(ctx, MO, "death_rate_per_1000", 2021)
    exc21 = _at(ctx, MO, "excess_deaths_pct_vs_2015_2019", 2021)
    cov21 = _at(ctx, MO, "covid_deaths_per_100k", 2021)
    imm22 = _at(ctx, MI, "immigration_per_1000", 2022)
    fb22 = _at(ctx, MI, "foreign_born_pct", 2022)
    tps22 = (_at(ctx, MI, "temporary_protection_beneficiaries", 2022)
             / _at(ctx, D, "population_jan", 2022) * 100)

    def card(ident, topic, family, title, blurb, alt, path, column, fmt,
             sources):
        pairs = _pairs(ctx, path, column)
        return {"id": ident, "topic": topic, "n": ident[:2],
                "family": family, "title": title, "blurb": blurb,
                "alt": alt, "spark": pairs,
                "stats": [ctx.stat(title, pairs, fmt)],
                "sources": sources}

    return [
        card("01-economy", "economy", MONEY,
             T(pl="Gospodarka — najszybsze dogonienie w Unii i szok cenowy",
               en="The Economy — The Union's Fastest Catch-Up, and Its Price "
                  "Shock",
               pt="A Economia — O Alcance Mais Rápido da União e o Choque "
                  "de Preços"),
             T(pl=f"Wzrost w każdym roku poza 2020, kiedy PKB spadł o "
                  f"{_num(abs(growth20), 'pl')}%, a w 2009 — gdy cała Unia "
                  f"była w recesji — rósł o {_num(growth09, 'pl')}%. "
                  f"Inflacja sięgnęła {_num(cpi22, 'pl')}% w 2022 roku, po "
                  f"deflecji {_num(cpi15, 'pl')}% w 2015.",
               en=f"Growth in every year but 2020, when GDP fell "
                  f"{_num(abs(growth20), 'en')}% — and {_num(growth09, 'en')}% "
                  f"in 2009, the year the Union was in recession. Inflation "
                  f"reached {_num(cpi22, 'en')}% in 2022, after deflation of "
                  f"{_num(cpi15, 'en')}% in 2015.",
               pt=f"Crescimento em todos os anos menos 2020, quando o PIB "
                  f"caiu {_num(abs(growth20), 'pt')}% — e "
                  f"{_num(growth09, 'pt')}% em 2009, o ano em que a União "
                  f"estava em recessão. A inflação chegou a "
                  f"{_num(cpi22, 'pt')}% em 2022, após a deflação de "
                  f"{_num(cpi15, 'pt')}% em 2015."),
             T(pl="Cztery panele o polskiej gospodarce. Wzrost jest dodatni "
                  "w każdym roku poza 2020; PKB na osobę rośnie z 9 069 USD "
                  "do 28 420 USD; inflacja szczytuje na 14,4% w 2022 roku; "
                  "bezrobocie rejestrowe spada z 14,8% do około 5%.",
               en="Four panels on the Polish economy. Growth is positive in "
                  "every year but 2020; GDP per person rises from US$9,069 "
                  "to US$28,420; inflation peaks at 14.4% in 2022; the "
                  "registered unemployment rate falls from 14.8% to about "
                  "5%.",
               pt="Quatro painéis sobre a economia polonesa. O crescimento é "
                  "positivo em todos os anos menos 2020; o PIB por pessoa "
                  "sobe de US$ 9.069 para US$ 28.420; a inflação atinge o "
                  "pico de 14,4% em 2022; o desemprego registrado cai de "
                  "14,8% para cerca de 5%."),
             E, "cpi_pct", "pct",
             [E, "macro/gdp_per_person.csv"]),

        card("02-fiscal", "fiscal", MONEY,
             T(pl="Finanse publiczne — sektor instytucji rządowych i "
                  "samorządowych, nie budżet państwa",
               en="Public Finances — General Government, Not the State "
                  "Budget",
               pt="Finanças Públicas — Governo Geral, Não o Orçamento do "
                  "Estado"),
             T(pl=f"ESA 2010, memoriałowo, sektor S13: notyfikacja EDP, "
                  f"którą Polska wysyła do Komisji. W 2025 roku wydatki "
                  f"sięgają {_num(exp25, 'pl')}% PKB przy dochodach "
                  f"{_num(rev25, 'pl')}%, a dług — {_num(debt25, 'pl')}%.",
               en=f"ESA 2010 accrual, sector S13: the EDP notification "
                  f"Poland sends to the Commission. In 2025 spending reaches "
                  f"{_num(exp25, 'en')}% of GDP against revenue of "
                  f"{_num(rev25, 'en')}%, and debt {_num(debt25, 'en')}%.",
               pt=f"ESA 2010 pelo regime de competência, setor S13: a "
                  f"notificação EDP que a Polônia envia à Comissão. Em 2025 "
                  f"as despesas chegam a {_num(exp25, 'pt')}% do PIB contra "
                  f"receitas de {_num(rev25, 'pt')}%, e a dívida a "
                  f"{_num(debt25, 'pt')}%."),
             T(pl="Cztery panele o finansach sektora rządowego. Saldo jest "
                  "ujemne w każdym roku, najniżej -7,4% PKB w 2010 i -7,2% "
                  "w 2025; dług rośnie z 47,1% do 59,6% PKB; obsługa długu "
                  "spada z 2,5% do 1,1% w 2021 roku i wraca do 2,5%.",
               en="Four panels on general-government finances. The balance "
                  "is negative in every year, at its worst -7.4% of GDP in "
                  "2010 and -7.2% in 2025; debt runs from 47.1% to 59.6% of "
                  "GDP; interest paid falls from 2.5% to 1.1% in 2021 and "
                  "back to 2.5%.",
               pt="Quatro painéis sobre as finanças do governo geral. O "
                  "saldo é negativo em todos os anos, no pior -7,4% do PIB "
                  "em 2010 e -7,2% em 2025; a dívida vai de 47,1% a 59,6% "
                  "do PIB; os juros pagos caem de 2,5% para 1,1% em 2021 e "
                  "voltam a 2,5%."),
             F, "debt_pct_gdp", "pct_gdp", [F]),

        card("03-spending", "spending", MONEY,
             T(pl="Wydatki — co robi państwo, funkcja po funkcji",
               en="Spending — What the State Does, Function by Function",
               pt="Despesas — O Que o Estado Faz, Função por Função"),
             T(pl=f"COFOG, ujęcie funkcjonalne: ochrona socjalna to "
                  f"{_num(soc24, 'pl')}% PKB, czyli ponad trzecią część z "
                  f"{_num(tot24, 'pl')}% wydatków ogółem w 2024 roku. "
                  f"Wskaźnik inwestycji spadł z 22,7% PKB w 2008 do 17,3%.",
               en=f"COFOG, by function: social protection is "
                  f"{_num(soc24, 'en')}% of GDP, more than a third of the "
                  f"{_num(tot24, 'en')}% spent in 2024. The investment rate "
                  f"fell from 22.7% of GDP in 2008 to 17.3%.",
               pt=f"COFOG, por função: a proteção social é "
                  f"{_num(soc24, 'pt')}% do PIB, mais de um terço dos "
                  f"{_num(tot24, 'pt')}% gastos em 2024. A taxa de "
                  f"investimento caiu de 22,7% do PIB em 2008 para 17,3%."),
             T(pl="Cztery panele o wydatkach publicznych. Stos warstwowy "
                  "rośnie z 44,3% do 49,4% PKB; ochrona socjalna to 18,3% "
                  "PKB; inwestycje publiczne mieszczą się między 3,3% a "
                  "6,0% PKB.",
               en="Four panels on public spending. The stacked total grows "
                  "from 44.3% to 49.4% of GDP; social protection is 18.3% of "
                  "GDP; public investment runs between 3.3% and 6.0% of GDP.",
               pt="Quatro painéis sobre as despesas públicas. O total "
                  "empilhado cresce de 44,3% para 49,4% do PIB; a proteção "
                  "social é 18,3% do PIB; o investimento público fica entre "
                  "3,3% e 6,0% do PIB."),
             S, "total_pct_gdp", "pct_gdp",
             [S, "fiscal/fiscal.csv"]),

        card("04-trade", "trade", WORLD,
             T(pl="Handel — dwa obwody, jedna otwarta gospodarka",
               en="Trade — Two Perimeters, One Open Economy",
               pt="Comércio — Dois Perímetros, Uma Economia Aberta"),
             T(pl=f"Eksport towarów i usług sięgnął {_num(exp22, 'pl')}% PKB "
                  f"w 2022 roku, import {_num(imp22, 'pl')}%. Na obwodzie "
                  f"celnym saldo towarów spadło do -{_num(abs(gbal22), 'pl')}"
                  f" mld EUR w 2022 i wróciło do +{_num(gbal23, 'pl')} mld "
                  f"w 2023 — bez usług, których tam nie ma.",
               en=f"Goods and services exports reached {_num(exp22, 'en')}% "
                  f"of GDP in 2022, imports {_num(imp22, 'en')}%. On the "
                  f"customs perimeter the goods balance fell to -EUR "
                  f"{_num(abs(gbal22), 'en')}bn in 2022 and returned to "
                  f"+EUR {_num(gbal23, 'en')}bn in 2023 — with no services "
                  f"in it.",
               pt=f"As exportações de bens e serviços chegaram a "
                  f"{_num(exp22, 'pt')}% do PIB em 2022, as importações a "
                  f"{_num(imp22, 'pt')}%. No perímetro aduaneiro o saldo de "
                  f"bens caiu para -EUR {_num(abs(gbal22), 'pt')} bi em "
                  f"2022 e voltou a +EUR {_num(gbal23, 'pt')} bi em 2023 — "
                  f"sem serviços."),
             T(pl="Cztery panele o handlu. Niemcy biorą około ćwierci "
                  "eksportu towarów, Chiny około 10%, a Rosja spada z 13,9% "
                  "w 2012 roku do 0,3% w 2025; saldo celne waha się wokół "
                  "zera, saldo rachunków narodowych jest dodatnie.",
               en="Four panels on trade. Germany takes about a quarter of "
                  "goods exports, China about 10%, and Russia falls from "
                  "13.9% in 2012 to 0.3% in 2025; the customs balance swings "
                  "around zero while the national-accounts balance stays in "
                  "surplus.",
               pt="Quatro painéis sobre o comércio. A Alemanha leva cerca de "
                  "um quarto das exportações de bens, a China cerca de 10%, "
                  "e a Rússia cai de 13,9% em 2012 para 0,3% em 2025; o "
                  "saldo aduaneiro oscila em torno de zero, o das contas "
                  "nacionais fica positivo."),
             TR, "exports_pct_gdp", "pct_gdp",
             [TR, "trade/partners.csv"]),

        card("05-markets", "markets", MONEY,
             T(pl="Rynki — stopa referencyjna, obligacja i złoty",
               en="Markets — The Reference Rate, the Bond and the Zloty",
               pt="Mercados — A Taxa de Referência, o Título e o Zlóti"),
             T(pl=f"Stopa referencyjna NBP stała na {_num(rate20, 'pl', 2)}% "
                  f"do października 2021 roku i sięgnęła "
                  f"{_num(rate22, 'pl', 2)}% na koniec 2022 — przy inflacji "
                  f"{_num(cpi22, 'pl')}%. Złoty osłabił się z indeksu "
                  f"{_num(fx08, 'pl', 0)} w 2008 do {_num(fx22, 'pl', 0)} w "
                  f"2022.",
               en=f"The NBP reference rate sat at {_num(rate20, 'en', 2)}% "
                  f"until October 2021 and reached {_num(rate22, 'en', 2)}% "
                  f"at the end of 2022 — against {_num(cpi22, 'en')}% "
                  f"inflation. The zloty index fell from "
                  f"{_num(fx08, 'en', 0)} in 2008 to {_num(fx22, 'en', 0)} "
                  f"in 2022.",
               pt=f"A taxa de referência do NBP ficou em "
                  f"{_num(rate20, 'pt', 2)}% até outubro de 2021 e chegou a "
                  f"{_num(rate22, 'pt', 2)}% no fim de 2022 — contra "
                  f"inflação de {_num(cpi22, 'pt')}%. O índice do zlóti caiu "
                  f"de {_num(fx08, 'pt', 0)} em 2008 para "
                  f"{_num(fx22, 'pt', 0)} em 2022."),
             T(pl="Cztery panele o rynkach. Stopa i inflacja na jednej "
                  "skali; rentowność dziesięcioletniej obligacji szczytuje "
                  "na 6,05% w 2022 roku; kurs złotego liczony jest tak, że "
                  "wzrost oznacza mocniejszą walutę; panel z WIG20 pozostaje "
                  "pusty z podanym powodem.",
               en="Four panels on Polish markets. The rate and inflation on "
                  "one scale; the 10-year yield peaks at 6.05% in 2022; the "
                  "currency index is drawn so that up means stronger; the "
                  "equity panel stays empty with its reason stated.",
               pt="Quatro painéis sobre os mercados. A taxa e a inflação na "
                  "mesma escala; o rendimento do título de 10 anos atinge "
                  "6,05% em 2022; o índice cambial é desenhado de modo que "
                  "subir signifique moeda mais forte; o painel do WIG20 "
                  "segue vazio com o motivo declarado."),
             M, "nbp_reference_rate_year_end_pct", "pct",
             [M, E]),

        card("06-credit", "credit", MONEY,
             T(pl="Kredyt — zadłużenie, które spadało, gdy gospodarka rosła",
               en="Credit — Household Debt That Fell While the Economy Grew",
               pt="Crédito — Dívida das Famílias que Caindo com a Economia a "
                  "Crescer"),
             T(pl=f"Zadłużenie gospodarstw domowych wzrosło z "
                  f"{_num(hd06, 'pl')}% PKB w 2006 do {_num(hd15, 'pl')}% w "
                  f"2015 i spadło do {_num(hd25, 'pl')}% w 2025 — jedyne "
                  f"dogonienie biegnące w drugą stronę. Złe kredyty: "
                  f"{_num(npl14, 'pl', 2)}% w 2014, {_num(npl25, 'pl', 2)}% "
                  f"w 2025.",
               en=f"Household debt rose from {_num(hd06, 'en')}% of GDP in "
                  f"2006 to {_num(hd15, 'en')}% in 2015 and fell to "
                  f"{_num(hd25, 'en')}% in 2025 — the one convergence running "
                  f"backwards. Non-performing loans: {_num(npl14, 'en', 2)}% "
                  f"in 2014, {_num(npl25, 'en', 2)}% in 2025.",
               pt=f"A dívida das famílias subiu de {_num(hd06, 'pt')}% do "
                  f"PIB em 2006 para {_num(hd15, 'pt')}% em 2015 e caiu para "
                  f"{_num(hd25, 'pt')}% em 2025 — a única convergência a "
                  f"correr ao contrário. Crédito malparado: "
                  f"{_num(npl14, 'pt', 2)}% em 2014, "
                  f"{_num(npl25, 'pt', 2)}% em 2025."),
             T(pl="Cztery panele o kredycie gospodarstw domowych. Dług w "
                  "procencie PKB rośnie do 35,9% w 2015 i spada do 22,1%; "
                  "panel stopy kredytowej pozostaje pusty, bo żadna oficjalna "
                  "seria nie jest dostępna maszynowo; złe kredyty spadają z "
                  "7,25% do 3,59%.",
               en="Four panels on household credit. Debt as a share of GDP "
                  "rises to 35.9% in 2015 and falls to 22.1%; the lending-rate "
                  "panel stays empty because no official series is on a "
                  "machine feed; non-performing loans fall from 7.25% to "
                  "3.59%.",
               pt="Quatro painéis sobre o crédito às famílias. A dívida em "
                  "percentagem do PIB sobe a 35,9% em 2015 e cai a 22,1%; o "
                  "painel da taxa de crédito fica vazio porque nenhuma série "
                  "oficial está disponível por via automática; o crédito "
                  "malparado cai de 7,25% para 3,59%."),
             C, "household_debt_pct_gdp", "pct_gdp", [C]),

        card("07-people", "people", PEOPLE,
             T(pl="Ludzie — nierówność spada, płaca rośnie w złotych",
               en="People — Inequality Falling, and a Wage Rising in Zloty",
               pt="Pessoas — Desigualdade em Queda e um Salário a Subir em "
                  "Zlóti"),
             T(pl=f"Wskaźnik Giniego z EU-SILC spadł z {_num(gini14, 'pl')} "
                  f"w 2014 do {_num(gini25, 'pl')} w 2025. Transfery "
                  f"obniżają krajową stopę ubóstwa z {_num(pov_before, 'pl')}"
                  f"% do {_num(pov_after, 'pl')}% w 2024 roku, a płaca "
                  f"minimalna rośnie z {_num(wage06, 'pl', 0)} do "
                  f"{_num(wage25, 'pl', 0)} zł miesięcznie.",
               en=f"The EU-SILC Gini fell from {_num(gini14, 'en')} in 2014 "
                  f"to {_num(gini25, 'en')} in 2025. Transfers cut the "
                  f"national poverty rate from {_num(pov_before, 'en')}% to "
                  f"{_num(pov_after, 'en')}% in 2024, and the minimum wage "
                  f"rises from {_num(wage06, 'en', 0)} to "
                  f"{_num(wage25, 'en', 0)} zloty a month.",
               pt=f"O Gini do EU-SILC caiu de {_num(gini14, 'pt')} em 2014 "
                  f"para {_num(gini25, 'pt')} em 2025. As transferências "
                  f"reduzem a taxa nacional de pobreza de "
                  f"{_num(pov_before, 'pt')}% para {_num(pov_after, 'pt')}% "
                  f"em 2024, e o salário mínimo sobe de "
                  f"{_num(wage06, 'pt', 0)} para {_num(wage25, 'pt', 0)} "
                  f"zlóti por mês."),
             T(pl="Cztery panele o dochodach. Gini spada, ubóstwo względne "
                  "spada, płaca minimalna w dolarach rośnie z 290 do 1 241 "
                  "USD, a w złotych rośnie w każdym roku bez wyjątku.",
               en="Four panels on incomes. The Gini falls, relative poverty "
                  "falls, the minimum wage in dollars rises from US$290 to "
                  "US$1,241, and in zloty it rises in every year without "
                  "exception.",
               pt="Quatro painéis sobre rendimentos. O Gini cai, a pobreza "
                  "relativa cai, o salário mínimo em dólares sobe de US$ 290 "
                  "para US$ 1.241 e, em zlóti, sobe em todos os anos sem "
                  "exceção."),
             P, "gini_eurostat", "dec2", [P, "macro/economy.csv"]),

        card("08-world", "world", WORLD,
             T(pl="Polska w świecie — rozmiar, rozwój, reputacja, rezerwy",
               en="Poland in the World — Size, Development, Reputation, "
                  "Reserves",
               pt="Polônia no Mundo — Tamanho, Desenvolvimento, Reputação, "
                  "Reservas"),
             T(pl=f"PKB w bieżących dolarach wzrósł z 346 mld w 2006 do "
                  f"{_num(gdp25, 'pl', 0)} mld w 2025 roku, a wskaźnik "
                  f"rozwoju społecznego osiągnął {_num(hdi23, 'pl', 3)} w "
                  f"2023. Rezerwy wzrosły sześciokrotnie.",
               en=f"GDP in current dollars rose from US$346bn in 2006 to "
                  f"US${_num(gdp25, 'en', 0)}bn in 2025, and the Human "
                  f"Development Index reached {_num(hdi23, 'en', 3)} in 2023. "
                  f"Reserves rose sixfold.",
               pt=f"O PIB em dólares correntes subiu de US$ 346 bi em 2006 "
                  f"para US$ {_num(gdp25, 'pt', 0)} bi em 2025, e o Índice "
                  f"de Desenvolvimento Humano chegou a "
                  f"{_num(hdi23, 'pt', 3)} em 2023. As reservas "
                  f"sextuplicaram."),
             T(pl="Cztery panele o miejscu Polski w świecie. PKB w dolarach "
                  "na skali logarytmicznej, HDI 0,831–0,906, wskaźnik "
                  "korupcji 58–53 (tylko metoda od 2012 roku), rezerwy od 48 "
                  "do 272 mld USD.",
               en="Four panels on Poland's place in the world. GDP in dollars "
                  "on a log scale, the HDI from 0.831 to 0.906, the "
                  "corruption score 58 to 53 (post-2012 method only), "
                  "reserves from US$48bn to US$272bn.",
               pt="Quatro painéis sobre o lugar da Polônia no mundo. O PIB em "
                  "dólares em escala logarítmica, o IDH de 0,831 a 0,906, a "
                  "pontuação de corrupção de 58 a 53 (apenas o método "
                  "posterior a 2012), as reservas de US$ 48 bi a US$ 272 bi."),
             W, "gdp_usd_bn", "usd_bn", [W]),

        card("09-demography", "demography", PEOPLE,
             T(pl="Demografia — ludność, która przestała rosnąć w 2012 roku",
               en="Demography — A Population That Peaked in 2012",
               pt="Demografia — Uma População que Parou de Crescer em 2012"),
             T(pl=f"{_num(pop06, 'pl')} mln mieszkańców 1 stycznia 2006 roku, "
                  f"{_num(pop26, 'pl')} mln 1 stycznia 2026. Dzienność spadła "
                  f"z {_num(tfr10, 'pl', 2)} do {_num(tfr25, 'pl', 2)} dziecka "
                  f"na kobietę — daleko poniżej poziomu zastępowalności.",
               en=f"{_num(pop06, 'en')}m residents on 1 January 2006, "
                  f"{_num(pop26, 'en')}m on 1 January 2026. Fertility fell "
                  f"from {_num(tfr10, 'en', 2)} to {_num(tfr25, 'en', 2)} "
                  f"children per woman — far below replacement.",
               pt=f"{_num(pop06, 'pt')} milhões de residentes em 1 de "
                  f"janeiro de 2006, {_num(pop26, 'pt')} milhões em 1 de "
                  f"janeiro de 2026. A fecundidade caiu de "
                  f"{_num(tfr10, 'pt', 2)} para {_num(tfr25, 'pt', 2)} "
                  f"filhos por mulher — muito abaixo da substituição."),
             T(pl="Cztery panele o ludności. Indeks spada ze 100 do 95,2; "
                  "krok w 2021 roku to korekta spisowa, nie zdarzenie "
                  "demograficzne; urodzenia na 1000 spadają, zgony rosną do "
                  "14,0 w 2021; panel migracji pozostaje pusty z podanym "
                  "powodem.",
               en="Four panels on population. The index falls from 100 to "
                  "95.2; the 2021 step is the census revision, not a "
                  "demographic event; births per 1,000 fall and deaths rise "
                  "to 14.0 in 2021; the migration panel stays empty with its "
                  "reason stated.",
               pt="Quatro painéis sobre a população. O índice cai de 100 para "
                  "95,2; o degrau de 2021 é a revisão do censo, não um evento "
                  "demográfico; os nascimentos por 1.000 caem e as mortes "
                  "sobem a 14,0 em 2021; o painel de migração fica vazio com "
                  "o motivo declarado."),
             D, "population_index_2006", "dec2", [D]),

        card("10-security", "security", PEOPLE,
             T(pl="Bezpieczeństwo — dwie liczby zabójstw i spadające "
                  "samobójstwa",
               en="Security — Two Homicide Counts and a Falling Suicide Rate",
               pt="Segurança — Duas Contagens de Homicídios e um Suicídio em "
                  "Queda"),
             T(pl=f"Policja odnotowała {_num(hom06, 'pl', 2)} potwierdzonych "
                  f"przestępstw zabójstwa na 100 tys. mieszkańców w 2006 roku "
                  f"i {_num(hom23, 'pl', 2)} w 2023. Ofiary śmiertelne "
                  f"w wyniku napaści to zupełnie inna liczba — i inna linia.",
               en=f"The police recorded {_num(hom06, 'en', 2)} confirmed "
                  f"homicide offences per 100,000 in 2006 and "
                  f"{_num(hom23, 'en', 2)} in 2023. Assault deaths are a "
                  f"different number entirely — and a different line.",
               pt=f"A polícia registou {_num(hom06, 'pt', 2)} crimes de "
                  f"homicídio confirmados por 100 mil habitantes em 2006 e "
                  f"{_num(hom23, 'pt', 2)} em 2023. As mortes por agressão "
                  f"são outro número — e outra linha."),
             T(pl="Cztery panele o przemocy i wypadkach. Zabójstwa według "
                  "policji spadają z 2,14 do 1,52 na 100 tys.; samobójstwa z "
                  "16,7 do 12,0; zgony w transporcie z 12,9 do 6,9; soczewka "
                  "pokazuje, że liczba policyjna jest około trzykrotnie "
                  "wyższa od liczby zgonów.",
               en="Four panels on violence and accidents. Police homicides "
                  "fall from 2.14 to 1.52 per 100,000; suicides from 16.7 to "
                  "12.0; transport deaths from 12.9 to 6.9; the lens shows "
                  "the police count running about three times the death "
                  "count.",
               pt="Quatro painéis sobre violência e acidentes. Os homicídios "
                  "registados pela polícia caem de 2,14 para 1,52 por "
                  "100.000; os suicídios de 16,7 para 12,0; as mortes no "
                  "transporte de 12,9 para 6,9; a lente mostra a contagem "
                  "policial cerca de três vezes superior à das mortes."),
             SEC, "homicides_police_per_100k", "per100k2", [SEC]),

        card("11-mortality", "mortality", PEOPLE,
             T(pl="Śmiertelność — fala pandemii i główni zabójcy",
               en="Mortality — The Pandemic Wave and the Big Killers",
               pt="Mortalidade — A Onda da Pandemia e os Grandes Algozes"),
             T(pl=f"Zgony na 1000 mieszkańców wzrosły do {_num(dr21, 'pl')} w "
                  f"2021 roku, o {_num(exc21, 'pl')}% powyżej średniej z lat "
                  f"2015–2019. COVID-19 jako przyczyna wyjściowa zabił "
                  f"{_num(cov21, 'pl', 0)} osób na 100 tys.",
               en=f"Deaths per 1,000 rose to {_num(dr21, 'en')} in 2021, "
                  f"{_num(exc21, 'en')}% above the 2015–2019 average. COVID-19 "
                  f"as an underlying cause killed {_num(cov21, 'en', 0)} "
                  f"people per 100,000.",
               pt=f"As mortes por 1.000 subiram a {_num(dr21, 'pt')} em 2021, "
                  f"{_num(exc21, 'pt')}% acima da média de 2015–2019. A "
                  f"COVID-19 como causa subjacente matou "
                  f"{_num(cov21, 'pt', 0)} pessoas por 100.000."),
             T(pl="Cztery panele o umieralności. Współczynnik zgonów rośnie z "
                  "9,7 do 14,0 w 2021 i spada do 11,2; nadwyżka zgonów "
                  "sięga 29,2%; COVID-19 to 243 na 100 tys.; choroby krążenia "
                  "i nowotwory zabijają znacznie więcej.",
               en="Four panels on mortality. The death rate rises from 9.7 to "
                  "14.0 in 2021 and falls to 11.2; excess deaths reach 29.2%; "
                  "COVID-19 is 243 per 100,000; circulatory disease and "
                  "cancer kill far more.",
               pt="Quatro painéis sobre mortalidade. A taxa de mortalidade "
                  "sobe de 9,7 para 14,0 em 2021 e cai para 11,2; o excesso "
                  "de mortes chega a 29,2%; a COVID-19 é 243 por 100.000; as "
                  "doenças circulatórias e o cancro matam muito mais."),
             MO, "deaths_all", "count", [MO, "demography/demography.csv"]),

        card("12-migration", "migration", PEOPLE,
             T(pl="Migracja — rejestr, który nie widzi uchodźców",
               en="Migration — The Register That Cannot See the Refugees",
               pt="Migração — O Registo que Não Vê os Refugiados"),
             T(pl=f"Rejestr meldunkowy odnotował {_num(imm22, 'pl')} "
                  f"przyjazdów na 1000 mieszkańców w 2022 roku — około "
                  f"dziesiątej części napływu. Cudzoziemcy urodzeni za "
                  f"granicą to {_num(fb22, 'pl')}% ludności, a osoby objęte "
                  f"ochroną czasową — {_num(tps22, 'pl')}%.",
               en=f"The residence register recorded {_num(imm22, 'en')} "
                  f"arrivals per 1,000 in 2022 — about a tenth of the inflow. "
                  f"Foreign-born residents are {_num(fb22, 'en')}% of the "
                  f"population, and people under temporary protection "
                  f"{_num(tps22, 'en')}%.",
               pt=f"O registo de residência anotou {_num(imm22, 'pt')} "
                  f"entradas por 1.000 em 2022 — cerca de um décimo do "
                  f"afluxo. Os residentes nascidos no estrangeiro são "
                  f"{_num(fb22, 'pt')}% da população e as pessoas sob "
                  f"proteção temporária {_num(tps22, 'pt')}%."),
             T(pl="Cztery panele o migracji. Rejestr widzi 7,5 przyjazdów na "
                  "1000 w 2022 roku; panel salda migracji pozostaje pusty, bo "
                  "obie oficjalne serie wychodzą poza wspólną skalę w 2020 "
                  "roku; soczewka rysuje obie serie na własnej skali.",
               en="Four panels on migration. The register sees 7.5 arrivals "
                  "per 1,000 in 2022; the net-migration panel stays empty "
                  "because both official series leave the shared scale in "
                  "2020; the lens draws both on their own scale.",
               pt="Quatro painéis sobre migração. O registo vê 7,5 entradas "
                  "por 1.000 em 2022; o painel da migração líquida fica vazio "
                  "porque ambas as séries oficiais saem da escala partilhada "
                  "em 2020; a lente desenha as duas em escala própria."),
             MI, "immigration_per_1000", "dec2",
             [MI, "demography/demography.csv"]),
    ]
