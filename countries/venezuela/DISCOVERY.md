# Venezuela — Phase A discovery report

Research pass run in the `venezuela` lane on **2026-10-25**, against the
brief's expectation that the national statistical system would be largely
unavailable. It is — but not in the way the brief expected: the INE's live
domain is `ine.gob.ve`, not `ine.gov.ve`, and it does serve machine-readable
tabulados; it simply does not serve the CPI or the national accounts, which
belong to a central bank that cannot be reached at all.

Every endpoint below was probed live today. HTTP codes are what the probe
returned; "timeout" means no TCP connection within the client's limit; "TLS"
means the handshake failed before any HTTP status existed. `SOURCES.yaml` and
`DATA_NOTES.md` are authoritative where they differ from this report.

**Delivered:** `country.yaml`, `SOURCES.yaml` (15 datasets, 16 recorded gaps),
`DATA_NOTES.md`, five fetchers, 15 curated CSVs, and this record.

---

## 1. Route table

### National publishers

| # | Publisher | Endpoint probed | Result (2026-10-25) | Meaning |
|---|---|---|---|---|
| 1 | INE | `https://ine.gov.ve/`, `http://ine.gov.ve/` | timeout, no TCP (25 s) | The domain in the brief is dead. Not the publisher. |
| 2 | INE | `https://ine.gob.ve/` | **200**, 615,190 bytes | Live WordPress portal. This is the national statistical office. |
| 3 | INE | `https://ine.gob.ve/economicos/` | 200, prose only | Describes an "SIEE"; links no CPI, no INPC, no national accounts. |
| 4 | INE | `https://ine.gob.ve/wp-json/wp/v2/search?search=precios` | 200 but **HTML, not JSON** | The WordPress REST API is not exposed; no machine index of the site. |
| 5 | INE | `/wp-content/uploads/2026/09/COEFICIENTE-GINI.xlsx` | **200, xlsx** | Household-survey Gini, cells 1999–2025. Staged. |
| 6 | INE | `/wp-content/uploads/2026/09/TRABAJO.xlsx` | 200, xlsx | Labour-force tabulado, 1999–2025, one sheet, concept codes only. Deferred. |
| 7 | INE | `/wp-content/uploads/2026/09/POR-TIPO-1998-2025.xlsx`, `POR-VARIABLE-1998-2025.xlsx` | 200, xlsx | Household survey by type/variable, 1998–2025. Not needed for a spine slot. |
| 8 | INE | `/wp-content/uploads/2026/04/Exportaciones-po-Capitulo-1998-2018.xls` (+ importaciones) | 200, **legacy .xls** | Trade by HS chapter to 2018 — not by partner. |
| 9 | INE | `/wp-content/uploads/2026/04/POR-ENTIDAD-Defunciones.xls`, `POR-ENTIDAD-nacimientos.xls`, `SUICIDIOS.xls`, `ESPERANZA-DE-VIDA.xls` | 200, **legacy .xls** | Civil registration and life expectancy. Deferred (BIFF8, no coverage statement). |
| 10 | INE | same host from the **build network** (`curl`) | **exit 000**, 25 s timeout, both schemes, `www.` and apex, no proxy | The publisher does not answer the build network. Only an agent egress proxy reaches it — which is how (5) was retrieved. |
| 11 | BCV | `https://www.bcv.org.ve/`, `https://bcv.org.ve/`, `http://…` | **TLS: "unable to verify the first certificate"** on every scheme and path | The central bank's certificate chain is incomplete. No HTTP status is ever reached. This is the publisher of the CPI, national accounts, policy rate, reserves and exchange rate. |
| 12 | BCV | `https://bdvenlinea.bcv.org.ve/` | DNS `EAI_AGAIN` | Banking portal does not resolve. |
| 13 | BCV | `curl` from the build network | exit 000, 1.4 s | Same failure, seen twice through two stacks. |
| 14 | datos.gob.ve | `https://datos.gob.ve/`, `http://…`, CKAN `/api/3/action/package_list` | **timeout**, both schemes | The official open-data portal does not answer. |
| 15 | MPPEF (economy & finance) | `https://www.mppef.gob.ve/` | **200** | Live. Hosts the "Gestión de Caja Pública" and "Presupuesto por Resultados" pages. |
| 16 | MPPEF | `/gcp-ampliada-mensual/`, `/gcp-ampliada-trimestral/`, `/spr-ampliada-trimestral/` | 200, WordPress Download Manager tables | The packages listed are **"Gobierno Central Presupuestario" annual workbooks 1998–2009**, last updated 7–8 Nov 2018. No 2010–2026 execution. |
| 17 | MPPP (planning) | `https://mppp.gob.ve/` | **TLS `ERR_TLS_CERT_ALTNAME_INVALID`** | Certificate does not match the hostname. |
| 18 | MPPP | `http://mppp.gob.ve/` | 200, 150,056 bytes | Reachable over plain http only: a news/publication portal, no series. |
| 19 | SENIAT (customs) | `http://www.seniat.gob.ve/`, `https://declaraciones.seniat.gob.ve/` | **timeout**, both | No customs statistics route. |
| 20 | Imprenta Nacional (Gaceta Oficial) | `http://www.imprenta.gov.ve/` | **DNS `EAI_AGAIN`** | The legal publisher of every decree (minimum wage, redenominations) does not resolve. |
| 21 | IVSS (social security) | `https://www.ivss.gov.ve/` | timeout | No route. |
| 22 | gob.ve | `https://www.gob.ve/` | DNS `EAI_AGAIN` | No route. |

### Harmonised layer

| # | Publisher | Endpoint | Result | Meaning |
|---|---|---|---|---|
| 23 | World Bank | `api.worldbank.org/v2/country/VEN/indicator/…` | **200** for all 21 indicators | Works; last updated 2026-10-08. The backbone of the staged data. |
| 24 | IMF WEO | `imf.org/external/datamapper/api/v1/<code>` with a **browser** UA | 403 / HTML | The edge blocks `Mozilla/5.0` UAs (the same finding as the Ukraine lane). |
| 25 | IMF WEO | same with `worldreports-data-fetcher/1.0` | **200**, full country map | Works. `GGXWDG_NGDP` returns **no VEN observations**. `rev/exp/pb/ie` end 2024, `GGXCNL_NGDP` 2025, `LUR` 2018, `NGDP_RPCH`/`PCPIPCH`/`NGDPD` to 2027 with projections. |
| 26 | IMF SDMX | `api.imf.org/external/sdmx/2.1/dataflow` | 200, 223 dataflows | The new portal answers. |
| 27 | IMF SDMX | `IMF.STA:ER` (exchange rates) for VE, annual, from 2006 | 200, **empty dataset** | The IFS exchange-rate successor has no Venezuelan series. |
| 28 | IMF SDMX | `IMF.RES,IFS`, `IMF.STA,IFS` | 404 "No such dataflow" | IFS is no longer a dataflow; the ER dataset above is its successor. |
| 29 | IMF SDMX | `IMF.STA:GFS_COFOG` | dataflow exists, **no VE data** | No COFOG for Venezuela. |
| 30 | UNDP | `hdr.undp.org/.../HDR25_Composite_indices_complete_time_series.csv` | **200**, 2.0 MB, Latin-1 | HDI 1990–2023, one vintage. Staged. |
| 31 | UNHCR | `api.unhcr.org/population/v1/population/?coo=VEN&yearFrom=2006&yearTo=2025` | **200**, 20 items | Displacement by country of origin. Staged as lens. |
| 32 | UNHCR | `?coo=Venezuela` (name instead of ISO3) | 200 but **empty** `items` | The API silently accepts a bad key and returns nothing — a presence test must assert non-empty. |
| 33 | UN Comtrade | `…?reporterCode=862&period=2012&cmdCode=TOTAL&flowCode=X` | **200**, 53 partner rows, US$95.03bn | Venezuela reported in 2012. |
| 34 | UN Comtrade | `period=2013` | **200**, 84 rows, US$87.96bn | …and in 2013. |
| 35 | UN Comtrade | `period=2014` | **200, count = 0** | Reporting stops. |
| 36 | UN Comtrade | `period=2016…2025` | **429** (rate limit), and 0 rows when it answers | No Venezuelan records. |
| 37 | Transparency Intl | `images.transparencycdn.org/.../CPI2025-Results-and-trends.xlsx`; `transparency.org/en/cpi/2024` | **403** (S3 AccessDenied; HTML 403) | Same block the Ukraine lane recorded. Not staged. |
| 38 | WHO | `ghoapi.azureedge.net/api/Indicator` | 200, catalogue | Carries **no general COVID-19 death indicator** (only in-prison codes). |
| 39 | WHO | `covid19.who.int/WHO-COVID-19-global-data.csv` | 200 but **HTML** | The CSV endpoint now serves a page. No official COVID series. |
| 40 | BIS | `stats.bis.org/api/v1/data/WS_TC/Q.VE.H.A.M.770.A` | **404** | Venezuela is not a BIS reporting country. |
| 41 | BIS | same key for `US` | **200** | Proves the endpoint works and the 404 is the country, not the query. |
| 42 | CEPALSTAT | `api.cepal.org/v1/` | DNS `EAI_AGAIN` | The regional harmoniser's API does not resolve from this network. |

That is the route audit the brief asks for: 42 probes, 22 national and 20
harmonised, every failure recorded with its mode.

---

## 2. What was chosen, and why

**The national layer is one series.** Only the INE's Gini is a Venezuelan
publication that survives the window. It is drawn as the national line, with
its own disclosure (`DATA_NOTES.md` §"The Gini needs its own disclosure").

**Everything else is harmonised, and says so.** The World Bank carries the
national accounts Venezuela stopped submitting, the UN population model, and
UNODC/WHO rates. The IMF carries the only inflation series through the
hyperinflation, and the general-government accounts — as **staff estimates**,
labelled as such in every affected column comment and in the plate note.

**Where two harmonised publishers exist, both are drawn.** Growth, dollar GDP,
inflation and unemployment each have two lines with different sizes, because
choosing one would hide the fact that this country's macro data is a
compilation of estimates rather than a national accounting identity.

**Nothing unofficial is staged.** The parallel/market exchange rates, the
ENCOVI university survey, the OVF violence counts and the R4V "Venezuelans
abroad" figure are all real, widely quoted, and none of them is an official
statistic. None is used, not even as a labelled proxy, because in each case an
official route exists in principle (BCV, INE) and is blocked — which is a
different thing from nonexistence.

---

## 3. Definitional traps found

1. **Three redenominations inside the window** (2008, 2018, 2021) with
   divisors 1,000 / 100,000 / 1,000,000. The World Bank restates pre-2008
   values in the post-2008 unit, so one divisor (1e11) covers 2006–2017; it is
   written in the CSV comment, the column name and `DATA_NOTES.md`.
2. **Placeholder zeros.** `NE.EXP/IMP.GNFS.ZS` and `NE.GDI.FTOT.ZS` return
   `0.0` for 2006–2011 where the series does not exist. Dropped, not drawn.
3. **Two exchange-rate conventions in one concept.** World Bank vs IMF dollar
   GDP differ by 40% in 2014 (214.8 vs 128.8 bn) because Venezuela ran several
   official rates. Both drawn, neither "the" answer.
4. **`lcu_per_usd` is not one currency.** 2006–2017 are bolívares fuertes; a
   naive read of "2.147" for 2006 as current bolívares would be a 1,000×
   error. Documented in the file header.
5. **A stale publisher title.** The INE workbook is named "Coeficiente Gini,
   1997 - 2020" while its cells run 1999–2025 and start in 1999. The title is
   recorded as stale; the cells are the data.
6. **Comtrade's "nes" buckets.** 2013 Venezuelan exports: US$29.87bn to
   "North America and Central America, nes", US$28.06bn to "Other Asia, nes",
   US$13.53bn to "LAIA, nes", US$11.01bn to "Areas, nes" — about US$82bn of
   US$88bn unallocated, against US$0.55bn to the United States. A partner
   chart on this would be a chart of the code list. Not drawn.
7. **The IMF's UA block.** A browser User-Agent gets 403/HTML from
   `www.imf.org`; a descriptive one gets 200. A fetcher that "works in a
   browser" fails here.
8. **UNHCR's silent empty.** `coo=Venezuela` returns `items: []` with HTTP
   200; only `coo=VEN` returns data. The fetcher asserts non-empty.
9. **Homicide holes and estimates.** 2013 and 2018 are missing in the UNODC
   series; the post-2019 fall is an estimate. Left blank and labelled — not
   interpolated.
10. **No census since 2011.** The population series is a model and its
    2016–2021 decline is modelled emigration, not a count.

---

## 4. Gate results (2026-10-25, lane)

```
python3 -m pytest -q tests/test_sources.py tests/test_data.py -k venezuela
17 passed, 289 deselected
```

Fetcher determinism (all four network fetchers, 2026-10-25):

```
fetch_worldbank: online x2 byte-identical; offline-warm byte-identical; cold-offline exit 2
fetch_imf:       online x2 byte-identical; offline-warm byte-identical; cold-offline exit 2
fetch_undp:      online x2 byte-identical; offline-warm byte-identical; cold-offline exit 2
fetch_unhcr:     online x2 byte-identical; offline-warm byte-identical; cold-offline exit 2
```

`fetch_ine.py` cannot be exercised from the build network (see route 10); its
cold-offline path exits 2 and writes nothing, and its 2026-10-25 payload is
preserved as `fetch/reference_ine_gini_2026-10-25.csv`.

**Whole-suite note:** `tests/test_numbers.py` is expected to fail for `pl`/`ru`
locales until the core number-style work lands (orchestrator's, not this
lane's). Nothing in this lane touches `core/`, `site/`, another country or the
layout baseline.

---

## 5. What this lane asked of the orchestrator, and what it got

Recorded as asked, then as answered. The answers are what the plates draw, and
`DATA_NOTES.md` ("How the scale conflicts were settled") is the decision record.

1. **`economy.inflation` — asked for a log axis or a widened shared range.**
   Answered with neither: the canonical slot stays visibly pending, and the
   series is drawn in the prices lens on a log axis. A hyperinflation cannot
   share a linear comparable scale, and the lens is the slot the spine keeps
   for a country's own story.
2. **Shared ranges — asked for four decisions.**
   `economy.growth` (IMF −33.2 against the old −32 floor), `fiscal.balance`
   (−31.9 against −24) and `trade.balance` (+36.3 against +15) were **widened
   atlas-wide** in `core/spine.py` and every country carrying those topics was
   regenerated; the three are drawn canonically. `migration.net` (−45.5 per
   1,000 against −10) was **refused**, on the same reasoning as the inflation:
   the canonical slot stays pending and the series is drawn in the migration
   lens on its own axis. `markets.currency` was checked and **fits** (the index
   bottoms at 21.5, inside log 0.1…200) only because the official rate series
   stops in 2017.
3. No core code change was otherwise required by this country's data.
