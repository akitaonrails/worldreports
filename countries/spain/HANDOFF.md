# Spain — handoff

Updated 2026-10-22 (third session, the plate spine). Spain is **on
`main`** (merged with the build session) and this pass redraws it on the
plate spine on branch `spine-spain`, off `plate-spine`. The old "do not
merge" note is obsolete: merging the spine branch is the next step, once
the shared spine work lands. Every plate declares its topic and claims its
slots in spine order; see PLATE_SPINE.md and the spine section of
DATA_NOTES.md for the conversions and the populations behind them.

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md) and
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) first. They
are not background reading; they are the specification.

---

## What is done

Everything the research pass queued. `plates.py` (declarative PLATES, alt
text on each), `chapters.py` (12 cards, unique topics, headline strip),
`ui.json` (es/en/pt), `events.py`, `i18n.json` (311 entries after the
spine pass, stale ones pruned, strict render clean),
`countries/spain/tests/test_plates.py` (46 tests after the spine pass,
including hand recomputations of the per-1,000 and per-100,000 rates),
the curated CSVs (47 files), SOURCES.yaml with curated + sidecar entries,
`output/` committed (36 plates + 36 thumbs), `provenance.json` (12 plates
read 42 files).

### The plates, on the spine (slot 1 · 2 · 3 · 4)

| # | topic | slots |
|---|------|--------|
| 01 | economy | real growth (Eurostat) · GDP per person, US$, log (WB) · IPC + HICP vs the 2% target · EPA unemployment + Eurostat LFS |
| 02 | fiscal | revenue and expenditure · balance (bars) + primary · Maastricht debt · interest paid (D41PAY) |
| 03 | spending | COFOG stack · social protection vs the rest · GFCF, whole economy · government GFCF |
| 04 | trade | exports and imports % of GDP (openness in the note) · balance % of GDP with goods and services lines · top destinations, % of goods exports (Comext) · lens: products, % of goods exports (Comext) |
| 05 | markets | ECB DFR + MRO vs Spanish IPC · 10y Maastricht yield · euro vs US$, index 2006 = 100, log · IBEX 35 in US$ vs S&P 500, index 2006 = 100, log |
| 06 | people | Gini, Eurostat + WB, not inverted · AROP-60 + WB US$8.30 · SMI in US$ a month · lens: employment |
| 07 | world | GDP US$ bn, log (€ level in the note) · HDI · TI CPI 2012–2025 · reserves US$ bn, log |
| 08 | demography | population index 2006 = 100 · TFR · births and deaths per 1,000 · natural increase + net migration per 1,000, seam kept |
| 09 | security | homicide per 100k (INE + UNODC, log) · suicide per 100k (INE + WHO) · road deaths per 100k (INE + WHO) · lens: the three side by side; police count pending |
| 10 | mortality | crude death rate · excess deaths % over 2015–19 · COVID per 100k, identified + suspected · lens: tumours vs circulatory per 100k |
| 11 | credit | household debt % of GDP (BIS) · TEDR + Euribor vs DFR · NPL ratio · lens: BIS debt service ratio |
| 12 | migration | **the seam panel**: immigration and emigration per 1,000, Eurostat split at 2021, INE EM 2021 · net migration per 1,000, same seam · foreign-born and foreign-citizen shares · lens: permits, asylum, naturalisations per 1,000 |

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

1. **Ministerio del Interior crime statistics** (no longer a pending
   panel — the security slots are homicide, suicide and road deaths from
   the death certificates; the lens says the police count is pending): the portal serves its 403 error page under HTTP
   200 to every automated client. Curate by hand from the Balance de
   Criminalidad; pair with the ECM count, which the plate already draws.
2. **DataComex** national-concept totals: the partner and product panels
   are now drawn from Eurostat Comext (same declarations, community
   concept). DataComex would go beside them, never into them.
3. **IGAE/Tesoro** national-definition fiscal series, beside (never in) the
   EDP columns, if a clean endpoint verifies.
4. **Transparency International CPI** — now fetched (2012–2025, CPI 2025
   spreadsheet). The pre-2012 0–10 scores are deliberately not drawn.
5. A refresh pass when 2025 completes: `make C=spain fetch`, diff sidecars,
   bump nothing until the annual totals exist.

## State of the branch

The research pass and the build are on `main`. `spine-spain` adds the
spine redraw on top of `plate-spine`, touching nothing outside
`countries/spain/`. New fetch code: `fetch/fetch_comext.py` (Comext
destinations and products, cross-checked against UN Comtrade), the
S&P 500 in `fetch_markets.py`, the SMI and the goods/services split in
`fetch_eurostat.py` (plus the COFOG zero-fill fix), TI's CPI in
`fetch_comparables.py`, and the ECP 1 July population in `fetch_ine.py`.
