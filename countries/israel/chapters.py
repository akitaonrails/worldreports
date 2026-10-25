"""Israel's twelve page cards, computed from reviewed publication CSVs."""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def _scaled(ctx, path, column, divisor):
    return [(y, v / divisor) for y, v in ctx.col(path, column)]


def headline(ctx):
    T = ctx.text
    return [
        ctx.stat(T(he="תמ״ג, דולר", en="GDP", pt="PIB"),
                 _scaled(ctx, "international/world.csv", "gdp_usd", 1e9),
                 "usd_bn"),
        ctx.stat(T(he="תמ״ג לנפש, דולר", en="GDP per person, US$", pt="PIB por pessoa, US$"),
                 ctx.col("international/world.csv", "gdp_per_person_usd"), "count"),
        ctx.stat(T(he="אוכלוסייה", en="Population", pt="População"),
                 _scaled(ctx, "demography/demography.csv", "population", 1e6), "pop_mn", kind="level"),
        ctx.stat(T(he="ריבית בנק ישראל", en="Bank of Israel rate", pt="Taxa do Banco de Israel"),
                 ctx.col("markets/policy_rate.csv", "policy_rate_pct"), "pct2"),
        ctx.stat(T(he="חוב משקי הבית", en="Household debt", pt="Dívida das famílias"),
                 ctx.col("credit/household_debt.csv", "household_debt_pct_gdp"), "pct_gdp"),
        ctx.stat(T(he="עוני יחסי", en="Relative poverty", pt="Pobreza relativa"),
                 ctx.col("social/income_distribution.csv", "poverty50_pct_meth2012_current"), "pct"),
        ctx.stat(T(he="עולים חדשים", en="New olim", pt="Novos olim"),
                 ctx.col("migration/olim_flow.csv", "olim"), "count"),
    ]


def build(ctx):
    T = ctx.text
    specs = [
        ("01-economy", "economy", MONEY,
         T(he="המשק הישראלי", en="The Israeli Economy", pt="A Economia Israelense"),
         T(he="צמיחה, הכנסה, מחירים ותעסוקה בסדרות השוואתיות של קרן המטבע, הבנק העולמי ו־OECD.", en="Growth, income, prices and jobs in comparable IMF, World Bank and OECD series.", pt="Crescimento, renda, preços e emprego em séries comparáveis do FMI, Banco Mundial e OCDE."),
         T(he="ארבעה פאנלים לשנים 2006–2025. הצמיחה הריאלית שלילית רק ב־2020; התמ״ג לנפש עולה, האינפלציה מגיעה לשיא ב־2022 והאבטלה יורדת.", en="Four panels for 2006–2025. Real growth is negative only in 2020; GDP per person rises, inflation peaks in 2022 and unemployment declines.", pt="Quatro painéis para 2006–2025. O crescimento real só é negativo em 2020; o PIB por pessoa sobe, a inflação atinge o pico em 2022 e o desemprego recua."),
         "macro/gdp_growth.csv", "gdp_growth_pct", "pct_s",
         ["macro/gdp_growth.csv", "international/world.csv", "macro/cpi_inflation.csv", "macro/economy.csv", "social/labour.csv"]),
        ("02-fiscal", "fiscal", MONEY,
         T(he="כספי הציבור", en="Public Finances", pt="Finanças Públicas"),
         T(he="הכנסות, הוצאות, מאזן וחוב של הממשלה הכללית לפי אותה מהדורת Fiscal Monitor.", en="General-government revenue, spending, balances and debt from one IMF Fiscal Monitor vintage.", pt="Receitas, despesas, saldos e dívida do governo geral em uma mesma edição do Fiscal Monitor do FMI."),
         T(he="ארבעה פאנלים. הגירעון מתרחב ב־2020 ושוב ב־2024; החוב יורד עד 2019, מזנק ב־2020 ועולה שוב בשנות המלחמה.", en="Four panels. The deficit widens in 2020 and again in 2024; gross debt falls through 2019, jumps in 2020 and rises again during the war years.", pt="Quatro painéis. O déficit aumenta em 2020 e novamente em 2024; a dívida bruta cai até 2019, salta em 2020 e volta a subir nos anos de guerra."),
         "fiscal/general_government.csv", "gross_debt_pct_gdp", "pct_gdp",
         ["fiscal/general_government.csv"]),
        ("03-spending", "spending", MONEY,
         T(he="לאן הולך הכסף", en="Where the Money Goes", pt="Para Onde Vai o Dinheiro"),
         T(he="הוצאות הממשלה לפי תפקיד, לצד השקעה ציבורית והשקעה במשק כולו — מדדים שאינם בני החלפה.", en="Government spending by function beside public and whole-economy investment—measures that are not interchangeable.", pt="Despesa pública por função ao lado do investimento público e da economia inteira — medidas que não são intercambiáveis."),
         T(he="ארבעה פאנלים מציגים את סך ההוצאה, קבוצות תפקידים, השקעה ממשלתית והשקעה קבועה במשק כולו כאחוז מהתמ״ג.", en="Four panels show total spending, functional groups, government investment and economy-wide fixed investment as shares of GDP.", pt="Quatro painéis mostram despesa total, grupos funcionais, investimento do governo e investimento fixo da economia como parcelas do PIB."),
         "spending/cofog.csv", "total_pct_gdp", "pct_gdp",
         ["spending/cofog.csv", "spending/public_investment.csv", "spending/whole_economy_investment.csv"]),
        ("04-trade", "trade", WORLD,
         T(he="סחר", en="Trade", pt="Comércio"),
         T(he="סחר סחורות ושירותים בחשבונות הלאומיים לצד יעדי יצוא סחורות במכס — שני תחומי כיסוי נפרדים.", en="National-accounts goods and services beside customs-goods destinations—two distinct coverage concepts.", pt="Bens e serviços das contas nacionais ao lado de destinos aduaneiros de bens — dois conceitos de cobertura distintos."),
         T(he="ארבעה פאנלים. היצוא והיבוא נעים סביב שליש מהתמ״ג; סדרת היעדים השנתית בהמתנה, ועדשת 2023 משתמשת ב־UN Comtrade ללא קטגוריה 837.", en="Four panels. Exports and imports run near a third of GDP; the annual destination series is pending, while the 2023 lens uses UN Comtrade customs-goods exports excluding category 837.", pt="Quatro painéis. Exportações e importações ficam perto de um terço do PIB; a série anual de destinos está pendente, enquanto a lente de 2023 usa o UN Comtrade, excluída a categoria 837."),
         "trade/trade.csv", "exports_pct_gdp", "pct_gdp",
         ["trade/trade.csv", "trade/trade_partners_comtrade.csv"]),
        ("05-markets", "markets", MONEY,
         T(he="כסף ושווקים", en="Money & Markets", pt="Moeda e Mercados"),
         T(he="ריבית בנק ישראל, תשואת האג״ח הממשלתית ל־8–11 שנים, השקל ומניות תל אביב בדולרים.", en="The Bank of Israel rate, the 8–11-year government-bond yield, the shekel and Tel Aviv equities in US dollars.", pt="A taxa do Banco de Israel, o rendimento do título público de 8–11 anos, o shekel e as ações de Tel Aviv em dólares."),
         T(he="ארבעה פאנלים לשנים 2006–2025. הריבית והתשואה הן ממוצעים שנתיים; מדד השקל מבוסס על ממוצע השער, ות״א־125 מוצג בדולרים מול S&P 500.", en="Four panels for 2006–2025. The policy rate and 8–11-year yield are annual averages; the shekel index uses annual exchange-rate averages, and the TA-125 is shown in US dollars against the S&P 500.", pt="Quatro painéis para 2006–2025. A taxa básica e o rendimento de 8–11 anos são médias anuais; o índice do shekel usa médias cambiais e o TA-125 aparece em dólares contra o S&P 500."),
         "markets/policy_rate.csv", "policy_rate_pct", "pct2",
         ["markets/policy_rate.csv", "markets/government_bond_10y.csv", "markets/usdils.csv", "markets/usdils_boi.csv", "markets/ta125.csv", "markets/sp500.csv"]),
        ("06-credit", "credit", MONEY,
         T(he="אשראי למשקי בית", en="Household Credit", pt="Crédito às Famílias"),
         T(he="חוב משקי הבית, ריבית על משכנתאות חדשות והלוואות לא־מתפקדות — כל מדד בהגדרתו.", en="Household debt, rates on new mortgages and non-performing loans—each kept on its own definition.", pt="Dívida das famílias, taxas de novas hipotecas e empréstimos inadimplentes — cada medida em sua definição."),
         T(he="שלושה פאנלים: מלאי חוב חלקי תמ״ג; ריבית משוקללת על הלוואות דיור חדשות ולא־צמודות; ושיעור הלוואות לא־מתפקדות ברבעון הרביעי.", en="Three panels: household debt stock divided by GDP; weighted rates on new unindexed housing loans; and the fourth-quarter NPL ratio for deposit takers.", pt="Três painéis: estoque de dívida familiar dividido pelo PIB; taxas ponderadas de novos financiamentos habitacionais não indexados; e inadimplência no quarto trimestre."),
         "credit/household_debt.csv", "household_debt_pct_gdp", "pct_gdp",
         ["credit/household_debt.csv", "credit/mortgage_rate.csv", "credit/npl_ratio.csv"]),
        ("07-people", "people", PEOPLE,
         T(he="אנשים, הכנסה ועוני", en="People, Income & Poverty", pt="Pessoas, Renda e Pobreza"),
         T(he="אי־שוויון ועוני של OECD לצד שכר המינימום הסטטוטורי; מקטעי השיטה אינם מחוברים.", en="OECD inequality and poverty beside the statutory minimum wage; method segments are not spliced.", pt="Desigualdade e pobreza da OCDE ao lado do salário mínimo legal; segmentos metodológicos não são unidos."),
         T(he="ארבעה פאנלים. ג׳יני ועוני מוצגים בשלושה מקטעי שיטה נפרדים; שכר המינימום הוא ממוצע חודשי משוקלל לפי מועדי התחולה.", en="Four panels. Gini and poverty appear as three separate method segments; the minimum wage is a month-weighted statutory average.", pt="Quatro painéis. Gini e pobreza aparecem em três segmentos metodológicos separados; o salário mínimo é uma média legal ponderada pelos meses."),
         "social/income_distribution.csv", "poverty50_pct_meth2012_current", "pct",
         ["social/income_distribution.csv", "social/minimum_wage.csv"]),
        ("08-world", "world", WORLD,
         T(he="ישראל בעולם", en="Israel in the World", pt="Israel no Mundo"),
         T(he="גודל כלכלי ורזרבות בדולרים, פיתוח אנושי ותפיסת שחיתות בהגדרות בין־לאומיות.", en="Economic size and reserves in US dollars, human development and perceived corruption on international definitions.", pt="Tamanho econômico e reservas em dólares, desenvolvimento humano e percepção de corrupção em definições internacionais."),
         T(he="ארבעה פאנלים. התמ״ג והרזרבות עולים; מדד הפיתוח האנושי מגיע ל־0.919 ב־2023, ומדד תפיסת השחיתות מוצג בסולם 0–100.", en="Four panels. GDP and reserves rise; HDI reaches 0.919 in 2023, and the Corruption Perceptions Index is shown on its 0–100 scale.", pt="Quatro painéis. PIB e reservas sobem; o IDH chega a 0,919 em 2023 e o Índice de Percepção da Corrupção aparece na escala 0–100."),
         "international/hdi.csv", "hdi", "dec3",
         ["international/world.csv", "international/hdi.csv", "international/cpi_ti.csv"]),
        ("09-demography", "demography", PEOPLE,
         T(he="דמוגרפיה", en="Demography", pt="Demografia"),
         T(he="אוכלוסייה, פריון, לידות, פטירות וגידול טבעי בסדרת הבנק העולמי המבוססת על UN WPP.", en="Population, fertility, births, deaths and natural increase in the World Bank series based on UN WPP.", pt="População, fecundidade, nascimentos, óbitos e crescimento natural na série do Banco Mundial baseada no UN WPP."),
         T(he="ארבעה פאנלים. האוכלוסייה גדלה לכעשרה מיליון; הפריון קרוב לשלושה ילדים לאישה; הילודה יורדת והתמותה עולה.", en="Four panels. Population grows to about ten million; fertility remains near three children per woman; the birth rate falls and the death rate rises.", pt="Quatro painéis. A população cresce para cerca de dez milhões; a fecundidade fica perto de três filhos por mulher; a natalidade cai e a mortalidade sobe."),
         "demography/demography.csv", "fertility", "dec2",
         ["demography/demography.csv"]),
        ("10-security", "security", PEOPLE,
         T(he="ביטחון ובטיחות", en="Security & Safety", pt="Segurança Pública"),
         T(he="שיעורי תמותה מ־UNODC ו־WHO לצד מקרי המתה שתועדו במשטרת ישראל — מדדים נפרדים.", en="UNODC and WHO mortality rates beside homicide cases recorded by Israel Police—separate measures.", pt="Taxas de mortalidade da UNODC e OMS ao lado de casos de homicídio registrados pela Polícia de Israel — medidas separadas."),
         T(he="ארבעה פאנלים. שיעורי המתה, התאבדות ותמותה בדרכים מוצגים בנפרד ממקרי המתה שתועדו במשטרת ישראל. הזינוק ב־2023 כולל את מתקפת 7 באוקטובר בסיווג הטכני 301.", en="Four panels. Homicide, suicide and road-death rates remain separate from homicide cases recorded by Israel Police. The 2023 spike includes the 7 October attack within technical category 301.", pt="Quatro painéis. Taxas de homicídio, suicídio e mortes no trânsito ficam separadas dos casos de homicídio registrados pela Polícia de Israel. O salto de 2023 inclui o ataque de 7 de outubro na categoria técnica 301."),
         "security/security.csv", "homicide_per_100k", "per100k2",
         ["security/security.csv", "security/homicide_police.csv"]),
        ("11-mortality", "mortality", PEOPLE,
         T(he="תמותה", en="Mortality", pt="Mortalidade"),
         T(he="פטירות רשומות, עודף מול ממוצע 2015–2019 וסיבות המוות הבסיסיות לפי OECD/WHO.", en="Registered deaths, excess against the 2015–2019 mean and underlying causes from OECD/WHO.", pt="Óbitos registrados, excesso contra a média de 2015–2019 e causas básicas da OCDE/OMS."),
         T(he="ארבעה פאנלים עד 2023 מציגים פטירות ושיעור גולמי, עודף מול בסיס קבוע, COVID-19 כסיבה בסיסית ושיעורי סרטן ומחלות מחזור הדם.", en="Four panels through 2023 show deaths and the crude rate, excess against a fixed baseline, COVID-19 as the underlying cause, and cancer and circulatory-disease rates.", pt="Quatro painéis até 2023 mostram óbitos e taxa bruta, excesso contra uma base fixa, COVID-19 como causa básica e taxas de câncer e doenças circulatórias."),
         "mortality/mortality.csv", "death_rate_per_1000", "dec2",
         ["mortality/mortality.csv"]),
        ("12-migration", "migration", PEOPLE,
         T(he="הגירה", en="Migration", pt="Migração"),
         T(he="זרמי ההגירה ההשוואתיים חסרים; אומדן נטו, מלאי ילידי חו״ל, עולים ורישומי היתרים נשארים מושגים נפרדים.", en="Comparable gross flows are pending; estimated net migration, foreign-born stock, olim and permit records remain distinct.", pt="Os fluxos brutos comparáveis estão pendentes; migração líquida estimada, estoque de nascidos no exterior, olim e registros de autorizações permanecem distintos."),
         T(he="ארבעה פאנלים. הזרם הגולמי ההשוואתי מסומן כחסר; אומדן האו״ם נשאר נפרד; חלק ילידי החוץ משתמש בשנות תמונת מצב; והעדשה מפרידה בין עולים לרישומי היתרים.", en="Four panels. Comparable gross flows are visibly pending; the UN estimate remains separate; foreign-born share uses snapshot years; and the lens separates olim from permit records.", pt="Quatro painéis. Os fluxos brutos comparáveis aparecem como pendentes; a estimativa da ONU fica separada; a parcela de nascidos no exterior usa anos de referência; e a lente separa olim de registros de autorizações."),
         "migration/olim_flow.csv", "olim", "count",
         ["migration/olim_flow.csv", "demography/demography.csv", "migration/migrant_stock_wb.csv", "migration/permits.csv"]),
    ]
    out = []
    for ident, topic, family, title, blurb, alt, path, column, fmt, sources in specs:
        pairs = ctx.col(path, column)
        out.append({"id": ident, "topic": topic, "n": ident[:2], "family": family,
                    "title": title, "blurb": blurb, "alt": alt, "spark": pairs,
                    "stats": [ctx.stat(title, pairs, fmt)], "sources": sources})
    return out
