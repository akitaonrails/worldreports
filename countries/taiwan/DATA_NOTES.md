# Taiwan — data notes (Phase B)

What each plate draws, what it divides by, what is deliberately not drawn.
SOURCES.yaml is the fetch contract; this is the reading guide.

## The framing fact, restated for the plates

The World Bank, the IMF and the UN do not carry Taiwan, so the spine's
usual harmonised second series does not exist for this country. Every
canonical slot that would normally lean on them is drawn from what
Taiwan publishes about itself — DGBAS (行政院主計總處), the Central Bank
(CBC), the Ministry of Finance (MOF) — and the label says so. Where a
substitute is a *different definition* rather than a *different publisher*
(CBC vs DGBAS inflation, customs vs balance-of-payments trade), the two
series ride as two clearly labelled lines and are never spliced.

## Chapter set

Twelve chapters: economy, fiscal, spending, trade, markets, credit, people,
world, demography, security, mortality and migration. The earlier claim that
people and migration sat behind query walls was stale: the DGBAS open-data
CSV/PDF, MOL effective-date page, RIS JSON API and NIA direct ODS are now
fetched into review sidecars and promoted only after their pinned checks pass.

## Bands (verified against the staged vintage)

Recession bands come ONLY from the staged DGBAS GDP vintage
(`data/economy/gdp_growth_quarterly.csv`, A018101010 quarterly rows,
pulled 2026-10-23). Year-over-year quarterly growth goes negative at
2008Q3 (−1.39), troughs at 2009Q1 (−7.87), and returns to positive at
2009Q4; the full year 2009 is −1.61. `country.yaml` bands that as
2008.75→2009.5, labelled "export collapse" (exports really did fall
around 40% y/y in late 2008).

**COVID-19 gets no band and no mark on the GDP plate.** 2020 grew +3.42%
and no quarter in the window is negative anywhere near 2020. The absence
of a COVID band on Taiwan's growth plate is itself the finding, and the
plate says so in a note. `tests/test_plates.py` pins both facts against
the CSVs: the band years, the trough quarter, and "no negative quarter
in 2019–2021".

## Conversions (core/rates.py) and the population used

- **Population series for every rate:** `demography/population.csv` —
  DGBAS A018101010 annual population (mid-year register count, whole
  governed territory, 2025: 23,353,203… exact latest value read from the
  CSV). It is the same scope and year as the death counts below, which
  are national death registrations.
- **Crude death rate (mortality slot 1, demography slot 3 line):**
  `mortality/causes_of_death.csv` `deaths_all_cause` ÷ population × 1,000.
  Cause deaths are registered deaths by underlying cause (DGBAS
  A170101020, monthly, aggregated to years); the series starts 2008, so
  the crude-death panel runs 2008–2025, not 2006 — the spine's axis does
  not clip it.
- **Suicide (security slot 2) and accidents (security slot 4 lens):**
  per 100,000 via `rates.per_100k`, same population. These are
  death-certificate counts — the police (NPA) place-of-occurrence series
  is a second column when it lands, not a splice.
- **Excess deaths (mortality slot 2):** % above the 2015–2019 mean of
  `deaths_all_cause`, computed from slot 1's counts, exactly as the
  spine prescribes.
- **Currency (markets slot 3):** `markets/usdtwd.csv` interbank annual
  mean, via `rates.fx_index` (inverted, 2006 = 100, up = stronger).
- **Equities (markets slot 4):** TWSE capital-weighted index annual
  AVERAGE from CBC EG27Y01, converted to US$ with the staged same-year
  average FX (`usdtwd.csv`), then indexed 2006 = 100. The Yahoo
  year-END close (`stock_index_yearend.csv`, official: false) rides as a
  labelled second line — average and year-end are different quantities,
  never joined.
- **Household debt (credit slot 1):** `credit/household_credit.csv`
  consumer loans ÷ GDP in the same NTD units (CBC EF99Y01 outstanding,
  national definition; BIS does not carry Taiwan — the label names it).
  Building loans are developers' credit, not household debt: they go to
  the lens panel, never summed into slot 1.
- **Fiscal ratios:** `fiscal/budget.csv` carries the publisher's own
  %GDP columns; MOF i2101 is all-levels (general-government) final
  accounts on a calendar year, so it is the canonical line, not the
  federal-perimeter exception. Debt-service ratio: i0121 debt category
  (thousand NTD) ÷ GDP (million NTD) × 100, the unit factor pinned in
  the test. Primary balance = overall balance + that ratio, labelled
  honestly as balance + debt-category outlays (the MOF category is
  債務; treat it as interest-plus-charges, the closest published proxy).
- **Minimum wage:** MOL effective-date monthly NTD levels are day-weighted
  within each calendar year and divided by that year's DGBAS annual-average
  NTD/US$ rate from `economy/gdp.csv`. Mid-year changes are therefore neither
  backdated nor treated as a year-end annual value; 2026 is not drawn without
  a complete annual FX observation.
- **Registered migration:** RIS ODRP011 is summed over every village, sex,
  month and API page. `foreign in + initial registration` is the registered
  incoming flow; `foreign out` is the outgoing flow. Rates divide by the
  DGBAS mid-year administrative-register population of the same governed
  territory. These are household-registration events, not all ARC migration.
- **ARC stock:** NIA counts foreigners with a valid ARC actually present at
  month-end. It is shown only in the migration lens, because it is neither a
  foreign-born stock nor all foreign citizens. Foreign labour is a subset.

## Seams and never-splice pairs

- **Inflation (economy slot 3):** DGBAS annual-average CPI y/y
  (`cpi.csv`) vs CBC period-based CPI y/y (`cpi_yoy_cbc.csv`, EF07M01).
  Two published rates, different bases — two labelled lines. The test
  pins their largest divergence year.
- **Accrual vs cash (fiscal):** i2101/i0121 accrual final accounts vs
  treasury cash (`accrual_vs_cash.csv`) — two bases, one idea; the cash
  columns are a labelled second reading, never spliced (the fetcher
  already asserts they differ).
- **Trade concepts (trade lens, slot 4):** MOF customs-compiled goods
  (`trade/goods.csv`, from the same customs records the geo-blocked
  Customs DB would give) vs CBC balance-of-payments goods
  (`world/bop_goods.csv`). Different definitions (FOB customs vs BoP),
  both kept, never spliced; the test asserts the levels differ.
- **TAIEX average vs year-end:** see equities above.
- **Trade coverage:** the spine's first two trade slots require
  national-accounts goods *and services*. Only customs and BoP goods are
  staged, so those canonical slots are visibly pending; the verified goods
  partner history remains in slot 3 and the two goods definitions in the lens.

## Pending (drawn as `ctx.pending` or as an absent chapter, with reason)

- **economy slot 4, unemployment:** filled from DGBAS A040107010, total
  unemployment rate, annual average (2006–2025).
- **markets slot 2, 10-year yield:** not in the staged CBC pulls; the
  CPMI strip was not verified end-to-end — pending, not invented.
- **spending slots 3–4, investment rates (GFCF):** not in the staged
  DGBAS key table; pending.
- **world slot 2 (HDI):** the UN does not carry Taiwan and no national
  publisher computes the HDI; this remains a true absence. Slot 3 is filled
  from Transparency International's CPI Historical sheet (2012 method).
- **demography slots 2 and 4 (fertility, natural increase/migration):** the
  audited ODRP003 route returned the RIS `查無資料` response for both historic
  and current months on 2026-10-23. ODRP011 fills registered international
  migration, but does not publish births or fertility; those remain pending
  rather than being inferred from a different table.
- **security slots 1 and 3 (homicide, road deaths):** police series are
  NPA-walled; the DGBAS death-certificate assault count was not in the
  staged cause set — pending with reason.
- **mortality slot 3 (COVID underlying cause):** the staged cause set
  does not carry the COVID code; pending, and it will be a second column
  against the excess series, never merged.
- **credit slot 2 (lending rate):** filled from CBC EH45M01 as the annual
  mean of monthly five-bank new-housing new-business rates, beside the CBC
  December rediscount rate. These are distinct rate concepts, not spliced.

## Population note (spine rule 5)

Every per-1,000 and per-100,000 conversion divides by
`demography/population.csv` — the DGBAS annual (mid-year) population of
the governed territory, the same scope as the national death
registrations it converts. No publisher's own rate exists for the cause
counts (DGBAS publishes counts), so `core/rates.py` does the division;
the tests pin one spot year by hand.
