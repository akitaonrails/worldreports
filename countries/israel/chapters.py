"""The Israel chapters: the cards, their copy and their provenance.

Every chapter declares its spine topic (PLATE_SPINE.md); the card's stem
must match the plate file, so the comparison viewer finds 01-economy.png
under chapter id 01-economy. `alt` is written prose about what the plate
shows — the only thing a reader using a screen reader gets.

Four spine chapters (spending, people, credit, mortality) are not here
yet: no series for them is staged (SOURCES.yaml meta.pending), and a
chapter of pending panels is worse than no chapter — DATA_NOTES.md keeps
the decision honest. The he copy is the reader's language, not a
back-translation; the RTL page work itself is Phase C.
"""
from __future__ import annotations

MONEY, WORLD, PEOPLE = "money", "world", "people"


def build(ctx) -> list[dict]:
    T = ctx.text
    return [
        {
            "id": "01-economy", "topic": "economy", "n": "01",
            "family": MONEY,
            "title": T(
                he="המשק הישראלי — צמיחה, הכנסה, מחירים ותעסוקה",
                en="The Israeli Economy — Growth, Income, Prices and Jobs",
                pt="A Economia Israelense — Crescimento, Renda, Preços e Emprego"),
            "blurb": T(
                he="גירסת שנתית אחת של קרן המטבע ושל הבנק העולמי מציגה שנת "
                   "היצגבות אחת בלבד — 2020. שנות המלחמה בולטות בהסברים, לא "
                   "בפסי הכנסה.",
                en="One annual vintage shows exactly one contraction year — "
                   "2020. The war years are told as events, not recession bands.",
                pt="Uma única safra anual mostra exatamente um ano de "
                   "contração — 2020. Os anos de guerra são eventos, não faixas de recessão."),
            "alt": T(
                he="ארבעה פאנלים על הכלכלה הישראלית, 2006–2025. הצמיחה "
                   "הריאלית חיובית בכל שנה מלבד 2020 ‎(-1.9%)‎; ב-2008 וב-2009, "
                   "שנות המשבר העולמי, צמחה המשק ב-3.2% וב-1.2%, ולכן אין פס "
                   "הכנסה. תל\"ג לנפש בדולרים עלה מ-22,500 ל-60,300 בערך. "
                   "האינפלציה נגעה בדפלציה באמצע שנות ה-2010 והגיעה ל-4.4% "
                   "ב-2022 מול יעד של 1%–3%; האבטלה ירדה מ-8.4% לכ-3%. "
                   "המקורות בינלאומיים עד שהלמ\"ס יחזור.",
                en="Four panels on the Israeli economy, 2006–2025. Real "
                   "growth is positive every year except 2020 (-1.9%); the "
                   "crisis years 2008 and 2009 grew +3.2% and +1.2%, so no "
                   "band. GDP per person in US$ rose from about 22,500 to "
                   "60,300. Inflation touched deflation in the mid-2010s and "
                   "peaked at 4.4% in 2022 against the 1–3% target; "
                   "unemployment fell from 8.4% to about 3%.",
                pt="Quatro painéis sobre a economia israelense, 2006–2025. "
                   "O crescimento real é positivo em todos os anos menos "
                   "2020 (-1,9%); os anos de crise 2008 e 2009 cresceram "
                   "+3,2% e +1,2%, sem faixa. O PIB por pessoa em dólares "
                   "subiu de cerca de 22.500 para 60.300. A inflação roçou a "
                   "deflação em meados dos anos 2010 e atingiu 4,4% em 2022 "
                   "contra a meta de 1–3%; o desemprego caiu de 8,4% para "
                   "cerca de 3%."),
            "sources": ["macro/gdp_growth_from_imf.csv",
                        "international/world_from_wb.csv",
                        "macro/cpi_inflation_from_imf.csv",
                        "macro/economy_from_wb.csv",
                        "social/labour_from_oecd.csv"],
        },
        {
            "id": "02-fiscal", "topic": "fiscal", "n": "02", "family": MONEY,
            "title": T(
                he="פיסקליות — הנפילה הארוכה בחוב, ושנות המלחמה",
                en="Public Finances — the Long Fall in Debt, and the War Years",
                pt="Finanças Públicas — a Longa Queda da Dívida e os Anos de Guerra"),
            "blurb": T(
                he="הממשלות הכלליות לפי קרן המטבע. המלחמה נראית בגרעון ובחוב "
                   "— לא בפס צמיחה, כי הצמיחה השנתית נשארה חיובית.",
                en="General government on the IMF's basis. The war shows in "
                   "the balance and the debt, not in a growth band, because "
                   "annual growth stayed positive.",
                pt="Governo geral na base do FMI. A guerra aparece no "
                   "saldo e na dívida, não numa faixa de crescimento: o "
                   "crescimento anual ficou positivo."),
            "alt": T(
                he="ארבעה פאנלים על הפיסקליות הישראלית. ההכנסות 35%–40% מהתמ\"ג "
                   "וההוצאות 37%–45%; הגרעון הגיע ל-10.7%- ב-2020 ול-8.1%- "
                   "ב-2024, שנת המלחמה; החוב הגולמי ירד מ-85.7% ב-2005 ל-59.5% "
                   "ב-2019, זינק ל-71.4% ב-2020 וניצב ב-67.9% ב-2025. המאזן "
                   "הראשוני והריבית הנגזרת משתמשים באותה מהדורת Fiscal Monitor.",
                en="Four panels on Israeli public finances. Revenue runs "
                   "35–40% of GDP and expenditure 37–45%; the balance hits "
                   "-10.7% in 2020 and -8.1% in 2024, the war year; gross "
                   "debt falls from 85.7% (2005) to 59.5% (2019), jumps to "
                   "71.4% (2020) and sits at 67.9% in 2025. The primary "
                   "balance and derived interest use the same Fiscal Monitor vintage.",
                pt="Quatro painéis sobre as finanças públicas de Israel. "
                   "Receitas de 35–40% do PIB e despesas de 37–45%; o saldo "
                   "chega a -10,7% em 2020 e -8,1% em 2024, o ano de guerra; "
                   "a dívida bruta cai de 85,7% (2005) a 59,5% (2019), salta "
                   "a 71,4% (2020) e fica em 67,9% em 2025. O resultado "
                   "primário e os juros derivados usam a mesma edição do Fiscal Monitor."),
            "sources": ["fiscal/general_government.csv"],
        },
        {
            "id": "03-trade", "topic": "trade", "n": "03", "family": WORLD,
            "title": T(
                he="מסחר — עודף שירותים שנושא גרעון סחורות",
                en="Trade — a Services Surplus Carrying a Goods Deficit",
                pt="Comércio — um Superávit de Serviços Carregando um Déficit de Bens"),
            "blurb": T(
                he="יצוא ויבוא לפי חשבונות לאומיים בבנק העולמי; קו הלמ\"ס "
                   "הארצי יחזור עם הלמ\"ס.",
                en="Exports and imports on the World Bank's national-accounts "
                   "basis; the CBS national line returns with CBS.",
                pt="Exportações e importações pela base de contas nacionais "
                   "do Banco Mundial; a linha nacional do CBS volta com o CBS."),
            "alt": T(
                he="שלושה פאנלים מצוירים. יצוא ויבוא כל אחד "
                   "בכ-שליש מהתמ\"ג ומעלה, והמאזן נע בין ‎-3%‎ ל-‎+5%‎; פאנל "
                   "יעדי 2023 משתמש ביצוא סחורות המכס של UN Comtrade ומחריג את קטגוריה 837.",
                en="Three panels drawn. Exports and "
                   "imports each run a third of GDP or more and the balance "
                   "swings between about -3% and +5%; the 2023 destinations "
                   "use UN Comtrade customs-goods exports and exclude special category 837.",
                pt="Três painéis desenhados. "
                   "Exportações e importações passam de um terço do PIB cada, "
                   "e o saldo oscila entre cerca de -3% e +5%; os destinos de "
                   "2023 usam bens alfandegários do UN Comtrade e excluem a categoria especial 837."),
            "sources": ["trade/trade_from_wb.csv",
                        "trade/trade_partners_comtrade.csv"],
        },
        {
            "id": "04-markets", "topic": "markets", "n": "04",
            "family": MONEY,
            "title": T(
                he="שווקים — השקל והבורסה בתל אביב",
                en="Markets — the Shekel and the Tel Aviv Exchange",
                pt="Mercados — o Shekel e a Bolsa de Tel Aviv"),
            "blurb": T(
                he="שני פאנלים מושהים עד שבנק ישראל נגיש: הריבית והתשואות. "
                   "קו המט\"ח רוכב על הממוצעים השנתיים של הבנק העולמי.",
                en="Two panels pending while the Bank of Israel portal stays "
                   "unreachable: the rates and the yields. The FX line rides "
                   "the World Bank's annual averages.",
                pt="Dois painéis pendentes enquanto o portal do Banco de "
                   "Israel permanece inacessível: juros e rendimentos. A "
                   "linha de câmbio usa as médias anuais do Banco Mundial."),
            "alt": T(
                he="ארבעה פאנלים על השווקים בישראל. פאנלי הריבית ותשואת "
                   "האג\"ח מציינים שהמקור חסום; השקל, עם מדד בסיס 2006, התחזק "
                   "לכ-129 עד 2025 לפי הממוצעים הרשמיים של הבנק העולמי, ותמונת "
                   "השער היציג של בנק ישראל מצוטטת כצילום־מצב מתויג; "
                   "בדולרים מדד ת\"א־125 מגיע לכ-510 מול מדד S&P 500 "
                   "שעומד על כ-483.",
                en="Four panels on Israeli markets. The policy-rate and bond-"
                   "yield panels say their sources are parked; the shekel, "
                   "indexed 2006 = 100, strengthened to about 129 by 2025 on "
                   "the World Bank's official annual averages, with the Bank "
                   "of Israel's intraday representative rate quoted as a "
                   "labelled snapshot; in US$ the TA-125 index reaches about "
                   "510 against the S&P 500's 483.",
                pt="Quatro painéis sobre os mercados israelenses. Os painéis "
                   "de juro e de rendimento de títulos dizem que suas fontes "
                   "estão arquivadas; o shekel, indexado em 2006 = 100, se "
                   "fortaleceu para cerca de 129 até 2025 pelas médias anuais "
                   "oficiais do Banco Mundial, com a taxa representativa "
                   "intraday do Banco de Israel citada como retrato rotulado; "
                   "em dólares o índice TA-125 chega a cerca de 510 contra "
                   "483 do S&P 500."),
            "sources": ["markets/usdils_from_wb.csv", "markets/usdils_from_boi.csv",
                        "markets/ta125_from_yahoo.csv",
                        "markets/sp500_from_yahoo.csv"],
        },
        {
            "id": "05-world", "topic": "world", "n": "05", "family": WORLD,
            "title": T(
                he="ישראל בעולם — גודל, פיתוח ורזרבות",
                en="Israel in the World — Size, Development and Reserves",
                pt="Israel no Mundo — Tamanho, Desenvolvimento e Reservas"),
            "blurb": T(
                he="תמ\"ג ורזרבות בדולרים, מדד הפיתוח של UNDP ומדד השחיתות בר-ההשוואה של Transparency International.",
                en="GDP and reserves in US dollars, UNDP development and "
                   "Transparency International's comparable CPI.",
                pt="PIB e reservas em dólares, desenvolvimento do PNUD e o "
                   "CPI comparável da Transparency International."),
            "alt": T(
                he="ארבעה פאנלים מצוירים. התמ\"ג בדולרים עלה מ-159 "
                   "מיליארד ל-611 מיליארד; מדד הפיתוח האנושי טפס מ-0.867 "
                   "ל-0.919 (2023, דירוג 27); הרזרבות הרשמיות עלו מ-29 ל-229 "
                   "מיליארד דולר; מדד השחיתות נע מ-60 ב-2012 ל-62 ב-2025.",
                en="Four panels drawn. GDP in US dollars rises from "
                   "about 159bn to 611bn; the Human Development Index climbs "
                   "from 0.867 to 0.919 (2023, rank 27); official reserves "
                   "climb from about 29bn to 229bn dollars; the CPI runs "
                   "from 60 in 2012 to 62 in 2025.",
                pt="Quatro painéis desenhados. O PIB em dólares sobe "
                   "de cerca de 159 bilhões para 611 bilhões; o IDH sobe de "
                   "0,867 para 0,919 (2023, posição 27); as reservas oficiais "
                   "sobem de cerca de 29 para 229 bilhões de dólares; o CPI "
                   "vai de 60 em 2012 a 62 em 2025."),
            "sources": ["international/world_from_wb.csv",
                        "international/hdi_from_undp.csv",
                        "international/cpi_ti.csv"],
        },
        {
            "id": "06-demography", "topic": "demography", "n": "06",
            "family": PEOPLE,
            "title": T(
                he="דמוגרפיה — עשרה מיליון, ופריון ילודה מהגבוהים ב-OECD",
                en="Demography — Ten Million, and the OECD's Highest Fertility",
                pt="Demografia — Dez Milhões e a Mais Alta Fertilidade da OCDE"),
            "blurb": T(
                he="נתוני הבנק העולמי (UN WPP) עד שמרשם האוכלוסין של הלמ\"ס, "
                   "מתפרסם בראש השנה, יהיה שוב נגיש.",
                en="World Bank (UN WPP) while the CBS population register — "
                   "published each Rosh Hashanah — is unreachable.",
                pt="Banco Mundial (UN WPP) enquanto o registro populacional "
                   "do CBS — publicado a cada Rosh Hashaná — está inacessível."),
            "alt": T(
                he="ארבעה פאנלים על האוכלוסייה בישראל. מדד 2006=100 טפס לכ-144 "
                   "עד 2025 — התושב העשירי במיליון נרשם ב-2024, והפאנל נושא את "
                   "סימון \"הסקלה הורחבה\"; הפריון נע בין 2.84 ל-3.11 ילדים "
                   "לאישה; לידות גולמיות ירדו מ-21.0 ל-18.6 והתמותה עלתה לכ-5.3 "
                   "לכל 1,000; תוספת טבעית כ-13 ל-1,000, וקו ההגירה נטה של ה-UN "
                   "מתחתיה.",
                en="Four panels on Israel's population. The index 2006 = 100 "
                   "runs to about 144 by 2025 — the ten-millionth resident "
                   "was registered in 2024, and the panel carries the scale-"
                   "extended marker; fertility stays between 2.84 and 3.11 "
                   "children per woman; crude births fall from 21.0 to 18.6 "
                   "while deaths rise toward 5.3 per 1,000; natural increase "
                   "sits near 13 per 1,000, above the UN net-migration line.",
                pt="Quatro painéis sobre a população de Israel. O índice "
                   "2006 = 100 sobe para cerca de 144 em 2025 — o décimo "
                   "milionésimo residente foi registrado em 2024, e o painel "
                   "traz o marcador de escala ampliada; a fertilidade fica "
                   "entre 2,84 e 3,11 filhos por mulher; nascimentos brutos "
                   "caem de 21,0 para 18,6 e óbitos sobem para perto de 5,3 "
                   "por mil; o aumento natural fica perto de 13 por mil, "
                   "acima da linha de migração líquida da ONU."),
            "sources": ["demography/demography_from_wb.csv"],
        },
        {
            "id": "07-security", "topic": "security", "n": "07",
            "family": PEOPLE,
            "title": T(
                he="ביטחון — שני רישומי רצח, וקבצי ה-7 באוקטובר",
                en="Security — Two Homicide Records, and the 7 October Files",
                pt="Segurança — Dois Registros de Homicídio e os Arquivos de 7 de Outubro"),
            "blurb": T(
                he="שיעורי UNODC ממלאים את 2006–2020; חלון הנתונים הפתוח של "
                   "המשטרה נפתח ב-2021. שני טורים, לעולם לא קו אחד תפור.",
                en="UNODC rates fill 2006–2020; the police open-data window "
                   "opens in 2021. Two series, never one spliced line.",
                pt="Taxas da UNODC preenchem 2006–2020; a janela de dados "
                   "abertos da polícia abre em 2021. Duas séries, nunca uma "
                   "linha costurada."),
            "alt": T(
                he="ארבעה פאנלים על מוות אלימה ותאונות. בפאנל הרצח (סקלה לוג) "
                   "שיעור UNODC נע סביב 1.3–2.2 ל-100,000, וקבצי 301 של המשטרה "
                   "לכל 100,000 תושבים מתחילים ב-2021 בלבד וקופצים לכ-12.3 ב-2023, "
                   "שנת ה-7 באוקטובר; האבדות בדרכים יורדות מ-6.4 ל-3.4 לפני "
                   "שסדרת WHO נעצרת; פאנל השפתון סופר את קבצי הרצח עצמם — 156, "
                   "112, 1,209, 458, 345 — וקובע שעמודת 2023 היא הטבח שנספר "
                   "בתוך סוג 301.",
                en="Four panels on violent and accidental death. On the log "
                   "homicide panel the UNODC rate runs near 1.3–2.2 per "
                   "100,000 while the police type-301 files per 100,000 start "
                   "only in 2021 and spike to about 12.3 in 2023, the "
                   "October-7 year; road deaths fall from 6.4 to 3.4 before "
                   "WHO's series stops; the lens panel counts the recorded "
                   "murder files themselves — 156, 112, 1,209, 458, 345 — "
                   "saying the 2023 column is the attack counted inside "
                   "type 301.",
                pt="Quatro painéis sobre morte violenta e acidental. No "
                   "painel logarítmico de homicídio, a taxa da UNODC fica "
                   "perto de 1,3–2,2 por 100 mil, enquanto os arquivos tipo "
                   "301 da polícia por 100 mil começam só em 2021 e disparam "
                   "para cerca de 12,3 em 2023, o ano de 7 de outubro; mortes "
                   "no trânsito caem de 6,4 para 3,4 antes da série da OMS "
                   "parar; a lente conta os arquivos de homicídio registrados "
                   "— 156, 112, 1.209, 458, 345 — dizendo que a "
                   "coluna de 2023 é o ataque contado dentro do tipo 301."),
            "sources": ["security/security_from_wb.csv",
                        "security/homicide_police_from_datagovil.csv"],
        },
        {
            "id": "08-migration", "topic": "migration", "n": "08",
            "family": PEOPLE,
            "title": T(
                he="הגירה — זרם חוק השבות וזרם ההיתרים",
                en="Migration — the Law of Return Flow and the Permit Flow",
                pt="Migração — o Fluxo da Lei do Retorno e o Fluxo de Permissões"),
            "blurb": T(
                he="שני סדרות רשמיות פתוחות: עולים חדשים ממשרד העלייה "
                   "והקליטה (מ-2015) והנפקות היתרים של רשות האוכלוסין "
                   "(מ-2019). לעולם לא נסכום אותם לשורה אחת.",
                en="Two official open-data series: new olim from the Ministry "
                   "of Aliyah and Integration (from 2015), PIBA issuance "
                   "(from 2019). Never summed into one line.",
                pt="Duas séries oficiais abertas: novos olim pelo Ministério "
                   "da Aliyah e Integração (desde 2015) e emissões da PIBA "
                   "(desde 2019). Nunca somadas numa só linha."),
            "alt": T(
                he="ארבעה פאנלים על הגירה לישראל, לכל 1,000 תושבים. זרם העולים "
                   "— באים בחוק השבות — הגיע לשיא של 76,601 ב-2022, גל מלחמת "
                   "אוקראינה (כ-8 ל-1,000); אומדן הנדידה נטה של ה-UN הגיע לכ-5.2 "
                   "באותה שנה, והפאנל קובע שאלה שני חפצים שונים; שיעור ילידי־חוץ "
                   "של UN DESA יורד מ-26.6% ב-2010 ל-22.3% ב-2024; פאנל השפתון מצייר היתרי "
                   "תושבות ועבודה חדשים (זרם, רשומות לא בני־אדם) עם קו ההארכות "
                   "לצידם, ומחריג בשמות את מחלקות התיירות והדיפלומטיה.",
                en="Four panels on Israeli migration, per 1,000 people. The "
                   "olim flow — arrivals under the Law of Return — peaks at "
                   "76,601 in 2022, the Ukraine-war wave (about 8 per 1,000); "
                   "the UN's net-migration estimate peaks near 5.2 per 1,000 "
                   "the same year, and the panel says the two are different "
                   "objects; the UN DESA foreign-born share falls from 26.6% "
                   "in 2010 to 22.3% in 2024; the lens draws new residence and work permits (a "
                   "flow, records not people) with extensions beside them, "
                   "visitor and diplomatic classes excluded by name.",
                pt="Quatro painéis sobre a migração para Israel, por mil "
                   "habitantes. O fluxo de olim — chegadas pela Lei do "
                   "Retorno — atinge 76.601 em 2022, a onda da guerra da "
                   "Ucrânia (cerca de 8 por mil); a estimativa de migração "
                   "líquida da ONU atinge perto de 5,2 por mil no mesmo ano, "
                   "e o painel diz que são objetos diferentes; a parcela de "
                   "nascidos no exterior da UN DESA cai de 26,6% em 2010 para 22,3% em 2024; a lente "
                   "desenha novas permissões de residência e trabalho (um "
                   "fluxo, registros não pessoas) com prorrogações ao lado, "
                   "excluindo nominalmente as classes de turista e diplomáticas."),
            "sources": ["migration/olim_flow_from_datagovil.csv",
                        "migration/permits_from_datagovil.csv",
                        "demography/demography_from_wb.csv",
                        "migration/migrant_stock_wb.csv"],
        },
    ]
