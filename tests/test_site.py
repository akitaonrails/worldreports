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

from core import page

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


def test_no_placeholder_survives_into_a_page(site):
    """Copy carries {n}, {window}, {year}; a page must carry none."""
    for path in pages_of(site):
        text = path.read_text(encoding="utf-8")
        left = set(re.findall(r"\{[a-z_]{2,12}\}", text))
        assert not left, f"{path}: unfilled {sorted(left)}"


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
