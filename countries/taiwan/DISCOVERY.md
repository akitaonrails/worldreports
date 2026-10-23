# Taiwan — discovery (Phase A research pass)

Written 2026-10-23. Every endpoint below was curled live on that date
unless a line says otherwise. SOURCES.yaml is the contract; this is the
field record behind it. Nothing here writes fetchers, plates, chapters,
i18n, ui or events.

The framing fact (COUNTRIES.md row 8): the World Bank, the IMF and the UN
do not carry Taiwan, so every chapter's usual supranational second
series must be replaced by a named substitute — the two DPAS engines,
the Central Bank's PCAxis API, the MOF trade database, and the WTO for
the one international ranking layer that does exist ("Chinese Taipei").
UN Comtrade was probed and does NOT report Taiwan as a reporter
(`reporterCode=158` answers `count: 0` on the public preview endpoint;
only partner-side mirrors exist).

## The two engines everything runs on

Two ASP.NET "dynamic query" engines (金諄資訊 DPAS family + one) carry
most of the official numbers, and both speak a plain HTTP protocol that
curl can drive.

### 1. DGBAS — nstatdb.dgbas.gov.tw (Directorate General of Budget, Accounting and Statistics)

Hosts: www.dgbas.gov.tw (budget side) and www.stat.gov.tw (statistics
side) share the query portal at **nstatdb.dgbas.gov.tw/dgbasAll/**.
English mirror: eng.dgbas.gov.tw and eng.stat.gov.tw (pages, not APIs).

Protocol, verified live end-to-end today:

- Table page (human): `webMain.aspx?sys=100&funid=qryout&funid2=<CODE>`
- Definition JSON: `webMain.aspx?sys=212&x=2100&funid=<CODE>` →
  `{funid, funname, source, cycleDef, minym, maxym, fmt, ...}`.
  Periods are ROC-year MM codes: `7000` = 1981-01, `11509` = 2026-09.
- **Data JSON: `webMain.aspx?sys=220&kind=100&funid=<CODE>&ym=<from>&ymt=<to>&cycle=<col>&outmode=8`**
  → `{funid, name, links, gentime, colh, col, row, orgdata, outdata,
  plusdata, ...}`; `orgdata` is rows of numbers, `outdata` formatted.
  outmode: 0 html, 1 Excel, 6 ODS, 2 CSV (Big5!), 3 CSV-UTF8, 7 PDF, 8 JSON.
- The index page's own tiles carry ready-made export parameter strings
  (`&cycle=42&outkind=11&outmode=8&fldlst=...&codlst0=...`) — harvest
  those for the column/codelist codes instead of guessing.
- Quirk: `usrdgbasJS.js` (the page's JS) is WAF-blocked to direct GETs
  — irrelevant once the sys/x protocol is known. Quirk: both DGBAS hosts
  serve a TLS chain this machine cannot verify (missing intermediate) —
  record; fetchers must pin a CA rather than shrug it off.

Verified tables (curl'd today):

| code | table | shape verified |
|---|---|---|
| A018101010 | national-income key table — 15 cols (population, avg FX, real growth y/y, GDP nominal NTD/USD, per-capita NTD/USD, GNI, NI…) at annual AND quarterly rows | ym=9500..11400, cycle=42+fldlst → 15×100 values; spot 2009 growth −1.61, 2020 +3.42 (all quarters positive), 2024 GDP US$790.1bn, 2025 GDP NT$28.72tn / US$953.2bn, per-capita US$40,626, population 22.82mn→23.60mn (2019 peak)→23.35mn |
| A030101015 | CPI, basic classification, monthly 1981-09 on | cycle=41 = headline 總指數; 2025-01 109.6 → 2026-09 110.x, base 2021=100 |
| A040107010 | unemployment rate tile | index page only |
| A046301010 | industry+services monthly periodic wage | index page only |
| A020001010 | median household disposable income | index page only |
| A200101010 | social-security expenditure / GDP | index page only |
| A170101020 | 主要死亡原因 monthly deaths by cause, 2008-01 to 2025-12 | definition JSON + tile export params verified (cycle=4, outkind=4, codlst0/1 select causes) |

### 2. MOF — web02.mof.gov.tw/njswww (final accounts, taxes, debt, trade)

Same engine family, its own trees: fiscal tree
`WebMain.aspx?sys=100&kind=10&type=1&funid=defjsp3` (69 leaves harvested),
trade tree `...funid=defjsp7` (27 leaves harvested). Data URL pattern
identical but `kind=21&type=1`:
`WebMain.aspx?sys=220&kind=21&type=1&funid=<CODE>&ym=&ymt=&cycle=&outmode=8`.
Query-form page is `sys=210` — it re-serves the form unless `sys=220`.

Verified end-to-end today:

| code | table | shape verified |
|---|---|---|
| i2101 | all-levels government net revenue / expenditure / balance / financing, annual 1974–2025, NTD | 2023 revenue 3,888,796,962 (thousands → ~NT$3.89tn) |
| i0232 | central government gross debt outstanding (≥1y non-self-amortizing, domestic), 2006–2025 | 2006: 3,622,642 mn ≈ NT$3.62tn (≈50% of GDP, plausible) |
| i9111 | trade value by continent/country, USD thousands, annual | 2025 exports US$639.96bn |
| i0111 / i0121 / i1111 / i1121 / i0124 / i1131 | revenue by source, expenditure by POLICY CATEGORY (final accounts, all levels & central only) | codes harvested, same protocol |
| i2201 / i2205 / i2211 | public treasury cash in/out | harvested — the cash-basis twin of the accrual tables: two publishers, one idea, in one database; two columns, never splice |
| i2401 / i0421 / i2451 | tax collections by fiscal-year and by calendar-year | harvested — note the SAME tax twice on two year keys |
| i9121 / i8141 / i8151 / i8134 / i8201 / i9203 / i9204 | trade by commodity (HS2, SITC, BEC), country×commodity, main partners | harvested |
| i9302–i9305 | unit-value and quantity indices | harvested |

Fiscal year = calendar year (年度 rows are plain calendar years) — no
`fiscal_year` key needed, unlike Japan/UK.

### 3. Central Bank — cpx.cbc.gov.tw (statistics database) + public JSON API

The legacy `www.cbc.gov.tw/opendata/*` JSON API is DEAD (302s to the
homepage). Its successor is the statistics database at
**cpx.cbc.gov.tw**, and every table has a keyless JSON endpoint:

- **`https://cpx.cbc.gov.tw/api/dataapi/Get?FileName=<CODE>`** (CODE
  without `.px`) → PCAxis-flavoured JSON: `{meta:{title, sender,
  prepared, filename, links, note, last_updated, units, matrix},
  data:{dataSets:[[row…],…], structure:{Table1:[{data:"…"},…]}}}`.
  Missing values are the string `"-"`. Period codes `"1987"` / `"1988M01"`.
- Tree: `POST /Tree/GetJsonTreeData` (JSON string of a node tree with
  `pxfilename`s); range UI flow is `/Range/RangeSelect?pxfilename=` —
  not needed once the API is used.

Verified today (codes → content):

| code | content | spot |
|---|---|---|
| EG2AM01 | policy rate, monthly from 1988M01: 重貼現率 (rediscount rate — that IS the CBC's policy rate; no OMO target-rate series), secured & short-term lending rates | period-end values |
| EG51M01 | USD spot monthly from 1992M01: bank-customer buy/sell, **interbank closing**, daily average; forward LC USD rate | 2026-08 close 31.666 |
| EG52M01 | spot rates for 13 other currencies, monthly — USD is NOT inside it | 1987M05 on |
| EG27Y01 | stock exchange trading and index, annual from 1987 (TWSE cap-weighted index) — its index column is the ANNUAL AVERAGE (2024: 21,382.78), not the year-end | — |
| EF07M01 | key monthly indicators: **foreign-exchange reserves (mn USD)** from 1992M01, bank NPL ratio (逾放比率), CPI y/y | one table carries three chapters |
| EF99Y01 | consumer loans and building loans outstanding — the credit chapter's spine, check columns (消費者貸款 includes cards/overdraft; 建築貸款 is developers' credit); five-bank new-housing-loan detail is EH45M01 | — |
| BPP2Y01 / BPP2Q01 / BPF4Y01 | balance of payments (goods+services, all items) and IIP, USD mn | 2025 row verified |

### 4. Markets — Yahoo ^TWII (official: false cross-check, NOT the spine)

`https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII?period1=&period2=&interval=1mo`
works with a browser UA (`range=5y&interval=1y` answers 400 — use months
and derive December closes). Dec-2021 17,674.4 / Dec-2024 23,525.41 —
consistent with TWSE history. stooq: JS-walled from this machine
(recorded, not retried). Because CBC EG27Y01 is the OFFICIAL index
series (annual average) and Yahoo is the year-end close, they are two
different quantities on one panel — label which is which.

### 5. WTO — the one international body, key-gated (PENDING)

Live probes: `stats.wto.org` answers an SPA HTML shell for every route
(`/api/...`, `/download/...` included); `data.wto.org` and `ttd.wto.org`
return Cloudflare 403 from this machine; `api.wto.org` answers 404 JSON
on guessed routes and its documented Stats API requires a free API
account. PENDING with reason: register the key in Phase B; WTO does
carry "Chinese Taipei" as a reporter (rank tables, profiles), which is
the whole point of this entry. ADB: carries some tables as
"Taipei,China" in Key Indicators products; not probed live — pending.

### 6. Customs Administration (web.customs.gov.tw) — statistics DB unreachable

The Customs portal links its 統計資料庫查詢系統 to
`portal.sw.nat.gov.tw/APGA/GA35` (the foreign-trade single window).
That host is unreachable from this machine (TCP timeout on v4 and v6,
likely geo/edge blocking). PENDING with reason. The goods-trade spine
is instead the MOF trade database above (i9111 etc.), compiled from the
same customs records — name that substitution loudly in DATA_NOTES.

### 7. Interior / RIS (population register) — portal reachable, keyless endpoint not found

`registration.moi.gov.tw` does not resolve from this machine. The MOI
population register publishes through www.ris.gov.tw (人口統計資料專區,
portal 37 → 674; the query app and its data files are JS-rendered;
`/database/...` paths 404). PENDING with reason. The verified substitute
for annual stock is the DGBAS population column (cycle=4 of A018101010);
monthly births/deaths still to be found (MOI RIS, or DGBAS tiles — a
死亡人數 tile exists in the index).

### 8. MOH / HPA (causes of death) — HPA WAF-blocked; DGBAS substitutes

`www.hpa.gov.tw` answers 403 "Web Application Firewall" to curl. PENDING
with reason (annual ICD-10 detail). Substitute verified in DPAS:
A170101020 monthly deaths by cause, 2008-01 to 2025-12.

### 9. NIA / MOL (migration) and NPA (crime) — reachable portals, no keyless files found

immigration.gov.tw business-statistics section (7344: 統計資料, 歷史資料區,
statistics theme hub) is live but its file links are JS-rendered;
MOL's 勞動統計專網 (foreign-worker permits) likewise; npa.gov.tw's
statistics module returns an error page to plain curl. PENDING with
reason, with the §4a naming discipline recorded in SOURCES (residents
stock vs work-permit flow vs new-resident flow; emigration unmeasured).

## Cross-checks performed

- Population: DGBAS 23.60mn peak (2019) → 23.35mn (2025) — brief said
  ~23.3mn falling since 2020 ✓.
- GDP: 2024 US$790.1bn (brief: ~US$800bn ✓); per-capita 2025 US$40,626.
- Exports 2025: customs-compiled US$640.0bn vs BoP-table 2025 row
  (different definitions — both kept, never spliced); MOF homepage
  indicator Sep-2026 exports US$87.2bn (partial-year sanity check).
- Reserves series (EF07M01) order ~US$500–650bn — "among the world's
  largest" ✓.
- Policy-rate file shows 1.700 as of 115.10.23 (2026-10) on the
  homepage's bkrldc.txt; EG2AM01 carries the long history.

## Pending list (nothing blocks; all with reason)

1. WTO Stats API — needs a free api.wto.org key; SPA/Cloudflare walls
   everything keyless from this machine.
2. Customs DB at portal.sw.nat.gov.tw — TCP-unreachable here (geo/edge).
3. MOI RIS monthly register tables — JS app, no keyless endpoint found.
4. HPA annual ICD-10 — WAF 403 to non-browser agents.
5. NIA/NPA/MOL machine endpoints — portals reachable, files JS-rendered.
6. MOEA (moea.gov.tw) — Cloudflare 403 from this machine; its export-
   orders indicator is mirrored by CBC EG46 and the BoP tables anyway.
7. Population projections — DGBAS news-page spreadsheets, vintage trap;
   one vintage only.
8. ADB "Taipei,China" — not probed live.
9. data.gov.tw — the catalog API is token-gated (package_search 404s
   keyless); do not treat it as a primary source anyway.

## Phase B notes (recorded, not acted)

- Locale code must be exactly `zh-Hant`: plate-spine's
  `core/numstyle.py` already keys that style (萬 1e4 / 億 1e8 / 兆 1e12,
  English marks; CURRENCY_AFFIX needs the NT$ column for TWD).
- CSV outmode=2 on the DPAS engines is Big5 — use outmode=8 (JSON) or 3
  (CSV-UTF8) instead.
- DPAS period codes are ROC years: subtract 1911; assert both a known
  year-end value and the ROC offset before trusting any pull
  ("endpoints that lie", SOURCING §4).
- CBC JSON marks missing as "-".
- nstatdb/www.dgbas/www.stat TLS chains need an explicit CA bundle.
- This machine's resolver (127.0.0.53) intermittently times out — the
  fetchers should retry DNS once before declaring a publisher dead.
