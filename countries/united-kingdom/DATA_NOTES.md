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

1. **The IPS era**, which Eurostat carries through 2019. The reviewed
   `flows_estat.csv` publication copy is trimmed to the atlas window,
   2006–2019; the ONS's own IPS-based LTIM series is not staged.
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

The demography plate also shows Eurostat's IPS-era calendar-year net flow
(immigration less emigration) through 2019 beside the ONS YE-December line.
They overlap in 2012–2019 but remain separately labelled segments. The ONS
method marker is placed at **2021.5**, the actual YE June 2021 boundary in
`events.py`, rather than shifted back onto the 2020 observation.

## Migration: the paperwork, and four asylum numbers

- The Home Office's asylum **applications** match Eurostat's first-time
  count to within 2 people in every year 2008–2018. 2019 differs (45,537
  vs 44,315), because the Home Office vintage was revised. Eurostat's
  `applications` column is a different quantity (it includes repeat
  claims).
- **Initial decisions** = grants + refusals, the Home Office headline.
  The sheet's own Decisions column folds in withdrawals and administrative
  outcomes, which the fetcher keeps in a column of their own.
- The asylum lens keeps **initial grants** visible beside applications and
  initial decisions; citizenship grants are a different administrative flow
  and are not substituted for this fourth asylum measure.
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

For a **share within a classification**, however, the denominator must be the
matching Eurostat total: foreign-born divided by the birth-classification
total, and foreign-citizen divided by the citizenship-classification total.
The stock plate uses those two internal denominators and does not substitute
the ONS population series. In the flow panels, the ONS net row is used as
published; it is not reconstructed from the publisher's rounded immigration
and emigration rows.

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

The security plate converts both homicide counts with the ONS mid-year
England-plus-Wales population for the corresponding labelled year. The police
series remains a year-ending-March measure drawn at the financial-year
midpoint; the certificate series remains a calendar-year registration measure.
The common denominator makes their rates legible but does not turn them into
one series.

Causes of death: Series DR 2025 Table 5 supplies 2016–2025, and the
21st Century Mortality file, grouped into the same chapters, supplies
2006–2015. On the 2016–2022 overlap they match to the death in every
chapter, and the fetcher asserts it. Both exclude **neonatal deaths**, so
the `all` row runs about 1,700–2,400 below the all-ages deaths in
`vital_from_ons.csv`. Four coding/production breaks are annotated, not
smoothed. The 2011 ICD-10 update creates the first seam. In 2014 **IRIS
replaced MMDS/NCHS**; MUSE was not the outgoing system. In 2020 **MUSE
replaced IRIS**, and MUSE itself was updated in 2022. Each boundary year
belongs to the incoming regime.

The mortality plate uses Series DR's **published crude death rate** rather than
recomputing it against the population file. Its excess-death bars use the
all-ages `vital.csv` death counts against one fixed 2015–2019 arithmetic mean;
they are not age-standardised. The COVID spine slot stays visibly pending:
chapter 22 is U00–U85, not an exact U07.1/U07.2 extract, so drawing it as
COVID-19 would be a false substitution. The cause lens uses chapters 2 and 9,
which exclude neonatal deaths, and draws five unjoined segments: 2006–2010,
2011–2013, 2014–2019, 2020–2021 and 2022 onward. This makes explicit that the
2015–2025 portion is not one software regime.

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

The fiscal spine's canonical flow measures now come from the IMF Fiscal
Monitor on one calendar-year general-government perimeter: revenue,
expenditure, overall balance and primary balance. IMF GFS supplies exact
general-government interest payable. ONS public-sector debt and the PESA
interest subfunction remain separately labelled national comparators: ONS
covers the whole public sector and nets liquid assets, while IMF debt is
general-government gross. They are not alternate vintages of one series.

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

The BIS household-credit-to-GDP series is also a stock: the plate uses Q4,
not the annual mean, and leaves 2026 blank because only Q1 is available.
The bad-loan slot uses World Bank `FB.AST.NPER.ZS`, sourced from the IMF's
Financial Soundness Indicators, rather than leaving a fetchable series
pending.

The BoE lending series are monthly **stocks**, read at December and never
summed. They come from the IADB under codes pinned against the Tables A–K
workbook, which itself carries only the latest months. The mortgage
quotes are new-business rates (2-year fixed at 60% LTV, from 2012, and
the revert-to-rate). Both product descriptions are asserted from the
IADB on every refresh.

## Trade: two bases, a source break, and probably gold

The ONS BoP goods-and-services totals and HMRC's customs-value goods by
partner are two different numbers. Partner export shares divide by HMRC's
complete customs-world export total, including unallocated special buckets;
they never use the selected partners as a denominator. For US exports in 2024 they are
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

The people plate likewise keeps two poverty concepts separate. DWP HBAI is
relative low income below 60% of that year's median, before and after housing
costs. World Bank `SI.POV.UMIC` is the absolute international threshold below
US$8.30 a day at 2021 PPP and ends in 2021. Their very different levels are a
definition result, not conflicting estimates.

The minimum-wage panel starts from the Low Pay Commission workbook's complete
effective-date history. It day-weights the highest statutory adult hourly rate
within each calendar year, then computes a monthly equivalent at 40 hours per
week × 52 ÷ 12 and converts it with the staged Bank of England annual-average
USD/GBP. UK law defines an hourly floor; the monthly value is only the plate's
common-hours convention. The adult eligibility age changed several times, so
"adult rate" follows the applicable highest-rate band rather than one fixed age.

## Fertility and corruption have explicit source seams

Eurostat `demo_find` ends at 2018. The fertility panel now uses World Bank
`SP.DYN.TFRT.IN` as one labelled modelled series throughout 2006–2024; it does
not append World Bank years to Eurostat history. Eurostat remains the source of
the UK-wide births and deaths in the neighbouring panels.

Transparency International changed the CPI method and scale in 2012. Official
annual archive files for 2006–2011 report scores on 0–10; the CPI 2025 workbook
reports the revised 2012–2025 series on 0–100. These are separate columns and
unjoined line segments. The old segment is positioned ×10 on the shared visual
axis, explicitly labelled as such, while the committed values remain on their
original scale. Only 2012 onward is comparable over time.

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
