# Canada — handoff

Updated 2026-10-22 (second session). Branch `canada`. The country now
**builds and the full suite is green** (`make test`: 621 passed + 20/20
JS): five chapters drawn from the staged data, with the StatCan chapters
absent rather than approximated. **Do not merge to `main` yet** — the
country is a five-chapter atlas and the dek says so; merging is a product
decision, not a test result.

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md) and
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) first. They
are not background reading; they are the specification.

---

## The blocker

**Statistics Canada's data site is down.** `www150.statcan.gc.ca` has
served an outage page under **HTTP 200** for every WDS endpoint since at
least 02:40Z on 2026-10-22. Verified still down at the start of the second
session. A browser User-Agent does not change it.

**Check it before assuming it is still down:**

```sh
curl -s https://www150.statcan.gc.ca/t1/wds/rest/getAllCubesListLite | head -c 20
# JSON starting '[' => back up.  '<!--Last modified' => still down.
```

The StatCan fetcher is the critical path for chapters 01, 04, 06, 08, 09,
10 and 11. The candidate table PIDs are listed below — **none has been
verified against a live API**; treat every one as a candidate, not a fact.
Any fetcher written against StatCan must check the payload shape before
caching: the outage page arrives under HTTP 200, and a cached error page
survives the retry that would have fixed it.

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
| markets | 33-10-0163 | annual average exchange rates (fills the 2006-07 USDCAD hole) |
| trade | 12-10-0011 | merchandise trade by partner |

The full-table CSV download (`getFullTableDownloadCSV/<pid>/en` → a zip
URL) is almost certainly the better route than the coordinate API.

---

## What is done

### The five chapters the staged data carries

Plates (declarative PLATES shape, ids keep their spine numbers):

- **02-fiscal** (FRT, federal, fiscal years): revenues vs total expenses
  %GDP; budgetary balance with the actuarial split drawn only from
  2008-09; public debt charges; accumulated deficit vs net debt in C$ tn
  over the full 1966–2024 FRT run (that one panel leaves the shared
  window on purpose — the 1990s paydown is the story).
- **03-spending** (FRT): expenses by category (stacked); program expenses
  vs debt charges; revenues by source; personal income tax vs all other
  revenue.
- **05-markets** (BoC): target rate eoy + avg from the static monthly
  table; GoC 2y/10y benchmark yields; USDCAD noon vs daily, never
  spliced, 2006-07 blank; TSX panel **pending** (see below).
- **07-world**: G7 net vs gross debt together, never net alone; G7
  general-government balance; HDI one vintage; reserves.
- **12-migration** (IRCC + WB): PR admissions with the 2006-14 hole
  visible (xlim stays 2006-2026); top-10 countries of citizenship
  (stacked, ranked once); study permits as a flow, labelled as one;
  WB population with the StatCan NPR caveat.

Supporting files: `events.py`, `ui.json` (en/fr/pt, dek names the absent
StatCan chapters), `DATA_NOTES.md` (the un-banded 2015 contraction, the
three debts, the IRCC 2015 start and rounding, the fiscal-year
convention, the USDCAD break), `i18n.json` (125 entries, strict render
clean), `tests/test_plates.py` (17 fact tests — 2020-21 balance −14.8%,
PR admissions 2024 = 480,955, 2023 avg rate 4.77, G7 2024 net 12.5 /
gross 111.3, the splice and back-fill guards).

`SOURCES.yaml` now lists the curated CSVs beside their `_from_*`
sidecars, which are kept for the next diff. Every CSV in `data/` was
curated 2026-10-22: shape-checked, spot values verified against the
numbers below, blanks carried over as blanks, e-notation floats rewritten
as plain numbers in `fiscal/liabilities.csv` (values unchanged).

### Layout and palette, verified (they were design intent before)

- `core.qa`: **zero faults** for canada in all three languages — no
  baseline entry needed. Two real bugs the QA loop caught: a `max()` on
  (year, value) tuples that picks the latest year rather than the peak,
  and a phantom y-tick above the ylim overlapping the subtitle (fixed
  with explicit `set_yticks`).
- Greyscale: eyeballed `07-world` desaturated — gross/net/average
  separate cleanly.
- Web chrome: measured — ink on ground 15.6:1, family accents 6.6–8.2:1
  on the warm near-black.

### One core/ change, flagged

`core/sitebuild.py`: added a `CAD` entry to `CURRENCY_AFFIX`
(en/fr/pt forms for `money_bn`/`money`). Additive only;
`tests/test_core.py::test_the_currency_is_one_the_site_can_write`
requires every country's currency to have an entry, so no new country
with a new currency can pass without it. No other country is affected.

---

## The traps already found, and what they cost

Unchanged from the first session and now mostly enforced by tests and
CSV comments: the retired noon rate (two series, part-years blank),
`V39079` starting April 2009 (use the static monthly table), the three
Canadian debts (never draw net alone), the April–March fiscal year
(`fiscal_year` = starting year; USA's files use the same key), the
actuarial split existing only from 2008-09 (never back-filled — a test
fails if it is), IRCC's round-to-five and 2015 start, and StatCan's
HTTP-200 outage page.

Spot values, for checking that a rerun has not silently changed shape:

- policy rate 2026 = 2.25, 2023 avg = 4.77, 2020 eoy = 0.25
- federal budgetary balance 2020-21 = **−14.8% of GDP**, program expenses
  27.4% — the largest single-year federal spending in Canadian peacetime
- G7 general government 2024: Canada net debt **12.5%**, gross **111.3%**
- PR admissions: 2020 = 183,075 · 2024 = 480,955 · 2025 = 390,625
- HDI 2023 = 0.939 · GDP per person 2025 = US$55,698 · reserves US$125.6bn

---

## What is left

1. **The StatCan fetcher and the seven missing chapters** — the table
   PIDs above, once the platform returns. They slot into spine numbers
   01, 04, 06, 08, 09, 10, 11 without renumbering anything.
2. **The S&P/TSX composite** (05 panel pending). Nobody official
   publishes it. stooq (`stooq.com/q/d/l/?s=^tsx&i=d`) was behind a
   JavaScript proof-of-work wall when tried — a headless browser could
   pass it, or another redistributor; mark `official: false`.
3. **Transparency International's CPI.** France curates it by hand with
   the 2012 break in the CSV and no `official: false` flag. Canada could
   do the same; it was left out rather than compiled from memory.
4. **The non-permanent-resident stock** (StatCan 17-10-0040) for the
   migration chapter — the story's missing piece: most of the 2023-24
   growth never appears in the admissions file.
5. When chapters are added: refresh `i18n.json` via
   `python3 -m pytest tests/test_catalogs.py -q -k canada`, extend
   `countries/canada/tests/`, and re-check `core.qa` faults stay at zero.
6. Then `make C=canada charts thumbs provenance && make site test` and
   merge is a conversation, not a default — see the note at the top.

## Other countries queued behind this one

Spain, United Kingdom (slug `united-kingdom`, languages en · pt), Italy,
Israel, Japan, China, Taiwan, Vietnam. See `COUNTRIES.md`.

Israel needs RTL — the user chose "build RTL support when we get there",
so `dir="rtl"`, a mirrored masthead and grid, a Hebrew font and bidi
shaping are unbuilt work, not a known-good path.

## State of `main`

`main` is green and deployed; https://worldreports.io is serving it.
Canada lives only on this branch.
