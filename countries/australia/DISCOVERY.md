# Australia — discovery record

Research pass 2026-10-25, all probes made from the build network on that
date. Every route below states what it answered, so a later agent does not
re-walk a dead end and, more importantly, does not mistake a block for an
absence. `SOURCES.yaml` is the manifest; this is the walk that produced it.

## The short version

| publisher | route | result |
|---|---|---|
| ABS — SDMX gateway | `https://api.data.abs.gov.au/rest/…` (the documented URL) | **no DNS record** |
| ABS — SDMX gateway | `https://data.api.abs.gov.au/rest/dataflow/ABS` | **200**, 3.2 MB, 1 228 dataflows |
| ABS — SDMX gateway | `https://data.api.abs.gov.au/data/…` (no `/rest`) | 403 error page |
| ABS — website releases | `https://www.abs.gov.au/statistics/…/*.xlsx` | **200**, xlsx |
| ABS — website sitemap | `https://www.abs.gov.au/sitemap.xml` | 200, 8 pages of URLs |
| RBA — everything | `https://www.rba.gov.au/…` incl. `robots.txt` | **403 Akamai "Access Denied"** on every path, http and https |
| RBA — mirror | `data.gov.au` organisation `reservebankofaustralia` | holds one dataset, last updated 2013 |
| IMF — DataMapper (www) | `https://www.imf.org/external/datamapper/…` | **403 Access Denied** |
| IMF — SDMX | `https://api.imf.org/external/sdmx/2.1/…` | **200**, dataflows WEO, FM, MFS_IR, GFS_COFOG |
| OECD — SDMX | `https://sdmx.oecd.org/public/rest/…` | **200** |
| World Bank — API | `https://api.worldbank.org/v2/country/AUS/indicator/…` | **200** |
| BIS — API | `https://stats.bis.org/api/v1/data/…` | **200** |
| APRA | `https://www.apra.gov.au/…/QADI performance….xlsx` | **200**, 1.8 MB |
| BITRE | `https://www.bitre.gov.au/statistics/safety` | HTTP/2 stream reset; http/1.1 timeout, 0 bytes |
| BITRE — mirror | `data.gov.au` ARDD fatality CSV | **200**, 55 360 records, last resource dated **October 2023** |
| WHO — GHO | `https://ghoapi.azureedge.net/api/MH_12`, `RS_198` | **200** |
| UNDP — HDR files | `https://hdr.undp.org/sites/default/files/2025_HDR/…csv` | **200** |
| Transparency International | `https://www.transparency.org/en/cpi/2025` | 403 (Cloudflare) |
| Transparency International — CDN | `https://images.transparencycdn.org/images/CPI2025_Results.xlsx` | **200**, 3.1 MB Strict-OOXML |
| AIHW | `https://www.aihw.gov.au/reports-data` | 403 |
| Home Affairs | `https://www.homeaffairs.gov.au/research-and-statistics/statistics` | **200** (PDF/HTML reports only) |
| Yahoo Finance | `https://query1.finance.yahoo.com/v8/finance/chart/…` | 200 with a historical range, 429 on the default `range=1y` |

## The ABS SDMX gateway: the host is backwards

ABS documents its Data API at `api.data.abs.gov.au`. From this network that
name **has no DNS record at all** — not a block page, an NXDOMAIN, which is
why the first probe returns `Errno -5 No address associated with hostname`.
A public resolver confirms the name does not exist:

```
GET https://dns.google/resolve?name=api.data.abs.gov.au&type=A
  → Status 0, no Answer, Authority NS ns-1969.awsdns-54.co.uk
GET https://dns.google/resolve?name=data.api.abs.gov.au&type=A
  → 3.162.247.5, 3.162.247.78, …
```

The working host is `data.api.abs.gov.au` (`.data.api.` not `api.data.`),
and it answers **only** under `/rest`:

| request | status | body |
|---|---|---|
| `GET data.api.abs.gov.au/dataflow/ABS` | 403 | HTML error page, 919 B |
| `GET data.api.abs.gov.au/rest/dataflow/ABS` | 200 | SDMX 2.1 structure, 3 230 545 B |
| `GET data.api.abs.gov.au/rest/data/ABS,CPI/1.10001.10.50.Q?…&format=csv` | 200 | CSV |
| `GET data.api.abs.gov.au/rest/data/ABS,CPI,1.1.1/all` | 404 | `Could not find Dataflow and/or DSD` |

The dataflow id is the SDMX **flow** id (`CPI`, `ANA_EXP`, `LF`, `ERP_Q`,
`NOM_CY`, `BIRTHS_SUMMARY`, `DEATHS_SUMMARY`, `ERP_COB`, `MERCH_EXP`), not
the catalogue number, and the key is positional with one value per
dimension. The exact keys used, all verified 2026-10-25:

| flow | dimensions | key | series |
|---|---|---|---|
| ANA_EXP | MEASURE.DATA_ITEM.SECTOR.TSEST.REGION.FREQ | `C.GPM.SSS.10.AUS.Q` | GDP, current prices |
| ANA_EXP | " | `VCH.GPM.SSS.10.AUS.Q` | GDP, chain volume |
| ANA_EXP | " | `C.GFC.SSS.10.AUS.Q` / `C.GFC.GGS.10.AUS.Q` | GFCF, all sectors / general government |
| ANA_EXP | " | `C.XGS.SSS.10.AUS.Q` / `C.MGS.SSS.10.AUS.Q` | exports / imports |
| ANA_EXP | " | `VCH.GPM.SSS.20.AUS.Q` | chain volume, **seasonally adjusted** (band dating only) |
| CPI | MEASURE.INDEX.TSEST.REGION.FREQ | `1.10001.10.50.Q` | all groups, Australia, original, quarterly |
| LF | MEASURE.SEX.AGE.TSEST.REGION.FREQ | `M13.3.1599.20.AUS.M` | unemployment rate, persons, SA, monthly |
| ERP_Q | MEASURE.SEX.AGE.REGION.FREQ | `1.3.TOT.AUS.Q` | ERP, persons |
| ERP_COB | AGE.SEX.COUNTRY_BIRTH.REGION.FREQ | `TOT.3.1101.AUS.A`, `TOT.3.TOT.AUS.A` | Australia-born, total |
| NOM_CY | MEASURE.AGE.SEX.REGION.FREQ | `1.TOT.3.AUS.A`, `2…`, `3…` | arrivals, departures, net |
| BIRTHS_SUMMARY | MEASURE.REGION.FREQ | `1.AUS.A`, `3.AUS.A` | births, crude birth rate |
| DEATHS_SUMMARY | MEASURE.SEX.REGION.FREQ | `4.3.AUS.A`, `5.3.AUS.A` | deaths, crude death rate |
| MERCH_EXP | COMMODITY_SITC.COUNTRY_DEST.STATE_ORIGIN.FREQ | `TOT..TOT.M` | goods exports by destination |

Two traps found in the flow list and avoided:

- **No annual frequency in the national accounts.** `ANA_EXP` answers a
  request with `FREQ=A` with `NoRecordsFound`, and `MERCH_EXP` does the
  same. The annual series here are built from quarters/months
  (DATA_NOTES.md states the rule). The ABS *does* publish annual national
  accounts, but on a **fiscal** year and only in the website tables, so
  using them would have put a July–June denominator under a calendar-year
  numerator.
- **`PROV_MORTALITY_CAUSE` is a stale slice.** It answers, but its
  `TIME_PERIOD` values stop in 2022 and its monthly dimension is carried
  as a separate key, so it cannot produce 2023–24 COVID counts. The final
  Causes of Death release (cat. 3303.0) was used instead — Table 1.2 is one
  vintage covering 2015–2024.

## The ABS website: releases and the xlsx trap

`www.abs.gov.au` answers normally (CloudFront), and `sitemap.xml` →
`sitemap.xml?page=1..8` lists every release. The data-cube URLs are
predictable and were the main route for the three publications the SDMX
gateway does not carry:

- `government-finance-statistics-annual/2024-25/55120DO021_202425.xlsx`
  (Table 939, general government, all levels) — **200**, five sheets.
  Repeated downloads in a tight loop returned 404 twice before succeeding;
  the fetcher retries and validates the `PK` zip magic, so a transient
  404 cannot cache an HTML page.
- `recorded-crime-victims/2025/1. Victims of crime, Australia (Tables 1
  to 8).xlsx` — **200**. Note the reference year: the "2025" release
  covers calendar **2025** (435 homicides, 448 in 2024).
- `causes-death-australia/2024/2024_01 Underlying causes of death
  (Australia).xlsx` — **200**, 869 KB, Table 1.2 is the multi-year cut.
- `household-income-and-wealth-australia/2019-20/1. Household income and
  income distribution, Australia.xlsx` — **200**; this is the **last**
  HIES, which is why the Gini line stops in 2019-20.

The GFS publication is the one that shapes the spending chapter: its
current vintage carries only **ten fiscal years** (2015-16 to 2024-25), so
the national COFOG cannot fill a 2006–2026 axis. That is why the canonical
COFOG is the OECD's and the ABS table is the cross-check.

## The Reserve Bank of Australia is blocked at the network edge

Every path answers a 364–431 byte Akamai "Access Denied" page:

```
GET https://www.rba.gov.au/statistics/tables/                        403  387 B
GET https://www.rba.gov.au/statistics/tables/csv/f1.1-data.csv       403  431 B
GET https://www.rba.gov.au/statistics/tables/xls/f01d.xls            403  416 B
GET https://www.rba.gov.au/rss/rss-cb-exchange-rates.xml             403  421 B
GET https://www.rba.gov.au/robots.txt                                403  386 B
GET http://www.rba.gov.au/statistics/tables/csv/f1.1-data.csv        403  431 B
```

`robots.txt` being forbidden is the proof that this is not a missing file,
a bad path or a user-agent rule: the host refuses this network. Two routes
were tried around it:

1. **data.gov.au**, where the RBA is a registered publisher. Its
   organisation holds one dataset, "Monetary Policy Changes", whose only
   resource is `tmpEMhiwQa02hist.xls` uploaded **2013-05-12** and stopping
   in 2013. A stale mirror is a route result, not a source.
2. **The IMF's IFS via `api.imf.org`**, which does carry Australia's
   policy rate (`MFS166`), bank lending rate (`MFS162`), 10-year yield
   (`S13BOND`) and money-market rate (`MMRT`). It answers — and **every one
   of those series except the policy rate stops in 2019**, with the policy
   rate itself ending in 2024. A lending-rate line that stops in 2019 is
   not a panel on a 2006–2026 axis.

What fills the market slots instead:

- **Policy rate** → BIS `WS_CBPOL` (`M.AU`), monthly end-of-period, whose
  own metadata names the Reserve Bank of Australia as the source and the
  cash rate target as the series. Official, same numbers, different door.
- **10-year yield** → OECD `DSD_STES@DF_FINMARK`, monthly.
- **Currency** → World Bank `PA.NUS.FCRF` annual average (no central-bank
  dependency, and the same vintage converts the minimum wage).
- **Credit** → BIS `WS_TC` for the stock and APRA for the NPL ratios.
- **Household lending rate** → **not filled**. See below.

## IMF: the website is blocked, the SDMX API is not

`www.imf.org` (including the DataMapper API every other country's fetcher
uses) answers 403 Access Denied, but `api.imf.org/external/sdmx/2.1/`
answers 200 with 223 dataflows. Two matter:

- **FM** (`IMF.FAD,FM,5.0.0`) — the Fiscal Monitor's key indicators for
  Australia: revenue, expenditure, net lending, primary balance, gross
  debt, all % of GDP, 2000–2031 with projections past the vintage year.
  This is the fiscal chapter's canonical series.
- **WEO** (`IMF.RES,WEO,9.0.0`) — `NGDP_RPCH`, the calendar-year growth
  cross-check.

The fiscal-year label was **verified, not assumed**: the Fund's "2025"
revenue is 36.67% of GDP and the ABS's FY2024/25 GFS revenue is 36.81%.
If the Fund were labelling by the starting year the pair would be 3 points
apart. It labels by the ending year, which is why the manifest says so.

## What the other publishers answered

- **World Bank** — every indicator used returns 200 with JSON. Two
  findings worth keeping:
  - `NY.GDP.MKTP.KD.ZG` for Australia is on a **fiscal-year** basis
    labelled by the ending year (2020 = −0.13, i.e. FY2019/20, against a
    calendar 2020 of −2.10). It is not used.
  - `SI.POV.HIC` (the $8.30/day line) is **empty** for Australia; only
    `SI.POV.UMIC` ($4.20/day) exists, 2008–2020.
- **OECD** — `DSD_NASEC10@DF_TABLE11` returns 25 840 Australian rows for
  2006+, but only in national currency: there is no percent-of-GDP unit in
  the Australian slice, so the ratio is computed against ABS GDP. The
  minimum-wage flow needs `PAY_PERIOD=W` filtered out of three pay periods
  (weekly, hourly, annual) or the 2025 value comes out as A$24.53.
- **BIS** — `WS_TC` household credit, quarterly to 2026-Q1, % of GDP,
  adjusted for breaks; `WS_DSR` household debt-service ratio;
  `WS_CBPOL` policy rates to 2026-09.
- **APRA** — the QADI performance workbook (1.8 MB) has 60 sheets. Table
  1g carries two asset-quality ratios on two definitions: "impaired
  facilities" to December 2021 and "non-performing" from 2022 — the 2022
  definition change is the reason the credit plate carries two columns.
  No interest-rate series exists in the workbook.
- **BITRE** — `www.bitre.gov.au` resets the HTTP/2 stream and times out on
  http/1.1 with zero bytes; `infrastructure.gov.au` behaves the same way.
  The data.gov.au ARDD mirror is real but frozen at October 2023.
- **WHO GHO** — `MH_12` (suicide, age-standardised) 2000–2023 and
  `RS_198` (road deaths, modelled) both answer. Only `MH_12` is drawn: the
  road-death estimate is a model, and the national count exists for the
  years it covers.
- **UNDP** — the 2025 HDR composite-indices CSV is one file covering
  1990–2023 for every country, which is the one-vintage property the HDI
  needs.
- **Transparency International** — the site 403s, the CDN file answers.
  The workbook is **Strict OOXML** (`purl.oclc.org/ooxml/…`), which
  openpyxl refuses: `wb.sheetnames` is `[]`. The fetcher unzips the file
  and reads `xl/worksheets/sheet6.xml` ("CPI Historical") directly,
  resolving shared strings. The historical sheet starts in 2012.
- **Yahoo Finance** — the chart API answers 200 for an explicit
  `period1/period2` range and 429 for the default `range=1y`. Monthly FX
  history is incomplete before 2008, so the equity conversion uses the
  World Bank's annual-average rate instead.
- **Home Affairs** — the statistics portal answers 200 but publishes
  reports (PDF/HTML), not a machine series for the Migration Program.

## Slots that are deliberately empty

Recorded in `SOURCES.yaml` `meta.pending` with the exact endpoint and
failure: the RBA's tables; the household lending rate; road deaths
2023–2025; a national poverty rate; the pre-2012 CPI; the Migration
Program lens. None of them is empty because nobody looked.

## What a Phase B agent inherits

- 26 curated CSVs under `data/`, each with a manifest entry, a sidecar
  trail and a note.
- Six fetchers that re-run to byte-identical files online and write
  nothing offline-cold (verified 2026-10-25).
- A calendar-year/fiscal-year seam that is labelled in every file and note,
  so the fiscal plate's x-axis is a decision already made rather than a
  surprise.
