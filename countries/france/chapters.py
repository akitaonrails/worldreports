"""The france chapters: the cards, their copy and their headline figures.

Editorial copy lives here. Every number is read from this country's CSVs at
build time by the context, so a figure on a card and the same figure on its
plate cannot disagree.

`spec` names how a figure is written, not what it means — see
core.sitebuild.NUMFMT and AFFIX. `kind` says whether it is current:
'flow' for an annual total that is only comparable once the year is
complete, 'level' for a stock or a rate read at a moment, 'projection' for
an official forward estimate.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def headline(ctx) -> list[dict]:
    """The figures the page leads with, above the plates.

    Six readings that frame everything below, computed from this country's
    CSVs at build time rather than typed in, so a refetch moves them
    instead of leaving the page quietly describing last year.

    `kind` is the load-bearing argument. An annual total or average is a
    flow: it stops at the last complete year, because the running year's
    partial figure is not comparable with the ones before it. A stock or a
    population estimate is a level, read at a moment and genuinely
    current. The year is printed under each figure by the page, from the
    row it was actually read from, so the labels do not repeat it.
    """
    return [
        ctx.stat({"fr": 'PIB', "en": 'GDP', "pt": 'PIB'},
                 ctx.col("macro/gdp.csv", "nominal_eurbn"), "money_bn"),
        ctx.stat({"fr": 'PIB par habitant, US$', "en": 'GDP per person, US$',
                  "pt": 'PIB por pessoa, US$'},
                 ctx.col("macro/gdp.csv", "gdp_per_capita_usd"), "count"),
        ctx.stat({"fr": 'Population', "en": 'Population', "pt": 'População'},
                 ctx.col("macro/gdp.csv", "population_mn"), "pop_mn", kind="level"),
        ctx.stat({"fr": 'Inflation (IPC)', "en": 'Inflation (CPI)',
                  "pt": 'Inflação (IPC)'},
                 ctx.col("macro/inflation.csv", "ipc"), "pct"),
        ctx.stat({"fr": 'Chômage', "en": 'Unemployment',
                  "pt": 'Desemprego'},
                 ctx.col("macro/unemployment.csv", "value"), "pct"),
        ctx.stat({"fr": 'Dette publique brute', "en": 'Gross public debt',
                  "pt": 'Dívida pública bruta'},
                 ctx.col("fiscal/debt.csv", "gross"), "pct_gdp", kind="level"),
    ]


def build(ctx) -> list[dict]:
    chapters = [
        {
            "id": "01_economy", "topic": "economy", "n": "01", "family": MONEY,
            "title": ctx.text(en="The French Economy", fr="L'Économie Française", pt="A Economia Francesa"),
            "blurb": ctx.text(en="Nominal size, real growth, income per person and inflation "
                "— the four numbers the rest depend on.", fr="Taille nominale, croissance réelle, revenu par habitant et "
                "inflation — les quatre chiffres dont dépend le reste.", pt="Tamanho nominal, crescimento real, renda por pessoa e "
                "inflação — os quatro números dos quais o resto depende."),
            "spark": ctx.col("macro/gdp.csv", "nominal_eurbn"),
            "stats": [
                ctx.stat({"en": "GDP", "fr": "PIB", "pt": "PIB"},
                     ctx.col("macro/gdp.csv", "nominal_eurbn"), "money_bn"),
                ctx.stat({"en": "Real growth", "fr": "Croissance réelle", "pt": "Crescimento real"},
                     ctx.col("macro/gdp.csv", "real_growth"), "pct_s"),
                ctx.stat({"en": "Inflation", "fr": "Inflation", "pt": "Inflação"},
                     ctx.col("macro/inflation.csv", "ipc"), "pct"),
            ],
        },
        {
            "id": "02_fiscal", "topic": "fiscal", "n": "02", "family": MONEY,
            "title": ctx.text(en="Taxes, Deficit & Debt", fr="Prélèvements, Déficit et Dette", pt="Impostos, Déficit e Dívida"),
            "blurb": ctx.text(en="The heaviest tax take in the EU, a deficit that never "
                "closes, and what that does to the debt stock.", fr="Les prélèvements les plus lourds de l'UE, un déficit qui ne "
                "se referme jamais, et ce que cela fait au stock de dette.", pt="A maior carga tributária da UE, um déficit que nunca fecha, "
                "e o que isso faz com o estoque da dívida."),
            "spark": ctx.col("fiscal/debt.csv", "gross"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Gross debt", "fr": "Dette brute", "pt": "Dívida bruta"},
                     ctx.col("fiscal/debt.csv", "gross"), "pct_gdp"),
                ctx.stat({"en": "Compulsory levies", "fr": "Prélèvements obligatoires", "pt": "Carga tributária"},
                     ctx.col("fiscal/tax_burden.csv", "insee"), "pct_gdp"),
                ctx.stat({"en": "Deficit", "fr": "Déficit", "pt": "Déficit"},
                     ctx.col("fiscal/deficit.csv", "deficit"), "pct_gdp_s"),
            ],
        },
        {
            "id": "03_spending", "topic": "spending", "n": "03", "family": MONEY,
            "title": ctx.text(en="Where the Money Goes", fr="Où Va l'Argent", pt="Para Onde Vai o Dinheiro"),
            "blurb": ctx.text(en="Public spending by function — social protection against "
                "everything else the state has to carry.", fr="La dépense publique par fonction — la protection sociale "
                "face à tout ce que l'État doit porter.", pt="O gasto público por função — a proteção social contra tudo "
                "mais que o Estado precisa carregar."),
            "spark": ctx.col("fiscal/spending_by_function.csv", "total"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Total spending", "fr": "Dépense totale", "pt": "Gasto total"},
                     ctx.col("fiscal/spending_by_function.csv", "total"),
                     "pct_gdp"),
                ctx.stat({"en": "Social protection", "fr": "Protection sociale", "pt": "Proteção social"},
                     ctx.col("fiscal/spending_by_function.csv",
                         "social_protection"), "pct_gdp"),
                ctx.stat({"en": "Public investment", "fr": "Investissement public", "pt": "Investimento público"},
                     ctx.col("fiscal/investment.csv", "gov_gfcf_pct_gdp"),
                     "pct_gdp"),
            ],
        },
        {
            "id": "04_trade", "topic": "trade", "n": "04", "family": WORLD,
            "title": ctx.text(en="Foreign Trade", fr="Commerce Extérieur", pt="Comércio Exterior"),
            "blurb": ctx.text(en="A goods deficit that became structural, and the aeronautics "
                "and luxury exports that soften it.", fr="Un déficit de biens devenu structurel, et les exportations "
                "aéronautiques et de luxe qui l'atténuent.", pt="Um déficit de bens que virou estrutural, e as exportações "
                "de aeronáutica e luxo que o amenizam."),
            "spark": ctx.col("trade/trade.csv", "balance"),
            "stats": [
                ctx.stat({"en": "Exports", "fr": "Exportations", "pt": "Exportações"},
                     ctx.col("trade/trade.csv", "exports"), "money_bn"),
                ctx.stat({"en": "Imports", "fr": "Importations", "pt": "Importações"},
                     ctx.col("trade/trade.csv", "imports"), "money_bn"),
                ctx.stat({"en": "Balance", "fr": "Solde", "pt": "Saldo"},
                     ctx.col("trade/trade.csv", "balance"), "money_bn"),
            ],
        },
        {
            "id": "05_markets", "topic": "markets", "n": "05", "family": MONEY,
            "title": ctx.text(en="Money & Markets", fr="Monnaie et Marchés", pt="Moeda e Mercados"),
            "blurb": ctx.text(en="The CAC 40 beside the S&P 500, the euro against the dollar, "
                "and eight years of negative rates.", fr="Le CAC 40 face au S&P 500, l'euro face au dollar, et huit "
                "années de taux négatifs.", pt="O CAC 40 ao lado do S&P 500, o euro contra o dólar, e oito "
                "anos de juros negativos."),
            "spark": ctx.col("markets/cac40.csv", "close"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "CAC 40", "fr": "CAC 40", "pt": "CAC 40"},
                     ctx.col("markets/cac40.csv", "close"), "count",
                     kind="level"),
                ctx.stat({"en": "US$ per €", "fr": "$US par €", "pt": "US$ por €"},
                     ctx.col("macro/eurusd.csv", "eop"), "dec2", kind="level"),
                ctx.stat({"en": "ECB rate", "fr": "Taux BCE", "pt": "Juros do BCE"},
                     ctx.col("macro/policy_rate.csv", "dfr"), "pct2",
                     kind="level"),
            ],
        },
        {
            "id": "06_people", "topic": "people", "n": "06", "family": PEOPLE,
            "title": ctx.text(en="Development, Jobs & Poverty", fr="Développement, Emploi et Pauvreté", pt="Desenvolvimento, Trabalho e Pobreza"),
            "blurb": ctx.text(en="Human development, inequality, unemployment, the minimum "
                "wage and a poverty rate that will not fall.", fr="Développement humain, inégalités, chômage, salaire minimum "
                "et un taux de pauvreté qui ne baisse pas.", pt="Desenvolvimento humano, desigualdade, desemprego, salário "
                "mínimo e uma taxa de pobreza que não cai."),
            "spark": ctx.col("macro/unemployment.csv", "value"),
            "stats": [
                ctx.stat({"en": "Unemployment", "fr": "Chômage", "pt": "Desemprego"},
                     ctx.col("macro/unemployment.csv", "value"), "pct"),
                ctx.stat({"en": "HDI", "fr": "IDH", "pt": "IDH"},
                     ctx.col("social/hdi.csv", "value"), "dec3"),
                ctx.stat({"en": "Poverty rate", "fr": "Taux de pauvreté", "pt": "Taxa de pobreza"},
                     ctx.col("social/poverty.csv", "rate60"), "pct"),
            ],
        },
        {
            "id": "07_world", "topic": "world", "n": "07", "family": WORLD,
            "title": ctx.text(en="France in the World", fr="La France dans le Monde", pt="A França no Mundo"),
            "blurb": ctx.text(en="How the outside world scores France, how open its economy "
                "is, and the gold behind its reserves.", fr="Comment le monde évalue la France, le degré d'ouverture de "
                "son économie, et l'or derrière ses réserves.", pt="Como o mundo avalia a França, quão aberta é sua economia, e "
                "o ouro por trás de suas reservas."),
            "spark": ctx.col("macro/reserves.csv", "eop_usdbn"),
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Reserves", "fr": "Réserves", "pt": "Reservas"},
                     ctx.col("macro/reserves.csv", "eop_usdbn"), "usd_bn"),
                ctx.stat({"en": "Corruption index", "fr": "Indice de corruption", "pt": "Índice de corrupção"},
                     ctx.col("international/cpi.csv", "score"), "score100"),
                ctx.stat({"en": "Competitiveness", "fr": "Compétitivité", "pt": "Competitividade"},
                     ctx.col("international/wef.csv", "rank"), "rank"),
            ],
        },
        {
            "id": "08_demographics", "topic": "demography", "n": "08", "family": PEOPLE,
            "title": ctx.text(en="The Demographic Transition", fr="La Transition Démographique", pt="A Transição Demográfica"),
            "blurb": ctx.text(en="Fertility at its lowest since the war, and deaths now "
                "outnumbering births.", fr="La fécondité au plus bas depuis la guerre, et des décès "
                "désormais plus nombreux que les naissances.", pt="A fecundidade no menor nível desde a guerra, e os óbitos "
                "agora superando os nascimentos."),
            "spark": [p for p in ctx.col("social/population.csv", "tfr")
                      if p[0] <= ctx.LAST_FULL_YEAR],
            "spark_level": True,
            "stats": [
                ctx.stat({"en": "Fertility rate", "fr": "Fécondité", "pt": "Taxa de fecundidade"},
                     [p for p in ctx.col("social/population.csv", "tfr")
                      if p[0] <= ctx.LAST_FULL_YEAR], "dec2"),
                ctx.stat({"en": "Births", "fr": "Naissances", "pt": "Nascimentos"},
                     [p for p in ctx.col("social/population.csv", "births")
                      if p[0] <= ctx.LAST_FULL_YEAR], "count"),
                ctx.stat({"en": "Population", "fr": "Population", "pt": "População"},
                     ctx.col("social/population.csv", "pop_mn"), "pop_mn",
                     year=2026, kind="projection"),
            ],
        },
        {
            "id": "09_security", "topic": "security", "n": "09", "family": PEOPLE,
            "title": ctx.text(en="Violence", fr="Violences", pt="Violência"),
            "blurb": ctx.text(en="Homicides counted two incompatible ways, femicides, and "
                "recorded violence that reflects reporting as much as crime.", fr="Les homicides comptés de deux façons incompatibles, les "
                "féminicides, et des violences enregistrées qui reflètent "
                "autant le dépôt de plainte que la délinquance.", pt="Homicídios contados de duas formas incompatíveis, "
                "feminicídios, e violências registradas que refletem tanto a "
                "denúncia quanto o crime."),
            "spark": ctx.col("social/homicides.csv", "ssmsi_rate"),
            "stats": [
                ctx.stat({"en": "Homicide rate", "fr": "Taux d'homicides", "pt": "Taxa de homicídios"},
                     ctx.col("social/homicides.csv", "ssmsi_rate"), "per100k"),
                ctx.stat({"en": "Homicides", "fr": "Homicides", "pt": "Homicídios"},
                     ctx.col("social/homicides.csv", "ssmsi_count"), "count"),
                ctx.stat({"en": "Killed by a partner", "fr": "Tuées par leur conjoint", "pt": "Mortas pelo companheiro"},
                     ctx.col("social/violence.csv", "women_killed_by_partner"),
                     "count"),
            ],
        },
        {
            "id": "10_mortality", "topic": "mortality", "n": "10", "family": PEOPLE,
            "title": ctx.text(en="Mortality", fr="Mortalité", pt="Mortalidade"),
            "blurb": ctx.text(en="COVID-19 and influenza deaths counted three different ways, "
                "against twenty years of all-cause mortality.", fr="Les morts du COVID-19 et de la grippe comptés de trois "
                "façons différentes, face à vingt ans de mortalité toutes "
                "causes.", pt="Mortes por COVID-19 e gripe contadas de três formas "
                "diferentes, contra vinte anos de mortalidade por todas as "
                "causas."),
            "spark": ctx.col("social/all_cause_deaths.csv", "insee"),
            "stats": [
                ctx.stat({"en": "All deaths", "fr": "Décès", "pt": "Óbitos"},
                     ctx.col("social/all_cause_deaths.csv", "insee"), "count"),
                # The CépiDc column, not the surveillance one: it is the only
                # COVID count that still has a recent year, and it is the one
                # that means "COVID was the underlying cause".
                ctx.stat({"en": "COVID-19 deaths (certified cause)", "fr": "Morts du COVID-19 (cause initiale)", "pt": "Mortes por COVID-19 (causa básica)"},
                     ctx.col("social/covid_deaths.csv", "deaths_cepidc"),
                     "count"),
                ctx.stat({"en": "Influenza deaths (certified cause)", "fr": "Morts de la grippe (cause initiale)", "pt": "Mortes por gripe (causa básica)"},
                     ctx.col("social/flu_deaths.csv", "deaths_cepidc"), "count"),
            ],
        },
        {
            "id": "11_credit", "topic": "credit", "n": "11", "family": MONEY,
            "title": ctx.text(en="Credit and Household Debt", fr="Le Crédit et la Dette des Ménages", pt="Crédito e Dívida das Famílias"),
            "blurb": ctx.text(en="What borrowing costs, how much households owe, and why a "
                "rate shock left the existing stock almost untouched.", fr="Ce que coûte emprunter, combien les ménages doivent, et "
                "pourquoi un choc de taux a laissé l'encours presque "
                "intact.", pt="Quanto custa tomar emprestado, quanto as famílias devem, e "
                "por que um choque de juros deixou o estoque quase "
                "intacto."),
            "spark": ctx.col("credit/household_debt.csv",
                         "hh_debt_pct_gdi_ecb_nco_q4"),
            "stats": [
                # A point-in-time rate, not an annual average: this is the
                # one a borrower would be quoted today.
                ctx.stat({"en": "New housing loan rate", "fr": "Taux des nouveaux crédits à l'habitat", "pt": "Juros de novos financiamentos imobiliários"},
                     ctx.col("credit/lending_rates.csv", "housing_new_total_pct"),
                     "pct2", kind="level"),
                ctx.stat({"en": "Household debt", "fr": "Dette des ménages", "pt": "Dívida das famílias"},
                     ctx.col("credit/household_debt.csv",
                         "hh_debt_pct_gdi_ecb_nco_q4"),
                     "pct", kind="level"),
                ctx.stat({"en": "Over-indebtedness filings", "fr": "Dossiers de surendettement", "pt": "Pedidos de superendividamento"},
                     ctx.col("credit/overindebtedness.csv",
                         "dossiers_deposes_published"), "count"),
            ],
        },
    ]

    return chapters
