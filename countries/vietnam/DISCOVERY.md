# Vietnam discovery: final report

> Kept as the research pass's record. Where it disagrees with
> `SOURCES.yaml` or `DATA_NOTES.md` (both corrected at consolidation),
> those two are right. Notably: every NSO number now comes through the
> HTML door, the WPP API answers 401, WHO causes run to 2023, and the
> UN DESA destination order is US, Japan, Australia, Taiwan, Korea, Canada.

Phase A is done. The deliverables are written in the lane and **not committed** (`git status` shows only `?? countries/vietnam/` and this file):

- `countries/vietnam/country.yaml`: slug `vietnam`, locales `vi` (first) + `en` (default, per precedent) + `pt`, window 2006–2026, `last_full_year: 2025`, `tick_every: 2`, VND, **`bands: []`** with the reasoning in a comment, a red/gold palette from the flag with a gold-tinted dark web chrome, and vi/en/pt seo and sources blocks. `name` is given in en/fr/pt/es/ko/vi; the wordmark is the endonym `Việt Nam`.
- `countries/vietnam/SOURCES.yaml`: written before any CSV. It plans 51 `*_from_<source>.csv` sidecars across 12 directories and adds 9 `meta.pending` entries. Every endpoint was curled live on 2026-10-22. The two traps that run through the whole manifest (the NSO's two PX-Web doors and the 2010 GDP-scale break) are written up in the header.

**Verification.** Both YAMLs parse (51 planned sidecars, 9 pending entries).
- **Rest of the suite:** `pytest tests/ -k "not vietnam" --ignore=tests/test_site.py` gives **363 passed**. `test_site.py` errors for every country because the site build sideloads `countries/vietnam/chapters.py`, which does not exist yet. That is the documented manifest-only state, the same as the Spain, Italy and Portugal lanes.
- **Vietnam's own tests:** 36 pass (palette, names, seo, manifest conventions, official-flag consistency). The rest fail only in the expected Phase A set: no i18n/chapters/plates/data/provenance yet. Two of those failures are real Phase B items rather than missing files:
- `test_the_currency_is_one_the_site_can_write[vietnam]`: VND has no `CURRENCY_AFFIX`.
- `test_every_locale_can_be_formatted[vietnam]`: `vi` has no `AFFIX`/`SEPARATORS` column.

Nothing is committed.

## Publishers (name · datasets · verified endpoints · payload · quirks)

**Cục Thống kê: National Statistics Office (NSO, ex-GSO, now under the Ministry of Finance).** It covers GDP, CPI, the state budget (republished from the MOF), trade (republished from Customs), interest rates, the central rate, credit and the BoP (republished from the SBV), labour, population, vitals, income, Gini, poverty, justice and traffic safety, and HIV.
- **`gso.gov.vn` no longer resolves.** The site is `www.nso.gov.vn`, and the database is PxWeb 2019 at `pxweb.nso.gov.vn`. A machine path exists. The lead's assumption that there would be no API was wrong, but only half the database is on the API.
- **Door 1, the JSON API** (`/api/v1/vi/<db>/<table>.px`; GET for metadata, POST for a query). It exposes only *Dân số và lao động* (population and labour), industry, investment, enterprise and education. National accounts, prices, trade and social tables 404 there. `json` and `csv` work; `json-stat2` 404s. **Trap: it rounds to SHOWDECIMALS, so the TFR (V02.15) comes back as "2" for every year.** The CSV is Windows-1252 with the labels destroyed.
- **Door 2, the HTML table pages** (`/pxweb/vi/<db>/<db>/<table>.px/`) cover every database. They are ASP.NET WebForms with `__VIEWSTATE`. To export: GET the page, POST every `ValuesListBox` option with `OutputFormatDropDownList=FileTypeJsonStat` and `ButtonViewTable`. The reply is a JSON-stat v1 attachment at full precision, UTF-8 with a BOM and **a trailing NUL byte**. A bad path lands on `/ErrorGeneral.aspx` under HTTP 200, so assert the content-disposition header. `FileTypePX` works but is iso-8859-15 and lossy. A working form-driver was written and used for every table below (scratchpad, not committed). The fetch swarm should port it into `fetch/fetch_nso.py`.
- **Tables verified with data today:**

  | Table | Contents | Spot values |
  |---|---|---|
  | V03.01 | GDP | 2024 = 11,510,329 bn VND; 2025 = 12,847,571; US$/person 2024 4,700 → ≈US$476bn, equal to the World Bank |
  | V03.13-14 / V03.15 | budget revenue | 2024 2,057,544 bn VND = 17.9% of GDP |
  | V03.16 / V03.17 | budget expenditure | 2024 2,148,477 bn VND = 18.7% of GDP |
  | V03.19 | credit | 2025 18,598 tn VND ≈ 145% of GDP |
  | V03.20 | BoP | 2018–2025 |
  | V03.21 | rates and central rate | central rate 2015–2025, 2025 = 24,977.2 |
  | V03.26 | market cap | 2018–2025 |
  | V11.08 | CPI, previous year = 100 | 2008 122.97; 2025 103.31 |
  | V09.01 | trade totals | exports 2023 354,721 US$mn vs UN Comtrade 353,078 |
  | V09.06 / V09.12 | trade by partner | US 2025 153,135 |
  | V09.14 / V09.15 | trade by group, services | |
  | V14.01 | NSO's own HDI | 2023 0.746 vs UNDP 0.766 |
  | V14.29 | income quintiles | |
  | V14.38 | Gini | |
  | V14.46 | poverty | |
  | V14.77 / V14.78 | justice | |
  | V14.86 / V14.87 | traffic and fire | |
  | V14.19 | HIV | |
  | V02.02 (API) | population | 2024 = 101,343.75 thousand |
  | V02.11 | CBR/CDR | |
  | V02.15 | TFR | 2024 1.91 |
  | V02.17 | infant mortality | |
  | V02.24 | life expectancy | |
  | V02.34 | registered deaths | |
  | V02.35 | labour force | |
  | V02.46 | informal employment | |
  | V02.59 | unemployment | |
  | V02.21-23 | internal migration | |

- **Quirks.**
  - Year labels carry status ("Sơ bộ 2025" is preliminary, "Ước tính 2025" an estimate).
  - The yearbook tables stop at 2025; 2026 exists in press releases only.
  - V03.01 lacks 2003–2008.
  - V03.16 lacks 2006.
  - USD deposit rates are all 0.00, and that is real: the SBV cap has held since 2015.
  - Footnote pages are empty. The PX `NOTEX` field does carry notes: the poverty-standard changes, and the GDP revaluation note on V03.01.
  - China is labelled "CHND Trung Hoa" in the trade tables.
  - The trade blocs overlap.
- **Breaks found:**
  - **GDP revaluation from 2010.** 2009 is on the old scale, 2010+ on the new.
  - **Gini falls from 0.423 to 0.375 between 2019 and 2020.** No footnote explains it, so it is annotated as an undocumented step and drawn as two segments.
  - **Poverty standard redefinitions** in 2016 and 2022. V14.01 and V14.46 disagree on 2016 (9.2 vs 5.8).
  - **Traffic deaths jump from 5,790 to 13,551 in 2022.** Accidents double while minor collisions fall, which points to reclassification.
  - **Life expectancy is identical in 2021 and 2022** (73.64), a carried value.

**State Bank of Vietnam (sbv.gov.vn).** Policy rates, FX, monetary statistics.
- An F5 WAF returns "Request Rejected" under **HTTP 200** to a bare curl. A full browser header set passes.
- Pages show **current values only**: refinancing 4.50%, rediscount 3.00%, central rate 25,632 on 2026-10-22, and today's interbank fixings. There is no history and no download.
- `/can-can-thanh-toan-quoc-te` returns 403. `dttktt.sbv.gov.vn` times out. The IMF SDMX MFS_IR returns 403.
- Covered via the NSO republications (V03.19/20/21). The policy-rate history is on the pending list.

**Ministry of Finance, Customs, Treasury.**
- `mof.gov.vn` is a Vite SPA with an undocumented `/api/`.
- `customs.gov.vn` resolves, but the connection times out on every path.
- `kbnn.vn` and `vst.mof.gov.vn` never connected.
- None of these blocks a chapter, because the NSO republishes the budget and Customs trade.

**Asian Development Bank: KIDB.** This is the strongest new comparables source.
- The lead's KIDB endpoint is live, behind an **SDMX v5 API**: `https://kidb.adb.org/api/v5/sdmx/data/ADB,<DF>/A..VIE?format=sdmx-csv&startPeriod=2005`. It is undocumented in HTML (the doc page is JS); the routes come from `/js/web.js`.
- The economy code is **VIE**, not VNM. `data.adb.org` is behind Cloudflare.
- It republishes the NSO's figures with `DATA_SOURCE` set to "National Statistics Office", and it fills the NSO's holes: GDP 2005–2009 on the old scale, with the footnote saying so.
- Dataflows verified:

  | Dataflow | Contents |
  |---|---|
  | DF_NA | national accounts |
  | DF_GOV_FIN | general-government GFS 2014, 2005–**2022** |
  | DF_MF_MON | M2, claims on the private sector |
  | DF_MF_FIN | NPL ratio 2008–2024; market cap |
  | DF_ER | FX average and end of period |
  | DF_GLOB_BOP | BoP 2005–2025; equals the NSO for 2018+ |
  | DF_PRI | CPI |
  | DF_LFE | labour; unemployment 15+ from 2005 |
  | DF_PPSI_POP | population |
  | DF_PPS_POV | poverty |
  | DF_EXT_DEBT | external debt |

- There is no quarterly national-accounts series: a Q key returns the annual rows.
- Every entry is `official: false` (it is a redistributor).

**World Bank WDI** (`api.worldbank.org/v2/country/VNM/...`, updated 2026-10-08). All entries are `official: false`.
- Values:
  - GDP: 2024 US$476.3bn, 2025 US$514.7bn.
  - Population: 2024 101.0mn (UN WPP, not the NSO).
  - Openness: 173.9% in 2024.
  - Reserves: 2025 US$85.6bn.
  - Official FX rate: 2006–2024.
  - Gini, poverty and national-headcount survey years: 2006–2022.
  - Net migration (WPP): its 2006 value of **+482,399** is an artefact.
  - Private credit to GDP: ends 2022.
- **It carries the GDP scale seam:** US$106.0bn in 2009, then US$147.2bn in 2010 (+39%).
- **Personal remittances are empty for Vietnam** (BX.TRF.PWKR.CD.DT has no data; the %GDP version stops in 2004).
- Homicide (VC.IHR.PSRC.P5) covers 2001–2011 only.

**IMF DataMapper.**
- Indicators: GGXWDG_NGDP (general-government debt: 2024 31.2, 2025 30.5), GGXCNL_NGDP, and NGDPD (**back-cast across the revaluation**: 2009 = US$129.0bn), plus projections to 2031.
- **Quirks:** a "Mozilla/5.0" UA gets an Akamai 403 (curl's default UA works), and the `/VNM` path does not filter, so the reply carries all countries. GGR_NGDP and GGX_NGDP are empty.

**UNDP HDR25 CSV.** VNM HDI 2023 0.766, rank 93 (the file is Latin-1). **UN DESA migrant stock 2024 xlsx.** Emigrants born in Vietnam 2024 = **3,693,537**; immigrants 326,418, on a citizenship-plus-refugees basis. It needs a browser UA, or the server returns an HTML error page. **UN WPP API**: location 704 answers. **UN Comtrade**: Vietnam is a reporter through 2023, and the API rate-limits with 429. **WHO GHO/GHE**: road deaths (RS_198, modelled, three times the police count before 2022), homicide (VIOLENCE_HOMICIDERATE, 2000–2021, about 1.8), and causes of death (xmart GHE_FULL, 2000–2021). This is the only cause-of-death source for Vietnam, and it is modelled.

**Markets** (`official: false`).
- **The lead's Yahoo `^VNI` is delisted.** `^VNINDEX.VN` returns one point, and `0P0000HY8X.VN` starts in 2020 and is wrong (2024-12 1,254.59 vs HOSE 1,266.78).
- **CafeF's JSON** (`cafef.vn/du-lieu/Ajax/PageNew/DataHistory/PriceHistory.ashx`) is verified. Year-ends: 2006 751.77, 2008 315.62, 2018 892.54, 2024 1,266.78, 2025 1,784.49.
- stooq is behind the JS wall (796 bytes). VNDirect's dchart and finfo return empty.
- `VND=X` on Yahoo is monthly from 2003-12. It is the market quote, which sits above the central rate.

## country.yaml decisions

- **`bands: []`.**
  - Annual real growth never fell below zero: the minimum is 2.55% in 2021, 2.87% in 2020, and 2008–09 ran at 5.66 and 5.40.
  - The NSO publishes no seasonally adjusted q/q series, so the two-quarter rule cannot be applied to an official number.
  - The only y/y quarterly contraction is 2021 Q3 (Delta lockdown; the NSO's first estimate was −6.17%, taken from the press release, not a table).
  - That quarter becomes an event, as do the 2008 inflation shock (CPI +23%), the 2011 stabilisation and the 2022 bond/property crisis.
- **Palette.**
  - RED `#A8261B` (primary, deep lacquer scarlet, clear of Canada, Spain and Portugal) and GOLD `#C08A14` (marigold from the star), with jade, teal, blue and navy as cool supports.
  - `flag_bands` is red/gold/red: the star laid flat as the middle band. There are three bands, as the test requires.
  - The web chrome is a gold-tinted olive-black (`#15130B`), distinct from Canada's red-black and Spain's brown.
  - The wordmark uses the two-word `mark_size` clamp and `mark_bearing 0.03em` for the diagonal V.
- **Locales.** `vi` (html `vi`, og `vi_VN`, endonym Tiếng Việt), then `en`, then `pt` (pt-BR). `default_locale: en`.
- **Fiscal layer decision.** The national layer is the NSO-republished **state budget** (cash, central plus local). The harmonised layers beside it are ADB general-government GFS (to 2022) and IMF WEO general-government debt and balance. The MOF's public-debt definition is pending. They are three concepts in three files, never spliced.
- **Spine departures, for DATA_NOTES:**
  - **Credit** becomes "credit to the economy": no household-debt series exists.
  - **Mortality** is built on modelled WHO causes plus registered deaths and HIV. There is no ICD register.
  - **Security** has no national homicide count. It uses prosecutions, police traffic deaths beside the WHO estimate, and the WHO homicide model.
  - **Migration** is emigration-led: UN DESA stock, WPP net migration, and secondary-income credit as a labelled remittance superset. The NSO's V02.21-23 is *internal* migration and is labelled so.

## Pending list (`meta.pending` in SOURCES.yaml; none of it blocks)

1. **SBV policy-rate history.** Only current values are online, and IMF SDMX returns 403. Hand-curate the refinancing-rate history from SBV decisions.
2. **SBV direct FX and monetary statistics.** Current snapshots only, and the BoP page is 403. Covered meanwhile by the NSO's V03.19/20/21.
3. **Customs direct (GDC).** The connection times out. Covered by the NSO's V09.* and Comtrade.
4. **MOF public-debt bulletin and budget outturn.** The site is an SPA, and the documents are PDFs. Covered meanwhile by the NSO's budget tables, ADB GFS and IMF WEO.
5. **DOLAB labour-export flows** (the key emigration flow). dolab and molisa time out; MOLISA's labour functions moved to MOHA in 2025. Hand-curate from year-end reports, as a flow and never on the stock axis.
6. **MPS crime and homicide.** No national series exists, and the UNODC portal downloads redirect. The gap is named on the plate.
7. **NSO National Summary Data Page** (`nsdp.nso.gov.vn`). The connection is reset. It may carry SDMX quarterly GDP and monthly CPI.
8. **Transparency International CPI.** Hand-curate, as France and Canada did.
9. **VN-Index from HOSE itself.** A React app with no endpoint. CafeF is staged instead.

## Recorded for Phase B (not done, per brief)

- **`vi` is a new locale.** It needs:
  - `AFFIX` and `SEPARATORS` columns in `core/sitebuild.py`. Vietnamese swaps marks like pt/es: `.` for thousands, `,` for decimals.
  - A **`VND` `CURRENCY_AFFIX`** entry. VND amounts carry no decimals. The NSO writes "tỷ đồng" (bn), "nghìn tỷ đồng" (tn) and "triệu đồng" (mn), with ₫ after the number. Suggested forms: `money_tn` → ("", " nghìn tỷ ₫") / en ("₫", "tn") / pt ("₫ ", " tri"), and `money` → ("", " ₫").
  - `vi` strings in `site/ui.json`.
  - **A `vi` entry in `name:` in every other country's country.yaml.** `test_catalogs` will demand it.
- **Plate font: verified.** Liberation Sans and Noto Sans (regular and bold), the faces `core/style.py` picks for Latin, carry all 90 precomposed Vietnamese letters (U+1EA0–1EF9) plus đ/Đ, ơ, ư and ₫. DejaVu Sans Mono has only 44/90, but `MONO_FONT` prefers Liberation Mono, which has 90/90. Matplotlib does not stack combining marks, so all copy must be **NFC**; the NSO's labels already are. No `SCRIPT_FONTS` entry is needed for `vi`.
- **Web chrome font.** `site/app.css` names Archivo but never loads it, so it falls back to system UI fonts. If Archivo is ever loaded from Google Fonts, include the `vietnamese` subset, which the family has.

## For the fetch swarm

- **`fetch_nso.py`.** The PxWeb form-driver (JSON-stat via the HTML door). Its rules:
  - Strip the BOM and the trailing NUL.
  - Assert the content-disposition and the dataset key.
  - Parse year and status from the labels.
  - Use the API door only for *Dân số và lao động*, and only where rounding is harmless.
- **`fetch_adb.py`.** SDMX v5 CSV with economy VIE. Honour `UNIT_MULT` and carry `FOOTNOTE`.
- **`fetch_comparables.py`.** World Bank, IMF (curl's default UA; select `VNM` from the all-country reply), UNDP, UN DESA (browser UA; check the PK magic), WPP, WHO GHO/GHE, and Comtrade (sleep between calls on 429).
- **`fetch_markets.py`.** CafeF VN-Index (assert non-empty `Data.Data`) and Yahoo `VND=X`.
- **The rule for every fetcher:** never splice the 2009/2010 GDP scales, the two poverty tables, the Gini segments, or the traffic-death segments.
