# Venezuela — what the numbers mean

The research record is [DISCOVERY.md](DISCOVERY.md); the manifest is
[SOURCES.yaml](SOURCES.yaml). This file carries the judgement calls the
plates will depend on, including the ones that ended with a panel left
unfinished on purpose.

## The country this data describes

Venezuela is the first country in the atlas whose **national statistical
system is largely absent**. The Central Bank publishes the CPI, the national
accounts, the policy rate, the reserves and the exchange rate, and its site
cannot be reached from this network at all. The INE publishes a WordPress
portal with census tabulados, a household-survey Gini and a labour tabulado,
but no CPI and no national accounts. The open-data portal times out. What is
left is the harmonised layer — and the whole editorial problem of this
country is to draw it without pretending the Fund's staff estimates are
Venezuelan outturns.

Every plate therefore says which kind of number it is drawing: a national
publication, a harmonised compilation, or a staff estimate. Where the three
disagree, they are separate labelled lines.

## The bolívar, three times

A monetary level in Venezuela is meaningless without naming its currency.
The bolívar was redenominated three times inside the plate window:

| from | unit | divisor to the next unit |
|---|---|---|
| before 1 Jan 2008 | bolívar (Bs) | 1,000 Bs = 1 bolívar fuerte |
| 1 Jan 2008 | bolívar fuerte (BsF, VEF) | 100,000 BsF = 1 bolívar soberano |
| 20 Aug 2018 | bolívar soberano (BsS, VES) | 1,000,000 BsS = 1 bolívar digital |
| 1 Oct 2021 | bolívar digital (VES) | — current unit |

So `1 VES = 1,000,000 BsS = 100,000,000,000 BsF = 100,000,000,000,000 Bs`.

What the atlas does with that:

- **The exchange-rate series is converted, and the divisor is written down.**
  `markets/fx_official.csv` carries the publisher's own figure
  (`lcu_per_usd`), the converted figure in VES (`ves_per_usd`, divided by
  1e11), and the currency index on 2006 = 100. The World Bank restates
  pre-2008 observations in the post-2008 unit — 2005 = 2.08975 is the
  2,089.75 Bs/USD peg divided by 1,000 — so the whole 2006–2017 run is
  quoted in bolívares fuertes and one divisor covers it.
- **No local-currency level is drawn anywhere else.** Nominal GDP, budget
  execution and wages exist in bolívares in the sources and are not plotted:
  across a hyperinflation a nominal level is not a unit. Everything money is
  either a share of GDP, US$, or an index.
- **The pre-2008 segment is not spliced into anything.** The only series that
  crosses a redenomination is the exchange rate, and it crosses it through
  the documented divisor, not through a rebasing assumption.

## Two publishers, one idea — the seams kept visible

Venezuela has no national series for growth, inflation, GDP in dollars or
unemployment, so the atlas draws two harmonised estimates rather than
choosing one and hiding the choice.

| concept | line drawn | second line | why both |
|---|---|---|---|
| real GDP growth | World Bank `NY.GDP.MKTP.KD.ZG` | IMF WEO `NGDP_RPCH` | 2020: −29.8 vs −33.2; same sign every year, different size — both are estimates of a rebased series |
| GDP in US$ | World Bank `NY.GDP.MKTP.CD` (canonical) | IMF WEO `NGDPD` | 2014: 214.8bn vs 128.8bn — the gap is the exchange-rate convention, not a revision |
| consumer inflation | IMF WEO `PCPIPCH` (the only series through the hyperinflation) | the BCV's INPC as the World Bank republishes it, 2009–2016 | the national CPI stops when the BCV stopped reporting; the two are never joined |
| unemployment | ILO modelled estimate (World Bank) | IMF WEO `LUR`, ends 2018 | no national survey series is usable (below) |

The rule applied everywhere: **two columns, two lines, both labelled**, and a
note saying what the difference is. No line in this country is stitched from
two publishers.

## Zeros that are not zeros

The World Bank's API returns `0.0` for `NE.EXP.GNFS.ZS`, `NE.IMP.GNFS.ZS` and
`NE.GDI.FTOT.ZS` in 2006–2011. Venezuela did not export nothing and invest
nothing: the national-accounts series behind those ratios does not exist for
those years and the gateway fills a zero instead of an empty cell. The
fetcher drops those years (asserting they are exactly zero before dropping
them) and the plates draw a line that starts in 2012. Trading a fake zero for
a hole is the same rule as never turning a hole into a zero.

## Derived series (and how)

- **Trade balance** — `exports − imports` from the same publisher and vintage
  on the plate. 2019 = +36.3 points of GDP.
- **Net migration per 1,000** — `SM.POP.NETM ÷ population × 1,000`, both from
  the same World Bank/UN WPP vintage. 2018 = −1,355,602 people ≈ −45 per
  1,000.
- **Gini in points** — the INE publishes a 0–1 index; the atlas draws 0–100,
  so the workbook's value is multiplied by 100. An exact unit change, not a
  re-estimate.
- **GDP in US$ bn** — the World Bank's dollar series divided by 1e9 so the
  axis and the column name agree.
- **Currency index** — `2.147 ÷ lcu_per_usd × 100`, i.e. 2006 = 100, rising =
  stronger against the dollar.
- **HDI** — as published; no derivation. One vintage (HDR 2025) throughout.

## Population denominators

One population series is used for every per-capita and per-1,000 rate:
`demography/population.csv`, the World Bank's `SP.POP.TOTL` = UN World
Population Prospects mid-year, whole territory. It is a **model**, and the
2016–2021 fall in it is modelled emigration, not a count — no census has been
taken since 2011. The INE's own register is not published as a series.

The UNHCR displacement figures are **origin-country totals** (people with a
protection status abroad), so they are never divided by Venezuela's
population to make a rate: they are the lens, on their own axis.

## How the scale conflicts were settled

Per `PLATE_SPINE.md` rule 6 the atlas-wide range lives in `core/spine.py`; a
country never sets its own, and data are never clipped to fit. Venezuela hit
five ranges, and the Phase B render settled them three ways:

| slot | shared range | Venezuela | settlement |
|---|---|---|---|
| economy.growth | −35 … +18 % | −33.2 (2020, IMF) | range **widened atlas-wide**; drawn canonically |
| fiscal.balance | −35 … +8 % of GDP | −31.9 (2018), −25.6 (2017) | widened with it; drawn canonically |
| trade.balance | −30 … +40 % of GDP | +36.3 (2019) | widened with it; drawn canonically |
| economy.inflation | −5 … 225 % | 65,374% (2018), 19,906% (2019) | **not drawn** in the canonical slot; pending, series in the prices lens on a log axis |
| migration.net | −10 … +40 per 1,000 | −45.5 (2018) | **not drawn** in the canonical slot; pending, series in the migration lens |

The first three needed one atlas-wide widening (`core/spine.py`, regenerated
for every country carrying the topic), not a country-local extension. The
last two are not scale problems that a wider number can solve: an arithmetic
axis would have to reach 65,374% to hold the inflation peak, which flattens
twenty years to the axis, and −45.5 per 1,000 is an emigration wave rather
than a migration rate. Both canonical slots therefore stay visibly pending
with the reason on the panel, and the series are drawn in the lens slots,
which exist for exactly this and are not expected to register in the
comparison viewer.

Inside their ranges, and worth saying because it is easy to assume otherwise:
`markets.currency` (log 0.1…200) — the index falls to 21.5, which fits, but
only because the official rate series stops in 2017; `demography.population`
(75…150) — the index peaks at 113.0 in 2016 and is 104.7 in 2025;
`security.homicide` (log 0.1…100), `world.gdp`, `world.reserves`,
`economy.unemployment`, `spending.investment`, `mortality.death_rate`,
`fiscal.revenue_expenditure` and `fiscal.interest` all fit.

No country-local axis is set anywhere: the plates read their ranges from
`core/spine.py` and `tests/test_spine.py` holds them there.

## The two lenses, and how they are labelled

Both are labelled twice — on the panel title, so a reader knows before reading
the axis, and in the footer, so the publisher and the definition travel with
the picture.

- **Prices (people plate, slot 4)**: *"Prices — consumer inflation on its own
  scale (%, log axis)"*. The y-axis is log with plain-number ticks from 10 to
  100,000; the note on the face says "a log axis, because a hyperinflation has
  no comparable linear scale: the canonical slot is left pending"; the footer
  names both series — the IMF's `PCPIPCH` staff estimate for 2006–2025 and the
  BCV's INPC as the World Bank republishes it for 2009–2016 — and says they
  are two lines, never joined. The 2009 seam (26.00% against 27.08%) is
  annotated on the panel and asserted in the tests.
- **The exodus (migration plate, slot 4)**: *"The exodus — net migration
  (bars, left) and the caseload abroad (line, right)"*. Two axes on one lens,
  each labelled by the note on the face ("UN WPP net migration, per 1,000; and
  UNHCR's origin-country caseload, in millions (gold, right). Two publishers,
  two scales, neither clipped to fit the other") and by the footer. The
  caseload is never divided by Venezuela's population: it is a count of
  people with a protection status abroad, not a rate.

## Derived series on the plates (and how)

Everything below is computed at draw time from two columns of the same
publisher and vintage, and the panel footer says "derived":

- **Trade balance** — `exports − imports` of goods and services, World Bank
  national accounts. 2019 = +36.27 points of GDP.
- **Exports and imports in US$ bn** (trade lens) — `share of GDP ÷ 100 ×
  the World Bank's current-US$ GDP`. 2012 ≈ US$110bn of exports,
  2025 ≈ US$14.8bn. A level derived from the same vintage's denominator, not
  a published dollar series.
- **Natural increase** — `crude birth rate − crude death rate`, UN WPP, both
  per 1,000 of the same population: 16.90 in 2006, 7.55 in 2024. The
  `demography.natural_migration` slot draws only this half; net migration is
  on the migration plate, and the panel says so.
- **Net migration per 1,000** — `SM.POP.NETM ÷ population × 1,000`, same
  vintage: 2018 = −1,355,602 ÷ 29,807,592 = −45.48.
- **Foreign-born share** — `UN DESA migrant stock ÷ the same year's
  population`: 4.68% (2010), 4.59% (2015), 4.66% (2020), 4.45% (2024).
  Snapshot years only; never interpolated.
- **Currency index** — `2.147 ÷ lcu_per_usd × 100`: 100 in 2006, 21.52 in
  2017, where the series stops.

## A fiscal seam worth writing down

The WEO's `pb` (primary balance) does not reconcile with its own `ie`
(interest paid) in every year: 2018 is −31.9% overall, 0.69% of interest and
−30.29% primary, where the arithmetic would give −31.21%. 2017 diverges much
further (−25.6, 0.04, −13.23). The primary balance is therefore drawn as
published and the panel calls it "the Fund's own definition"; it is never
recomputed from the interest line, and `tests/test_plates.py` pins that
mismatch so a future vintage which does reconcile is noticed.

## What is not drawn, and why

These are findings, not omissions. Each has its routes and exact failure in
`SOURCES.yaml` `meta.pending`.

- **The credit chapter** — no panel it could fill: BIS has no Venezuelan
  household-credit series (HTTP 404 for the VE key, 200 for the US key), the
  BCV is unreachable, and SUDEBAN publishes no machine series.
- **The policy rate** — BCV only, unreachable; the IMF has no Venezuelan
  policy-rate indicator and its exchange-rate dataset returns an empty
  Venezuela slice. A rate-versus-inflation panel cannot be drawn from the
  inflation side alone.
- **The equity index** — no verified redistributor series exists for the
  Caracas exchange's index; the market is thin enough to need its own
  definition note.
- **Government debt** — `GGXWDG_NGDP` has no Venezuelan observations at all
  in the October 2026 vintage; the World Bank's debt indicator returns zero
  rows. The panel is pending, not zero, and no alternative concept is
  substituted.
- **Export destinations** — Venezuela's Comtrade reporting stops after 2013,
  and the 2013 submission attributes about US$82bn of US$88bn of exports to
  residual buckets ("nes" partner groups), so a destination chart would chart
  Comtrade's code list. Pending.
- **Poverty** — the World Bank's PIP series ends in 2006; the INE publishes no
  poverty tabulado; the ENCOVI university survey is not an official statistic
  and is not used.
- **Minimum wage** — the Imprenta Nacional's DNS does not resolve, no machine
  series exists, and the US$-per-month conversion the spine wants is
  impossible after 2017 because the official exchange rate ends there.
- **COFOG and public investment** — Venezuela reports no COFOG to the IMF and
  the MPPEF's functional budget presentation stops in 2009.
- **COVID-19 deaths and excess deaths** — WHO publishes no general COVID death
  indicator in its GHO catalogue any more (and its global CSV now serves
  HTML), and excess deaths need the INE's legacy `.xls` death counts.
- **National unemployment, births, deaths** — the INE's labour tabulado
  identifies its rows by numeric concept codes whose legend is not in the
  workbook; the civil-registration tabulados are legacy BIFF8 `.xls` with no
  coverage statement and the host is unreachable from the build network.
  Deferred rather than guessed.
- **Reserves after 2017, exchange rate after 2017** — the BCV stopped being
  reachable; both lines end where the publisher stops, with the hole visible.

## Annotations the plates must carry

Two seams are recorded in the CSV headers and must appear on the panels:

- **2009 inflation, 26.00 (IMF) against 27.08 (the BCV's INPC).** Every other
  overlap year agrees to the second decimal. The BCV rebased its INPC in 2008
  and the Fund did not follow the revision — a 1.1-point seam, annotated, not
  smoothed.
- **Suicide, 6.12 (2015) to 10.49 (2016) and back to 7–9 afterwards.** A 71%
  one-year rise that then falls back is a change in the WHO estimate vintage,
  not behaviour.
- **Growth before and after the rebasing.** The IMF's Venezuelan GDP level is
  a rebased staff estimate, so growth rates either side of a rebasing year are
  not strictly comparable; the note goes on the economy panel.

## The Gini needs its own disclosure

`people/gini.csv` is the one national series that runs the whole window, and
the INE's published values sit at 0.38–0.39 from 2014 to 2025 — a flat
inequality line through the largest economic collapse in the region's modern
history. Independent university surveys (ENCOVI) report far higher
inequality. The atlas draws the official series because it is the official
one, and the plate must carry a note saying that the publisher documents
neither the survey's coverage nor its non-response in the emigration years.
This is exactly the "what a cause-of-death code follows" trap in a different
costume: the series is real, the publisher's production of it is not
transparent, and silence would read as a finding.

## `last_full_year`

**2025.** The IMF's October 2026 vintage treats 2025 as a finished year
(estimates, not projections) for growth, inflation and the overall balance,
and the World Bank carries 2025 GDP and population. There is no national
outturn to prefer over them, because there is no national outturn. Anything
after 2025 is a WEO projection and lives only in a `_proj` column — and for
the fiscal series there is no `_proj` column at all, because the vintage
publishes no Venezuelan fiscal projections beyond 2025.

## Fetchers

| fetcher | writes | publisher |
|---|---|---|
| `fetch/fetch_worldbank.py` | `data/**/*_from_worldbank.csv` | World Bank WDI |
| `fetch/fetch_imf.py` | `data/**/*_from_imf.csv` | IMF WEO via DataMapper |
| `fetch/fetch_undp.py` | `data/world/hdi_from_undp.csv` | UNDP HDR |
| `fetch/fetch_unhcr.py` | `data/migration/displacement_from_unhcr.csv` | UNHCR |
| `fetch/fetch_ine.py` | `data/people/gini_from_ine.csv` | INE tabulados |

Each writes review sidecars only, checks the payload shape before caching (a
200 carrying HTML is rejected), pins the values the discovery pass verified,
and never touches a curated file. `--offline` reads the cache only: a cold
cache exits non-zero and writes nothing, and repeated runs are byte-identical
(checked 2026-10-25: two online runs and two warm offline runs of all four
network fetchers produced identical sidecars; cold offline exits 2).

`fetch_ine.py` **cannot run from this network**: the INE host does not answer
the build network at all (curl exit 000 after a 25-second timeout, both
schemes, both hostnames, no proxy configured), though it answers an agent's
egress proxy. The 2026-10-25 workbook's values are preserved cell by cell in
`fetch/reference_ine_gini_2026-10-25.csv`, and the curated Gini was promoted
from that dated reference. Running the fetcher from a network that reaches the
INE regenerates the sidecar to diff against it — that is the expected path,
not a workaround.

## What Phase B asked of `core/` — resolved

1. **A log axis for the hyperinflation.** Not granted atlas-wide, and not
   needed: the canonical `economy.inflation` slot stays pending and the series
   is drawn in the prices lens on a log axis, which a lens may set for itself.
   That is the same settlement the atlas uses for Ukraine's wartime migration:
   the comparable slot keeps its scale, the outlier series keeps its data.
2. **Shared-range decisions for growth, the fiscal balance, the trade
   balance and net migration.** Granted for the first three — the atlas-wide
   ranges were widened once in `core/spine.py` and regenerated for every
   country carrying the topic — and refused for net migration, which is drawn
   in the migration lens instead. `markets.currency` needed nothing: its log
   floor of 0.1 already holds the 21.5 the index falls to.
3. Nothing else. The country's own directory reads only its own data, and
   `tests/test_isolation.py` proves it.

## Phase B, as delivered

Eleven plates on the spine, in this order: economy, fiscal, spending, trade,
markets, people, world, demography, security, mortality, migration. Three
locale catalogs (es, en, pt), `events.py` for the two dated rules drawn (the
2018 redenomination on the currency panel and COVID-19 on the death rate),
eleven chapter cards whose copy interpolates the committed figures, and the
localised `unavailable` list of eleven gaps. Rendered, thumbnailed and
provenanced in all three locales; the layout probe reports zero faults in
each.
