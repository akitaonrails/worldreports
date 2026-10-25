"""Cards and headline figures for Switzerland's twelve spine chapters."""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def _bn(series, divisor=1_000):
    return [(y, v / divisor) for y, v in series]


def headline(ctx):
    return [
        ctx.stat({"de": "BIP", "en": "GDP", "pt": "PIB"},
                 _bn(ctx.col("international/gdp_usd_wb.csv", "gdp_usd"),
                     1_000_000_000), "usd_bn"),
        ctx.stat({"de": "BIP pro Person, US$", "en": "GDP per person, US$", "pt": "PIB por pessoa, US$"},
                 ctx.col("international/gdp_pc_wb.csv", "gdp_per_person_usd"), "count"),
        ctx.stat({"de": "Bevölkerung", "en": "Population", "pt": "População"},
                 _bn(ctx.col("demography/balance_bfs.csv", "pop_31dec"), 1_000_000), "pop_mn", kind="level"),
        ctx.stat({"de": "Reales Wachstum", "en": "Real growth", "pt": "Crescimento real"},
                 ctx.col("macro/gdp_bfs.csv", "gdp_real_growth_pct"), "pct_s"),
        ctx.stat({"de": "Teuerung", "en": "Inflation", "pt": "Inflação"},
                 ctx.col("macro/cpi_bfs.csv", "cpi_inflation_pct"), "pct"),
        ctx.stat({"de": "Arbeitslosigkeit", "en": "Unemployment", "pt": "Desemprego"},
                 ctx.col("macro/unemployment_rate_bfs.csv", "ilo_rate_annual_pct"), "pct", kind="level"),
        ctx.stat({"de": "Staatsverschuldung", "en": "Government debt", "pt": "Dívida pública"},
                 ctx.col("international/gg_debt_imf.csv", "gross_debt_pct_gdp"), "pct_gdp", kind="level"),
    ]


COPY = {
"economy": ({"de":"Die Wirtschaft","en":"The Economy","pt":"A Economia"},
 {"de":"Wachstum, Preise und Arbeit bleiben stabil, während Dollarwerte auch den starken Franken abbilden.","en":"Growth, prices and work remain stable, while dollar readings also carry the strong franc.","pt":"Crescimento, preços e trabalho seguem estáveis, enquanto as leituras em dólar também refletem o franco forte."}),
"fiscal": ({"de":"Öffentliche Finanzen","en":"Public Finances","pt":"Contas Públicas"},
 {"de":"Vier amtliche Schuldenbegriffe werden getrennt; der Primärsaldo wird aus einer Eurostat-Vintage berechnet.","en":"Four official debt concepts stay separate; the primary balance is computed within one Eurostat vintage.","pt":"Quatro conceitos oficiais de dívida ficam separados; o saldo primário é calculado numa única edição do Eurostat."}),
"spending": ({"de":"Wohin das Geld fliesst","en":"Where the Money Goes","pt":"Para Onde Vai o Dinheiro"},
 {"de":"Die Staatsrechnung lässt obligatorische Krankenversicherung und berufliche Vorsorge ausserhalb des Staates.","en":"The government account leaves compulsory health insurance and occupational pensions outside government.","pt":"A conta do governo deixa o seguro-saúde obrigatório e a previdência ocupacional fora do governo."}),
"trade": ({"de":"Aussenhandel","en":"Trade","pt":"Comércio"},
 {"de":"Gold verändert das Handelstotal; Total 1, Total 2 und Gold werden nie als dieselbe Reihe behandelt.","en":"Gold changes the trade total; Total 1, Total 2 and gold are never treated as one series.","pt":"O ouro muda o total comercial; Total 1, Total 2 e ouro nunca são tratados como uma única série."}),
"markets": ({"de":"Geld und Märkte","en":"Money and Markets","pt":"Dinheiro e Mercados"},
 {"de":"Negativzinsen, der starke Franken und der SMI erzählen dieselbe Ära aus drei Blickwinkeln.","en":"Negative rates, the strong franc and the SMI tell the same era from three angles.","pt":"Juros negativos, o franco forte e o SMI contam a mesma era por três ângulos."}),
"credit": ({"de":"Kredite","en":"Credit","pt":"Crédito"},
 {"de":"BIZ-Haushaltskredite, Hypothekarzinsen und Bank-NPL bleiben nach Definition getrennt.","en":"BIS household credit, mortgage rates and bank NPLs remain separate by definition.","pt":"Crédito domiciliar do BIS, juros hipotecários e NPL bancário permanecem separados por definição."}),
"people": ({"de":"Menschen","en":"People","pt":"Pessoas"},
 {"de":"Ungleichheit und Armut werden nach mehreren amtlichen Definitionen gezeigt; einen nationalen Mindestlohn gibt es nicht.","en":"Inequality and poverty appear under several official definitions; there is no national minimum wage.","pt":"Desigualdade e pobreza aparecem sob várias definições oficiais; não há salário mínimo nacional."}),
"world": ({"de":"Die Schweiz in der Welt","en":"Switzerland in the World","pt":"A Suíça no Mundo"},
 {"de":"Ein sehr hohes Pro-Kopf-Einkommen steht neben HDI, Korruptionsindex und aussergewöhnlich grossen Reserven.","en":"Very high income per person sits beside HDI, the corruption index and exceptionally large reserves.","pt":"Uma renda por pessoa muito alta aparece ao lado do IDH, do índice de corrupção e de reservas excepcionais."}),
"demography": ({"de":"Demografie","en":"Demography","pt":"Demografia"},
 {"de":"Tiefe Fertilität und negative natürliche Bilanz treffen auf anhaltend positive Nettomigration.","en":"Low fertility and negative natural change meet persistently positive net migration.","pt":"Baixa fecundidade e saldo natural negativo encontram migração líquida persistentemente positiva."}),
"security": ({"de":"Sicherheit","en":"Security","pt":"Segurança"},
 {"de":"Tötungen und Verkehrstote sind selten; der Suizidbruch 2009 ist eine Klassifikationsänderung.","en":"Homicide and road deaths are rare; the 2009 suicide break is a classification change.","pt":"Homicídios e mortes no trânsito são raros; a ruptura de suicídio em 2009 é uma mudança de classificação."}),
"mortality": ({"de":"Sterblichkeit","en":"Mortality","pt":"Mortalidade"},
 {"de":"Pandemie und Alterung stehen auf einer festen Vorkrisenbasis, mit Ursachen getrennt ausgewiesen.","en":"The pandemic and ageing sit on a fixed pre-crisis baseline, with causes kept separate.","pt":"A pandemia e o envelhecimento aparecem sobre uma base fixa pré-crise, com causas mantidas separadas."}),
"migration": ({"de":"Migration","en":"Migration","pt":"Migração"},
 {"de":"Statuswechsel gehören zur BFS-Einwanderung; Asylflüsse, S-Bestand und Einbürgerungen bleiben verschieden.","en":"Status changes belong to BFS immigration; asylum flows, the S-status stock and citizenship stay distinct.","pt":"Mudanças de status entram na imigração do BFS; fluxos de asilo, estoque S e cidadania ficam distintos."}),
}


SERIES = {
"economy": ("macro/gdp_bfs.csv", "gdp_real_growth_pct", "pct_s"),
"fiscal": ("fiscal/general_government_estat.csv", "balance_pct_gdp", "pct_gdp"),
"spending": ("fiscal/spending_by_function_estat.csv", "total", "pct_gdp"),
"trade": ("trade/current_account_snb.csv", "ca_balance", "money_bn"),
"markets": ("markets/smi_yahoo.csv", "close", "count"),
"credit": ("credit/household_credit_bis.csv", "household_credit_pct_gdp_q4", "pct_gdp"),
"people": ("social/gini_estat.csv", "gini", "count"),
"world": ("international/gdp_usd_wb.csv", "gdp_usd", "usd_bn"),
"demography": ("demography/fertility_bfs.csv", "tfr", "dec2"),
"security": ("security/homicide_police_bfs.csv", "homicide_completed_per_100k", "per100k"),
"mortality": ("demography/balance_bfs.csv", "deaths", "count"),
"migration": ("migration/flows_bfs.csv", "net_total", "count"),
}


def build(ctx):
    out = []
    families = [MONEY, MONEY, MONEY, WORLD, MONEY, MONEY, PEOPLE, WORLD, PEOPLE, PEOPLE, PEOPLE, PEOPLE]
    for i, (topic, family) in enumerate(zip(COPY, families), 1):
        title, blurb = COPY[topic]
        rel, col, spec = SERIES[topic]
        series = ctx.col(rel, col)
        if topic == "trade": series = _bn(series)
        if topic == "world": series = _bn(series, 1_000_000_000)
        out.append({"id": f"{i:02d}-{topic}", "topic": topic, "n": f"{i:02d}",
                    "family": family, "title": ctx.text(**title),
                    "blurb": ctx.text(**blurb), "spark": series,
                    "stats": [ctx.stat(title, series, spec)]})
    return out
