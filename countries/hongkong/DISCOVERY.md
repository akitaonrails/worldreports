# Hong Kong — discovery log

Research pass 2026-10-25, from the batch lane's network. This is the record of
what was probed, what answered, what refused and how, and why each series was
chosen. The curated files and their per-series notes are in `SOURCES.yaml`;
the arithmetic is in `DATA_NOTES.md`.

## Framing, decided before any number was pulled

Hong Kong is a **Special Administrative Region of the People's Republic of
China**, not a sovereign state. The atlas carries it because its statistics
are institutionally its own: a separate statistical office (C&SD), a separate
currency board (HKMA), a separate customs territory, a separate legal system
and a separate reporting row in every international dataset (`HKG`, never
`CHN`).

So the page compares Hong Kong **as an economy**. It never presents an SAR
statistic as a Chinese national statistic and never mixes the two. Where a
comparison is international — GDP in dollars, HDI, the corruption index,
homicide — the source is a body that reports Hong Kong separately, and the
note says which body.

## The seven publishers, for this economy

| role | institution | what it carries here | machine route |
|---|---|---|---|
| statistical office | Census and Statistics Department (C&SD) | national accounts, CPI, labour force, population, vital events, merchandise trade, government accounts, money and interest rates, crime counts | **JSON API** `api/get.php?id=<table>&full_series=1`, 590 tables |
| central bank / currency board | Hong Kong Monetary Authority (HKMA) | Base Rate, HIBOR context, reserves, bank asset quality, EFN yields | open API **walled** (405); Monthly Statistical Bulletin **XLS/XLSX** works |
| fiscal | Financial Secretary's Office / Treasury | revenue and expenditure (GRA and funds) | via C&SD table 340-47001 |
| customs | C&SD (trade statistics) / Customs and Excise | exports, imports, destinations, products | via C&SD tables 410-500xx |
| vital statistics | Department of Health | registered deaths by leading cause, COVID-19 | **CSV on data.gov.hk** |
| police / justice | Hong Kong Police via C&SD | reported offences | via C&SD table 940-92033 (2021+) |
| market | Hang Seng Indexes Company (private), Yahoo as redistributor | HSI close | Yahoo chart JSON, `official: false` |
| migration | Immigration Department / C&SD | net movement only | via C&SD table 110-01003 |

Comparables layer actually available for `HKG`: World Bank WDI, IMF WEO
(which reports the SAR as an economy), UNDP HDR, BIS, Transparency
International. Hong Kong is **not** an OECD member, **not** a WHO member state
and **not** in Eurostat, so COFOG, the WHO mortality database and the Eurostat
migration tables have no Hong Kong row at all — that shapes several pending
slots below.

## Route table — what answered, what did not

| publisher / endpoint | result | date | consequence |
|---|---|---|---|
| `https://www.censtatd.gov.hk/en/` | 200 | 10-25 | main site reachable |
| `https://www.censtatd.gov.hk/data/WebTableList.json` | 200, 590 tables with themes and API links | 10-25 | the catalogue that made table selection possible |
| `api/get.php?id=310-31001&lang=en&param=<fabricated lz-string>` | 200 with `"dataSet": []` | 10-25 | the `param` form is an LZ-string of the reader's UI selection; unusable |
| `api/get.php?id=310-31001&lang=en&full_series=1` | 200, 3,069 rows | 10-25 | **the route used** for 26 tables |
| same endpoint from Python `urllib` default UA | **403** | 10-25 | fetcher sets `User-Agent: curl/8.5.0`; verified that this alone flips it to 200 |
| `https://api.hkma.gov.hk/public/.../daily-figures-interbank-liquidity` | **200 on the first call** (100 records, Base Rate 4.25 on 2026-10-23) then **405** on every path | 10-25 | the HKMA API is behind an Aliyun WAF that refuses this network; not reproducible, payload not kept |
| HKMA API with browser UA / Referer / Accept-Language / XHR header / HTTP/1.0 | **405** every combination | 10-25 | ruled out as a UA problem |
| `https://www.hkma.gov.hk/eng/data-publications-and-research/data-and-statistics/` | 200 | 10-25 | the website is not walled |
| Monthly Statistical Bulletin `T0804.xlsx`, `T030601.xls` | 200 | 10-25 | reserves and classified loans taken here |
| EFBN closing archive `.../efbn/attach/YYYYMMDD_CLOSINGS.xlsx` | 200 from 2015, **404** before 2015 | 10-25 | tenor probe only (see pending: no 10-year benchmark) |
| `https://www.hkgb.gov.hk/en/statistics/statistic.html` → `T0905.xls` | 200, sheets per tenor (1/2/3/5/10/15/20-year) | 10-25 | these are **issue lists**, not yields |
| `https://data.gov.hk/en-data/api/3/action/package_search?q=...` | 200 | 10-25 | mirrors C&SD tables; carries DoH death statistics; **0 results** for poverty, minimum wage, gini, one-way permit |
| `https://www.dh.gov.hk/datagovhk/ncdd/...Leading Cause of Death...(EN).csv` | 200 | 10-25 | mortality chapter |
| `https://stats.bis.org/api/v1/data/WS_CBPOL/D.HK?format=csv` | 200, 7,956 rows | 10-25 | Base Rate (HKMA's own rate, compiled by BIS) |
| `https://stats.bis.org/api/v1/data/WS_TC/Q.HK.H.A.M.770.A?format=csv` | 200, 85 quarters | 10-25 | household credit to GDP |
| `https://stats.bis.org/api/v1/data/WS_TC/Q.HK.A.M.770.A` | **404** "No data for data query" | 10-25 | the all-sectors key does not exist for HK; the household (`H`) and private (`P`) keys do |
| `https://api.worldbank.org/v2/country/HKG/indicator/...` | 200 for GDP, per capita, reserves, population, TFR, life expectancy, net migration, trade, GFCF, unemployment, growth, CPI, homicide | 10-25 | harmonised layer |
| World Bank `SI.POV.GINI`, `SH.STA.SUIC.P5`, `SH.STA.TRAF.P5`, `SI.POV.NAHC` for HKG | 200 with an **empty data array** | 10-25 | no Gini, suicide, road-death or poverty series from WDI |
| `https://www.imf.org/external/datamapper/api/v1/rev/HKG` | **403** with a browser UA, **200** with a curl UA | 10-25 | fiscal and macro comparables |
| IMF `GGR_NGDP`, `GGX_NGDP` | 200 but no `HKG` series | 10-25 | the DataMapper codes are `rev`/`exp`/`pb`/`GGXWDG_NGDP`/`ie` |
| `https://hdr.undp.org/.../HDR25_Composite_indices_complete_time_series.csv` | 200 (after a redirect; 403 to urllib's default UA) | 10-25 | HDI |
| `https://images.transparencycdn.org/images/CPI2025_Results.xlsx` | 307 → 200 (needs redirects followed) | 10-25 | CPI scores; the workbook's defined names break openpyxl, so it is read from XML |
| `https://query1.finance.yahoo.com/v8/finance/chart/%5EHSI` | 200 | 10-25 | HSI year-ends, `official: false` |
| `https://www.labour.gov.hk/eng/news/smw.htm` and two sibling paths | **404** | 10-25 | minimum-wage series not found on a machine-readable route |

## What was chosen, and the traps behind each choice

**C&SD as the national spine.** The API is a genuine JSON service with no key
and no quota, and `full_series=1` returns the whole table. Four traps were hit
and are handled in the fetcher: the empty-`dataSet` under HTTP 200 (a bad
`param`), the 403-to-urllib behaviour, rows that omit a dimension key entirely
when it does not apply (total rows have no `SEX`), and multiple dimensions
collapsing when a table is read without declaring them. That last one is how
an early read of the labour-force table produced the **female** labour force
as though it were the total: the fix is that every table declares its
dimension fields and the curated file selects the empty total code, never a
row position.

**Two fiscal publishers, two perimeters.** The government's own accounts
(C&SD 340-47001) are cash, on the General Revenue Account, in a financial
year starting 1 April, and their revenue total includes transfers between
government funds. The IMF's general-government series is calendar-year,
consolidates the funds, nets out intra-government transfers and is the only
general-government perimeter published for Hong Kong. They differ by roughly
a point of GDP and sometimes in sign. Both are staged; neither is spliced.

**The currency board is the markets story.** The Base Rate is not a policy
choice: it is the Fed funds target upper bound plus 50bp, so the HKD rate
follows the Fed. Spot HKD is confined to 7.75-7.85 by the convertibility
undertakings and does not float, which is why the currency panel uses the
effective exchange rate index rather than the peg.

**No ten-year benchmark.** The HKMA's only machine-readable yield source is
the EFBN closing archive. Checked year by year: the 10Y-coded notes still
outstanding at each year-end 2015-2023 had 0.4 to 1.5 years to maturity (old
issues about to mature), and from 2024 the HKMA issues only 2- and 15-year
paper, so no 10-year note exists at all. The `T0905` sheets on hkgb.gov.hk
list 10-year issues but publish no yields. The slot is pending with that
evidence rather than filled with a 15-year or a 1-year tenor.

**Government consumption is not government spending.** C&SD's functional
table (310-32023) covers GCE, so cash transfers — pensions, social security,
allowances — are outside it and "social protection" reads under 4% of the
total. That is a real property of the classification, not a data error, and
the plate has to say so or the chart will claim Hong Kong spends almost
nothing on social protection.

**Crime counts restart in 2021.** The police re-based their offence
classification then; C&SD's table begins at 2021 and no earlier year is
spliced onto it. The long homicide comparison is the UNODC/World Bank series.
2025 carries a single-quarter anomaly (170 murder and manslaughter cases in
Q4 against 19 in the first three quarters) which the plate will need to
annotate; it is kept exactly as published.

**Deaths have two publishers and they answer different questions.** C&SD's
vital events give the crude death rate; the Department of Health gives
registered deaths by leading cause, with COVID-19 as a named cause and the
ICD coding change in 2024 documented in the file's own note. `excess deaths`
is computed here from the DoH all-cause counts — a different quantity from a
weekly P-score series and never compared with one.

## Series that stay pending, with the route that failed

Recorded in full under `meta.pending` in `SOURCES.yaml`:

| slot | status | the route that failed |
|---|---|---|
| markets slot 2, 10-year yield | does not exist on a comparable definition | HKMA API 405; EFBN archive has no on-the-run 10Y note; hkgb `T0905` publishes no yields |
| people slot 1, Gini | report-only | not in C&SD's 590 tables; data.gov.hk 0; WDI empty; HDR has none |
| people slot 2, poverty | report-only | data.gov.hk 0; no C&SD table; Hong Kong is not a PIP country |
| people slot 3, minimum wage | no machine-readable official series found | labour.gov.hk SMW paths 404; data.gov.hk 0; no C&SD table |
| security slot 2, suicide | no separate official series | DoH aggregates suicides into "external causes"; WHO GHO has no HKG (not a member state); WDI empty; Coroner PDFs only |
| security slot 3, road deaths | no machine-readable series found | data.gov.hk has one one-off feature article; WDI empty; WHO has no HKG |
| migration slot 1, gross flows | not published on a residence basis | C&SD publishes only the residual; ImmD publishes passenger movements and the one-way permit quota |
| migration slot 3, foreign-born share | census points only | no annual birthplace series in the web tables |

## Determinism

All six fetchers were run twice from a warm cache and their sidecars compared
byte for byte (see the report): identical. Every payload is cached under
`countries/hongkong/cache/` (git-ignored) so `--offline` reproduces a run
without a network; `--offline` with a cold cache exits non-zero and writes
nothing.

Non-determinism that was designed out: the EFBN archive is probed by date, so
a 404 (a public holiday, or before 2015) is skipped rather than cached as
data; the BIS and World Bank payloads are ordered by key before writing; and
no file carries a fetch timestamp.
