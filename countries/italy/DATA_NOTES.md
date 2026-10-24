# Italy — data notes

These notes cover what the Italian sources were like to work with, and the
judgement calls a reader of the plates should not have to work out again.
`SOURCES.yaml` holds the caveats for each file. This file holds the ones
that span several files. The research pass and consolidation were both
done on 2026-10-22. `DISCOVERY.md` is the research pass's own report, kept
as a record. Where it disagrees with this file, this file and
`SOURCES.yaml` are right.

---

## ISTAT went quiet halfway through

esploradati.istat.it stopped answering at about 10:35 and was still timing
out at consolidation. It is almost certainly throttling after a morning of
heavy pulls. Every ISTAT sidecar staged here came from responses cached
before then. Six series are `meta.pending`, and each one's key is already
pinned in `fetch_istat.py`: the NIC on bases 1995 and 2010 plus ISTAT's
published rate, the attempted/mafia/infant homicide columns, life tables,
fertility by mother's citizenship, the non-EU permit stock, and
citizenship acquisitions by process. Two staged files are partial because
of this, and each says so in a `# PENDING` comment line:
`nic_from_istat.csv` and `homicide_police_from_istat.csv`.

None of the six blocks a canonical spine slot. Eurostat HICP carries
inflation from 2006, `demo_find` carries the TFR, `migr_resfirst` carries
permits, and `migr_acq` carries naturalisations.

## The national accounts and the labour survey stack every vintage

ISTAT's national-accounts and labour flows carry an EDITION dimension,
with one full copy of the history per release. The fetcher keeps the
latest edition, ordered as (year, month, release), so 2026M10 > 2026M9 and
2026M9G11 sorts correctly. Pinned today: GDP **2026M10**, unemployment
**2026M9G11**. Edition order matters: Q1-2025 growth moved 0.338 → 0.393
between 2026M9 and 2026M10. A rerun after a new release changes numbers,
and that is a revision, not a bug.

GDP comes in quarterly **levels** (€mn, raw). The annual figure is the
sum of the four quarters, and it equals Eurostat `nama_10_gdp` within €5mn
in every year 2006–2025.

## Unemployment: one series from 2006 after all

The discovery feared a 2021 survey-regulation seam (pending #7). The fetch
settled it. The current-regulation flow 151_884 is **backcast to
2006-Q1**, so 2006–2025 is one series on the post-2021 definitions. It is
within 0.1 point of Eurostat `une_rt_a` in every year from 2009, and it is
the only coverage for 2006–2008, because `une_rt_a` starts in 2009 for
Italy. Draw ISTAT as the line. Eurostat beside it adds nothing visible.

## The NIC rebase, and why the early NIC is missing

ISTAT rebased the NIC to 2025 = 100 with the January-2026 release. Flow
167_747 holds base 2015, and that base covers **2016–2025 only**. The
years 2006–2015 are published on bases 1995 and 2010, which are pending.
Within base 2015 the computed rates match ISTAT's published media annua:
2017 1.2, 2022 8.1, 2023 5.7, 2024 1.0, 2025 1.5. The 2026 cell is the
base-2025 mean of nine months. **Never compute a rate across that seam**
from the two index columns. When the published-rate column (MEASURE 8)
lands, it carries the rate across the bases.

HICP against NIC: within 0.2 point most years, but 2022 is HICP 8.7
against NIC 8.1 and 2023 is 5.9 against 5.7. The indices differ in
scope and weighting (the HICP counts what households actually pay,
including sales prices). Economy slot 3 draws HICP, the
harmonised series, with the NIC beside it.

## Population: one vintage, mostly from Eurostat

ISTAT re-based resident population after the 2011 census and again for
the permanent census (2018 onward). Flow 22_289 now carries **only
1-Jan-2019 to 1-Jan-2026** (2026 flagged as an estimate). Eurostat
`demo_gind` and `migr_pop1ctz` carry ISTAT's reconstructed series from
2006 and equal 22_289 to the person on every year they share. So the
2006+ population line is the Eurostat file, on one vintage, with ISTAT as
its confirmation. The same holds for foreign residents: 29_7 covers
2019–2026 and matches Eurostat `FOR_STLS`.

The World Bank population is mid-year. It runs 35–245k above the
1-January series before 2014 and 13–200k below it afterwards. Use it for
nothing but GDP per person.

**Rates per 1,000 and per 100,000** use Eurostat `demo_gind` 1-January
population. That is the same territory (Italy) and the same legal scope
(registered residents) as ISTAT's births, deaths, flows and
certificate-based causes. For example, 2024 crude birth rate is 6.27 and
crude death rate 11.08. Eurostat's own published crude rates use the
annual average population, so they differ in the second decimal. If a
plate quotes Eurostat's rate, use the published one rather than ours.

## Deaths: three counts

- Register deaths (ISTAT 26_29, from 2011) equal `demo_gind` exactly. Use
  `demo_gind` for 2006–2010 and for 2025 (651,830).
- Death certificates (39_494, all causes) are a different count: 2023
  662,652 against 671,065 on the register. Never subtract one from the
  other.
- Causes of death run 2006–2023 on the European shortlist (91 codes that
  nest; never sum the column). COVID-19 (code 20) is 78,408 in 2020
  (131.5 per 100k) and 15,851 in 2023. Suicide (17_2) is about 3,650–3,730
  a year, 6.1–6.5 per 100k. Transport accidents (17_1_1) are **all
  modes**, not road only: 2019 3,296 against ISTAT's road-accident count
  of about 3,170 at 30 days. Label the security slot accordingly, or fetch
  the road series (see HANDOFF).

## Homicide: police counts are higher in every year

| Year | Police-recorded completed intentional homicides (73_67) | Certificates, assault X85–Y09 (39_494) | Certificates ÷ police-recorded |
|---|---|---|---|
| 2006 | 621 | 475 | 0.76 |
| 2010 | 526 | 413 | 0.79 |
| 2015 | 469 | 355 | 0.76 |
| 2019 | 318 | 235 | 0.74 |
| 2020 | 289 | 212 | 0.73 |
| 2023 | **341** | **239** | **0.70** |
| 2024 | 326 | — | |

Unlike Spain or Portugal, Italy's two counts do not cross. The
certificates are 15–30% lower in every year, and the gap is widening.
These are offences against deaths, place of occurrence against the
victim's residence, and police against the certifying doctor. Plausible
contributors, none of them measured here:
- victims who are not registered residents, including irregular migrants
  and visitors, appear in the police count but not in the resident
  certificate count;
- deaths certified as "undetermined intent" (Y10–Y34);
- offences reclassified after the report.

Record both lines and claim neither as the truth. ISTAT's own police rate
is published to **one decimal** (0.6 in 2024). On the spine's log axis,
0.5 and 0.6 are a visible step that is really rounding. For a smoother
line, compute count ÷ `demo_gind` population (2024: 0.55) and say so, or
draw ISTAT's published rate as the spine prefers and note the rounding.
UNODC `VC.IHR.PSRC.P5` is not staged.

## Migration: one series under two names, and a 2008–2010 gap

- **Eurostat's two cuts have equal totals** (`migr_imm1ctz` =
  `migr_imm3ctb`, 2008–2024, asserted by the fetcher). Italy sends one
  flow under both definitions. The citizenship/birth contrast lives in the
  splits: non-EU 352,461 by citizenship against 373,637 by birth in 2024.
  The EU/non-EU splits exist only from 2020, for both flows.
- **ISTAT 28_185 against Eurostat.** They are equal to the person in
  2006–2007 and 2011–2024. In 2008–2010 Eurostat is higher:

  | Year | Imm. Eurostat | Imm. ISTAT | Δ | Emi. Eurostat | Emi. ISTAT | Δ |
  |---|---|---|---|---|---|---|
  | 2008 | 534,712 | 494,394 | +40,318 | 80,947 | 61,671 | +19,276 |
  | 2009 | 442,940 | 421,859 | +21,081 | 80,597 | 64,921 | +15,676 |
  | 2010 | 458,856 | 447,744 | +11,112 | 78,771 | 67,501 | +11,270 |

  The gap opens exactly with reference year 2008, the first year under
  Regulation (EC) 862/2007, and closes in 2011, the census year. The most
  likely reading is that Italy's 2008–2010 transmissions were adjusted to
  the Regulation's 12-month usual-residence definition, or revised against
  the 2011 census, while ISTAT's register series was not. That is
  **unverified**: the Eurostat metadata page has no Italy-specific note.
  The Italian-citizen splits differ in the same years (2008: 38,163 against
  32,118). Draw them as two lines, never spliced, and annotate 2008–2010 as
  "definitions differ".
- ISTAT already has **2025** (immigration 439,916, emigration 144,157).
  Eurostat stops at 2024.
- Register emigration undercounts: leaving needs no paperwork, and AIRE
  registration lags. The balance column in the ISTAT file is a simple
  difference with no adjustment. Publish the two flows.
- Stocks on 1-Jan-2025: foreign citizens 5,371,251 (9.1%), foreign-born
  6,928,045 (11.8%). The citizenship code is **`FOR_STLS`**, because
  `citizen=FOR` returns a well-formed empty cube for Italy. The birth cut
  uses `FOR`.
- Naturalisations are high. They peaked at 201,591 in 2016 and passed
  213k in 2022–2024, which is why the foreign-citizen share rises more
  slowly than the foreign-born share. First permits reached 433,099 in
  2025. Permits are administrative events, not arrivals.

## Credit: two NPL measures and a borrowed denominator

- **Household debt.** Banca d'Italia's financial accounts give loans to
  households and NPISH (F41 + F42, read at Q4). BdI publishes no
  disposable income, so the ratio divides by Eurostat `nasa_10_nf_tr` B6G
  S14_S15. The column is named `_computed`. For 2024 it gives 55.9,
  against 56.1 in the BdI Financial Stability Report and 55.4 in Eurostat
  `tec00104`. The spine's slot is **% of GDP on BIS**. The same loans over
  Eurostat GDP give 36.1 (2024), BIS WS_TC gives 36.0 and Eurostat
  `tipspd22` gives 36.1, so all three agree. BIS is not staged.
- **NPL.** The primary series is the IMF FSI **gross** NPL ratio, from
  2011: 18.0% at the 2015 peak, 2.4% in 2025. The 2011–2014 values predate
  the 2015 EBA non-performing-exposure definition, so annotate the seam.
  Beside it sits the *sofferenze* stock. The discovery called it "net of
  provisions". It is **gross**, and it was **discontinued after March
  2024**. Its ratio is computed against loans in the same month, which
  makes the 2024 row mixed: bad loans and their ratio are March, while
  the loans column is December. Read the period columns. The FSI ratio
  covers 2025-Q2 at 2.6, against 2.7 in BdI's FSR (a narrower bank set).
  The two measures are never joined.
- Lending rates (MIR): new house-purchase loans averaged 1.32% in 2020 and
  4.17% in 2023. 2026 has eight months.

## Fiscal: EDP throughout

The MEF/RGS BDAP never connected, so every fiscal number is the Eurostat
EDP transmission, which is the same Maastricht aggregate RGS computes.
Points to annotate:
- Debt crossed **€3tn in 2025** (Q4 €3,097.1bn, 136.7% of GDP). The peak
  ratio was 154.7% in 2020.
- The primary balance was positive every year 2010–2019, then negative
  2020–2023, and back in surplus in 2024 (+0.5) and 2025 (+0.7). Interest
  is 3.3–5.1% of GDP throughout.
- The 2021–2023 deficits (−8.9, −8.1, −7.1) and the COFOG "other" bump
  (GF06 housing, 4.3/5.1/6.1% of GDP) are the building bonuses
  (Superbonus 110%). ESA records the credits as expenditure when the work
  is done. Check the EDP notification notes before writing the annotation.
- COFOG runs to 2024. The summed groups (defence + order, other) exist
  only in years where every part is published. Consolidation fixed a
  `.get(y, 0)` zero-fill; no number changed, because every part runs
  1995–2024.

## Inequality and poverty

- **Eurostat's SILC Gini for Italy now starts in 2014.** `ilc_di12` and
  `tessi190` both hold Italy for survey years 2014–2025 only. This is the
  source, not the fetch. For 2006–2013 the World Bank Gini (EU-SILC
  microdata, its own income definition) is the only line. It runs 1.0–3.2
  points above Eurostat, so draw both, labelled, and never splice them.
- AROP (`ilc_li02`) does cover 2006–2025, on the survey-year axis.
- ISTAT absolute poverty (household incidence, 34_727) is the national
  headline: 6.0% in 2014, 8.1% in 2025. The new series starts in 2014 on
  a revised basket. The old series (34_201, to 2013) is a different
  basket and is not staged. Household incidence is not overlaid on the
  canonical person-rate axis. The lens explicitly contrasts person-based
  EU-SILC risk with ISTAT's household-based relative-poverty measure.

## Markets

- The BTP 10-year yield (Eurostat `irt_lt_mcby_a`) equals the ECB IRS
  monthly mean to 0.01 in every year 2006–2025. The 2012 peak is 5.49.
- The policy rate is the ECB's: the DFR at year-end, with the MRO beside
  it. The MRO is blank for 2006–2007 in the series as staged. The 2026
  cell is the live 2.50.
- FTSE MIB comes from Yahoo, `official: false`, as a price index
  (dividends excluded). Year-end closes are staged for 2005–2025, plus the
  live 2026 bar (48,813.77). The spine's slot is in **US$, indexed 2006**:
  combine it with the ECB year-end rate, plus an S&P 500 series this lane
  has not staged.

## World and comparables

- WB GDP in US$ equals Eurostat × the ECB mean rate within 0.25% for
  2006–2023, and is 0.4% low in 2024. The Bank still has the
  national-accounts vintage from before ISTAT's 2026 revision. The
  openness series shows the same vintage gap.
- Reserves jumped from US$290.5bn in 2024 to 434.0bn in 2025. That is the
  gold price on Italy's ~2,450 t, not purchases. The plate should say
  that the ECB holds the union's buffer.
- The HDI file (HDR 2025) is Latin-1 and covers 2005–2023.

## Departures from the spine (confirmed at build)

No chapter is forced out. Gaps are listed slot by slot in HANDOFF.md. People
slot 3 is a true absence rather than an unfinished fetch: Italy has **no
statutory minimum wage**. Pay floors come from sector collective agreements
(CCNL). The panel says so and draws nothing.

## Changes made in consolidation

- `SOURCES.yaml`: corrected throughout:
  - ISTAT: coverage (NIC base 2015 is 2016–2025; population and foreign
    residents 2019+; poverty 2014+; deaths 2011–2024), the
    ITTOT/IT immigration and emigration keys, X1033, and the six-part crime
    key; labour pending #7 resolved.
  - BdI: the PROSPETTODATI paging, bad loans gross and ending March 2024,
    FSI as primary, the Eurostat denominator, and the fetcher name.
  - Eurostat: the COFOG zero-fill fix and Gini from 2014 only.
  - The World Bank Gini entry moved from `international/` to `social/`,
    where the fetcher writes it. Four manifest entries with no sidecar
    (lifexp, fertility, permit stock, acquisitions) moved to
    `meta.pending`. The labour-continuity pending item was dropped as
    resolved, and an ISTAT-throttle item and a minimum-wage item were
    added.
- `fetch_eurostat.py`: `demography_from_estat.csv` now writes population
  in persons and births and deaths as whole numbers (the first draft wrote
  `pop_mn` and counts with four decimals). The values are unchanged.
- `DISCOVERY.md` moved here from the lane root.

## Cross-source checks run in consolidation

| Check | Result |
|---|---|
| ISTAT ΣQ GDP (ed. 2026M10) vs Eurostat B1GQ | within €5mn every year 2006–2025 |
| ISTAT RFL vs Eurostat `une_rt_a` | within 0.1pt 2009–2025 (2024 6.57 vs 6.5) |
| NIC computed rate vs ISTAT published | equal 2017–2025 |
| NIC vs HICP | ≤0.2pt most years; 2022 8.1 vs 8.7 |
| ISTAT 22_289 / 29_7 vs Eurostat population / FOR_STLS | equal to the person 2019–2026 |
| ISTAT births / deaths vs `demo_gind` | identical (births 2006–24, deaths 2011–24); 2025 births 355,772 vs 355,435 (provisional) |
| WB population vs Eurostat 1-Jan | +35k…+245k to 2013, −13k…−200k after (mid-year) |
| ISTAT vs Eurostat immigration / emigration | identical 2006–07 and 2011–24; Eurostat higher 2008–10 (above) |
| Eurostat imm1ctz vs imm3ctb totals | identical 2008–2024 |
| Police vs certificate homicide | certificates 15–30% lower every year; 2023 239 vs 341 |
| BdI loans/GDI vs BdI FSR vs Eurostat `tec00104` | 55.9 / 56.1 / 55.4 (2024) |
| BdI loans/GDP vs BIS WS_TC vs Eurostat `tipspd22` | 36.1 / 36.0 / 36.1 (2024) |
| FSI gross NPL vs BdI FSR | 2.6 vs 2.7 (2025-Q2) |
| Eurostat Maastricht yield vs ECB IRS monthly mean | ≤0.01 every year 2006–2025 |
| Eurostat GDP × ECB vs WB GDP US$ | ≤0.25% 2006–23; WB −0.4% in 2024 |
| (P6+P7)/GDP vs WB openness | ±0.05 to 2009; WB 0.2–1.0 above after (vintage) |
| WB Gini vs Eurostat SILC | WB 1.0–3.2pt higher 2014–23 (2023 34.3 vs 31.5) |

## Build decisions (the plate pass)

- **ISTAT was still down through the build.** Its six `meta.pending`
  series got no plates, no scraped stand-ins and no gap-filled lines.
  The two slots whose national detail they would have carried — the
  mafia-homicide columns in the security lens, and the ISTAT NIC bases
  before 2016 — say so on the panel instead.
- **Recession bands** come from the staged vintage's quarter-on-quarter
  sign runs (Eurostat `namq_10_gdp`, edition 2026-10-22) and are pinned
  in `country.yaml` and in a test: 2008.25–2009.5, 2011.25–2013.0,
  2020.0–2020.5. The 2019 Q3–Q4 negatives on this vintage touch the
  pandemic run but belong to the growth stall, which is drawn as an
  event annotation, not a band; 2013 Q4/2014 Q1 at −0.1 stay out.
- **Harmonised substitutes, each labelled as what it is:**
  - credit slot 1: the spine's BIS household-debt series is not staged;
    BdI loans ÷ Eurostat GDP is drawn instead, and the note pins it
    (36.1 for 2024 against BIS 36.0 and Eurostat 36.1). The S&P 500
    dashed comparator is `meta.pending`.
  - security slot 3: the staged death certificate shortlist carries only
    `17_1_1`, transport accidents by **all modes**, not road-only. It is
    therefore kept out of the canonical panel, which remains visibly pending
    for the ISTAT 30-day road-death or Eurostat `tran_sf_roadus` series.
  - trade slot 3 uses the 2023 Italy-reporter UN Comtrade customs-goods
    snapshot, with shares divided by the World export total. It is retained
    in the trade lens; canonical destination slot 3 remains pending until an
    annual partner series is staged. World slot 3
    uses TI's CPI 2025 workbook and keeps only its comparable 2012–2025
    method. People slot 3 remains empty because no statutory national
    minimum wage exists; the panel states that absence explicitly.
- **Rates** are counts over the Eurostat 1-January population from the
  same file (`demo_gind`), the same territory and registered-resident
  scope; where ISTAT publishes its own rate (police-recorded homicides) its rate
  is used. CBR 6.27 and CDR 11.08 for 2024, pinned.
- **The NIC panel draws one base only** (`index_b2015`, 2016–2025); the
  base-2025 index starts 2026-01 and is staged but not drawn; nothing
  is spliced across the 2025 rebase.
- **i18n**: `i18n.json` carries all 376 rendered strings in Italian,
  English and Portuguese; the render is strict-clean in all three.
- **Layout**: the render passes `tests/test_layout.py` with zero faults
  in it, en and pt — every panel goes through `_finish` (style_axis),
  and notes, legends and event marks sit where the reference scale
  leaves room.
