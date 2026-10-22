# Portugal discovery — final report

> Kept as the research-pass record. Several first guesses here were corrected by the fetchers and the consolidation pass: INE 0014144 is the regional-accounts vintage (2024 = 2.1, not the national accounts' 2.7); births 0012436 starts 2021, not 2024; INE deaths 0008834 stop at 2023; INE poverty 0009821 starts 2017; INE Gini and poverty are labelled by income year, one behind Eurostat; 0008269 already carries the revised 2021–23 net migration; INE net migration includes a +148k statistical adjustment in 2021; Eurostat demo_find TFR is not on the revised denominators; `flag_bands` needs three bands (tests/test_core.py), not two. `SOURCES.yaml` and `DATA_NOTES.md` are authoritative where they differ.

Phase A complete. Deliverables written in the lane, **uncommitted** (only `?? countries/portugal/` in git status):

- `countries/portugal/country.yaml` — slug `portugal`, locales `pt` (pt-PT, first) + `en` (default `en`, per repo precedent), window 2006–2026, `last_full_year: 2025`, `tick_every: 2`, EUR, three recession bands (dating below), green/red/bronze palette from the flag with a green-tinted dark web chrome, pt/en seo and sources blocks.
- `countries/portugal/SOURCES.yaml` — written before any CSV; 50 planned `*_from_<source>.csv` entries across 8 target dirs + 4 `meta.pending` entries. Every endpoint curled live on 2026-10-22.

Verification: both YAMLs parse; `pytest tests/test_site.py` green (130) with the country dir moved aside, so baseline is intact; with the dir present the suite discovers Portugal and fails on missing `chapters.py` etc. — the expected state (same as Spain's session). Nothing committed.

## Publishers (name · datasets · verified endpoints · quirks)

**INE Portugal** — GDP, IPC, labour, population, vitals, causes of death, income/inequality, crime rates, trade, migration flows, foreign-resident stock.
- JSON API live: `https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd={code}&Dim1=…&lang=PT` + `pindicaMeta.jsp?varcd={code}` for metadata incl. all dimension category codes. **The Base-de-Dados `indOcorrCod` equals the API `varcd`**, so the website's pesquisa maps titles → codes.
- Period codes: annual `S7A{year}`, quarterly `S5A{year}{q}`, monthly `S3A{year}{mm}`. Geography total is `Dim2=PT`; totals per dim are `T`.
- Key codes verified (metadata and/or data): GDP quarterly €M base-2021 `0013428` (2024 quarters sum = 291,153 €mn = Eurostat to the million); real growth `0014144`/`0013431`; IPC annual-avg rate = December of `0014649` (Dec-2024 = 2.42, Dec-2022 = 7.83 ✓), monthly y/y `0014647`, base 2025; HICP y/y `0014655`; unemployment Série 2021 `0012173` (2011–2025: 2024 = 6.4 ✓), Série 2011 `0006191`, long monthly `0007976` (1998+); population `0004167` (revised vintage, 31-Dec reference); births `0008086` (2011–2023 only; NUTS-2024 successors `0012436`/`0012094` start 2024/2026 — gap to mind), deaths `0008834` (sum APU+AMU+APR; 2020 = 123,385 ✓), TFR `0001293`, life expectancy `0001724`; causes of death `0008206` (1980–2022, assault = cause code `64`, 2022 = 97) + `0013166` (2022–2024); crime rates `0008074` (2011–2022) + `0012260` (2021–2025, total 2024 = 31.2‰) — DGPJ-sourced, **no homicide category**; Gini ICOR `0004212` (2003–2024); poverty `0009821`/`0014079`; goods trade monthly by partner × CPA-2008 `0004172`/`0004169` (Jan-2005→Aug-2026); immigration `0006055`, emigration `0006050`, net migration `0013179`/`0008269`; foreign-resident stock `0009107`/`0010247`/`0013220` (all stale at 2023 — SEF→AIMA transition).
- Quirks: API returns `Sucesso.Falso` JSON (not an HTTP error) on bad dim codes; all-causes code `T-LES` is in the metadata but rejected by the data endpoint; 40k cells/call cap.

**Banco de Portugal (BPstat)** — yields, mortgage rates, household debt, NPLs, budget outturn, GG debt.
- API live, no key: metadata `/data/v1/series/?series_ids={id}&lang=EN`; observations JSON-stat via `/data/v1/domains/{dom}/datasets/{dsid}/?series_ids={id}` (docs: `https://bpstat.bportugal.pt/data/docs`). Trailing slashes mandatory; rate-limited with `X-Throttle`.
- Verified series: 10y OT yield monthly `12099464` (1993-07→2026-09; Jan-2012 = 13.85), German 10y `12560098` for the spread; mortgage new-business rate `12533735` (2003-01→, Aug-2026 = 3.0) and percentile-based `12710779` (2018-12→); household debt `12457924` (M€, 2007-12→; 2006 blank), housing loans %GDP `12458135` (65.7 → peak 70.3 → 37.9); NPL ratio `12504544` (FSI quarterly 2015Q4→2026Q2, 17.5→2.1; peak 17.9 in 2016Q2); Budget Outturn domain 10 (State 88873/88884/88894, general government 12560943/…, DGO republished, cash basis — beside EDP, never spliced); Maastricht debt also in domain 28 as cross-check.
- Euribor: not carried by BdP; the ECB key Spain might have used 404s. Mortgage-rate series cover the pass-through panel.

**Eurostat (geo=PT)** — verified live with Spain's exact patterns (reuse `fetch/eurostat.py` + `fetch_eurostat.py` with `GEO="PT"`):
- nama_10_gdp: 2024 €291.2bn (= INE), 2025 €308.5bn; growth 2020 −8.2, 2022 +7.0.
- gov_10dd_edpt1: debt 2011 114.0 → 2013 130.8 → 2020 134.1 → 2024 93.0 → 2025 89.2; deficit 2010 −11.4 (revised up over the years), 2023 +1.1, 2024 +0.7; gov_10q_ggdebt Q4-2025 €275.1bn.
- une_rt_a PT **starts 2009** (2006–08 blank, carried blank — INE covers them); prc_hicp_aind 2022 8.1 / 2024 2.7; irt_lt_mcby_a 2012 10.55; ilc_di12 PT **only 2014–2025** (INE ICOR covers 2003+); ilc_li02 1995+; crim_off_cat `iccs=ICCS0101` police homicide 2008 = 124 → 2024 = 72 (dimension is `iccs`, wrong name → HTTP 400).
- Migration suite: all present; unit=PER empty-cube trap confirmed for PT; **`citizen=FOR` also returns an empty cube** — foreign stock = EU27_2020_FOR + NEU27_2020_FOR (1-Jan-2024: 179,276 + 866,111). First permits 2025 = 310,639 (AIMA backlog — label it). Asylum small (2024 = 2,690). Naturalisations ~17–32k/yr.

**ECB** — DFR/MRO/EXR pattern from Spain verified live (DFR 2.5 on 2026-10-22; EXR CSV). Copy `fetch_ecb.py`.

**IGCP** — site reachable; two xlsx files verified downloadable (monthly debt stock, historical debt indicators). Quirk: download URL carries a churning month folder (`/2026-09/…`) — resolve the href from the page at fetch time.

**World Bank / UNDP** — PRT verified (GDP 2024 US$313.7bn; population 2024 = 10,694,681 — pre-revision vintage); HDR25 CSV has the PRT row (send a browser UA). Adapt `fetch_comparables.py` with ISO3=PRT.

**Yahoo Finance** — PSI 20 is now `PSI20.LS` (old `^PSI20` delisted); verified monthly from **2013-04-30**, Dec closes 2013 6,558.85 / 2024 6,377.26 / 2025 8,263.65. `official: false`.

## country.yaml decisions

- **Bands** (namq_10_gdp PT, SCA q/q pulled today): `2008.25–2009.25` "2008–09 crisis" (four negatives 2008Q2–2009Q1); `2010.75–2013.0` "2010–13 debt crisis" (nine negatives 2010Q4–2012Q4; bailout requested 6 Apr 2011 mid-band; isolated dips 2013Q3/2014Q1 excluded by the two-quarter rule); `2020.0–2020.5` "COVID-19" (−4.3, −15.0; 2021Q1 −2.9 isolated → event, not band).
- **Locales**: `pt` first with `pt-PT`/`pt_PT` (European Portuguese — the country's own copy; the shared `pt` NUMFMT/AFFIX column serves both PT and BR), `default_locale: en` per precedent.
- **Palette**: VERDE `#1E5C3D` (primary), RED `#AE3A2C` (warmer than Spain's `#A32630`, deeper than Italy's future green/red), BRONZE `#A8822F` from the armillary sphere; `flag_bands` has **two** bands (the flag's 2:3 green/red) — core slices/iterates the list so length 2 is safe. Web chrome is a green-tinted near-black, money accent `#63B87E`.
- **Fiscal layer decision**: Eurostat EDP as primary (Portugal reports it under obligation), BPstat domain-10 budget outturn (DGO) as the national cash-basis layer, IGCP stock as the treasury definition — three definitions, three files.

## The big trap (flagged at the top of SOURCES.yaml)

On 2026-06-22 INE revised population estimates 2021–2024 upward (~10.75mn → **11,387,222** at end-2024; end-2025 = 11,424,031) on a new administrative methodology counting ~1.6mn foreign residents. Migration flows revised with it: INE immigration 2022 = **495,979** vs Eurostat's stale transmission 167,098 (they agree through 2020 exactly — 2019: 95,382 both). Vintage map: INE 0004167/0006055/0006050 = revised; Eurostat migr_* = pre-revision and immigration **stops at 2023**; Eurostat demo_gind = revised; WB = pre-revision. This is Portugal's §4a "series break, hard, and recently" — the migration and demography chapters must mark the 2021 seam and never mix vintages.

## Pending list (none blocking)

1. **AIMA** (aima.gov.pt — connection never established, not a 403; sefstat.sef.pt dead): RIFA PDFs; covered meanwhile by Eurostat migr_* + INE's legal-resident stock (stale 2023).
2. **SSI / RASI** (segurancainterna.pt unreachable; portugal.gov.pt RASI page 404): police homicide covered by Eurostat crim_off_cat + INE cause-of-death code 64; hand-curate RASI later.
3. **DGO direct** (dgo.gov.pt unreachable): mitigated via BPstat budget-outturn republication.
4. **PSI-20 2005–2012 year-ends**: Yahoo starts 2013; stooq `^psi` serves the same JS wall as ^tsx/^ibex (796-byte page under 200); Euronext live probe 404'd. Hand-curate at plate-build; approximate memory targets for sanity-checking (unverified): 2006 ≈ 11,300, 2007 ≈ 13,000, 2008 ≈ 6,340, 2012 ≈ 5,650.

## For the fetch swarm

Copy Spain's `fetch/eurostat.py`, `fetch_eurostat.py` (GEO="PT"), `fetch_ecb.py`, `fetch_comparables.py` (ISO3=PRT) and `fetch_markets.py` (symbol PSI20.LS). New fetchers: `fetch_ine.py` (pindica API, dim codes above), `fetch_bpstat.py` (JSON-stat; Spain's eurostat.py stride decoder is reusable — BPstat is JSON-stat v2 with `reference_date` as the time dim), `fetch_igcp.py` (xlsx, resolve href from page). Fetchers must assert payload shape (INE's `Sucesso.Falso`, Eurostat's empty-cube traps) and never overwrite curated files.