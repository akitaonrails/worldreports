# Chile — discovery record, 2026-10-25

What was probed for Chile, what answered, what did not and how it failed,
what was chosen and why. Phase A only: no plates, no chapters, no copy.
Everything below was run from this worktree's network on 2026-10-25; the
national probes are reproducible with `countries/chile/fetch/fetch_*.py`,
and every one of them prints the HTTP status and the first bytes of the
body rather than a summary of them.

The short version: the harmonised layer answered completely, and almost
every Chilean publisher answered as a web page. MINSAL/DEIS through
`datos.gob.cl` is the one national body that served a machine-readable
file, and it carries the mortality chapter. The rest of the national
layer is recorded in `SOURCES.yaml` `meta.pending` with the exact
endpoint and the failure mode.

---

## 1. Route table

Status codes are what came back, not what the site says about itself. A
row marked **bot wall** returned HTTP 200 with an anti-automation page,
which is the failure mode this repository treats as the most dangerous:
it parses as something.

| Publisher | Endpoint probed | Status | What came back | Outcome |
|---|---|---|---|---|
| Banco Central de Chile | `si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?function=GetSeries&timeseries=G073` (anonymous) | 200 | HTML error page, redirect to `ErrorPage.htm` | no data |
| Banco Central de Chile | same, with dummy `user`/`pass` | 200 | JSON `{"Codigo": -5, "Descripcion": "Invalid username or password"}` | API is credentialled; token by registration |
| Banco Central de Chile | `www.bcentral.cl/web/guest/estadisticas` | 200 | Incapsula bot wall | no data |
| Banco Central de Chile | `si3.bcentral.cl/estadisticas/Principal1/Excel/CCNN/PIB/PIB_trimestral.xls` | 200 | HTML page, not a workbook | no data |
| Banco Central de Chile | `si3.bcentral.cl/Siete/ES/Siete/Cuadro/.../PM_TPM` | 200 | HTML shell, grid filled by JavaScript | no data |
| INE | `stat.ine.cl/` | 200 | login shell ("INE.STAT") | no anonymous statistics |
| INE | `stat.ine.cl/api/v1/auth/login` | 404 | empty | documented API tree not served |
| INE | `ine.gob.cl/.../indice-de-precios-al-consumidor` | 200 | HTML; links only monthly bulletins as PDF | no index file |
| INE | `ine.gob.cl/.../proyecciones-de-poblacion` | 200 | HTML; narrative and PDFs | no projection file |
| INE | `datos.gob.cl` INE organisation | 200 | 63 catalogue entries, IPC and ENE included, **0 resources each** | stale catalogue pointing back at ine.gob.cl |
| Dipres | `dipres.gob.cl/598/w3-channel.html` | 200 | Drupal HTML; article pages and PDFs | no file index |
| Dipres | `dipres.gob.cl/598/w3-propertyvalue-21469.html` | 404 | — | site restructured |
| Dipres | `dipres.gob.cl/597/w3-multipropertyvalues-15199-37782.html` | 200 | HTML listing | workbooks attached per article |
| CMF | `cmfchile.cl/portal/estadisticas/626/w4-propertyname-619.html` | 200 | HTML, client-side grids | no file |
| CMF | `cmfchile.cl/institucional/estadisticas/archivos/.../SP_A.rar` | 403 | — | blocked |
| Aduanas | `aduana.cl/.../port/estadisticas.html` | 200 | HTML, query form | no file |
| Aduanas | `aduana.cl/.../port/compendio.html` | 404 | — | — |
| SII | `sii.cl/sobre_el_sii/estadisticas_de_empresas.html` | 200 | per-year HTML pages | no series |
| SII | `sii.cl/estadisticas/inicio.htm` | 404 | — | — |
| MINSAL / DEIS (via datos.gob.cl) | `DEF_SEMANA_EPIDEMIOLOGICA.csv` | 200 | 141,920 rows, pipe-delimited, 6.3 MB | **staged** |
| Mintrab | `mintrab.gob.cl/` and `?s=ingreso+minimo+mensual` | 200 | WordPress HTML, news posts | no data |
| ChileAtiende | `chileatiende.gob.cl/fichas/18028-ingreso-minimo-mensual` | 404 | — | no table |
| BCN | `bcn.cl/leychile/` | 200 | HTML law database (statutes, not a series) | next route for the minimum wage |
| INE | `ine.gob.cl/.../estadisticas-vitales` | 404 | — | cause-of-death tables are annual PDFs |
| datos.gob.cl | `package_search?q=covid` | 200 | 165 datasets, all procurement and mining; no death counts | no data |
| Bolsa de Santiago | `bolsadesantiago.com/api/...` | 200 | Radware captcha page | no data |
| World Bank API | `api.worldbank.org/v2/country/CHL/indicator/...` | 200 | JSON, vintage 2026-10-08 | **staged** |
| IMF DataMapper | `imf.org/external/datamapper/api/v1/{code}` | 200 | JSON (403 to `urllib`'s default UA; needs a browser-shaped one) | **staged** |
| BIS | `stats.bis.org/api/v1/data/WS_CBPOL/D.CL/all` | 200 | SDMX-CSV, 5,433 daily observations | **staged** |
| BIS | `stats.bis.org/api/v1/data/WS_TC/Q.CL.H.A.M.770.A/all` | 200 | SDMX-CSV, 85 quarters | **staged** |
| BIS | `stats.bis.org/api/.../WS_DSR/Q.CL` | 404 | — | Chile not in the BIS debt-service table |
| OECD SDMX | `sdmx.oecd.org/.../DSD_NAAG_VI@DF_NAAG_OTEF,/A.CHL.OTES13F...` | 200 | SDMX-CSV, COFOG 2018-2024 | **staged** |
| OECD SDMX | `.../DSD_NAAG_VI@DF_NAAG_VI,/A.CHL.P51GS13...` | 200 | SDMX-CSV, government GFCF 2007-2012 | **staged** |
| OECD SDMX | `OECD.ELS.SAE,DSD_EARNINGS@MW_CURP` (minimum wage) | 404 | NoRecordsFound for CHL | no data |
| UNDP | `HDR25_Composite_indices_complete_time_series.csv` | 200 | Latin-1 CSV (not UTF-8), HDI 1990-2023 | **staged** |
| Transparency International | `CPI2025_Results.xlsx` | 200 | xlsx that `openpyxl` refuses (invalid defined names); read from OOXML | **staged** |
| UN Comtrade | `comtradeapi.un.org/public/v1/preview/C/A/HS?...reporterCode=152&period=2024` | 200 | JSON, 178 partner rows | **staged** |
| WHO | `covid19.who.int/WHO-COVID-19-global-data.csv` | 200 | the dashboard's **HTML page** where the CSV used to be | no data |
| Yahoo Finance | `query1.finance.yahoo.com/v8/finance/chart/^IPSA` | 404 | `No data found` (also for `IPSA.SN`) | no data |
| ILOSTAT | `webapps.ilo.org/ilostat-files/...MW_CUR_NB_A.csv.gz` | 403 | — | no data |

Two things worth keeping from that table. First, the Banco Central is the
best-documented API in the country and the only one that tells you
plainly what went wrong (`Codigo: -5`), which makes it a route that will
work the day somebody registers a token. Second, `datos.gob.cl` is not a
mirror of the statistics offices: it carries 63 INE datasets whose
resources were stripped years ago, so a resource count of zero there is
not evidence that a statistic does not exist.

---

## 2. What was chosen, and why

**The national layer that exists.** MINSAL/DEIS's weekly deaths file is a
genuine national publication: 16 regions × 2 sexes × 5 age bands × week,
with the population of each cell in the same row. Summed to the year it
gives registered deaths, and summed across cells it gives INE's projected
population. That is the mortality chapter's national line and this
country's only `official: true` dataset.

**The rest is the harmonised layer, labelled as such.** World Bank,
IMF, BIS and OECD carry nearly every canonical slot for a country that
reports to all four, and every one of them is `official: false` in
`SOURCES.yaml` because the page prints an Official column and the
harmoniser is not the publisher. Where the harmoniser is republishing a
Chilean series (the CPI, the policy rate, the exchange rate, the national
accounts), the note says whose series it is.

**One year, not a series, for trade partners.** UN Comtrade's free
preview is capped at recent periods and its full API needs a key, so
`trade/partners_2024.csv` is 2024 as a snapshot for a lens slot. The
fetcher asserts that China is the top destination and that the partner
rows cover 100% of the world total, which is what will fail loudly when
the year changes.

---

## 3. Definitional traps found in this country

**The CPI changed base twice.** The index is base 2018 = 100 up to the
2023 rebasing and base 2023 = 100 after it. The World Bank's annual
percentage change is already a chain, so the staged inflation column does
not carry the seam; a future national index line would, and the note in
`SOURCES.yaml` says so before anyone draws it.

**CASEN is biennial and has been rebased.** The Gini and the national
poverty rate are not annual series: 2006, 2009, 2011, 2013, 2015, 2017,
2020, 2022, 2024. The poverty line itself changed in 2013 and again with
the 2017 survey, so the level is not one method across the window. Blank
years are years without a survey.

**Two fiscal perimeters, and the one Chile argues about is neither of the
harmonised ones.** The IMF series staged here is general government. The
country's public argument is about the **central government** and its
**structural balance rule** — a cyclically adjusted target computed on
copper's long-run price — which Dipres publishes and which is not
retrievable mechanically (see `meta.pending`). The general-government
line is canonical for the atlas; it is not the rule the budget is written
against, and the plates must not imply that it is.

**Customs and the balance of payments are different trade series.** The
national-accounts basis (goods **and** services, `trade/trade.csv`) and
the customs goods-only basis (`trade/partners_2024.csv`) differ by the
services balance and by valuation. They are two files and are never
spliced.

**Copper is a price, not a policy.** Every fiscal and trade swing in this
window tracks the copper price and the terms of trade: the 2006-07
surplus, the 2009 deficit, the 2021-22 revenue spike and the 2022
rebound. An annotation that reads the 2022 surplus as austerity or the
2020 deficit as profligacy is reading the price of a metal. The data
cannot settle that; the notes say which years are price-driven.

**Pension-fund withdrawals are not household debt and not saving.**
Between 2020 and 2021 Chileans withdrew about 10% of GDP from the
pension system, which raised household **deposits** and consumption. The
credit series here is credit from all sources, % of GDP: it peaks in 2020
for reasons of denominator as much as numerator (GDP fell 6.1%). The
withdrawals belong in the lens and never inside the debt line.

**The population denominator is not one series.** DEIS embeds INE's
projection (2019: 19,107,216); the World Bank publishes the UN series
(2019: 19,197,744), about 0.5% higher. Deaths divided by the wrong one
moves a crude rate by 0.03 per 1,000, which is small but not nothing on a
0-16 axis. `mortality/mortality.csv` carries both rates in two columns.

**Sixteen regions, but not the same sixteen.** Ñuble was created from
Biobío in 2018. National totals are unaffected, so the staged series does
not break — but any future regional cut has to say which map it is on.

**Migration ran at 9.5 per 1,000 in 2019.** The 2018-2023 wave (Venezuela,
Haiti, Colombia, Peru, Bolivia) is the largest in the country's history,
and the UN's net-migration residual puts 2019 at 181,339 people. The
stock series is five-yearly and measures the **foreign-born**, which is
not the foreign-citizen population: naturalisations move the second
without moving the first. Immigration and emigration flows from SERMIG
and INE are pending.

**Homicide has two publishers and they disagree.** UNODC's series (staged)
is a compromise between the police record and the death certificates.
Chile's own Carabineros/PDI count and the Fiscalía's are separate series
on separate bases; the post-2020 rise appears in all of them, which is
the finding, but the levels are not interchangeable.

**The peso is not a unit across thirteen years.** 530 to the dollar in
2006, 951 in 2025. Nominal CLP levels appear only as annotations; the
markets plate indexes 2006 = 100, and card figures are in dollars.

**`2026` is a running year everywhere.** INE's September 2026 IPC bulletin
exists, the BIS policy rate has 201 trading days, BIS household credit has
one quarter with no Q4, and DEIS's 2026 rows carry zeroes for weeks that
have not happened. `last_full_year` is 2025.

---

## 4. Recession bands

The bands in `country.yaml` come from the staged GDP vintage only:
`macro/economy.csv: real_growth_pct < 0` gives 2009 (-1.12) and 2020
(-6.14). Nothing else in the window contracts on an annual basis — 2014,
2017 and 2023 are near-zero but positive (0.68 in 2023), and a band drawn
on a quarterly definition would not match this annual series. Phase B
should assert the list against the CSV.

---

## 5. What is not drawn, and why

Twelve series are recorded as pending in `SOURCES.yaml` `meta.pending`,
each with its exact endpoint and failure. The four that matter for the
spine are:

- **markets slot 2, the 10-year yield** — the Banco Central's series is
  behind a token and the BIS does not compile a 10-year benchmark for
  Chile. The slot is pending, not proxied by the policy rate.
- **markets slot 4, the equity index** — the Bolsa de Santiago's API is
  captcha-walled, Yahoo has no IPSA symbol, stooq challenge-blocks. This
  is the country's one canonical slot with no route at all.
- **people slot 3, the minimum wage** — Chile has a statutory minimum
  wage; it is set by law and reajustado every year, and no machine-
  readable official series answered. The slot is pending rather than
  transcribed from memory, which is the one place this lane chose to leave
  a hole instead of closing it with a number nobody could check.
- **mortality slot 3, COVID-19 deaths** — DEIS's weekly file has no cause
  column, WHO's global CSV now serves an HTML page, and no cause-of-death
  resource exists on `datos.gob.cl`. All-cause excess deaths are staged
  and are not a substitute for the cause-specific count.

`spending/cofog.csv` starts in 2018 because that is when Chile began
reporting COFOG to the OECD, and `spending/public_investment.csv` stops
in 2012 because the OECD series did. Neither is back-filled. The
2006-2017 functional split could be built from Dipres' national
classification, which is a mapping rather than a source, and that
decision belongs to Phase B with the plates in front of it.
