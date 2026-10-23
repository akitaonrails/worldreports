# Canada — handoff

Updated 2026-10-22 (spine-redraw lane). The country is **on `main`** (the
five-chapter atlas landed in 8b03c87/b32de7a; the earlier "do not merge"
note in this file was stale and is withdrawn). This branch redraws the
atlas onto the plate spine: twelve chapters, the five Canadian-publisher
ones kept as they were where the spine allows, and the seven that had been
absent — economy, trade, people, demography, security, mortality, credit —
built from the harmonised publishers (World Bank, IMF, OECD, BIS,
UNODC/WHO), each panel saying so. Statistics Canada's own line rides
beside the harmonised one where it differs; the slots it will land in are
mapped below. No Statistics Canada number is typed into `plates.py`.

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md) and
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) first. They
are not background reading; they are the specification.

---

## Statistics Canada — fetched, curated, staged; the plate switch is next

From 02:40Z on 2026-10-22 `www150.statcan.gc.ca` served an outage page
under **HTTP 200** for every WDS endpoint; that outage is why the seven
chapters above were built from harmonised publishers instead of waiting.
The platform answered again the same day, and on 2026-10-22 the
`statcan-canada` lane wrote the fetcher and staged the national series:

- `fetch/fetch_statcan.py` — twelve cubes, each verified against
  `getCubeMetadata` (title, CURRENT status, CANSIM id, start year)
  before data is read; full-table zips shape-checked (zip magic, CSV
  member) before caching, because the outage page arrived under HTTP 200
  and a cached error page survives the retry that would have fixed it.
  Spot values (43) and cross-checks against the staged harmonised twins
  run before anything is written; offline reruns are byte-identical.
- Sidecars: `*_from_statcan.csv` in macro/, trade/, social/, credit/.
- Curated national files: `economy_statcan.csv`, `trade_statcan.csv`,
  `gini_statcan.csv`, `poverty_statcan.csv`, `population_statcan.csv`,
  `components_statcan.csv`, `demography_statcan.csv`,
  `security_statcan.csv`, `mortality_statcan.csv`,
  `household_credit_statcan.csv`, `debt_service_statcan.csv` — all
  manifest-listed with provenance, all official Statistics Canada
  numbers, all conversions recorded in `DATA_NOTES.md`.

**Candidate PIDs verified and swapped** (each resolved live):
36-10-0222 → **36-10-0699** (the candidate is the provincial table);
11-10-0190 → **11-10-0134** (the candidate is an income-level table);
13-10-0386 → **11-10-0135** for MBM rates (the candidate is coroner
deaths); 35-10-0177 → **35-10-0068** (the candidate is the whole UCR
violation file); 36-10-0639 → **38-10-0235** (dollar liabilities, not
the ratio); 17-10-0005 → **17-10-0009** for the quarterly estimate;
12-10-0011 dropped outright — customs goods only, not the trade slots'
goods-and-services national accounts. Kept for other chapters:
33-10-0163 (markets FX, 2006-07), 17-10-0121 (NPR stock, 2021 only) and
10-10-0005 (CCOFOG, spending).

### The plate-switch plan (integration lane)

The harmonised series stays canonical (spine rule 10); StatCan rides
beside it as the labelled national line. Nothing in the data is
waiting; the switch is drawing and i18n:

| chapter.slot | harmonised line (stays) | national line to add |
|---|---|---|
| 01 economy 1 | `growth_prices.csv:real_growth_pct` | `economy_statcan.csv:real_growth_pct` |
| 01 economy 3 | `growth_prices.csv:cpi_inflation_pct` | `economy_statcan.csv:cpi_inflation_pct` (keep the target line) |
| 01 economy 4 | `economy.csv:unemployment_pct` (ILO) | `economy_statcan.csv:lfs_unemployment_pct` |
| 04 trade 1 | `trade.csv:exports/imports_pct_gdp` | `trade_statcan.csv:exports/imports_pct_gdp` |
| 04 trade 2 | balance = WB difference | balance = StatCan difference (compute from `trade_statcan.csv`; still not stored) |
| 06 people 1 | `gini.csv` (WB) + `income.csv` (OECD) | `gini_statcan.csv:gini_aftertax` ×100 — legend names the three definitions |
| 06 people 2 | `poverty.csv:poverty_830_pct` | `poverty_statcan.csv:mbm_2018_pct` then `mbm_2023_pct` as two labelled segments — never one joined line |
| 08 demography 1 | `international/population.csv` index | `population_statcan.csv:population_july1` as the national index |
| 08 demography 2 | `demography.csv:fertility` | `demography_statcan.csv:total_fertility_rate` |
| 08 demography 3 | `demography.csv:birth/death_rate_per_1000` | `demography_statcan.csv:birth_rate_per_1000`; crude death rate = `components_statcan.csv:deaths` ÷ `population_statcan.csv:population_july1` |
| 08 demography 4 | `demography.csv:net_migration` per 1,000 | natural increase and net migration from `components_statcan.csv` per 1,000 of the same-vintage July population (July–June key!) |
| 09 security 1 | `security.csv:homicide_per_100k` (UNODC) | `security_statcan.csv:homicide_rate_per_100k` (police-reported) |
| 10 mortality 1 | `causes_of_death.csv:all_causes_per_100k` | crude rate from `mortality_statcan.csv:deaths_all_causes` ÷ July population |
| 10 mortality 2 | excess from the OECD `deaths` counts | recompute excess on `deaths_all_causes` (2015-2019 mean, the house rule stays) |
| 10 mortality 3 | `causes_of_death.csv:covid19_per_100k` | `deaths_covid_19` ÷ population ×100,000 |
| 11 credit 1 | `household_credit.csv:hh_credit_pct_gdp_q4` (BIS) | `household_credit_statcan.csv:hh_debt_to_disp_income_q4` — legend says the denominators differ (GDP vs disposable income) |
| 11 credit 4 | `debt_service.csv` (BIS modelled) | `debt_service_statcan.csv:hh_dsr_pct_q4` + mortgage split |

When the lines land: new panel titles/legends need i18n strings
(`python3 -m pytest tests/test_catalogs.py -q -k canada` renders the
catalog strict), `countries/canada/tests/test_plates.py` should assert
at least one StatCan fact per switched slot (the spot values in
`fetch_statcan.py`'s SPOT list are all reproducible), `tests/test_layout.py`
fault counts must not grow in any language, and the panel footnotes
currently saying "Statistics Canada line pending" must be removed from
the plates *and* their i18n entries retired — a stale pending footnote
above a drawn national line is the page lying about its own data.

---

## What is done

### The twelve chapters, on the spine

Plates (declarative PLATES shape, ids are the spine's chapter numbers):

- **01-economy, 04-trade, 06-people, 08-demography, 09-security,
  10-mortality, 11-credit**: new, built from the harmonised publishers
  (WB/IMF/OECD/BIS/UNODC/PHAC) — each panel footnotes that the Statistics
  Canada line is pending, per the map above.
- **02-fiscal** (IMF general government calendar-year canonical, the
  FRT federal fiscal-year series as the labelled national lines beside
  it): revenue/expenditure, balance + primary, gross debt with the two
  figures quoted instead, interest paid.
- **03-spending** (IMF COFOG stacked by function, social protection vs
  the rest, WB GFCF, OECD public investment; federal FRT figures as
  notes).
- **05-markets** (BoC): policy rate vs inflation; 10y yield with the 2y
  beside it; the dollar as index 2006 = 100 on the Fed H.10 base with
  the BoC noon (to 2016) and single daily (from 2017) series never
  spliced; TSX in US$ vs the S&P 500 (Yahoo, `official: false`).
- **07-world**: GDP in US$ bn (log), HDI one vintage, TI's CPI,
  reserves.
- **12-migration** (IRCC + WB): admissions and study permits per 1,000
  (flows, labelled as flows; permits keep the "flow" wording), net
  migration, foreign-born share; the 2006-14 hole stays visible.

Supporting files: `events.py`, `ui.json`, `DATA_NOTES.md`, `i18n.json`
(fr + pt for every spine unit, panel title and note), `fetch/` (BoC,
FRT, comparables, IRCC, harmonised, spine), `tests/test_plates.py`
(the fact tests — 2020-21 federal balance −14.8%, PR admissions 2024 =
480,955, the splice and back-fill and flow/stock guards, re-expressed
against the spine slots).

`SOURCES.yaml` now lists the curated CSVs beside their `_from_*`
sidecars, which are kept for the next diff. Every CSV in `data/` was
curated 2026-10-22: shape-checked, spot values verified against the
numbers below, blanks carried over as blanks, e-notation floats rewritten
as plain numbers in `fiscal/liabilities.csv` (values unchanged).

### Layout and palette, verified (they were design intent before)

- `core.qa`: **zero faults** for canada in all three languages — no
  baseline entry needed. Two real bugs the QA loop caught: a `max()` on
  (year, value) tuples that picks the latest year rather than the peak,
  and a phantom y-tick above the ylim overlapping the subtitle (fixed
  with explicit `set_yticks`).
- Greyscale: eyeballed `07-world` desaturated — gross/net/average
  separate cleanly.
- Web chrome: measured — ink on ground 15.6:1, family accents 6.6–8.2:1
  on the warm near-black.

### One core/ change, flagged

`core/sitebuild.py`: added a `CAD` entry to `CURRENCY_AFFIX`
(en/fr/pt forms for `money_bn`/`money`). Additive only;
`tests/test_core.py::test_the_currency_is_one_the_site_can_write`
requires every country's currency to have an entry, so no new country
with a new currency can pass without it. No other country is affected.

---

## The traps already found, and what they cost

Unchanged from the first session and now mostly enforced by tests and
CSV comments: the retired noon rate (two series, part-years blank),
`V39079` starting April 2009 (use the static monthly table), the three
Canadian debts (never draw net alone), the April–March fiscal year
(`fiscal_year` = starting year; USA's files use the same key), the
actuarial split existing only from 2008-09 (never back-filled — a test
fails if it is), IRCC's round-to-five and 2015 start, and StatCan's
HTTP-200 outage page.

Spot values, for checking that a rerun has not silently changed shape:

- policy rate 2026 = 2.25, 2023 avg = 4.77, 2020 eoy = 0.25
- federal budgetary balance 2020-21 = **−14.8% of GDP**, program expenses
  27.4% — the largest single-year federal spending in Canadian peacetime
- G7 general government 2024: Canada net debt **12.5%**, gross **111.3%**
- PR admissions: 2020 = 183,075 · 2024 = 480,955 · 2025 = 390,625
- HDI 2023 = 0.939 · GDP per person 2025 = US$55,698 · reserves US$125.6bn

---

## What is left

1. **The plate switch** — the StatCan fetcher, sidecars and curated
   national series are in (`fetch/fetch_statcan.py`, the `*_statcan.csv`
   files); what is left is drawing the labelled national lines into the
   slots mapped above, the i18n for the new legends, and retiring the
   "pending" footnotes. Follow the switch-plan table.
2. **The S&P/TSX composite** is drawn (05 markets slot 4) from Yahoo
   Finance month-end closes, `official: false`, sidecar kept. If an
   official publisher ever appears (stooq was behind a JS
   proof-of-work wall), replace the feed and re-curate.
3. **Transparency International's CPI** is drawn (07 world slot 3)
   from TI's 2012-onward series, the same way France curates it; the
   earlier 0–10 scores are not in TI's time series and are not drawn.
4. **The non-permanent-resident stock** for the migration chapter — the
   story's missing piece: most of the 2023-24 growth never appears in
   the admissions file. The old candidate 17-10-0040 verified live as
   components of international migration; the stock is 17-10-0121 (by
   type, quarterly, 2021 on — short) or the inactive 17-10-0023 (ends
   2022). Two labelled regimes on the panel, never a splice.
5. When the national lines land: refresh `i18n.json` via
   `python3 -m pytest tests/test_catalogs.py -q -k canada`, extend
   `countries/canada/tests/`, and keep `tests/test_layout.py` fault
   counts down.
6. `make C=canada charts thumbs provenance site test` before merging
   anything built on top of this branch.

## Other countries queued behind this one

United Kingdom (slug `united-kingdom`, languages en · pt), Italy,
Israel, Japan, China, Taiwan, Vietnam. See `COUNTRIES.md`.

Israel needs RTL — the user chose "build RTL support when we get there",
so `dir="rtl"`, a mirrored masthead and grid, a Hebrew font and bidi
shaping are unbuilt work, not a known-good path.

## State of `main`

`main` is green and deployed; https://worldreports.io is serving it —
Canada included, since the atlas merged in 8b03c87/b32de7a. This branch
carries the spine redraw on top.
