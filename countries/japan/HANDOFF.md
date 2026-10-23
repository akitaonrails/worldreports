# Japan — handoff

Written 2026-10-22, covering the research pass, the fetch swarm and
consolidation, on branch `japan`. This session produced:

- the research and the sources manifest;
- eleven fetchers;
- 45 staged sidecars.

It did **not** produce plates, chapters, i18n, ui, events, curated CSVs
or country tests. Because `country.yaml` exists, the shared suite
discovers Japan and fails on those missing files, which is expected. The
check that nothing else broke is
`python3 -m pytest tests/ -q -k "not japan" --ignore=tests/test_site.py`,
and it gave **363 passed** at consolidation.

The Japan-only run (`-k japan --ignore=tests/test_site.py`) gave 38 passed
and 19 failed. All the data, manifest and core checks pass: parsing,
columns, ordering, duplicates, placeholders, thousands separators,
manifest ↔ files, `official: false`, palette, seo, years and font. The 19
failures are the expected later-phase set:

- 6 catalog tests (no `i18n.json`);
- 3 isolation tests and 2 provenance tests (no `plates.py`, `chapters.py`
  or `provenance.json`);
- 6 layout tests (no plates to draw);
- `test_every_locale_can_be_formatted[japan]` (no `ja` column in
  `AFFIX`);
- `test_the_currency_is_one_the_site_can_write[japan]` (no JPY in
  `CURRENCY_AFFIX`).

The CJK font-table entry for `ja` has no failing test yet. It will matter
when plates render Japanese.

The full suite gave 431 passed, 27 failed and 111 errors:

- every error is the `test_site.py` fixture raising "countries/japan/
  chapters.py does not exist" (120 tracebacks);
- the 3 non-Japan failures are the cross-country comparison tests in
  `test_site.py`, which fail for the same reason.

This is the same shape as the Portugal and UK lanes.

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md),
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) and the plate
spine (`PLATE_SPINE.md`, `core/spine.py` once merged) first. They are the
specification.

---

## What is done

`countries/japan/` holds:

- `country.yaml`. It is unchanged from discovery:
  - locales ja / en / pt, default en;
  - window 2006–2026, `last_full_year` 2025, `tick_every` 2;
  - JPY, five recession bands, a Hinomaru palette.
- `SOURCES.yaml`, corrected in consolidation to what the fetchers do.
  - It has 45 entries and 45 sidecars, one-to-one, and every
    `refreshed_by` exists.
  - It has 6 `meta.pending` entries. The central-debt-before-2021 item is
    removed, because the debt history is staged via WARP.
- `DATA_NOTES.md`: the cross-file traps, the denominator rule, the seams
  and the cross-source table.
- `DISCOVERY.md`, moved here from the lane root. `SOURCES.yaml` and
  `DATA_NOTES.md` override it where they differ, most importantly on the
  flow-of-funds debt.
- 45 staged sidecars under `data/`, every one a `*_from_<source>.csv`.
  Nothing is curated yet.

Consolidation re-ran every fetcher once from cache with `python3 -I`, in
sequence. All asserts passed together and all 45 sidecars came out
**byte-identical** to the swarm's output (sha256). `fetch_mof.py` was then
changed (below) and re-run, and it was byte-identical again.

Several fetchers re-read their index or listing pages on every run to
resolve edition-specific ids, so even "from cache" touches the network
for a few HTML pages: stat, esri, isa, npa, mhlw, mof. `make C=japan
fetch` needs the network.

| Fetcher | Publisher | What it pulled |
|---|---|---|
| `fetch_stat.py` | Statistics Bureau via e-Stat file layer and stat.go.jp | CPI on both bases (national and Tokyo), LFS long table, population estimates 2006–2024, 2020/2025 census (imputed) |
| `fetch_esri.py` | Cabinet Office ESRI | QE calendar, fiscal and quarterly GDP (qe262_2); FY2024 annual GG accounts (GFS 6-2) and COFOG (7) |
| `fetch_boj.py` | BoJ Time-Series API | call rate, basic loan rate, USD/JPY, NEER/REER, monetary base, current account, FoF GG liabilities (L900−L700), household loans |
| `fetch_mof.py` | MOF (+ NDL WARP) | zeisyu tax revenue, 財政統計 tables 1/4/20, central debt 2006–2026, JGB yields, reserves |
| `fetch_customs.py` | Japan Customs | goods trade annual + 2026 YTD, eight partners × two directions |
| `fetch_markets.py` | Yahoo (`official: false`) | Nikkei 225 monthly closes 1996-11 → 2026-10 |
| `fetch_comparables.py` | WB, UNDP, IMF, OECD, UNHCR (`official: false`) | GDP US$, GDP/person, population, reserves, openness, Gini, homicide rate, HDI, IMF debt/balance, OECD IDD, asylum |
| `fetch_mhlw.py` | MHLW | vital statistics long series, causes of death per edition, life tables, poverty |
| `fetch_ipss.py` | IPSS | 2023 projection, nine variants, 2020–2070 |
| `fetch_isa.py` | ISA / MOJ | foreign residents (two regimes), entrants, naturalisation |
| `fetch_npa.py` | NPA | police-recorded 殺人 2006–2025 |

## Dependencies the fetchers need (CI never runs them)

CI (`.github/workflows/pages.yml`) installs only `requirements.txt` and
builds from the committed CSVs. The fetchers need:

- **Python**: openpyxl (in `requirements-fetch.txt`) and **pdfplumber**,
  which `fetch_isa.py` (naturalisation PDF) and `fetch_npa.py` (2006–2019
  PDF editions) use. pdfplumber is **not** in `requirements-fetch.txt`.
  That file is outside this lane, so it is flagged here for the merge
  rather than edited.
- **System binaries**:
  - LibreOffice `soffice`: `fetch_mhlw.py` uses it to convert the
    pre-2019 .xls editions, with a private profile under
    `cache/mhlw_soffice_profile`.
  - poppler `pdftotext`: used by `fetch_mhlw.py` and `fetch_ipss.py`
    (Statistics Bureau cross-checks) and by `fetch_mof.py` (the
    settlement-summary PDF).
- **xlrd is no longer needed.** `fetch_mof.py` used to add the user
  site-packages back onto `sys.path` under `-I` to import xlrd. It now
  carries the small BIFF8 reader from `fetch_isa.py`, copied rather than
  imported, because fetchers are standalone scripts and `-I` drops the
  script directory. Consolidation checked it cell-for-cell against xlrd
  2.0.2 on zeisyu.xls and all four suii.xls editions, and the output is
  byte-identical. `fetch_mhlw.py` still uses soffice rather than that
  reader, because its workbooks are larger and multi-sheet. Moving it to
  the reader would be a further clean-up, not needed for correctness.

## Corrections the consolidation made to the discovery's account

1. **Flow-of-funds GG liabilities.** These are **¥1,399.2tn**, not
   ¥948.6tn. L900 equals A900 (assets), because the column closes on L700.
   This was verified independently against the live API: the nine
   instruments sum to L900 − L700.
2. **MOF central debt.** The total **excludes** guaranteed debt. The
   2006–2021 history is staged from WARP, and that pending item is gone.
3. **MOF 第4表.** Its unit is ¥ **million**, not ¥1,000.
4. **CPI.** It comes from e-Stat's long series on each base, with
   **published** rates. The zmi files are only the check.
5. **Census.** The figures are the imputed table 2-3 (不詳補完値), not
   the PDF summary. The raw table under-counts Japanese.
6. **MHLW.** Each of these was a different file or code from what
   discovery recorded:
   - the long series is the 2025 edition's 第2表/第3表;
   - the life-table year series is life25-**13**;
   - poverty comes from 09.xlsx;
   - the cause table's number moves between editions;
   - COVID is 22200 for 2020–22 and 22201 from 2023.
7. **ISA.** The entrants lid is 000001486941 (not …942). The table
   numbers move in 2022.
8. **NPA.** 2006–2019 are PDF-only, and 2007 comes from the 2008
   edition.
9. **Customs.** The EU line is EU28 through 2019 and EU27 from 2020.
   **UNHCR** reports from 2021 at level FA. The **Nikkei** starts in
   1996-11.
10. **BoJ policy target, read off the staged data.** The targets look
    like 0.75% (Dec-2025), 1.0% (Jun-2026) and **1.25% (Sep-2026)**.
    Discovery stopped at 1.0%. These are still unverified against the
    statements.

## Spot values, for checking that a rerun has not silently changed shape

- **GDP:**
  - nominal CY2024 ¥636,893.3bn, CY2025 ¥666,440.7bn;
  - real SA 2026 Q2 ¥598,950.5bn (annualised level);
  - WB 2024 US$4.190tn, IMF 4.208tn.
- **Prices and labour:**
  - CPI 2020 base: 2022 +2.5, 2025 +3.2 (annual, from index);
  - 2026-08 headline y/y 2.0 (2020 base) / 1.9 (2025 base);
  - unemployment 2006 4.1, 2009 5.1, 2025 2.5.
- **Debt:**
  - IMF gross 2020 228.8, 2024 213.6, 2025 204.8;
  - MOF central Jun-2026 ¥1,346,683.3bn;
  - FoF GG liabilities 2025 Q4 ¥1,399,225.9bn (assets ¥948,630.8bn).
- **Fiscal:**
  - tax FY2024 ¥75,232.1bn, FY2025 ¥84,222.6bn;
  - GA expenditure settlement FY2024 ¥123,024.0bn;
  - bond dependency FY2020 73.5%.
- **Markets:**
  - USD/JPY 2024 151.50, 2025 149.65;
  - call rate Sep-2026 1.043;
  - JGB 10y 2025 mean 1.543, 2026-09-30 3.057;
  - Nikkei Dec-2025 50,339.48.
- **External:**
  - customs 2024 X ¥107,087.5bn, M ¥112,716.0bn; 2026 YTD 8 months;
  - current account 2025 ¥32,235.0bn;
  - reserves Dec-2025 US$1,369,775mn.
- **Credit:** FoF household loans 2025 Q4 ¥388,433.9bn.
- **Demography:**
  - births 2025 671,270, deaths 1,589,533, TFR 1.14;
  - e0 2025 81.35 / 87.33;
  - population 2024 123,802k (Japanese 120,296k);
  - census 2025 122,972,528 (Japanese 119,131,935, foreign 3,840,593).
- **Security and mortality:**
  - homicide deaths 2025 211;
  - police 殺人 2025 976;
  - COVID 2022 47,661 (22200), 2024 35,865 (22201);
  - senility 2025 214,712.
- **Migration:**
  - foreign residents end-2025 4,125,395 (end-2012 2,033,656);
  - registered foreigners end-2011 2,078,508;
  - new entrants 2025 39,184,525, of which non-short-stay 726,420;
  - naturalisations granted 2025 9,258.

## Spine coverage (PLATE_SPINE.md, 2026-10-22)

Each slot has one of three statuses:

- **staged**: the data are in `data/`. Some need only arithmetic at build
  time, such as a share, an index or a rate on the named population.
- **fetch**: the indicator exists at a harmonised or national publisher
  but is not staged. Per spine rule 11 it must be fetched, through a
  fetcher with a sidecar and a manifest entry, before the plate is drawn.
- **unavailable**: it genuinely does not exist for Japan, and the slot
  uses `ctx.pending` with the reason.

Per-100k rates on MHLW counts divide by the **Japanese-national
population**: `population_from_stat.csv` `japanese_k` for 2006–2024 and
`census_from_stat.csv` `japanese` for 2025. MHLW's own rates use the same
denominator. The census and the estimates both give it.

| Topic · slot | Indicator | Status | From / note |
|---|---|---|---|
| economy 1 | Real GDP growth | staged | `gdp_from_esri` real CY (compute y/y) |
| economy 2 | GDP per person, US$ | staged | `gdp_pc_from_wb` |
| economy 3 | CPI inflation + target | staged | `cpi_from_stat` published y/y, one base per line. The 2% target (since Jan-2013) is an annotation |
| economy 4 | Unemployment | staged | `labour_from_stat` (national LFS ≈ ILO definition) |
| fiscal 1 | GG revenue & expenditure, % GDP | staged (FY) / **fetch** (CY) | ESRI 6-2 is fiscal year. A calendar-year harmonised series (OECD EO / national accounts table 12) is needed for the canonical CY line. IMF GGR/GGX are empty for JPN |
| fiscal 2 | Overall balance / primary balance | staged / **fetch** | IMF GGXCNL staged. Primary balance: add IMF GGXONLB_NGDP to `fetch_comparables` |
| fiscal 3 | Gross debt, % GDP | staged | `gg_fiscal_from_imf`. MOF central and FoF lines beside it, labelled |
| fiscal 4 | Interest paid, % GDP | staged (FY) / **fetch** (CY) | ESRI `gg_interest` FY. CY needs OECD |
| spending 1 | COFOG stacked, % GDP | staged (FY) | `cofog_from_esri` ÷ FY GDP. Map 10 divisions → 7 spine groups |
| spending 2 | Social protection vs rest | staged (FY) | same |
| spending 3 | GFCF, whole economy, % GDP | staged | ESRI CY components (residential + non-residential + public investment). WB NE.GDI.FTOT.ZS optional cross-check |
| spending 4 | Public investment, % GDP | staged | ESRI `public_investment_nominal_cy` (公的固定資本形成, which includes public corporations, so say so). GG-only GFCF: OECD fetch if a strict GG line is wanted |
| trade 1 | Exports, imports, % GDP | staged | ESRI X/M CY (= WB openness to 0.2pt) |
| trade 2 | Trade balance, % GDP | staged | ESRI X − M |
| trade 3 | Top export destinations, % of goods exports | staged | `trade_partners_from_customs` ÷ `trade_from_customs`. The EU28→EU27 seam is at 2020 |
| trade 4 | lens | staged | e.g. BoP: goods deficit against the primary-income surplus (`current_account_from_boj`) |
| markets 1 | Policy rate vs inflation | staged (realised) / **curate** | call rate staged. The decided target must be hand-curated (`meta.pending`) |
| markets 2 | 10y yield, annual average | staged | `jgb_from_mof` `jgb_10y_avg` (= OECD MEI to 0.03pt) |
| markets 3 | Currency vs US$, index 2006=100, up = stronger | staged | invert `usdjpy_avg` (yen per $) |
| markets 4 | Equity index in US$ vs S&P 500 in US$ | staged / **fetch** | Nikkei ÷ USD/JPY staged. The S&P 500 line needs a fetch (use whatever the other lanes standardise on) |
| credit 1 | Household debt, % GDP (BIS) | **fetch** | BIS WS_TC Q.JP.H.A.M.770.A (61.8% at 2024 Q4, verified live). FoF loans ÷ GDP (59.2%) is the national line |
| credit 2 | Household lending rate vs policy | **fetch** | BoJ IR04 new-loan/housing rates (codes not yet pinned) |
| credit 3 | NPL ratio | **fetch** | FSA 金融再生法開示債権 ratio or IMF FSI. Nothing staged |
| credit 4 | lens (DSR, stock …) | staged / **fetch** | the FoF stocks are staged. BIS WS_DSR needs a fetch |
| people 1 | Gini | staged | OECD IDD (two methods) + WB. A national MHLW 所得再分配調査 Gini is optional |
| people 2 | Poverty (national) + WB $8.30 line | staged / **fetch** | MHLW relative poverty staged. WB PIP $8.30 for JPN needs a fetch (sparse) |
| people 3 | Minimum wage, US$/month | **fetch** | Japan has a statutory, prefecture-set hourly minimum. The national weighted average (MHLW 地域別最低賃金 全国加重平均, e.g. ¥1,055 FY2024) needs a fetch, and an hours convention for "per month" |
| people 4 | lens | staged | LFS participation and employment, child poverty |
| world 1 | GDP, US$ bn | staged | `gdp_usd_from_wb` |
| world 2 | HDI | staged | `hdi_from_undp` |
| world 3 | CPI (TI) | **curate** | Transparency International, hand-curated (`meta.pending`), with the 2012 seam |
| world 4 | Reserves, US$ bn | staged | `reserves_from_mof` / `reserves_from_wb` |
| demography 1 | Population index 2006=100 | staged | `population_from_stat` + census 2025 (seam). The IPSS projection is a note |
| demography 2 | TFR + 2.1 line | staged | `vital_from_mhlw` |
| demography 3 | Crude birth and death rates per 1,000 | staged | `vital_from_mhlw` (published, Japanese-national basis) |
| demography 4 | Natural increase and net migration per 1,000 | staged / **fetch** | natural change rate staged. Net migration: the Statistics Bureau 人口推計 入国超過 (net international migration, total and by nationality), or WB SM.POP.NETM as the harmonised line |
| security 1 | Homicide rate per 100k | staged | MHLW 他殺 ÷ Japanese pop. WB/UNODC beside it. Police 殺人 (incl. attempts) as a labelled third line or a note |
| security 2 | Suicide per 100k | staged | MHLW 20200 ÷ Japanese pop. The NPA 自殺統計 (all residents) is an optional second line |
| security 3 | Road traffic deaths per 100k | **fetch** | not staged. MHLW 20101 交通事故 is in the same cause tables (add the column to `fetch_mhlw.py`), or NPA 30-day traffic deaths, or WHO |
| security 4 | lens | staged | police 殺人 against deaths, the 4.6× gap |
| mortality 1 | Crude death rate | staged | `vital_from_mhlw` |
| mortality 2 | Excess deaths vs 2015–19 | staged | compute from `vital_from_mhlw` deaths (revised series) |
| mortality 3 | COVID-19 per 100k | staged | 22200 (2020–22) and 22201 (2023+) as two segments ÷ Japanese pop |
| mortality 4 | lens | staged | senility, aspiration pneumonia (2017 break), cancer |
| migration 1 | Immigration and emigration per 1,000 | **fetch** / partly unavailable | no emigration register. The Statistics Bureau estimates' 入国者数 / 出国者数 (≥3-month movers) are the national flows, and need a fetch. ISA non-short-stay new entrants (staged) are events, not people |
| migration 2 | Net migration per 1,000 | **fetch** | same source as demography 4 |
| migration 3 | Foreign-born share (+ foreign-citizen share) | staged (citizen) / **unavailable** (born) | foreign-citizen share from census / estimates / ISA. **No country-of-birth cut exists**, so use `ctx.pending` with that reason |
| migration 4 | lens | staged | ISA stocks by status, naturalisation, asylum (UNHCR; ISA curation pending) |

Summary of the 48 slots:

- **Fully staged: 31.** Spending 1–2 are on FY.
- **Partly staged: 9.** The national or FY line is staged, but the
  canonical line needs a fetch or curation. These are fiscal 1, 2 and 4,
  markets 1 and 4, credit 4, people 2, demography 4 and migration 3.
- **Fetch-only: 7.** These are credit 1–3, people 3, security 3 and
  migration 1–2.
- **Curation-only: 1** (TI CPI).
- **Unavailable:**
  - the country-of-birth half of migration 3;
  - an emigration register, which affects migration 1. Use the Statistics
    Bureau's ≥3-month movers instead.

## Pending

These are in `SOURCES.yaml` `meta.pending` unless marked. None blocks
the build.

1. **e-Stat API appId** (user decision). The API answers HTTP 200 with
   STATUS 100 without one. Every staged series uses the anonymous file
   layer, so nothing needs it today. Registering needs a person's email,
   and with an appId several per-year loops would become single DB
   calls. **Register or not, the user's call.**
2. **BoJ policy target**: hand-curate it from the statements. The staged
   data suggest 0.75 / 1.0 / 1.25% steps in Dec-2025 / Jun-2026 /
   Sep-2026.
3. **Monthly Labour Survey wages**: the file id is not pinned, and the
   2019 sampling-scandal break must be annotated.
4. **ISA asylum press release**: now needed to settle UNHCR's 2024
   "recognized" 1,857 (refugees plus complementary protection?).
5. **MOFA Japanese abroad**: returned 403.
6. **Transparency International CPI**: hand-curate it.
7. *(not in meta)* **pdfplumber** belongs in `requirements-fetch.txt`.
   That is a root file, so it is for the merge.
8. *(not in meta)* The spine "fetch" slots above.
9. *(not in meta)* ESRI's FY2025 annual accounts (due Dec-2026) will
   extend `gg_accounts` and `cofog`. The 2021–2025 population estimates
   will be re-based on the 2025 census, which moves every 2021–2024 rate.

## Open decisions for the user

1. **The 2024 H1 recession band: decided, keep it** (user, 2026-10-22).
   Published real q/q is −0.1 and −0.1 (annualised −0.4 / −0.5), which
   meets the two-quarter rule. ESRI dates no recession there, so the build
   phase must add a country test that asserts both quarters are still
   negative in the staged QE, so a revision that lifts either one fails
   the build and the band is reconsidered then.
2. **The e-Stat API appId**: register it or stay on the file layer.

## What the next session should build

1. **The curated CSVs**, each diffed against its sidecar and trimmed to
   2006–2026. Decide the FY/CY presentation for the fiscal and spending
   plates once the CY harmonised fetch exists.
2. **The spine fetches** listed above, each with a sidecar and a manifest
   entry.
3. **plates.py** on the spine. The ones that need care:
   - **fiscal 3**: three debts, never spliced, with the IMF line
     canonical.
   - **security and mortality**: rates on the Japanese-national
     population, named in the panel.
   - **migration**: the 2012 regime seam, the citizenship-only caveat, and
     entries ≠ people.
   - **markets**: the realised rate against the curated target, plus the
     YCC band from Sep-2016 to Mar-2024.
4. **Phase-B core work**, all additive:
   - a `ja` column in `core/sitebuild.py` `AFFIX`;
   - JPY in `CURRENCY_AFFIX` (no decimals; ¥ prefix in en/pt; 兆円 / 億円
     suffixes in ja; KRW is the template);
   - a `ja` entry in the `core/style.py` script-font table (Noto Sans CJK
     JP, which matplotlib here sees);
   - `ja` chrome in `site/ui.json`;
   - `name.ja` in every other country.yaml.
5. **chapters.py / events.py / i18n.json** in ja, en and pt. events.py
   candidates:
   - the March 2011 earthquake;
   - QQE (April 2013);
   - the negative rate (January 2016);
   - YCC (Sept 2016 – Mar 2024);
   - consumption tax rises (April 2014, October 2019);
   - the July 2012 residence card;
   - the 2020–22 border closure;
   - complementary protection (Dec 2023);
   - the 2025 census.
6. **countries/japan/tests/**: fact tests from the spot values, plus
   no-splice guards:
   - registered and resident columns never share a row;
   - 10601 is blank before 2017;
   - 22201 is blank before 2023;
   - the 2026 trade annual columns are blank;
   - FoF L900 equals assets.
7. Then `make C=japan charts thumbs provenance && make site test`, and the
   merge conversation. Merging is a decision, not a default.

## State of the branch

`japan` was cut from `main` at 2b0e367. This session added only
`countries/japan/`, and nothing in `core/`, `site/`, `tests/`, the root
requirements or another country's directory was touched. `cache/` (67MB)
and `__pycache__/` are gitignored and are not committed.
