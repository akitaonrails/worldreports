"""Turn a country's CSVs and its chapter copy into the pages we publish.

Every figure on the site is read out of `countries/<slug>/data` at build
time. Nothing is frozen into the page source and nothing is typed twice, so
the cards, the headline numbers and the plates cannot drift apart: they are
three renderings of one set of CSVs.

A chapter is declared in `countries/<slug>/chapters.py` and looks like this:

    {
      "id": "01_economy", "n": "01", "family": "money",
      "title": {"en": "The French Economy", "fr": "...", "pt": "..."},
      "blurb": {"en": "...", ...},
      "spark": ctx.col("macro/gdp.csv", "nominal_eurbn"),
      "stats": [ctx.stat({"en": "GDP", ...},
                         ctx.col("macro/gdp.csv", "nominal_eurbn"),
                         "money_bn")],
    }

`ctx.stat` decides for itself whether a figure is current: see `stat`.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from core import numstyle

#: How many beats (mini-stories) a story may have.
MIN_BEATS, MAX_BEATS = 3, 6

# A no-break space, not U+202F: see core.numstyle.
NBSP = numstyle.NBSP


# ------------------------------------------------------------- formatting
# How each kind of figure is written: the numeric format once, then the
# prefix and suffix each language puts around it.
NUMFMT = {
    "money_bn": "{:,.0f}", "money": "{:,.0f}", "money_tn": "{:,.0f}",
    "money_tn1": "{:,.1f}",
    "money2": "{:,.2f}",
    "usd_bn": "{:,.0f}", "usd_bn_s": "{:+,.0f}", "usd_bn1": "{:,.1f}",
    "pct": "{:,.1f}", "pct_s": "{:+,.1f}", "pct2": "{:,.2f}",
    "pct_gdp": "{:,.1f}", "pct_gdp_s": "{:+,.1f}",
    "count": "{:,.0f}", "rank": "{:,.0f}", "score100": "{:,.0f}",
    "dec3": "{:,.3f}", "dec2": "{:,.2f}", "dec1": "{:,.1f}",
    "pop_mn": "{:,.1f}", "per100k": "{:,.1f}", "per100k2": "{:,.2f}",
    "years": "{:,.1f}", "index": "{:,.0f}",
}

# Language-level affixes. These describe the language, not the country:
# Portuguese writes "% do PIB" whether the subject is Brazil or Korea.
# French moves a currency to the end, which is why each entry is a
# (prefix, suffix) pair rather than a shared prefix and three suffixes.
AFFIX = {
    "pct":       {"en": ("", "%"), "fr": ("", f"{NBSP}%"), "pt": ("", "%"),
                  "es": ("", "%"), "ko": ("", "%")},
    "pct_s":     {"en": ("", "%"), "fr": ("", f"{NBSP}%"), "pt": ("", "%"),
                  "es": ("", "%"), "ko": ("", "%")},
    "pct2":      {"en": ("", "%"), "fr": ("", f"{NBSP}%"), "pt": ("", "%"),
                  "es": ("", "%"), "ko": ("", "%")},
    "pct_gdp":   {"en": ("", "% GDP"), "fr": ("", f"{NBSP}% du PIB"),
                  "pt": ("", "% do PIB"), "es": ("", "% del PIB"),
                  "ko": ("", "% GDP")},
    "pct_gdp_s": {"en": ("", "% GDP"), "fr": ("", f"{NBSP}% du PIB"),
                  "pt": ("", "% do PIB"), "es": ("", "% del PIB"),
                  "ko": ("", "% GDP")},
    "count":     {l: ("", "") for l in ("en", "fr", "pt", "es", "ko")},
    "dec3":      {l: ("", "") for l in ("en", "fr", "pt", "es", "ko")},
    "dec2":      {l: ("", "") for l in ("en", "fr", "pt", "es", "ko")},
    "dec1":      {l: ("", "") for l in ("en", "fr", "pt", "es", "ko")},
    "index":     {l: ("", "") for l in ("en", "fr", "pt", "es", "ko")},
    "rank":      {l: ("#", "") for l in ("en", "fr", "pt", "es", "ko")},
    "score100":  {l: ("", "/100") for l in ("en", "fr", "pt", "es", "ko")},
    "pop_mn":    {"en": ("", "M"), "fr": ("", f"{NBSP}M"), "pt": ("", " mi"),
                  "es": ("", " M"), "ko": ("", "백만")},
    "per100k":   {"en": ("", "/100k"), "fr": ("", "/100 000 hab."),
                  "pt": ("", "/100 mil"), "es": ("", "/100 mil"),
                  "ko": ("", "/10만")},
    "per100k2":  {"en": ("", "/100k"), "fr": ("", "/100 000 hab."),
                  "pt": ("", "/100 mil"), "es": ("", "/100 mil"),
                  "ko": ("", "/10만")},
    "years":     {"en": ("", " yrs"), "fr": ("", " ans"),
                  "pt": ("", " anos"), "es": ("", " años"),
                  "ko": ("", "년")},
    "usd_bn":    {"en": ("US$ ", "bn"), "fr": ("", f"{NBSP}Md$US"),
                  "pt": ("US$ ", " bi"), "es": ("US$ ", "bn"),
                  "ko": ("", "십억 달러")},
    "usd_bn_s":  {"en": ("US$ ", "bn"), "fr": ("", f"{NBSP}Md$US"),
                  "pt": ("US$ ", " bi"), "es": ("US$ ", "bn"),
                  "ko": ("", "십억 달러")},
    "usd_bn1":   {"en": ("US$ ", "bn"), "fr": ("", f"{NBSP}Md$US"),
                  "pt": ("US$ ", " bi"), "es": ("US$ ", "bn"),
                  "ko": ("", "십억 달러")},
}

# The country's own currency, keyed by ISO 4217. Only the money specs need
# this, and only the country's own currency is ever used with them.
CURRENCY_AFFIX = {
    "CAD": {"money_bn": {"en": ("C$ ", "bn"), "fr": ("", f"{NBSP}Md$CA"),
                         "pt": ("C$ ", " bi")},
            "money":    {"en": ("C$ ", ""), "fr": ("", f"{NBSP}$CA"),
                         "pt": ("C$ ", "")}},
    "EUR": {"money_bn": {"en": ("€", "bn"), "fr": ("", f"{NBSP}Md€"),
                         "es": ("€ ", " mm"),
                         "pt": ("€ ", " bi")},
            "money":    {"en": ("€", ""), "fr": ("", f"{NBSP}€"),
                         "es": ("€", ""),
                         "pt": ("€ ", "")}},
    "BRL": {"money_bn": {"en": ("R$ ", "bn"), "pt": ("R$ ", " bi")},
            "money_tn1": {"en": ("R$ ", "tn"), "pt": ("R$ ", " tri")},
            "money2":   {"en": ("R$ ", ""), "pt": ("R$ ", "")},
            "money":    {"en": ("R$ ", ""), "pt": ("R$ ", "")}},
    "USD": {"money_bn": {"en": ("US$ ", "bn"), "pt": ("US$ ", " bi")},
            "money":    {"en": ("US$ ", ""), "pt": ("US$ ", "")}},
    "ARS": {"money_bn": {"en": ("$", "bn"), "es": ("$ ", " mm"),
                         "pt": ("$ ", " bi")},
            "money":    {"en": ("$", ""), "es": ("$ ", ""),
                         "pt": ("$ ", "")}},
    "KRW": {"money_tn": {"en": ("₩", "tn"), "ko": ("", "조 원"),
                         "pt": ("₩ ", " tri")},
            "money":    {"en": ("₩", ""), "ko": ("", " 원"),
                         "pt": ("₩ ", "")}},
}

# The styles added for Phase B, one block per style so each reads as the
# convention it is and carries its source. Merged into AFFIX and
# CURRENCY_AFFIX below. The styles above (en, fr, pt, es, ko) are what the
# published countries were built with and are left exactly as they were.
#
# "{mag}" in a suffix is the style's own magnitude word, for the styles
# that rescale onto a ladder (core.numstyle.LADDERS): 684 bn is written
# 6,840億ドル, not 684億. A style without a ladder writes the spec's
# magnitude one-for-one, or one word up from a thousand (STEP_UP, below),
# and never has the placeholder.
_N = NBSP
_STYLE_AFFIX = {
    # Duden and DIN 5008: a space before %, the amount before the unit,
    # "Mrd." and "Mio." with their points, "US-$" (Duden). The EU style
    # guide's German section agrees on the order and the space.
    "de": {
        "pct": ("", f"{_N}%"), "pct_s": ("", f"{_N}%"), "pct2": ("", f"{_N}%"),
        "pct_gdp": ("", f"{_N}% des BIP"), "pct_gdp_s": ("", f"{_N}% des BIP"),
        "rank": ("Platz ", ""), "score100": ("", "/100"),
        "pop_mn": ("", f"{_N}Mio."),
        "per100k": ("", "/100.000 Einw."), "per100k2": ("", "/100.000 Einw."),
        "years": ("", " Jahre"),
        "usd_bn": ("", f"{_N}Mrd.{_N}US-$"), "usd_bn_s": ("", f"{_N}Mrd.{_N}US-$"),
        "usd_bn1": ("", f"{_N}Mrd.{_N}US-$"),
    },
    # ISTAT and Treccani: % with no space (ISTAT house style), "mld" and
    # "mln", the ISO code after the amount as the EU style guide's Italian
    # section places it, "24º" for a rank.
    "it": {
        "pct": ("", "%"), "pct_s": ("", "%"), "pct2": ("", "%"),
        "pct_gdp": ("", "% del PIL"), "pct_gdp_s": ("", "% del PIL"),
        "rank": ("", "º"), "score100": ("", "/100"),
        "pop_mn": ("", f"{_N}mln"),
        "per100k": ("", "/100.000 ab."), "per100k2": ("", "/100.000 ab."),
        "years": ("", " anni"),
        "usd_bn": ("", f"{_N}mld{_N}USD"), "usd_bn_s": ("", f"{_N}mld{_N}USD"),
        "usd_bn1": ("", f"{_N}mld{_N}USD"),
    },
    # European Portuguese: the EU style guide's Portuguese section and
    # CLDR pt-PT. "mil milhões" for 10^9 — a "bilião" is 10^12 here — a
    # space before %, the currency after the amount, "24.º" (AO 1990).
    "pt-PT": {
        "pct": ("", f"{_N}%"), "pct_s": ("", f"{_N}%"), "pct2": ("", f"{_N}%"),
        "pct_gdp": ("", f"{_N}% do PIB"), "pct_gdp_s": ("", f"{_N}% do PIB"),
        "rank": ("", ".º"), "score100": ("", "/100"),
        "pop_mn": ("", f"{_N}milhões"),
        "per100k": ("", "/100 mil hab."), "per100k2": ("", "/100 mil hab."),
        "years": ("", " anos"),
        "usd_bn": ("", f"{_N}mil milhões de dólares"),
        "usd_bn_s": ("", f"{_N}mil milhões de dólares"),
        "usd_bn1": ("", f"{_N}mil milhões de dólares"),
    },
    # CLDR ja, and the Cabinet Office's and the BoJ's own usage: GDP比 in
    # front, 位 for a rank, the 万/億/兆 ladder with the unit word after.
    "ja": {
        "pct": ("", "%"), "pct_s": ("", "%"), "pct2": ("", "%"),
        "pct_gdp": ("GDP比", "%"), "pct_gdp_s": ("GDP比", "%"),
        "rank": ("", "位"), "score100": ("", "/100"),
        "pop_mn": ("", "{mag}人"),
        "per100k": ("", "/10万人"), "per100k2": ("", "/10万人"),
        "years": ("", "年"),
        "usd_bn": ("", "{mag}ドル"), "usd_bn_s": ("", "{mag}ドル"),
        "usd_bn1": ("", "{mag}ドル"),
    },
    # CLDR zh, and the NBS's usage: 占GDP的, 第…位, 万/亿/万亿.
    "zh-Hans": {
        "pct": ("", "%"), "pct_s": ("", "%"), "pct2": ("", "%"),
        "pct_gdp": ("占GDP的", "%"), "pct_gdp_s": ("占GDP的", "%"),
        "rank": ("第", "位"), "score100": ("", "/100"),
        "pop_mn": ("", "{mag}人"),
        "per100k": ("", "/10万人"), "per100k2": ("", "/10万人"),
        "years": ("", "年"),
        "usd_bn": ("", "{mag}美元"), "usd_bn_s": ("", "{mag}美元"),
        "usd_bn1": ("", "{mag}美元"),
    },
    # CLDR zh-Hant, and DGBAS usage: 萬/億/兆 (兆 is 10^12 in Taiwan),
    # 第…名.
    "zh-Hant": {
        "pct": ("", "%"), "pct_s": ("", "%"), "pct2": ("", "%"),
        "pct_gdp": ("占GDP的", "%"), "pct_gdp_s": ("占GDP的", "%"),
        "rank": ("第", "名"), "score100": ("", "/100"),
        "pop_mn": ("", "{mag}人"),
        "per100k": ("", "/10萬人"), "per100k2": ("", "/10萬人"),
        "years": ("", "年"),
        "usd_bn": ("", "{mag}美元"), "usd_bn_s": ("", "{mag}美元"),
        "usd_bn1": ("", "{mag}美元"),
    },
    # CLDR vi (no space before %), and the GSO's usage: "% GDP",
    # triệu/tỷ/nghìn tỷ, "tỷ USD".
    "vi": {
        "pct": ("", "%"), "pct_s": ("", "%"), "pct2": ("", "%"),
        "pct_gdp": ("", "% GDP"), "pct_gdp_s": ("", "% GDP"),
        "rank": ("hạng ", ""), "score100": ("", "/100"),
        "pop_mn": ("", f"{_N}{{mag}}"),
        "per100k": ("", "/100.000 dân"), "per100k2": ("", "/100.000 dân"),
        "years": ("", " năm"),
        "usd_bn": ("", f"{_N}{{mag}} USD"), "usd_bn_s": ("", f"{_N}{{mag}} USD"),
        "usd_bn1": ("", f"{_N}{{mag}} USD"),
    },
    # CLDR he. Numbers and affixes only: the words are in logical order
    # and no bidi marks are inserted — right-to-left layout is out of
    # scope here (COUNTRIES.md).
    "he": {
        "pct": ("", "%"), "pct_s": ("", "%"), "pct2": ("", "%"),
        "pct_gdp": ("", "% מהתוצר"), "pct_gdp_s": ("", "% מהתוצר"),
        "rank": ("מקום ", ""), "score100": ("", "/100"),
        "pop_mn": ("", f"{_N}מיליון"),
        "per100k": ("", " ל-100 אלף"), "per100k2": ("", " ל-100 אלף"),
        "years": ("", " שנים"),
        "usd_bn": ("", f"{_N}מיליארד דולר"),
        "usd_bn_s": ("", f"{_N}מיליארד דולר"),
        "usd_bn1": ("", f"{_N}מיליארד דולר"),
    },
    # Ukrainian: a space before the percent sign (Ukrainian orthography),
    # the amount before the unit, "№" for a rank, "млн"/"млрд"/"трлн" one
    # for one. The hryvnia follows the amount: "2 991 млрд грн".
    # Polish: the amount before the unit, "zł" after it, no space before
    # %, "mld"/"bln" (miliard/bilion) and "24. miejsce".
    "pl": {
        "pct": ("", "%"), "pct_s": ("", "%"), "pct2": ("", "%"),
        "pct_gdp": ("", "% PKB"), "pct_gdp_s": ("", "% PKB"),
        "rank": ("", ". miejsce"), "score100": ("", "/100"),
        "pop_mn": ("", f"{_N}mln"),
        "per100k": ("", "/100 tys."), "per100k2": ("", "/100 tys."),
        "years": ("", " lat"),
        "usd_bn": ("", f"{_N}mld{_N}USD"),
        "usd_bn_s": ("", f"{_N}mld{_N}USD"),
        "usd_bn1": ("", f"{_N}mld{_N}USD"),
    },
    # Russian: a space before %, "млрд долл.", the rouble after the amount.
    "ru": {
        "pct": ("", f"{_N}%"), "pct_s": ("", f"{_N}%"), "pct2": ("", f"{_N}%"),
        "pct_gdp": ("", f"{_N}% ВВП"), "pct_gdp_s": ("", f"{_N}% ВВП"),
        "rank": ("", "-е место"), "score100": ("", "/100"),
        "pop_mn": ("", f"{_N}млн"),
        "per100k": ("", "/100 тыс."), "per100k2": ("", "/100 тыс."),
        "years": ("", " лет"),
        "usd_bn": ("", f"{_N}млрд{_N}долл."),
        "usd_bn_s": ("", f"{_N}млрд{_N}долл."),
        "usd_bn1": ("", f"{_N}млрд{_N}долл."),
    },
    "uk": {
        "pct": ("", f"{_N}%"), "pct_s": ("", f"{_N}%"), "pct2": ("", f"{_N}%"),
        "pct_gdp": ("", f"{_N}% ВВП"),
        "pct_gdp_s": ("", f"{_N}% ВВП"),
        "rank": ("№", ""), "score100": ("", "/100"),
        "pop_mn": ("", f"{_N}млн"),
        "per100k": ("", "/100 тис."), "per100k2": ("", "/100 тис."),
        "years": ("", " років"),
        "usd_bn": ("", f"{_N}млрд{_N}дол."),
        "usd_bn_s": ("", f"{_N}млрд{_N}дол."),
        "usd_bn1": ("", f"{_N}млрд{_N}дол."),
    },
}
for _style, _forms in _STYLE_AFFIX.items():
    for _spec in ("count", "dec3", "dec2", "dec1", "index"):
        _forms.setdefault(_spec, ("", ""))
    for _spec, _form in _forms.items():
        AFFIX[_spec][_style] = _form

# The same for the money specs, per currency. EUR gains the de, it and
# pt-PT forms; the new currencies carry every style of every country that
# uses them. English follows the EU style guide: the symbol before the
# amount, an ISO code (CHF) before it with a space.
_STYLE_CURRENCY = {
    "EUR": {
        "money_bn": {"de": ("", f"{_N}Mrd.{_N}€"), "it": ("", f"{_N}mld{_N}€"),
                     "pt-PT": ("", f"{_N}mil milhões de euros")},
        "money":    {"de": ("", f"{_N}€"), "it": ("", f"{_N}€"),
                     "pt-PT": ("", f"{_N}€")},
    },
    "GBP": {
        "money_bn": {"en": ("£", "bn"), "pt": ("£ ", " bi")},
        "money":    {"en": ("£", ""), "pt": ("£ ", "")},
        "money2":   {"en": ("£", ""), "pt": ("£ ", "")},
    },
    "CHF": {
        "money_bn": {"en": ("CHF ", "bn"), "pt": ("CHF ", " bi"),
                     "de": ("", f"{_N}Mrd.{_N}CHF")},
        "money":    {"en": ("CHF ", ""), "pt": ("CHF ", ""),
                     "de": ("", f"{_N}CHF")},
        "money2":   {"en": ("CHF ", ""), "pt": ("CHF ", ""),
                     "de": ("", f"{_N}CHF")},
    },
    "UAH": {
        "money_bn": {"en": ("₴", "bn"), "uk": ("", f"{_N}млрд{_N}грн"),
                     "pt": ("₴ ", " bi")},
        "money_tn": {"en": ("₴", "tn"), "uk": ("", f"{_N}трлн{_N}грн"),
                     "pt": ("₴ ", " tri")},
        "money":    {"en": ("₴", ""), "uk": ("", f"{_N}грн"),
                     "pt": ("₴ ", "")},
        "money2":   {"en": ("₴", ""), "uk": ("", f"{_N}грн"),
                     "pt": ("₴ ", "")},
    },
    "PLN": {
        "money_bn": {"pl": ("", f"{_N}mld{_N}zł"), "en": ("PLN ", "bn"),
                     "pt": ("PLN ", " bi")},
        "money":    {"pl": ("", f"{_N}zł"), "en": ("PLN ", ""),
                     "pt": ("PLN ", "")},
    },
    "RUB": {
        "money_bn": {"ru": ("", f"{_N}млрд{_N}₽"), "en": ("RUB ", "bn"),
                     "pt": ("RUB ", " bi")},
        "money_tn": {"ru": ("", f"{_N}трлн{_N}₽"), "en": ("RUB ", "tn"),
                     "pt": ("RUB ", " tri")},
        "money":    {"ru": ("", f"{_N}₽"), "en": ("RUB ", ""),
                     "pt": ("RUB ", "")},
    },
    "AUD": {
        "money_bn": {"en": ("A$", "bn"), "pt": ("A$ ", " bi")},
        "money":    {"en": ("A$", ""), "pt": ("A$ ", "")},
    },
    "SGD": {
        "money_bn": {"en": ("S$", "bn"), "pt": ("S$ ", " bi")},
        "money_tn": {"en": ("S$", "tn"), "pt": ("S$ ", " tri")},
        "money":    {"en": ("S$", ""), "pt": ("S$ ", "")},
    },
    "HKD": {
        "money_bn": {"en": ("HK$", "bn"), "zh-Hant": ("", "{mag}港元"),
                     "pt": ("HK$ ", " bi")},
        "money":    {"en": ("HK$", ""), "zh-Hant": ("", "港元"),
                     "pt": ("HK$ ", "")},
    },
    "CLP": {
        "money_bn": {"es": ("$ ", " mm"), "en": ("CLP ", "bn"),
                     "pt": ("CLP$ ", " bi")},
        "money":    {"es": ("$ ", ""), "en": ("CLP ", ""),
                     "pt": ("CLP$ ", "")},
    },
    "PYG": {
        "money_bn": {"es": ("₲ ", " mm"), "en": ("PYG ", "bn"),
                     "pt": ("₲ ", " bi")},
        "money":    {"es": ("₲ ", ""), "en": ("PYG ", ""),
                     "pt": ("₲ ", "")},
    },
    "VES": {
        "money_bn": {"es": ("Bs. ", " mm"), "en": ("VES ", "bn"),
                     "pt": ("Bs. ", " bi")},
        "money":    {"es": ("Bs. ", ""), "en": ("VES ", ""),
                     "pt": ("Bs. ", "")},
    },
    "JPY": {
        "money_bn": {"en": ("¥", "bn"), "pt": ("¥ ", " bi"),
                     "ja": ("", "{mag}円")},
        "money_tn": {"en": ("¥", "tn"), "pt": ("¥ ", " tri"),
                     "ja": ("", "{mag}円")},
        "money":    {"en": ("¥", ""), "pt": ("¥ ", ""), "ja": ("", "円")},
        "money2":   {"en": ("¥", ""), "pt": ("¥ ", ""), "ja": ("", "円")},
    },
    "CNY": {
        "money_bn": {"en": ("CN¥", "bn"), "pt": ("CN¥ ", " bi"),
                     "zh-Hans": ("", "{mag}元")},
        "money_tn": {"en": ("CN¥", "tn"), "pt": ("CN¥ ", " tri"),
                     "zh-Hans": ("", "{mag}元")},
        "money":    {"en": ("CN¥", ""), "pt": ("CN¥ ", ""),
                     "zh-Hans": ("", "元")},
        "money2":   {"en": ("CN¥", ""), "pt": ("CN¥ ", ""),
                     "zh-Hans": ("", "元")},
    },
    "TWD": {
        "money_bn": {"en": ("NT$", "bn"), "pt": ("NT$ ", " bi"),
                     "zh-Hant": ("", "{mag}元")},
        "money_tn": {"en": ("NT$", "tn"), "pt": ("NT$ ", " tri"),
                     "zh-Hant": ("", "{mag}元")},
        "money":    {"en": ("NT$", ""), "pt": ("NT$ ", ""),
                     "zh-Hant": ("", "元")},
        "money2":   {"en": ("NT$", ""), "pt": ("NT$ ", ""),
                     "zh-Hant": ("", "元")},
    },
    # Vietnamese writes "tỷ đồng" with a magnitude word and the ₫ sign
    # after a plain amount (CLDR vi: 1.234 ₫).
    "VND": {
        "money_bn": {"en": ("₫", "bn"), "pt": ("₫ ", " bi"),
                     "vi": ("", f"{_N}{{mag}} đồng")},
        "money_tn": {"en": ("₫", "tn"), "pt": ("₫ ", " tri"),
                     "vi": ("", f"{_N}{{mag}} đồng")},
        "money":    {"en": ("₫", ""), "pt": ("₫ ", ""), "vi": ("", f"{_N}₫")},
        "money2":   {"en": ("₫", ""), "pt": ("₫ ", ""), "vi": ("", f"{_N}₫")},
    },
    # CLDR he puts ₪ after the amount with a space.
    "ILS": {
        "money_bn": {"en": ("₪", "bn"), "pt": ("₪ ", " bi"),
                     "he": ("", f"{_N}מיליארד ₪")},
        "money":    {"en": ("₪", ""), "pt": ("₪ ", ""), "he": ("", f"{_N}₪")},
        "money2":   {"en": ("₪", ""), "pt": ("₪ ", ""), "he": ("", f"{_N}₪")},
    },
}
for _code, _specs in _STYLE_CURRENCY.items():
    for _spec, _forms in _specs.items():
        CURRENCY_AFFIX.setdefault(_code, {}).setdefault(_spec, {}).update(_forms)

# The separators live in core.numstyle, shared with the plates, so a card
# and its plate cannot write the same figure two ways.
SEPARATORS = numstyle.SEPARATORS


def localize_number(num: str, style: str) -> str:
    """Rewrite the decimal and thousands marks for one number style."""
    return numstyle.swap(num, style)


# Numbers inside a sentence: thousands groups or a decimal. A year on its
# own has neither, and a full stop is not a decimal point, so neither is
# touched.
_IN_PROSE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+")


def localize_prose(text: str, style: str) -> str:
    """Rewrite the numbers in a sentence, and only the numbers."""
    if style not in SEPARATORS:
        return text
    return _IN_PROSE.sub(lambda m: numstyle.swap(m.group(0), style), text)


# A style without a ladder writes the spec's magnitude one-for-one, which
# leaves a GDP of 30,861 bn reading as "US$ 30,861bn". From a thousand of
# the spec's unit up, the figure moves one word up instead, to three
# significant digits: US$ 30.9tn, R$ 1,10 tri, 1.41bn people. Each entry
# is (the word at the spec's magnitude, the word a thousand times larger)
# as it appears in that style's suffix. A style that is absent keeps its
# published form on purpose: French and Italian write thousands of
# milliards ("2 991 Md€", INSEE and ISTAT usage), and neither pt-PT nor
# Hebrew has a figure on the site large enough to need one. Population
# steps up only in en and pt: no es, de or ko page has a billion people.
STEP_UP_SPECS = {"money_bn", "usd_bn", "usd_bn_s", "usd_bn1", "pop_mn"}
STEP_UP = {
    "en": (("bn", "tn"), ("M", "bn")),
    "pt": ((" bi", " tri"), (" mi", " bi")),
    # billón = 10^12 (RAE). The Spanish dollar specs are written "bn".
    "es": ((" mm", " billones"), ("bn", " billones")),
    "de": (("Mrd.", "Bio."),),
    "ko": (("십억", "조"),),
    "uk": (("млрд", "трлн"), ("млн", "млрд")),
    "pl": (("mld", "bln"), ("mln", "mld")),
    "ru": (("млрд", "трлн"), ("млн", "млрд")),
}
_STEP_SIG = 3


def _stepped_up(value: float, spec: str, style: str,
                suffix: str) -> tuple[str, str] | None:
    """`value` one magnitude word up, or None when it stays where it is."""
    if spec not in STEP_UP_SPECS or not math.isfinite(value):
        return None
    # The threshold is the figure as it would print, so 999.6 bn steps up
    # rather than rounding to "1,000bn", the form this rule exists to avoid.
    shown = float(NUMFMT[spec].format(value).replace(",", ""))
    if abs(shown) < 1000:
        return None
    for word, larger in STEP_UP.get(style, ()):
        if word in suffix:
            n = value / 1000
            # Count the digits after rounding to three significant ones:
            # 9.996 is 10.0, not 10.00.
            digits = len(str(int(abs(float(f"{n:.{_STEP_SIG}g}")))))
            sign = "+" if "{:+" in NUMFMT[spec] else ""
            return (f"{n:{sign},.{max(0, _STEP_SIG - digits)}f}",
                    suffix.replace(word, larger, 1))
    return None


def format_figure(value: float, spec: str, style: str,
                  prefix: str, suffix: str) -> str:
    """One figure in one number style, affixes included.

    A style with a magnitude ladder rescales the figure onto its own word
    ("{mag}" in the suffix); a figure of a thousand or more of the spec's
    unit moves one word up (STEP_UP); every other figure is formatted with
    the spec's NUMFMT and has its marks swapped.
    """
    scaled = numstyle.rescaled(value, spec, style, NUMFMT[spec])
    if scaled is not None:
        n, mag = scaled
        return f"{prefix}{localize_number(n, style)}{suffix.replace('{mag}', mag)}"
    stepped = _stepped_up(value, spec, style, suffix)
    if stepped is not None:
        n, suffix = stepped
        return f"{prefix}{localize_number(n, style)}{suffix}"
    n = NUMFMT[spec].format(value)
    return f"{prefix}{localize_number(n, style)}{suffix}"


class SiteContext:
    """What a country's chapters.py is handed.

    Mirrors core.context.Context: bound to one country, reads only that
    country's CSVs, and knows its locales and its last complete year.
    """

    def __init__(self, country):
        self.c = country
        self.locales = country.locale_codes
        self.LAST_FULL_YEAR = country.last_full_year

    # ------------------------------------------------------------- data
    def col(self, path: str, column: str, key: str = "year"):
        """(year, value) pairs for one column, blanks dropped, sorted."""
        table = self.c.table(path)
        if not table or column not in table:
            return []
        rows = []
        for y, v in zip(table.get(key, []), table[column]):
            if y is None or v is None or v != v or isinstance(v, str):
                continue
            rows.append((int(y), float(v)))
        return sorted(rows)

    @staticmethod
    def last(pairs, year=None):
        """The latest (year, value), or a specific year if given."""
        if not pairs:
            return None
        if year is not None:
            return next((p for p in pairs if p[0] == year), None)
        return pairs[-1]

    # ------------------------------------------------------- formatting
    def affix(self, spec: str, style: str) -> tuple[str, str]:
        """The (prefix, suffix) a spec takes in one number style."""
        per_locale = AFFIX.get(spec)
        if per_locale is None:
            per_locale = CURRENCY_AFFIX.get(self.c.currency, {}).get(spec)
        if per_locale is None:
            raise KeyError(
                f"{self.c.slug}: no affix for spec {spec!r}. Add it to "
                f"core.sitebuild.AFFIX, or to CURRENCY_AFFIX under "
                f"{self.c.currency!r} if it is a money figure.")
        if style not in per_locale:
            raise KeyError(
                f"{self.c.slug}: spec {spec!r} has no {style!r} form; "
                f"it has {sorted(per_locale)}")
        return per_locale[style]

    def render(self, value: float, spec: str) -> dict[str, str]:
        """A figure written for each of this country's locales.

        Keyed by locale, written in that locale's number style: Portugal's
        "pt" card reads 291 mil milhões de euros, while a Brazilian GDP
        value can use the compact R$ 11,7 tri spec.
        """
        out = {}
        for locale in self.locales:
            style = self.c.number_style(locale)
            prefix, suffix = self.affix(spec, style)
            out[locale] = format_figure(value, spec, style, prefix, suffix)
        return out

    def text(self, **per_locale) -> dict[str, str]:
        """Editorial copy, one string per locale.

        Every locale the country publishes has to be present: a card that
        falls back to English in the middle of a French page reads as a
        bug, and silently serving one is worse than failing the build.
        """
        missing = [l for l in self.locales if l not in per_locale]
        if missing:
            raise KeyError(
                f"{self.c.slug}: copy is missing {missing} "
                f"(got {sorted(per_locale)})")
        return {l: per_locale[l] for l in self.locales}

    def fact(self, pairs, spec: str, year=None, kind="flow") -> dict:
        """One figure for a story to quote: its value per locale, and its year.

        Reads the series the way `stat` does — a flow stops at the last full
        year, a level (kind='level') may be the running one, and `year`
        picks one — but there is no label to write, because the sentence
        around it is the label. A year with no value is an error: a story
        that quotes a number the data do not have is the failure this
        exists to prevent.
        """
        if kind == "flow" and year is None:
            pairs = [p for p in pairs if p[0] <= self.LAST_FULL_YEAR]
        p = self.last(pairs, year)
        if p is None:
            raise KeyError(f"{self.c.slug}: no value for a story fact "
                           f"(year={year!r}, kind={kind!r})")
        return {"value": self.render(p[1], spec), "year": p[0]}

    def story(self, title: dict, beats: list, facts: dict | None = None
              ) -> dict[str, dict]:
        """The plain-language reading of one panel, one per locale.

        A `title`, which states what the panel says rather than naming it,
        and a few short `beats`: mini-stories, each a (head, text) pair of
        `ctx.text(...)`. The first says how to read this kind of chart, the
        middle ones take one thing the panel shows each (what it puts in
        front, what it leaves behind), the last says what it does not tell.
        Three to six, because fewer is a caption and more is a wall.

        `{name}` anywhere in the title, a head or a text is filled with that
        fact's value in the locale's own number style and `{name_year}` with
        its year, so the sentence says what the CSV says and a refetch moves
        both. A placeholder with no fact, or a fact nothing uses, fails the
        build: the first prints a brace to a reader, the second is a number
        that was reworded out of the story and will be wrong the next time
        the data move.
        """
        if not MIN_BEATS <= len(beats) <= MAX_BEATS:
            raise ValueError(
                f"{self.c.slug}: a story has {MIN_BEATS} to {MAX_BEATS} "
                f"beats, got {len(beats)}")
        facts = facts or {}
        used: set[str] = set()

        def fill_in(text: str, loc: str) -> str:
            def fill(m):
                name, tail = m.group(1), m.group(2)
                if name not in facts:
                    raise KeyError(f"{self.c.slug}: story has no fact "
                                   f"{name!r} for {{{name}{tail}}}")
                used.add(name)
                f = facts[name]
                return str(f["year"] if tail else f["value"][loc])
            return re.sub(r"\{(\w+?)(_year)?\}", fill, text)

        def pick(copy: dict, what: str, loc: str) -> str:
            if loc not in copy:
                raise KeyError(f"{self.c.slug}: story {what} is missing "
                               f"[{loc}] (got {sorted(copy)})")
            return fill_in(copy[loc], loc)

        out: dict[str, dict] = {}
        for loc in self.locales:
            out[loc] = {
                "title": pick(title, "title", loc),
                "beats": [{"head": pick(head, f"beat {i + 1} head", loc),
                           "text": pick(text, f"beat {i + 1} text", loc)}
                          for i, (head, text) in enumerate(beats)],
            }
        unused = sorted(set(facts) - used)
        if unused:
            raise KeyError(f"{self.c.slug}: story facts {unused} are "
                           f"never used")
        return out

    def stat(self, label: dict, pairs, spec: str, year=None, kind="flow"):
        """One headline figure, with the year it belongs to.

        kind='flow' for annual totals and averages, which are only
        comparable once the year is complete, so they stop at the
        country's last full year. kind='level' for point-in-time readings
        (a stock, a rate, a closing price), where the latest value is
        genuinely current. kind='projection' for an official forward
        estimate, which is legitimately dated past the last full year —
        shown with its year and never labelled as current.
        """
        if kind == "total":
            # A cumulative count belongs to no single year — deaths
            # recorded across a pandemic, not deaths in 2024 — so it is
            # summed and published without one. Reading its last value
            # instead would quietly report one year as the whole total.
            if not pairs:
                return None
            years = [y for y, _ in pairs]
            return {
                "label": self.text(**label),
                "value": self.render(sum(v for _, v in pairs), spec),
                "year": None,
                # A total has no year but it does have a window, and a
                # cumulative count published without one is unreadable:
                # "COVID-19 deaths recorded · total" could be a year or a
                # decade. The page prints the span instead of the year.
                "span": [min(years), max(years)],
                "asof": "total",
            }
        if kind == "flow" and year is None:
            pairs = [p for p in pairs if p[0] <= self.LAST_FULL_YEAR]
        p = self.last(pairs, year)
        if p is None:
            return None
        return {
            "label": self.text(**label),
            "value": self.render(p[1], spec),
            "year": p[0],
            "asof": {"level": "level",
                     "projection": "projection"}.get(kind, "year"),
        }


# --------------------------------------------------------------- sparkline
def spark(pairs, level: bool = False, last_full_year: int | None = None):
    """A chapter's sparkline, normalised to 0..1 against its own range.

    A flow series is truncated to the last complete year, because the
    running year's partial total would draw a cliff the data does not
    contain. `level=True` marks a stock or a rate read at a moment, where
    the latest reading is genuinely current and is kept.

    The page only needs the shape, so the points are rounded and the years
    carried alongside rather than per point.
    """
    if not pairs:
        return None
    if not level and last_full_year is not None:
        pairs = [p for p in pairs if p[0] <= last_full_year]
    if not pairs:
        return None
    ys = [p[0] for p in pairs]
    vs = [p[1] for p in pairs]
    lo, hi = min(vs), max(vs)
    span = (hi - lo) or 1.0
    return {"from": ys[0], "to": ys[-1],
            "points": [round((v - lo) / span, 4) for v in vs]}


# ------------------------------------------------------------- data tables
def pretty(v: float) -> str:
    """A figure for a data table: enough precision to be useful, no more.

    Trailing zeros are stripped so a column of integers does not read as
    though it were measured to two decimals.
    """
    if abs(v) >= 1_000_000:
        return f"{v:,.0f}"
    if abs(v) >= 100:
        return f"{v:,.1f}".rstrip("0").rstrip(".")
    return f"{v:,.2f}".rstrip("0").rstrip(".")


def table_for(ctx, spec: dict) -> dict:
    """The plate's underlying CSV as a table, one header row per locale.

    This is the only way a reader who cannot see the figure gets the
    numbers, so the cells are the committed values rather than a rounded
    retelling of them.
    """
    rows = ctx.c.rows(spec["csv"], key=spec.get("key", "year")) or {}
    names = [n for n, _ in spec["columns"]]
    ordered = [rows[y] for y in sorted(rows)]
    return {
        "columns": {loc: [label[loc] for _, label in spec["columns"]]
                    for loc in ctx.locales},
        "rows": [[(r.get(n) or "").strip() for n in names] for r in ordered],
        "csv": spec["csv"],
    }


# Sentence skeletons for alt text assembled from a plate's own numbers.
# Templates per language, because they describe the language.
PHRASES = {
    "en": {"intro": "{n} panels: {panels}.",
           "range": "{label} runs from {first} in {y0} to {last} in {y1}",
           "high": "highest {high} in {yh}", "low": "lowest {low} in {yl}",
           "table": "The underlying figures are in the table below.",
           "sep": "; "},
    "pt": {"intro": "{n} painéis: {panels}.",
           "range": "{label} vai de {first} em {y0} a {last} em {y1}",
           "high": "máximo de {high} em {yh}", "low": "mínimo de {low} em {yl}",
           "table": "Os números por trás estão na tabela abaixo.",
           "sep": "; "},
    "fr": {"intro": "{n} panneaux : {panels}.",
           "range": "{label} passe de {first} en {y0} à {last} en {y1}",
           "high": "maximum de {high} en {yh}",
           "low": "minimum de {low} en {yl}",
           "table": "Les chiffres sous-jacents figurent dans le tableau "
                    "ci-dessous.",
           "sep": " ; "},
    "es": {"intro": "{n} paneles: {panels}.",
           "range": "{label} va de {first} en {y0} a {last} en {y1}",
           "high": "máximo de {high} en {yh}", "low": "mínimo de {low} en {yl}",
           "table": "Las cifras subyacentes están en la tabla de abajo.",
           "sep": "; "},
    "ko": {"intro": "패널 {n}개: {panels}.",
           "range": "{label}은 {y0}년 {first}에서 {y1}년 {last}로",
           "high": "최고 {yh}년 {high}", "low": "최저 {yl}년 {low}",
           "table": "기초 수치는 아래 표에 있습니다.",
           "sep": "; "},
}


# How an alt text assembled from a chapter's headline figures reads.
STAT_PHRASES = {
    "en": {"joiner": "; ", "in": "{label} {value} in {year}",
           "noyear": "{label} {value}",
           "tail": "Every figure is read from this country's committed CSVs."},
    "pt": {"joiner": "; ", "in": "{label} {value} em {year}",
           "noyear": "{label} {value}",
           "tail": "Cada número é lido dos CSVs versionados deste país."},
    "fr": {"joiner": " ; ", "in": "{label} {value} en {year}",
           "noyear": "{label} {value}",
           "tail": "Chaque chiffre est lu dans les CSV versionnés de ce pays."},
    "es": {"joiner": "; ", "in": "{label} {value} en {year}",
           "noyear": "{label} {value}",
           "tail": "Cada cifra se lee de los CSV versionados de este país."},
    "ko": {"joiner": "; ", "in": "{label} {year}년 {value}",
           "noyear": "{label} {value}",
           "tail": "모든 수치는 이 나라의 커밋된 CSV에서 읽습니다."},
}


def describe_from_stats(chapter: dict, locale: str) -> str | None:
    """Alt text built from a chapter's own headline figures.

    The weakest of the three descriptions and the last to be tried: it
    states the figures the card already shows rather than the shape of the
    lines, which is what a hand-written `alt` would say. It exists because
    an undescribed figure gives a screen-reader user nothing at all, and
    every number in it is read from the CSVs rather than composed.
    """
    stats = chapter.get("stats") or []
    if not stats:
        return None
    ph = STAT_PHRASES.get(locale)
    if ph is None:
        return None
    title = (chapter.get("title") or {}).get(locale, "")
    blurb = (chapter.get("blurb") or {}).get(locale, "")
    parts = []
    for s in stats:
        label = s["label"].get(locale, "")
        value = s["value"].get(locale, "")
        year = s.get("year")
        template = ph["in"] if year else ph["noyear"]
        parts.append(template.format(label=label, value=value, year=year))
    head = ". ".join(x.rstrip(".") for x in (title, blurb) if x)
    return f"{head}. " + ph["joiner"].join(parts) + ". " + ph["tail"]


def describe(ctx, chapter: dict, locale: str) -> str | None:
    """Alt text assembled from the plate's own numbers.

    Only used when a chapter has no hand-written `alt`: a described figure
    is better than an undescribed one, but a sentence someone wrote about
    what the plate actually shows is better than either.
    """
    spec = chapter.get("table")
    if not spec or not spec.get("facts"):
        return None
    ph = PHRASES.get(locale)
    if ph is None:
        return None
    table = ctx.c.rows(spec["csv"], key=spec.get("key", "year")) or {}
    years = sorted(table)
    labels = {n: label.get(locale, label.get("en"))
              for n, label in spec["columns"]}
    parts = []
    for name in spec["facts"]:
        got = []
        for y in years:
            raw = (table[y].get(name) or "").strip()
            try:
                got.append((y, float(raw)))
            except ValueError:
                continue
        if not got:
            continue
        hi = max(got, key=lambda p: p[1])
        lo = min(got, key=lambda p: p[1])
        piece = ph["range"].format(
            label=labels.get(name, name), first=pretty(got[0][1]),
            y0=got[0][0], last=pretty(got[-1][1]), y1=got[-1][0])
        piece += ", " + ph["high"].format(high=pretty(hi[1]), yh=hi[0])
        piece += ", " + ph["low"].format(low=pretty(lo[1]), yl=lo[0])
        parts.append(piece)
    panels = chapter.get("panels") or []
    out = ph["intro"].format(
        n=len(panels) or 4,
        panels=", ".join(p.rstrip(".") for p in panels)) if panels else ""
    if parts:
        out = (out + " " if out else "") + ph["sep"].join(parts) + ". "
    out += ph["table"]
    # Only the numbers: swapping every mark in the sentence turned its
    # full stops into commas ("na tabela abaixo,") on every pt alt text.
    return localize_prose(out, ctx.c.number_style(locale))


# ---------------------------------------------------------- provenance
# The five SOURCES.yaml files grew three different shapes. All three are
# read rather than rewritten, because the manifests are the reviewed record
# of where each number came from and reformatting them by hand is how a
# publisher attribution gets attached to the wrong file.
#
#   datasets: [{file, title, publisher, official}]        argentina
#   files: {"macro/gdp.csv": {title, publisher, ...}}     south-korea
#   macro: {"gdp.csv": {source, url, notes}}              brasil, france, usa
#
# A dataset is treated as official unless the manifest says otherwise, except
# where it carries an explicit `official: false` — the market references in
# the Argentine manifest, which are not official statistics and are labelled
# as such on the page.
def _clip(text: str, limit: int) -> str:
    """Shorten to `limit` characters at a word boundary, with an ellipsis."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    head = cut.rsplit(" ", 1)[0] if " " in cut else cut
    return head.rstrip(" ,;:.—-") + "…"


def datasets_for(country) -> list[dict]:
    """Every CSV behind a country's plates, with its publisher and coverage.

    Coverage is read from the CSV itself rather than from the manifest, so a
    file that gains a year reports it without anyone editing the YAML.
    """
    import yaml

    path = country.dir / "SOURCES.yaml"
    if not path.exists():
        return []
    manifest = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    entries: list[dict] = []
    if isinstance(manifest.get("datasets"), list):
        for e in manifest["datasets"]:
            entries.append({"file": e["file"], "title": e.get("title", ""),
                            "publisher": e.get("publisher", ""),
                            "url": e.get("url", ""),
                            "official": bool(e.get("official", True))})
    elif isinstance(manifest.get("files"), dict):
        for rel, e in manifest["files"].items():
            entries.append({"file": rel, "title": e.get("title", ""),
                            "publisher": e.get("publisher", ""),
                            "url": e.get("url", ""),
                            "official": bool(e.get("official", True))})
    else:
        for group, files in manifest.items():
            if not isinstance(files, dict) or group == "meta":
                continue
            for name, e in files.items():
                if not isinstance(e, dict):
                    continue
                entries.append({
                    "file": f"{group}/{name}",
                    "title": e.get("notes", "") or e.get("title", ""),
                    "publisher": e.get("source", "") or e.get("publisher", ""),
                    "url": e.get("url", ""),
                    "official": bool(e.get("official", True))})

    out = []
    for e in entries:
        table = None
        try:
            table = country.table(e["file"])
        except Exception:  # a manifest entry whose file has moved
            table = None
        years = sorted(y for y in (table or {}).get("year", []) if y)
        out.append({
            **e,
            "publisher": " ".join(str(e["publisher"]).split()),
            # The manifest's notes run to paragraphs; the table wants a
            # line. Cut at a word, not mid-word: "It is here because no"
            # reads as a broken sentence rather than a shortened one.
            "title": _clip(" ".join(str(e["title"]).split()), 150),
            "coverage": f"{years[0]}-{years[-1]}" if years else "—",
            "columns": len(table) if table else 0,
            "present": table is not None,
        })
    return sorted(out, key=lambda r: r["file"])


def _chapters_module(country):
    from core.sideload import sibling
    return sibling(str(country.dir / "chapters.py"), "chapters")


def headline_for(country) -> list[dict]:
    """The figures a country carries above its plates, if it declares any.

    Optional: three of the five never had a headline strip, and an empty
    one is better than an invented one.
    """
    module = _chapters_module(country)
    fn = getattr(module, "headline", None)
    if fn is None:
        return []
    return [s for s in fn(SiteContext(country)) if s]


def chapters_for(country) -> list[dict]:
    """Load and evaluate one country's chapter declarations."""
    module = _chapters_module(country)
    ctx = SiteContext(country)
    built = module.build(ctx)
    out = []
    for ch in built:
        ch = dict(ch)
        pairs = ch.pop("spark", None)
        level = ch.pop("spark_level", False)
        if pairs is not None:
            ch["spark"] = spark(pairs, level=level,
                                last_full_year=country.last_full_year)
        ch["stats"] = [s for s in ch.get("stats", []) if s]
        spec = ch.get("table")
        if spec:
            ch["table"] = table_for(ctx, spec)
        # Three ways to describe a figure, best first. A sentence someone
        # wrote about what the plate shows beats one assembled from its
        # facts, which beats one assembled from the card's own numbers,
        # which beats leaving a figure undescribed.
        if not ch.get("alt"):
            alt = {}
            for loc in country.locale_codes:
                alt[loc] = (describe(ctx, {**ch, "table": spec}, loc)
                            if spec else None) \
                    or describe_from_stats(ch, loc)
            ch["alt"] = alt if any(alt.values()) else None
        out.append(ch)
    return out


def write_data_json(country, chapters: list[dict], out: Path) -> Path:
    """The machine-readable copy of what the pages show."""
    payload = {
        "country": country.slug,
        "locales": list(country.locale_codes),
        "default_locale": country.default_locale,
        "chapters": chapters,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    return out
