# Notes on Korean official statistics

Written while building this atlas, as a record of what the official sources
are actually like to work with. `SOURCES.yaml` says where every number came
from; this file says what it was like to get it, what nearly went wrong, and
what a reader should distrust.

It is opinionated on purpose. Where I think a published number is easy to
misuse, I say so.

---

## 1. The short version

South Korea publishes a *lot*, it publishes it early, and most of it is
free. Three things make it harder than it looks:

1. **The portals are built for people, not programs.** The one open API that
   needs no registration (the Bank of Korea's) is excellent. Everything else
   is either key-gated, AJAX-rendered, or capped at a window too short for a
   twenty-year series.
2. **Almost every important series exists twice.** Public debt, the fiscal
   balance, the Gini coefficient, elderly poverty, road deaths, COVID deaths,
   semiconductor exports — each has two official numbers, computed by two
   agencies or on two bases, both correct, both quoted interchangeably in the
   press. Picking the wrong one is the main way to be confidently wrong about
   Korea.
3. **The 2025 reorganisation moved things.** 통계청 / Statistics Korea became
   국가데이터처 / the Ministry of Data and Statistics and moved from
   `kostat.go.kr` to `mods.go.kr`. Older releases still carry the old name;
   both appear in `data/SOURCES.yaml`, each attributed to whichever is
   accurate for the document actually used.

If you only remember one thing: **never splice two official series into one
line.** This repository keeps them in separate columns and draws them as
separate lines, every time.

---

## 2. The sources, ranked by how usable they are

### Bank of Korea ECOS — the best thing here

`https://ecos.bok.or.kr/api/` · machine-readable JSON, 844 statistic tables.

Nominally key-gated, but the literal key `sample` works on every endpoint.
It is capped at 10 rows per request, which paging makes irrelevant: a
250-month series is 25 requests. Everything in `data/macro/`,
`data/fiscal/government.csv`, `data/fiscal/spending_by_function.csv`,
`data/trade/` and `data/macro/external.csv` comes from here.

What makes it good:

- **Depth.** Annual national accounts to 1953, CPI to 1965, customs trade by
  partner country to 1965, COFOG government spending 1970–2024, the official
  population projection to 2072.
- **Breadth by proxy.** ECOS republishes Korea Customs Service trade and
  Statistics Korea population, so one almost-keyless API covers three
  agencies with consistent period coding.
- **Honest period codes.** Annual, quarterly and monthly cuts of the same
  table are distinguishable, which matters more than it sounds (see §4).

What to watch:

- Error messages are Korean-only, and **a wrong item code returns INFO-200
  "no data" rather than an error** — a typo looks exactly like a series that
  does not exist.
- `list_total_count` sometimes disagrees with the rows actually served, so
  paged reads can duplicate at the seams. `fetch/fetch_bok.py` keys rows by
  period rather than appending them, which makes a duplicate harmless.
- **There is no search endpoint.** Finding a table means paging the whole
  catalogue (85 requests) and grepping it locally. Worth doing once and
  keeping.
- The annual row for a year in progress is the **cumulative total of the
  months published so far**, not a projection. 2026 exports read 814.72bn
  because that is January–September. Verified by summing the monthly series;
  the atlas draws it and labels it partial.

### e-나라지표 / index.go.kr — the right numbers behind the wrong door

The government's own indicator portal, and the only free source I found with
annual, multi-cause mortality, poverty, workplace-accident and vital
statistics in one place.

It has an undocumented keyless JSON endpoint
(`POST /unity/index/IndexTblGraphAjax.do`, `sttsCd` + `chartOrd`), but that
endpoint is **hard-capped at the most recent 12 years** and ignores
`sDate`/`eDate`. The HTML table endpoint (`showStblGams3.do`) with
`freq=Y&period=FROM:TO` returns the full run, so this repository parses HTML.
That is fragile and I would rather not, but it is the difference between a
twenty-year series and a twelve-year one.

Other friction:

- `sttsCd` codes are **not discoverable**: there is no working search, and the
  indicator index pages render empty without a session. Every code in
  `fetch/fetch_index_kr.py` was found by hand and is commented with the
  portal's own label so the next person does not have to repeat it.
- The "Excel download" re-posts the HTML table already on the page. It adds
  nothing.
- Its tables come in **two layouts** — years across the header, or years down
  the first column — and which one you get is a property of the indicator,
  not a parameter. Both are handled.

### Statistics Korea / MODS press releases (PDF) — authoritative, not serial

The Causes of Death, Birth and Death Statistics and Household Finance and
Welfare releases are detailed, careful and explicit about their own
limitations. `pdftotext -layout` parses them cleanly.

The catch: **the long-run appendix tables are biennial** (2014, 2016, 2018,
2020, 2022, 2023, 2024). A PDF gives you a shape, not an annual series. Where
a PDF was the only source, the missing years are left empty rather than
interpolated.

The Causes of Death release deserves credit for carrying an explicit warning
that its COVID-19 death count differs from the KDCA's because the counting
basis differs. That is exactly the disclosure most statistical agencies omit.

### KOSIS — closed, for this purpose

`kosis.kr` is the national statistics portal and the obvious place to start.
Its OpenAPI **requires a registered key** with no public sample equivalent to
ECOS's, and its `statHtml` pages load their tables by AJAX, so a plain fetch
returns page furniture and no numbers. One abandoned series — annual
influenza deaths, a 104-item table — is missing from this atlas because of
that, and for no other reason.

### International sources, used only for comparison

World Bank (openness, R&D), UNDP (HDI), Transparency International (CPI),
UN Comtrade (exports by HS heading), Yahoo Finance (KOSPI, S&P 500 closes).
All keyless, all fine. Comtrade's public preview endpoint returns HTTP 429
freely; the fetcher retries with escalating backoff and caches per year.

---

## 3. The series that exist twice

This is the heart of it. Every one of these is a case where two official
numbers describe the same idea and differ by enough to change a conclusion.

| Idea | Number A | Number B | Gap |
| --- | --- | --- | --- |
| Public debt | D1 국가채무, central + local | D2 일반정부부채, general government | ~4 pp of GDP |
| Fiscal balance | 관리재정수지, Korea's headline | SNA net lending, ECOS | 1–2 pp of GDP |
| Income inequality | 가계금융복지조사 (2011–) | 가계동향조사 (discontinued) | ~0.05 Gini |
| Elderly poverty | 65 and over (index.go.kr) | 66 and over (MODS headline, OECD) | ~2 pp |
| Elderly poverty | disposable income 35.9% (2024) | market income 54.9% (2024) | 19 pp |
| Road deaths | police, within 30 days: 4.9/100k | 운수사고 cause of death: 6.5/100k | 1.6/100k |
| COVID deaths | death certificates (MODS) | KDCA surveillance | varies by year |
| Semiconductor exports | MTI national scheme: 173.4bn | HS 8542: 142.8bn | 30bn |
| Workplace deaths | fatal accident *rate*, halved | *count* of deaths, flat | opposite signs |

Four of these are worth spelling out.

**D1 against D2.** Two different universes, both official, both called
"national debt" in English coverage. D2 adds non-profit institutions
controlled by government. Plate 02 draws D2 as the outer band with D1 filled
*inside* it, so the containment is visible rather than asserted in a label.

**Elderly poverty on two age bases.** index.go.kr publishes 65+; the MODS
headline release and the OECD comparison use 66+ (the retirement-age base).
They differ by about two points and get quoted interchangeably. This atlas
uses 65+ throughout and says so on the plate.

**The workplace rate and count.** The fatal-accident rate per 10,000 workers
fell from 0.96 to 0.38 between 2006 and 2025 while the number of deaths went
from 2,238 to 2,248. Both are correct: the workforce grew, and the deaths now
counted include categories added to the definition. A chart showing only the
rate tells a story of dramatic improvement; only the count, of none at all.
Plate 09 draws both, which is the only honest option.

**COVID deaths.** Worse than a basis difference. The 2024 Causes of Death
release's trend table prints **0** for 2020, while the 2020 release itself
published **950**. Same agency, same series, two documents. This repository
follows the per-year releases (950 / 5,030 / 31,280 / 7,442 / 3,208 / 1,096
for 2020–2025), documents the contradiction in `data/SOURCES.yaml`, and has a
test named after it so nobody "fixes" the file back to the trend table.

---

## 4. Breaks, traps and things that cost me time

**The GDP base year changed from 2015 to 2020.** This re-levels every "% of
GDP" ratio in the national accounts. Debt and spending ratios published
before and after the rebasing are not comparable, and plenty of secondary
sources mix them.

**Minimum wage was not a calendar-year figure until 2007.** The 2006 figure
covers 2005-09-01 to 2006-12-31 — a sixteen-month transitional period. Drawn
as an annual point without a note, it is simply wrong.

**Influenza is not in the headline cause-of-death release.** Korea publishes
*pneumonia* (9.4 per 100k in 2006, 60.8 in 2025 — one of the largest moves of
any cause in the window, mostly ageing). Influenza deaths exist in KOSIS's
detailed tables, which need a key. Plate 09 draws pneumonia and says that is
what it is drawing.

**A grouped table repeats its label.** index.go.kr prints a group heading
only on the group's first row, so the same label — 처분가능소득 — appears once
per survey and the rows are told apart *only by which heading they follow*.
Matching on the label alone returned the discontinued survey's 42.8% instead
of the current 35.9%: both plausible, seven points apart, no error anywhere.
`as_series(..., after="가계금융복지조사")` exists for this, and silence is its
answer if the heading changes, because falling back to the other survey would
be worse than failing.

**A row inherits the cell above it.** In the wide layout the portal drops the
label cell when a row repeats the previous row's label, so data rows must be
aligned to the years **from the right**. Aligned from the left, every value
lands one year early.

**A label row parses as data.** A non-numeric cell has to become an empty
value, not a zero and not a string. Without that guard a farmland series once
arrived in the public-debt file, plausible-looking and completely wrong.

**Transparency International changed their own header capitalisation.**
`"CPI Score"` in the 2012–2013 columns, `"CPI score"` from 2014. Exact
matching silently dropped the two oldest years — the series just started
later than it should have, with nothing to suggest a bug.

**Provisional against confirmed vital statistics.** The February release is
provisional (2025: 254,457 births / 363,389 deaths); the confirmed
registration basis gives 254,341 / 362,968. Mixing them produced a file whose
natural-change column disagreed with its own two inputs by one. The fetcher
now owns the whole file from one indicator on one basis, and natural change
is computed rather than read so it cannot disagree.

**A third-party index level.** A secondary table gave KOSPI's 2020 close as
2,486; the actual year-end close was 2,873.47. Transcribed market levels are
not worth the risk — the atlas pulls them from an exchange history endpoint.

**Korea's export classification is national.** Exports by product are
published under MTI, which is not comparable with anything outside Korea, and
ECOS only carries a coarse four-way split. Plate 04 is built on HS headings
from Comtrade instead, which is why its semiconductor figure (142.8bn for
2025) is lower than the 173.4bn in Korean press coverage. Both are real; they
count different things.

---

## 5. Availability, by subject

**Very good.** National accounts, prices, money and credit, exchange rates,
trade by partner and by HS heading, reserves, the international investment
position, government revenue/expenditure/COFOG spending, population and the
official projection to 2072, births, deaths, fertility, life expectancy,
causes of death by rate, road deaths, workplace accidents, household credit.

**Adequate, with caveats.** Inequality and poverty (survey break in 2011, two
age bases, biennial long-run tables in the PDFs). Public debt (two
definitions, one rebasing). Homicide (the police series is clean; the
cause-of-death series is a different count).

**Hard to get freely.** Anything that lives only in KOSIS's detailed tables —
influenza deaths among them. Regional breakdowns below the province level.
Anything needing a microdata request.

**Published faster than I expected.** Causes of death for 2025 and confirmed
vital statistics for 2025 were both available while building this, as were
nine months of 2026 trade. Korea is quicker to publish than most countries
whose statistics I have worked with.

---

## 6. What I would tell the next person

- **Start at ECOS.** Page the catalogue once, keep it, grep it locally.
- **Read the release, not just the table.** The caveat that matters is almost
  always in the PDF's notes and almost never in the API.
- **Expect two of everything,** and write down which one you chose and why.
  `data/SOURCES.yaml` exists for that; its `caveats` field was most of the
  work in this repository and all of its value.
- **Make the fetchers idempotent and the data committed.** Re-running a
  fetcher once overwrote five curated years of the poverty file, because the
  indicator it used stops at 2019. Fetchers here write sidecar files where
  curation is involved, and the tests assert the landmarks the plates claim —
  the 2014 net-creditor crossing, the 2020 demographic crossing, the
  workplace rate/count divergence — so a fetch that invalidates a panel's
  heading fails the build instead of quietly changing what the atlas says.
- **Don't trust a round number you did not source.** Every figure I checked
  against a secondary table that disagreed with an official one, the official
  one was right.
