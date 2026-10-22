# Canada — data notes

What these sources were like to work with, and the judgement calls a reader
of the plates should not have to reverse-engineer. `SOURCES.yaml` carries
the per-file caveats; this file carries the ones that cross files.

---

## Why seven chapters are missing

Statistics Canada's data platform (`www150.statcan.gc.ca`) has served an
outage page under HTTP 200 — not an error code, an HTML apology — for every
WDS endpoint since at least 2026-10-22 02:40Z. StatCan publishes the
national accounts, the CPI, the labour force survey, population estimates,
causes of death, the homicide survey, household credit and merchandise
trade: chapters 01, 04, 06, 08, 09, 10 and 11 of the spine. They are absent
rather than approximated, and they will slot into their spine numbers when
the platform returns — nothing here gets renumbered. The candidate table
PIDs are in `HANDOFF.md`, each still to be verified against a live API.

A corollary trap for the fetcher that will be written then: the outage page
arrives under HTTP 200, so a fetcher must check the payload shape before
caching, or it caches an error page that survives the retry that would have
fixed it. The existing fetchers already do.

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
net series is therefore never drawn alone: the World plate shows net and
gross together, and the fiscal plate keeps the two federal measures on
their own panel.

## The fiscal-year convention

Everything in `fiscal/` is the **federal** government on fiscal years,
April to March, and `fiscal_year` holds the *starting* year: 2024 is
2024-04-01 to 2025-03-31. The World plate is the opposite convention —
general government, calendar years — which is what makes it comparable
across the G7 and incomparable with the fiscal plates. Both say so on their
faces.

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
blank, with the coverage in the `*_months` columns, because either
presented as an annual average lands inside the plausible range and nothing
downstream would catch it. **2006 and 2007 are still holes** pending
StatCan table 33-10-0163 (annual average exchange rates). The direction is
CAD per USD: a rising line is a weaker Canadian dollar.

The policy rate comes from the monthly static table
(`STATIC_ATABLE_V39079`), not from `V39079` itself, which Valet carries
only from April 2009 — a plate drawn from it would open at 0.25% with the
whole 2008 easing missing in front of it.

## The IRCC files

The permanent-resident and study-permit open data **begin in 2015** — the
2006-2014 half of this atlas's window is not in them, and the migration
plate leaves that visible rather than starting the axis late. Every cell is
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

## The comparables layer

The World Bank and UNDP series are harmonised cross-country readings, kept
as comparables and magnitude checks, marked `official: false` and never
spliced into a national series. The World Bank's Gini is derived from the
Canadian Income Survey under its own income definition and is not
Statistics Canada's own Gini; it is staged but not drawn while the People
chapter is absent. The HDI is one vintage throughout — the Human
Development Report recomputes the whole back-series at each methodology
change, so a trend assembled from successive annual reports would be partly
an artefact of the reports.

## What is still pending even so

- The S&P/TSX composite. Nobody official publishes a stock index; stooq,
  the usual redistributor, was behind a JavaScript proof-of-work wall when
  tried, so the panel is pending rather than hand-typed from memory.
- Transparency International's CPI. No stable machine endpoint, and the
  2012 methodology break means pre-2012 scores are not on the same scale.
  The World plate has four panels without it; it stays out rather than
  being compiled from memory.
