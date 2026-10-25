# Poland — discovery and route audit

Research pass 2026-10-25. This is the record of what was probed, what
answered, how it failed, what was chosen and why. `SOURCES.yaml` is the
manifest of the reviewed result; `DATA_NOTES.md` carries the judgement
calls the plates will depend on.

Every probe below was made from the lane's discovery network on
2026-10-25 with a plain research user agent, over HTTPS, and the HTTP
status recorded is what came back. Where a route failed, the failure is
part of the finding, not an excuse for the next paragraph.

---

## 1. The seven institutions, for Poland

| Role | Institution | Machine route | Result |
|---|---|---|---|
| National statistical office | GUS — Główny Urząd Statystyczny | `stat.gov.pl` publication XLSX; BDL API `bdl.stat.gov.pl/api/v1`; BDM `bdm.stat.gov.pl` | **200 on both website and XLSX**; BDL data endpoints 200, BDL metadata 429; BDM has no public API |
| Central bank | NBP — Narodowy Bank Polski | `api.nbp.pl` (FX, gold); `nbp.pl` statistics | **200 on api.nbp.pl**; **403 Incapsula** on every nbp.pl page |
| Finance ministry | Ministerstwo Finansów | `gov.pl/web/finanse`, `finanse.mf.gov.pl`, `dane.gov.pl` | **200 on gov.pl pages**; `finanse.mf.gov.pl` 302; no machine series needed (Eurostat EDP is the same notification) |
| Customs | Krajowa Administracja Skarbowa / GUS trade statistics | INTRASTAT via GUS, Eurostat Comext | **200 on Comext** — used |
| Vital statistics | GUS (births, deaths, causes) | GUS publications, Eurostat `demo_gind` / `hlth_cd_aro` | **200 both** |
| Police / justice | Policja (statystyka.policja.pl) | XLSX attachments | **200, with data to 2023** |
| Market | GPW (Warsaw Stock Exchange), redistributors | `gpw.pl/archiwum-notowan`; Yahoo; stooq | GPW 200 but per-session JS app; Yahoo returns one point; stooq JS-walled → **pending** |

The harmonised layer for Poland is Eurostat, and not as a fallback: Poland
has been an EU member since 2004, so the ESA 2010 national accounts, the
EDP notification, COFOG, the LFS, the HICP, EU-SILC, the cause-of-death
table and the eleven migration tables are all reported under a statistical
obligation. Eurostat is the publishing channel for those, and
`PLATE_SPINE.md` rule 10 makes the harmonised series canonical where
national definitions differ. World Bank, UNDP, BIS and the EBA carry the
comparables.

---

## 2. Route table — every probe, with its status

### 2.1 GUS (national statistical office)

| Route | Status | What came back | Used? |
|---|---|---|---|
| `https://stat.gov.pl/en/` | 200 | HTML portal | navigation only |
| `https://stat.gov.pl/sitemap.xml` | 200 | 2,124 URLs — used to find the macro-indicators page | yes |
| `https://stat.gov.pl/wskazniki-makroekonomiczne/` | 200 | the macro-indicators page, with three XLSX attachments | yes |
| `.../roczne_wskazniki_makroekonomiczne_cz_iii.xlsx` | 200, 516 KB | 32 sheets of annual indicators, 1989–2025 | **primary national source** |
| `.../wybrane_miesieczne_wskazniki_makroekonomiczne_cz_i.xlsx` | 200, 692 KB | monthly indicators — no policy rate, so not used | no |
| `https://bdl.stat.gov.pl/api/v1/data/by-variable/3643` | 200 | one variable, one unit | works |
| `https://bdl.stat.gov.pl/api/v1/data/by-unit/000000000000` | 200 | works | works |
| `https://bdl.stat.gov.pl/api/v1/subjects` | **429** | `API calls quota exceeded! Maximum admitted 1000 per 12 h` | blocked |
| `https://bdl.stat.gov.pl/api/v1/variables` | **429** | same quota message (Polish) | blocked |
| `https://bdl.stat.gov.pl/api/v1/units` | **429** | same | blocked |
| `https://bdm.stat.gov.pl/` | 200 | React app, no documented JSON API; `/api/v1/subjects` 404 | no |
| `https://api.stat.gov.pl/Home/ApiInfo` | 302 | redirects to BDM | no |
| `https://stat.gov.pl/sdmx/` | 404 | GUS does not run an SDMX endpoint | — |

**What the 429 means, precisely.** The BDL API is alive: the two *data*
endpoints answer. The *metadata* endpoints — the ones that list subjects,
variables and territorial units — are rate-limited per network to 1,000
calls per 12 hours, and that bucket was already exhausted when this lane
started. Without metadata, variable IDs cannot be discovered, and
`data/by-variable/3643` is only usable if one already knows that 3643 is
the right variable. The published annual workbook answers completely and
is the same publisher's own compilation, so the national series come from
it. This is recorded in `SOURCES.yaml` `meta.pending` with the retry path
(a registered `X-ClientId`, or a quieter network).

### 2.2 NBP (central bank)

| Route | Status | Note |
|---|---|---|
| `https://api.nbp.pl/` | 200 | documents FX tables A/B/C and the gold price — and nothing else |
| `https://api.nbp.pl/api/exchangerates/rates/a/usd/?format=json` | 200 | daily mid-rates, used |
| `https://api.nbp.pl/api/cenyzlota/?format=json` | 200 | gold, not needed |
| `https://nbp.pl/podstawowe-stopy-procentowe-archiwum/` | **403** | Incapsula/JS challenge body |
| `https://nbp.pl/oficjalne-aktywa-rezerwowe/` | **403** | same |
| `https://static.nbp.pl/` | 200 challenge | same wall |
| `https://statystyka.nbp.pl/` | **000** | no connection |

**Consequence, and it shaped the markets and credit chapters.** The FX
series (annual mean of the daily mid-rates) is fully available. The
policy-rate *daily* history, the monthly reserve assets, the CHF-mortgage
share and the sector-wide NPL ratio are not, because every page that
carries them is behind the challenge. The policy rate is therefore staged
as the 31 December value GUS republishes (`markets.csv`, documented as a
year-end convention, unlike the annual means the atlas uses elsewhere);
reserves are the World Bank's year-end record; the CHF share and the
sector NPL are not staged at all; and the household **lending rate** slot
is genuinely pending (see §4).

### 2.3 Eurostat (harmonised layer and, for an EU member, a publisher)

| Dataset | Status | Used for |
|---|---|---|
| `nama_10_gdp` | 200 | GDP, growth, GFCF, P6/P7, goods/services split |
| `prc_hicp_aind` | 200 | HICP |
| `une_rt_a` | 200 (2009+ for 15–74) | LFS annual average |
| `gov_10dd_edpt1` | 200 | deficit, debt |
| `gov_10a_main` | 200 | revenue, expenditure, interest, government GFCF |
| `gov_10a_exp` | 200 | COFOG by function |
| `irt_lt_mcby_a` | 200 | 10-year yield |
| `ilc_di12`, `ilc_li02` | 200 | Gini, AROP |
| `earn_mw_cur` | 200 | statutory minimum wage in PLN |
| `demo_gind`, `demo_find` | 200 | population, births, deaths, rates, TFR |
| `hlth_cd_aro` | 200 (2011+) | deaths by cause, COVID, assault, self-harm |
| `migr_imm1ctz`, `migr_emi1ctz` | 200 | registered flows |
| `migr_pop1ctz`, `migr_pop3ctb` | 200 | citizenship and birthplace stocks |
| `migr_asyappctza`, `migr_asydcfsta` | 200 (unit `PER`) | asylum |
| `migr_resfirst`, `migr_acq` | 200 | permits issued, naturalisations |
| `migr_asytpsm` | 200 (2022-03+) | temporary protection stock |
| `DS-045409` (Comext) | 200 | goods exports by partner |

Two API behaviours worth writing down because they cost time:

* **A bad filter is answered with an empty cube, not an error.** `unit=NR`
  on the asylum and permit datasets returns a well-formed JSON-stat body
  with no values. Every series in `fetch_eurostat.py` is checked for
  emptiness before it is written.
* **Pinning matters.** `migr_pop3ctb` names "all foreign-born" `FOR`,
  while `migr_pop1ctz` names "all foreign" `FOR_STLS`. Using the
  citizenship code on the birthplace dimension returns empty, which is how
  the difference was found.

### 2.4 The other harmonised bodies

| Body | Route | Status | Outcome |
|---|---|---|---|
| World Bank | `api.worldbank.org/v2/country/POL/indicator/...` | 200 | GDP, GDP per person, reserves, Gini, WHO/UNODC rates — used |
| World Bank | `FR.INR.LEND` (lending rate) | 200 with **no populated value** | nothing to stage |
| World Bank | `GFDD.SI.02` (NPL) | 200, ends **2020** | cross-check only |
| BIS | `stats.bis.org/api/v1/data/WS_TC/Q.PL.H.A.M.770.A` | 200 with `Accept: application/vnd.sdmx.data+json` (406 without) | household debt — used |
| BIS | `WS_DSR` same key | **404** | DSR not staged |
| EBA | Risk Dashboard page + data annex XLSX (Q2 2026, 6.8 MB) | 200 | NPL ratio 2014 Q4–2026 Q2 — used |
| UNDP | `hdrdata.org/api/...` | **404** (API key required) | not used |
| UNDP | `HDR25_Composite_indices_complete_time_series.csv` | 200, 2 MB | HDI to 2023 — used |
| Transparency Intl. | `transparency.org/en/cpi/2025` | **403** Cloudflare | blocked |
| Transparency Intl. | `images.transparencycdn.org/.../CPI2025-...xlsx` | **403** S3 AccessDenied | blocked |
| Transparency Intl. | `images.transparencycdn.org/.../CPI2024-...xlsx` | 200, 270 KB | CPI 2012–2024 — used |
| IMF | `imf.org/external/datamapper/api/v1/NGDP_RPCH/POL` | **403** Access Denied | blocked |
| IMF | `api.imf.org/external/sdmx/2.1/dataflow` | 200 (catalogue) | catalogue only |
| IMF | `api.imf.org/.../data/...` | **500 / 404 / 204** | no data |
| IMF | `dataservices.imf.org` | **DNS failure** (curl 6) | gone |
| OECD | `sdmx.oecd.org/.../dataflow/OECD.SDD.STES?format=structure` | 200 | catalogue |
| OECD | `.../DF_FINMARK` data queries | **404**, flow flagged `NonProductionDataflow` | no share prices |
| Police | `statystyka.policja.pl/.../zabojstwo` + two XLSX attachments | 200 | homicide 1999–2023 — used |
| comtradeapi.un.org | preview API | 200 | not used: Comext is the EU customs channel and covers the same goods |
| dane.gov.pl | `api.dane.gov.pl/1.4/datasets` | 200 | searched; no NBP rate/NPL dataset, no GUS macro dataset worth the trip |
| Ministry of Finance | `gov.pl/web/finanse/dlug-publiczny` | 200 HTML | release layer only; the EDP figures come from Eurostat |
| Ministry of Finance | `finanse.mf.gov.pl` | 302 | redirect only |
| Yahoo Finance | `query1.../chart/WIG20.WA?range=20y&interval=1mo` | 200 with **one point** | not a series |
| Yahoo Finance | `query2...` | empty body | blocked |
| stooq | `stooq.com/q/d/l/?s=wig20&i=d` | 200 HTML challenge | no CSV |
| GPW | `gpw.pl/archiwum-notowan?fetch=1&...&date=2024-12-30` | 200 **HTML**, not the XLSX | per-session JS app |
| FRED | `fred.stlouisfed.org/graph/fredgraph.csv?id=SPASTT01PLM661N` | **000** Cloudflare | blocked |

---

## 3. What was chosen, and the seams

**National against harmonised.** GUS and Eurostat both publish most of the
spine's Polish series, and they are not always the same number even when
they describe the same thing. The atlas keeps both: GUS is the national
line, Eurostat the comparable one, in separate columns of the same CSV,
never spliced. Where they agree to the decimal — the EDP deficit and debt;
2024 births 251.8 thousand against 251,782 — that agreement is itself the
check.

**Three labour-market definitions exist and all three are staged, but the
printing quirk is what costs.** GUS prints each unemployment rate twice, in
adjacent rows, with an overlap: the labelled row holds the publisher's
current figures and the unlabelled row the longer back-run. For BAEL the
rows agree (2021: 2.9% both). For the registered rate they do not — 2020
reads 6.8% in one row and 6.3% in the other, 2021 5.8% against 5.4%, and
the published national figures are the lower row. A reader who takes "the
row under the label" concatenates the two and gets a step that never
happened; the fetcher joins them where they agree (long row to 2021,
current row from 2022) and the result is continuous. On top of that, GUS's
BAEL figure is "the last survey of the year" while Eurostat's is the annual
average, so both are staged under their publisher's name.

**Trade has two perimeters.** Customs goods (GUS, EUR/USD/PLN) and
national-accounts goods and services (Eurostat P6/P7). In 2024 they are
EUR 353bn against EUR 443bn. Both are official and neither is the other;
`trade.csv` carries them in separate column families and derives the
balance inside each.

**The population revision is the single most dangerous number here.** GUS's
own annual workbook still prints the unrevised 31 December balance:
37,766.3 thousand for 2022. GUS's revised, residence-based series — the
one Eurostat carries — is 36,897 thousand on 1 January 2022. The ~1.0
million gap is the people the 2021 census found absent for twelve months
or more. A per-capita figure or a death rate computed on the wrong one is
off by about 3% in every year after 2019. The workbook column is staged in
the sidecar for the diff and is **not** used; the plates read the revised
series.

**Migration is four stories.** The residence register did not see the war
inflow: registered immigration 2022 = 275,515, net registered migration
0.2 per 1,000, while the population-balance residual says 12.6 per 1,000
and the temporary-protection stock says 954,800 people at the end of 2023.
The foreign-born stock (933,118) is twice the foreign-citizen stock
(435,964) on the same date, because naturalisation and repatriation move
people across that boundary without anybody moving. Poland reports
citizenship as groups only, so there is no "Ukrainian" column to fetch.

**Fiscal and debt: one definition is enough.** Eurostat's EDP aggregates
are the same notification GUS publishes nationally and they agree to the
decimal, so the national series is a cross-check column rather than a
second line. The Ministry of Finance's cash-basis state-budget deficit and
its narrower *dług publiczny* are different objects and are absent.

**Security: two official homicide counts, a factor of three apart.** Police
confirmed offences (attempts included) 559 in 2023; vital-statistics
assault deaths 197 in the same year. Both are published, both are drawn,
neither is called "the" homicide count.

**Mortality: excess deaths are derived.** Deaths from `demo_gind` against
their own 2015–2019 mean, one vintage, one formula: +18.8% in 2020 and
+29.2% in 2021. COVID deaths are U071 + U072 from Eurostat's cause table
(which starts in 2011): a sum of two published ICD-10 codes, not a splice
of two publishers. Circulatory and cancer counts carry the lens.

**Markets: the policy rate is a year-end reading.** See §4. This is the one
place where Poland's panel is not the same statistic as its peers' and the
caption has to say so.

---

## 4. What could not be staged, and exactly how it failed

Recorded in full in `SOURCES.yaml` `meta.pending`; summarised here.

1. **Household lending rate (credit slot 2).** NBP's pages are behind an
   Incapsula challenge (403), `api.nbp.pl` carries only FX and gold;
   Eurostat's `ei_mfir_m` for PL exposes only deposit and money-market
   codes, and the older MIR dataflows (`irt_mr`, `irt_mr_a`, `mir`) answer
   404 on the dissemination API; the World Bank's `FR.INR.LEND` has 66
   Polish rows and not one value; `knf.gov.pl` does not resolve. Pending,
   with the note, rather than a proxy labelled as the national rate.
2. **WIG20 in US$ (markets slot 4).** GPW's archive is per-session and
   JS-driven (the documented fetch URL returns HTML); Yahoo returns a
   single monthly point for a 20-year range; stooq is JS-walled; OECD's
   share-price flow is non-production and 404s; FRED is Cloudflare-blocked.
3. **Policy rate daily history.** Blocked with NBP; the year-end value GUS
   republishes is what is drawn.
4. **Debt-service ratio.** BIS `WS_DSR` key unresolved (404).
5. **Pre-2012 CPI.** Exists, but on a 0–10 method; deliberately not
   multiplied by ten and spliced. The column starts in 2012.
6. **Sector-wide NPL and the CHF-mortgage share.** NBP-only, blocked.

---

## 5. Known-value checks performed

Every fetcher asserts at least one published value before it writes; the
list below is what was checked by hand during the research pass, in
addition to those assertions.

| Series | Value checked | Source of the check |
|---|---|---|
| Nominal GDP 2024 | 3,669,531 mn zł | GUS workbook, same sheet |
| Real GDP growth 2024 / 2020 | +3.2% / −2.0% | GUS, Eurostat agree |
| CPI 2022 / 2023 / 2024 | 14.4% / 11.4% / 3.6% | GUS index |
| Registered unemployment 2024 | 5.1% | GUS |
| EDP deficit / debt 2024 | −6.4% / 54.8% of GDP | GUS and Eurostat agree |
| Population 1 Jan 2022 | 36,889,761 (revised) | Eurostat; GUS workbook prints 37,766.3 thousand unrevised |
| Births / deaths 2024 | 251,782 / 408,504 | Eurostat and GUS agree |
| COVID deaths 2021 | 90,228 (243 per 100k) | Eurostat cause table |
| Police homicide 2023 | 559 confirmed, 574 initiated | Police XLSX |
| Assault deaths 2023 | 197 | Eurostat cause table |
| Minimum wage 2024 S1/S2 | 4,242 / 4,300 zł | Eurostat `earn_mw_cur` |
| USD/PLN annual mean 2024 | 3.98 | NBP Table A, 252 quotations |
| Goods exports 2024 | EUR 353.3bn; Germany 25.2% | Comext |
| Household debt 2024 | 22.6% of GDP | BIS |
| NPL 2024 Q4 | 3.81% | EBA |
| HDI 2023 | 0.906 | UNDP HDR 2025 |
| CPI score 2024 | 53 | TI 2024 edition |
| Temporary protection end-2023 | 954,800 | Eurostat `migr_asytpsm` |

---

## 6. Determinism

All ten fetchers were run twice against a warm cache: the sidecars are
byte-identical (`md5sum` diff empty). A cold run with the network removed
exits non-zero and writes no file (verified with `HTTPS_PROXY` pointed at
a closed port and the cache moved aside). No fetcher writes a curated CSV.
