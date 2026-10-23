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
| `france` | fr · en · pt | 12 | 46 |
| `israel` | he · en · pt | 8 | 18 |
| `spain` | es · en · pt | 12 | 46 |
| `south-korea` | ko · en · pt | 11 | 43 |
| `united-kingdom` | en · pt | 12 | 45 |
| `usa` | en · pt | 11 | 43 |

The counts are the spine-vintage numbers (2026-10-22): plates are the drawn
chapters per country, datasets the curated CSVs the plates read, sidecars and
cross-check files not counted.

## Queued

| # | Country | Slug | Languages | What it needs that we do not have |
|---|---------|------|-----------|------------------------------------|
| 1 | Italy | `italy` | it · en · pt | A fourth Romance locale. New `AFFIX` column for `it`. Migration from Eurostat and ISTAT. |
| 2 | Japan | `japan` | ja · en · pt | CJK: Noto Sans CJK JP, already installed. Fiscal year starts in April. |
| 3 | China | `china` | zh-Hans · en · pt | CJK Simplified. Source reliability is the whole problem; see below. |
| 4 | Taiwan | `taiwan` | zh-Hant · en · pt | CJK Traditional. Not in most international datasets; see below. |
| 5 | Vietnam | `vietnam` | vi · en · pt | Vietnamese diacritics — check the plate font covers them. |
| 6 | Portugal | `portugal` | pt · en | Nothing new — Portuguese is already in the atlas. Eurostat alongside INE Portugal, as with France and Spain. |
| 7 | Switzerland | `switzerland` | de · en · pt | A German locale — new `AFFIX` column for `de`. Not in the EU: EFTA member, so Eurostat carries it in many but not all tables — verify per dataset. CHF, not EUR; SNB, not ECB. |

## Known problems, written down before they are hit

**Israel is right-to-left.** Neither the page nor matplotlib handles RTL
today: the masthead, the card grid and the figure text all assume
left-to-right, and matplotlib does no bidi shaping, so Hebrew renders
reversed and unjoined even with a Hebrew font installed. This is roughly a
country's worth of work on its own, and it is being built rather than
skipped — a country that does not publish in its own language is not an
edition of this atlas. It also buys Arabic later.

**China's problem is not the language.** The National Bureau of Statistics
publishes a full set of numbers; the question a reader will have is
whether to believe them. The atlas does not answer that question by
leaving China out or by substituting a Western estimate for an official
one. It publishes what the NBS publishes, marked as such, beside the
international series — World Bank, IMF, UN Comtrade — where those exist,
and says in the notes where the two disagree and by how much. That is the
same rule every other country here gets.

**Taiwan is missing from the international layer.** The World Bank, the
IMF and the UN do not carry it, so the comparables that make every other
country legible are mostly unavailable. DGBAS and the central bank publish
well and in depth; the `World` chapter will have to be built from what
Taiwan publishes about itself plus the bodies that do carry it (the WTO,
and its own customs administration).

**Fiscal years that are not calendar years.** Japan's starts in April,
as do the United Kingdom's and India's should it ever be queued. The USA
already has this — its debt table keys on `fiscal_year` — so the mechanism
exists; it just has to be used deliberately and labelled on the panel.

**Number styles.** `AFFIX` and `CURRENCY_AFFIX` in `core/sitebuild.py`
and the unit rules in `core/i18n.py` are keyed by *number style*
(`core/numstyle.py`), and every Phase B style — de, it, pt-PT, ja,
zh-Hans, zh-Hant, vi, he — and currency — GBP, CHF, JPY, VND, CNY, TWD,
ILS — already has its forms. `tests/test_numbers.py` reads every lane's
country.yaml and fails on a locale or currency with no form, which is the
intended behaviour. Portugal must declare `number_style: {pt: pt-PT}`.
Hebrew has its numbers and affixes only; right-to-left layout is still
the open problem described above.

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
