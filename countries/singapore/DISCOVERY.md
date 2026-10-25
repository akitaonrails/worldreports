# Singapore — Phase A discovery report

Research pass run 2026-10-25 in the `singapore` lane (branch `singapore`,
based on main `406994d`). Every endpoint below was probed live from the
discovery network on that date and its result recorded, including the ones
that failed. `SOURCES.yaml` is authoritative where this report and it
disagree; `DATA_NOTES.md` carries the judgement calls.

Singapore is a city-state: 744 km², one statistical geography, no
sub-national level to consolidate. That removes one whole class of problem
and creates three others — the population denominator is contested (§2), the
fiscal year is not the calendar year (§3), and the country has no policy
interest rate at all (§4). All three are handled in the data layer and
repeated on the plates.

## Delivered in this lane

- `country.yaml` — identity in all 15 locale names, **en + pt** locales
  (English is Singapore's working official language, so it fills both the
  "official language" and the "English" roles the atlas publishes — said in
  the file's comments), window 2006–2026, `last_full_year: 2025`,
  `tick_every: 2`, `spine: true`, SGD, a palette with three flag bands, two
  recession bands dated on the quarterly chained GDP series, SEO in en/pt,
  and the five shared-scale conflicts recorded in a comment block.
- `SOURCES.yaml` — 16 curated datasets across 10 topic directories plus 14
  `meta.pending` entries, each with the endpoint tried and its failure.
- `fetch/fetch_singstat.py` — one fetcher for the national publisher, 28
  tables, every table title asserted, 16 anchors pinned.
- `fetch/fetch_comparables.py` — World Bank, IMF, UNDP and BIS in one script
  with its own anchors.
- `data/**/*.csv` — 16 curated files; fetchers write only `*_from_*.csv`
  sidecars beside them.
- `DATA_NOTES.md` — the judgement calls, the derived columns and their
  formulas, and what is not drawn.

Gate (`tests/test_sources.py tests/test_data.py -k singapore`): 15 passed,
2 failed — both are the provenance pair (`test_every_plate_cites_files…`,
`test_no_plate_is_drawn_from_a_sidecar`) which need `provenance.json`, i.e.
plates. That is the expected Phase A state.

---

## 1. Publisher-by-publisher

### Singapore Department of Statistics — Table Builder API — **WORKS**

The primary source and one of the better statistical APIs probed in this
project: no key, no registration, JSON in and JSON out.

- `GET https://tablebuilder.singstat.gov.sg/api/table/metadata/<id>` → 200.
  `Data.records` carries `theme`, `subject`, `topic`, `title`, `frequency`,
  `startPeriod`, `endPeriod`, `dataLastUpdated`, and the series list with
  `uoM` (unit of measure).
- `GET https://tablebuilder.singstat.gov.sg/api/table/tabledata/<id>` → 200.
  `Data.row[]` carries `seriesNo`, `rowText`, `uoM` and `columns[]` of
  `{key, value}` per period.
- A retired id answers **404 with a JSON body** (`StatusCode: 404`,
  `Message: "Resource Not Found."`), never an HTML page. The shape is still
  checked before caching.
- **Row values** are strings; a missing observation is `"-"` in some tables
  (M130191 has one) and `null`/`""` in others. All three are treated as
  missing and dropped — never as zero.

**Two access conditions, both real, neither fatal:**

1. **The host rate-limits.** A sweep of all 1,049 table ids started answering
   **403** after roughly two hundred metadata requests and recovered within
   minutes. The fetcher therefore takes one table at a time with a pause and
   exponential backoff on 403 — it treats 403 as "slow down", not as "gone".
2. **Client fingerprint.** A plain `urllib` request is refused with 403 for a
   table that `curl` and `requests` fetch at the same instant, with the same
   User-Agent. The fetchers therefore use `requests` (already the declared
   fetch-time dependency) with a browser UA and `Accept: application/json`.

**Table discovery — and a stale-index trap.** The Table Builder front end is
a SPA with no search endpoint on the API host: `/api/table/tablesearch`,
`/api/table/summary` and `/api/table/search` all answer 404 for both GET and
POST. The publisher's own `sitemap.xml` (200, 349 KB) enumerates the ids
instead: **1,049 live `table/TS/M…` entries**, plus 1,735 saved views
(`table/CT/…`, not tables), 48 `LDC` and 2 `TR`.

The obvious shortcut — data.gov.sg's catalogue, whose dataset descriptions
carry "Adapted from: …/table/CT/<num>" links — is **not reliable** and is
recorded as such in `SOURCES.yaml meta.pending`:

- `M450091`, cited by the catalogue as "Merchandise Exports By Region/Market",
  returns **404 Resource Not Found**;
- many links point at saved views (`CT/…`) rather than tables;
- at least one dataset name belongs to a different table than the id beside
  it (the name "Government Overall Fiscal Position (% Of GDP)" was mapped to
  `M130671`, which is "Taxes On Fossil Fuels, Quarterly"; the real table is
  `M130661`).

Consequence: ids used here come from the sitemap and every one is asserted
against its metadata title inside the fetcher. A re-pointed id fails the fetch
rather than silently changing a chart.

**A cell cap that silently truncates.** `tabledata` returns at most about
**5,000 cells** per response, and `offset` is inert (it echoes back but does
not page). For `M451521` "Merchandise Exports By Region And Market" — 160 rows
× 285 monthly columns — the payload stops after **row 18, "Honduras"**, with
no error. The endpoint does honour a `search` row filter, so the fetcher asks
for each market by name and merges. Without that discovery the trade-partners
panel would have shown the Americas and nothing else.

**Tables adopted** (ids confirmed by title, all live on 2026-10-25):

| id | title | used for |
|---|---|---|
| M015021 | Expenditure on GDP at current prices, annual | GDP, exports/imports, GFCF |
| M015951 | Key data of GDP in chained (2015) dollars, annual | real GDP, growth |
| M015121 | Per-capita GNI and GDP at current prices, annual | GDP per person (S$/US$) |
| M213751 | CPI, 2024 as base year, monthly | inflation |
| M182332 | Unemployment rate 15+, end June, annual, SA | unemployment |
| M130661 | Government overall fiscal position, % of GDP | fiscal ratios |
| M130601 | General government finance, annual (cash) | sidecar evidence only |
| M130191 | Government debt by maturity, end of calendar year | debt stock |
| M130581 / M130591 | Operating / development expenditure by sector | spending by ministry |
| M451521 | Merchandise exports by region and market, monthly | export destinations |
| M700071 | Current banks interest rates, end of period, monthly | 10y yield, SORA |
| M700851 | Exchange rates, average for period, annual | S$/US$ |
| M700031 | Official foreign reserves, end of period, monthly | reserves |
| M700981 | Household sector balance sheet, quarterly | household debt |
| M810001 | Indicators on population, annual | population, density, natural increase |
| M810091 | Births and fertility rates, annual | TFR, crude birth rate |
| M810481 | Death and death rates, annual | deaths, crude death rate, IMR |
| M810501 | Life expectancy by sex, annual | life expectancy |
| M810131 | Deaths by broad groups of causes, annual | causes, suicides |
| M810361 | Key indicators on household employment income | Gini, median income |
| M810791 | Share of non-resident population by pass type | migration stock |
| M890891 | Cases recorded for selected major offences, annual | murder, violence |
| M651421 | Death rate due to road traffic injuries, annual | road deaths |
| M890151 | Land area, annual | land, density |

Also fetched for band-dating and recorded but not curated: `M015902` (GDP,
chained, seasonally adjusted, quarter-on-quarter growth) — the only series
that can date a recession, since the annual line shows just one negative year.

**Verified anchors** (16, asserted in the fetcher): GDP at current prices 2025
= S$789,529.2m; chained 2015 GDP 2025 = S$593,869.9m; GDP per person 2025 =
S$129,194; total population 2025 = 6,111,175; TFR 2025 = 0.87; crude death
rate 2025 = 6.0; life expectancy 2025 = 83.9; total deaths by cause 2025 =
26,499; unemployment 2025 = 2.0%; land area 2025 = 744.3 km²; murder 2025 =
7; road death rate 2024 = 2.35; S$/US$ 2025 = 1.3066; CPI Sep-2026 = 103.551;
10-year yield Sep-2026 = 2.47%; reserves Sep-2026 = S$553,573.4m.

### Monetary Authority of Singapore — **BLOCKED from this network**

`https://eservices.mas.gov.sg/api/action/datastore/search.json`,
`/api/3/action/package_list`, a datastore query with a resource id, and
`/statistics/api/v1/` all return either a **MAS "maintenance.mas.gov.sg" HTML
page under HTTP 200** or a 404 with an HTML body. Nothing from this host is
parsed or cached: an HTML failure served as success is precisely the failure
mode `SOURCING_A_COUNTRY.md` describes.

Consequence: the bank lending rate and the non-performing-loan ratio (credit
slots 2 and 3) have no staged data, and MAS core inflation is unavailable.
This is an access condition on the discovery network, not evidence that the
series are unpublished; the retry is one fetch from an unblocked network.

### Singapore Ministry of Finance / budget documents — not needed

Every fiscal ratio in the spine is published by SingStat from the same
Ministry of Finance estimates (M130661's own footnote links
`singaporebudget.gov.sg`). The ministry's own PDF/Excel releases would be a
second presentation of the same numbers, so they were not fetched: the
publisher that computes the ratio is the statistical office, and the
`SOURCES.yaml` note cites the ministry's estimate cycle for the
actual/revised/budget status of each year.

### data.gov.sg — **WORKS** (as an index only)

`https://api-production.data.gov.sg/v2/public/api/datasets?page=<n>` → 200,
4,664 datasets at 10 per page (the page size is fixed; `pageSize`, `size`,
`limit` and `rows` are all ignored), and `…/datasets/<id>/metadata` → 200 with
column metadata and `managedBy`. Useful to *find* things, unreliable as a map
to Table Builder ids (§1). Not used as a data route for anything staged.

### World Bank — **WORKS**

`https://api.worldbank.org/v2/country/SGP/indicator/<code>?format=json` → 200,
`lastupdated 2026-10-08`. Verified: `NY.GDP.MKTP.CD` 2024 =
572,877,260,178.427; `NY.GDP.PCAP.CD` 2025 = 98,813.98; `SP.POP.TOTL` 2025 =
6,111,175 — the last is **identical** to SingStat's total population, which is
the cross-check that the harmonised and national populations are the same
object.

**One coverage gap:** `SI.POV.GINI` returns an **empty series** for Singapore
(the World Bank's poverty and inequality database has no Singapore row). No
harmonised Gini line exists for this country. Recorded, not filled.

### IMF — **WORKS**, with two coverage decisions

`https://www.imf.org/external/datamapper/api/v1/<code>/SGP` → 200. A browser
User-Agent is refused by the edge; a descriptive one is served.

- Populated for Singapore: `NGDP_RPCH` (growth), `PCPIPCH` (CPI), `LUR`
  (unemployment), `GGXCNL_NGDP` (balance), `GGXWDG_NGDP` (gross debt),
  `G_X_G01_GDP_PT` (Fiscal Monitor expenditure).
- **Empty for Singapore:** `rev`, `exp`, `ie` and `pb` return an empty inner
  object, and the Fiscal Monitor's revenue indicator `G_GR_G01_GDP_PT` has no
  SGP row at all. A control query on a known-covered country returns values in
  the same position, so this is the publisher's coverage decision, not a
  broken request. **Revenue is therefore not derived** as expenditure minus
  balance: both are rounded separately and the subtraction would invent
  precision.

Verified: 2024 growth 5.3, balance +3.8% of GDP, gross debt 165.8% of GDP,
expenditure 14.23%; 2025 growth 5.0, CPI 0.9.

### UNDP — **WORKS**

`HDR25_Composite_indices_complete_time_series.csv` (200, 2.0 MB, Latin-1, not
UTF-8). One row per country, one column per year, plus sibling columns for the
rank — so the key must match `hdi_YYYY` exactly or a rank lands where a value
belongs. Singapore: HDI 0.946 in 2023, 0.948 in 2021, 0.942 in 2022 (the HDR
recomputes its whole back-series each year, so one vintage is used
throughout).

### BIS — **WORKS**, with a key trap

`https://stats.bis.org/api/v1/data/WS_TC/Q.SG.H.A.M.770.A.E?format=csv` → 200.
**The eight-segment key matters:** with the collection segment omitted
(`…770.A`) the API does not error — it serves **Australia's** series. The
fetcher asserts `TITLE_TS` starts with "Singapore" and that the unit is
"Percentage of GDP" before parsing.

Singapore credit to households, % of GDP, Q4: 44.0 (2025), 42.4 (2024), 44.6
(2024 Q1). The national balance-sheet liabilities are 51.6% of GDP for the
same year — two definitions, seven points apart, both official (§5 of
`DATA_NOTES.md`).

### OECD — **reachable**, no Singapore COFOG

`https://sdmx.oecd.org/public/rest/dataflow/all/all/latest?format=json-structure-2.0.0`
→ 200, 1,552 dataflows. `DSD_NASEC10@DF_TABLE11` is "Annual government
expenditure by function (COFOG)", the spine's preferred source, and needs a
**13-dimension** key. A query with `FRA` in the reference-area position
returns 903 KB of 2022 data; the identical query with `SGP` returns
`NoRecordsFound` (HTTP 404, SDMX body). Singapore is not an OECD member and
table 11 does not carry it. This is the route result the gap rule asks for,
and it is why the spending chapter draws the national ministry classification
in the lens instead.

The IMF's COFOG route was probed too: `api.imf.org/external/sdmx/2.1/...`
answers 204/404 and exposes no dataflow artefact at the paths tried.

### UN Comtrade — **WORKS** (not staged)

`https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=702&period=2023&cmdCode=TOTAL&flowCode=X`
→ 200, 224 records. Staged as a possible cross-check for the trade-partners
panel; the published series is SingStat's M451521 and the Comtrade snapshot is
one year, so it is not drawn. Recorded here as a working route.

### WHO — **WORKS**, no COVID series

`https://ghoapi.azureedge.net/api/Indicator` → 200 (415 KB). The catalogue
carries no general COVID-19 death indicator for Singapore, and
`covid19.who.int/WHO-COVID-19-global-data.csv` now follows to an HTML page
rather than a CSV. The mortality plate's COVID slot stays pending.

### Transparency International — **BLOCKED**

`images.transparencycdn.org/images/CPI2025-Results-and-trends.xlsx` → 307
following to **403 S3 AccessDenied**, with and without a browser UA. Other
lanes fetched the identical URL, so this is a network block. World slot 3
stays pending.

### stooq / Yahoo — the equity redistributor

- `stooq.com/q/d/l/?s=…` serves a JavaScript proof-of-work challenge page under
  **HTTP 200** — the endpoint that lies, again. Not used.
- `query1.finance.yahoo.com/v8/finance/chart/%5ESTI?range=5y&interval=1mo` →
  **200** with `^STI` metadata (currency SGD, exchange SES, timezone
  Asia/Singapore). Obtainable, `official: false`, and one fetch away from being
  staged with its FX vintage.

---

## 2. The population question, and why it is not a footnote

SingStat publishes five population lines at mid-year. In 2025: total
6,111,175; resident 4,204,515; citizen 3,660,683; permanent resident 543,832;
non-resident 1,906,660. Every rate in this country divides by one of them, and
the publisher's own choice is not uniform:

- vital rates (crude birth, crude death, infant mortality) → **residents**;
- labour-force rates → **residents**;
- crime rate and population density → **total**;
- old-age support ratio → **citizens**.

A crude death rate of 6.0 per 1,000 is 6.0 per 1,000 *residents*; over the
total population the same 26,499 deaths are 4.3. That is a 40% difference made
entirely of denominator, and it is the single easiest way to publish a wrong
number about this country. The files carry both bases in separate columns with
the scope in the column name and in the header.

---

## 3. Fiscal year, budget year, actual year

`M130661` states its own perimeter in its footnote, quoted in full in
`SOURCES.yaml`:

> "Data refer to the Government's financial year, which begins on 1 April of
> the current year and ends on 31 March of the following year. … Data for
> FY2026 are budgeted estimates. Data for FY2025 are revised estimates. Data
> up to FY2024 are actual figures."

So one column carries actuals, a revised estimate and a budget. The key is
`fiscal_year`, not `year`, and no conversion to calendar years was attempted:
it would invent four months and misalign the country against every
calendar-year peer.

---

## 4. There is no policy rate, so the markets plate has a hole in it

MAS manages the S$NEER band; it does not set a rate. The spine's markets slot 1
is "policy rate vs inflation". Singapore has no such quantity, and the three
ways to fake one — call SORA a policy rate, import the Fed funds rate, or draw
the band's implied rate — are all false statements. The recorded decision is in
`SOURCES.yaml meta.pending`: leave the slot visibly pending, or draw SORA
labelled as a money-market benchmark. The 10-year yield and the currency fill
their slots normally.

---

## 5. What the API *did* answer that the spine did not ask for

Worth recording because they are the country's real story and belong in lens
slots:

- **Household net worth** S$3,296,640.5m at end-2025 against liabilities of
  S$407,531.3m — a debt ratio without an asset side reads as a burden
  Singapore households do not carry.
- **Six Gini coefficients** in one table (before/after transfers and taxes, on
  three equivalisation bases). The gap between before (0.426) and after
  (0.359) is the redistribution, and drawing only one hides it.
- **Non-residents by pass type**, as a share of the non-resident population
  at mid-2025: work permits 44%, migrant domestic workers 16%, long-term
  visit/dependant's passes 15%, employment passes 11%, S passes 9%, student
  passes 5% (mid-2026 has already moved to 45/16/15/10/9/5). This is the
  closest Singapore comes to a migration chapter, and it is a stock by legal
  status, not a flow.
- **Land area** 744.3 km² in 2025 against 581.5 in 1960 — the country is
  physically growing.
- **TFR 0.87** in 2025 (0.97 in 2023 and 2024): among the lowest ever recorded
  anywhere.

---

## 6. Route table

| publisher | endpoint | result 2026-10-25 | used |
|---|---|---|---|
| SingStat | `tablebuilder.singstat.gov.sg/api/table/{metadata,tabledata}/<id>` | 200 JSON; 404 JSON for retired ids; 403 under load | **yes** |
| SingStat | sitemap.xml id enumeration | 200, 1,049 `TS` ids | **yes** (discovery) |
| SingStat | `/api/table/tablesearch`, `/summary`, `/search` | 404 GET and POST | no |
| MAS | `eservices.mas.gov.sg/api/action/datastore/search.json` | HTML maintenance page under 200 | no — blocked |
| MAS | `eservices.mas.gov.sg/api/3/action/package_list` | HTML 200 | no — blocked |
| MAS | `eservices.mas.gov.sg/statistics/api/v1/` | 404 HTML | no — blocked |
| data.gov.sg | `/v2/public/api/datasets?page=n` | 200, 4,664 datasets | discovery only |
| data.gov.sg | catalogued `tablebuilder` links | stale ids / saved views | no |
| World Bank | `api.worldbank.org/v2/country/SGP/indicator/<code>` | 200 | **yes** |
| IMF | `imf.org/external/datamapper/api/v1/<code>/SGP` | 200; `rev`/`exp`/`ie`/`pb` empty | **yes** |
| IMF | `G_GR_G01_GDP_PT` (Fiscal Monitor revenue) | 200, no SGP series | no — coverage |
| UNDP | HDR 2025 composite indices CSV | 200, 2.0 MB Latin-1 | **yes** |
| BIS | `stats.bis.org/api/v1/data/WS_TC/Q.SG.H.A.M.770.A.E` | 200 (7-segment key returns Australia) | **yes** |
| OECD | SDMX dataflow catalogue | 200, 1,552 flows | discovery |
| OECD | `DSD_NASEC10@DF_TABLE11` COFOG | `NoRecordsFound` for SGP (FRA control: 903 KB) | no — not covered |
| IMF | `api.imf.org/external/sdmx/2.1/…` | 204 / 404, no artefact | no — blocked |
| UN Comtrade | `comtradeapi.un.org/public/v1/preview/…` | 200 | no (one-year snapshot) |
| WHO | `ghoapi.azureedge.net/api/Indicator` | 200, no COVID death indicator | no |
| Transparency Intl | CPI 2025 workbook | 307 → 403 S3 AccessDenied | no — blocked |
| stooq | `stooq.com/q/d/l/?s=…` | JS proof-of-work page under 200 | no |
| Yahoo | `query1.finance.yahoo.com/.../%5ESTI` | 200 | not staged |

---

## 7. Determinism and the shape checks

Run in the lane on 2026-10-25:

- **online twice** → every `*_from_*.csv` byte-identical;
- **offline, warm cache** → byte-identical, exit 0;
- **offline, cold cache** → exit 1, nothing written;
- a table whose metadata **title** differs from the pinned one aborts the run
  (this is what catches a re-pointed id);
- a non-JSON body under HTTP 200 aborts the run;
- a table with no rows aborts the run;
- a series label that does not match exactly aborts the run, with the near
  matches printed — positional indexing is never used;
- a duplicate series label within one table is reported and the first kept
  (`M891481` carries each offence twice, as a count and as a rate);
- 16 national anchors and 9 comparator anchors are asserted against the raw
  payload before any aggregation.

---

## 8. What Phase B still needs from this lane

Nothing blocking: every canonical slot either has staged data or a
`meta.pending` entry with the route result. The open items, in the order they
matter:

1. **markets slot 1** — decide pending vs SORA-labelled-as-benchmark (§4).
2. **markets slot 4** — the STI is one Yahoo fetch away; it needs the index
   history and 2006 FX reconciled on one vintage before indexing.
3. **credit slots 2–3** — MAS block; retry from an unblocked network.
4. **world slot 3** — TI block.
5. **spending slots 1–2** — COFOG does not exist for Singapore; draw the
   ministry classification in the lens, labelled.
6. **mortality slot 3** — no COVID series exists on any route; pending.
7. **people slot 2** — no poverty line exists; slot 3 — no minimum wage
   exists. Both are findings to state, not gaps to fill.

---

## 9. Gate results, and the one core change this lane needs

`pytest tests/ -k "singapore and not test_site"` on 2026-10-25 (lane):
**40 passed, 20 failed.** Eighteen of the twenty are the expected Phase B
set — every one is a plate, catalogue or provenance test that cannot pass
before `plates.py`, `i18n.json`, `ui.json` and `provenance.json` exist:

- `test_catalogs.py` × 6 — no `i18n.json`;
- `test_isolation.py` × 3, `test_layout.py` × 4, `test_legends.py` × 1,
  `test_spine.py` × 2 — no `plates.py`/`chapters.py`;
- `test_sources.py` × 2 — no `provenance.json` (it is written by a real
  render).

Focused gate (`tests/test_sources.py tests/test_data.py -k singapore`):
**15 passed, 2 failed**, the same provenance pair. Every data test passes:
shapes, year ordering, duplicates, placeholders, empty columns, thousands
separators, and the reader round-trip.

**The two failures that are a real core gap, not a Phase B gap:**

```
tests/test_core.py::test_the_currency_is_one_the_site_can_write[singapore]
tests/test_numbers.py::test_every_country_can_write_its_own_money[singapore]
```

Both fail on `'SGD' has no per-language form`. `core/sitebuild.py`'s
`CURRENCY_AFFIX` has ARS, BRL, CAD, CHF, CNY, EUR, GBP, ILS, JPY, KRW, TWD,
UAH, USD and VND — not SGD. **This lane does not edit `core/`.** The exact
entry Singapore needs, following the USD shape and Singapore's own S$
convention (the prefix exists precisely to distinguish the Singapore dollar
from the US one, so it is not dropped for the short form either):

```python
"SGD": {
    "money":    {"en": ("S$ ", ""),     "pt": ("S$ ", "")},
    "money_bn": {"en": ("S$ ", "bn"),   "pt": ("S$ ", " bi")},
},
```

The test requires `money` plus at least one of `money_bn`/`money_tn`, and a
form for every declared locale (here `en` and `pt`). If a Phase B chapter uses
`money_tn`, `money_tn1` or `money2`, those need entries too:
`("S$ ", "tn")` / `("S$ ", "tri")` on the same pattern. `usd_bn` and its
siblings are already covered by the existing USD entry.

**No other core change is required by this country.** The `en` and `pt` number
styles both already exist and both already have plate unit rules.
