# United Kingdom — data notes

What these sources were like to work with, and the judgement calls a reader
of the plates should not have to reverse-engineer. `SOURCES.yaml` carries
the per-file caveats; this file carries the ones that cross files.
Research pass and consolidation: 2026-10-22. `DISCOVERY.md` is the
research pass's own report, kept as a record; where it and this file
disagree, this file and `SOURCES.yaml` are right.

---

## The harmonised layer is half gone, and it fails quietly

Since Brexit the Eurostat API has dropped the UK from `nama_10_gdp`,
`gov_10dd_edpt1`, `une_rt_a` and `ilc_di12`. The slice comes back
**well-formed and empty under HTTP 200**, not as a 404. The migration
suite and HICP are frozen at 2019 (`migr_resfirst` at 2018), and only
`demo_gind` and the Maastricht yield still run to the present. So the
national series are the ONS, the Bank, the Home Office, HMRC, DWP and the
Treasury, and the harmonised comparisons come from the IMF (fiscal) and
the World Bank (everything else). `fetch_eurostat.py` fails loudly on an
empty cube, and it asserts the last populated year, so a revived series
fails the run too.

UK-specific endpoint trap: `unit=PER`, which Spain needed, **empties** the
UK migration cubes (the unit dimension collapses to size 0). For the UK
the unit filter is dropped. `migr_resfirst` has no sex dimension, so
`sex=T` returns a 400. The EU27_2020 citizenship aggregates are empty for
a former member, so the splits are EU28/non-EU28, which start in 2013
(flows) or 2014 (stocks).

## Migration: three regimes, and the ONS series is not one of them

The research pass described three regimes: IPS to 2019, admin-based from
YE June 2021, then the late-2025 revisions. The current ONS edition
(YE December 2025, published 21 May 2026) shows a different shape, and
the plate has to follow it:

1. **The IPS era**, which Eurostat carries for 1998–2019 (`flows_from_estat.csv`,
   with a real hole at 2005). The ONS's own IPS-based LTIM series is not
   staged.
2. **The ONS "new approach" back-series, YE June 2012 to YE March 2021.**
   It is admin-based for foreign nationals (EU+ from DWP/HMRC RAPID,
   non-EU+ from Home Office borders data), but British nationals still
   come from the IPS, adjusted to the 2021 census in November 2023.
3. **YE June 2021 onward**, which is fully administrative: British
   nationals from RAPID, EU+ from Home Office visa and settled-status data.
   EU+ also gains the EEA states and Switzerland at this point.

On top of the three, the November 2025 British-nationals method change
has been carried back across the whole current edition, so this
spreadsheet is one vintage. The ONS's own notes 16–17 say British
estimates before and after June 2021 are not comparable, and that every
comparison across that date needs caution. The plate draws the ONS line
with the June 2021 seam marked on it.

**The two series overlap for 2012–2019 and disagree badly.** YE December
against calendar year: immigration is 16–37% higher on the ONS
(2019: 788,000 vs 680,906; 2015: 797,000 vs 631,452), and emigration
39–65% higher (2019: 605,000 vs 368,385). Net migration therefore swings
both ways: 2019 is 184k on the ONS and 313k on Eurostat, while 2018 is
276k against 260k. British immigration is the one thing the two sources
agree on (they share the IPS): 2019 is 71,000 against 77,514. **Never
join the two lines.** Draw both, label both, and let the 2012–2019
overlap show the size of the method change.

The ONS reference periods are **rolling years ending** (YE) in March,
June, September and December, rounded to the nearest thousand by the
ONS. Only the YE December rows are calendar years, and the `status` flags
(P, R, "P,R") come from the publisher.

## Migration: the paperwork, and four asylum numbers

- The Home Office's asylum **applications** match Eurostat's first-time
  count to within 2 people in every year 2008–2018. 2019 differs (45,537
  vs 44,315), because the Home Office vintage was revised. Eurostat's
  `applications` column is a different quantity (it includes repeat
  claims).
- **Initial decisions** = grants + refusals, the Home Office headline.
  The sheet's own Decisions column folds in withdrawals and administrative
  outcomes, which the fetcher keeps in a column of their own.
- The **backlog** is a 31 December stock, from 2010 onward.
- **The asylum series is revised.** The YE December 2024 edition headlined
  108,138 claimants for 2024. This vintage says 104,764, after the Atlas
  caseworking migration and data-quality work. The fetchers assert the
  current edition only.
- **Citizenship:** the Home Office grants run 3–600 above Eurostat's
  `migr_acq` in every year 2006–2019 (a revision gap). From 2020 the Home
  Office series continues as a separate segment, never spliced.
- **Settlement** includes settlement on arrival until May 2019. That
  component has its own column, so the break shows. Pre-2020 years come
  from the summary tables, because the detailed datasets start in 2020.
- **Visas** are permissions, and transit visas are split out to match the
  headline "Other". **Irregular arrivals** are detections (events), 2018
  onward.

**Eurostat's `migr_pop1ctz` total is not a population.** It equals
`demo_gind`'s 1 January figure only in 2009–2012. It is 227k below in
2006, 190k above in 2019, and 2003 is lower than 2001. Use its
national/foreign split, which is what the stock panel needs. The totals
are wrong for the population itself.

## Scopes: the UK, Great Britain, and England & Wales

There is no UK-wide police homicide count and no UK-wide cause-of-death
table. Scotland and Northern Ireland publish their own (`meta.pending`).
So the scopes are mixed, and every plate must name the one it uses:

| Scope | Files |
|---|---|
| UK | GDP, prices, labour, earnings, fiscal (PSF, PESA), trade, markets, credit, population (ONS mid-year and Eurostat 1 January), life tables, Gini, HBAI poverty (from 2002/03; earlier years are GB only and not staged), all migration |
| England & Wales | births and deaths (`vital_from_ons`), causes of death, both homicide series |

The UK-wide births and deaths reference tables exist, but their current
edition is 2021. Eurostat's `demo_gind` carries UK births and deaths to
2025 (2025: 649,525 births and 650,469 deaths against E&W's 585,396 and
570,988). It is the harmonised UK twin, drawn beside the E&W series and
never mixed into it.

## Two homicide counts, and a coding break inside one of them

The Homicide Index (police, place of occurrence, **year ending March**,
offences) and the death certificate (ONS 21st Century Mortality,
**calendar year of registration**, deaths) disagree in both directions
(2019: 676 police vs 701 death-certificate on the ONS definition). That
is the usual two-publishers pair.

The second trap is a coding break. **Before 2007 the ONS coded deaths
pending inquest to Y33.9** (undetermined intent, about 435 in 2006). From
2007 it used U50.9. So `homicide_ons_definition` reads 342 in 2006 and
790 in 2007, and that jump is the code change. Start that line at 2007,
or annotate 2006. The pure-assault column (X85–Y09) has no such break,
but it collapses to 147 in 2020 because COVID delayed inquests and the
deaths sat in U50.9 instead. **The certificate series ends at 2022**
(2023–25 pending, see HANDOFF).

Causes of death: Series DR 2025 Table 5 supplies 2016–2025, and the
21st Century Mortality file, grouped into the same chapters, supplies
2006–2015. On the 2016–2022 overlap they match to the death in every
chapter, and the fetcher asserts it. Both exclude **neonatal deaths**, so
the `all` row runs about 1,700–2,400 below the all-ages deaths in
`vital_from_ons.csv`. Two coding breaks are annotated, not smoothed: the
2011 ICD-10 update and the 2014 MUSE-to-IRIS software change.

## Fiscal years, calendar years, and a key that says which

The budget, PESA, HBAI, the ONS Gini and the Homicide Index all run on
**April–March financial years**. Every such file is keyed `fiscal_year`
on the **starting** year (2024 = 2024-25 = FYE 2025), the USA/Canada
convention. The two PSF files carry both on one `year` row: `*_calendar`
for the calendar year and `*_fiscal` for the financial year starting in
April of `year`, summed from the monthly rows and blank until all twelve
months are out. PSND carries December and end-March stocks. A plate must
never draw a fiscal-year series on the same axis as a calendar one
without saying so.

Cross-checks: PSF total managed expenditure and PESA's TME agree to
within 0.1% for every financial year to 2024-25. 2025-26 differs by 0.4%,
because PESA is the July vintage and PSF the October one. The IMF's
general-government series is calendar-year and gross. Its debt runs 5–8
points above PSND ex (2024: 99.4% vs 94.1%), and its net lending is
within about 1 point of PSNB/GDP. These are different aggregates, never
spliced.

The research pass got three fiscal series wrong. **JW2V is the current
budget deficit, not receipts**: receipts are JW2O and TME is KX5Q, with
J5II = JW2O − KX5Q asserted every month. **HF6W is in £ billion.** And FY
2020-21 borrowing is now **−£310.8bn** (the ~£322bn quoted at the time
has been revised away).

## Household debt is S.14 only, and it is wider than bank lending

CVZH and CVZI share one title. The research pass guessed that one was
S.14 and the other S.14+S.15. In fact both are **S.14, the same ratio at
two frequencies** (annual rows only, and quarterly rows only, with every
annual value equal to Q4). The fetcher rebuilds the ratio from NIWK/HABN
within 0.1 point and asserts that the S.14+S.15 pair (NNRE/QWND) runs
about 3 points lower. Its numerator is **all loans to households,
including student loans and non-bank lenders**: £2,194.9bn at Q4 2025,
against the Bank of England's £1,941.4bn of MFI lending to individuals.
These are two scopes, so the plate labels which one it draws and does
not treat the gap as a disagreement.

The BoE lending series are monthly **stocks**, read at December and never
summed. They come from the IADB under codes pinned against the Tables A–K
workbook, which itself carries only the latest months. The mortgage
quotes are new-business rates (2-year fixed at 60% LTV, from 2012, and
the revert-to-rate). Both product descriptions are asserted from the
IADB on every refresh.

## Trade: two bases, a source break, and probably gold

The ONS BoP goods-and-services totals and HMRC's customs-value goods by
partner are two different numbers. For US exports in 2024 they are
£59.3bn and £57.5bn. HMRC's EU trade comes from the Intrastat survey up
to 2020 and from customs declarations from 2021 (Great Britain only), so
the partner panel has a **source break at Brexit**. Imports from
Switzerland jump from £17.0bn (2024) to £43.2bn (2025), and to £46.9bn in
the first eight months of 2026. That pattern is almost certainly
non-monetary gold, which the ONS headline excludes. **It has not been
verified by commodity.** Do it before the partner chart goes out (see
HANDOFF).

## Inequality: the Gini runs on two definitions

The ONS Gini (equivalised disposable income, FYE, top-income adjusted)
runs 1–3 points above the World Bank's (2019: 35.4 vs 32.8). They come
from the same survey family, read through different definitions, and they
are not two measurements of one number. The WB series has no 2022+, and
those holes stay holes. HBAI has a seam at 2021/22, where the survey was
integrated with administrative records. 2020/21 was collected under COVID
restrictions on a reduced sample.

## Labour: the LFS broke

LFS response rates collapsed through 2023–24. The ONS suspended and
reweighted the outputs and is moving to the Transformed LFS, so the
unemployment, employment and AWE-adjacent figures from 2023 onward are
annotated rather than smoothed. Eurostat has no UK `une_rt_a`, so there
is no harmonised twin.

## Revisions seen during this one day

Every first guess the pass checked came back revised. The asylum
claimants for 2024 (108,138 → 104,764), FY 2020-21 PSNB (~£322bn →
£310.8bn), the LTIM history (the whole British-nationals series, November
2025) and, for completeness, 2019 asylum on Eurostat against the Home
Office. Every spot value in HANDOFF is **this vintage**, and a rerun that
moves one should be diffed and explained, never "corrected" back.

## Cross-source checks run in consolidation

| Check | Result |
|---|---|
| ONS YBHA × BoE USD/GBP vs WB GDP US$ | within 0.5% every year (2024: 3,713 vs 3,695.5bn) |
| ONS mid-year population vs WB | within 0.05% every year |
| ONS mid-year vs Eurostat 1 Jan | consistent (mid-2019 66.63mn between 1 Jan 2019 66.46mn and 1 Jan 2020 66.68mn) |
| PSF TME (FY) vs PESA TME | ≤0.1% to 2024-25; 0.4% in 2025-26 |
| PSNB/GDP (cal) vs IMF net lending | within ~1pt (2020: −12.7 vs −12.9) |
| PSND ex vs IMF gross debt | IMF 5–8pt higher (definitions) |
| ONS (X+M)/GDP vs WB openness | within 1.3pt |
| HO asylum applications vs Eurostat first-time | ≤2 people 2008–18; +2.8% in 2019 |
| HO citizenship vs Eurostat migr_acq | +3 to +599 a year (≤0.3%) |
| ONS LTIM vs Eurostat flows, 2012–19 | imm +16–37%, emi +39–65% (method) |
| Eurostat migr_pop1ctz total vs demo_gind | −227k (2006) to +190k (2019) |
| Police vs certificate homicide | both directions; 2006/07 Y33.9→U50.9 break |
| ONS S.14 loans vs BoE MFI lending | ONS £253bn higher (scope: student loans, non-banks) |
| HMRC customs vs ONS BoP, US exports 2024 | £57.5bn vs £59.3bn (basis) |
| ONS Gini vs WB Gini | ONS 1–3pt higher (definition) |
| BoE 10y gilt | **no second source in the lane** (Eurostat yield pending) |
