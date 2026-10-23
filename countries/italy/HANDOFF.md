# Italy — handoff

Written 2026-10-22 after the research pass, the fetch swarm and
consolidation, on branch `italy`. This session produced:
- the research;
- the sources manifest;
- six fetchers;
- the staged sidecars.

It did **not** produce plates, chapters, i18n, ui, events, curated CSVs or
country tests. `country.yaml` exists, so the shared suite discovers Italy
and fails on those missing files. That is expected.

The check that nothing else broke is
`python3 -m pytest tests/ -q -k "not italy" --ignore=tests/test_site.py`,
which gave **363 passed** at consolidation. JS tests: 20/20.
`test_site.py` builds the whole site in a fixture, so a country without
`chapters.py` errors every country's site tests: 8 failed and 111 errors,
all from `countries/italy/chapters.py does not exist`.

Italy's own run (`-k italy`) gave 39 passed and 18 failed. Every failure is
a later-phase file:
- `plates.py`: 8 failures (layout ×6, isolation ×2);
- `i18n.json`: 6 (catalogs);
- `provenance.json`: 3 (sources ×2, isolation);
- the `it` locale: 1. `test_every_locale_can_be_formatted` reports
  "spec 'pct' has no form for ['it']" because `core/sitebuild.py` AFFIX
  has no `it` column yet.

The manifest, data and remaining core checks all pass.

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md),
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) and the
spine (`PLATE_SPINE.md`, `core/spine.py`) first. They are the
specification, and you need them before building anything.

---

## What is done

`countries/italy/` holds:

- `country.yaml` (unchanged from discovery). Locales are it (it-IT), en
  and pt, with en as default. The window is 2006–2026, `last_full_year`
  2025, `tick_every` 2, currency EUR. There are three recession bands
  dated off Eurostat `namq_10_gdp` q/q: 2008–09, 2011–13 and COVID.
  The palette is green-led, with three `flag_bands`.
- `SOURCES.yaml`, corrected to what the fetchers do. It has one entry per
  staged sidecar (44), every `refreshed_by` exists, and there are 8
  `meta.pending` entries.
- `DATA_NOTES.md`: the traps, the cross-source table, and the
  consolidation changes.
- `DISCOVERY.md`: the research report, kept as a record. It was moved
  here from the lane root.
- 44 staged sidecars under `data/`, every one a `*_from_<source>.csv`.
  Nothing is curated yet.

Every fetcher was re-run from cache with `python3 -I` inside a
network-less namespace (`unshare -rn`). That proves no fetcher touches the
network for a cached query. All asserts passed together. The output was
byte-identical to the swarm's, except `demography_from_estat.csv`, which
consolidation deliberately reformatted: population in persons and counts
as integers, with values unchanged. A second offline run was
byte-identical.

| Fetcher | Publisher | What it pulled |
|---|---|---|
| `fetch/fetch_istat.py` | ISTAT I.Stat SDMX (esploradati) | quarterly GDP levels (EDITION-pinned), NIC base 2015 + base-2025 months, RFL unemployment (backcast to 2006), absolute/relative poverty, population and foreign residents (2019+), births, deaths (2011+), causes of death (91 codes, 2006–23), police homicide, certificate homicide, anagraphic migration flows |
| `fetch/fetch_eurostat.py` | Eurostat, geo=IT | GDP, EDP debt/deficit/interest, revenue/expenditure, tax ratio, COFOG, investment, P6/P7, une_rt_a, HICP, Maastricht yield, Gini (2014+), AROP, demo_gind/demo_find, the migr_* suite (flows on both cuts, stocks with FOR_STLS, asylum, first permits, acquisitions) |
| `fetch/fetch_bdi.py` | Banca d'Italia BDS (PROSPETTODATI) | household loans (financial accounts) ÷ Eurostat GDI, IMF-FSI gross NPL ratio, bad loans (to Mar 2024), MIR lending rates |
| `fetch/fetch_ecb.py` | ECB Data Portal | DFR and MRO year-end, EUR/USD mean and year-end |
| `fetch/fetch_comparables.py` | World Bank, UNDP | GDP US$, GDP/person, population, reserves, openness, Gini, HDI, all `official: false` |
| `fetch/fetch_markets.py` | Yahoo Finance (`official: false`) | FTSE MIB year-end closes 2005–2025 + the live 2026 bar |

## ISTAT: six series still pending

esploradati.istat.it has been timing out since about 10:35. At
consolidation, `curl -s -m 20 https://esploradati.istat.it/` gave exit 28
after 20 s, so it was not hammered. These are pending, with keys already
pinned in the fetcher:

| # | Series | Flow / key | Spine effect |
|---|---|---|---|
| 1 | NIC bases 1995 and 2010 + ISTAT's published annual rate | 167_747 `A.IT.2+10+40.4+8.00` | economy slot 3 covered by Eurostat HICP 2006+; NIC is the second line, 2017–25 computable today |
| 2 | attempted / mafia / infant homicide columns | 73_67 `A.IT.CRIMEN.ATTEMPHOM+MAFIAHOM+INFANTHOM.9.YRDUR` | security lens only |
| 3 | life tables | 26_295 `A.IT.LIFEXP..Y0` | no slot (Eurostat demo_mlexpec as alternative) |
| 4 | TFR by mother's citizenship | 25_326_DF_DCIS_FECONDITA1_5 `A.IT.TOTFERR..TOTAL` | demography slot 2 covered by Eurostat demo_find 2006–2024 |
| 5 | valid non-EU permit stock | 29_348_DF_DCIS_PERMSOGG1_1 `A.IT.RESPER.9.999.ALL..TOTAL.99` | migration lens covered by Eurostat first permits (a flow); stock twin migr_resvalid not staged |
| 6 | citizenship acquisitions by process | 29_849 `A.IT.ACQCITIZ.9.WORLD..TOTAL` | migration lens covered by Eurostat migr_acq totals |

**Re-run** when `curl -s -m 20 https://esploradati.istat.it/` answers,
from the repo root of the `italy` lane:

```
python3 -I countries/italy/fetch/fetch_istat.py
```

The fetcher reuses `cache/` for every query already answered, with no
network for those. It spaces live requests 3 s apart, and it stops trying
after the first connection-level failure. When the run lands:
- add manifest entries for `social/lifexp_from_istat.csv`,
  `social/fertility_from_istat.csv`,
  `migration/permits_stock_from_istat.csv` and
  `migration/citizenship_acquisitions_from_istat.csv`;
- remove the ISTAT item from `meta.pending`;
- check that the `# PENDING` lines have left `nic_from_istat.csv` and
  `homicide_police_from_istat.csv`.

## Spot values, for checking that a rerun has not silently changed shape

- GDP 2025 **€2,265.0bn** on both publishers (ISTAT ed. 2026M10), growth
  2020 −8.7, 2021 9.2, 2025 0.6; WB 2024 US$2,383bn
- NIC base 2015: 2024 120.8, 2025 122.6; HICP 2022 8.7; unemployment
  ISTAT 2006 6.86, 2014 12.79, 2025 6.05 (Eurostat 2009+ only)
- EDP debt 2020 154.7, 2025 **136.7%**, Q4-2025 €3,097.1bn; deficit 2020
  −9.4, 2025 −3.1; primary 2025 +0.7; interest 2012 5.1
- 10y yield 2012 **5.49**; DFR live 2.50; EUR/USD 2024 avg 1.0824; FTSE
  MIB end-2025 44,945
- Household loans end-2025 €819.9bn; debt/GDI 2024 55.9; FSI NPL 2015
  18.0 → 2025 2.4; bad loans Mar-2024 €30,335mn
- Population 1-Jan-2025 **58,943,464** (ISTAT = Eurostat), 1-Jan-2026
  58,942,828 (e); births 2024 369,944; deaths 2024 653,109; TFR 2024 1.18
- Immigration 2024 451,583 (both cuts), emigration 2024 188,903; ISTAT
  2025 439,916 / 144,157; foreign citizens 1-Jan-2025 5,371,251,
  foreign-born 6,928,045
- Asylum applications 2024 158,605; first permits 2025 433,099;
  acquisitions 2024 217,448
- Homicide 2023: police **341**, certificates **239**; police 2024 326
  (0.6/100k)
- Gini SILC 2025 31.0 (2014+), WB 2023 34.3; absolute poverty hh 2025 8.1

## Spine coverage (PLATE_SPINE.md)

**S** = fillable from staged sidecars, **F** = needs a harmonised fetch
(the source exists), **P** = genuinely unavailable (`ctx.pending`).

| Topic | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| economy | S growth (Eurostat) | S GDP/person (WB) | S HICP + NIC beside (NIC 2006–15 pending ISTAT); ECB 2% line | S ISTAT RFL 2006+, Eurostat beside |
| fiscal | S revenue/expenditure | S balance + primary | S EDP debt | S interest D41PAY |
| spending | S COFOG 7 groups (to 2024) | S social protection vs rest | S GFCF % GDP | S government GFCF |
| trade | S P6/P7 % GDP (WB openness beside) | S balance, computed | **F** top export destinations: Coeweb unreachable, so use Eurostat Comext (`DS-045409`/`ext_st_eu27_2020sitc`) or UN Comtrade | lens: free choice (e.g. P6 goods vs services) |
| markets | S DFR vs HICP | S BTP 10y | S EUR/USD index 2006=100 | S FTSE MIB in US$ with ECB rate; **F** S&P 500 (add `^GSPC` to fetch_markets, as France does) |
| credit | **F** BIS WS_TC `Q.IT.H.A.M.770.A` (BdI loans/GDP = 36.1 already agree, but the slot is BIS) | S MIR house-purchase rate vs DFR | S FSI gross NPL (2011+), bad-loans ratio beside | lens: S debt/GDI; or **F** BIS WS_DSR |
| people | S SILC Gini 2014+ with WB Gini 2005–23 beside (Eurostat has no IT before 2014) | S ISTAT absolute poverty 2014+ / AROP 2006+; **F** WB PIP US$8.30 line if Italy has it | **P** no statutory minimum wage (CCNL sector floors) | lens: S relative poverty / AROP |
| world | S GDP US$ | S HDI (to 2023) | **F** TI CPI, hand-curated with the 2012 seam (`meta.pending`) | S reserves (2025 gold jump) |
| demography | S population index (Eurostat 2006+) | S TFR demo_find (+ ISTAT split pending) | S crude birth/death per 1,000, computed | S natural increase + net migration (ISTAT flows); Eurostat CNMIGRATRT optional |
| security | S police (ISTAT rate) + certificates; **F** UNODC `VC.IHR.PSRC.P5` (WB API) | S suicide 17_2 per 100k (to 2023) | S/F transport accidents 17_1_1 is all modes; road-only needs ISTAT road accidents or Eurostat `tran_sf_roadus` | lens: mafia homicides, pending ISTAT |
| mortality | S crude death rate | S excess deaths vs 2015–19, computed (2020 +16.4%) | S COVID-19 per 100k (2020 131.5) | S lens from causes |
| migration | S imm/emi per 1,000 | S net per 1,000 | S foreign-born 11.8% + foreign-citizen 9.1% | S asylum / permits / acquisitions |

The only **P** is the minimum wage. Every **F** is a source that exists
and should be fetched through the country's fetchers, with a sidecar and a
manifest entry, before the plate is drawn (spine rule 11).

## What the next session should build

1. **The harmonised fetches** marked F above: BIS WS_TC (and WS_DSR),
   S&P 500, UNODC homicide, Comext/Comtrade partner shares, road deaths,
   WB PIP, and the TI CPI by hand. Re-run the ISTAT fetcher if the host
   is back.
2. **Curated CSVs**, each diffed against its sidecar and trimmed to
   2006–2026. Their manifest entries go beside the sidecar entries.
3. **plates.py** on the spine. The places that need care:
   - **economy**: ISTAT unemployment as one line from 2006, since it is
     backcast; the NIC rebase seam at 2025/2026, never computed across.
   - **fiscal / spending**: annotate the Superbonus years (2021–23
     deficits, the GF06 bump) after checking the EDP notes; debt crossing
     €3tn in 2025.
   - **people**: the Gini seam, with Eurostat from 2014 and WB alone
     before.
   - **security**: two homicide lines that never cross, ISTAT's rate
     rounded to one decimal, and "transport accidents" labelled as such.
   - **migration**: Eurostat vs ISTAT 2008–2010, two lines and a note.
     ISTAT 2025 beyond Eurostat. FOR_STLS on the citizenship cut.
   - **credit**: the bad-loans series ends March 2024, and its 2024 row
     mixes March and December.
4. **The `it` locale**, a core change for Phase B. Add an `it` column to
   `AFFIX` / `CURRENCY_AFFIX` in `core/sitebuild.py` (candidates are in
   `DISCOVERY.md`: "mld" for billions, comma decimals, "/100 mila").
   Also add `it` entries to `site/ui.json`. Without the column,
   `test_every_locale_can_be_formatted[italy]` fails.
5. **chapters.py / events.py / i18n.json** in it, en and pt. Candidate
   events:
   - the 2011 spread crisis and the Monti government;
   - "whatever it takes" (July 2012);
   - the 2013–14 near-third dip;
   - the 2019 stall;
   - the first Western COVID lockdown (March 2020);
   - the PNRR (2021);
   - the Superbonus;
   - the 2026 ECB hike.
6. **countries/italy/tests/**: fact tests on the spot values above, plus
   no-splice guards:
   - NIC base 2015 blank before 2016;
   - Eurostat unemployment blank 2006–08;
   - Eurostat Gini blank before 2014;
   - bad loans blank after 2024;
   - ISTAT and Eurostat migration equal 2011–2024 and different in
     2008–2010.
7. Then `make C=italy charts thumbs provenance && make site test`, and
   the merge conversation. Merging is a decision, not a default.

## State of the branch

`italy` was cut from `main` at 2b0e367. This session added only
`countries/italy/`. Nothing in `core/`, `site/` or another country's
directory was touched. `cache/` (8.6 MB) and `__pycache__/` are
gitignored and not committed.
