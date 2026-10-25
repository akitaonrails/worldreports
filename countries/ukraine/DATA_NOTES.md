# Ukraine — what the numbers mean

The research record is [DISCOVERY.md](DISCOVERY.md); the manifest is
[SOURCES.yaml](SOURCES.yaml). This file carries the judgement calls the
plates depend on.

## Territory

Two different territories are drawn, and never joined:

- **Ukrstat's register** (`demography/population_ukrstat.csv`) excludes the
  temporarily occupied territories from 2015 — Crimea and Sevastopol, and
  from 2022 the occupied parts of Donetsk, Luhansk, Kherson and Zaporizhzhia
  oblasts. The publisher's own note says so. The step from 45,426,249 (2014)
  to 42,929,298 (2015) is that perimeter change, not a demographic event,
  and is annotated on the plate. The series ends at 1 January 2022.
- **The World Bank / UN estimate** (`demography/population.csv`) includes
  Crimea throughout (2021 = 44,298,640; 2025 = 38,980,376).

The atlas draws both as separate labelled lines. No value from one is ever
used to fill a year of the other.

## The shared comparison scale was widened

Ukraine's 2022 real GDP growth is −28.76% (World Bank national accounts;
the IMF WEO says −28.8 on its own vintage). That is outside the atlas-wide
range the economy topic used before this country joined (−18 to +18), and
the register's 2022 index (79.8 on 2006 = 100) is outside the population
slot's old floor of 80. Per PLATE_SPINE the range is widened once in
`core/spine.py` — growth to (−32, 18), population to (75, 150) — and every
country carrying those topics is regenerated. No country overrides its own
scale.

## Derived series

**The price level** on the people plate is derived, not published: the
annual CPI inflation rates in `macro/economy.csv` are chained from 2006 =
100 (`level[t] = level[t−1] × (1 + cpi[t]/100)`), one vintage. 2025 lands at
about 1,006, i.e. 10.1× the 2006 price level. The plate says it is derived.

## Gaps, and why they stay gaps

- **Unemployment** stops in 2021. The World Bank's ILO-modelled estimate has
  no value for 2022–2025 because no labour-force survey was run in the war
  years. The rows are blank, not zero, and the plate labels its last value
  as modelled.
- **Gini** stops in 2020: the household survey behind it was suspended.
- **Births, deaths, fertility, migration**: Ukrstat publishes them to 2022,
  but the cached SDMX dataflow's dimension code list does not identify the
  total series unambiguously. That is incomplete definition research, and
  the panels stay pending rather than drawing a series that might be a
  sub-slice (for example, births to one citizenship group).
- **Poverty, minimum wage**: the survey has not published since 2021; the
  statutory minimum is set in hryvnia and no official monthly US$ series is
  staged.
- **Corruption Perceptions Index**: Transparency International's workbook
  answers 403 to this network.

Each pending slot names its reason on the panel and in `ui.json`; none is
filled with a proxy.

## Fetchers

`fetch/fetch_comparables.py` writes the World Bank, IMF and UNDP sidecars;
`fetch/fetch_ukrstat.py` writes the SSSU population sidecar from the SDMX
dataflow payload (offline from the cache, since stat.gov.ua answers 403 to
this network). Both write `*_from_*` review sidecars only — the curated
CSVs are a separate reviewed step — and both are re-runnable: two offline
runs produce byte-identical sidecars.

## Historical first-pass omissions (superseded by nine-plate edition)

The initial four-chapter release had no fiscal, trade, markets, credit,
security or mortality plates. The later upstream update filled fiscal,
trade, markets, security and mortality from compatible verified sources,
as described below. **Only credit remains an unpublished chapter.**
The Treasury cash series introduced here complements — it does not
replace — the current IMF general-government fiscal plate.

## Fiscal, trade, markets, security and mortality

These five chapters were added after the route audit (2026-10-24): the
national publishers that block automated access are the Ministry of
Finance, the customs service and the Prosecutor General, but the
harmonised layer and the central bank answer.

- **Fiscal** — IMF WEO (October 2026 vintage), general government, one
  vintage for all six columns. Observed to 2024; the 2025 debt figure
  (107.1% of GDP) is the latest WEO year and stays in its `_proj` column
  in the sidecar, never drawn as observed. Interest is the published
  `ie` series, not a subtraction of two rounded balances.
- **Trade** — World Bank national accounts, goods and services. The
  balance is derived from the same two columns on the plate, never from
  a second publisher.
- **Markets** — the NBU's own statistics API: the key policy rate
  (`KEY_PolicyRate`, annual mean of the daily rate) and the official
  exchange rate (`rate_per_unit`, annual mean). The hryvnia index is
  2006 = 100, up = stronger, so the line falls as the currency weakens.
- **Security** — UNODC and WHO rates via the World Bank. Homicide and
  suicide stop in 2021 and road deaths in 2019; the holes are real.
- **Mortality** — crude death rate and life expectancy from the World
  Bank. The 2021 death-rate peak (17.1 per 1,000) is drawn at its size.
- **Spending** — the NBU/Treasury monthly budget execution, consolidated
  budget, cash basis, functional classification. December is the
  year-to-date total; `Total_1` is asserted to equal the sum of the ten
  functions, and the inter-budget transfer (0180) is excluded or the
  stack would double-count it. It is NOT the IMF accrual layer the
  fiscal chapter draws, and both plates say which is which.
- **Migration** — the UN/WB net-migration estimate to 2021 on the
  canonical scale; the 2022 wartime displacement (−139 per 1,000) is
  drawn in the lens on its own scale, labelled, because widening the
  comparison range to fit a war would flatten every other country.
  Migrant stock is a snapshot series (2010, 2015, 2020, 2024).

## Still not drawn

Credit is the one chapter absent, and the route audit is the reason it
is not drawn rather than a reason it was not tried: IMF `HH_ALL` has no
Ukraine series; the NBU `loan` endpoint publishes monthly dimension
slices, and its mortgage and consumer components exceed their own total
before 2016 (2010: 214.4bn total against 239.9bn of components), so the
composition is not definitionally consistent; `banksfinrep` carries loan
provisions, not a non-performing ratio; `data.gov.ua` has no NPL dataset;
and the lending rate has no machine series in the open API. Publishing a
single line beside three empty panels would not be an edition, so the
chapter waits for a consistent NBU household-credit and NPL series. The
remaining pending slots are listed on the page in all three languages and
in `ui.json`.

The atlas-wide ranges were widened a second time for this pass —
revenue/expenditure to 80, fiscal balance to -24, trade balance to -30
and the crude death rate to 22 — with every country regenerated.

## Treasury fiscal data — annual reference dates and scope (2026-10-24)

The **NBU republishes State Treasury cash-budget execution**, not harmonised
IMF general-government accrual statistics. The reviewed data in
`fiscal/treasury_functional.csv` are **2011–2025 consolidated budget (CBU)**
functional outturns, measured in **million nominal UAH**, split into the ten
original top-level Ukrainian budget classification codes `0100`–`1000`.
The reported `gf_budgtef_Total_1` is **expenditure excluding interbudget
transfers**, not an additional category. National functional classes must
not be treated as a checked mapping to the atlas's seven COFOG-like groups.

**Critical date mapping:** in the NBU `budget` cube, an annual record
`dt=20240101` reports the **2023** calendar-year execution.
`dt=20250101` reports **2024**. The previous research probe mistakenly
treated the NBU January date as the same calendar year. It was corrected
rather than imported wholesale. The source date is kept as a separate
column, so this rule can be audited without inferring it from a chart.

The independent cross-check is the **Ministry of Finance** statistical book
[Budget of Ukraine 2024](https://mof.gov.ua/storage/files/Badgef%20of%20Ukraine2024.pdf),
especially section **2.3, pages 34–37**, with:
- **2023:** defence 2,097,621.9 million UAH; consolidated spending
  4,441,364.6 million UAH.
- **2024:** defence 2,305,242.7 million UAH; consolidated spending
  4,945,680.7 million UAH.

All 15 annual ten-category sums reconcile with the same-year functional
total within **0.3 million UAH** (source presentation rounding).
A **stronger independent cross-check** is now available: the
[Ministry of Finance's 2025 ANNUAL consolidated-budget workbook](https://www.mof.gov.ua/storage/files/4_%D0%97%D0%91_%D1%80%D1%96%D0%BA_%D1%81%D0%B0%D0%B9%D1%82_25.xlsx),
sheet **`2025 рік`**, publishes **6,006,387.27484437 million UAH**
for 2025 functional spending, **3,069,857.41825598 million UAH**
for defence and **264,998.32655720 million UAH** for economic affairs.
All ten functional categories match the NBU's 2025 annual observations
within **0.05 million UAH**, the NBU's one-decimal reporting precision.
The Ministry's category `0100` is split into *general public services
excluding debt servicing* (**149,697.44444124 million**) and *debt
servicing/derivative payments* (**362,494.81121092 million**). Adding only
those two subcomponents recovers the NBU's `0100` rounded amount
(**512,192.3 million UAH**). This is a within-classification
reconciliation, not an unverified COFOG conversion.

The [Open Budget consolidated portal's DECEMBER 2025 edition](https://openbudget.gov.ua/?budgetType=CONSOLIDATED&month=12&year=2025)
instead lists **5,999,467.11164619 million UAH** for spending and
**258,106.094607 million** for economic affairs. The later annual
publication is **6,920.18835381 million UAH higher** overall, of which
**6,892.23195020 million UAH** relates to economic affairs. The earlier
edition is preserved in `fetch/reference_openbudget_2025.csv`; the annual
edition is preserved in `fetch/reference_mof_2025_annual.csv`.
**The apparent NBU-versus-Open-Budget disagreement was a comparison
between two publisher editions**: the annual MoF figures independently
confirm the NBU values. This does NOT establish which administrative
bookings or revisions caused the change from December to annual.

The non-governmental index.minfin.com.ua site carries the earlier
December edition for 2025 and has some differences in earlier years.
Those differences are not used to revise the curator's independently
verified annual series. Neither cash-budget vintage is mixed with the
IMF's general-government accrual accounts.

The economic-classification total `gf_budgtee_Total` does not agree
exactly (for example, the 2023 fiscal-year observation is 4,433,206.4
million UAH); its variance is not discarded or blended into the
functional time series. Revenue / balance / financing classifications
must receive their own identity verification before use. The signed
`gf_budgtfd_total` is financing with deficit-positive sign — **not** a
general-government primary balance. We stage none of those as fiscal
accounts yet.

**Discontinuities and limits:** the wartime fiscal envelope and territory
of execution may change around 2014 and 2022. This is not a constant-
territory panel; nominal expenditures may change because of prices,
administrative scope or budget priorities. Values are not inflation
adjusted, expressed as GDP shares, reconstructed, interpolated or
converted to USD. Do not infer constant-definition expenditure growth.
The national functional categories remain supplementary **source material**
until a defensible national-only plate is implemented and visually reviewed.

`fetch/fetch_treasury.py` re-fetches the full JSON cube and writes
`fetch/cache/treasury_functional_from_nbu.csv` **only** (a review sidecar).
It validates JSON and field names, annual dates, unit, parent/category
hierarchy, duplicated codes, annual gaps, numeric sanity, Ministry of
Finance anchors and within-year reconciliation. It never overwrites
the committed source-of-truth CSV. Compare the entire historical sidecar
to the curated CSV before accepting revisions.
