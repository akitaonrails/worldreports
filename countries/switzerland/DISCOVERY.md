# Switzerland — Phase A discovery report (2026-10-22)

**Delivered (uncommitted, in the `switzerland` lane as instructed):**
- `countries/switzerland/country.yaml`
- `countries/switzerland/SOURCES.yaml`: 60 planned datasets across 11 target directories, plus 6 `meta.pending` entries. It was written before any CSV exists, and every URL in it was curled live today.

**Verification.** Both files parse as YAML. Without `test_site.py`, the rest of the suite (`-k "not switzerland"`) gives **363 passed**, so the baseline still holds.

Switzerland's own run gives 36 passed. The failures are the expected Phase A set: no `i18n.json`, `data/`, `provenance.json` or `chapters.py` yet. Two of them are real cross-phase items, both caused by the new `de` locale and CHF:
- `test_every_locale_can_be_formatted[switzerland]`: "spec 'pct' has no form for ['de']".
- `test_the_currency_is_one_the_site_can_write[switzerland]`: "currency 'CHF' has no per-language form".

---

## Publishers (all probed live 2026-10-22)

### BFS / OFS — Federal Statistical Office (the workhorse)
Two machine channels. Both are verified, and each has quirks.

1. **STAT-TAB PxWeb v1**: `https://www.pxweb.bfs.admin.ch/api/v1/de/{db}/{db}.px`.
   - Root catalogue: 643 databases.
   - A GET returns metadata JSON. A POST with a JSON query and `"response":{"format":"csv"}` returns CSV in **Windows-1252**.
   - Rate limits: **HTTP 429 lockout** after a burst of about 30 calls in 10 s. Some databases exist only under `/de/` (`/en/` answers HTTP 400). The STATPOP-by-permit table is **slow**: one national query took 92 s, and a 3-year query timed out at 90 s.
   - Tables verified with data:
     - Demographic balance `px-x-0102020000_101`, 1971–2025, with 16 components. Schweiz 2025: 1 Jan 9,051,029, births 78,153, deaths 71,904, immigration 204,261, emigration 133,829, 31 Dec **9,127,125**.
     - Police crime statistics (PKS) `px-x-1903020100_101`, 2009–2025. Completed homicides: 2024 = 45, 2025 = 55. **Attempts run four times higher** (2025: 251).
     - STATPOP by permit `px-x-0103010000_101`. In 2025, 65,260 people with S status were counted in the *permanent* population.
     - Population scenarios 2025–2055 `px-x-0104000000_101`.
     - Immigration and emigration detail `px-x-0103020200_*` and `_0103020300_*`.
   - GDP, the CPI and income are **not** in PxWeb.
2. **DAM asset API**: `https://dam-api.bfs.admin.ch/hub/api/dam/assets?orderNr=<asset number>` finds the current `damId`, then `/hub/api/dam/assets/{damId}/master` downloads the file (csv or xlsx).
   - **Trap:** `orderNr` matches by **prefix** and returns versions marked OLD as well, so the fetcher must filter on the exact `shop.orderNr` and on lifecycle CURRENT.
   - Assets verified:
     - GDP `ts-x-04.02.01.02`. This is a CSV that **repeats rows**. 2024 = CHF 860.9bn, 2025 = 881.6bn, real growth 2009 = −1.9%.
     - CPI (LIK) `cc-d-05.02.08`. Annual rates: 2022 2.8%, 2024 1.1%, 2025 0.2%. **Rebased to Dec-2025 = 100.**
     - ILO unemployed vs SECO registered `je-d-03.03.00.01`. In 2006, ILO counted 195k unemployed and SECO registered 131.5k. Breaks: the RAV registration system changed in March 2018, and the 2009/10 SAKE survey break has been back-adjusted.
     - ILO unemployment rate `je-d-03.03.01.14`: 2025 = 4.84%.
     - Employment `ts-x-03.02.01.01`.
     - Wage index `ts-x-03.04.03.00.06`. The base-2020 file starts in 2021.
     - HABE Gini `je-d-20.03.01.02.02`: 2023 = 0.305.
     - Absolute poverty `je-d-20.03.02.01.01`: 2024 = 8.4%.
     - **SILC payment arrears** `je-d-20.02.04.08`: 15.4% of people had arrears of some kind in 2024, and 0.21% had mortgage arrears.
     - Births and fertility `je-d-01.04.01.01`.
     - Life expectancy `je-d-01.04.02.03.01`.
     - Causes of death for men and women `je-d-14.03.04.01.03` and `.04`. These end in 2024. Recent years are strings with apostrophe thousands separators ("36'728"), and suicide includes **assisted suicide up to 2008**.

### SNB — data.snb.ch cube API (markets, credit, reserves, BoP)
The pattern is `https://data.snb.ch/api/cube/{id}/data/csv/en?dimSel=D0(..)&fromDate=..`, with dimensions at `/api/cube/{id}/dimensions/en`. The CSV is semicolon-separated with a BOM, starts with a 2-line header (CubeId, PublishingDate), and leaves an empty Value where a series has no data. There is no public cube list; I took the 186 cube ids from a CKAN mirror.

Verified cubes:
- **`snboffzisa`**: two instruments, which must never be drawn as one line. The 3-month Libor target range runs to 2019-05; the policy rate `LZ` runs from 2019-06 (−0.75 then, 0 since 2025-06).
- **`devkua` / `devkum`**: exchange rates in CHF per EUR or USD, so a rising line means a weaker franc. EUR averaged 1.5729 in 2006 and 0.9370 in 2025. The 1.20 floor and its removal on 2015-01-15 are visible in the monthly data.
- **`rendeiduebm`**: the 10-year Confederation yield, 2006-01 = 2.153 and 2026-09 = 0.586.
  - **Trap:** `rendoblim`, `rendoblid` and `rendopar` froze at 2025-07 (last published 2025-09-01) but still answer HTTP 200.
- **`zikreddet`**: new-loan rates from 2009-05. `zikrepro` starts only in 2025-08 (it is a new survey).
- **`bakredsekbrm`**: bank loans to households. Dec-2006 CHF 524.3bn, Dec-2025 945.3bn.
- **`frsekgevehup` / `frsekphupooe`**: financial-accounts household debt from all lenders. 2025 = 1,051.0bn. Starts in **2016**.
- **`snbimfra`**: reserves, US$1,075.1bn in Dec-2025, equal to the World Bank figure.
- **`bopcurra`**: the BoP current account, starting in **2016**. In 2025 gold was 149.6bn of 461.0bn goods receipts.

### EFV / FFA — Federal Finance Administration (fiscal)
Static CSVs at `https://www.data.finance.admin.ch/static/assets/datasets/...`.

`fs_dashboard/main_extern.csv` covers general government plus the Confederation, cantons, communes and social security, in both the FS and GFS models, for 1990–2030. It has a source column (Rechnung, Prognosen, Budget), and its ratios are fractions rather than percentages.

**For 2025 the fiscal data is still marked Prognosen (forecast).** For 2024 there are four debt figures for general government, all correct:

| Measure | Source | 2024, % of GDP |
|---|---|---|
| Maastricht debt | EFV | 23.7 |
| GFS gross debt | EFV | 30.0 |
| GFS total liabilities | EFV | 40.4 |
| GGXWDG | IMF | 40.4 |

There are also two tax ratios: 26.7% and an "extended" 37.3%, which adds compulsory health-insurance and occupational-pension contributions.

`fir_art_funk.csv` (spending by function) and `gfs_dashboard/cofog_int.csv` are listed. Eurostat's EDP tables do **not** cover CH (the geo dimension has size 0).

### SECO
`realtime-database.xlsx` holds one vintage matrix per variable.
- openpyxl needs `read_only` plus `reset_dimensions()`, and a normal load fails on a missing drawing.
- The latest vintage in the file is 2026-06-01, which lags SECO's newest release by a quarter.
- `gdp_cssa` is GDP adjusted for **major sporting events**. FIFA, IOC and UEFA licence revenue booked in Switzerland moves GDP in championship years.
- The `amstat.ch` v2 site answers 404. SECO's registered-unemployment counts are available through the BFS table instead.

### BAZG / FOCBS — customs (trade)
Data comes as CSVs on `ocean.bazg.admin.ch/open-data-reports/…`: semicolon-separated, served as octet-stream. The scope is the **Swiss–Liechtenstein customs area**.
- `SA_COUNTRY_EXP/IMP` covers 1995-01 to 2026-09. **One period column mixes months (1–12) and quarters (24–27)**, so summing every row doubles the total. There is no World row.
- `TN8_controlCode_Gold_IMP` covers gold from 2021.
- The trade chapter rests on the split between **Total 1 (excluding gold) and Total 2 (including gold)**.

### Eurostat (EFTA coverage, verified per dataset)
**Present for CH:**
- National accounts: `nama_10_gdp` (unit must be `CP_MNAC`; `CP_MCHF` returns an empty cube) and `namq_10_gdp`.
- Government: `gov_10a_main`, `gov_10a_exp`, `gov_10a_taxag`.
- Prices and labour: `prc_hicp_aind`, `lfsa_urgan` (1996+; `une_rt_a` starts in 2010).
- Income: `ilc_di12` (2014+), `ilc_li02`. `ilc_li02` no longer has an `indic_il` dimension and answers HTTP 400 if one is sent.
- Population: `demo_gind`, `demo_find`, `demo_mlexpec`.
- Crime and causes of death: `crim_off_cat` ICCS0101 (2008–2024, equal to PKS completed homicides) and `hlth_cd_aro`. The assault code is **`X85-Y09_Y871`**; plain `X85-Y09` returns an empty cube. Assault deaths in 2022 were 35, against 42 police-recorded homicides.
- Financial accounts: `nasa_10_f_bs`. Household loans were 105.7% of GDP in 2006 and 123.0% in 2025.
- **The full §4a migration suite:**
  - `imm1ctz` 1998–2024, equal to BFS and including status changes.
  - `imm3ctb` 2011+.
  - `emi1ctz`.
  - `pop1ctz`: `citizen=FOR` returns an empty cube, so use `FOR_STLS`.
  - `pop3ctb` 2011+.
  - `asyappctza`: `unit=PER` works for CH.
  - `asydcfsta`.
  - `resfirst`, with **2019 and 2020 missing**.
  - `resvalid`, `migr_acq`, `migr_eipre`.

**Absent:**
- `gov_10dd_edpt1` and `gov_10dd_ggd` (geo dimension size 0).
- `irt_lt_mcby_a`.

**Vintage trap:** for 2021 and later, Eurostat's Swiss GDP is the **previous BFS vintage**: 2024 = 854.0bn against BFS 860.9bn. Every Eurostat ratio for CH therefore uses the old denominator.

### Comparables (all `official: false`)
- World Bank (CHE): GDP 2024 US$969.9bn and 2025 US$1,043.5bn, on the old vintage. On the BFS vintage, 2024 is about US$978bn. **Magnitude check passed: about US$1tn.**
- World Bank population, 2025 mid-year: 9,092,436. **Magnitude check passed: about 9.1mn.**
- World Bank Gini: 33.5 in 2023, then null.
- UNDP HDR25 HDI: 0.970 in 2023, rank 2. The file is Latin-1 and needs a browser User-Agent.
- IMF DataMapper `GGXWDG_NGDP/CHE`: 40.4 in 2024, with projections to 2031.

### Yahoo `^SSMI` (`official: false`)
Monthly from 2005-01.
- Yahoo needs the short User-Agent `Mozilla/5.0 (X11; Linux x86_64)`. Both a full Chrome User-Agent and the default curl one got HTTP 429.
- **Timestamp trap:** bar timestamps are Zurich midnight expressed in UTC, so a naive conversion labels every bar one month early.
- Verified December closes: 2006 8,785.7 · 2008 5,534.5 · 2024 11,600.9 · 2025 13,267.5.
- stooq is JS-walled (a 796-byte page under HTTP 200).

## The five Swiss traps (they head SOURCES.yaml)
1. **GDP vintages.** BFS revised on 2026-08-25; Eurostat and the World Bank have not caught up.
2. **Gold in trade.** Total 1 and Total 2 differ, and gold was CHF 150bn of goods receipts in 2025.
3. **Immigration includes changes of status.** The 2023 figure of 263k is largely Ukrainians with S status passing 12 months.
4. **Assisted suicide.** It moved out of suicide from 2009.
5. **Four debt measures and two tax ratios.**

There are also several smaller ones:
- The policy instrument changes between the Libor target range and the policy rate.
- Survey and register unemployment are different series.
- Homicide attempts are four times the completed count.
- Some SNB and financial-accounts series start in 2016.
- The geography differs: Liechtenstein is inside the BAZG and SNB data.

## country.yaml decisions
- **Locales: `de` (de-CH) first, then `en` (default, per repo precedent), then `pt` (pt-BR).** German is the majority language and the one BFS publishes first. French and Italian are noted as easy additions later. `name` covers en, fr, pt, es, ko and de, plus `it: Svizzera` because Italy is adding that locale. The wordmark is `Schweiz`; "Helvetia" was considered and rejected.
- **Bands.** I dated them from quarter-on-quarter real GDP, checking SECO `gdp_cssa` against Eurostat `namq_10_gdp`:
  - `2008.75–2009.25`: 2008 Q4 and 2009 Q1, SECO −2.1 and −1.5.
  - `2020.0–2020.5`: COVID.
  - **The franc-floor removal on 2015-01-15 is an EVENT, not a band.** 2015 Q1 is −0.0 at SECO and −0.3 at Eurostat, a single quarter at most.
  - Also not banded: 2011 Q3, 2016 Q4, 2018 Q3, 2023 Q2 and 2025 Q3, each a single negative quarter.
- **Palette.** One hue like Canada's. The red is `#B01E2D`, a cooler crimson darkened from the flag's #DA291C. Its companions are cool alpine colours: slate `#2A3F55`, glacier blue `#3A6F96`, fir green `#3F6E45`, lake teal `#1E7A74`, plus gold and purple. The flag bands are red, paper, red.
- **Web chrome.** A neutral graphite ground `#14171B`, distinct from Canada's red-black `#1A1012` and Spain's `#1E1210`. Money is accented in red `#E46A5E`.
- **Window** 2006–2026, `last_full_year: 2025`, `tick_every: 2`, currency CHF. `seo.spatial` is Switzerland; the comment there says Liechtenstein is inside the BAZG and SNB data and must never share a line with Switzerland-only series.

## Pending list (`meta.pending`, none blocking)
1. **SEM direct.** The site loads, but its yearly asylum statistics now come only as PDFs, and its opendata.swiss datasets point at a 2019 archive. Covered for now by Eurostat (which SEM reports to) and BFS STATPOP.
2. **SECO amstat registered-unemployment rate.** The v2 site answers 404. The counts come through BFS, and the real-time database has `ur_*` sheets that have not been parsed yet.
3. **Household arrears register.** None exists, so the BFS SILC payment-arrears survey is staged in its place.
4. **SNB balance of payments and household financial accounts before 2016.** The API does not serve them. Eurostat `nasa_10_f_bs` provides the long series, drawn beside the SNB figures and never spliced.
5. **stooq `^smi`.** JS-walled; it would only have been a cross-check.
6. **Transparency International, IMD and WEF.** To be curated by hand at build phase.

Also unopened but listed as CURRENT: firearm deaths (`je-d-14.03.04.01.13`) and assisted suicide (`je-d-14.03.04.01.14`). I have not verified mortgage rates for 2006 to 2009-04.

## For Phase B and the fetch swarm (recorded only, no action taken)
- **`de` is a new locale.**
  - It needs a `de` column in every `AFFIX` spec in `core/sitebuild.py`, plus a `CHF` entry in `CURRENCY_AFFIX`. Suggested values:
    - `pct_gdp` → `("", " % des BIP")`.
    - `pop_mn` → `("", " Mio.")`.
    - `per100k` → `("", "/100 000")`.
    - `years` → `("", " Jahre")`.
    - CHF `money_bn` → en `("CHF ", "bn")`, de `("CHF ", " Mrd.")`, pt `("CHF ", " bi")`.
  - Swiss German writes thousands with an apostrophe (1'234) and decimals with a point. That is a new separator rule; decide whether to follow it or use the generic German one.
  - `site/ui.json` needs `de` chrome.
  - **Every other country's `country.yaml` needs `name.de`**, or `test_the_comparison_names_every_country_in_every_language` fails.
- **Fetchers named in `refreshed_by`:**
  - New: `fetch_bfs.py` (PxWeb and DAM, cp1252, 429 back-off, exact orderNr plus CURRENT), `fetch_snb.py` (cube CSV; assert the latest month is recent), `fetch_efv.py`, `fetch_seco.py`, `fetch_bazg.py` (months only).
  - Reused: `fetch_eurostat.py` with GEO="CH", `fetch_comparables.py` with ISO3=CHE plus the IMF, and `fetch_markets.py` with `^SSMI`, Zurich time and the short User-Agent.
- Every fetcher should check the shape of what it pulled before caching: Eurostat's empty cubes under HTTP 200, frozen SNB cubes, BFS duplicate rows, apostrophe-number strings, and EFV's Prognosen rows.
