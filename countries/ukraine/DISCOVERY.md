# Ukraine — Phase A discovery report

Research pass run 2026-10-24 in the `ukraine` lane, against the issue #1
contributor matrix treated as untrusted evidence: every endpoint below was
curl'd live today and every number re-derived from the raw payload where the
endpoint answered. `country.yaml` and `SOURCES.yaml` are the deliverables;
this file is the record. `SOURCES.yaml` and (later) `DATA_NOTES.md` are
authoritative where they differ from this report.

**Verification:** both files parse as YAML. Gate (2026-10-24, lane):
`pytest tests/ -q --ignore=tests/test_site.py -k "not ukraine"` →
**1220 passed**, 4 failed — all four are the expected shared-code set:
`test_every_declared_style_is_known`, `test_every_style_has_every_language_spec[uk]`,
`test_every_style_has_plate_rules[uk]` (the `uk` number style does not
exist yet), and `test_comparison_peers_use_identical_canonical_axes`
(raises `SystemExit: ukraine: no plates.py` — Phase B). The ukraine
subset: 36 passed / 26 failed, the failures being exactly the Phase A
set — missing `data/`, `i18n.json`, `plates.py`, `chapters.py`,
`provenance.json` — plus the three recorded shared-code needs (`uk`
style, UAH `CURRENCY_AFFIX`, the three-flag-band assertion). The
`tests/test_site.py` errors hit every country including the published
ones (the site is not built in this lane), as in the UK lane. No other
country is affected by this lane's files.

**Delivered (uncommitted, in the lane as instructed):**

- `country.yaml` — identity, locales (uk/en/pt, default en), window
  2006–2026, `last_full_year: 2025`, four recession bands dated on the
  NBU quarterly GDP series (pulled live, current vintage), azure/gold
  palette, seo in uk/en/pt, and the five shared-scale conflicts recorded
  in a comment block.
- `SOURCES.yaml` — 30 planned datasets across 9 topic directories plus
  9 `meta.pending` entries, written before any CSV exists.

---

## Publisher-by-publisher, all probed live 2026-10-24

### State Statistics Service of Ukraine (Ukrstat / SSSU) — BLOCKED here, mirrored

- `stat.gov.ua`: **HTTP 403 "The request is blocked"** (WAF page with a
  reference ID) on every route tried — `/`, `/en/development-api`, and the
  SDMX registry path — both schemes, browser UA included. `www.ukrstat.gov.ua`
  never answers; no `api.`/`sdmx.` subdomains resolve. The issue's author
  reached the docs, so this is a network/geo block, not a dead publisher.
  **Exact failure mode recorded; retry from an unblocked network at fetch
  time.** The documented API shape (from the publisher's own step-by-step
  page, via search index): SDMX 2.1 registry at
  `https://stat.gov.ua/sdmx/workspaces/default:integration/registry/sdmx/2.1/dataflow/SSSU/<FLOW>/<version>?detail=full&references=none`, agency SSSU, plus an SDMX v3 route.
- **Working official mirrors, verified today:**
  - SDG portal `sdg.stat.gov.ua` (200) → its data files on
    `uaukrstat.github.io/data-ukraine-sdg/`. The Gini CSV
    (`uk/data/10-1-1.csv`) was pulled: **2015 = 0.227 … 2021 = 0.244;
    2022–2025 present but blank** — the issue's anchor reproduced exactly,
    from the publisher's own file. The CSV carries oblast and urban/rural
    cuts in the same file (headline = the all-Ukraine row).
  - `data.gov.ua` CKAN API (200): organization
    `derzhavna-sluzhba-statystyky-ukrayiny` holds **388 datasets**
    including annual/quarterly national accounts, population structure,
    births, deaths, CPI, household incomes. Resources are CSV/XLSX/JSON
    served from data.gov.ua itself; probed samples are CP1251-encoded and
    **per-resource vintage varies (one national-accounts resource is from
    2020)** — the fetcher asserts freshness per resource.

### National Bank of Ukraine — the workhorse, fully accessible

`bank.gov.ua` answers 200 with a browser UA (the contributor's 403s were
UA-related). The open-data directory (`/en/open-data/api-dev`, fetched and
parsed) documents **36 `statdirectory` endpoints**; probed today:

- `exchange` — official FX daily: USD 2006-01-03 = **5.05** (the peg) ✓,
  2024-01-01 = **38.002** ✓. Base of the spine currency index (UAH/USD,
  rising = weaker; inverted via `ctx.fx_index`).
- `key` — policy rate daily back to 2006: 2006-01-01 = 9.5 ✓ (known NBU
  discount rate), 2024-01-01 = 15.0 ✓, 2026-10-23 = 16.0. Markets slot 1.
- `res` — official reserve assets monthly, USD mn: 2024-12 = **39,927.12**
  (with the FX/gold/SDR split). World slot 4 national line.
- `economicactivity` — quarterly national accounts (GDP expenditure
  breakdown: FCE, GFCF, exports/imports of G&S, GVA), **from 2010** (2006
  and 2010-Q4 probes return 0/79 rows; 2011-Q4 112). The quarter label is
  the first month of the FOLLOWING quarter (verified: its `202207` row is
  −36.6 = Ukrstat's 2022 Q2). Pulled 2011–2026 today for the band dating.
  Q4-2025 GDP at current prices = 1,925,991 mn UAH.
- `inflation` — CPI cube (annual and monthly), dimensions: ku (region,
  null = Ukraine), mcrd081 (COICOP division, `Total` = all items), tzep
  (comparison basis: PCPM_/DTPY_/PCCM_/PCCP_). Sep-2026 all-items rows
  read 10.8–11.1 across the year-on-year bases — **the issue's "110.0"
  anchor is NOT reproduced exactly**; the headline basis is pinned against
  the NBU technical-instructions PDF before the fetcher writes.
- `budget` — Treasury budget execution republication, annual functional
  classification, **from 2014**: 2024 Defence = 2,097,621.9 mn UAH, total
  expenditure 4,441,364.6 mn (66 rows). Spending chapter national line.
- `loan` (43,898 rows/month), `mir` (51,154 rows/month — new-business
  deposit/loan rates), `banksfinrep`, `monetary`, `balanceofpayments` all
  answer; dimension codelists come from the technical guide.
- NPL: the page `/en/stability/npl` links an editioned xlsx
  (`Data_NPLs _2026-09-01_en.xlsx`, verified: per-bank volumes + ratio
  sheets, served as `application/octet-stream` — check zip magic) and
  Flourish data JS with the **full quarterly ratio series from 2006**,
  pulled today: peak **56.2% (Q3 2017)**, 27–39% through 2022–2025, then a
  drop to 13.9% at Q1 2026 that lands exactly on the IMF FSI value — a
  presumed definition/write-off break to confirm before drawing; a seam,
  never smoothed.

### Open Budget — BLOCKED here

`openbudget.gov.ua`: **Akamai "Access Denied"** (edgesuite reference) on
every route, browser UA included; `open-budget.gov.ua` does not resolve.
The CC BY 4.0 licence claim is from the publisher's about page (issue
quote). Not blocking: the NBU budget cube republishes Treasury execution.

### Ministry of Finance — site blocked, data mirrored officially

`mof.gov.ua` 403 today. The Ministry's own data.gov.ua dataset
`4119d762-a5c1-4c4c-9c30-e2abdd383fb4` (state + state-guaranteed debt)
answers: monthly legacy-XLS snapshots, each a time-series workbook in bn
UAH/USD with the state/guaranteed split. Verified value: total
**3,929.7 bn UAH at Nov-2022** (2022-12-31 edition). The issue's
9,602.89 bn UAH (31 Aug 2026) is consistent with the trajectory;
magnitude-confirmed, page-unverified. This is **not** the canonical
general-government debt — the IMF WEO line is (107.1% of GDP, 2025).

### Verkhovna Rada — unreachable

`zakon.rada.gov.ua`: connection failure on both schemes (no HTTP status).
The 2026 minimum wage (8,647 UAH/month, Law 4695-IX art. 8) is confirmed
by convergent professional secondary sources; the law text is verified
when the portal answers. Historical values are hand-curated per budget
law, one law number per year.

### State Customs Service — blocked

`customs.gov.ua` 403 today; its data.gov.ua datasets are registers and
classifiers, not flows. Partners slot runs on IMF IMTS + UN Comtrade.

### Office of the Prosecutor General — accessible with browser UA

`new.gp.gov.ua/en/posts/statistika` (200) indexes the monthly recorded-
crime posts; attachments are real xlsx workbooks on
`old.gp.gov.ua/ua/file_downloader.html?...` (verified download, zip
signature, octet-stream content type). The contributor's 403 was
UA-related. **Unverified:** the Article-115 intentional-homicide row
inside the workbooks, the table structure and year coverage — pinned by
the fetch swarm before staging. Wartime restriction of prosecutor
statistics is expected to leave a 2022+ hole.

### Comparables layer — all verified live today

- **World Bank** (all `official: false`): growth −28.76/+5.53/+3.25/+1.82
  for 2022–2025 (matches the issue's Ukrstat anchors and the IMF);
  GDP 2024 = **US$190.8bn**, 2025 = US$214.2bn; local-currency GDP 2024 =
  **7,662,376 mn UAH — byte-identical to Ukrstat's published figure**;
  population (incl. Crimea) 2006 = 47.28mn, 2021 = 44.30mn, 2025 =
  38.98mn; CPI 2025 = 12.73; ILO unemployment **stops 2021 = 9.834**;
  reserves 2025 = US$57.27bn; exports/imports 2025 = 25.3/51.8% of GDP;
  GFCF 19.4%; TFR 2024 = 0.988; births 5.5 / deaths 13.6 per 1,000;
  **net migration 2022 = −5,699,445**; migrant stock 2024 = 13.4%;
  homicide 2021 = 3.78/100k (UNODC); suicide 21.2 (2021); road deaths
  10.2 (2019); NPL (IMF FSI) 2025 = 13.92; Gini ends 2020 = 25.6;
  poverty $8.30 ends 2020 = 11.3%.
- **IMF DataMapper**: GGXWDG_NGDP 2025 = 107.1% (span 1997–2031);
  GGXCNL_NGDP 2023 = **−19.3%**; Fiscal Monitor GGR/G_X/GGXONLB all
  present (expenditure 2025 = 74.2% of GDP). Later years are projections —
  stop at 2025.
- **IMF SDMX GFS**: GFS_COFOG `UKR.S13` answers (240 series, 2015–2025,
  % of GDP, ten divisions); GFS_SOO answers (233 series incl. interest
  G24 and G31 public investment, 2015–2025). **2006–2014 holes stay
  holes.**
- **IMF IMTS**: UKR goods exports by partner in raw US$ (Poland 2024 =
  $4.397bn ✓ magnitude) — **coverage starts 2018**; 2006–2017 from
  **UN Comtrade public preview API** (verified with a live 2006 query;
  500-row page cap). Two segments, annotated seam.
- **UNDP HDR25 composite CSV**: Ukraine HDI 2006 = 0.762, 2021 = 0.772,
  2022 = 0.772 (carried across the invasion year — noted), 2023 = 0.779.
- **Transparency International CPI workbook**: S3 **403 AccessDenied**
  from this network (plain and browser UA); Canada's lane fetched the same
  URL on 2026-10-22 — network block, retry at fetch time.
- **BIS**: WS_TC household credit and WS_DSR for UA answer **HTTP 404** —
  Ukraine is not in the BIS credit statistics. Credit slot 1 has no
  harmonised line; the NBU loan cube ÷ GDP derivation is the national
  line, formula documented at curation.
- **Eurostat**: `demo_gind` UA = 1-Jan population 1996–2020, **2021
  missing**, 2022 = 40,997,698, nothing after (the 2014→2015 step is the
  Crimea exclusion); `nama_10_gdp` UA in €M to 2024; `irt_lt_mcby_a`,
  `une_rt_a`, `ilc_di12`, `migr_imm1ctz` all return **well-formed empty**
  UA slices (the UK lesson: empty, not 404 — fail loudly on it).

## Issue anchors: verdict table

| Issue claim | Verdict (2026-10-24) |
|---|---|
| GDP growth −28.8/+5.5/+3.2/+1.8 (2022–2025) | **Confirmed** (WB −28.76/5.53/3.25/1.82; IMF identical) |
| GDP 2024 = 7,662,376 mn UAH | **Confirmed** (WB local-currency series identical to the hryvnia) |
| CPI Sep-2026 = 110.0 y/y | **Not reproduced**: NBU cube's all-items Sep-2026 y/y bases read 10.8–11.1; headline basis to pin from the NBU technical guide |
| Unemployment 2021 = 9.9% | **Confirmed** (WB/ILO 9.834); series stops there |
| Gini 2021 = 0.244, 2022–25 missing | **Confirmed from the publisher's own CSV** (uaukrstat.github.io) |
| Population 1-Jan-2022 = 41,167,335 | Corroborated (Eurostat 40,997,698 and WB 41,048,766 within 0.4%); Ukrstat page itself blocked |
| State+guaranteed debt 9,602.89 bn UAH, Aug-2026 | Magnitude-consistent with the verified MoF workbook series; page blocked |
| Minimum wage 8,647 UAH from 1-Jan-2026 | Confirmed by convergent secondary citation of Law 4695-IX art. 8; rada.gov.ua unreachable |
| NBU/prosecutor 403s | **UA-related**: both answer 200 with a browser UA today |
| stat.gov.ua / openbudget.gov.ua / mof.gov.ua / customs.gov.ua | Blocked from this network (WAF/Akamai), recorded in meta.pending |
| GDP "~US$180bn 2024" (kickoff brief) | Actually **US$190.8bn** (WB) |
| Population "~41mn in 2021 and falling" (kickoff brief) | 41.2mn is the **national registered** count (excl. Crimea); the WB harmonised figure incl. Crimea is 44.3mn — the 3.1mn gap is territory, not error |

## country.yaml decisions

- **Locales** uk (official-first) · en (default, repo precedent) · pt.
- **Window** 2006–2026, `tick_every: 2`, `last_full_year: 2025` (Ukrstat
  published final 2025 GDP in March 2026; IMF/WB carry 2025 outturns;
  IMTS 2025 complete). Wartime per-series gaps are earlier and stay.
- **Bands**, dated on the NBU quarterly GDP y/y series pulled today
  (quarter label = first month of the following quarter; the q/q rule is
  pending Ukrstat access): 2008.75–2009.75 (provisional — NBU quarterly
  starts 2010; annual 2009 = −15.1% and the known quarterly profile),
  2014.0–2016.0 (eight consecutive negative quarters), 2020.0–2020.75
  (y/y evidence; the house q/q convention would give 2020.0–2020.5),
  2022.0–2023.25 (five negative quarters; 2022 Q2 = −36.6). **Not
  banded:** 2012 Q4–2013 Q4 (five mildly negative quarters but annual
  2013 ≈ 0.0% — stagnation; candidate event).
- **Palette**: flag azure #005BBB / yellow #FFD500 pulled down to steel
  blue #1F6AB2 / navy #123D63 / gold #B88A12; web chrome a cold
  deep-azure night (#071521) distinct from the UK's navy-black (#0D1220)
  and the Americas' warm blacks; `mark_bearing 0.06em` (U, as UK/USA);
  two flag bands, neither paper-coloured.
- **name** in all twelve existing locales plus uk (Україна).

## Shared-code needs (recorded, not built — integration phase)

1. **core/spine.py scale revisions** (each forces regeneration of every
   country carrying the topic + `tests/test_spine.py` + overlay QA):
   - `economy.growth` −18..+18 → must take −28.8 (2022);
   - `fiscal.balance` −16..+8 → −19.3 (2023);
   - `fiscal.revenue_expenditure` 0..70 → expenditure 74.2 (2025);
   - `credit.npl` 0..20 → 56.2 (2017);
   - `demography.natural_increase_net_migration` and `migration.net`
     −10..+40 → ≈ −139 per 1,000 (2022), if the WPP wartime outflow is
     drawn canonically at all — the alternative is the displacement lens.
2. **core/numstyle.py**: `uk` style — STYLES, SEPARATORS (narrow NBSP
   thousands, comma decimal per DSTU 4163), AFFIX/PERCENT forms; no
   ladder needed (Ukrainian groups by thousands: "млрд"/"млн").
3. **core/sitebuild.py CURRENCY_AFFIX**: UAH (₴ after the amount,
   non-breaking space; "млрд грн" forms in uk) for every spec its locales
   use — Canada's CAD entry is the template.
4. **Every existing country's `name` map gains a `uk` entry**
   (`test_the_comparison_names_every_country_in_every_language` reads
   every locale any country publishes).
5. **site/ui.json chrome strings in uk.**
6. **Fonts: no change needed.** fontconfig reports Ukrainian coverage
   (`:lang=uk`) in both Noto Sans and Liberation Sans, and DejaVu Sans —
   the existing LATIN_TITLE/LATIN_BODY stacks — carries the full
   Ukrainian alphabet (Ґґ Єє Її Іі). `uk` does NOT need a SCRIPT_FONTS
   entry; verify once at render time with a real plate.
7. **tests/test_core.py::test_the_palette_fills_every_slot_the_page_needs**
   hard-codes three flag bands; Ukraine's flag has two. Relax the shared
   assertion to accept two or three (`core/page.py` already slices
   `[:3]`, so two bands render fine). Ukraine's `flag_bands` stays
   truthful at two.

## Pending list

All nine entries are in `SOURCES.yaml` under `meta.pending` with exact
failure modes: Ukrstat SDMX/site (WAF 403), Open Budget (Akamai),
mof.gov.ua (403), customs.gov.ua (403), zakon.rada.gov.ua (no
connection), TI CPI workbook (S3 403, network-specific), UNHCR/IOM data
APIs (JS-assembled), the 10-year yield (possibly nonexistent — classify
before pending), the equity index (redistributor needed).

## For the fetch swarm

Planned fetchers (named in `refreshed_by`): `fetch_nbu.py` (the 36-endpoint
statdirectory API + NPL files — browser UA, zip-magic checks, dimension
codelists from the technical guide, the quarter-label convention pinned
against 2022 Q2 = −36.6), `fetch_ukrstat.py` (SDMX if reachable;
data.gov.ua mirror and the SDG CSVs otherwise), `fetch_datagovua.py`
(CKAN; MoF debt), `fetch_gp.py` (prosecutor xlsx attachments),
`fetch_rada.py` (budget laws), `fetch_comparables.py` (WB + UNDP),
`fetch_harmonised.py` (IMF DataMapper + Eurostat residual),
`fetch_spine.py` (IMF SDMX GFS/IMTS + Comtrade + TI),
`fetch_markets.py` (equity redistributor). Every fetcher fails loudly on
the shapes documented here: WAF block pages under 403, Eurostat's
well-formed empty slices, octet-stream xlsx, CP1251 CSVs, and the NPL
definition break at 2025→2026.
