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
| `argentina` | es · en · pt | 13 | 41 |
| `australia` | en · pt | 12 | 27 |
| `brasil` | pt · en | 12 | 47 |
| `canada` | en · fr · pt | 12 | 53 |
| `chile` | es · en · pt | 12 | 17 |
| `china` | zh-Hans · en · pt | 12 | 27 |
| `france` | fr · en · pt | 12 | 46 |
| `hongkong` | zh-Hant · en · pt | 12 | 32 |
| `israel` | he · en · pt | 12 | 32 |
| `italy` | it · en · pt | 12 | 49 |
| `japan` | ja · en · pt | 12 | 47 |
| `paraguay` | es · en · pt | 12 | 16 |
| `poland` | pl · en · pt | 12 | 14 |
| `portugal` | pt · en | 12 | 52 |
| `russia` | ru · en · pt | 12 | 30 |
| `singapore` | en · pt | 12 | 16 |
| `south-korea` | ko · en · pt | 12 | 45 |
| `spain` | es · en · pt | 12 | 46 |
| `switzerland` | de · en · pt | 12 | 67 |
| `taiwan` | zh-Hant · en · pt | 12 | 28 |
| `ukraine` | uk · en · pt | 11 | 19 |
| `united-kingdom` | en · pt | 12 | 45 |
| `usa` | en · pt | 12 | 44 |
| `venezuela` | es · en · pt | 11 | 15 |
| `vietnam` | vi · en · pt | 12 | 46 |

The inventory started from the 2026-10-22 spine vintage and records
subsequent verified additions. Plates count published chapters; datasets
count curated CSVs declared in SOURCES.yaml, including source-only
national datasets where documented. Review sidecars and independent
cross-check files are not counted.

## Queued

The 2026-10-25 batch is complete and published: Poland, Australia, Chile,
Singapore, Hong Kong, Paraguay, Russia and Venezuela. Phase A (data) ran in
parallel lanes with every official route probed and recorded; Phase B built
each country in its own lane; the merges ran in queue order with one final
regeneration of all twenty-five countries.

The earlier eight-country queue (2026-10-22) is also complete. Ukraine —
proposed in issue #1 and discovered 2026-10-24 — is published with eleven
chapters: economy, public finances, spending, trade, markets,
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

**Fiscal years that are not calendar years.** Japan's starts in April;
so do the United Kingdom's, Australia's (July), and Singapore's and Hong
Kong's (April). The USA
already has this — its debt table keys on `fiscal_year`. Japan's fiscal
observations are labelled by starting year and plotted at the October midpoint
(`year + 0.75`), pinned by semantic tests.

**Number styles.** `AFFIX` and `CURRENCY_AFFIX` in `core/sitebuild.py`
and the unit rules in `core/i18n.py` are keyed by *number style*
(`core/numstyle.py`). Every style the atlas publishes has its forms —
de, it, pt-PT, ja, zh-Hans, zh-Hant, vi, he, uk, pl, ru — and every
currency in use: GBP, CHF, JPY, VND, CNY, TWD, ILS, UAH, PLN, RUB, AUD,
SGD, HKD, CLP, PYG, VES. `tests/test_numbers.py` reads every lane's
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
