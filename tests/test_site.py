"""Build the whole site into a temporary directory and read what came out.

The pages are the deliverable. Everything else here is checked as data;
this is the one suite that checks the artifact, because the ways a static
site goes wrong — a link to a plate that was never rendered, an image with
no alt text, a page that claims to be in Korean and is in English — are
invisible to every test that stops at the data.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from core import page, sitebuild, spine

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
# Elements whose end tag HTML lets you leave out.
OPTIONAL_CLOSE = {"li", "p", "td", "th", "tr", "option", "dt", "dd",
                  "thead", "tbody", "colgroup", "col"}


class Doc(HTMLParser):
    """Just enough parsing to ask structural questions of a built page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.open: list[tuple[str, int]] = []
        self.unbalanced: list[str] = []
        self.imgs: list[dict] = []
        self.links: list[str] = []
        self.ids: list[str] = []
        self.headings: list[str] = []
        self.jsonld: list[str] = []
        self.meta: dict[str, str] = {}
        self.alternates: list[tuple[str, str]] = []
        self.html_lang = ""
        self._ld = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in VOID:
            self.open.append((tag, self.getpos()[0]))
        if tag == "html":
            self.html_lang = a.get("lang", "")
        elif tag == "img":
            self.imgs.append({**a, "_line": self.getpos()[0]})
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key] = a.get("content", "")
        elif tag == "link":
            if a.get("rel") == "alternate" and a.get("hreflang"):
                self.alternates.append((a["hreflang"], a.get("href", "")))
            elif a.get("rel") == "canonical":
                self.meta["canonical"] = a.get("href", "")
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._ld = True
        if a.get("id"):
            self.ids.append(a["id"])
        if tag in ("h1", "h2", "h3"):
            self.headings.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "script":
            self._ld = False
        while self.open:
            top, line = self.open.pop()
            if top == tag:
                return
            if top not in OPTIONAL_CLOSE:
                self.unbalanced.append(
                    f"line {self.getpos()[0]}: </{tag}> closes <{top}> "
                    f"opened on line {line}")
                return

    def handle_data(self, data):
        if self._ld and data.strip():
            self.jsonld.append(data)


@pytest.fixture(scope="session")
def site(tmp_path_factory):
    """One build, read by every test below."""
    out = tmp_path_factory.mktemp("site")
    problems = page.build(out)
    assert not problems, "\n".join(problems)
    return out


def pages_of(site: Path, country=None):
    if country is None:
        return sorted(site.rglob("index.html"))
    return sorted((site / country.slug).glob("*/index.html"))


def parse(path: Path) -> Doc:
    d = Doc()
    d.feed(path.read_text(encoding="utf-8"))
    d.close()
    return d


# ------------------------------------------------------------- structure
def test_a_page_exists_for_every_country_and_language(site, country):
    for loc in country.locales:
        assert (site / country.slug / loc.code / "index.html").exists(), \
            f"{country.slug}/{loc.code}: not built"
    assert (site / country.slug / "index.html").exists(), \
        f"{country.slug}: no language negotiator"


def test_every_country_homepage_has_a_summary_strip(site, country):
    """A country may add readings, but it may not silently lose the summary."""
    headline = sitebuild.headline_for(country)
    assert len(headline) >= 6, \
        f"{country.slug}: homepage has only {len(headline)} summary readings"
    for loc in country.locales:
        path = site / country.slug / loc.code / "index.html"
        text = path.read_text(encoding="utf-8")
        assert text.count('<section class="headline"') == 1, \
            f"{country.slug}/{loc.code}: homepage summary strip is missing"
        assert text.count('class="headline__item"') == len(headline), \
            f"{country.slug}/{loc.code}: homepage summary is incomplete"


def test_every_headline_strip_leads_with_gdp_then_population(country):
    """The same three readings, in the same order, on every country page.

    GDP, then GDP per person, then population: a reader moving between
    countries must not have to re-learn where the size of the economy sits.
    Country-specific readings follow, in whatever order that country needs.
    """
    headline = sitebuild.headline_for(country)
    labels = [h["label"]["en"] for h in headline]
    assert labels[0].startswith("GDP"), \
        f"{country.slug}: first reading is {labels[0]!r}, not GDP"
    assert not labels[0].startswith("GDP per person"), \
        f"{country.slug}: the strip leads with GDP per person"
    assert labels[1].startswith("GDP per person"), \
        f"{country.slug}: second reading is {labels[1]!r}"
    assert labels[2].startswith("Population"), \
        f"{country.slug}: third reading is {labels[2]!r}, not population"
    # Population is a level, read at a moment, not a flow that stops early.
    assert headline[2]["value"], f"{country.slug}: population has no value"


def test_the_front_page_links_to_every_country(site, countries):
    doc = parse(site / "index.html")
    for c in countries:
        assert f"/{c.slug}/" in doc.links, f"front page omits {c.slug}"


def test_every_page_is_well_formed(site):
    for path in pages_of(site):
        doc = parse(path)
        assert not doc.unbalanced, f"{path.name}: {doc.unbalanced[:3]}"
        left = [t for t, _ in doc.open if t not in OPTIONAL_CLOSE]
        assert not left, f"{path}: never closed {left}"


def test_google_analytics_is_loaded_once_on_every_page(site):
    measurement_id = page.GOOGLE_ANALYTICS_ID
    loader = ("https://www.googletagmanager.com/gtag/js?id="
              f"{measurement_id}")
    config = f"gtag('config', '{measurement_id}')"
    for path in pages_of(site):
        text = path.read_text(encoding="utf-8")
        assert text.count(loader) == 1, f"{path}: GA4 loader missing or repeated"
        assert text.count(config) == 1, f"{path}: GA4 config missing or repeated"


def test_every_page_has_exactly_one_h1(site):
    for path in pages_of(site):
        doc = parse(path)
        assert doc.headings.count("h1") == 1, \
            f"{path}: {doc.headings.count('h1')} h1 elements"


def test_every_internal_link_resolves(site):
    for path in pages_of(site):
        doc = parse(path)
        for href in doc.links:
            if href.startswith(("http", "mailto:", "#", "data:")):
                continue
            target = (site / href.lstrip("/")) if href.startswith("/") \
                else (path.parent / href)
            if not target.suffix:
                target = target / "index.html"
            assert target.exists(), f"{path}: dead link {href}"


# --------------------------------------------------------- accessibility
def test_every_image_carries_alt_text(site):
    for path in pages_of(site):
        for img in parse(path).imgs:
            assert "alt" in img, f"{path}:{img['_line']}: <img> without alt"


def test_every_plate_thumbnail_describes_its_plate(site, country):
    """Alt text is the whole figure for a reader who cannot see it.

    An empty alt would be correct for decoration and is wrong here: these
    images are the content. A one-word alt is not much better, so this
    insists on a sentence.
    """
    for path in pages_of(site, country):
        for img in parse(path).imgs:
            if "card__thumb" not in img.get("class", ""):
                continue
            alt = img.get("alt", "")
            assert len(alt.split()) >= 5, f"{path}: thin alt {alt!r}"


def test_every_plate_image_reserves_its_space(site, country):
    """Width and height let the browser hold the space before it loads.

    Without them a grid of eleven cards reflows as each thumbnail
    arrives, which on a phone means the thing you were reading moves.
    """
    for path in pages_of(site, country):
        for img in parse(path).imgs:
            if "card__thumb" not in img.get("class", ""):
                continue
            assert img.get("width") and img.get("height"), \
                f"{path}: thumbnail without dimensions"


def test_every_page_starts_with_a_skip_link(site):
    for path in pages_of(site):
        text = path.read_text(encoding="utf-8")
        if "class=\"skip\"" not in text:
            continue     # the negotiator has nothing to skip
        body = text.split("<body", 1)[1]
        assert body.index('class="skip"') < 200, \
            f"{path}: the skip link is not the first thing in the body"


def test_the_plate_data_is_in_the_document(site, country):
    """Not fetched on demand: a disclosure the reader can open is in the
    accessibility tree whether or not it is open, and a fetch is not."""
    for path in pages_of(site, country):
        text = path.read_text(encoding="utf-8")
        assert text.count("<details class=\"data\">") >= 1, \
            f"{path}: no plate carries its data"


# -------------------------------------------------------------- language
def test_each_page_declares_the_language_it_is_in(site, country):
    for loc in country.locales:
        doc = parse(site / country.slug / loc.code / "index.html")
        assert doc.html_lang == loc.html_lang, \
            f"{country.slug}/{loc.code}: <html lang={doc.html_lang!r}>"


def test_each_page_declares_its_writing_direction(site, country):
    for loc in country.locales:
        text = (site / country.slug / loc.code / "index.html") \
            .read_text(encoding="utf-8")
        assert f'<html lang="{loc.html_lang}" dir="{loc.direction}">' in text, \
            f"{country.slug}/{loc.code}: wrong writing direction"


def test_each_page_points_at_every_translation_of_itself(site, country):
    """hreflang is how a search engine knows these are one page in three
    languages rather than three pages competing with each other."""
    want = {l.html_lang for l in country.locales} | {"x-default"}
    for loc in country.locales:
        doc = parse(site / country.slug / loc.code / "index.html")
        assert {h for h, _ in doc.alternates} == want, \
            f"{country.slug}/{loc.code}: alternates {doc.alternates}"


def test_each_page_is_canonical_for_itself(site, country):
    for loc in country.locales:
        doc = parse(site / country.slug / loc.code / "index.html")
        assert doc.meta["canonical"].endswith(f"/{country.slug}/{loc.code}/")


def test_the_negotiator_is_not_indexed(site, country):
    """It stands for the locale pages, which carry the canonical."""
    doc = parse(site / country.slug / "index.html")
    assert "noindex" in doc.meta.get("robots", "")


# The one block on a page that is allowed to carry a placeholder: the
# strings the script composes sentences from at runtime, which the
# generator cannot fill because it does not know which country the reader
# will pick to compare against.
UI_BLOCK = re.compile(r"<script>window\.UI = .*?</script>", re.S)
# What those strings may ask the script for.
SCRIPT_FILLS = {"{lang}", "{n}"}


def test_no_placeholder_survives_into_a_page(site):
    """Copy carries {n}, {window}, {year}; a page must carry none."""
    for path in pages_of(site):
        text = UI_BLOCK.sub("", path.read_text(encoding="utf-8"))
        left = set(re.findall(r"\{[a-z_]{2,12}\}", text))
        assert not left, f"{path}: unfilled {sorted(left)}"


def test_the_script_only_asks_for_placeholders_it_can_fill(site):
    """The runtime strings are exempt from the sweep above, so they get
    their own: a typo there would otherwise ship `{langauge}` to a reader
    with nothing to catch it."""
    for path in pages_of(site):
        for block in UI_BLOCK.findall(path.read_text(encoding="utf-8")):
            left = set(re.findall(r"\{[a-z_]{2,12}\}", block))
            assert left <= SCRIPT_FILLS, \
                f"{path}: window.UI asks for {sorted(left - SCRIPT_FILLS)}"


def test_a_page_is_not_silently_in_the_wrong_language(site, country):
    """Two pages of one country with identical bodies means one of them
    fell back to the other's language instead of being translated."""
    bodies = {}
    for loc in country.locales:
        text = (site / country.slug / loc.code / "index.html") \
            .read_text(encoding="utf-8")
        bodies[loc.code] = text.split("<body", 1)[1]
    seen = {}
    for code, body in bodies.items():
        assert body not in seen, \
            f"{country.slug}: {code} and {seen[body]} are the same page"
        seen[body] = code


# -------------------------------------------------------------------- seo
def test_every_page_describes_itself(site):
    for path in pages_of(site):
        doc = parse(path)
        if "noindex" in doc.meta.get("robots", ""):
            continue
        assert len(doc.meta.get("description", "")) > 60, \
            f"{path}: thin or missing description"
        assert doc.meta.get("og:title"), f"{path}: no og:title"


def test_the_structured_data_is_valid(site):
    for path in pages_of(site):
        for blob in parse(path).jsonld:
            doc = json.loads(blob)       # raises on malformed
            assert doc.get("@context") == "https://schema.org"
            assert doc.get("@type")


def test_the_sitemap_lists_every_published_page(site, countries):
    xml = (site / "sitemap.xml").read_text(encoding="utf-8")
    for c in countries:
        for loc in c.locales:
            assert f"/{c.slug}/{loc.code}/</loc>" in xml, \
                f"sitemap omits {c.slug}/{loc.code}"


def test_the_site_is_served_at_its_own_domain(site):
    assert (site / "CNAME").read_text().strip() == "worldreports.io"
    assert (site / ".nojekyll").exists(), \
        "GitHub Pages would run Jekyll and drop files beginning with _"


def test_unavailable_data_copy_is_rendered_and_escaped(countries):
    """A declared gap is public, localised page copy, never raw HTML."""
    c = countries[0]
    shared = {
        "en": {
            "availability.title": "Data we could not obtain",
            "availability.lead": "Known gaps are listed explicitly.",
        },
        "pt": {
            "availability.title": "Dados que não foi possível obter",
            "availability.lead": "As lacunas conhecidas são declaradas.",
        },
    }
    local = {
        "en": {"unavailable": [
            {"term": "Blocked <portal>",
             "detail": "No reviewed series & no substitute."},
        ]},
        "pt": {"unavailable": [
            {"term": "Portal bloqueado", "detail": "Série indisponível."},
        ]},
    }
    en = page._availability(page.Chrome(c, "en", shared, local, 1))
    pt = page._availability(page.Chrome(c, "pt", shared, local, 1))
    assert 'id="data-gaps"' in en
    assert "Data we could not obtain" in en
    assert "Blocked &lt;portal&gt;" in en
    assert "No reviewed series &amp; no substitute." in en
    assert "Dados que não foi possível obter" in pt
    assert "Portal bloqueado" in pt


def test_a_country_without_declared_gaps_gets_no_empty_section(countries):
    c = countries[0]
    ch = page.Chrome(c, "en", {"en": {}}, {"en": {}}, 1)
    assert page._availability(ch) == ""


def test_unavailable_data_heading_exists_in_every_published_language(countries):
    shared = page._ui()
    codes = {loc.code for c in countries for loc in c.locales}
    for code in codes:
        assert shared.get(code, {}).get("availability.title"), code
        assert shared.get(code, {}).get("availability.lead"), code


# ------------------------------------------------------------- the plates
def test_every_card_links_to_a_plate_that_exists(site, country):
    for loc in country.locales:
        path = site / country.slug / loc.code / "index.html"
        doc = parse(path)
        plates = [h for h in doc.links if "/output/" in h]
        assert plates, f"{country.slug}/{loc.code}: no plate links"
        for href in plates:
            assert (path.parent / href).exists(), f"{path}: missing {href}"


def test_every_plate_has_a_thumbnail_in_every_language(site, country):
    for loc in country.locales:
        path = site / country.slug / loc.code / "index.html"
        for img in parse(path).imgs:
            src = img.get("src", "")
            if "thumbs/" not in src:
                continue
            assert (path.parent / src).exists(), f"{path}: missing {src}"


def test_thumbnails_stay_small_enough_to_put_ten_on_one_page(site, country):
    """A full plate is ~300KB. Eleven of those above the fold is a page
    that does not load on a phone, which is why the cards show copies."""
    thumbs = list((site / country.slug / "output" / "thumbs").glob("*.png"))
    assert thumbs, f"{country.slug}: no thumbnails"
    biggest = max(thumbs, key=lambda p: p.stat().st_size)
    assert biggest.stat().st_size < 120_000, \
        f"{country.slug}: {biggest.name} is {biggest.stat().st_size // 1024}KB"


# ----------------------------------------------- the committed artifacts
def test_every_chapter_has_a_committed_plate_in_every_language(country):
    """The plates are committed, and the pages link to the committed files.

    So a chapter whose plate was never rendered, or rendered before a
    language was added, is a broken image on a published page. Checked
    against the repository rather than against the build, because that is
    what gets served.
    """
    from core import sitebuild

    out = country.out_dir
    missing = []
    for ch in sitebuild.chapters_for(country):
        for code in country.locale_codes:
            suffix = "" if code == "en" else f".{code}"
            for rel in (f"{ch['id']}{suffix}.png", f"{ch['id']}{suffix}.svg",
                        f"thumbs/{ch['id']}{suffix}.png"):
                if not (out / rel).exists():
                    missing.append(rel)
    assert not missing, (f"{country.slug}: {len(missing)} missing: "
                         f"{missing[:6]} — run `make C={country.slug} charts "
                         f"thumbs`")


def test_no_plate_is_left_over_from_a_chapter_that_is_gone(country):
    """A renamed plate leaves its old file behind, and nothing links to it.

    It then ships as a file the site serves, the sitemap does not list and
    no page mentions — which is how a stale figure outlives the data it
    was drawn from.
    """
    from core import sitebuild

    ids = {ch["id"] for ch in sitebuild.chapters_for(country)}
    stray = []
    for path in country.out_dir.rglob("*.png"):
        stem = path.stem.split(".")[0]
        if stem not in ids:
            stray.append(str(path.relative_to(country.out_dir)))
    assert not stray, f"{country.slug}: {len(stray)} orphaned: {stray[:6]}"


# ------------------------------------------------------------- comparison
#
# The comparison control puts one country's plate on top of another's. That
# only means anything if the two really are the same chapter, and the plate
# numbering does not say so: France's `01_economy` and Argentina's
# `01-output` are the same chapter, Argentina has no `spending` chapter at
# all, and Brazil numbers trade sixth where France numbers it fourth. The
# `topic` each chapter declares is what makes them comparable, so it is
# what these tests are about.

# The spine, from SOURCING_A_COUNTRY.md. A country may leave a chapter out;
# it may not invent a topic, because a topic nothing else shares is a
# comparison that can never be offered.
SPINE = {
    "economy", "prices", "fiscal", "spending", "trade", "markets",
    "people", "world", "demography", "security", "mortality", "credit",
    "migration",
}


def test_every_chapter_declares_a_topic(country):
    for d in sitebuild.chapters_for(country):
        assert d.get("topic"), f"{country.slug}/{d['id']}: no topic"


def test_every_topic_is_one_of_the_spine(country):
    for d in sitebuild.chapters_for(country):
        assert d["topic"] in SPINE, \
            f"{country.slug}/{d['id']}: topic {d['topic']!r} is not in the spine"


def test_a_country_never_declares_one_topic_twice(country):
    """Two chapters on one topic make the comparison ambiguous: the menu
    would offer the country once and show whichever plate sorted first."""
    seen = {}
    for d in sitebuild.chapters_for(country):
        assert d["topic"] not in seen, (
            f"{country.slug}: {d['id']} and {seen[d['topic']]} both claim "
            f"topic {d['topic']!r}")
        seen[d["topic"]] = d["id"]


def test_the_comparison_index_points_at_plates_that_exist(countries):
    """Every path in compare.json resolves to a committed file.

    The index is built from chapter ids and locale codes rather than by
    listing the directory, so a chapter renamed without its plate being
    re-rendered would publish a comparison that 404s. Nothing on the page
    would say so — the seam would just wipe onto nothing.
    """
    index = page.compare_index(countries)
    by_slug = {c.slug: c for c in countries}
    missing = []
    for topic, entries in index["topics"].items():
        for entry in entries:
            out = by_slug[entry["slug"]].dir / "output"
            for loc, plate in entry["plates"].items():
                for key in ("thumb", "svg"):
                    rel = plate[key].split(f'/{entry["slug"]}/output/')[-1]
                    if not (out / rel).exists():
                        missing.append(f'{entry["slug"]}/{loc}/{key}: {rel}')
    assert not missing, "comparison points at absent plates:\n  " + \
        "\n  ".join(missing[:10])


def test_the_comparison_index_offers_a_peer_for_the_shared_chapters(countries):
    """The point of the feature is that the common chapters are common.

    Not every topic is shared — Argentina is the only country with a
    `prices` chapter, because it is the only one whose price index has a
    decade missing from it — but the spine ones are, and a refactor that
    quietly broke the topic tagging would show up here as chapters that
    suddenly have nobody to compare with.
    """
    index = page.compare_index(countries)
    shared = {t for t, e in index["topics"].items() if len(e) > 1}
    assert {"economy", "fiscal", "trade", "markets", "people",
            "demography", "security", "credit"} <= shared, \
        f"expected the spine to be shared; shared topics are {sorted(shared)}"


def test_the_comparison_names_every_country_in_every_language(countries):
    """The menu on a Korean page names France in Korean."""
    index = page.compare_index(countries)
    locales = {loc for c in countries for loc in c.locale_codes}
    for entries in index["topics"].values():
        for entry in entries:
            missing = [l for l in locales if not entry["name"].get(l)]
            assert not missing, \
                f'{entry["slug"]}: no name in {missing}'


def test_the_comparison_control_is_in_the_viewer_on_every_page(site):
    """One control, in one place, on all thirteen pages.

    The comparison belongs to the full-screen viewer. The seam only
    means anything at a size where the panels can be read, and on a card
    the plate is 400px wide. The control was briefly on the cards and it
    was two unreadable thumbnails with a line between them.

    Every page gets it because every page is built by the same function;
    this is the test that says so, and it is the one that fails if a
    country is ever given a hand-written page of its own.
    """
    for path in pages_of(site):
        text = path.read_text(encoding="utf-8")
        if "<body" not in text or 'id="viewer"' not in text:
            continue     # the front page and the negotiators have no viewer
        bar, grid = text.split('id="viewer"', 1)[1], text.split('id="viewer"', 1)[0]
        assert 'id="v-cmp-menu"' in bar, f"{path}: the viewer has no comparison"
        assert 'id="v-cmp-off"' in bar, f"{path}: nothing clears the comparison"
        assert 'class="vcmp"' in bar, f"{path}: the viewer has no seam"
        assert "cmp__" not in grid, \
            f"{path}: a comparison control leaked back onto the grid"


def test_every_card_carries_the_topic_the_comparison_matches_on(site, country):
    """The viewer reads the topic off the card it was opened from, so a
    card without one silently offers no peers at all."""
    for path in pages_of(site, country):
        text = path.read_text(encoding="utf-8")
        cards = text.count("<article class=\"card\"")
        assert text.count("data-topic=") >= cards, \
            f"{path}: {cards} cards but only {text.count('data-topic=')} topics"
        assert 'data-topic=""' not in text, f"{path}: a card has an empty topic"


def test_each_page_tells_the_script_which_locale_it_is(site, country):
    """`<html lang>` is a language tag and carries a region — es-AR,
    pt-BR — and will carry a script before this atlas is finished. The
    comparison index is keyed by the bare locale code, so the page states
    that code outright rather than leaving the script to lop a tag apart.
    Reading the tag is how the menu came to name France "France" on a
    Spanish page: `es-AR` matched nothing and it fell through to English.
    """
    for loc in country.locales:
        text = (site / country.slug / loc.code / "index.html") \
            .read_text(encoding="utf-8")
        assert f'data-loc="{loc.code}"' in text, \
            f"{country.slug}/{loc.code}: the body does not declare its locale"


# --------------------------------------------------------------- stories
def _with_stories(country):
    return [d for d in sitebuild.chapters_for(country) if d.get("stories")]


def _card_of(text: str, chapter_id: str) -> str:
    """The markup of one chapter's card."""
    start = text.index(f'data-id="{chapter_id}"')
    return text[start:text.index("</article>", start)]


def test_a_card_carries_the_stories_of_its_panels(site, country):
    """The viewer reads the stories from the card, so the page works — and
    can be read — without the script."""
    from html import escape
    for d in _with_stories(country):
        order = [s.key for s in spine.slots(d["topic"])]
        for loc in country.locales:
            text = (site / country.slug / loc.code / "index.html"
                    ).read_text(encoding="utf-8")
            card = _card_of(text, d["id"])
            assert card.count('<li class="story"') == len(d["stories"])
            for key, story in d["stories"].items():
                cell = ",".join(f"{v:.4f}" for v in
                                spine.panel_cell(order.index(key)))
                assert (f'data-slot="{key}" data-cell="{cell}"') in card, \
                    f"{country.slug}/{loc.code}/{key}: no card entry"
                told = story[loc.code]
                wanted = [told["title"]] + [x for b in told["beats"]
                                            for x in (b["head"], b["text"])]
                for text in wanted:
                    assert escape(text, quote=True) in card, \
                        f"{country.slug}/{loc.code}/{key}: {text[:30]!r} missing"
            assert card.count('class="story__part"') == \
                sum(len(s[loc.code]["beats"]) for s in d["stories"].values())


def test_only_a_chapter_with_stories_gets_a_story_section(site, country):
    for loc in country.locales:
        text = (site / country.slug / loc.code / "index.html"
                ).read_text(encoding="utf-8")
        assert text.count('class="data stories"') == \
            len(_with_stories(country)), \
            f"{country.slug}/{loc.code}: story sections out of step"


def test_the_viewer_has_a_place_for_the_story(site):
    for path in sorted(site.glob("*/*/index.html")):
        text = path.read_text(encoding="utf-8")
        assert 'id="v-story"' in text, f"{path}: the viewer has no story"
        assert 'id="v-story-close"' in text, f"{path}: nothing closes it"
        assert 'id="v-tip"' in text, f"{path}: no hover card"
        assert 'id="v-read"' in text, f"{path}: no readout for the isolated chart"
        for key in ("story.kicker", "story.hint", "story.keys"):
            assert f'"{key}"' in text, f"{path}: the script is not given {key}"


def test_the_comparison_index_carries_each_countrys_own_stories(countries):
    """A reader comparing with Brazil clicks Brazil's side and gets
    Brazil's story, so the index has to carry it — and only where a
    country wrote one."""
    index = page.compare_index(countries)
    by_slug = {c.slug: c for c in countries}
    for entries in index["topics"].values():
        for entry in entries:
            country = by_slug[entry["slug"]]
            written = {d["id"]: d for d in _with_stories(country)}
            for loc, plate in entry["plates"].items():
                if entry["id"] not in written:
                    assert "stories" not in plate, \
                        f'{entry["slug"]}/{entry["id"]}: stories from nowhere'
                    continue
                d = written[entry["id"]]
                assert set(plate["stories"]) == set(d["stories"])
                for key, got in plate["stories"].items():
                    told = d["stories"][key][loc]
                    assert got["title"] == told["title"]
                    assert [(p["label"], p["text"]) for p in got["parts"]] == \
                        [(b["head"], b["text"]) for b in told["beats"]]
                    assert len(got["cell"]) == 4
