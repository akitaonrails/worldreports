# The queue

Which countries are in, which are coming, and what each one needs that the
last one did not. One at a time, in this order. Method:
[SOURCING_A_COUNTRY.md](SOURCING_A_COUNTRY.md), then
[ADDING_A_COUNTRY.md](ADDING_A_COUNTRY.md).

Every country publishes in **its own official language, plus English and
Portuguese**, and every plate is drawn in each of them.

## Published

| Slug | Languages | Plates | Datasets |
|------|-----------|--------|----------|
| `argentina` | es · en · pt | 9 | 25 |
| `brasil` | pt · en | 11 | 32 |
| `france` | fr · en · pt | 11 | 36 |
| `south-korea` | ko · en · pt | 10 | 37 |
| `usa` | en · pt | 11 | 28 |

## Queued

| # | Country | Slug | Languages | What it needs that we do not have |
|---|---------|------|-----------|------------------------------------|
| 1 | Canada | `canada` | en · fr · pt | Two national languages, both already in the atlas. Nothing new. Migration from IRCC and StatCan, which publish it unusually well. |
| 2 | Spain | `spain` | es · en · pt | Nothing new. Eurostat alongside INE, as with France. **First migration chapter** (see below). |
| 3 | United Kingdom | `united-kingdom` | en · pt | Post-Brexit: the Eurostat migration series carries UK values only to 2019. Migration from the ONS and the Home Office, across three methodologies in five years. |
| 4 | Italy | `italy` | it · en · pt | A fourth Romance locale. New `AFFIX` column for `it`. Migration from Eurostat and ISTAT. |
| 5 | Israel | `israel` | he · en · pt | **Right-to-left.** See below. |
| 6 | Japan | `japan` | ja · en · pt | CJK: Noto Sans CJK JP, already installed. Fiscal year starts in April. |
| 7 | China | `china` | zh-Hans · en · pt | CJK Simplified. Source reliability is the whole problem; see below. |
| 8 | Taiwan | `taiwan` | zh-Hant · en · pt | CJK Traditional. Not in most international datasets; see below. |
| 9 | Vietnam | `vietnam` | vi · en · pt | Vietnamese diacritics — check the plate font covers them. |

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

**A fourth and fifth script.** `AFFIX` and `CURRENCY_AFFIX` in
`core/sitebuild.py` are keyed by language, and every new locale needs a
column in both. The catalog test fails until it has one, which is the
intended behaviour.

## The migration chapter

A twelfth chapter, added to the spine for the European countries at the
point they were queued, and available to any country whose publishers
measure it. Eurostat carries eleven harmonised migration tables covering
every EU member — immigration and emigration, the resident stock on both
the citizenship and the country-of-birth definition, asylum applications
and first-instance decisions, first and valid residence permits,
acquisitions of citizenship — all verified live against the dissemination
API before being written down here.

That makes Spain, Italy and France straightforward and the United Kingdom
hard, because its Eurostat rows stop in 2019 and the ONS has changed
method twice since. Hard is not a reason to leave it out; it is a reason
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
