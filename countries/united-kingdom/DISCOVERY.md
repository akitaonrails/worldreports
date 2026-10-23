# United Kingdom — Phase A discovery report

> Kept as the research-pass record. Several first guesses here were corrected by the fetchers and the consolidation pass (JW2V is not receipts; CVZH/CVZI are both S.14; HF6W is £bn; the ONS admin-based migration series runs back to YE June 2012; FY 2020-21 PSNB is now −£310.8bn; recrime-geo-pfa.csv is a lookup). `SOURCES.yaml` and `DATA_NOTES.md` are authoritative where they differ.

**Delivered (uncommitted, in the lane as instructed):**
- `country.yaml`
- `SOURCES.yaml` — 45 planned datasets across 11 target directories + 6 pending entries, written before any CSV exists; every URL curl'd live today (2026-10-22)

**Verification:** both files parse as YAML. `python3 -m pytest tests/ -q -k "not united" --ignore=tests/test_site.py` → **363 passed**. The UK's own failures are exactly the expected Phase A set: missing `i18n.json`/`data/`/`provenance.json`/`chapters.py` (later phases), plus one real cross-phase item — `test_the_currency_is_one_the_site_can_write[united-kingdom]` fails because **GBP has no `CURRENCY_AFFIX` entry in `core/sitebuild.py`** (additive core change needed in a later phase, Canada's CAD entry is the template; flagged in a country.yaml comment). 36 UK tests already pass (palette, name-in-all-locales, manifest conventions, official-flag consistency).

---

## Publishers (all probed live 2026-10-22)

### ONS — the workhorse (economy, prices, labour, fiscal outturn, population, vital stats, mortality, inequality, credit, migration)
Three distinct machine channels, all verified:

1. **The timeseries generator** — `https://www.ons.gov.uk/generator?format=csv&uri=<theme>/timeseries/<cdid>/<dataset>`. Header block (title, CDID, source dataset, release date) then one row per period; the annual frequency returns annual rows directly. Verified CDIDs: `YBHA` (nominal GDP £m; 2024 = £2,905.0bn ✓ vs WB US$3,695.5bn at ~1.28 avg USD/GBP), `ABMI` (CVM quarterly), `IHXW` (GDP/head), `L55O` (CPIH annual rate), `D7G7` (CPI), `MGSX` (LFS unemployment), `LF24` (employment), `KAB9` (AWE weekly pay), `J5II` (PSNB ex, **negative = borrowing**; calendar 2020 = −£269.9bn ✓ vs FY 2020-21 ≈ £322bn), `JW2V` (current receipts), `HF6W`/`HF6X` (PSND £m / %GDP), `IKBH`/`IKBI` (exports/imports G&S, BoP, dataset MRET), `HBOP` (current account, dataset PNBP), `CVZH`/`CVZI` (household debt-to-income — **both carry the identical title "Households (S.14)…"; one is S.14+S.15 and the fetcher must disambiguate and assert**). A `.../timeseries/<cdid>/<dataset>/data` JSON variant also works (that's how the bands were dated). Rate limits: ons.gov.uk answers Cloudflare error 1015 under rapid fire — space requests.
2. **Bulletin dataset xlsx** — per-edition files under `/file?uri=...`. Verified: mid-year population estimates (`/mid2025/mye25tablesuk.xlsx`, 200 — **the `/current/` symlink 404s for this dataset and for LTIM but works for the homicide tables; resolve editioned paths from the dataset page, never hardcode `/current/`**); birth summary tables and Series DR deaths-by-cause (per-year editions 2006–2025; pre-2010 editions are legacy `.xls` with `tcm77` names); national life tables UK (`nltuk198020223.xlsx`, 3-year pooled windows); household income inequality (to FYE2025, UK scope, FYE key); homicide appendix tables (E&W, **YE March**); LTIM migration spreadsheet (see below).
3. **The beta API** (`api.beta.ons.gov.uk/v1`) — catalog works (338 datasets) but is **stale**: `mid-year-pop-est` stops at mid-2022 editions, `tax-benefits-statistics` latest version is dated 2022-09. The `trade` dataset is current (v65, 2026-02) but `/observations` did not answer within 60s even single-month/single-country (its 400-on-bad-dimension error listing valid dims is well-behaved). Use bulletin xlsx for population/inequality; uktradeinfo for trade.

### Bank of England — IADB + monthly tables (markets, credit)
- IADB CSV: `https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp?csv.x=yes&Datefrom=…&Dateto=…&SeriesCodes=<CODE>&UsingCodes=Y&VPD=Y&VFD=N` — **302-redirects** (fetcher must follow), then `application/csv`, `dd-Mmm-yyyy` dates. Verified: `IUDBEDR` Bank Rate (0.75 Jan-2020 ✓), `XUDLUSS` USD per GBP (1.3189 02-Jan-2020 ✓ — **falling line = weaker pound, opposite of Canada's USDCAD direction**), `XUDLBK67` sterling ERI (80.6 ✓), `IUDMNPY` 10y gilt zero-coupon (0.85 Jan-2020 ✓), `IUMZICQ` 2y-fixed 60%-LTV mortgage quote (4.48 Jan-2025; description pulled verbatim via `html.x=yes`). **A bogus series code returns an HTML page under HTTP 200** — shape-check the header row. `IUMTLMV` answers (7.48 Jan-2025) but its product description is unverified — pending in the manifest.
- Money & credit release xlsx: `/-/media/boe/files/statistics/money-and-credit/2026/tables-a-and-k-august-2026.xlsx` (Tables A–K; Table G = lending to individuals; monthly **stocks**, never summed). Note: `LPQAUYN` looked like household debt and is actually quarterly M4 (£3.1tn) — verified description; do not use.

### Home Office (migration, asylum, police-recorded crime)
- **gov.uk content API** is the enumeration layer: `https://www.gov.uk/api/content/government/statistical-data-sets/immigration-system-statistics-data-tables` → 48 xlsx attachments on `assets.publishing.service.gov.uk` (verified direct download of the 12MB asylum-claims file): asylum claims / awaiting-decision / outcomes, entry-clearance visas, sponsorship, settlement, citizenship (naturalisations), returns, detention, EU settlement, illegal-entry-routes. Stable slug + content API → never hardcode media URLs.
- Police recorded crime: `police-recorded-crime-and-outcomes-open-data-tables` — its offence tables are large ods workbooks of rolling quarters by force area; `recrime-geo-pfa.csv` is only a force-area **geography lookup** (no counts), used by the fetcher solely to assert the 43 territorial forces of England & Wales.
- Irregular migration collection verified (`/government/collections/irregular-migration-to-the-uk-statistics`). Detections-of-arrivals caveat applies verbatim (event ≠ person).

### HMRC uktradeinfo (trade by partner)
OData v4 at `https://api.uktradeinfo.com/OTS` — `$metadata`, `Country` codelist (400 = United States), `$filter` on MonthId(yyyymm)/FlowTypeId/CountryId/CommodityId all sub-second; `$count` ≈ 505,681 rows/month at full granularity → fetcher aggregates; one filtered probe returned a suspicious 2.0 cell, so the total/sentinel-id conventions (-990 class) must be pinned with a magnitude assertion in the fetcher. Customs-value goods only — never spliced with the BoP series.

### Eurostat (harmonised layer — patchier than documented)
Verified per-dataset today: **dropped entirely** (well-formed EMPTY, not 404): `nama_10_gdp`, `gov_10dd_edpt1` (EDP fiscal!), `une_rt_a` (LFS), `ilc_di12` (Gini); **frozen at 2019**: `prc_hicp_aind`, migration flows (`migr_imm1ctz` 1998–2019 with a 2005 hole; 2019 immigration 680,906, emigration 368,385), stocks (`migr_pop1ctz` 1999–2019; 66,647,112 in 2019), asylum (`migr_asyappctza` 2019: 44,315 first-time/46,130 total), naturalisations (`migr_acq` 2019: 159,348); permits `migr_resfirst` stop a year earlier (2008–**2018**) and have **no sex dimension** (sex=T → 400 INVALID_QUERY_DIMENSION); **still current**: `demo_gind` (population 1960–2026; 2026 = 69,554,275) and `irt_lt_mcby_a` (Maastricht yield 1984–2024). **Endpoint trap verified**: adding `unit=PER` (Spain's fix) to UK migration queries collapses the unit dimension to size 0 under HTTP 200 — drop it for UK slices; fail loudly on empty either way.

### Comparables (all `official: false`)
- World Bank GBR: all six Canada-pattern indicators verified (GDP 2024 US$3,695.5bn; population 69,281,000; openness 62.8%; reserves US$174.6bn; GDP/person 53,341; **gini 2023/2024 null — it lags, holes stay holes**).
- UNDP HDR25 composite file: GBR `hdi_2023` = 0.946 ✓.
- **IMF DataMapper API** (new for this country): `https://www.imf.org/external/datamapper/api/v1/GGXWDG_NGDP/GBR` — history from 1980, forecasts to 2031 (mark as projections). This is the harmonised fiscal layer the UK no longer gets from Eurostat; never spliced with ONS PSF.

### Yahoo Finance (FTSE 100, `official: false`)
`query1.finance.yahoo.com/v8/finance/chart/%5EFTSE` — monthly closes 2005–2026; year-ends verified: 2007 = 6,456.9 · 2024 = 8,173.0 · 2025 = 9,931.4. Price index only (FTSE's dividend yield is among the highest of major indices — plate must say so).

### ONS migration (the three regimes)
LTIM spreadsheet verified downloading from the editioned path (`/yearendingdecember2025/may2026publicationspreadsheet.xlsx`). Regimes: (1) IPS era → Eurostat segment 1998–2019; (2) admin-based (Home Office visas + DWP RAPID) from YE June 2021; (3) the late-2025 revisions embodied in the current vintage. Reference periods are **YE June/December, not calendar years**. Segments, never a splice.

## country.yaml decisions

- **Bands** — dated empirically off ONS `ABMI` q/q, current vintage (release 2026-09-29), pulled and computed today: `2008.25–2009.5` (five consecutive negatives), `2020.0–2020.5` (Q2 −19.9%), **`2023.5–2024.0` — the shallow late-2023 technical recession (−0.16, −0.26) meets the two-quarter rule and is banded**. Explicitly not banded, on the same evidence: the 2012 double-dip (revised away — single negative quarters Q2/Q4), 2021 Q1 (single), the 2016 post-vote slowdown (never two in a row).
- **Palette** — Union Jack red/white/blue: `#B32438` red (darkened off #C8102E), navy `#1B2E63` primary / mid-blue `#2E5FA3` (lifted off #012169, which is nearly ink), paper middle `flag_bands` (auto-outlined). Cool navy-black web chrome (`#0D1220`) distinct from USA's blue and Canada's/Spain's warm blacks; `mark_bearing 0.06em` (U, as USA's wordmark) and the two-word `mark_size` clamp.
- Locales en (default) + pt; window 2006–2026; `last_full_year 2025`; `tick_every 2`; `fiscal_year` convention (April–March) required for PSF, PESA, HBAI, homicide — same trap as Canada/USA.

## Pending list (in `SOURCES.yaml` under `meta.pending`, none blocking)

1. **OBR** — 403 Cloudflare on every route tried (`/data/`, historical-forecasts xlsx, browser UA). Forecasts only; outturn is ONS PSF.
2. **DMO** — page loads but data links are JS/AJAX-assembled; no static endpoint found. Not needed for v1 (debt stock = ONS PSND).
3. **stooq ^FTSE** — JS proof-of-work wall (same as ^TSX/^IBEX); Yahoo used.
4. **ONS beta `trade` observations** — >60s at usable granularity; uktradeinfo used.
5. **NRS / Scottish Government / PSNI / NISRA** — no UK-wide crime or cause-of-death series exists; v1 declares the **E&W scope** on security/mortality plates (UK-wide births/deaths possible but the ONS UK vital-statistics reference tables lag at 2021).
6. **Transparency International CPI** — hand-curation at build phase, as France/Canada.

## For the fetch swarm

Planned fetchers (named in `refreshed_by`): `fetch_ons.py` (generator CDIDs + bulletin xlsx), `fetch_boe.py` (IADB + money-and-credit xlsx), `fetch_homeoffice.py` (gov.uk content API → xlsx), `fetch_dwp.py` (HBAI), `fetch_hmt.py` (PESA), `fetch_uktradeinfo.py` (OData), `fetch_eurostat.py` (UK residual coverage), `fetch_comparables.py` (WB + UNDP + IMF), `fetch_markets.py` (Yahoo). Every fetcher must shape-check before caching (BoE HTML-under-200 for bad codes, Eurostat empty-cube-under-200, ONS `/current/` 404s, uktradeinfo suppressed cells) and leave FY/calendar, S.14/S.14+S.15, and segment boundaries exactly as the manifest's notes describe.
