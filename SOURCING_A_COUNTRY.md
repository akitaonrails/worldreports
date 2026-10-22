# Sourcing a country

`ADDING_A_COUNTRY.md` says how to put a country into this repository.
This says how to decide **what the plates are and where their numbers come
from** — the research that happens before any code is written, and the
traps that five countries have already walked into.

Read it in full before sourcing a country for the first time. The expensive
mistakes here are not bugs; they are plausible-looking charts that say
something untrue, and every one listed below was shipped by someone careful
before it was caught.

---

## 1. The spine

Five countries converged on the same eleven chapters, not by plan but
because the same questions turn out to be the ones official statistics can
actually answer across two decades. A new country starts from this spine and
departs from it only where its own data forces the departure.

| # | Chapter | Family | The question it must answer |
|---|---------|--------|------------------------------|
| 01 | Economy | money | How big, growing how fast, per person how much, and prices rising how fast |
| 02 | Fiscal | money | What the state takes, what it borrows, what it owes |
| 03 | Spending | money | Where the money goes, by function |
| 04 | Trade | world | What it sells and buys, to and from whom |
| 05 | Markets | money | The policy rate, the currency, the index, the cost of borrowing |
| 06 | People | people | Work, income, inequality, poverty |
| 07 | World | world | How it ranks and what it holds — reserves, HDI, corruption, competitiveness |
| 08 | Demography | people | Births, deaths, ageing, the projection |
| 09 | Security | people | Homicide and violence, on the sources that disagree |
| 10 | Mortality | people | What people die of, and how that moved |
| 11 | Credit | money | What households owe and how badly they are servicing it |
| 12 | Migration | people | Who arrives, who leaves, who is already here, and on which definition |

Chapter 12 is newer than the other eleven and is not on the five
published countries yet. It is in the spine because it is one of the few
things every European statistical system measures in depth and almost
nobody reads carefully — see §4a, which is longer than any other trap
section for a reason.

Each chapter is one plate of four panels. Four is the budget: a panel is
about 7×4 inches at reading size, and a fifth makes every one of them too
small to read the tick labels.

**Departures are expected, and they are editorial decisions to be recorded.**
Argentina has no "World" plate and splits prices out of Economy into a plate
of its own, because a decade of the CPI is missing and that absence is the
single most important fact about the country's data. Brazil has
"Epidemics" where France has "Mortality". Korea has "Safety" where the USA
has both "Mortality" and "Violence". When a country's data has a shape, the
plates follow the shape — but write down why in `DATA_NOTES.md`, because a
missing chapter otherwise reads as an oversight.

---

## 2. Finding the publishers

Seven institutions carry almost everything. Find this country's version of
each before deciding anything else, and find the **machine-readable
endpoint**, not the press release.

1. **The national statistical office.** National accounts, the CPI, the
   labour force survey, population, income and inequality. This is the
   single most important body and usually publishes four of the eleven
   chapters on its own.
2. **The central bank.** The policy rate, exchange rates, international
   reserves, household credit, monetary aggregates. Central banks tend to
   have the best APIs in any given country.
3. **The treasury or finance ministry, and the budget office if separate.**
   Revenue, deficit, debt stock, spending by function. Watch for two
   publishers here; see §4.
4. **The customs or trade authority.** Exports and imports by partner and
   by product. Often a separate body from the statistical office, and often
   on a different definition from it; see §4.
5. **Vital statistics** — a health ministry, a civil registry, or the
   statistical office. Deaths by cause, life expectancy, births.
6. **The interior or justice ministry, or the national police.** Homicide
   and recorded crime. Almost always disagrees with the vital-statistics
   count of the same deaths; see §4.
7. **The market, which is nobody official.** The stock index close, a
   parallel exchange rate, a sovereign-risk spread. Nobody publishes these
   as a statistic. Take them from a redistributor, mark `official: false`,
   and say so on the plate.

Then the **comparables layer**, which is what makes a country legible to a
reader who does not live in it: the World Bank (national accounts, PIP for
poverty), UNDP (HDI), the IMF, Transparency International (CPI),
the World Economic Forum, the OECD for members, Eurostat for EU members,
and UN Comtrade for trade. Use these for ranking and cross-country
comparison, never as a substitute for a national number the country itself
publishes. Where both exist, draw both and label the difference.

### What to prefer, in order

1. The body that **computes** the number, in its own release.
2. That body's API or bulk file, over a scraped page.
3. A supranational body that **harmonises** it (Eurostat, OECD), as a
   second series beside the national one — never spliced into it.
4. A redistributor, only where nothing official exists, marked as such.

A number that cannot be traced to (1) or (3) does not go on a plate.

---

## 3. The research pass, in order

Do this before writing any code. It takes a day or two per country and it
is the whole job; the plates are the easy part.

1. **Name the seven institutions** for this country and find their data
   portals. Write them into `country.yaml`'s `sources` block as you go.
2. **For each of the eleven chapters, find the series.** For each series,
   record: who publishes it, the exact endpoint or document, the unit, the
   geographic scope, the first and last year available, and the revision
   policy. This is `SOURCES.yaml`, and **it is written before the CSVs**.
3. **Pull one year by hand and sanity-check the magnitude** against a
   second source. An order-of-magnitude error — millions read as
   thousands, a quarterly rate read as annual — is invisible on a chart
   that has no reference point.
4. **Find the breaks.** Every country has them: a methodology change, a
   rebasing, a change of government statistical practice, a war, a
   pandemic, a census. Ask the publisher's own documentation where its
   series is not comparable with itself. These become annotations, and
   where two definitions exist, two columns.
5. **Decide `last_full_year`.** Which annual totals are complete? This is
   one number and it governs every dashed line in the atlas.
6. **Write the fetchers**, one per publisher, each writing sidecars.
7. **Then** the CSVs, the plates, the cards and the tests.

A country whose `SOURCES.yaml` is written last will have plates built from
whatever was easy to download, which is not the same atlas.

---

## 4. The traps

Every one of these produced a wrong published chart in one of the five
existing countries. They recur in every country; only the names change.

### Two publishers, one idea

The most common and the most dangerous, because both numbers are correct.

- The **budget** is published by the budget office on an accrual, revised
  basis and by the treasury on a cash basis, and they differ (the USA:
  $35bn apart on one year's outlays, within $2bn on its neighbours).
- The **tax burden** is published nationally and by the harmoniser, which
  counts imputed employer contributions and the national figure does not
  (France: about a point apart, permanently).
- **Inequality** comes from a tax file and from a household survey, which
  are different populations with different income definitions.
- **Homicides** come from the police record, counted at the place of
  occurrence, and from death certificates, counted at the victim's
  residence. They disagree in both directions and neither is wrong.
- **Trade** is counted at customs value as goods cross the border, and on a
  balance-of-payments basis including services (the USA: ~$300bn apart).
- **Public debt** has at least two definitions in most countries, by
  consolidation and by which level of government is included.

**Never splice them.** Two columns, two lines, both labelled, and a note
saying what the difference is. A single line stitched from two publishers
is the one thing this atlas must never contain, and the reason it must not
is that the seam always lands on a politically interesting year.

Take **one publisher per row** where a single series is unavoidable, record
which in a `source` column, and keep the seam in the data where a reader
can see it.

### 4a. Migration, which is the worst of them

Every trap above appears in migration statistics at once, and the subject
attracts readers who already know what they think. The atlas publishes it
the same way it publishes everything else — the official number, the
definition it is on, and the number beside it that measures the adjacent
thing — and the care has to be greater, not the ambition smaller.

**Flow and stock are different chapters of the same story.** How many
arrived in a year is not how many are here. Both belong on the plate, in
separate panels, never on one axis.

**Citizenship is not country of birth.** A naturalisation moves somebody
from "foreign citizen" to "citizen" without anybody moving, so a
foreign-citizen stock can fall in a year of record arrivals. Eurostat
publishes both cuts and so should the plate: `migr_pop1ctz` by citizenship
against `migr_pop3ctb` by country of birth, and `migr_imm1ctz` against
`migr_imm3ctb` for the flow. Where they diverge, the gap is the
naturalisation rate, which is itself a finding — `migr_acq` measures it.

**Net migration is a difference of two numbers, one of which is badly
measured.** Arrivals are recorded because arriving requires paperwork;
departures frequently are not, because leaving does not. Register-based
emigration counts are known to be low in most of Europe. Publish
immigration and emigration as two series and let the reader see the net,
rather than publishing a net figure whose error is dominated by the series
nobody can measure.

**Asylum has four numbers and they are not each other.** Applications
(`migr_asyappctza`), first-instance decisions (`migr_asydcfsta`), grants,
and people actually present. They differ by an order of magnitude at the
edges, they lag each other by years, and conflating them is the single
most common error in public writing on the subject. One panel, four
labelled series, or four panels — never one line called "asylum".

**A residence permit is not a person.** `migr_resfirst` counts first
permits issued in a year; `migr_resvalid` counts permits in force. Someone
who changes status gets a new first permit without a new arrival.

**An irregular-crossing detection is an event, not a person.** Frontex
counts detections at a border segment: one person crossing two borders is
two detections, and a person detected twice on one border is two. It is a
genuine official series and it does not measure how many people came.

**Intra-EU movement and third-country nationals are different legal
objects** with different data behind them. A chart that adds them is
measuring nothing in particular. Eurostat's citizenship dimension splits
them; use it.

**The series break, hard, and recently.** The United Kingdom is the clean
example: its Eurostat migration series carries values to 2019 and stops —
the dataset's time dimension runs to 2024, but the UK rows end, which is
the sort of thing that silently truncates a chart rather than failing it.
After that the ONS is the source, and the ONS itself moved from the
International Passenger Survey to administrative data (Home Office visa
records and the DWP's RAPID database) after the pandemic, then revised EU
and British national estimates again in late 2025 — upward, substantially.
Three regimes in five years. They are annotated, drawn as separate
segments, and never joined into one line.

**Eurostat's migration tables, verified live against the dissemination
API:** `migr_imm1ctz` and `migr_imm3ctb` (immigration, by citizenship and
by country of birth), `migr_emi1ctz` (emigration), `migr_pop1ctz` and
`migr_pop3ctb` (population on 1 January, both cuts), `migr_asyappctza`
(asylum applicants), `migr_asydcfsta` (first-instance decisions),
`migr_resfirst` and `migr_resvalid` (permits), `migr_acq` (acquisitions of
citizenship), `migr_eipre` (third-country nationals found illegally
present). These cover every EU member on one harmonised definition, which
is what makes a European migration chapter possible at all.

For a country outside that system, the equivalents are the national
register or population survey, the interior ministry for permits and
asylum, and the border agency for entries — three publishers who will
disagree, which is the ordinary condition of this chapter rather than a
problem with it.

### A subset drawn as a peer

Headline unemployment is contained in broad unemployment. Firearm homicides
are contained in firearm deaths. Debt held by the public is contained in
gross debt. Drawn as two lines of equal weight, the reader divides them by
eye and gets a ratio that is not the one the chart implies.

Say it in the legend entry — "U-3, the headline rate (subset of U-6)" — and
where the chapter promises a share, draw the share as its own panel.

### The partial year

A year in progress is not a small year. Annual totals and averages stop at
`last_full_year`; a genuinely current reading — a debt stock, a policy
rate, a closing price — may show the running year and is labelled as the
latest point, not as the year's result.

The caption must say *how* incomplete: "2026: 9 of 12 months". The worst
bug in the original build drew half a year of trade as an annual total,
which read as a 50% collapse in exports that never happened.

### Re-basing and vintages

A census re-bases the population estimate, and growth measured across the
boundary between two vintages is not growth. A development index is
recomputed for its whole history with each annual report, so mixing report
years produces steps that are methodology rather than development.

Compute change **within a vintage**, and use one vintage throughout.

### Definitional breaks

A tax credit becomes a contribution cut, and the tax burden falls a point
for no economic reason. A crime qualifier is created in law and takes years
to be applied consistently, so its early rise is classification, not
behaviour. A reporting pause ends and a delinquency rate goes from 0.6% to
9.2% in a year.

These are annotated on the line, never smoothed. Unannotated, a definitional
break is the largest policy effect on the chart and it never happened.

### Nominal currency across a long window

Where prices have risen by orders of magnitude, nominal local currency is
not a unit and nothing is plotted in it across years. Use constant prices,
a share of GDP, or dollars — and say which.

### Geographic scope

Most countries publish at more than one geography: metropolitan against
including overseas territories, mainland against including an autonomous
region, the state against the island. Pick one, name it in `country.yaml`'s
`seo.spatial`, and never mix two inside a single line.

### Survey against administrative

A survey measures what people report; an administrative record measures
what an office processed. A labour force survey and a payroll register are
not the same series, and the gap between them is itself a finding.

### What a cause-of-death code follows

An ICD code follows whoever certifies the death, not whoever decides what
happened. Deaths at the hands of police are routinely coded as ordinary
homicide; research puts roughly half of them there. Publish the official
series because it is the official one, and say in the note what it misses.

"Underlying cause" and "deaths involving" are two different questions, and
for an epidemic they differ enormously — for one country in 2020, by 0.2%
on all causes, 9.9% on COVID and 639.5% on pneumonia. Separate columns,
separate lines, never spliced.

### Quarterly series that are annualised

Current-dollar quarterly national accounts are usually seasonally adjusted
*annual rates*. The annual figure is the **mean** of the quarters, not the
sum. Summing them overstates output fourfold, and the result still looks
like a chart.

### Endpoints that lie

An official gateway may serve an HTML error page under HTTP 200, which
parses as zero rows or as garbage. A trade series may zero-fill months it
has not published, so a presence test counts twelve months in August. A
consolidated series may differ from the first-published numbers everyone
remembers.

Assert what you expect: a known year-end value, a row count, a non-zero
month. A fetcher that cannot confirm it pulled what it meant to pull should
fail rather than write.

### A missing year is missing

Blanks are years the publisher has not covered. Nothing interpolates across
them and nothing zero-fills them: a hole in a series is a hole, not a
collapse to zero. Where a hole is long and a substitute exists, draw the
substitute in a different colour and never in the same line.

---

## 5. What counts as official

A dataset is official unless the manifest says otherwise, and `official:
false` is a flag in `SOURCES.yaml`, not a sentence in a `notes:` field —
the page reads the flag. A test looks for exactly that contradiction.

Mark `official: false` for: stock indices, parallel or black-market
exchange rates, sovereign-risk spreads, industry and trade-association
surveys, think-tank compilations, and anything from a redistributor.

Being unofficial is not a reason to leave a number out. It is a reason to
say so where it appears.

---

## 6. Fetchers and sidecars

One script per publisher, in `countries/<slug>/fetch/`, run by hand and
never by the build. A fetcher **never overwrites a curated number**: it
writes `<name>_check.csv` or `<name>_from_<source>.csv` beside the curated
file, and a person diffs it.

This is not caution for its own sake. Official APIs revise history silently,
change units between editions, and serve errors as data. The sidecar makes
every one of those a diff somebody reads rather than a chart that quietly
changed.

---

## 7. Before calling a country done

- [ ] Every CSV has a `SOURCES.yaml` entry with publisher, URL and notes.
- [ ] Every non-official dataset carries `official: false`.
- [ ] Every series' scope is one geography, named.
- [ ] Every pair of incompatible series is two columns, drawn as two lines.
- [ ] Every break is annotated on the panel where it appears.
- [ ] `last_full_year` is right, and every partial caption says how partial.
- [ ] Every magnitude was checked against a second source at least once.
- [ ] `DATA_NOTES.md` records the judgement calls and the departures from
      the spine.
- [ ] Each plate asserts at least one fact about its own data in
      `countries/<slug>/tests/`, so a refetch that invalidates a claim
      fails loudly.
- [ ] The plates are drawn in every language the country publishes, and
      the catalog test passes with no missing strings.
