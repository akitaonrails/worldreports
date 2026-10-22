# Vietnam — handoff

Written 2026-10-22, after the research pass, the fetch swarm and the
consolidation. Branch `vietnam`, cut from `main` at 2b0e367.

This session produced the research, the sources manifest, four fetchers
and the staged sidecars. It did **not** produce plates, chapters, i18n,
ui, events or tests.

Because `country.yaml` exists, the shared test suite discovers Vietnam
and fails on the files that are missing. That is expected. To check
that nothing else broke, run:

    python3 -m pytest tests/ -q -k "not vietnam" --ignore=tests/test_site.py

At consolidation that gave 363 passed. `test_site.py` builds the whole
site in a fixture, so a country without `chapters.py` makes every
country's site tests error. JS tests: 20/20.

Vietnam's own run (`-k vietnam`) gave 38 passed and 19 failed. All
of the data and manifest checks in `test_data.py` and `test_sources.py`
pass, except the two that need plates. Every failure is one of the
expected Phase B items:

| Failing test(s) | Cause |
|---|---|
| `test_catalogs.py` ×6 | no `i18n.json` |
| `test_isolation.py::test_drawing_plates…`, `test_layout.py` ×6 (vi/en/pt) | no `plates.py` |
| `test_isolation.py::test_building_chapters…` | no `chapters.py` |
| `test_isolation.py::test_recorded_provenance…` | no `provenance.json` |
| `test_sources.py::test_every_plate_cites…`, `::test_no_plate_is_drawn_from_a_sidecar` | no plates / provenance |
| `test_core.py::test_the_currency_is_one_the_site_can_write` | `VND` has no `CURRENCY_AFFIX` |
| `test_core.py::test_every_locale_can_be_formatted` | `vi` has no `AFFIX`/`SEPARATORS` column |

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md),
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) and the
plate spine (`PLATE_SPINE.md`, `core/spine.py` once merged) first.

---

## What is done

`countries/vietnam/` holds:

- **`country.yaml`.** Locales vi/en/pt, default en, window 2006–2026,
  `last_full_year` 2025, `tick_every` 2, VND, and `bands: []`. The
  reasoning for the empty bands is in the file: no annual contraction,
  and no official seasonally adjusted q/q series. It also has the
  red/gold palette and vi/en/pt seo and sources blocks.
- **`SOURCES.yaml`.** Written before the CSVs, then corrected to what
  the fetchers do. It has one entry for each of the 51 sidecars, every
  `refreshed_by` exists, and `meta.pending` lists nine sources that
  could not be staged.
- **`DATA_NOTES.md`.** The traps, the breaks, the spine departures and
  the cross-source table.
- **`DISCOVERY.md`.** The research pass's report, kept as a record.
  `SOURCES.yaml` and `DATA_NOTES.md` override it.
- **51 staged sidecars** under `data/`, every one a `*_from_<source>.csv`.
  Nothing is curated yet.

Every fetcher was re-run with `python3 -I` after an agent's
`rm -rf cache` mid-run. The cache had already been refilled, so all
four ran from cache. All their asserts pass together: 0 failures,
including the NSO fetcher's `expect()` checks, 22 ADB checks, 53
comparables checks and 11 markets checks. Two consecutive runs are
byte-identical.

No fetcher deletes anything. There is no `rmtree`, `unlink` or
`remove` in `fetch/`. Each one writes only its own cache prefix (`nso_`,
`adb_`, `cmp_`, `cafef_`/`yahoo_`) and its own sidecars.

A warm-cache run is not fully offline. It still makes two live calls:

- `fetch_nso.py` asks the World Bank for 2024 GDP to cross-check
  per-person GDP times population.
- `fetch_comparables.py` asks Comtrade again for 2024 and 2025 on
  every run, because empty replies are not cached.

| Fetcher | Publisher | What it pulled |
|---|---|---|
| `fetch/fetch_nso.py` | NSO PX-Web, HTML JSON-stat door (API door as cross-check only) | GDP (two scales), CPI, state-budget revenue and spending, trade totals, trade by partner and group, rates and central rate, market cap, BoP, credit, population, vitals, life expectancy, labour, income quintiles, Gini (two segments), poverty (+ inferred standard), NSO HDI, justice, traffic and fire (two segments), HIV, registered deaths, internal migration |
| `fetch/fetch_adb.py` | ADB KIDB SDMX v5 (VIE) | national accounts 2005–2025 (old and new scale), general-government GFS to 2022, LFS 15+, BoP, money and credit with the NPL ratio (DF_MF_FIN folded in), and secondary-income credit as the remittance proxy |
| `fetch/fetch_comparables.py` | WB, IMF DataMapper, UNDP, UN DESA, UN WPP bulk CSV, WHO GHO/GHE, Comtrade, ADB DF_ER | the comparables layer, all `official: false` |
| `fetch/fetch_markets.py` | CafeF, Yahoo (`official: false`) | VN-Index year-end closes 2005–2026; VND=X, 275 monthly closes |

Fixes made in consolidation (no value changed; see DATA_NOTES):

- `fetch_nso.py` now sorts rows by year and drops columns that are
  blank in every year, naming them in the CSV header.
- `fetch_adb.py` writes `break_flags` only when some observation is
  flagged.
- A V14.01 population-vintage comment was corrected.

## Spot values, for checking that a rerun has not silently changed shape

- GDP 2024 **11,510,329 bn VND** (revalued scale); 2009 1,809,149
  (old scale). WB US$: 2009 106.0bn (old scale), 2010 147.2bn, 2024
  476.3bn. IMF back-cast: 2009 129.0bn. Real growth 2024 7.04, 2025
  8.02.
- CPI (prev. year = 100): 2008 **122.97**, 2025 103.31.
- State budget revenue 2024 2,057,544 bn VND = 17.9% of GDP. IMF gross
  debt 2024 31.2%.
- Exports 2023 **354,721** US$mn (Comtrade 353,078); US exports 2025
  153,135.
- Central rate 2025 24,977.2 (blank for 2015–17). VN-Index 2024
  **1,266.78**, 2025 1,784.49. VND=X Dec 2025 26,225.
- Population 2024 **101,343.75** thousand; TFR 2024 1.91; life
  expectancy 2021 = 2022 = 73.642.
- Gini 2019 0.423 → 2020 0.375; poverty V14.46 2016 5.8 vs V14.01 9.2.
- Traffic deaths 2021 5,790 → 2022 **13,551**; WHO road 2019 23.5 per
  100k.
- Registered deaths 2022 725,035; WHO GHE COVID-19 2021 85,608.
- Credit to the economy 2025 18,598 tn VND; NPL (IMF FSI) 2024 4.85.
- Emigrant stock 2024 **3,693,537**; secondary-income credit 2025
  19,766 US$mn.

## Spine coverage (PLATE_SPINE.md)

The labels used in this section:

- **Staged** means the indicator is in a sidecar now. Some slots still
  need a rate computed or an index built at plate time.
- **Fetch** means a harmonised or official source exists and should be
  added to a fetcher before the plate is drawn (spine rule 11). Each one
  was spot-checked live on 2026-10-22.
- **Unavailable** means the indicator genuinely does not exist. The slot
  takes `ctx.pending` or a stated substitute.

### economy
1. **Real growth.** Staged: NSO 2009+, ADB 2005–08 (continuous, no seam).
2. **GDP per person, US$.** Staged: WB, with the 2010 scale seam drawn
   as two segments.
3. **CPI.** Staged: NSO V11.08. The inflation **target** line (the
   National Assembly's annual ~4–4.5%) is **not staged**. Hand-curate it
   from the yearly resolutions.
4. **Unemployment.** Staged: NSO working age 2010+, with ADB 15+ beside
   it from 2005.

### fiscal
1. **Revenue and expenditure, % of GDP.** Staged general government:
   ADB to **2022** only. The IMF's GGR/GGX are empty in DataMapper.
   **Fetch**: the WEO full-database file (or IMF GFS) for 2023–2025 GG
   revenue and expenditure. Without it, the NSO state-budget ratios
   (2018+) ride beside a GG line that stops in 2022.
2. **Overall and primary balance.** Staged: IMF net lending to 2031
   (projections apart), and ADB net lending plus primary balance
   (GXOPB) to 2022. An IMF primary balance is not in DataMapper, so the
   primary line ends in 2022 unless the WEO file is fetched.
3. **Gross debt.** Staged: IMF GGXWDG. The MOF's public-debt definition
   is pending.
4. **Interest paid.** Staged: ADB GG interest, bn VND, to 2022 (divide
   by the revalued GDP). **Fetch**: WEO or GFS for 2023+.

### spending
1. **By function, stacked.** Staged: NSO budget heads, not COFOG. %-of-GDP
   heads exist for 2018+; levels from 2005 (2006 missing). Five of the
   seven COFOG groups map cleanly: education, health, social
   protection, economic affairs, general public services/administration.
   **Defence + public order: unavailable.** Vietnam's budget tables do
   not publish them.
2. **Social protection vs the rest.** Staged: the NSO "đảm bảo xã hội"
   head, with the note that it is a budget head.
3. **Investment rate (GFCF).** Staged: NSO V03.01 capital formation and
   fixed assets, % of GDP.
4. **Public investment.** Staged: ADB GG net investment in nonfinancial
   assets to 2022, and the NSO development-investment head (state
   budget) as the national line.

### trade
1. **Exports and imports of goods and services, % of GDP.** Staged: NSO
   V03.01 national-accounts ratios, with WB openness as a check.
2. **Balance.** Staged: computed from slot 1.
3. **Top export destinations.** Staged: NSO V09.06 by partner, divided
   by the TỔNG SỐ row.
4. **Lens.** Staged: V09.14 groups, and the US surplus against the China
   deficit (V09.06/V09.12).

### markets
1. **Policy rate vs inflation.** **Unavailable as a machine series.**
   The SBV shows only today's rates. IMF SDMX MFS_IR answers 403, and
   BIS WS_CBPOL has no VN key (404, while TH returns data). Hand-curate
   the refinancing-rate history from SBV decisions (`meta.pending`).
2. **10-year government bond yield.** **Not staged. Fetch**: ADB
   AsianBondsOnline publishes VN government yields by tenor. Its
   endpoint was not probed in this session.
3. **Currency vs US$, index 2006 = 100.** Staged: WB/IMF annual average
   (2006–2024). Use the NSO central rate or ADB end-period for 2025,
   and Yahoo for the market quote. Invert so that up means stronger.
4. **Equity index in US$.** Staged: VN-Index year-end (CafeF) ÷ FX. The
   S&P 500 comparison line is not in this lane.

### credit
1. **Household debt, % of GDP.** **Unavailable.** There is no household
   series. BIS WS_TC has no VN key (404, where TH returns data). The
   substitute is credit to the economy as a % of GDP (NSO 2015+, ADB
   claims on the private sector 2005+, WB to 2022), recorded as a
   departure.
2. **Lending rate vs policy rate.** Staged: NSO V03.21 average lending
   rates 2015+, for all borrowers rather than households. **Fetch**:
   ADB DF_MF_FIN `FILR_PA` (lending rate 2005–2023). It is already in
   `cache/adb_DF_MF_FIN.csv`, so add one CREDIT row to `fetch_adb.py`.
   WB FR.INR.LEND also answers (2023 9.32). The policy rate is the
   gap from markets slot 1.
3. **NPL ratio.** Staged: ADB/IMF FSI 2008–2024.
4. **Lens.** Staged: credit growth, M2/GDP, and credit by currency and
   tenor.

### people
1. **Gini.** Staged: NSO ×100 in two segments (2019/2020 step), with
   the WB consumption Gini beside it.
2. **Poverty.** Staged: national V14.46 by standard, with V14.01 beside
   it. **Fetch**: the WB **US$8.30/day** line (SI.POV.UMIC answers: 2022
   21.5, 2018 24.2). Only the $3/day line (SI.POV.DDAY) is staged.
3. **Minimum wage, US$/month.** **Not staged. Fetch**: ILOSTAT
   statutory minimum wage, or hand-curate from the government decrees.
   Vietnam's minimum is **regional** (four regions), so the slot needs
   a stated choice, such as Region I.
4. **Lens.** Staged: informal employment rate, income quintiles (Q5/Q1).

### world
1. **GDP, US$ bn.** Staged: WB with the seam, and IMF continuous.
2. **HDI.** Staged: UNDP, with the NSO's own HDI beside it.
3. **Corruption Perceptions Index.** **Pending**, hand-curated
   (Transparency International, `meta.pending`).
4. **Reserves.** Staged: WB FI.RES.TOTL.CD.

### demography
1. **Population, index.** Staged: NSO V02.02, with the WPP projection
   for the note.
2. **TFR.** Staged: NSO (full precision) and WB.
3. **CBR and CDR.** Staged: NSO survey rates, with WPP beside them.
4. **Natural increase and net migration per 1,000.** Staged: NSO natural
   increase, plus WPP/WB net migration ÷ population. 2006's +482k is an
   artefact.

### security
1. **Homicide rate.** **The national series is unavailable**: Vietnam
   publishes no homicide count. Staged: UNODC via WB (2001–2011), the
   WHO model (2000–2021), and WHO GHE interpersonal violence (to 2023).
2. **Suicide rate.** Staged as a model only: WHO GHE self-harm (level 3,
   2000–2023). **Fetch** the WHO/WB crude rate (SH.STA.SUIC.P5 answers:
   2021 7.3) for the same-definition comparable. A national series is
   unavailable.
3. **Road deaths per 100k.** Staged: NSO police counts ÷ NSO population,
   in two segments at 2022, with the WHO RS_198 model beside them.
4. **Lens.** Staged: prosecutions, indictments and trials (V14.77), and
   fire.

### mortality
1. **Crude death rate.** Staged: NSO (survey-based), with registered
   deaths and WPP beside it.
2. **Excess deaths vs 2015–2019.** **No registration baseline.**
   Registered deaths start in 2018, and their 2022 peak is
   late-registration lag. Computing from the survey CDR × population is
   possible, but it is a survey, so label it so. Otherwise the slot
   takes `ctx.pending`.
3. **COVID-19 deaths per 100k, underlying cause.** **No national
   cause-of-death register.** Staged: the WHO GHE modelled COVID-19
   series (2021 85,608). **Fetch**: WHO's reported COVID-19 deaths
   (the WHO dashboard CSV) as the reported line beside the model.
4. **Lens.** Staged: HIV/AIDS deaths, WHO causes.

### migration
1. **Immigration and emigration per 1,000.** **Unavailable.** Neither
   flow is published. DOLAB contract-worker departures are pending a
   hand-curation from year-end reports (a flow of departures, not
   emigrants).
2. **Net migration per 1,000.** Staged: WPP/WB ÷ population.
3. **Foreign-born share.** Staged with caveats: the UN DESA immigrant
   stock (citizenship plus refugees, not birth) ÷ population, as
   five-yearly points.
4. **Lens.** Staged: emigrant stock by destination, secondary-income
   credit (a remittance superset), internal migration.

## Pending (none blocks the build; all in `SOURCES.yaml` `meta.pending` or above)

1. **SBV policy-rate history**: hand-curate it. It also feeds credit
   slot 2.
2. **SBV direct FX and monetary statistics**: covered by the NSO and ADB.
3. **Customs direct (GDC)**: times out. Covered by NSO V09.* and
   Comtrade.
4. **MOF public-debt bulletin and budget outturn**: the national debt
   definition. The 2025 spending "Ước tính" (25.8% of GDP vs 18.7%)
   needs the quyết toán before any claim is made.
5. **DOLAB labour-export flows**: hand-curate.
6. **MPS crime and homicide**: there is no national series. The gap is
   named on the plate.
7. **NSO NSDP page** (`nsdp.nso.gov.vn`): it may carry SDMX quarterly
   GDP and monthly CPI.
8. **Transparency International CPI**: hand-curate it with the 2012
   break.
9. **VN-Index from HOSE**: CafeF is staged instead.
10. **Spine fetches from the coverage list above**: WEO GG
    revenue/expenditure/interest 2023+, the 10y yield
    (AsianBondsOnline), ADB `FILR_PA`, WB SI.POV.UMIC, the minimum wage
    (ILOSTAT or decrees), WB/WHO suicide rate, WHO reported COVID
    deaths, and the CPI target.
11. **Comtrade 2024–2025**: not yet loaded at the UN. The fetcher picks
    them up automatically.
12. **ADB DF_MF_FIN market cap** (CM_MKT_LCAP_GD_ZS, 2008–2025): it is
    in the cache but not staged. Add it if the markets plate needs
    market cap before 2018.

## What the next session should build

1. **The curated CSVs**, each diffed against its sidecar and trimmed to
   2006–2026. Several sidecars start earlier: NSO 1990/1995/1998/2000,
   IMF 1980, WHO 2000. The WPP projection runs to 2100 and belongs in a
   note only. Their SOURCES.yaml entries go beside the sidecar entries.
2. **plates.py** on the spine. It carries the departures above (credit to
   the economy; modelled mortality; security without a homicide count;
   emigration-led migration) and these annotations:
   - the 2010 GDP-scale seam;
   - the Gini 2019/2020 step;
   - the poverty standards (2016, 2022);
   - the traffic 2022 reclassification;
   - the carried 2021 life-expectancy value;
   - ICLS 19 from 2021;
   - BPM6 from 2014;
   - the USD-deposit 0% cap from 2016;
   - VND per USD, where rising means weaker.
3. **chapters.py / ui.json / events.py / i18n.json** in vi, en and pt.
   Candidates for events.py:
   - the 2008 inflation shock (CPI +23%);
   - the 2011 Resolution 11 stabilisation;
   - the 2019 GDP revaluation;
   - the 2021 Q3 Delta lockdown;
   - the 2022 bond and property crisis (Vạn Thịnh Phát, Tân Hoàng Minh);
   - the 2025 abolition of the two-child policy;
   - the 2025 provincial merger (63 → 34).
4. **Phase B core changes**, additive only and flagged in the commit:
   - a **`VND` `CURRENCY_AFFIX`** entry (forms suggested in
     DISCOVERY.md);
   - a **`vi`** column in `AFFIX`/`SEPARATORS` (`.` thousands, `,`
     decimals);
   - `vi` strings in `site/ui.json`;
   - a `vi` entry in every other country's `name:`.
5. **`countries/vietnam/tests/`**: fact tests that use the spot values
   above, plus no-splice guards:
   - `_old_scale` blank from 2010;
   - `_revalued` blank to 2009;
   - `gini_*_2020_on` blank before 2020;
   - `traffic_*_from2022` blank before 2022;
   - Comtrade with no zero years.
6. Then `make C=vietnam charts thumbs provenance && make site test`, and
   the merge conversation.

## State of the branch

This session added only `countries/vietnam/`. Nothing in `core/`,
`site/` or another country's directory was touched. `cache/`, `output/`
and `__pycache__/` are git-ignored and not committed.
