"""The shared code must not know which countries exist.

Five atlases were merged by moving everything they had in common into
`core/`. That only stays true if `core/` never learns a country's name: the
moment it does, adding a sixth country means editing shared code, and the
five that already work become five things that can break.

So this reads the shared code and fails on a country's name in it, and
reads each country's declaration and fails on anything the shared code
would need special-cased.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

from core import style
from core.country import COUNTRIES_DIR, Country
from core.sitebuild import AFFIX, CURRENCY_AFFIX, NUMFMT

ROOT = Path(__file__).resolve().parent.parent
SHARED = sorted((ROOT / "core").glob("*.py")) + [ROOT / "site" / "app.js",
                                                 ROOT / "site" / "app.css"]

# Words that would mean the shared code is thinking about one country.
# Slugs and wordmarks, plus the institutions and currencies each atlas
# names, since "INSEE" in core/ is the same mistake as "france".
FORBIDDEN = {
    "france", "brasil", "brazil", "argentina", "south-korea", "korea",
    "insee", "eurostat", "ibge", "indec", "bcra", "kostat", "bok",
    "banco central", "banque de france", "real", "peso", "won",
    "euro", "tricolore", "merval", "ibovespa", "kospi",
}
# Words that are legitimately in the shared code for other reasons.
ALLOWED_CONTEXT = re.compile(r"euro(pean|zone)|\.eur\b|EUR|real[ _-]?(growth|terms|gdp)",
                             re.I)


def _searchable(path: Path) -> str:
    """The file's text with its explanatory prose removed.

    A comment may name a country to explain why a rule exists — that is
    documentation, not a dependency. Code that names one is the problem.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".py":
        tree = ast.parse(text)
        docstrings = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc:
                    docstrings.append(doc)
        lines = [ln for ln in text.splitlines()
                 if not ln.lstrip().startswith("#")]
        text = "\n".join(lines)
        for doc in docstrings:
            text = text.replace(doc, "")
        return text
    # js/css: strip // and /* */ comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"^\s*//.*$", "", text, flags=re.M)


@pytest.mark.parametrize("path", SHARED, ids=lambda p: p.name)
def test_shared_code_names_no_country(path):
    body = _searchable(path)
    hits = []
    for word in FORBIDDEN:
        for m in re.finditer(rf"\b{re.escape(word)}\b", body, re.I):
            line = body[:m.start()].count("\n") + 1
            context = body.splitlines()[line - 1]
            if ALLOWED_CONTEXT.search(context):
                continue
            hits.append(f"line {line}: {context.strip()[:90]}")
    assert not hits, (f"{path.name} names a country in code:\n  "
                      + "\n  ".join(dict.fromkeys(hits)))


# A country branch checkout leaves gitignored leftovers (cache/,
# __pycache__/) behind in a directory whose tracked files belong to another
# branch. A directory holding nothing else is a checkout artefact, not a
# country, and must not trip the declaration check.
_LEFTOVER_DIRS = {"cache", "__pycache__"}


def _has_country_content(d: Path) -> bool:
    return any(f.is_file()
               and not (_LEFTOVER_DIRS & set(f.relative_to(d).parts[:-1]))
               for f in d.rglob("*"))


def test_every_country_directory_declares_itself():
    """A directory under countries/ without a country.yaml is invisible."""
    dirs = {p.name for p in COUNTRIES_DIR.iterdir()
            if p.is_dir() and not p.name.startswith((".", "__"))
            and _has_country_content(p)}
    declared = {c.slug for c in Country.all()}
    assert dirs == declared, f"undeclared: {sorted(dirs - declared)}"


def test_the_slug_matches_the_directory(country):
    assert country.slug == country.dir.name


def test_locales_are_distinct_and_include_the_default(country):
    codes = list(country.locale_codes)
    assert len(codes) == len(set(codes))
    assert country.default_locale in codes
    for loc in country.locales:
        assert loc.endonym, f"{country.slug}/{loc.code}: no endonym"
        assert loc.html_lang, f"{country.slug}/{loc.code}: no html_lang"


def test_every_locale_can_be_formatted(country):
    """The site formats numbers per language; a locale it cannot is a bug.

    Not every language changes the separators — Korean keeps the English
    ones — but every language must be known to the units table, or a plate
    would publish "bn" to a reader who does not read English.
    """
    styles = [country.number_style(c) for c in country.locale_codes]
    for spec, per_locale in AFFIX.items():
        missing = [c for c in styles if c not in per_locale]
        assert not missing, \
            f"{country.slug}: spec {spec!r} has no form for {missing}"
    for spec, per_locale in NUMFMT.items():
        assert callable(per_locale) or isinstance(per_locale, str), spec


def test_the_currency_is_one_the_site_can_write(country):
    code = country.currency.get("code") if isinstance(country.currency, dict) \
        else country.currency
    assert code in CURRENCY_AFFIX, \
        f"{country.slug}: currency {code!r} has no per-language form"


def test_the_palette_fills_every_slot_the_plates_need(country):
    p = country.palette
    for slot in ("ink", "muted", "faint", "paper", "card", "grid", "spine",
                 "band", "primary", "alert", "series"):
        assert getattr(p, slot, None), f"{country.slug}: palette.{slot} unset"
    assert len(p.series) >= 3, f"{country.slug}: fewer than three series colours"


def test_the_palette_fills_every_slot_the_page_needs(country):
    """The page reads the same palette the plates are drawn with."""
    web = getattr(country.palette, "web", None) or {}
    for slot in ("ground", "raised", "raised_2", "rule", "ink", "muted",
                 "faint", "money", "world", "people"):
        assert web.get(slot), f"{country.slug}: palette.web.{slot} unset"
    bands = getattr(country.palette, "flag_bands", None) or []
    assert len(bands) == 3, f"{country.slug}: wanted three flag bands"


@pytest.mark.parametrize("key", ["ground", "raised", "rule", "ink", "muted",
                                 "faint", "money", "world", "people"])
def test_web_colours_are_hex(country, key):
    value = (getattr(country.palette, "web", None) or {}).get(key, "")
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", str(value)), \
        f"{country.slug}: palette.web.{key} = {value!r}"


def test_years_are_a_contiguous_span(country):
    years = list(country.years)
    assert years == list(range(years[0], years[-1] + 1))
    assert years[0] <= country.last_full_year <= years[-1]


def test_seo_is_written_in_every_locale(country):
    for field in ("title", "description"):
        value = country.seo.get(field) or {}
        missing = [c for c in country.locale_codes if not value.get(c)]
        assert not missing, f"{country.slug}: seo.{field} missing {missing}"
    assert country.seo.get("keywords"), f"{country.slug}: no seo keywords"


def test_headroom_only_ever_grows_the_axis(country):
    """Room for an annotation above a series must not crop the series.

    `headroom` exists so a value label has somewhere to sit; an
    implementation that set the limits rather than widening them would
    silently cut the peak it was making room for.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from core import context

    ctx = context.Context(country)
    fig = ctx.fig("t", "s")
    ax = fig.next_panel("panel")
    ax.set_ylim(0, 10)
    fig.headroom(ax, top=0.5, bottom=0.1)
    low, high = ax.get_ylim()
    assert high > 10 and low < 0
    plt.close(fig.fig)


def test_a_script_that_needs_a_font_says_which(country):
    """A language whose script no installed font covers must be declared.

    Korean plates drawn with a Latin-only font come out as rows of empty
    boxes, and nothing raises. The build refuses instead — but only for
    languages the font table knows about, so the table has to know about
    every script published here.
    """
    for code in country.locale_codes:
        assert style.has_script_font(code), (
            f"{country.slug}/{code}: no installed font can render this "
            f"language; install the font before rendering")
