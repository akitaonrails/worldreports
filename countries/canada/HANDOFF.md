# Canada — handoff

Updated 2026-10-22 (spine-redraw lane). The country is **on `main`** (the
five-chapter atlas landed in 8b03c87/b32de7a; the earlier "do not merge"
note in this file was stale and is withdrawn). This branch redraws the
atlas onto the plate spine: twelve chapters, the five Canadian-publisher
ones kept as they were where the spine allows, and the seven that had been
absent — economy, trade, people, demography, security, mortality, credit —
built from the harmonised publishers (World Bank, IMF, OECD, BIS,
UNODC/WHO), each panel saying so. Statistics Canada's own line rides
beside the harmonised one where it differs; the slots it will land in are
mapped below. No Statistics Canada number is typed into `plates.py`.

Read [`../../ADDING_A_COUNTRY.md`](../../ADDING_A_COUNTRY.md) and
[`../../SOURCING_A_COUNTRY.md`](../../SOURCING_A_COUNTRY.md) first. They
are not background reading; they are the specification.

---

## Statistics Canada — back up, fetch follow-up work

From 02:40Z on 2026-10-22 `www150.statcan.gc.ca` served an outage page
under **HTTP 200** for every WDS endpoint; that outage is why the seven
chapters above were built from harmonised publishers instead of waiting.

**Probed again at the start of the spine lane (2026-10-22):**

```sh
curl -s -m 20 https://www150.statcan.gc.ca/t1/wds/rest/getAllCubesListLite | head -c 60
# -> [{"productId":10100001,"cansimId":"183-0021","cubeTitleEn":"
```

The reply starts with `[` — **the platform answers again.** Still, no
StatCan fetcher exists in `fetch/` and the spine lane deliberately did
not start a fetch campaign: the redraw is finished on the harmonised
path, and the national lines below are follow-up work, one fetcher and
one PR per chapter group. Any fetcher written against StatCan must check
the payload shape before caching: the outage page arrived under HTTP 200,
and a cached error page survives the retry that would have fixed it.

### Slots that take the Statistics Canada line when it is fetched

The harmonised series stays canonical (spine rule 10); StatCan rides
beside it as the labelled national line:

| chapter.slot | national line | candidate table |
|---|---|---|
| 01 economy 1 | real GDP growth from the national accounts | 36-10-0222 |
| 01 economy 3 | national CPI beside the WB series | 18-10-0005 |
| 01 economy 4 | LFS unemployment beside the ILO estimate | 14-10-0327 |
| 04 trade 1–2 | StatCan balance reprints beside the WB | 12-10-0011 |
| 05 markets 3 | annual average FX filling the 2006–07 hole (the H.10 series covers it meanwhile) | 33-10-0163 |
| 06 people 1 | StatCan's own Gini, not the WB derivation | 11-10-0190 |
| 06 people 2 | the official Market Basket Measure line | (MBM, CANSIM) |
| 08 demography 1/3/4 | quarterly demographic estimate, vital statistics, components of growth | 17-10-0005, 17-10-0008 |
| 09 security 1 | police-reported homicide beside UNODC | 35-10-0177 |
| 10 mortality 1–3 | death registrations direct from the source | 13-10-0394 |
| 11 credit 1 | household debt-to-disposable-income beside the BIS debt-to-GDP | 36-10-0639 |
| 12 migration 1–2 | outflows / components of growth | 17-10-0008 |
| 12 migration 3 | census foreign-born share | census |
| 12 migration 4 | the non-permanent-resident **stock** — the story's missing piece | 17-10-0040 |

The candidate table PIDs are **unverified against a live API**; treat
every one as a candidate, not a fact. The full-table CSV download
(`getFullTableDownloadCSV/<pid>/en` → a zip URL) is almost certainly the
better route than the coordinate API.

---

## What is done

### The twelve chapters, on the spine

Plates (declarative PLATES shape, ids are the spine's chapter numbers):

- **01-economy, 04-trade, 06-people, 08-demography, 09-security,
  10-mortality, 11-credit**: new, built from the harmonised publishers
  (WB/IMF/OECD/BIS/UNODC/PHAC) — each panel footnotes that the Statistics
  Canada line is pending, per the map above.
- **02-fiscal** (IMF general government calendar-year canonical, the
  FRT federal fiscal-year series as the labelled national lines beside
  it): revenue/expenditure, balance + primary, gross debt with the two
  figures quoted instead, interest paid.
- **03-spending** (IMF COFOG stacked by function, social protection vs
  the rest, WB GFCF, OECD public investment; federal FRT figures as
  notes).
- **05-markets** (BoC): policy rate vs inflation; 10y yield with the 2y
  beside it; the dollar as index 2006 = 100 on the Fed H.10 base with
  the BoC noon (to 2016) and single daily (from 2017) series never
  spliced; TSX in US$ vs the S&P 500 (Yahoo, `official: false`).
- **07-world**: GDP in US$ bn (log), HDI one vintage, TI's CPI,
  reserves.
- **12-migration** (IRCC + WB): admissions and study permits per 1,000
  (flows, labelled as flows; permits keep the "flow" wording), net
  migration, foreign-born share; the 2006-14 hole stays visible.

Supporting files: `events.py`, `ui.json`, `DATA_NOTES.md`, `i18n.json`
(fr + pt for every spine unit, panel title and note), `fetch/` (BoC,
FRT, comparables, IRCC, harmonised, spine), `tests/test_plates.py`
(the fact tests — 2020-21 federal balance −14.8%, PR admissions 2024 =
480,955, the splice and back-fill and flow/stock guards, re-expressed
against the spine slots).

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

1. **The StatCan fetcher and the national lines** — the platform
   answered again (probe above); write the fetcher, shape-check before
   caching, and add the labelled national lines to the slots mapped
   above. Nothing needs renumbering.
2. **The S&P/TSX composite** is drawn (05 markets slot 4) from Yahoo
   Finance month-end closes, `official: false`, sidecar kept. If an
   official publisher ever appears (stooq was behind a JS
   proof-of-work wall), replace the feed and re-curate.
3. **Transparency International's CPI** is drawn (07 world slot 3)
   from TI's 2012-onward series, the same way France curates it; the
   earlier 0–10 scores are not in TI's time series and are not drawn.
4. **The non-permanent-resident stock** (StatCan 17-10-0040) for the
   migration chapter — the story's missing piece: most of the 2023-24
   growth never appears in the admissions file.
5. When the national lines land: refresh `i18n.json` via
   `python3 -m pytest tests/test_catalogs.py -q -k canada`, extend
   `countries/canada/tests/`, and keep `tests/test_layout.py` fault
   counts down.
6. `make C=canada charts thumbs provenance site test` before merging
   anything built on top of this branch.

## Other countries queued behind this one

United Kingdom (slug `united-kingdom`, languages en · pt), Italy,
Israel, Japan, China, Taiwan, Vietnam. See `COUNTRIES.md`.

Israel needs RTL — the user chose "build RTL support when we get there",
so `dir="rtl"`, a mirrored masthead and grid, a Hebrew font and bidi
shaping are unbuilt work, not a known-good path.

## State of `main`

`main` is green and deployed; https://worldreports.io is serving it —
Canada included, since the atlas merged in 8b03c87/b32de7a. This branch
carries the spine redraw on top.
