# The plate spine

Every country draws the same chapter with the same panels in the same
places, on the same scales, in the same units. That is what makes the
comparison viewer work: it wipes one country's plate across another's at
the same size, so a reader can only read the difference if growth sits
over growth and a homicide rate sits over a homicide rate.

This file is the decision record (2026-10-22). `core/spine.py` is its
executable form, and `tests/test_spine.py` holds every country to it.

## Rules that apply to every plate

1. **One frame.** Every plate is 2 × 2 at 16.0 × 10.2 in, `right=0.955`.
   There are no 3 × 2 plates and no other figure sizes. A chapter that
   needs a fifth panel needs a better fourth one.
2. **One time axis.** Every time-series panel spans the country's window
   (2006–2026 for all of them today) and labels every second year, so
   `tick_every: 2` everywhere. There are no bespoke x-windows. Snapshot
   panels (export products by year) are allowed only in a lens slot.
3. **Shared slots, then the lens.** Each topic below lists its slots. A
   *canonical* slot holds the same indicator, in the same unit, on the
   same axis in every country. A *lens* slot is the country's own story,
   such as US overdoses, Brazilian police killings or the Argentine
   parallel dollar. It is labelled as such and is not expected to register.
4. **One unit per canonical slot.** Counts become rates where countries
   differ in size, using these bases:
   - deaths and violence: per 100,000 people;
   - births, deaths and migration flows: per 1,000 people;
   - money: % of GDP, or US$ when it must be a level;
   - currencies: index 2006 = 100, rising = stronger against the US$;
   - equities: index 2006 = 100, in US$.
   Local-currency levels and raw counts survive as annotations or in the
   lens slot, never as the shared unit.
5. **Converting a count to a rate:** rate = count ÷ population × base.
   The population must be the same year and the same territorial and
   legal scope as the count. Examples: England & Wales homicides over the
   England & Wales population, Japanese-national deaths over the
   Japanese-national population, mid-year where the publisher's own rates
   use mid-year. Where the publisher already publishes the rate, use the
   published rate. The panel or DATA_NOTES names the population series.
6. **One atlas-wide scale per canonical slot.** It is listed below and
   lives in `core/spine.py`. Every country, including one whose panel is
   visibly pending, uses exactly that scale and those ticks. A pixel wipe
   cannot compare country-local extensions. When accepted data leave the
   range, rendering fails: widen the single shared range deliberately,
   regenerate every country carrying that topic, and review the visual
   cost. Data are never clipped or silently rescaled. Log axes are used
   only where the spine says so, for every country at once.
7. **Same direction everywhere.** Higher is more on every axis, with no
   inverted Gini or rank axes. The title says which way is good when it
   matters.
8. **Same marks.** Every time-series panel uses `ctx.line` or `ctx.bars`,
   so the running year is dashed or hatched the same way everywhere.
   Recession bands from country.yaml go on every time-series panel, via
   `add_recessions`, labelled on slot 1 only. Events come from
   `events.py` via `add_event`.
9. **Commentary per country.** Each canonical panel carries at most two
   short notes that say what this country's line means, such as the
   bailout year, the method break or the target. Breaks and definitional
   seams are drawn as seams (separate segments plus a note), never spliced.
10. **Same series definition across countries.** Where national
    definitions differ, the canonical slot uses the harmonised series
    (Eurostat, IMF, World Bank, BIS, OECD, WHO/UNODC). The national series
    rides beside it as a second line when it differs in a way worth
    showing. Which one is which is said in the legend.
11. **Gaps are fetched, not left.** If a country lacks a canonical
    indicator, check its SOURCES.yaml and the harmonised publishers
    first. Fetch it if it exists, through the country's fetchers with
    sidecars and a manifest entry. `ctx.pending` is only for data that
    genuinely do not exist, and its note says why.

## What the viewer reads off a spine plate

Because every spine plate is the same 2×2 frame, the viewer can find the panel
under a click or a pointer without being told where it is.

- **Panel cells.** `spine.panel_cell(i)` is the cell panel `i` occupies on the
  picture, as fractions of its width and height. It repeats the margins the
  figure is built with (`PANEL_INK`, `INK_PAD`) and is measured from the
  panel's ink (title, ticks, labels), so all four crops are the same size.
  `tests/test_spine.py` draws every plate that has stories and fails if a panel
  spills out of its cell.
- **The readout.** `Infographic.save` writes `<plate>[.<lang>].hover.json`
  beside the picture (`core/hover.py`): where each panel's axes sit, its limits
  and the series it drew, read off the finished figure. The viewer uses it to
  say what each series was at the year under the pointer. It is generated, so
  it is committed with the plate like a thumbnail; a plate with none simply has
  no readout. A panel on a calendar axis, with bars grouped by year, is read;
  bars laid on their side, or a panel with no year to point at, are not.

## Topics and slots

Slot numbers are reading order (1 top-left, 2 top-right, 3 bottom-left,
4 bottom-right). "ref" is the fixed atlas-wide y-range. Historical arrow
marks show which end originally drove range selection; they do not permit
country-local extension.

### economy — growth, income, prices, jobs
| slot | indicator | unit | ref scale | preferred source |
|---|---|---|---|---|
| 1 | Real GDP growth | % per year, bars | −18 … +18 symmetric | national accounts / Eurostat |
| 2 | GDP per person | US$ current, line | log 500 … 200,000 | World Bank NY.GDP.PCAP.CD |
| 3 | Consumer price inflation (+ target line) | % per year | −5 … 225 | national CPI; HICP beside it in the EU |
| 4 | Unemployment rate | % of labour force | 0 … 30 ↑ | national LFS; Eurostat/ILO beside it |
The nominal GDP size moves to **world** slot 1.

### fiscal — general government, calendar years
| slot | indicator | unit | ref | source |
|---|---|---|---|---|
| 1 | Revenue and expenditure | % of GDP, two lines | 0 … 70 | Eurostat / OECD / IMF WEO |
| 2 | Overall balance (bars), primary balance (line) | % of GDP | −16 … +8 ↕ | same |
| 3 | Gross debt | % of GDP | 0 … 300 | Eurostat EDP / IMF GGXWDG_NGDP |
| 4 | Interest paid | % of GDP | 0 … 10 | Eurostat D41PAY / IMF / OECD |
A federal or fiscal-year national perimeter (US, Canada, Brazil central
government) is drawn as a second, labelled line where it is the series the
country argues about. The general-government line stays canonical.

### spending
| slot | indicator | unit | ref | source |
|---|---|---|---|---|
| 1 | Spending by function, stacked | % of GDP | 0 … 65 | COFOG (Eurostat / OECD table 11) |
| 2 | Social protection vs everything else | % of GDP | 0 … 45 | COFOG |
| 3 | Investment rate, whole economy (GFCF) | % of GDP | 0 … 50 | national accounts / WB NE.GDI.FTOT.ZS |
| 4 | Public investment (government GFCF) | % of GDP | 0 … 12 | Eurostat P51G / OECD |
COFOG groups (seven): social protection, health, education, general public
services, economic affairs, defence + public order, other. A country
without COFOG uses its national functional classification, mapped onto
those seven where the mapping is clean, and the note says so.

### trade — goods and services, national-accounts basis
| slot | indicator | unit | ref | source |
|---|---|---|---|---|
| 1 | Exports and imports | % of GDP, two lines | 0 … 100 ↑ | national accounts / WB NE.EXP/IMP.GNFS.ZS |
| 2 | Trade balance | % of GDP, bars | −15 … +15 ↕ | same |
| 3 | Top export destinations | % of goods exports | 0 … 90 | customs / Comtrade |
| 4 | lens (products, energy share, two official deficits, …) | | | |
US$ or local-currency levels go in the annotations.

### markets
| slot | indicator | unit | ref | source |
|---|---|---|---|---|
| 1 | Policy rate vs inflation | %, two lines | −5 … 225 | central bank; CPI from economy |
| 2 | 10-year government bond yield | %, annual average | −2 … 30 | central bank / Eurostat irt_lt_mcby_a |
| 3 | Currency against the US$ | index 2006 = 100, annual average, up = stronger | log 0.1 … 200 | central bank; US uses the broad dollar index |
| 4 | Main equity index in US$, with the S&P 500 in US$ dashed | index 2006 = 100 | log 10 … 1,000 | exchange / redistributor (`official: false`) |

### credit
| slot | indicator | unit | ref | source |
|---|---|---|---|---|
| 1 | Household debt | % of GDP | 0 … 140 | BIS total credit WS_TC Q.CC.H.A.M.770.A (year-end Q4) |
| 2 | Household lending rate vs policy rate | % | −2 … 110 | central bank (new mortgage loans where possible) |
| 3 | Non-performing / delinquent loans | % of loans | 0 … 20 ↑ | central bank (definition in the legend) |
| 4 | lens (debt service ratio, stock in local currency, arrears, …) | | | BIS WS_DSR where available |

### people
| slot | indicator | unit | ref | source |
|---|---|---|---|---|
| 1 | Income inequality, Gini | 0 … 100 points, not inverted | 20 … 60 | national survey + WB/SILC beside it |
| 2 | Poverty rate, national definition; WB US$8.30/day line beside it where it exists | % of people | 0 … 80 | national; WB PIP |
| 3 | Minimum wage | US$ per month at the annual average exchange rate | 0 … 3,000 ↑ | national; converted with the staged FX |
| 4 | lens (median income, child or old-age poverty, employment, …) | | | |
A country with no statutory national minimum wage (Italy, Switzerland)
says exactly that in slot 3 via `ctx.pending`, which is a true statement,
not a gap.

### world — the country among the others
| slot | indicator | unit | ref | source |
|---|---|---|---|---|
| 1 | GDP at current prices | US$ bn | log 10 … 50,000 | World Bank NY.GDP.MKTP.CD |
| 2 | Human Development Index | 0 … 1 | 0.5 … 1.0 | UNDP |
| 3 | Corruption Perceptions Index | 0 … 100 score | 0 … 100 | Transparency International (2012+ method; earlier ×10 shown as a seam) |
| 4 | Official reserves | US$ bn | log 1 … 5,000 | WB FI.RES.TOTL.CD / central bank |
The WEF competitiveness rank was discontinued after 2019 and leaves the spine.

### demography
| slot | indicator | unit | ref | source |
|---|---|---|---|---|
| 1 | Population | index 2006 = 100, level in the note | 80 … 150 | national statistics |
| 2 | Total fertility rate (+2.1 line) | children per woman | 0 … 3.5 | national / WB |
| 3 | Crude birth and death rates | per 1,000 people | 0 … 25 | national / WB / Eurostat |
| 4 | Natural increase and net migration | per 1,000 people | −10 … +40 | national / Eurostat CNMIGRATRT / WB SM.POP.NETM |
Projections are a note on slot 1 (e.g. projected peak and year), not a
panel with its own axis.

### security
| slot | indicator | unit | ref | source |
|---|---|---|---|---|
| 1 | Homicide rate: national series, plus UNODC/WHO where it differs | per 100,000 | log 0.1 … 100 | national; UNODC VC.IHR.PSRC.P5 |
| 2 | Suicide rate | per 100,000 | 0 … 40 | national cause-of-death / WHO |
| 3 | Road traffic deaths | per 100,000 | 0 … 40 | national / WHO |
| 4 | lens (femicide per 100k women, police killings, overdoses, workplace deaths, …) | | | |

### mortality
| slot | indicator | unit | ref | source |
|---|---|---|---|---|
| 1 | Crude death rate | per 1,000 people | 0 … 16 | national vital statistics |
| 2 | Excess deaths | % above the 2015–2019 average | −20 … +40 | computed from slot 1's counts |
| 3 | COVID-19 deaths, underlying cause | per 100,000 | 0 … 300 ↑ | national cause-of-death |
| 4 | lens (influenza, dengue, the big killers, …) | per 100,000 | | |
Korea's cause-of-death content moves from security to a new mortality
chapter, and Argentina's from demography to a new mortality chapter.

### migration
| slot | indicator | unit | ref | source |
|---|---|---|---|---|
| 1 | Immigration and emigration | per 1,000 people | 0 … 50 | national / Eurostat |
| 2 | Net migration | per 1,000 people | −10 … +40 | national / Eurostat / WB |
| 3 | Foreign-born share of the population (+ foreign-citizen share) | % of population | 0 … 50 ↑ | national / Eurostat |
| 4 | lens (asylum, permits, citizenship, regimes, …) | | | |

### prices (Argentina only)
Argentina keeps its prices chapter as a national lens: inflation, the
official and parallel dollar, and the gap. Its CPI is also drawn in
economy slot 3, its currency in markets slot 3 and its reserves in world
slot 4, so it meets every other country.

## Chapter mapping fixes
- **Argentina:** "living" → people, "people" (vital statistics) →
  demography, mortality content → a new mortality chapter, and new
  spending and world chapters from staged and harmonised data.
- **Korea:** "safety" keeps topic security on the slots above, and its
  cause-of-death panels move to a new mortality chapter.
- **USA:** economy is rebuilt on the spine, unemployment moves there,
  TFR and life expectancy leave world, and `tick_every` becomes 2.
- **Canada:** chapters blocked on StatCan get built from harmonised
  sources where the spine allows (WB/IMF/BIS/OECD), with StatCan as the
  national line when it returns.
