# Israel — discovery report (Phase A data pass)

Written 2026-10-22 in lane `.slim/worktrees/israel` (branch `israel`,
off main 272cc7b). Research pass per `SOURCING_A_COUNTRY.md` §3:
publishers named, endpoints curl'd live today, payload shapes recorded,
`SOURCES.yaml` written before any CSV. No fetchers, plates, chapters,
i18n, ui or events here — and no CSVs staged. `SOURCES.yaml` is the
authority where this file is looser.

Israel is the atlas's first right-to-left country. Per COUNTRIES.md the
RTL page/grid/font/bidi work is unbuilt Phase B/C work; this pass
records only what the **data layer** needs.

---

## The shape of this country's sourcing

The headline finding is the inverse of Canada's StatCan outage: here
the **national statistical office as a whole** is unreachable from
scripted clients on this machine, and a large part of the official
domestic layer (CBS) is parked with a route mapped for reopening it.
What IS verified is unusually good: the government open-data portal
(data.gov.il, CKAN + datastore) carries the migration chapter and the
police crime files in queryable, machine-readable form; the Bank of
Israel publishes a live JSON FX API; and Israel sits fully inside the
international layer — World Bank, IMF WEO, UNDP and the OECD, whose
SDMX API even carries Israel-specific LFS flows. The harmonised layer
is doing what it exists to do; the national series of record stay
parked until CBS is reachable, and nothing is spliced across them.

## Publishers, in the order SOURCING §2 asks for them

### 1. CBS Israel — the national statistical office. BLOCKED, parked.

Endpoints probed 2026-10-22:

| URL | Result |
|---|---|
| `www.cbs.gov.il/en/pages/default.aspx` | TCP reset **after** a completed TLS handshake (real `*.cbs.gov.il` DigiCert cert, TLSv1.2, server at 192.114.84.16) |
| `cbs.gov.il/...`, `data.cbs.gov.il/en`, `/api`, `/Query` | same reset |
| `data.cbs.gov.il/` | 403 |
| `data.cbs.gov.il/en/help` | 200 — Hebrew/English **"Oops, Something is wrong"** error page |
| `www.cbs.gov.il/reader/?TD=510...`, `/en/pages/pilot_api.aspx` | 200 — same error page (JS `go2cbs()` redirect) |

Two distinct failure modes: connection resets, and error pages served
under HTTP 200 — exactly the "endpoints that lie" trap, so presence
tests here are worthless. The API key application flow (the CBS
"pilot_api" DataHub) is browser-side only. CBS is the publisher of
record for national accounts, CPI, LFS, population (incl. the annual
**Rosh Hashanah release**, preliminary-vs-final vintage trap), vital
statistics, causes of death, income/inequality and goods trade. All
parked under that one reason.

data.gov.il hosts CBS under the Hebrew acronym org **`lamas`** (14
datasets), but they are census/geographic/road-accident microdata —
no CPI/GDP/LFS time series. Re-probe with an API key or a browser-side
route; until then the macro plates fall back to the harmonised layer,
labelled as such.

### 2. Bank of Israel — central bank. Partially verified.

The redesigned portal (`boi.org.il/en/data/`) is a JS SPA; its
118KB shell contains no server-side data links. But:

- **Verified live JSON API:** `https://www.boi.org.il/currency.xml`
  301-redirects to **`https://boi.org.il/PublicApi/GetExchangeRates`**
  — payload `{"exchangeRates":[{"key":"USD","currentExchangeRate":
  3.107,"currentChange":...,"unit":1,"lastUpdate":"2026-10-22T12:22:
  03Z"},...]}`. ILS per foreign unit; **JPY-style rows carry
  `unit:100`** (rate per 100 units) — divide by `unit` in the fetcher.
  It is an intraday snapshot of the representative rate, not history.
- `PublicApi/GetInterestRate(s)`, `GetCPI`, `GetMortgageRates`,
  `GetGovernmentBonds`: 404. Several other paths return a **Radware
  bot-challenge loader page under HTTP 200** — another lying endpoint;
  a 200 here proves nothing.
- The `bank_israel` org on data.gov.il (30 datasets) advertises the
  *old-site* files, all now dead: `meshulav_luah_heb.xls` (CPI
  composite, 404), `yaz0106.zip` (daily FX history, 404),
  `pribmash.xls`/`mashfix.xls` (mortgage rates, 404), dataset 381
  (mac"m yields) links to the retired `www.bankisrael.gov.il/series/`
  catalogue. data.gov.il metadata is a graveyard on this org — check
  every resource URL before trusting the manifest.

Policy rate, FX history, reserves: parked pending the BoI MSIB data
portal mapping or hand curation from the Monetary Committee pages
(future decision dates — 2027 — are already in the site's sitemap, a
good curation anchor).

### 3. MoF / Accountant General — fiscal. Parked; IMF verified beside.

`agf.gov.il` NXDOMAIN; `budgets.gov.il` NXDOMAIN; no MoF org on
data.gov.il; `mof.gov.il` resolves (the standard gov.il MoF pages)
but no machine-readable endpoint was found this pass. Verified fiscal
fallback: **IMF DataMapper** —
`https://www.imf.org/external/datamapper/api/v1/GG_DEBT_GDP/ISR`
(2024: 67.8% GDP; 2020: 71.1%) and `NGDP_RPCH` (2009 **-2.8**, 2020
-1.9, 2023 +2.0, 2024 +1.7). Quirk: the `/ISR` path segment does not
filter — every country returns; filter client-side. WEO projections
live in the same object (to 2031) and need their own columns. Israel's
own D7 debt definition (cash-basis AGF vs general-government IMF —
the §4 two-publishers trap) stays parked; when it lands, two columns.

### 4. Migration — PIBA + Aliyah and Integration. Verified, and the chapter's definitional spine is visible in the data.

CKAN on **data.gov.il**, `datastore_search` verified live today:

- `new-olim-by-years` (Ministry of Aliyah and Integration):
  **person-level PUF** — `year_aliya, month_aliya, age, gender
  (זכר/נקבה), erez_moza, subcont, yeshuv_klita, machoz, mikzoa`,
  rows through 2025-09; siblings `new-olim-by-month`,
  `new-olim-by-cities`, 1989–2015 age/profession cuts. Aliyah is the
  **Law of Return (1950/1952)** flow — a legal category with no
  foreign analogue: olim are not "visa holders", and the §4a rule
  bites hard here — never sum olim with work permits or asylum
  seekers into one immigration line; flow (this) vs stock (population
  register) in separate panels.
- `stats_rish` (PIBA): monthly visa/permit issuance, Hebrew columns
  (`אשרה` class, `תת־אשרה` subclass, `ארץ דרכון` passport country)
  and crucially three count columns — `חדשים` (new) vs `הארכות`
  (extensions) vs `תיקונים` (amendments). That is `migr_resfirst`
  vs `migr_resvalid` made concrete: only `חדשים` behaves like a
  first-permit flow. Stocks parked.
- Asylum (PIBA/ASO): no dataset found; parked with the §4a four-
  numbers rule noted.
- Population stocks (CBS register): parked with CBS; WB `SP.POP.TOTL`
  verified as cross-check (2024: 10.00mn — the country crossed 10mn
  in 2024).

### 5. Israel Police — crime. Verified, short window.

`crime_records_data` (org `israel-police`): one dictionary CSV
(crime group/type codes and names, `SensitivityFlag`) plus **one CSV
per year 2021–2025** of *cases by region × quarter × crime type*,
all in the datastore. Homicide is a crime type inside this taxonomy
(map via the dictionary). 2006–2020 is not on the portal; the CBS
death-certificate homicide second count (§4a) is parked with CBS.

### 6. Vital statistics / causes of death — CBS-only. Parked.

### 7. The market — nobody official.

- **Yahoo Finance, verified:**
  `query1.finance.yahoo.com/v8/finance/chart/%5ETA125.TA?range=max&
  interval=1mo` → TASE **TA-125** monthly closes back to **1992**
  (409 obs). Year-ends: 2006 958.3 · 2010 1203.8 · 2015 1246.2 ·
  2020 1624.1 · 2024 2500.6 · 2025 3995.6 (latest 4067.9).
  `interval=1y` is rejected; derive year-ends from 1mo. `^TA35.TA`
  is 404 — TA-35 parked. `official: false` regardless.
- **stooq:** JS browser-challenge under HTTP 200, as expected — dead
  from this machine.

### 8. Comparables — all four bodies, verified.

- **World Bank** (JSON, `[meta, rows]`): GDP 513.4/542.3/610.8bn for
  2023/24/25; population above; `lastupdated 2026-10-08`.
- **UNDP** HDR25 CSV: ISR row present, Very High, rank 27.
- **IMF DataMapper** (above).
- **OECD SDMX REST** — `https://sdmx.oecd.org/public/rest`: agency
  `OECD.SDD.TPS` dataflow list is live (~800KB); **Israel-specific
  flows exist** — `DSD_LFS@DF_IALFS_INDIC` pulled live: **1,059
  series, generic SDMX-XML**, quarterly to 2026-Q2 (and monthly) in
  one payload. Key quirks for the swarm: nine key segments
  (`ISR........`); `response_format` is *not* a parameter (Accept
  header only); `dimensionAtObservation` accepts only the DSD's own
  dimensions. Inequality IDD = `OECD.WISE.INE, DSD_WISE_IDD@DF_IDD`
  (version not resolved — parked). This is the harmonised migration/
  labour/inequality layer that pairs with the national series like
  Eurostat does for EU countries.

## RTL — what the DATA layer needs (Phase B/C is elsewhere)

- `he` is a new locale and script. `core/numstyle.py` (plate-spine,
  read-only) **already defines the `he` number style**: CLDR-he uses
  English decimal/grouping marks, and the module itself states it
  does numbers/affixes only — bidi (direction, RLM) is the page's
  job. So no data-side number surprises.
- `AFFIX`/`CURRENCY_AFFIX` need `he` columns in Phase B (ILS: ₪
  symbol convention), as COUNTRIES.md already flags for new locales.
- The CSVs stay plain LTR files; but **cell values from
  data.gov.il are Hebrew strings** (gender, passport country, visa
  class, crime names, settlement names, UTF-8). Fetchers must keep
  UTF-8 and map Hebrew values → stable codes so any locale can label
  them; never embed Hebrew display strings as join keys.
- The Rosh Hashanah population release is a *calendar* quirk, not a
  script one: the Hebrew calendar pins it to Sept/Oct; record release
  date per vintage in DATA_NOTES when CBS lands.

## Bands (record what the data say)

- **2008–09:** IMF WEO (current vintage) shows Israel **+3.8 (2008)
  then -2.8 (2009)** — a contraction year, so the band is defensible
  on annual data; the two-quarter q/q test still awaits CBS quarterly
  (parked). Band kept.
- **2020:** -1.9% — qualifies.
- **2023– war period:** annual growth stayed positive (+2.0, +1.7;
  2025 +3.5) and debt jumped 61.5 → 67.8% of GDP. Whether the q/q
  contractions after Oct 2023 meet the two-quarter rule needs CBS
  quarterly — parked, band marked candidate. Events annotate the
  data; no editorialising.

## country.yaml decisions this pass

Slug `israel`; locales he (he-IL/he_IL, endonym עברית) · en (default
per precedent) · pt; `name` in en/fr/pt/es/ko/he. Window 2006–2026,
`last_full_year` 2025, `tick_every` 2, currency ILS. Palette: darkened
saturated flag blue `#0B3D91` primary, cool siblings, oxblood alert —
collision-checked against canada/korea/UK plate blues and the five
existing near-black web grounds (canada #1A1012, spain #1E1210,
portugal #101A14, UK #0D1220, korea #0A1E31); Israel gets the one
*saturated* dark-blue ground (#0B2447). Italy's ground re-check at
merge (queued, not in tree). seo he/en/pt; sources block names CBS
Israel, BoI, MoF and PIBA (he/en/pt) and must match SOURCES.yaml.
Hebrew strings in seo were proofed (a first draft had a corrupted
word — fixed).

## Pending list (nothing blocks the lane)

1. CBS whole-portal block (resets + 200-error pages); API key is
   browser-side. Everything CBS-only parked with it.
2. BoI beyond `PublicApi/GetExchangeRates`: policy rate, FX history,
   reserves, mac"m yields, mortgage rates (old URLs 404; SPA unwalled
   mapping needed; Radware 200-loader guard against naive paths).
3. MoF/AGF machine-readable budget execution & D7 debt.
4. OECD inequality flow version (`DSD_WISE_IDD@DF_IDD`) and the
   EMN/PIP migration tables key.
5. Asylum (ASO) endpoints; PIBA permit stocks.
6. Police crime years before 2021.
7. TA-35 symbol (if wanted beside TA-125).
8. Italy's web ground at merge; `mark_bearing` for the Hebrew
   wordmark (Phase B masthead).
9. WB PA.NUS.FCRF annual FX average as FX-history stopgap (pattern
   verified, indicator not yet pulled).
