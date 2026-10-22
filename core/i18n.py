"""Plates, translated at save time.

Each country's chart script builds every figure in English. Just before it is
written, `localize()` walks every piece of text matplotlib holds — titles,
panel headings, annotations, legend entries, tick labels, the source line —
and rewrites it. One hook instead of several hundred wrapped string literals,
and nothing can be missed by accident: `missing()` reports every string that
was rendered with no translation, and `make charts` fails on a non-empty
list.

Numbers are rewritten too, because the readerships do not write them the
same way:

    en   €2,991bn      1,234.5      44,000
    fr   2 991 Md€     1 234,5      44 000
    pt   € 2.991 bi    1.234,5      44.000
    es   US$ 684bn     1.234,5      44.000
    ko   684십억 달러   1,234.5      44,000

French moves the currency mark to the end and Korean appends the magnitude
word, which is why the unit rules are substitutions rather than a suffix
table. Korean keeps the English separators, so it has no separator entry at
all — swapping them there would be wrong, not merely unnecessary.

The rules below are keyed by *language*, because that is what they describe:
Portuguese writes 1.234,5 whether the subject is Brazil or Korea. The
catalogs are keyed by *country*, because that is what they describe: only
the Argentine plates ever say "country risk, EMBI+".
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib.text as mtext
import matplotlib.ticker as mticker

LANG = "en"
_COUNTRY = None
_missing: set[str] = set()

# French thousands separator. A no-break space, not U+202F (narrow no-break
# space): the fonts the plates fall back to do not all carry U+202F, and a
# missing glyph renders as a tofu box in the middle of every large number.
NBSP = " "


# --------------------------------------------------------------- numbers
# A number as matplotlib renders it: optional thousands groups, optional
# decimals. Years (2006) and ranges (2006-2026) have neither, so they are
# never matched and cannot be mangled into "2 006".
_NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+")

# Used only to abstract a string into a catalog key, never to rewrite one.
# A year on its own, and then any number a sentence might carry including a
# decimal or a thousands group: 2019, 2.5, 385,676.
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_ANY_NUMBER = re.compile(r"-?\d[\d.,]*")
# The positional form Argentina's catalog uses abstracts every number; the
# brace form Brazil's and the USA's use tries years first, so a key that
# varies only by year stays readable in the catalog.
_LOOSE_NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")

_SEPARATORS = {
    "fr": {",": NBSP, ".": ","},
    "pt": {",": ".", ".": ","},
    "es": {",": ".", ".": ","},
    # ko: intentionally absent. Korean uses the English separators.
}

# Unit and currency rules, applied BEFORE the separators are swapped, so the
# digit groups are still in their English form and `[\d,.]` is enough to
# match them. Order matters: the suffixed forms have to be tried before the
# bare currency rule, or "€2,991bn" loses its "bn".
_UNITS = {
    "fr": [
        (re.compile(r"€\s*([\d,.]+)\s*tn\b"), rf"\1{NBSP}B€"),
        (re.compile(r"€\s*([\d,.]+)\s*bn\b"), rf"\1{NBSP}Md€"),
        (re.compile(r"€\s*([\d,.]+)\s*mn\b"), rf"\1{NBSP}M€"),
        (re.compile(r"€\s*([\d,.]+)"), rf"\1{NBSP}€"),
        (re.compile(r"US\$\s*([\d,.]+)\s*tn\b"), rf"\1{NBSP}B$US"),
        (re.compile(r"US\$\s*([\d,.]+)\s*bn\b"), rf"\1{NBSP}Md$US"),
        (re.compile(r"US\$\s*([\d,.]+)"), rf"\1{NBSP}$US"),
        (re.compile(r"/100k\b"), "/100 000 hab."),
        (re.compile(r"(?<=\d)pp\b"), f"{NBSP}pt"),
        (re.compile(r"(?<=\d)M\b"), f"{NBSP}M"),
    ],
    # Portuguese: 'bi' is 10^9 and 'tri' is 10^12, so the magnitude word maps
    # one-for-one onto the English token and the digits never move.
    "pt": [
        (re.compile(r"(?<=\d)\s*tn\b"), " tri"),
        (re.compile(r"(?<=\d)\s*bn\b"), " bi"),
        (re.compile(r"(?<=\d)\s*mn\b"), " mi"),
        (re.compile(r"€\s*(?=[\d,.])"), "€ "),
        (re.compile(r"/100k\b"), "/100 mil"),
        (re.compile(r"(?<=\d)pp\b"), " p.p."),
        (re.compile(r"(?<=\d)M\b"), " mi"),
    ],
    # Spanish leaves the magnitudes in their English form, as the Argentine
    # plates always have: 'mil millones' does not fit an axis label, and the
    # few places the words are spelled out have catalog entries of their own.
    "es": [
        (re.compile(r"/100k\b"), "/100 mil"),
        (re.compile(r"(?<=\d)pp\b"), " p.p."),
    ],
    # Korean magnitude words. Each is the exact equivalent of the English
    # token, so the digits in front of it never change: 십억 *is* "billion"
    # (10억), not "100 million". /10만 is per-100,000, the same denominator
    # as /100k.
    "ko": [
        (re.compile(r"(?<=\d)tn\b"), "조"),
        (re.compile(r"(?<=\d)bn\b"), "십억"),
        (re.compile(r"(?<=\d)mn\b"), "백만"),
        (re.compile(r"(?<=\d)M\b"), "백만"),
        (re.compile(r"/100k\b"), "/10만"),
        (re.compile(r"(?<=\d)pp\b"), "%p"),
    ],
}

# Korean writes the currency after the number. These run last, on a string
# whose magnitude word is already Korean, and they anchor on the whole
# string so they fire on a bare value label ('US$ 684bn') and leave a
# currency mentioned inside a sentence alone — that sentence has a catalog
# entry of its own.
_CURRENCY_SUFFIX = {
    "ko": [
        (re.compile(r"^US\$\s*(.+)$"), r"\1 달러"),
        (re.compile(r"^₩\s*(.+)$"), r"\1 원"),
        (re.compile(r"^€\s*(.+)$"), r"\1 유로"),
    ],
}


def set_lang(lang: str) -> None:
    """Select the language the next figure will be saved in."""
    global LANG
    if _COUNTRY is not None and lang not in _COUNTRY.locale_codes:
        raise ValueError(
            f"{_COUNTRY.slug} does not publish in {lang!r}; "
            f"it publishes {list(_COUNTRY.locale_codes)}")
    LANG = lang


def bind(country) -> None:
    """Load one country's catalog. Replaces whatever was loaded before.

    The engine holds exactly one country at a time on purpose: a single
    process rendering two countries would otherwise be able to translate a
    Brazilian plate with an Argentine catalog, and the two share enough
    English phrasing that the result would look right.
    """
    global _COUNTRY
    _COUNTRY = country
    _load_catalog.cache_clear()
    _values_cache.clear()
    reset_missing()


def missing() -> list[str]:
    """Strings that were rendered with no translation, sorted."""
    return sorted(_missing)


def reset_missing() -> None:
    _missing.clear()


def swap_separators(text: str, lang: str | None = None) -> str:
    """Rewrite the decimal and thousands marks for one locale.

    The substitution is a single `translate` pass per match, so the comma and
    the point swap simultaneously instead of collapsing into each other —
    a two-step replace turns 12,739.5 into 12.739.5.
    """
    table = _SEPARATORS.get(lang or LANG)
    if not table:
        return text
    swap = str.maketrans(table)
    return _NUMBER.sub(lambda m: m.group(0).translate(swap), text)


def apply_units(text: str, lang: str | None = None) -> str:
    lang = lang or LANG
    for pattern, repl in _UNITS.get(lang, ()):
        text = pattern.sub(repl, text)
    stripped = text.strip()
    for pattern, repl in _CURRENCY_SUFFIX.get(lang, ()):
        if pattern.match(stripped):
            return pattern.sub(repl, stripped)
    return text


def localize_numbers(text: str, lang: str | None = None) -> str:
    return swap_separators(apply_units(text, lang), lang)


# ---------------------------------------------------------------- lookup
# A value label carries no language of its own: "€2,991bn" or "44,000" only
# needs its separators and unit swapped, not a catalog entry. Strip the
# currency marks, the digits and the magnitude suffixes; if no letter is
# left, there is nothing to translate.
_VALUE_PARTS = re.compile(
    r"US\$|€|₩|R\$|\$US|Md€|M€|B€|Md\$US|B\$US|[\d.,:%+\-–—/()\s ]"
    r"|(?<=\d)(?:tn|bn|mn|pp|M|k|bi|mi|tri)\b")


def is_value_label(text: str) -> bool:
    return not re.search(r"[^\W\d_]", _VALUE_PARTS.sub("", text))


class _Catalog:
    """One country's translations, indexed for each kind of lookup.

    Three key shapes grew up in the five original repositories and all three
    are still in use, so all three are supported rather than rewritten:

      "Real GDP growth"                exact
      "peak {0} in {1}"                positional — every number abstracted
      "rebased {} = 100"               brace — years first, then any number

    A key whose numbers come from the data must not be pinned in its
    filled-in form: the build would break the day a series gains an earlier
    year, which is exactly what happened to the Brazilian markets plate.
    """

    __slots__ = ("exact", "positional", "brace")

    def __init__(self, raw: dict, lang: str):
        self.exact: dict[str, str] = {}
        self.positional: dict[str, str] = {}
        self.brace: dict[str, str] = {}
        for english, per_lang in raw.items():
            hit = per_lang.get(lang) if isinstance(per_lang, dict) else None
            if hit is None:
                continue
            if re.search(r"\{\d\}", english):
                self.positional[english] = hit
            elif "{}" in english:
                self.brace[english] = hit
            else:
                self.exact[english] = hit

    def get(self, text: str) -> str | None:
        hit = self.exact.get(text)
        if hit is not None:
            return hit

        if self.positional:
            key, numbers = _abstract(text, _ANY_NUMBER)
            template = self.positional.get(key)
            if template is not None:
                try:
                    return template.format(
                        *[localize_numbers(n) for n in numbers])
                except (IndexError, KeyError):
                    pass

        if self.brace:
            for pattern in (_YEAR, _LOOSE_NUMBER):
                if not pattern.search(text):
                    continue
                template = pattern.sub("{}", text)
                hit = self.brace.get(template)
                if hit is not None:
                    # Captured values are localized before substitution, so
                    # a Brazilian reader gets 2,5% rather than 2.5%.
                    try:
                        return hit.format(*(localize_numbers(v)
                                            for v in pattern.findall(text)))
                    except (IndexError, KeyError):
                        pass
                if template in self.values():
                    # A second pass over the same figure sees the filled-in
                    # translation, which no longer matches its own template.
                    return text
        return None

    def values(self) -> frozenset[str]:
        return frozenset(self.exact.values()) | frozenset(self.brace.values())


def _abstract(text: str, pattern) -> tuple[str, list[str]]:
    """Replace every number with a positional placeholder.

    "2026: 8 months of 12" becomes ("{0}: {1} months of {2}", [...]), so one
    catalog entry covers every year and every count. Without this the
    catalog would need a row per value, and a new year of data would break
    the build for no reason.
    """
    numbers: list[str] = []

    def take(match: re.Match[str]) -> str:
        numbers.append(match.group(0))
        return "{%d}" % (len(numbers) - 1)

    return pattern.sub(take, text), numbers


_catalogs: dict[tuple, _Catalog] = {}


def _load_catalog(lang: str) -> _Catalog:
    if _COUNTRY is None:
        raise RuntimeError("core.i18n.bind(country) has not been called")
    key = (_COUNTRY.slug, lang)
    hit = _catalogs.get(key)
    if hit is None:
        path = _COUNTRY.dir / "i18n.json"
        raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        hit = _catalogs[key] = _Catalog(raw, lang)
    return hit


_load_catalog.cache_clear = _catalogs.clear  # type: ignore[attr-defined]

_values_cache: dict[tuple, frozenset] = {}


def _translated_values() -> frozenset[str]:
    """Every string the active catalog can produce, so already-translated
    text is recognised rather than reported as untranslated."""
    key = (_COUNTRY.slug if _COUNTRY else None, LANG)
    hit = _values_cache.get(key)
    if hit is None:
        hit = _values_cache[key] = _load_catalog(LANG).values()
    return hit


def translate(text: str) -> str:
    """One rendered string in the target language."""
    if LANG == "en" or not text:
        return text
    catalog = _load_catalog(LANG)
    out = []
    # Annotations are often multi-line; each line is translated on its own so
    # a wrapped caption does not need its line breaks baked into the
    # catalog. A catalog key may still contain a newline, so the whole
    # string is tried first.
    whole = catalog.get(text.strip())
    if whole is not None:
        return text.replace(text.strip(), whole)
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or is_value_label(stripped):
            out.append(localize_numbers(line))
            continue
        hit = catalog.get(stripped)
        if hit is None and stripped in _translated_values():
            # Already translated: a second pass over the same figure must not
            # report our own output as a gap in the catalog.
            out.append(line)
        elif hit is None:
            _missing.add(stripped)
            out.append(localize_numbers(line))
        else:
            # A translation is written with its own separators already.
            out.append(line.replace(stripped, hit))
    return "\n".join(out)


class _LocalizedFormatter(mticker.Formatter):
    """Wraps a tick formatter so its output is localized.

    Tick labels cannot be fixed by rewriting their text: savefig triggers a
    redraw, which regenerates every label from the formatter and throws the
    edit away. Only replacing the formatter survives. set_locs is forwarded
    because ScalarFormatter decides its own precision from the tick
    positions, and would format against stale ones otherwise.

    The language is read at call time, not captured, so one wrapped axis
    renders correctly if the figure is saved again in another language.
    """

    def __init__(self, inner):
        self.inner = inner

    def set_locs(self, locs):
        self.inner.set_locs(locs)
        super().set_locs(locs)

    def __call__(self, x, pos=None):
        return localize_numbers(self.inner(x, pos))

    def format_data(self, value):
        return localize_numbers(self.inner.format_data(value))


def _localize_ticks(fig) -> None:
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            inner = axis.get_major_formatter()
            if isinstance(inner, _LocalizedFormatter):
                continue
            axis.set_major_formatter(_LocalizedFormatter(inner))


# Marker set on a Text artist once it has been rewritten. Localizing a figure
# twice must be a no-op: a value label like "€ 2.991 bi" is still a value
# label on the second pass, so it would be run through the number rules
# again and "2.991" would come back as "2,991" — a number a thousand times
# too small, produced silently.
_DONE = "_worldreports_localized"


def mark_localized(artist) -> None:
    """Declare that this Text was composed already translated.

    For a label whose parts are not all translatable — a URL beside a
    sentence — so the sweep below leaves it alone instead of looking the
    whole line up and reporting a gap that is not one.
    """
    setattr(artist, _DONE, LANG)


def localize(fig) -> None:
    """Rewrite every piece of text in a finished figure.

    Tick labels are formatted lazily, so the canvas is drawn first or they
    come back empty. Only real Text artists are matched: a legend entry is
    also reachable as an offsetbox TextArea wrapping that same Text, and
    visiting the wrapper afterwards reads back the translation we just wrote
    and reports it as untranslated.
    """
    if LANG == "en":
        return
    fig.canvas.draw()
    _localize_ticks(fig)
    for text in fig.findobj(match=mtext.Text):
        if getattr(text, _DONE, None) == LANG:
            continue
        current = text.get_text()
        if not current:
            continue
        new = translate(current)
        if new != current:
            text.set_text(new)
        setattr(text, _DONE, LANG)


# ------------------------------------------------------------- authoring
def coverage(country) -> dict[str, list[str]]:
    """Which catalog entries each of a country's languages is missing.

    Used by `make i18n` and by the tests, so a country cannot be published
    with a half-filled catalog.
    """
    path = country.dir / "i18n.json"
    raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    gaps = {}
    for code in country.locale_codes:
        if code == "en":
            continue
        gaps[code] = sorted(
            k for k, v in raw.items()
            if not isinstance(v, dict) or not v.get(code))
    return gaps
