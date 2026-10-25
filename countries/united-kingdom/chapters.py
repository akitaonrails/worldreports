"""The United Kingdom chapters: the cards, their copy and their headline figures.

Editorial copy lives here. Every number is read from this country's CSVs at
build time by the context, so a figure on a card and the same figure on its
plate cannot disagree.

Twelve chapters, all born on the shared spine. `kind` says whether a figure
is current: 'flow' for an annual total or average, which is only comparable
once the year is complete; 'level' for a stock or a rate read at a moment.
The fiscal and household-survey series run on the April-March financial year
and are keyed fiscal_year — the starting year, labelled 2024 for 2024-25.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def headline(ctx) -> list[dict]:
    """The figures the page leads with, above the plates."""
    return [
        ctx.stat({"en": "GDP", "pt": "PIB"},
                 [(y, v / 1e9) for y, v in
                  ctx.col("international/gdp_usd.csv", "gdp_usd")], "usd_bn"),
        ctx.stat({"en": "GDP per person, US$", "pt": "PIB por pessoa, US$"},
                 ctx.col("international/gdp_pc.csv", "gdp_per_person_usd"),
                 "count"),
        ctx.stat({"en": "Population", "pt": "População"},
                 [(y, v / 1e6) for y, v in
                  ctx.col("demography/population.csv", "population_uk")],
                 "pop_mn", kind="level"),
        ctx.stat({"en": "Bank Rate, year-end", "pt": "Bank Rate, fim de ano"},
                 ctx.col("markets/bank_rate.csv", "bank_rate_eoy"), "pct2",
                 kind="level"),
        ctx.stat({"en": "Net migration, YE December",
                  "pt": "Migração líquida, fim de dez."},
                 _net_migration(ctx), "count"),
        ctx.stat({"en": "Unemployment", "pt": "Desemprego"},
                 ctx.col("macro/labour.csv", "unemployment_rate_pct"),
                 "pct", kind="level"),
        ctx.stat({"en": "Asylum applications",
                  "pt": "Pedidos de asilo"},
                 ctx.col("migration/asylum.csv", "applications_persons"),
                 "count"),
    ]


def build(ctx) -> list[dict]:
    chapters = [
        {
            "id": "01-economy", "topic": "economy", "n": "01",
            "family": MONEY,
            "title": ctx.text(en="The Economy", pt="A Economia"),
            "blurb": ctx.text(
                en="Real GDP broke only twice in twenty years — 2009 and "
                   "2020 — while the US-dollar readings bent with sterling: "
                   "the 2016 and 2022 falls in GDP per person are exchange "
                   "rates, not output.",
                pt="O PIB real só quebrou duas vezes em vinte anos — 2009 e "
                   "2020 — enquanto as leituras em dólares se curvavam com a "
                   "libra: as quedas de 2016 e 2022 no PIB por pessoa são "
                   "câmbio, não produção."),
            "spark": _growth(ctx),
            "stats": [
                ctx.stat({"en": "GDP per person, US$",
                          "pt": "PIB por pessoa, US$"},
                         ctx.col("international/gdp_pc.csv",
                                 "gdp_per_person_usd"), "count"),
                ctx.stat({"en": "Real growth", "pt": "Crescimento real"},
                         _growth(ctx), "pct_s"),
                ctx.stat({"en": "Unemployment", "pt": "Desemprego"},
                         ctx.col("macro/labour.csv",
                                 "unemployment_rate_pct"), "pct",
                         kind="level"),
            ],
        },
        {
            "id": "02-fiscal", "topic": "fiscal", "n": "02", "family": MONEY,
            "title": ctx.text(en="Public Finances",
                              pt="As Contas Públicas"),
            "blurb": ctx.text(
                en="Borrowing ex banks reached −£311bn on the financial year "
                   "of the pandemic; the debt the UK argues about, PSND, ran "
                   "past 90% of GDP from 2021 and the IMF's gross reading "
                   "runs higher again.",
                pt="O endividamento líquido dos setores públicos chegou a "
                   "−£311 bilhões no ano fiscal da pandemia; a dívida de que "
                   "o Reino Unido discute, a PSND, passou de 90% do PIB em "
                   "2021, e a leitura bruta do FMI é ainda maior."),
            "spark": ctx.col("international/fiscal_imf.csv",
                             "overall_balance_pct_gdp"),
            "stats": [
                ctx.stat({"en": "Borrowing, calendar year",
                          "pt": "Endividamento, ano civil"},
                         [(y, v / 1000) for y, v in
                          ctx.col("fiscal/psnb.csv",
                                  "psnb_ex_calendar_gbp_mn")], "money_bn"),
                ctx.stat({"en": "Net debt (ONS, ex banks)",
                          "pt": "Dívida líquida (ONS, sem bancos)"},
                         ctx.col("fiscal/psnd.csv", "psnd_ex_dec_pct_gdp"),
                         "pct_gdp", kind="level"),
                ctx.stat({"en": "Gross debt (IMF)",
                          "pt": "Dívida bruta (FMI)"},
                         ctx.col("international/fiscal_imf.csv",
                                 "gross_debt_pct_gdp"), "pct_gdp",
                         kind="level"),
            ],
        },
        {
            "id": "03-spending", "topic": "spending", "n": "03",
            "family": MONEY,
            "title": ctx.text(en="Where the Money Goes",
                              pt="Para Onde Vai o Dinheiro"),
            "blurb": ctx.text(
                en="Social protection is the biggest single function and "
                   "still growing; the whole economy's investment rate near "
                   "19% of GDP is low by G7 standards, and no British series "
                   "publishes public investment.",
                pt="A proteção social é a maior função individual e segue "
                   "crescendo; a taxa de investimento da economia, perto de "
                   "19% do PIB, é baixa para o padrão do G7, e nenhuma série "
                   "britânica publica o investimento público."),
            "spark": ctx.col("fiscal/spending_by_function.csv",
                             "social_protection_bn", key="fiscal_year"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Social protection",
                          "pt": "Proteção social"},
                         ctx.col("fiscal/spending_by_function.csv",
                                 "social_protection_bn", key="fiscal_year"),
                         "money_bn"),
                ctx.stat({"en": "Health", "pt": "Saúde"},
                         ctx.col("fiscal/spending_by_function.csv",
                                 "health_bn", key="fiscal_year"),
                         "money_bn"),
                ctx.stat({"en": "Investment rate (GFCF)",
                          "pt": "Taxa de investimento (FBCF)"},
                         ctx.col("international/gfcf.csv", "gfcf_pct_gdp"),
                         "pct_gdp", kind="level"),
            ],
        },
        {
            "id": "04-trade", "topic": "trade", "n": "04", "family": WORLD,
            "title": ctx.text(en="Trade", pt="Comércio"),
            "blurb": ctx.text(
                en="A deficit in goods and services in every year on this "
                   "page; the United States is the largest goods customer, "
                   "and 2021 changes how goods are counted — Intrastat ends, "
                   "customs declarations begin.",
                pt="Déficit em bens e serviços em todos os anos desta página; "
                   "os Estados Unidos são o maior cliente de bens, e 2021 "
                   "muda a contagem: o Intrastat termina e começam as "
                   "declarações aduaneiras."),
            "spark": ctx.col("trade/totals.csv", "current_account_gbp_mn"),
            "stats": [
                ctx.stat({"en": "Exports, goods & services",
                          "pt": "Exportações, bens e serviços"},
                         [(y, v / 1000) for y, v in
                          ctx.col("trade/totals.csv", "exports_gs_gbp_mn")],
                         "money_bn"),
                ctx.stat({"en": "United States, goods exports",
                          "pt": "Estados Unidos, exportações de bens"},
                         _partner_share(ctx, "United States"), "pct",
                         kind="level"),
                ctx.stat({"en": "Current account",
                          "pt": "Conta corrente"},
                         [(y, v / 1000) for y, v in
                          ctx.col("trade/totals.csv",
                                  "current_account_gbp_mn")], "money_bn"),
            ],
        },
        {
            "id": "05-markets", "topic": "markets", "n": "05",
            "family": MONEY,
            "title": ctx.text(en="Money & Markets",
                              pt="Dinheiro e Mercados"),
            "blurb": ctx.text(
                en="Bank Rate went from 0.1% to 5.25% and back to 3.75% in "
                   "five years; sterling fell on the referendum vote and "
                   "never went back, and the FTSE 100 in dollars shows what "
                   "a weak pound did for London's foreign earnings.",
                pt="O Bank Rate foi de 0,1% a 5,25% e voltou a 3,75% em cinco "
                   "anos; a libra caiu no referendo e nunca voltou, e o FTSE "
                   "100 em dólares mostra o que uma libra fraca fez pelos "
                   "ganhos estrangeiros de Londres."),
            "spark": ctx.col("markets/bank_rate.csv", "bank_rate_eoy"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Bank Rate, year-end",
                          "pt": "Bank Rate, fim de ano"},
                         ctx.col("markets/bank_rate.csv", "bank_rate_eoy"),
                         "pct2", kind="level"),
                ctx.stat({"en": "10-year gilt", "pt": "Gilt de 10 anos"},
                         ctx.col("markets/gilt_yield.csv", "gilt_10y_eoy"),
                         "pct2", kind="level"),
                ctx.stat({"en": "US$ per £, year-end",
                          "pt": "US$ por £, fim de ano"},
                         ctx.col("markets/sterling.csv", "usd_per_gbp_eoy"),
                         "dec3", kind="level"),
            ],
        },
        {
            "id": "06-credit", "topic": "credit", "n": "06", "family": MONEY,
            "title": ctx.text(en="Household Credit",
                              pt="Crédito às Famílias"),
            "blurb": ctx.text(
                en="Household credit peaked near 100% of GDP around the "
                   "financial crisis and now stands at 74%; because British "
                   "mortgages are mostly fixed, the 2022 hikes reached "
                   "payments only as contracts renewed.",
                pt="O crédito às famílias atingiu o pico perto de 100% do PIB "
                   "na crise financeira e hoje está em 74%; como os "
                   "financiamentos britânicos são em maioria prefixados, as "
                   "altas de 2022 só chegaram às parcelas na renovação."),
            "spark": ctx.col("credit/household_credit.csv",
                             "household_credit_pct_gdp_q4"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Household credit",
                          "pt": "Crédito às famílias"},
                         ctx.col("credit/household_credit.csv",
                                 "household_credit_pct_gdp_q4"), "pct_gdp",
                         kind="level"),
                ctx.stat({"en": "Debt to income (ONS)",
                          "pt": "Dívida e renda (ONS)"},
                         ctx.col("credit/household_debt.csv",
                                 "hh_debt_to_income_pct_q4"), "pct_gdp",
                         kind="level"),
                ctx.stat({"en": "Two-year mortgage quote",
                          "pt": "Juro do financiamento de 2 anos"},
                         ctx.col("credit/mortgage_rate.csv",
                                 "mortgage_2y_60ltv_avg"), "pct2"),
            ],
        },
        {
            "id": "07-people", "topic": "people", "n": "07", "family": PEOPLE,
            "title": ctx.text(en="People", pt="Pessoas"),
            "blurb": ctx.text(
                en="The Gini ran down across the window on the ONS series, "
                   "from 37 points in 2006-07 to 33 in 2024-25; housing "
                   "costs move the relative-low-income rate by about four "
                   "points, and the statutory wage floor has more than "
                   "doubled in cash terms since 2007.",
                pt="O Gini caiu ao longo da janela na série do ONS, de 37 "
                   "pontos em 2006-07 para 33 em 2024-25; os custos de "
                   "moradia movem a taxa de baixa renda em cerca de quatro "
                   "pontos, e o piso legal de salário mais que dobrou em "
                   "termos monetários desde 2007."),
            "spark": ctx.col("social/gini.csv", "gini_pct",
                             key="fiscal_year"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Gini, disposable income",
                          "pt": "Gini, renda disponível"},
                         ctx.col("social/gini.csv", "gini_pct",
                                 key="fiscal_year"), "pct", kind="level"),
                ctx.stat({"en": "Low income, after housing",
                          "pt": "Baixa renda, após moradia"},
                         ctx.col("social/poverty.csv",
                                 "relative_low_income_ahc_pct",
                                 key="fiscal_year"), "pct", kind="level"),
                ctx.stat({"en": "Minimum wage, US$/month",
                          "pt": "Salário mínimo, US$/mês"},
                         ctx.col("social/minimum_wage.csv",
                                 "adult_rate_usd_month"), "count"),
            ],
        },
        {
            "id": "08-world", "topic": "world", "n": "08", "family": WORLD,
            "title": ctx.text(en="In the World",
                              pt="No Mundo"),
            "blurb": ctx.text(
                en="A US$4-trn economy in 2025 dollars, among the world's "
                   "six largest; human development near the top, "
                   "perception-of-corruption scores drifting down since "
                   "2012, and reserves small by design under a floating "
                   "pound.",
                pt="Uma economia de US$ 4 trilhões em dólares de 2025, entre "
                   "as seis maiores do mundo; desenvolvimento humano no topo, "
                   "as notas de percepção de corrupção em queda desde 2012, "
                   "e reservas pequenas por projeto sob uma libra flutuante."),
            "spark": ctx.col("international/hdi.csv", "hdi"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "GDP, US$", "pt": "PIB, US$"},
                         [(y, v / 1e9) for y, v in
                          ctx.col("international/gdp_usd.csv", "gdp_usd")],
                         "usd_bn"),
                ctx.stat({"en": "Human Development Index",
                          "pt": "Índice de Desenvolvimento Humano"},
                         ctx.col("international/hdi.csv", "hdi"), "dec3",
                         kind="level"),
                ctx.stat({"en": "Corruption perceptions",
                          "pt": "Percepção de corrupção"},
                         ctx.col("international/cpi.csv",
                                 "cpi_2012_method_0_100"), "score100",
                         kind="level"),
            ],
        },
        {
            "id": "09-demography", "topic": "demography", "n": "09",
            "family": PEOPLE,
            "title": ctx.text(en="Population", pt="População"),
            "blurb": ctx.text(
                en="8.7 million more residents than in 2006, almost all of "
                   "it net migration after 2021; fertility sits below "
                   "replacement in every year of the window and near 1.5 "
                   "children per woman by 2024.",
                pt="8,7 milhões de moradores a mais que em 2006, quase tudo "
                   "migração líquida depois de 2021; a fecundidade fica "
                   "abaixo do nível de reposição em todos os anos da janela, "
                   "perto de 1,5 filho por mulher em 2024."),
            "spark": ctx.col("demography/population.csv", "population_uk"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Population", "pt": "População"},
                         [(y, v / 1e6) for y, v in
                          ctx.col("demography/population.csv",
                                  "population_uk")], "pop_mn",
                         kind="level"),
                ctx.stat({"en": "Fertility rate",
                          "pt": "Taxa de fecundidade"},
                         ctx.col("demography/fertility.csv", "tfr"), "dec2",
                         kind="level"),
                ctx.stat({"en": "Natural increase",
                          "pt": "Crescimento vegetativo"},
                         _natural_increase(ctx), "count"),
            ],
        },
        {
            "id": "10-security", "topic": "security", "n": "10",
            "family": PEOPLE,
            "title": ctx.text(en="Safety", pt="Segurança"),
            "blurb": ctx.text(
                en="Homicide is rare for England & Wales — around one per "
                   "100,000 — and the two official counts, police and death "
                   "certificate, are separately rated and never joined. No "
                   "UK-wide crime series exists.",
                pt="O homicídio é raro na Inglaterra e no País de Gales — "
                   "cerca de um por 100 mil — e as duas contagens oficiais, "
                   "polícia e certidão de óbito, têm notas separadas e nunca "
                   "são emendadas. Não há série de crime para todo o Reino "
                   "Unido."),
            "spark": ctx.col("security/homicide_deaths.csv",
                             "homicide_ons_definition"),
            "stats": [
                ctx.stat({"en": "Homicides, certificates (E&W)",
                          "pt": "Homicídios, certidões (I&P Gales)"},
                         ctx.col("security/homicide_deaths.csv",
                                 "homicide_ons_definition"), "count"),
                ctx.stat({"en": "Police-recorded homicide offences (E&W)",
                          "pt": "Ocorrências de homicídio registradas pela polícia (Inglaterra e País de Gales)"},
                         ctx.col("security/homicide_police.csv",
                                 "offences_currently_recorded",
                                 key="fiscal_year"), "count"),
                ctx.stat({"en": "Road deaths (UK)",
                          "pt": "Mortes no trânsito (RU)"},
                         ctx.col("international/road_deaths.csv",
                                 "road_deaths_per_100k"), "per100k",
                         kind="level"),
            ],
        },
        {
            "id": "11-mortality", "topic": "mortality", "n": "11",
            "family": PEOPLE,
            "title": ctx.text(en="Mortality", pt="Mortalidade"),
            "blurb": ctx.text(
                en="Registered deaths in England & Wales ran 14% above the "
                   "2015–19 mean in 2020 and 8–9% in 2022 and 2023 — and the "
                   "five software and coding changes in the cause-of-death "
                   "series are drawn as seams, not smoothed over.",
                pt="Os óbitos registrados na Inglaterra e no País de Gales "
                   "ficaram 14% acima da média de 2015–19 em 2020 e 8–9% em "
                   "2022 e 2023 — e as cinco mudanças de software e de "
                   "codificação da série de causas de morte são desenhadas "
                   "como emendas, não alisadas."),
            "spark": ctx.col("demography/vital.csv", "deaths"),
            "stats": [
                ctx.stat({"en": "Deaths registered (E&W)",
                          "pt": "Óbitos registrados (I&P Gales)"},
                         ctx.col("demography/vital.csv", "deaths"), "count"),
                ctx.stat({"en": "Crude death rate",
                          "pt": "Taxa bruta de mortalidade"},
                         ctx.col("demography/vital.csv",
                                 "crude_death_rate_per_1000"), "dec2",
                         kind="level"),
                ctx.stat({"en": "Excess deaths vs 2015–19",
                          "pt": "Mortes a mais vs 2015–19"},
                         _excess_vs(ctx, 2015, 2019), "pct_s"),
            ],
        },
        {
            "id": "12-migration", "topic": "migration", "n": "12",
            "family": PEOPLE,
            "title": ctx.text(en="Migration", pt="Migração"),
            "blurb": ctx.text(
                en="The chapter this country queued for: net migration ran "
                   "near 900,000 a year in 2022-23, the rules on dependants "
                   "and study visas tightened, and the estimate for the year "
                   "ending December 2025 came down to 171,000. Three systems "
                   "measured it — Eurostat to 2019, the ONS's administrative "
                   "approach, and the Home Office's own paperwork — and the "
                   "plates keep the three apart.",
                pt="O capítulo por que este país entrou na fila: a migração "
                   "líquida perto de 900 mil ao ano em 2022-23; as regras "
                   "para dependentes e vistos de estudo apertaram, e a "
                   "estimativa para o ano terminado em dezembro de 2025 caiu "
                   "a 171 mil. Três sistemas a mediram — Eurostat até 2019, "
                   "a metodologia administrativa do ONS e a papelada do Home "
                   "Office — e as pranchas mantêm os três separados."),
            "spark": _net_migration(ctx),
            "stats": [
                ctx.stat({"en": "Net migration, YE December",
                          "pt": "Migração líquida, fim de dez."},
                         _net_migration(ctx), "count"),
                ctx.stat({"en": "Asylum applications",
                          "pt": "Pedidos de asilo"},
                         ctx.col("migration/asylum.csv",
                                 "applications_persons"), "count"),
                ctx.stat({"en": "Citizenship grants",
                          "pt": "Concessões de cidadania"},
                         ctx.col("migration/naturalisation.csv",
                                 "citizenship_grants"), "count"),
            ],
        },
    ]

    return chapters


def _growth(ctx):
    """Real GDP growth, % per year, computed from the chained-volume levels
    the same way the economy plate computes it."""
    levels = dict(ctx.col("macro/gdp.csv", "gdp_real_cvm_gbp_mn"))
    return [(y, (levels[y] / levels[y - 1] - 1) * 100)
            for y in sorted(levels) if y - 1 in levels]


def _net_migration(ctx):
    """ONS net migration for rolling years ending December — the only
    reference period that is a calendar year, and never immigration minus
    emigration: the publisher's own net row is used."""
    table = ctx.c.table("migration/flows.csv") or {}
    out = []
    for period, flow, value in zip(table.get("period_end", []),
                                   table.get("flow", []),
                                   table.get("all_nationalities", [])):
        if (isinstance(period, str) and period.endswith("-12")
                and flow == "net" and value == value):
            out.append((int(period[:4]), float(value)))
    return sorted(out)


def _natural_increase(ctx):
    """Eurostat UK births minus deaths, calendar years — the same pair of
    columns the demography plate divides by the ONS population."""
    births = dict(ctx.col("demography/demography.csv", "births"))
    deaths = dict(ctx.col("demography/demography.csv", "deaths"))
    return [(y, births[y] - deaths[y]) for y in sorted(births)
            if y in deaths]


def _partner_share(ctx, name):
    """One partner's share of all UK goods exports, as HMRC's own share
    column reports it — the same ratio the destinations panel draws."""
    table = ctx.c.table("trade/goods_by_partner.csv") or {}
    out = []
    for year, country, share, months in zip(table.get("year", []),
                                            table.get("country", []),
                                            table.get("export_share", []),
                                            table.get("months", [])):
        if (country == name and int(float(months)) == 12
                and (str(share) or "").strip()):
            out.append((int(year), float(share)))
    return sorted(out)


def _excess_vs(ctx, lo: int, hi: int):
    """Registered deaths against the mean of the lo–hi base years, as a
    percentage — the same series and baseline the mortality plate draws."""
    deaths = dict(ctx.col("demography/vital.csv", "deaths"))
    base_years = [y for y in range(lo, hi + 1) if y in deaths]
    if not base_years:
        return []
    base = sum(deaths[y] for y in base_years) / len(base_years)
    return [(y, (deaths[y] / base - 1) * 100) for y in sorted(deaths)
            if y >= lo]
