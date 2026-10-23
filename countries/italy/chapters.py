"""The italy chapters: the cards, their copy and their headline figures.

Editorial copy lives here. Every number is read from this country's CSVs at
build time by the context, so a figure on a card and the same figure on its
plate cannot disagree.

Twelve chapters, on the shared spine, in the same order as the plates:
`id` is the plate file's stem, so a card and its plate are the same number
in the comparison viewer. `kind` says whether a figure is current: 'flow'
for an annual total or average, which stops at the last complete year;
'level' for a stock or a rate read at a moment; 'total' for a cumulative
count that belongs to no single year.

Two Italian quirks show up in the card figures. The crude rates and the
suicide rate are computed here from the same register counts and the same
1-January population the plates divide, so card and plate print the same
decimal; the COVID count is a cumulative certificate total (code 20,
2020–23) and carries its span, not a year; and there is no minimum-wage
stat to put on the people card, because Italy has no statutory one.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def _joined(ctx, num_rel: str, num_col: str, den_rel: str, den_col: str,
            scale: float = 1.0) -> list[tuple[int, float]]:
    """(year, num/den × scale) for the years both files carry."""
    den = dict(ctx.col(den_rel, den_col))
    return [(y, v / den[y] * scale)
            for y, v in ctx.col(num_rel, num_col) if y in den]


def _causes(ctx, code: str) -> list[tuple[int, float]]:
    """One code's death counts from the shortlist file, never summed
    across codes: the European shortlist nests, so the column contains
    families and their members side by side.

    Read with the csv module, as the plates do: read_table number-casts
    the code column and float("17_1_1") is 1711.0 — Python's underscore
    digit grouping. The codes are ICD shortlist labels, not numbers.
    """
    import csv
    path = ctx.c.data("social/causes_of_death.csv")
    out = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(ln for ln in fh
                                if not ln.lstrip().startswith("#"))
        for r in reader:
            if r["code"] == code and (r.get("deaths") or "").strip():
                out.append((int(float(r["year"])), float(r["deaths"])))
    return sorted(out)


def _per_pop(ctx, pairs, scale: float) -> list[tuple[int, float]]:
    """Counts over the Eurostat 1-January population — the same division
    the plates make, so card and plate print the same decimal."""
    pop = dict(ctx.col("social/demography.csv", "population"))
    return [(y, v / pop[y] * scale) for y, v in pairs if y in pop]


def headline(ctx) -> list[dict]:
    """The figures the page leads with, above the plates."""
    return [
        ctx.stat({"it": "PIL", "en": "GDP", "pt": "PIB"},
                 ctx.col("macro/gdp.csv", "nominal_eurbn"),
                 "money_bn"),
        ctx.stat({"it": "PIL pro capite, US$", "en": "GDP per person, US$",
                  "pt": "PIB por pessoa, US$"},
                 ctx.col("international/gdp_pc.csv",
                         "gdp_per_person_usd"), "count"),
        ctx.stat({"it": "Popolazione", "en": "Population", "pt": "População"},
                 [(y, v / 1e6) for y, v in
                  ctx.col("social/demography.csv", "population")],
                 "pop_mn", kind="level"),
        ctx.stat({"it": "Inflazione (IPCA)", "en": "Inflation (HICP)",
                  "pt": "Inflação (IPCA)"},
                 ctx.col("macro/hicp.csv", "hicp"), "pct"),
        ctx.stat({"it": "Tasso di disoccupazione", "en": "Unemployment",
                  "pt": "Taxa de desemprego"},
                 ctx.col("macro/unemployment.csv",
                         "unemp_rate_avg"), "pct"),
        ctx.stat({"it": "Debito pubblico lordo", "en": "Gross public debt",
                  "pt": "Dívida pública bruta"},
                 ctx.col("fiscal/debt.csv", "gross_pct_gdp"),
                 "pct_gdp", kind="level"),
    ]


def build(ctx) -> list[dict]:
    pop = "social/demography.csv"

    deaths = dict(ctx.col(pop, "deaths"))
    base = sum(deaths[y] for y in range(2015, 2020)) / 5
    excess_2020 = [(y, (deaths[y] / base - 1) * 100) for y in (2020,)
                   if y in deaths]

    exports = dict(ctx.col("trade/trade_from_estat.csv", "exports_eurbn"))
    imports = dict(ctx.col("trade/trade_from_estat.csv", "imports_eurbn"))
    balance = [(y, exports[y] - imports[y]) for y in sorted(exports)
               if y in imports]

    chapters = [
        {
            "id": "01-economy", "topic": "economy", "n": "01",
            "family": MONEY,
            "title": ctx.text(
                it="Crescita, prezzi e il lungo ristagno",
                en="Growth, Prices and the Long Stall",
                pt="Crescimento, preços e o longo estancamento"),
            "blurb": ctx.text(
                it="La crescita reale che si ferma dopo la crisi del 2008, "
                   "il PIL pro capite in dollari e la disoccupazione ISTAT "
                   "che dimezza solo a metà anni Venti.",
                en="Real growth that never recovers the 2008 loss, income "
                   "per person in dollars, and an unemployment rate that "
                   "halves only in the late 2020s.",
                pt="O crescimento real que nunca recupera a perda de 2008, "
                   "a renda per pessoa em dólares e um desemprego que só "
                   "cai pela metade no fim dos anos 2020."),
            "spark": ctx.col("macro/gdp.csv", "nominal_eurbn"),
            "stats": [
                ctx.stat({"it": "PIL", "en": "GDP", "pt": "PIB"},
                         ctx.col("macro/gdp.csv", "nominal_eurbn"),
                         "money_bn"),
                ctx.stat({"it": "Crescita reale", "en": "Real growth",
                          "pt": "Crescimento real"},
                         ctx.col("macro/gdp.csv", "real_growth"),
                         "pct_s"),
                ctx.stat({"it": "Inflazione (IPCA)", "en": "Inflation (HICP)",
                          "pt": "Inflação (IPCA)"},
                         ctx.col("macro/hicp.csv", "hicp"), "pct"),
                ctx.stat({"it": "Disoccupazione (media annua)",
                          "en": "Unemployment (annual average)",
                          "pt": "Desemprego (média anual)"},
                         ctx.col("macro/unemployment.csv",
                                 "unemp_rate_avg"), "pct"),
            ],
        },
        {
            "id": "02-fiscal", "topic": "fiscal", "n": "02",
            "family": MONEY,
            "title": ctx.text(
                it="Prelievo, disavanzo e debito",
                en="Levies, Deficit and Debt",
                pt="Tributos, déficit e dívida"),
            "blurb": ctx.text(
                it="Il prelievo europeo più alto dopo Danimarca e Belgio, "
                   "un disavanzo che non chiude mai e un debito che la "
                   "crisi del 2011–12 porta oltre il 130% del PIL.",
                en="One of Europe's heaviest tax takes, a deficit that has "
                   "never closed, and a debt the 2011–12 crisis pushed past "
                   "130% of GDP.",
                pt="Uma das cargas tributárias mais pesadas da Europa, um "
                   "déficit que nunca fecha e uma dívida que a crise de "
                   "2011–12 levou acima de 130% do PIB."),
            "spark": ctx.col("fiscal/debt.csv", "gross_pct_gdp"),
            "spark_level": True,
            "stats": [
                ctx.stat({"it": "Debito pubblico lordo",
                          "en": "Gross public debt", "pt": "Dívida pública"},
                         ctx.col("fiscal/debt.csv",
                                 "gross_pct_gdp"), "pct_gdp", kind="level"),
                ctx.stat({"it": "Indebitamento netto", "en": "Deficit",
                          "pt": "Déficit"},
                         ctx.col("fiscal/deficit.csv", "deficit"),
                         "pct_gdp_s"),
                ctx.stat({"it": "Pressione fiscale", "en": "Tax burden",
                          "pt": "Carga tributária"},
                         ctx.col("fiscal/tax_burden.csv", "estat"),
                         "pct_gdp"),
            ],
        },
        {
            "id": "03-spending", "topic": "spending", "n": "03",
            "family": MONEY,
            "title": ctx.text(
                it="Dove va la spesa",
                en="Where the Money Goes",
                pt="Para onde vai o gasto"),
            "blurb": ctx.text(
                it="La spesa pubblica per funzione: le pensioni dentro la "
                   "protezione sociale, e il salto del 2020 che non torna "
                   "indietro nemmeno nel 2024.",
                en="Public spending by function: pensions inside social "
                   "protection, and the 2020 jump that had still not come "
                   "back down by 2024.",
                pt="O gasto público por função: pensões dentro da proteção "
                   "social, e o salto de 2020 que ainda não tinha voltado "
                   "em 2024."),
            "spark": ctx.col("fiscal/spending_by_function.csv",
                             "total"),
            "spark_level": True,
            "stats": [
                ctx.stat({"it": "Spesa totale", "en": "Total spending",
                          "pt": "Gasto total"},
                         ctx.col("fiscal/spending_by_function.csv",
                                 "total"), "pct_gdp"),
                ctx.stat({"it": "Protezione sociale",
                          "en": "Social protection", "pt": "Proteção social"},
                         ctx.col("fiscal/spending_by_function.csv",
                                 "social_protection"), "pct_gdp"),
                ctx.stat({"it": "Investimento pubblico",
                          "en": "Public investment",
                          "pt": "Investimento público"},
                         ctx.col("fiscal/investment.csv",
                                 "gov_gfcf_pct_gdp"), "pct_gdp"),
            ],
        },
        {
            "id": "04-trade", "topic": "trade", "n": "04",
            "family": WORLD,
            "title": ctx.text(
                it="Commercio con l'estero",
                en="Foreign Trade",
                pt="Comércio exterior"),
            "blurb": ctx.text(
                it="Una manifattura forte che esporta, fatturata in euro; "
                   "il saldo merci in rosso solo negli anni del gas caro, "
                   "2011 e 2022, in surplus negli altri.",
                en="A strong manufacturing base that exports, billed in "
                   "euros; a customs goods balance in deficit only in the "
                   "expensive-gas years, 2011 and 2022, in surplus in all "
                   "the others.",
                pt="Uma indústria forte que exporta, faturada em euros; "
                   "saldo aduaneiro de mercadorias em déficit só nos anos "
                   "de gás caro, 2011 e 2022, positivo nos demais."),
            "spark": balance,
            "stats": [
                ctx.stat({"it": "Esportazioni (fob)", "en": "Exports (fob)",
                          "pt": "Exportações (fob)"},
                         ctx.col("trade/trade_from_estat.csv",
                                 "exports_eurbn"), "money_bn"),
                ctx.stat({"it": "Importazioni (fob)", "en": "Imports (fob)",
                          "pt": "Importações (fob)"},
                         ctx.col("trade/trade_from_estat.csv",
                                 "imports_eurbn"), "money_bn"),
                ctx.stat({"it": "Saldo merci", "en": "Goods balance",
                          "pt": "Saldo de mercadorias"},
                         balance, "money_bn"),
            ],
        },
        {
            "id": "05-markets", "topic": "markets", "n": "05",
            "family": MONEY,
            "title": ctx.text(
                it="Moneta e mercati",
                en="Money and Markets",
                pt="Moeda e mercados"),
            "blurb": ctx.text(
                it="Piazza Affari in dollari: metà del valore bruciato nel "
                   "2012 e un decennio per non ritrovarlo; il BTP decennale "
                   "al picco dello spread.",
                en="Milan in dollars: half its value burned by 2012 and a "
                   "decade that did not bring it back; the ten-year BTP at "
                   "the peak of the spread.",
                pt="Milão em dólares: metade do valor queimado até 2012 e "
                   "uma década que não o recuperou; o BTP de dez anos no "
                   "pico do spread."),
            "spark": ctx.col("markets/ftsemib.csv", "close"),
            "spark_level": True,
            "stats": [
                ctx.stat({"it": "FTSE MIB (fine anno)",
                          "en": "FTSE MIB (year-end)",
                          "pt": "FTSE MIB (fim de ano)"},
                         ctx.col("markets/ftsemib.csv", "close"),
                         "count", kind="level"),
                ctx.stat({"it": "BTP decennale (media annua)",
                          "en": "10-year BTP (annual average)",
                          "pt": "BTP de 10 anos (média anual)"},
                         ctx.col("markets/yield_10y.csv",
                                 "yield_10y"), "pct2"),
                ctx.stat({"it": "Tasso BCE (depositi, fine anno)",
                          "en": "ECB rate (deposit, year-end)",
                          "pt": "Taxa do BCE (depósitos, fim de ano)"},
                         ctx.col("markets/policy_rate.csv", "dfr"),
                         "pct2", kind="level"),
            ],
        },
        {
            "id": "06-credit", "topic": "credit", "n": "06",
            "family": MONEY,
            "title": ctx.text(
                it="Credito e debito delle famiglie",
                en="Credit and Household Debt",
                pt="Crédito e dívida das famílias"),
            "blurb": ctx.text(
                it="Quanto costa mutui, quanto devono le famiglie sul loro "
                   "reddito disponibile, e le sofferenze bancarie che scende "
                   "dai picchi della crisi.",
                en="What borrowing costs, how much households owe against "
                   "their own disposable income, and the NPL ratio sliding "
                   "down from its crisis peak.",
                pt="Quanto custa empréstimo, quanto as famílias devem sobre "
                   "a própria renda disponível e as inadimplências que "
                   "caem do pico da crise."),
            "spark": ctx.col("credit/household_debt.csv",
                             "debt_pct_gdi_computed"),
            "spark_level": True,
            "stats": [
                ctx.stat({"it": "Debiti delle famiglie (prestiti)",
                          "en": "Household loans", "pt": "Empréstimos das "
                          "famílias"},
                         ctx.col("credit/household_debt.csv",
                                 "loans_eurbn"), "money_bn", kind="level"),
                ctx.stat({"it": "Mutui nuovi (media annua)",
                          "en": "New mortgage rate (annual average)",
                          "pt": "Juros de novos imóveis (média anual)"},
                         ctx.col("credit/lending_rate.csv",
                                 "house_new_avg"), "pct2"),
                ctx.stat({"it": "Sofferenze su prestiti",
                          "en": "NPL share of loans",
                          "pt": "Inadimplência sobre empréstimos"},
                         ctx.col("credit/npl.csv",
                                 "npl_gross_ratio_fsi"), "pct"),
            ],
        },
        {
            "id": "07-people", "topic": "people", "n": "07",
            "family": PEOPLE,
            "title": ctx.text(
                it="Disuguaglianza e povertà",
                en="Inequality and Poverty",
                pt="Desigualdade e pobreza"),
            "blurb": ctx.text(
                it="Il Gini EU-SILC dal 2014, la soglia europea di rischio e "
                   "la povertà assoluta ISTAT che sale dopo il 2019. Nessun "
                   "salario minimo per legge: contano i contratti collettivi.",
                en="The EU-SILC Gini from 2014, Europe's at-risk line and "
                   "ISTAT's absolute poverty climbing after 2019. No "
                   "statutory minimum wage: the collective agreements set "
                   "the floors.",
                pt="O Gini EU-SILC desde 2014, a linha europeia de risco e a "
                   "pobreza absoluta do ISTAT que sobe após 2019. Sem "
                   "salário mínimo legal: os pisos vêm dos acordos "
                   "coletivos."),
            "spark": ctx.col("social/poverty.csv", "arop60"),
            "stats": [
                ctx.stat({"it": "A rischio di povertà (60%)",
                          "en": "At risk of poverty (60%)",
                          "pt": "Em risco de pobreza (60%)"},
                         ctx.col("social/poverty.csv", "arop60"),
                         "pct"),
                ctx.stat({"it": "Gini (EU-SILC)", "en": "Gini (EU-SILC)",
                          "pt": "Gini (EU-SILC)"},
                         ctx.col("social/gini.csv", "silc"),
                         "dec2"),
                ctx.stat({"it": "Povertà assoluta (ISTAT)",
                          "en": "Absolute poverty (ISTAT)",
                          "pt": "Pobreza absoluta (ISTAT)"},
                         ctx.col("social/poverty_abs.csv",
                                 "abs_hh"), "pct"),
            ],
        },
        {
            "id": "08-world", "topic": "world", "n": "08",
            "family": WORLD,
            "title": ctx.text(
                it="L'Italia nel mondo",
                en="Italy in the World",
                pt="A Itália no mundo"),
            "blurb": ctx.text(
                it="La dimensione dell'economia in dollari, lo sviluppo "
                   "umano e le riserve ufficiali — senza oro dal 2023, per "
                   "la prima volta in questo archivio.",
                en="The economy's size in dollars, human development, and "
                   "the official reserves — no gold figure in this archive "
                   "past 2023.",
                pt="O tamanho da economia em dólares, o desenvolvimento "
                   "humano e as reservas oficiais — sem número de ouro neste "
                   "arquivo depois de 2023."),
            "spark": ctx.col("international/reserves.csv",
                             "reserves_usd"),
            "spark_level": True,
            "stats": [
                ctx.stat({"it": "PIL in dollari", "en": "GDP in US$",
                          "pt": "PIB em dólares"},
                         [(y, v / 1e9) for y, v in
                          ctx.col("international/gdp_usd.csv",
                                  "gdp_usd")], "usd_bn"),
                ctx.stat({"it": "ISU", "en": "HDI", "pt": "IDH"},
                         ctx.col("international/hdi.csv", "hdi"),
                         "dec3"),
                ctx.stat({"it": "Riserve ufficiali", "en": "Reserves",
                          "pt": "Reservas"},
                         [(y, v / 1e9) for y, v in
                          ctx.col("international/reserves.csv",
                                  "reserves_usd")], "usd_bn", kind="level"),
            ],
        },
        {
            "id": "09-demography", "topic": "demography", "n": "09",
            "family": PEOPLE,
            "title": ctx.text(
                it="L'inverno demografico",
                en="The Demographic Winter",
                pt="O inverno demográfico"),
            "blurb": ctx.text(
                it="Fecondità 1,18 figli per donna nel 2024, tra i valori "
                   "più bassi mai registrati in tempo di pace; più morti che "
                   "nati dal 2007, ogni anno da allora.",
                en="Fertility at 1.18 children per woman in 2024, among the "
                   "lowest ever recorded in peacetime; more deaths than "
                   "births in every year since 2007.",
                pt="Fecundidade de 1,18 filhos por mulher em 2024, entre os "
                   "mais baixos já registrados em tempo de paz; mais mortes "
                   "que nascimentos todo ano desde 2007."),
            "spark": ctx.col(pop, "tfr"),
            "spark_level": True,
            "stats": [
                ctx.stat({"it": "Figli per donna", "en": "Children per woman",
                          "pt": "Filhos por mulher"},
                         ctx.col(pop, "tfr"), "dec2"),
                ctx.stat({"it": "Tasso di mortalità",
                          "en": "Death rate (per 1,000)",
                          "pt": "Taxa de mortalidade (por 1.000)"},
                         _joined(ctx, pop, "deaths", pop, "population",
                                 1000.0), "dec2"),
                ctx.stat({"it": "Popolazione al 1° gennaio",
                          "en": "Population (1 January)",
                          "pt": "População (1º de janeiro)"},
                         [(y, v / 1e6) for y, v in
                          ctx.col(pop, "population")],
                         "pop_mn", kind="level"),
            ],
        },
        {
            "id": "10-security", "topic": "security", "n": "10",
            "family": PEOPLE,
            "title": ctx.text(
                it="Violenza",
                en="Violence",
                pt="Violência"),
            "blurb": ctx.text(
                it="Omicidi contati due volte — polizia e certificati — e "
                   "sempre in calo; i suicidi fermi da vent'anni; il delitto "
                   "di mafia in attesa che l'ISTAT riapra i suoi flussi.",
                en="Homicides counted twice — police and certificates — and "
                   "falling either way; suicides flat for two decades; the "
                   "mafia killing count waiting for ISTAT to open its "
                   "flows again.",
                pt="Homicídios contados duas vezes — polícia e certidões — "
                   "e sempre em queda; suicídios estáveis há duas décadas; "
                   "o registro mafioso à espera de o ISTAT reabrir seus "
                   "fluxos."),
            "spark": ctx.col("security/homicide_police.csv",
                             "intenhom"),
            "stats": [
                ctx.stat({"it": "Omicidi volontari (polizia)",
                          "en": "Intentional homicides (police)",
                          "pt": "Homicídios dolosos (polícia)"},
                         ctx.col("security/homicide_police.csv",
                                 "intenhom"), "count"),
                ctx.stat({"it": "Tasso di omicidi (polizia)",
                          "en": "Homicide rate (police)",
                          "pt": "Taxa de homicídios (polícia)"},
                         ctx.col("security/homicide_police.csv",
                                 "intenhom_per100k"), "per100k"),
                ctx.stat({"it": "Tasso di suicidi",
                          "en": "Suicide rate", "pt": "Taxa de suicídios"},
                         _per_pop(ctx, _causes(ctx, "17_2"), 1e5),
                         "per100k"),
            ],
        },
        {
            "id": "11-mortality", "topic": "mortality", "n": "11",
            "family": PEOPLE,
            "title": ctx.text(
                it="Mortalità — prima del tempo",
                en="Mortality — Old Before Their Time",
                pt="Mortalidade — antes da hora"),
            "blurb": ctx.text(
                it="Il tasso di mortalità che risale, l'eccesso del 2020 sul "
                   "2015–19, e i morti per COVID dai certificati — causa "
                   "iniziale, codice 20.",
                en="The climbing death rate, the 2020 excess over the "
                   "2015–19 average, and the certificate deaths with COVID "
                   "as underlying cause.",
                pt="A taxa de mortalidade em alta, o excesso de 2020 sobre "
                   "a média 2015–19 e as mortes com COVID como causa "
                   "básica nos certidões."),
            "spark": ctx.col(pop, "deaths"),
            "stats": [
                ctx.stat({"it": "Morti ogni 1.000",
                          "en": "Deaths per 1,000", "pt": "Mortes por 1.000"},
                         _joined(ctx, pop, "deaths", pop, "population",
                                 1000.0), "dec2"),
                ctx.stat({"it": "Morti per COVID (certificati, 2020–23)",
                          "en": "COVID-19 deaths (certificates, 2020–23)",
                          "pt": "Mortes por COVID (certidões, 2020–23)"},
                         _causes(ctx, "20"), "count", kind="total"),
                ctx.stat({"it": "Eccesso di mortalità 2020",
                          "en": "2020 excess deaths",
                          "pt": "Excesso de mortalidade em 2020"},
                         excess_2020, "pct_s", kind="level"),
            ],
        },
        {
            "id": "12-migration", "topic": "migration", "n": "12",
            "family": PEOPLE,
            "title": ctx.text(
                it="Migrazione — arrivi e cittadini che partono",
                en="Migration — Arrivals, and the Citizens Who Leave",
                pt="Migração — chegadas e cidadãos que partem"),
            "blurb": ctx.text(
                it="Un flusso di ingressi che coincide con Eurostat, e "
                   "l'emigrazione italiana che cresce dal 2015; le "
                   "cittadinanze acquisite come lente sul ricambio.",
                en="An arrivals flow that agrees with Eurostat, and an "
                   "Italian emigration that has been climbing since 2015; "
                   "acquired citizenships as the lens on the turnover.",
                pt="Um fluxo de entradas que bate com a Eurostat e uma "
                   "emigração italiana em alta desde 2015; as cidadanias "
                   "adquiridas como lente da troca."),
            "spark": ctx.col("migration/immigration.csv",
                             "by_citizenship_total"),
            "stats": [
                ctx.stat({"it": "Immigrati (cittadinanza)",
                          "en": "Immigrants (by citizenship)",
                          "pt": "Imigrantes (por cidadania)"},
                         ctx.col("migration/immigration.csv",
                                 "by_citizenship_total"), "count"),
                ctx.stat({"it": "Emigrati (cittadinanza)",
                          "en": "Emigrants (by citizenship)",
                          "pt": "Emigrantes (por cidadania)"},
                         ctx.col("migration/emigration.csv",
                                 "by_citizenship_total"), "count"),
                ctx.stat({"it": "Nuovi cittadini per naturalizzazione",
                          "en": "New citizens by naturalisation",
                          "pt": "Novos cidadãos por naturalização"},
                         ctx.col("migration/naturalisation.csv",
                                 "acquisitions"), "count"),
            ],
        },
    ]
    return chapters
