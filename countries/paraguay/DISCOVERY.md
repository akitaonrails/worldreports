# Paraguay — discovery record, 2026-10-25

Status: Phase A (data). This is the publisher-by-publisher record: what was
probed, what answered, what did not and how it failed, what was chosen and
why, and the route table the gap rule requires. `SOURCES.yaml` carries the
per-file provenance; this file carries the search.

All probes below were made from the discovery network on **2026-10-25**,
with a browser `User-Agent` for the national sites and a descriptive
`worldreports-data-fetcher/1.0` for the IMF (whose edge rejects
`Mozilla/5.0`). HTTP codes are the first response, redirects followed.

---

## 1. The seven institutions, and who answered

| Role | Institution | Host | Result |
|---|---|---|---|
| National statistical office | Instituto Nacional de Estadística (INE) | `ine.gov.py` | **200**, full HTML + XLSX releases |
| Central bank | Banco Central del Paraguay (BCP) | `bcp.gov.py` | **403 Cloudflare "Just a moment…"** on every path and both schemes |
| Finance ministry | Ministerio de Economía y Finanzas (MEF, formerly Hacienda) | `mef.gov.py` = `hacienda.gov.py` | **200**, annual fiscal series and monthly SITUFIN workbooks |
| Customs / trade | Dirección Nacional de Ingresos Tributarios (DNIT, absorbed the Aduana) | `dnit.gov.py`, `aduana.gov.py` | **200**, but tax-collection tables only — no trade flows |
| Vital statistics | INE — *Nacimientos, matrimonios y defunciones*; INE population projections | `ine.gov.py` | **200** |
| Police / justice | Ministerio Público; Policía Nacional | — | no machine-readable series found; UNODC/WHO via the harmonised layer |
| Market (nobody official) | Bolsa de Valores de Asunción (BVA) | `bva.com.py` | no continuous official index published |

Adjacent and official mirrors probed:

| Route | Result |
|---|---|
| `datos.gov.py` (national open-data portal) | **200 but a "Sitio en Mantenimiento" page** — the whole CKAN portal is down, `/api/3/action/package_search` answers 404 HTML. A route result, not a dead dataset: BCP and MEF datasets are mirrored there when it is up. |
| `ine.gov.py/microdatos/` (ANDA catalogue) | 200; microdata files, not aggregate series |
| `anda.ine.gov.py` | 200; DDI/metadata catalogue, `/api/catalog/search` 200 with no series |
| `ods.ine.gov.py` (SDG portal) | 200; `/api/` serves an HTML "404 - INE" page **under HTTP 200** |
| `ine.gov.py/api/` | 403; `/api/v1/` and `/sdmx/` 404; `api.ine.gov.py` no DNS |
| `ioe.ine.gov.py` | 200; inventory of statistical operations, not data |
| `estadisticas.bcp.gov.py` | **403** Cloudflare |
| `siec.bcp.gov.py`, `open.bcp.gov.py`, `api.bcp.gov.py`, `datos.bcp.gov.py` | no DNS / no connection |
| `infoleg`/`informacionpublica.paraguay.gov.py` | 200; request portal only |

The BCP block is the single largest constraint on this country: GDP,
the policy rate, the guaraní, reserves, credit and the CPI are all BCP
products here. The CPI is **not** an INE product in Paraguay — the BCP
computes it (base December 2017 = 100) and INE's site carries no IPC
section at all (checked: the whole `publicacion/` index and the
`Estadísticas Económicas` menu). The harmonised route below therefore
carries those series, labelled as the IMF's record of what the BCP
reported, never as the BCP's own release.

---

## 2. What each accessible publisher actually gives

### INE — `ine.gov.py` (200)

| Series | Endpoint | Shape |
|---|---|---|
| Population, births, deaths, TFR, life expectancy, net migration, 1950–2050 | `Publicaciones/Biblioteca/documento/266/Estimaciones y Proyecciones Nacional por año 1950-2050. Revisión 2024.xlsx` | one workbook, sheets *Poblac a mitad de año 1950-2050*, *Componentes Demográficos*, *Medidas de Composición*. Annual, mid-year population, revision 2024 |
| Labour-market rates (EPHC) | `assets/documento/328/1. Tasas.xlsx` | annual, national |
| Poverty incidence, absolute and relative | `assets/documento/11/...pobreza...xlsx` and `assets/documento/29/...` | annual 1997-98 → 2025 |
| Gini and income | `publicacion/5/ingresos` | annual EPHC |
| Registered births and deaths | `publicacion/21/nacimientos-matrimonios-y-defunciones` | annual, administrative record |

INE publishes **no machine API**. Probed on 2026-10-25:
`/api/` answers 403, `/api/v1/` 404, `/sdmx/` 404, `api.ine.gov.py` does
not resolve, `anda.ine.gov.py`'s catalogue API answers 200 with metadata
(DDI records, no series), and `ods.ine.gov.py/api/` answers **HTTP 200
with an HTML "404 - INE" page** — the endpoint that lies, which is why
every fetcher here checks the payload shape before caching anything. The
"Gráficos Dinámicos" (`/vt/*.php`) pages embed Flourish charts whose data
are not exposed; the underlying XLSX files on the publication pages are
the series and are what the fetchers read.

### MEF — `mef.gov.py` (200)

| Series | Endpoint |
|---|---|
| Central-administration fiscal series **2003–2025**, in guaraníes and in **% of GDP** | `/sites/default/files/2026-05/MEFP 2001 ADMINISTRACIÓN CENTRAL 2003-2025 serie anual.xlsx` |
| The long national history **1980–2022**, in millions of guaraníes | `/sites/default/files/2024-12/Situacion Financiera 1980-2022(1).xlsx` |
| Monthly SITUFIN workbooks and the monthly series 2003–2026 | `/es/situfin` |

The annual workbook's `% PIB` sheet is the national line the fiscal plate
argues about: revenue, expenditure, interest, the operating balance, the
primary result, net lending/borrowing, and — directly relevant to
Paraguay — **Itaipú and Yacyretá royalties and energy-cession
compensation as their own revenue lines**. It is MEF's GFS-2001
presentation of the **Administración Central**: cash basis, central
government, not the general-government accrual perimeter the IMF WEO
publishes. The two are kept in separate columns.

### DNIT / Aduana — `dnit.gov.py` (200)

The statistics page carries tax collection, taxpayer counts and the
"500 mayores aportantes" lists. The customs administration was merged
into DNIT in 2023 and `aduana.gov.py` now serves the same Liferay portal.
**No export/import flow tables are published as files.** Trade therefore
comes from the harmonised layer and UN Comtrade, with this recorded.

### Harmonised layer

| Agency | Route | Result |
|---|---|---|
| World Bank | `api.worldbank.org/v2/country/PRY/indicator/...` | **200**, 2000–2025 for all the canonical indicators |
| IMF DataMapper (WEO Oct 2026) | `imf.org/external/datamapper/api/v1/<code>/PRY` | **200**; 403 to a `Mozilla/5.0` UA, 200 to a descriptive one |
| IMF SDMX 2.1 (`api.imf.org`) | `data/IMF.STA,<flow>/PRY...` | **200**: `CPI`, `ER`, `FSIBSIS`, `LS`, `GFS_COFOG`, `IMTS`, `ITG`, `MFS_IR`, `IRFCL` all carry PRY |
| UNDP HDR | `hdr.undp.org/.../HDR25_Composite_indices_complete_time_series.csv` | **200**, 2.0 MB, Latin-1 |
| UN Comtrade preview | `comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=600` | **200**, 140 partner rows for 2024 |
| Transparency International | `images.transparencycdn.org/.../CPI2025-Results-and-trends.xlsx` | see `SOURCES.yaml` meta.pending |

---

## 3. Definitional traps found, and the decision for each

**The CPI is the BCP's, not INE's.** Its base changed to December 2017 =
100 in 2018, so the index level is not one series across 2006–2026. The
plate needs the *rate*, which the IMF IFS carries as a year-on-year
transformation of the BCP's index (`YOY_PCH_PA_PT`, COICOP total). The
World Bank's `FP.CPI.TOTL.ZG` is the same underlying series, annual; the
two are staged and cross-checked, never spliced with a national level the
BCP did not publish to us.

**Itaipú is revenue, not output.** The MEF series carries "Regalías y
compensación Itaipú y Yacyretá" and "Compensación cesión de energía
Itaipú y Yacyretá" as fiscal revenue lines. Hydroelectricity is also a
large share of Paraguay's *exports* (electricity sold to Brazil and
Argentina) but the binational treaty revenue and the electricity export
are different objects. They stay labelled as fiscal revenue and as an
export line respectively, and neither is presented as GDP.

**Central administration versus general government.** MEF's national
series (cash, Administración Central, 12–15% of GDP revenue) and the IMF
WEO general-government series (18–19% of GDP) differ by about five
points of GDP permanently. Two columns, two labelled lines.

**The 2023 redenomination did not happen.** The guaraní (PYG) is quoted
in whole units; the proposal to divide by 1,000 was abandoned and no
redenomination took place in 2023 or since. Every PYG figure here is in
current guaraníes of its year, and the MEF workbook mixes **millions**
(the 1980–2022 sheet, "En millones de guaraníes") with **thousands of
millions** (the 2003–2025 sheet, "En miles de millones de guaraníes").
The fetcher reads the unit from the sheet header and asserts the
magnitude against GDP before writing; no file here carries a PYG level
whose unit is inferred from a filename.

**Two guaraní-per-dollar conventions.** The IMF ER flow gives
`XDC_USD` (national currency per US$) as a period average; the World Bank
`PA.NUS.FCRF` is the same convention. Both are used; the plate indexes
2006 = 100 with up = stronger, so a *fall* in PYG/USD is a stronger
guaraní and the index must be built from the reciprocal.

**Population: projection, not census count.** INE's revision-2024 series
is an *estimate/projection* that runs 1950–2050 and already contains the
2022 census. It is the national denominator for every rate here, and the
years after the census are projections — recorded as such, and the plate
note says where observation ends.

**Homicides: two publishers.** UNODC/WHO via the World Bank (`VC.IHR.PSRC.P5`)
and the Ministerio Público's own annual reports disagree. Only the
harmonised series is staged here; the national publisher's figures are
PDF tables with no machine series, recorded in `meta.pending`.

---

## 4. Route table (the gap rule, item by item)

| Spine slot | National route tried | Result | Harmonised route | Staged? |
|---|---|---|---|---|
| economy.growth | BCP national accounts (`bcp.gov.py/webapps/...`) | 403 Cloudflare | IMF WEO `NGDP_RPCH`, WB `NY.GDP.MKTP.KD.ZG` | yes |
| economy.gdp_per_person | BCP | 403 | WB `NY.GDP.PCAP.CD` | yes |
| economy.inflation | BCP IPC | 403; INE publishes no CPI | IMF IFS `CPI` YOY, WB `FP.CPI.TOTL.ZG` | yes |
| economy.unemployment | INE EPHC `1. Tasas.xlsx` | **200** | IMF `LS`, WB `SL.UEM.TOTL.ZS` | yes |
| fiscal.* | MEF annual series | **200** | IMF WEO general government | yes |
| spending.COFOG | MEF functional tables (PDF) | partial, see notes | IMF `GFS_COFOG` | yes |
| spending.GFCF | — | — | WB `NE.GDI.FTOT.ZS` | yes |
| trade.exports/imports | BCP, DNIT | 403 / no flow tables | WB `NE.EXP/IMP.GNFS.ZS` | yes |
| trade.partners | DNIT | no files | UN Comtrade; IMF `IMTS` | yes |
| markets.policy_rate | BCP TPM | 403 | IMF `MFS_IR` ends 2022 | pending, `meta.pending` |
| markets.bond_yield | BCP/MEF | 403 / no series | — | pending |
| markets.fx | BCP | 403 | IMF `ER` `XDC_USD` PA; WB `PA.NUS.FCRF` | yes |
| markets.equity | BVA | no index series | — | pending |
| people.gini | INE EPHC | **200** | WB `SI.POV.GINI` | yes |
| people.poverty | INE EPHC | **200** | WB PIP | yes |
| people.minimum_wage | MTESS decrees | see notes | — | yes |
| world.gdp_usd | BCP | 403 | WB `NY.GDP.MKTP.CD` | yes |
| world.hdi | — | — | UNDP HDR 2025 | yes |
| world.cpi_corruption | — | — | Transparency International | see pending |
| world.reserves | BCP | 403 | WB `FI.RES.TOTL.CD` | yes |
| demography.* | INE projections rev. 2024 | **200** | WB `SP.POP.TOTL`, `SP.DYN.*` | yes |
| security.* | Ministerio Público | PDF only | UNODC/WHO via WB | yes |
| mortality.* | INE vital statistics + projections | **200** | WB `SP.DYN.CDRT.IN` | yes |
| credit.household_debt | BCP | 403 | no BIS series for PRY | pending |
| credit.npl | BCP | 403 | IMF `FSIBSIS` | yes |
| migration.flows | INE (net migration in the projection) | **200** | WB `SM.POP.NETM`, `SM.POP.TOTL` | yes |

Every pending row is written out with its exact endpoint and failure in
`SOURCES.yaml` → `meta.pending`.
