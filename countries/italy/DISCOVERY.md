# Italy — Phase A discovery report (2026-10-22)

> Kept as the research pass's record. Where it disagrees with `SOURCES.yaml` or `DATA_NOTES.md` (both corrected in consolidation), those are right.

**Deliverables written** (in the `italy` lane, untracked, NOT committed per brief):
- `countries/italy/country.yaml` — slug `italy`, locales it/en/pt (it official-first, en default per repo precedent), window 2006–2026, last_full_year 2025, tick_every 2, three recession bands dated off Eurostat q/q SA growth, tricolore-derived palette, it/en/pt seo + sources blocks.
- `countries/italy/SOURCES.yaml` — 48 planned datasets across 9 directories + `meta.pending` (7 items), written before any CSV exists. Both files parse as YAML; full suite green without `countries/italy/` (493 passed); with it, the only failure is the expected `countries/italy/chapters.py does not exist` collection error — the documented manifest-only state.

## Publishers (all endpoints curl'd today, payload shape recorded)

**ISTAT — I.Stat SDMX** (base `https://esploradati.istat.it/SDMXWS/rest/data/{FLOW}/{KEY}`; the old `sdmx.istat.it` 302s to a dead end). Verified live: catalogue 4,961 dataflows; SDMX 2.1 GenericData default, CSV via `Accept: text/csv`. Flows verified with data: `163_156` GDP quarterly (2025 raw quarters sum €2,265,002.6mn = Eurostat's 2,265,002.5 to the decimal), `163_184_DF_DCCN_PILQ_1` (GDP+components, but B1GQ_1 empty — levels live in 163_156), NIC CPI `167_747_DCSP_NIC2B2025_1` (annual means 1996–2025 base 2015: 2024=120.8, 2025=122.6 → +1.5% ✓) + `167_745_DF_DCSP_NIC1B2025_1` (monthly from 2026, base 2025 — the rebase seam, same as Spain's IPC), labour `151_884`/`150_883` (2024 quarters 7.10→6.23, mean ≈6.6 vs Eurostat 6.5 ✓), population `22_289`, births `25_74` (national key verified: 2024=369,944 exactly), deaths `26_29_DF_DCIS_DECESSI_2` (shape verified; national key timed out under throttling — pin from DSD), life tables `26_295`, fertility `25_326_..._5`, poverty `34_727` (current, has 2025) vs interrupted `34_201` (ends 2013), migration `28_185` (anagraphic flows), `29_7` foreign residents (1-Jan-2025 = 5,371,251 = Eurostat FOR_STLS exactly ✓), `29_317`, permits stock `29_348`, citizenship acquisitions `29_849`, crime `73_67` (delitti denunciati, TYPE_CRIME=INTENHOM verified 0.6/100k 2024 — Min Interno SDI data via ISTAT), causes of death `39_494_DF_DCIS_CMORTE1_RES_1` (13 dims, 91-item European shortlist incl. assault codes; ~29MB/year unkeyed).
Quirks (all in SOURCES.yaml header): **EDITION dimension** on national accounts and labour flows stacks every vintage — pin latest or quarters repeat per vintage (2026M9→M10 revised 2025Q1 growth 0.338→0.393); "NoRecordsFound" = **HTTP 404**; short keys = HTTP 422; total codes vary per codelist (TOTAL/ALL/WORLD/99 — in births, `99` IS the marital-status total); unkeyed flows are heavy (births 22MB/2yr); server throttles after repeated large pulls.

**Eurostat** (geo=IT, Spain's fetcher patterns reused verbatim). Verified: nama_10_gdp, namq_10_gdp (used for band dating), gov_10dd_edpt1 (debt 2024 134.3%, 2025 136.7%; deficit 2024 −3.4, 2025 −3.1), gov_10q_ggdebt (2025Q4 €3,097.1bn — crossed €3tn in 2025 ✓ press), gov_10a_main (revenue 2024 46.9), gov_10a_taxag (needs Spain's key `na_item=D2_D5_D91_D61_M_D995&sector=S13_S212`; `TR` returns empty; 2024 = 42.3 ✓ MEF's own announced figure), gov_10a_exp COFOG (GF10 2024 21.3), une_rt_a (**starts 2009 for IT — 2006–08 blank, same hole as Spain**), prc_hicp_aind (2024 1.1), irt_lt_mcby_a (2012 5.49, 2025 3.59), ilc_di12 (**dim is `statinfo=GINI_HND`, indic_il → HTTP 400**; 2024 32.2), ilc_li02 (2024 18.9), demo_gind (pop 1-Jan-2025 58,943,464; births 2024 = ISTAT exact; deaths 653,109), demo_find (TFR 2024 1.18 record low). **Migration suite** all verified: imm1ctz 1998+, imm3ctb 2008+, emi1ctz, pop1ctz (**Italy quirk: foreign aggregate is `FOR_STLS`, `citizen=FOR` returns well-formed EMPTY — same silent-truncation family as Spain's unit=NR**), pop3ctb (FOR works: 2025 foreign-born 6,928,045), asyappctza unit=PER (2024 158,605; 2025 already present), resfirst unit=PER (2024 346,411), migr_acq (2024 217,448). **No EM/EMCR-style splice for Italy**: totals identical on both cuts 2008–2024, no break flags; the citizenship/birth contrast lives in the splits (non-EU flow split present from 2020).

**Banca d'Italia** — legacy Base Dati Statistica inquiry app verified scriptable: `POST https://infostat.bancaditalia.it/inquiry/home?calltype=asin&service=GETINQUIRYSCOPE` → JSON (session config, export limits). Bad calls return an HTML "Risorsa Protetta" page under HTTP 500 (endpoints-that-lie pattern). The 2023+ portal `statistiche.bancaditalia.it` is an Angular SPA over an undocumented relative `/api/` (pending). Wanted series: household+NPISH debt/disposable income, sofferenze NPL (December stocks — never sum months), household lending rates.

**MEF / RGS / Tesoro** — BDAP never connected (curl exit 6, like Spain's IGAE); rgs.mef.gov.it/tesoro.it are document portals. **Decision (Spain's): fiscal layer = Eurostat EDP transmission**; national-definition series beside it later if a clean endpoint verifies, never spliced.

**Ministero dell'Interno** — site live, crime pages document-oriented, no machine endpoint today. NOT blocking: ISTAT `73_67` carries the same SDI police record (verified homicide series). Second count = ISTAT causes-of-death assault codes (two-publishers-one-idea).

**ECB** — EXR and FM verified with CSV (`?format=csvdata`): EUR/USD 2026-10-21 = 1.1234; DFR now **2.50** (raised during 2026 from the 2.00 2025 year-end — data, take as-is).

**Comparables** — World Bank ITA verified (GDP 2024 US$2,383bn consistent with €2,211bn at 2024 FX; WB gini 2023 34.3 vs SILC 31.5 — two cuts of one survey); UNDP HDR25 CSV verified (ITA HDI 2023 = 0.915; **file is Latin-1, not UTF-8**). **Yahoo `FTSEMIB.MI` works** (2025-10-21 close 42,648.0; latest 49,643.69), `official: false`; **stooq `^ftsemib` is JS-walled** (verified: noscript verification page under HTTP 200, same as ^IBEX/^TSX).

## country.yaml decisions

- **Bands** (Eurostat namq_10_gdp CLV_PCH_PRE SCA, today's vintage): 2008Q2–2009Q2 five consecutive negatives → `2008.25–2009.5`; 2011Q2–2013Q1 eight consecutive → `2011.25–2013.0`; COVID `2020.0–2020.5`. Marginal cases documented in the band comment: 2013Q4–2014Q1 (−0.1 twice, within rounding — Italy's "third dip" debate) and **2019Q3–Q4 already negative (−0.5, −0.4), so the sign run into COVID is technically continuous from 2019Q3** — band marks the pandemic episode, the 2019 stall belongs in events.
- **Palette**: green-led (neither Spain nor Canada leads green): VERDE `#247A4B`, ROSSO `#A3282C`, flag_bands green/paper/red (paper middle → outline, as Canada), web chrome cool green-black (`#101712` ground) — distinct in hue from Spain's warm `#1E1210` and Canada's red `#1A1012`. mark_bearing 0.045em for "Italia" (I = plain stem, between A's 0.012 and F's 0.055).
- **name**: en Italy / fr Italie / pt Itália / es Italia / ko 이탈리아 (pattern confirmed from all six existing country.yaml files).

## Pending list (SOURCES.yaml `meta.pending`, none blocking)

1. **MEF/RGS/Tesoro (BDAP)** — unreachable; fiscal = Eurostat EDP (decision recorded).
2. **Min Interno direct crime portal** — document-only; police series staged via ISTAT 73_67.
3. **ISTAT Coeweb** (trade composition) — connection never established; trade levels from Eurostat P6/P7 + WB openness.
4. **stooq ^ftsemib** — JS-walled; Yahoo staged instead.
5. **BdI new-portal SPA API** — undocumented; infostat asin service is the verified path.
6. **Transparency International CPI** — hand-curated at build phase (France pattern).
7. **Labour pre-2021 continuity** — current-regulation flows vs `_UNT2020` old-regulation twins; Eurostat LFS hole 2006–08; fetcher must check backcast before drawing across 2020 (two columns if needed, never spliced).

## Flagged for later phases (not done, per brief)

- **`it` is a new locale** needing an `AFFIX`/`CURRENCY_AFFIX` column in `core/sitebuild.py` (currently keyed en/fr/pt/es/ko; the catalog test will fail without it — intended) — Phase B shared-code change. Italian candidates: `pct_gdp` → ("%","del PIL"), `pop_mn` → (""," M"), `per100k` → ("","/100 mil"), `years` → (""," anni"), EUR money_bn ("€","bn")/("€"," mld")? (Mld is the Italian billions convention — decide in Phase B), separators: Italian swaps like pt/es (`{",": ".", ".": ","}`).
- `site/ui.json` shared chrome needs `it` entries (build phase).
- The `it` locale means plates/chrome copy in Italian — chapters/i18n/ui/events are the build-phase swarm's, not written here.