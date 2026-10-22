"""Each country's translation catalog, and the engine that applies it.

A plate half in English is worse than a plate plainly in English: the
reader cannot tell which half was translated and which was forgotten. The
renderer already fails the build on an untranslated string, so what is
left to test here is the catalog's own hygiene — entries that are blank,
keys with stray whitespace, and translations that kept the English digit
grouping and so publish 1,234 to a reader who reads 1.234.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

from core import i18n


def catalog(country) -> dict:
    return json.loads((country.dir / "i18n.json").read_text(encoding="utf-8"))


def test_the_catalog_parses_and_is_not_empty(country):
    assert catalog(country), f"{country.slug}: empty catalog"


def test_english_is_the_source_and_needs_no_entries(country):
    for key, value in catalog(country).items():
        assert "en" not in value, \
            f"{country.slug}: {key!r} carries an English 'translation'"


def test_no_entry_is_blank(country):
    """A blank translation renders as a blank label, not as the English."""
    for key, value in catalog(country).items():
        for lang, text in value.items():
            assert str(text).strip(), f"{country.slug}: {key!r}/{lang} is blank"


def test_keys_are_stripped(country):
    """A key with a stray space never matches the string on the figure."""
    for key in catalog(country):
        assert key == key.strip(), f"{country.slug}: {key!r} has edge space"


def test_no_translation_keeps_the_english_number_verbatim(country):
    """1,234 means one thousand in English and one-point-two in French.

    This cannot be judged from the translation alone: "0,467" is a correct
    Spanish decimal and "1,234" is an uncorrected English thousand, and
    the two look the same. So it is judged against the key — the English
    the translator was given — and only for comma-grouped thousands, which
    nothing but an English number is ever spelled as.

    A lone "3.2" is deliberately not checked. It is as likely to be the
    name of a thing as a quantity ("OMB Historical Tables 3.2"), and the
    cost of the two mistakes is not comparable: a decimal point left
    alone reads oddly, a thousands comma left alone reads as a number a
    thousand times smaller.
    """
    grouped = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")
    for key, value in catalog(country).items():
        english = set(grouped.findall(key))
        if not english:
            continue
        for lang, text in value.items():
            if lang not in i18n._SEPARATORS:
                continue      # Korean keeps the English separators
            kept = {n for n in grouped.findall(str(text)) if n in english}
            assert not kept, (
                f"{country.slug}: {key[:50]!r}/{lang} kept {sorted(kept)} "
                f"with English thousands separators")


def test_every_string_the_plates_emit_has_a_translation(country):
    """The authoritative check: draw everything, in every language.

    A catalog can be complete against itself and still miss the one label
    a plate builds at draw time. The only way to know is to draw the
    plates and see what came out untranslated — which is what the renderer
    does, and what this asserts it finds nothing of.

    It is slow, because it really renders every plate in every language.
    It is also the test that would have caught every translation gap the
    five projects ever shipped.
    """
    import tempfile

    from core.render import render_country

    with tempfile.TemporaryDirectory() as tmp:
        problems = render_country(country, out_dir=pathlib.Path(tmp),
                                  strict=True)
    assert not problems, (f"{country.slug}:\n  " + "\n  ".join(problems))


# ------------------------------------------------------------- the engine
@pytest.fixture
def bound(country):
    i18n.bind(country)
    yield i18n
    i18n.set_lang("en")


def test_an_unknown_language_is_refused_at_the_door(bound, country):
    with pytest.raises(Exception):
        bound.set_lang("xx")


def test_english_passes_everything_through_untouched(bound):
    bound.set_lang("en")
    for s in ("GDP, US$ bn", "1,234.5", "12.3%", "2006-2026"):
        assert bound.translate(s) == s


def test_a_pure_number_needs_no_catalog_entry(bound, country):
    """Tick labels are numbers; demanding a translation for each is noise."""
    for lang in country.locale_codes:
        bound.set_lang(lang)
        bound.reset_missing()
        for s in ("2006", "1,234", "12.3", "-4.5", "0"):
            bound.translate(s)
        assert not bound.missing(), f"{lang}: {bound.missing()}"


def test_a_missing_string_is_recorded_not_guessed(bound, country):
    langs = [l for l in country.locale_codes if l != "en"]
    if not langs:
        pytest.skip("publishes English only")
    bound.set_lang(langs[0])
    bound.reset_missing()
    phrase = "a label that is certainly not in any catalog here"
    assert bound.translate(phrase) == phrase
    assert phrase in bound.missing()


def test_localizing_twice_is_a_no_op(country):
    """savefig redraws, so localize() runs again on an already-translated
    figure. Separators swapped a second time would turn 1 234,5 into
    something else entirely."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    langs = [l for l in country.locale_codes if l in i18n._SEPARATORS]
    if not langs:
        pytest.skip("no language here changes separators")
    i18n.bind(country)
    i18n.set_lang(langs[0])
    fig = plt.figure()
    t = fig.text(0.1, 0.1, "1,234.5")
    i18n.localize(fig)
    once = t.get_text()
    i18n.localize(fig)
    assert t.get_text() == once
    plt.close(fig)
    i18n.set_lang("en")
