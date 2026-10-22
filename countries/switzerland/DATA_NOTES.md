# Switzerland — data notes

What these sources were like to work with, and the judgement calls a reader
of the plates should not have to reverse-engineer. `SOURCES.yaml` carries
the per-file caveats; this file carries the ones that cross files.
Research pass, fetch swarm and consolidation: 2026-10-22. `DISCOVERY.md`
is the research pass's own report, kept as a record. Where it and this
file disagree, this file and `SOURCES.yaml` are right. The main places
they disagree are listed at the end.

All years are **calendar years**. The Swiss fiscal year is the calendar
year. An early brief said the fiscal year starts in April; that line was a
template leak, and nothing in any fetcher or sidecar is keyed on April
(checked by grep, and every BFS/EFV sidecar comment says so).

---

## 1. Two GDP vintages, and the seam is 2023

The BFS revised the annual national accounts on **2026-08-25**. Eurostat
`nama_10_gdp` and the World Bank still carry the previous BFS vintage.
They agree to the decimal through **2022** and part from **2023**. The
research pass said 2021; it was wrong.

| Year | BFS (current) | Eurostat (old) | Gap | Real growth BFS / Eurostat |
|---|---|---|---|---|
| 2022 | 819,703.7 | 819,703.7 | 0 | 3.53 / 3.5 |
| 2023 | 837,159.4 | 834,189.8 | +2,970 | 1.00 / 0.8 |
| 2024 | 860,932.1 | 853,957.0 | +6,975 | 1.52 / 1.4 |
| 2025 | 881,571.8 | 867,544.7 | +14,027 | 1.61 / 1.3 |

CHF millions. `fetch_bfs.py` asserts equality for 2006–2022 every run, so
when Eurostat takes the revision the run fails rather than the note going
stale.

Consequences:

- **Every Eurostat ratio to GDP for CH uses the old denominator from
  2023**: government TR/TE/B9/D41, the tax burden, COFOG, and household
  debt. So do World Bank GDP in US$, GDP per person and openness.
- **EFV divides by the current BFS vintage** (its `bip` 2024 = 860,932).
- Never divide a BFS numerator by a Eurostat denominator, or the reverse.
  Example: SNB HH+NPISH loans 2025 1,066.8bn over BFS GDP gives 121.0%.
  Eurostat publishes 123.0%. Both are right on their own vintage.
- World Bank GDP 2024 is US$969.9bn. BFS GDP at the SNB's 2024 mean
  USD/CHF gives about US$978bn.
- **Growth on the economy plate:** draw BFS ACPP as the national line. The
  harmonised Eurostat line beside it (spine rule 10) differs from 2023 by
  vintage alone, and the legend must say so.

## 2. Gold: two trade totals, and the BoP gold line is not the customs one

Switzerland refines most of the world's gold, so goods trade has two
totals.

- **Total 1** (*konjunkturelles Total*) excludes gold bars, other precious
  metals, gems, art and antiques.
- **Total 2** (*Generaltotal*) includes them.

| 2025, CHF mn | Exports / receipts | Imports / expenses |
|---|---|---|
| BAZG TOTAL1 (sum of continents) | 286,840 | 232,846 |
| SNB BoP Total 1 (DAT1) | 286,840 | — |
| BAZG TOTAL2 (CTCI5 SITC files) | 461,014 | 423,223 |
| SNB BoP foreign-trade total | 461,014 | — |
| BAZG GOLD_SITC971 | 163,762 | 179,833 |
| SNB BoP non-monetary gold | 149,583 | 173,745 |
| BAZG 7108.12 imports (gold file) | — | 173.7bn = BoP expenses |
| BFS P61 / P61XF11 (goods exports incl. / excl. gold) | 517,532 / 365,027 | |

Rules:

- **Both trade totals match to the franc** between customs and the BoP.
  The **gold lines do not**: customs SITC 971 exports 163.8bn against BoP
  gold receipts 149.6bn. Never equate them.
- **TOTAL2 begins in 2012.** Gold bars entered special trade on
  1 January 2012. Before that the same file gives `TOTAL2_PRE2012`, where
  gold is largely outside (2011 gold 2.1bn; 2012 82.3bn). That is a
  break, not a gold boom.
- **The gold file is imports of 7108.12 only.** It does not cover all of
  SITC 971, and it has no exports.
- **The BFS national accounts carry gold too.** P6/P7 include it. The
  `_ex_gold` columns remove it.
- **The spine's trade slot 1** (exports and imports % GDP, national
  accounts) uses BFS P6/P7 over BFS GDP, on one vintage. It includes
  gold. Phase B decides whether the ex-gold line rides beside it. It
  should, because 2025's jump is gold to the US.

Scope: BAZG data is the **Swiss–Liechtenstein customs area**.

## 3. Immigration counts changes of status, and Eurostat changes its mind

BFS immigration is *Einwanderung inkl. Änderung des Bevölkerungstyps*.
Someone who has spent 12 months in the non-permanent population (asylum
seekers, S status, L permits) is counted as an immigrant when they move
into the permanent one. The 2023 peak (263,081) is largely Ukrainians with
S status crossing that line: the type-change component was 87,623 that
year. 65,260 S-status holders were in the permanent population at
end-2025.

**Consolidation finding.** Eurostat `migr_imm1ctz` CH is **not** one
definition across years:

| Years | Eurostat vs BFS |
|---|---|
| 2000–2010 | equal (type changes included) |
| 2011–2022 | lower by **exactly** BFS's type-change component (2015: 153,627 vs 188,515; 2022: 167,079 vs 190,883) |
| 2023–2024 | equal again (2023 263,081) |

Emigration is equal in every year. The research pass checked only 2023
and concluded "same definition". The harmonised series therefore has two
definitional seams, at 2010/11 and 2022/23. `fetch_eurostat.py` now pins
2010, 2015, 2022 and 2023, so a re-transmission that changes either
regime fails the run.

For the migration plate (slots 1–2, per 1,000 people):

- **Draw BFS**, labelled "incl. change of population type". Its
  definition is constant.
- If the Eurostat line appears, draw it as three segments with both
  seams annotated, never as one line.
- Net migration is BFS immigration minus emigration, which includes the
  type changes. Say so.

Other migration notes:

- **The stock** is on two cuts: foreign citizens on 1 Jan 2025 2,478,134
  (Eurostat FOR_STLS) and foreign-born 2,870,124 (2011+ only). Slot 3's
  foreign-born share has no harmonised value before 2011.
- **The permit table** is STATPOP. Its 2010 total equals the balance's
  1 Jan 2011 stock (the first register year). From 2011 it equals the
  31 Dec stock to the person.
- **First permits** (`migr_resfirst`) are missing for 2019 and 2020, and
  the holes stay blank. They cover third-country nationals only.
- **S status is not asylum.** It is absent from the asylum tables.
  Asylum applications 2025 were 25,750; first-time applications 23,415.

## 4. Assisted suicide is inside suicide until 2008

BFS publishes assisted suicide as its own series **from 2003**, not 2009.

- **2003–2008:** the same deaths are also inside "Suizid" in the
  cause-of-death table.
- **From 2009:** they are coded to the underlying disease instead.

Suicide falls from 1,313 (2008) to 1,105 (2009) for that reason alone.
Assisted suicide grows from 253 (2008) to 1,774 (2024). **Never add the
two series**, in any year. Draw them side by side, with the 2008/09 seam
annotated on the suicide line.

Eurostat `hlth_cd_aro` starts in 2011, so it is on the post-2009
definition throughout. It uses `resid=TOT_IN`, all deaths in the country
including non-residents, so it sits above BFS:

| | Eurostat | BFS residents |
|---|---|---|
| Suicide 2024 | 1,043 | 996 |
| All causes 2022 | 75,199 | 74,425 |

Suicide **rates** (security slot 2) are computed from the BFS resident
counts over the BFS resident population (§9). The age-standardised rates
BFS publishes by sex are not the spine's crude rate.

## 5. Four debt figures, two tax ratios, and outturn against forecast

All of these are general government, 2024, % of GDP, and all are correct.

| Measure | Value | Source |
|---|---|---|
| Maastricht debt | 23.7 | EFV |
| GFS gross debt | 30.0 | EFV |
| GFS total liabilities | 40.4 | EFV |
| IMF GGXWDG_NGDP | 40.4 | IMF (= EFV total liabilities) |
| Net debt | 18.3 | EFV |
| Fiskalquote (tax ratio) | 26.7 | EFV |
| Extended tax ratio | 37.3 | EFV (adds compulsory health-insurance premiums and BVG pension contributions) |
| Eurostat tax burden (D2_D5_D91_D61_M_D995) | 27.8 | Eurostat, old vintage |

- **Fiscal slot 3** (gross debt) uses the IMF series. Eurostat has no EDP
  tables for CH, and the IMF series equals EFV total liabilities. The
  Maastricht 23.7 belongs in the note, or as a labelled second line, so
  a reader comparing with the EU understands why 23.7 and 40.4 both
  appear.
- **EFV against Eurostat on revenue and expenditure:**
  - 2024 TR 31.6 vs 33.1, TE 31.4 vs 32.8.
  - The 1.5-point gap is more than the vintage (about 0.25 pt), so it is
    also a recording difference between the EFV GFS model and Eurostat's
    ESA table.
  - The canonical slot (rule 10) uses Eurostat, with EFV beside it.
  - The balances agree: B9 0.3 vs EFV 0.29.
- **Interest** (slot 4) comes from Eurostat D41PAY (2024 0.3%). EFV
  publishes no interest column.
- **Primary balance** = B9 + D41PAY, both Eurostat. It is computable.
- **Outturn vs forecast:** every EFV row carries its status. For general
  government, **2024 is the last outturn**. 2025 and 2026 are EFV
  forecasts (*Prognosen*), and `fetch_efv.py` asserts that last-outturn
  year. Subsectors differ: the Confederation and social security already
  have 2025 accounts. A 2025 general-government point on a plate is
  drawn as a forecast, never as a result.
- **Spending by function** now comes from EFV `gfs_dashboard/cofog_int.csv`
  (the ten COFOG divisions):
  - The ten sum to EFV GFS expenditure (asserted).
  - They sit within 1.5 pt of Eurostat COFOG.
  - The national functional file `fir_art_funk.csv` is 1.26 GB and was
    not used.
  - Social protection is only 12.2% of GDP (2024) because compulsory
    health insurance and occupational pensions sit outside government.
    The spending plate needs that note, or the Swiss welfare state reads
    as small.

## 6. SNB: two instruments, two credit definitions, three breaks

- **The policy rate.** Until 2019-05 the SNB set a target range for
  3-month CHF Libor (`libor_target_lower/upper`). From 2019-06 it sets the
  SNB policy rate (−0.75 then; 0.0 since 2025-06). These are separate
  columns, never one line. Markets slot 1 draws the range as a band and
  the policy rate as a line, with the 2019 seam annotated.
- **The fromDate trap**, which the research pass fell into. Asked without
  `fromDate`, a cube answers only its recent past. With it:
  - `bopcurra` runs from 1983, not 2016.
  - Financial accounts `frsekgevehup` run from 1999, not 2016.
  - Offered mortgage rates `zikrepro` run from 1990 (variable) and
    2007-12 (fixed), not 2025-08.

  As a result, the old pending item 4 ("BoP and household FA before
  2016") is gone, and 2006–2009-04 mortgage rates are covered by the
  offered variable rate.
- **Two household-debt definitions:**
  - Banks only (`bakredsekbrm`): Dec-2025 945.3bn.
  - All lenders (financial accounts): 1,051.0bn households, 1,066.8bn
    HH+NPISH, equal to Eurostat `nasa_10_f_bs` to the million.

  They are two lines. The spine's credit slot 1 wants BIS WS_TC (2025-Q4
  122.9% of GDP), which is not staged yet (see HANDOFF).
- **Breaks in the bank series:**
  - +60bn between 2006-08 and 2006-09 (reporting change; every December
    row in the window is after it).
  - −10bn in other loans in 2007-12, unexplained.
  - **2026-04**: about 17bn reclassified from mortgages to other loans.
    The 2026 split is not comparable with 2025; the total is.
- **`rendoblim` froze at 2025-07** while still answering HTTP 200. The
  yields come from `rendeiduebm`, and every monthly cube is asserted to
  be recent.
- **The franc floor** (1.20 per EUR from 2011-09-06, removed 2015-01-15)
  is an event, not a band. FX is CHF per unit, so a rising line is a
  weaker franc. Markets slot 3 must invert it into "up = stronger".

## 7. The Liechtenstein question (open)

- **BAZG trade** is the Swiss–Liechtenstein customs area. That is certain.
- **The SNB cubes** (bank credit, BoP, reserves, financial accounts): the
  research pass and the fetchers assumed "currency area incl.
  Liechtenstein", but no SNB note found today says so per cube. The
  sidecar comments and `country.yaml` were softened to "unconfirmed".
  It is `meta.pending` in SOURCES.yaml.
- **Before an SNB panel claims a scope**, read each cube's methodological
  notes. Until then, the panel names the SNB as its scope.
- **BFS, EFV and SECO** are Switzerland only.

## 8. Survey against register, and three Ginis

- **Unemployment** has two concepts, so two lines:
  - The ILO survey rate (BFS SAKE): annual 2010+, Q2-only before 2010 in
    its own column; 2025 4.84%.
  - SECO's registered count (2025 job seekers 214.1k). It has a
    registration-system break in March 2018.
  - Eurostat `lfsa_urgan` (2025 4.9) is the harmonised twin of the ILO
    rate.
- **Three Ginis for 2023**, and none is the other:
  - HABE disposable 0.305 (a fraction).
  - SILC 31.5 (Eurostat; the income year is the year before the label).
  - World Bank 33.5.

  People slot 1 uses SILC as the harmonised line, with HABE beside it on
  the same 0–100 scale (×100, labelled).
- **Poverty** has two definitions, so two lines:
  - The BFS absolute poverty rate against the SKOS social minimum: 2024
    8.4%.
  - Eurostat's relative at-risk rate (60% of the median): 16.2%.
- **Arrears** are a SILC survey of people, not a loan register. 2024:
  any arrears 15.36%, **taxes 8.75%** (the research pass's 3.86% was the
  utilities column), mortgage 0.21% of owners. Denominators differ by
  item, and there is a definitional seam in `loans_pct` in 2017.

## 9. Rates and denominators (the UNIT RULE)

The spine wants deaths and violence per 100,000 people, and births,
deaths and migration per 1,000.

- **The population of record** is the BFS permanent resident population
  from the demographic balance (`balance_from_bfs.csv`), Switzerland
  only. Use the mean of 1 Jan and 31 Dec as the mid-year denominator.
  `fetch_bfs.py` already does this for the PKS homicide rate (2024 0.50,
  2025 0.61 per 100k). The panel or DATA_NOTES names it.
- **The cross-check:** the World Bank mid-year population agrees within
  0.04% (2025 9,092,436 vs the BFS mean 9,089,077).
- **The denominator seam:** from 2010 the permanent population includes
  asylum seekers and S-status holders resident 12+ months. It is small
  and noted in the fertility sidecar.
- **Two homicide counts, never one line:**
  - Police completed homicides (PKS 2024 45; Eurostat ICCS0101 equal, and
    carrying 2008).
  - Assault deaths on death certificates (Eurostat 2024 38; counted by
    residence, not by place of offence).

  Attempts (251 in 2025) are four times the completed count. The PKS
  "total" is mostly attempts and is never drawn as "homicides".
- **Firearm deaths** (204 in 2024, of which 183 suicides) are a superset
  of firearm homicide. They are a lens, not a homicide peer.

## 10. Smaller things that will bite

- **The SECO real-time database** stops at **2026Q1**: its latest vintage
  is 2026q2, released 2026-06-01. Eurostat `namq_10_gdp` already has
  2026Q2.
  - `gdp_cssa` (SECO's headline) is also adjusted for major sporting
    events (FIFA/IOC/UEFA licence revenue). `gdp` and Eurostat are not.
    They are separate columns.
  - The `_qoq_first` columns keep first releases. For `gdp_cssa` they
    are blank before vintage 2018q3.
- **The CPI was rebased to Dec-2025 = 100.** Take rates, not levels
  across bases. The LIK and the HICP differ by tenths (2015 −1.1 vs
  −0.8).
- **The wage index has three bases**, written as labelled rows
  (`1993=100`, `2010=100`, `2020=100`). The base-2010 file starts in 2011,
  so 2006–2010 come from base 1993. Draw the BFS year-on-year changes,
  which are asserted equal where bases overlap.
- **Life expectancy is by sex only.** BFS publishes no both-sexes figure
  and none is computed.
- **The demographic balance publishes 0 for flows before 1981.** Those
  are holes, not zeros, so the sidecar starts in 1981.
- **The projection's launch years (2024–2025) are modelled.** They are
  never spliced onto the observed balance. Spine: the projection is a
  note on demography slot 1 (reference scenario A-00-2025).
- **The SMI** is Yahoo, `official: false`. Bars are stamped at Zurich
  midnight in UTC, a month early if converted naively. The 2026 row is a
  live reading (`as_of 2026-10-22`).

## Where DISCOVERY.md is wrong (corrected here and in SOURCES.yaml)

| DISCOVERY.md said | Correct |
|---|---|
| GDP vintages part from 2021 | from 2023 (equal through 2022) |
| Eurostat imm1ctz = BFS, same definition | equal 2000–10 and 2023–24; excludes type changes 2011–22 |
| Assisted suicide moved out of suicide from 2009 (own series from 2009) | own series from 2003; inside Suizid 2003–08 |
| SNB BoP and household FA start 2016; zikrepro starts 2025-08 | 1983, 1999, 1990/2007-12 with fromDate |
| SILC taxes arrears 3.9% | 8.75% (3.86% is utilities) |
| ILO annual rate 2012–2025 | annual from 2010; Q2-only before |
| Wage base-2010 covers 2006–2020 | starts 2011; 2006–10 from base 1993 |
| BFS GDP CSV repeats rows | not in this edition (still asserted) |
| Spending by function from fir_art_funk.csv | EFV gfs_dashboard/cofog_int.csv |
| SNB series include Liechtenstein | unconfirmed (open) |
| Gold file = gold trade | imports of 7108.12 only |
