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

## Not drawn, on purpose

Fiscal, trade, markets, credit, security and mortality chapters are not
published at all this pass rather than assembled from a different perimeter
or a partner's mirror data. The blocked publishers and their exact failure
modes are in `SOURCES.yaml` `meta.pending`, and the page discloses the
absence in each locale.

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

## Still not drawn

Credit is the one chapter deliberately absent: the NBU publishes credit
aggregates as monthly distributions that need their own definition
review, and no comparable household-debt series is staged. The remaining
pending slots are listed on the page in all three languages and in
`ui.json`.

The atlas-wide ranges were widened a second time for this pass —
revenue/expenditure to 80, fiscal balance to -24, trade balance to -30
and the crude death rate to 22 — with every country regenerated.
