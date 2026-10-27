# Adding or updating a country

Instructions to myself, written while merging five independent atlases into
one tree. Read the first section even when only refreshing a number.

This is the **mechanics**: the files, the APIs, the build loop.
[SOURCING_A_COUNTRY.md](SOURCING_A_COUNTRY.md) is what comes first — how to
decide what the plates are and which institution publishes each number.

---

## The rule that outranks every other

**No code that draws one country may read another country's data.**

Five atlases that used to be five repositories now share a checkout. The
failure that matters here is not a crash: it is a French number on a
Brazilian plate. Nobody notices, because both are plausible, and the atlas
is worth nothing the moment one of them is wrong.

So the rule is mechanical, not a convention. Four things enforce it, and
all four must keep holding:

1. **One accessor.** Every path is resolved by `core.country.within(base,
   rel, slug)`, which resolves the result and refuses anything that lands
   outside `countries/<slug>/`. A `..` segment, an absolute path and a
   symlink pointing out all fail the same test, because it checks the
   resolved target and not the string. `Country.data()`, `Country.out()`
   and `Context.table()` are all it.
2. **Filesystem watching.** `tests/test_isolation.py` draws every plate
   and builds every card with `open` watched, and fails on any read
   outside the country's own directory. It is verified against a
   deliberate breach, so it is known to catch one rather than assumed to.
3. **Recorded provenance.** `core.provenance` watches a real render and
   writes `countries/<slug>/provenance.json`: plate → the CSVs it read.
   `tests/test_sources.py` checks every recorded file against that
   country's own manifest.
4. **No country's name in shared code.** `tests/test_core.py` reads
   `core/` and fails if it names a country in code. A comment may explain
   one; an `if slug == "france"` may not.

Practically, that means two things when working here:

- A plate function receives a `ctx` and nothing else. It never imports
  `pathlib` to build a path, never reads `countries/` itself, and has no
  way to name another country. Keep it that way.
- A fetcher lives in `countries/<slug>/fetch/`, computes
  `ROOT = Path(__file__).resolve().parent.parent`, and writes only under
  `ROOT / "data"` and `ROOT / "cache"`. It is the one kind of code here
  that touches the network, and it is never run by the build.

---

## The layout

```
countries/<slug>/
  country.yaml       identity: name, locales, palette, years, bands
  data/              the committed CSVs — the source of truth
  SOURCES.yaml       who publishes each CSV, and its caveats
  DATA_NOTES.md      what these sources were like to work with
  provenance.json    generated: plate -> the CSVs it read
  plates.py          PLATES, and one function per plate
  chapters.py        build(ctx) -> the cards, their copy, their figures
  i18n.json          every string the plates emit, translated
  ui.json            the masthead line, the dek, the reading notes
  events.py          EVENTS: year -> a short label for annotations
  datasets.py        optional, where a country reads its CSVs its own way
  fetch/             the refreshers. The only code that uses the network.
  output/            the rendered plates and thumbs. Committed.
  tests/             only what cannot be asked of every country
```

Nothing outside `countries/<slug>/` changes when a country is added. If a
new country needs a change in `core/`, that change has to make sense for
the other five — and if it does not, the country is asking for a hook that
belongs in its own `country.yaml`.

---

## Adding one

### 1. `country.yaml`

Copy France's and replace it. The fields that need thought:

- **`locales`** — in the order the page offers them, each with `code`,
  `html_lang`, `og_locale` and `endonym`. This is the country's own set:
  Argentina publishes Spanish and South Korea Korean, and neither needs
  the other's. `default_locale` is the one the language negotiator falls
  back to.
- **`number_style`** — optional. How a locale writes its numbers, when
  that is not the language's base style. Portugal and Brazil share the
  `pt` catalogs and chrome but not their numbers, so Portugal says

  ```yaml
  number_style: {pt: pt-PT}
  ```

  and its cards read `291 mil milhões de euros` and `12,5 %` where
  Brazil's read `R$ 11.745 bi` and `12,5%`. A locale not named here uses
  the style of the same name — Brazil names nothing. The style must be one
  of the language's own (`core.numstyle.STYLES`); the loader refuses
  `{pt: de}`, and `tests/test_numbers.py` fails a country whose
  `html_lang` names a style it did not select. German is German on every
  German page, Switzerland's included: there is no `de-CH` style.
- **`name`** — the country's name in *every* locale any country publishes,
  not just its own. The atlas switcher on a Korean page names France in
  Korean, so a missing entry there is a hole on someone else's page.
  `tests/test_catalogs.py` fails on one.
- **`years`** and **`last_full_year`** — the span every plate shares, and
  the last year whose annual totals are complete. Everything about partial
  years follows from the second number; see below.
- **`tick_every`** — the x-axis stride. Twenty-one annual ticks do not fit.
- **`palette`** — the country's own colours, and the reason this is in yaml
  rather than code. Flags are not chart palettes: pure flag colours next to
  each other vibrate and white is the paper, so these are darkened,
  desaturated siblings that survive greyscale. `flag_bands` is the header
  rule; a band the colour of the paper gets an outline automatically.
  `palette.web` is the site chrome, and `mark_bearing` / `mark_size` tune
  the wordmark: the bearing is per-letter (an open F needs less than a B,
  and Hangul needs none, because CJK glyphs are centred in a fixed em box).
- **`seo`** — `title`, `description` and `keywords` per locale. Real
  sentences; they are what a search result shows.
- **`sources`** — the institutions named in the dek, per locale. They must
  agree with `SOURCES.yaml`.

### 2. `data/` and `SOURCES.yaml`

Commit the CSVs first, and give every one an entry in `SOURCES.yaml` with
its publisher, its URL and its caveats. A committed CSV with no entry fails
the build.

A dataset is official unless the manifest says otherwise. If a series is
*not* — a market index, a parallel exchange rate, an industry survey —
write `official: false` on it. Do not leave the disclaimer in the prose of
a `notes:` field: the page reads the flag, not the prose, and will label it
"Official" while its own note denies it. A test looks for exactly that
contradiction, in five languages.

Every row needs every column. A row missing its trailing comma parses as
one column short and the plate silently loses a year.

### 3. `plates.py`

```python
def plate_economy(ctx):
    gdp = ctx.table("macro/gdp.csv")
    ig = ctx.fig("Title", "Subtitle", source=ctx.source("INSEE", "Eurostat"))
    ax = ig.next_panel("GDP at current prices")
    yrs, vals = ctx.series(gdp, "nominal_bn")
    ctx.line(ax, yrs, vals, ctx.p.BLUE)
    for ax in ig.axes_flat:
        ig.style_axis(ax)
    ig.save(ctx.out("01_economy.png"))

PLATES = (
    dict(id="01", slug="economy", builder=plate_economy,
         title="...", subtitle="...", alt="..."),
)
```

Two shapes are accepted, because two grew up in the five original
projects. **New countries use the declarative one above**: the title and
the alt text are reviewable without reading the drawing code, and `alt` is
required there because it is the only thing a screen-reader user gets
instead of the image. The older shape — `("plate_economy", plate_economy)`,
the function titling and saving itself — is kept working for the plates
already drawn that way.

What the context gives you, and why to use it rather than the equivalent:

- `ctx.table(rel)` / `ctx.rows(rel)` / `ctx.has(rel)` — the CSVs, resolved
  under this country's `data/`. This is the isolation boundary.
- `ctx.line` / `ctx.bars` — already carry this country's `last_full_year`,
  so the running year is dashed or hatched without the call site
  remembering. This is the single most load-bearing binding here: the worst
  bug in the original build drew half a year of trade as an annual total,
  which read as a 50% export collapse that never happened.
- `ctx.fig(...)` — a figure in this country's identity. The default
  `right=0.955` leaves room for the label of a second y-axis in the
  right-hand column; `core.qa` fails the build when a label runs off the
  canvas. Pass `topic=` to draw on the spine (below).
- `ctx.pending(ax)` — the placeholder for a panel whose CSV is not
  committed yet. Better than an empty axes, and visible in review.
- `ctx.p` — the palette. `ctx.p.cycle(i)` for a series without a meaning.
- `ig.add_event`, `ig.add_band`, `ig.add_recessions`, `ig.mark_partial`,
  `ig.headroom` — annotations. Keep events sparse per panel: twenty rules
  on a line is a timeline, not a chart.

#### Drawing on the spine

Every country draws a chapter with the same panels in the same slots, on
the same scales and in the same units, so the comparison viewer can wipe
one country's plate over another's. [PLATE_SPINE.md](PLATE_SPINE.md)
holds the decisions and `core/spine.py` the table: each topic's four
slots, canonical or lens, with the unit, the reference y-range and
whether it is log.

A plate goes on the spine by declaring its topic and claiming its panels
by key with `ig.slot(key, title)` instead of `ig.next_panel(title)`:

```python
def plate_economy(ctx, ig):                     # declarative builder
    gdp = ctx.table("macro/gdp.csv")

    ax = ig.slot("economy.growth", "Real GDP growth (% per year)")
    yrs, vals = ctx.series(gdp, "real_growth")
    ctx.bars(ax, yrs, vals, lambda v: ctx.p.GREEN if v >= 0 else ctx.p.alert)
    ig.add_recessions(ax)                        # labelled on slot 1 only

    ax = ig.slot("economy.gdp_per_person", "GDP per person (US$, current)")
    ctx.line(ax, *ctx.series(gdp, "gdp_per_capita_usd"), ctx.p.BLUE)
    ig.add_recessions(ax, label=False)

    ax = ig.slot("economy.inflation", "Consumer prices (% per year)")
    ctx.pending(ax)                              # only if it truly doesn't exist

    ax = ig.slot("economy.unemployment", "Unemployment (% of labour force)")
    ...
    for a in ig.axes_flat:
        ig.style_axis(a)

PLATES = (
    dict(id="01", slug="economy", topic="economy", builder=plate_economy,
         title="...", subtitle="...", alt="..."),
)
```

A function plate passes the topic itself:
`ig = ctx.fig(title, subtitle, source=..., topic="economy")`, and then
saves as usual.

What the spine does for you, and what it holds you to:

- **The frame is fixed.** A plate with a topic is 2 × 2 at 16 × 10.2 in,
  `right=0.955`, and the country's `tick_every` must be 2. Anything else
  raises when the figure is created.
- **Slots go in order.** Claiming `economy.inflation` before
  `economy.growth` raises. Each slot lands in its own place on the grid
  (slot 3 is bottom-left whatever happened before), every canonical slot
  must be claimed (`ctx.pending` it when the data do not exist), and a
  lens slot, always the last, may be left out and is then hidden.
  `next_panel` is refused on a spine plate.
- **The scale is applied for you.** When the plate is saved, each
  canonical panel is put on its reference range, so any `set_ylim` or
  `headroom` you call on it is overridden. If your data leave the range
  the axis grows until they fit, never clipping them, and the panel says
  "scale extended" in its top-right corner. Signed slots get a zero line
  and log slots a log axis with fixed ticks as soon as they are claimed.
  Lens slots and pending panels are left as you drew them.
- **The unit is the y-axis label** (pass `unit=False` if the panel says
  it some other way). The unit strings and "scale extended" go through
  your `i18n.json` like everything else; `core.spine.strings()` lists
  them.
- **Rates come from `ctx.per_100k(count, population)` and
  `ctx.per_1000(...)`**, which match the two series by year and raise
  when a year has a count but no population. `ctx.index_2006(series)`
  rebases a level, and `ctx.fx_index(lc_per_usd)` turns local currency
  per US$ into an index where up means stronger. They live in
  `core/rates.py`.

Set `spine: true` in `country.yaml` once every plate is migrated.
`tests/test_spine.py` then draws all of them and checks that each chapter's
plate declares the chapter's topic, that slots carry their keys in order,
the frame, `tick_every`, that no y-axis is inverted or clips its data,
that log slots are log, and that every canonical panel sits on its
reference range unless it carries the marker.

### 4. `chapters.py`

`build(ctx)` returns the cards in page order. Every number on a card is
read from the CSVs at build time, so a figure on a card and the same figure
on its plate cannot disagree:

```python
{
  "id": "01_economy", "topic": "economy", "n": "01", "family": MONEY,
  "title": ctx.text(en="The Economy", pt="A Economia"),
  "blurb": ctx.text(en="...", pt="..."),
  "spark": ctx.col("macro/gdp.csv", "nominal_bn"),
  "stats": [ctx.stat({"en": "GDP"}, ctx.col("macro/gdp.csv", "nominal_bn"),
                     "money_bn")],
}
```

`topic` is this chapter's place in the shared spine — `economy`,
`fiscal`, `spending`, `trade`, `markets`, `people`, `world`, `demography`,
`security`, `mortality`, `credit`, `migration` — and it is what the
comparison control matches on. The numbering cannot do that job: France's
`01_economy` and Argentina's `01-output` are the same chapter, Brazil
numbers trade sixth where France numbers it fourth, and Argentina has no
`spending` chapter at all. Declare the topic the chapter actually answers;
a topic no other country has simply means the comparison menu will say so,
which is honest. A country may not use one topic twice — the comparison
would have no way to choose between the two plates — and `tests/test_site.py`
enforces both that and the spine.

`family` is one of `money`, `world`, `people` — the filter chips on the
page. The third argument to `ctx.stat` is a format spec from
`core.sitebuild.NUMFMT`, which says how a figure is *written*, not what it
means. Each locale then writes it in its number style: the separators and
the magnitude word (`Mrd.`, `mil milhões`, `bi`), the currency on the side
that language puts it, and — in Japanese, Chinese and Vietnamese — the
figure *rescaled* onto the language's own magnitudes, so `money_tn` 636.9
for Japan is `637兆円` and `usd_bn` 684.4 is `6,844億ドル`
(`core.numstyle.LADDERS`). Elsewhere a figure of a thousand or more of
the spec's unit moves one word up, to three significant digits —
`usd_bn` 30,861 is `US$ 30.9tn`, `R$ 1,10 tri`, `1,04 Bio. US-$` —
except in French and Italian, which keep `2 991 Md€` and `2.265 mld €`
(`core.sitebuild.STEP_UP`). Every style and currency in the atlas, with
its exact output, is pinned in `tests/test_numbers.py`; a new currency
needs a `CURRENCY_AFFIX` entry for every style its country publishes. `kind=` says whether it is current: `flow` for an annual total,
only comparable once the year is complete; `level` for a stock or a rate
read at a moment; `projection` for an official forward estimate. Getting
this wrong puts a half-finished year on a card as though it were a result.

#### Stories (optional)

A chapter may carry a `"stories"` entry: for each of its panels, a short reading
the viewer opens beside the isolated chart. Brazil's are the reference
(`countries/brasil/stories.py`, one `<topic>_stories(ctx)` function per chapter,
loaded from `chapters.py` with `core.sideload.sibling`):

```python
"stories": {"economy.growth": ctx.story(
    title=ctx.text(en="GDP only passed its 2014 level in {back_year}", pt="..."),
    beats=[(ctx.text(en="Two falls add up to double the covid one", pt="..."),
            ctx.text(en="Chained, {y1} and {y2} take {loss} off GDP...", pt="..."))],
    facts={"back": ..., "loss": ...})}
```

- 3 to 4 insights per panel, each a head of at most 7 words and one or two
  sentences of at most 32. An insight says what the chart shows but does not
  say (a ratio, an accumulation, who overtook whom, what a highlight implies,
  what the picture leaves out); it never recaps the chart or explains how to
  read it. The title is the one sentence a reader keeps, so it must be true on
  its own.
- Every number and year is a `{placeholder}` filled from the country's CSVs
  (`ctx.fact`), in each locale's number style. A claim that is only true while
  the data keep a certain shape is guarded with a `need(...)` that raises, so a
  refetch that falsifies a sentence breaks the build instead of publishing it.
- No cause that is not in the data, no judgement of governments or people, no
  hypothetical.
- Every locale the country publishes is written (`tests/test_stories.py` fails
  on a gap).

### 5. `i18n.json` and `ui.json`

`i18n.json` maps each English string the plates emit to its translations:

```json
{"(half year)": {"fr": "(semestre)", "pt": "(meio ano)"}}
```

The figures are localised at save time, on the finished figure, so a plate
cannot ship half-translated — and a string with no entry stops the render
rather than shipping in the wrong language.
`tests/test_catalogs.py::test_every_string_the_plates_emit_has_a_translation`
renders everything in every language with `strict=True`, which is the
authoritative check: write the plates first, run it, and let it tell you
what the catalog is missing.

`ui.json` is keyed by locale and carries the page chrome: `line` (the
masthead), `dek`, `notes` (the reading caveats), `colophon`. The shared
chrome — buttons, the viewer, the sources table — lives in `site/ui.json`
and needs an entry in the new country's languages if they are new to the
atlas.

`{n}`, `{window}`, `{from}`, `{to}`, `{generated}` are substituted in any
of this copy. An unsubstituted `{window}` on a page means the key was
spelled something else.

### 6. `fetch/`

One script per publisher, run by hand, never by the build:

```sh
make C=<slug> fetch
```

A fetcher **never overwrites a curated number.** It writes what it pulled
beside the curated file, as `<name>_check.csv` or `<name>_from_<source>.csv`,
and a person diffs it. A live API that revises its history, or serves an
error page under HTTP 200, therefore cannot change a published chart. Both
sidecar conventions are recognised by `tests/test_sources.py`, which also
fails if any plate draws from one.

Fetchers need `requests` and sometimes `openpyxl` —
`requirements-fetch.txt`, deliberately not installed by CI.

### 7. Render, record, build

```sh
make C=<slug> charts thumbs provenance
make site
make test
```

`charts` draws every plate in every language the country publishes.
`thumbs` makes the card-sized copies. `provenance` records what each plate
read. All three write under `countries/<slug>/`, and the plates and thumbs
are **committed** — they are the reviewable artefact beside the CSV that
produced them.

A language whose script no installed font covers is refused rather than
drawn: a page of tofu boxes is worse than a build error. Korean needs
`fonts-noto-cjk`. Note that matplotlib indexes only the first face of an
OpenType collection, so it may see "Noto Sans CJK JP" where fontconfig
lists KR — the pan-CJK faces are one glyph set with different regional
defaults for Han, and every one of them carries the whole Hangul block, so
the JP face is a correct fallback for Korean rather than an approximation.

### 8. Tests

Everything in `tests/` that takes a `country` argument runs against the new
country automatically — the isolation boundary, the manifest, the CSV
shapes, the catalogs, the pages, the layout. That is the point of the
monorepo: a rule that holds for France has to hold for a country added next
year without anyone remembering to copy the test.

`countries/<slug>/tests/` is for what can only be asked of this country —
the facts its plates assert. Write these as claims about the data, not
about pixels:

- Ask the CSV for the fact, then check the panel says it. A test that
  reads two series off a chart and zips them by index compares different
  years; use `Panel.paired(a, b)` from `tests/probe.py`, which aligns on
  the year.
- A test that `skipTest`s when it cannot find what it is looking for has
  stopped checking. One here did, silently, for months.
- The layout checker (`core.qa`) is fatal for a label drawn outside the
  canvas and held at a committed count baseline for the house-style faults
  — overlap, clipping, a label on the data. Re-record it with `make
  baseline` only after looking at the plate and deciding the change is
  right.

---

## Updating a country

1. `make C=<slug> fetch` — refresh the sidecars.
2. Diff each sidecar against its curated CSV. Copy across what you accept;
   leave a year the publisher has not covered **empty**. A blank is dropped
   from a line; it is never zero-filled, because a hole in a series is a
   hole and not a collapse to zero.
3. Bump `last_full_year` in `country.yaml` when a year completes, and
   `years.to` when the window moves.
4. The captions that say *how* incomplete a partial year is — "2025: 11
   months · 2026: 9 months" — are written on the plate and do need
   editing. `grep mark_partial countries/<slug>/plates.py` finds them all.
5. `make C=<slug> charts thumbs provenance && make site test`.
6. Commit the CSVs, the plates, the thumbs and `provenance.json` together,
   so every chart stays reproducible from its committed inputs.

If a refreshed number invalidates something a plate *says*, a test in
`countries/<slug>/tests/` fails. That is the design: the claim breaks
loudly instead of changing quietly.

---

## Things that have gone wrong here, so they do not again

- A dataset labelled **Official** whose own note said it was not. The page
  reads the flag, not the prose.
- A CSV row **missing its trailing comma**, which parsed one column short.
- A semantic test pointed at the wrong panel, where it found nothing to
  compare and **skipped instead of failing**.
- Two series **zipped by index** rather than aligned by year, comparing
  2006 against 2013.
- Six plates whose right-hand **axis label was drawn off the canvas** — not
  clipped, not drawn at all, so the reader never learned what the second
  axis measured.
- A `from core.country import within` in a country's `datasets.py`, which
  bound the function at import time and **read around the watcher**. Import
  the module, call `_boundary.within(...)`, and the one check stays one
  check.
