# Russia — Phase A discovery report

Research pass run 2026-10-25 in the `russia` lane. Every endpoint below was
curl'd live on that date and every status code and byte count is what the
discovery network returned. `SOURCES.yaml` is authoritative where this report
and the manifest differ; `DATA_NOTES.md` records the conversions.

**The headline finding, and it is not the expected one.** The queue said
"Rosstat/EMISS access is likely blocked, so the harmonised layer plus
documented blocks". Half of that is true. EMISS (`fedstat.ru`) answers 403,
`data.gov.ru` does not connect at all and `customs.gov.ru` does not connect
either — but **`rosstat.gov.ru` serves its full publication set**, and the
reason it looks dead to a default client is a TLS detail, not a wall. See the
Rosstat section: plain `curl https://rosstat.gov.ru/` reports
`000`/no-connection because the certificate chain is signed by a Russian
Trusted Root CA that no public trust store carries. The site content itself
is intact and reachable.

---

## Route table — every publisher probed

HTTP status, byte count and content type as returned to
`curl -skL -m 30 -A "Mozilla/5.0 ... Chrome/126.0"` on **2026-10-25**.
`000` means no HTTP response at all (connection or TLS failure), and the
failure mode is stated in the notes.

| # | Publisher | Endpoint | Result | Verdict |
|---|-----------|----------|--------|---------|
| 1 | Rosstat | `https://rosstat.gov.ru/` | **000** (TLS: issuer not in trust store) | reachable with the chain unverified |
| 1 | Rosstat | `http://rosstat.gov.ru/` | 302 → `https://rosstat.gov.ru/` | redirect confirmed |
| 1 | Rosstat | `https://rosstat.gov.ru/` `-k` | **200, 826,371 B, text/html** | **works** |
| 1 | Rosstat | `https://rosstat.gov.ru/statistics/accounts` | 200, 798,909 B | **works** — national accounts |
| 1 | Rosstat | `https://rosstat.gov.ru/statistics/price` | 200, 881,934 B | **works** — CPI |
| 1 | Rosstat | `https://rosstat.gov.ru/folder/12781` | 200, 860,216 B | **works** — population |
| 1 | Rosstat | `https://rosstat.gov.ru/statistics/finance` | 200, 756,496 B | **works** — enterprise finance |
| 1 | Rosstat | `https://rosstat.gov.ru/statistics/vneshnyaya_torgovlya` | 200, 746,397 B | **works** — foreign trade |
| 1 | Rosstat | `https://rosstat.gov.ru/storage/mediabank/VVP_god_s1995-2025.xlsx` | 200, 61,737 B, xlsx | **works** |
| 1 | Rosstat | `https://rosstat.gov.ru/storage/mediabank/VVP_kvartal_s-1995-2026.xlsx` | 200, 115,224 B, xlsx | **works** |
| 1 | Rosstat | `https://rosstat.gov.ru/storage/mediabank/VVP_na_dushu_s1995-2024.xlsx` | 200, 39,954 B, xlsx | **works** |
| 1 | Rosstat | `https://rosstat.gov.ru/storage/mediabank/ipc_s_1992-2025.xlsx` | 200, 37,856 B, xlsx | **works** |
| 1 | Rosstat | `https://rosstat.gov.ru/storage/mediabank/popul_1897+.xlsx` | 200, 14,063 B, xlsx | **works** |
| 1 | Rosstat | `https://rosstat.gov.ru/storage/mediabank/Popul components_1990+.xlsx` | 200, 33,627 B, xlsx | **works** |
| 1 | Rosstat | `https://eng.rosstat.gov.ru/` | **000** | no connection (host does not answer) |
| 1 | Rosstat | `https://www.gks.ru/` (the old host) | **000** | no connection |
| 2 | EMISS / fedstat | `https://fedstat.ru/` | **403, 80 B** | blocked |
| 2 | EMISS / fedstat | `https://www.fedstat.ru/` | **403, 80 B** | blocked |
| 2 | EMISS / fedstat | `https://fedstat.ru/indicator/31572` | **403, 80 B** | blocked |
| 3 | data.gov.ru | `https://data.gov.ru/` | **000** | no connection |
| 3 | data.gov.ru | `http://data.gov.ru/` | **000** | no connection |
| 4 | Bank of Russia | `https://www.cbr.ru/` | 200, 76,054 B | **works** |
| 4 | Bank of Russia | `https://www.cbr.ru/eng/` | 200, 58,602 B | **works** — English mirror |
| 4 | Bank of Russia | `https://www.cbr.ru/hd_base/KeyRate/` | 200, 93,354 B | **works** — key-rate history table |
| 4 | Bank of Russia | `https://www.cbr.ru/scripts/XML_daily.asp?date_req=01/01/2024` | 200, 7,592 B, XML | **works** — daily FX |
| 4 | Bank of Russia | `https://www.cbr.ru/scripts/XML_dynamic.asp?...VAL_NM_RQ=R01235` | 200, 29,546 B, XML | **works** — FX time series |
| 4 | Bank of Russia | `https://www.cbr.ru/hd_base/zcyc_params/` | 200, 31,818 B | **works** — OFZ zero-coupon curve |
| 4 | Bank of Russia | `https://www.cbr.ru/statistics/bank_sector/sors/` | 200, 1,496,456 B | **works** — banking-sector aggregates |
| 5 | Ministry of Finance | `https://minfin.gov.ru/ru/` | 200 (301 first), 107,287 B | **works** |
| 5 | Ministry of Finance | `https://minfin.gov.ru/ru/statistics/fedbud/` | 200, 43,889 B | **works** — federal budget |
| 5 | Ministry of Finance | `https://minfin.gov.ru/ru/statistics/fedbud/execute/` | 200, 34,572 B | **works** — budget execution |
| 5 | Ministry of Finance | `https://minfin.gov.ru/ru/statistics/public_debt/external/` | 404, 25,389 B | wrong path; debt lives elsewhere |
| 6 | Federal Customs Service | `https://customs.gov.ru/` | **000** | no connection |
| 6 | Federal Customs Service | `https://customs.gov.ru/statistic` | **000** | no connection |
| 7 | Moscow Exchange | `https://iss.moex.com/iss/history/engines/stock/markets/index/securities/IMOEX.json` | 200, JSON | **works** |
| 8 | World Bank | `https://api.worldbank.org/v2/country/RUS/indicator/NY.GDP.MKTP.KD.ZG?format=json` | 200 | **works** |
| 9 | IMF | `https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH/RUS` | 200, 121,784 B | **works** |
| 9 | IMF | `https://api.imf.org/external/sdmx/2.1/data/IFS/A.RU.` | **404** | wrong SDMX path; DataMapper used instead |
| 10 | BIS | `https://stats.bis.org/api/v1/data/WS_TC/Q.RU.H.A.M.770.A?format=csv` | 200, 18,314 B, CSV | **works** — household credit |
| 11 | UN Comtrade | `https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=643&period=2023&cmdCode=TOTAL&flowCode=X` | 200, `count: 0` | **reports nothing for 2023** — see below |
| 11 | UN Comtrade | same, `period=2022` | 200, `count: 0` | reports nothing |
| 11 | UN Comtrade | same, `reporterCode=810` (Ukraine) | 200, `count: 0` at that moment | rate-limited, not a finding |
| 12 | UNDP HDR | `https://hdrdata.org/api/CompositeIndices/query?...` | **404** | API shape changed; the HDR bulk workbook route is used |
| 13 | WHO GHO | `https://ghoapi.azureedge.net/api/Indicator` | (probed by the Ukraine lane 2026-10-25) | no general COVID-19 death indicator |

### Rosstat — the TLS failure that reads as a wall

`openssl s_client -connect rosstat.gov.ru:443` **connects** and returns a
valid certificate:

```
subject=CN=*.rosstat.gov.ru, O=Федеральная служба государственной статистики,
        C=RU, ST=77 г.Москва, L=г. Москва, street=ул. Мясницкая 39, строение 1,
        OGRN=1047708023483
verify error:num=20: unable to get local issuer certificate
```

The chain terminates in a Russian Trusted Root CA (Минцифры), which is not in
the Mozilla bundle, so `curl` without `-k` aborts before the request and
reports `000` with zero bytes — indistinguishable in a status column from a
geo-block. It is not one: the same request with the chain unverified returns
826 KB of the statistical office's home page and every `/statistics/*` route
and every `/storage/mediabank/*.xlsx` below it answers 200.

**How the fetcher handles it.** `fetch/fetch_rosstat.py` opens the connection
with certificate verification **on** by default and fails with a clear
message; it accepts `--rosstat-insecure` for the specific case of a network
without the Russian root installed, and it records in the sidecar which mode
produced it. Nothing about a *number* depends on the mode — the transport
does. The correct permanent fix is to install the Russian Trusted Root CA in
the fetch host's trust store, which is a host decision, not a repository one.

Rosstat's workbooks are the **national layer**: the computing institution's
own release, in its own currency, on its own territorial definition. They are
staged beside the World Bank and IMF series, never spliced into them.

### EMISS / fedstat — 403, and what it would have carried

`fedstat.ru` and `www.fedstat.ru` return a bare **403 with an 80-byte body**
on `/`, on an indicator page and on the export path. This is the Unified
Interdepartmental Statistical Information System — the machine-readable SDMX-
ish layer over Rosstat's indicator registry, and the one route that would give
a single tidy series per indicator instead of a workbook per topic. It is
blocked from this network. Rosstat's own workbooks carry the same underlying
numbers, so the *data* are not lost; what is lost is the convenient shape and
the per-indicator metadata. Recorded in `meta.pending`, not worked around.

### data.gov.ru and customs.gov.ru — no connection at all

Neither host completes a TCP connection (`000`, no bytes, no TLS error). Not
a 403 and not a timeout on a slow server: no route. Both are recorded in
`meta.pending` with the date. Customs matters because Russia **stopped
publishing detailed foreign-trade statistics in 2022** — the Federal Customs
Service suspended its public release after February 2022 — so even an
unblocked host would carry a truncated series. That is a published-data gap,
not an access gap, and it is documented as one.

### UN Comtrade — Russia reports nothing in this window

Russia (reporter 643) returns `count: 0` for 2022 and 2023 HS total exports
through the preview API. Rosstat's own foreign-trade page still publishes an
annual aggregate workbook, so the canonical trade slot is filled from the
World Bank's national-accounts series and the partner-destination panel is
served from what does exist — a **Rosstat** annual aggregate, with the
per-partner cut left pending and disclosed. No unofficial mirror is
substituted for the missing customs detail.

### The Bank of Russia — the best API of the set

Every route answers: the key-rate history table (1,223 daily rows
2022-01-01…2026-10-23), the FX time series as XML, the OFZ zero-coupon curve,
and the banking-sector aggregates. This is the markets and credit chapter:
the policy rate, the rouble, the 10-year yield, lending rates, the NPL ratio
and the household-credit stock. The 2022 break — the emergency 20% rate on
28 February 2022, the capital-control regime, the MOEX closure from 25
February to 24 March 2022 — is drawn as a break, not smoothed.

### The Ministry of Finance

Answers. Federal budget revenue, expenditure and the balance, and the debt
stock, in roubles. Two perimeters exist and are kept apart: the **federal**
budget (what Minfin executes) and the **general government** (what the IMF
WEO harmonises). The spine's fiscal slots are general government; the federal
line rides beside it, labelled, because it is the series Russian policy
argument is actually about.

---

## What is staged, and on which definition

Thirty curated CSVs across eleven topic directories, each with its
sidecar beside it. The manifest (`SOURCES.yaml`) is the list; the
definitional decisions that matter are:

1. **Territorial scope.** Rosstat's population and national accounts
   **include Crimea and Sevastopol from 2014**, which Russia annexed and
   counts; from 2022 the publisher's own footnote excludes the four
   oblasts annexed that year, so 2022+ is a narrower perimeter again. The
   World Bank and the UN do not reproduce the 2014 step. The two lines are
   drawn separately and neither is called "the population of Russia"
   without its scope. This is the single largest seam in the country's
   data and it lands on an interesting year, which is exactly the case
   `SOURCING_A_COUNTRY.md` §4 warns about.
2. **Two CPI definitions.** Rosstat's headline is December-to-December
   (2015: 12.91%); the World Bank's is the annual average (2015: 15.53%).
   Both published, both correct, two columns.
3. **Three fiscal perimeters.** The federal budget (Minfin, cash, one
   level, roubles), general government (IMF WEO, accrual, % of GDP), and
   the non-oil-and-gas deficit the Ministry leads with. Never spliced.
4. **Nominal roubles are not a unit across this window.** On the staged
   vintage, 2025 nominal GDP is 8.0× its 2006 level while the
   physical-volume index is 1.56×. Nominal over real implies 5.1× and
   chaining the published deflator gives 5.9×; both are the price level, and
   neither makes a rouble a unit a level can be drawn in across twenty
   years. Every level that spans years is in constant prices, a share of GDP,
   or dollars, and says which.
5. **The sanctions-era stops**, each recorded as a gap and never filled:
   the detailed customs statistics (suspended 2022, host unreachable), the
   federal spending breakdown (sections stop at 2021), homicide and
   suicide (2021), road deaths (2019), bank NPL (2023), Gini (2023), the
   IMF revenue/expenditure lines (2024).

## Correction made during the pass

The first cut of `country.yaml`'s recession bands was written from memory of
the crisis years and said "2008 Q3 – 2009 Q3", "2014 Q3 – 2016 Q4",
"2020 Q2 – 2020 Q4" and "2022 Q2 – 2023 Q1". Staging the quarterly index
(`macro/gdp_quarterly.csv`) showed three of the four were wrong:

- the 2008 crisis run is **Q4 2008 – Q4 2009**, five quarters, not four;
- there is **no negative quarter in 2014 after Q1**, so a band starting in
  Q3 2014 would have drawn a recession during a year of +0.74% growth; the
  run is **Q1 2015 – Q1 2016**;
- COVID is **Q2 2020 – Q1 2021**, four quarters;
- and the quarterly series **ends at 2021 Q4**, so the 2022 band cannot be
  dated by quarter at all and is dated on the calendar year instead.

The bands were re-dated on the staged vintage and the mistake is recorded
here rather than quietly fixed, because it is exactly the failure
`SOURCING_A_COUNTRY.md` describes: a plausible-looking band on a chart is
a claim, and this one was not yet a claim about the country's data.

## Verification

- **Gate** (2026-10-25, lane):
  `pytest tests/test_sources.py tests/test_data.py -k russia` →
  **15 passed, 2 failed** (final run on the committed diff). Both failures are `provenance.json` missing,
  which is a Phase-B artefact (`test_every_plate_cites_files_the_manifest_declares`,
  `test_no_plate_is_drawn_from_a_sidecar`) — nothing in this lane draws a
  plate. `tests/test_numbers.py -k russia` → **1 failed, 1 passed**: the
  failure is `no forms for RUB` (`CURRENCY_AFFIX`), recorded in
  `DATA_NOTES.md` §15 as a core need, not patched here. **Phase B closed
  both:** `provenance.json` is written (12 plates, 29 curated files), and
  the RUB and `ru` blocks landed on `main` with the batch, so the whole
  suite is green — see `DATA_NOTES.md` §16 for the phase's own gate.
- **Determinism, online twice:** all five fetchers re-run against a live
  network → every sidecar **byte-identical** (md5 diff empty).
- **Determinism, offline-warm:** with `http_proxy`/`https_proxy` pointing
  at a closed port and the cache present, every fetcher reproduced the
  same bytes and its anchors still verified.
- **Determinism, offline-cold:** cache removed and network blocked →
  `fetch_rosstat.py` exits **1** on the first download, before any parse,
  and writes nothing.
- **Known observations:** every fetcher asserts its anchors before writing
  (Rosstat nominal GDP 2006 = 26,917.2 and growth 2022 = −1.44; CPI 2015 =
  12.91; the 2014→15 population step = +2.7m; the key rate peak 20.00% on
  28.02.2022; federal deficit 2024 = −3,471.9; BIS household credit
  2024 = 21.5% of GDP). A revised or truncated payload fails at fetch
  time rather than landing in a chart.
- Staged values were checked against a second authoritative route at least
  once each; the exact pairs are in `SOURCES.yaml` (`VERIFIED` lines),
  `DATA_NOTES.md` §13, and the table there.

