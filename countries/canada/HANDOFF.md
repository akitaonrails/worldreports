# Canada — handoff

Written 2026-10-22. Branch `canada`, off `main` at `e0903e0`. Nothing here
is on `main` and nothing here should be merged until the country builds:
a half-built country **fails the shared suite**, because every test that
takes a `country` argument discovers Canada from `country.yaml` the
moment it exists.

```
$ python3 -m pytest tests/ -q
FAILED tests/test_catalogs.py::test_the_catalog_parses_and_is_not_empty[canada]
  FileNotFoundError: countries/canada/i18n.json
```

That is expected and is the correct signal. It will keep failing until
`plates.py`, `chapters.py`, `i18n.json` and `ui.json` exist. Work on this
branch, run `python3 -m pytest tests/ -q -k "not canada"` while the
country is incomplete, and only merge when the full suite is green.

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md) and
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) first. They
are not background reading; they are the specification, and everything
below assumes them.

---

## The blocker

**Statistics Canada's data site is down.** `www150.statcan.gc.ca` has
served an outage page under **HTTP 200** for every WDS endpoint since at
least 02:40Z on 2026-10-22, including:

```
/t1/wds/rest/getAllCubesListLite
/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods
/t1/wds/rest/getFullTableDownloadCSV/<pid>/en
/t1/tbl1/en/tv.action?pid=...
```

Every one returns 92,815 bytes of `text/html` titled *"We're sorry! The
website is currently unavailable"*. A browser User-Agent does not change
it. `www.statcan.gc.ca` itself answers 302, so it is the data platform
rather than DNS.

**Check it before assuming it is still down:**

```sh
curl -s https://www150.statcan.gc.ca/t1/wds/rest/getAllCubesListLite | head -c 20
# JSON starting '[' => back up.  '<!--Last modified' => still down.
```

This matters because StatCan is the publisher for **eight of the twelve
chapters**. It is why this handoff exists rather than a finished country.

There was a background poller waiting on it; it does not survive the
session, so re-establish one or check by hand.

---

## What is done

### `country.yaml` — complete and loading

```sh
python3 -c "from core.country import Country; c=Country.load('canada'); print(c.slug, [l.code for l in c.locales])"
# canada ['en', 'fr', 'pt']
```

Locales **en · fr · pt**, default `en`. Window 2006–2026, `last_full_year`
2025, `tick_every` 2. Two bands: 2008–09 and COVID. The 2015 oil
contraction is deliberately *not* banded — it met the two-quarter rule,
employment never fell, and the Bank of Canada declined to call it a
recession, so it belongs on a plate as an event and not across all of
them. That decision needs restating in `DATA_NOTES.md`.

Palette: flag red darkened off `#D80621` to `#B5272F`, cool siblings
chosen to stay apart from it in greyscale. Web chrome is a warm
near-black rather than a dark red, because the three family accents have
to stay apart from each other and from the page, and a red accent on a
red ground is the one pair that cannot.

**Unverified:** the palette has never been rendered. Nothing has drawn a
plate yet, so the greyscale claim and the web-chrome contrast are design
intent, not measurement. Check them the first time `make C=canada charts`
runs.

### Four fetchers, written, run, and holding real data

All four follow the house rules: they live in `countries/canada/fetch/`,
compute `ROOT` from `__file__`, write only `_from_*` sidecars, and are
never run by the build.

| Fetcher | Source | Writes |
|---|---|---|
| `fetch_bankofcanada.py` | Valet | `markets/rates_from_boc.csv`, `markets/usdcad_from_boc.csv` |
| `fetch_frt.py` | Fiscal Reference Tables Nov 2025 (xlsx) | 4 × `fiscal/`, 3 × `international/g7_*` |
| `fetch_comparables.py` | World Bank, UNDP | 5 × `international/`, `social/gini_from_wb.csv` |
| `fetch_ircc.py` | IRCC open data | 3 × `migration/` |

`fetch_frt.py` needs `openpyxl` (`requirements-fetch.txt`). Run any of
them with `python3 -I` — the cache directory holds downloaded files and
`-I` keeps the interpreter from importing out of it.

Spot values, for checking that a rerun has not silently changed shape:

- policy rate 2026 = 2.25, 2023 avg = 4.77, 2020 eoy = 0.25
- federal budgetary balance 2020-21 = **−14.8% of GDP**, program expenses
  27.4% — the largest single-year federal spending in Canadian peacetime
- G7 general government 2024: Canada net debt **12.5%**, gross **111.3%**
- PR admissions: 2020 = 183,075 · 2024 = 480,955 · 2025 = 390,625
- HDI 2023 = 0.939 · GDP per person 2025 = US$55,698 · reserves US$125.6bn

### `SOURCES.yaml` — written before the CSVs, as the doc requires

19 entries. It describes the sidecars and the curated files they are to
become. Every `official: false` is set deliberately — the World
Bank/UNDP layer is comparables, never a substitute for a national
number.

---

## The traps already found, and what they cost

These are in `SOURCES.yaml` too. They are repeated here because each one
produced a plausible wrong number that nothing downstream would have
caught.

**The Bank of Canada retired the USD noon rate on 2017-03-01.**
`IEXE0101` runs May 2007 → April 2017; `FXUSDCAD` runs 2017-01 →. A
naive annual mean therefore hands you an **eight-month** average for 2007
and a **four-month** average for 2017, both landing inside the plausible
range for the Canadian dollar. The fetcher now blanks any non-running
year with fewer than 12 months covered and writes a `*_months` column
beside each average. **2006 and 2007 are still empty** and need StatCan
table **33-10-0163** (annual average exchange rates).

**`V39079` does not go back far enough.** Valet carries the business-daily
target rate only from April 2009 — the middle of the post-2008 easing. A
plate drawn from it opens at 0.25% with no fall in front of it. Use
`STATIC_ATABLE_V39079`, the monthly table, which runs from 1998.

**Three different Canadian debts.** Federal accumulated deficit (~42% of
GDP), general-government *net* debt (12.5%), general-government *gross*
debt (111.3%). All three are correct, all three answer different
questions, and all three get quoted as "Canada's debt". The net figure is
low because it nets off CPP/QPP assets that most G7 members do not hold
in that form — so **draw net and gross together, never net alone.**

**The federal fiscal year is April–March.** `fiscal_year` holds the
*starting* year: 2024 means 2024-04-01 → 2025-03-31. Never plot it
against a calendar series without saying so. The USA country has the same
problem and solved it with a `fiscal_year` key — follow that.

**The actuarial split does not exist before 2008-09.** Net actuarial
losses became a separate expense line in 2019-20 with only 2008-09 onward
reclassified, and the discount-rate methodology changed in 2017-18 with
2008-09 onward restated. Those columns are empty for 2005–2007 and that
is correct. **Do not back-fill them from the undivided balance.**

**IRCC rounds every cell to a multiple of five.** All 19,503 of them, no
exceptions; IRCC labels the files "not for calculations". Nationally it
is nothing — 2024 sums to 482,960 against a published 483,390, 0.02%
apart — but a country of citizenship with two admissions is published as
zero or five. Composition panels must stay far above that floor. The
files are **tab-separated despite the `.csv` extension** and **begin in
2015**, so 2006–2014 is not in them.

**Statistics Canada serves its outage page under HTTP 200.** Any fetcher
written against it must check the payload shape before caching, or it
will cache an error page that survives the retry that would have fixed
it. `fetch_bankofcanada.py` and `fetch_comparables.py` already do this;
`fetch_frt.py` checks the xlsx magic number.

---

## What is left

### 1. The StatCan fetcher — the critical path

Nothing else can proceed far without it. Eight chapters depend on it.
Tables identified but **not yet verified against a live API** (the site
went down before any could be opened — treat every PID below as a
candidate, not a fact):

| Chapter | Table | What for |
|---|---|---|
| economy | 36-10-0222 | GDP, expenditure-based, annual |
| economy | 18-10-0005 | CPI, annual average |
| people | 14-10-0327 | labour force survey, unemployment |
| people | 11-10-0190 | income, after-tax, by decile |
| demography | 17-10-0005 | population by age |
| demography | 17-10-0008 | components of population growth |
| migration | 17-10-0040 | quarterly estimates, **non-permanent residents** |
| mortality | 13-10-0394 | leading causes of death |
| security | 35-10-0177 | homicide survey |
| credit | 36-10-0639 | household debt to disposable income |
| markets | 33-10-0163 | annual average exchange rates |
| trade | 12-10-0011 | merchandise trade by partner |

The WDS pattern that was being probed when the site went down:

```
POST /t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods
  [{"productId": 36100222, "coordinate": [...], "latestN": 30}]
GET  /t1/wds/rest/getFullTableDownloadCSV/<pid>/en   -> a zip URL
```

The full-table CSV download is almost certainly the better route: the
coordinate API needs the member positions of every dimension, which is a
second call per table and easy to get wrong silently.

### 2. The chapters

The spine says twelve. Canada's shape argues for **eleven plus
migration**, because the migration story is not a side chapter here: the
population grew about 3% in 2023, unmatched in the G7 and unmatched in
Canada since 1957, and most of it was non-permanent residents — students
and temporary workers who do not appear in the permanent-resident file at
all. The policy reversal that followed shows in the IRCC data already
pulled (481k admissions in 2024 → 391k in 2025).

Pick a `topic` per chapter from the spine, one each, no repeats — the
comparison control matches on it and `tests/test_site.py` enforces both
rules.

### 3. Still missing entirely

- `plates.py`, `chapters.py`, `i18n.json`, `ui.json`, `events.py`
- `DATA_NOTES.md` — and it owes an explanation of the un-banded 2015
  contraction, of the three debts, and of the 2015 start of the IRCC
  files
- `tests/` — the facts Canada's own plates assert
- Curated CSVs. **Everything in `data/` is a sidecar.** Nothing has been
  curated, nothing has been diffed, and no plate may draw from a
  `_from_*` file — `tests/test_sources.py` fails if one does.
- The S&P/TSX composite for the markets chapter. There is no official
  publisher; take it from a redistributor and set `official: false`.
- Transparency International's CPI for the world chapter. No stable
  machine endpoint, and the 2012 methodology break means pre-2012 scores
  are not on the same scale — curate by hand with the break in the CSV.

### 4. Then

```sh
make C=canada charts thumbs provenance
make site
make test          # must be fully green, including the catalogs
```

Commit the CSVs, the plates, the thumbs and `provenance.json` together.

---

## Other countries queued behind this one

Spain, United Kingdom (the user chose "United Kingdom" over "England":
there is no English GDP, deficit, debt, trade balance or policy rate;
slug `united-kingdom`, languages en · pt), Italy, Israel, Japan, China,
Taiwan, Vietnam. See `COUNTRIES.md`.

Israel needs RTL — the user chose "build RTL support when we get there",
so `dir="rtl"`, a mirrored masthead and grid, a Hebrew font and bidi
shaping are unbuilt work, not a known-good path.

## State of `main`

`main` is green and deployed. The last change moved the plate comparison
out of the card grid and into the fullscreen viewer, where the plates are
large enough for the seam to mean anything; CI passed and
https://worldreports.io is serving it. 528 tests pass there.
