# Hong Kong — data notes

What these files mean, how each derived column was computed, which population
denominator sits under which rate, and what is deliberately not drawn. The
provenance claim per file is `SOURCES.yaml`; the route-by-route research log
is `DISCOVERY.md`.

## 1. What this country is, in the data

Hong Kong is a Special Administrative Region of China. Every series here is
the SAR's own: C&SD's national accounts, the HKMA's rates and reserves, the
Department of Health's registered deaths, the police's reported offences. No
Chinese national series appears anywhere in `data/`, and no Hong Kong series
is presented as a Chinese one. The World Bank, the IMF, UNDP, the BIS and
Transparency International all report Hong Kong as its own economy (`HKG`);
none of them reports it inside `CHN`.

The page's dek says this plainly rather than leaving it to the notes.

## 2. The window, and what "2025" means

`years: {from: 2006, to: 2026}`, `last_full_year: 2025`.

2025 is complete for everything staged: C&SD published revised 2025 annual
GDP (3,329,843 HK$mn), the 2025 labour-force average, the 2025 CPI average,
2025 merchandise trade and 2025 population components; the HKMA published
2025 year-end reserves and asset quality; the Department of Health's cause
series runs to 2024 (its own file's last year) and 2025 is left empty there
rather than inferred; C&SD's services trade table has not released 2025 at
this vintage and 2025 is empty there too.

2026 exists only as quarters and half-years (GDP to 2026Q2, population to
2026-06, CPI to 2026-09) and is drawn as the running year, dashed, never as a
year's result. Where a series has no 2026 observation at all the cell is
empty.

## 3. Derived columns, and exactly how they were derived

Only six columns in `data/` are computed rather than copied. Each is stated
here so a reader can reproduce it from the committed inputs.

| file | column | formula |
|---|---|---|
| `macro/gdp.csv` | (none — all copied) | — |
| `fiscal/govt.csv` | `balance_hkd_mn` | revenue − expenditure, same financial year |
| `fiscal/govt.csv` | `revenue_excl_fund_transfers_hkd_mn` | revenue − "transfers from Funds" (REV_4) |
| `spending/investment.csv` | `gfcf_pct_gdp`, `public_gfcf_pct_gdp` | GFCF ÷ nominal GDP × 100, same year |
| `trade/trade_gdp.csv` | all three columns | exports/imports/balance of goods and services ÷ nominal GDP × 100 |
| `trade/destinations.csv`, `trade/products.csv` | `share_pct` | partner or product exports ÷ that year's total exports × 100 |
| `markets/equity.csv` | `hsi_usd_index_2006` | (HSI ÷ HKD per US$ in that year) ÷ (HSI 2006 ÷ HKD per US$ 2006) × 100 |
| `world/gdp_usd.csv` | `gdp_usd_bn` | NY.GDP.MKTP.CD ÷ 1e9 |
| `demography/population.csv` | `growth_pct` | year-on-year change of the mid-year series, one vintage |
| `demography/components.csv` | every column | the December observation — the publisher reports a 12-month change at each half-year point, so the two halves are never summed |
| `demography/fertility.csv` | `tfr` | published per 1,000 women ÷ 1,000 |
| `security/crime.csv` | `homicide_rate_per_100k` | murder and manslaughter cases ÷ mid-year population × 100,000 |
| `mortality/deaths.csv` | `excess_deaths_pct_vs_2015_2019` | deaths ÷ mean(2015-2019 deaths) − 1, × 100 |
| `migration/net_movement.csv` | `net_movement_per_1000` | net movement (thousands) ÷ mid-year population (thousands) × 1,000 |
| `people/income.csv` | `median_household_income_real_2024_hkd` | median monthly household income ÷ composite CPI × 100 |

No column is interpolated, forward-filled or zero-filled anywhere in the
directory. Where a publisher has not released a year the cell is empty and
the plate must break the line.

## 4. Population denominators

Three different populations appear in Hong Kong statistics and they are not
interchangeable:

1. **Mid-year population** (C&SD 110-01001, June) — the denominator used here
   for homicide rates and net-movement rates. Includes foreign domestic
   helpers and all usual residents.
2. **Land-based non-institutional population** — the labour force survey's
   frame. The LFS covers people living in households, so foreign domestic
   helpers living with their employers *are* covered by the headline LFS but
   C&SD also publishes an "excluding FDH" variant of most labour tables. The
   staged labour series is the total, not the FDH-excluded one.
3. **Population excluding foreign domestic helpers** — the variant behind
   `TFR_XFDH` and several dependency ratios. It is smaller by roughly 340,000
   people (~4.5%), which is why a fertility rate computed on the total
   population and one published on this base are not the same number.

Where the rate is published by the office that counts it (crude birth and
death rates, life expectancy), the published rate is used rather than
recomputed.

## 5. The seams that must not be spliced

**Fiscal year versus calendar year.** `fiscal/govt.csv` labels a year by the
start of the financial year (2024 = 1 April 2024 to 31 March 2025) and runs to
FY2025; `fiscal/gg_imf.csv` is calendar year and stops at 2024, the last
observed WEO year — the IMF payload's debt column continues to 2031 as staff
projections, which are not staged as outcomes. A ratio of the national cash accounts to
calendar-year GDP is therefore approximate at the March boundary; the plate
says "financial year" on the national line and draws no such ratio without
saying so. The two files are never joined into one series.

**Cash GRA versus general government.** The national account is cash, on the
government's own perimeter, and its revenue total contains transfers between
government funds. The IMF series is accrual-adjacent GFS on the general
government perimeter with intra-government transfers netted out. In 2024 the
national account shows a surplus on its own definition while the IMF shows a
primary deficit of 5.6% of GDP, because the two are measuring different
government. Both are correct; they are two labelled lines.

**Customs trade versus national accounts.** `trade/merchandise.csv` is goods
crossing the boundary at customs value and includes re-exports.
`trade/trade_gdp.csv` is goods *and services* on the national-accounts basis
and is the only one comparable with other countries' trade ratios. They move
together but they are not the same number, and the gap is services.

**Government consumption versus total spending.** `spending/gce_function.csv`
is GCE: the government's own consumption. Cash transfers are outside it.
Consequently "social protection" is 3.7% of GCE in 2025 and health is 30.5%;
a reader who takes those shares as shares of total government spending will be
wrong by a wide margin. The plate's caption has to carry this.

**Reported crime versus death certificates.** `security/crime.csv` counts
offences reported to the police, from 2021 (the classification re-base).
`mortality/deaths.csv` counts registered deaths by underlying cause. They are
different populations, different counting places and different definitions of
the same event, and are never compared as though one checked the other.

**Net movement versus migration.** `migration/net_movement.csv` is the
publisher's residual: population change minus births plus deaths, over the
twelve months to 31 December. It absorbs residents' moves, foreign domestic
helpers' arrivals and departures, and any error in the population estimate.
C&SD splits it into one-way permit holders from the Mainland and everyone
else, and that split is staged because it is the publisher's own: in 2024 the
one-way component was +40.0 thousand while the rest was -52.5 thousand. It is
a net figure within a permit category, not an arrivals count, and the plate
calls the whole thing by the publisher's name, never "net migration".

**COVID-19 coding.** The Department of Health coded COVID-19 deaths to J98.8
up to 2023 and to U07.1/U07.2 from 2024. The series is continuous in intent
but the code behind it changes in 2024; the publisher's note travels with the
file and the plate carries the note.

## 6. The 2025-Q4 crime anomaly

`security/cases_from_censtatd.csv` reports 170 murder and manslaughter cases
in 2025-Q4, against 19 across the first three quarters of the year (5, 2 and
12). The quarterly series is internally consistent and the annual row repeats
it, so it is published as it stands. It is an order of magnitude above every
other quarter in the table. The security plate must annotate that quarter
rather than let a reader read the annual line as a trend. Phase B should
decide the annotation's wording from the police release for that quarter.

## 7. What is not drawn, and why

Recorded as `meta.pending` in `SOURCES.yaml` and, in Phase B, as the page's
unavailable-data disclosures:

- **10-year government bond yield.** No continuous benchmark exists. The
  EFBN closing archive's 10Y-coded notes had under two years to maturity at
  every year-end 2015-2023 and no 10-year note is outstanding from 2024. The
  probe is kept as `markets/efn_tenor_probe_from_hkma.csv` so the finding is
  reproducible.
- **Gini, poverty, minimum wage.** Published in thematic reports, report
  attachments and Gazette notices; none on a machine-readable official route
  this pass could find. The `people` chapter has three canonical slots
  pending and says where each number lives. Its lens slot carries the median
  household income (`people/income.csv`), which is the income series that
  *does* exist as a table.
- **Suicide, road deaths.** The Department of Health aggregates suicides into
  "external causes"; Hong Kong is not a WHO member state so GHO carries no
  row; WDI is empty for both. Not guessed from adjacent series.
- **Gross immigration and emigration; foreign-born share.** Neither is
  published on a residence basis; the census gives a single foreign-born point
  (2021) and the atlas does not interpolate between census points.
- **COFOG.** Hong Kong publishes a national functional classification of
  government consumption, not COFOG, and is not an OECD member. The national
  classification is staged and mapped onto the spine's seven groups, labelled
  as a national classification.

## 8. Judgements that could reasonably have gone the other way

**Reserves: national, not World Bank.** The World Bank's FI.RES.TOTL.CD stops
in 2023; the HKMA's own table 8.4 runs to 2026 and its 2023 value
(425,554 US$mn) matches the World Bank's 425,554,111,033 exactly, which is
what licenses using the national series for the recent years. The series is
the Exchange Fund's foreign currency assets, not the government's fiscal
reserves in HK$.

**Base Rate via the BIS.** The HKMA's API refused this network after its
first call, so the rate comes from the BIS compilation of the HKMA's official
base rate. The published value on the day of the one successful call (4.25%
on 2026-10-23) matches the BIS series' last observation, which is the
cross-check.

**HSI year-end, not annual average.** Yahoo's monthly bars give year-end
closes. Taiwan's plates use the exchange's official annual average where one
exists; Hong Kong's index compiler publishes no official annual average
series, so the year-end point is what exists and is labelled as a point.

**Fertility excluding foreign domestic helpers.** This is the publisher's
headline TFR and the one comparable with other countries' TFRs (it agrees
with the World Bank's 0.84 for 2024). The all-women rate would be a different
series and is not staged.

**Crime from 2021 only.** Tempting to fetch an older police series to lengthen
the panel; the re-based classification makes that a splice across a
definitional break, so the panel is short and honest, with the World Bank /
UNODC homicide series standing in for the long comparison.

## 9. Refreshing

```sh
make C=hongkong fetch          # runs the six fetchers, rewrites sidecars only
python3 -m countries.hongkong.fetch.fetch_censtatd --offline   # cold cache fails loudly
```

Then diff each `*_from_*.csv` against its curated file, promote accepted
values by hand, bump `last_full_year` when a year completes, and re-run the
gate:

```sh
TMPDIR=.slim/tmp/hongkong python3 -m pytest -q \
  --basetemp=.slim/ptmp/hongkong tests/test_sources.py tests/test_data.py -k hongkong
```

The fetchers assert a published value before writing, so a payload that
answers 200 with the wrong table fails instead of committing.

## 10. Three slots the shared comparison scales cannot hold

The atlas draws one y-scale per canonical slot (`core/spine.py`) so a reader
can wipe one country's plate over another's. Hong Kong has three readings
that leave those ranges by more than a rounding, and one country may not
carry a scale of its own. Each is visibly pending on its panel, with the
extent and the reason, and each is drawn in a lens at its own scale so the
data are still published:

| slot | reading | shared range | drawn where |
|---|---|---|---|
| `trade.exports_imports` | 176.3% to 221.6% of GDP (2006–2025) | 0 … 100 | `trade.lens`, own scale, beside the customs goods ratio |
| `migration.net` | −11.5 per 1,000 in 2020 | −10 … +40 | `migration.lens`, own scale, with the one-way/others split |
| `demography.natural_migration` | the same −11.5 (net movement is half this panel) | −10 … +40 | the same lens; the panel names it |

An entrepot's export ratio is not an error and not a units mistake: imports
are re-exported, so goods and services each run near twice GDP. Widening the
shared trade range to accommodate 222% would halve every other country's
panel, which is the one thing the comparison contract exists to prevent; the
orchestrator's choice is either to widen it deliberately for everyone or to
keep Hong Kong's ratio in the lens, and this page does the second until told
otherwise. The two migration panels are a milder case — 1.5 points past a
floor — and would cost little to widen to −15; they stay pending because a
country lane may not edit the shared range.

## 11. What Phase B decided, and why

**Recession bands come from the staged quarterly vintage.** Every quarter
with a negative year-on-year reading in C&SD 310-31001's chained-volume
series: 2008Q4–2009Q3, 2019Q3–Q4, 2020Q1–Q4 and 2022Q1–Q4. No band is
inferred from an annual growth rate, so 2015 (a weak year, never negative)
is not shaded. The bands are named in one line of the first economy panel
rather than four labels on the axis: `2019 unrest`, `COVID-19` and
`fifth wave` are only months apart, and four captions at the top of one
panel overprint each other.

**The 2025-Q4 crime figure is published as recorded, with the wording the
police table supports.** The security panel's note reads: 194 murder and
manslaughter cases in the year, 170 of them reported in the fourth quarter
against 19 across the first three, the annual row reading 194 where the
quarters sum to 189. Nothing is revised, smoothed or dropped. The quarterly
detail itself lives in the fetcher's sidecar, and repository rules forbid a
plate from drawing a sidecar, so the figure is stated on the panel and
asserted in `tests/test_plates.py` from the committed files rather than
plotted. Promoting that sidecar to a curated quarterly CSV is the one change
that would let the spike be drawn as well as stated.

**Excess deaths are drawn from 2015.** The staged column runs from 2006, but
2006 reads −20.6% — outside the shared −20 floor — and, more to the point,
a comparison with a baseline five years in the future is not the statistic
the panel claims to show. The plate draws 2015 onward, the years the
baseline is made of, and the note says so. Canada's plate makes the same
choice for the same reason.

**The markets currency panel draws the effective rate.** The bilateral
HKD/US$ rate is fixed by statute between 7.75 and 7.85 and cannot move, so
drawing it alone would be a flat line at 100 and would tell a reader nothing.
The panel draws C&SD's trade-weighted effective index rebased to 2006 = 100
(which moves, because the US dollar does) with the pegged bilateral rate as
a labelled flat line beside it. This follows the spine's own precedent for
the United States, whose slot carries the broad dollar index.

**The Base Rate and prime are annual means; HIBOR is year-end.** The two are
not interchangeable and are never drawn on one axis as if they were. The
credit lens therefore uses the savings deposit rate against prime — both
annual means from the same table — instead of overnight HIBOR against an
annual-mean Base Rate, which would have compared a year-end fixing with a
year's average.

**One GRA line, at the financial year's midpoint.** `fiscal/govt.csv` labels
a year by the April it starts in, so its cash balance is drawn a quarter of a
year to the right, divided by that calendar year's GDP and labelled
"financial year". The consolidation gap is real and is the point: in FY2024
the cash account shows +0.6% of GDP while the IMF's consolidated general
government shows −5.8%. The line stays solid to its end because FY2025 is a
closed set of accounts, not a year still running.

**Life expectancy is the mortality lens.** The Department of Health's cause
table puts suicides, road deaths and falls in one "external causes" row, so
neither security slot can be filled from it; the lens instead carries the
period life tables published with the vital events, which show the 2022 dip
the fifth wave caused.

**The homicide panel starts in 2021 because the police table does.** The
long UNODC comparison is staged only as a fetcher sidecar, and a plate may
not read a sidecar; the canonical slot is therefore the national series,
five years long, with the re-base stated on the panel.
