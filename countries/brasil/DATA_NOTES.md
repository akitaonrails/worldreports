# Notes on the sources

Working notes on what Brazilian official statistics are actually like to
gather, kept separate from [SOURCES.yaml](SOURCES.yaml). That file is the
manifest and says *what* each series is. This one is hand-written and says
what I thought of it — where the data is good, where it is fragile, and which
mistakes it invites.

Everything below is either something I hit directly while building this
repo, or something verified against a live endpoint during research. Where
a claim is second-hand or was true on one day only, it says so.

---

## The short version

Brazilian official data is better than its reputation. IBGE, BCB and
Tesouro all publish clean, documented, free, no-key APIs that return JSON
and go back decades. The BCB's SGS in particular is close to ideal: one
URL pattern, one series code, daily granularity, values from 1971.

The difficulty is almost never *getting* a number. It is knowing what the
number counts, and noticing when that changed.

So the useful question is not "is this source reliable?" — nearly all of
them are, in the sense that the institution is honest and competent. The
question is "what kind of thing is this, and what will silently go wrong
if I treat it as a simple time series?" Those failure modes differ by
*kind*, not by degree of trustworthiness, which is why this document is
organised around the failure modes rather than ranked by publisher.

---

## Six ways these series go wrong

### 1. The code changes underneath you

The single most dangerous pattern, because the data keeps arriving and
nothing errors.

**Dengue, found while building plate 10.** The ICD-10 2019 revision moved
dengue from `A90`/`A91` to `A97`. SIM switched during 2025: `A97` shows up
with 4 deaths in 2024, then carries the whole series from 2025 while
`A90`/`A91` vanish. A fetcher reading only the old pair reports 2025 as a
year in which **nobody in Brazil died of dengue**. DATASUS does signal it —
the `A90` row is labelled `>> A97` — but it returns a perfectly well-formed
table either way.

**Federal spending, função 12.** In 2000 the budget function changed from
"Educação e Cultura" to "Educação". The 1999→2000 fall from R$16.06bn to
R$10.62bn is entirely reclassification.

**Femicide.** The qualifier was created by Lei 13.104/2015 and took years
to be applied consistently. The rising femicide share through 2015–2019 is
substantially courts and police learning to use a new category, not a
surge in killing. This repo's plate 9 says so on the plate, because the
two lines move in opposite directions and invite exactly the wrong read.

### 2. The instrument changes, and the old and new are both "official"

- **PNAD → PNAD-C at 2015/16.** Illiteracy drops 7.95 → 6.7 and years of
  schooling for 25+ jumps 7.2 → 9.1. Neither is a change in Brazil.
- **PME → PNAD-C** for unemployment: different age floor (15+ vs 14+),
  different concept (*desemprego aberto* vs *desocupação*), six metro
  regions vs national.
- **Tax burden, 2010.** STN moved to GFSM-2014 and dropped FGTS and
  Sistema S, worth about −1.8pp.
- **National accounts vintages.** The ref-2000 revision raised the 2004 GDP
  level about 10.9%. Usefully, SIDRA serves only the current vintage, so
  the break bites only if you quote contemporaneous figures against it.

The honest treatment is a separate column and a visible gap, never a
splice. This repo does that for homicides (IPEA/SIM vs FBSP) and says so
in the plate subtitle.

### 3. The series is a model, not a count

Worth flagging loudly because it looks identical to measured data:

- **IPEA's "estimated" homicides** add a modelled share of deaths filed
  with undetermined intent. The gap reached 17% in 2024. Both the
  registered and the estimated series are official.
- **IBGE population beyond 2025** is a projection, not a measurement, and
  the repo marks it `kind="projection"` for that reason.
- **Rates are often not recomputable.** IPEA's homicide rates use a
  documented patchwork of denominators; the Atlas PDF itself prints 20.1
  where the API gives 20.03. Use the publisher's rate, don't derive it.

### 4. Two official numbers for the same thing

Not an error, and not resolvable by picking the "better" one.

- **COVID deaths, 2020: 194,949 or 213,233.** The Ministry's panel counted
  notifications as they arrived during the emergency; SIM counts death
  certificates as finally coded. Different instruments, different
  purposes, both correct.
- **Education spending as % of GDP, 2021: 5.50, 5.503, or 4.561** — INEP,
  UNESCO UIS (which mirrors INEP to three decimals), and OECD EAG (ISCED
  1–8 only). Never put these on one axis.
- **Illiteracy 2022: 7.0% (Censo) or 5.6% (PNAD-C)**, same universe.

### 5. Absence that looks like zero

The subtlest class, and the one that bit this repo twice in one session.

- **TabNet omits rows with no deaths.** A cause that genuinely had zero and
  a cause you failed to query are byte-identical in the response.
- **Querying SIM for `U07` returns zero, not an error.** The `obt10uf`
  definition carries no ICD-10 chapter XXII at all, so the natural query
  for COVID succeeds and reports nothing. COVID lives under `B34`, whose
  pre-pandemic baseline of ~64 deaths a year is the only thing that makes
  that readable as a proxy.
- **SIDRA returns HTTP 200 with eight blank-named `".."` rows** when you
  omit a classification — which a naive fetcher writes as real years.
- **Our own bug, same shape.** `u_eop.get(base_year, 1)` silently returned
  `1` because `dollar.csv` began in 2006 and IBOV in 2005, multiplying the
  S&P-in-reais line by the raw exchange rate instead of its ratio to the
  base year. It inflated a published chart by 2.3407× — the 2005 year-end
  PTAX — under a title reading "R$100 invested in 2005". A default value
  turned a missing year into a plausible wrong answer.

The lesson is the same in all four: **make absence raise, not default.**

A close cousin: **BCB's SGS returns values without names.** `bcdata.sgs.20717`
gives you a clean monthly series and no indication of what it measures. By
magnitude it looks like the household lending rate — it is the highest of
its family, at 48.5% — but it is *recursos livres, total*. The household
series is 20716, at 38.2%. Both are plausible, both are "the interest rate
on credit", and plotting one under the other's label would be invisible on
the chart and wrong by ten points. The fix is cheap and worth doing every
time: BCB's open-data catalog carries a `codigo_sgs` field, so
`dadosabertos.bcb.gov.br/api/3/action/package_search?fq=codigo_sgs:20717`
returns the official name. Never label an SGS series from its values.

### 6. Delivery is more fragile than the data

These are operational, not statistical, but they break builds:

- **`download.inep.gov.br` serves an incomplete TLS chain.** The
  intermediate is never sent, so Python *and* curl both fail with
  `CERTIFICATE_VERIFY_FAILED`. The fix is appending the intermediate to
  certifi's bundle — not `verify=False`.
- **Tesouro anexo IDs rotate every edition**, so hard-coded publication
  URLs break on a schedule.
- **BCB SGS under a WAF block returns HTTP 200 with an HTML body** titled
  "Requisição inválida!". Any fetcher that checks only the status code
  will write blank cells and exit 0.
- **INEP download URLs cannot be guessed.** Year tabs are AJAX stubs, and
  the path family changes most years — five distinct shapes for one
  indicator across 2007–2025.
- **`dados.gov.br`'s CKAN API now requires a key** (401), and several
  former open-data hosts no longer resolve at all.

---

## How much to trust what, in practice

Ordered by how little interpretation they need, not by institutional
quality — every publisher here is honest.

| Tier | Sources | Why |
|---|---|---|
| **Just use it** | BCB SGS (PTAX, Selic, reserves, debt, credit, household indebtedness), IBGE SIDRA v3, UNDP HDI | Stable URL patterns, single vintage, documented, no key, long history. Reserves go back to 1971 and are USD-denominated, so they survive every currency redenomination. Resolve every SGS code to its official name first — see above. |
| **Use it, read the notes** | IBGE national accounts, World Bank/UIS mirrors, Tesouro series API | Correct, but vintage- and definition-sensitive. The WB gini/poverty series mirror national surveys, so they inherit survey breaks without showing them. |
| **Use it, annotate the plate** | SIM/DATASUS, IPEA Atlas, FBSP, INEP | Excellent data about a *classification process* as much as about the world. Needs the caveat drawn, not footnoted. |
| **Handle with care** | OECD/PISA, Transparency International CPI, WEF | Real methodology breaks the publishers themselves disclaim. TI says pre-2012 CPI scores are not comparable year to year *at all*. |
| **Don't** | Nominal R$ series before 1995, Ibovespa before 1997 | The unit changes mid-series. SGS series 1 crosses four redenominations with no unit column; SGS series 7 contains a verified 10:1 index division between Dec/1996 and Dec/1997. |

---

## Things worth saying plainly

**Coverage is better than expected going back, and worse than expected
coming forward.** HDI reaches 1990, gini and poverty 1981, IPCA 1980,
reserves 1971 — all clean, all one vintage. Meanwhile INEP's consolidated
education-investment series **stops at 2021**, and several Tesouro
open-data sets only start in 2017–2019. The recent past is often the gap.

**The pandemic is a hole in the data, not just in the economy.** INEP
forbade recording reprovação and abandono across much of the country in
2020–2021, so approval rates jump to 98.2%. IBGE published no PNAD-C
education module for either year. Any indicator that "improved" in 2020
should be assumed to be an artefact until shown otherwise.

**Rising coverage mechanically worsens stage-level indicators.** Pulling
the last marginal students into ensino médio adds the highest-risk
students. Brazil's PISA coverage index went 0.55 (2003) → 0.76 (2025), so
a flat PISA score over that period is a real improvement being reported as
stagnation. This cuts against the intuitive "enrolment up, quality down"
framing, and a plate that doesn't say so is misleading even while every
number on it is correct.

**The most interesting series are the ones measuring two things at once.**
Femicides measure killing *and* the spread of a legal category. Registered
homicides measure violence *and* the quality of death certification.
Dengue deaths measure an epidemic *and* an ICD migration. These are not
flaws — but a chart that shows only the line is telling half the story,
and usually the wrong half.

---

## What this repo does about it

- `data/SOURCES.yaml` carries a `notes:` field per series for exactly these
  caveats, and the sources table on the page is generated from it with the
  years read off the CSVs, so coverage claims cannot drift from the files.
- Household credit covers the SFN only. It excludes fintech lenders outside
  the system, consórcios and informal credit, so the 49.9% debt-to-income
  figure is a floor, not the whole of what households owe.
- Different instruments get different columns and are never spliced.
- `tests/test_plate_semantics.py` asserts that a label means what its
  numbers say, which is the one class of error visual QA cannot catch.
- Fetchers raise rather than default when a value is missing, after the
  `u_eop.get(base_year, 1)` bug above.

### Still open

- Fetchers do not yet fail loudly on an HTTP 200 carrying an HTML error
  body. The BCB WAF episode would currently blank whole years and exit 0.
- Nothing yet distinguishes, on the page itself, a measured series from a
  modelled or projected one. See the discussion about source badges.

Fixed while writing this: `SOURCES.yaml` had described SGS 432 as Selic
"accumulated in year". It is the Copom *target* rate at year end — a daily
series that holds flat between meetings, which is what makes it visible:
true accumulated Selic for 2005 was about 19.05% against the 18.00 the
file records.

---

## On the plate spine (2026-10-22)

Every plate now keeps to the shared spine (`PLATE_SPINE.md`,
`core/spine.py`): the same four slots, units and scales as every other
country, so the comparison viewer can wipe a Brazilian plate over a
French one. What that took, and the judgement calls in it:

### Counts became rates, and over which population

| Panel | Count | Population (same year, same scope) |
|---|---|---|
| Security: suicide, road deaths | SIM by residence (`social/deaths.csv`: X60–X84, V01–V89) | IBGE resident population, 1 July, projection rev. 2024 (`social/population.csv : pop_mn`) |
| Security lens: deaths resulting from police intervention | FBSP `police_killings` | the same IBGE population. FBSP's own MVI rate implies 213.37M for 2025 against IBGE's 213.42M, so it is the denominator FBSP uses |
| Security lens: homicides of women, femicides | FBSP `women_homicides`, `femicides` | female population, mid-year, UN WPP via the World Bank (`social/demography.csv : population_female`). IBGE's projection by sex is not staged; the WPP total runs about 0.3% under IBGE's, so these rates are, if anything, a hair high |
| Mortality: crude death rate, excess | SIM registered deaths (`social/deaths.csv : registered`) | IBGE population as above |
| Mortality: COVID-19, influenza, dengue | SIM, B34 / J09–J11 / A90+A91+A97 | IBGE population as above |
| Demography: births, deaths, natural increase | IBGE projection model (`social/population.csv`) | the same file's `pop_mn`, so numerator and denominator are one model |
| Demography: net migration | WPP count (`social/demography.csv : net_migration`) | the WPP population of the same year, same file |
| People: minimum wage in US$ | R$ a month (`macro/minimum_wage.csv`) | ÷ the year's average PTAX (`macro/dollar.csv : avg`) |

Published rates are drawn as published, never recomputed: IPEA's homicide
rates, FBSP's MVI rate.

### Registered deaths are new, and differ from the model

The old plates drew deaths from IBGE's projection model, which is a
model. `fetch_sim_causes.py` now also reads SIM's registered total, and
the mortality chapter draws that. The model corrects for
under-registration, so it runs above SIM through 2019 (2019: 1,376,835 vs
1,349,801) and below it after (2024: 1,507,335 vs 1,532,015). Both are on
the crude-death-rate panel, labelled. Excess deaths are computed from the
registered counts against their 2015–19 mean, drawn from 2015 on: before
the baseline the gap to it is population growth, not a deficit of deaths.
There is no age adjustment.

### Fiscal: the IMF line is canonical, the Brazilian lines ride beside it

General government on the IMF's basis is the spine's series. Brazil argues
in other measures: the Tesouro's central-government primary result, the
BCB's DBGG gross and DLSP net debt, and the NFSP nominal interest bill
(new, `fiscal/nfsp.csv`, consolidated public sector). The IMF's interest
is net interest, primary balance minus overall balance; the BCB's is
nominal interest on the NFSP perimeter. They agree within about a point
except 2023–24, when the BCB's runs higher. The tax burden keeps its 2010
seam: two segments, never joined.

The canonical debt slot draws only gross measures: IMF general-government
gross and the BCB's DBGG gross definition. DLSP remains documented in the
curated source but is not overlaid on the gross-debt axis.

### Spending: COFOG for the whole general government

Brazil does not report COFOG to the OECD, but the Tesouro, SOF and IBGE
compile it for the general government — federal, state and municipal —
from 2010 (`fiscal/cofog.csv`, `fetch_cofog.py`). The ten divisions map
onto the spine's seven groups with no judgement call, and their total
equals the IMF's general-government expenditure to the hundredth in 2010
and 2015, which is as good a cross-check as two publishers get. The old
plate's federal budget functions (SIAFI) were a narrower perimeter whose
"encargos especiais" mixed interest with transfers to states; they stay
committed for the chapter's R$ figures but are no longer drawn. 2006–09
are empty on the stack: COFOG starts in 2010 and is not back-cast.

The Tesouro's portal (tesourotransparente.gov.br) answered HTTP 429 for
the whole session; the files themselves came from cdn.tesouro.gov.br,
found through the Internet Archive's copy of the publication page. The
2024 edition's spreadsheet was not reachable, so 2024 is transcribed by
hand from its report's Table 1, and the fetcher checks the two editions
agree on 2023.

### A 10-year yield where none is published

No official API publishes a constant-maturity 10-year yield for Brazil,
and the OECD's "long-term interest rate" for Brazil is the TJLP, a BNDES
lending rate. `fetch_tesouro_direto.py` builds one from the Tesouro
Direto offer rates for the NTN-F nearest ten years out, day by day. It is
a retail offer rate, not ANBIMA's curve, and was not cross-checked
against ANBIMA (behind a login); its level tracks the Selic cycle as it
should (7.3% in 2020, 14.1% in 2025). 2006 and 2009 are blank: no NTN-F
on offer matured within 1.5 years of ten.

### Moved, merged or dropped

- Nominal GDP in R$ trillion: the size now sits on world slot 1 in US$,
  with the R$ level in its note.
- Unemployment moved from people to economy slot 4, with the ILO estimate
  beside PNAD-C and PME, none spliced.
- HDI moved from people to world. The WEF competitiveness rank left the
  atlas (discontinued after 2019); `international/wef.csv` stays
  committed but undrawn.
- Trade openness left the world plate: trade slot 1 now draws exports and
  imports of goods and services as a share of GDP.
- Goods trade in US$ (SECEX) survives in the trade notes; the product
  snapshot is the trade lens.
- The "R$100 invested in 2005" panel, with the S&P 500 converted into
  reais, became the spine's Ibovespa-in-US$ against the S&P 500, both
  2006 = 100; the reais-versus-dollars story is its note.
- Total credit to GDP is a note on the BIS household-debt panel; the
  BCB's debt-to-income and debt-service ratios are the credit lens.
- The minimum wage in reais, nominal and real, is the people lens; the
  canonical slot is the same wage in US$.
- The demography plate no longer runs to 2070. The projection lives in
  slot 1's note (peak 220.4M in 2041) and slot 4's (deaths overtake births
  in 2042).
- The mortality log panel is gone: everything is per 100,000 on linear
  axes, where influenza and dengue no longer need a log scale to show.
# Migration

The gross-flow slot remains pending after a focused definition gate. IBGE's
2024 projection report publishes estimated immigration and an STI-based net
balance, but naively applying its stated identity implies negative emigration
in 2020. That is a method incompatibility, not a zero and not permission to
splice in border movements. The plate therefore uses WPP net migration only,
plus same-census IBGE birthplace and citizenship stocks and the 2010/2022
Latin-America-born census comparison.
