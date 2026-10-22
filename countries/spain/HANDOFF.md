# Spain — handoff

Updated 2026-10-22 (second session, the build). Branch `spain`. The country
is **built and the full suite is green**: `python3 -m pytest` → 733 passed,
`node --test tests/js/*.test.js` → 20/20, layout QA **zero faults in all
three languages** (no baseline entry needed). Twelve plates, all twelve
spine topics, drawn in es/en/pt. **Do not merge to `main` yet** — merging
is a product decision, not a test result (see Canada's HANDOFF for the same
note).

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md) and
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) first. They
are not background reading; they are the specification.

---

## What is done

Everything the research pass queued. `plates.py` (declarative PLATES, alt
text on each), `chapters.py` (12 cards, unique topics, headline strip),
`ui.json` (es/en/pt), `events.py`, `i18n.json` (244 entries, strict render
clean), `countries/spain/tests/test_plates.py` (22 fact tests), the curated
CSVs (37 files, every one diffed from its sidecar with the spot values
asserted at curation time), SOURCES.yaml with curated + sidecar entries,
`output/` committed (36 plates + 36 thumbs), `provenance.json` (12 plates
read 37 files).

### The plates, as built

| # | slug | Panels |
|---|------|--------|
| 01 | economy | GDP €bn (Eurostat bars + INE line, both drawn); real growth; GDP/person US$ (WB); IPC vs HICP vs the 2% aim |
| 02 | fiscal | revenue vs expenditure; deficit + primary (computed, labelled); Maastricht debt; interest vs the harmonised tax take |
| 03 | spending | COFOG stack; social protection vs the rest; whole-economy investment (the brick years, 30.1%); public investment |
| 04 | trade | exports vs imports (ESA 2010 goods+services); the balance (surplus since 2011); openness (WB); partners/products **pending** (DataComex) |
| 05 | markets | ECB DFR + MRO (MRO blank before Oct 2008, as in France); the 10y Maastricht yield (5.85% in 2012); EUR/USD; IBEX 35 via Yahoo (official: false, price index, 2026 = live reading) |
| 06 | people | EPA unemployment + Eurostat LFS (hole before 2009 visible); employment level; Gini two cuts of one survey (inverted axis); AROP-60 with the relative-threshold note |
| 07 | world | GDP US$; GDP/person US$; HDI one vintage; reserves with the eurozone note |
| 08 | demography | population (ECP, the 2012–16 decline annotated); births vs deaths (crossover 2015, COVID 494k); TFR (1.10 in 2024); natural increase vs net migration, two methodologies never joined |
| 09 | security | homicide by death certificate (ECM, counts and computed rate); **police count pending** (Interior portal walled); violent deaths in context (suicide > traffic > homicide) |
| 10 | mortality | all deaths; tumours vs circulatory (crossover only in 2024); COVID certified, identified vs suspected stacked; excess over the 2015–19 mean (computed, labelled) |
| 11 | credit | Euribor 12m vs TEDR new housing; household debt 141%→75% of income; NPL ratio (computed, Dec stocks, 13.6% in Dec 2013, the 2014 reporting change annotated); loan stock Q4 |
| 12 | migration | **the 2021 seam panel**: Eurostat split at 2021, INE EM to 2021, INE EMCR from 2021, 528,856 vs 887,960 annotated; arrivals vs departures; the stock on both definitions with the naturalisation gap shaded; the year's paperwork (applications / decisions / positive / permits / naturalisations, five labelled series) |

### One core/ change, flagged (the documented extension point)

`core/sitebuild.py`: the `EUR` entry in `CURRENCY_AFFIX` gained `es` forms
(money_bn `("€ ", " mm")`, money `("€", "")`), following Argentina's es
convention. France publishes EUR in en/fr/pt and needed no es; Spain is the
first eurozone country publishing in Spanish. Additive only;
`tests/test_core.py::test_the_currency_is_one_the_site_can_write` requires
it. Nothing else outside `countries/spain/` changed.

## Traps found in the build phase (in addition to DATA_NOTES.md)

1. **The ECM cause-name split.** The fetcher first split series names at
   the first "." — which mangled chapter names ("II.Tumores" → "II") and
   collapsed "COVID-19. Virus identificado" with "…no identificado
   (sospechoso)" into one key, silently keeping only the identified count.
   The fetcher now splits at the dimension boundary and asserts both COVID
   rows exist. (Also: adjacent SERIES_TABLA pages repeat their boundary
   rows — same name with the same code is a page overlap, with a different
   code is a real collision; the fetcher distinguishes them.)
2. **The IPC 2006 rate needs the 2005 index mean** — the fetcher computes
   the annual mean one year beyond the window before taking the rate.
3. **The household-debt peak is 141% in 2008** (annual mean), not the ~138%
   in 2010 that the research pass's notes said from the Q4 column. The
   curated note and the plate agree on 141%/2008 now.
4. **matplotlib keeps tick labels for positions outside the ylim**, and
   the layout QA counts a tick at 600 from a 280–560 axis as overlapping
   the plate subtitle. If a panel's axis ends just below a round number,
   set the yticks explicitly (see plate_demography, births/deaths).
5. `Panel.bars()` matches no patches on this matplotlib (Canada's caveat):
   read `ax.patches` directly, without a transform filter.

## Spot values for regression-checking a rerun

All carried in `countries/spain/tests/test_plates.py`; the load-bearing
ones: GDP 2024 = €1,598.59bn on BOTH publishers · growth 2020 = −10.9% ·
IPC 2008 = 4.08 / 2024 = 2.77 · EPA 2013 = 26.09 / 2024 = 11.34 · EDP debt
2013 = 100.0 / 2024 = 101.4 · deficit 2012 = −11.5 · employment 2013 =
17,139k · ECP 1-Jan-2025 = 49,128,297 · births 2024 = 318,005 · deaths 2024
= 436,118 · ECM homicide 2024 = 324 · COVID certified 2020 = 60,358 +
14,481 suspected · tumours 115,578 vs circulatory 113,620 in 2024 · EM 2021
= 528,856 vs EMCR 2021 = 887,960 · Eurostat immigration 2024 = 1,288,562 ·
naturalisations 2024 = 252,476 · asylum applications 2024 = 167,750 · first
permits 2024 = 561,640 · NPL Dec-2013 = 13.6% · household debt 2008 =
140.7% · yield 2012 = 5.85% · IBEX 2007 close = 15,182.30 · trade balance
first positive 2011.

## What is left (the pending rule, none blocking)

1. **Ministerio del Interior crime statistics** (security plate's third
   panel is `ctx.pending`): the portal serves its 403 error page under HTTP
   200 to every automated client. Curate by hand from the Balance de
   Criminalidad; pair with the ECM count, which the plate already draws.
2. **DataComex** (trade plate's fourth panel): customs goods by partner and
   product — a different universe from the national-accounts series the
   plate carries; never mix the two.
3. **IGAE/Tesoro** national-definition fiscal series, beside (never in) the
   EDP columns, if a clean endpoint verifies.
4. **Transparency International CPI** — curated by hand with the 2012
   break, as France does.
5. A refresh pass when 2025 completes: `make C=spain fetch`, diff sidecars,
   bump nothing until the annual totals exist.

## State of the branch

`spain` is `main` + the research pass + this build. Nothing outside
`countries/spain/` changed except the one additive CURRENCY_AFFIX entry
above. The suite is green on the whole repo, Canada included.
