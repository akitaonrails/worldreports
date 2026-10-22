# United Kingdom — handoff

Written 2026-10-22: research pass, fetch swarm and consolidation. Branch
`united-kingdom`. This session produced the research, the sources
manifest, nine fetchers and the staged sidecars. It did **not** produce
plates, chapters, i18n, ui, events or tests. Because `country.yaml`
exists, the shared test suite discovers the UK and fails on those
missing files. That is expected. The check that nothing else broke is
`python3 -m pytest tests/ -q -k "not united" --ignore=tests/test_site.py`
(459 passed at consolidation; `test_site.py` builds the whole site in a
fixture, so a country without `chapters.py` errors every country's site
tests, not just its own). The UK's own data and manifest checks in
`test_data.py`/`test_sources.py` pass, except the two that read
`provenance.json`. The full run at consolidation was 560 passed,
24 failed, 111 errors, and every one traces to a missing `chapters.py`,
`plates.py`, `i18n.json` or `provenance.json`, or to the GBP affix
below. JS: 20/20.

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md) and
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) first. They
are not background reading. They are the specification.

---

## What is done

`countries/united-kingdom/` holds:

- `country.yaml`: locales en/pt, default en, window 2006–2026,
  last_full_year 2025, tick_every 2, and three recession bands dated off
  the q/q sign of ONS ABMI (2008–09, COVID, and the shallow late-2023
  recession). It also has a Union-Jack-derived palette and en/pt seo and
  sources blocks.
- `SOURCES.yaml`: written before the CSVs, then corrected to what the
  fetchers do. It has one entry per staged dataset, with units stated for
  the sidecars that carry no `#` header, and `meta.pending` for the
  sources that could not be staged.
- `DATA_NOTES.md`: the traps and the cross-source table.
- `DISCOVERY.md`: the research pass's report, kept as a record.
  `SOURCES.yaml` and `DATA_NOTES.md` override it where they differ.
- 45 staged sidecars under `data/`, every one a `*_from_<source>.csv`.
  Nothing is curated yet.

Every fetcher was re-run from cache with `python3 -I` in consolidation.
All their asserts pass together, and the output is byte-identical to the
first run. The one exception is a deliberate comment fix in
`homicide_deaths_from_ons.csv` (the Y33.9 break).

| Fetcher | Publisher | What it pulled |
|---|---|---|
| `fetch/fetch_ons.py` | ONS generator CSV + bulletin xlsx | GDP (YBHA/ABMI/IHXW), CPIH/CPI, LFS unemployment/employment, AWE (+ computed real), PSNB/PSND/receipts/TME on calendar and fiscal keys, BoP trade + current account, S.14 debt-to-income, mid-year population (UK + 4 nations), E&W births/deaths/rates, UK life tables, Gini (FYE), 21CM homicide by certificate, DR/21CM causes by ICD-10 chapter, LTIM admin-based migration |
| `fetch/fetch_boe.py` | Bank of England IADB (+ Tables A–K xlsx to pin codes) | Bank Rate, USD/GBP and ERI, 10y zero-coupon gilt, 2y-fixed 60% LTV and revert-to-rate mortgage quotes, lending-to-individuals stocks (December) |
| `fetch/fetch_homeoffice.py` | Home Office via gov.uk content API; ONS homicide appendix | asylum (applications / initial decisions / grants / withdrawn / backlog), visas by route, settlement, citizenship, irregular detections, Homicide Index (YE March) |
| `fetch/fetch_dwp.py` | DWP HBAI | relative low income BHC/AHC, 2002/03–2024/25 |
| `fetch/fetch_hmt.py` | HM Treasury PESA 2026 | Table 4.2 spending by function + TME, 2003-04–2025-26 |
| `fetch/fetch_uktradeinfo.py` | HMRC uktradeinfo OData | customs goods trade with ten partners, 2006–2026 (2026 = 8 months) |
| `fetch/fetch_eurostat.py` | Eurostat, geo=UK | the frozen migration suite to 2019 (flows both cuts, stocks both cuts, asylum, permits to 2018, acquisitions) and demo_gind/demo_find |
| `fetch/fetch_comparables.py` | World Bank, UNDP, IMF DataMapper | GDP US$, GDP/person, population, reserves, openness, Gini, HDI, IMF gross debt and net lending (+ projections in their own columns), all `official: false` |
| `fetch/fetch_markets.py` | Yahoo Finance (`official: false`) | FTSE 100 year-end closes 2005–2026 |

## Spot values, for checking that a rerun has not silently changed shape

- GDP 2024 **£2,904.95bn** nominal (YBHA), 2025 £3,044.6bn; WB 2024
  US$3,695.5bn
- CPIH 2022 **7.9%**, CPI 2022 9.1%; unemployment 2025 4.9%
- PSNB ex: calendar 2020 **−£269.9bn**, FY 2020-21 **−£310.8bn**; PSND ex
  Dec 2025 £2,924.5bn = 94.2% of GDP; TME FY 2024-25 £1,290.3bn (PSF)
  vs £1,290.0bn (PESA)
- Bank Rate 2023 eoy 5.25, 2025 eoy 3.75; 10y gilt 2020 avg 0.37, 2025
  avg 4.58; USD/GBP 2024 avg 1.2783
- Household debt (S.14) Q4: 2007 **155.2%** → 2025 116.6%; BoE lending
  to individuals Dec 2025 £1,941.4bn
- Population mid-2025 **69,483,939** (UK); Eurostat 1 Jan 2026
  69,554,275
- E&W births 2025 585,396; deaths 2025 570,988 (2020: 607,922)
- Homicide Index currently recorded, YE March 2025 = **522**; YE March
  2024 = 566; certificate (ONS definition) 2022 = 754
- Migration (ONS, YE Dec): immigration 2023 **1,441,000**, 2025
  813,000 (P); net 2022 891,000, 2025 171,000 (P). Eurostat 2019
  immigration 680,906 / emigration 368,385
- Asylum applications (HO, persons) 2024 **104,764** (not 108,138);
  2022 95,007; small-boat detections 2022 45,774
- Citizenship grants 2024 269,806; Eurostat migr_acq 2019 159,348
- FTSE 100: 2007 close 6,456.9 · 2024 8,173.0 · 2025 9,931.4

## Pending (none blocks the build; all in `SOURCES.yaml` `meta.pending` or below)

1. **Homicide by death certificate, 2023–2025.** The 21CM file ends at
   2022, and DR publishes no all-ages assault row. Wait for the next
   21CM edition, or find an ONS registration table. Do not estimate.
2. **Switzerland in the trade-partner file.** Imports jump from £17bn
   to £43bn in 2025, almost certainly non-monetary gold. Pull the
   partner by commodity (SITC 97 / HS 7108) from uktradeinfo before
   drawing it, and decide whether to show precious metals separately.
3. **Eurostat HICP (to 2019) and the Maastricht 10y yield (to 2024).**
   These are not staged. Without the yield, the gilt series has no
   second source in the lane.
4. **Scotland and Northern Ireland** crime and causes of death (NRS,
   PSNI, NISRA). The v1 plates declare E&W scope instead.
5. **OBR** (Cloudflare 403) and **DMO** (JS-assembled). Neither is
   needed for v1.
6. **Transparency International CPI**: curate it by hand with the 2012
   break, as France and Canada do.
7. **British-national migration before YE March 2018.** The ONS cover
   sheet documents the IPS adjustment only for YE March 2018 to
   YE March 2021, and it does not say how 2012–2017 British estimates
   were made. Ask the ONS release, or read its methods article, before
   annotating that stretch.
8. **The ONS IPS-era LTIM series** (to YE March 2020) is not staged. It
   could join Eurostat's IPS segment as the national twin.

## What the next session should build

1. **The curated CSVs**, each diffed against its sidecar, with the
   window trimmed to 2006–2026 (several sidecars start earlier: Eurostat
   1960/1998, IMF 1980, PESA 2003, HBAI 2002, FTSE 2005). Their
   SOURCES.yaml entries go beside the sidecar entries.
2. **plates.py** on the declarative PLATES shape, spine-numbered, all
   twelve chapters. The departures to decide and record in DATA_NOTES:
   security and mortality are E&W scope, and must say so in the dek.
   World has no Eurostat comparisons; the IMF and WB carry it. Migration
   (12) is the reason the UK is queued. Its first panel should draw
   Eurostat to 2019 and the ONS from YE June 2012, with the overlap
   visible and the June 2021 seam annotated. Asylum's four numbers stay
   four series. Stocks are drawn on both cuts, with naturalisations
   beside them.
3. **Annotations the data already demands:** the LFS break (2023→), the
   HBAI 2021/22 seam, the Y33.9→U50.9 break in 2007, MUSE→IRIS in 2014,
   settlement-on-arrival ending May 2019, HMRC Intrastat→customs in
   2021, the PESA breaks (2010-11, 2011-12, 2015-16), USD/GBP's
   direction (a falling line is a weaker pound), and the FTSE as a price
   index.
4. **chapters.py / ui.json / events.py / i18n.json**, in en and pt.
   events.py candidates: the June 2016 referendum, January 2020 Brexit /
   end of transition in December 2020, the September 2022 mini-budget
   and gilt crisis, the post-Brexit points-based system (January 2021),
   the 2024 dependants rule changes, and the May 2024 LFS reweighting.
5. **Phase B, core change: GBP needs a `CURRENCY_AFFIX` entry** in
   `core/sitebuild.py` (en and pt forms, with Canada's CAD as the
   template). `tests/test_core.py::test_the_currency_is_one_the_site_can_write`
   requires it. It is additive only. Flag it in the commit, as Spain
   flagged its EUR `es` forms.
6. **countries/united-kingdom/tests/**: fact tests that make claims about
   the CSVs. Use the spot values above and add the no-splice guards:
   Eurostat flows blank after 2019, the ONS migration series starting
   at 2012-06, homicide certificates blank after 2022, and PSNB fiscal
   blank until twelve months exist.
7. Then `make C=united-kingdom charts thumbs provenance && make site test`,
   and the merge conversation. Merging is a decision, not a default
   (see Canada's HANDOFF).

## State of the branch

`united-kingdom` was cut from `main` at 2b0e367. This session added only
`countries/united-kingdom/`. Nothing in `core/`, `site/` or another
country's directory was touched.
