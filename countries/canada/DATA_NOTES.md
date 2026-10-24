# Canada — data notes

What these sources were like to work with, and the judgement calls a reader
of the plates should not have to reverse-engineer. `SOURCES.yaml` carries
the per-file caveats; this file carries the ones that cross files.

---

## The seven national chapters, and the Statistics Canada outage

Statistics Canada's data platform (`www150.statcan.gc.ca`) served an
outage page under HTTP 200 — not an error code, an HTML apology — for
every WDS endpoint from at least 2026-10-22 02:40Z. It answered a probe
again the same day, but no fetcher was written against it during this
lane. The chapters StatCan publishes — the economy, trade, people,
demography, security, mortality and credit — are therefore built from the
harmonised international versions of the same statistics: World Bank WDI
(national accounts, CPI, UN population components, UNODC homicide), the
IMF (WEO debt, GFS/COFOG, IMTS trade, financial soundness), the OECD
(income distribution, minimum wages, cause-of-death registrations,
general-government investment), UN DESA, WHO and the BIS. Every panel
names its publisher on its face, the harmonised series stays canonical,
and `HANDOFF.md` maps the slots that take a labelled Statistics Canada
line beside it once a fetcher exists. No StatCan number is typed into
`plates.py`.

A standing trap for that fetcher: the outage page arrived under HTTP 200,
so it must check the payload shape before caching, or it caches an error
page that survives the retry that would have fixed it. The existing
fetchers already do.

---

## The Statistics Canada pass (the national line is staged)

The platform answered again on 2026-10-22 and `fetch/fetch_statcan.py`
now pulls it: twelve cubes verified against `getCubeMetadata` (title,
CURRENT status, CANSIM id and start year asserted before any data is
read), full-table zips shape-checked (zip magic bytes and the expected
CSV member) before caching. The sidecars are `*_from_statcan.csv`
beside each harmonised file, and the curated national series are the
`*_statcan.csv` files: economy, trade, people (Gini, low income),
demography (population, fertility, components), security, mortality and
credit. No plate reads any of them yet — the switch is an
integration-chapter step (the plan is in `HANDOFF.md`), and the
harmonised series stays canonical until a plate names both lines.

**Candidates the handoff listed that failed verification and what
answered instead.** A PID that resolves to a different statistic is a
wrong chart waiting to happen, so every candidate was checked live:

| handoff candidate | what it actually is | used instead |
|---|---|---|
| 36-10-0222 | provincial/territorial GDP | 36-10-0699 (Canada annual) |
| 12-10-0011 | monthly customs goods trade | trade lives in 36-10-0699 — the trade slots are goods **and services**, national accounts |
| 11-10-0190 | income levels table | 11-10-0134 (the Gini cube) |
| 13-10-0386 | coroner-investigated deaths | the MBM rates live in 11-10-0135 |
| 35-10-0177 | the whole UCR violation file | 35-10-0068 (the homicide table) |
| 36-10-0639 | household credit in dollars | 38-10-0235 (debt to disposable income) |
| 17-10-0005 | July 1 estimates by age and sex | 17-10-0009 (quarterly demographic estimate) |

Verified but left for their chapters: 33-10-0163 (monthly average FX —
the markets 2006-07 fix), 17-10-0121/0023 (the non-permanent-resident
stock — migration's missing piece, only from 2021), 10-10-0005 (CCOFOG
— spending's national classification, not COFOG as the OECD knows it).

**Conversions, in one place.**

- CPI inflation (`macro/economy_statcan.csv`) is the year-over-year per
  cent change of the published annual-average all-items index
  (2002=100). The cube publishes the index level; the change is
  arithmetic, done at curation, and the sidecar keeps only levels.
- Trade % of GDP divides current-dollar exports and imports of goods
  and services by current-dollar GDP, all from cube 36-10-0699 in one
  fetch pass, so the ratio can never mix two vintages. Cross-check:
  the World Bank's 2019 figures reproduce StatCan's own to a hundredth
  of a point — the WB line is this same statistic redistributed.
- The crude death rate is **not staged**: StatCan publishes no national
  series for it. Integration divides the deaths in
  `social/components_statcan.csv` by the July 1 population estimate.
- Quarterly credit ratios (debt to disposable income, debt service) are
  annualised by the house convention — Q4 value, mean of published
  quarters, and the quarter count; StatCan's quarters are referenced by
  their starting month, so Q4 is the October reference.
- Component per-1,000 rates divide a July 1–June 30 count by the July 1
  population of the same period start — both from the same vintage of
  the demographic estimates.

**Definition pairs the plates must keep as two lines.** The World Bank
GDP, CPI, trade, population, birth/fertility rates and death counts
reproduce StatCan's own numbers with small redistribution differences —
same statistic, two publishers, still never spliced. The LFS annual
unemployment (not seasonally adjusted, 5.7 in 2019) and the ILO
modelled estimate (5.69) coincide by calibration, not identity. The
MBM exists on two bases — 2018-base (2015-2023) and 2023-base
(2020-) — as two columns that no plate may join. Household debt appears
as BIS credit over GDP (~104% in 2019) and StatCan credit-market debt
over disposable income (~177%): different denominators, both correct.
Debt service appears as the BIS modelled ratio (13.7) and StatCan's
actual payments (14.95). Homicide appears three times: police-reported
(253-0001, 2.10 per 100k in 2021), UNODC's harmonised intentional
homicide (2.08), and death-registered assault (497 deaths in 2021,
inside `mortality_statcan.csv`). Each pair is two labelled lines.

## The un-banded 2015 contraction

The 2015 oil-price shock met the mechanical two-quarter definition of a
recession — GDP fell in Q1 and Q2 — and is argued about to this day:
employment never fell, and the Bank of Canada declined to call it a
recession. `country.yaml` bands only 2008-09 and COVID-19; 2015 appears as
an event on the plates where it matters, not as a band across all of them.
A band is a claim that every series on every plate turned on it, and for
2015 that claim is contested.

## Three different Canadian debts

All three are correct and all three get quoted as "Canada's debt":

- the federal **accumulated deficit** (C$1.27tn in 2024-25) — what budget
  documents call "the federal debt";
- federal **net debt** (C$1.39tn) — total liabilities minus financial
  assets, a different quantity again;
- **general-government** debt on the IMF's basis — all levels of
  government plus the CPP/QPP — which reads **111.3%** of GDP gross and
  **12.5%** net in 2024.

The net figure is low because it nets off the assets of the Canada and
Quebec Pension Plans, which most G7 members do not hold in that form. The
canonical fiscal debt panel therefore draws only general-government gross
debt. Net debt and the federal accumulated deficit remain documented source
context; the latter's C$ level is quoted in a note but neither is overlaid on
the gross-debt axis.

## The fiscal-year convention

Everything in `fiscal/` is the **federal** government on fiscal years,
April to March, and `fiscal_year` holds the *starting* year: 2024 is
2024-04-01 to 2025-03-31. The IMF's general-government lines in the same
panels are **calendar** years — that is what makes them comparable across
the G7 and not with the federal line. To keep both honest on one axis,
federal points are plotted at their fiscal midpoint, a quarter-year right
of the start year (`FY_SHIFT` in `plates.py`), and the recession bands
fall where they actually fell against either convention. Every line is
labelled with the basis it is on.

The actuarial split in `transactions_pct_gdp.csv` exists only from 2008-09:
net actuarial losses became a separate expense line in 2019-20 with only
2008-09 onward reclassified, and the discount-rate methodology changed in
2017-18. The empty cells before 2008-09 are correct and are never
back-filled from the undivided balance.

The pollution-pricing proceeds are omitted from the revenue file: they are
returned to Canadians and appear as both a revenue and an expense, so
counting them in a revenue panel overstates the take by its own size. The
federal carbon levy was removed on 1 April 2025.

## The exchange-rate break

The Bank of Canada retired the USD noon rate on 2017-03-01 and replaced it
with a single indicative rate published at 16:30, computed differently.
January to April 2017 exists on both, which is what makes the break
measurable rather than asserted. The noon series begins in May 2007, so
2007 is an eight-month window and 2017 a four-month one — both are left
blank on the Bank of Canada segments, with the coverage in the `*_months`
columns, because either presented as an annual average lands inside the
plausible range and nothing downstream would catch it. **2006 and 2007
are covered by the Federal Reserve's H.10 cross rate**
(`markets/usdcad_h10.csv`, fetch/fetch_spine.py): the only annual averages
that span the start of the window, and the currency slot indexes all
three series on that H.10 2006 average (=100) so the base year is never
borrowed from a segment that does not cover it. The panel draws the index
rising = a *stronger* Canadian dollar — inverted from the C$-per-US$
quotes underneath, and the panel title says so.

The policy rate comes from the monthly static table
(`STATIC_ATABLE_V39079`), not from `V39079` itself, which Valet carries
only from April 2009 — a plate drawn from it would open at 0.25% with the
whole 2008 easing missing in front of it.

## The IRCC files

The permanent-resident and study-permit open data **begin in 2015**. They are
policy subsets retained in the migration lens, not substitutes for the
canonical gross immigration and emigration pair, which remains pending.
Every cell is
rounded to a multiple of five (all 19,503 of them; IRCC labels the files
"not for calculations"). Nationally it is nothing — 2024 sums to 482,960
against a published 483,390 — but a small country of citizenship is
published as zero or five, so the composition panel stays far above that
floor. Citizenship, not country of birth or of last residence: the three
give different answers and are regularly quoted as one.

The study-permit series is a **flow** — permits signed in the period — not
the stock of students present, which is several times larger and belongs to
StatCan's non-permanent-resident estimate (table 17-10-0040, quarterly).
That estimate is the missing piece of the migration story: most of the
2023-24 population growth of about 3% a year — unmatched in the G7 — was
non-permanent residents who never appear in the admissions file at all.

Statistics Canada's household-debt-to-disposable-income series is also kept
in the reviewed source files, but not drawn on the canonical household-credit
axis, which is debt as a share of GDP. The two denominators are not comparable.

## The comparables layer

The World Bank and UNDP series are harmonised cross-country readings,
marked `official: false`. While Statistics Canada is offline they stand in
as the national readings for the seven chapters above — never spliced
into a StatCan line when one arrives, and every panel names the publisher.
The World Bank's Gini is derived from the Canadian Income Survey under the
Bank's own income definition and is not Statistics Canada's own Gini; the
people plate draws it beside the OECD's reading, two labelled lines, and
neither is presented as Canada's official figure. The HDI is one vintage
throughout — the Human Development Report recomputes the whole back-series
at each methodology change, so a trend assembled from successive annual
reports would be partly an artefact of the reports.

## Conversions, and the numbers the plates compute

- The migration and demography rates are per 1,000 people: IRCC flows and
  the UN net-migration estimate divided by the World Bank mid-year
  population (`international/population.csv`, SP.POP.TOTL) — mid-year
  because it is the one population vintage every numerator can share.
  Admissions are calendar-year counts; the panel's partial-year rule
  drops the running year rather than drawing it.
- The minimum-wage panel converts the OECD employment-weighted average of
  the provincial minimums: annual C$ ÷ 12, at the H.10 annual average
  rate. Canada has no single national minimum; the panel says so.
- Equities are converted monthly, not annually: each month's TSX close is
  turned into US$ at that month's H.10 average before the annual mean of
  month-end closes is taken, which is why the 2014–15 currency slide sits
  inside the US$ index.
- Excess deaths are raw registrations against the 2015–2019 mean of
  deaths, with no population or age adjustment — and the panel's footnote
  says so, because a country adding a million people a year would print a
  positive excess with no mortality event at all.

## What is still pending even so

- The national line switch on the plates: the StatCan series are
  fetched, curated and manifest-listed (see the pass above), but no
  plate reads them yet — the panel footnotes still say the national
  line is pending. The switch plan is in `HANDOFF.md`; it is a redraw
  step, not a data step. The markets 2006-07 currency hole (33-10-0163)
  and the non-permanent-resident stock (17-10-0121, 2021 on) stay open
  for their chapters.
- The S&P/TSX composite has no official publisher, so the markets plate
  draws the Yahoo redistributor feed — annual mean of month-end closes,
  labelled *not an official statistic* on the panel itself rather than
  left out. A revision at Yahoo moves a plate; that is the price, and the
  sidecar file is what a diff would catch.
- Transparency International's CPI is drawn on the world plate from 2012
  only: the older 0–10 scores are not on the current 0–100 scale and no
  pre-2012 point has been conjured to lengthen the line.
- IRCC's admissions-by-principal-province file (ODP-PR-PT_IMMCAT) is
  declared in `fetch/fetch_ircc.py` but was never fetched; no plate asks
  for it.
