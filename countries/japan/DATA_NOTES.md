# Japan — data notes

What these sources were like to work with, and the judgement calls a reader
of the plates should not have to reverse-engineer. `SOURCES.yaml` carries
the per-file caveats; this file carries the ones that cross files.
Research pass, eleven fetchers and consolidation: 2026-10-22.
`DISCOVERY.md` is the research pass's own report, kept as a record. Where
it and this file disagree, this file and `SOURCES.yaml` are right. The
largest disagreement is the flow-of-funds debt, below.

---

## The flow-of-funds "debt" was the asset side

Discovery recorded `FOF_FFAS420L900` ("Liabilities/Total/General
government") as general-government liabilities: ¥948.6tn at 2025 Q4, well
below MOF's ¥1,346.7tn. That number is the government's financial
**assets**. A flow-of-funds liabilities column closes on L700, the
difference between financial assets and liabilities, so L900 equals A900
to the unit in every quarter.

`fetch_boj.py` writes liabilities as L900 − L700 and asserts L900 = A900.
Consolidation checked it independently against the live API. The nine
general-government liability instruments (L200 loans, L300 debt
securities, L334 equity, L340 derivatives, L500 deposits money, L510 trade
credits, L520 payables, L550 other external, L600 others) sum to exactly
L900 − L700:

| Quarter | Σ instruments (¥100mn) | L900 − L700 | L900 = A900 |
|---|---|---|---|
| 2006 Q4 | 9,445,428 | 9,445,428 | 5,814,546 |
| 2016 Q4 | 12,778,656 | 12,778,656 | — |
| 2025 Q4 | 13,992,259 | 13,992,259 | 9,486,308 |

So general-government liabilities at market value are **¥1,399.2tn**
(2025 Q4), not ¥948.6tn. The sidecar keeps assets and the net position
beside them, labelled.

## Three debts, and their order

| End-2024, % of CY GDP (ESRI ¥636.9tn) | |
|---|---|
| BoJ flow of funds, GG liabilities, market value, all instruments | **226.7%** (¥1,443.6tn) |
| IMF WEO gross GG debt (GGXWDG_NGDP) | **213.6%** |
| MOF central government, face value (JGB + borrowings + FBs) | **206.9%** (¥1,317.6tn) |
| ESRI GFS balance sheet, GG liabilities (FY2024, FY GDP) | 200.1% |

They sit in a stable order across the window: 2006 is 174.7 / 152.1 /
154.0, and 2020 is 254.1 / 228.8 / 218.8. The flow of funds is highest
because it counts every instrument, not just debt securities and loans.
None is spliced onto another, and the fiscal plate names which one it
draws.

The brief's ">250% of GDP" is an older WEO vintage on the 2015-base GDP.
On today's IMF vintage the 2020 peak is 228.8%. Only the flow-of-funds
measure ever went above 250% (2020: 254.1%).

MOF's total **excludes** government-guaranteed debt, which is a
contingent liability with its own column. Discovery's note said
"plus government-guaranteed debt". The 2006–2021 history is no longer
pending. It comes from MOF's own editions in the NDL web archive, and
every overlap between editions agrees to 0 億円.

## Vital statistics are Japanese nationals, and so must the denominator be

MHLW's 人口動態統計 count **Japanese nationals in Japan**. Births to two
foreign parents and deaths of foreign residents are excluded. The
published rates divide by the **Japanese** population, which
consolidation confirmed: 2024 deaths 1,605,378 ÷ 120.296mn Japanese =
13.35‰. That matches the published 13.3. Divided by the total population
it would be 12.97.

The rule this sets for every drawn per-100k slot (homicide, suicide, COVID):
**the count's population is `japanese_k`** in
`population_from_stat.csv`.

MHLW cause code 20100 is not a road-death series: it covers the broader
accident category and its 2011 jump includes disaster deaths. It therefore
stays out of the canonical road-traffic slot, which remains visibly pending
until an NPA or WHO road-only history is staged.

- 2006–2024: the estimates' Japanese population on 1 October. The
  2006–2020 values are intercensally adjusted. The 2021–2024 values are
  still on the 2020-census base and will be revised.
- 2025: the census Japanese count, 119,131,935 (`census_from_stat.csv`),
  because no 2025 estimate exists. That is a change of base, and the
  panel notes it.
- Where MHLW publishes the rate itself (crude birth and death rates,
  infant mortality), use the published rate.

Rates on the right denominator, from the staged counts:

| | 2006 | 2015 | 2020 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|
| Homicide deaths per 100k (MHLW ÷ Japanese pop) | 0.46 | 0.25 | 0.20 | 0.18 | 0.19 | 0.19 |
| World Bank / UNODC per 100k | 0.48 | 0.29 | 0.25 | 0.23 | 0.23 | — |
| Police 殺人 incl. attempts per 100k (NPA ÷ total pop) | 1.02 | 0.73 | 0.74 | 0.68 | 0.73 | 0.78 |
| Suicide per 100k (MHLW 20200) | 23.7 | 18.5 | 16.4 | 17.4 | 17.4 | 16.3 |
| COVID-19 per 100k (22200 to 2022, 22201 from 2023) | — | — | 2.8 | 39.1 | 31.4 | 29.8 |

The police count covers everyone in Japan by place of occurrence, so it
divides by the total population. It is the wrong numerator for a
"homicide rate" whatever the denominator, because 殺人 includes attempts
and preparation (976 recorded against 211 deaths in 2025, 4.6×). It is a
second labelled line, never the rate.

MHLW deaths agree with the Statistics Bureau's Oct–Sep all-resident
deaths within ±2.5% in every year, and to −0.06% over 2015–2024. Births
run 2–5% below it. The gap is births to foreign parents, and it widens as
the foreign population grows.

## Breaks the plates must draw as seams

- **CPI 2020 → 2025 base.** Both bases are published in parallel back to
  1970, and each has its own published 12-month rates. Before 2026 they
  are identical (240 of 240 months). In 2026, 3 of 8 months differ. Rate
  lines stay on one base, the column says which, and nothing is
  re-computed across the seam.
- **July 2012, the residence card.** 2006–2011 is 外国人登録 (registered
  foreigners, which included some short-stayers). From end-2012 it is
  在留外国人. They sit in different columns and never share a row. The
  2011→2012 step (2.08mn → 2.03mn) is the seam, not a fall.
- **Census rebasing.** The 2021–2024 population estimates are on the
  2020 census base, and 2025 exists only as the census (122,973k, against
  the 2024 estimate's 123,802k). Population growth 2024→2025 between the two files
  is a change of base. The LFS is publisher-spliced onto successive
  censuses, and `benchmark_census` says which census each year rests on.
- **2017 ICD-10 (2013 version).** 10601 aspiration pneumonia split out of
  10200 pneumonia, which drops by ~22k that year for coding alone. The
  new code is its own column, blank before 2017, and is never added back.
- **COVID codes.** The 2020–2022 editions publish only 22200 (the
  special-purpose U-codes, which in practice means COVID: 3,466 / 16,784 /
  47,661). 22201 is split out from the 2023 edition (38,086 against
  22200's 38,120). These are two columns. A COVID line takes 22200 to 2022
  and 22201 from 2023 as two labelled segments.
- **The 2019 re-tabulation.** MHLW re-tabulated 2004, 2006 and 2009–2017
  after prefectures under-reported. The long series (第2表) is revised,
  but the per-year cause editions are not. `all_causes` and
  `all_causes_revised` differ by up to 410 (2016), and the gap is
  unallocated to causes.
- **EU28 → EU27.** The customs EU line is the membership of the time, so
  2019 (¥8,955.3bn exports) includes the UK. 2019→2020 is a definitional
  drop plus COVID.
- **UNHCR from 2021.** Japan's positive decisions are reported only at
  level FA (final, all instances combined). FI and appeal "recognized"
  cells are blank from 2021, and the FA columns are separate. The 2024 FA
  "recognized" figure is **1,857**, against 289 in 2023 and 187 in 2025.
  ISA's own 2024 figures, from memory and unverified because the ISA
  release was not reachable, are about 190 refugees recognised plus
  about 1,661 granted complementary protection, which began in December
  2023 and went mostly to Ukrainians. 190 + 1,661 = 1,851, so UNHCR almost
  certainly folds the two into one cell. Do not draw 2024 as a surge in
  refugee recognition until the ISA release is curated
  (`meta.pending`).
- **Poverty, 2018.** The survey has two income definitions, old and new
  (OECD 2015 terms). 2018 is on both (15.4 / 15.7), and OECD IDD mirrors
  it as METH2011/METH2012.
- **The 2011 LFS.** Iwate, Miyagi and Fukushima were not surveyed
  March–August, so the year is a supplementary estimate (flagged).
- **Effective exchange rates** start in 2010 on CY2020=100. The
  discontinued March-1973 base is not spliced.

## Calendar against fiscal

Japan's fiscal year runs April–March. Every FY column here is keyed on its
**starting** year (FY2024 = Apr 2024 – Mar 2025), and no fetcher keys a
calendar series on an April year. Plates draw each fiscal year at its
1 October midpoint, so FY2024 appears at `2024.75`. The FY series are:

- ESRI annual accounts: GG accounts and COFOG.
- ESRI `*_fy` GDP columns.
- MOF zeisyu and the general account.

Everything else is calendar or point-in-time:

- ESRI `*_cy` GDP and QE quarters, customs, BoP, BoJ markets, JGB, reserves.
- MHLW, NPA, ISA.
- Population on 1 October; ISA stocks at 31 December; MOF debt at
  quarter-ends.

The spine's fiscal slots are on general government in **calendar** years.
ESRI's GG accounts are fiscal years only, and IMF DataMapper's GGR/GGX
answer empty for Japan. So revenue, expenditure and interest are FY on the
staged data. Consolidation's check: ESRI FY net lending agrees with the
IMF's calendar balance to within a point (2006 −3.0 / −3.0; 2020 −10.0 /
−9.0; 2024 −1.4 / −1.7). A calendar-year harmonised fetch (OECD) is
listed in HANDOFF.

## Units, as published and as staged

Most yen series are converted by the fetcher to **¥ billion**, and every
sidecar's comment block names the published unit:

| Published | Where | Staged |
|---|---|---|
| 10億円 (¥bn) | ESRI QE and annual accounts | ¥bn |
| 億円 (¥100mn) | BoJ API, MOF zeisyu, MOF debt (suii) | ¥bn (÷10) |
| 百万円 (¥mn) | MOF 財政統計 第4表 | ¥bn (÷1,000) |
| 千円 (¥1,000) | Customs, MOF 第1表 and 第20表 | ¥bn (÷1,000,000) |
| 万人 (10,000 persons) | LFS | thousands (×10) |
| thousands | population estimates, IPSS | thousands |
| persons | census, MHLW, ISA, NPA, MOJ | persons |
| US$mn | MOF reserves | US$mn |

Discovery had 第4表 in ¥1,000. It is ¥ million, and the fetcher asserts
the unit cell of every table.

## Holes, zero-fills and partial years

- Customs `d41ma.csv` writes the unpublished months of 2026 as "0,0". The
  fetcher counts a month only if both sides are non-zero, requires the
  zeros to be strictly trailing, and writes 2026 only as a year-to-date
  (8 of 12 months) in `*_ytd` columns. The annual columns are blank.
- The BoP annual totals are blank for the part-year, with `months`
  showing how many months exist.
- Stock-type sidecars carry the running year at its latest reading, with
  `asof_month` or `asof_quarter`: BoJ FoF, monetary base, reserves, rates.
- The JGB 2026 row is ten months long and its `last_date` says so.
- Nikkei's 2026-10 bar is a live reading (`partial=1`).
- MHLW "-" means zero and is written 0. "…" and "・" are written blank. A
  code absent from an edition is blank.
- WB nulls stay blank. Openness stops at 2024, the WB Gini covers
  2008–2020, and the UNODC homicide rate stops at 2023.
- OECD/MHLW poverty is triennial. The years between surveys are holes and
  are not interpolated.
- Population 2025 is absent on purpose.

## The 2024 H1 recession band (a decision for the user)

`country.yaml` bands 2024 Q1–Q2 on two consecutive negative quarters in
the current QE (qe262_2). Published real q/q is −0.1 and −0.1
(annualised −0.4 / −0.5). That meets the two-quarter rule, matches the UK
precedent, and sits inside revision noise. ESRI dates no recession there.
2025 Q3 (−0.4) is a single quarter and is not banded. **Keep or drop is
the user's call**. If kept, re-check it on every QE refresh, because one
revision of either quarter to zero removes it. A test asserting the two
negatives would make that fail loudly.

## Departures from the spine (for the build to confirm)

The spine (`PLATE_SPINE.md`) fixes slots across countries. Japan's data
force these departures:

- **No country-of-birth cut** (migration slot 3). Japan publishes
  citizenship only, so the slot is foreign-citizen share, and the panel
  says so. It is a true statement, not a gap.
- **No emigration register** (migration slot 1). Departures in ISA are
  travel events, and MOFA's count of Japanese abroad (a stock) returned
  403. Immigration and emigration per 1,000 would need the Statistics
  Bureau's 入国超過 in the population estimates, which is not staged.
- **Policy rate** is the realised call rate until the target is
  hand-curated, and the target changed kind three times.
- **Fiscal slots** are FY, not CY, on the national accounts.
- **Senility (老衰)** is the third-largest certified cause and rising,
  from 27.8k to 214.7k over the window. It is a lens for the mortality
  chapter, and it also makes cross-country cause comparisons misleading.

## Cross-source checks run in consolidation

| Chapter | Check | Result |
|---|---|---|
| Economy | ESRI nominal CY ÷ BoJ USD/JPY mean vs WB / IMF US$ GDP | 2006 4,648.8 / 4,648.1 / 4,648.1bn; 2024 4,203.9 / 4,190.0 / 4,207.6; 2025 4,453.3 / 4,435.2 / 4,453.1 (WB 0.3–0.4% low in 2024–25) |
| Economy | ESRI (X+M)/GDP vs WB openness | 2006 29.7 / 29.7; 2024 45.1 / 44.9 |
| Economy | LFS 2025 15+ population vs 2025 census 15+ | 109,730k vs 109,624k |
| Prices | CPI 2025-base vs 2020-base published rates | identical 240/240 months to 2025; 3 of 8 differ in 2026 |
| Fiscal | MOF central debt / FoF GG liabilities / IMF, % CY GDP, 2024 | 206.9 / 226.7 / 213.6 |
| Fiscal | FoF L900 vs A900; Σ liability instruments vs L900 − L700 | equal every quarter; equal at 2006/2016/2025 Q4 (live API) |
| Fiscal | ESRI GG net lending (FY) vs IMF (CY) | 2006 −3.0 / −3.0; 2020 −10.0 / −9.0; 2024 −1.4 / −1.7 |
| Fiscal | zeisyu FY2025 vs 令和7年度決算概要 settlement | equal (842,226 億円); zeisyu = 第4表 tax in every year |
| Fiscal | MOF debt editions (live + 4 WARP captures) on overlapping quarters | agree to 0 億円 |
| Trade | Customs 2024 exports at WB rate vs WB/WTO merchandise exports | US$707.5bn vs 707.0bn (+0.07%) |
| Trade | Customs goods exports vs ESRI exports of goods and services | 2024 16.8% vs 22.2% of GDP (services); never spliced |
| Trade | BoP current account = goods + services + primary + secondary | within ¥1bn |
| Markets | JGB 10y annual mean vs OECD MEI IRLTLT01JPM156N | worst gap +0.034pp (2010) |
| Markets | FM01 daily call rate monthly mean vs FM02 | reproduces |
| World | MOF reserves Dec-2024 vs WB FI.RES.TOTL.CD | US$1,230,715mn vs 1,230,667mn |
| Credit | BoJ FoF household loans / CY GDP vs BIS WS_TC H 770 | 2024 59.2% vs 61.8% (BIS adds NPISHs; live check, not staged) |
| Demography | MHLW deaths vs Statistics Bureau Oct–Sep deaths | ±2.5% each year; −0.06% summed 2015–24 |
| Demography | MHLW death rate vs deaths ÷ Japanese pop | 13.3 vs 13.35 (2024): the denominator is Japanese nationals |
| Demography | MHLW TFR and e0 vs World Bank | equal (TFR 2006/2015/2024; e0 2019/2023) |
| Demography | IPSS medium 2021–24 vs Statistics Bureau estimates | within +0.05% |
| Demography | Population 2024: Statistics Bureau 1 Oct vs WB mid-year | 123,802k vs 123,975k |
| Security | NPA 殺人 / MHLW 他殺 deaths, 2025 | 976 / 211 = 4.6× |
| Security | MHLW homicide per 100k (Japanese pop) vs WB/UNODC | 2023 0.19 vs 0.23 |
| Mortality | causes 2024 in the 2024 vs 2025 edition | identical |
| Migration | ISA end-2025 vs Census foreign (1 Oct 2025) vs estimates foreign (2024) | 4,125,395 / 3,840,593 / 3,506k: three stocks for one idea |
| Migration | MOJ naturalisation grants vs the by-nationality PDF 2023–25 | equal |
| Migration | UNHCR 2024 FA recognised vs ISA (from memory) | 1,857 vs ~190 + ~1,661 complementary: unverified |

## Changes to the discovery's files made in consolidation

- `SOURCES.yaml`: corrected throughout to what the fetchers do. The fixes
  include the FoF liabilities, MOF debt excluding guaranteed debt and its
  WARP history, the 第4表 unit, the CPI source (e-Stat long series on
  both bases), the census source (imputed table 2-3), the MHLW long
  series, life-table and poverty files, the cause-table renumbering and
  COVID codes, the IPSS tables, the ISA entrants lid (…941) and table
  numbers, the NPA PDF editions, the EU28→EU27 seam, UNHCR's FA level and
  the Nikkei start month. The central-debt-before-2021 pending item is
  removed. The policy-target and asylum pending notes are extended.
- `fetch/fetch_mof.py`: the xlrd import, which put the user site-packages
  back on `sys.path` under `python3 -I`, is replaced by the BIFF8 reader
  from `fetch_isa.py`. Consolidation checked it cell-for-cell against
  xlrd 2.0.2 on all five cached .xls files, and the output is
  byte-identical.
- `DISCOVERY.md` moved from the lane root into `countries/japan/`.
- `country.yaml` is unchanged. The 2024 H1 band is left for the user.
