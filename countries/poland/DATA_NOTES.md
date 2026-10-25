# Poland — what the numbers mean

The research record is [DISCOVERY.md](DISCOVERY.md); the manifest is
[SOURCES.yaml](SOURCES.yaml). This file carries the judgement calls the
plates will depend on, and the ones that would be invisible in a chart.

## Territory and population

One territory: Poland, national scope, calendar years. The hard part is
not the border but the denominator.

**Two population series exist and only one is used.**

- The **revised, residence-based** series — GUS's post-2021-census figure,
  which Eurostat carries — is `demography.csv` → `population_jan`:
  38,157,055 on 1 January 2006 and 36,332,765 on 1 January 2026.
- GUS's own macro workbook still prints the **unrevised 31 December
  balance**: 37,766.3 thousand for 2022, about 1.0 million higher. The gap
  is the people the 2021 census found absent from Poland for twelve months
  or more.

The workbook's column is written to the sidecar so the diff shows it, and
is deliberately **not** staged. Every per-capita figure and every rate in
this country divides by the revised series. Using the unrevised balance
would understate every rate by about 3% from 2020 onward — a systematic
error that looks like a trend.

## The labour market: two definitions, and one printing quirk that matters

GUS prints each unemployment rate **twice, in adjacent rows**: the
labelled row states the years the publisher currently reports, and the
unlabelled row immediately below carries the longer back-run. The two
overlap, and in the overlap they behave differently:

- **BAEL (LFS)**: the rows agree (2021: 2.9% both). GUS's note says the
  LFS is methodologically consistent from 2010, so this is one series
  printed twice.
- **Registered rate**: the rows disagree — 2020 reads **6.8%** in the
  upper row and **6.3%** in the lower, 2021 **5.8%** against **5.4%**. The
  published national figures are 6.2% and 5.4% (the lower row).

The fetcher therefore joins them where they agree: the long row through
2021, the current row from 2022, no step at the join. The result is one
publisher's series, and `macro/economy.csv` carries exactly three
jobless columns:

| Column | What it is | Covers |
|---|---|---|
| `unemployment_registered_pct` | administrative registered rate (registered unemployed / economically active persons) | 2006–2025 |
| `unemployment_lfs_pct` | BAEL survey rate | 2010–2025 |
| `unemployment_estat_pct` | Eurostat's LFS **annual average** | 2009–2025 |

The registered rate is *administrative* and the BAEL rate is a *survey*;
the gap between them — about 2 points for two decades — is itself the
finding, and neither is spliced into the other. GUS's BAEL value is **the
last survey of the year** while Eurostat's is the **annual average**, which
is why both columns exist.

The residual 2020–21 disagreement between GUS's own two rows is a revision
the publisher did not mark in red (its legend reserves red for that). It is
recorded here rather than smoothed away; a plate that draws the registered
rate should note that its 2020 value is the long-row figure.

## Prices

The national CPI (`cpi_pct`) is GUS's annual index. The HICP (`hicp_pct`)
is Eurostat's harmonised index. They move together but are not identical —
from 2022 the HICP's housing weights differ — so both columns exist and the
plate draws the national line with the harmonised one beside it.

The story the panel has to carry: inflation at 14.4% in 2022 (the highest
in the EU), 0.0% in 2014 and −0.9% in 2015 (deflation), and 3.6% in 2024.
The National Bank's reference rate was 0.10% until October 2021 and 6.75%
at the end of 2022 — the real-rate trough.

## Money, currency and what is converted

Poland is outside the euro area and keeps the złoty. Every money slot is
labelled with its currency in the column name:

- `gdp_nominal_pln_bn`, `minimum_wage_pln_month`, `goods_*_mln_eur`,
  `household_debt_pct_gdp` (a ratio, unit-free), `gdp_usd_bn`,
  `reserves_usd_bn`, `gdp_per_capita_usd`, `minimum_wage_usd_month`.
- Eurostat national-accounts values are in **EUR** because that is how
  Poland reports them; the zloty figures are GUS's own.
- The minimum wage's dollar column is a **derivation**: statutory PLN at
  NBP's annual mean USD/PLN. Both columns are staged so the conversion can
  be audited rather than trusted.

## Fiscal

One definition, deliberately: ESA 2010, general government (S13), accrual,
calendar year — the EDP notification Poland sends to the Commission.
Eurostat and GUS publish the same aggregates and agree to the decimal
(2024: revenue 42.8%, expenditure 49.2%, deficit −6.4%, debt 54.8% of GDP),
so the GUS columns are a cross-check, not a second line.

Absent on purpose: the Ministry of Finance's **cash-basis state-budget**
deficit (a narrower perimeter, a different accounting basis) and its
**dług publiczny** (public debt, which excludes some agency liabilities and
runs a few points below the Maastricht debt). Both are official; neither is
the general-government series and neither is spliced into it.

2025 is GUS's **preliminary** estimate ('a' in the workbook): deficit
−7.2%, debt 59.6%. That is why `last_full_year` is 2024.

## Trade: two perimeters in one file

| Family | Perimeter | Unit | Publisher |
|---|---|---|---|
| `exports_pct_gdp`, `imports_pct_gdp`, `balance_pct_gdp` | goods **and services**, national accounts (ownership change) | % of GDP | Eurostat P6/P7 |
| `goods_exports_mln_eur`, `goods_imports_mln_eur`, `goods_balance_mln_eur` | **customs goods** only (INTRASTAT + EXTRASTAT) | EUR million | GUS |
| `partners.csv` | customs goods by destination | % of world goods exports | Eurostat Comext |

2024: EUR 353bn of goods at customs against EUR 443bn of goods and services
in the national accounts. The difference is services and conventions. They
are never the same series and are never joined.

Poland's export geography is the convergence story: Germany ~25%, Czechia
~4.3%, and after 2022 Russia falls out of the list while Ukraine rises.

## Markets — the one panel that is not the peers' statistic

`nbp_reference_rate_year_end_pct` is the NBP reference rate on **31
December**. Every other country in the atlas draws an annual mean. NBP's
daily policy-rate series sits behind a site challenge and `api.nbp.pl`
exposes only exchange rates, so the daily mean cannot be computed from a
machine source here. The plate must say "reference rate, 31 December" in
its caption; the alternative — pretending the year-end value is an annual
average — would misstate 2022 by nearly two points.

The currency is drawn as an index where **up = stronger**: `pln_index_usd_2006`
= 2006 mean ÷ year mean × 100, so the 2008 zloty collapse (2.37/US$) and
the 2022 weakening (4.69/US$) both read as falls.

`chf_pln_year_end` is staged because it is the rate Poland's
franc-denominated mortgage holders actually read, in 2008 and again after
the Swiss National Bank removed the peg in January 2015.

The WIG20 is **pending**: see `SOURCES.yaml` `meta.pending`. No official
exchange series could be assembled in this pass.

## People

Three poverty numbers, three thresholds, none interchangeable:

- `gini_eurostat` — EU-SILC Gini, 0–100 (24.9 in 2025, from 32.1 in 2014).
- `arop60_pct` — at-risk-of-poverty after transfers at **60% of median**,
  the EU headline (13.2% in 2025).
- `relative_poverty_after_transfers_pct` — GUS's national series at **50%
  of median** (13.8% in 2024), with the pre-transfer rate beside it (45.4%)
  so the effect of transfers is visible rather than asserted.

The minimum wage is the statutory monthly gross rate. Poland legislated a
**second increase on 1 July** in 2023 and 2024, so those years have two
rates; the staged value is their mean and the two halves are in the sidecar.
The dollar column converts at NBP's annual mean.

## Migration is four numbers, and the register is the one that fails

This is the chapter where a careless chart would be worst.

| Number | 2022 | What it measures |
|---|---|---|
| `immigration_registered` | 275,515 | meldunek registrations — **did not see the refugees** |
| `emigration_registered` | 228,006 | the same register, outward |
| `net_migration_registered_per_1000` | 0.2 | the register's own balance |
| `net_migration_residual_per_1000` | 12.6 | population change minus natural change |
| `temporary_protection_beneficiaries` | 961,340 (end-2022); 954,800 (end-2023) | people under temporary protection |
| `foreign_citizens` / `foreign_born` | 435,964 / 933,118 (1 Jan 2023) | two legal cuts of the same stock |

The Ukrainian inflow of 2022 was roughly a million people, and the
residence register recorded about a tenth of it, because registering a
permanent residence was not what refugees did. The population-balance
residual and the temporary-protection stock are the two measures that show
it; both are estimates or status counts, and both are labelled.

The citizenship cut and the birthplace cut diverge by half a million
people on the same day: naturalisation and repatriation move somebody
across the citizenship line without anybody moving. Eurostat's Polish
citizenship table carries only groups (EU27, non-EU27, foreign+stateless),
never single countries, so there is no "Ukrainian citizens" column to draw
— a limitation of what Poland reports, not of the fetch.

Asylum applications, first residence permits (permits **issued**, not in
force) and acquisitions of citizenship are three further questions. They
are staged as three columns and are never one line.

## Mortality

`deaths_all` and the crude rate are `demo_gind` (2006+). Causes are
`hlth_cd_aro`, which starts in 2011 — the earlier years are blank in the
cause columns, not zero.

**Excess deaths** is derived: `deaths_all` against the mean of 2015–2019
of the same series, one formula, one vintage — +18.8% in 2020, +29.2% in
2021, +1.6% in 2024. The cause table's own total for 2024 (409,194)
differs from the vital-statistics total (408,504) by 0.2%; both are
published as they are.

**COVID deaths** are U071 + U072, underlying cause: 41,486 (2020), 90,228
(2021, 243 per 100,000), 29,072 (2022). Poland's 2021 wave is the largest
single feature of the mortality chapter.

## Security — two homicide counts, a factor of three apart

- Police **confirmed offences** include attempts: 559 in 2023, 1.52 per
  100,000. Proceedings initiated: 574.
- Vital-statistics **assault deaths** (ICD X85–Y09): 197 in 2023, 0.54 per
  100,000.

Both are official, both are staged, and they answer different questions.
A single "homicides" line built from one and labelled with the other's
meaning is the mistake this chapter exists to avoid.

Suicides: 4,580 in 2023 (12.5 per 100,000), down from a 2006 peak of about
17 per 100,000 by the WHO estimate and 5,000-plus deaths by the national
count. `transport_deaths` is **broad transport** (V–Y85: road, rail, air,
water), not road-only; `road_deaths_who_per_100k` is the WHO estimate and
stops in 2019, the last year WHO published.

## Credit

`household_debt_pct_gdp` is the BIS's harmonised series — credit to
households and NPIs from all lenders, break-adjusted, read at Q4: 18.3% in
2006, a peak near 34% around 2011, 22.6% in 2024. Low by EU standards and
one of the few places where Poland is *not* converging upward.

`npl_ratio_pct_q4` is the EBA Risk Dashboard's NPL ratio for its reporting
banks in Poland — **large banks, not the whole sector**, so it sits below
the NBP's sector-wide ratio (which is unreachable from this network). That
scope is on the panel, not only here.

The **lending-rate slot is pending** and the debt-service ratio is not
staged: every official route was tried and recorded (NBP behind a
challenge, Eurostat's MIR codes absent for PL, the World Bank's lending
series empty for Poland, KNF unreachable, the BIS DSR key unresolved).

## Gaps and coverage, per series

`last_full_year` is 2024 because GUS marks 2025 as a preliminary estimate
in the national accounts, the EDP aggregates and external trade. The
series' own ends are shorter than that and stay visible:

| Series | Ends | Why |
|---|---|---|
| CPI, minimum wage (Eurostat), GDP | 2025 (2026 for the wage) | published annually, ahead of the accounts |
| HDI | 2023 | the Human Development Report runs two years behind |
| CPI score | 2024 | the 2025 edition's workbook answers S3 AccessDenied |
| Police homicide | 2023 | the publisher's attachment stops there |
| Assault / self-harm / COVID deaths | 2024 | cause-of-death table |
| WHO road deaths, suicide estimate | 2019 / 2021 | WHO publication cycle |
| World Bank NPL cross-check | 2020 | the Bank's FSD compilation |
| Temporary protection | 2026 (August) | monthly, current |
| Gini (Eurostat) | 2025 | EU-SILC |

## What is not drawn, and why

- **WIG20** (markets slot 4): pending. GPW's archive is per-session and
  JS-driven, Yahoo returns a single point, stooq is JS-walled, OECD's flow
  is non-production, FRED is Cloudflare-blocked.
- **Household lending rate** (credit slot 2): pending, with five routes
  recorded.
- **Policy-rate daily mean**: not available; the year-end reading is drawn
  and labelled instead.
- **Pre-2012 CPI**: a 0–10 index on a different method; not multiplied by
  ten and spliced.

## Fetchers

Ten scripts, one per publisher, all writing `*_from_<source>.csv` sidecars
and never a curated file:

| Script | Publisher | Sidecars |
|---|---|---|
| `fetch_eurostat.py` | Eurostat statistics API | 13 files across macro, fiscal, spending, trade, markets, people, demography, mortality, security, migration |
| `fetch_gus.py` | GUS annual indicators workbook | economy, fiscal, demography, markets, trade, people |
| `fetch_nbp.py` | NBP Table A | markets |
| `fetch_worldbank.py` | World Bank WDI | macro, world, people, security, credit |
| `fetch_bis.py` | BIS total credit | credit |
| `fetch_eba.py` | EBA Risk Dashboard | credit |
| `fetch_undp.py` | UNDP HDR | world |
| `fetch_ti.py` | Transparency International | world |
| `fetch_comext.py` | Eurostat Comext | trade |
| `fetch_police.py` | Polish Police | security |

`fetch/common.py` holds the cache, the shape checks and the deterministic
CSV writer; `fetch/eurostat.py` holds the JSON-stat decoder. Two runs
against a warm cache produce byte-identical sidecars; a cold run with no
network exits non-zero and writes nothing. `fetch_ti.py` reads the CPI
workbook straight out of the zip because its edition is strict OOXML,
which openpyxl refuses.

## What the plates draw, and how

Twelve chapters on the spine: economy, fiscal, spending, trade, markets,
credit, people, world, demography, security, mortality, migration. Every
panel claims its slot key in spine order, so the comparison viewer wipes a
Polish panel over the same panel of every other country.

**Conversions, and the population they divide by.** One denominator
throughout: `demography.csv` → `population_jan`, the revised residence
series, on 1 January of the year named. Where the publisher already
publishes the rate, that rate is drawn rather than recomputed (the police
homicide rate, the LFS, the crude birth, death and natural-change rates,
the BIS debt ratio, the Eurostat shares). The four derived panels:

| Panel | Formula | Base |
|---|---|---|
| mortality, excess deaths | `deaths_all` against its own 2015–2019 mean | one vintage |
| mortality lens, circulatory and cancer | cause counts ÷ `population_jan` × 100,000 | same year |
| migration slot 3, protection stock | beneficiaries ÷ `population_jan` × 100 | same year |
| demography slot 1 | the staged `population_index_2006` column | 1 Jan 2006 = 100 |

`tests/test_plates.py` recomputes each of them from the CSVs and pins the
result, including the 2023 police-homicide rate at 2.84× the assault-death
count and the currency index at 129.0 (2008) and 69.6 (2022).

One derived column was recomputed in this phase. `excess_deaths_pct_vs_2015_2019`
did not reproduce from its own documented formula (2021 read +29.02% where
`deaths_all` against the 2015–2019 mean gives +29.25%), so the column was
recomputed from the committed counts at one vintage: +18.8% in 2020,
+29.2% in 2021, +1.6% in 2024. The plates, the notes and the manifest all
read the new values; the formula is unchanged.

**Drawn as seams, never joined.** CPI against HICP (two lines, both
named); the BAEL survey against the administrative register (two lines,
about two points apart, and the 2020 register point is the long-row 6.3%,
not the upper row's 6.8% — GUS's own unmarked revision, recorded above);
goods and services in the national accounts against customs goods (two
panels: a share of GDP and EUR billion, which disagree in sign in 2013,
2018 and 2022); police-confirmed offences against assault deaths (2.84×
in 2023 — an offence count is not a death count); the EBA's large-bank NPL
ratio against the World Bank's system-wide one (2014+ against 2006–2020);
circulatory against cancer deaths; the register's net-migration rate
against the population-balance residual.

**Two scales the atlas has not widened.** `migration.net` and
`demography.natural_migration` are visibly pending, with the reason on
the panel and in `ui.json`: in 2020 Eurostat's registered net-migration
rate is −20.3 per 1,000 and the population-balance residual −16.7, both
outside the shared −10…+40. Both series are drawn on their own scale in
the migration chapter's lens rather than flattening the peers, exactly as
Ukraine's wartime displacement is. `country.yaml` records the two slots
and the values; if the orchestrator widens those ranges, both slots can
be claimed with no other change.

**The lens choices**, one per topic, are the country's own story and not
expected to register with a peer: the customs goods balance in EUR
(trade), the two NPL compilations (credit), the statutory wage in zloty
beside the dollar one (people), police offences against assault deaths
(security), circulatory and cancer deaths (mortality), and the two
net-migration series (migration).

**Running years.** `last_full_year` is 2024, so 2025 and 2026 are drawn
dashed or hatched on every time-series panel, even where the publisher
has printed a value: GUS marks the 2025 national accounts, EDP aggregates
and trade as preliminary. The cards read the last full year for flows and
the latest point for levels, and say which year they mean.

**One rounding seam, recorded.** The COFOG stack's top for 2024 is the sum
of the seven published layers, 49.3% of GDP, against the publisher's own
`total_pct_gdp` of 49.4% — each layer is published to one decimal and the
sum drifts. The annotation prints the stack (49.3), because that is what
the reader sees; the difference is not reconciled.
