"""How each language writes a number: the part pages and plates share.

A *number style* is the set of conventions one readership writes figures
in: the decimal and thousands marks, and, for the languages that count in
myriads, the magnitude words. It is usually the language itself, but not
always — Portugal and Brazil share the catalogs and the chrome ("pt") and
write numbers differently:

    pt     (Brazil)     2.991,5   US$ 684 bi     12,5%
    pt-PT  (Portugal)   2 991,5   684 mil milhões de dólares   12,5 %

So a country picks a style per locale in its country.yaml,

    number_style: {pt: pt-PT}

and every locale it does not name uses the style of the same name.
`Country.number_style(code)` resolves it; core.sitebuild (the pages) and
core.i18n (the plates) both format through the style, never the bare
language code.

The affix tables — "% do PIB", "Mrd. €", "兆円" — stay where they were, in
core.sitebuild and core.i18n, keyed by style. What lives here is what both
of them need and must not disagree on: the separators, and the magnitude
ladders.

Sources, per style (the affix tables in core.sitebuild and the unit rules
in core.i18n cite theirs beside each style):

    en      house style since the merge: 1,234.5
    fr      Imprimerie nationale / EU Interinstitutional Style Guide (ISG):
            1 234,5 with a no-break space
    pt      Brazilian usage (ABNT, IBGE): 1.234,5
    pt-PT   ISG Portuguese section and CLDR pt-PT: 1 234,5, the group
            mark a space (CLDR has U+202F; we use U+00A0, see below)
    es      the original Argentine and Spanish plates: 1.234,5
    ko      CLDR ko: English marks
    de      Duden and DIN 5008, as the user asked: 1.234,5 — on every
            German page, Switzerland's included (no Swiss apostrophe)
    it      ISTAT and Treccani usage: 1.234,5
    ja      CLDR ja: English marks; 万 億 兆 = 1e4 1e8 1e12
    zh-Hans CLDR zh: English marks; 万 亿 万亿 = 1e4 1e8 1e12
    zh-Hant CLDR zh-Hant: English marks; 萬 億 兆 = 1e4 1e8 1e12
    vi      CLDR vi: 1.234,5; triệu tỷ nghìn tỷ = 1e6 1e9 1e12
    he      CLDR he: English marks. Hebrew is right-to-left; this module
            does numbers and affixes only. Bidi (the page direction, RLM
            marks around a figure, matplotlib's lack of shaping) is out
            of scope here and tracked in COUNTRIES.md.
"""
from __future__ import annotations

import math
import re

# A no-break space, not U+202F (narrow no-break space): the fonts the
# plates fall back to do not all carry U+202F, and a missing glyph renders
# as a tofu box in the middle of every large number.
NBSP = "\u00a0"

#: Every number style the atlas can write, and the language it belongs to.
#: A country may map a locale only onto a style of the same language.
STYLES = {
    "en": "en", "fr": "fr", "pt": "pt", "pt-PT": "pt", "es": "es",
    "ko": "ko", "de": "de", "it": "it", "ja": "ja",
    "zh-Hans": "zh-Hans", "zh-Hant": "zh-Hant", "vi": "vi", "he": "he",
    "uk": "uk", "pl": "pl", "ru": "ru",
}

# The decimal and thousands marks, for the styles that change them. A
# style that keeps the English marks (en, ko, ja, zh-*, he) is absent on
# purpose: tests read "in SEPARATORS" as "this style swaps the marks".
SEPARATORS = {
    "fr": {",": NBSP, ".": ","},
    "pt": {",": ".", ".": ","},
    "pt-PT": {",": NBSP, ".": ","},
    "es": {",": ".", ".": ","},
    "de": {",": ".", ".": ","},
    "it": {",": ".", ".": ","},
    "vi": {",": ".", ".": ","},
    # Ukrainian: CLDR uk — a comma for the decimal and a non-breaking
    # space for the thousands, as in "1 234,5".
    "uk": {",": NBSP, ".": ","},
    # CLDR pl and ru: comma decimal, non-breaking-space thousands.
    "pl": {",": NBSP, ".": ","},
    "ru": {",": NBSP, ".": ","},
}


def swap(num: str, style: str) -> str:
    """Rewrite the marks in an English-formatted number for one style.

    One `translate` pass, so the comma and the point swap simultaneously
    instead of collapsing into each other: a two-step replace turns
    12,739.5 into 12.739.5.
    """
    table = SEPARATORS.get(style)
    return num.translate(str.maketrans(table)) if table else num


# ------------------------------------------------------------ magnitudes
# The base magnitude of each spec that carries one: a money_bn figure is a
# count of billions, a pop_mn figure a count of millions.
SCALE = {
    "money_bn": 1e9, "money_tn": 1e12,
    "usd_bn": 1e9, "usd_bn_s": 1e9, "usd_bn1": 1e9,
    "pop_mn": 1e6,
}

# Languages that do not group by thousands write a magnitude word of their
# own, and the figure has to be *rescaled* onto it, not merely given a new
# suffix: 684 bn is 6,840億 (億 = 1e8), and ¥636.9 tn is 636.9兆 (兆 = 1e12).
# The rung is picked by size, as a Japanese or Chinese writer would pick
# it — 6,840億ドル but 1.2兆ドル — largest first; a value below the last
# rung is written on the last rung.
#
# A style with no ladder writes the spec's own magnitude ("bn" → "Mrd.",
# "mil milhões", "מיליארד") and never rescales onto a ladder; from a
# thousand of that unit it moves one word up instead (core.sitebuild
# STEP_UP: "Mrd." → "Bio.", 십억 → 조). Korean would belong here (조/억)
# but keeps those exact forms until its pages are reworked on purpose.
LADDERS = {
    "ja":      ((1e12, "兆"), (1e8, "億"), (1e4, "万")),
    "zh-Hans": ((1e12, "万亿"), (1e8, "亿"), (1e4, "万")),
    "zh-Hant": ((1e12, "兆"), (1e8, "億"), (1e4, "萬")),
    "vi":      ((1e12, "nghìn tỷ"), (1e9, "tỷ"), (1e6, "triệu")),
}

# How many decimals a rescaled figure keeps. Never finer than the English
# figure it came from — "684bn" carries the nearest billion, so on a ja
# page it is 6,844億 and not 6,844.0億 — and never more than four
# significant digits or two decimals, so a figure moved onto a larger
# rung does not sprout precision: 609,312 bn yen is 609.3兆円, not
# 609.312兆円, and 1,408.28 million people are 14.08亿人.
_SIG = 4
_MAX_DECIMALS = 2

_PRECISION = re.compile(r"\.(\d+)f")


def rung(units: float, style: str, base: float) -> tuple[float, str]:
    """The (threshold, word) an amount in units is written on.

    The largest rung the amount reaches; zero, which reaches none, sits on
    the rung nearest the spec's own magnitude.
    """
    ladder = LADDERS[style]
    size = abs(units)
    if size == 0:
        return next((r for r in ladder if r[0] <= base), ladder[-1])
    for threshold, word in ladder:
        if size >= threshold:
            return threshold, word
    return ladder[-1]


def _on_rung(n_base: float, decimals: int, base: float, style: str,
             sign: str = "") -> tuple[str, str]:
    units = n_base * base
    threshold, word = rung(units, style, base)
    n = units / threshold
    digits = len(str(int(abs(round(n)))))
    finest = decimals + round(math.log10(threshold / base))
    d = max(0, min(finest, _SIG - digits, _MAX_DECIMALS))
    return f"{n:{sign},.{d}f}", word


def precision(fmt: str) -> int:
    """The decimal count a NUMFMT entry asks for."""
    m = _PRECISION.search(fmt)
    return int(m.group(1)) if m else 0


def rescaled(value: float, spec: str, style: str,
             fmt: str) -> tuple[str, str] | None:
    """`value` (a count of the spec's base unit) on the style's own rung.

    Returns the English-formatted number and the magnitude word, or None
    when the style writes this spec one-for-one. `fmt` is the spec's
    NUMFMT entry: its sign and its precision carry over.

        rescaled(684.4, "usd_bn", "ja", "{:,.0f}")     -> ("6,844", "億")
        rescaled(609312, "money_bn", "ja", "{:,.0f}")  -> ("609.3", "兆")
    """
    if style not in LADDERS or spec not in SCALE:
        return None
    sign = "+" if "{:+" in fmt else ""
    return _on_rung(value, precision(fmt), SCALE[spec], style, sign)


#: The English magnitude tokens a plate label can carry.
UNITS = {"tn": 1e12, "bn": 1e9, "mn": 1e6, "M": 1e6}


def on_ladder(english_number: str, english_unit: str,
              style: str) -> tuple[str, str]:
    """A plate's "684bn" on a ladder style: ("6,840", "億").

    The digits are parsed from the English label, so the precision the
    plate chose is the precision the rescaled label keeps.
    """
    shown = english_number.split(".")[1] if "." in english_number else ""
    sign = "+" if english_number.startswith("+") else ""
    # matplotlib writes a negative with U+2212; keep the mark it chose.
    minus = english_number.startswith("−")
    value = float(english_number.lstrip("−").replace(",", ""))
    n, word = _on_rung(value, len(shown), UNITS[english_unit], style, sign)
    return ("−" + n if minus else n), word
