# Singapore — Phase A discovery report

Research pass run 2026-10-25 in the `singapore` lane (branch `singapore`,
based on main `406994d`). Every endpoint below was probed live from the
discovery network on 2026-10-25 and its result recorded, including the
ones that failed. `SOURCES.yaml` is authoritative where this report and it
disagree; `DATA_NOTES.md` carries the judgement calls.

Singapore is a city-state with no sub-national statistical geography worth
splitting: the whole country is 735 km² and the "national" and "urban"
series are the same series. Two consequences run through the whole lane and
are repeated in `DATA_NOTES.md` because they govern how the numbers may be
read:

- **GDP per person is the headline, not GDP.** The population denominator is
  not a stable quantity: it is composed of citizens, permanent residents and
  a large non-resident population on work permits, and the non-resident share
  moves with the construction and services cycle. A per-capita series that
  does not say which population it divides by is not a statistic.
- **"Country" is not the right frame.** Singapore is a city and a state at
  once. Ratios that mix a national-accounts aggregate with a land area (GDP
  per km², population density) are legitimate extra readings here and are
  meaningless in the same slot for a large country; they stay in the lens.

## Status

Phase A deliverables in progress. Route table and per-publisher results
below are updated as each publisher is probed; nothing here is a claim about
data that has not been fetched.

## Publisher-by-publisher, probed live 2026-10-25

### Singapore Department of Statistics (SingStat) — Table Builder API — WORKS

The publisher's own machine-readable route, and the primary source for this
country. No key, no registration.

- `GET https://tablebuilder.singstat.gov.sg/api/table/metadata/<id>` → 200,
  JSON. `Data.records` carries `theme`, `subject`, `topic`, `title`,
  `frequency`, `startPeriod`, `endPeriod`, `dataLastUpdated` and the row
  (series) list with `uoM` (unit of measure).
- `GET https://tablebuilder.singstat.gov.sg/api/table/tabledata/<id>` → 200,
  JSON. `Data.row[]` carries `seriesNo`, `rowText`, `uoM`, and
  `columns[].value` per period.
- A bad id answers a JSON body under **HTTP 404** with
  `StatusCode: 404` (`{"Data":{},"DataCount":0,...}`), not an HTML page —
  but the shape is still checked before caching, because the failure mode
  recorded in `SOURCING_A_COUNTRY.md` is a gateway serving 200 for an error.
- **Table discovery.** The Table Builder site is a SPA with no search
  endpoint on the API host: `/api/table/tablesearch`, `/api/table/summary`
  and `/api/table/search` all answer **404** for GET and POST. The
  publisher's own `https://tablebuilder.singstat.gov.sg/sitemap.xml`
  (200, 349 KB) enumerates the table ids instead: **1,049 `table/TS/M…`
  entries** (plus 1,735 `table/CT/…` saved views, 48 `LDC`, 2 `TR`). Each
  `M…` id was then resolved through the metadata endpoint to build the
  title index used to pick tables below; the ids and titles that were
  adopted are recorded in `SOURCES.yaml`, not the whole index.
- Numeric ids also resolve (`/tabledata/17287` → 200 for a
  Supply-Use table), which is why `data.gov.sg` descriptions citing
  `table/CT/<num>` can be turned back into API calls.

**Verified anchor:** `M810001` "Indicators On Population, Annual" — 200,
`dataLastUpdated: 25/09/2026`, `startPeriod 1950`…`endPeriod 2026`,
series 1 "Total Population" in `uoM: Number`, with the publisher's own
footnote that pre-1990 data are de facto and 1990 onwards de jure. That
concept change is a real break and is recorded before anything is drawn
from it.

### Monetary Authority of Singapore (MAS) — BLOCKED from this network

`https://eservices.mas.gov.sg/api/action/datastore/search.json`,
`/api/3/action/package_list` and the datastore query path all return an
**HTML maintenance/redirect page ("MAS", `maintenance.mas.gov.sg/eservice/`)
under HTTP 200** — the exact "endpoint that lies" failure. No JSON, no
CKAN catalogue. Recorded as an access failure on the discovery network, not
as an absent dataset; the retry is one fetch from an unblocked network.

Consequence for the spine: `markets` slot 1 is "policy rate vs inflation",
and **Singapore has no policy interest rate**. MAS conducts monetary policy
through a trade-weighted exchange-rate band (S$NEER), not a policy rate. The
slot therefore needs an explicit editorial decision (recorded in
`DATA_NOTES.md`) rather than a substituted interest rate passed off as a
policy rate.

### data.gov.sg — WORKS

`https://api-production.data.gov.sg/v2/public/api/datasets?page=<n>` → 200,
JSON catalogue, and `…/datasets/<id>/metadata` → 200 with the column
metadata, `datasetSize`, `lastUpdatedAt`, `managedBy`. Many SingStat tables
are republished here as CSV with the Table Builder id in the description;
this is the fallback route when the Table Builder payload is awkward, and
the route for MAS series that the MAS host will not serve.

### The World Bank — WORKS

`https://api.worldbank.org/v2/country/SGP/indicator/<code>?format=json` →
200. Verified: `NY.GDP.MKTP.CD` 2024 = **572,877,260,178.427** (US$572.9bn),
`lastupdated 2026-10-08`. This is the harmonised layer and the comparable
per-person denominator.

### IMF — WORKS

`https://www.imf.org/external/datamapper/api/v1/<code>/SGP` → 200, the
DataMapper payload (`values.<code>.SGP.<year>`). A browser UA is refused by
the edge; a descriptive UA is served.

### UNDP — pending probe

### Transparency International, UNODC, WHO — pending probe
