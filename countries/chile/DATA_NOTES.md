# Chile — data notes

Phase A record: what is in `data/`, what was converted to get there, which
denominator each rate uses, where the seams are, and what is deliberately
not drawn. `DISCOVERY.md` is the route log; `SOURCES.yaml` is the
per-file provenance and the pending list.

Currency: **CLP**. No redenomination inside the window (the 1975 change
is thirty years before it), but the peso is quoted in units, not
thousands, in every staged file, and the exchange rate moved from 530 to
951 per US$ — so no nominal peso level is comparable across this window
and none is plotted as one.

`last_full_year: 2025`. INE's September 2026 bulletin is out, the BIS
policy rate has 201 trading days for 2026, household credit has one 2026
quarter with no Q4, and DEIS's 2026 rows carry zeroes for weeks that have
not happened. 2025 is the last year whose annual totals are complete in
every staged source.

---

## 1. What is staged

| Chapter | File | Coverage | Publisher |
|---|---|---|---|
| economy | `macro/economy.csv` | 2006-2025 | World Bank WDI |
| economy / markets | `macro/fx.csv` | 2006-2025 | World Bank (BCCh series) |
| world | `world/world.csv` | 2006-2025 | WB, UNDP, TI |
| fiscal | `fiscal/fiscal.csv` | 2006-2025 | IMF WEO + Fiscal Monitor |
| fiscal | `fiscal/tax.csv` | 2006-2024 | World Bank |
| spending | `spending/cofog.csv` | **2018-2024** | OECD table 11 |
| spending | `spending/public_investment.csv` | **2007-2012** | OECD NAAG |
| trade | `trade/trade.csv` | 2006-2025 | World Bank |
| trade | `trade/partners_2024.csv` | 2024 only | UN Comtrade (Aduanas) |
| markets | `markets/policy_rate.csv` | 2006-2026 | BIS (BCCh series) |
| credit | `credit/household_credit.csv` | 2006-2026 | BIS |
| people | `people/gini.csv` | 9 survey years | World Bank (CASEN) |
| people | `people/poverty.csv` | 9 survey years | World Bank (CASEN, PIP) |
| demography | `demography/demography.csv` | 2006-2025 | World Bank (UN WPP/INE) |
| mortality | `mortality/mortality.csv` | **2010-2025** | **MINSAL/DEIS** + WB |
| security | `security/security.csv` | 2006-2023 | World Bank (UNODC/WHO) |
| migration | `migration/migration.csv` | 2006-2025 | World Bank (UN) |

Only `mortality/mortality.csv` is `official: true`: MINSAL publishes the
death counts. Everything else is a harmoniser's republication and is
flagged accordingly, even where the underlying series is Chilean.

---

## 2. Conversions and derivations

Every arithmetic step is named here, and each is in the file as a column
rather than applied silently at draw time.

- **`world/world.csv: gdp_usd_bn`, `reserves_usd_bn`** — US$ divided by
  1e9, one decimal. The source is in dollars, not thousands or millions.
- **`trade/trade.csv: trade_balance_pct_gdp`** — exports minus imports,
  both already % of GDP, two decimals. No other series is touched.
- **`demography/demography.csv: natural_increase_per_1000`** — crude
  birth rate minus crude death rate, both World Bank, per 1,000.
- **`mortality/mortality.csv: crude_death_rate_national`** — DEIS deaths
  ÷ DEIS-embedded population × 1,000. `crude_death_rate_wb` is the World
  Bank's own rate on the UN denominator, not this calculation repeated on
  another population.
- **`mortality/mortality.csv: excess_deaths_pct_vs_2015_2019`** — the
  mean of 2015-2019 registered deaths is 105,681; each year from 2020 is
  expressed as a percentage above or below it. Blank before 2020 by
  construction, because a baseline cannot contain its own comparison
  years. The 2015-2019 window is the spine's convention, not Chile's.
- **`migration/migration.csv: net_migration_per_1000`** — the UN net
  migration count ÷ World Bank population × 1,000.
- **`migration/migration.csv: foreign_born_share_pct`** — UN migrant
  stock ÷ population × 100. Only the five stock years carry it.
- **`markets/policy_rate.csv: policy_rate_pct`** — the mean of the daily
  policy target published in the year, not the year-end value, so that it
  is the same kind of number as the annual CPI it is drawn against.
  `days_observed` says how many daily points the mean rests on.

The `#` comment block at the top of each CSV carries the caveat that does
not fit in a YAML note; `core.plotting.read_table` skips those lines and
`core.plotting.comments` reads them back.

---

## 3. Denominators

Two population series, never mixed:

- **UN WPP / World Bank** (`demography/demography.csv: population`) —
  2006: 16,509,195; 2019: 19,197,744; 2025: 19,859,921. Denominator of
  the World Bank rates and of the migration per-1,000 figures.
- **INE projection as embedded in DEIS** (`mortality/mortality.csv:
  population`) — 2010: 17,063,927; 2019: 19,107,216; 2025: 20,206,953.
  Denominator of the national crude death rate, so the count and the
  denominator come from the same publisher and the same vintage.

They differ by up to about 0.5% and in opposite directions across the
window (DEIS is lower in 2019, higher in 2025), which is what a national
projection and a UN revision do. Neither is wrong; a rate that mixed them
would be.

Per-100,000 rates in `security/security.csv` are the publishers' own
rates, not recomputed counts: UNODC and WHO publish rates on the same
population basis they publish the counts on, and recomputing them on
another denominator would silently disagree with the source.

---

## 4. Seams and breaks

- **CPI base.** 2018 = 100 up to the 2023 rebasing, 2023 = 100 after it.
  The staged column is the annual percentage change (a chain), so it does
  not carry the seam. A future national index level would.
- **CASEN.** Biennial and rebased twice. The Gini and the national
  poverty rate are drawn as observations, never interpolated, and the
  poverty line change is a note on the panel.
- **COFOG.** Starts 2018: that is when Chile began reporting the table to
  the OECD. 2006-2017 are blank. A spine panel spanning 2006-2026 will
  show an eight-year line inside a twenty-one-year axis, and the
  subtitle has to say so — this is the largest single hole in the
  country's canonical set.
- **Government GFCF.** The OECD series stops at 2012 for Chile (the
  series was discontinued). Blank after, not continued from another
  source on another basis.
- **WHO series.** Suicide ends 2021, road deaths 2019. Carried forward
  they would draw a flat line that no publisher stands behind.
- **UNDP HDI.** One vintage (HDR 2025), recomputed across the whole
  history each report. Never mix vintages: a step between report years is
  methodology.
- **TI CPI.** 2012 method throughout (the workbook's historical sheet
  starts at 2012), so no ×10 seam appears. TI changes its source mix year
  to year; the series is drawn as published.
- **UN migrant stock.** Five-year grid. It is a step series and is drawn
  as points, not an annual line.
- **Ñuble.** Split from Biobío in 2018; national totals unaffected, any
  regional cut is a different map.
- **Fiscal perimeter.** The staged series is general government. The
  central-government structural-balance rule the Chilean budget is
  actually written against is a narrower perimeter, published by Dipres,
  and is pending.

---

## 5. Choices worth arguing with

**Why the harmonised layer carries most of the country.** Every Chilean
publisher except MINSAL answered this network with a web page, a login or
a bot wall (`DISCOVERY.md` §1; `SOURCES.yaml` `meta.pending`). The
alternative was to publish nothing, which the repository's rules do not
allow either. So the canonical slots use the harmonised series, each note
names whose national series it is republishing, and the national line
joins it when the publisher's own route answers. That is a decision about
this network on this date, not a claim that Chile does not publish.

**Why the national fiscal series is not approximated.** Dipres' numbers
are the ones Chileans argue about, and the general-government series
differs from them by perimeter (and, in the structural-balance rule, by
cyclical adjustment). A "close enough" central-government line would be
the most plausible-looking wrong chart in this country. It stays pending.

**Why the minimum wage stays blank.** Chile's minimum wage exists, is
statutory and is reajustado annually — this is not a case of absence. No
machine-readable official series answered (Dirección del Trabajo, OECD
`MW_CURP`/`RMW`, ILOSTAT, `datos.gob.cl`), and transcribing thirteen
annual values from memory into a CSV would be exactly the
plausible-looking number this repository exists to prevent. The next pass
should pull it from the laws on `bcn.cl` and cite the law number per
year.

**Why the trade partner snapshot is one year.** Comtrade's free preview
is capped at recent periods. A single well-labelled year in a lens slot
is honest; a stitched "top partner over time" from mixed vintages is not.

**Why `mortality` is a national file with a harmonised column.** The
chapter's first panel is the national death count — that is what MINSAL
publishes and it is `official: true`. The World Bank rate sits beside it
in its own column because the atlas's other countries are on the
harmonised basis and the comparison viewer needs them to register. Two
columns, two denominators, both labelled on the panel.

---

## 6. Checks that were run

- **WEO vs Fiscal Monitor balance**: worst disagreement across 2006-2025
  is 0.05 percentage points, asserted by the fetcher before the file is
  written. Two vintages of one number in one file would be a splice.
- **COFOG divisions vs total**: the ten divisions sum to the published
  total within 0.15 points of GDP in every year, asserted by the fetcher.
- **DEIS annual totals**: 2019 = 109,324, 2021 = 137,267, 2024 = 126,322
  deaths, pinned in the fetcher; 16 regions asserted; the running year is
  dropped by requiring 52+ weeks and non-zero late weeks.
- **DEIS population**: within 18-21 million and consistent with the World
  Bank series to 0.5%.
- **Comtrade**: China is the top destination, 177 partners, partner rows
  cover 100.00% of the US$ 98.9bn world total.
- **Harmonised spot values**: twenty pinned values (2019 GDP, 2020
  unemployment, 2022 inflation, 2021 debt, 2019 homicide, 2023 HDI, 2020
  policy rate, 2019 household credit, 2022 COFOG health, and others) read
  off the publishers on 2026-10-25.
- **Second source for the headline level**: the World Bank's GDP for 2019
  (US$ 278.3bn) and 2024 (US$ 329.3bn) agrees with the IMF's NGDPD
  (278.06 and 329.20) to within 0.1%, so the staged dollar level is not a
  unit error.
- **Determinism**: all twenty sidecars re-fetched warm are byte-identical;
  a cold cache with the network refused exits non-zero and writes
  nothing.
- **Gate**: `tests/test_sources.py` and `tests/test_data.py` for Chile —
  17 passed.

---

## 7. What is not drawn, and why

Twelve pending series are listed in `SOURCES.yaml` `meta.pending` with
their exact endpoints and failures. On the spine they cost four slots:

- markets slot 2 (10-year yield) — BCCh token, no BIS benchmark for Chile.
- markets slot 4 (equity index) — Bolsa de Santiago captcha, no Yahoo
  symbol, stooq challenge.
- people slot 3 (minimum wage) — see §5.
- mortality slot 3 (COVID-19 deaths) — no cause column anywhere
  retrievable.

The spending chapter's slot 1 will be short (2018-2024) and slot 4 short
(2007-2012) for the reasons in §4. Everything else on the spine is
filled.

---

## 7. What the plates draw, slot by slot

Phase B maps every staged file onto the spine. The slot each one claims,
and the conversions done at draw time (all of them on `core/rates.py`, none
of them arithmetic invented in `plates.py`):

| topic | slot | drawn from | conversion |
|---|---|---|---|
| economy | 1 growth | `macro/economy.csv: real_growth_pct` | none; bars, recession bands |
| economy | 2 GDP per person | `world/world.csv: gdp_per_person_usd` | none; log axis, shared ladder |
| economy | 3 inflation | `macro/economy.csv: inflation_pct` | none |
| economy | 4 unemployment | `macro/economy.csv: unemployment_pct` | none; ILO modelled, labelled |
| fiscal | 1 revenue/expenditure | `fiscal/fiscal.csv` | none |
| fiscal | 2 balance | `fiscal/fiscal.csv` balance + primary | none, two series |
| fiscal | 3 debt | `fiscal/fiscal.csv: debt_pct_gdp` | none |
| fiscal | 4 interest | — | **pending**: DataMapper has no GG interest code; Dipres is HTML |
| spending | 1 by function | `spending/cofog.csv` | seven groups; defence and public order stay separate `stackplot` layers, environment+housing+recreation are the spine's "other" |
| spending | 2 social vs rest | `spending/cofog.csv` | rest = total − social protection, same file |
| spending | 3 investment | `macro/economy.csv: gfcf_pct_gdp` | none |
| spending | 4 public investment | `spending/public_investment.csv` | none; 2007-2012 only |
| trade | 1 exports/imports | `trade/trade.csv` | none |
| trade | 2 balance | `trade/trade.csv: trade_balance_pct_gdp` | already derived in the file (exports − imports) |
| trade | 3 destinations | — | **pending**: one-year customs snapshot only |
| trade | 4 lens | `trade/partners_2024.csv` | shares as published; top ten bars, one year |
| markets | 1 policy vs CPI | `markets/policy_rate.csv` + `macro/economy.csv` | none (both annual means) |
| markets | 2 10-year yield | — | **pending**: BCCh token; no BIS benchmark |
| markets | 3 currency | `macro/fx.csv: clp_per_usd` | `ctx.fx_index` — 2006 = 100, inverted so up = stronger; 2025 = 55.7 |
| markets | 4 equities | — | **pending**: Bolsa captcha, no Yahoo/stooq series |
| credit | 1 household debt | `credit/household_credit.csv: hh_debt_pct_gdp_q4` | the Q4 stock, never the annual mean; 2026 has no Q4 and is not drawn |
| credit | 2 lending rate | — | **pending**: CMF HTML/403 |
| credit | 3 NPL | — | **pending**: CMF provisions, not an NPL ratio |
| people | 1 Gini | `people/gini.csv` | markers only, nine CASEN surveys |
| people | 2 poverty | `people/poverty.csv` | markers only; national line and the US$8.30 PIP line as two questions |
| people | 3 minimum wage | — | **pending**: statutory; next route is bcn.cl/leychile |
| world | 1 GDP | `world/world.csv: gdp_usd_bn` | none, log |
| world | 2 HDI | `world/world.csv: hdi` | none; stops 2023 |
| world | 3 CPI | `world/world.csv: cpi_score` | none; starts 2012 |
| world | 4 reserves | `world/world.csv: reserves_usd_bn` | none, log |
| demography | 1 population | `demography/demography.csv: population` | `ctx.index_2006`; 2025 = 120.3 |
| demography | 2 fertility | `demography/demography.csv: fertility` | none; 2.1 reference line |
| demography | 3 birth/death | `demography/demography.csv` | none, two published rates |
| demography | 4 natural/migration | `demography/demography.csv` + `migration/migration.csv` | none; both already per 1,000 on the UN population |
| security | 1 homicide | `security/security.csv: homicide_per_100k` | published rate used as published |
| security | 2 suicide | `security/security.csv: suicide_per_100k` | published rate, age-standardised |
| security | 3 road deaths | `security/security.csv: road_deaths_per_100k` | published rate |
| mortality | 1 death rate | `mortality/mortality.csv` national + WB | national = deaths ÷ DEIS population × 1,000 (in the file); WB = its own published rate on the UN population. Two lines, never one |
| mortality | 2 excess deaths | `mortality/mortality.csv` | in the file: (deaths ÷ mean 2015-2019 − 1) × 100; baseline 105,681 |
| mortality | 3 COVID | — | **pending**: no cause column anywhere retrievable |
| mortality | 4 lens | `mortality/mortality.csv: deaths` | the count itself, with the 2015-2019 mean as a dashed reference |
| migration | 1 flows | — | **pending**: SERMIG permits, not arrivals/departures |
| migration | 2 net | `migration/migration.csv: net_migration_per_1000` | none (count ÷ UN population × 1,000 in the file) |
| migration | 3 foreign-born | `migration/migration.csv` share | markers only, five-year UN stock |
| migration | 4 lens | `migration/migration.csv: net_migration` | persons a year, own scale |

No canonical y-scale is set in country code, and no staged value leaves the
shared range in `core/spine.py`: the widest reading of each slot is
growth 11.34 / −6.14, expenditure 33.60, fiscal balance 8.00, debt 41.8,
COFOG total 34.09, investment 26.88, exports 45.13, trade balance 14.02,
the policy rate's 2023 mean 10.50, household debt 48.3, Gini 47.7, poverty
28.7, GDP US$357.4bn, HDI 0.878, reserves US$51.3bn, population 120.3
index, homicide 6.80, death rate 6.98, excess deaths 29.9, foreign-born
7.78.

### Lens choices

Three lenses carry a story the canonical slots cannot:

- **Trade** — the 2024 goods snapshot: China takes 37.8% of a US$98.9bn
  total, more than the next two together. It is one year, labelled, and is
  not the annual series slot 3 would need.
- **Mortality** — the death count itself against its 2015-2019 mean, so a
  reader can see the 31,586 deaths of 2021 above the baseline rather than
  only the percentage.
- **Migration** — persons a year, because "12.6 per 1,000" hides that the
  2018 wave was 237,807 people and that 2020's collapse was a measurement
  artefact as much as a border closure.

Credit and security have no lens: nothing staged answers a fourth question
there, and the panel is hidden rather than filled with a duplicate line.

### Bands and events

The two recession bands in `country.yaml` are exactly the years of negative
real growth in `macro/economy.csv` (2009, 2020); a country test recomputes
the list from the CSV, so a refetch that adds a contraction fails the
build. Bands are drawn on every time-series panel and named only on the
first, at a height each panel's own scale leaves empty (the 2009 name above
a long Spanish title collided otherwise).

Three events come from `events.py` and nothing else is annotated: the
October 2019 *estallido social* on the GDP-per-person panel (the year after
it grew 0.6%), the 2011 copper peak on trade, and the 2022-23 tightening on
the policy-rate panel.

## 8. Still not drawn, and why

Five canonical slots and four national lines stay visibly pending; each
carries its route result on the panel and a full entry in `SOURCES.yaml`
`meta.pending` and `ui.json` `unavailable`:

- markets slot 2 (10-year yield) — BCCh token; no BIS benchmark for Chile.
- markets slot 4 (equity index) — Bolsa de Santiago captcha, no Yahoo
  symbol, stooq challenge.
- fiscal slot 4 (interest paid) — no general-government interest indicator
  on DataMapper; Dipres is HTML behind article pages.
- credit slots 2 and 3 (lending rate, NPL) — CMF HTML/403; provisions are
  not an arrears ratio.
- people slot 3 (minimum wage) — statutory but not machine-readable; next
  route is the laws on bcn.cl/leychile, one per reajuste.
- mortality slot 3 (COVID-19 deaths) — no cause column anywhere
  retrievable.
- trade slot 3 (annual destinations) — customs HTML; Comtrade's free
  preview is one period.
- migration slot 1 (gross flows) — SERMIG permits, not arrivals and
  departures.

Two national lines are pending rather than approximated: INE's own CPI and
labour-force survey (the World Bank's republication is drawn and labelled),
and the Carabineros/PDI and Fiscalía homicide count (UNODC's compromise
series is drawn and labelled). The spending plate's slot 1 is short
(2018-2024) and slot 4 short (2007-2012) for the reasons in §4; both
panels name their window.
