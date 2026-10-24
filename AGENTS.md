# Instructions for agents

These instructions apply to the whole repository. A country-data pull request
is not a collection of plausible charts: it is a reproducible claim about what
specific publishers measured, on which definitions, in which years. Preserve
that standard when adding a country or refreshing one already here.

## Read before changing country data

Read these documents in order and follow them as part of this file:

1. [SOURCING_A_COUNTRY.md](SOURCING_A_COUNTRY.md) — research order, source
   hierarchy, definitional traps, fetcher rules and the sourcing checklist.
2. [COUNTRIES.md](COUNTRIES.md) — current publication inventory, language
   policy, known country-specific hazards and any active queue.
3. [ADDING_A_COUNTRY.md](ADDING_A_COUNTRY.md) — repository layout, country
   isolation, implementation, localization, rendering and tests.
4. [PLATE_SPINE.md](PLATE_SPINE.md) — canonical topics, panel slots, units,
   scales and preferred comparable sources.

For an update, also read the country's `DATA_NOTES.md`, `SOURCES.yaml`,
`country.yaml`, `ui.json`, tests and any `DISCOVERY.md` or `HANDOFF.md`. Do not
infer an old series' meaning from its filename or chart title.

When these documents disagree with an implementation detail, stop and resolve
the discrepancy from the publisher's metadata and the repository tests. Do not
silently choose the easiest interpretation.

## Non-negotiable rules

1. **Keep countries isolated.** Country code may read only its own directory
   through the repository accessors. Never copy another country's values into
   a new country, reach across country directories at runtime, or add a
   country-specific branch to `core/`.
2. **Committed CSVs are the publication source of truth.** Rendering and site
   builds must remain offline and reproducible. Network access belongs only in
   `countries/<slug>/fetch/`.
3. **Research precedes charts.** Identify the computing institution, exact
   endpoint, definition, unit, geography, time basis, coverage and revision
   policy before implementing a series. Write `SOURCES.yaml` and source notes
   as the evidence is established, not after the plate is drawn.
4. **Fetchers never overwrite curated data.** They write review sidecars such
   as `*_check.csv` or `*_from_<source>.csv`. A human or agent reviews the diff
   and deliberately promotes accepted values into the curated CSV.
5. **Never splice incompatible series.** National and harmonized, cash and
   accrual, central and general government, customs and balance of payments,
   survey and administrative, citizenship and birthplace, and police and
   vital-statistics series stay separate and labelled.
6. **Never turn missing into zero.** Preserve missing years as missing. Do not
   interpolate, forward-fill or zero-fill unless the publisher defines that
   operation and the plate says so.
7. **A proxy remains a proxy.** Use one only when it answers a useful adjacent
   question, label it in the data, plate, page copy and source notes, and never
   present it as the requested national statistic.
8. **Official status is data, not prose.** Set `official: false` in
   `SOURCES.yaml` for redistributors, market series, associations and other
   non-official sources. A note alone is insufficient.
9. **Generated artifacts travel with their inputs.** Commit accepted CSVs,
   rendered plates, thumbnails and `provenance.json` together.
10. **No silent gaps.** Every canonical slot is filled with verified data or
    visibly pending with a precise explanation. An empty, failed or omitted
    graph is never an acceptable final state.

## Classify every apparent data gap

**A gap is not closed until every official route has been tried.** Do not
leave a good source behind: before a slot is marked pending, the lane must
have attempted, and recorded the result of, every route that could carry the
series — the national publisher's own API and file downloads, its official
mirrors and open-data portals (for Ukraine: `data.gov.ua`, the SDG portal),
the central bank, the finance ministry, the customs authority, the treasury,
the prosecutor/court statistics publisher, the market regulator, and the
harmonised international layer (IMF, World Bank, OECD, Eurostat, UN bodies)
including the agency's own API rather than only its republication. "The main
site 403s" is a route result, not a finding that the data is unavailable.
A slot may be skipped only when the statistic does not exist, is not
published on any official route at all, or every route has been attempted
and its failure mode recorded with a date. A chapter may not be omitted
because the obvious publisher is blocked while a working official mirror or
national publisher exists untried.

Before calling a panel unavailable, determine which case actually applies:

- **Not applicable or nonexistent:** for example, no national statutory
  minimum wage. State that directly; it is a finding, not a fetch failure.
- **Published and retrievable:** fetch and stage it. A blank panel is unfinished.
- **Published but blocked or unstable:** try the documented machine-readable
  endpoint, official bulk download and appropriate harmonized source. Record
  the endpoint, response or failure mode, and review date in the country's
  notes or manifest.
- **Published but not yet definition-checked:** it remains work to do. Do not
  describe it as nonexistent.
- **Available only on an incompatible definition:** keep the desired slot
  pending or show the adjacent series explicitly as a proxy; do not relabel it.
- **Absent from one international publisher:** check national and other
  appropriate sources. Coverage decisions differ by dataset, especially for
  Taiwan.
- **Present in the CSV but absent from the plate:** diagnose the code, schema,
  provenance and render path. This is a rendering defect, not missing data.

For every unresolved gap, use `ctx.pending(...)` where the spine requires the
slot and add a localized entry to each locale's `unavailable` list in
`countries/<slug>/ui.json`. The explanation must distinguish true absence,
access failure, incomplete research and deliberate rejection of a bad proxy.
Keep `SOURCES.yaml`, `DATA_NOTES.md`, page copy and the plate consistent.

Do not leave stale words such as “pending,” “official only,” or “unavailable”
after filling a gap. Search the country's metadata, chapter copy, source notes
and rendered site for contradictions.

## New-country workflow

1. Inspect the worktree and existing country conventions. Preserve unrelated
   user changes and do not use destructive Git commands.
2. Build a source matrix for every spine topic before coding. For each desired
   slot record publisher, dataset/table/code, URL, definition, unit, geography,
   frequency, period basis, first/last observation, revision status, official
   status and a known-value check.
3. Start with the national statistical office, central bank, finance ministry,
   customs authority, vital-statistics publisher and police/justice publisher.
   Add harmonized sources for canonical comparisons; do not pass them off as
   the national layer.
4. Create the country directory and manifest as described in
   `ADDING_A_COUNTRY.md`. New plates use the declarative form and the shared
   spine unless a documented national-data reason requires a departure.
5. Write one fetcher per publisher. Validate content type or file signature,
   expected columns, row counts, year coverage and at least one known value.
   Official gateways sometimes return error HTML with HTTP 200; a fetcher must
   reject it rather than cache or parse it as data.
6. Normalize only after preserving the source meaning. Keep raw-source or
   sidecar evidence reviewable, put units in column names where practical, and
   document every calculation or mapping.
7. Implement chapters, plates, events, locale catalogs, UI copy, SEO, source
   disclosure and country-specific semantic tests. Every visible claim must be
   supported by a committed file and every locale must carry equivalent facts.
8. Resolve all fillable gaps. For what remains, publish the localized
   unavailable-data disclosure described above.
9. Regenerate and verify the entire country, then run the repository-wide gate
   before opening the pull request.

## Existing-country update workflow

1. Read the country's notes and manifest, then run `make C=<slug> fetch` to
   create sidecars. A failing fetch does not authorize replacement with a
   convenient different series.
2. Diff every sidecar against its curated CSV. Investigate historical
   revisions, changes of units, code lists, geography, methodology, frequency
   and provisional/final status. Do not review only the newest row.
3. Sanity-check at least one known observation and the latest accepted value
   against the publisher's presentation or a second authoritative source.
4. Promote only reviewed values. Update `last_full_year`, the country window,
   partial-period captions, events, annotations, source notes and card copy when
   the new data require it.
5. Re-check every prior statement affected by the refresh. Peaks, lows,
   rankings, recession bands, “latest” claims and narrative captions can become
   stale even when the chart still renders.
6. Regenerate plates, thumbnails and provenance. Inspect the country page to
   ensure each dataset is used by the intended plate and no source or pending
   disclosure became stale.
7. Run the full PR gate below. Keep the update scoped; do not mix unrelated
   redesigns or refactors into a data refresh.

## Normalization review

Explicitly verify these dimensions before joining, comparing or deriving data:

- calendar year, fiscal year, quarter and observation date;
- fiscal-year label convention (starting year or ending year);
- local calendars such as Taiwan's ROC year (`ROC + 1911`);
- flow, stock, rate, share, index and cumulative year-to-date value;
- monthly/quarterly aggregation (sum, mean, last observation or annualized);
- current versus constant prices and the price/base year;
- local currency scale (units, thousands, millions, billions) and FX convention;
- nominal, real, seasonally adjusted and calendar-adjusted status;
- cash/accrual accounting and budget/outturn/forecast status;
- central, federal, state, public-sector and general-government perimeter;
- residence, citizenship, birthplace, nationality and event/person counts;
- territorial coverage and population denominator;
- survey versus administrative record;
- national versus harmonized methodology and report vintage;
- suppressed, provisional, revised, missing and structurally unavailable values.

Use one vintage for a recomputed historical index. Derive a value only when the
components share a compatible definition and vintage; document the formula and
test a known result. Align series by year or date, never by list position.

## Verification and visual review

### Comparison-scale contract

The comparison viewer wipes one finished country SVG over another. Canonical
panels therefore need more than the same topic and position: they must use the
same indicator definition, denominator, unit, base year, axis type, limits and
ticks. Follow `PLATE_SPINE.md` and `core/spine.py` exactly.

- Put only the canonical definition in a canonical slot. A useful proxy or
  adjacent national measure belongs in the lens or remains visibly pending;
  disclosure does not make unlike units comparable.
- Convert counts with the same-scope population and canonical denominator.
  Do not mix people with households, gross with net, goods with goods and
  services, admissions with total immigration, or a non-2006 index with a
  `2006 = 100` slot.
- Never set a canonical y-scale in country code. The atlas-wide range is the
  one in `core/spine.py`, and pending panels inherit it too. If verified data
  exceed it, update the shared range and regenerate every country carrying
  that topic; never extend only one country.
- Canonical time-series slots use the common year window. A one-year category
  snapshot belongs in a lens, not in a canonical time-series slot.
- Before opening a PR, run `python3 -m pytest tests/test_spine.py -q`. Its
  comparison-contract test requires identical positions, scales, limits,
  ticks and units across every peer. Then inspect representative overlay wipes
  (a low, middle and outlier country) for every changed topic.

During iteration, run focused country tests and renders. Before a country PR is
ready, run from the repository root:

```sh
make C=<slug> charts thumbs provenance
make site
make test
git diff --check
```

If shared code, shared UI, the spine, number formatting or more than one country
changed, regenerate and test all countries:

```sh
make charts thumbs provenance site
make test
git diff --check
```

Tests are necessary but not sufficient. Inspect every changed plate in every
published locale, its thumbnail and the generated country page. Check for blank
panels, missing series, clipped labels, untranslated strings, unreadable text,
wrong units, axes that hide data, stale annotations, incorrect source labels
and partial years drawn as completed totals. Compare the rendered plate with
the curated CSV and `provenance.json` rather than trusting a screenshot alone.

Do not update a layout baseline merely to make a failure disappear. Inspect the
plate, explain why the new layout is correct, and only then record the baseline.

## Pull-request contract

A country pull request should be reviewable without reconstructing the research
session. Its description must state:

- whether it adds a country or refreshes an existing one;
- the publishers and exact datasets added or changed;
- the covered years and `last_full_year` decision;
- the important definitions, conversions, derivations and source seams;
- every proxy, non-official source and spine departure;
- every unresolved or blocked source, the attempted endpoint/failure and how
  the site discloses it;
- whether historical values changed and why;
- the plates, locales and generated artifacts reviewed;
- the exact verification commands and results.

The diff must not contain caches, downloaded workbooks, temporary probes,
unreviewed sidecars, credentials or unrelated files. It must contain the source
manifest and notes for every curated CSV, semantic tests for country-specific
claims, all required translations, regenerated outputs and provenance.

Before handing off, confirm the worktree contains only intentional changes and
that every claimed test actually ran on the final diff. Do not describe a PR as
complete while fillable slots, stale disclosures, failing fetch validation,
missing translations, unreviewed generated output or unexplained test failures
remain.
