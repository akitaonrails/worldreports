# Japan — Phase A discovery report (2026-10-22)

**Delivered (uncommitted, in the lane as instructed; `git status` shows only `?? countries/japan/` plus this file):**
- `countries/japan/country.yaml`: slug `japan`, locales ja/en/pt (ja first, en default per precedent), window 2006–2026, `last_full_year: 2025`, `tick_every: 2`, JPY, five bands, a Hinomaru-derived palette with violet-sumi web chrome, ja/en/pt seo and sources blocks.
- `countries/japan/SOURCES.yaml`: 45 planned `*_from_<source>.csv` datasets in 11 directories. Discovery recorded 7 `meta.pending` entries; the current manifest has 5 after central-debt history and TI CPI were staged.

**Verification:** both files parse as YAML. `pytest tests/ -k "not japan" --ignore=tests/test_site.py` gives **363 passed**, so the baseline is intact. With Japan included, 36 Japan tests pass (palette, web hex, seo in all three locales, years, locales, slug, font). The 21 failures are the expected Phase A set:
- missing `i18n.json`, `data/`, `plates.py`, `chapters.py` and `provenance.json`;
- two real cross-phase items: `test_every_locale_can_be_formatted[japan]` (there is no `ja` column in `AFFIX`) and `test_the_currency_is_one_the_site_can_write[japan]` (there is no JPY in `CURRENCY_AFFIX`). Both are additive `core/` changes for Phase B.

---

## Publishers (all probed live 2026-10-22)

### e-Stat (Statistics Bureau / National Statistics Center): the portal behind almost everything
- **The trap is confirmed.** The API (`api.e-stat.go.jp/rest/3.0/app/json/getStatsList|getStatsData`) needs an appId. Called with no appId, or with `appId=` left empty, it returns **HTTP 200** with `RESULT.STATUS 100` "認証に失敗しました。アプリケーションIDを確認して下さい。" No key exists here and none was registered, because registration needs a person's email. This is recorded in `meta.pending`.
- **Anonymous route, verified:** the FILE layer, `https://www.e-stat.go.jp/stat-search/file-download?statInfId={12d}&fileKind={0 Excel|1 CSV|4 Excel-report}`. It returns the file with a content-disposition filename. The listing pages `…/stat-search/files?page=1&layout=datalist&lid={lid}` are scrapeable HTML; statInfIds change with every edition, so fetchers resolve them from the listing at fetch time and assert the table number. Every e-Stat-hosted series in the manifest goes through this route, so nothing is blocked.

### Statistics Bureau of Japan (MIC): CPI, LFS, population, census
- **CPI.** `stat.go.jp/data/cpi/2020/csv/zmi2020aa.csv` (2020=100, 2020-01→2026-08) and `…/2025/csv/zmi2025aa.csv` (**rebased to 2025 this year**; both bases are published in parallel). The long rounded series from 1970 is e-Stat `statInfId=000032103842`. All are Shift_JIS, one column per item. Annual rates computed from the index: 2022 +2.5%, 2023 +3.3%, 2024 +2.7%, 2025 +3.2%. The Tokyo ku-area file `tmi2025aa.csv` runs one month ahead.
- **LFS.** `lt02.xlsx` (statInfId `000001082681`), 1953–2025, **units 万人 (ten thousand)**. Unemployment: 2006 4.1, 2009 5.1, 2024 2.5, 2025 2.5. Breaks: the 2011 values are supplementary estimates (Iwate, Miyagi and Fukushima were not surveyed Mar–Aug 2011), plus census re-benchmarking every five years, with a separate "既公表値" sheet holding previously published values.
- **Population estimates.** The long series 2000–2020 (statInfId `000013168601`, thousands, total and Japanese) gives 2006 = 127,901. The 2024 annual release (`jinsui/2024np/zuhyou/05k2024-1.xlsx`) gives 123,802k, the 14th consecutive fall. There is **no 2025np page (404)**: census years are covered by the census instead.
- **2025 Census** (published 2026-09-29, `kokusei/2025/kekka/pdf/summary_01.pdf`): **122,973k** total, Japanese 119,132k, **foreign 3,840k** (+39.8% on 2020). **Re-basing trap:** the estimates still run on the 2020 census (the 2026-10-20 release is "令和2年国勢調査を基準とする確定値"; the 1 Oct 2026 provisional is 122.69mn). The 2021–2025 estimates will be revised onto the 2025 census later. Until then, growth measured across that seam is not real growth.

### Cabinet Office (ESRI): national accounts
- **QE CSVs.** Today's release is `esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/gaku-{mcy,mfy,jcy,jk}2622.csv`, 2020 benchmark, ¥bn, Shift_JIS. **The release directory and file suffix move with every QE**, so the fetcher resolves them from `sokuhou_top.html`. Nominal CY2024 = ¥636,893.3bn, CY2025 = ¥666,440.7bn.
- **Quarterly real SA levels are annualised.** The file header says so ("年率で表示"), so the annual figure is the mean of the quarters, never the sum. The quarter label carries the year only on Q1 rows.
- **Annual accounts.** FY2024 (`kakuhou/files/2024/tables/2024s6_2_jp.xlsx`, the general-government sector accounts, with subsector column blocks per FY) and `2024s7_jp.xlsx` (COFOG, one sheet per wareki fiscal year). The FY2025 edition is not out yet (404; due Dec 2026).
- **Business-cycle reference dates** (`esri.cao.go.jp/jp/stat/di/hiduke.html`), used to cross-check the bands: contractions Feb 2008–Mar 2009, Mar–Nov 2012, Oct 2018–May 2020.

### Bank of Japan: Time-Series Data Search API (new, anonymous, verified)
- **API.** `https://www.stat-search.boj.or.jp/api/v1/getDataCode?format={json|csv}&lang=en&db=…&code=…&startDate=YYYYMM`, with `getMetadata` per database. Limits: ≤250 series and ≤60k points per request; paging uses `NEXTPOSITION`. The CSV has an 11-line preamble and quoted names containing commas. `STATUS 200 / M181000I` means success. The BoJ API does not carry JGB yields; those come from MOF (below).
- **Verified series:**
  - `FM02 STRACLUCON` (overnight call, monthly average): Dec-2016 −0.044, Aug-2024 0.227, Dec-2025 0.557, Sep-2026 **1.043**.
  - `FM08 FXERM07` (USD/JPY monthly average): 2024 mean 151.50, 2025 149.65, Sep-2026 156.23. Yen per dollar, so **a rising line means a weaker yen**.
  - `FM09` effective exchange rates (2020=100). The pre-2010 series is on another base.
  - `MD01 MABS1AN11` (monetary base, ¥100mn).
  - `IR01 MADR1M` (basic loan rate).
  - `BP01 BPBP6JYNCB` (current account): CY2024 sum ¥29.28tn, 2025 ¥32.24tn.
  - **Flow of funds:** `FOF_FFAS430L200` household loans, 2025Q4 ¥388.4tn (quarter codes YYYYQQ). `FOF_FFAS420L900` general-government liabilities, ¥948.6tn **at market value**.
- **No policy-target series exists**, and the target changed kind three times inside the window (overnight call → monetary base → −0.1% plus YCC → overnight call). Hand-curation is pending.

### Ministry of Finance and Japan Customs: fiscal, JGB yields, debt, reserves, trade
- **JGB yields.** `mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv`: daily 1–40y from 1974, **wareki dates (S49.9.24, R8.9.30)**, "-" for tenors not yet issued. The running month is in `jgbcm.csv`, which ends with an advice row. 10y: 2016-07 −0.26, **2026-09-30 3.057**.
- **Tax revenue.** `tax_policy/summary/condition/zeisyu.xls`, FY, ¥100mn: FY2024 ¥75.2tn, FY2025 ¥84.2tn (confirm this is the settlement figure). Settlement tables: `policy/budget/reference/statistics/01…35.xlsx`, in ¥1,000, and the file number ≠ the table number everywhere.
- **Central-government debt.** `jgbs/reference/gbb/suii.xls` covers only the last five years: June 2026 **¥1,346.7tn**. Older editions are archived at the NDL (pending).
- **Reserves.** `policy/international_policy/reference/official_reserve_assets/historical.csv`, US$mn monthly from 2000, with the year forward-filled: Dec-2024 1,230,715 (= World Bank), Dec-2025 1,369,775.
- **Customs.** `customs.go.jp/toukei/suii/html/data/d41ca.csv` (annual) and `d41ma.csv` (monthly), ¥1,000, Shift_JIS: 2024 exports ¥107.09tn, imports ¥112.72tn.
  - **`d41ma.csv` zero-fills future months** (2026/09–12 = "0,0"), so 2026 really has 8 of 12 months.
  - Partner files: `d52caNNN` (exports) and `d62caNNN` (imports) for US, EU, Asia, China, Korea, ASEAN, Middle East, Russia. Exports to the US went from ¥21.29tn (2024) to ¥20.37tn (2025).

### MHLW: vital statistics, causes of death, life tables, poverty
- **2025 final** (`toukei/saikin/hw/jinkou/kakutei25/xls/06_hyoR07.xlsx`): births **671,270**, deaths **1,589,533**, TFR **1.14**. Scope is **Japanese nationals in Japan**.
- **Long series** (`kakutei24/xls/19_R06zu_kakutei.xlsx`, births and TFR from 1947, labelled in wareki): 2006 births 1,092,674.
- **Causes, table 8, per-year editions** (the file name changes every few years: hyo.xls → hyo.xlsx → 06_hyoR07.xlsx). 2025: cancer 378,829, heart disease 220,539, **senility 214,712**, COVID 21,496, **homicide (他殺) 211**.
- **Life tables 2025:** men 81.35, women 87.33.
- **Living Conditions Survey 2025:** relative poverty **15.0%** (income year 2024), triennial; 2018 exists on two income definitions.
- **Monthly Labour Survey:** the listing was verified but the file id was not pinned. The 2019 sampling-scandal break (only re-estimated from 2012) is recorded in pending.

### National Police Agency: crime
- One CSV per year through e-Stat: 2025 is `statInfId 000040410682` (cp932). Year index: `npa.go.jp/publications/statistics/sousa/statistics.html`.
- **殺人 recorded in 2025 = 976**, a figure that **includes attempts and preparation**, against MHLW's 211 homicide deaths. That is a nearly fivefold "two publishers, one idea" gap, so it is drawn as two lines.

### Immigration Services Agency and MOJ: migration (§4a mapping)
- **Stock: 在留外国人統計.** Semi-annual; lids are listed with full-width digit labels on `moj.go.jp/isa/policies/statistics/toukei_ichiran_touroku.html`. **End-2025: 4,125,395** (statInfId `000040472260`). The definition is mid/long-term zairyu-card holders plus special permanent residents. There is a **hard break in July 2012**, when alien registration was replaced by the residence card.
  - There are three stocks for one idea: ISA 4.13mn, Census 3.84mn, and the estimates' total minus Japanese.
  - Everything is cut by citizenship; **Japan publishes no country-of-birth cut**.
- **Flow: 出入国管理統計, table 25-00-05 新規入国外国人** (statInfId `000040476160`). The 2025 total is 39,184,525, of which 38,458,105 are temporary visitors. **Only 726,420 non-short-stay new entrants are migration.** An entry is an event, not a person.
- **Naturalisation** (MOJ PDF `content/001458302.pdf`): 2025 granted 9,258, applications 14,103, refused 666; 2006 granted 14,108.
- **Asylum:** the UNHCR API (`api.unhcr.org/population/v1/asylum-applications/?coa=JPN`) was verified (2023 new first-instance applications: 13,823). The ISA's national press-release figures are pending.
- **Emigration:** MOFA's count of Japanese residents abroad returned 403 (pending). Japan has no emigration register.

### Comparables (all `official: false`)
- **World Bank JPN** (lastupdated 2026-10-08): GDP 2024 **US$4.190tn**, consistent with ESRI ¥636.9tn at ¥151.5 per dollar; population 2024 123.98mn (mid-year); reserves US$1.231tn; openness 44.9% (2024); Gini sparse (2008–2020); homicide 0.23 per 100k (2023).
- **UNDP HDR25:** HDI 2023 = 0.925, rank 23.
- **OECD IDD:** Gini 0.338 (2021).
- **IMF DataMapper:** `GGXWDG_NGDP/JPN` gross debt 2020 228.8%, **2024 213.6%**, 2025 204.8%; projections to 2031.

### Yahoo Finance: Nikkei 225 (`official: false`)
- `query1.finance.yahoo.com/v8/finance/chart/%5EN225?interval=1mo&range=30y` needs a short User-Agent.
- **Timestamp trap:** bars are stamped at JST midnight, which is 15:00 UTC on the previous day. Labelled in UTC, every month slips back by one, so apply `gmtoffset` before labelling.
- Year-ends (JST): 2007 15,307.8, 2008 8,859.6, 2012 10,395.2, 2024 39,894.5, **2025 50,339.5**; latest close 62,907.8.
- stooq `^nkx` is JS-walled (796 bytes under HTTP 200).

## Magnitude cross-checks against the brief
| Brief says | Verified |
|---|---|
| Population ~124mn, declining | Yes. 123,802k on 1 Oct 2024; 122,973k at the 2025 Census; 122.69mn provisional for 1 Oct 2026 |
| GDP ~US$4.2tn | Yes. World Bank 4.190tn, IMF 4.208tn, ESRI ¥636.9tn ÷ 151.5 |
| Debt >250% of GDP | **No, not on the current vintage.** IMF gross general-government debt is 213.6% (2024), with a 2020 peak of 228.8%. The >250% figures came from older WEO vintages on the 2015-base GDP; the 2020 benchmark revision raised nominal GDP. There are three debts in the manifest, never spliced: IMF general government, MOF central government at face value (¥1,346.7tn), and flow of funds at market value (¥948.6tn) |

## country.yaml decisions
- **Bands** are dated off ESRI `gaku-jk2622` q/q growth (current vintage, computed today) and cross-read against ESRI's reference dates:
  - `2008.25–2009.25`: four negative quarters, matching ESRI.
  - **`2010.75–2011.5` "2010–11 contraction"**: three negative quarters that meet the rule. The earthquake is an **event** inside the band, not its label, and ESRI does not date this one.
  - `2012.25–2013.0`: three negative quarters, matching ESRI.
  - `2020.0–2020.5` COVID: banded by atlas precedent. In this vintage only 2020Q2 is negative (2020Q1 +0.3).
  - **`2024.0–2024.5` "2024 H1 dip"** (−0.09 and −0.12): banded on the UK precedent, but it sits inside revision noise. This is the one band the parent may want to overrule.
  - Single quarters were not banded: 2014Q2 (the consumption-tax rise), 2023Q3 and others.
- **Locales and name.** `ja` (html_lang `ja`, og `ja_JP`, endonym 日本語), `en`, `pt-BR`, with `default_locale: en`. `name` is filled in en/fr/pt/es/ko/ja. Wordmark 日本 with `mark_bearing: "0"`.
- **Palette** (one hue, from the Hinomaru):
  - Primary is a darkened beni red, `#9E1B32`, kept distinct from Canada's `#B5272F` and the UK's `#B32438`.
  - Cool siblings: indigo `#26456E`, slate blue `#3A6EA5`, teal `#2A7F86`, plus gold, purple and green.
  - `flag_bands` are paper/red/paper: the disc laid flat, with the paper bands outlined. The test requires exactly three bands.
  - Web chrome is a violet-cast sumi black (`#15121A`), distinct from every existing ground (warm red-blacks, navies, green-blacks). The accents are rose `#E46F78`, teal `#4FA9B0` and gold `#D6A646`.
- **Fiscal year** follows the `fiscal_year` convention (April–March, keyed on the starting year) for MOF, ESRI annual accounts and the LFS FY table. Calendar and fiscal series are always separate columns.

## Pending list (SOURCES.yaml `meta.pending`, none blocking)
1. **e-Stat API appId.** Unregistered; it returns STATUS 100 under HTTP 200. The file layer covers v1, and registering is a person's call.
2. **BoJ policy target.** No API series exists, and there are three regimes in the window. Hand-curate from the monetary-policy statements. The 0.75% and 1.0% levels for 2026 are inferred from the realised call rate and not yet verified.
3. **Monthly Labour Survey wages.** The file id is not pinned, and the 2019 sampling-scandal break must be annotated.
4. **ISA asylum press releases.** The URL was not found; UNHCR data is staged instead.
5. **MOFA Japanese abroad.** Returned 403.

Resolved since discovery: MOF central-government debt before 2021 is staged
from the NDL archive, and TI CPI is staged from the pinned CPI 2025 historical
workbook (2026-10-23).

Also unpinned but noted in their entries: the IPSS projection table files (the page is verified; only PDFs are linked), the BoJ IR04 lending-rate codes, and household disposable income from ESRI for the debt-to-income ratio.

## Flagged for Phase B (recorded, not done)
- **`core/sitebuild.py`:** `AFFIX` needs a `ja` column. `CURRENCY_AFFIX` needs JPY: no decimals, ¥ prefix in en/pt, and 兆円/億円 suffix units in ja. The KRW entry is the template.
- **`core/style.py`:** the script-font table has `ko` but no `ja`; add `"ja": ["Noto Sans CJK JP", …]`. Matplotlib here sees Noto Sans and Serif CJK JP (verified).
- **`site/ui.json`:** needs `ja` chrome.
- **Every other country.yaml** needs a `name.ja` entry once a page publishes in Japanese.
- **For fetcher authors:** cp932 decoding, wareki conversion, 万人/億円/千円 units, statInfId resolution at fetch time, the moving QE directory, the customs zero-fill, Yahoo's JST timestamps, and asserting `STATUS 0` / `M181000I` before caching.

## For the fetch swarm
Planned fetchers (named in `refreshed_by`):
- `fetch_stat.py`: CPI, LFS, population, census.
- `fetch_esri.py`: QE and annual accounts.
- `fetch_boj.py`: the API.
- `fetch_mof.py`: zeisyu, settlement tables, JGB, debt, reserves.
- `fetch_customs.py`
- `fetch_mhlw.py`: vital statistics, causes, life tables, poverty.
- `fetch_npa.py`
- `fetch_isa.py`: residents, entrants, naturalisation.
- `fetch_ipss.py`
- `fetch_comparables.py`: World Bank, UNDP, IMF, OECD, UNHCR. Adapt Canada's with ISO3=JPN.
- `fetch_markets.py`: Yahoo ^N225.
