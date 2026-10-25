# The queue

Which countries are in, which are coming, and what each one needs that the
last one did not. Method: [SOURCING_A_COUNTRY.md](SOURCING_A_COUNTRY.md),
then [ADDING_A_COUNTRY.md](ADDING_A_COUNTRY.md).

The work runs in three horizontal phases, not country-by-country verticals
(decided 2026-10-22, after Canada's StatCan outage proved that a country
stuck on one source idles the whole pipeline):

1. **Data for all** — research pass, `SOURCES.yaml`, fetchers and staged
   CSVs, in per-country worktree lanes, three at a time. A source that is
   down or walled goes on the country's pending list and the lane moves on.
2. **Plates for all** — `plates.py`, i18n catalogs, events, fact tests.
   Sequential: the layout baseline and the string catalogs are shared.
3. **Site for all** — `chapters.py`, `ui.json`, `make site`, merge, deploy.
   A country merges to main only when all three phases are green for it.

Every country publishes in **its own official language, plus English and
Portuguese**, and every plate is drawn in each of them.

## Published

| Slug | Languages | Plates | Datasets |
|------|-----------|--------|----------|
| `argentina` | es · en · pt | 12 | 39 |
| `brasil` | pt · en | 11 | 45 |
| `canada` | en · fr · pt | 12 | 53 |
| `china` | zh-Hans · en · pt | 12 | 24 |
| `france` | fr · en · pt | 12 | 46 |
| `israel` | he · en · pt | 8 | 17 |
| `italy` | it · en · pt | 12 | 37 |
| `japan` | ja · en · pt | 12 | 31 |
| `portugal` | pt · en | 12 | 37 |
| `spain` | es · en · pt | 12 | 46 |
| `south-korea` | ko · en · pt | 11 | 43 |
| `switzerland` | de · en · pt | 12 | 46 |
| `taiwan` | zh-Hant · en · pt | 10 | 18 |
| `ukraine` | uk · en · pt | 11 | 19 |
| `united-kingdom` | en · pt | 12 | 45 |
| `usa` | en · pt | 11 | 43 |
| `vietnam` | vi · en · pt | 12 | 36 |

The inventory started from the 2026-10-22 spine vintage and records
subsequent verified additions. Plates count published chapters; datasets
count curated CSVs declared in SOURCES.yaml, including source-only
national datasets where documented. Review sidecars and independent
cross-check files are not counted.

## Queued

The 2026-10-25 batch, eight countries in queue order. Phase A (data) runs in
parallel lanes; Phase B (plates) starts only when a country's data gates
green; merges stay sequential in this order.

| # | Country | Slug | Languages | What it needs that we do not have |
|---|---------|------|-----------|------------------------------------|
| 1 | Poland | `poland` | pl · en · pt | A Polish number style and page chrome; GUS/BDL national layer. |
| 2 | Australia | `australia` | en · pt | ABS SDMX; quarterly national accounts to annualise on a documented rule. |
| 3 | Chile | `chile` | es · en · pt | Banco Central de Chile API (may need a token); CLP forms. |
| 4 | Singapore | `singapore` | en · pt | SingStat Table Builder API; SGD forms; a city-state, so population and land are not the usual denominators. |
| 5 | Hong Kong | `hongkong` | zh-Hant · en · pt | C&SD API; HKD forms; "country" framing needs care (a SAR, compared as an economy). |
| 6 | Paraguay | `paraguay` | es · en · pt | INE/BCP; PYG forms; a large informal economy and a binational hydro story. |
| 7 | Russia | `russia` | ru · en · pt | A Russian number style and chrome; Rosstat/EMISS access is likely blocked, so the harmonised layer plus documented blocks. |
| 8 | Venezuela | `venezuela` | es · en · pt | INE/BCV publication has largely stopped; hyperinflation and migration; expect the harmonised layer and explicit gaps. |

None. The eight-country queue opened on 2026-10-22 is complete, and
Ukraine — proposed in issue #1 and discovered 2026-10-24 — is published
with eleven chapters: economy, public finances, spending, trade, markets,
people, world, demography, security, mortality and migration. The obvious
national publishers block automated access, so the fiscal chapter is the
IMF's general-government layer, spending and markets come from the NBU's
own API (Treasury execution and the key rate), and security/mortality from
UNODC, WHO and the World Bank. Only credit is not published: its routes
were tried and the official split is not internally consistent before
2016, which SOURCES.yaml records in full.
Its catalogue is the atlas's first Ukrainian one, and the shared number
style, site chrome and comparison names were extended for it.

## Known problems, written down before they are hit

**Israel is right-to-left.** The shared page layer now declares RTL direction,
and the figure layer applies bidi ordering with a font that covers Hebrew and
the Latin/numeric fragments in data labels. Exact layout QA is zero in Hebrew,
English and Portuguese. This also establishes the path for a later Arabic
edition.

**China's problem is not the language.** The National Bureau of Statistics
publishes a full set of numbers; the question a reader will have is
whether to believe them. The atlas does not answer that question by
leaving China out or by substituting a Western estimate for an official
one. It publishes what the NBS publishes, marked as such, beside the
international series — World Bank, IMF, UN Comtrade — where those exist,
and says in the notes where the two disagree and by how much. Quarterly NBS
evidence remains unavailable, so the recession-band decision is explicitly
pending rather than inferred from positive annual growth.

**Taiwan is missing from the international layer.** The World Bank, the
IMF and the UN do not carry it, so the comparables that make every other
country legible are mostly unavailable. DGBAS and the central bank publish
well and in depth; the `World` chapter is built from what Taiwan publishes
about itself plus the bodies that do carry it (the WTO and its own customs
administration). Unsupported comparison slots remain visibly pending.

**Fiscal years that are not calendar years.** Japan's starts in April,
as do the United Kingdom's and India's should it ever be queued. The USA
already has this — its debt table keys on `fiscal_year`. Japan's fiscal
observations are labelled by starting year and plotted at the October midpoint
(`year + 0.75`), pinned by semantic tests.

**Number styles.** `AFFIX` and `CURRENCY_AFFIX` in `core/sitebuild.py`
and the unit rules in `core/i18n.py` are keyed by *number style*
(`core/numstyle.py`), and every Phase B style — de, it, pt-PT, ja,
zh-Hans, zh-Hant, vi, he — and currency — GBP, CHF, JPY, VND, CNY, TWD,
ILS — already has its forms. `tests/test_numbers.py` reads every lane's
country.yaml and fails on a locale or currency with no form, which is the
intended behaviour. Portugal must declare `number_style: {pt: pt-PT}`.
Hebrew now has numbers, affixes, bidi figure text and right-to-left page
layout; the exact-layout gate covers all three Israel locales.

## The migration chapter

A twelfth chapter, added to the spine for the European countries at the
point they were queued, and available to any country whose publishers
measure it. Eurostat carries eleven harmonised migration tables covering
every EU member — immigration and emigration, the resident stock on both
the citizenship and the country-of-birth definition, asylum applications
and first-instance decisions, first and valid residence permits,
acquisitions of citizenship — all verified live against the dissemination
API before being written down here.

That makes Spain, Italy, Portugal and France straightforward and the United Kingdom
hard, because its Eurostat rows stop in 2019 and the ONS has changed
method twice since. Switzerland sits between the two: EFTA membership puts
it in many of the same tables, but coverage has to be verified dataset by
dataset rather than assumed. Hard is not a reason to leave it out; it is a reason
to draw the three regimes as three segments and say so on the panel.

**This chapter needs more care than any other in the atlas**, and the
reason is not the data. It is that almost every number in it is routinely
quoted as a different number: applications as arrivals, permits as people,
detections as crossings, a foreign-citizen stock as a foreign-born one.
`SOURCING_A_COUNTRY.md` §4a lists each confusion and which pair of series
separates it. The rule is the same as everywhere else here — publish what
the body that counts it published, on the definition it counted, next to
the series that measures the adjacent thing — and the discipline has to be
tighter because the subject invites the opposite.

France is already published without this chapter and is the obvious
candidate to get it first, since its Eurostat coverage is complete and its
interior ministry publishes permits and asylum decisions in depth.
