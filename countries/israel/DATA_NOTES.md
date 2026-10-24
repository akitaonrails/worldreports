# Israel — data notes (Phase B)

Everything the plates assert about definitions, seams and conversions, in
one place. SOURCES.yaml remains the publisher-level record; this is the
plate-level one.

## Hebrew and right-to-left rendering

Israel is the atlas's first Hebrew country. The shared renderer selects
**DejaVu Sans**, whose cmap covers both Hebrew and the Latin/numeric fragments
used in data labels, and converts localized Hebrew runs
from logical to visual order before Matplotlib lays them out. Generated
Hebrew pages declare `dir="rtl"`; English and Portuguese pages remain LTR.
The layout probe runs for `israel/he` and must reach zero faults like the
other locales. Plate text uses `ILS` rather than depending on the shekel
glyph.

## Bands: COVID-2020 only, verified against the staged vintage

country.yaml carries one band: `{from: 2020.0, to: 2020.9, label:
"COVID-19"}`. Decision record, all pinned in tests/test_plates.py:

- 2020: `macro/gdp_growth_from_imf.csv` (the staged WEO vintage) says
  **-1.9%** — a real annual contraction. The two-quarter q/q test that
  would normally corroborate it rides on CBS quarterly, which is parked;
  every country built from the harmonised layer draws the annual sign,
  this one included.
- 2008-09: **no band.** The discovery pass's "−2.8 in 2009" was Sudan's
  row (the DataMapper `/ISR` segment does not filter — see SOURCES.yaml).
  The staged series says +3.2 (2008) and +1.2 (2009), and the World Bank
  national-accounts vintage independently agrees. A contraction the
  staged vintage does not show is not bandable.
- 2023-25 war years: **no band.** +2.0 / +1.7 / +3.5 — annual growth
  stayed positive. CBS quarterly might yet meet the two-quarter rule for
  the war quarter; until it returns, the war is drawn as events.

## Events, not bands (events.py)

- 7 October 2023 (mark at 2023.75) on the economy, fiscal and security
  panels, where the data visibly turn.
- The war-fiscal reaction — revenue 34.6% of GDP vs expenditure 43.7% in
  2024, balance −8.1%, debt 61.9 → 67.7 → 67.9% of GDP — is annotated on
  the fiscal plate as events and notes. It is never turned into a band,
  because a band would assert a growth contraction the series denies.
- The October-7 files inside the Israel Police type-301 series (2023: 1,209
  recorded cases) are annotated on the security plate as recorded data.
  Police commentary sometimes excludes the national-terror files from its
  annual homicide reporting; **the open-data file does not** — that
  definitional seam is stated on the panel.

## Count→rate conversions (spine rule 5) and the population used

All rates use the World Bank `SP.POP.TOTL` mid-year series staged as
`demography/demography_from_wb.csv` — same year, national scope, matching
the UNODC/WHO rate series' own denominator when a published rate exists
(where a publisher publishes a rate, the published rate is drawn, not a
recomputed one):

- Israel Police type-301 cases per 100,000:
  `security/homicide_police.csv` type_301 count ÷ that year's
  population × 100,000. Spot: 2023 =
  1,209 / 9,849,000 = **12.28** per 100,000 (test recomputes).
- olim per 1,000: olim_flow ÷ population × 1,000. Spot: 2022 = 76,601 /
  9,557,500 = **8.01** per 1,000.
- net migration per 1,000: WB `SM.POP.NETM` ÷ population. Spot: 2022 =
  50,004 / 9,557,500 = **5.23**.
- permits per 1,000: PIBA new-permit counts ÷ population (flow wording
  throughout — a permit is a record, not a person, and never a stock).

## Seams that are drawn as seams, never spliced

- **Homicide, security slot 1:** the UNODC rate (via WB, 2005-2022) and
  the Israel Police type-301 count converted per 100,000 (2021-2025) are
  **two labelled series on two colours**. The police window is 2021+
  only — it is stated on the panel and pinned in tests; nothing is
  extrapolated backwards into the 2006-2020 half, and the UNODC rate is
  never extended past 2022 to dress up the line. CBS death-certificate
  homicide (the residence-based second count) is parked with CBS.
  Type 302 (killing by hostile action) is its own column and its own
  note, never added to 301.
- **Aliyah vs permits vs net migration (migration plate):** olim are a
  Law-of-Return legal flow (Ministry of Aliyah and Integration, 2015+);
  PIBA issuance is permit records (2019+); UN net migration is an
  estimate. Three objects, three panels/series, one rule: never summed
  into one "immigration" line. The PIBA lens excludes the tourist/visitor
  classes (ב/2 family dominate the raw totals), excludes the diplomatic
  and unverified-definition classes, and excludes the PIBA classes named
  עולה/חוזר because they would double-count the olim line; which classes
  are in is stated on the panel and computed from the CSV in tests.
- **Trade destinations:** the staged UN Comtrade file is a reviewed 2023
  customs-goods snapshot, not an annual time series. It remains in the trade
  lens; the canonical destinations slot stays visibly pending.
- **FX:** the WB `PA.NUS.FCRF` annual averages (2005-2025) carry the
  index line. The Bank of Israel PublicApi row is a **snapshot of the
  representative rate on one intraday timestamp** (2026-10-22), quoted as
  a labelled snapshot note — never appended to the history line. BoI
  daily history is dead (404); that is why the line is WB's.
- **Equities:** TA-125 via Yahoo (`official: false`). Yahoo's levels
  differ from TASE's published year-end closes by a few percent (SOURCES
  records the pairs); the panel says the source is a redistributor. The
  US$ conversion uses the staged WB FX — pinned spot: 2006 base =
  925.60/4.4558, 2025 = 3,654.94/3.4519 → index ≈ 510 against the S&P
  500's ≈ 483. 2026 is not converted (no staged 2026 FX) and the partial
  year stays hatched/dashed.

## Harmonised lines with the national line named (CBS pattern)

CBS is the publisher of record and unreachable from this machine
(SOURCES.yaml meta.pending), so CBS-only national layers remain visibly
pending. Verified harmonised layers are used where their definitions fit:
WB/IMF macro and trade, OECD LFS and IDD, and OECD/WHO national-vital-
registration mortality. They are labelled as harmonised data, not as direct
CBS downloads. The OECD `DSD_LFS@DF_IALFS_INDIC` unemployment line is
Israel's own LFS re-published by the OECD, so it is labelled as the LFS
definition (survey, not the NII payroll register); the ILO-modelled WB line
is the beside-line. Direct Bank of Israel workbooks provide the national
policy-rate, government-yield, household-debt, mortgage-rate and banking NPL
series independently of the blocked CBS route.

## Filled gaps and the remaining pending lens

The former policy-rate and 10-year-yield gaps are filled from stable BoI
workbooks. Spending now has OECD COFOG and general-government investment plus
a separately labelled WB whole-economy investment series. People now has OECD
IDD Gini/relative-poverty segments and the official Bituach Leumi statutory
minimum wage. Credit now has BoI household debt, new-mortgage rates and the
banking-system NPL ratio. Mortality now has OECD/WHO harmonised Israeli
national-vital-registration counts and crude rates.

The only remaining credit lens gap is a household debt-service ratio. BIS
WS_DSR has no Israel coverage and no compatible BoI household-sector DSR time
series was verified. Mortgage-origination payment-to-income distributions are
not substituted because they are not a stock DSR. CBS-direct national survey,
national-accounts and mortality tables remain blocked as distinct national
layers; their absence does not invalidate the explicitly labelled harmonised
series. Other residual routes remain itemised in SOURCES.yaml `meta.pending`.

## Spending and people normalization

- OECD COFOG is consolidated general-government expenditure, percent of GDP,
  2006-2024. The seven spine groups are explicit sums of GF01-GF10 and are
  checked against OECD total within 0.02 percentage point. OECD public
  investment is S13 gross fixed capital formation; WB whole-economy GFCF is a
  different perimeter and is never used as its replacement.
- OECD IDD preserves three definition segments in separate columns:
  METH2011/D_CUR (2008-2011), METH2012/D_INC (2011-2022), and the
  METH2012/D_CUR 2023 point. The plate must not connect them into one line.
  Poverty means below 50% of median equivalised disposable household income,
  not an absolute poverty line.
- The statutory minimum wage is the calendar-year mean of the twelve monthly
  legal ILS levels. Its USD view divides by committed annual-average ILS/USD;
  it is a nominal conversion, not purchasing power. The incomplete 2026 year
  is omitted.

## Bank of Israel market and credit normalization

- Policy rate: 2006-2016 is the mean of 12 monthly liquidity-period averages;
  2017-2025 is the calendar-day-weighted declared nominal rate using effective
  dates. `annual_aggregation` exposes this seam.
- The 10-year yield is the mean of 12 monthly yields on the longest unindexed
  government bond with 8-11 years remaining. It is not a constant-maturity or
  model zero-coupon curve.
- Household debt is BoI `CRA_OUT_0204`, total debt to all lenders, Q4 stock in
  NIS billion. Percent of GDP is derived from WDI annual current-NIS GDP:
  `Q4 debt / (GDP / 1e9) * 100`; the mixed-source ratio is labelled as such.
- The mortgage rate covers new unindexed-shekel housing loans, fixed and
  variable, and begins with complete years in 2014. The pre-2013 fixed-only
  sheet is not spliced. The NPL ratio is the deposit-taker banking-system
  `FSANL` Q4 ratio, not household delinquency, with the November 2022 IMF FSI
  2006-to-2019 Guide seam retained.

## Mortality normalization

OECD Causes of Mortality redistributes national vital-registration underlying-
cause records via the WHO Mortality Database. It is not a model estimate or a
COVID surveillance series. The accepted rows are annual, both sexes, all
ages, 2005-2023. Counts use `DT`; crude `DT_10P5HB` rates are per 100,000, so
the all-cause rate is divided by 100 for the per-1,000 plate. Cancer and
circulatory lines remain crude per 100,000; age-standardised rows are excluded.
Excess mortality is `(deaths / 44,673.8 - 1) * 100`, where 44,673.8 is the
fixed 2015-2019 mean. It begins in 2015 and is unadjusted. Later years stay
blank until the same source vintage advances.

## Other honesty notes carried on the plates

- olim 2006-2014: not on the portal (XLS behind a CloudFront wall); the
  flow panel opens in 2015 and says so — no back-fill.
- WB suicide series stops 2021 and road deaths 2019 in WB's own coverage
  — the lines stop; the holes stay holes.
- Fertility/crude birth/death for 2025 are blank in the WB vintage — the
  lines stop at 2024.
- population index 2025 ≈ 143 vs the 80-130 reference: the axis **grows**
  and carries the "scale extended" marker (spine rule 6), never the data.
- WB reserves 2024 (214.5bn) run 1.2% above the BoI's own release (adds
  IMF-related items) — footered, not reconciled by hand.
- HDI is one vintage (HDR 2025, series to 2023) throughout.
