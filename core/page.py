"""Write the static site: one real HTML page per country per language.

    python3 -m core.page            # every country, into _site/
    python3 -m core.page france
    python3 -m core.page --out /tmp/check

Why the pages are built here rather than in the browser
-------------------------------------------------------
Four of the five original sites rendered their index from a data.json at
page load and switched language in place with `?lang=`. That is pleasant to
write and bad for everything that matters here: a crawler sees an empty
list, a reader without JavaScript sees nothing, a screen reader announces a
page that is still loading, and the three translations of a page share one
URL so none of them can be linked, shared or indexed.

So every locale gets its own directory and its own finished document, with
the cards, their figures, their numbers, their alt text and the table
behind each plate already in the markup. `/france/` itself is a small
negotiator that sends a reader to the language they asked for. What is
left for the script is only what HTML cannot do: filter, and zoom.

The isolation rule
------------------
A page is written from exactly one `Country`, and every file it reads it
reads through that country's own accessors, which refuse a path outside
`countries/<slug>/`. The only things shared across countries are the
chrome in site/ui.json and the five flags on the front page. Nothing in
this module names a country.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import shutil
import sys
from pathlib import Path

from core import sitebuild, spine
from core.country import COUNTRIES_DIR, ROOT, Country

SITE = ROOT / "site"
ORIGIN = "https://worldreports.io"
REPO = "https://github.com/akitaonrails/worldreports"
GOOGLE_ANALYTICS_ID = "G-7LKE9YHT74"

# The thumbnails are rendered at this size; stating it in the markup lets the
# browser reserve the space before the image arrives, so the cards do not
# jump as the grid fills.
THUMB_W, THUMB_H = 560, 357

# Every full plate is rendered at this size (core.render); stated on the
# og:image so a share preview can lay out before the image arrives.
PLATE_W, PLATE_H = 2720, 1733

FAMILIES = ("money", "world", "people")


def _analytics() -> str:
    """The shared GA4 tag, included once in every HTML document."""
    return f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GOOGLE_ANALYTICS_ID}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag() {{ dataLayer.push(arguments); }}
    gtag('js', new Date());
    gtag('config', '{GOOGLE_ANALYTICS_ID}');
  </script>"""


def e(v) -> str:
    """Escape for an attribute or a text node, quotes included.

    Everything interpolated below is our own, but an alt attribute built by
    concatenation is exactly where a stray apostrophe in a French blurb
    silently truncates the markup.
    """
    return html.escape("" if v is None else str(v), quote=True)


def _provenance_map(country: Country) -> dict:
    """What core.provenance recorded for this country, keyed by plate id."""
    path = country.dir / "provenance.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _ui() -> dict:
    return json.loads((SITE / "ui.json").read_text(encoding="utf-8"))


def _country_ui(country: Country) -> dict:
    path = country.dir / "ui.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


class Chrome:
    """The strings one page is written with, in one language.

    Falls back to the country's default locale and then to English, so a
    language added to a country before its copy is written produces a page
    in the wrong language rather than a page full of holes.
    """

    def __init__(self, country: Country, locale: str, shared: dict,
                 local: dict, n_plates: int, built: str = ""):
        self.country = country
        self.locale = locale
        self.built = built
        self._chain = [locale, country.default_locale, "en"]
        self._shared = shared
        self._local = local
        self._n = n_plates

    def _pick(self, store: dict, key: str):
        for loc in self._chain:
            d = store.get(loc) or {}
            if key in d and d[key] not in (None, ""):
                return d[key]
        return None

    # Copy carries placeholders rather than the facts themselves, so a
    # country that gains a plate or a year does not need its sentences
    # rewritten in three languages. {n} is the plate count, {window} the
    # years the plates span, {year} a figure's own year — filled at the
    # figure, because each one has a different one.
    def fill(self, text: str, **extra) -> str:
        c = self.country
        values = {"n": self._n,
                  "window": f"{c.years[0]}-{c.years[-1]}",
                  "from": c.years[0], "to": c.years[-1],
                  "generated": self.built, "date": self.built,
                  **extra}
        for key, value in values.items():
            text = text.replace("{" + key + "}", str(value))
        return text

    def t(self, key: str, **extra) -> str:
        """A chrome string, with its placeholders filled."""
        v = self._pick(self._shared, key)
        return "" if v is None else self.fill(str(v), **extra)

    def c(self, key: str, default=""):
        """A country string: the masthead line, the dek, the notes."""
        v = self._pick(self._local, key)
        if v is None:
            return default
        if isinstance(v, str):
            return self.fill(v)
        if isinstance(v, list):
            return [self.fill(x) if isinstance(x, str) else x for x in v]
        return v

    def tx(self, value) -> str:
        """A per-locale value out of the chapter data."""
        if isinstance(value, dict):
            for loc in self._chain:
                if value.get(loc):
                    return str(value[loc])
            return next((str(v) for v in value.values() if v), "")
        return "" if value is None else str(value)


# --------------------------------------------------------------- fragments
def css_vars(country: Country) -> str:
    """The country's palette, as the custom properties app.css reads.

    The plates and the page are coloured from the same block in
    country.yaml, which is what keeps a chart and the card around it from
    being two different blues.
    """
    web = dict(getattr(country.palette, "web", None) or {})
    bands = list(getattr(country.palette, "flag_bands", None) or [])
    lines = []
    for key in ("ground", "raised", "raised_2", "rule", "ink", "muted",
                "faint", "money", "world", "people", "paper"):
        if web.get(key):
            lines.append(f"  --{key.replace('_', '-')}: {web[key]};")
    for i, colour in enumerate(bands[:3], start=1):
        lines.append(f"  --flag-{i}: {colour};")
    for key, prop in (("mark_bearing", "--mark-bearing"),
                      ("mark_size", "--mark-size")):
        if web.get(key) is not None:
            lines.append(f"  {prop}: {web[key]};")
    return ":root {\n" + "\n".join(lines) + "\n}"


def _alternates(country: Country, ui: dict, local: dict, n: int) -> str:
    """hreflang for every language this country publishes, plus x-default.

    x-default points at the country's negotiator rather than at one of the
    languages: a reader whose language we do not publish should be offered
    the choice, not silently handed English.
    """
    out = [f'<link rel="alternate" hreflang="x-default" '
           f'href="{ORIGIN}/{country.slug}/">']
    for loc in country.locales:
        out.append(f'<link rel="alternate" hreflang="{e(loc.html_lang)}" '
                   f'href="{ORIGIN}/{country.slug}/{loc.code}/">')
    return "\n  ".join(out)


def _keywords(country: Country, locale: str) -> list[str]:
    """The seo keywords in one language.

    Most countries declare one flat list; a country whose keywords are
    themselves translated (Taiwan's) declares them per locale. Reading a
    dict with `', '.join(...)` joins its keys — "zh-Hant, en, pt" as
    keywords — so the shape is resolved here rather than at each use.
    """
    kw = country.seo.get("keywords")
    if isinstance(kw, dict):
        kw = kw.get(locale) or kw.get(country.default_locale) \
            or next((v for v in kw.values() if v), [])
    return [str(k) for k in (kw or [])]


def _jsonld(country: Country, ch: Chrome, datasets: list[dict]) -> str:
    """A Dataset record, so the page is findable as data and not only as text.

    Every plate on the page is drawn from committed CSVs, and the CSVs are
    in the repository, so the distribution is real and resolvable rather
    than a claim about availability.
    """
    loc = ch.locale
    years = f"{country.years[0]}/{country.years[-1]}"
    publishers = sorted({d["publisher"] for d in datasets if d["publisher"]})
    doc = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": ch.t("doc.title") or ch.tx(country.seo.get("title")),
        "description": ch.tx(country.seo.get("description")),
        "url": f"{ORIGIN}/{country.slug}/{loc}/",
        "inLanguage": country.locale(loc).html_lang,
        "keywords": _keywords(country, loc),
        "temporalCoverage": years,
        "spatialCoverage": country.seo.get("spatial") or ch.tx(country.name),
        "isAccessibleForFree": True,
        "license": "https://github.com/akitaonrails/worldreports/blob/main/LICENSE",
        "creator": {"@type": "Organization", "name": "worldreports.io",
                    "url": ORIGIN},
        "distribution": [{
            "@type": "DataDownload",
            "encodingFormat": "text/csv",
            "contentUrl": f"{REPO}/tree/main/countries/{country.slug}/data",
        }],
        "variableMeasured": [d["title"] or d["file"] for d in datasets][:40],
        "citation": publishers,
    }
    return json.dumps({k: v for k, v in doc.items() if v},
                      ensure_ascii=False, indent=1)


def _ticks(country: Country) -> str:
    bands = list(getattr(country.palette, "flag_bands", None) or [])
    return ('<div class="ticks" aria-hidden="true">'
            + "".join("<i></i>" for _ in bands[:3] or (0, 0, 0))
            + "</div>")


def _atlas(country: Country, ch: Chrome, peers: list[Country]) -> str:
    """The country switcher.

    A reader who is on the French page in Portuguese and clicks Brazil
    wants Brazil in Portuguese. So the link goes to the same language where
    the target country publishes it, and to that country's negotiator where
    it does not — never to a page in a language the reader did not pick.
    """
    items = []
    for peer in peers:
        here = peer.slug == country.slug
        loc = ch.locale if ch.locale in peer.locale_codes else None
        href = f"/{peer.slug}/" + (f"{loc}/" if loc else "")
        current = ' aria-current="true"' if here else ""
        items.append(
            f'      <li><a href="{e(href)}"{current}>'
            f'<span class="atlas__flag" aria-hidden="true">{e(peer.flag_emoji)}</span>'
            f'<span>{e(ch.tx(peer.name))}</span></a></li>')
    return f"""<details class="atlas">
    <summary aria-label="{e(ch.t('country.label'))}">
      <span class="atlas__flag" aria-hidden="true">{e(country.flag_emoji)}</span>
      <span>{e(ch.tx(country.name))}</span>
      <span class="atlas__caret" aria-hidden="true">▾</span>
    </summary>
    <ul class="atlas__menu">
{chr(10).join(items)}
      <li class="atlas__sep" role="presentation"></li>
      <li><a href="/">{e(ch.t('country.all'))}</a></li>
    </ul>
  </details>"""


def _langs(country: Country, ch: Chrome) -> str:
    """Plain links between sibling directories, each named in its own tongue.

    The endonym rather than the language's name in the current language: a
    reader looking for Portuguese is looking for the word "Português",
    whatever language the page they are on happens to be in.
    """
    if len(country.locales) < 2:
        return ""
    out = []
    for loc in country.locales:
        on = loc.code == ch.locale
        cls = "lang__btn is-on" if on else "lang__btn"
        current = ' aria-current="true"' if on else ""
        out.append(f'<a class="{cls}" hreflang="{e(loc.html_lang)}" '
                   f'lang="{e(loc.html_lang)}" href="../{loc.code}/"'
                   f'{current}>{e(loc.endonym)}</a>')
    return (f'<nav class="lang" aria-label="{e(ch.t("lang.label"))}">'
            + "".join(out) + "</nav>")


def _filters(ch: Chrome, families: list[str]) -> str:
    """One chip per theme the country actually uses, plus All.

    A country whose plates are all economic should not be offered a People
    filter that would empty the grid.
    """
    chips = [f'<button type="button" class="chip is-on" data-family="all" '
             f'aria-pressed="true">{e(ch.t("filters.all"))}</button>']
    for fam in FAMILIES:
        if fam not in families:
            continue
        chips.append(
            f'<button type="button" class="chip" data-family="{fam}" '
            f'aria-pressed="false">'
            f'<span class="chip__dot" data-f="{fam}" aria-hidden="true"></span>'
            f'{e(ch.t("filters." + fam))}</button>')
    return (f'<div class="filters" role="group" '
            f'aria-label="{e(ch.t("filters.label"))}">'
            + "".join(chips) + "</div>")


def _label(ch: Chrome, s: dict) -> str:
    """A figure's label, with {year} filled from that figure's own year."""
    return ch.fill(ch.tx(s["label"]), year=s.get("year") or "")


def _asof(ch: Chrome, s: dict) -> str:
    """When a figure is from.

    A level is a current reading and carries no year; a projection says
    so; a cumulative total carries the window it was summed over, because
    it belongs to no single year; everything else is the year's own total.

    Note the `or ""`: a total's `year` key is present and holds None, so
    `.get("year", "")` returns None and the page printed "None · total".
    """
    kind = s.get("asof")
    year = s.get("year") or ""
    if kind == "level":
        return ch.t("card.latest")
    if kind == "projection":
        return f'{year} · {ch.t("card.projected")}'.lstrip(" ·")
    if kind == "total":
        span = s.get("span") or []
        window = f"{span[0]}–{span[1]}" if len(span) == 2 else year
        return f'{window} · {ch.t("card.total")}'.lstrip(" ·")
    return str(year)


def _spark(ch: Chrome, sp: dict) -> str:
    """The card's thumbnail chart, as a path rather than an image.

    Decorative: the same series is in the plate above it and the table
    below it, so it is hidden from assistive technology instead of being
    described twice.
    """
    pts = sp.get("points") or []
    if len(pts) < 2:
        return ""
    w, h = 300, 40
    step = w / (len(pts) - 1)
    d = "".join(f'{"L" if i else "M"}{i * step:.2f} '
                f'{h - v * (h - 2) - 1:.2f}' for i, v in enumerate(pts))
    return f"""<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true">
          <path class="spark__area" d="{d}L{w} {h}L0 {h}Z"></path>
          <path class="spark__line" d="{d}"></path>
        </svg>
        <div class="spark__span"><span>{e(sp.get("from"))}</span><span>{e(sp.get("to"))}</span></div>"""


def _data_table(ch: Chrome, ch_data: dict) -> str:
    """The figures behind one plate, folded away but present in the markup.

    A plate is a picture of a table, and a picture carries no numbers. This
    is how a reader using a screen reader, or checking a figure against the
    source, gets them — so it is a real table in the document, inside a
    <details> that the accessibility tree can still see into, and not
    something the script fetches on demand.
    """
    table = ch_data.get("table")
    if not table or not table.get("rows"):
        return ""
    cols = table["columns"].get(ch.locale) or next(iter(table["columns"].values()))
    head = "".join(f'<th scope="col">{e(c)}</th>' for c in cols)
    body = []
    for row in table["rows"]:
        cells = "".join(
            (f'<th scope="row">{e(v)}</th>' if i == 0 else f"<td>{e(v)}</td>")
            for i, v in enumerate(row))
        body.append(f"<tr>{cells}</tr>")
    csv = table.get("csv", "")
    return f"""<details class="data">
          <summary>{e(ch.t("table.show"))}</summary>
          <div class="tablewrap">
            <table class="t">
              <caption>{e(ch.t("table.caption"))}
                {e(ch.t("table.csv"))}: <code>{e(csv)}</code></caption>
              <thead><tr>{head}</tr></thead>
              <tbody>{"".join(body)}</tbody>
            </table>
          </div>
        </details>"""


def _provenance(ch: Chrome, files: list[str], by_file: dict) -> str:
    """The files one plate was drawn from, with who publishes each.

    Recorded by watching the plate read them rather than written down
    beside it (see core.provenance), so a plate that stops using a file
    stops citing it. This is the part of accessibility that is not about
    markup: a figure a reader cannot see is still checkable if they can see
    which committed file it came from.

    A list rather than a table, because this sits inside a card about a
    third of the page wide: three columns there give one word per line,
    and the filename, its publisher and its years read perfectly well as
    one entry each.
    """
    if not files:
        return ""
    items = []
    for rel in files:
        d = by_file.get(rel, {})
        link = f"{REPO}/blob/main/countries/{ch.country.slug}/data/{rel}"
        meta = " · ".join(x for x in (d.get("publisher"), d.get("coverage")) if x)
        items.append(
            f'<li><a href="{e(link)}"><code>{e(rel)}</code></a>'
            + (f'<span class="src__meta">{e(meta)}</span>' if meta else "")
            + "</li>")
    return f"""<details class="data">
          <summary>{e(ch.t("plate.from"))} · {len(files)}</summary>
          <p class="src__lead">{e(ch.t("plate.from.lead"))}</p>
          <ul class="src">{"".join(items)}</ul>
        </details>"""


def compare_index(countries: list[Country]) -> dict:
    """Which countries publish the same chapter, and where their plate is.

    The comparison control needs to know that France's `01_economy` and
    Argentina's `01-output` are the same chapter of the same atlas. The
    numbering does not say so — the five original projects numbered their
    own plates and Argentina has no `spending` chapter at all — so each
    chapter declares a `topic` from the shared spine and this groups them
    by it.

    Written once for the whole site rather than inlined on every page:
    thirteen pages would otherwise each carry every other country's plate
    list, and the index is only read when a reader actually asks for a
    comparison.

    This is page assembly, not plate rendering. It reads each country
    through its own accessors and writes nothing into any of them; no
    number crosses a border here, only the path to an already-rendered
    image.
    """
    topics: dict[str, list[dict]] = {}
    for c in countries:
        for d in sitebuild.chapters_for(c):
            topic = d.get("topic")
            if not topic:
                continue
            # One entry per locale the country publishes, so the page can
            # prefer the language the reader is already in and fall back
            # to this country's own when it does not publish it.
            plates = {}
            for code in c.locale_codes:
                suffix = "" if code == "en" else f".{code}"
                stem = f"{d['id']}{suffix}"
                # Root-relative, not absolute: the same file has to work
                # on worldreports.io and on whatever port `make serve` is
                # on, and a plate fetched from the live origin while
                # previewing a local build would compare the wrong thing.
                plates[code] = {
                    "thumb": f"/{c.slug}/output/thumbs/{stem}.png",
                    "svg": f"/{c.slug}/output/{stem}.svg",
                    "title": (d["title"] or {}).get(code) or "",
                    "alt": (d.get("alt") or {}).get(code) or "",
                }
                if d.get("stories"):
                    plates[code]["stories"] = _stories_for(d, code)
            topics.setdefault(topic, []).append({
                "slug": c.slug,
                "flag": c.flag_emoji,
                "name": d_name(c),
                "n": d["n"],
                "id": d["id"],
                "default": c.default_locale,
                "locales": list(c.locale_codes),
                "plates": plates,
            })
    for entries in topics.values():
        entries.sort(key=lambda x: x["slug"])
    return {"topics": topics}


def d_name(c: Country) -> dict:
    """A country's name in every language the atlas publishes.

    The comparison menu on a Korean page names France in Korean, so this
    is the whole dict rather than one locale's string.
    """
    return dict(c.name)


def _plate_files(ch_data: dict, locale: str, default: str) -> tuple[str, str, str]:
    """Where this plate's three files are, relative to a locale directory.

    English keeps the plain filename and every other language gets a
    suffix — the same rule `Infographic.save` writes them by — so the page
    and the renderer cannot disagree about which file is which.
    """
    suffix = "" if locale == "en" else f".{locale}"
    stem = f"{ch_data['id']}{suffix}"
    return (f"../output/thumbs/{stem}.png",
            f"../output/{stem}.svg",
            f"../output/{stem}.png")


def _cell(topic: str, key: str) -> list[float]:
    """Where a panel answers a click, as fractions of its plate."""
    order = [s.key for s in spine.slots(topic)]
    return [round(v, 4) for v in spine.panel_cell(order.index(key))]


def _stories_for(ch_data: dict, locale: str) -> dict:
    """One locale's stories for the comparison index: text and cell, by slot.

    The viewer knows only the plate it is showing, so the other country's
    side of a comparison needs its own story and its own cell carried here.
    """
    return {key: {"title": s[locale]["title"],
                  "parts": [{"label": b["head"], "text": b["text"]}
                            for b in s[locale]["beats"]],
                  "cell": _cell(ch_data["topic"], key)}
            for key, s in ch_data["stories"].items() if locale in s}


def _stories(ch: Chrome, d: dict) -> str:
    """What each panel of a plate says, for a reader who is not an expert.

    In the card, in the document, folded away: like the data table it is
    reachable without the script, indexable, and what the viewer's balloon
    reads from. Panels are listed in the spine's reading order, each with
    the cell the viewer treats as that panel.
    """
    stories = d.get("stories")
    if not stories:
        return ""
    items = []
    for slot in spine.slots(d["topic"]):
        s = stories.get(slot.key)
        if not s:
            continue
        cell = ",".join(f"{v:.4f}" for v in _cell(d["topic"], slot.key))
        title = ch.tx({loc: v["title"] for loc, v in s.items()})
        loc = next(l for l in ch._chain if l in s)
        parts = "".join(
            f'<p class="story__part"><strong class="story__label">'
            f'{e(b["head"])}</strong> '
            f'<span class="story__text">{e(b["text"])}</span></p>'
            for b in s[loc]["beats"])
        items.append(
            f'<li class="story" data-slot="{e(slot.key)}" '
            f'data-cell="{cell}">'
            f'<h4 class="story__title">{e(title)}</h4>{parts}</li>')
    return f"""<details class="data stories">
          <summary>{e(ch.t("stories.show"))} · {len(items)}</summary>
          <p class="src__lead">{e(ch.t("stories.lead"))}</p>
          <ol class="story__list">{"".join(items)}</ol>
        </details>"""


def _card(country: Country, ch: Chrome, d: dict, i: int,
          provenance: dict, by_file: dict) -> str:
    title, blurb = ch.tx(d["title"]), ch.tx(d["blurb"])
    alt = ch.tx(d.get("alt")) or f"{title} — {blurb}"
    thumb, svg, png = _plate_files(d, ch.locale, country.default_locale)
    label = f'{ch.t("card.plate")} {d["n"]}'

    stats = "".join(f"""
        <div class="stat">
          <span class="stat__v">{e(ch.tx(s["value"]))}</span>
          <span class="stat__k">{e(_label(ch, s))}
            <span class="stat__y">{e(_asof(ch, s))}</span>
          </span>
        </div>""" for s in d.get("stats", []))

    return f"""<li data-family="{e(d['family'])}" data-id="{e(d['id'])}"
        data-title="{e(title)}" data-alt="{e(alt)}" data-label="{e(label)}"
        data-svg="{e(svg)}" data-topic="{e(d.get('topic', ''))}">
      <article class="card" style="--fam: var(--{e(d['family'])})">
        <a class="figure__open" href="{e(svg)}">
          <img class="card__thumb" src="{e(thumb)}" alt="{e(alt)}"
               width="{THUMB_W}" height="{THUMB_H}"
               loading="{'eager' if i < 2 else 'lazy'}" decoding="async">
        </a>
        <span class="card__n">{e(label)}</span>
        <h3 class="card__title">{e(title)}</h3>
        <p class="card__blurb">{e(blurb)}</p>
        <div class="figure__tools">
          <a href="{e(svg)}">{e(ch.t("view"))}</a>
          <a href="{e(svg)}" download>{e(ch.t("download"))}</a>
          {_data_table(ch, d)}
          {_provenance(ch, provenance.get(d["id"], []), by_file)}
          {_stories(ch, d)}
        </div>
        {_spark(ch, d["spark"]) if d.get("spark") else ""}
        <div class="stats">{stats}</div>
      </article>
    </li>"""


def _headline(ch: Chrome, stats: list[dict]) -> str:
    if not stats:
        return ""
    items = "".join(f"""
      <li class="headline__item">
        <span class="headline__v">{e(ch.tx(s["value"]))}</span>
        <span class="headline__k">{e(_label(ch, s))}</span>
        <span class="headline__y">{e(_asof(ch, s))}</span>
      </li>""" for s in stats)
    return f"""<section class="headline" aria-labelledby="headline-h">
    <h2 class="sr" id="headline-h">{e(ch.t("nav.headline"))}</h2>
    <ul class="headline__list">{items}</ul>
  </section>"""


def _sources(ch: Chrome, datasets: list[dict]) -> str:
    """The provenance table: every file, who publishes it, what it covers.

    Coverage is read from the CSV rather than from the manifest, so this
    table cannot claim a year the data does not contain.
    """
    if not datasets:
        return ""
    rows = []
    for d in datasets:
        kind = (f'<span class="is-official">{e(ch.t("sources.official"))}</span>'
                if d["official"] else
                f'<span class="is-other">{e(ch.t("sources.other"))}</span>')
        pub = e(d["publisher"])
        if d.get("url"):
            pub = f'<a href="{e(d["url"])}">{pub}</a>'
        csv = (f'{REPO}/blob/main/countries/{ch.country.slug}/data/'
               f'{d["file"]}')
        rows.append(
            f'<tr><th scope="row">'
            f'<a href="{e(csv)}"><code>{e(d["file"])}</code></a></th>'
            f'<td>{e(d["title"])}</td><td>{pub}</td>'
            f'<td>{e(d["coverage"])}</td><td>{kind}</td></tr>')
    heads = ("sources.file", "sources.dataset", "sources.publisher",
             "sources.coverage", "sources.kind")
    head = "".join(f'<th scope="col">{e(ch.t(k))}</th>' for k in heads)
    # Folded away by default. This is the longest thing on the page by a
    # wide margin — one row per committed CSV, thirty-odd of them — and it
    # sits between the plates and the colophon, so left open it is a wall
    # of filenames a reader has to scroll past to reach the end of the
    # page. A <details> keeps every row in the DOM and in the
    # accessibility tree, so it is still found by a page search, still
    # read by a screen reader that walks the document, and still indexed.
    return f"""<section id="sources" aria-labelledby="sources-h">
    <h2 id="sources-h">{e(ch.t("sources.title"))}</h2>
    <p class="dek">{e(ch.t("sources.lead"))}</p>
    <details class="sources__all">
      <summary>{e(ch.t("sources.show", n=len(rows)))}</summary>
      <div class="tablewrap tablewrap--tall">
        <table class="t srctable srctable--all">
          <colgroup><col><col><col><col><col></colgroup>
          <thead><tr>{head}</tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>
    </details>
  </section>"""


def _availability(ch: Chrome) -> str:
    """Known country-specific gaps, stated rather than silently omitted.

    The entries live in the country's ``ui.json`` because a blocked portal,
    an unpublished series, and a concept that does not exist are facts about
    that country, not shared site furniture.  The heading and the promise not
    to invent a substitute are shared chrome and therefore translated once in
    ``site/ui.json``.

    ``unavailable`` accepts the same small term/detail shape as ``colophon``.
    Keeping it explicit is deliberate: SOURCES.yaml also records alternative
    mirrors and failed probes that do not leave a hole on a plate, so deriving
    this public list from every ``pending`` note would overstate what is
    actually missing.
    """
    entries = ch.c("unavailable", []) or []
    if not entries:
        return ""
    rows = []
    for item in entries:
        if isinstance(item, str):
            rows.append(f"<li>{e(item)}</li>")
            continue
        term = e(item.get("term", ""))
        detail = e(item.get("detail", ""))
        rows.append(f"<li><strong>{term}</strong><span>{detail}</span></li>")
    return f"""<section class="availability" id="data-gaps"
             aria-labelledby="data-gaps-h">
      <h2 id="data-gaps-h">{e(ch.t("availability.title"))}</h2>
      <p class="dek">{e(ch.t("availability.lead"))}</p>
      <ul class="availability__list">{"".join(rows)}</ul>
    </section>"""


def _colophon(country: Country, ch: Chrome, datasets: list[dict],
              built: str) -> str:
    entries = ch.c("colophon", []) or []
    dl = "".join(f"<dt>{e(x['term'])}</dt><dd>{x['detail']}</dd>"
                 for x in entries)
    notes = "".join(f"<p>{n}</p>" for n in (ch.c("notes", []) or []))
    left = (f'<dl class="sources">{dl}</dl>' if dl else "")
    return f"""<footer class="colophon">
    <h2 class="sr">{e(ch.t("nav.sources"))}</h2>
    {_sources(ch, datasets)}
    <div class="colophon__cols">
      {left}
      <div class="notes">
        {f'<h3>{e(ch.t("notes.title"))}</h3>{notes}' if notes else ''}
        <p class="notes__repo">
          <a href="{REPO}">{e(ch.t("repo"))}</a><br>
          {e(ch.t("generated"))}
        </p>
      </div>
    </div>
    {_availability(ch)}
  </footer>"""


def _ui_json(ch: Chrome) -> str:
    """The few strings the script builds sentences from, in this locale.

    Everything else on the page is translated by the generator and written
    into the HTML. These cannot be: the comparison menu is assembled at
    runtime from countries this page does not otherwise mention.
    """
    keys = ("compare.none", "compare.lang", "compare.loading",
            "compare.hint", "compare.clear",
            "story.kicker", "story.hint", "story.keys")
    return json.dumps({k: ch.t(k) for k in keys}, ensure_ascii=False)


def _viewer(ch: Chrome) -> str:
    """The zoomable plate.

    Written into the page empty rather than created by the script, so its
    labels are translated by the same generator as everything else and the
    dialog cannot appear in the wrong language.
    """
    return f"""<div class="viewer" id="viewer" hidden role="dialog"
       aria-modal="true" aria-labelledby="v-title">
    <div class="viewer__bar">
      <div class="viewer__id">
        <span class="viewer__n" id="v-n"></span>
        <strong class="viewer__title" id="v-title"></strong>
      </div>
      <div class="viewer__tools">
        <details class="cmp__menu" id="v-cmp-menu">
          <summary class="cmp__btn">
            <span class="cmp__ico" aria-hidden="true"></span>
            <span class="cmp__label">{e(ch.t("compare"))}</span>
          </summary>
          <div class="cmp__sheet">
            <p class="cmp__lead">{e(ch.t("compare.with"))}</p>
            <div class="cmp__list"></div>
          </div>
        </details>
        <button type="button" class="tool tool--close" id="v-cmp-off"
                hidden aria-label="{e(ch.t("compare.clear"))}">×</button>
        <button type="button" class="tool" id="v-out"
                aria-label="{e(ch.t("viewer.zoomOut"))}">−</button>
        <button type="button" class="tool tool--wide" id="v-level"
                aria-label="{e(ch.t("viewer.zoomReset"))}">100%</button>
        <button type="button" class="tool" id="v-in"
                aria-label="{e(ch.t("viewer.zoomIn"))}">+</button>
        <a class="tool tool--wide" id="v-dl" href="#"
           aria-label="{e(ch.t("download"))}">SVG</a>
        <button type="button" class="tool tool--close" id="v-close"
                aria-label="{e(ch.t("viewer.close"))}">×</button>
      </div>
    </div>
    <div class="viewer__stage" id="v-stage">
      <img class="viewer__img" id="v-img" alt="">
      <img class="viewer__img viewer__cmp" id="v-cmp" alt="" hidden>
      <div class="hot" id="v-hot" hidden></div>
      <div class="tip" id="v-tip" role="tooltip">
        <strong class="tip__title" id="v-tip-title"></strong>
        <span class="tip__cue">{e(ch.t("story.cue"))}</span>
      </div>
      <div class="read" id="v-read" aria-hidden="true">
        <span class="read__line" id="v-read-line"></span>
        <div class="read__card" id="v-read-card"></div>
      </div>
      <aside class="balloon" id="v-story" hidden role="dialog"
             aria-labelledby="v-story-title">
        <button type="button" class="tool tool--close balloon__close"
                id="v-story-close"
                aria-label="{e(ch.t("story.close"))}">×</button>
        <span class="balloon__from" id="v-story-from"></span>
        <h3 class="balloon__heading" id="v-story-title"></h3>
        <div class="balloon__parts" id="v-story-body"></div>
      </aside>
      <div class="vcmp" id="v-wipe" hidden>
        <span class="vcmp__edge"></span>
        <span class="vcmp__grip" tabindex="0" role="slider"
              aria-label="{e(ch.t("compare.position"))}"
              aria-valuemin="0" aria-valuemax="100" aria-valuenow="50"></span>
        <span class="vcmp__tag vcmp__tag--a" id="v-cmp-a"></span>
        <span class="vcmp__tag vcmp__tag--b" id="v-cmp-b"></span>
      </div>
    </div>
    <div class="viewer__foot">
      <button type="button" class="step" id="v-prev">←&nbsp;{e(ch.t("viewer.prev"))}</button>
      <span class="viewer__hint">{e(ch.t("viewer.hint"))}
        <span id="v-story-hint" hidden>{e(ch.t("story.hint"))}</span></span>
      <button type="button" class="step" id="v-next">{e(ch.t("viewer.next"))}&nbsp;→</button>
    </div>
  </div>"""


# ------------------------------------------------------------------ pages
def country_page(country: Country, locale: str, chapters: list[dict],
                 headline: list[dict], datasets: list[dict],
                 peers: list[Country], shared: dict, local: dict,
                 built: str, provenance: dict) -> str:
    ch = Chrome(country, locale, shared, local, len(chapters), built)
    by_file = {d["file"]: d for d in datasets}
    loc = country.locale(locale)
    families = sorted({c["family"] for c in chapters})
    title = ch.tx(country.seo.get("title")) or ch.tx(country.name)
    desc = ch.tx(country.seo.get("description"))
    cards = "\n    ".join(_card(country, ch, d, i, provenance, by_file)
                          for i, d in enumerate(chapters))
    # The share image is the first plate in the page's own language — a
    # Portuguese page shared into a feed should preview the Portuguese
    # plate, not the English one behind the plain filename.
    suffix = "" if locale == "en" else f".{locale}"
    social = f"{ORIGIN}/{country.slug}/output/{chapters[0]['id']}{suffix}.png" \
        if chapters else ""
    social_alt = ch.tx(chapters[0]["title"]) if chapters else ""
    og_alt_locales = "\n  ".join(
        f'<meta property="og:locale:alternate" content="{e(l.og_locale)}">'
        for l in country.locales if l.code != locale)

    return f"""<!doctype html>
<html lang="{e(loc.html_lang)}" dir="{e(loc.direction)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {_analytics()}
  <title>{e(title)}</title>
  <meta name="description" content="{e(desc)}">
  <meta name="keywords" content="{e(', '.join(_keywords(country, locale)))}">
  <link rel="canonical" href="{ORIGIN}/{country.slug}/{locale}/">
  {_alternates(country, shared, local, len(chapters))}
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="worldreports.io">
  <meta property="og:locale" content="{e(loc.og_locale)}">
  {og_alt_locales}
  <meta property="og:title" content="{e(title)}">
  <meta property="og:description" content="{e(desc)}">
  <meta property="og:url" content="{ORIGIN}/{country.slug}/{locale}/">
  <meta property="og:image" content="{e(social)}">
  <meta property="og:image:type" content="image/png">
  <meta property="og:image:width" content="{PLATE_W}">
  <meta property="og:image:height" content="{PLATE_H}">
  <meta property="og:image:alt" content="{e(social_alt)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{e(title)}">
  <meta name="twitter:description" content="{e(desc)}">
  <meta name="twitter:image" content="{e(social)}">
  <meta name="twitter:image:alt" content="{e(social_alt)}">
  <link rel="icon" href="data:image/svg+xml,{e('<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1 1\"><text y=\".85\" font-size=\"1\">' + country.flag_emoji + '</text></svg>')}">
  <link rel="stylesheet" href="../../assets/app.css">
  <style>{css_vars(country)}</style>
  <script type="application/ld+json">
{_jsonld(country, ch, datasets)}
  </script>
</head>
<body data-slug="{e(country.slug)}" data-loc="{e(ch.locale)}" data-name="{e(ch.tx(country.name) or country.wordmark)}">
  <a class="skip" href="#plates">{e(ch.t("skip"))}</a>

  <header class="masthead">
    <div class="masthead__inner">
      <div class="masthead__top">
        {_ticks(country)}
        <div class="corner">
          {_atlas(country, ch, peers)}
          {_langs(country, ch)}
        </div>
      </div>
      <h1 class="wordmark">{e(country.wordmark)}</h1>
      <p class="masthead__line">{e(ch.c("line"))}</p>
      <p class="dek">{ch.c("dek")}</p>
    </div>
  </header>

  {_headline(ch, headline)}

  <main class="index" id="plates">
    <div class="index__head">
      <h2 class="index__title">{e(ch.t("index.title"))}</h2>
      {_filters(ch, families)}
    </div>
    <ol class="grid">
    {cards}
    </ol>
    <p class="grid__loading" id="grid-empty" hidden>{e(ch.t("filters.none"))}</p>
  </main>

  {_colophon(country, ch, datasets, built)}
  {_viewer(ch)}

  <script>window.UI = {_ui_json(ch)};</script>
  <script src="../../assets/viewer.js"></script>
  <script src="../../assets/app.js"></script>
</body>
</html>
"""


def negotiator(country: Country, shared: dict, local: dict,
               n: int) -> str:
    """`/france/` — a choice of language, not a guess at one.

    It redirects to the language the browser asks for when that is one we
    publish, and otherwise shows the list. Either way the languages are
    real links, so the page works with the script off and a crawler
    following it lands on a real document. It is noindex because the
    document it stands for is the locale page, which carries the canonical.
    """
    ch = Chrome(country, country.default_locale, shared, local, n)
    codes = list(country.locale_codes)
    links = "".join(
        f'<li><a href="{l.code}/" hreflang="{e(l.html_lang)}" '
        f'lang="{e(l.html_lang)}">{e(l.endonym)}</a></li>'
        for l in country.locales)
    return f"""<!doctype html>
<html lang="{e(country.locale(country.default_locale).html_lang)}" dir="{e(country.locale(country.default_locale).direction)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {_analytics()}
  <meta name="robots" content="noindex, follow">
  <title>{e(ch.tx(country.name))} — worldreports.io</title>
  <link rel="canonical" href="{ORIGIN}/{country.slug}/{country.default_locale}/">
  {_alternates(country, shared, local, n)}
  <link rel="stylesheet" href="../assets/app.css">
  <style>{css_vars(country)}</style>
</head>
<body class="home">
  <div class="home__head">
    <p class="home__flag" aria-hidden="true">{e(country.flag_emoji)}</p>
    <h1 class="home__mark">{e(country.wordmark)}</h1>
    <p class="home__dek">{e(ch.t("lang.label"))}</p>
  </div>
  <ul class="home__grid">{links}</ul>
  <p class="home__foot"><a href="/">{e(ch.t("country.all"))}</a></p>
  <script>
    /* The list above is the page; this only saves a click for a reader
       whose browser already said which language they read. */
    (() => {{
      const have = {json.dumps(codes)};
      for (const tag of navigator.languages || [navigator.language || ""]) {{
        const base = String(tag).toLowerCase().split("-")[0];
        const hit = have.find((c) => c === base);
        if (hit) {{ location.replace(hit + "/" + location.hash); return; }}
      }}
      location.replace({json.dumps(country.default_locale)} + "/" + location.hash);
    }})();
  </script>
</body>
</html>
"""


def home(countries: list[Country], shared: dict, built: str) -> str:
    """The front page: five flags and nothing to read before them.

    It is in English with each country named in its own language too, since
    there is no country yet to pick a language from, and every card links
    to that country's negotiator so the reader's own language is honoured
    one click later.
    """
    cards = []
    for c in countries:
        bands = list(getattr(c.palette, "flag_bands", None) or [])[:3]
        strip = "".join(f'<i style="background:{e(b)}"></i>' for b in bands)
        endonyms = ", ".join(l.endonym for l in c.locales)
        # The country's own name beside the English one, where the two
        # differ. Its own name is the one in the language it publishes
        # first — not merely the first non-English name it carries, which
        # for the United States would be the Portuguese exonym, and not
        # the default locale either, which is English everywhere because
        # English is the fallback rather than anyone's first language.
        native = c.name.get(c.locales[0].code)
        also = f" · {e(native)}" if native and native != c.name.get("en") else ""
        cards.append(f"""<li><a class="home__card" href="/{c.slug}/">
      <span class="home__flag" aria-hidden="true">{e(c.flag_emoji)}</span>
      <span class="home__bands" aria-hidden="true">{strip}</span>
      <span class="home__name">{e(c.name.get("en") or c.wordmark)}{also}</span>
      <span class="home__meta">{c.years[0]}–{c.years[-1]} · {e(endonyms)}</span>
    </a></li>""")

    years = (min(c.years[0] for c in countries),
             max(c.years[-1] for c in countries))
    doc = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "worldreports.io",
        "url": ORIGIN + "/",
        "description": "Plates of official statistics, one country at a time, "
                       "built only from committed CSVs.",
        "hasPart": [{"@type": "Dataset",
                     "name": c.name.get("en") or c.wordmark,
                     "url": f"{ORIGIN}/{c.slug}/"} for c in countries],
    }
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {_analytics()}
  <title>worldreports.io — official statistics, country by country</title>
  <meta name="description" content="Data plates on {len(countries)} countries, {years[0]}–{years[1]}, built only from the statistics their own institutions publish and regenerated from committed CSVs.">
  <link rel="canonical" href="{ORIGIN}/">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="en_US">
  <meta property="og:title" content="worldreports.io">
  <meta property="og:description" content="Official statistics, country by country.">
  <meta property="og:url" content="{ORIGIN}/">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="worldreports.io">
  <meta name="twitter:description" content="Official statistics, country by country.">
  <link rel="icon" href="data:image/svg+xml,{e('<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1 1\"><text y=\".85\" font-size=\"1\">🌍</text></svg>')}">
  <link rel="stylesheet" href="assets/app.css">
  <script type="application/ld+json">
{json.dumps(doc, ensure_ascii=False, indent=1)}
  </script>
</head>
<body class="home">
  <header class="home__head">
    <h1 class="home__mark">worldreports.io</h1>
    <p class="home__dek">Plates of official statistics, one country at a
      time. Every figure comes from the institution that publishes it, and
      every chart is regenerated from CSVs committed in the open — so a
      number on a page and the file behind it cannot drift apart.</p>
  </header>
  <ul class="home__grid">
    {chr(10).join(cards)}
  </ul>
  <footer class="home__foot">
    <a href="{REPO}">Data, charts and source on GitHub</a> ·
    built {built}
  </footer>
</body>
</html>
"""


# ------------------------------------------------------------------ build
def _sitemap(countries: list[Country], built: str) -> str:
    urls = [f"  <url><loc>{ORIGIN}/</loc><lastmod>{built}</lastmod>"
            f"<priority>1.0</priority></url>"]
    for c in countries:
        for loc in c.locales:
            alts = "".join(
                f'<xhtml:link rel="alternate" hreflang="{l.html_lang}" '
                f'href="{ORIGIN}/{c.slug}/{l.code}/"/>' for l in c.locales)
            urls.append(
                f"  <url><loc>{ORIGIN}/{c.slug}/{loc.code}/</loc>"
                f"<lastmod>{built}</lastmod><priority>0.8</priority>"
                f'<xhtml:link rel="alternate" hreflang="x-default" '
                f'href="{ORIGIN}/{c.slug}/"/>{alts}</url>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(urls) + "\n</urlset>\n")


def build(out_dir: Path, only: list[str] | None = None) -> list[str]:
    """Write the whole site. Returns the problems found."""
    countries = Country.all()
    wanted = [c for c in countries if not only or c.slug in only]
    shared = _ui()
    built = _dt.date.today().isoformat()
    problems: list[str] = []

    out_dir.mkdir(parents=True, exist_ok=True)
    assets = out_dir / "assets"
    assets.mkdir(exist_ok=True)
    for name in ("app.css", "app.js", "viewer.js"):
        shutil.copy2(SITE / name, assets / name)

    # Every country's plates, grouped by the chapter they belong to. The
    # comparison control fetches this once, on first use.
    (out_dir / "compare.json").write_text(
        json.dumps(compare_index(countries), ensure_ascii=False,
                   separators=(",", ":")),
        encoding="utf-8")

    for country in wanted:
        local = _country_ui(country)
        # Every read below goes through the country's own accessors, so a
        # chapter that reaches for another country's CSV raises rather than
        # quietly publishing the wrong nation's numbers.
        chapters = sitebuild.chapters_for(country)
        headline = sitebuild.headline_for(country)
        datasets = sitebuild.datasets_for(country)
        provenance = _provenance_map(country)
        missing = [d["file"] for d in datasets if not d["present"]]
        if missing:
            problems.append(f"{country.slug}: manifest names {len(missing)} "
                            f"missing file(s): {', '.join(missing[:4])}")

        root = out_dir / country.slug
        root.mkdir(parents=True, exist_ok=True)
        (root / "index.html").write_text(
            negotiator(country, shared, local, len(chapters)),
            encoding="utf-8")

        plates = country.dir / "output"
        if plates.is_dir():
            shutil.copytree(plates, root / "output", dirs_exist_ok=True)
        else:
            problems.append(f"{country.slug}: no rendered plates in output/")

        for loc in country.locales:
            d = root / loc.code
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text(
                country_page(country, loc.code, chapters, headline, datasets,
                             countries, shared, local, built, provenance),
                encoding="utf-8")
        sitebuild.write_data_json(country, chapters, root / "data.json")
        print(f"  {country.slug}: {len(chapters)} plates × "
              f"{len(country.locales)} languages, {len(datasets)} datasets")

    if not only:
        (out_dir / "index.html").write_text(home(countries, shared, built),
                                            encoding="utf-8")
        (out_dir / "CNAME").write_text("worldreports.io\n", encoding="utf-8")
        (out_dir / "sitemap.xml").write_text(_sitemap(countries, built),
                                             encoding="utf-8")
        (out_dir / "robots.txt").write_text(
            f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n",
            encoding="utf-8")
        # GitHub Pages runs Jekyll over the artifact unless told not to, and
        # Jekyll drops files whose names begin with an underscore.
        (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("country", nargs="*", help="slugs; default every country")
    ap.add_argument("--out", default=str(ROOT / "_site"))
    a = ap.parse_args(argv)
    problems = build(Path(a.out), only=a.country or None)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
