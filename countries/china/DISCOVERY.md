# China — Phase A discovery report

> Kept as the research-pass record (2026-10-22). `SOURCES.yaml` is the
> authoritative, machine-readable manifest where the two differ. This is the
> prose record: per publisher — what it publishes, the exact endpoint curl'd
> live today, the payload shape, the quirks, the honest official flags, and the
> pending list. No `fetch/`, `data/`, `plates.py`, `chapters.py`, `i18n.json`,
> `ui.json` or `events.py` were written (Phase A only).

## The China rule, restated

COUNTRIES.md row 7: *"the atlas publishes what the NBS publishes, marked as such,
beside the international series where those exist, and says in the notes where
the two disagree and by how much."* Every national-official series in
`SOURCES.yaml` (`official: true`) has a World Bank / IMF / UN twin (`official:
false`) of the *same quantity*, each in its own entry, both drawn side by side,
never spliced, with the disagreement quantified in the notes. China's difficulty
is source reliability, not the language — the method is identical to every other
country here.

## Delivered (committed on branch `china`, lane `.slim/worktrees/china`)

- `countries/china/country.yaml` — identity, locales, palette, window, bands.
- `countries/china/SOURCES.yaml` — the manifest: one entry per planned dataset
  across the twelve-chapter families, every endpoint curl'd live today with the
  outcome recorded, five `pending` entries. Written before any CSV exists.
- This report.

## Live-probe summary (2026-10-22, from this machine)

| Publisher | Channel | Result |
|---|---|---|
| World Bank API | `api.worldbank.org/v2/.../CHN/indicator/...` | **LIVE** JSON, `lastupdated 2026-10-08` |
| IMF DataMapper | `imf.org/external/datamapper/api/v1/...` | **LIVE** JSON (filter quirk, below) |
| UNDP HDI | HDR25 composite CSV | **LIVE** 200, text/csv, ~2.0 MB |
| Yahoo Finance | `query1.../v8/finance/chart/000001.SS` | **LIVE** (needs browser UA) |
| UN Comtrade | `comtradeapi.un.org/public/v1/preview/...` | **LIVE** 200, no key, row-capped |
| NBS `data.stats.gov.cn` | `easyquery.htm` | **403 BLOCKED** on every variant |
| GACC `customs.gov.cn` | portal | **412 BLOCKED** (anti-bot precondition) |
| PBoC `pbc.gov.cn` | portal | **200** (series endpoint not isolated) |
| SAFE `safe.gov.cn` | portal | **200** |
| MOF `mof.gov.cn` | portal | **200** |

## Publishers

### Comparables layer — World Bank (all `official: false`)

`GET https://api.worldbank.org/v2/country/CHN/indicator/<ID>?date=<from>:<to>&format=json`
→ JSON array `[meta, [observations]]`; meta carries `lastupdated`. All verified
live today; magnitudes cross-checked against the brief:

- `NY.GDP.MKTP.CD` (GDP, current US$): **2025 US$19,498,039,388,043 (19.5tn)**,
  2024 18.73tn, 2023 18.27tn, 2022 18.32tn, 2021 18.20tn. Brief's US$18–19tn
  check PASSES. **Quirk to hold onto:** the current-USD level *falls* 2022→2023
  (18.32→18.27tn) purely on the exchange rate while real growth was +5.4% — the
  current-USD series is a size reading, never a growth reading.
- `NY.GDP.MKTP.KD.ZG` (real growth, annual %): 2025 4.96, 2024 4.96, 2023 5.42,
  2022 3.13, 2021 8.57, 2020 2.34. No negative year.
- `NY.GDP.PCAP.CD`: 2025 **US$13,861.97**.
- `SP.POP.TOTL` (UN WPP): peak **2022 = 1,412,175,000**, then 2023 1,410,710,000,
  2024 1,408,975,000, 2025 **1,406,585,000**. Brief's "~1.41bn, falling since
  2022" PASSES.
- `FI.RES.TOTL.CD` (IMF IFS, reserves incl. gold): 2025 **US$3,748,744,952,818**,
  2024 US$3.46tn. Gold-revaluation lifts the IFS figure; SAFE is national record.
- `NE.TRD.GNFS.ZS` (trade % of GDP): 2025 **37.96%** (down from ~60% mid-2000s).
- `SI.POV.GINI`: 2022 **36.0**, 2023/2024 **null** — the WB series *lags*; the
  nulls stay null (a hole is a hole, not a collapse).
- `SM.POP.TOTL.ZS` (UN DESA migrant stock, % pop): 2024 **0.1%** (2023 null) —
  international migration is marginal; the real story is internal.

### IMF DataMapper (fiscal + growth cross-read, `official: false`)

`GET https://www.imf.org/external/datamapper/api/v1/<IND>/CHN`
**Filter quirk (verified):** the `/CHN` segment does **not** narrow the response —
it returns **all 229 countries** under `values.<IND>`. The fetcher must read
`values.<IND>.CHN`, not assume a one-country body.

- `NGDP_RPCH` (real growth %): CHN 2006 12.7 … 2020 2.3, 2021 8.6, 2022 3.1,
  2023 5.4, 2024 5.0, 2025 5.0. Programmatic check: **zero** negative CHN years
  in 2006–2026. This is the band evidence.
- `GGXWDG_NGDP` (gen-gov gross debt % GDP): 2006 25.2, 2009 33.9, then
  2018 55.7 → 2020 70.6 → 2023 84.1 → **2025 98.6**. This is the IMF *broad*
  perimeter — dozens of points above the MOF's narrow on-budget debt because it
  counts local-government/LGFV-adjacent bodies. That gap is a China finding.

### UNDP HDI (`official: false`, one vintage)

`GET https://hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_complete_time_series.csv`
→ 200, text/csv, ~2.0 MB, one row per country. CHN row present; HDI climbs from
~0.49 (1990) to ~0.80 (latest). **One vintage throughout** — HDR recomputes the
whole back-series each methodology change, so a trend assembled across report
years is partly an artefact of the reports.

### Market — SSE Composite (`official: false`, redistributor)

`GET https://query1.finance.yahoo.com/v8/finance/chart/000001.SS?period1=…&period2=…&interval=1mo`
(needs a browser `User-Agent`). JSON chart object: `meta.symbol 000001.SS`,
exchange **SHH** (Shanghai), `instrumentType INDEX`, `currency CNY`,
firstTradeDate 1997-07. Year-ends from monthly bars. Nobody publishes a stock
index as a statistic → `official: false`, labelled on the plate. **stooq is
JS-walled** from this machine (per brief) → Yahoo is the source.

### NBS (国家统计局) — the workhorse, but **machine API BLOCKED**

`https://data.stats.gov.cn/easyquery.htm?m=QueryData&dbcode=hgyr|hgjd&…`
returned **HTTP 403** on every variant tried today — root and `/english/`,
annual `hgyr` and the trade shape, with and without a browser UA (~1–1.8s each,
295–313-byte error bodies). The **portals do** answer: `www.stats.gov.cn` → 200
(slow, ~6s) and `stats.gov.cn/english/` → 200 (~1.9s). So the NBS-official
series the atlas wants (GDP level in CNY, quarterly growth, surveyed urban
unemployment, Gini, births/deaths/life expectancy, floating population) can be
sourced from the reachable portal/communiqués but **not from the JSON API here**.
`official: true` is preserved on these entries; they are parked on `pending`
rather than scraped. Cross-reads live elsewhere (WB growth, IMF debt, WB Gini)
let the plates carry a China economy/people/demography chapter even while NBS is
403.

### GACC (海关总署) — trade by partner, **BLOCKED**

`http://www.customs.gov.cn/` → **HTTP 412** (Precondition Failed / anti-bot) from
this machine. Goods-trade-by-partner parked. Reachable cross-checks: **UN
Comtrade** `GET https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=156&period=2023&cmdCode=87`
→ 200, no key (reporter **156 = China**; preview is row-capped, a partner-total
cross-check, not a substitute for the GACC national figure). GACC's own endpoint
needs an alternate route in Phase B.

### PBoC / SAFE / MOF — portals live, series endpoints to isolate in Phase B

All three portals return **200** (`pbc.gov.cn` 2.75s, `safe.gov.cn` 3.46s,
`mof.gov.cn` 1.61s). The machine-readable series endpoints were **not isolated**
this session and are named in `refreshed_by` (`fetch_pboc.py` / `fetch_safe.py` /
`fetch_mof.py`). Two definitional traps to map, already in the manifest notes:
- **Policy rate:** benchmark lending rate (pre-2019) vs **LPR** (monthly since
  Aug 2019) — a definitional break, two columns, annotated, never one line.
- **USD/CNY:** the PBoC daily **central parity / fixing (中间价)** and the
  **CFETS market close** are two series — never one. CNY per USD, rising = weaker renminbi.

## country.yaml decisions

- **Locales** `zh-Hans` (official-first) / `en` (default per precedent) / `pt`,
  following south-korea's non-Latin pattern (`code` = language not country,
  `html_lang`/`og_locale` carry region). `zh-Hans` → `html_lang zh-CN`,
  `og_locale zh_CN`, `endonym 简体中文`. `name` filled in en/fr/pt/es/ko +
  zh-Hans (the atlas names China on every other country's switcher too).
- **Wordmark** `中国`; `web.mark_bearing: "0"` — CJK glyphs are centred in a
  fixed em box (same reasoning as Hangul on the south-korea file).
- **Window** 2006–2026, `last_full_year 2025` (WB carries a full 2025 for GDP
  and population → 2025 is complete), `tick_every 2`.
- **Bands `[]`** — verified today: zero negative annual real-GDP years for CHN
  across 2006–2026 on both IMF and WB; COVID was a single-quarter contraction.
  The strict two-quarter test wants the quarterly series (NBS 403) — flagged on
  pending — but the annual evidence rules a two-quarter recession out on its own.
  2020 shock + 2022 / 2024-25 slowdowns go on the plates as **events**.
- **Palette** from the flag: red field (#DE2910) darkened to maroon `RED #9C1F2E`
  / `RED_D #75151F`, star gold (#FFDE00) darkened to amber `GOLD #C8961E` /
  `GOLD_D #A07814`, plus cool siblings. Chosen **distinct from Canada**
  (brick-red `#B5272F`) and **ahead of Vietnam's** planned red/gold sibling.
  `flag_bands` red · paper · gold (paper middle auto-outlined). Web chrome is a
  warm near-black, **not** a saturated red, because the money accent is a coral
  and a coral accent on a red ground is the one pair that cannot coexist.
- **Currency CNY.**

## Phase B note — number formatting already covered

`core/numstyle.py` (branch `plate-spine`) **already carries a `zh-Hans` style**:
it is in `STYLES`; `SEPARATORS` deliberately omits it (zh uses English marks —
`1,234.5`); `LADDERS["zh-Hans"] = ((1e12,"万亿"),(1e8,"亿"),(1e4,"万"))`. So the
big-number words the brief worried about (亿/万亿) are handled — a `money_bn` /
`usd_bn` / `money_tn` / `pop_mn` figure rescales onto the 万/亿/万亿 ladder
automatically. What remains for later phases is the `AFFIX` / `CURRENCY_AFFIX`
column for `zh-Hans` in `core/sitebuild.py` (元/¥ and the "% of GDP" form) and
the `zh-Hans` site/ui chrome — both additive core changes, not this lane's work.

## Pending list (in `SOURCES.yaml` under `pending`; none blocks the build)

1. **NBS machine API 403** — `data.stats.gov.cn/easyquery.htm` refuses every
   variant; portals are 200. Source official figures from the reachable
   portal/communiqués or an authenticated route in Phase B; never scrape a 403.
2. **GACC 412** — customs.gov.cn anti-bot. Use UN Comtrade (live) + NBS English
   portal as cross-checks; get a GACC route in Phase B.
3. **PBoC / SAFE / MOF endpoints** — portals live, series endpoints not isolated
   (LPR history, 中间价 vs CFETS close, reserves, budget execution).
4. **Security/homicide — likely none** — no credible public criminal-homicide
   series expected. Parked honestly, not scraped; the Security chapter may depart
   from the spine and must record that in `DATA_NOTES.md` later.
5. **Quarterly band confirmation** — annual evidence is conclusive (no negative
   year); the two-quarter q/q test needs the blocked NBS quarterly series.

## For the fetch swarm

Planned fetchers (named in `refreshed_by`): `fetch_comparables.py` (WB + IMF
DataMapper + UNDP — all live and already verified), `fetch_markets.py` (Yahoo
000001.SS), `fetch_comtrade.py` (UN Comtrade preview), then the blocked/parked
`fetch_nbs.py`, `fetch_gacc.py`, `fetch_pboc.py`, `fetch_safe.py`, `fetch_mof.py`.
Shape-check before caching (WB `[meta,[obs]]` with null holes preserved; IMF
229-country body → extract `values.<IND>.CHN`; Yahoo browser-UA). Every NBS/IMF
pair stays two labelled series; the DataMapper broad debt and the MOF narrow
debt never merge; 中间价 and the CFETS close never merge.
