# Portugal — handoff

Written 2026-10-22: research pass, fetch swarm and consolidation. Branch
`portugal`. This session produced the research, the sources manifest,
seven fetchers (plus the shared `eurostat.py` helper) and the staged
sidecars. It did **not** produce plates, chapters, i18n, ui, events,
curated CSVs or tests. Because `country.yaml` exists, the shared suite
discovers Portugal and fails on those missing files. That is expected. The
check that nothing else broke is
`python3 -m pytest tests/ -q -k "not portugal" --ignore=tests/test_site.py`.
`test_site.py` builds the whole site in a fixture, so a country without
`chapters.py` errors every country's site tests, not just its own.
Portugal's own manifest, data and core checks pass, except the ones that
need `provenance.json`, `plates.py`, `chapters.py` or `i18n.json`.
At consolidation: the "not portugal" run gave 363 passed. The full run gave
433 passed, 23 failed, 111 errors, and every one traces to a missing
`chapters.py` (120 tracebacks), `plates.py`, `i18n.json` or
`provenance.json`. The three cross-country comparison tests in
`test_site.py` fail for the same reason. JS: 20/20. The one real failure
the data phase could fix was `flag_bands` (two bands where three are
required), and it was fixed in `country.yaml`.

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md) and
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) first. They
are not background reading. They are the specification.

---

## What is done

`countries/portugal/` holds:

- `country.yaml`: locales pt (pt-PT, European Portuguese) and en, default
  en, window 2006–2026, last_full_year 2025, tick_every 2, EUR, and three
  recession bands dated off the q/q sign of Eurostat `namq_10_gdp`
  (2008–09, the 2010–13 debt crisis, COVID). Green/red/bronze palette.
  `flag_bands` was changed to three bands in consolidation, because the
  core test requires three.
- `SOURCES.yaml`: written before the CSVs, then corrected to what the
  fetchers do. It has one entry per staged sidecar (50, and every
  `refreshed_by` exists), units for the sidecars without a `#` header, and
  7 `meta.pending` entries.
- `DATA_NOTES.md`: the traps and the cross-source table.
- `DISCOVERY.md`: the research pass's report, kept as a record.
  `SOURCES.yaml` and `DATA_NOTES.md` override it where they differ.
- 50 staged sidecars under `data/`, every one a `*_from_<source>.csv`.
  Nothing is curated yet.

Every fetcher was re-run from cache with `python3 -I` in consolidation.
All their asserts pass together, and the output is byte-identical to the
first run apart from deliberate comment fixes (INE GDP growth vintage,
the INE Gini/poverty year convention, the IGCP-vs-EDP sign change, the
Eurostat stock vintage date, TFR vintage and break flags). A second run
after those fixes was byte-identical. `fetch_igcp.py` re-reads the
igcp.pt page on every run to resolve the dated href, so it touches the
network once even from cache.

| Fetcher | Publisher | What it pulled |
|---|---|---|
| `fetch/fetch_ine.py` | INE JSON API (pindica) | quarterly GDP summed to years + regional-accounts growth, IPC, three unemployment vintages, revised population, births (two NUTS vintages + 2026 months), deaths to 2023, TFR, life tables, causes of death (65 causes, two indicators), DGPJ crime rates, ICOR Gini and poverty, monthly goods trade by partner, revised migration flows and balance, legal-resident foreign stock |
| `fetch/fetch_bpstat.py` | Banco de Portugal BPstat | 10y PT and DE yields + spread, two mortgage-rate compilations, household debt (€ and % GDP), NPL ratio, DGO budget outturn (State 2006+, GG 2013+), Maastricht-debt cross-check |
| `fetch/fetch_eurostat.py` (+ `eurostat.py`) | Eurostat, geo=PT | GDP, EDP debt/deficit, revenue/expenditure, tax ratio, COFOG, investment, P6/P7, unemployment, HICP, Maastricht yield, Gini, AROP, demo_gind/demo_find, police homicide, the migr_* suite (flows, stocks, asylum, permits, acquisitions) |
| `fetch/fetch_ecb.py` | ECB Data Portal | DFR and MRO year-end, EUR/USD mean and year-end |
| `fetch/fetch_igcp.py` | IGCP xlsx | direct State debt, December stocks 2001–2026, currency/fixed-rate shares, maturity, duration |
| `fetch/fetch_comparables.py` | World Bank, UNDP | GDP US$, GDP/person, population, reserves, openness, Gini, HDI, all `official: false` |
| `fetch/fetch_markets.py` | Yahoo Finance (`official: false`) | PSI 20 year-end closes 2013–2026 |

## The GDP-growth finding

INE 0014144 says 2024 real growth was **2.1**. Eurostat says **2.7**. Both
are annual volume growth on base 2021. 0014144 is the **regional
accounts**, last updated 2026-01-06, with 2024 provisional and no 2025. It
predates the September-2026 national accounts. INE's own quarterly y/y
(0013431) now averages 2.7 for 2024, and the World Bank's 2024–25 US$
level is 0.5–0.6% low for the same reason. It is a stale vintage, not a
different concept. Draw growth from `gdp_from_estat.csv`. The fetcher
fails when 0014144 moves, so the note cannot go stale silently. Full
reasoning in DATA_NOTES.

## Spot values, for checking that a rerun has not silently changed shape

- GDP 2024 **€291.15bn** on both publishers, 2025 €308.54bn; growth 2020
  −8.2, 2024 2.7 (Eurostat) / 2.1 (INE regional, stale); WB 2024
  US$313.7bn
- IPC 2022 7.83, HICP 2022 8.1; unemployment (Série 2021) 2013 **17.2**,
  2025 6.0
- EDP debt 2013 130.8, 2020 134.1, 2025 **89.2%**; Q4-2025 €275.1bn;
  IGCP direct debt Dec-2025 €315,237mn; deficit 2010 −11.4, 2023 +1.1
- 10y yield 2012 avg **10.55** (spread to Bund 8.98pp); DFR live 2.50;
  EUR/USD 2024 avg 1.0824; PSI 20 end-2025 8,263.65
- Household debt Dec-2025 €173,642mn; housing loans 70.2% of GDP (2012) →
  37.1% (2025); NPL 2015 17.5% → 2025 2.1%
- Population 31-Dec-2024 **11,387,222** (revised; = demo_gind
  1-Jan-2025), end-2025 11,424,031; WB 2024 10,694,681 (pre-revision);
  migr_pop1ctz 1-Jan-2025 10,749,635 (pre-revision)
- Births 2025 87,764; deaths 2023 118,328 (INE), 2025 121,817 (Eurostat);
  TFR 2024 1.27 (INE) vs 1.41 (demo_find)
- Immigration (INE revised) 2022 **495,979**, Eurostat 2022 167,098;
  emigration INE 2024 188,871; net migration 2021 250,079 (incl. +148k
  adjustment)
- First permits 2025 **310,639**; asylum applications 2024 2,690;
  legal-resident foreigners end-2023 1,044,238 (Brazilian 368,391)
- Homicide: police 2024 72, certificates 2024 86 (2022: 75 vs 97)
- Gini INE 2024 30.9 = Eurostat 2025 30.9; AROP INE 2024 15.4 = Eurostat
  2025

## Pending (none blocks the build; all in `SOURCES.yaml` `meta.pending` unless noted)

1. **AIMA** (aima.gov.pt never connected). The permit-based stock is stale
   at 2023, and RIFA 2024/2025 are PDFs. Eurostat migr_* covers the gap.
2. **RASI / SSI police homicide** (segurancainterna.pt never connected).
   Eurostat ICCS0101 carries the police count to 2024.
3. **DGO direct** (dgo.gov.pt never connected). Mitigated by the BPstat
   republication.
4. **PSI 20 year-ends 2006–2012**: Yahoo starts 2013-04. Hand-curate from
   a redistributor, verified, or leave the hole.
5. **INE deaths 2024–2025** on the NUTS-2024 indicator: not found. Use
   Eurostat demo_gind beside, not spliced.
6. **The 2024 asylum-decisions break** (positive = 10 of 1,005): read the
   Eurostat ESMS footnote before annotating.
7. **Transparency International CPI**: curate by hand with the 2012 break.
8. *(not in meta)* INE's HICP twin (0014655) is not staged. It is not
   needed, because the Eurostat HICP is the same instrument.
9. *(not in meta)* The World Bank's 2024–25 GDP and per-person figures are
   on the old national-accounts vintage. Refresh before the world plate,
   and expect them to move.

## What the next session should build

1. **The curated CSVs**, each diffed against its sidecar, trimmed to
   2006–2026 (IGCP starts 2001). Their SOURCES.yaml entries go beside the
   sidecar entries. Decide per file which year convention ICOR uses on
   the plate, because INE and Eurostat label the same numbers a year
   apart.
2. **plates.py** on the declarative PLATES shape, all twelve spine topics.
   The ones that need care:
   - **01 economy**: Eurostat growth, not 0014144.
   - **02 fiscal**: EDP debt, with the IGCP stock beside it and the sign
     change visible. Draw the cash outturn beside the EDP deficit, with
     2014 (Novo Banco) and 2017 (CGD) annotated.
   - **08 demography**: INE revised population with the 2021–24 revision
     annotated, INE TFR (not demo_find), and deaths 2024–25 from Eurostat
     in a different colour.
   - **09 security**: police vs certificate, two lines.
   - **12 migration**: the 2021 seam is the headline (INE revised flows
     vs Eurostat pre-revision, joined nowhere). Draw arrivals and
     departures, not only the balance, and label the 2021 adjustment if
     the balance appears. Show the stocks on both cuts with the vintage
     named, and label the permit surge of 2025 as backlog clearance.
3. **Annotations the data already demands:** the 2021 population revision
   (INE vs Eurostat/WB), the 2021 LFS questionnaire seam, the 2011
   bailout (in-band), MRO blank before Oct 2008, the DFR going negative,
   the Dec-2015 IGCP margin-account break, Eurostat break flags (stock
   2009, demo_gind 2022, asylum decisions 2024, permits 2025), the GB→XU/XI
   split in 2021, and USD/EUR's direction.
4. **chapters.py / ui.json / events.py / i18n.json** in pt (European
   Portuguese spelling and usage) and en. events.py candidates: the April
   2011 bailout request and May 2014 exit, the 2014 BES resolution, the
   2015–2019 *geringonça* government, the 2023 end of the golden visa for
   property, the SEF→AIMA hand-over (October 2023), and the June-2026
   population revision.
5. **A core decision to make.** EUR already has pt and en forms in
   `CURRENCY_AFFIX`, so the currency test should pass as is. But the pt
   form is `("€ ", " bi")`, which is Brazilian usage. In pt-PT a
   (short-scale) billion is *mil milhões* (often written "mM€" or
   "mil M€"), and "bi" reads as Brazilian. The `pt` column is shared with
   Brazil and France's pt page. Decide before drawing plates whether
   Portugal's pages accept the shared form, or whether core needs a
   locale-region hook. That would be a core change, and it would need to
   make sense for every country.
6. **countries/portugal/tests/**: fact tests on the CSVs, using the spot
   values above. Add no-splice guards: Eurostat immigration blank after
   2023, INE flows equal to Eurostat through 2020 and diverging in 2021,
   INE deaths blank after 2023, PSI blank before 2013, and the
   one-year-shift identity for Gini.
7. Then `make C=portugal charts thumbs provenance && make site test`, and
   the merge conversation. Merging is a decision, not a default.

## State of the branch

`portugal` was cut from `main` at 2b0e367. This session added only
`countries/portugal/`. Nothing in `core/`, `site/` or another country's
directory was touched. `cache/` and `__pycache__/` are gitignored and not
committed.
