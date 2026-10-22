"""The canada chapters: the cards, their copy and their headline figures.

Editorial copy lives here. Every number is read from this country's CSVs at
build time by the context, so a figure on a card and the same figure on its
plate cannot disagree.

Five chapters exist while Statistics Canada's platform is down. The spine
numbers are kept — 01, 04, 06, 08, 09, 10 and 11 slot in when StatCan
returns — so nothing here gets renumbered. `kind` says whether a figure is
current: 'flow' for an annual total, 'level' for a stock or a rate read at a
moment.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def headline(ctx) -> list[dict]:
    """The figures the page leads with, above the plates."""
    return [
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
