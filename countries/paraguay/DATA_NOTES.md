# Paraguay — data notes

What these sources were like to work with, what was converted, which
denominators are which, and what is not drawn and why. `SOURCES.yaml` is
the per-file provenance and `DISCOVERY.md` the publisher-by-publisher
search record; this file is the reasoning that connects them.

Research pass and curation: **2026-10-25**. Every endpoint below was
probed live that day from the discovery network.

---

## 1. The shape of the country's data

Paraguay is the first country in this batch where the **central bank is
the problem**. The Banco Central del Paraguay computes the national
accounts, the consumer price index, the policy rate, the reference
guaraní rate and the household-credit series — and `bcp.gov.py` answers
Cloudflare's "Just a moment…" challenge (HTTP 403) on every path tried,
both schemes, with a browser User-Agent, on 2026-10-25. That is a
recorded block, not a missing statistic.

What that changes, concretely:

- The **national statistical office is not the CPI publisher** here. INE
  publishes population, births and deaths, the labour force survey,
  poverty and income — and it has no consumer-price section at all. A
  reader who assumes every country's CPI comes from its statistical
  office will look for it in the wrong place and conclude it does not
  exist.
- The series that *do* answer nationally are strong: INE's revision-2024
  projection workbook is a complete demography chapter in one file, and
  MEF's fiscal workbook is a complete fiscal chapter in one file. Both
  are official and both are national.
- Everything else is the harmonised layer, and it is labelled as the
  IMF's or the World Bank's **record of what the BCP reported**, never as
  "the BCP's figure". That distinction is the whole point of the
  `official: false` flag on those files.

## 2. Units, denominators, and the guaraní

**No redenomination happened.** Paraguay's guaraní (PYG) is quoted in
whole units; the 2023 proposal to divide by 1,000 was abandoned and no
redenomination has taken place since. There is therefore no "new
guaraní" anywhere in this directory, and no series needed rescaling.

**Two PYG scales from one publisher.** The MEF's current workbook
(`MEFP 2001 ADMINISTRACIÓN CENTRAL 2003-2025 serie anual.xlsx`) is in
*miles de millones de guaraníes* — thousands of millions — while its
older sibling (`Situacion Financiera 1980-2022.xlsx`) is in *millones*.
That is a factor of 1,000 between two files from the same ministry.
`fetch_mef.py` reads the level sheet and the percent sheet and asserts
that the implied GDP is the same number from revenue and from
expenditure, and that it sits in the hundreds of thousands of millions;
a unit read as millions fails there instead of on a plate. The curated
column that carries a level is named `gdp_pyg_bn` and its note says
"thousands of millions".

**Two population denominators, 9% apart.** INE's revision-2024 series
puts mid-2025 population at **6,417,076**; the UN World Population
Prospects series the World Bank republishes puts it at **7,013,000**.
The gap is the 2022 census: INE rebased on it, the UN WPP has not.
Every rate in this directory therefore names its denominator:

- `demography/population.csv`, `mortality/mortality.csv` and the net
  migration rate use **INE's** population (the national denominator).
- `gdp_per_person_usd` is the World Bank's, which divides by the UN
  series. Dividing the same GDP by INE's population gives about 9% more.
  The canonical slot uses the World Bank's so the comparison viewer
  compares like with like across countries, and the alternative is stated
  here rather than hidden.
- Homicide, suicide and road deaths are published per 100,000 by
  UNODC/WHO, and their denominators are neither of the above; they are
  drawn as published rather than recomputed.

**Currency conversion.** The only US$ conversion done in the data is the
minimum wage: `minimum_wage_usd_month = minimum_wage_pyg_month ÷
pyg_per_usd` for the same year, using the IMF's annual period average.
Converting inside the plate instead would leave the convention implicit.

## 3. Definitions kept apart

| Two things that look like one | What is staged |
|---|---|
| **General government** (IMF WEO, accrual, 15–19% of GDP revenue) and **central administration** (MEF, cash, 13–15%) | Two files, two labelled lines, a permanent gap of about four points of GDP. Never spliced. |
| **ILO modelled unemployment** (World Bank, 2006–2025) and **INE's EPHC** (2017–2025) | Two columns. The ILO series is the only continuous one; the national line starts at the 2017 survey redesign and the panel says so. |
| **Goods and services trade** (national accounts, includes electricity exports) and **customs goods by partner** (IMF DOTS) | `trade/trade.csv` and `trade/partners.csv`; different denominators and never joined. |
| **Private-sector credit** and **household debt** | Only private credit is staged. The household split is behind the BCP block and is pending, not relabelled. |
| **Itaipú royalties** and **Itaipú energy-cession compensation** | Two separate revenue columns from the MEF table. Both are fiscal revenue under the binational treaties; neither is a hydro share of GDP. |
| **Projection's births/deaths** and **registered vital statistics** | Only the projection is machine-readable. It is labelled as the projection's estimate, and excess deaths are not computed from it (see §6). |

### The 2017 survey break

INE ran the *Encuesta Permanente de Hogares* (EPH) until 2016 and the
*EPHC* from 2017. Poverty incidence is staged as one column across the
break because it is one published series from one publisher, but the
break is a change of survey design and the plate annotates 2017. Nothing
was smoothed across it.

### The 2022 census and the projection

The revision-2024 workbook is one vintage and contains the census, so the
whole 1950–2050 run is internally consistent. Years after the census base
are projections and the demography plate marks where observation ends.
The series is not mixed with the older revision.

## 4. What the numbers say (anchors used to verify the fetch)

Every one of these is asserted in a fetcher, so a silent revision fails
the refresh rather than changing a plate:

- Real GDP growth 2019 **−0.40%**, 2020 **−0.82%**, 2023 **+5.29%**,
  2025 **+6.64%** (World Bank); the IMF's independent line has 2024
  **4.7** on both.
- GDP US$ **44.74bn** (2024) and **49.28bn** (2025); the nominal rise is
  real growth (6.6%) plus the CPI (4.0%) with the exchange rate roughly
  flat, not an appreciation story.
- CPI **9.77%** (2022), **4.04%** (2025); identical in the IMF and World
  Bank series.
- Guaraní **5,635.09/US$** (2006 average) and **7,545.45** (2025): the
  guaraní's strongest year in this window is 2011 at 4,193.80 (index 134
  on 2006 = 100, up = stronger) and it ends 2025 at index 75 — a nominal
  depreciation of about a quarter over twenty years, with the real
  story being the 2011–2015 reversal and the 2019–2022 slide.
- MEF central administration: revenue **12.63%** of GDP (2006),
  **15.04%** (2024); net lending **−2.00%** (2025) — the same figure the
  December 2025 SITUFIN workbook prints.
- Itaipú/Yacyretá royalties **2.07%** of GDP (2006) falling to
  **0.88%** (2025); the energy-cession compensation **0.42%** (2006),
  **0.58%** (2024) and **0.04%** (2025). The 2025 collapse follows the
  Annex C revision of Itaipú's tariff — the fact is annotated, the cause
  is not asserted by the data.
- Freeze on reality: the MEF's own **PIB** row is 236,681.5 (2019) and
  292,166.8 (2022) in thousands of millions of guaraníes, and the level
  sheet's revenue and expenditure imply the same GDP to within 0.5%.
- IMF DOTS partner shares: **Argentina 10.18%** of goods exports in 2016,
  **28.99%** in 2018 and **26.00%** in 2020 — the values the Fund's
  payload carries. The first curation pass published 0.00 for those five
  years, and the rest-of-world residual absorbed the difference; §10
  records the parse bug and its correction.

## 5. The story the data carry

- **Soy and hydro, not manufacturing.** Exports are 37–46% of GDP on a
  goods-and-services basis while customs goods exports are US$10.9bn —
  the difference is largely electricity sold to Brazil and Argentina,
  which has no "product" in the customs tables. The trade chapter shows
  the national-accounts shares; the partner panel shows the customs
  destinations (Brazil 47.6% of goods exports in 2006, Argentina 33.1%
  and Brazil 32.3% in 2024).
- **The 2019–2020 recession is two negative years**, −0.40% and −0.82%,
  and it is banded as one episode on every time-series panel. 2022 at
  −0.03% is a stagnation and is deliberately not banded.
- **A large informal sector** is visible only as a gap: the EPHC's
  informality tables exist (INE publishes them from 2022) but there is
  no 2006-onwards series, so it is not a canonical panel. It is recorded
  in `DISCOVERY.md` as available work rather than drawn from three years.
- **Inequality falls slowly**: Gini 53.0 (2006) to 44.2 (2024), with the
  poverty rate halving from 47.3% to 16.0%. Both are INE's survey; the
  Gini line is the World Bank's harmonisation of it (see §6).

## 6. What is not drawn, and why

Full endpoint and failure list: `SOURCES.yaml` → `meta.pending`. The
short version:

- **Policy rate, ten-year yield, equity index.** The BCP is blocked; the
  IMF's MFS_IR carries Paraguay's rates only to 2022 and no policy-rate
  indicator; the MEF has no secondary-market yield series; the BVA has no
  continuous index. A policy-rate panel that stopped in 2022 beside 2025
  inflation would imply a stance nobody holds.
- **COFOG functional spending.** The IMF's GFS_COFOG has Paraguay for
  2023–2024 only, in one sector; the MEF publishes the functional
  classification in budget documents, not as an execution series; the
  national open-data portal is down. Two years is not a panel.
- **Household debt and the lending rate.** BIS has no Paraguay series.
- **Excess deaths and COVID-19 deaths.** No registered annual death count
  is machine-readable after 2017, and the revision-2024 series already
  contains the pandemic — subtracting a baseline from it would measure
  the model, not the deaths.
- **Immigration and emigration flows.** No reachable publisher gives
  annual flow counts; only the net is drawn, labelled as a net.
- **The corruption index.** Transparency International's CDN answers 403
  from this network (the same block Ukraine's lane recorded); the landing
  page carries one year only.
- **INE's own Gini.** Published only as a legacy `.xls`; the fetcher stack
  has `openpyxl` only. The values were read by hand and agree with the
  World Bank's harmonised Gini within 0.4 points, which is why the
  harmonised series is the staged one.

## 7. Guaraní as a plate locale: not in this pass

Spanish is the official language; Guaraní is co-official under Ley
4251/2011 and is spoken by a majority. It is not a plate locale here
because **no publisher in this directory issues statistical tables in
Guaraní** — the plates' vocabulary (labour force, poverty line, general
government, non-performing loans) has no official Guaraní terminology to
anchor a translation, and inventing one would put a language on the page
that the country's own statistics do not use. `country.yaml` records the
reason beside the locale list. If INE begins publishing Guaraní
catalogues, this becomes a translation task rather than a research one.

## 8. Departures from the spine

None in the chapter list — Paraguay draws all twelve topics the spine
defines, in spine order. The departures are within chapters. Every
canonical slot that is not drawn is `ctx.pending` with the failing route
on the panel and in `ui.json` in all three locales; nothing is replaced
by a proxy.

| topic | 1 | 2 | 3 | 4 (lens) |
|---|---|---|---|---|
| economy | growth, bars | GDP per person, World Bank/UN | CPI | ILO modelled beside INE's EPHC |
| fiscal | GG accrual + MEF cash, four lines | overall/primary balance + MEF net lending | gross debt | interest paid |
| spending | **pending** (COFOG) | **pending** (COFOG) | whole-economy GFCF | central-government fixed assets |
| trade | exports/imports, national accounts | balance | customs destinations, five shares | **Itaipú–Yacyretá treaty revenue** |
| markets | **pending** (policy rate) | **pending** (10y yield) | guaraní index 2006 = 100 | **pending** (equity index) |
| credit | **pending** (household debt) | **pending** (household lending rate) | NPL ratio | **private-sector credit**, labelled as not household debt |
| people | Gini, World Bank harmonised | poverty + extreme poverty, INE | minimum wage in US$ | **what the minimum is worth in guaraníes** |
| world | GDP, US$ | HDI | **pending** (CPI) | reserves |
| demography | population index, INE and UN | fertility + 2.1 line | crude birth and death rates | natural increase + net migration |
| security | homicide | suicide | road deaths | **the three on one axis** |
| mortality | crude death rate | **pending** (excess) | **pending** (COVID-19) | **life expectancy** |
| migration | **pending** (flows) | net migration, each publisher's denominator | foreign-born share | **the outflow in persons** |

The four lenses that needed a decision, and why:

- **trade** — the royalties and the energy-cession compensation are the
  country's most distinctive economic fact and a reader looks for the
  electricity in the trade chapter. They are drawn there as **fiscal
  revenue under the binational treaties**, in their own panel, with the
  footnote saying the electricity itself is inside the exports series.
  The canonical slots still carry national-accounts trade and customs
  shares only. `test_plates` asserts the label.
- **people** — the statutory minimum is drawn in dollars (the spine's
  unit) and its guaraní path is drawn beside it as an index chained
  against the CPI of one vintage. The finding is not the nominal rise:
  the rate rose 2.3-fold in guaraníes between 2006 and 2024, prices rose
  2.3-fold too, and the real minimum ends at **98 on 2006 = 100** — just
  below where it started. The panel says the index is derived and not a
  published real wage.
- **security** — no extra source exists, so the lens puts the plate's own
  three staged rates on one axis. It answers the question the three
  separate panels leave open: road deaths exceed the homicide rate in
  every year both series cover, from 1.2 times in 2006 to 2.6 times in
  2019.
- **migration** — the UN's net migration in persons, as a level, so the
  size of the outflow is visible; the stock panels cannot show it.

Bands and events: the three downturn bands in `country.yaml` are drawn on
every time-series panel and named on economy slot 1 only. 2022 (−0.03%)
is annotated on the growth panel and deliberately not banded. The events
drawn are in `events.py`: the 2017 EPH → EPHC redesign, fertility falling
below replacement in 2022, the 2024 minimum-wage decree, and the 2025
Annex C tariff revision on the hydro lens.

Every pending panel is disclosed on the page through `ui.json`'s
`unavailable` list in each locale, in the wording of `SOURCES.yaml` →
`meta.pending`.

## 9. Verification performed in this pass

```
make C=paraguay fetch        # six fetchers, sidecars only, anchors asserted
make C=paraguay charts thumbs provenance
make C=paraguay site
pytest                       # the full suite, both phases
```

- `test_sources` and `test_data`: **17 passed** in Phase A. `provenance.json`
  was an empty object there because no plate had been drawn; Phase B
  overwrote it with the recorded reads, and the tests that read it now see
  twelve plates' worth of files, none of them a sidecar.
- `test_numbers` failed for `PYG` in the Phase A lane because that lane's
  base commit predated the batch's currency work. This lane is rebased onto
  the core that carries the PYG forms, and it passes.
- Determinism: every fetcher was run twice online and the sidecars were
  byte-identical; a cold cache re-fetches the same payloads, and an
  offline cold run exits non-zero without writing.
- Phase B: `countries/paraguay/tests/test_plates.py` holds twenty claims
  against the committed CSVs — the two fiscal perimeters, the two
  population denominators, the per-publisher migration denominators, the
  wage conversion at each year's own rate, the CPI chain, the partner
  shares summing to 100, the pending slots and the catalog's spine units.
- Layout: zero faults in `es`, `en` and `pt` (`tests/test_layout.py` has no
  baseline entry for this country, so any fault fails the build).

## 10. Correction found in Phase B: the partner shares

The first curation pass published `trade/partners.csv` with Argentina at
**0.00%** for 2016-2020. That was not a reading of the source: the
fetcher matched series with the regex
`<Series ([^>]*)>(.*?)</Series>`, and the IMF's payload writes a partner
it has no observation for as a self-closing `<Series .../>`. Such a tag
never ends in `</Series>`, so the regex paired it with the NEXT series'
closing tag: the empty partner was recorded with the following partner's
value, and the partner whose observation had been swallowed was then
missing from the parsed map, where `dict.get(code, 0.0)` turned absence
into a zero. The rest-of-world residual absorbed the missing points, so
the columns still summed to 100 — which is exactly why nothing looked
wrong.

The payload itself carries Argentina at 10.18% (2016), 16.49% (2017),
28.99% (2018), 21.39% (2019) and 26.00% (2020). The fetcher now parses
the XML by structure, writes a blank rather than a zero when a named
partner is absent, and asserts the 2016 value at 10.18 ± 0.02. Every
other year, and every other column, was already correct — the regenerated
sidecar differs from the curated file only in those five rows.

No other sidecar changed: re-running the fetcher against the cache
reproduced `fiscal_from_imf`, `growth_from_imf`, `cpi_from_imf` and
`fx_from_imf` byte for byte.
