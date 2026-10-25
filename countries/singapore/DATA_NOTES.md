# Singapore — what these numbers are, and how to read them

Phase A (data) notes, 2026-10-25. The publisher-by-publisher probe record is
`DISCOVERY.md`; the manifest is `SOURCES.yaml`. This file is the judgement
calls: what was derived, what was deliberately not derived, which two things
that look alike are not the same thing, and what is not drawn at all.

---

## 0. The frame is wrong before it is right

Singapore is a city and a state at once, 744 km² of it, and three of the
atlas's habitual frames break here. They are stated once here and repeated on
the plates where they bite.

**GDP per person is the headline, and the denominator is contested.** The
resident population is 4.20 million, the citizen population 3.66 million, and
the total population 6.11 million — because 1.91 million people are here on
work permits, employment passes, S passes, student passes and dependant's
passes. The non-resident share moves with the construction and services
cycle, so "GDP per person" can fall in a year when GDP rises. Every per-capita
figure in this lane names the population it divides by; the World Bank's
(NY.GDP.PCAP.CD) divides by the *total*, which is the only choice that matches
what is being produced.

**"Country" misleads on trade.** A city that refines, packs and re-exports
what it imports has exports of goods and services at 178% of GDP and imports
at 142% (2025). That is not an error and it is not a customs anomaly: it is
what a small open economy's national accounts look like. It also means the
customs series (domestic exports *plus* re-exports) and the national-accounts
series are different objects, and they are staged in different files.

**Land area and density are legitimate readings here.** 744.3 km² at
end-2025, up from 581.5 in 1960 by reclamation, and 8,300 people per km² in
that year (8,332 by mid-2026). They are in the demography
file because they change what the other numbers mean. They are *lens*
material, not a comparison slot: no other country in the atlas is also its own
city, so a density axis wiped across Germany would compare incomparable
territories.

---

## 1. Population: three populations, never one

SingStat publishes, at mid-year (end June):

| line | 2025 | what it is |
|---|---|---|
| `population_total` | 6,111,175 | everyone present: citizens + PRs + non-residents |
| `population_resident` | 4,204,515 | citizens + permanent residents |
| `population_citizen` | 3,660,683 | citizens only |
| `population_pr` | 543,832 | permanent residents |
| `population_nonresident` | 1,906,660 | pass holders and their dependants |

Only one denominator is ever used per series, and it is named:

- **Total** for GDP per person (comparable with the World Bank), for the
  murder and suicide rates (both counts cover everyone present — see §6), and
  for the publisher's own crime and population-density rates.
- **Resident** for every vital rate the publisher publishes (crude birth,
  crude death, infant mortality) and for the labour-force rates. These are the
  publisher's own definitions, and they are about a third higher than the same
  count over the total population. That is a denominator, not a finding.
- **Citizen** for the old-age support ratio, because the pension system and
  the argument about it are about citizens.

The World Bank's `SP.POP.TOTL` agrees with SingStat's total to the person in
2024 and 2025 (6,036,860 and 6,111,175). That is the check that the two
"populations" are the same object; where they are not, the file says so.

**A census/rebase note.** The publisher's own footnote records a de facto
concept before 1990 and de jure from 1990. The window starts in 2006, so that
break is outside every plate, and no series here is drawn across it.

---

## 2. Fiscal years are not calendar years

Every SingStat public-finance table is labelled by the **starting year** of a
1 April – 31 March financial year. The column is therefore `fiscal_year`, not
`year`:

- `fiscal_year 2026` = 1 April 2026 to 31 March 2027;
- the publisher states that FY2026 is the **budget estimate**, FY2025 the
  **revised estimate**, and FY2024 and earlier **actuals**.

Three kinds of number share one column. A plate that draws FY2026 as an
outturn is wrong, and Phase B must mark it. Nothing here converts a fiscal
year to a calendar year: the conversion would invent four months of data and
would silently misalign this country against every calendar-year peer.

The IMF's general-government series is on **calendar** years and lives in a
different file (`fiscal/imf_general_government.csv`). The two are never joined
on "year" — that would put a 1 April–31 March ratio next to a calendar one and
make the seam land on whichever year had the bigger deficit.

---

## 3. Singapore's gross debt is not a debt burden

IMF `GGXWDG_NGDP` puts general-government gross debt at 165.8% of GDP in 2024
and the national end-2025 stock is S$1,292.4bn against GDP of S$789.5bn —
163.7% on the calendar basis, within two points on a different year basis.

The number is real and it is published. What it is not is a measure of
distress: the government issues Singapore Government Securities to hold the
CPF Board's liabilities and to build the reserves that generate the Net
Investment Returns Contribution, and it publishes no net-debt series on any
route probed. A gross ratio with no asset side, wiped across France or the
USA, reads as a debt crisis that does not exist. **The panel carries the
"gross, no offset" note or the line is a lie.**

The fiscal-year cash ratios tell the other half of the story: operating
revenue 16.3% of GDP, total expenditure 15.5%, overall position +1.9% in
FY2025, before the Net Investment Returns Contribution is added back.

---

## 4. There is no policy interest rate

MAS conducts monetary policy by managing a trade-weighted exchange-rate band
(S$NEER) — its slope, width and level — and not by setting a rate. The spine's
markets slot 1 is "policy rate vs inflation" and **this country has no such
quantity.**

The recorded decision, in `SOURCES.yaml meta.pending`:

- the slot stays visibly pending, or
- SORA (the Singapore Overnight Rate Average, published by SingStat in
  M700071) is drawn **labelled as a money-market benchmark**, never as a
  policy rate.

What must not happen: naming the 3-month SORA a "policy rate", or importing
the Fed funds rate because the S$ is managed against a basket that includes
the US$. Either would be a false statement about how this economy is run.

The 10-year yield (2.30% in 2025) is a genuine market series and fills markets
slot 2 normally.

---

## 5. Two definitions, both official, drawn twice

The atlas forbids splicing; Singapore supplies three cases in one country.

**Gini.** `M810361` prints **six** coefficients: before and after government
transfers and taxes, each on three equivalisation bases (per household member,
modified OECD scale, square-root scale). The two staged are the
per-household-member pair — 0.426 before, 0.359 after, in 2025 — and the
after-transfers figure is the one Singapore quotes as its headline. The gap
between them (6.7 points) is the redistributive effect of the transfers and
taxes, which is the interesting number and is invisible if only one is drawn.

Note also what the income base is: **employment** income including employer
CPF contributions, among **resident employed households**. It excludes
investment income and excludes households with no employed member. It is not
the same object as a SILC or a tax-file Gini, and the World Bank's harmonised
Gini has no Singapore row at all (`SI.POV.GINI` returns an empty series), so
there is no comparison line — an absence the plate must state rather than
fill.

**Household debt.** The national balance-sheet liabilities (`M700981`) are
51.6% of GDP at end-2025; the BIS harmonised credit aggregate (`WS_TC`) is
44.0%. Seven points apart, both correct, different perimeters (the national
figure includes HDB housing loans and non-bank lending the BIS aggregate
treats differently). Two labelled lines.

**Trade.** National accounts (goods *and* services, 178% of GDP) and customs
merchandise trade (S$739bn of exports, of which re-exports are the larger
part) are separate files and separate panels.

---

## 6. Security and mortality: denominators, coding and a preliminary year

**Denominators.** Both national rates divide by the **total** population of
the same year, because both counts cover everyone present:

- **Murder** is a recorded offence against anyone in Singapore. Verified
  against the publisher's own crime rate: its 2025 physical-crime rate of 341
  is exactly 20,857 cases over the mid-2025 total population of 6,111,175.
  The same basis reproduces the UNODC series **exactly** for 2011 (0.309 per
  100,000), which is the strongest available confirmation that the denominator
  is right.
- **Suicide** sits inside `M810131`, whose total reconciles with *all* deaths
  in Singapore (26,499 in 2025) rather than the resident subset (25,300). The
  same-basis check: 2020 gives 7.9 per 100,000 against WHO's 8.94, where a
  resident denominator would give 11.2 and no agreement at all.

**Murder is not intentional homicide.** It is a Penal Code category. The
UNODC series is drawn beside it, never substituted for it. The two happen to
agree in Singapore because the police count is what UNODC uses, and that is
worth knowing rather than assuming.

**Two coding breaks in the cause-of-death file.** Deaths to 2011 are coded to
ICD-9 and from 2012 to ICD-10 — the publisher's own footnote — so the cause
groups are not strictly comparable across 2012 and the seam is annotated, never
smoothed. Separately, **the publisher marks 2025 preliminary**, and the two
external-cause groups collapse in that year while every natural-cause group
holds steady:

| | 2023 | 2024 | 2025 |
|---|---|---|---|
| accidents, poisonings and violence | 873 | 917 | **536** |
| suicides | 434 | 441 | **256** |
| malignant neoplasms | 6,623 | 7,000 | 7,046 |
| circulatory | 8,705 | 8,457 | 8,621 |

A 42% fall in suicides in one year is not a public-health event; it is
coroner's cases still being assigned at the time of publication. **Do not
describe the 2025 suicide or accident count as a decline**, and if the panel
annotates anything, it annotates this.

**There is no COVID-19 row.** The publisher's broad cause groups predate the
ICD-10-COVID code, so pandemic deaths sit inside "diseases of the respiratory
system" and "infective and parasitic diseases" and cannot be separated without
microdata. WHO's GHO catalogue carries no general COVID death indicator for
Singapore. The mortality plate's COVID slot has no series (see
`SOURCES.yaml meta.pending`) and says so.

---

## 7. Prices and rates: one vintage, complete years only

`M213751` is the **2024-base** CPI and back-computes its whole history, so the
2006–2025 index is one coherent vintage and no rebasing seam is spliced in.
Inflation is the year-on-year change of the **calendar-year mean** of the
monthly index — not December-on-December. 2025 = 0.90%, which the IMF's
`PCPIPCH` independently gives as 0.9.

**Annual means and sums are taken over complete years only.** The fetcher
refuses a year with fewer than twelve monthly (or four quarterly) observations,
so 2026 — nine months of prices, nine months of exports, nine months of
reserves — does not appear as an annual figure anywhere. What 2026 does carry
is what is genuinely a point reading: the mid-2026 population (6,208,523), the
end-June 2026 unemployment rate (1.9%), and the mid-2026 pass-type shares. The
plate dashes the running year; the data never pretend it is finished.

This rule cost one convenience: the CPI panel's last point is 2025, not
September 2026. That is the correct trade — a nine-month mean sitting in a
column of twelve-month means is a comparison of unlike things.

---

## 8. Derived columns, and exactly how

Everything below is computed in `fetch/fetch_singstat.py` or in the promotion
step, and stated in the file's own header. Nothing is interpolated, carried
forward or zero-filled.

| column | formula | why it is safe |
|---|---|---|
| `real_growth_pct` | year-on-year change of `gdp_real_2015_chained_sgd_mn` | one vintage of one chained series; a rebasing cannot become growth |
| `inflation_pct` | year-on-year change of the calendar-year mean CPI | one vintage; complete years |
| `exports_pct_gdp`, `imports_pct_gdp`, `balance_pct_gdp` | national-accounts flows ÷ GDP, same table, same vintage | no splice, no second publisher |
| `liabilities_pct_gdp` | Q4 stock ÷ that year's GDP at current prices | same year, both from SingStat |
| `murder_per_100k`, `suicide_per_100k` | count ÷ mid-year **total** population × 100,000 | verified against the publisher's own crime rate and against UNODC |
| `total_debt_sgd_mn` | domestic + external debt, publisher's own lines | external debt is nil in every year of the window |
| `share_of_exports_pct` | market exports ÷ Total All Markets, same year | region rows aggregate markets and are never added to them |
| `net_migration_wb` | UN WPP model as the World Bank carries it | an estimate, labelled as one, in its own column |

Excess deaths — the spine's mortality slot 2 — is **not** computed here. The
spine defines it as the percentage above the 2015–2019 average of the crude
death count, and Singapore's death count is rising steadily with an ageing
population, so a 2015–2019 baseline would attribute most of the 2020–2024 rise
to the pandemic. It needs an age-standardised baseline to be honest, and that
is a Phase B decision with the evidence in front of it, not a number invented
in Phase A.

---

## 9. What is not drawn, and why

Full text with endpoints and failure modes is in `SOURCES.yaml meta.pending`;
this is the classification the repo requires.

**Does not exist (a finding, not a gap):**

- **No policy interest rate.** MAS targets an exchange-rate band (§4).
- **No official poverty line** and therefore no national poverty rate. The
  government publishes income deciles, ComCare caseloads and Workfare instead.
- **No statutory minimum wage.** The Progressive Wage Model sets sectoral
  floors; that is not a national minimum wage and is not converted into one.
- **No immigration or emigration flow series** on any route probed. What is
  published is a stock by legal status — citizens, PRs, non-residents by pass
  type — and that is what the migration file carries.

**Published but not reachable from this network:**

- **MAS's statistics API** serves an HTML maintenance page under HTTP 200 (or
  404 with an HTML body). That blocks the bank lending rate, the NPL ratio and
  MAS core inflation — credit slots 2 and 3 have no staged data. Retry is one
  fetch from an unblocked network.
- **Transparency International's CPI workbook** — S3 AccessDenied (403). World
  slot 3 stays pending.
- **data.gov.sg's catalogue** itself works; its Table Builder "adapted from"
  links do not (retired ids, saved views, and at least one name belonging to a
  different table). Table ids come from the publisher's sitemap instead.

**Coverage decisions by the publisher (not access failures):**

- **IMF general-government revenue and interest** are empty for Singapore on
  the DataMapper, and the Fiscal Monitor's revenue indicator has no SGP row,
  while expenditure, balance and debt do. Revenue is **not** derived as
  "expenditure minus balance": both are rounded separately and the subtraction
  would invent precision.
- **OECD COFOG (table 11)** returns `NoRecordsFound` for Singapore where the
  identical query returns 903 KB for France. Singapore is not an OECD member.
  The national ministry classification is staged and drawn in the lens; it is
  not relabelled as COFOG.
- **World Bank Gini**: no Singapore row.

**Obtainable but not staged in this phase:**

- **Straits Times Index** — Yahoo's chart API answers 200 with `^STI`
  metadata, so it is one fetch away. It needs the index history and that
  year's exchange rate reconciled on one vintage before it can be indexed
  2006 = 100 in US$, and it would be `official: false`. Stooq, the atlas's
  usual redistributor, is JavaScript-walled from this network.

---

## 10. Verification record

Every table is pinned to observations read off the live payload on
2026-10-25, so a silent revision or a re-pointed id fails the fetch instead of
changing a chart. The anchors, and the independent second source that agrees:

| claim | value | second source |
|---|---|---|
| real GDP growth 2024 | 5.34% (national chained) | IMF WEO 5.3 |
| real GDP growth 2025 | 5.03% | IMF WEO 5.0 |
| CPI inflation 2025 | 0.90% (2024-base index) | IMF PCPIPCH 0.9 |
| GDP per person 2025 | US$98,878 (national) | World Bank US$98,813.98 |
| total population 2025 | 6,111,175 | World Bank 6,111,175 (identical) |
| reserves end-2025 | S$526.3bn (Dec-2025; S$553.6bn by Sep-2026) | World Bank US$432.11bn |
| gross debt 2025 | S$1,292.4bn = 163.7% of GDP | IMF 165.7% (different year basis) |
| murder rate 2011 | 0.309 per 100,000 | UNODC 0.309 (identical) |
| HDI 2023 | 0.946 | HDR 2025 (the same file) |

Determinism, run in the lane on 2026-10-25:

- **online twice:** every `*_from_*.csv` byte-identical (md5 set unchanged);
- **offline with a warm cache:** byte-identical, exit 0;
- **offline with a cold cache:** exit 1 having written nothing.

The fetchers refuse to write when a table's metadata title differs from the
one pinned here, when a payload is not JSON, when a table has no rows, or when
an anchor moves — which is how a re-pointed id was caught in discovery
(`M450091`, cited by data.gov.sg, no longer resolves).

---

## 11. Seams to annotate in Phase B

1. **2008–09 and 2020** — the only two multi-quarter contractions in the
   quarterly series (`M015902`), banded in `country.yaml`. The annual series
   shows only 2020 as a negative year (+0.13% in 2009), which is why the
   quarterly series was fetched to date the bands.
2. **2012** — ICD-9 to ICD-10 in the cause-of-death groups.
3. **2025** — preliminary cause-of-death year; external causes incomplete.
4. **2011** — the national homicide series starts here (`M890891`); earlier
   years are blank, not zero.
5. **FY2026** — budget estimate, not outturn, in the fiscal-year file.
6. **2020** — the annual bar reads −3.61%, which is mild for a year whose
   second quarter fell 12.1% quarter-on-quarter: the recession was two
   quarters inside a year that began and ended with growth. The bar and the
   band tell different halves of the same story and both are drawn.

---

## 12. Phase B: what the twelve plates actually draw

Written with the plates, 2026-10-25. Every panel below reads a committed
CSV; `provenance.json` records which file each plate opened, and
`tests/test_plates.py` recomputes each quoted figure from those files.

### The three slots that do not fit the shared scales

`PLATE_SPINE.md` rule 6 puts one atlas-wide range per canonical slot in
`core/spine.py`, and a country may not extend it. Three staged series
leave it. Each is reported here rather than clipped, rescaled or silently
dropped, and each stays visibly pending with the extent on the panel and
the reason in `ui.json`:

| slot | shared range | Singapore extent | what the plate does |
|---|---|---|---|
| `trade.exports_imports` | 0–100% of GDP | exports 228.99%, imports 208.33% (2008) | pending; both lines in the trade lens, own axis |
| `security.homicide` | log 0.1–100 | 0.068 per 100,000 (2023) | pending; count annotated, floor request noted |
| `migration.net` | −10 … +40 per 1,000 | +41.9 (2007), −25.6 (2020) | pending; drawn in the migration lens, own axis |

`mortality.excess_deaths` is a fourth, smaller case: the derived series
starts at −20.8% in 2006 against a floor of −20. The slot is drawn, but
only from the baseline period (2015–2025), where the statistic is
meaningful anyway; the panel's foot states the 2006 value and the shared
floor, and `ui.json` carries the same sentence. Widen that floor to −25
and the whole series can be drawn.

### Denominators, one per claim

| what | divided by | why | check |
|---|---|---|---|
| GDP per person | total population | what is produced, by everyone present | national 98,878 vs World Bank 98,813.98 in 2025 |
| crude birth/death rates, TFR | resident population | the publisher's own vital rates | resident deaths 25,300 ÷ 4,204,515 × 1,000 = 6.0 ✓ |
| natural increase | resident population | births minus deaths of residents | 2,093 ÷ 4,204,515 × 1,000 = 0.50 ✓ |
| murder, suicide, road deaths, recorded offences | total population | the counts cover everyone present | 2025 suicides 256 ÷ 6,111,175 × 100,000 = 4.19 ✓ |
| foreign citizens | total population | total − citizens, both from one table | 2,450,492 ÷ 6,111,175 = 40.1% ✓ |
| household debt (national) | same-year GDP | a year-end stock over that year's GDP | S$1,292,369.5mn ÷ S$789,529.2mn = 163.7% ✓ |
| net migration (lens) | total population | the UN estimate is of everyone present | +16,892 ÷ 6,111,175 × 1,000 = 2.76 ✓ |

The same count read over the other population is drawn nowhere: a reader
who wants deaths per 1,000 of everyone present gets it as a footnote
(4.3), never as a second unlabelled line.

### One value promoted from a sidecar into a curated file

Phase A staged whole-economy investment as a World Bank comparator only in
the fetch sidecar `macro/gfcf_from_wb.csv`, which a plate may not read
(`tests/test_sources.py`). The series was reviewed against the sidecar,
whose values it reproduces exactly, and promoted on 2026-10-25 into
`macro/economy.csv` as `gfcf_pct_gdp_wb` — beside the file's other
harmonised `_imf`/`_wb` columns, which are kept apart from the national
series in the same way. `SOURCES.yaml` records the promotion. Nothing
national was re-derived: the column is the World Bank's NE.GDI.FTOT.ZS,
and the spending plate's foot says it is a comparator rather than a
national-accounts series.

### Derived columns in the plates (not in the files)

- `excess_deaths_pct` = deaths ÷ mean(2015–2019 deaths) − 1, ×100. One
  vintage, one table; the baseline is unadjusted for age and the panel
  says so, because Singapore's death count rises every year with its age
  structure.
- Gini is published 0–1 and drawn at 0–100 because the spine's slot is
  `Gini, 0–100`. Multiply by 100; nothing else changes.
- natural increase per 1,000 = `natural_increase_residents` ÷ mid-year
  resident population × 1,000.
- national gross debt ratio = `total_debt_sgd_mn` ÷ that year's
  `gdp_current_sgd_mn` × 100, both from SingStat, both end-year/calendar.
  It is drawn beside the IMF's calendar general-government line, labelled.
- foreign citizens = (`population_total` − `population_citizen`) ÷
  `population_total` × 100. This is a **legal-status** share, not a
  foreign-born share, and the panel title says "Foreign citizens".
- recorded offences per 100,000 = police count ÷ mid-year total
  population × 100,000.

### Seams, and how each is drawn

1. **2012, ICD-9 → ICD-10** (section 11.2). Three causes, each as two
   segments with a gap and a dotted rule between them (`events.MARKS["icd"]`),
   plus the footnote: dotted is the ICD-9 coding, solid the ICD-10 one.
   Never one joined line.
2. **2025, preliminary causes** (11.3). The suicide line is split at 2024 so
   2025 is dashed and labelled "preliminary"; the mortality lens carries the
   same note. The words "decline" and "fell" do not appear next to either
   2025 external-cause number, and `test_plates.py` asserts the wording.
3. **Fiscal years** (11.5). The national cash series (1 April–31 March,
   labelled by its starting year) is *not* drawn on any calendar-year panel
   and no calendar-year series is drawn on it. The fiscal card's
   gross-debt/balance panels are IMF calendar years; the national budget
   appears only as the labelled second line of the debt panel, where the
   ratio is the lane's own derivation (above).
4. **2011** (11.4). The homicide and police series start in 2011 and the
   panels are blank before it — no zero, no extrapolation. Homicide is
   pending for the scale reason, not for the hole.
5. **2020** (11.6). The growth bar reads −3.61% and the band spans
   2020.0–2020.5; both are drawn and a note explains that the year began
   and ended with growth.

### What is deliberately not drawn, and where the reason lives

Seventeen of the forty-eight panels are pending. Each carries its route on
the panel (two locales), an entry in `ui.json` `unavailable`, and the
manifest's `meta.pending` note with the endpoint and the failure mode:

fiscal 1 and 4 (IMF revenue and interest coverage), spending 1, 2 and 4
(no COFOG; no clean two-way social split; no government GFCF), trade 1
(scale), markets 1 and 4 (no policy rate; STI not staged), credit 2 and 3
(MAS HTML-200), people 2 and 3 (no official poverty line; no statutory
minimum wage), world 3 (TI 403), security 1 (log floor), mortality 3 (no
COVID line), migration 1 and 2 (no flow series; scale).

### Currency and number forms

The pages and plates use the SGD forms core provides for this lane —
en `S$3,297bn`, pt `S$ 3.297 bi` — and the price/income series stay in
S$ with the unit in the panel title. No S$ figure is converted to US$
anywhere in the plates except the reserves, where the World Bank's own
US$ series is drawn (one publisher, no cross-rate invented here).
