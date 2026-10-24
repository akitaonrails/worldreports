# China — data notes

What the sources were like to work with, which conversions the plates make,
which population every rate divides, and which seams and bands were decided
— and decided NOT to draw. Where this file and `SOURCES.yaml` disagree, the
manifest wins; this is the prose record.

## Publication completion — 2026-10-23

The reviewed harmonised inputs now feed all twelve comparison-spine chapters
in Simplified Chinese, English and Portuguese. The national layer remains an
explicitly declared absence, not a substitution: panels either name the
World Bank, IMF, UNDP, UNODC/WHO or UN Comtrade reading, or show a pending
marker with the blocked national route. No panel calls an international line
an NBS, GACC, PBoC, SAFE or MOF series. The committed output contains all 36
localized plates and thumbnails, and `provenance.json` records every stable
CSV actually read. Semantic tests pin the perimeters, denominators, snapshot
years and non-splicing rules described below.

## Bands: quarterly evidence unavailable; decision pending

`country.yaml` carries `bands: []`. Against the STAGED vintage, every year in
both columns of
`data/economy/gdp_growth_intl.csv` (World Bank WDI and IMF WEO, 2006–2025)
is positive — the trough is 2020 at +2.34 / +2.30, not a contraction.
That establishes only that the annual series contains no annual contraction.
It does not establish whether two consecutive negative quarters occurred.
The deceleration from 14% to 5% is carried by the line shape, plus events.
`countries/china/tests/test_plates.py` pins the annual fact and the absence of
quarterly evidence; it does not infer a quarterly result from annual values.

The strict two-consecutive-quarter test wants the quarterly series, which
is blocked with the NBS API (403, see SOURCES.yaml pending). The annual
evidence cannot decide that test. Confirm the q/q signs when an NBS route
opens. Until then the recession-band decision is pending and unsupported;
`bands: []` records that no evidence-backed band is published, not that a
recession has been ruled out.

## 2020 is not a band

China's annual GDP GREW in 2020 (+2.3%). The staged vintage shows the
positive-but-depressed annual result. It is drawn as the bar's shape and an
event note (COVID-19 shock), not as a recession-band conclusion. 2022 (+3.1)
and the 2024–25 slowdown are events in the same way; none settles the missing
quarterly test.

## Harmonised layer carries the national slots (NBS 403 / GACC 412)

The NBS machine API (data.stats.gov.cn, 403) and GACC (customs.gov.cn,
412) are blocked sources parked on the SOURCES.yaml pending list — never
scraped around, never invented. Under the spine's rule 10 (same series
definition across countries) the canonical slots are drawn from the
harmonised publishers instead: World Bank WDI, IMF WEO via DataMapper,
UNDP HDR25, UN Comtrade, Yahoo for the market index. Every such panel
says in its note or label that the line is the harmonised reading and
that the national series of record (NBS / GACC / PBoC / SAFE / MOF)
replaces it when the block lifts. This is the same pattern Canada used
pre-StatCan. When the national line joins it rides BESIDE the
international line as its own labelled column — two lines, never
spliced, never averaged (the China rule, COUNTRIES.md row 7).

## Population series used for every rate

One population series for all conversions: `data/demography/population_intl.csv`
(World Bank SP.POP.TOTL, UN WPP 2024-revision vintage). Same year, same
territorial scope (mainland China on the UN definition) as every count it
divides. Where the publisher already publishes a per-capita rate (WB/UNODC
homicide, WHO suicide and road deaths, WB crude birth/death rates) the
published rate is used directly — no recomputed rate — and the series
name goes in the panel note.

## Conversions the plates make

- **Equity index (markets slot 4):** the staged SSE Composite is a CNY
  price index (Yahoo redistribution, `official: false`). The spine unit
  is US$ at 2006 = 100, so each year's close is divided by that year's
  World Bank official exchange rate (PA.NUS.FCRF, CNY per USD, annual
  average) and rebased with `index_2006`. S&P 500 beside it, dashed,
  same convention, also Yahoo redistribution.
- **Currency (markets slot 3):** `fx_index` of PA.NUS.FCRF (CNY per USD):
  up = stronger renminbi. PBoC's 中间价 fixing and the CFETS close are
  two national series and both blocked/pending; when they open the
  harmonised single rate is replaced, not blended.
- **Birth counts (demography lens):** derived as crude birth rate ÷ 1000
  × population — the WPP rate and the WPP population are one internally
  consistent vintage, so the product is that vintage's births, in
  millions. Labelled derived. The one-child → two-child → three-child
  break in this series is the demography lens; it replaces the property-
  sector lens, for which no price series is staged.
- **Natural increase (demography slot 4):** crude birth rate − crude
  death rate, both WB published rates (same source, same scope).
- **Trade balance (trade slot 2):** exports % GDP − imports % GDP, both
  from the staged WB openness file — arithmetic on one source, not a
  splice across two.

## Seams and holes

- WB Gini stops at 2022; 2006–07 and 2009 are holes in the WB series.
  Holes stay holes; the NBS Gini (different definition) would be its own
  labelled column when the block lifts.
- UN DESA migrant stock exists only at five-year vintages (2010, 2015,
  2020, 2024) — a stepped line, not interpolated.
- HDI is ONE vintage (HDR25) and ends 2023 (2024 not published for CHN).
- Comtrade partner shares are a 2023 SNAPSHOT, kept in the country lens rather
  than the canonical destination time-series slot; Comtrade's China report
  carries no Taiwan partner code, and that attribution caveat rides in the CSV
  header.
- No plate splices a harmonised line to a national one anywhere: there
  are no national lines yet to splice to.

## Honest pending panels

Slots whose only publisher is blocked or does not publish for China stay
`ctx.pending` with the reason on the panel: COFOG spending functions,
public investment, PBoC policy rate (LPR — a definitional break, two columns,
never one), 10-year yield, comparable household lending rates, China's
national minimum wage (set by provinces — there is no single national
statutory rate to plot), top export destinations as a time series, and
China's covid-19 deaths (official counts stopped in 2023 and are not
comparable). The IMF Fiscal Monitor now fills the harmonised fiscal-flow
slots, and BIS fills household credit plus the broader private-sector DSR;
neither is relabelled as a Chinese national series.
