# Spain — handoff

Written 2026-10-22, research pass. Branch `spain`, fresh off `main`.
This session produced the research, the sources manifest, six fetchers and
the staged sidecars — **not** plates, chapters, i18n, events or tests. The
moment `country.yaml` exists the shared test suite discovers Spain and
fails on those missing files; that is expected and correct, and the check
that nothing else broke is `python3 -m pytest tests/ -q -k "not spain"`.

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md) and
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) first. They
are not background reading; they are the specification.

---

## What is done

`countries/spain/` holds `country.yaml` (locales es/en/pt, window
2006–2026, last_full_year 2025, tick_every 2, three recession bands dated
off the q/q sign of Eurostat `namq_10_gdp`, a rojigualda-derived palette,
trilingual seo and sources blocks), `SOURCES.yaml` (written before the
CSVs, one entry per staged dataset, `meta.pending` for the sources that
could not be staged), `DATA_NOTES.md` (the traps), and 31 staged sidecars
under `data/`, every one a `*_from_<source>.csv` — nothing is curated yet.

The fetchers, all run this session with `python3 -I`, all asserting payload
shape before caching:

| Fetcher | Publisher | What it pulled |
|---|---|---|
| `fetch/fetch_eurostat.py` (+ `eurostat.py`, France's JSON-stat client copied verbatim) | Eurostat dissemination API, geo=ES | national accounts, EDP debt/deficit/revenue, COFOG, tax burden, GFCF, LFS unemployment, HICP, 10y Maastricht yield, quarterly EDP debt in €, EU-SILC gini/poverty, demography + fertility, and the full migration suite (migr_imm1ctz/imm3ctb/emi1ctz/pop1ctz/pop3ctb on both cuts, asyappctza, resfirst, migr_acq) |
| `fetch/fetch_ine.py` | INE Tempus3/jaxiT3 | CNTR quarterly GDP summed to the year, the linked IPC index (base 2025) + derived annual rate, EPA unemployment annual average, ECP resident population at 1 January, MNP births/deaths (monthly, summed, partial years blank with month counts), ECM causes of death (119 reduced-list causes, long format, incl. assault/homicide), EM and EMCR migration flows |
| `fetch/fetch_bde.py` | Banco de España bierest API (new, April 2025) | Euribor 12m, TEDR new housing loans, household+NPISH debt % of disposable income, doubtful loans + total credit (December stocks) with a computed NPL ratio |
| `fetch/fetch_ecb.py` | ECB Data Portal (France's pattern, Spain's own data dir) | EUR/USD reference rate (avg + year-end), DFR and MRO year-end |
| `fetch/fetch_comparables.py` | World Bank + UNDP (Canada's fetcher adapted, ISO3=ESP) | GDP US$, GDP per person, population, reserves, openness, gini, HDI — all `official: false` |
| `fetch/fetch_markets.py` | Yahoo Finance (redistributor, `official: false`) | IBEX 35 year-end closes 2005–2026 |

## Spot values, for checking that a rerun has not silently changed shape

- GDP 2024: **€1,598.6bn** (Eurostat and INE exactly equal — same
  transmission, today's vintage), real growth 3.7%; 2006: €1,005.0bn
- EDP debt: 2011 69.5% → 2012 89.6% → 2013 100.0% → 2023 105.3% → 2024
  **101.4%** of GDP (the 2024 step down is partly the GDP benchmark
  revision, not repayment)
- Deficit: 2009 **−11.2%**, 2012 **−11.5%** (includes the bank recap),
  2024 −3.2%
- Unemployment (EPA, INE): 2013 **26.09%**, 2024 **11.34%**, 2025 10.50%
- IPC annual rate (from the linked index): 2008 **4.08**, 2024 **2.77**,
  2025 2.67; HICP 2008 4.1, 2020 −0.3
- Population (ECP, 1 Jan): 2006 44,009,969 · 2025 **49,128,297** ·
  2026 49,596,376
- Births 2024 = 318,005; deaths 2024 = 436,118 (matches ECM all-causes to
  the unit); homicide by death certificate (ECM "Agresiones") 2024 = 324
- Migration: immigration (Eurostat) 2019 = 750,480 · 2021 = 887,960 ·
  2024 = 1,288,562 — and INE's old-methodology EM says 2021 = 528,856.
  **That pair is the chapter.** Foreign-citizen stock 1-Jan-2025 = 6.9mn
  vs foreign-born 9.5mn; naturalisations 2024 = 252,476; asylum
  applications 2024 = 167,750; first permits 2024 = 561,640
- 10y Maastricht yield: 2012 **5.85%**; Euribor 12m 2024 avg 3.27;
  mortgage TEDR 2024 3.35
- Household debt: **138%** of disposable income in 2010 → 75% in 2025;
  NPL ratio (computed) Dec-2013 **13.6%**, 2024 3.3%
- ECB: DFR 2024 eoy 3.00, 2025 eoy 2.00; EUR/USD 2024 avg 1.0824
- IBEX 35: 2007 close 15,182.30 · 2012 8,167.50 · 2025 17,307.80 · latest
  bar 2026-10-21 19,323.50
- Comparables: GDP 2024 US$1.726tn · GDP/person 2023 US$33,493 · HDI 2023
  0.918 · reserves 2023 US$103.1bn · WB gini 2023 33.4 · openness 2023
  71.8%

## The traps found this session (all in DATA_NOTES.md with the detail)

1. **Eurostat's Spain immigration series is already spliced at 2021**
   (EM through 2020, EMCR from 2021). The INE publishes 2021 on both:
   528,856 vs 887,960. Two INE files staged to keep the seam visible;
   the plate must mark the break on the Eurostat line.
2. **Banco de España's API serves observations newest-first with null
   holes, units only in metadata, gzip even when identity is requested,
   and HTML error pages under HTTP 200.** The credit series are monthly
   STOCKS in thousands of euro — the first fetcher version summed the
   months and produced an NPL numerator twelve times too big. Fixed to
   December readings.
3. **INE's Tempus3**: error pages are ISO-8859-15 HTML under HTTP 200;
   `DATOS_SERIE` 404s without `nult`; `nult` caps ~300 rows/series;
   period codes 19-22 = Q1-Q4, 1-12 = months, 28 = annual.
4. **Eurostat migration units**: `migr_asyappctza` and `migr_resfirst`
   want `unit=PER`; with `unit=NR` the cube returns well-formed and
   EMPTY. The fetcher fails loudly on empty migration results.
   The flow datasets (and migr_acq) also carry an `agedef` dimension the
   stock ones do not — pinned to REACH where it exists.
5. **Eurostat LFS unemployment for ES (15-74) starts 2009** — 2006-2008
   blank in the source, carried as blanks; the EPA covers those years.
6. **IPC base is now 2025** (rebased early 2026; fifth base in the
   window). The linked series is staged; the rate derived from it
   reproduces the official media anual.
7. **Asylum and first-permits start 2008; the EU/non-EU citizenship
   splits on flows start 2022 (stocks 2015)** — holes are holes, carried
   blank.

## What failed or is blocked (the pending rule applied, none blocking)

- **Ministerio del Interior — crime.** The Portal Estadístico de
  Criminalidad serves its 403 error page under HTTP 200 to every
  automated client tried (plain and browser UA). No fetcher written;
  curation by hand from the Balance de Criminalidad when the security
  chapter is built. The ECM assault series (staged) is its pair.
- **IGAE / Tesoro Público.** `www.igae.pap.hacienda.gob.es` and
  `www.tesoro.es` never established a connection from this machine (not a
  403 — a timeout). Fiscal layer is the Eurostat EDP transmission, which
  is the same aggregate Spain reports; a national-definition series goes
  BESIDE it later if a clean endpoint verifies.
- **stooq ^IBEX**: JS proof-of-work wall (same as ^TSX in the Canada
  session). Yahoo used instead, `official: false`.
- **DataComex** (customs trade by partner/product): not probed; the
  trade chapter's composition panels wait for the build phase. World
  Bank openness is staged as the comparables layer.
- **Transparency International CPI**: curated by hand with the 2012
  break, as France does — left for the build phase.

All four/ five are in `SOURCES.yaml` under `meta.pending` (the sources
table and the manifest tests ignore `meta`) and/or above.

## What the next session should build

1. **plates.py** on the declarative PLATES shape, spine-numbered. The
   staged data carries all twelve spine topics except trade's composition
   panels (levels can come from openness + Eurostat national-accounts
   exports/imports if wanted) and security's police series (pending).
   Suggested departures from the spine, to decide then: none forced —
   Spain's data fits the spine unusually well. The migration chapter (12)
   is the reason Spain was queued second: flows on both definitions with
   the 2021 break marked, stocks on both cuts with naturalisations beside
   them, asylum's four numbers as separate series, permits as permits.
2. **chapters.py / ui.json / events.py / i18n.json** — es/en/pt. Spain's
   `es` is peninsular Spanish where Argentina's is Rioplatense; both are
   `es` locale keys, so check `site/ui.json` and the shared catalogs
   already carry what es needs (they do for Argentina).
3. **events.py** candidates: 2012 bank bailout (June), 2012 labour
   reform, 2010 and 2012 austerity turns, 2017-10 Catalan referendum,
   2020 COVID, 2021 EMCR methodology change, 2026 IPC base 2025.
4. **countries/spain/tests/** — fact tests as claims about the CSVs:
   the 2021 EM/EMCR pair (528,856 vs 887,960), EPA 2013 = 26.09, debt
   2013 = 100.0, NPL 2013 = 13.6, IPC 2024 = 2.77, ECP 2025 = 49,128,297,
   homicide ECM 2024 = 324, and the no-splice guards (EM blank after
   2021, EMCR blank before it, Eurostat LFS blank before 2009).
5. Then `make C=spain charts thumbs provenance && make site test`, and
   the merge conversation — see Canada's HANDOFF for why that is a
   decision and not a default.

## State of the branch

`spain` was cut fresh from `main` (which is green and deployed). This
session added only `countries/spain/`; nothing in `core/`, `site/` or
another country's directory was touched. One deviation from the task
brief to flag: the brief suggested `default_locale: es`, but every
published country — Argentina and South Korea included — sets
`default_locale: en` with the official language first in the locales
list; Spain follows that precedent (es first, default en). Change it only
as an atlas-wide decision.
