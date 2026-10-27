"""Every number style, written out: the figures a reader actually sees.

The other suites check that a locale *has* a form; this one checks what
the form is. Each row below is a figure as it appears on a card (pages) or
a plate label (plates), in one number style, spelled out character for
character — so a change to a separator, a unit word or a rescaling rule
shows up here as a diff rather than on a published page.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from core import i18n, numstyle
from core.country import Country
from core.sitebuild import (AFFIX, CURRENCY_AFFIX, NUMFMT, SiteContext,
                            format_figure, localize_prose)

N = numstyle.NBSP
ROOT = Path(__file__).resolve().parent.parent


def card(style: str, spec: str, value: float, currency: str | None = None):
    per = AFFIX.get(spec) or CURRENCY_AFFIX[currency][spec]
    prefix, suffix = per[style]
    return format_figure(value, spec, style, prefix, suffix)


# ------------------------------------------------------------- the cards
# (style, spec, currency, value, expected)
CARDS = [
    # The published styles. These are the strings already on the site and
    # must not move. (Figures of a thousand bn or more step up a word;
    # those are pinned in the block after this one.)
    ("en", "money_bn", "EUR", 291.4, "€291bn"),
    ("fr", "money_bn", "EUR", 2991.4, f"2{N}991{N}Md€"),
    ("fr", "pct_gdp", None, 12.5, f"12,5{N}% du PIB"),
    ("pt", "money_bn", "BRL", 745.2, "R$ 745 bi"),
    ("pt", "money_tn1", "BRL", 11.7452, "R$ 11,7 tri"),
    ("pt", "pct", None, 12.5, "12,5%"),
    ("es", "money_bn", "EUR", 594.3, "€ 594 mm"),
    ("ko", "money_tn", "KRW", 2549.1, "2,549조 원"),
    ("ko", "usd_bn", None, 684.4, "684십억 달러"),

    # A thousand of the spec's unit or more moves one word up, to three
    # significant digits (STEP_UP); French and Italian keep their
    # thousands of milliards, and 조 is already the top Korean word.
    ("en", "money_bn", "EUR", 2991.4, "€2.99tn"),
    ("en", "money_bn", "JPY", 666441, "¥666tn"),
    ("en", "usd_bn", None, 30861.0, "US$ 30.9tn"),
    ("en", "usd_bn_s", None, -1248.0, "US$ -1.25tn"),
    ("en", "usd_bn", None, 4003.0, "US$ 4.00tn"),
    ("en", "pop_mn", None, 1406.6, "1.41bn"),
    ("pt", "money_bn", "BRL", 1101.3, "R$ 1,10 tri"),
    ("pt", "money_bn", "BRL", 11745.2, "R$ 11,7 tri"),
    ("pt", "pop_mn", None, 1406.6, "1,41 bi"),
    ("es", "money_bn", "EUR", 1690.2, "€ 1,69 billones"),
    ("de", "usd_bn", None, 1044.0, f"1,04{N}Bio.{N}US-$"),
    ("ko", "usd_bn", None, 1872.0, "1.87조 달러"),
    ("it", "money_bn", "EUR", 2265.0, f"2.265{N}mld{N}€"),
    ("ko", "money_tn", "KRW", 2677.0, "2,677조 원"),
    ("en", "money_bn", "EUR", 999.4, "€999bn"),
    # The edges: the threshold is the printed figure, and the digits are
    # counted after rounding.
    ("en", "usd_bn", None, 999.5, "US$ 1.00tn"),
    ("en", "usd_bn_s", None, -999.6, "US$ -1.00tn"),
    ("en", "pop_mn", None, 999.96, "1.00bn"),
    ("pt", "money_bn", "BRL", 999.5, "R$ 1,00 tri"),
    ("en", "usd_bn", None, 9996.0, "US$ 10.0tn"),
    ("en", "usd_bn", None, 99960.0, "US$ 100tn"),
    ("es", "usd_bn", None, 1044.0, "US$ 1,04 billones"),
    ("es", "usd_bn", None, 683.3, "US$ 683bn"),

    # German: Duden / DIN 5008, on every German page — Switzerland's too.
    ("de", "pct_gdp", None, 12.5, f"12,5{N}% des BIP"),
    ("de", "pct_s", None, -0.4, f"-0,4{N}%"),
    ("de", "money_bn", "EUR", 4305.3, f"4,31{N}Bio.{N}€"),
    ("de", "money_bn", "CHF", 812.4, f"812{N}Mrd.{N}CHF"),
    ("de", "money", "CHF", 1234567, f"1.234.567{N}CHF"),
    ("de", "usd_bn", None, 684.4, f"684{N}Mrd.{N}US-$"),
    ("de", "pop_mn", None, 8.96, f"9,0{N}Mio."),
    ("de", "dec2", None, 1234.567, "1.234,57"),
    ("de", "dec1", None, 1234.56, "1.234,6"),
    ("de", "rank", None, 24, "Platz 24"),
    ("de", "years", None, 83.4, "83,4 Jahre"),

    # Italian: ISTAT / Treccani.
    ("it", "pct_gdp", None, 135.3, "135,3% del PIL"),
    ("it", "money_bn", "EUR", 2192.2, f"2.192{N}mld{N}€"),
    ("it", "money", "EUR", 38200, f"38.200{N}€"),
    ("it", "pop_mn", None, 58.99, f"59,0{N}mln"),
    ("it", "rank", None, 41, "41º"),

    # European Portuguese: "mil milhões", a space as the group mark and
    # before %, the euro after the amount.
    ("pt-PT", "money_bn", "EUR", 291.153, f"291{N}mil milhões de euros"),
    ("pt-PT", "money", "EUR", 27450, f"27{N}450{N}€"),
    ("pt-PT", "pct", None, 12.5, f"12,5{N}%"),
    ("pt-PT", "pct_gdp", None, 99.1, f"99,1{N}% do PIB"),
    ("pt-PT", "count", None, 10639726, f"10{N}639{N}726"),
    ("pt-PT", "usd_bn", None, 39.2, f"39{N}mil milhões de dólares"),
    ("pt-PT", "rank", None, 3, "3.º"),

    # Japanese: rescaled onto 万/億/兆 (1e4, 1e8, 1e12).
    ("ja", "money_tn", "JPY", 636.9, "637兆円"),         # ¥636.9tn, .0f
    ("ja", "money_bn", "JPY", 609312, "609.3兆円"),      # ¥609,312bn
    ("ja", "money", "JPY", 4950000, "4,950,000円"),
    ("ja", "usd_bn", None, 684.4, "6,844億ドル"),         # 6.844e11
    ("ja", "usd_bn", None, 1234.5, "1.23兆ドル"),
    ("ja", "usd_bn_s", None, -23.4, "-234億ドル"),
    ("ja", "pct_gdp", None, 236.7, "GDP比236.7%"),
    ("ja", "pop_mn", None, 124.5, "1.25億人"),
    ("ja", "pop_mn", None, 12.3, "1,230万人"),
    ("ja", "rank", None, 38, "38位"),

    # Simplified Chinese: 万/亿/万亿.
    ("zh-Hans", "money_bn", "CNY", 134908.4, "134.9万亿元"),  # 1.349e14
    ("zh-Hans", "usd_bn", None, 684.4, "6,844亿美元"),
    ("zh-Hans", "pop_mn", None, 1408.28, "14.08亿人"),
    ("zh-Hans", "pct_gdp", None, 4.1, "占GDP的4.1%"),
    ("zh-Hans", "rank", None, 3, "第3位"),

    # Traditional Chinese (Taiwan): 萬/億/兆, 兆 = 1e12.
    ("zh-Hant", "money_bn", "TWD", 24658.7, "24.66兆元"),
    ("zh-Hant", "usd_bn_s", None, -23.4, "-234億美元"),
    ("zh-Hant", "pop_mn", None, 23.4, "2,340萬人"),
    ("zh-Hant", "rank", None, 12, "第12名"),

    # Vietnamese: triệu/tỷ/nghìn tỷ, CLDR vi separators.
    ("vi", "money_bn", "VND", 11511900, f"11.512{N}nghìn tỷ đồng"),
    ("vi", "money", "VND", 114000000, f"114.000.000{N}₫"),
    ("vi", "usd_bn", None, 476.3, f"476{N}tỷ USD"),
    ("vi", "pop_mn", None, 101.3, f"101,3{N}triệu"),
    ("vi", "pct_gdp", None, 3.1, "3,1% GDP"),

    # Hebrew: numbers and affixes only (RTL is out of scope).
    ("he", "money_bn", "ILS", 1952.3, f"1,952{N}מיליארד ₪"),
    ("he", "pct", None, 3.2, "3.2%"),
    ("he", "pop_mn", None, 9.98, f"10.0{N}מיליון"),

    # English forms of the new currencies (EU style guide: symbol first,
    # an ISO code first with a space).
    ("en", "money_bn", "GBP", 2851.0, "£2.85tn"),
    ("en", "money_bn", "CHF", 812.4, "CHF 812bn"),
    ("en", "money_tn", "JPY", 636.9, "¥637tn"),
    ("pt", "money_bn", "GBP", 2851.0, "£ 2,85 tri"),
]


@pytest.mark.parametrize("style,spec,currency,value,expected", CARDS,
                         ids=[f"{r[0]}-{r[1]}-{r[2] or ''}-{r[3]}"
                              for r in CARDS])
def test_a_card_figure_is_written_natively(style, spec, currency, value,
                                           expected):
    assert card(style, spec, value, currency) == expected


# Each ladder style's words and what they are worth.
WORTH = {
    "ja": {"兆": 1e12, "億": 1e8, "万": 1e4},
    "zh-Hans": {"万亿": 1e12, "亿": 1e8, "万": 1e4},
    "zh-Hant": {"兆": 1e12, "億": 1e8, "萬": 1e4},
    "vi": {"nghìn tỷ": 1e12, "tỷ": 1e9, "triệu": 1e6},
}


def test_the_ladders_are_worth_what_the_words_say():
    """億 is 1e8 and 兆 1e12: the rescaling is only right if these are."""
    for style, ladder in numstyle.LADDERS.items():
        assert dict((w, t) for t, w in ladder) == WORTH[style], style


@pytest.mark.parametrize("style", sorted(numstyle.LADDERS))
@pytest.mark.parametrize("spec,value", [
    ("money_bn", 609312.0), ("money_bn", 4.2), ("money_bn", 134908.4),
    ("money_tn", 636.9), ("usd_bn", 684.4), ("usd_bn", 1234.5),
    ("usd_bn1", 12.34), ("pop_mn", 1408.28), ("pop_mn", 23.4),
    ("pop_mn", 0.85),
])
def test_a_rescaled_figure_is_the_same_amount(style, spec, value):
    """Read the rescaled figure back and it is the same amount, within the
    rounding the English figure itself carries."""
    n, word = numstyle.rescaled(value, spec, style, NUMFMT[spec])
    back = float(numstyle.swap(n, style).replace(".", "").replace(",", ".")
                 if style in numstyle.SEPARATORS else n.replace(",", ""))
    amount = back * WORTH[style][word]
    truth = value * numstyle.SCALE[spec]
    # The figure is rounded to its own last digit (at most four significant
    # digits, at most two decimals) or to the English figure's last digit,
    # whichever is coarser: the error is at most half of that.
    shown = len(n.split(".")[1]) if "." in n else 0
    tolerance = max(0.5 * 10 ** -shown * WORTH[style][word],
                    0.5 * numstyle.SCALE[spec] * 10 ** -numstyle.precision(
                        NUMFMT[spec])) * 1.0001
    assert math.isclose(amount, truth, abs_tol=tolerance), (n, word)


# ------------------------------------------------------------ the plates
# (style, English label as a plate draws it, expected)
PLATES = [
    ("fr", "€2,991bn", f"2{N}991{N}Md€"),
    ("pt", "€2,991bn", "€ 2.991 bi"),
    ("ko", "US$ 684bn", "684십억 달러"),
    ("de", "€2,991bn", f"2.991{N}Mrd.{N}€"),
    ("de", "CHF 812bn", f"812{N}Mrd.{N}CHF"),
    ("de", "12.5%", f"12,5{N}%"),
    ("de", "/100k", "/100.000 Einw."),
    ("de", "+0.3pp", f"+0,3{N}Pp."),
    ("it", "€2,192bn", f"2.192{N}mld{N}€"),
    ("it", "12.5%", "12,5%"),
    ("pt-PT", "€291bn", f"291{N}mil M{N}€"),
    ("pt-PT", "1,234.5", f"1{N}234,5"),
    ("pt-PT", "12.5%", f"12,5{N}%"),
    ("ja", "¥636.9tn", "636.9兆円"),
    ("ja", "US$ 684bn", "6,840億ドル"),
    ("ja", "12.5bn", "125億"),
    ("ja", "125.1M", "1.25億"),
    ("ja", "+0.3pp", "+0.3ポイント"),
    ("zh-Hans", "CN¥134.9tn", "134.9万亿元"),
    ("zh-Hans", "US$ 684bn", "6,840亿美元"),
    ("zh-Hant", "NT$24.7tn", "24.7兆元"),
    ("zh-Hant", "/100k", "/10萬人"),
    ("vi", "₫11,511.9tn", f"11.512{N}nghìn tỷ{N}đồng"),  # 4 digits kept
    ("vi", "US$ 476bn", f"476{N}tỷ{N}USD"),
    ("vi", "/100k", "/100.000 dân"),
    ("he", "₪1,952bn", f"1,952{N}מיליארד{N}₪"),
    ("he", "US$ 684bn", f"684{N}מיליארד{N}דולר"),
]


@pytest.mark.parametrize("style,english,expected", PLATES,
                         ids=[f"{r[0]}-{r[1]}" for r in PLATES])
def test_a_plate_label_is_written_natively(style, english, expected):
    assert i18n.localize_numbers(english, style) == expected


# ------------------------------------------------- separators, round trip
UNTOUCHABLE = ["2006", "2019", "2006–2026", "2006-2026", "1999–2000",
               "FY2024", "Q3 2025", "2019/20", "2024-25", "1 2 3",
               "p. 12", "art. 3", "Table 3", "2026 (partial)"]


@pytest.mark.parametrize("style", sorted(set(numstyle.SEPARATORS)
                                         | set(i18n._UNITS)))
def test_years_and_ranges_are_never_rewritten(style):
    for text in UNTOUCHABLE:
        assert i18n.swap_separators(text, style) == text, (style, text)
        assert i18n.localize_numbers(text, style) == text, (style, text)


def _unswap(text: str, style: str) -> str:
    inverse = {v: k for k, v in numstyle.SEPARATORS[style].items()}
    return text.translate(str.maketrans(inverse))


@pytest.mark.parametrize("style", sorted(numstyle.SEPARATORS))
def test_the_separator_swap_round_trips(style):
    """Swapping and swapping back gives the English number: no mark is
    collapsed into the other (12,739.5 never becomes 12.739.5 and then
    something unreadable)."""
    for english in ["12,739.5", "1,234,567.89", "0.5", "999.999",
                    "44,000", "3.14159", "1,000,000"]:
        local = i18n.swap_separators(english, style)
        assert local != english
        assert _unswap(local, style) == english, (style, english, local)


def test_the_two_tables_are_one():
    """Pages and plates swap from the same table, so they cannot drift."""
    from core import sitebuild
    assert sitebuild.SEPARATORS is i18n._SEPARATORS is numstyle.SEPARATORS


def test_prose_keeps_its_full_stops():
    """An alt text is localized number by number, not mark by mark: a
    sentence-wide swap turned every full stop into a comma."""
    out = localize_prose("GDP runs from 1,234.5 in 2006 to 2.5 in 2026. "
                         "The figures are below.", "pt")
    assert out == ("GDP runs from 1.234,5 in 2006 to 2,5 in 2026. "
                   "The figures are below.")


# ----------------------------------------------------- coverage, Phase B
def _yaml_paths() -> list[Path]:
    """country.yaml in this checkout, and in the sibling lanes if any.

    Phase B is built in parallel worktrees under .slim/worktrees/, each
    adding one country. Reading theirs too means a lane cannot ship a
    locale this table has no form for: the gap shows up here, before the
    merge, rather than as a KeyError in that lane's page build.
    """
    roots = {ROOT}
    if ROOT.parent.name == "worktrees":
        roots |= {p for p in ROOT.parent.iterdir() if p.is_dir()}
        if ROOT.parent.parent.name == ".slim":
            roots.add(ROOT.parent.parent.parent)        # the main checkout
    paths = []
    for r in sorted(roots):
        paths += sorted((r / "countries").glob("*/country.yaml"))
    return paths


def _declared():
    """(slug, currency, {styles}) for every country.yaml we can see, plus
    the Phase B countries queued in COUNTRIES.md that have no lane yet."""
    out = {}
    for path in _yaml_paths():
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        codes = [loc["code"] for loc in cfg["locales"]]
        chosen = cfg.get("number_style") or {}
        styles = {chosen.get(c, c) for c in codes}
        slug = cfg["slug"]
        cur = out.setdefault(slug, (cfg["currency"]["code"], set()))
        cur[1].update(styles)
    for slug, currency, styles in QUEUED:
        out.setdefault(slug, (currency, set()))[1].update(styles)
    return out


# COUNTRIES.md's queue: the countries whose lane has not started, and the
# style a lane's locale is meant to end up in (Portugal's pt is pt-PT).
QUEUED = [
    ("china", "CNY", {"zh-Hans", "en", "pt"}),
    ("taiwan", "TWD", {"zh-Hant", "en", "pt"}),
    ("israel", "ILS", {"he", "en", "pt"}),
    ("portugal", "EUR", {"pt-PT", "en"}),
    ("switzerland", "CHF", {"de", "en", "pt"}),
]

DECLARED = _declared()
ALL_STYLES = sorted(set().union(*(s for _, s in DECLARED.values())))
MONEY_SPECS = sorted(s for s in NUMFMT if s not in AFFIX)


def test_every_spec_is_a_language_affix_or_a_money_figure():
    for spec in NUMFMT:
        assert spec in AFFIX or any(spec in c for c in CURRENCY_AFFIX.values()), \
            spec
    for spec in AFFIX:
        assert spec in NUMFMT, spec


def test_every_declared_style_is_known():
    for slug, (_, styles) in DECLARED.items():
        unknown = styles - set(numstyle.STYLES)
        assert not unknown, f"{slug}: no number style {sorted(unknown)}"


@pytest.mark.parametrize("style", ALL_STYLES)
def test_every_style_has_every_language_spec(style):
    missing = [spec for spec in AFFIX if style not in AFFIX[spec]]
    assert not missing, f"style {style!r} has no form for {missing}"


@pytest.mark.parametrize("slug", sorted(DECLARED))
def test_every_country_can_write_its_own_money(slug):
    currency, styles = DECLARED[slug]
    assert currency in CURRENCY_AFFIX, f"{slug}: no forms for {currency}"
    specs = CURRENCY_AFFIX[currency]
    assert "money" in specs and {"money_bn", "money_tn"} & set(specs), \
        (slug, sorted(specs))
    for spec, per_style in specs.items():
        missing = sorted(styles - set(per_style))
        assert not missing, f"{slug}: {currency} {spec} has no {missing} form"


@pytest.mark.parametrize("style", [s for s in ALL_STYLES if s != "en"])
def test_every_style_has_plate_rules(style):
    """A style with no unit rules would print "bn" on a plate."""
    assert style in i18n._UNITS, style


def test_a_ladder_style_rescales_and_no_other_does():
    """"{mag}" in a suffix means the figure is rescaled onto the style's own
    word; it must appear exactly where a ladder will fill it."""
    tables = [AFFIX] + list(CURRENCY_AFFIX.values())
    for table in tables:
        for spec, per_style in table.items():
            for style, (prefix, suffix) in per_style.items():
                ladder = style in numstyle.LADDERS and spec in numstyle.SCALE
                assert ("{mag}" in suffix) == ladder, (spec, style, suffix)
                assert "{mag}" not in prefix


# ------------------------------------------------------- the pt-PT switch
def _throwaway(tmp_path, extra: dict) -> Country:
    cfg = yaml.safe_load(
        (ROOT / "countries/brasil/country.yaml").read_text(encoding="utf-8"))
    cfg.update(slug="lusitania", currency={"code": "EUR"}, **extra)
    d = tmp_path / "lusitania"
    d.mkdir()
    (d / "country.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True),
                                    encoding="utf-8")
    return Country.from_dir(d)


def test_number_style_selects_european_portuguese(tmp_path):
    c = _throwaway(tmp_path, {"number_style": {"pt": "pt-PT"}})
    assert c.number_style("pt") == "pt-PT"
    assert c.number_style("en") == "en"
    ctx = SiteContext(c)
    got = ctx.render(291.153, "money_bn")
    assert got == {"pt": f"291{N}mil milhões de euros", "en": "€291bn"}
    assert ctx.render(12.5, "pct") == {"pt": f"12,5{N}%", "en": "12.5%"}

    i18n.bind(c)
    try:
        assert i18n.localize_numbers("€2,991bn", "pt") == f"2{N}991{N}mil M{N}€"
        assert i18n.swap_separators("1,234.5", "pt") == f"1{N}234,5"
    finally:
        i18n.bind(Country.load("brasil"))
        assert i18n.swap_separators("1,234.5", "pt") == "1.234,5"


def test_brazil_keeps_the_base_style():
    c = Country.load("brasil")
    assert c.number_style("pt") == "pt"
    assert SiteContext(c).render(11745.2, "money_bn")["pt"] == "R$ 11,7 tri"
    assert SiteContext(c).render(745.2, "money_bn")["pt"] == "R$ 745 bi"


def test_number_style_must_match_the_language(tmp_path):
    with pytest.raises(ValueError, match="not a 'pt' style"):
        _throwaway(tmp_path, {"number_style": {"pt": "de"}})


def test_number_style_must_name_a_locale(tmp_path):
    with pytest.raises(ValueError, match="not among its locales"):
        _throwaway(tmp_path, {"number_style": {"fr": "fr"}})


def test_a_country_written_for_a_styled_audience_selects_the_style(country):
    """Portugal's html_lang is pt-PT; its numbers must be too.

    A country whose `html_lang` names a style the atlas has — pt-PT — and
    does not select it is publishing Brazilian numbers to Portuguese
    readers. de-CH, en-GB, es-AR name no style of their own and pass: the
    user's rule is German numbers on every German page.
    """
    for loc in country.locales:
        if loc.html_lang in numstyle.STYLES and loc.html_lang != loc.code:
            assert country.number_style(loc.code) == loc.html_lang, (
                f"{country.slug}: {loc.code} is html_lang {loc.html_lang} — "
                f"add `number_style: {{{loc.code}: {loc.html_lang}}}` to "
                f"country.yaml")


def test_a_missing_figure_does_not_crash_the_step_up():
    prefix, suffix = AFFIX["usd_bn"]["en"]
    assert format_figure(float("nan"), "usd_bn", "en", prefix, suffix) == "US$ nanbn"
    assert format_figure(float("inf"), "usd_bn", "en", prefix, suffix) == "US$ infbn"
