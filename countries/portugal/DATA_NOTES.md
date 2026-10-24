# Portugal — data notes

What these sources were like to work with, and the judgement calls a reader
of the plates should not have to reverse-engineer. `SOURCES.yaml` carries
the per-file caveats; this file carries the ones that cross files.
Research pass and consolidation: 2026-10-22. `DISCOVERY.md` is the
research pass's own report, kept as a record; where it and this file
disagree, this file and `SOURCES.yaml` are right.

---

## The June-2026 population revision is the whole country's trap

On 2026-06-22 the INE revised resident population for 2021–2024 on an
administrative-data method that counts foreign residents the old
register-based estimate missed. End-2024 went from 10,749,635 to
**11,387,222**, and the 2021+ migration flows were revised with it. The
publishers in this lane sit on different sides of that line, sometimes
inside one publisher:

| Series | Vintage |
|---|---|
| INE population 0004167, immigration 0006055, emigration 0006050, net migration 0013179 and 0008269, TFR 0001293 | revised |
| Eurostat `demo_gind` (population, births, deaths) | revised (break flag on 1-Jan-2022) |
| Eurostat `demo_find` (TFR) | **not** revised: equal to INE to 2020, then 1.35/1.43/1.45/1.41 against INE's 1.30/1.34/1.32/1.27 for 2021–24 |
| Eurostat `migr_*` (flows, stocks) | pre-revision; immigration stops at 2023, emigration at 2024 |
| World Bank population (and so GDP per person) | pre-revision |

Three consequences for the build:

1. **Never mix vintages on one plate without saying so.** The
   pre-revision `migr_pop1ctz` stock (1-Jan-2025: 10,749,635) and the
   revised population for the same date (11,387,222) are 637,587 apart.
2. **The 2021 step in the INE flows is methodology, not a wave.** INE
   and Eurostat agree to the person on immigration and emigration in every
   year 2008–2020. From 2021 INE's revised immigration is 222,775 (2021)
   and 495,979 (2022), against Eurostat's 97,119 and 167,098. Draw the INE
   line with the 2020→2021 seam marked, and the Eurostat line beside it,
   never joined.
3. **Any per-person rate needs a named denominator.** The UNIT RULE
   applies: deaths and homicides per 100k use the same-year, same-scope
   population, and the plate names it. For Portugal that means the INE
   revised series, and the rate moves (down) in 2021–2024 for the
   denominator alone.

INE's revised emigration also corrects a known undercount: departures were
28,219 in 2019 on the register basis and are 120,806–188,871 a year on the
new one. The pre-2021 emigration line is therefore low by construction,
and the note on the plate should say so.

## Net migration is not immigration minus emigration (from 2021)

INE's *saldo migratório* includes a statistical adjustment. Through 2020 it
equals immigration − emigration to the person. From 2021 it does not:

| Year | Saldo (0013179) | Imm − Emi | Adjustment |
|---|---|---|---|
| 2021 | 250,079 | 101,969 | **+148,110** |
| 2022 | 371,277 | 367,443 | +3,834 |
| 2023 | 307,288 | 297,664 | +9,624 |
| 2024 | 216,629 | 206,033 | +10,596 |
| 2025 | 70,862 | 74,305 | −3,443 |

The 2021 balance is mostly the census-to-administrative reconciliation.
Publish the two flows (SOURCING §4a) and, if the balance is drawn at all,
label it as INE's balance including the adjustment.
`0008269` (NUTS-2013) already carries the revised 2021–2023 values,
identical to `0013179`.

## Two stocks that look like one, and a stock that is really permits

- **Eurostat's foreign-citizen stock on 1 January (pre-revision) tracks
  the SEF/AIMA legal-resident count at the previous 31 December**, and in
  the last two years matches it almost exactly: 1-Jan-2024 1,045,387
  against INE's legal-resident 1,044,238 at end-2023 (+0.1%), 1-Jan-2023
  785,031 against 781,247 (+0.5%). In 2018–2022 it ran 4–12% *below* the
  permit count, and in 2014–2017 within ±2.5%. These are two definitions
  that converged, not one series.
- The legal-resident stock (`foreign_residents_from_ine.csv`) is **stale
  at 2023**, because the SEF→AIMA transition broke the series. AIMA's RIFA
  2024/2025 are PDFs on a site that never answered (`meta.pending`).
- `citizen=FOR` is an empty cube for PT. The foreign stock is
  EU27_2020_FOR + NEU27_2020_FOR, drawn as two components.
- Eurostat flags a break in `migr_pop1ctz` at 1-Jan-2009. The 2006–2008
  totals sit on the pre-2011-census basis.

## The paperwork: four numbers, two breaks

- **First residence permits 2025 = 310,639** (2024: 121,872). This is
  AIMA clearing the *manifestação de interesse* backlog: administrative
  events, not arrivals. Eurostat flags 2025 as a break.
- **Asylum decisions carry a break flag in 2024**, and positive decisions
  that year are **10 of 1,005** as published (2023: 310 of 435; 2025: 460
  of 1,375). The reason is not yet read (`meta.pending`). Annotate it and
  do not read it as policy.
- Asylum numbers are small (2024: 2,690 applications). Applications,
  first-time applications, decisions and positive decisions are four
  series.
- Naturalisations (`migr_acq`) run 17–32k a year. 2007 is a hole in the
  source, and 2006 (4,447) predates the 2006 nationality law.

## GDP growth: one number for 2024, on two vintages

`gdp_from_ine.csv` carries INE indicator **0014144**, which gives 2024 real
growth as **2.1**. `gdp_from_estat.csv` gives **2.70**. The investigation:

- 0014144 is an **annual** volume rate (prices of the previous year, base
  2021). It is not a Q4 year-on-year (Q4-2024 y/y is 3.0) and not a
  different base.
- Its metadata name ends "INE, **Contas económicas regionais**". It is the
  regional accounts (NUTS-2024), last updated **2026-01-06**, with 2024
  flagged *Dado provisório*, and it has no 2025.
- The national accounts were revised after that. INE's own quarterly
  chain-linked y/y (0013431, updated 2026-09-23) reads 2.4 / 2.6 / 2.7 /
  3.0 through 2024 and 1.8 / 1.8 / 2.1 / 1.9 through 2025. That is 2.7 and
  1.9 on average, matching Eurostat (dataset updated 2026-10-21, 2024 no
  longer provisional).
- The World Bank confirms it from the other side. WB current-US$ GDP
  equals Eurostat × the ECB mean rate to 0.01% for 2006–2023, but is 0.5%
  low in 2024 and 0.6% low in 2025. The Bank still holds the
  pre-revision nominal level for those two years.
- 2006–2023 the two growth series agree to the decimal.

So the 2.1 is a **stale vintage**, and the 2.7 is current. The column is
annual growth, the comment and the manifest now say it is the
regional-accounts vintage, and the fetcher asserts both the provenance
and the 2.1, so a catch-up release fails the run instead of quietly
changing. **The economy plate draws growth from Eurostat**, and the INE
nominal level (which is current and equals Eurostat to the million).
0013431 is deliberately not carried, because a quarterly y/y does not
aggregate to a year.

## Year conventions: INE's survey data is one year behind Eurostat's label

INE labels ICOR (EU-SILC) results by the **income reference year**.
Eurostat labels the same numbers by **survey year**. They are equal to the
decimal after a one-year shift:

- Gini: INE 2013…2024 = Eurostat `ilc_di12` 2014…2025 (INE 2024 30.9 =
  Eurostat 2025 30.9).
- At-risk-of-poverty: INE 2017…2024 = Eurostat `ilc_li02` 2018…2025.

Compared unshifted, they appear to disagree by up to 1.8 points, which is
an artefact of the labels. So `poverty_from_ine.csv` adds no information
that Eurostat lacks (and 0009821 starts only in 2017), and
`gini_from_ine.csv` adds 2003–2013. Pick one x-axis convention per plate
and say which. The World Bank Gini is a third cut: 1.6–2.6 points above
Eurostat on the income-year axis.

## Geography: "T" is not "PT"

Every INE vital-statistics and cause-of-death cube has both a **T**
(Total) and a **PT** (Portugal) category for place of residence. T also
counts people resident abroad or of unknown residence (2022 assault
deaths: T 98, PT 97). Every staged INE series uses PT, the resident
population, which also matches Eurostat's scope. "Portugal" includes the
Açores and Madeira throughout; nothing mainland-only is staged.

## Vital statistics and causes of death

- Births: 0008086 (NUTS-2013, 2011–2023) and **0012436 (NUTS-2024, from
  2021, not 2024)** are identical on 2021–2023. They also equal Eurostat
  `demo_gind` (2011 differs by one birth). 0012094 gives eight months of
  2026 (57,421), a partial year.
- Deaths: 0008834 (sum of the three urban-typology categories, because
  there is no total) **stops at 2023**. It is within 18 a year of
  `demo_gind`. For 2024–2025, deaths exist only on Eurostat (118,396 /
  121,817) until the INE NUTS-2024 indicator is found (`meta.pending`).
- Causes: 0008206 (to 2022) and 0013166 (2022–2024) are **identical for
  all 65 causes in 2022**, so the seam is a relabelling. All-causes
  `T-LES` is listed in the metadata and refused by the data endpoint.
  Totals come from 0008834 / `demo_gind`. The zeros (meningococcal
  infection, SIDS) are published zeros.

## Homicide: police count and death certificate disagree both ways

| Year | Police (Eurostat ICCS0101) | Certificates (INE code 64) |
|---|---|---|
| 2008 | 124 | 146 |
| 2013 | 144 | 97 |
| 2016 | 66 | 83 |
| 2022 | 75 | 97 |
| 2024 | 72 | 86 |

These are offences against deaths, place of occurrence against residence,
police against the certifying doctor. They are two lines, and neither is
wrong. The national police count (RASI) is `meta.pending`. INE/DGPJ crime
rates (‰) have no homicide category. Their two indicators are identical
on 2021–2022.

## Three debt stocks and two deficits

- **Maastricht debt** (Eurostat EDP) equals BPstat's republication (series
  12561512) in every year. The fetcher checks it.
- **IGCP direct State debt** is a different object, and the gap changes
  sign. It ran €3–28bn *below* EDP through 2018 and €10–40bn *above* it
  from 2021 (Dec-2025: €315.2bn vs €275.1bn). EDP adds the rest of general
  government and nets out State debt held inside it. Never one line.
  IGCP breaks: Dec-2015 (margin accounts enter the total) and Dec-2018
  (duration valuation).
- **Cash budget outturn** (DGO via BPstat) against the **EDP deficit**.
  The two agree in some years (2013 −5.2 vs −5.2; 2020 −5.8 vs −5.8) and
  are 3 points apart in others (2014: −4.1 cash vs −7.4 EDP, the Novo
  Banco resolution capital; 2017: −1.3 vs −3.0, the CGD
  recapitalisation). The general-government cash series starts in 2013;
  the State series in 2006. All are year-to-date stocks read at December,
  so 2026 is eight months.
- The EDP deficit 2010 (−11.4) is the revised figure. Bank support was
  reclassified into it later, so the number quoted at the time was
  smaller.

## Prices, labour, markets: where the pairs agree

- IPC vs HICP: within 0.4 points in every year except 2023 (IPC 4.31,
  HICP 5.3). The HICP weights non-residents' spending, i.e. tourism.
- INE unemployment Série 2021 vs Eurostat: within 0.1 every year
  2011–2025. Série 2011 runs 0.1–1.0 below Série 2021 on the 2011–2020
  overlap: that is the vintage seam. The mean of twelve monthly estimates
  covers 2006–2010, where Eurostat for PT is empty.
- BPstat 10y yield vs Eurostat Maastricht yield: within 0.01 every year.
  The DE yield beside it gives a computed spread (8.98pp in 2012).
- Mortgage rates: two compilations (long series from 2003, percentile
  variable-rate from Dec-2018), two columns.
- PSI 20: Yahoo starts 2013-04-30, so it cannot truthfully be rebased to the
  spine's common 2006 base. The canonical equity slot stays pending rather
  than publishing a 2013-base series as comparable. The source remains
  `official: false`; the 2026 cell is the live bar of the fetch date.
- The policy rate's 2026 cell is the live DFR (2.50), not a year-end.

## Trade: two bases

INE customs goods exports are 59–72% of the national-accounts P6 (2025:
€79.0bn vs €133.9bn). Services, mostly tourism, are the rest, and the share
has fallen since 2020. INE serves **placeholder zeros** for the EU-27
aggregates in 2005–2012 (never compiled) and for GB after 2021 (split
into XU/XI). The fetcher drops both, so those cells are holes. World =
intra + extra is asserted month by month. 2026 has eight months.

## Credit

Household debt (BPstat) is a December stock: €173.6bn in 2025. The housing
ratio fell from 70.2% of GDP (2010/2012) to 37.1% (2025). The ratios are
quarterly and lag the monthly € stock in the running year. The NPL ratio
(FSI) starts 2015Q4 at 17.5% and is 2.1% now. The older *crédito
malparado* series is not spliced on.

## Departures from the spine (for the build to confirm)

None forced by the data so far: all twelve topics have staged series. The
weak spots are security (no national police count, so Eurostat ICCS0101
carries it), markets (PSI 20 missing 2006–2012), and migration stocks,
which are stale at 2023 on the permit basis and pre-revision on the
Eurostat basis.

## Changes to the discovery's files made in consolidation

- `country.yaml`: `flag_bands` is now three bands (green, bronze for the
  armillary sphere, red). `tests/test_core.py` requires three; the
  discovery's two-band version failed it.
- `SOURCES.yaml`: corrected throughout (see the commit). Start years,
  vintages, year conventions, units for comment-less sidecars, break
  flags, and three new `meta.pending` entries.

## Cross-source checks run in consolidation

| Check | Result |
|---|---|
| INE ΣQ nominal GDP vs Eurostat B1GQ | equal to ≤ €5mn every year 2006–2025 |
| INE 0014144 vs Eurostat real growth | equal 2006–2023; **2024: 2.1 vs 2.7 (vintage, see above)** |
| INE 0013431 quarterly y/y mean vs Eurostat | 2024 2.7, 2025 1.9: equal |
| Eurostat GDP × ECB EUR/USD vs WB GDP US$ | ≤0.01% 2006–23; WB 0.5–0.6% low 2024–25 (old vintage) |
| (P6+P7)/GDP vs WB openness | 0.0 to 2023; −0.4/−0.3 in 2024–25 (same vintage gap) |
| INE IPC vs Eurostat HICP | ≤0.4pt, except 2023 (1.0pt) |
| INE unemployment S2021 vs Eurostat | ≤0.1pt 2011–25 |
| BPstat 10y yield vs Eurostat Maastricht yield | ≤0.01 every year |
| BPstat Maastricht debt (12561512) vs Eurostat | 0.00pt every year 2006–25 |
| IGCP direct debt vs EDP debt € | −€28bn (2010) … +€40bn (2025), sign change 2019–21 |
| GG cash balance vs EDP deficit | equal 2013/2020; up to 3.3pt apart (2014) |
| INE vs Eurostat immigration / emigration | identical 2008–2020; INE revised far higher from 2021 |
| INE net migration vs imm − emi | equal to 2020; +148k adjustment in 2021 |
| INE 31-Dec vs `demo_gind` 1-Jan | within 50 people every year |
| WB population vs Eurostat pre-revision 1-Jan mean | exact 2009–10 and 2023–24; 8–88k below otherwise; ~690k below INE revised in 2024 |
| INE births vs `demo_gind` | identical (2011: 1 birth) |
| INE deaths vs `demo_gind` | within 18 a year |
| INE TFR vs `demo_find` | equal to 2020; Eurostat 0.05–0.14 higher 2021–24 (denominator vintage) |
| INE Gini / poverty vs Eurostat | identical after a one-year shift (income vs survey year) |
| Eurostat foreign-citizen stock (1 Jan) vs INE legal residents (prior 31 Dec) | +0.1% / +0.5% in 2024 / 2023; −4% to −12% in 2018–22 |
| Police vs certificate homicide | both directions (2013: 144 vs 97; 2022: 75 vs 97) |
| INE goods X vs national-accounts P6 | 59–72% (services) |
| causes 0008206 vs 0013166, 2022 | identical, 65 of 65 causes |
