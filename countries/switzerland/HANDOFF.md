# Switzerland — handoff

## Publication completion — 2026-10-23

Switzerland is now a complete spine country. The publication contains 12
plates in German, English and Portuguese; 60 reviewed stable datasets plus
six added spine-gap datasets; localized chapter and page copy; committed
PNG, SVG and thumbnail output; and recorded provenance for all 46 files the
plates actually read. `ctx.pending` remains only for the true absence of a
statutory national minimum wage.

The gaps named by the original handoff were closed: Eurostat public
investment, BIS Q4 household credit, IMF FSI non-performing loans,
World Bank/UNODC homicide, World Bank/WHO road deaths, World Bank poverty and
the Transparency International CPI 2025 workbook are all curated
and declared in `SOURCES.yaml`. Plates keep CHF and US-dollar series apart,
select EFV general government rather than mixing its five sectors, preserve
the 2023 GDP-vintage seam, use Total 1 as the customs partner denominator,
and keep migration flows, asylum flows and S-status stock distinct.

`countries/switzerland/tests/test_plates.py` provides 24 semantic and
clipping checks. The focused publication gate completed with **77 passed**;
the layout inspector reports **zero faults** for de, en and pt. The final
full-repository gate and its exact count belong at the bottom of this file
after the integration run.

The remainder of this document is the archival Phase-A handoff. Statements
that work was still missing or that a spine gap still needed fetching are
superseded by the completion note above; the source-specific cautions remain
useful.

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md),
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) and the
plate spine (`PLATE_SPINE.md` / `core/spine.py`, on the `plate-spine`
branch) first. They are the specification. [`DATA_NOTES.md`](DATA_NOTES.md)
carries the traps and the cross-source table.

---

## What is done

`countries/switzerland/` holds:

- **`country.yaml`:**
  - Locales: **de** (de-CH, first), en (the default), pt (pt-BR).
  - Window 2006–2026, `last_full_year` 2025, `tick_every` 2, CHF.
  - Bands: 2008Q4–2009Q1 and COVID. The 2015 franc shock is an event,
    not a band.
  - In consolidation, only the Liechtenstein comment changed (§7 of
    DATA_NOTES).
- **`SOURCES.yaml`:**
  - Written before the CSVs, then corrected to what the fetchers do.
  - 60 entries, one per staged sidecar, and every `refreshed_by` exists
    and writes that file (checked).
  - 8 `meta.pending` entries.
- **`DATA_NOTES.md`:** the cross-file traps, and a table of where
  DISCOVERY.md was wrong.
- **`DISCOVERY.md`:** the research pass's report, kept as a record and
  moved here from the lane root.
- **60 staged sidecars** under `data/`, every one a `*_from_<source>.csv`.
  Nothing is curated yet.

| Fetcher | Publisher | What it pulled |
|---|---|---|
| `fetch/fetch_bfs.py` | BFS DAM assets + STAT-TAB PxWeb | GDP (current vintage, gold split), LIK, ILO/SECO unemployment, ILO rate, employment, wage index (3 bases), HABE Gini, poverty, SILC arrears, demographic balance, fertility, life tables, projection (16 scenarios), PKS homicide, causes of death, firearm deaths, assisted suicide, migration flows, STATPOP by permit |
| `fetch/fetch_eurostat.py` | Eurostat, geo=CH | nama/namq GDP, gov_10a_main (B9/TR/TE/D41PAY), COFOG, tax burden, HICP, lfsa_urgan, ilc_di12, ilc_li02, demo_gind, crim_off_cat, hlth_cd_aro, nasa_10_f_bs, the migr_* suite |
| `fetch/fetch_snb.py` | SNB cube API | policy rate + Libor range, FX, yields, new-loan and offered mortgage rates, bank household credit, household financial accounts, reserves, BoP current account |
| `fetch/fetch_efv.py` | EFV open data | general government + 4 subsectors (FS and GFS models, status per row), COFOG from `gfs_dashboard/cofog_int.csv` |
| `fetch/fetch_seco.py` | SECO real-time database | quarterly real GDP, `gdp_cssa` and `gdp`, current and first-release q/q |
| `fetch/fetch_bazg.py` | BAZG open-data bucket | goods by partner (Total 1), TOTAL2/TOTAL2_PRE2012/GOLD_SITC971 from the CTCI5 SITC files, gold imports 7108.12 |
| `fetch/fetch_markets.py` | Yahoo (`official: false`) | SMI year-end closes 2005–2026 |
| `fetch/fetch_comparables.py` | World Bank, UNDP, IMF (`official: false`) | GDP US$, GDP/person, population, reserves, openness, Gini, HDI, GGXWDG_NGDP |

## Re-running the fetchers

Every fetcher was re-run from cache with `python3 -I` in consolidation,
twice. All asserts passed together and the second run was
**byte-identical** to the first. Against the swarm's original output, the
only value changes are three deliberate layout fixes that the data tests
required:

- `wages_from_bfs.csv`: `base` is written as `2010=100`, so the row key is
  (year, base).
- `projection_from_bfs.csv`: sorted by year, then scenario.
- `gold_from_bazg.csv`: `month` is written as `YYYY-MM`.

Everything else that changed is comment text (the corrections below).

Cache behaviour, for whoever refreshes:

- **BFS** resolves every DAM asset number online on each run, about 45 s
  with the 1.5 s spacing. The master file is cached by damId, so a new
  edition is a new download. The PxWeb caches (`cache/bfs_px_*.csv`)
  have fixed names: delete them to refresh.
- **BAZG** reads the bucket listing on each run, a few seconds. The 9 GB
  CTCI5 files are streamed only when no
  `cache/bazg_CTCI5_*_<etag>_monthly.csv` matches the object's current
  ETag. The cache-hit path was confirmed: the re-runs took 4 s and
  streamed nothing. A republished file has a new ETag and is streamed
  once, and the old aggregate is removed (only its own prefix).
- **SECO:** the workbook in cache was first placed by hand. Consolidation
  ran the fetcher's own `resolve()` + `get()` path live (JSON content API
  → DAM URL → xlsx). It returned a file byte-identical to the cached one
  (sha256 `7a3c16a5…`), so the cache is honest and the download path
  works. Delete `cache/seco_realtime-database.xlsx` to refresh.
- **SNB, EFV, Eurostat, comparables and Yahoo** use fixed-name caches:
  delete a file to refresh it.
  - SNB asserts that monthly cubes are recent relative to today, so a
    stale cache eventually fails loudly.
- **No fetcher deletes anything** outside its own cache prefix.
- **Dependency:** BFS and SECO need `openpyxl`.

## Corrections made in consolidation

- **GDP vintage seam is 2023, not 2021.** Fixed in the Eurostat and
  comparables fetchers (comments and the check label), in SOURCES.yaml
  and in every sidecar comment.
- **Eurostat immigration seams (new finding).** `migr_imm1ctz` CH
  excludes type changes in 2011–2022 and includes them in 2000–2010 and
  2023–2024. The comment was rewritten and four pinning asserts were
  added. The BFS flows comment was corrected too.
- **"Starts 2016" removed** from the SNB docstring, the bank-credit
  comment and the Eurostat household-debt comment (the fromDate trap).
- **The Liechtenstein claims softened** to "unconfirmed" in the SNB
  sidecars and `country.yaml`.
- **Data-test fixes**: the three layout changes listed above.

## SOURCES.yaml changes

1. **Header:**
   - Calendar-year statement, no April fiscal year.
   - Vintage seam 2023.
   - Gold: totals match between customs and BoP, the gold lines do not.
   - The Eurostat immigration seams.
   - Assisted suicide from 2003, never added.
   - Geography: Liechtenstein open.
2. **Pending:**
   - Dropped the "BoP / household FA before 2016" item.
   - Added: the Liechtenstein scope question; the spine gaps that exist
     at harmonised publishers; the statutory minimum wage (none).
   - The arrears entry now names the IMF FSI bank NPL ratio.
3. **BFS:**
   - GDP: no repeated rows in this edition, plus the gold split.
   - ILO rate annual from 2010.
   - Wage index from three bases (2006–10 from base 1993,
     `ts-x-03.04.03.00.04`).
   - Arrears: taxes 8.75%, utilities 3.86%.
   - Life expectancy by sex only.
   - Balance: holes before 1981, fixed-name PxWeb caches.
   - Permit table: 2010 = 1 Jan 2011 stock.
   - Firearm deaths and assisted suicide now described from the opened
     files (assisted suicide from 2003).
   - Projection sort order.
4. **Eurostat:**
   - GDP equal through 2022.
   - Gov: D41PAY listed, and the EFV gap explained.
   - Flows: the seams.
   - Household debt: no "2016".
   - hlth_cd_aro: TOT_IN includes non-residents.
5. **EFV:**
   - **Spending by function switched to `gfs_dashboard/cofog_int.csv`.**
   - Staatsquote 31.35.
   - The TR/TE gap against Eurostat; no interest column.
6. **SNB:**
   - bopcurra from 1983 with fromDate; Total 2 = BAZG.
   - zikrepro from 1990/2007-12 (so 2006–09 mortgage rates are covered).
   - Bank credit breaks 2006-09, 2007-12 and 2026-04.
   - FA from 1999, levels equal to Eurostat.
7. **BAZG:**
   - CTCI5 files named as the TOTAL2 source, with the 2012 break.
   - Named total lines.
   - ETag-keyed cache.
   - The gold file is 7108.12 imports only.
8. **SECO:**
   - The sidecar stops at 2026Q1.
   - URL resolution documented.
   - The hand-placed cache verified live.
9. **Markets, comparables:** no correction needed beyond the vintage
   year.

## Spot values, for checking that a rerun has not silently changed shape

- **GDP:**
  - BFS 2024 CHF 860,932mn and 2025 881,572mn; Eurostat 2024 853,957mn.
  - Real growth 2009 −1.93, 2020 −2.26, 2025 1.61.
  - SECO `gdp_cssa` q/q 2025Q3 −0.41.
- **Prices, labour, wages:**
  - LIK 2022 2.8, 2025 0.2; HICP 2015 −0.8.
  - ILO unemployment 2025 4.84%.
- **Fiscal:**
  - EFV 2024: balance +0.29% GDP, Maastricht 23.7, GFS gross 30.0,
    liabilities 40.4 (IMF 40.4), Fiskalquote 26.7, extended 37.3.
  - 2025 is a forecast.
- **Trade:**
  - 2025 TOTAL1 exports 286,840mn, TOTAL2 461,014mn (= BoP).
  - Customs gold exports 163.8bn; BoP gold receipts 149.6bn.
  - Current account 2025 +49.6bn.
- **Markets:**
  - Policy rate 2019-06 −0.75, 2026-09 0.0.
  - USD/CHF 2025 average 0.8314.
  - 10y yield 2026-09 0.586.
  - SMI end-2025 13,267.48.
- **Credit:**
  - Bank household credit Dec-2025 945,300mn.
  - FA HH+NPISH 2025 1,066,789mn; Eurostat 123.0% GDP (BFS GDP: 121.0%).
- **World:**
  - Reserves Dec-2025 US$1,075.1bn (WB 1,075.7bn).
  - WB GDP 2024 US$969.9bn; GDP/person 2025 US$114,769.
  - HDI 2023 0.970.
- **Demography:**
  - Population 31-Dec-2025 9,127,125.
  - TFR 2025 1.28.
  - e0 2025: men 82.7, women 86.3.
  - Deaths 2019 67,780, 2020 76,195.
- **Migration:**
  - Immigration (BFS) 2023 263,081; type changes 87,623.
  - Eurostat 2015 153,627 vs BFS 188,515.
  - Foreign citizens 1-Jan-2025 2,478,134; foreign-born 2,870,124.
- **Security and mortality:**
  - Homicide (PKS completed) 2024 45 (= Eurostat), 2025 55; 0.61 per 100k.
  - Suicide 2008 1,313 → 2009 1,105; assisted suicide 2024 1,774.
  - COVID deaths 2020 9,294.

## Spine coverage (PLATE_SPINE.md)

The labels used below:

- **Staged**: the series is in a sidecar.
- **Computable**: built from staged sidecars on one vintage and one scope.
- **Fetch**: exists at a harmonised publisher, probed live 2026-10-22,
  not yet staged.
- **Unavailable**: genuinely does not exist, so `ctx.pending` with the
  reason.

| Topic · slot | Status | From |
|---|---|---|
| economy 1 real GDP growth | staged | BFS ACPP (national) + Eurostat beside (old vintage 2023+) |
| economy 2 GDP per person US$ | staged | WB NY.GDP.PCAP.CD (old vintage 2023+) |
| economy 3 CPI + target | staged | LIK + HICP; SNB price stability = 0–2% (a band, not a point) |
| economy 4 unemployment | staged | BFS ILO rate + Eurostat lfsa_urgan; SECO registered as a note |
| fiscal 1 revenue / expenditure | staged | Eurostat TR/TE (canonical) + EFV beside |
| fiscal 2 balance + primary | staged / computable | Eurostat B9; primary = B9 + D41PAY |
| fiscal 3 gross debt | staged | IMF GGXWDG_NGDP (= EFV liabilities); Maastricht in the note |
| fiscal 4 interest | staged | Eurostat D41PAY |
| spending 1 COFOG stacked | staged | Eurostat gov_10a_exp + EFV cofog_int |
| spending 2 social protection vs rest | staged | same (note: compulsory insurance is outside government) |
| spending 3 GFCF whole economy | computable | BFS P51G ÷ BFS GDP (WB NE.GDI.FTOT.ZS not staged) |
| spending 4 public investment | **fetch** | Eurostat gov_10a_main P51G S13 (2022–25: 2.9–3.2% GDP) |
| trade 1 exports / imports % GDP | computable | BFS P6/P7 ÷ BFS GDP (gold incl.; ex-gold line beside) |
| trade 2 trade balance | computable | same |
| trade 3 top export destinations | computable | BAZG partners ÷ TOTAL1 (Total 1 basis, say so) |
| trade 4 lens | staged | gold: Total 1 vs Total 2, BAZG gold file, BoP gold |
| markets 1 policy rate vs inflation | staged | SNB snboffzisa (range to 2019-05, rate from 2019-06) + LIK |
| markets 2 10y yield | computable | SNB rendeiduebm, annual mean of months |
| markets 3 currency vs US$ | computable | SNB USD/CHF, inverted to an index 2006 = 100, up = stronger |
| markets 4 equity in US$ | computable | Yahoo SMI × SNB USD/CHF; S&P 500 from the shared series |
| credit 1 household debt % GDP | **fetch** | BIS WS_TC Q.CH.H.A.M.770.A (2025-Q4 122.9); Eurostat nasa and SNB FA are staged beside |
| credit 2 lending vs policy rate | staged | SNB new mortgages (2009-05+) / offered variable (1990+), two lines |
| credit 3 NPL | **fetch** | WB FB.AST.NPER.ZS = IMF FSI bank NPL ratio (2024 0.83%, all bank loans, not households) |
| credit 4 lens | staged | SILC arrears (survey of people), bank vs all-lender stock |
| people 1 Gini | staged | Eurostat SILC + BFS HABE (×100) + WB |
| people 2 poverty | staged + fetch | BFS absolute + Eurostat AROP; WB US$8.30 line (SI.POV.UMIC) throttled, unconfirmed |
| people 3 minimum wage | **unavailable** | Switzerland has **no statutory national minimum wage** (rejected in the 2014 vote). Some cantons have one (Neuchâtel, Jura, Ticino, Geneva, Basel-Stadt), so `ctx.pending` says exactly that, as Italy's does |
| people 4 lens | staged | arrears, wages, the HABE transfers |
| world 1 GDP US$ bn | staged | WB NY.GDP.MKTP.CD |
| world 2 HDI | staged | UNDP HDR25 |
| world 3 corruption (TI CPI) | staged | TI CPI 2025 workbook, comparable 2012–2025 method |
| world 4 reserves | staged | SNB snbimfra + WB |
| demography 1 population index | staged | BFS balance; projection A-00-2025 as a note |
| demography 2 TFR | staged | BFS |
| demography 3 crude birth / death rates | computable | BFS balance ÷ mean population |
| demography 4 natural increase / net migration | computable | BFS balance (net incl. type changes, say so) |
| security 1 homicide rate | staged + fetch | PKS completed per 100k (staged); WB VC.IHR.PSRC.P5 UNODC to fetch (2023 0.60) |
| security 2 suicide rate | computable | BFS Suizid ÷ population; 2008/09 assisted-suicide seam |
| security 3 road deaths | computable | BFS "Strassenverkehrsunfälle" ÷ population (2024: 221 deaths) |
| security 4 lens | staged | firearm deaths (mostly suicides), attempts vs completed, assisted suicide |
| mortality 1 crude death rate | computable | BFS balance |
| mortality 2 excess deaths | computable | BFS balance deaths vs 2015–19 mean |
| mortality 3 COVID per 100k | computable | BFS causes COVID-19 ÷ population |
| mortality 4 lens | staged | BFS causes (dementia, cancers, assisted suicide) |
| migration 1 immigration / emigration | computable | BFS flows ÷ population, labelled "incl. change of population type" |
| migration 2 net migration | computable | same |
| migration 3 foreign-born share (+ foreign citizens) | computable | Eurostat pop3ctb (2011+ only) / pop1ctz (1998+) |
| migration 4 lens | staged | type changes / S status, permits, asylum, naturalisations |

**To fetch before Phase B draws those slots** (rule 11): Eurostat P51G,
BIS WS_TC, WB FB.AST.NPER.ZS, WB VC.IHR.PSRC.P5, and a retry of WB
SI.POV.UMIC.

- Add them to `fetch_eurostat.py` / `fetch_comparables.py`, with sidecars
  and manifest entries.
- BIS needs a small helper (there is no BIS fetcher in this lane).

**Genuinely unavailable:** a statutory national minimum wage, and a
household loan-delinquency register. The arrears survey is the lens
instead, and the bank-wide NPL ratio is the canonical slot.

## Pending (all in `SOURCES.yaml` `meta.pending` unless noted)

1. **SEM direct.** The yearly asylum statistics are now PDFs only, and
   SEM's opendata.swiss sets are stale at 2019. Covered by Eurostat
   (SEM reports to it) and BFS STATPOP.
2. **The SECO registered-unemployment rate** (amstat v2 answers 404). The
   counts are staged via BFS, and the real-time database's `ur_*` sheets
   are not parsed.
3. **A household arrears register.** None exists, so the SILC survey is
   staged instead.
4. **stooq ^smi** is JS-walled. It would only be a cross-check.
5. **IMD/WEF competitiveness comparisons** (optional; neither is a
   canonical page slot). TI CPI is already staged.
6. **Liechtenstein scope of the SNB cubes**: read the SNB notes per cube.
7. **The spine gaps listed above** (fetch).
8. **Minimum wage**: none statutory (a true statement for slot 3).
9. *(not in meta)* The WB and Eurostat GDP-based ratios move once those
   publishers take the 2026-08-25 BFS revision. The BFS fetcher's
   2006–2022 equality assert will not catch the change; the
   Eurostat/comparables spot checks for 2023–2025 will.
10. *(not in meta)* The SECO workbook lags a quarter (to 2026Q1). Re-run
    `fetch_seco.py` after SECO refreshes it.

## Phase B notes (core decisions; not done here)

- **The `de` locale is new to the repository:**
  - Every `AFFIX` spec in `core/sitebuild.py` needs a `de` column. The
    current columns are en/fr/pt/es/ko. Suggested values:
    - `pct` / `pct2` / `pct_s` → `("", " %")` (German spaces the sign).
    - `pct_gdp` → `("", " % des BIP")`.
    - `pop_mn` → `("", " Mio.")`.
    - `per100k` → `("", "/100 000")`.
    - `years` → `("", " Jahre")`.
    - `rank` → `("Nr. ", "")` or `"#"`.
    - `usd_bn` → `("", " Mrd. US$")`.
  - `SEPARATORS` needs a `de` entry, and `core.i18n` needs the same rule
    on the plates.
  - The `de` column also needs `site/ui.json` chrome and an i18n
    catalogue.
  - Today `test_every_locale_can_be_formatted[switzerland]` fails with
    "spec 'pct' has no form for ['de']".
- **CURRENCY_AFFIX needs `CHF`.** Today
  `test_the_currency_is_one_the_site_can_write[switzerland]` fails.
  Suggested values:
  - `money_bn`: en `("CHF ", "bn")`, de `("", " Mrd. CHF")` (or
    `("CHF ", " Mrd.")`), pt `("CHF ", " bi")`.
  - `money`: en `("CHF ", "")`, de `("CHF ", "")`, pt `("CHF ", "")`.
- **The Swiss thousands separator.** de-CH writes 1'234'567.8, with an
  apostrophe (U+2019 or ') for thousands and a point for decimals. The
  generic German rule is 1.234.567,8. **Recommendation:**
  - Pages: use the Swiss convention, a `de` SEPARATORS entry of
    `{",": "’"}` with the point kept. That is how BFS, SNB and every
    Swiss reader writes numbers.
  - Data: BFS's own workbooks carry `36'728` strings, which the fetcher
    already parses.
  - Why not generic German: it would look foreign in Zurich and would
    collide with nothing, since no other country uses `de` today.
  - If Germany or Austria arrives later, this becomes a locale-region
    hook (`de-CH` vs `de-DE`). It is the same question Portugal raised
    for pt-PT and pt-BR, so decide both together.
  - The decision is the user's, because it is a core change.
- **German names for every country.**
  `test_the_comparison_names_every_country_in_every_language` needs
  `name.de` in every other country's `country.yaml`:
  - Frankreich, Brasilien, Vereinigte Staaten, Südkorea, Argentinien,
    Kanada, Spanien, Portugal, Vereinigtes Königreich, Italien, Japan,
    Vietnam.
  - That is a cross-lane change, made at merge, not here. Switzerland's
    own `name` block already carries de and the others.
- **Plates:** the spine coverage above.
  - Every SNB panel names its scope as the SNB (Liechtenstein question).
  - Every BAZG panel names the customs area.
  - Every Eurostat ratio panel names the old GDP vintage from 2023.
- **events.py candidates:**
  - Franc floor introduced 2011-09-06 and removed 2015-01-15.
  - Negative rates 2014-12 / 2015-01.
  - Libor → SNB policy rate, 2019-06.
  - S status activated, 2022-03.
  - Credit Suisse rescue, 2023-03.
  - Gold into special trade, 2012-01.
  - Assisted-suicide coding change, 2009.
  - BFS GDP revision, 2026-08-25.
  - US tariffs on Swiss goods and the gold flows of 2025.

## Tests at consolidation

- **Without Switzerland:**
  `python3 -m pytest tests/ -q -k "not switzerland" --ignore=tests/test_site.py`
  gives **363 passed**, the baseline.
- **Switzerland's own** (`-k switzerland --ignore=tests/test_site.py`):
  **38 passed, 19 failed.** Every failure is a later-phase file:
  - Catalogs ×6: no `i18n.json`.
  - Core ×2: no `de` AFFIX column, and no CHF in `CURRENCY_AFFIX`.
  - Isolation ×3, layout ×6 and sources ×2: no `plates.py`,
    `chapters.py` or `provenance.json`.
- **The data tests now all pass.** Two real failures were fixed in the
  fetchers:
  - Projection years out of order.
  - Duplicate keys in the wages and gold files.
- **Full run:** 431 passed, 27 failed, 111 errors.
  - All 111 errors are `test_site.py` fixtures, which raise
    `ModuleNotFoundError` on `countries/switzerland/chapters.py` and so
    error every country's site tests.
  - The test_site failures are Switzerland's chapter/plate tests plus
    three cross-country comparison tests, all for the same reason; the
    comparison-names test also needs `name.de` everywhere.
- **JS:** 20/20.
- **No spine test:** this branch predates `plate-spine`, so it has no
  `tests/test_spine.py`.

## State of the branch

This session added only `countries/switzerland/`. Nothing in `core/`,
`site/` or another country's directory was touched. `cache/` and
`__pycache__/` are gitignored and not committed. `output/` is empty.
