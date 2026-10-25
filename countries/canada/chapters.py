"""The canada chapters: the cards, their copy and their headline figures.

Editorial copy lives here. Every number is read from this country's CSVs at
build time by the context, so a figure on a card and the same figure on its
plate cannot disagree.

Twelve chapters, on the shared spine. Five rest on the Canadian publishers
that answered during the Statistics Canada outage — Finance, the Bank of
Canada, IRCC, PHAC; the other seven are drawn from the harmonised
international versions of the national series (World Bank, IMF, OECD, UN,
WHO, BIS), and their plates say so. `kind` says whether a figure is
current: 'flow' for an annual total, 'level' for a stock or a rate read at a
moment.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def headline(ctx) -> list[dict]:
    """The figures the page leads with, above the plates."""
    return [
        ctx.stat({"en": "GDP", "fr": "PIB", "pt": "PIB"},
                 [(y, v / 1e9) for y, v in
                  ctx.col("international/gdp_usd.csv", "gdp_usd")], "usd_bn"),
        ctx.stat({"en": "GDP per person, US$", "fr": "PIB par habitant, $US",
                  "pt": "PIB por pessoa, US$"},
                 ctx.col("international/gdp_pc.csv", "gdp_per_person_usd"),
                 "count"),
        ctx.stat({"en": "Population", "fr": "Population", "pt": "População"},
                 [(y, v / 1e6) for y, v in
                  ctx.col("international/population.csv", "population")],
                 "pop_mn", kind="level"),
        ctx.stat({"en": "Policy rate, year-end", "fr": "Taux directeur, fin d'année",
                  "pt": "Juro básico, fim de ano"},
                 ctx.col("markets/rates.csv", "target_rate_eoy"), "pct2",
                 kind="level"),
        ctx.stat({"en": "Federal balance", "fr": "Solde budgétaire fédéral",
                  "pt": "Saldo orçamentário federal"},
                 ctx.col("fiscal/transactions_pct_gdp.csv", "budgetary_balance",
                         key="fiscal_year"), "pct_gdp_s"),
        ctx.stat({"en": "Gross debt (general govt)", "fr": "Dette brute (administrations publiques)",
                  "pt": "Dívida bruta (governo geral)"},
                 ctx.col("international/g7_gross_debt.csv", "canada"),
                 "pct_gdp", kind="level"),
        ctx.stat({"en": "PR admissions", "fr": "Admissions de résidents permanents",
                  "pt": "Admissões de residentes permanentes"},
                 ctx.col("migration/pr_admissions.csv", "admissions"), "count"),
    ]


def build(ctx) -> list[dict]:
    chapters = [
        {
            "id": "01-economy", "topic": "economy", "n": "01",
            "family": MONEY,
            "title": ctx.text(en="The Economy",
                              fr="L'Économie",
                              pt="A Economia"),
            "blurb": ctx.text(
                en="Real growth broke only twice in twenty years — 2009 and "
                   "2020 — while the US-dollar readings bent with the oil "
                   "price and the Canadian dollar.",
                fr="La croissance réelle ne s'est brisée que deux fois en "
                   "vingt ans — 2009 et 2020 — pendant que les lectures en "
                   "dollars américains pliaient avec le prix du pétrole et "
                   "le dollar canadien.",
                pt="O crescimento real só quebrou duas vezes em vinte anos "
                   "— 2009 e 2020 — enquanto as leituras em dólares "
                   "americanos se curvavam com o preço do petróleo e o câmbio."),
            "spark": ctx.col("macro/growth_prices.csv", "real_growth_pct"),
            "stats": [
                ctx.stat({"en": "GDP per person, US$",
                          "fr": "PIB par habitant, $US",
                          "pt": "PIB por pessoa, US$"},
                         ctx.col("international/gdp_pc.csv",
                                 "gdp_per_person_usd"), "count"),
                ctx.stat({"en": "Real growth", "fr": "Croissance réelle",
                          "pt": "Crescimento real"},
                         ctx.col("macro/growth_prices.csv",
                                 "real_growth_pct"), "pct_s"),
                ctx.stat({"en": "CPI inflation", "fr": "Inflation (IPC)",
                          "pt": "Inflação (IPC)"},
                         ctx.col("macro/growth_prices.csv",
                                 "cpi_inflation_pct"), "pct"),
            ],
        },
        {
            "id": "02-fiscal", "topic": "fiscal", "n": "02", "family": MONEY,
            "title": ctx.text(en="The Federal Books",
                              fr="Les Comptes Fédéraux",
                              pt="As Contas Federais"),
            "blurb": ctx.text(
                en="Revenue, deficits and the debt stock, on Ottawa's own "
                   "fiscal-year accounts — the 2020-21 deficit was the "
                   "largest in Canadian peacetime.",
                fr="Recettes, déficits et stock de dette, selon les comptes "
                   "de l'exercice fédéral — le déficit de 2020-21 fut le "
                   "plus important en temps de paix au Canada.",
                pt="Receitas, déficits e o estoque da dívida, nas contas do "
                   "ano fiscal federal — o déficit de 2020-21 foi o maior "
                   "em tempos de paz no Canadá."),
            "spark": ctx.col("fiscal/transactions_pct_gdp.csv",
                             "budgetary_balance", key="fiscal_year"),
            "stats": [
                ctx.stat({"en": "Balance", "fr": "Solde", "pt": "Saldo"},
                         ctx.col("fiscal/transactions_pct_gdp.csv",
                                 "budgetary_balance", key="fiscal_year"),
                         "pct_gdp_s"),
                ctx.stat({"en": "Revenues", "fr": "Recettes", "pt": "Receitas"},
                         ctx.col("fiscal/transactions_pct_gdp.csv", "revenues",
                                 key="fiscal_year"), "pct_gdp"),
                ctx.stat({"en": "Total expenses", "fr": "Dépenses totales",
                          "pt": "Despesas totais"},
                         ctx.col("fiscal/expenses_pct_gdp.csv", "total_expenses",
                                 key="fiscal_year"), "pct_gdp"),
            ],
        },
        {
            "id": "03-spending", "topic": "spending", "n": "03", "family": MONEY,
            "title": ctx.text(en="Where the Money Goes",
                              fr="Où Va l'Argent",
                              pt="Para Onde Vai o Dinheiro"),
            "blurb": ctx.text(
                en="Federal expenses by category against revenues by source "
                   "— and the one tax that carries about half of the take.",
                fr="Les dépenses fédérales par catégorie face aux recettes "
                   "par source — et l'impôt qui porte environ la moitié de "
                   "la collecte.",
                pt="As despesas federais por categoria contra as receitas "
                   "por fonte — e o imposto que carrega cerca de metade da "
                   "arrecadação."),
            "spark": ctx.col("fiscal/expenses_pct_gdp.csv",
                             "total_program_expenses", key="fiscal_year"),
            "stats": [
                ctx.stat({"en": "Program expenses", "fr": "Dépenses de programmes",
                          "pt": "Despesas de programas"},
                         ctx.col("fiscal/expenses_pct_gdp.csv",
                                 "total_program_expenses", key="fiscal_year"),
                         "pct_gdp"),
                ctx.stat({"en": "Transfers to persons", "fr": "Transferts aux personnes",
                          "pt": "Transferências a pessoas"},
                         ctx.col("fiscal/expenses_pct_gdp.csv",
                                 "transfers_to_persons", key="fiscal_year"),
                         "pct_gdp"),
                ctx.stat({"en": "Personal income tax", "fr": "Impôt sur le revenu des personnes",
                          "pt": "Imposto de renda de pessoas físicas"},
                         ctx.col("fiscal/revenues_pct_gdp.csv",
                                 "personal_income_tax", key="fiscal_year"),
                         "pct_gdp"),
            ],
        },
        {
            "id": "04-trade", "topic": "trade", "n": "04",
            "family": WORLD,
            "title": ctx.text(en="Foreign Trade",
                              fr="Le Commerce Extérieur",
                              pt="O Comércio Exterior"),
            "blurb": ctx.text(
                en="About a third of GDP crosses the border each way, and "
                   "three quarters of the goods go south: the surplus with "
                   "one customer pays for the deficit with everyone else.",
                fr="Environ un tiers du PIB traverse la frontière dans "
                   "chaque sens et les trois quarts des marchandises vont "
                   "vers le sud : l'excédent avec un seul client paie le "
                   "déficit avec tous les autres.",
                pt="Cerca de um terço do PIB cruza a fronteira em cada "
                   "sentido, e três quartos das mercadorias vão para o sul: "
                   "o superávit com um único cliente paga o déficit com "
                   "todos os outros."),
            "spark": ctx.col("trade/trade.csv", "exports_pct_gdp"),
            "stats": [
                ctx.stat({"en": "Exports", "fr": "Exportations",
                          "pt": "Exportações"},
                         ctx.col("trade/trade.csv", "exports_pct_gdp"),
                         "pct_gdp"),
                ctx.stat({"en": "Imports", "fr": "Importations",
                          "pt": "Importações"},
                         ctx.col("trade/trade.csv", "imports_pct_gdp"),
                         "pct_gdp"),
                ctx.stat({"en": "US share, goods exports",
                          "fr": "Part des États-Unis, exportations de biens",
                          "pt": "Parte dos EUA, exportações de mercadorias"},
                         _us_share(ctx), "pct", kind="level"),
            ],
        },
        {
            "id": "05-markets", "topic": "markets", "n": "05", "family": MONEY,
            "title": ctx.text(en="Money & Markets",
                              fr="Monnaie et Marchés",
                              pt="Moeda e Mercados"),
            "blurb": ctx.text(
                en="The policy rate's fall and return, Government of Canada "
                   "yields, and a dollar quoted on two series that are never "
                   "spliced.",
                fr="La chute puis le retour du taux directeur, les rendements "
                   "des obligations du gouvernement du Canada, et un dollar "
                   "coté sur deux séries jamais raccordées.",
                pt="A queda e o retorno do juro básico, os rendimentos dos "
                   "títulos do governo do Canadá, e um dólar cotado em duas "
                   "séries que nunca são emendadas."),
            "spark": ctx.col("markets/rates.csv", "target_rate_eoy"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Policy rate, year-end", "fr": "Taux directeur, fin d'année",
                          "pt": "Juro básico, fim de ano"},
                         ctx.col("markets/rates.csv", "target_rate_eoy"),
                         "pct2", kind="level"),
                ctx.stat({"en": "10-year yield", "fr": "Rendement à 10 ans",
                          "pt": "Juro de 10 anos"},
                         ctx.col("markets/rates.csv", "yield_10y_avg"),
                         "pct2"),
                ctx.stat({"en": "CAD per USD", "fr": "CAD par USD",
                          "pt": "CAD por USD"},
                         ctx.col("markets/usdcad.csv", "usd_cad_daily_avg"),
                         "dec2", kind="level"),
            ],
        },
        {
            "id": "06-people", "topic": "people", "n": "06",
            "family": PEOPLE,
            "title": ctx.text(en="People",
                              fr="Les Conditions de Vie",
                              pt="As Pessoas"),
            "blurb": ctx.text(
                en="The pandemic benefits cut inequality in 2020, and the "
                   "child benefit took child poverty from 17% to 7% — "
                   "before both crept back.",
                fr="Les prestations pandémiques ont réduit les inégalités "
                   "en 2020, et l'Allocation canadienne pour enfants a fait "
                   "passer la pauvreté infantile de 17 % à 7 % — avant que "
                   "les deux ne remontent.",
                pt="Os benefícios da pandemia reduziram a desigualdade em "
                   "2020, e o benefício infantil levou a pobreza das crianças "
                   "de 17% a 7% — antes de ambos voltarem a subir."),
            "spark": ctx.col("social/income.csv", "gini"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Gini, disposable income",
                          "fr": "Gini, revenu disponible",
                          "pt": "Gini, renda disponível"},
                         [(y, v * 100) for y, v in
                          ctx.col("social/income.csv", "gini")], "dec2",
                         kind="level"),
                ctx.stat({"en": "Poverty, below half the median",
                          "fr": "Pauvreté, sous la moitié du revenu médian",
                          "pt": "Pobreza, abaixo de metade da mediana"},
                         ctx.col("social/income.csv", "poverty_50_pct"),
                         "pct"),
                ctx.stat({"en": "Child poverty",
                          "fr": "Pauvreté infantile",
                          "pt": "Pobreza infantil"},
                         ctx.col("social/income.csv",
                                 "child_poverty_50_pct"), "pct"),
            ],
        },
        {
            "id": "07-world", "topic": "world", "n": "07", "family": WORLD,
            "title": ctx.text(en="Canada in the World",
                              fr="Le Canada dans le Monde",
                              pt="O Canadá no Mundo"),
            "blurb": ctx.text(
                en="Gross debt near the G7 average and a net figure a tenth "
                   "of it — the gap is the pension plans, and the pair is "
                   "the story.",
                fr="Une dette brute proche de la moyenne du G7 et une dette "
                   "nette dix fois moindre — l'écart tient aux caisses de "
                   "retraite, et la paire est le sujet.",
                pt="Dívida bruta perto da média do G7 e uma dívida líquida "
                   "dez vezes menor — a diferença está nos fundos de "
                   "pensão, e o par é a história."),
            "spark": ctx.col("international/g7_gross_debt.csv", "canada"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Gross debt (general govt)", "fr": "Dette brute (admin. publiques)",
                          "pt": "Dívida bruta (governo geral)"},
                         ctx.col("international/g7_gross_debt.csv", "canada"),
                         "pct_gdp", kind="level"),
                ctx.stat({"en": "Net debt (general govt)", "fr": "Dette nette (admin. publiques)",
                          "pt": "Dívida líquida (governo geral)"},
                         ctx.col("international/g7_net_debt.csv", "canada"),
                         "pct_gdp", kind="level"),
                ctx.stat({"en": "HDI", "fr": "IDH", "pt": "IDH"},
                         ctx.col("international/hdi.csv", "hdi"), "dec3"),
                ctx.stat({"en": "Reserves", "fr": "Réserves", "pt": "Reservas"},
                         [(y, v / 1e9) for y, v in
                          ctx.col("international/reserves.csv", "reserves_usd")],
                         "usd_bn", kind="level"),
            ],
        },
        {
            "id": "08-demography", "topic": "demography", "n": "08",
            "family": PEOPLE,
            "title": ctx.text(en="Demography",
                              fr="La Démographie",
                              pt="A Demografia"),
            "blurb": ctx.text(
                en="The fastest-growing population in the G7 — +2.8% in "
                   "2023 alone, mostly non-permanent residents — while "
                   "fertility fell to 1.25.",
                fr="La population qui croît le plus vite du G7 — +2,8 % "
                   "rien qu'en 2023, pour l'essentiel des résidents non "
                   "permanents — pendant que la fécondité tombait à 1,25.",
                pt="A população que mais cresce no G7 — +2,8% só em 2023, "
                   "em sua maioria não residentes permanentes — enquanto a "
                   "fecundidade caía a 1,25."),
            "spark": ctx.col("international/population.csv", "population"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Population", "fr": "Population",
                          "pt": "População"},
                         [(y, v / 1e6) for y, v in
                          ctx.col("international/population.csv",
                                  "population")], "pop_mn", kind="level"),
                ctx.stat({"en": "Fertility rate",
                          "fr": "Indice de fécondité",
                          "pt": "Taxa de fecundidade"},
                         ctx.col("social/demography.csv", "fertility"),
                         "dec2", kind="level"),
                ctx.stat({"en": "Net migration",
                          "fr": "Solde migratoire",
                          "pt": "Migração líquida"},
                         ctx.col("social/demography.csv", "net_migration"),
                         "count"),
            ],
        },
        {
            "id": "09-security", "topic": "security", "n": "09",
            "family": PEOPLE,
            "title": ctx.text(en="Security",
                              fr="La Sécurité",
                              pt="A Segurança"),
            "blurb": ctx.text(
                en="The homicide rate never left 1.4–2.3 per 100,000; the "
                   "opioid crisis is the exception on the page — 20 deaths "
                   "per 100,000 in 2023.",
                fr="Le taux d'homicide n'a jamais quitté 1,4 à 2,3 pour "
                   "100 000 ; la crise des opioïdes est l'exception de la "
                   "page — 20 décès pour 100 000 en 2023.",
                pt="A taxa de homicídios nunca saiu de 1,4 a 2,3 por 100 "
                   "mil; a crise dos opioides é a exceção da página — 20 "
                   "mortes por 100 mil em 2023."),
            "spark": ctx.col("social/security.csv", "homicide_per_100k"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Homicide rate",
                          "fr": "Taux d'homicide",
                          "pt": "Taxa de homicídios"},
                         ctx.col("social/security.csv",
                                 "homicide_per_100k"), "per100k2",
                         kind="level"),
                ctx.stat({"en": "Road deaths",
                          "fr": "Morts sur la route",
                          "pt": "Mortes no trânsito"},
                         ctx.col("social/security.csv",
                                 "road_deaths_per_100k"), "per100k",
                         kind="level"),
                ctx.stat({"en": "Opioid deaths",
                          "fr": "Décès liés aux opioïdes",
                          "pt": "Mortes por opioides"},
                         ctx.col("social/opioids.csv", "deaths"), "count"),
            ],
        },
        {
            "id": "10-mortality", "topic": "mortality", "n": "10",
            "family": PEOPLE,
            "title": ctx.text(en="Mortality",
                              fr="La Mortalité",
                              pt="A Mortalidade"),
            "blurb": ctx.text(
                en="Deaths ran 22% above the 2015–19 average in 2022, and "
                   "COVID's worst year was the Omicron year, not the first "
                   "one.",
                fr="Les décès ont dépassé de 22 % la moyenne 2015–19 en "
                   "2022, et l'année la plus meurtrière de la COVID fut "
                   "celle d'Omicron, pas la première.",
                pt="As mortes superaram em 22% a média de 2015–19 em 2022, "
                   "e o ano mais letal da COVID foi o da Ômicron, não o "
                   "primeiro."),
            "spark": ctx.col("social/causes_of_death.csv", "deaths"),
            "stats": [
                ctx.stat({"en": "Deaths", "fr": "Décès", "pt": "Óbitos"},
                         ctx.col("social/causes_of_death.csv", "deaths"),
                         "count"),
                ctx.stat({"en": "Crude death rate",
                          "fr": "Taux de mortalité brut",
                          "pt": "Taxa bruta de mortalidade"},
                         [(y, v / 100) for y, v in
                          ctx.col("social/causes_of_death.csv",
                                  "all_causes_per_100k")], "dec2",
                         kind="level"),
                ctx.stat({"en": "Excess deaths vs 2015–19",
                          "fr": "Surmortalité vs 2015–19",
                          "pt": "Mortes a mais vs 2015–19"},
                         _excess_vs(ctx, 2015, 2019), "pct_s"),
            ],
        },
        {
            "id": "11-credit", "topic": "credit", "n": "11",
            "family": MONEY,
            "title": ctx.text(en="Credit",
                              fr="Le Crédit",
                              pt="O Crédito"),
            "blurb": ctx.text(
                en="A fixed-rate country, so the 2022 hikes reached the "
                   "payments only as mortgages renewed: the debt-service "
                   "ratio peaked at 14.6% in 2023.",
                fr="Un pays à taux fixe : les hausses de 2022 n'atteignent "
                   "les paiements qu'au renouvellement des prêts "
                   "hypothécaires — le service de la dette a culminé à "
                   "14,6 % en 2023.",
                pt="Um país de taxa fixa: as altas de 2022 só chegaram às "
                   "parcelas na renovação dos financiamentos — o serviço da "
                   "dívida atingiu o pico de 14,6% em 2023."),
            "spark": ctx.col("credit/household_credit.csv",
                             "hh_credit_pct_gdp_q4"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Household debt",
                          "fr": "Dette des ménages",
                          "pt": "Dívida das famílias"},
                         ctx.col("credit/household_credit.csv",
                                 "hh_credit_pct_gdp_q4"), "pct_gdp",
                         kind="level"),
                ctx.stat({"en": "Debt service",
                          "fr": "Service de la dette",
                          "pt": "Serviço da dívida"},
                         ctx.col("credit/debt_service.csv",
                                 "hh_dsr_pct_q4"), "pct"),
                ctx.stat({"en": "New mortgage rate",
                          "fr": "Taux sur nouveaux prêts",
                          "pt": "Juro de novos financiamentos"},
                         ctx.col("credit/mortgage_rates.csv",
                                 "new_mortgage_rate"), "pct2"),
            ],
        },
        {
            "id": "12-migration", "topic": "migration", "n": "12", "family": PEOPLE,
            "title": ctx.text(en="Migration",
                              fr="Migration",
                              pt="Migração"),
            "blurb": ctx.text(
                en="Admissions climbed to a record, then the policy reversed "
                   "— and the population grew about 3% a year in 2023-24, "
                   "unmatched in the G7.",
                fr="Les admissions ont grimpé jusqu'à un record, puis la "
                   "politique a fait demi-tour — et la population a crû "
                   "d'environ 3 % par an en 2023-24, sans équivalent dans "
                   "le G7.",
                pt="As admissões subiram a um recorde, e então a política "
                   "reverteu — e a população cresceu cerca de 3% ao ano em "
                   "2023-24, sem paralelo no G7."),
            "spark": ctx.col("migration/pr_admissions.csv", "admissions"),
            "stats": [
                ctx.stat({"en": "PR admissions", "fr": "Admissions RP",
                          "pt": "Admissões RP"},
                         ctx.col("migration/pr_admissions.csv", "admissions"),
                         "count"),
                ctx.stat({"en": "Study permits signed", "fr": "Permis d'études signés",
                          "pt": "Permissões de estudo assinadas"},
                         ctx.col("migration/study_permits.csv", "permit_holders"),
                         "count"),
                ctx.stat({"en": "Population", "fr": "Population", "pt": "População"},
                         [(y, v / 1e6) for y, v in
                          ctx.col("international/population.csv", "population")],
                         "pop_mn", kind="level"),
            ],
        },
    ]

    return chapters


def _us_share(ctx):
    """United States as a share of Canada's goods exports, per year.

    The IMF partner file is in dollars and the world line is in the same
    file, so the share is computed, never typed: it is the same ratio the
    destinations panel draws.
    """
    usa = dict(ctx.col("trade/partners.csv", "exports_usa_usd"))
    world = dict(ctx.col("trade/partners.csv", "exports_world_usd"))
    return [(y, usa[y] / world[y] * 100) for y in sorted(usa)
            if y in world and world[y]]


def _excess_vs(ctx, lo: int, hi: int):
    """Registered deaths against the mean of the lo–hi base years, as a
    percentage: the same series the mortality plate's second slot draws."""
    deaths = dict(ctx.col("social/causes_of_death.csv", "deaths"))
    base_years = [y for y in range(lo, hi + 1) if y in deaths]
    if not base_years:
        return []
    base = sum(deaths[y] for y in base_years) / len(base_years)
    return [(y, (deaths[y] / base - 1) * 100) for y in sorted(deaths)
            if y >= lo]
