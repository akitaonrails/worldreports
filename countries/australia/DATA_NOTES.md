# Australia — what the numbers mean

The research record is [DISCOVERY.md](DISCOVERY.md); the manifest is
[SOURCES.yaml](SOURCES.yaml). This file carries the judgement calls the
plates will depend on, written before any plate exists.

## Calendar years, fiscal years, and the one rule that keeps them apart

The atlas draws annual series on a calendar-year axis. Australia's official
statistics are published on **both** bases and the difference is not
cosmetic:

- **Calendar years** — the CPI, the labour force, births, deaths, recorded
  crime, net overseas migration, population, the World Bank and the IMF's
  WEO growth series all run January–December.
- **Fiscal years, July–June** — the national accounts' annual tables, the
  Government Finance Statistics (cat. 5512.0), the Commonwealth budget,
  and the IMF's *fiscal* rows for Australia. The Fund labels the year by
  the year it **ends**: its "2025" is FY2024/25.

Everything in `data/macro/`, `data/trade/`, `data/spending/investment.csv`,
`data/markets/`, `data/credit/`, `data/people/`, `data/demography/`,
`data/security/`, `data/mortality/` and `data/migration/` is **calendar
year**. `data/fiscal/fiscal.csv` and the ABS GFS sidecars are **fiscal
year**, carry the FY label in the `year` column and the period name in the
manifest and the notes, and are never drawn on a calendar-year axis
without saying which is which.

### The annualisation rule, stated once

The ABS publishes the national accounts quarterly. The atlas draws annual
values, so they are built from the quarters by one of two rules, and the
rule is part of the number's meaning:

| kind | series | rule |
|---|---|---|
| flow | GDP, GFCF, exports, imports, births, deaths, arrivals, departures | **sum of the four calendar quarters** |
| rate | CPI index, unemployment rate | **mean of the four quarters / twelve months** |
| stock | population | **the 30 June reading (Q2)** |

A year with fewer than four quarters is **not emitted at all**: 2026 has
two quarters in the ABS gateway and is not in any annual column. This is
why the CSV stops at 2025 while the plate window runs to 2026 — the plate
draws the running year from the quarterly sidecar only if a Phase B agent
asks for it, and nothing is forward-filled.

The quarterly source is the **original** (not seasonally adjusted) series,
because the annual sum of original quarters is the year, whereas the annual
sum of seasonally adjusted quarters is the year plus whatever the seasonal
adjustment did to it. Two consequences worth knowing:

- The calendar-year chain-volume sum is not byte-identical to the ABS's own
  *fiscal*-year annual chain-volume estimate. It differs in the second
  decimal of growth. It is the same concept computed on the calendar
  alignment the atlas uses, and it is checked against the Fund and the
  Bank below.
- Quarter-on-quarter growth from original terms is dominated by the March
  quarter's seasonal dip (every Q1 shows −6% to −8%), so it cannot be used
  to date anything. The recession bands are therefore dated from the
  **seasonally adjusted** series, which is fetched for that purpose only.

## Australia's growth series and the trap in the World Bank's

The World Bank's `NY.GDP.MKTP.KD.ZG` for Australia is on a **fiscal-year
basis labelled by the year the fiscal year ends**. Its 2020 value is
−0.13%, which is FY2019/20; Australia's *calendar* 2020 fell 2.10%. The
series looks plausible and is wrong for a January–December axis. It is not
used anywhere in this country, and the manifest says so. The cross-check
line is the IMF WEO `NGDP_RPCH`, which is calendar: 2020 −2.07, 2022
+4.27 against the ABS −2.10 and +4.21.

## Two publishers, one idea: the fiscal chapter

`data/fiscal/fiscal.csv` carries **eleven columns from three publishers**
and the differences between them are the chapter's substance:

| column | publisher | basis |
|---|---|---|
| revenue, expenditure, balance, primary balance, gross debt | IMF Fiscal Monitor (general government) | accrual, July–June, FY label |
| `gfs_*` columns | ABS GFS 5512.0 (all levels of government) | accrual, July–June, FY label, FY2015/16+ |
| `interest_pct_gdp` | **derived** | see below |

For FY2024/25 the two publishers agree on revenue to 0.14 points (IMF
36.67%, ABS 36.81% of GDP) and disagree on expenditure by 2.4 points (IMF
39.56%, ABS 37.11%). The difference is a definition: the Fund's
expenditure includes net acquisition of non-financial assets, the ABS's
"expenses" line does not, and the ABS's own net lending/borrowing row is
the comparable one. Both lines are drawn; neither is spliced into the
other; the plate says which is which.

**Interest paid** is the one slot neither publisher answers directly. The
Fund's key-indicator set has no interest line, and the World Bank's
`GC.XPN.INTP.RV.ZS` is interest as a share of *revenue*, not of GDP. The
column is therefore a derivation, and the derivation is in the file:

    interest_pct_gdp = GC.XPN.INTP.RV.ZS ÷ 100 × revenue_pct_gdp

both for the same fiscal-year label. It runs 2006–2022, because the World
Bank series stops in 2022. From FY2015/16 the ABS's own interest row sits
beside it (`gfs_interest_pct_gdp`, 1.47% of GDP in FY2015/16 rising to
1.71% in FY2024/25); the derived line reads 0.5–0.9% over the same years
on the Bank's narrower concept. A reader sees both; a chart shows the
break rather than an average of two definitions.

## The ABS's COFOG is ten years; the OECD's is nineteen

The national functional classification `5512.0` current vintage covers
FY2015/16 onwards only. A spending plate on a 2006–2026 axis would be 40%
empty, so the canonical series is the **OECD's COFOG** (calendar years,
2006–2024, general government, accrual), with the ABS table staged as a
cross-check sidecar. The two agree within about a point on every group for
the years they overlap; the OECD puts social protection at
10.38% of GDP in calendar 2016 and the ABS at 10.00% in FY2016/17; health
is 7.89% against 7.03%.

The seven spine groups are built from the ten COFOG divisions, and one
ABS-presentation quirk is handled explicitly: the ABS prints **Transport**
as its own row, outside "Economic affairs", and the eleven rows add up to
its published total. The atlas follows the publisher, so
`economic_affairs` is "Economic affairs + Transport", and the fetcher
asserts that the eleven ABS rows sum to the ABS's own total before it
writes anything.

The COFOG ratio needs a GDP denominator the OECD slice does not carry for
Australia, so it is the ABS's calendar-year GDP at current prices — the
same SNA concept, the same country, a different publisher. A ratio across
two publishers is a smaller error than a numerator on one vintage divided
by a denominator on another, and the note on the plate says which GDP.

## Population denominators

Everything per-person uses **ABS estimated resident population at 30 June
of the same year** (`demography/population.csv`): deaths, births, net
overseas migration, homicide, road deaths, COVID deaths, excess deaths.
This is the population the ABS itself divides by, so its published rates
and the atlas's recomputed ones agree.

Two things that are not the same population and are never mixed:

- **ERP at 30 June** (a stock at a moment) and the **Census count** (every
  five years, with a post-enumeration adjustment). ERP is revised after
  each census; the June 2021 quarter carries the 2021 Census rebase, which
  shows as a step in the population index and is a revision, not a year of
  extraordinary growth.
- **Residents** and **overseas-born residents**: the overseas-born share
  is total ERP minus the Australia-born ERP (`ERP_COB`), not a census
  percentage carried forward.

## Migration: flow, stock and program are three different things

`data/migration/migration.csv` carries NOM arrivals, NOM departures, the
net, and the overseas-born share. The definitions that matter:

- **NOM is not a count of visas or of border crossings.** A person is a
  net overseas migrant if they are in Australia 12 of the next 16 months
  (or absent 12 of 16). The ABS revises the last two years as the 16-month
  window closes; 2024's +329,940 is a final figure and 2025 does not exist
  yet.
- **The Migration Program** (Home Affairs permanent additions, ~185,000 a
  year) is a *program outcome*, an administrative count of visas granted,
  and is not comparable with NOM arrivals (which include temporary
  entrants and returning citizens and are measured after the fact). It is
  not drawn (SOURCES.yaml `meta.pending`): the lens panel is optional and a
  program count on the same axis as NOM would be the exact error the
  atlas's migration notes warn about.
- **Overseas-born share** is a stock from a different question (who is
  here) and its own panel.

## Security and mortality: the same death, four counts

`security/homicide_per_100k` is the **police-recorded** victimisation rate
(ABS 4510.0), counted where the offence occurred. `mortality/` comes from
**death certificates** (ABS 3303.0), counted where the person lived and by
underlying cause. The two counts of homicide differ in both directions and
neither is wrong; they are in different chapters, on different definitions,
and are never joined.

- **Suicide**: the WHO's age-standardised rate (`MH_12`, 2006–2023) is the
  canonical line. The ABS's own suicide table starts in 2015 and reports
  age-specific and crude rates, so using it would truncate the panel by a
  decade. The WHO rate is the harmonised cut of the same underlying
  registration data. 2024–25 are blank.
- **Road deaths**: BITRE's individual fatality record (ARDD), count over
  ERP. The BITRE host itself is unreachable and the data.gov.au mirror
  stops at October 2023, so the line ends in **2022** — the last complete
  calendar year in the mirror. WHO's modelled estimate would extend it and
  is a different measurement (a model, not a count), so it is not drawn.
- **COVID-19**: deaths where COVID-19 was the **underlying cause**
  (U07.1–U07.2), from one vintage of the Causes of Death release (2024),
  over the same year's ERP. "Deaths involving" COVID is a much larger
  number and a different question; it is not in this file.
- **Excess deaths**: the crude death rate against its own **2015–2019
  mean** (6.56 per 1,000). The baseline is the measurement: against a
  2015–2019 average the pandemic years are outside the average; against a
  long-run trend the 2022 peak would look smaller. 2022 reads +11.9%,
  2023 +4.9%, 2024 +4.9%, 2025 +4.0%.

## Credit: two NPL definitions, and a panel that is not drawn

APRA changed its asset-quality measure in 2022. The CSVs carry both:

- `npl_impaired_pct` — impaired facilities ÷ loans and advances,
  September 2004 to December 2021, 0.3–0.5%;
- `npl_nonperforming_pct` — non-performing ÷ loans and advances, 2022
  onwards, about 1.1% at December 2025.

The step from 0.3% to 1.1% is mostly the definition: the new measure adds
facilities 90+ days past due. Drawn as one line it would be a fabricated
credit event. Two columns, a break, a note.

**The household lending rate is not drawn.** The RBA publishes it (F5) and
every path on `rba.gov.au` answers 403 to this network; the IMF's IFS
lending-rate series stops in 2019; APRA publishes no rate. A slot with a
lending rate that stops seven years before the axis ends, or with the IFS
"average bank rate" mislabelled as a new-mortgage rate, would be worse than
a slot that is honestly empty. The credit plate therefore has three
panels and a pending entry that names the endpoint.

## The currency, the index and the dollars

- Levels in `fiscal/`, `trade/` sidecars and `country.yaml` are **AUD**;
  ratio slots are % of GDP; the two US$ slots (GDP per person, GDP at
  current prices, reserves) are US$ because that is what the spine compares.
- The currency index is **2006 = 100, rising = stronger**, built as
  2006 AUD/US$ ÷ year AUD/US$ from the World Bank's annual-average rate.
  The same vintage converts the minimum wage, so a reader cannot get two
  different dollars on one page.
- The equity panel is the ASX 200 **in US$**, annual mean of monthly
  closes divided by the same annual-average FX, rebased on its own 2006
  mean. Yahoo is a redistributor: `official: false`, said on the plate.

## Price levels and rebasing

The CPI index in `macro/economy.csv` is the ABS's **linked** all-groups
series, which is why it can be compared across the 2012, 2014 and
September-2017 weighting rebases (the ABS links the history). The index is
not used as a level anywhere; only its year-on-year change is drawn, and
the annual mean of the index is the intermediate step, stated here so that
a later agent does not treat the mean of a quarterly index as a published
annual index.

## What is not drawn, and why

Each of these has a `meta.pending` entry with the endpoint and the failure:

1. **RBA statistical tables** (cash rate direct, F5 lending rates, F2
   yields, F11 FX) — 403 on every path including `robots.txt`.
2. **Household lending rate** — the chain of blocked/truncated routes
   above.
3. **Road deaths 2023–2025** — BITRE host resets/times out; mirror stops
   at October 2023.
4. **A national poverty rate** — the ABS publishes no official line; the
   World Bank's $8.30 line is empty; the domestic 50%-of-median estimate is
   a research compilation, cited in the notes, not drawn.
5. **CPI corruption before 2012** — TI's retired 0–10 scale is not in the
   2025 workbook and TI declares it incomparable.
6. **Permanent Migration Program additions** — a program count, not an
   arrival; PDF-only on the Home Affairs portal; a lens slot, not a
   canonical one.

## Reproducing this

```sh
python3 -I fetch/fetch_abs.py          # ABS SDMX: accounts, CPI, LF, ERP, NOM, births, deaths, exports
python3 -I fetch/fetch_abs_tables.py   # ABS xlsx: GFS/COFOG, recorded crime, causes of death, HIES Gini
python3 -I fetch/fetch_comparables.py  # World Bank, IMF FM/WEO, UNDP, WHO, BIS credit, TI
python3 -I fetch/fetch_oecd.py         # OECD COFOG, long-term rate, minimum wage
python3 -I fetch/fetch_markets.py      # BIS policy rate, Yahoo equity
python3 -I fetch/fetch_financial.py    # APRA NPL, BITRE road deaths
```

`fetch_abs.py` must run before `fetch_abs_tables.py` and `fetch_oecd.py`
(both read the quarterly GDP sidecar for a denominator), and
`fetch_comparables.py` before `fetch_oecd.py` and `fetch_markets.py` (both
read the World Bank FX column). `make C=australia fetch` runs them in the
directory's glob order, which is that order; each dependent fetcher refuses
to guess a denominator and exits with the reason if its input is missing. Every fetcher writes `*_from_<source>.csv`
sidecars and **no** curated file: the promotion from sidecar to
`data/**/<name>.csv` was done by hand against these notes.

## What Phase B promoted, and why (2026-10-25)

Two values that already existed in reviewed sidecars were promoted into
curated files so the spine's canonical panels could be drawn from published
data rather than left pending. Both were checked against the publisher's own
presentation before the promotion, and neither is a new measurement.

- **`trade/destinations.csv`** — the four largest merchandise-export
  destinations of 2025 (China, Japan, Korea, the United States) as a share of
  total goods exports, 2006–2025, from the ABS MERCH_EXP table already staged
  as `destinations_all_from_abs.csv`. The denominator is the ABS's own "Total"
  row of the same table. The four partners are ranked **once, on 2025**, and
  held fixed for the whole back-series: a line moves because Australia shipped
  a different mix, never because the ranking changed under it. 2025 reproduces
  `destinations_2025.csv` exactly (China 33.59%, Japan 11.60%, Korea 7.87%,
  United States 7.67%). It is the customs/merchandise basis and does not add
  up to the national-accounts exports ratio on slot 1.
- **`security/security.csv`** — two count columns, `homicide_victims` and
  `road_deaths`, the numerators the published rates were computed from (ABS
  recorded crime; BITRE ARDD). The rates stay canonical; the counts are drawn
  only in the security lens, where a count answers the question a rate cannot
  (how many people, in a country whose population grew 35%).

## How the plates draw the fiscal year

The fiscal chapter is the one place the plates leave the calendar grid. Every
fiscal series is July–June and its `year` column is the year the year **ends**
(the Fund's convention, confirmed against the ABS in the section above), so a
value is drawn at its year's midpoint, `year − 0.5` — FY2024/25 at 2024.5 —
which is where that year actually sits between the calendar years either side
of it. Each fiscal panel carries an "FY" label, and the axis is the atlas's
shared 2006–2026 axis: the fiscal lines must register horizontally with every
other country's fiscal plate, because the viewer wipes one over another.
Nothing calendar-year is ever drawn on that plate.

## What the plates leave pending, and where the proxy sits

- **Credit slot 2 (household lending rate)** is a pending panel: the RBA's F5
  table is blocked, IMF IFS ends in 2019, and APRA publishes no rate. The
  panel says which endpoint is missing; three other panels carry the chapter.
- **Road deaths** stop in 2022 and the panel says so on its face. The rest of
  the axis is a hole, not a zero.
- **Poverty** is drawn as the World Bank's US$4.20-a-day line, labelled as the
  international line, because no national poverty rate exists: the ABS
  publishes none and the domestic 50%-of-median figure is a research
  compilation. The panel and the page both say this; the panel does not
  pretend the proxy is the national measure.
- **Corruption Perceptions Index** starts in 2012. TI's retired 0–10 scale is
  not comparable and the 2026 workbook does not carry it; the panel says where
  the line begins and why.
- **The Migration Program lens is not drawn.** Home Affairs publishes the
  program outcome as PDF and HTML report tables, not as a machine series, and
  a visa-grant count on a NOM axis would be the exact error this file warns
  about. The migration lens draws net overseas migration in persons instead,
  labelled as a count of the same NOM series the canonical panel divides.
